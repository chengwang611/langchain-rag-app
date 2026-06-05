"""
models.py — Domain schemas for capital market risk review.

Extend this file to:
- Add new risk categories (e.g. ESG, Operational, Regulatory)
- Add new severity levels or scoring fields
- Add compliance mapping fields (e.g. Basel, FRTB, CCAR references)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages


# ── Risk categories ─────────────────────────────────────────────────────────
# EXTEND: add more categories to match your firm's taxonomy
RiskCategory = Literal[
    "Market",
    "Liquidity",
    "Counterparty",
    "Model",
    "Operational",
    "Regulatory",
    "Other",
]

# ── Severity levels ──────────────────────────────────────────────────────────
# EXTEND: add "informational" or numeric score alongside literal
Severity = Literal["low", "medium", "high", "critical"]

# ── Human decision options ────────────────────────────────────────────────────
# EXTEND: add "escalate" or "delegate" for multi-tier approval workflows
HumanDecision = Literal["approve", "edit", "reject"] | None


@dataclass
class RiskFinding:
    """
    Single structured risk finding extracted from a document chunk.

    EXTEND:
    - Add `regulation_ref: str` for Basel/FRTB/CCAR mapping
    - Add `desk: str` for trading desk attribution
    - Add `recommended_action: str` for remediation tracking
    - Add `due_date: str` for SLA tracking
    """

    category: RiskCategory
    severity: Severity
    snippet: str                   # exact text evidence from document
    rationale: str                 # analyst reasoning
    source_id: str                 # document chunk reference
    page_number: int | None = None # EXTEND: populate when parsing PDF pages
    tags: list[str] = field(default_factory=list)  # EXTEND: free-form labels


class ReviewState(TypedDict):
    """
    Shared LangGraph state flowing through all nodes.

    EXTEND:
    - Add `user_id: str` for audit trail
    - Add `document_metadata: dict` for doc classification
    - Add `confidence_score: float` from LLM self-evaluation
    - Add `escalation_level: int` for multi-tier HITL routing
    """

    # ── Input ────────────────────────────────────────────────────────────────
    messages: Annotated[list, add_messages]    # conversation history
    raw_docs: list[str]                        # raw document texts
    query: str                                 # retrieval query

    # ── Intermediate pipeline state ──────────────────────────────────────────
    chunks: list                               # split document chunks
    retrieved: list                            # top-k retrieved chunks
    draft_summary: str                         # LLM draft executive summary
    findings_json: str                         # JSON array of RiskFindings

    # ── Agent outputs ────────────────────────────────────────────────────────
    # Populated by compliance_agent_node (Basel III/IV + XXX risk appetite check)
    compliance_report: str | None

    # Populated by market_sensitivity_agent_node (VaR delta, CVA, RWA)
    market_sensitivity_report: str | None

    # Populated by escalation_agent_node (Slack / email / ServiceNow actions taken)
    escalation_log: list[str]

    # True when critical or high findings triggered notifications
    escalation_required: bool

    # ── HITL fields ──────────────────────────────────────────────────────────
    human_decision: HumanDecision              # approve / edit / reject
    edited_summary: str | None                 # human-edited summary if decision==edit

    # ── Output ───────────────────────────────────────────────────────────────
    final_summary: str | None                  # approved final summary

