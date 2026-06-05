"""
main.py — Entry point for running the capital market risk review pipeline.

Usage:
    python -m src.template.capital_market_risk_review.main

EXTEND:
- Accept document file paths as CLI arguments (argparse)
- Accept query as CLI argument
- Add batch mode: loop over a folder of documents
- Add output mode: write final_summary to file or database
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv

from src.template.capital_market_risk_review.graph import build_graph
from src.template.capital_market_risk_review.models import ReviewState

load_dotenv()


# ── Sample documents ─────────────────────────────────────────────────────────
# EXTEND: replace with real document loaders
#   from langchain_community.document_loaders import PyPDFLoader
#   docs = PyPDFLoader("path/to/risk_report.pdf").load()
SAMPLE_DOCS = [
    "Desk VaR limit utilization increased from 72% to 96% over 3 days "
    "driven by elevated rates volatility. Breach notification has not been sent.",

    "Stress scenario analysis shows concentrated exposure in long-end swaps. "
    "Liquidity assumptions used in the model are 6 months stale and require refresh.",

    "Counterparty CSA thresholds were amended on two bilateral agreements. "
    "Margin call processing latency increased to T+3, above the T+1 SLA.",

    "Model risk: the VaR model for FX options has not been re-validated "
    "since Q3 last year. A significant regime change occurred in Q1 this year.",
]

# EXTEND: make query configurable via CLI or config file
QUERY = "Summarize material market risk issues, control gaps, and limit breaches."


def main():
    # Build graph with in-memory checkpointer
    # EXTEND: use SqliteSaver("checkpoints.db") for durable checkpoints
    graph = build_graph()

    # Thread ID ties all invocations together for checkpoint resume
    # EXTEND: generate unique thread_id per review case (e.g. uuid4)
    config = {"configurable": {"thread_id": "risk-review-demo-1"}}

    # Initial state
    initial_state: ReviewState = {
        "messages": [],
        "raw_docs": SAMPLE_DOCS,
        "query": QUERY,
        "chunks": [],
        "retrieved": [],
        "draft_summary": "",
        "findings_json": "[]",
        "human_decision": None,
        "edited_summary": None,
        "final_summary": None,
    }

    # ── Step 1: Run until HITL interrupt ─────────────────────────────────────
    print("=" * 60)
    print("STEP 1: Running pipeline until human review pause...")
    print("=" * 60)

    paused_state = graph.invoke(initial_state, config=config)

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

    # ── Step 2: Simulate human decision ──────────────────────────────────────
    # EXTEND: replace with actual UI input (web form, Slack, CLI prompt)
    print("\n" + "=" * 60)
    print("STEP 2: Human reviewer approves...")
    print("=" * 60)

    # Options:
    #   {"human_decision": "approve"}
    #   {"human_decision": "edit", "edited_summary": "Custom text..."}
    #   {"human_decision": "reject"}
    human_input = {
        "human_decision": "approve",
        "edited_summary": None,
    }

    final_state = graph.invoke(human_input, config=config)

    print("\nFinal Summary:")
    print("-" * 40)
    print(final_state.get("final_summary", "No summary produced."))


if __name__ == "__main__":
    main()

