"""
review.py — Human-in-the-Loop (HITL) pause, decision routing, and finalization.

EXTEND:
- Add multi-tier approval (junior analyst → senior → risk officer)
- Add escalation: auto-escalate if severity contains "critical"
- Connect interrupt payload to a real UI (Slack, email, web dashboard)
- Add audit log: write decision + timestamp + user_id to database
- Add SLA timer: auto-reject if no decision within N minutes
"""

from __future__ import annotations

from langgraph.types import interrupt

from .models import ReviewState


def human_review_node(state: ReviewState) -> ReviewState:
    """
    Pause graph execution and wait for a human decision.

    When resumed, state must include:
        human_decision: "approve" | "edit" | "reject"
        edited_summary: str | None  (only required when decision == "edit")

    EXTEND:
    - Send interrupt payload to a Slack webhook or email notification
    - Include findings_json in payload so reviewer sees structured data
    - Add `reviewer_id` field to capture who approved
    - Add `review_notes` field for optional free-text comments
    """
    if state.get("human_decision") is None:
        # Graph pauses here until resumed with human_decision in state
        interrupt(
            {
                "type": "risk_review_approval",
                "message": "Please review the draft summary and findings below.",
                "draft_summary": state.get("draft_summary", ""),
                "findings_json": state.get("findings_json", "[]"),
                # EXTEND: add "findings_count", "critical_count" for quick triage
                "instructions": (
                    "Resume with human_decision set to: "
                    "'approve', 'edit' (provide edited_summary), or 'reject'."
                ),
            }
        )
    return {}


def route_after_review(state: ReviewState) -> str:
    """
    Decide next node based on human decision.

    EXTEND:
    - Add "escalate" route for critical findings requiring senior sign-off
    - Add "rework" route to send back to analyze_node with reviewer comments
    """
    decision = state.get("human_decision")
    if decision in {"approve", "edit", "reject"}:
        return "finalize"
    # No decision yet (should not happen after interrupt resumes)
    return "__end__"


def finalize_node(state: ReviewState) -> ReviewState:
    """
    Apply human decision and produce the final summary.

    EXTEND:
    - Write final_summary + findings_json to a database or document store
    - Generate a formatted PDF/Word report
    - Trigger downstream workflow (e.g. notify risk committee, update JIRA)
    - Add `approved_by`, `approved_at` fields to audit trail
    """
    decision = state.get("human_decision")

    if decision == "approve":
        # Use draft as-is
        final = state.get("draft_summary", "")

    elif decision == "edit":
        # Use human-edited version, fall back to draft if empty
        final = state.get("edited_summary") or state.get("draft_summary", "")

    else:
        # rejected
        final = "Review rejected by human approver. No summary published."

    return {"final_summary": final}

