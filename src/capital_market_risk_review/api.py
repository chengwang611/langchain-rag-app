"""
api.py — FastAPI service layer for the capital market risk review pipeline.

Exposes two pipelines as REST endpoints:

  POST /ingest/{fund_id}             — Pipeline 1: ingest documents for a fund
  POST /review/start                 — Pipeline 2: start review (runs to HITL pause)
  POST /review/{thread_id}/resume    — Resume after human decision
  GET  /review/{thread_id}/status    — Poll current state of a review
  GET  /health                       — Health check (used by Azure Container Apps)

Run locally:
  uvicorn capital_market_risk_review.api:app --reload --port 8000

EXTEND:
- Add OAuth2 / Azure AD authentication (fastapi.security.OAuth2AuthorizationCodeBearer)
- Add per-endpoint RBAC: ingest requires "risk-ops" role, resume requires "risk-analyst"
- Add request logging middleware for audit trail
- Add rate limiting (slowapi) to protect against abuse
- Add async background tasks for long-running ingestion jobs (BackgroundTasks)
"""


from __future__ import annotations

import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .graph import (
    build_ingestion_graph,
    build_review_graph,
)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Capital Market Risk Review API",
    description=(
        "Two-pipeline multi-agent LangGraph service for automated "
        "capital market risk document analysis with HITL approval."
    ),
    version="1.0.0",
)

# Build graphs once at startup — both are thread-safe in LangGraph
# EXTEND: inject a PostgresSaver checkpointer here for durable HITL state
_ingestion_graph = build_ingestion_graph()
_review_graph    = build_review_graph()


# ── Request / response models ─────────────────────────────────────────────────

class IngestRequest(BaseModel):
    """
    Payload for Pipeline 1 — document ingestion.
    EXTEND: accept base64-encoded file bytes and decode server-side
            instead of pre-extracted text.
    """
    report_date: str             # YYYY-MM-DD, e.g. "2026-06-05"
    raw_docs: list[str]          # text already extracted from PDF / Word files
    source_files: list[str] = [] # original file names / Azure Blob paths for metadata


class IngestResponse(BaseModel):
    status: str
    fund_id: str
    chunks_ingested: str         # informational — "see server logs"


class ReviewStartRequest(BaseModel):
    """
    Payload for Pipeline 2 — start a risk review for a fund.
    EXTEND: add report_date_from / report_date_to for time-bounded retrieval.
    """
    fund_id: str
    query: str = "Summarize material market risk issues, control gaps, and limit breaches."


class ReviewStartResponse(BaseModel):
    thread_id: str
    status: str                  # "awaiting_human_review"
    draft_summary: str
    findings_json: str
    compliance_report: Optional[str]
    market_sensitivity_report: Optional[str]
    escalation_log: list[str]
    escalation_required: bool


class ResumeRequest(BaseModel):
    """
    Payload to resume a paused review after human decision.
    EXTEND: add reviewer_id and review_notes for audit trail.
    """
    human_decision: str          # "approve" | "edit" | "reject"
    edited_summary: Optional[str] = None


class ResumeResponse(BaseModel):
    thread_id: str
    status: str                  # "completed" | "rejected"
    final_summary: Optional[str]


class StatusResponse(BaseModel):
    thread_id: str
    human_decision: Optional[str]
    final_summary: Optional[str]
    escalation_required: bool


# ── Helper: build empty state defaults ───────────────────────────────────────

def _empty_state(fund_id: str = "") -> dict:
    """Return a ReviewState dict with all fields set to safe empty defaults."""
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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
def health():
    """
    Health check endpoint — used by Azure Container Apps liveness probe.
    Returns 200 OK when the service is ready to accept requests.
    """
    return {"status": "ok"}


@app.post("/ingest/{fund_id}", response_model=IngestResponse, status_code=202, tags=["ingestion"])
def ingest(fund_id: str, req: IngestRequest):
    """
    Pipeline 1 — Ingest risk report documents for a fund.

    Call this endpoint hourly / daily per fund as new risk reports arrive.
    Documents are split, tagged with fund_id + report_date, embedded, and
    persisted. Subsequent calls accumulate new chunks without re-embedding
    existing documents.

    EXTEND:
    - Accept multipart/form-data file upload and extract text server-side
    - Run as an async background task for large document sets
    - Trigger via Azure Event Grid when a new file lands in Blob Storage
    """
    if not req.raw_docs:
        raise HTTPException(status_code=422, detail="raw_docs must not be empty.")

    state = {
        **_empty_state(fund_id),
        "report_date": req.report_date,
        "source_files": req.source_files,
        "raw_docs": req.raw_docs,
    }

    config = {"configurable": {"thread_id": f"ingest-{fund_id}-{req.report_date}"}}
    _ingestion_graph.invoke(state, config=config)

    return IngestResponse(
        status="ingested",
        fund_id=fund_id,
        chunks_ingested="see server logs",
    )


@app.post("/review/start", response_model=ReviewStartResponse, tags=["review"])
def start_review(req: ReviewStartRequest):
    """
    Pipeline 2 — Start a risk review for a fund.

    Runs the full pipeline until the HITL interrupt:
      retrieve → analyze → compliance_agent → market_sensitivity_agent
      → escalation_agent → [PAUSE]

    Returns thread_id which must be used to resume after human decision.

    EXTEND:
    - Validate that fund_id has ingested documents before starting review
    - Generate thread_id from a case management system for traceability
    - Store thread_id → reviewer assignment in a task database
    """
    thread_id = f"review-{req.fund_id}-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    state = {
        **_empty_state(req.fund_id),
        "query": req.query,
    }

    try:
        paused = _review_graph.invoke(state, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ReviewStartResponse(
        thread_id=thread_id,
        status="awaiting_human_review",
        draft_summary=paused.get("draft_summary", ""),
        findings_json=paused.get("findings_json", "[]"),
        compliance_report=paused.get("compliance_report"),
        market_sensitivity_report=paused.get("market_sensitivity_report"),
        escalation_log=paused.get("escalation_log", []),
        escalation_required=paused.get("escalation_required", False),
    )


@app.post("/review/{thread_id}/resume", response_model=ResumeResponse, tags=["review"])
def resume_review(thread_id: str, req: ResumeRequest):
    """
    Resume a paused review with a human decision.

    The same thread_id from /review/start must be used — LangGraph
    rehydrates the full pipeline state from the checkpointer and applies
    the human decision in finalize_node.

    EXTEND:
    - Validate reviewer_id against an RBAC policy before accepting decision
    - Write decision + reviewer_id + timestamp to audit log database
    - Trigger downstream notification (email, Slack) on approval
    """
    if req.human_decision not in {"approve", "edit", "reject"}:
        raise HTTPException(
            status_code=422,
            detail="human_decision must be 'approve', 'edit', or 'reject'.",
        )
    if req.human_decision == "edit" and not req.edited_summary:
        raise HTTPException(
            status_code=422,
            detail="edited_summary is required when human_decision is 'edit'.",
        )

    config = {"configurable": {"thread_id": thread_id}}
    update = {
        "human_decision": req.human_decision,
        "edited_summary": req.edited_summary,
    }

    try:
        final = _review_graph.invoke(update, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    status = "rejected" if req.human_decision == "reject" else "completed"
    return ResumeResponse(
        thread_id=thread_id,
        status=status,
        final_summary=final.get("final_summary"),
    )


@app.get("/review/{thread_id}/status", response_model=StatusResponse, tags=["review"])
def get_status(thread_id: str):
    """
    Poll the current state of a review thread.

    Useful for UI polling to detect when a review has been completed
    or if escalation was triggered.

    EXTEND:
    - Return full findings_json and agent reports for rich UI display
    - Add WebSocket endpoint for real-time status push
    """
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = _review_graph.get_state(config)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Thread not found: {e}")

    values = state.values if hasattr(state, "values") else {}
    return StatusResponse(
        thread_id=thread_id,
        human_decision=values.get("human_decision"),
        final_summary=values.get("final_summary"),
        escalation_required=values.get("escalation_required", False),
    )

