"""
graph.py — LangGraph workflow assembly for capital market risk review.

TWO SEPARATE GRAPHS
-------------------
1. build_ingestion_graph()  — hourly / daily batch ingestion per fund
     START → ingest → embed_and_persist → END

2. build_review_graph()     — delegated to review_process package
     START → retrieve → analyze → compliance_agent → market_sensitivity_agent
           → escalation_agent → human_review → finalize → END
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .ingest import embed_and_persist_node, ingest_node
from .models import ReviewState
from .review_process.graph import build_review_graph


def build_ingestion_graph(checkpointer=None):
    """Assemble the ingestion pipeline graph."""
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(ReviewState)

    builder.add_node("ingest", ingest_node)
    builder.add_node("embed_and_persist", embed_and_persist_node)

    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "embed_and_persist")
    builder.add_edge("embed_and_persist", END)

    return builder.compile(checkpointer=checkpointer)


def build_graph(checkpointer=None):
    """Backward-compatible alias for build_review_graph()."""
    return build_review_graph(checkpointer=checkpointer)
