# Capital Market Risk Review — XXX Capital Markets Template

## What this template does

End-to-end multi-agent LangGraph pipeline that:
1. Ingests raw capital market risk documents
2. Splits + embeds them into a vector store
3. Retrieves top-k most relevant chunks via semantic similarity search
4. Runs LLM analysis to produce a draft executive summary + structured JSON findings
5. **Regulatory Compliance Agent** — cross-references findings against Basel III/IV thresholds and XXX internal risk appetite limits, flags breaches, and generates remediation recommendations
6. **Market Sensitivity Analysis Agent** — enriches findings with quantitative metrics: VaR delta, CVA exposure, and RWA capital impact estimates
7. **Risk Escalation Agent** — classifies findings by severity, routes critical/high findings to designated senior risk officers via Slack, email, and ServiceNow
8. Pauses for Human-in-the-Loop (HITL) review with full enriched context
9. Resumes with human decision: `approve` / `edit` / `reject`
10. Produces a final approved summary

---

## File structure

```
src/template/capital_market_risk_review/
├── __init__.py           ← package marker
├── models.py             ← domain schemas (RiskFinding, ReviewState)
├── ingest.py             ← document loading, splitting, and chunking
├── analyze.py            ← LLM risk analysis and findings extraction
├── compliance_agent.py   ← Regulatory Compliance Agent (Basel III/IV + XXX limits)
├── market_agent.py       ← Market Sensitivity Agent (VaR, CVA, RWA)
├── escalation_agent.py   ← Risk Escalation Agent (Slack / email / ServiceNow)
├── review.py             ← HITL pause, routing, and finalization
├── graph.py              ← LangGraph pipeline assembly
├── main.py               ← entry point / demo runner
├── DESIGN.md             ← architecture and design documentation
└── README.md             ← this file
```

---

## Run locally

```zsh
# Set your API key
export OPENAI_API_KEY="your_key_here"

# Run the full pipeline
python -m src.template.capital_market_risk_review.main
```

---

## Graph flow

```
START
  └── ingest                   split documents into overlapping chunks
       └── retrieve            embed + similarity search top-k chunks
            └── analyze        LLM draft summary + structured JSON findings
                 └── compliance_agent        Basel III/IV breach check + XXX risk appetite
                      └── market_sensitivity_agent   VaR delta, CVA, RWA enrichment
                           └── escalation_agent      severity routing → Slack/email/ServiceNow
                                └── human_review     HITL interrupt (pause here)
                                     └── finalize    apply approve / edit / reject
                                          └── END
```

---

## Agent overview

### 🔍 Regulatory Compliance Agent (`compliance_agent.py`)
Uses three LangChain tools in an agentic loop:
| Tool | Purpose |
|---|---|
| `check_basel_threshold` | Check observed metric against Basel III/IV threshold (BCBS 352, 325, 238, 295, SR 11-7) |
| `get_xxx_risk_appetite` | Retrieve XXX Capital Markets internal limits and warning thresholds |
| `generate_remediation_recommendation` | Produce structured remediation action with owner, SLA, and policy reference |

### 📊 Market Sensitivity Analysis Agent (`market_agent.py`)
Uses three LangChain tools with Basel III capital charge calculations:
| Tool | Purpose |
|---|---|
| `calculate_var_delta` | 99% / 10-day VaR, DV01, SVaR, and IMA capital charge per asset class |
| `estimate_cva_exposure` | CVA exposure via EPE × PD × LGD with market spread factor (BCBS 325) |
| `calculate_rwa_impact` | RWA and Pillar 1 capital requirements under Basel III Standardised Approach |

### 🚨 Risk Escalation Agent (`escalation_agent.py`)
Uses four LangChain tools for automated notification routing:
| Tool | Purpose |
|---|---|
| `classify_findings_by_severity` | Count and bucket findings; determine if escalation is required |
| `send_slack_notification` | Route to `#xxx-cm-critical-risk-alerts` / `#xxx-cm-risk-alerts` etc. |
| `send_email_notification` | Email designated risk officer (Chief Market Risk Officer, Head of MRM, etc.) |
| `create_servicenow_ticket` | Open incident ticket with priority, assignment group, and XXX policy reference |

---

## HITL flow in code

```python
# Step 1: Run full pipeline until HITL interrupt (after all 3 agents)
paused_state = graph.invoke(initial_state, config=config)

# Outputs available before human reviews:
paused_state["draft_summary"]              # LLM draft
paused_state["findings_json"]              # structured risk findings
paused_state["compliance_report"]          # Basel III/IV breach report
paused_state["market_sensitivity_report"]  # VaR / CVA / RWA metrics
paused_state["escalation_log"]             # notification actions taken
paused_state["escalation_required"]        # True if critical/high findings

# Step 2: Resume with human decision (same thread_id)
final_state = graph.invoke(
    {"human_decision": "approve"},          # or "edit" / "reject"
    config=config,
)
```

---

## Extension points summary

| File | What to extend |
|---|---|
| `models.py` | Add risk categories, `user_id`, `confidence_score`, `escalation_level` |
| `ingest.py` | Swap InMemoryVectorStore → pgvector/Chroma, add PDF/Word/Excel loaders |
| `analyze.py` | Swap gpt-4o-mini → gpt-4o, add Pydantic structured output, self-critique node |
| `compliance_agent.py` | Connect to Bloomberg Regulatory feed, add OSFI B-2/B-10, FRTB SBM |
| `market_agent.py` | Connect to Bloomberg BLPAPI / Murex for live positions, add Greeks (DV01, CS01, Vega) |
| `escalation_agent.py` | Wire real Slack SDK / SMTP / ServiceNow REST API, add PagerDuty / JIRA |
| `review.py` | Add multi-tier approval chain, audit log to PostgreSQL, SLA timer |
| `graph.py` | Add parallel branches for compliance+market agents, critique node, PDF report node |
| `main.py` | Add CLI args (argparse), batch mode, real document file loading |
