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
import json
import os
import sys
from datetime import date
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Support both execution styles:
# 1) python -m capital_market_risk_review.embedding_process.main
# 2) python src/capital_market_risk_review/embedding_process/main.py
try:
    from .spark_pipeline import EmbeddingPipelineConfig, SparkEmbeddingPipeline
    from .vector_backend import FileFundVectorStore, InMemoryFundVectorStore, PGVectorFundStore
except ImportError:
    project_src = Path(__file__).resolve().parents[2]
    if str(project_src) not in sys.path:
        sys.path.insert(0, str(project_src))
    from capital_market_risk_review.embedding_process.spark_pipeline import (
        EmbeddingPipelineConfig,
        SparkEmbeddingPipeline,
    )
    from capital_market_risk_review.embedding_process.vector_backend import (
        FileFundVectorStore,
        InMemoryFundVectorStore,
        PGVectorFundStore,
    )


def _resolve_python_exec() -> str:
    """Return one interpreter path for Spark driver and executors.

    Precedence keeps behavior predictable in k8s:
    1) explicit app override
    2) existing Spark env override
    3) current process interpreter
    """
    return (
        os.environ.get("EMBEDDING_PROCESS_PYTHON_EXEC")
        or os.environ.get("PYSPARK_PYTHON")
        or sys.executable
    )


def _build_spark(app_name: str, shuffle_partitions: int) -> SparkSession:
    """Create a standard Spark session for batch ingestion jobs."""
    python_exec = _resolve_python_exec()

    # Keep Spark worker/driver interpreter aligned to avoid version mismatch.
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", python_exec)
    os.environ.setdefault("PYSPARK_PYTHON", python_exec)

    return (
        SparkSession.builder.appName(app_name)
        .config("spark.pyspark.driver.python", python_exec)
        .config("spark.pyspark.python", python_exec)
        # These configs are important when Spark executors run in separate k8s pods.
        .config("spark.executorEnv.PYSPARK_PYTHON", python_exec)
        .config("spark.executorEnv.PYSPARK_DRIVER_PYTHON", python_exec)
        .config("spark.kubernetes.driverEnv.PYSPARK_PYTHON", python_exec)
        .config("spark.kubernetes.driverEnv.PYSPARK_DRIVER_PYTHON", python_exec)
        .config("spark.kubernetes.executorEnv.PYSPARK_PYTHON", python_exec)
        .config("spark.kubernetes.executorEnv.PYSPARK_DRIVER_PYTHON", python_exec)
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
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
        df = spark.read.json(input_jsonl)
        return df.withColumn("report_date", F.coalesce(F.col("report_date"), F.lit(process_date)))

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

    # Avoid createDataFrame(sample) to keep the demo path independent from pyarrow.
    json_rows = [json.dumps(x) for x in sample]
    rdd = spark.sparkContext.parallelize(json_rows)
    return spark.read.json(rdd)


def _build_backend(name: str, file_backend_path: str):
    """Select vector backend implementation."""
    if name == "in-memory":
        return InMemoryFundVectorStore()

    if name == "file":
        return FileFundVectorStore(storage_path=file_backend_path)

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
        choices=["in-memory", "file", "pgvector"],
        help="Vector store backend implementation.",
    )
    parser.add_argument(
        "--file-backend-path",
        default=".local_data/fund_chunks.jsonl",
        help="Local JSONL path used when --vector-backend file.",
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
        backend = _build_backend(args.vector_backend, args.file_backend_path)
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
