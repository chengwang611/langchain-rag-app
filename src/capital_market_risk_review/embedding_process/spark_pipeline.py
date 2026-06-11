"""PySpark ingestion + chunking + embedding orchestration.

This module is built for daily Airflow triggering over high document volumes.
For phase 1, vectors are persisted to an in-memory backend; backend abstraction
allows a later swap to PGVector without changing Spark job control flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from langchain_core.documents import Document
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
        ]
    )
)


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[dict]:
    """Chunk a single document text into overlapping windows.

    EXTEND:
    - Replace with sentence-aware chunking for cleaner semantic boundaries.
    - Use token-aware splitters if targeting strict token budgets.
    """
    if not text:
        return []

    chunks: List[dict] = []
    step = max(1, chunk_size - chunk_overlap)
    idx = 0
    chunk_idx = 0
    while idx < len(text):
        window = text[idx : idx + chunk_size].strip()
        if window:
            chunks.append({"chunk_index": chunk_idx, "chunk_text": window})
            chunk_idx += 1
        idx += step
    return chunks


@dataclass
class EmbeddingPipelineConfig:
    chunk_size: int = 1200
    chunk_overlap: int = 200


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
        """Return an exploded chunk DataFrame with one row per text chunk."""
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
                        "chunk_id": chunk_id,
                        "source_id": chunk_id,
                    },
                )
            )
        return docs

    def run(self, spark: SparkSession, source_df: DataFrame) -> dict:
        """Execute end-to-end chunking and persistence.

        Note: phase 1 in-memory backend persists in driver process only.
        For very large jobs, this is intentionally a stepping stone.

        EXTEND:
        - Move persistence into a scalable sink (PGVector) and avoid driver-side
          materialization by writing chunks partition-wise.
        - Add checkpointing/resume semantics for long-running Spark jobs.
        """
        self.validate_input_schema(source_df)
        chunks_df = self.build_chunks_df(source_df).cache()

        total_docs = source_df.count()
        total_chunks = chunks_df.count()
        distinct_funds = chunks_df.select("fund_id").distinct().count()

        # Phase 1: collect in streaming fashion on driver and persist in batches.
        # This keeps code simple and deterministic for local validation.
        # EXTEND: replace toLocalIterator with partition writes to PGVector.
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

        return {
            "documents_read": total_docs,
            "chunks_created": total_chunks,
            "funds_processed": distinct_funds,
            "chunks_persisted": persisted,
            "backend_total_documents": self.backend.total_documents(),
        }

