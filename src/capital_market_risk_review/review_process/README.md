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
