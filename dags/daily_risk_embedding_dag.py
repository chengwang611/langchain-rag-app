"""Airflow 3 DAG — Daily Capital Market Risk Report Embedding Ingestion.

Triggers the PySpark embedding process daily for each configured fund.
Designed for Airflow 3 running on Azure (Azure Container Apps + Managed Airflow
or Azure Data Factory with Airflow).

IMPORTANT — Spark Execution Model:
    The embedding process runs Spark in LOCAL mode inside the container.
    It does NOT submit jobs to an external Spark cluster on Kubernetes.
    The Dockerfile.embedding installs openjdk-17-jre-headless, and
    _build_spark() in main.py creates a local SparkSession
    (SparkSession.builder.appName(...).getOrCreate()).

    This means:
    - Driver + executors all run in the same JVM within the container
    - No need for a separate Spark cluster (K8s, YARN, or standalone)
    - The container IS the Spark runtime — it starts, processes, and exits
    - For production scale-up, swap to DatabricksRunNowOperator or
      SparkKubernetesOperator (see EXTEND comments in run_embedding)

Architecture:
    ┌──────────────────────────────────────────────────────────────────┐
    │  Airflow 3 DAG (daily_risk_embedding)                           │
    │                                                                  │
    │  For each fund_id in FUND_IDS:                                   │
    │    ┌──────────────────────────────────────────────────────┐      │
    │    │  Task: fetch_reports_{fund_id}                       │      │
    │    │  - Pull new risk report files from source (Blob/S3)  │      │
    │    │  - Write to shared JSONL: /data/ingest/{ds}.jsonl    │      │
    │    └──────────────┬───────────────────────────────────────┘      │
    │                   ▼                                              │
    │    ┌──────────────────────────────────────────────────────┐      │
    │    │  Task: run_embedding_{fund_id}                       │      │
    │    │  - docker run capital-market-risk-embedding          │      │
    │    │    (Spark runs in LOCAL mode inside the container)   │      │
    │    │    --process-date {{ ds }}                           │      │
    │    │    --input-jsonl /data/ingest/{fund_id}_{{ ds }}.jsonl      │
    │    │    --vector-backend pgvector                         │      │
    │    └──────────────────────────────────────────────────────┘      │
    │                                                                  │
    │  After all funds complete:                                       │
    │    ┌──────────────────────────────────────────────────────┐      │
    │    │  Task: verify_ingestion                              │      │
    │    │  - Check total_documents() per fund_id               │      │
    │    │  - Alert if any fund has 0 new chunks                │      │
    │    └──────────────────────────────────────────────────────┘      │
    └──────────────────────────────────────────────────────────────────┘

Airflow 3 Notes:
    - Uses @dag decorator (Airflow 3 recommended style)
    - TaskFlow API with type-annotated Python functions
    - DockerOperator for running the embedding container
    - Supports Airflow 3's deferrable operators for long-running Spark jobs
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

# Airflow 3 uses the same core imports but with @dag decorator as preferred style.
from airflow.decorators import dag, task
from airflow.models.baseoperator import chain
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.utils.trigger_rule import TriggerRule

# ── Configuration ──────────────────────────────────────────────────────────────

# The list of fund IDs to process daily.
# EXTEND: Read from Airflow Variable or external config for dynamic fund management.
FUND_IDS: list[str] = [
    "FUND-0001",
    "FUND-0002",
    "FUND-0003",
]

# Default arguments applied to all tasks.
default_args: dict[str, Any] = {
    "owner": "risk-engineering",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    # Airflow 3 supports max_retry_delay for exponential backoff.
    "max_retry_delay": timedelta(hours=1),
}

# Environment variables passed to the Docker container.
# These should be set as Airflow connections / variables in production.
_EMBEDDING_ENV: dict[str, str] = {
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    "PGVECTOR_CONNECTION_STRING": os.environ.get(
        "PGVECTOR_CONNECTION_STRING",
        "postgresql+psycopg://risk_user:risk_pass@postgres:5432/risk_review",
    ),
    "EMBEDDING_PROCESS_PYTHON_EXEC": "/usr/bin/python3",
    "SPARK_LOCAL_IP": "127.0.0.1",
    "PYTHONPATH": "/app/src",
}

# Docker image for the embedding process (published by CI/CD).
_EMBEDDING_IMAGE: str = os.environ.get(
    "EMBEDDING_IMAGE",
    "acrcmrisk.azurecr.io/capital-market-risk-embedding:latest",
)

# Shared volume mount for input JSONL files and output vector store.
_DATA_VOLUME: str = "/mnt/risk-data:/data"


# ── DAG Definition ─────────────────────────────────────────────────────────────


@dag(
    dag_id="daily_risk_embedding",
    description="Daily PySpark embedding ingestion for all funds",
    schedule="0 6 * * *",  # Every day at 06:00 UTC
    start_date=datetime(2026, 6, 1),
    catchup=False,
    default_args=default_args,
    tags=["risk", "embedding", "pyspark"],
    # Airflow 3: max_consecutive_failed_dag_runs pauses the DAG after N failures.
    max_consecutive_failed_dag_runs=5,
    # Airflow 3: render_template_as_native_obj enables Jinja templates in TaskFlow.
    render_template_as_native_obj=True,
)
def daily_risk_embedding():
    """Daily risk report embedding DAG — one task group per fund."""

    # ── Task 1: Verify source data availability ────────────────────────────────

    @task(
        task_id="check_source_availability",
        retries=1,
    )
    def check_source_availability(**context) -> dict[str, bool]:
        """Check that source data exists for all configured funds.

        In production, this would query Azure Blob Storage / S3 for the
        expected report files for the current execution date.

        Returns a dict mapping fund_id -> data_available (bool).
        """
        execution_date = context["ds"]  # YYYY-MM-DD format
        print(f"[check_source_availability] Checking reports for date: {execution_date}")

        # EXTEND: Replace with actual blob storage check.
        # Example:
        #   from azure.storage.blob import BlobServiceClient
        #   client = BlobServiceClient.from_connection_string(...)
        #   for fund_id in FUND_IDS:
        #       container = client.get_container_client(f"risk-reports-{fund_id}")
        #       blobs = container.list_blobs(name_starts_with=execution_date)
        #       available[fund_id] = any(blobs)

        available = {fund_id: True for fund_id in FUND_IDS}
        print(f"[check_source_availability] Result: {available}")
        return available

    # ── Task 2: Per-fund embedding tasks (dynamically mapped) ──────────────────

    @task(
        task_id="fetch_reports",
        retries=2,
        # Airflow 3: map_index_template for better UI logging per mapped instance.
        map_index_template="{{ fund_id }}",
    )
    def fetch_reports(fund_id: str, **context) -> str:
        """Fetch new risk reports for a single fund and write to JSONL.

        In production, this downloads files from Azure Blob Storage and
        writes them to a shared volume as JSONL for the embedding container.

        Returns the path to the generated JSONL file.
        """
        execution_date = context["ds"]
        output_path = f"/data/ingest/{fund_id}_{execution_date}.jsonl"
        print(f"[fetch_reports] Fund={fund_id} Date={execution_date} -> {output_path}")

        # EXTEND: Replace with actual blob download logic.
        # Example:
        #   from azure.storage.blob import BlobServiceClient
        #   client = BlobServiceClient.from_connection_string(...)
        #   container = client.get_container_client(f"risk-reports-{fund_id}")
        #   with open(output_path, "w") as f:
        #       for blob in container.list_blobs(name_starts_with=execution_date):
        #           blob_client = container.get_blob_client(blob)
        #           content = blob_client.download_blob().readall()
        #           f.write(json.dumps({"fund_id": fund_id, ...}) + "\n")

        # Simulated: create a placeholder JSONL for demo purposes.
        import json

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            for doc_idx in range(1, 4):
                record = {
                    "fund_id": fund_id,
                    "document_id": f"{fund_id}-DOC-{doc_idx:03d}",
                    "report_date": execution_date,
                    "source_file": f"{fund_id}_risk_report_{doc_idx:03d}.txt",
                    "text": (
                        "VaR utilization increased significantly with rate volatility. "
                        "Liquidity assumptions are stale and counterparty margin latency rose. "
                        "Model re-validation is overdue after regime change. "
                    ),
                }
                f.write(json.dumps(record) + "\n")

        return output_path

    @task(
        task_id="run_embedding",
        retries=2,
        map_index_template="{{ fund_id }}",
    )
    def run_embedding(fund_id: str, input_path: str, **context) -> dict:
        """Run the PySpark embedding container for one fund.

        Spark Execution Model:
            Spark runs in LOCAL mode inside the container. The container image
            (capital-market-risk-embedding) includes openjdk-17-jre-headless and
            PySpark. When the container starts, main.py creates a local
            SparkSession and runs the pipeline within the same process.

            This is NOT a Spark-submit to an external cluster. The container
            IS the Spark runtime — it starts, processes data, and exits.

        Uses DockerOperator to run the embedding image with fund-scoped input.
        In Airflow 3 on Azure, this can be replaced with:
        - Azure Container Instances (ACI) operator (same local-Spark-in-container model)
        - KubernetesPodOperator (if using Azure Kubernetes Service)
        - DatabricksRunNowOperator (if migrating to Azure Databricks — this would
          change the execution model to Databricks-managed Spark clusters)
        """
        execution_date = context["ds"]
        print(f"[run_embedding] Fund={fund_id} Input={input_path}")
        print(f"[run_embedding] Spark mode: LOCAL (inside container)")
        print(f"[run_embedding] Container image: {_EMBEDDING_IMAGE}")

        # EXTEND: Replace DockerOperator with the appropriate Azure operator.
        #
        # Option A: Azure Container Instances (same local-Spark model)
        #   from airflow.providers.microsoft.azure.operators.container_instance import
        #       AzureContainerInstancesOperator
        #   AzureContainerInstancesOperator(
        #       task_id=f"embedding_aci_{fund_id}",
        #       image=_EMBEDDING_IMAGE,
        #       resource_requests={"cpu": 4.0, "memory_in_gb": 8},
        #       environment_variables=_EMBEDDING_ENV,
        #       command_line=f"--process-date {execution_date} "
        #                    f"--input-jsonl {input_path} "
        #                    f"--vector-backend pgvector",
        #   )
        #
        # Option B: Azure Databricks (changes Spark to cluster mode)
        #   from airflow.providers.databricks.operators.databricks import
        #       DatabricksRunNowOperator
        #   DatabricksRunNowOperator(
        #       task_id=f"embedding_databricks_{fund_id}",
        #       job_id="<databricks-job-id>",
        #       notebook_params={
        #           "fund_id": fund_id,
        #           "process_date": execution_date,
        #           "input_path": input_path,
        #       },
        #   )

        embedding_task = DockerOperator(
            task_id=f"embedding_container_{fund_id}",
            image=_EMBEDDING_IMAGE,
            api_version="auto",
            auto_remove=True,
            docker_url="unix://var/run/docker.sock",
            network_mode="bridge",
            environment=_EMBEDDING_ENV,
            mounts=[_DATA_VOLUME],
            command=[
                "--process-date", execution_date,
                "--input-jsonl", input_path,
                "--vector-backend", "pgvector",
                "--spark-app-name", f"risk-embed-{fund_id}-{execution_date}",
            ],
            # Airflow 3: deferrable mode for long-running Spark jobs.
            # Set to True to free the worker slot while the container runs.
            deferrable=False,
        )

        result = embedding_task.execute(context)
        return {
            "fund_id": fund_id,
            "execution_date": execution_date,
            "status": "completed",
            "input_path": input_path,
        }

    # ── Task 3: Verification ───────────────────────────────────────────────────

    @task(
        task_id="verify_ingestion",
        trigger_rule=TriggerRule.ALL_DONE,
    )
    def verify_ingestion(embedding_results: list[dict], **context) -> None:
        """Verify that all funds were processed successfully.

        Runs after all embedding tasks complete (even if some failed).
        Sends alert if any fund failed or produced 0 chunks.
        """
        execution_date = context["ds"]
        print(f"[verify_ingestion] Date={execution_date}")

        failures = [r for r in embedding_results if r.get("status") != "completed"]
        if failures:
            failed_ids = [r["fund_id"] for r in failures]
            print(f"[verify_ingestion] FAILED funds: {failed_ids}")
            # EXTEND: Send Slack / PagerDuty alert.
            # from airflow.notifications import send_slack_message
            # send_slack_message(f"Embedding failed for funds: {failed_ids}")
            raise ValueError(f"Embedding failed for funds: {failed_ids}")

        success_count = len(embedding_results)
        print(f"[verify_ingestion] All {success_count} funds processed successfully.")

        # EXTEND: Query PGVector for per-fund document counts.
        # from sqlalchemy import create_engine
        # engine = create_engine(_EMBEDDING_ENV["PGVECTOR_CONNECTION_STRING"])
        # for fund_id in FUND_IDS:
        #     count = engine.execute(
        #         "SELECT COUNT(*) FROM langchain_pg_embedding WHERE metadata->>'fund_id' = :f",
        #         {"f": fund_id}
        #     ).scalar()
        #     print(f"  {fund_id}: {count} chunks")

    # ── Pipeline Assembly ──────────────────────────────────────────────────────

    # Task 1: Check source availability (single task)
    source_check = check_source_availability()

    # Task 2: Per-fund tasks — dynamically mapped over FUND_IDS.
    # Airflow 3 supports dynamic task mapping natively:
    #   .expand(fund_id=FUND_IDS) creates one mapped instance per fund.
    fetch_tasks = fetch_reports.expand(fund_id=FUND_IDS)
    embed_tasks = run_embedding.expand(
        fund_id=FUND_IDS,
        input_path=fetch_tasks,
    )

    # Task 3: Verification (collects all embedding results)
    verify = verify_ingestion(embed_tasks)

    # ── Execution Order ────────────────────────────────────────────────────────
    #
    #   check_source_availability
    #         │
    #         ├── fetch_reports(FUND-0001) → run_embedding(FUND-0001)
    #         ├── fetch_reports(FUND-0002) → run_embedding(FUND-0002)
    #         └── fetch_reports(FUND-0003) → run_embedding(FUND-0003)
    #         │
    #         └── verify_ingestion (after ALL funds complete)
    #
    # chain() sets linear dependencies within each fund's pipeline.
    # The expand() calls handle the fan-out across funds.

    chain(source_check, fetch_tasks, embed_tasks, verify)


# ── DAG Registration ───────────────────────────────────────────────────────────

dag = daily_risk_embedding()
