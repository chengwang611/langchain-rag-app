"""
graph.py — LangGraph workflow assembly for capital market risk review.

Pipeline:
  START
    └── ingest          (split documents into chunks)
         └── retrieve   (embed + retrieve top-k chunks)
              └── analyze   (LLM draft summary + findings)
                   └── human_review  (HITL pause/approve)
                        └── finalize  (apply decision)
                             └── END

EXTEND:
- Add a "validate" node after analyze to check JSON schema before review
- Add a "critique" node for LLM self-review before human sees it
- Add parallel branches for different risk categories
- Add a "report" node to render PDF/Word output after finalize
- Add LangSmith tracing for observability
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.template.capital_market_risk_review.analyze import analyze_node
from src.template.capital_market_risk_review.ingest import ingest_node, retrieve_node
from src.template.capital_market_risk_review.models import ReviewState
from src.template.capital_market_risk_review.review import (
    finalize_node,
    human_review_node,
    route_after_review,
)


def build_graph(checkpointer=None):
    """
    Assemble and compile the risk review graph.

    Args:
        checkpointer: LangGraph checkpointer for state persistence.
                      Defaults to in-memory MemorySaver.
                      EXTEND: pass SqliteSaver or PostgresSaver for production.

    Returns:
        Compiled LangGraph graph.

    EXTEND:
    - Accept a config dict to toggle nodes (e.g. skip HITL for batch runs)
    - Add interrupt_before=["human_review"] as alternative interrupt strategy
    - Add debug=True for verbose node tracing during development
    """
    if checkpointer is None:
        # EXTEND: replace with SqliteSaver or PostgresSaver for production
        checkpointer = MemorySaver()

    builder = StateGraph(ReviewState)

    # ── Register nodes ───────────────────────────────────────────────────────
    builder.add_node("ingest", ingest_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("finalize", finalize_node)

    # ── Wire edges ───────────────────────────────────────────────────────────
    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "retrieve")
    builder.add_edge("retrieve", "analyze")
    builder.add_edge("analyze", "human_review")

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

