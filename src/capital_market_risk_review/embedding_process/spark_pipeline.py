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

