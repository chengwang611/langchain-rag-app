# Resume Project Experience Variants

## Version A — One-line Resume Bullet
Built a two-pipeline AI agent platform for capital markets risk review using LangGraph/LangChain, FastAPI, and PySpark, enabling scheduled fund-level document embedding and on-demand HITL risk analysis (compliance, VaR/CVA/RWA, escalation) with containerized deployment on Kubernetes/OpenShift/Azure.

## Version B — Interview-ready Project Experience
**AI Agent Platform for Capital Markets Risk Review**

Designed and implemented a production-oriented two-pipeline architecture that separates scheduled ingestion/embedding from continuous review serving. The embedding pipeline processes multi-fund risk reports on daily/hourly cadence, while the review API retrieves fund-scoped context and orchestrates specialized AI agents for risk summarization, compliance checks, market sensitivity analysis (VaR/CVA/RWA), escalation routing, and human-in-the-loop approval.

### Scope and Contributions
- Built fund-isolated retrieval (`fund_id`-scoped) to prevent cross-fund data leakage.
- Implemented resumable review threads with human decision checkpoints (`approve` / `edit` / `reject`).
- Added specialized agent behaviors for regulatory compliance, market sensitivity, and escalation workflows.
- Structured deployment into two containerized workloads:
  - `review-api` for continuous service
  - `embedding-job` for scheduler-triggered batch processing

### Tech Stack
- Python, FastAPI, Pydantic
- LangGraph, LangChain, OpenAI APIs
- PySpark (batch ingestion/embedding)
- Vector backend abstraction (file backend phase 1, PGVector-ready)
- Docker (separate images), Kubernetes/OpenShift/Azure patterns
- Airflow/Databricks scheduler integration patterns

