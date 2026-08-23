# Resume Package — Capital Market Risk Review Project

> For: UBC CS Bachelor (2027 grad) | Target: AI Application/Agent Engineer
> Location: USA West Coast | US Citizen (no visa sponsorship needed)

---

## 1. Resume Experience Entry (Copy-Paste Ready)

### Option A — Concise (1 bullet per capability)

```
**Capital Market Risk Review System — AI Agent Engineer**
*Bank Client Internship | 2026 | Python, LangGraph, LangChain, PySpark, FastAPI, Azure*

- Architected a two-pipeline multi-agent LangGraph system for a capital markets bank:
  a PySpark batch ingestion pipeline (chunking + embedding + persistence) decoupled from
  an on-demand review pipeline (retrieval → 3 AI agents → human-in-the-loop approval),
  enabling independent scaling and fund-level data isolation
- Built 3 specialized AI agents with 10 LangChain tools: Regulatory Compliance (Basel III/IV
  threshold checks), Market Sensitivity (VaR/CVA/RWA quantitative enrichment), and Risk
  Escalation (severity-based Slack/email/ServiceNow routing)
- Implemented fund-scoped RAG retrieval with PGVector metadata filtering, ensuring Fund A's
  documents never pollute Fund B's results; designed a pluggable VectorStoreBackend protocol
  (InMemory/File/PGVector) for seamless production migration
- Implemented Human-in-the-Loop (HITL) approval using LangGraph checkpointing (thread_id),
  enabling analysts to approve/edit/reject AI findings before finalization
- Deployed as a FastAPI REST service (5 endpoints) containerized via multi-stage Docker and
  deployed to Azure Container Apps with GitHub Actions CI/CD (build → ACR → deploy)
- Designed a 17-field typed state contract (ReviewState TypedDict) enforcing clean interfaces
  across all pipeline stages
```

### Option B — Expanded (with metrics, for senior roles)

```
**Capital Market Risk Review System — AI Agent Engineer**
*Bank Client Internship | 2026 | Python, LangGraph, LangChain, PySpark, FastAPI, Azure*

- Architected a two-pipeline multi-agent LangGraph system (7-node review graph + batch
  ingestion graph) for a capital markets bank, decoupling expensive embedding from on-demand
  retrieval to support hourly/daily ingestion across multiple funds
- Built 3 specialized AI agents with 10 LangChain tools: Regulatory Compliance Agent
  (Basel III/IV threshold checks across 5 risk categories), Market Sensitivity Agent
  (99%/10-day VaR, CVA via EPE×PD×LGD, RWA under Standardised Approach), and Risk
  Escalation Agent (severity-based routing to Slack/email/ServiceNow)
- Implemented fund-scoped RAG retrieval with PGVector metadata filtering (fund_id isolation
  at both write-time and read-time), plus a pluggable VectorStoreBackend protocol supporting
  InMemory/File/PGVector backends for zero-friction production migration
- Implemented Human-in-the-Loop (HITL) approval using LangGraph interrupt + MemorySaver
  checkpointing, enabling analysts to approve/edit/reject AI findings before finalization
- Deployed as a FastAPI REST service (5 endpoints: ingest, start, resume, status, health)
  with Pydantic validation, containerized via multi-stage Docker (non-root, HEALTHCHECK),
  and deployed to Azure Container Apps with GitHub Actions CI/CD
- Designed a 17-field typed state contract (ReviewState TypedDict) enforcing clean interfaces
  across ingestion, retrieval, LLM analysis, agent enrichment, HITL, and finalization
```

---

## 1b. Data Engineer Experience Entry (Copy-Paste Ready)

### Option A — Concise

```
**Data Engineer Intern — Bank Client**
*2026 | PySpark, AWS (Glue/EMR/SageMaker), Azure Databricks, Airflow, S3, SQS, Lambda*

- Built event-driven ETL pipelines on AWS (S3 → SQS → Lambda → Glue/EMR) with
  exactly-once processing using S3 conditional put (IfNoneMatch='*') folder-level
  locks — no DynamoDB needed; added DLQ for failed messages and idempotency markers
- Implemented a medallion-architecture (Bronze→Silver→Gold) ingestion & ETL pipeline
  on Azure Databricks ingesting from Salesforce (Bulk API 2.0) and PMM (REST API),
  writing curated Delta tables managed by Unity Catalog; deployed via Databricks
  Asset Bundles (DAB) with CI/CD across dev/staging/prod
- Built an automated ML pipeline on AWS SageMaker (S3 event → SQS → Lambda → Pipeline)
  with preprocess/train/evaluate/register steps, XGBoost, and metric-gated model
  registration (PendingManualApproval)
- Developed an SMB-to-S3 file transfer utility preserving folder structure, and an
  Airflow DAG orchestrating daily customer/inventory report ETL with MSSQL integration
- Provisioned all infrastructure via CloudFormation and CDK with GitHub Actions CI/CD
```

### Option B — Expanded (with metrics)

```
**Data Engineer Intern — Bank Client**
*2026 | PySpark, AWS (Glue/EMR/SageMaker), Azure Databricks, Airflow, S3, SQS, Lambda*

- Designed event-driven ETL pipelines on AWS (S3 → SQS → Lambda → Glue/EMR) achieving
  exactly-once processing via S3 conditional put (IfNoneMatch='*') atomic folder-level
  locks, eliminating the need for DynamoDB; implemented DLQ retry and idempotency
  markers (_SUCCESS, _MANIFEST.json) for fault-tolerant batch processing
- Implemented a medallion-architecture (Bronze→Silver→Gold) pipeline on Azure Databricks
  ingesting from Salesforce (Bulk API 2.0) and PMM (REST API) with OAuth2 auth, writing
  curated Delta tables managed by Unity Catalog; deployed declaratively via Databricks
  Asset Bundles (DAB) with CI/CD promotion across dev/staging/prod environments
- Built an automated ML pipeline on AWS SageMaker (S3 event → SQS → Lambda → Pipeline)
  with preprocess/train/evaluate/register steps using XGBoost, and metric-gated model
  registration (accuracy ≥ 75% → PendingManualApproval) for MLOps governance
- Developed an SMB-to-S3 file transfer utility (chunked streaming, folder preservation)
  and an Airflow DAG orchestrating daily customer/inventory report ETL with MSSQL
  integration and dependency-based scheduling
- Provisioned all infrastructure as code via CloudFormation and AWS CDK with GitHub
  Actions CI/CD (OIDC) for repeatable, auditable deployments
```

---

## 2. Tech Stack Summary (Skills Section)

| Category | Technologies |
|---|---|
| **AI/LLM** | LangGraph, LangChain, OpenAI GPT-4o-mini, RAG, Multi-Agent Systems, Tool Calling, Human-in-the-Loop |
| **Data Engineering** | PySpark, Spark SQL, Delta Lake, Unity Catalog, Medallion Architecture, ETL/ELT, Parquet, CDC |
| **Cloud — AWS** | S3, SQS, Lambda, Glue, EMR, SageMaker, CloudFormation, CDK, Lake Formation, Athena, Redshift |
| **Cloud — Azure** | Databricks, ADLS Gen2, Azure Container Apps, Key Vault, CI/CD |
| **Orchestration** | Airflow, Databricks Workflows, Databricks Asset Bundles (DAB), GitHub Actions |
| **Data Sources** | Salesforce (Bulk API 2.0), PMM (REST API), SMB shares, MSSQL, CSV/JSON |
| **Backend** | Python, FastAPI, Pydantic, REST API, TypedDict |
| **DevOps** | Docker, GitHub Actions, CloudFormation, CDK, CI/CD |
| **Domain** | Basel III/IV, VaR, CVA, RWA, Capital Markets Risk, Regulatory Compliance |

---

## 3. Project Summary (for GitHub README / Portfolio)

```
# Capital Market Risk Review System

A production-grade multi-agent AI system for automating capital market risk document
review at a tier-1 bank. Built with LangGraph, LangChain, PySpark, and FastAPI.

## Architecture
- Two-pipeline design: batch ingestion (PySpark) decoupled from on-demand review
- 7-node LangGraph review pipeline: retrieve → analyze → compliance → market → escalate → HITL → finalize
- 3 specialized AI agents with 10 tools (Basel III/IV, VaR/CVA/RWA, Slack/email/ServiceNow)
- Fund-scoped RAG retrieval with PGVector metadata filtering
- Human-in-the-loop approval with LangGraph checkpointing

## Tech Stack
Python | LangGraph | LangChain | OpenAI | PySpark | PGVector | FastAPI | Docker | Azure

## Deployment
FastAPI REST service → Docker → Azure Container Apps → GitHub Actions CI/CD
```

---

## 4. Interview Talking Points

### The 2-Minute Story

> "I built a multi-agent AI system for a capital markets bank that automates risk document
> review. The challenge was that risk analysts were manually reviewing thousands of fund
> reports daily. I architected a two-pipeline LangGraph system: a PySpark batch pipeline
> ingests and embeds documents, and an on-demand review pipeline runs 3 specialized AI
> agents — a compliance agent checking Basel III/IV thresholds, a market sensitivity agent
> computing VaR/CVA/RWA, and an escalation agent routing critical findings. I added a
> human-in-the-loop approval step so analysts can review AI findings before they're
> finalized. I deployed it as a FastAPI service on Azure with CI/CD."

### Likely Interview Questions

| Question | Your Answer |
|---|---|
| "Why two pipelines?" | Decouple expensive embedding from on-demand retrieval; independent scaling; fund isolation |
| "How does HITL work?" | LangGraph interrupt + MemorySaver checkpointing; resume with thread_id |
| "How do you ensure fund isolation?" | fund_id tagged at write-time, filtered at read-time (PGVector metadata filter) |
| "Why LangGraph over LangChain?" | Stateful graph, checkpointing, conditional routing, multi-agent coordination |
| "How would you scale this?" | PGVector for production, Databricks for Spark, multi-region DR |

---

## 5. Job Hunting Strategy

### Target Companies (West Coast, AI Agent focus)

| Tier | Companies | Why |
|---|---|---|
| **Tier 1** | OpenAI, Anthropic, Google DeepMind, Meta AI | Agent engineering is core; LangGraph experience directly relevant |
| **Tier 2** | Databricks, Snowflake, Scale AI, Cohere, Mistral | Data + AI intersection matches your profile |
| **Tier 3** | Salesforce (Agentforce), ServiceNow, HubSpot | Enterprise AI agents; bank domain experience helps |
| **Fintech** | Stripe, Plaid, Robinhood, Coinbase | Financial domain + AI = your sweet spot |

### Your Key Advantages

1. **US Citizen** — No visa sponsorship needed. Lead with this for West Coast roles.
2. **Real bank client** — Not a school project. Interviewers take you seriously.
3. **Full-stack AI** — LLM orchestration + data engineering + cloud deployment. Most candidates have only one.
4. **Production-grade** — Docker, CI/CD, Azure deployment shows full lifecycle understanding.

### Application Timeline

```
Aug-Sep 2026:  Apply to 2027 new grad roles (OpenAI, Anthropic, Databricks, Snowflake)
Oct-Dec 2026:  Interview season (phone screens → onsites)
Jan-Mar 2027:  Offers + negotiation
Apr 2027:      Graduate, start summer 2027
```

### Interview Prep Focus

| Topic | Priority | Why |
|---|---|---|
| **LangGraph/LangChain** | High | Core differentiator; explain graph architecture |
| **System Design (AI)** | High | "Design a multi-agent system" is common |
| **RAG deep dive** | High | Chunking, embedding, retrieval, re-ranking |
| **Python + Data Structures** | Medium | Standard SWE rounds |
| **SQL + Spark** | Medium | Data engineering foundation |
| **Behavioral** | Medium | "Tell me about the bank project" — 2-min story |

---

## 6. What to Add Next (Round Out Your Profile)

Your profile is strong on **AI orchestration** but light on **production LLM evaluation**. Add one:

- **LLM evaluation harness** (RAGAS, LangSmith) — measure retrieval quality
- **Prompt engineering case study** — show you can optimize for accuracy
- **Fine-tuning project** — even a small LoRA fine-tune shows depth

This makes you a complete "AI Application Engineer" rather than just an "agent builder."
