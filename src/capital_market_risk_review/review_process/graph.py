"""LangGraph assembly for review-time workflow."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .analyze import analyze_node
from .compliance_agent import compliance_agent_node
from .escalation_agent import escalation_agent_node
from .market_agent import market_sensitivity_agent_node
from .models import ReviewState
from .hitl import finalize_node, human_review_node, route_after_review
from .retrieval import retrieve_node


def build_review_graph(checkpointer=None):
    """Build review graph using persisted embeddings from embedding_process backends."""
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(ReviewState)

    builder.add_node("retrieve", retrieve_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("compliance_agent", compliance_agent_node)
    builder.add_node("market_sensitivity_agent", market_sensitivity_agent_node)
    builder.add_node("escalation_agent", escalation_agent_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "analyze")
    builder.add_edge("analyze", "compliance_agent")
    builder.add_edge("compliance_agent", "market_sensitivity_agent")
    builder.add_edge("market_sensitivity_agent", "escalation_agent")
    builder.add_edge("escalation_agent", "human_review")

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
