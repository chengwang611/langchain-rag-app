# Review Process Package

This package owns query-time review orchestration.

## Modules

- `api.py`: canonical FastAPI module for review and ingestion endpoints.
- `analyze.py`: LLM summary + findings extraction node.
- `compliance_agent.py`: compliance agent implementation.
- `market_agent.py`: market sensitivity agent implementation.
- `escalation_agent.py`: escalation agent implementation.
- `graph.py`: assembles review LangGraph nodes.
- `retrieval.py`: `retrieve_node` using backends from `embedding_process`.
- `hitl.py`: human-review pause and finalization nodes.

## Runtime config

- `REVIEW_VECTOR_BACKEND`: `auto` (default), `file`, `pgvector`
- `REVIEW_FILE_BACKEND_PATH`: local JSONL path when backend is `file` or `auto`
- `REVIEW_TOP_K`: top-k retrieval size (default `8`)

`auto` mode uses file-backed retrieval when the file exists; otherwise it falls back to legacy in-process retrieval for local demo compatibility.
