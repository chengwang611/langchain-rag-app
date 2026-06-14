# Docker Images: Review API + Embedding Batch

This folder defines two separate images built from the same source code:

1. `docker/Dockerfile.review` -> continuous review API service
2. `docker/Dockerfile.embedding` -> scheduled embedding batch job

This separation matches production behavior:
- review API runs 24x7 behind Service/Ingress
- embedding job is triggered by scheduler (Airflow / Databricks / CronJob)

## Build

```zsh
cd /Users/chengwang/PycharmProjects/langchain-rag-app

docker build -f docker/Dockerfile.review -t capital-market-risk-review-api:latest .
docker build -f docker/Dockerfile.embedding -t capital-market-risk-embedding:latest .
```

## Run review API image

```zsh
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="<your_key>" \
  -e REVIEW_VECTOR_BACKEND=file \
  -e REVIEW_FILE_BACKEND_PATH=/data/fund_chunks.jsonl \
  -v /Users/chengwang/PycharmProjects/langchain-rag-app/.local_data:/data \
  capital-market-risk-review-api:latest
```

Verify:

```zsh
curl http://localhost:8000/health
```

## Run embedding batch image

```zsh
docker run --rm \
  -e OPENAI_API_KEY="<your_key>" \
  -v /Users/chengwang/PycharmProjects/langchain-rag-app/.local_data:/data \
  capital-market-risk-embedding:latest \
  --process-date 2026-06-14 \
  --vector-backend file \
  --file-backend-path /data/fund_chunks.jsonl \
  --shuffle-partitions 2
```

## Environment variables

### Review API image
- `OPENAI_API_KEY` (required)
- `PORT` (default `8000`)
- `REVIEW_VECTOR_BACKEND` (`file`, `pgvector`, `auto`)
- `REVIEW_FILE_BACKEND_PATH` (default `/data/fund_chunks.jsonl`)
- `PGVECTOR_CONNECTION_STRING` (required for `pgvector` backend)

### Embedding image
- `OPENAI_API_KEY` (required when embedding model/API is used)
- `PGVECTOR_CONNECTION_STRING` (required for `--vector-backend pgvector`)
- `SPARK_LOCAL_IP` (default `127.0.0.1`, useful for local Spark)

## Kubernetes / OCP / AKS mapping

- `capital-market-risk-review-api` -> `Deployment` + `Service` (+ ingress)
- `capital-market-risk-embedding` -> `CronJob` (or Airflow/Databricks triggered job)

Use the same mounted path or persistent backend between workloads so review retrieval can see the latest embedded chunks.

## Notes

- `Dockerfile.embedding` includes Java runtime for PySpark.
- `Dockerfile.review` is intentionally lighter and API-only.
- Both run as non-root user (`uid=10001`) for platform security compatibility.

