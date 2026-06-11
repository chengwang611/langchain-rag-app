# Embedding Process (PySpark)

Separated batch pipeline for daily document ingestion + embedding.

## Why this package exists

The online review API should stay responsive. Large-scale ingestion (thousands of
fund IDs and high document volumes) is moved to a dedicated PySpark batch package.

## Package name note

Python package is `embedding_process` (underscore). A hyphenated name like
`embedding-process` is not valid for Python module imports.

## Input schema

Expected source fields:
- `fund_id` (string)
- `document_id` (string)
- `report_date` (string, YYYY-MM-DD)
- `source_file` (string)
- `text` (string)

## Run locally

```zsh
python -m capital_market_risk_review.embedding_process.main \
  --process-date 2026-06-10 \
  --vector-backend in-memory
```

Run with JSONL input:

```zsh
python -m capital_market_risk_review.embedding_process.main \
  --process-date 2026-06-10 \
  --input-jsonl /path/to/reports.jsonl \
  --vector-backend in-memory
```

Run with local file persistence backend:

```zsh
python -m capital_market_risk_review.embedding_process.main \
  --process-date 2026-06-10 \
  --vector-backend file \
  --file-backend-path .local_data/fund_chunks.jsonl
```

## Airflow usage idea

Use a `BashOperator` (phase 1):

```python
BashOperator(
    task_id="daily_embedding_process",
    bash_command=(
        "python -m capital_market_risk_review.embedding_process.main "
        "--process-date {{ ds }} "
        "--input-jsonl /data/risk_reports_{{ ds }}.jsonl "
        "--vector-backend in-memory"
    ),
)
```

## Phase 1 and migration path

- Phase 1 backends:
  - `InMemoryFundVectorStore` for fastest local loop.
  - `FileFundVectorStore` for local persistence across process restarts.
- Switch point: `vector_backend.py` -> `PGVectorFundStore` implementation.
- No Spark control-flow changes needed when switching backend.

## Next extensions

- Add dedup with deterministic `chunk_id` + RecordManager.
- Replace driver-side persistence with partition-level writes to PGVector.
- Add Delta table for run metrics and failures.
- Add report-date retention and fund-level backfill mode.

## Kubernetes note (important)

If this job runs in k8s, set one Python path that exists in both driver and executor images.
The entrypoint now aligns Spark driver and worker Python automatically, but explicit env is best in production.

Recommended pod env:

```zsh
export EMBEDDING_PROCESS_PYTHON_EXEC=/usr/bin/python3
```

Equivalent Spark submit configs (if you manage Spark outside this script):

```zsh
--conf spark.pyspark.python=/usr/bin/python3
--conf spark.pyspark.driver.python=/usr/bin/python3
--conf spark.executorEnv.PYSPARK_PYTHON=/usr/bin/python3
--conf spark.kubernetes.executorEnv.PYSPARK_PYTHON=/usr/bin/python3
```
