"""
main.py — Entry point demonstrating the two-pipeline design.

Usage:
    python -m capital_market_risk_review.main

TWO PIPELINES:
  Pipeline 1 — Ingestion (runs hourly / daily as a batch job)
    build_ingestion_graph()  →  ingest_node  →  embed_and_persist_node
    - Call once per fund per reporting cycle
    - Chunks are tagged with fund_id and accumulated in the persistent store

  Pipeline 2 — Review (runs at query / review time)
    build_review_graph()  →  retrieve_node (filtered by fund_id)  →  analyze  →
    compliance_agent  →  market_sensitivity_agent  →  escalation_agent  →
    human_review (HITL pause)  →  finalize

EXTEND:
- Accept fund_id and report file paths as CLI arguments (argparse)
- Schedule ingestion as an hourly cron job or Airflow DAG
- Replace raw_docs with PyPDFLoader / AzureBlobLoader for real files
- Write final_summary + findings to a risk management database
"""

from __future__ import annotations

import json

from dotenv import load_dotenv

from .graph import (
    build_ingestion_graph,
    build_review_graph,
)
from .models import ReviewState

load_dotenv()


# ── Shared state defaults ─────────────────────────────────────────────────────
# Fields not used by a given pipeline are set to safe empty defaults.
def _empty_state() -> ReviewState:
    return {
        "messages": [],
        "fund_id": "",
        "report_date": None,
        "source_files": [],
        "raw_docs": [],
        "query": "",
        "chunks": [],
        "retrieved": [],
        "draft_summary": "",
        "findings_json": "[]",
        "compliance_report": None,
        "market_sensitivity_report": None,
        "escalation_log": [],
        "escalation_required": False,
        "human_decision": None,
        "edited_summary": None,
        "final_summary": None,
    }


# ── Sample fund reports ───────────────────────────────────────────────────────
# EXTEND: replace with real PyPDFLoader / AzureBlobLoader calls
FUND_REPORTS: dict[str, list[str]] = {
    "FUND-001": [
        "Desk VaR limit utilization increased from 72% to 96% over 3 days "
        "driven by elevated rates volatility. Breach notification has not been sent.",
        "Stress scenario analysis shows concentrated exposure in long-end swaps. "
        "Liquidity assumptions used in the model are 6 months stale and require refresh.",
    ],
    "FUND-002": [
        "Counterparty CSA thresholds were amended on two bilateral agreements. "
        "Margin call processing latency increased to T+3, above the T+1 SLA.",
        "Model risk: the VaR model for FX options has not been re-validated "
        "since Q3 last year. A significant regime change occurred in Q1 this year.",
    ],
    "FUND-003": [
        "Equity desk breached its DV01 limit by 12% on three consecutive days. "
        "Risk manager was notified but no formal escalation was recorded.",
        "Operational risk: a settlement failure rate of 3.2% was observed this week, "
        "exceeding the internal threshold of 1.5%. Root cause is under investigation.",
    ],
}

REVIEW_FUND_ID = "FUND-001"
QUERY = "Summarize material market risk issues, control gaps, and limit breaches."


def run_ingestion_pipeline(ingestion_graph, fund_id: str, docs: list[str], report_date: str):
    """Ingest a batch of documents for a single fund."""
    print(f"\n  Ingesting fund_id={fund_id} | date={report_date} | {len(docs)} documents")
    state = {
        **_empty_state(),
        "fund_id": fund_id,
        "report_date": report_date,
        "source_files": [f"{fund_id}_risk_report_{report_date}.pdf"],
        "raw_docs": docs,
    }
    config = {"configurable": {"thread_id": f"ingest-{fund_id}-{report_date}"}}
    ingestion_graph.invoke(state, config=config)


def main():
    # ── PIPELINE 1: Batch Ingestion ───────────────────────────────────────────
    # Simulates two ingestion runs (e.g. yesterday's and today's reports)
    # Real usage: schedule as hourly cron / Airflow DAG per fund
    print("=" * 60)
    print("PIPELINE 1: Batch ingestion (hourly / daily)")
    print("=" * 60)

    ingestion_graph = build_ingestion_graph()

    for run_date in ["2026-06-04", "2026-06-05"]:   # simulate two daily runs
        print(f"\nIngestion run: {run_date}")
        for fund_id, docs in FUND_REPORTS.items():
            run_ingestion_pipeline(ingestion_graph, fund_id, docs, run_date)

    # ── PIPELINE 2: Review (fund_id scoped) ───────────────────────────────────
    print("\n" + "=" * 60)
    print(f"PIPELINE 2: Review for fund_id={REVIEW_FUND_ID}")
    print("=" * 60)

    review_graph = build_review_graph()

    # Each review case gets a unique thread_id for HITL checkpoint tracking
    # EXTEND: generate uuid4 per review case
    config = {"configurable": {"thread_id": f"review-{REVIEW_FUND_ID}-2026-06-05"}}

    review_state: ReviewState = {
        **_empty_state(),
        "fund_id": REVIEW_FUND_ID,
        "query": QUERY,
    }

    # ── Step 1: Run until HITL interrupt ─────────────────────────────────────
    print(f"\nSTEP 1: Running review pipeline until human review pause...")
    paused_state = review_graph.invoke(review_state, config=config)

    print("\nDraft Summary:")
    print("-" * 40)
    print(paused_state.get("draft_summary", ""))

    print("\nRisk Findings (JSON):")
    print("-" * 40)
    try:
        findings = json.loads(paused_state.get("findings_json", "[]"))
        print(json.dumps(findings, indent=2))
    except json.JSONDecodeError:
        print(paused_state.get("findings_json", "[]"))

    print("\n" + "=" * 60)
    print("AGENT: Regulatory Compliance Report")
    print("=" * 60)
    print(paused_state.get("compliance_report", "No compliance report generated."))

    print("\n" + "=" * 60)
    print("AGENT: Market Sensitivity Report")
    print("=" * 60)
    print(paused_state.get("market_sensitivity_report", "No market sensitivity report generated."))

    print("\n" + "=" * 60)
    print("AGENT: Escalation Log")
    print("=" * 60)
    escalation_log = paused_state.get("escalation_log", [])
    print("\n".join(escalation_log) if escalation_log else "No escalations triggered.")
    print(f"\nEscalation required: {paused_state.get('escalation_required', False)}")

    # ── Step 2: Simulate human decision ──────────────────────────────────────
    # EXTEND: replace with actual UI input (web form, Slack, CLI prompt)
    print("\n" + "=" * 60)
    print("STEP 2: Human reviewer approves...")
    print("=" * 60)

    final_state = review_graph.invoke(
        {"human_decision": "approve", "edited_summary": None},
        config=config,
    )

    print("\nFinal Summary:")
    print("-" * 40)
    print(final_state.get("final_summary", "No summary produced."))


if __name__ == "__main__":
    main()

