"""
graph.py — LangGraph workflow assembly for capital market risk review.

TWO SEPARATE GRAPHS
-------------------
1. build_ingestion_graph()  — hourly / daily batch ingestion per fund
     START → ingest → embed_and_persist → END

2. build_review_graph()     — runs at query / review time per fund
     START
       └── retrieve               (load persisted chunks, filter by fund_id)
            └── analyze           (LLM draft summary + structured findings)
                 └── compliance_agent      (Basel III/IV + XXX risk appetite)
                      └── market_sensitivity_agent  (VaR delta, CVA, RWA)
                           └── escalation_agent     (severity routing + notifications)
                                └── human_review    (HITL pause/approve)
                                     └── finalize   (apply decision)
                                          └── END

EXTEND:
- Add a "validate" node after analyze to check JSON schema before agents run
- Add parallel branches for compliance_agent and market_sensitivity_agent
- Add a "report" node to render PDF/Word output after finalize
- Add LangSmith tracing for end-to-end observability
- Add report_date range filter to retrieve_node for time-bounded reviews
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from capital_market_risk_review.analyze import analyze_node
from capital_market_risk_review.compliance_agent import compliance_agent_node
from capital_market_risk_review.escalation_agent import escalation_agent_node
from capital_market_risk_review.ingest import (
    embed_and_persist_node,
    ingest_node,
    retrieve_node,
)
from capital_market_risk_review.market_agent import market_sensitivity_agent_node
from capital_market_risk_review.models import ReviewState
from capital_market_risk_review.review import (
    finalize_node,
    human_review_node,
    route_after_review,
)


def build_ingestion_graph(checkpointer=None):
    """
    Assemble the ingestion pipeline graph.

    Runs hourly / daily per fund to:
      1. Split raw documents into chunks tagged with fund_id + report_date
      2. Embed and persist chunks to the vector store (incrementally)

    Args:
        checkpointer: LangGraph checkpointer. Defaults to MemorySaver.
                      EXTEND: pass SqliteSaver for durable ingestion audit trail.

    Usage:
        graph = build_ingestion_graph()
        graph.invoke({
            "fund_id": "FUND-001",
            "report_date": "2026-06-05",
            "source_files": ["FUND-001_daily_risk_report.pdf"],
            "raw_docs": [...],
            ...
        })
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(ReviewState)

    builder.add_node("ingest", ingest_node)
    builder.add_node("embed_and_persist", embed_and_persist_node)

    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "embed_and_persist")
    builder.add_edge("embed_and_persist", END)

    return builder.compile(checkpointer=checkpointer)


def build_review_graph(checkpointer=None):
    """
    Assemble the review pipeline graph.

    Runs at query / review time for a specific fund_id:
      1. Retrieve top-k chunks filtered by fund_id from the persistent store
      2. Analyze with LLM to produce draft summary + structured findings
      3. Run compliance, market sensitivity, and escalation agents
      4. Pause for HITL review
      5. Finalize with human decision

    Args:
        checkpointer: LangGraph checkpointer for HITL state persistence.
                      Defaults to MemorySaver.
                      EXTEND: pass SqliteSaver or PostgresSaver for production.

    Usage:
        graph = build_review_graph()
        config = {"configurable": {"thread_id": f"review-FUND-001-2026-06-05"}}
        paused = graph.invoke({"fund_id": "FUND-001", "query": "...", ...}, config=config)
        final  = graph.invoke({"human_decision": "approve"}, config=config)
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(ReviewState)

    # ── Register nodes ───────────────────────────────────────────────────────
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("compliance_agent", compliance_agent_node)
    builder.add_node("market_sensitivity_agent", market_sensitivity_agent_node)
    builder.add_node("escalation_agent", escalation_agent_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("finalize", finalize_node)

    # ── Wire edges ───────────────────────────────────────────────────────────
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "analyze")
    builder.add_edge("analyze", "compliance_agent")
    builder.add_edge("compliance_agent", "market_sensitivity_agent")
    builder.add_edge("market_sensitivity_agent", "escalation_agent")
    builder.add_edge("escalation_agent", "human_review")

    # Conditional routing after human decision
    builder.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "finalize": "finalize",
            "__end__": END,
        },
    )

    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)


def build_graph(checkpointer=None):
    """Backward-compatible alias for build_review_graph()."""
    return build_review_graph(checkpointer=checkpointer)
