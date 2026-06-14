# Review Process Package

This package owns query-time review orchestration.

## Modules

- `api.py`: canonical FastAPI module for review endpoints.
- `analyze.py`: LLM summary + findings extraction node.
- `compliance_agent.py`: compliance agent implementation.
- `market_agent.py`: market sensitivity agent implementation.
- `escalation_agent.py`: escalation agent implementation.
- `graph.py`: assembles review LangGraph nodes.
- `retrieval.py`: `retrieve_node` using backends from `embedding_process`.
- `hitl.py`: human-review pause and finalization nodes.
- `models.py`: canonical `ReviewState`, `RiskFinding`, `empty_review_state`.
- `main.py`: local review demo runner that bootstraps sample docs into file backend.

## Runtime config

- `REVIEW_VECTOR_BACKEND`: `auto` (default), `file`, `pgvector`
- `REVIEW_FILE_BACKEND_PATH`: local JSONL path when backend is `file` or `auto`
- `REVIEW_TOP_K`: top-k retrieval size (default `8`)

`auto` mode uses the file-backed retrieval path. If the file does not exist, retrieval returns no hits and logs guidance to run `embedding_process` first.

## Notes

- Ingestion/embedding is not provided by this package at API runtime.
- Production ingestion should run through `capital_market_risk_review.embedding_process`.

## Run instructions

Use module execution as the default (recommended) to avoid Python package-context import issues.

```zsh
cd /Users/chengwang/PycharmProjects/langchain-rag-app
export OPENAI_API_KEY="<your_key>"
python -m capital_market_risk_review.review_process.main
```

If you run by file path, it should also work with the current bootstrap logic in `main.py`:

```zsh
cd /Users/chengwang/PycharmProjects/langchain-rag-app
export OPENAI_API_KEY="<your_key>"
python src/capital_market_risk_review/review_process/main.py
```

If retrieval returns no hits, run ingestion first to create persisted chunks:

```zsh
cd /Users/chengwang/PycharmProjects/langchain-rag-app
python -m capital_market_risk_review.embedding_process.main \
  --process-date 2026-06-14 \
  --vector-backend file \
  --file-backend-path .local_data/fund_chunks.jsonl \
  --shuffle-partitions 2
```

Then run review again.
