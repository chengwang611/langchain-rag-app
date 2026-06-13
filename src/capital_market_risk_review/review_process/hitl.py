"""Human-in-the-loop nodes for the review pipeline."""

from __future__ import annotations

import importlib
from typing import cast


def _interrupt(payload: dict) -> None:
    """Load langgraph interrupt lazily to keep IDE/static checks tolerant."""
    interrupt_fn = getattr(importlib.import_module("langgraph.types"), "interrupt")
    interrupt_fn(payload)


def human_review_node(state: dict) -> dict:
    """Pause graph execution and wait for a human decision."""
    if state.get("human_decision") is None:
        payload = cast(
            dict,
            {
                "type": "risk_review_approval",
                "message": "Please review the draft summary and findings below.",
                "draft_summary": state.get("draft_summary", ""),
                "findings_json": state.get("findings_json", "[]"),
                "instructions": (
                    "Resume with human_decision set to: "
                    "'approve', 'edit' (provide edited_summary), or 'reject'."
                ),
            },
        )
        _interrupt(payload)
    return state


def route_after_review(state: dict) -> str:
    """Route to finalize when a valid decision is present."""
    decision = state.get("human_decision")
    if decision in {"approve", "edit", "reject"}:
        return "finalize"
    return "__end__"


def finalize_node(state: dict) -> dict:
    """Apply human decision and produce final summary."""
    decision = state.get("human_decision")

    if decision == "approve":
        final = state.get("draft_summary", "")
    elif decision == "edit":
        final = state.get("edited_summary") or state.get("draft_summary", "")
    else:
        final = "Review rejected by human approver. No summary published."

    return {**state, "final_summary": final}
