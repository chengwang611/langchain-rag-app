# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Despite the repo name `langchain-rag-app`, the actual project is **Capital Market Risk Review** — a two-pipeline, multi-agent LangGraph system (package `capital_market_risk_review`, under `src/`). It ingests fund risk reports, embeds them scoped by `fund_id`, then runs an on-demand review pipeline (retrieve → analyze → 3 agents → human-in-the-loop → finalize) exposed as a FastAPI service.

## Commands

Setup:
```zsh
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # dev extras: ruff, pytest, httpx
cp .env.example .env             # set OPENAI_API_KEY
```

Lint (ruff, line-length 100):
```zsh
ruff check src/
ruff format src/
```

Run the review API locally:
```zsh
uvicorn capital_market_risk_review.review_process.api:app --reload --port 8000
# Swagger UI at http://localhost:8000/docs
```

Local review demo (bootstraps sample docs into the file backend, then runs the review graph):
```zsh
python -m capital_market_risk_review.review_process.main   # or: risk-review-demo
```

Run the ingestion/embedding batch (Pipeline 1). `file` backend persists to JSONL that the review pipeline reads back:
```zsh
python -m capital_market_risk_review.embedding_process.main \
  --process-date 2026-06-05 --vector-backend file \
  --file-backend-path .local_data/fund_chunks.jsonl --shuffle-partitions 2
# or: embedding-process ...
```
Omit `--input-jsonl` and it generates synthetic demo data (FUND-0001..0010). Required source JSONL schema: `fund_id, document_id, report_date, source_file, text`.

Docker (two separate images by design):
```zsh
docker build -f docker/Dockerfile.review    -t capital-market-risk-review-api:latest .
docker build -f docker/Dockerfile.embedding -t capital-market-risk-embedding:latest .
```

## Architecture

Two **independent** LangGraph pipelines, deliberately decoupled so embedding cost is paid once at ingest and reviews are event-driven:

**Pipeline 1 — Ingestion** (`embedding_process/`, PySpark batch, runs hourly/daily per fund):
`START → ingest (chunk + tag) → embed_and_persist → END`. Every chunk is tagged with `fund_id` + `report_date` metadata at write time.

**Pipeline 2 — Review** (`review_process/`, on-demand per `fund_id` + query):
`retrieve → analyze → compliance_agent → market_sensitivity_agent → escalation_agent → human_review (HITL pause) → finalize`. Assembled in `review_process/graph.py::build_review_graph()`.

The two pipelines communicate **only** through the persisted vector store — there is no shared in-process state. `review_process/retrieval.py` reads back what `embedding_process` wrote.

### fund_id isolation (core invariant)
Multi-tenancy is enforced at both ends: chunks are tagged with `fund_id` at ingest, and `similarity_search(fund_id=..., query, k)` filters strictly by `fund_id` at retrieval. Fund A's documents must never appear when reviewing Fund B. Preserve this whenever touching ingestion metadata or retrieval.

### Vector backend abstraction
`embedding_process/vector_backend.py` defines the `VectorStoreBackend` Protocol (`add_documents`, `similarity_search`, `total_documents`) with three implementations:
- `InMemoryFundVectorStore` — uses real OpenAI embeddings; lost on exit; dev only.
- `FileFundVectorStore` — JSONL-backed persistence (`.local_data/fund_chunks.jsonl`). **Note:** its `similarity_search` is keyword token-overlap, NOT vector similarity — no embeddings at read time. This is the default local/demo path.
- `PGVectorFundStore` — production target, currently `NotImplementedError` placeholders.

Both `embedding_process/main.py` and `review_process/retrieval.py` select a backend via config. Review-side selection uses env var `REVIEW_VECTOR_BACKEND` (`auto`|`file`|`pgvector`), `REVIEW_FILE_BACKEND_PATH`, and `REVIEW_TOP_K`. Keep the backend contract stable so the review path never changes when the storage layer is swapped.

### State contract
`review_process/models.py` holds the canonical `ReviewState` (a `TypedDict`, ~17 fields spanning both pipelines) and `RiskFinding`. `messages` uses `Annotated[list, add_messages]`. Findings are currently LLM-generated JSON text (`findings_json`), not yet validated against `RiskFinding`.

### Agents
The three agents (`compliance_agent.py`, `market_agent.py`, `escalation_agent.py`) all follow the same manual ReAct tool-calling loop (`llm_with_tools.invoke` → execute `tool_calls` → append `ToolMessage` → repeat). Their tools (Basel threshold checks, VaR/CVA/RWA math, Slack/email/ServiceNow routing) are **simulated** — external integrations are stubbed hooks, not live.

### HITL & checkpointing
`hitl.py` provides `human_review_node`, `route_after_review` (approve/edit/reject), and `finalize_node`. The graph pauses at `human_review` via a LangGraph interrupt; resume by invoking again with `{"human_decision": ...}` on the same `thread_id`. Default checkpointer is `MemorySaver` (in-process, lost on restart) — `build_review_graph(checkpointer=...)` accepts a durable one (e.g. `PostgresSaver`).

### API
`review_process/api.py`: `GET /health`, `POST /review/start` (runs to HITL pause, returns `thread_id` + agent outputs), `POST /review/{thread_id}/resume`, `GET /review/{thread_id}/status`. Pydantic models validate input before it enters the graph.

## Config / env vars

`OPENAI_API_KEY` (required), `OPENAI_MODEL` (default `gpt-4o-mini`), `OPENAI_EMBEDDING_MODEL` (default `text-embedding-3-small`). Review retrieval: `REVIEW_VECTOR_BACKEND`, `REVIEW_FILE_BACKEND_PATH`, `REVIEW_TOP_K`. PGVector path (unimplemented): `PGVECTOR_CONNECTION_STRING`. Spark interpreter: `EMBEDDING_PROCESS_PYTHON_EXEC` / `PYSPARK_PYTHON`.

## Deployment

CI (`.github/workflows/deploy.yml`) triggers on push to `master`: builds both images via `az acr build` and deploys the review API to Azure Container Apps (deploy job gated on the `production` GitHub Environment). Embedding is meant to run as a scheduler-driven batch (Airflow/Databricks/OCP CronJob), not as part of the API deploy.

## Gotchas

- **Stale `pyproject.toml` console scripts:** `rag-ingest` / `rag-query` point at `rag_app.cli`, which does not exist. Working entrypoints are `risk-review-demo` and `embedding-process`.
- **No test suite yet** — `pytest` and `httpx` are installed as dev extras but there are no test files.
- Pins to note: `numpy<2` and `pyarrow<17` for Spark ABI compatibility; `pyspark>=3.5,<4` (Java 11).
- `DESIGN.md` is the authoritative deep-dive (state table, agent tool tables, production extension guide, deployment options A/B). `capital_market_review_design_deepseek.md` is a separate generated design doc.