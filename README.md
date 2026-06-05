# Capital Market Risk Review — XXX Capital Markets

## What this project does

End-to-end **two-pipeline** multi-agent LangGraph system for automated capital market risk document analysis with human oversight, designed to support many funds with documents ingested daily or hourly.

---

## Two-pipeline architecture

### Pipeline 1 — Ingestion (runs hourly / daily per fund)
```
START → ingest_node → embed_and_persist_node → END
```
- Loads raw risk report documents for a given `fund_id`
- Splits into overlapping chunks tagged with `fund_id` + `report_date` metadata
- Embeds and **persists** chunks to the vector store (incrementally — new reports are appended, not re-embedded)
- Fully isolated per fund: each fund's chunks are stored separately

### Pipeline 2 — Review (runs at query / review time per fund)
```
START → retrieve → analyze → compliance_agent → market_sensitivity_agent
      → escalation_agent → human_review (HITL pause) → finalize → END
```
- Retrieves top-k chunks **filtered strictly by `fund_id`** from the persistent store
- Fund A's documents never pollute Fund B's retrieval
- Runs the full 3-agent + HITL pipeline

---

## Project layout

```
src/capital_market_risk_review/
├── __init__.py           ← package marker
├── models.py             ← domain schemas (RiskFinding, ReviewState incl. fund_id)
├── ingest.py             ← ingest_node, embed_and_persist_node, retrieve_node
├── analyze.py            ← LLM risk analysis and findings extraction
├── compliance_agent.py   ← Regulatory Compliance Agent (Basel III/IV + XXX limits)
├── market_agent.py       ← Market Sensitivity Agent (VaR, CVA, RWA)
├── escalation_agent.py   ← Risk Escalation Agent (Slack / email / ServiceNow)
├── review.py             ← HITL pause, routing, and finalization
├── graph.py              ← build_ingestion_graph() + build_review_graph()
├── main.py               ← demo: batch ingestion of 3 funds + review for FUND-001
├── DESIGN.md             ← architecture and design documentation
└── README.md             ← module-level readme
```

---

## Quick start

```zsh
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# Edit .env and set OPENAI_API_KEY

# Run the demo (ingests 3 funds × 2 dates, then reviews FUND-001)
python -m src.capital_market_risk_review.main
```

---

## Graph flows

### Ingestion graph
```
START
  └── ingest              split docs, tag chunks with fund_id + report_date
       └── embed_and_persist   write chunks to persistent store (keyed by fund_id)
            └── END
```

### Review graph
```
START
  └── retrieve                load fund_id-filtered chunks from persistent store
       └── analyze            LLM draft summary + structured JSON findings
            └── compliance_agent        Basel III/IV breach check + XXX risk appetite
                 └── market_sensitivity_agent   VaR delta, CVA, RWA enrichment
                      └── escalation_agent      severity routing → Slack/email/ServiceNow
                           └── human_review     HITL interrupt (pause here)
                                └── finalize    apply approve / edit / reject
                                     └── END
```

---

## Key design: why ingestion and retrieval are separate

| Concern | Ingestion pipeline | Review pipeline |
|---|---|---|
| When it runs | Hourly / daily batch job | On demand at review time |
| Embedding cost | Paid once per document | Never — already embedded |
| fund_id isolation | Tag every chunk at ingest time | Filter at retrieval time |
| Supports many funds | Loop over funds in batch | Single fund per review |
| Vector store | Write (`add_documents`) | Read (`similarity_search + filter`) |

---

## Usage in code

### Pipeline 1 — Ingest a fund's daily report
```python
from src.capital_market_risk_review.graph import build_ingestion_graph

graph = build_ingestion_graph()
graph.invoke({
    "fund_id": "FUND-001",
    "report_date": "2026-06-05",
    "source_files": ["FUND-001_daily_risk_report.pdf"],
    "raw_docs": ["VaR limit utilization..."],
    ...
})
```

### Pipeline 2 — Review a fund at query time
```python
from src.capital_market_risk_review.graph import build_review_graph

graph = build_review_graph()
config = {"configurable": {"thread_id": "review-FUND-001-2026-06-05"}}

# Step 1: run until HITL pause
paused = graph.invoke({
    "fund_id": "FUND-001",        # ← scopes retrieval to this fund only
    "query": "Summarize material risk issues...",
    ...
}, config=config)

# Step 2: resume with human decision
final = graph.invoke({"human_decision": "approve"}, config=config)
```

---

## Agent overview

### 🔍 Regulatory Compliance Agent (`compliance_agent.py`)
| Tool | Purpose |
|---|---|
| `check_basel_threshold` | Check observed metric against Basel III/IV threshold (BCBS 352, 325, 238, SR 11-7) |
| `get_xxx_risk_appetite` | Retrieve XXX Capital Markets internal limits and warning thresholds |
| `generate_remediation_recommendation` | Produce structured remediation action with owner, SLA, and policy reference |

### 📊 Market Sensitivity Analysis Agent (`market_agent.py`)
| Tool | Purpose |
|---|---|
| `calculate_var_delta` | 99%/10-day VaR, DV01, SVaR, and IMA capital charge per asset class |
| `estimate_cva_exposure` | CVA via EPE × PD × LGD with market spread factor (BCBS 325) |
| `calculate_rwa_impact` | RWA and Pillar 1 capital requirements under Basel III SA (BCBS 424) |

### 🚨 Risk Escalation Agent (`escalation_agent.py`)
| Tool | Purpose |
|---|---|
| `classify_findings_by_severity` | Count and bucket findings; determine if escalation is required |
| `send_slack_notification` | Route to `#xxx-cm-critical-risk-alerts` / `#xxx-cm-risk-alerts` etc. |
| `send_email_notification` | Email designated risk officer by severity + category |
| `create_servicenow_ticket` | Open P1/P2 incident with assignment group and XXX policy reference |

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model for analysis and agents |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embeddings for ingestion and retrieval |

---

## Extension points summary

| File | What to extend |
|---|---|
| `models.py` | Add `user_id`, `confidence_score`, `escalation_level`, `report_date` range filter |
| `ingest.py` | Swap `_FUND_DOCUMENT_STORE` → pgvector; add `RecordManager` for dedup; add PDF/Word loaders |
| `analyze.py` | Swap gpt-4o-mini → gpt-4o; add Pydantic structured output; add self-critique |
| `compliance_agent.py` | Connect Bloomberg Regulatory feed; add OSFI B-2/B-10; add FRTB SBM |
| `market_agent.py` | Connect Bloomberg BLPAPI / Murex for live positions; add Greeks (DV01, CS01) |
| `escalation_agent.py` | Wire real Slack SDK / SMTP / ServiceNow REST API; add PagerDuty / JIRA |
| `review.py` | Add multi-tier approval chain; audit log to PostgreSQL; SLA timer |
| `graph.py` | Add parallel branches; critique node; PDF report node; LangSmith tracing |
| `main.py` | Add argparse for fund_id + file path; schedule with Airflow / cron |

---

## License

MIT (use freely for your projects).
