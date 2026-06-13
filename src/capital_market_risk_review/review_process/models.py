"""Canonical review-domain schemas and shared state helpers.

This module is the source of truth for review-time state used by:
- review_process.api
- review_process.graph and review nodes
- local review_process.main demo runner
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages


RiskCategory = Literal[
    "Market",
    "Liquidity",
    "Counterparty",
    "Model",
    "Operational",
    "Regulatory",
    "Other",
]

Severity = Literal["low", "medium", "high", "critical"]
HumanDecision = Optional[Literal["approve", "edit", "reject"]]


@dataclass
class RiskFinding:
    """Single structured risk finding extracted from retrieved context."""

    category: RiskCategory
    severity: Severity
    snippet: str
    rationale: str
    source_id: str
    page_number: Optional[int] = None
    tags: list[str] = field(default_factory=list)


class ReviewState(TypedDict):
    """Shared LangGraph state for ingestion and review flows."""

    fund_id: str
    report_date: Optional[str]
    source_files: list[str]

    messages: Annotated[list, add_messages]
    raw_docs: list[str]
    query: str

    chunks: list
    retrieved: list
    draft_summary: str
    findings_json: str

    compliance_report: Optional[str]
    market_sensitivity_report: Optional[str]
    escalation_log: list[str]
    escalation_required: bool

    human_decision: HumanDecision
    edited_summary: Optional[str]
    final_summary: Optional[str]


def empty_review_state(fund_id: str = "") -> ReviewState:
    """Factory for a fully initialized state object.

    Centralizing defaults removes duplicate `_empty_state` definitions in
    API and local runner code.
    """

    return {
        "messages": [],
        "fund_id": fund_id,
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

