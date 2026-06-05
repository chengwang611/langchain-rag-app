# Capital Market Risk Review — Design Document

## 1. Document Control
- **Owner:** XXX Capital Markets — Technology & Risk Engineering
- **Reviewers:** Market Risk, Counterparty Credit Risk, Model Risk, Regulatory Affairs
- **Version:** 2.0.0
- **Last Updated:** 2026-06-05
- **Status:** Implemented (agents active; external API integrations simulated)

---

## 2. Purpose and Scope

This document describes the design of the `capital_market_risk_review` LangGraph multi-agent pipeline, covering:
1. **Current implementation** — what is fully built and runnable today
2. **Production extension guide** — integration hooks and recommended next steps

### In Scope
- **Two-pipeline design**: separate ingestion (hourly/daily batch) from review (on-demand)
- Multi-fund support: each fund's documents are isolated by `fund_id` throughout
- Risk document ingestion, chunking, metadata tagging, and persistent embedding
- Fund-scoped semantic retrieval (`fund_id` filter at query time)
- LLM-driven draft summary and structured findings extraction
- Regulatory compliance checking (Basel III/IV, XXX internal limits)
- Quantitative market sensitivity enrichment (VaR, CVA, RWA)
- Automated severity-based escalation (Slack, email, ServiceNow)
- Human-in-the-Loop (HITL) review with full enriched context
- Resumable workflow with LangGraph checkpointing

### Out of Scope (current template — see §7 for roadmap)
- Persistent vector database (using module-level dict as demo store)
- Live Bloomberg / Murex / Calypso market data feeds
- Real Slack / SMTP / ServiceNow API integrations
- Enterprise authn/authz and RBAC
- Full audit database and regulatory record-keeping
- Production monitoring and LangSmith tracing

---

## 3. Architecture Overview

### 3.1 Two-Pipeline Design

The system is deliberately split into two independent LangGraph graphs:

```
┌─────────────────────────────────────────────────────────────┐
│  PIPELINE 1 — Ingestion  (hourly / daily batch per fund)    │
│                                                             │
│  for each fund, for each new risk report file:              │
│    START → ingest_node → embed_and_persist_node → END       │
│                                                             │
│  Output: chunks stored in vector DB, keyed by fund_id       │
└─────────────────────────────────────────────────────────────┘
                          │
                          │  persistent vector store
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PIPELINE 2 — Review  (on demand, per fund_id + query)      │
│                                                             │
│  retrieve (fund_id filter) → analyze → compliance_agent     │
│  → market_sensitivity_agent → escalation_agent              │
│  → human_review (HITL) → finalize → END                     │
│                                                             │
│  Output: final_summary, escalation_log, compliance_report   │
└─────────────────────────────────────────────────────────────┘
```

**Why separate?**
- Embedding is expensive — pay it once at ingest time, not on every query
- Ingestion runs continuously; reviews are event-driven
- Each pipeline can fail, retry, and scale independently
- fund_id isolation is enforced at both write-time (tag) and read-time (filter)

---

### 3.2 Folder and Modules

| Module | Responsibility |
|---|---|
| `models.py` | `RiskFinding` dataclass, `ReviewState` TypedDict (17 fields incl. `fund_id`, `report_date`, `source_files`) |
| `ingest.py` | `ingest_node`, `embed_and_persist_node`, `retrieve_node`, `_FUND_DOCUMENT_STORE` |
| `analyze.py` | LLM draft summary + structured JSON findings extraction via `gpt-4o-mini` |
| `compliance_agent.py` | **Regulatory Compliance Agent** — Basel III/IV + XXX risk appetite tools |
| `market_agent.py` | **Market Sensitivity Analysis Agent** — VaR delta, CVA exposure, RWA capital impact |
| `escalation_agent.py` | **Risk Escalation Agent** — severity classification, Slack/email/ServiceNow |
| `review.py` | HITL interrupt, decision routing, finalization |
| `graph.py` | `build_ingestion_graph()`, `build_review_graph()`, `build_graph()` (alias) |
| `main.py` | Demo: batch ingestion of 3 funds × 2 dates, then review for FUND-001 |

---

### 3.3 State Contract (`ReviewState`)

All 17 fields shared across both pipelines via `TypedDict`:

| Field | Type | Pipeline | Populated By |
|---|---|---|---|
| `fund_id` | `str` | Both | Caller — identifies which fund's docs to ingest/retrieve |
| `report_date` | `str \| None` | Ingestion | Caller — YYYY-MM-DD date of the risk report |
| `source_files` | `list[str]` | Ingestion | Caller — file paths or S3 keys |
| `messages` | `Annotated[list, add_messages]` | Both | All nodes |
| `raw_docs` | `list[str]` | Ingestion | Caller / file loaders |
| `query` | `str` | Review | Caller |
| `chunks` | `list` | Ingestion | `ingest_node` |
| `retrieved` | `list` | Review | `retrieve_node` |
| `draft_summary` | `str` | Review | `analyze_node` |
| `findings_json` | `str` | Review | `analyze_node` (JSON array) |
| `compliance_report` | `str \| None` | Review | `compliance_agent_node` |
| `market_sensitivity_report` | `str \| None` | Review | `market_sensitivity_agent_node` |
| `escalation_log` | `list[str]` | Review | `escalation_agent_node` |
| `escalation_required` | `bool` | Review | `escalation_agent_node` |
| `human_decision` | `"approve" \| "edit" \| "reject" \| None` | Review | Human via HITL |
| `edited_summary` | `str \| None` | Review | Human via HITL |
| `final_summary` | `str \| None` | Review | `finalize_node` |

---

### 3.4 fund_id Isolation — Write and Read

**At ingest time** — every chunk is tagged:
```python
Document(
    page_content=text,
    metadata={
        "source_id": f"{fund_id}_doc_{i}",
        "fund_id": fund_id,        # ← stored in chunk metadata
        "report_date": report_date,
        "source_file": source_files[i],
    }
)
```

**At retrieve time** — strict filter by fund_id:
```python
# Demo (module-level dict):
fund_chunks = _FUND_DOCUMENT_STORE.get(fund_id, [])   # only this fund's chunks
vector_store = InMemoryVectorStore.from_documents(fund_chunks, embeddings)

# Production (pgvector):
vector_store.similarity_search(query, k=8, filter={"fund_id": fund_id})
```

Fund A's documents are **never visible** when reviewing Fund B.

---

### 3.5 Persistent Store — Demo vs Production

| | Demo (current) | Production (EXTEND) |
|---|---|---|
| Store | `_FUND_DOCUMENT_STORE: dict[str, list[Document]]` | `PGVector` / `Chroma` / Azure AI Search |
| Persistence scope | Single process | Cross-process, durable |
| Deduplication | None (re-run appends) | `RecordManager` with `cleanup="incremental"` |
| fund_id filtering | Dict key lookup | `filter={"fund_id": fund_id}` on vector store |
| Index size control | No TTL | Report date TTL: purge chunks older than N days |

---

### 3.6 Ingestion Node Detail

```
ingest_node
  Input:  raw_docs (list[str]), fund_id, report_date, source_files
  Action: RecursiveCharacterTextSplitter (1200/200 overlap)
          Tag each chunk: fund_id, report_date, source_file, source_id
  Output: chunks (list[Document])

embed_and_persist_node
  Input:  chunks, fund_id
  Action: Append chunks to _FUND_DOCUMENT_STORE[fund_id]
          (EXTEND: PGVector.add_documents(chunks))
  Output: {} (side effect only — chunks persisted)
```

---

### 3.7 Review Node Detail

```
retrieve_node
  Input:  fund_id, query
  Action: Load fund_chunks = _FUND_DOCUMENT_STORE[fund_id]
          Build InMemoryVectorStore from fund_chunks only
          similarity_search(query, k=8)
          (EXTEND: PGVector filter={"fund_id": fund_id})
  Output: retrieved (list[Document])

analyze_node → compliance_agent_node → market_sensitivity_agent_node
           → escalation_agent_node → human_review_node → finalize_node
  (same as v1 — see §3.8–3.11)
```

---

### 3.8 Agent Design — Agentic Tool-Calling Loop

Each agent uses the same ReAct pattern:
```python
response = llm_with_tools.invoke(messages)
for _ in range(max_iterations):
    messages.append(response)
    if not response.tool_calls:
        break
    for tc in response.tool_calls:
        result = tool_executor[tc["name"]].invoke(tc["args"])
        messages.append(ToolMessage(result, tool_call_id=tc["id"]))
    response = llm_with_tools.invoke(messages)
```

---

### 3.9 Regulatory Compliance Agent Tools

| Tool | Regulation Ref | Key Logic |
|---|---|---|
| `check_basel_threshold` | BCBS 352 / 325 / 238 / SR 11-7 | Observed metric vs threshold dict → `BREACH/COMPLIANT` |
| `get_xxx_risk_appetite` | XXX CM Internal Policies v3–v5 | Returns internal limits + escalation owner |
| `generate_remediation_recommendation` | Above + OSFI | Owner, SLA, regulatory ref, escalation flag |

---

### 3.10 Market Sensitivity Agent Tools

| Tool | Regulation Ref | Key Logic |
|---|---|---|
| `calculate_var_delta` | BCBS 352 (IMA) | `VaR = position × daily_vol × z_score × √period`; capital = VaR × 3.0 |
| `estimate_cva_exposure` | BCBS 325 | `CVA = PD × LGD × EPE × market_factor`; capital = CVA × 1.5 |
| `calculate_rwa_impact` | BCBS 424 / CRR2 SA | `RWA = EAD × risk_weight`; Pillar 1 = 8%, CCB = 2.5% |

---

### 3.11 Escalation Agent Routing Matrix

| Severity | Slack | Email | ServiceNow | SLA |
|---|---|---|---|---|
| `critical` | `#xxx-cm-critical-risk-alerts` | Chief Risk Officer | P1 - Critical | Immediate |
| `high` | `#xxx-cm-risk-alerts` | Head of Risk (by category) | P2 - High | 3 business days |
| `medium` | `#xxx-cm-risk-monitoring` | — | — | 5 business days |
| `low` | `#xxx-cm-risk-log` | — | — | Log only |

---

## 4. Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Two separate graphs | `build_ingestion_graph` + `build_review_graph` | Decouples batch cadence from on-demand queries; independent scaling |
| fund_id tagging at ingest | Chunk metadata `fund_id` field | Enables vector store filter at retrieval — no cross-fund leakage |
| Module-level dict store | `_FUND_DOCUMENT_STORE` | Zero-infra demo; swap point is a single function call |
| Incremental append | `existing + chunks` per fund | Supports hourly runs accumulating historical context |
| Agent pattern | ReAct tool-calling loop | Deterministic tool selection; auditable reasoning chain |
| LLM | `gpt-4o-mini` | Cost-efficient for template; swap to `gpt-4o` for production |
| Checkpointing | `MemorySaver` | In-process HITL; `EXTEND` to `SqliteSaver/PostgresSaver` |

---

## 5. Known Gaps / Production Risks

| # | Gap | Impact | Mitigation |
|---|---|---|---|
| 1 | `_FUND_DOCUMENT_STORE` is in-process only | Data lost on restart | Replace with PGVector |
| 2 | No deduplication in `embed_and_persist_node` | Duplicate chunks on re-run | Add `RecordManager` with `cleanup="incremental"` |
| 3 | No TTL on stored chunks | Index grows unbounded | Add report_date TTL policy |
| 4 | Simulated Slack / email / ServiceNow | Notifications not delivered | Wire real API clients |
| 5 | Market data is static / simulated | VaR/CVA figures not live | Connect Bloomberg BLPAPI |
| 6 | No RBAC on HITL approval | Any caller can approve | Add reviewer identity + RBAC |
| 7 | Findings are LLM-generated JSON text | Schema may drift | Add `RiskFinding.model_validate_json()` |
| 8 | `MemorySaver` lost on restart | HITL checkpoint not durable | Replace with `PostgresSaver` |
| 9 | Basel thresholds hardcoded | Rules become stale | Connect Bloomberg Regulatory |

---

## 6. Production Extension Guide

### 6.1 Replace Demo Store with PGVector (`ingest.py`)
```python
from langchain_postgres.vectorstores import PGVector
import os

vector_store = PGVector(
    connection_string=os.environ["PGVECTOR_CONNECTION_STRING"],
    embedding_function=embeddings,
    collection_name="fund_risk_docs",
)

# embed_and_persist_node:
vector_store.add_documents(chunks)

# retrieve_node:
retrieved = vector_store.similarity_search(
    query, k=8, filter={"fund_id": fund_id}
)
```

### 6.2 Add Deduplication with RecordManager (`ingest.py`)
```python
from langchain.indexes import SQLRecordManager, index

record_manager = SQLRecordManager(
    f"pgvector/{fund_id}", db_url=os.environ["RECORD_MANAGER_DB_URL"]
)
index(chunks, record_manager, vector_store, cleanup="incremental")
```

### 6.3 Schedule Ingestion as Airflow DAG (`main.py`)
```python
# airflow_dag.py
from airflow.decorators import dag, task
@dag(schedule="0 * * * *")   # hourly
def fund_risk_ingestion():
    @task
    def ingest_fund(fund_id: str, report_date: str):
        graph = build_ingestion_graph()
        graph.invoke({...})
```

### 6.4 Real Slack / Email / ServiceNow (`escalation_agent.py`)
```python
# Slack
from slack_sdk import WebClient
WebClient(token=os.environ["SLACK_BOT_TOKEN"]).chat_postMessage(...)

# Email
import smtplib
with smtplib.SMTP_SSL("smtp.xxx.com", 465) as server: ...

# ServiceNow
import requests
requests.post(f"{SNOW_INSTANCE}/api/now/table/incident", json={...})
```

### 6.5 Durable Checkpointing (`graph.py`)
```python
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string(os.environ["POSTGRES_URL"])
graph = build_review_graph(checkpointer=checkpointer)
```

---

## 7. Production Roadmap

| Priority | Item | Owner |
|---|---|---|
| P0 | Replace `_FUND_DOCUMENT_STORE` with PGVector | Platform Engineering |
| P0 | Add `RecordManager` deduplication in `embed_and_persist_node` | Platform Engineering |
| P0 | Replace `MemorySaver` with `PostgresSaver` | Platform Engineering |
| P1 | Wire real Slack / email / ServiceNow in `escalation_agent.py` | Platform Engineering |
| P1 | Connect Bloomberg BLPAPI for live market data | Quant Risk Engineering |
| P1 | Add OSFI B-2 / B-10 rules to `compliance_agent.py` | Regulatory Affairs |
| P1 | Add Pydantic validation of `findings_json` | Risk Technology |
| P1 | Add reviewer identity + audit log in `finalize_node` | Risk Technology |
| P2 | Add report_date TTL policy in `embed_and_persist_node` | Platform Engineering |
| P2 | Add Airflow / cron scheduling for ingestion pipeline | Platform Engineering |
| P2 | Add LangSmith tracing for end-to-end observability | Platform Engineering |
| P3 | Add parallel graph branches for compliance + market agents | Risk Technology |
| P3 | Add PDF/Word report generation node after `finalize` | Risk Technology |

---

## 8. Testing Strategy

| Layer | What to test | How |
|---|---|---|
| Unit | `ingest_node` — chunk metadata tagging | Assert `fund_id` + `report_date` in every chunk's metadata |
| Unit | `embed_and_persist_node` — fund isolation | Assert `_FUND_DOCUMENT_STORE["FUND-A"]` does not contain FUND-B chunks |
| Unit | `retrieve_node` — fund_id filter | Ingest 2 funds, query each, assert no cross-fund documents returned |
| Unit | `embed_and_persist_node` — incremental append | Run twice, assert total chunk count doubles |
| Unit | Each tool function | pytest with known input/output pairs |
| Integration | Full ingestion pipeline | `build_ingestion_graph().invoke({...})` end-to-end |
| Integration | Full review pipeline with mocked LLM | `FakeListChatModel` |
| Agent | Compliance agent tool selection | Assert tools called for high/critical findings |
| HITL | Pause/resume correctness | Invoke twice with same `thread_id` |
| Escalation | Severity routing matrix | Assert correct channel/email/ServiceNow per severity |

---

## 9. Decision Log

| Date | Decision |
|---|---|
| 2026-06-05 | Initial template — RAG pipeline + HITL |
| 2026-06-05 | Added Regulatory Compliance, Market Sensitivity, Escalation agents |
| 2026-06-05 | Replaced all firm name references with anonymised placeholder (XXX) |
| 2026-06-05 | **Split into two separate pipelines** — ingestion (batch) vs review (on-demand) |
| 2026-06-05 | Added `fund_id` to chunk metadata at ingest time; filter at retrieve time |
| 2026-06-05 | Added `embed_and_persist_node` — separates embedding cost from retrieval |
| 2026-06-05 | Module-level `_FUND_DOCUMENT_STORE` as demo persistence with pgvector swap hooks |
| 2026-06-05 | Added `build_ingestion_graph()` to `graph.py`; `build_review_graph()` starts from `retrieve_node` |
