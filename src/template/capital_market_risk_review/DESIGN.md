# Capital Market Risk Review — Design Document

## 1. Document Control
- **Owner:** XXX Capital Markets — Technology & Risk Engineering
- **Reviewers:** Market Risk, Counterparty Credit Risk, Model Risk, Regulatory Affairs
- **Version:** 1.0.0
- **Last Updated:** 2026-06-05
- **Status:** Implemented (agents active; external API integrations simulated)

---

## 2. Purpose and Scope

This document describes the design of the `capital_market_risk_review` LangGraph multi-agent pipeline, covering:
1. **Current implementation** — what is fully built and runnable today
2. **Production extension guide** — integration hooks and recommended next steps

### In Scope
- Risk document ingestion, chunking, and semantic retrieval
- LLM-driven draft summary and structured findings extraction
- Regulatory compliance checking (Basel III/IV, XXX internal limits)
- Quantitative market sensitivity enrichment (VaR, CVA, RWA)
- Automated severity-based escalation (Slack, email, ServiceNow)
- Human-in-the-Loop (HITL) review with full enriched context
- Resumable workflow with LangGraph checkpointing

### Out of Scope (current template — see §7 for roadmap)
- Persistent vector database
- Live Bloomberg / Murex / Calypso market data feeds
- Real Slack / SMTP / ServiceNow API integrations
- Enterprise authn/authz and RBAC
- Full audit database and regulatory record-keeping
- Production monitoring and LangSmith tracing

---

## 3. Current Implementation (As-Is)

### 3.1 Folder and Modules

| Module | Responsibility |
|---|---|
| `models.py` | Domain schemas: `RiskFinding`, `ReviewState` (all state fields) |
| `ingest.py` | Document loading, RecursiveCharacterTextSplitter, InMemoryVectorStore |
| `analyze.py` | LLM draft summary + structured JSON findings extraction via `gpt-4o-mini` |
| `compliance_agent.py` | **Regulatory Compliance Agent** — Basel III/IV threshold checks + XXX risk appetite + remediation recommendations |
| `market_agent.py` | **Market Sensitivity Analysis Agent** — VaR delta, CVA exposure, RWA capital impact |
| `escalation_agent.py` | **Risk Escalation Agent** — severity classification, Slack/email/ServiceNow notifications |
| `review.py` | HITL interrupt, decision routing (`approve/edit/reject`), finalization |
| `graph.py` | LangGraph `StateGraph` assembly and `MemorySaver` checkpointing |
| `main.py` | Demo runner: full invoke → display agent outputs → HITL resume |

---

### 3.2 State Contract (`ReviewState`)

All state fields shared across all nodes via `TypedDict`:

| Field | Type | Populated By |
|---|---|---|
| `messages` | `Annotated[list, add_messages]` | All nodes (conversation history) |
| `raw_docs` | `list[str]` | Caller / `main.py` |
| `query` | `str` | Caller / `main.py` |
| `chunks` | `list` | `ingest_node` |
| `retrieved` | `list` | `retrieve_node` |
| `draft_summary` | `str` | `analyze_node` |
| `findings_json` | `str` | `analyze_node` (JSON array) |
| `compliance_report` | `str \| None` | `compliance_agent_node` |
| `market_sensitivity_report` | `str \| None` | `market_sensitivity_agent_node` |
| `escalation_log` | `list[str]` | `escalation_agent_node` |
| `escalation_required` | `bool` | `escalation_agent_node` |
| `human_decision` | `"approve" \| "edit" \| "reject" \| None` | Human via HITL resume |
| `edited_summary` | `str \| None` | Human via HITL resume |
| `final_summary` | `str \| None` | `finalize_node` |

---

### 3.3 Runtime Graph Flow

```
START
  └── ingest                    RecursiveCharacterTextSplitter (1200 / 200 overlap)
       └── retrieve             InMemoryVectorStore similarity search (top-8)
            └── analyze         gpt-4o-mini → draft_summary + findings_json
                 └── compliance_agent
                 │    Tools: check_basel_threshold, get_xxx_risk_appetite,
                 │            generate_remediation_recommendation
                 │    Output: compliance_report
                      └── market_sensitivity_agent
                      │    Tools: calculate_var_delta, estimate_cva_exposure,
                      │            calculate_rwa_impact
                      │    Output: market_sensitivity_report
                           └── escalation_agent
                           │    Tools: classify_findings_by_severity,
                           │            send_slack_notification,
                           │            send_email_notification,
                           │            create_servicenow_ticket
                           │    Output: escalation_log, escalation_required
                                └── human_review   ← interrupt() — graph pauses here
                                     ├── [approve] → finalize → END
                                     ├── [edit]    → finalize → END
                                     └── [reject]  → finalize → END
```

---

### 3.4 Agent Design — Agentic Tool-Calling Loop

Each of the three agents follows the same ReAct-style pattern:

```python
response = llm_with_tools.invoke(messages)      # first call
for _ in range(max_iterations):
    messages.append(response)
    if not response.tool_calls:
        break                                    # LLM produced final text answer
    for tc in response.tool_calls:
        result = tool_executor[tc["name"]].invoke(tc["args"])
        messages.append(ToolMessage(result, tool_call_id=tc["id"]))
    response = llm_with_tools.invoke(messages)  # next reasoning step
```

The LLM autonomously decides which tools to call and in what order based on the findings context.

---

### 3.5 Regulatory Compliance Agent Tools

| Tool | Regulation Ref | Key Logic |
|---|---|---|
| `check_basel_threshold` | BCBS 352 / 325 / 238 / SR 11-7 | Compares observed metric to threshold dict; returns `BREACH/COMPLIANT` |
| `get_xxx_risk_appetite` | XXX CM Internal Policies v3–v5 | Returns internal warning/breach limits + escalation owner |
| `generate_remediation_recommendation` | Above + OSFI guidelines | Generates owner, SLA, regulatory ref, escalation flag per finding |

---

### 3.6 Market Sensitivity Agent Tools

| Tool | Regulation Ref | Key Logic |
|---|---|---|
| `calculate_var_delta` | BCBS 352 (IMA) | `VaR = position × daily_vol × z_score × √holding_period`; capital = VaR × 3.0 |
| `estimate_cva_exposure` | BCBS 325 | `CVA = PD × LGD × EPE × market_factor`; capital = CVA × 1.5 |
| `calculate_rwa_impact` | BCBS 424 / CRR2 (SA) | `RWA = EAD × risk_weight`; Pillar 1 = RWA × 8%, CCB = RWA × 2.5% |

---

### 3.7 Escalation Agent — Routing Matrix

| Severity | Slack | Email | ServiceNow | Priority |
|---|---|---|---|---|
| `critical` | `#xxx-cm-critical-risk-alerts` | Chief Risk Officer | P1 - Critical | Immediate |
| `high` | `#xxx-cm-risk-alerts` | Head of Risk (by category) | P2 - High | 3 business days |
| `medium` | `#xxx-cm-risk-monitoring` | — | — | 5 business days |
| `low` | `#xxx-cm-risk-log` | — | — | Log only |

---

### 3.8 HITL Pause/Resume

The graph uses checkpointing and a stable `thread_id`:
- **First invoke** runs all nodes (ingest → … → escalation_agent) then pauses at `human_review`
- **Second invoke** (same `thread_id`) resumes with:
  - `{ "human_decision": "approve" }` — draft summary becomes final
  - `{ "human_decision": "edit", "edited_summary": "..." }` — edited version becomes final
  - `{ "human_decision": "reject" }` — rejection notice published, no summary released

---

## 4. Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Graph engine | LangGraph `StateGraph` | Native interrupt/resume, typed state, checkpointing |
| Agent pattern | Tool-calling loop (ReAct-style) | Deterministic tool selection; auditable reasoning chain |
| LLM | `gpt-4o-mini` | Cost-efficient for template; swap to `gpt-4o` for production |
| Embeddings | `OpenAIEmbeddings` (`text-embedding-3-small`) | High quality, fast; swappable |
| Vector store | `InMemoryVectorStore` | Zero-infra for demo; `EXTEND` hooks for pgvector/Chroma |
| Checkpointing | `MemorySaver` | In-process for demo; `EXTEND` to `SqliteSaver/PostgresSaver` |
| Agent ordering | Sequential (compliance → market → escalation) | Each agent enriches context for the next |
| Notifications | Simulated (print + structured JSON) | Production hooks documented inline per tool |

---

## 5. Known Gaps / Production Risks

| # | Gap | Impact | Mitigation |
|---|---|---|---|
| 1 | In-memory vector store — not durable | Data lost between restarts | Replace with pgvector / Chroma |
| 2 | Simulated Slack / email / ServiceNow | Notifications not delivered | Wire real API clients (see §6) |
| 3 | Market data is static / simulated | VaR/CVA figures not live | Connect Bloomberg BLPAPI / Murex |
| 4 | No authentication on HITL approval | Any caller can approve | Add RBAC + reviewer identity capture |
| 5 | Findings are LLM-generated JSON text | Schema may drift | Add Pydantic `model_validate_json()` |
| 6 | No audit trail database | Non-compliant for regulated usage | Write decisions to PostgreSQL |
| 7 | `MemorySaver` lost on process restart | Checkpoints not durable | Replace with `SqliteSaver/PostgresSaver` |
| 8 | Basel thresholds are hardcoded | Rules become stale | Connect to Bloomberg Regulatory / BCBS portal |

---

## 6. Production Extension Guide

### 6.1 Real Slack Integration (`escalation_agent.py`)
```python
from slack_sdk import WebClient
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
client.chat_postMessage(channel=channel, text=message)
```

### 6.2 Real Email Integration (`escalation_agent.py`)
```python
import smtplib
with smtplib.SMTP_SSL("smtp.xxx.com", 465) as server:
    server.login(user, password)
    server.sendmail(sender, recipient, msg.as_string())
```

### 6.3 Real ServiceNow Integration (`escalation_agent.py`)
```python
import requests
resp = requests.post(
    f"{os.environ['SNOW_INSTANCE']}/api/now/table/incident",
    json={"short_description": ..., "priority": ..., "assignment_group": ...},
    auth=(os.environ["SNOW_USER"], os.environ["SNOW_PASSWORD"]),
)
ticket_id = resp.json()["result"]["number"]
```

### 6.4 Real Bloomberg Market Data (`market_agent.py`)
```python
import blpapi
# Replace SIMULATED_MARKET_DATA with live field requests:
# LAST_PRICE on USSW10 Curncy, CDX IG Curncy, VIX Index, etc.
```

### 6.5 Durable Checkpointing (`graph.py`)
```python
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
graph = build_graph(checkpointer=checkpointer)
```

### 6.6 Pydantic Findings Validation (`analyze.py`)
```python
findings = [RiskFinding.model_validate(f) for f in json.loads(findings_json)]
```

### 6.7 Audit Trail (`review.py` → `finalize_node`)
```python
# After finalize decision, write to PostgreSQL:
cursor.execute(
    "INSERT INTO audit_log (thread_id, decision, reviewer_id, timestamp) VALUES (%s,%s,%s,%s)",
    (thread_id, decision, reviewer_id, datetime.utcnow()),
)
```

---

## 7. Production Roadmap

| Priority | Item | Owner |
|---|---|---|
| P0 | Wire real Slack / email / ServiceNow in `escalation_agent.py` | Platform Engineering |
| P0 | Replace `MemorySaver` with `PostgresSaver` for durable checkpoints | Platform Engineering |
| P1 | Connect Bloomberg BLPAPI for live market data in `market_agent.py` | Quant Risk Engineering |
| P1 | Add OSFI B-2 / B-10 rules to `compliance_agent.py` | Regulatory Affairs |
| P1 | Add Pydantic validation of `findings_json` after `analyze_node` | Risk Technology |
| P1 | Add reviewer identity + audit log in `finalize_node` | Risk Technology |
| P2 | Replace InMemoryVectorStore with pgvector / Azure AI Search | Platform Engineering |
| P2 | Add parallel graph branches for compliance + market agents | Risk Technology |
| P2 | Add LangSmith tracing for end-to-end observability | Platform Engineering |
| P3 | Add critique node (LLM self-review before HITL) | Risk Technology |
| P3 | Add PDF/Word report generation node after `finalize` | Risk Technology |

---

## 8. Testing Strategy

| Layer | What to test | How |
|---|---|---|
| Unit | Each tool function (`check_basel_threshold`, `calculate_var_delta`, etc.) | pytest with known input/output pairs |
| Unit | Node functions (`ingest_node`, `analyze_node`, `finalize_node`) | pytest with mocked LLM responses |
| Integration | Full pipeline with mocked OpenAI | LangChain `FakeListChatModel` |
| Agent | Compliance agent tool selection | Assert tool calls made for high/critical findings |
| HITL | Pause/resume correctness | Invoke twice with same `thread_id`; assert state continuity |
| Escalation | Severity routing matrix | Assert Slack/email/ServiceNow called for correct severities |
| Failure | Invalid JSON findings, missing human decision, empty docs | Assert graceful degradation |

---

## 9. Decision Log

| Date | Decision |
|---|---|
| 2026-06-05 | Initial template — RAG pipeline + HITL documented |
| 2026-06-05 | Added Regulatory Compliance Agent (`compliance_agent.py`) with Basel III/IV + XXX risk appetite tools |
| 2026-06-05 | Added Market Sensitivity Analysis Agent (`market_agent.py`) with VaR / CVA / RWA tools |
| 2026-06-05 | Added Risk Escalation Agent (`escalation_agent.py`) with Slack / email / ServiceNow routing |
| 2026-06-05 | Sequential agent ordering chosen: compliance → market → escalation (each enriches the next) |
| 2026-06-05 | External API integrations simulated with inline production hooks for all three agents |
