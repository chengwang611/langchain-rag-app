"""Local review demo entrypoint.

Usage:
    python -m capital_market_risk_review.review_process.main

This demo bootstraps sample chunks into the file-backed store used by
`review_process.retrieval` so the review graph can run end-to-end.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..embedding_process.vector_backend import FileFundVectorStore
from .graph import build_review_graph
from .models import empty_review_state

load_dotenv()

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


def _bootstrap_demo_store(process_date: str) -> None:
    """Persist sample documents into file backend used by retrieve_node."""
    store_path = os.getenv("REVIEW_FILE_BACKEND_PATH", ".local_data/fund_chunks.jsonl")
    os.environ.setdefault("REVIEW_VECTOR_BACKEND", "file")
    Path(store_path).parent.mkdir(parents=True, exist_ok=True)

    backend = FileFundVectorStore(storage_path=store_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)

    for fund_id, docs in FUND_REPORTS.items():
        source_docs = [
            Document(
                page_content=text,
                metadata={
                    "fund_id": fund_id,
                    "document_id": f"{fund_id}-DOC-{i:03d}",
                    "report_date": process_date,
                    "source_file": f"{fund_id}_risk_report_{process_date}.txt",
                    "chunk_index": i,
                    "chunk_id": f"{fund_id}:{process_date}:{i}",
                    "source_id": f"{fund_id}:{process_date}:{i}",
                },
            )
            for i, text in enumerate(docs)
        ]
        chunked = splitter.split_documents(source_docs)
        backend.add_documents(chunked)


def main() -> int:
    process_date = "2026-06-05"

    print("=" * 60)
    print("BOOTSTRAP: sample ingestion into file backend")
    print("=" * 60)
    _bootstrap_demo_store(process_date=process_date)

    print("\n" + "=" * 60)
    print(f"PIPELINE: Review for fund_id={REVIEW_FUND_ID}")
    print("=" * 60)

    review_graph = build_review_graph()
    config = {"configurable": {"thread_id": f"review-{REVIEW_FUND_ID}-{process_date}"}}

    review_state = empty_review_state(REVIEW_FUND_ID)
    review_state["query"] = QUERY

    print("\nSTEP 1: Running review pipeline until human review pause...")
    paused_state = review_graph.invoke(review_state, config=config)

    print("\nDraft Summary:\n" + "-" * 40)
    print(paused_state.get("draft_summary", ""))

    print("\nRisk Findings (JSON):\n" + "-" * 40)
    try:
        print(json.dumps(json.loads(paused_state.get("findings_json", "[]")), indent=2))
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

    print("\n" + "=" * 60)
    print("STEP 2: Human reviewer approves...")
    print("=" * 60)

    final_state = review_graph.invoke(
        {"human_decision": "approve", "edited_summary": None},
        config=config,
    )

    print("\nFinal Summary:\n" + "-" * 40)
    print(final_state.get("final_summary", "No summary produced."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
