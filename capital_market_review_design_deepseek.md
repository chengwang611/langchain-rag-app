# Capital Market Risk Review — DeepSeek Design Analysis

> **Project:** `langchain-rag-app` — Capital Market Risk Review for XXX Capital Markets
> **Analysis Date:** 2026-06-27
> **Analyst:** DeepSeek (code review of full source tree)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Pipeline 1: Ingestion & Embedding](#3-pipeline-1-ingestion--embedding)
4. [Pipeline 2: Review & Multi-Agent Workflow](#4-pipeline-2-review--multi-agent-workflow)
5. [State Management & Data Flow](#5-state-management--data-flow)
6. [Agent Design Patterns](#6-agent-design-patterns)
7. [Vector Store Abstraction Layer](#7-vector-store-abstraction-layer)
8. [API Layer & Human-in-the-Loop](#8-api-layer--human-in-the-loop)
9. [Deployment & Infrastructure](#9-deployment--infrastructure)
10. [Design Strengths](#10-design-strengths)
11. [Design Weaknesses & Risks](#11-design-weaknesses--risks)
12. [Recommended Improvements](#12-recommended-improvements)
13. [Appendix: File Map](#13-appendix-file-map)

---

## 1. Executive Summary

This project implements an **end-to-end multi-agent LangGraph system** for automated capital market risk document analysis. It is designed for a tier-1 bank's capital markets division ("XXX Capital Markets") to process risk reports across many investment funds.

The system is split into **two independent pipelines**:

| Pipeline | Purpose | Trigger | Tech |
|---|---|---|---|
| **Ingestion** | Batch-process risk documents → chunk → embed → persist | Hourly/daily (Airflow) | PySpark, LangChain, OpenAI Embeddings |
| **Review** | On-demand risk analysis via multi-agent workflow | API call / manual trigger | LangGraph, FastAPI, OpenAI GPT-4o-mini |

The two-pipeline separation is the **central architectural decision**: embedding is expensive (OpenAI API cost), so it is paid once at ingest time rather than on every review query. Each pipeline can fail, retry, and scale independently.

---

## 2. System Architecture Overview

### 2.1 High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PIPELINE 1 — INGESTION (batch, hourly/daily)                          │
│                                                                         │
│  Risk Report Files (JSONL)                                              │
│       │                                                                 │
│       ▼                                                                 │
│  PySpark DataFrame                                                      │
│       │  Columns: fund_id, document_id, report_date, source_file, text  │
│       ▼                                                                 │
│  Sliding Window Chunking (1200 chars, 200 overlap)                      │
│       │                                                                 │
│       ▼                                                                 │
│  Metadata Tagging (fund_id, document_id, chunk_id, report_date, ...)    │
│       │                                                                 │
│       ▼                                                                 │
│  Vector Backend Persistence (File / InMemory / PGVector)                │
│       │                                                                 │
│       ▼                                                                 │
│  .local_data/fund_chunks.jsonl  ◄──── shared persistent store ──────┐  │
└─────────────────────────────────────────────────────────────────────│──┘
                                                                      │
┌─────────────────────────────────────────────────────────────────────│──┐
│  PIPELINE 2 — REVIEW (on-demand)                                    │  │
│                                                                      │  │
│  POST /review/start  { fund_id, query }                              │  │
│       │                                                              │  │
│       ▼                                                              │  │
│  retrieve_node ──── reads from ──────────────────────────────────────┘  │
│       │  similarity_search(fund_id, query, k=8)                        │
│       ▼                                                                │
│  analyze_node ──── LLM draft summary + structured JSON findings        │
│       │                                                                 │
│       ▼                                                                 │
│  compliance_agent_node ──── Basel III/IV checks + XXX risk appetite     │
│       │  Tool calls: check_basel_threshold, get_xxx_risk_appetite,      │
│       │               generate_remediation_recommendation               │
│       ▼                                                                 │
│  market_sensitivity_agent_node ──── VaR, CVA, RWA enrichment            │
│       │  Tool calls: calculate_var_delta, estimate_cva_exposure,        │
│       │               calculate_rwa_impact                              │
│       ▼                                                                 │
│  escalation_agent_node ──── severity routing + notifications            │
│       │  Tool calls: classify_findings_by_severity, send_slack,         │
│       │               send_email, create_servicenow_ticket              │
│       ▼                                                                 │
│  human_review_node ──── HITL pause (LangGraph interrupt)                │
│       │                                                                 │
│       ▼                                                                 │
│  finalize_node ──── apply approve / edit / reject                      │
│       │                                                                 │
│       ▼                                                                 │
│  final_summary produced                                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Module Layout

```
src/capital_market_risk_review/
├── __init__.py                          # Package marker
├── embedding_process/                   # Pipeline 1: Batch ingestion
│   ├── __init__.py
│   ├── main.py                          # CLI entrypoint with argparse
│   ├── spark_pipeline.py                # PySpark chunking + embedding orchestration
│   ├── vector_backend.py                # Vector store abstraction (3 backends)
│   └── README.md
├── review_process/                      # Pipeline 2: Review workflow
│   ├── __init__.py
│   ├── models.py                        # ReviewState TypedDict, RiskFinding dataclass
│   ├── graph.py                         # build_review_graph() LangGraph assembly
│   ├── retrieval.py                     # retrieve_node — fund-scoped vector search
│   ├── analyze.py                       # analyze_node — LLM summary + findings
│   ├── compliance_agent.py              # compliance_agent_node — regulatory checks
│   ├── market_agent.py                  # market_sensitivity_agent_node — VaR/CVA/RWA
│   ├── escalation_agent.py              # escalation_agent_node — notifications
│   ├── hitl.py                          # human_review_node + finalize_node
│   ├── api.py                           # FastAPI service (4 endpoints)
│   └── main.py                          # Local demo runner
```

---

## 3. Pipeline 1: Ingestion & Embedding

### 3.1 Entrypoint: [`embedding_process/main.py`](src/capital_market_risk_review/embedding_process/main.py)

The embedding pipeline is a **standalone CLI application** designed for Airflow/CRON triggering.

**CLI Arguments:**

| Argument | Default | Description |
|---|---|---|
| `--process-date` | today | Business date (YYYY-MM-DD) |
| `--input-jsonl` | None (uses synthetic data) | Path to JSONL source documents |
| `--vector-backend` | `in-memory` | One of: `in-memory`, `file`, `pgvector` |
| `--file-backend-path` | `.local_data/fund_chunks.jsonl` | JSONL path for file backend |
| `--chunk-size` | 1200 | Character window size |
| `--chunk-overlap` | 200 | Overlap between consecutive chunks |
| `--spark-app-name` | `risk-embedding-process` | Spark application name |
| `--shuffle-partitions` | 200 | Spark shuffle parallelism |

### 3.2 Data Loading ([`main.py`](src/capital_market_risk_review/embedding_process/main.py):92-128)

Two modes:
1. **Production mode** (`--input-jsonl`): Reads JSONL into a Spark DataFrame. Required columns: `fund_id`, `document_id`, `report_date`, `source_file`, `text`.
2. **Demo mode** (no `--input-jsonl`): Generates synthetic data — 10 funds (FUND-0001 to FUND-0010), each with 5 documents of placeholder risk text about VaR utilization, liquidity assumptions, and model re-validation.

### 3.3 Spark Session Configuration ([`main.py`](src/capital_market_risk_review/embedding_process/main.py):66-89)

The Spark session is configured with:
- Python interpreter alignment between driver and executors (critical for k8s)
- Adaptive query execution enabled
- Configurable shuffle partitions
- Kubernetes environment variables for pod-level Python path consistency

### 3.4 Chunking Logic ([`spark_pipeline.py`](src/capital_market_risk_review/embedding_process/spark_pipeline.py):32-52, 91-113)

The `SparkEmbeddingPipeline` class:

1. **Validates** input schema (requires 5 columns)
2. **Chunks** via a Spark UDF using a **sliding window** approach:
   - Window size: 1200 characters
   - Step size: 1000 characters (1200 - 200 overlap)
   - Produces overlapping chunks to preserve context at boundaries
3. **Explodes** the chunk array so each row becomes one chunk with `chunk_index`

**Design observation:** The chunking is character-based, not token-aware or sentence-aware. This is a known simplification noted in the code comments ("EXTEND: Replace with sentence-aware chunking").

### 3.5 Metadata Enrichment ([`spark_pipeline.py`](src/capital_market_risk_review/embedding_process/spark_pipeline.py):115-133)

Each chunk is wrapped as a LangChain `Document` with rich metadata:

```python
Document(
    page_content=row.chunk_text,
    metadata={
        "fund_id": row.fund_id,          # Fund isolation key
        "document_id": row.document_id,   # Source document identifier
        "report_date": row.report_date,   # Business date
        "source_file": row.source_file,   # Original file path
        "chunk_index": row.chunk_index,   # Position within document
        "chunk_id": f"{fund_id}:{document_id}:{chunk_index}",  # Unique ID
        "source_id": chunk_id,            # Alias for retrieval reference
    }
)
```

### 3.6 Persistence ([`spark_pipeline.py`](src/capital_market_risk_review/embedding_process/spark_pipeline.py):135-173)

Chunks are persisted in **batches of 1000** via `backend.add_documents()`. The pipeline collects rows from the Spark DataFrame using `toLocalIterator()` (driver-side materialization) and writes them in batches.

**Metrics returned:**
- `documents_read` — total source documents
- `chunks_created` — total chunks after splitting
- `funds_processed` — distinct fund IDs
- `chunks_persisted` — chunks written to backend
- `backend_total_documents` — total in backend after write

---

## 4. Pipeline 2: Review & Multi-Agent Workflow

### 4.1 LangGraph Assembly ([`graph.py`](src/capital_market_risk_review/review_process/graph.py))

The review graph is a **linear chain** of 7 nodes with one conditional branch:

```python
START → retrieve → analyze → compliance_agent → market_sensitivity_agent
     → escalation_agent → human_review ──→ finalize → END
                                      └──→ END (if no decision)
```

The graph uses `MemorySaver` as the checkpoint backend, enabling **resumable workflows** — the graph pauses at `human_review`, waits for external input, and resumes from the same point.

### 4.2 Node-by-Node Analysis

#### 4.2.1 `retrieve_node` ([`retrieval.py`](src/capital_market_risk_review/review_process/retrieval.py):60-78)

**Purpose:** Load fund-scoped chunks from the persistent vector store.

**Behavior:**
1. Reads `REVIEW_VECTOR_BACKEND` env var (default: `auto`)
2. Selects backend: `file` → `FileFundVectorStore`, `pgvector` → `PGVectorFundStore`, `auto` → file if JSONL exists
3. Calls `backend.similarity_search(fund_id, query, k=8)` — strict fund_id filter
4. Returns empty list if no hits (graceful degradation)

**Key design:** The retrieval is **fully decoupled** from the ingestion pipeline. It reads from the same persistent store (JSONL file or PGVector) that the embedding pipeline wrote to. This means the review pipeline never needs to know about Spark or batch processing.

#### 4.2.2 `analyze_node` ([`analyze.py`](src/capital_market_risk_review/review_process/analyze.py):38-70)

**Purpose:** Generate an executive summary and structured JSON findings from retrieved chunks.

**Behavior:**
1. Concatenates retrieved chunks with `[source_id]` labels
2. Sends to `gpt-4o-mini` with a system prompt instructing it to act as a senior capital-markets risk reviewer
3. Parses the response by splitting on `JSON:` delimiter
4. Returns `draft_summary` (text) and `findings_json` (JSON array string)

**System prompt rules:**
- Base all statements strictly on provided context — no hallucination
- If evidence is insufficient, state that explicitly
- Each finding must have: `category`, `severity`, `snippet`, `rationale`, `source_id`

**Design observation:** This is a **single LLM call** with no tool-calling loop. The analysis is purely generative — the LLM reasons over the retrieved context and produces structured output.

#### 4.2.3 `compliance_agent_node` ([`compliance_agent.py`](src/capital_market_risk_review/review_process/compliance_agent.py):194-222)

**Purpose:** Cross-reference findings against Basel III/IV regulatory thresholds and XXX internal risk appetite limits.

**Tool-calling loop** (max 12 iterations):
1. LLM receives findings JSON + compliance system prompt
2. LLM calls tools as needed:
   - `check_basel_threshold(category, metric, observed_value)` — checks against hardcoded Basel limits (e.g., VaR utilization > 85%, LCR < 100%)
   - `get_xxx_risk_appetite(category)` — retrieves internal risk appetite limits per category
   - `generate_remediation_recommendation(category, severity, breach_description)` — produces structured remediation with SLA, owner, and policy references
3. Tool results are fed back as `ToolMessage`
4. Loop continues until LLM stops calling tools or max iterations reached

**Basel thresholds defined:**
| Category | Key Metrics |
|---|---|
| Market | VaR utilization ≤ 85%, Stressed VaR multiplier ≤ 3.0, Backtesting breaches ≤ 4 |
| Liquidity | LCR ≥ 100%, NSFR ≥ 100%, Model staleness ≤ 6 months |
| Counterparty | CVA capital charge threshold $1M, Margin call SLA ≤ 1 day |
| Model | Revalidation ≤ 12 months, Backtesting breaches ≤ 4 |
| Regulatory | Reporting lag ≤ 5 days |

**XXX risk appetite defined:**
| Category | Warning | Breach | Owner |
|---|---|---|---|
| Market | VaR > 80% | VaR > 95% | Head of Market Risk |
| Liquidity | Buffer < 30 days | Buffer < 10 days | Chief Liquidity Officer |
| Counterparty | Margin latency > 2 days | Margin latency > 3 days | Head of CCR |
| Model | Age > 12 months | Regime change trigger | Model Risk Committee |

#### 4.2.4 `market_sensitivity_agent_node` ([`market_agent.py`](src/capital_market_risk_review/review_process/market_agent.py):210-239)

**Purpose:** Enrich findings with quantitative market sensitivity metrics.

**Tool-calling loop** (max 12 iterations):
1. LLM receives findings JSON + compliance context + market system prompt
2. LLM calls tools:
   - `calculate_var_delta(asset_class, position_size_usd, confidence_level, holding_period)` — computes VaR using parametric method (z-score × daily vol × position), Basel III capital charge (VaR × 3.0), and stressed VaR (VaR × 1.5)
   - `estimate_cva_exposure(counterparty_rating, product_type, notional_usd, maturity_years)` — computes CVA using PD × LGD × EPE with market factor adjustment
   - `calculate_rwa_impact(exposure_class, exposure_usd, risk_weight_pct)` — computes RWA using standardized approach risk weights, minimum capital (8%), Tier 1 (6%), CCB (2.5%)

**Simulated market data** provides context for rates, credit spreads, FX, equity, and commodity markets.

**Design observation:** All market data is **simulated** (hardcoded dicts). The tools perform calculations but do not connect to live Bloomberg/Murex/Calypso feeds.

#### 4.2.5 `escalation_agent_node` ([`escalation_agent.py`](src/capital_market_risk_review/review_process/escalation_agent.py):194-237)

**Purpose:** Classify findings by severity and route notifications through simulated channels.

**Tool-calling loop** (max 20 iterations):
1. LLM receives findings + compliance report + market report + escalation system prompt
2. LLM calls tools:
   - `classify_findings_by_severity(findings_json)` — parses findings, counts by severity tier, flags escalation needed if critical or high findings exist
   - `send_slack_notification(severity, category, message)` — routes to channel based on severity (`#xxx-cm-critical-risk-alerts`, `#xxx-cm-risk-alerts`, etc.)
   - `send_email_notification(severity, category, subject, body)` — sends to designated risk officer per severity × category
   - `create_servicenow_ticket(category, severity, short_description, detailed_description)` — creates incident with priority mapping

**Escalation protocol:**
| Severity | Slack | Email | ServiceNow |
|---|---|---|---|
| CRITICAL | ✅ | ✅ | ✅ |
| HIGH | ✅ | ❌ | ✅ |
| MEDIUM | ✅ | ❌ | ❌ |
| LOW | Log only | ❌ | ❌ |

**Design observation:** All notification channels are **simulated** — they print to stdout and return JSON records with `"status": "SENT (simulated — wire Slack SDK for production)"`. The escalation directory maps severity × category to named risk officers.

#### 4.2.6 `human_review_node` ([`hitl.py`](src/capital_market_risk_review/review_process/hitl.py):15-32)

**Purpose:** Pause graph execution and wait for human decision.

**Behavior:**
1. Checks if `human_decision` is already set in state
2. If not, calls `langgraph.types.interrupt()` with a payload containing the draft summary, findings JSON, and instructions
3. The graph **pauses** here — execution can be resumed later with a decision

**Resume options:**
- `approve` — accept draft summary as final
- `edit` — provide `edited_summary` to override draft
- `reject` — discard the review

#### 4.2.7 `finalize_node` ([`hitl.py`](src/capital_market_risk_review/review_process/hitl.py):43-54)

**Purpose:** Apply human decision and produce final summary.

| Decision | Final Summary |
|---|---|
| `approve` | `draft_summary` |
| `edit` | `edited_summary` (falls back to `draft_summary`) |
| `reject` | `"Review rejected by human approver. No summary published."` |

---

## 5. State Management & Data Flow

### 5.1 ReviewState TypedDict ([`models.py`](src/capital_market_risk_review/review_process/models.py):44-67)

All 17 fields of the shared state:

| # | Field | Type | Populated By | Used By |
|---|---|---|---|---|
| 1 | `fund_id` | `str` | Caller | All nodes |
| 2 | `report_date` | `Optional[str]` | Caller | Metadata |
| 3 | `source_files` | `list[str]` | Caller | Metadata |
| 4 | `messages` | `Annotated[list, add_messages]` | All nodes | LangGraph message passing |
| 5 | `raw_docs` | `list[str]` | Caller | (reserved) |
| 6 | `query` | `str` | Caller | `retrieve_node`, `analyze_node` |
| 7 | `chunks` | `list` | Ingestion | (reserved) |
| 8 | `retrieved` | `list` | `retrieve_node` | `analyze_node` |
| 9 | `draft_summary` | `str` | `analyze_node` | `human_review_node`, `finalize_node` |
| 10 | `findings_json` | `str` | `analyze_node` | All agent nodes |
| 11 | `compliance_report` | `Optional[str]` | `compliance_agent_node` | `market_sensitivity_agent_node`, `escalation_agent_node` |
| 12 | `market_sensitivity_report` | `Optional[str]` | `market_sensitivity_agent_node` | `escalation_agent_node` |
| 13 | `escalation_log` | `list[str]` | `escalation_agent_node` | Output |
| 14 | `escalation_required` | `bool` | `escalation_agent_node` | Output |
| 15 | `human_decision` | `Optional[Literal["approve","edit","reject"]]` | Human via HITL | `route_after_review`, `finalize_node` |
| 16 | `edited_summary` | `Optional[str]` | Human via HITL | `finalize_node` |
| 17 | `final_summary` | `Optional[str]` | `finalize_node` | Output |

### 5.2 Data Flow Through the Graph

```
Caller provides: fund_id, query
    │
    ▼
retrieve_node:  fund_id + query → retrieved chunks (list[Document])
    │
    ▼
analyze_node:   retrieved chunks → draft_summary (str) + findings_json (str)
    │
    ▼
compliance_agent_node:  findings_json → compliance_report (str)
    │
    ▼
market_sensitivity_agent_node:  findings_json + compliance_report → market_sensitivity_report (str)
    │
    ▼
escalation_agent_node:  findings_json + compliance_report + market_sensitivity_report
    → escalation_log (list[str]) + escalation_required (bool)
    │
    ▼
human_review_node:  draft_summary + findings_json + compliance_report + market_sensitivity_report
    → PAUSE → human_decision (str) + edited_summary (Optional[str])
    │
    ▼
finalize_node:  human_decision + draft_summary/edited_summary → final_summary (str)
```

### 5.3 RiskFinding Dataclass ([`models.py`](src/capital_market_risk_review/review_process/models.py):31-41)

```python
@dataclass
class RiskFinding:
    category: RiskCategory      # Market | Liquidity | Counterparty | Model | Operational | Regulatory | Other
    severity: Severity          # low | medium | high | critical
    snippet: str                # Exact quoted evidence from source
    rationale: str              # Reasoning for severity assessment
    source_id: str              # Reference back to source chunk
    page_number: Optional[int]  # Optional page reference
    tags: list[str]             # Optional classification tags
```

---

## 6. Agent Design Patterns

### 6.1 ReAct Tool-Calling Loop

All three agent nodes (compliance, market sensitivity, escalation) follow the same **ReAct (Reasoning + Acting)** pattern:

```python
response = llm_with_tools.invoke(messages)
for _ in range(max_iterations):
    messages.append(response)
    if not response.tool_calls:
        break
    for tc in response.tool_calls:
        result = tool_executor[tc["name"]].invoke(tc["args"])
        messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
    response = llm_with_tools.invoke(messages)
```

| Agent | Max Iterations | Tools |
|---|---|---|
| Compliance | 12 | `check_basel_threshold`, `get_xxx_risk_appetite`, `generate_remediation_recommendation` |
| Market Sensitivity | 12 | `calculate_var_delta`, `estimate_cva_exposure`, `calculate_rwa_impact` |
| Escalation | 20 | `classify_findings_by_severity`, `send_slack_notification`, `send_email_notification`, `create_servicenow_ticket` |

### 6.2 Tool Design

All tools are decorated with `@tool` from `langchain_core.tools` and return JSON strings. This is a deliberate choice — JSON output is structured enough for the LLM to parse and reason about, while keeping the tool interface simple.

**Tool categories:**

| Category | Tools | Data Source |
|---|---|---|
| Regulatory | `check_basel_threshold`, `get_xxx_risk_appetite`, `generate_remediation_recommendation` | Hardcoded dicts in code |
| Quantitative | `calculate_var_delta`, `estimate_cva_exposure`, `calculate_rwa_impact` | Parametric formulas + simulated market data |
| Notification | `classify_findings_by_severity`, `send_slack_notification`, `send_email_notification`, `create_servicenow_ticket` | Hardcoded directory + simulated delivery |

### 6.3 Agent System Prompts

Each agent has a detailed system prompt that:
1. **Defines the role** (e.g., "You are the Regulatory Compliance Agent for XXX Capital Markets")
2. **Specifies the protocol** (e.g., "Process ALL findings systematically. For each finding: call check_basel_threshold...")
3. **Defines the output format** (e.g., "Produce a structured compliance report with: COMPLIANCE STATUS, Per-finding breach flags...")

---

## 7. Vector Store Abstraction Layer

### 7.1 Protocol ([`vector_backend.py`](src/capital_market_risk_review/embedding_process/vector_backend.py):25-43)

```python
class VectorStoreBackend(Protocol):
    def add_documents(self, documents: Iterable[Document]) -> int: ...
    def similarity_search(self, fund_id: str, query: str, k: int = 8) -> List[Document]: ...
    def total_documents(self) -> int: ...
```

### 7.2 Implementations

#### `InMemoryFundVectorStore` ([`vector_backend.py`](src/capital_market_risk_review/embedding_process/vector_backend.py):47-82)

- **Storage:** Process-local dict `{fund_id: [Document, ...]}`
- **Search:** Builds ephemeral `InMemoryVectorStore` with `OpenAIEmbeddings` at query time
- **Persistence:** None — data lost on process exit
- **Use case:** Local development and testing

#### `FileFundVectorStore` ([`vector_backend.py`](src/capital_market_risk_review/embedding_process/vector_backend.py):116-203)

- **Storage:** JSONL file (default: `.local_data/fund_chunks.jsonl`)
- **Search:** **Token overlap scoring** (bag-of-words) — no embedding calls at query time
  - Tokenizes query and each document into lowercase alphanumeric tokens
  - Scores documents by sum of `min(query_count, doc_count)` for each token
  - Returns top-k by score
- **Persistence:** Append-only JSONL — survives process restarts
- **Use case:** Phase 1 production without external database dependency

#### `PGVectorFundStore` ([`vector_backend.py`](src/capital_market_risk_review/embedding_process/vector_backend.py):86-112)

- **Status:** Placeholder — all methods raise `NotImplementedError`
- **Target:** PostgreSQL with PGVector extension
- **Use case:** Production deployment with persistent, scalable vector storage

### 7.3 Backend Selection Logic

**Ingestion pipeline** ([`main.py`](src/capital_market_risk_review/embedding_process/main.py):131-147):
- `--vector-backend in-memory` → `InMemoryFundVectorStore`
- `--vector-backend file` → `FileFundVectorStore`
- `--vector-backend pgvector` → `PGVectorFundStore` (requires `PGVECTOR_CONNECTION_STRING`)

**Review pipeline** ([`retrieval.py`](src/capital_market_risk_review/review_process/retrieval.py):24-57):
- `REVIEW_VECTOR_BACKEND=auto` (default) → uses file backend if JSONL exists
- `REVIEW_VECTOR_BACKEND=file` → forces file backend
- `REVIEW_VECTOR_BACKEND=pgvector` → forces PGVector (requires `PGVECTOR_CONNECTION_STRING`)

---

## 8. API Layer & Human-in-the-Loop

### 8.1 FastAPI Endpoints ([`api.py`](src/capital_market_risk_review/review_process/api.py))

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/review/start` | Start a new review workflow |
| `POST` | `/review/{thread_id}/resume` | Resume a paused review with human decision |
| `GET` | `/review/{thread_id}/status` | Get current state of a review thread |

### 8.2 Review Start Flow

1. Client sends `POST /review/start` with `{ fund_id, query }`
2. Server generates a `thread_id` (e.g., `review-FUND-001-a1b2c3d4`)
3. Server invokes the LangGraph with `empty_review_state(fund_id)` + query
4. Graph runs through all 5 nodes (retrieve → analyze → compliance → market → escalation) until it hits `human_review_node`
5. Graph **pauses** — the interrupt is triggered
6. Server returns the accumulated state: draft summary, findings, compliance report, market report, escalation log

### 8.3 Review Resume Flow

1. Client sends `POST /review/{thread_id}/resume` with `{ human_decision, edited_summary? }`
2. Server invokes the graph again with the update
3. Graph resumes from `human_review_node`, routes to `finalize_node`
4. Server returns the final summary

### 8.4 Thread Management

- Threads are identified by `thread_id` and managed by LangGraph's `MemorySaver` checkpointer
- State is stored in-memory — lost on server restart
- The `GET /review/{thread_id}/status` endpoint allows polling for current state

---

## 9. Deployment & Infrastructure

### 9.1 Docker Images

**Review API** ([`docker/Dockerfile.review`](docker/Dockerfile.review)):
- Base: `python:3.11-slim`
- Installs: `ca-certificates`, `tini` (PID 1 signal handling)
- Runs: `uvicorn` serving the FastAPI app on port 8000
- Non-root user (`appuser`, UID 10001)
- Health check: HTTP GET `/health` every 30s
- Default backend: file-based at `/data/fund_chunks.jsonl`

**Embedding Process** ([`docker/Dockerfile.embedding`](docker/Dockerfile.embedding)):
- Base: `python:3.11-slim`
- Installs: `openjdk-17-jre-headless` (required by PySpark), `ca-certificates`, `tini`
- Runs: `python -m capital_market_risk_review.embedding_process.main`
- Default: file backend at `/data/fund_chunks.jsonl`

### 9.2 CI/CD ([`.github/workflows/deploy.yml`](.github/workflows/deploy.yml))

**Trigger:** Push to `master` branch or manual dispatch

**Job 1 — Build:**
1. Checkout source
2. Azure login (using service principal credentials)
3. Build and push review API image to Azure Container Registry
4. Build and push embedding job image to ACR

**Job 2 — Deploy:**
1. Requires manual approval (GitHub Environments `production`)
2. Updates Azure Container App with new review API image
3. Outputs the deployed URL and embedding image tag

### 9.3 Target Infrastructure

- **Cloud:** Azure
- **Compute:** Azure Container Apps (review API), ACR for image registry
- **Scheduling:** Airflow (referenced in comments) for embedding job triggering
- **Vector Store:** Phase 1 = file-based JSONL; Phase 2 target = PGVector on PostgreSQL

---

## 10. Design Strengths

### 10.1 Clean Separation of Concerns

The two-pipeline architecture (ingestion vs. review) is the strongest design decision. It correctly recognizes that:
- Embedding is expensive (OpenAI API calls) and should be done once
- Ingestion is a batch operation; review is event-driven
- Each pipeline has different scaling characteristics

### 10.2 Fund-Level Isolation

Every chunk is tagged with `fund_id` at ingest time, and retrieval strictly filters by `fund_id`. This is enforced at both write-time (metadata tagging) and read-time (backend filter). Fund A's documents are never visible when reviewing Fund B.

### 10.3 Backend Abstraction

The `VectorStoreBackend` protocol cleanly decouples the pipeline logic from the storage implementation. Swapping from in-memory → file → PGVector requires no changes to the Spark pipeline or review graph.

### 10.4 Resumable Workflows

LangGraph's checkpointing with `MemorySaver` enables the Human-in-the-Loop pattern. The graph pauses at `human_review_node` and can be resumed hours or days later with a decision.

### 10.5 Structured Agent Design

Each agent has:
- A clear, single responsibility
- A well-defined system prompt with protocol instructions
- A bounded set of tools
- A max iteration limit to prevent infinite loops

### 10.6 Graceful Degradation

- `retrieve_node` returns empty list if no chunks found (rather than crashing)
- `analyze_node` produces `"[]"` if JSON parsing fails
- `finalize_node` falls back to `draft_summary` if `edited_summary` is missing

---

## 11. Design Weaknesses & Risks

### 11.1 No Persistent Checkpointing

`MemorySaver` stores all thread state in process memory. A server restart loses all in-progress reviews. For production, this needs to be replaced with a persistent checkpointer (e.g., `PostgresSaver` or `SqliteSaver`).

### 11.2 Simulated External Integrations

All external systems are simulated:
- Market data feeds (hardcoded dicts)
- Slack notifications (print to stdout)
- Email notifications (print to stdout)
- ServiceNow tickets (generated fake IDs)

The code explicitly marks these as "simulated" with comments like "wire Slack SDK for production", but there is no integration test or adapter pattern to make the swap clean.

### 11.3 File Backend Search Quality

`FileFundVectorStore.similarity_search()` uses **bag-of-words token overlap** — not semantic search. This means:
- "VaR limit breach" and "Value at Risk threshold exceeded" would score 0 overlap despite being semantically identical
- Stop words and common financial terms dominate the scoring
- No embedding is computed at query time (by design), but the trade-off is poor retrieval quality

### 11.4 No Deduplication

The file backend is append-only. Running the embedding pipeline multiple times for the same fund on the same day will **duplicate chunks** in the JSONL file. There is no `chunk_id`-based deduplication or upsert logic.

### 11.5 No Token-Aware Chunking

The chunking is character-based (1200 chars, 200 overlap), not token-aware. This means:
- A single chunk may contain partial sentences at boundaries
- The LLM's context window is token-based, so character-based chunks don't align with the model's native units
- Multilingual documents (e.g., French regulatory text) would have different character-to-token ratios

### 11.6 Single LLM Provider

All LLM calls use `gpt-4o-mini` from OpenAI. There is no:
- Fallback provider (e.g., Azure OpenAI, Anthropic, local model)
- Model routing based on task complexity
- Cost optimization (e.g., cheaper model for simple classification, expensive model for complex reasoning)

### 11.7 No Authentication or Authorization

The FastAPI service has no auth middleware. Any client can start reviews, resume threads, or check status. For a bank's capital markets division, this is a significant security gap.

### 11.8 Limited Error Handling

- API endpoints catch broad `Exception` and return 500 — no structured error types
- Agent tool-calling loops have max iterations but no timeout or circuit breaker
- No retry logic for transient failures (e.g., OpenAI API rate limits)
- No logging framework — all output uses `print()` statements

### 11.9 No Testing Infrastructure

There are no unit tests, integration tests, or end-to-end tests in the codebase. The `pyproject.toml` lists `pytest` as a dev dependency, but no test files exist.

---

## 12. Recommended Improvements

### 12.1 Critical (Production-Blocking)

| Priority | Issue | Recommendation |
|---|---|---|
| P0 | No persistent checkpointing | Replace `MemorySaver` with `PostgresSaver` or `SqliteSaver` for durable thread state |
| P0 | No auth | Add API key or OAuth2 middleware to FastAPI |
| P0 | No deduplication | Add `chunk_id`-based deduplication in `FileFundVectorStore.add_documents()` |

### 12.2 High Priority

| Priority | Issue | Recommendation |
|---|---|---|
| P1 | File backend search quality | Replace bag-of-words with persistent vector index (e.g., Chroma, FAISS) or implement PGVector |
| P1 | Simulated integrations | Implement adapter pattern for Slack SDK, SMTP/SendGrid, ServiceNow REST API |
| P1 | No tests | Add pytest tests: unit tests for tools, integration tests for graph, API tests with TestClient |

### 12.3 Medium Priority

| Priority | Issue | Recommendation |
|---|---|---|
| P2 | Token-aware chunking | Replace `_chunk_text()` with `RecursiveCharacterTextSplitter` or token-based splitter |
| P2 | Structured logging | Replace `print()` with `structlog` or `loguru` |
| P2 | LLM provider abstraction | Add model routing with fallback support |
| P2 | Error types | Define custom exception hierarchy and FastAPI exception handlers |

### 12.4 Low Priority

| Priority | Issue | Recommendation |
|---|---|---|
| P3 | Sentence-aware chunking | Use `NLTK` or `spaCy` sentence splitter for cleaner semantic boundaries |
| P3 | Monitoring | Add LangSmith tracing, Prometheus metrics, and structured audit logging |
| P3 | CI/CD testing | Add test step to GitHub Actions workflow |
| P3 | Rate limiting | Add `tenacity` retry decorator to LLM calls |

### 12.5 Specific Code Improvements

**1. Make `FileFundVectorStore` search semantic:**
```python
# Instead of bag-of-words token overlap, build and persist a vector index
def similarity_search(self, fund_id: str, query: str, k: int = 8) -> List[Document]:
    self._ensure_loaded()
    docs = self._documents_by_fund.get(fund_id, [])
    if not docs:
        return []
    # Build ephemeral vector store at query time (same as InMemoryFundVectorStore)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    store = InMemoryVectorStore.from_documents(docs, embeddings)
    return store.similarity_search(query, k=k)
```

**2. Add deduplication to file backend:**
```python
def add_documents(self, documents: Iterable[Document]) -> int:
    self._ensure_loaded()
    existing_ids = {doc.metadata.get("chunk_id") for fund_docs in self._documents_by_fund.values() for doc in fund_docs}
    new_docs = [doc for doc in documents if doc.metadata.get("chunk_id") not in existing_ids]
    # ... persist only new_docs
```

**3. Replace `MemorySaver` with persistent checkpointer:**
```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(os.environ["PGVECTOR_CONNECTION_STRING"])
graph = build_review_graph(checkpointer=checkpointer)
```

**4. Add structured error handling to API:**
```python
from fastapi import Request
from fastapi.responses import JSONResponse

class ReviewError(Exception):
    def __init__(self, code: str, detail: str, status_code: int = 500):
        self.code = code
        self.detail = detail
        self.status_code = status_code

@app.exception_handler(ReviewError)
async def review_error_handler(request: Request, exc: ReviewError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "detail": exc.detail},
    )
```

---

## 13. Appendix: File Map

| File | Lines | Purpose |
|---|---|---|
| [`pyproject.toml`](pyproject.toml) | 56 | Project metadata, dependencies, CLI entry points |
| [`src/capital_market_risk_review/__init__.py`](src/capital_market_risk_review/__init__.py) | 9 | Package marker |
| [`src/capital_market_risk_review/embedding_process/__init__.py`](src/capital_market_risk_review/embedding_process/__init__.py) | - | Package marker |
| [`src/capital_market_risk_review/embedding_process/main.py`](src/capital_market_risk_review/embedding_process/main.py) | 215 | CLI entrypoint, Spark session builder, backend selector |
| [`src/capital_market_risk_review/embedding_process/spark_pipeline.py`](src/capital_market_risk_review/embedding_process/spark_pipeline.py) | 175 | PySpark chunking + embedding orchestration |
| [`src/capital_market_risk_review/embedding_process/vector_backend.py`](src/capital_market_risk_review/embedding_process/vector_backend.py) | 203 | Vector store abstraction (3 backends) |
| [`src/capital_market_risk_review/review_process/__init__.py`](src/capital_market_risk_review/review_process/__init__.py) | - | Package marker |
| [`src/capital_market_risk_review/review_process/models.py`](src/capital_market_risk_review/review_process/models.py) | 97 | ReviewState TypedDict, RiskFinding dataclass |
| [`src/capital_market_risk_review/review_process/graph.py`](src/capital_market_risk_review/review_process/graph.py) | 51 | LangGraph assembly |
| [`src/capital_market_risk_review/review_process/retrieval.py`](src/capital_market_risk_review/review_process/retrieval.py) | 79 | Fund-scoped vector retrieval |
| [`src/capital_market_risk_review/review_process/analyze.py`](src/capital_market_risk_review/review_process/analyze.py) | 71 | LLM summary + findings extraction |
| [`src/capital_market_risk_review/review_process/compliance_agent.py`](src/capital_market_risk_review/review_process/compliance_agent.py) | 223 | Regulatory compliance agent |
| [`src/capital_market_risk_review/review_process/market_agent.py`](src/capital_market_risk_review/review_process/market_agent.py) | 240 | Market sensitivity agent |
| [`src/capital_market_risk_review/review_process/escalation_agent.py`](src/capital_market_risk_review/review_process/escalation_agent.py) | 238 | Escalation agent |
| [`src/capital_market_risk_review/review_process/hitl.py`](src/capital_market_risk_review/review_process/hitl.py) | 55 | Human-in-the-loop + finalize |
| [`src/capital_market_risk_review/review_process/api.py`](src/capital_market_risk_review/review_process/api.py) | 148 | FastAPI service |
| [`src/capital_market_risk_review/review_process/main.py`](src/capital_market_risk_review/review_process/main.py) | 158 | Local demo runner |
| [`docker/Dockerfile.review`](docker/Dockerfile.review) | 39 | Review API container image |
| [`docker/Dockerfile.embedding`](docker/Dockerfile.embedding) | 32 | Embedding process container image |
| [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) | 89 | CI/CD to Azure Container Apps |