# RBC Capital Markets Experience Pack

This file is intentionally split for three direct uses:
1. `Part 1` -> copy/paste to your Word resume
2. `Part 2` -> copy/paste to your LinkedIn profile
3. `Part 3` -> private interview reference (detailed stories)

Core positioning across all parts:
- Track A: Senior Data Engineer/Architect (Spark ingestion and ETL)
- Track B: Senior AI Workflow Engineer (LLM, RAG, agents)
- Target platforms: Kubernetes/OpenShift (OCP), Azure, Azure Databricks
- Working style: hands-on ownership from design and analysis through implementation and production-oriented delivery

Use this together with `docs/DESIGN.md` and `src/capital_market_risk_review/experience.txt`.

---

## Part 1 - Word Resume Copy/Paste

**RBC Capital Markets (Contract) - Senior Data Engineer / AI Platform Architect (LLM, RAG, Agents)**  
*Python, PySpark, Scala Spark, LangChain, LangGraph, OpenAI GPT-4o-mini, FastAPI, Airflow, Kubernetes/OpenShift (OCP), Azure, Azure Databricks, PostgreSQL/pgvector, Docker, S3/MinIO*

**AI Agent & LLM Development:** 8+ years designing, implementing, and deploying production data ingestion/ETL pipelines; 2+ years building LLM + RAG + multi-agent workflows for financial risk, compliance analysis, and operational decision support using LangChain, LangGraph, OpenAI GPT models, vector stores (pgvector, FAISS), and tool-calling agent patterns; hands-on execution with GitHub Copilot, Claude Code, and Codex for accelerated delivery.

Led two parallel senior tracks for a capital-markets risk platform. On the data engineering side, I architected Spark-first ingestion and ETL frameworks (PySpark with Scala Spark-compatible patterns) to process heterogeneous source feeds into data-lake/data-store-ready layers, including metadata normalization, unstructured transformation, and embedding persistence. On the AI side, I engineered an LLM/RAG + LangChain/LangGraph multi-agent workflow for fund-scoped risk analysis, compliance enrichment, quantitative impact evaluation, escalation routing, and human-in-the-loop approval. I designed production-oriented workload separation between scheduled embedding jobs and on-demand review APIs, with deployment targets across Kubernetes/OpenShift (OCP), Azure, and Azure Databricks for scalable and resilient operation.

I take end-to-end ownership across architecture design, technical analysis, implementation, and delivery. I also use AI coding tools (GitHub Copilot, Claude Code, and Codex) to accelerate iteration, improve engineering throughput, and keep quality controls human-governed.

- Architected Spark ETL pipelines that decouple batch ingestion from request-time serving for better cost, latency, and operational control.
- Built reusable PySpark ETL patterns portable to Scala Spark delivery models for enterprise data engineering teams.
- Designed heterogeneous onboarding contracts (file, S3-compatible object storage, enterprise extract patterns) with strict fund-level metadata controls.
- Implemented LLM + RAG review workflow grounded on fund-scoped retrieval to improve output relevance and traceability.
- Engineered LangGraph multi-agent orchestration with typed `ReviewState` state contracts and resumable FastAPI execution.
- Mapped production target runtime across Kubernetes/OpenShift (OCP), Azure services, and Azure Databricks workflows.
- Drove design-to-delivery execution hands-on, using Copilot, Claude Code, and Codex to speed implementation while maintaining architecture and review discipline.

---

## Part 2 - LinkedIn Copy/Paste

At RBC Capital Markets (contract), I delivered two parallel senior capabilities in one platform: enterprise Spark data engineering and LLM/RAG agent workflow engineering.

**AI Agent Development Skills:** LangChain, LangGraph, OpenAI GPT-4o/GPT-4, retrieval-augmented generation (RAG), vector stores (PostgreSQL/pgvector, FAISS), semantic search, multi-agent orchestration, tool-calling patterns, human-in-the-loop workflows, FastAPI service deployment, LLM fine-tuning, prompt engineering, and production LLM debugging using Copilot, Claude Code, and Codex.

On the data side, I built Spark-first ingestion and ETL frameworks (PySpark with Scala Spark-compatible patterns) to onboard heterogeneous risk-document sources, normalize metadata, and publish retrieval-ready outputs to vector/data-store layers. On the AI side, I implemented an LLM + RAG + LangChain/LangGraph multi-agent workflow that generates grounded risk findings with compliance checks, market-sensitivity enrichment, escalation logic, and human-in-the-loop decision controls.

I led the full lifecycle hands-on: design, analysis, implementation, and production-oriented delivery. I also defined production deployment targets across Kubernetes/OpenShift (OCP), Azure, and Azure Databricks, with clear separation between scheduled embedding jobs and on-demand API-driven review workflows. This project demonstrates dual senior ownership in both Spark data engineering architecture and AI workflow platform design for regulated capital-markets environments.

To improve delivery speed and engineering efficiency, I actively used GitHub Copilot, Claude Code, and Codex for development acceleration while keeping architecture decisions, validation, and quality gates human-owned.

---

## Part 3 - Personal Interview Reference (Detailed)

## 1) 30-second pitch
"I delivered this platform through two parallel senior tracks: first, I built Spark-based ingestion and ETL frameworks for heterogeneous capital-markets documents into data-lake/data-store-ready layers; second, I built an LLM/RAG + LangGraph agent workflow for grounded risk analysis and analyst-guided decisions. The architecture decouples heavy ETL from low-latency review, enforces fund-level isolation, and supports production-style deployment across Airflow, Kubernetes/OpenShift (OCP), Azure, and Azure Databricks."

## 2) Architecture story (what to draw on whiteboard)
1. Ingestion path: source docs -> Spark chunking -> embedding -> vector persistence
2. Retrieval path: fund-scoped similarity search (`fund_id` filter)
3. Review path: analyze -> compliance -> market sensitivity -> escalation -> HITL -> finalize
4. API wrapper: start/resume/status endpoints with thread checkpointing
5. Deployment split: `review-api` (always-on) vs `embedding-job` (scheduled)

## 3) My ownership areas (say this explicitly)
- End-to-end architecture design and module boundaries.
- Spark ETL framework design (PySpark implementation with Scala Spark-compatible patterns) for heterogeneous ingestion, transformation, and embedding persistence.
- Data architecture for metadata normalization, isolation boundaries, and storage abstractions targeting lake/store evolution.
- LLM/RAG design for retrieval-grounded analysis and agent coordination over fund-scoped context.
- Multi-agent orchestration contracts (`ReviewState` shared typed state).
- API and deployment packaging strategy.
- Production hardening roadmap and risk decomposition.
- Hands-on execution from design analysis to implementation delivery using Copilot, Claude Code, and Codex to improve speed without reducing engineering rigor.

## 4) Interview talking points by theme

### Data engineering depth
- Why Spark for ingestion/embedding ETL: parallelism, scheduling fit, future scale, and portability across PySpark and Scala Spark delivery models.
- How to onboard heterogeneous sources: normalize metadata (`fund_id`, `report_date`, `source_file`) and keep contracts stable across file, object-store, and enterprise extract inputs.
- Idempotency controls: dedup strategy and retention/TTL policy for growing vector indexes.
- Why separate batch ingestion from request-time retrieval: cost, latency, operational isolation, and independent scaling of data and serving planes.

### AI workflow depth (LLM, RAG, agents)
- Why LangGraph over a single chain: explicit node boundaries and resumable control flow.
- Why RAG with LLMs: grounded responses, lower hallucination risk, and better traceability to retrieved fund documents.
- Why HITL matters in banking: approval gates, accountability, and auditability.
- How tool-calling agents improve explainability for compliance/market/escalation outputs.
- How to prevent cross-fund leakage: fund-scoped retrieval filters and metadata discipline.

### Platform and deployment depth
- Two images, two runtime modes: API service vs scheduled batch job.
- OpenShift/Kubernetes (OCP) + Airflow path vs Azure/Azure Databricks path: control/compliance vs delivery speed.
- Maturity gaps to close first: durable checkpoints, RBAC/SSO, immutable audit trail, live market data.

## 5) "Implemented" vs "Extension-ready" guardrail
Use this framing in interviews:
- **Implemented now:** two-pipeline architecture, PySpark embedding ETL, fund-scoped retrieval, multi-agent workflow, HITL, FastAPI layer, container split.
- **Designed next (roadmap):** full enterprise audit persistence, external API integrations (Slack/email/ServiceNow), multi-jurisdiction rules engine, Bloomberg live feeds, DR hardening.

## 6) Likely tough questions and short answers
- **Q: Why not embed during review request?**
  A: Embedding on request is expensive and adds latency. Pre-computing during scheduled ingestion reduces cost and improves response-time consistency.

- **Q: How do you avoid data leakage across funds?**
  A: Every chunk is tagged with `fund_id` on ingest and retrieval enforces `fund_id` filter at query time.

- **Q: What would you productionize first?**
  A: Durable checkpoint store, vector dedup + TTL, RBAC/SSO, immutable audit log, and real external integration clients.

- **Q: Where is your data engineering value beyond AI orchestration?**
  A: The PySpark ETL layer, source normalization strategy, storage abstraction, scheduling/deployment patterns, and operational controls are core data-platform work.

## 7) Final positioning statement
"This project demonstrates senior ownership across data engineering and LLM/RAG + AI agent architecture: from ingestion ETL and storage contracts to retrieval-grounded LLM orchestration and deployment strategy, with clear production hardening paths for regulated banking environments."
