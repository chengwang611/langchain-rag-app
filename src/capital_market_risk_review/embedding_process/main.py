"""Airflow-triggerable PySpark embedding process entrypoint.

This module is intentionally separated from the online review API path.
Use it as a daily batch job to ingest large report volumes across many fund IDs.

Example (local):
  python -m capital_market_risk_review.embedding_process.main \
    --process-date 2026-06-10 \
    --input-jsonl /path/to/reports.jsonl \
    --vector-backend in-memory
"""

from __future__ import annotations

import argparse
import os
from datetime import date

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from .spark_pipeline import EmbeddingPipelineConfig, SparkEmbeddingPipeline
from .vector_backend import InMemoryFundVectorStore, PGVectorFundStore


def _build_spark(app_name: str, shuffle_partitions: int) -> SparkSession:
    """Create Spark session with practical defaults for daily batch execution."""
    return (
        SparkSession.builder.appName(app_name)
        # EXTEND: tune partitions based on cluster size and input volume.
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        # EXTEND: configure dynamic allocation and adaptive query execution.
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )


def _load_source_df(spark: SparkSession, input_jsonl: str | None, process_date: str):
    """Load source documents from jsonl or generate synthetic demo data.

    Required schema:
    - fund_id
    - document_id
    - report_date
    - source_file
    - text
    """
    if input_jsonl:
        # Expected format: one JSON object per line.
        df = spark.read.json(input_jsonl)
        return df.withColumn("report_date", F.coalesce(F.col("report_date"), F.lit(process_date)))

    # Demo fallback if no input path is provided.
    # EXTEND: replace with Azure Blob / ADLS / S3 readers in production.
    sample = []
    for fund_idx in range(1, 11):
        fund_id = f"FUND-{fund_idx:04d}"
        for doc_idx in range(1, 6):
            sample.append(
                {
                    "fund_id": fund_id,
                    "document_id": f"{fund_id}-DOC-{doc_idx:03d}",
                    "report_date": process_date,
                    "source_file": f"{fund_id}_risk_report_{doc_idx:03d}.txt",
                    "text": (
                        "VaR utilization increased significantly with rate volatility. "
                        "Liquidity assumptions are stale and counterparty margin latency rose. "
                        "Model re-validation is overdue after regime change. "
                    )
                    * 25,
                }
            )
    return spark.createDataFrame(sample)


def _build_backend(name: str):
    """Select vector backend.

    Phase 1 default is in-memory. PGVector is intentionally scaffolded for easy
    switch once infra is ready.
    """
    if name == "in-memory":
        return InMemoryFundVectorStore()

    if name == "pgvector":
        conn = os.getenv("PGVECTOR_CONNECTION_STRING", "")
        if not conn:
            raise ValueError(
                "PGVECTOR_CONNECTION_STRING is required when --vector-backend pgvector"
            )
        return PGVectorFundStore(connection_string=conn)

    raise ValueError(f"Unsupported backend: {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PySpark ingestion + embedding process for daily Airflow runs."
    )
    parser.add_argument(
        "--process-date",
        default=str(date.today()),
        help="Business process date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--input-jsonl",
        default=None,
        help="Path to JSONL source documents. If omitted, synthetic demo data is used.",
    )
    parser.add_argument(
        "--vector-backend",
        default="in-memory",
        choices=["in-memory", "pgvector"],
        help="Vector store backend implementation.",
    )
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--chunk-overlap", type=int, default=200)
    parser.add_argument("--spark-app-name", default="risk-embedding-process")
    parser.add_argument("--shuffle-partitions", type=int, default=200)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    spark = _build_spark(
        app_name=args.spark_app_name,
        shuffle_partitions=args.shuffle_partitions,
    )

    try:
        source_df = _load_source_df(
            spark=spark,
            input_jsonl=args.input_jsonl,
            process_date=args.process_date,
        )
        backend = _build_backend(args.vector_backend)
        pipeline = SparkEmbeddingPipeline(
            backend=backend,
            config=EmbeddingPipelineConfig(
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
            ),
        )

        metrics = pipeline.run(spark=spark, source_df=source_df)
        print("[embedding-process] completed")
        for k, v in metrics.items():
            print(f"  - {k}: {v}")
        return 0
    finally:
        spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())

