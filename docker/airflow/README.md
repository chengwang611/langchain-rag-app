# Airflow 3 DAG — Deployment Guide for Azure

> This document explains how to deploy and manage the `daily_risk_embedding` DAG
> on Azure using Airflow 3.

---

## Architecture Overview

```
                    ┌──────────────────────────────┐
                    │   Azure Container Registry    │
                    │   (acrcmrisk.azurecr.io)      │
                    └──────────┬───────────────────┘
                               │ docker pull
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  Airflow 3 (Azure Managed / Self-Hosted on ACA)                  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  DAG: daily_risk_embedding                               │    │
│  │                                                          │    │
│  │  check_source_availability                               │    │
│  │       │                                                  │    │
│  │       ├── fetch_reports(FUND-0001) → run_embedding(...)  │    │
│  │       ├── fetch_reports(FUND-0002) → run_embedding(...)  │    │
│  │       └── fetch_reports(FUND-0003) → run_embedding(...)  │    │
│  │       │                                                  │    │
│  │       └── verify_ingestion                               │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Scheduler runs at 06:00 UTC daily                               │
└──────────────────────────────────────────────────────────────────┘
```

---

## Option 1: Azure Managed Airflow (Azure Data Factory / MWAA)

Azure offers two managed Airflow options:

| Option | Description | Best For |
|---|---|---|
| **Azure Data Factory — Managed Airflow** | ADF includes an Airflow 3-compatible managed environment | Teams already using ADF |
| **Azure Native Managed Airflow** | First-party Airflow 3 service (preview) | Teams wanting pure Airflow |

### Deployment Steps

```bash
# 1. Install Airflow CLI (if using self-managed)
pip install apache-airflow==3.0.0

# 2. Copy the DAG to the Airflow DAGs folder
# For ADF Managed Airflow, this is typically an Azure Blob Storage container
az storage blob upload \
  --container-name airflow-dags \
  --name dags/daily_risk_embedding_dag.py \
  --file dags/daily_risk_embedding_dag.py \
  --account-name <your-storage-account>

# 3. Set required Airflow Variables and Connections
airflow variables set FUND_IDS '["FUND-0001", "FUND-0002", "FUND-0003"]'

airflow connections add 'postgres_pgvector' \
  --conn-type 'postgres' \
  --conn-host '<pgvector-host>.postgres.database.azure.com' \
  --conn-login 'risk_user' \
  --conn-password '<password>' \
  --conn-port 5432

airflow connections add 'azure_blob_risk_reports' \
  --conn-type 'azure_blob_storage' \
  --conn-login '<storage-account-name>' \
  --conn-password '<storage-account-key>'
```

---

## Option 2: Self-Hosted Airflow 3 on Azure Container Apps

For teams that want full control over Airflow configuration.

### Prerequisites

- Azure CLI installed (`az`)
- Docker installed
- Azure Container Registry (already configured in [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml))

### Step 1: Create Airflow Configuration

```yaml
# docker/airflow/docker-compose.airflow.yml
version: "3.9"

x-airflow-common: &airflow-common
  image: apache/airflow:3.0.0-python3.11
  environment: &airflow-common-env
    AIRFLOW__CORE__EXECUTOR: LocalExecutor
    AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg://airflow:airflow@postgres-airflow:5432/airflow
    AIRFLOW__CORE__FERNET_KEY: ""
    AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: "true"
    AIRFLOW__CORE__LOAD_EXAMPLES: "false"
    AIRFLOW__API__AUTH_BACKENDS: "airflow.api.auth.backend.basic_auth"
    AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL: "30"
    # Embedding process env vars
    OPENAI_API_KEY: ${OPENAI_API_KEY}
    PGVECTOR_CONNECTION_STRING: postgresql+psycopg://risk_user:risk_pass@postgres:5432/risk_review
    EMBEDDING_IMAGE: acrcmrisk.azurecr.io/capital-market-risk-embedding:latest
  volumes:
    - ../dags:/opt/airflow/dags
    - ../src:/opt/airflow/src
    - ../.local_data:/opt/airflow/data
    - /var/run/docker.sock:/var/run/docker.sock
  networks:
    - risk-review-network

services:
  postgres-airflow:
    image: postgres:16
    environment:
      POSTGRES_DB: airflow
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
    volumes:
      - airflow-pgdata:/var/lib/postgresql/data
    networks:
      - risk-review-network
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 5s
      retries: 5

  airflow-init:
    <<: *airflow-common
    entrypoint: /bin/bash
    command:
      - -c
      - |
        airflow db init
        airflow users create \
          --username admin \
          --firstname Admin \
          --lastname User \
          --role Admin \
          --email admin@example.com \
          --password admin
    restart: "no"

  airflow-scheduler:
    <<: *airflow-common
    command: scheduler
    restart: always
    depends_on:
      airflow-init:
        condition: service_completed_successfully

  airflow-webserver:
    <<: *airflow-common
    command: webserver
    ports:
      - "8080:8080"
    restart: always
    depends_on:
      airflow-init:
        condition: service_completed_successfully

networks:
  risk-review-network:
    external: true

volumes:
  airflow-pgdata:
```

### Step 2: Deploy to Azure Container Apps

```bash
# Build and push Airflow image with custom dependencies
cat > docker/airflow/Dockerfile.airflow << 'EOF'
FROM apache/airflow:3.0.0-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

USER airflow
RUN pip install --no-cache-dir \
    apache-airflow-providers-docker \
    apache-airflow-providers-microsoft-azure

COPY dags/ /opt/airflow/dags/
EOF

# Build and push
az acr build \
  --registry acrcmrisk \
  --file docker/airflow/Dockerfile.airflow \
  --image airflow-risk-review:latest \
  .

# Deploy Airflow scheduler as a Container App job
az containerapp job create \
  --name "airflow-scheduler" \
  --resource-group rg-risk-review \
  --environment env-risk-review \
  --image acrcmrisk.azurecr.io/airflow-risk-review:latest \
  --command "airflow" "scheduler" \
  --cpu "2.0" --memory "4Gi" \
  --registry-server acrcmrisk.azurecr.io \
  --env-vars \
    AIRFLOW__CORE__EXECUTOR=LocalExecutor \
    AIRFLOW__CORE__SQL_ALCHEMY_CONN="postgresql+psycopg://airflow:airflow@postgres-airflow:5432/airflow" \
    OPENAI_API_KEY="secretref:openai-api-key" \
    PGVECTOR_CONNECTION_STRING="secretref:pgvector-connection-string"

# Deploy Airflow webserver as a Container App
az containerapp create \
  --name "airflow-webserver" \
  --resource-group rg-risk-review \
  --environment env-risk-review \
  --image acrcmrisk.azurecr.io/airflow-risk-review:latest \
  --command "airflow" "webserver" \
  --cpu "1.0" --memory "2Gi" \
  --registry-server acrcmrisk.azurecr.io \
  --ingress external \
  --target-port 8080 \
  --env-vars \
    AIRFLOW__CORE__EXECUTOR=LocalExecutor \
    AIRFLOW__CORE__SQL_ALCHEMY_CONN="postgresql+psycopg://airflow:airflow@postgres-airflow:5432/airflow"
```

---

## Option 3: Azure Container Apps Jobs (Simplest)

If you don't need a full Airflow deployment, Azure Container Apps Jobs provide
a cron-based scheduler that directly runs the embedding container.

```bash
# Create a Container Apps Job that runs daily at 06:00 UTC
az containerapp job create \
  --name "daily-risk-embedding" \
  --resource-group rg-risk-review \
  --environment env-risk-review \
  --image acrcmrisk.azurecr.io/capital-market-risk-embedding:latest \
  --cpu "4.0" --memory "8Gi" \
  --registry-server acrcmrisk.azurecr.io \
  --cron-expression "0 6 * * *" \
  --env-vars \
    OPENAI_API_KEY="secretref:openai-api-key" \
    PGVECTOR_CONNECTION_STRING="secretref:pgvector-connection-string" \
  --command "python" "-m" "capital_market_risk_review.embedding_process.main" \
  --args "--process-date" "{{ $(date +%Y-%m-%d) }}" \
         "--input-jsonl" "/data/ingest/$(date +%Y-%m-%d).jsonl" \
         "--vector-backend" "pgvector"
```

---

## DAG Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key for embeddings |
| `PGVECTOR_CONNECTION_STRING` | Yes | — | PostgreSQL connection string for vector store |
| `EMBEDDING_IMAGE` | No | `acrcmrisk.azurecr.io/...` | Docker image for embedding process |
| `FUND_IDS` | No | `["FUND-0001","FUND-0002","FUND-0003"]` | JSON array of fund IDs to process |

### Airflow Variables (set via UI or CLI)

| Variable | Description |
|---|---|
| `FUND_IDS` | JSON list of active fund IDs |
| `slack_webhook_url` | Slack webhook for failure alerts |
| `alert_email_recipients` | Comma-separated email addresses for alerts |

### Connections (set via UI or CLI)

| Connection ID | Type | Purpose |
|---|---|---|
| `postgres_pgvector` | Postgres | PGVector database for verification queries |
| `azure_blob_risk_reports` | Azure Blob Storage | Source risk report files |

---

## Monitoring

### DAG Metrics to Watch

| Metric | Alert Threshold | Action |
|---|---|---|
| `dag_failure` | Any failure | Check Spark logs in Azure Monitor |
| `task_failure` | >2 consecutive | Investigate fund-specific data issues |
| `duration > 2h` | >2 hours | Scale Spark resources |
| `0 chunks ingested` | Any fund | Check source data availability |

### Logging

- Airflow task logs are available in the Airflow webserver UI
- Spark driver logs are streamed to stdout (captured by Airflow)
- For production: configure Azure Monitor to collect container logs

### Alerting

The DAG includes a `verify_ingestion` task that raises `ValueError` on failure.
Configure Airflow to send alerts via:

```bash
airflow variables set slack_webhook_url "https://hooks.slack.com/services/xxx/yyy/zzz"
airflow variables set alert_email_recipients "risk-engineering@xxx.com"
```

---

## EXTEND: Production Hardening

1. **Replace DockerOperator** with Azure-specific operators:
   - `AzureContainerInstancesOperator` for ACI
   - `KubernetesPodOperator` for AKS
   - `DatabricksRunNowOperator` for Azure Databricks

2. **Add deduplication** — Use `RecordManager` with `cleanup="incremental"`
   to avoid re-embedding unchanged documents.

3. **Add backfill support** — Add a `--backfill-days` parameter to reprocess
   historical data when regulatory rules change.

4. **Add data quality checks** — Validate source schema, detect anomalies
   in document volume, and alert on unexpected changes.

5. **Add run metrics** — Write ingestion run stats (chunk count, duration,
   fund_id) to a Delta table or Postgres for dashboards.
