"""PySpark ingestion + chunking + embedding orchestration.

This module is built for daily Airflow triggering over high document volumes.
The backend abstraction (VectorStoreBackend protocol) allows transparent
switching between driver-local stores (file, in-memory) and external databases
(PGVector) without changing the Spark pipeline logic.

Write strategy is selected automatically based on the backend:
- Driver-local backends (file, in-memory): use toLocalIterator() to collect
  data to the driver before writing.
- External database backends (PGVector): use foreachPartition() to write
  in parallel from executor tasks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T

from .vector_backend import VectorStoreBackend


# UDF output schema for exploded chunk rows.
_CHUNK_SCHEMA = T.ArrayType(
    T.StructType(
        [
            T.StructField("chunk_index", T.IntegerType(), nullable=False),
            T.StructField("chunk_text", T.StringType(), nullable=False),
            T.StructField("section_title", T.StringType(), nullable=True),
            T.StructField("token_estimate", T.IntegerType(), nullable=False),
        ]
    )
)


_SECTION_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+|(?:section\s+)?\d+(?:\.\d+)*[.)]?\s+|[A-Z][A-Z0-9 /&(),:;\-]{8,})"
)
_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def _normalize_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph and heading boundaries."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _estimate_tokens(text: str) -> int:
    """Estimate token count without binding Spark executors to a model tokenizer package."""
    return len(_TOKEN_RE.findall(text))


def _length_function(text: str) -> int:
    """Length function used by the splitter; approximates model-token budget."""
    return _estimate_tokens(text)


def _infer_section_title(chunk: str, previous_section: str | None = None) -> str | None:
    """Infer the most relevant heading visible in a chunk."""
    for line in chunk.splitlines():
        candidate = line.strip().strip("#").strip()
        if candidate and len(candidate) <= 140 and _SECTION_HEADING_RE.match(line):
            return candidate
    return previous_section


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[dict]:
    """Chunk a single document into semantic, overlap-preserving windows.

    The splitter prefers larger document boundaries first (section breaks,
    paragraphs, sentences, words) before falling back to characters. Chunk size
    and overlap are interpreted as approximate token budgets through
    ``_length_function`` so retrieval chunks better align with embedding/LLM
    context limits than raw character windows.
    """
    normalized = _normalize_text(text or "")
    if not normalized:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=_length_function,
        separators=[
            "\n## ",
            "\n# ",
            "\n\n",
            "\n",
            ". ",
            "; ",
            ", ",
            " ",
            "",
        ],
        keep_separator=True,
        strip_whitespace=True,
    )

    chunks: List[dict] = []
    current_section: str | None = None
    for chunk_text in splitter.split_text(normalized):
        cleaned = chunk_text.strip()
        if not cleaned:
            continue
        current_section = _infer_section_title(cleaned, current_section)
        chunks.append(
            {
                "chunk_index": len(chunks),
                "chunk_text": cleaned,
                "section_title": current_section,
                "token_estimate": _estimate_tokens(cleaned),
            }
        )
    return chunks


@dataclass
class EmbeddingPipelineConfig:
    # Approximate token budget, not raw characters. 600 tokens is a balanced
    # default for capital-market risk narratives: enough context for coherent
    # clauses/tables while keeping retrieval focused.
    chunk_size: int = 600
    chunk_overlap: int = 100

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")


class SparkEmbeddingPipeline:
    """Separated ingestion and embedding pipeline executed via PySpark.

    Input DataFrame contract (required columns):
    - fund_id: str
    - document_id: str
    - report_date: str (YYYY-MM-DD)
    - source_file: str
    - text: str

    Output:
    - Documents are chunked and persisted through backend.add_documents().

    EXTEND:
    - Add quality filters (min text length, language detection).
    - Add deduplication by (fund_id, document_hash).
    - Write run metrics to a monitoring table (e.g. Delta, Postgres).
    """

    def __init__(self, backend: VectorStoreBackend, config: EmbeddingPipelineConfig):
        self.backend = backend
        self.config = config

    def validate_input_schema(self, df: DataFrame) -> None:
        required = {"fund_id", "document_id", "report_date", "source_file", "text"}
        present = set(df.columns)
        missing = required - present
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

    def build_chunks_df(self, df: DataFrame) -> DataFrame:
        """Return an exploded chunk DataFrame with one row per semantic text chunk."""
        chunk_udf = F.udf(
            lambda x: _chunk_text(
                text=x,
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
            ),
            _CHUNK_SCHEMA,
        )

        return (
            df.withColumn("chunks", chunk_udf(F.col("text")))
            .withColumn("chunk", F.explode(F.col("chunks")))
            .select(
                F.col("fund_id"),
                F.col("document_id"),
                F.col("report_date"),
                F.col("source_file"),
                F.col("chunk.chunk_index").alias("chunk_index"),
                F.col("chunk.chunk_text").alias("chunk_text"),
                F.col("chunk.section_title").alias("section_title"),
                F.col("chunk.token_estimate").alias("token_estimate"),
            )
        )

    def _to_documents(self, rows: Iterable) -> List[Document]:
        docs: List[Document] = []
        for row in rows:
            chunk_id = f"{row.fund_id}:{row.document_id}:{row.chunk_index}"
            docs.append(
                Document(
                    page_content=row.chunk_text,
                    metadata={
                        "fund_id": row.fund_id,
                        "document_id": row.document_id,
                        "report_date": row.report_date,
                        "source_file": row.source_file,
                        "chunk_index": row.chunk_index,
                        "section_title": row.section_title,
                        "token_estimate": row.token_estimate,
                        "chunk_id": chunk_id,
                        "source_id": chunk_id,
                    },
                )
            )
        return docs

    def _write_via_driver(self, chunks_df: DataFrame) -> int:
        """Collect chunks to driver and write via backend.add_documents().

        Used for driver-local backends (file, in-memory) that cannot be
        accessed from executor tasks. Data is collected in streaming fashion
        using toLocalIterator() and persisted in batches to avoid holding
        all chunks in driver memory at once.

        This is the original phase 1 strategy — simple, deterministic,
        and suitable for local validation and small-to-medium datasets.
        """
        persisted = 0
        batch: List = []
        batch_size = 1000
        for row in chunks_df.toLocalIterator():
            batch.append(row)
            if len(batch) >= batch_size:
                persisted += self.backend.add_documents(self._to_documents(batch))
                batch = []
        if batch:
            persisted += self.backend.add_documents(self._to_documents(batch))
        return persisted

    def _write_via_partitions(self, chunks_df: DataFrame) -> int:
        """Write chunks in parallel from each Spark partition.

        Used for external database backends (PGVector) that can be connected
        to directly from executor tasks. Each partition opens its own backend
        connection and writes its chunk batch independently.

        This strategy:
        - Avoids collecting all data to the driver (scales to any dataset size)
        - Writes in parallel across all available Spark executors
        - Requires the backend to be serializable or reconstructible on executors
        """
        backend = self.backend
        to_documents = self._to_documents

        def write_partition(rows_iter):
            batch = list(rows_iter)
            if not batch:
                return
            backend.add_documents(to_documents(batch))

        chunks_df.foreachPartition(write_partition)

        # foreachPartition doesn't return a count, so estimate from source.
        return chunks_df.count()

    def run(self, spark: SparkSession, source_df: DataFrame) -> dict:
        """Execute end-to-end chunking and persistence.

        Write strategy is selected automatically:
        - Driver-local backends (file, in-memory): toLocalIterator()
        - External database backends (PGVector): foreachPartition()

        EXTEND:
        - Add checkpointing/resume semantics for long-running Spark jobs.
        - Add quality filters (min text length, language detection).
        - Add deduplication by (fund_id, document_hash).
        """
        self.validate_input_schema(source_df)
        chunks_df = self.build_chunks_df(source_df).cache()

        total_docs = source_df.count()
        total_chunks = chunks_df.count()
        distinct_funds = chunks_df.select("fund_id").distinct().count()

        if self.backend.requires_driver_local_write:
            print(
                f"[spark-pipeline] backend requires driver-local write "
                f"({type(self.backend).__name__}) — using toLocalIterator()"
            )
            persisted = self._write_via_driver(chunks_df)
        else:
            print(
                f"[spark-pipeline] backend supports distributed write "
                f"({type(self.backend).__name__}) — using foreachPartition()"
            )
            persisted = self._write_via_partitions(chunks_df)

        return {
            "documents_read": total_docs,
            "chunks_created": total_chunks,
            "funds_processed": distinct_funds,
            "chunks_persisted": persisted,
            "backend_total_documents": self.backend.total_documents(),
        }

