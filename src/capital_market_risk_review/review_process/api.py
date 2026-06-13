"""FastAPI service layer for review workflow.

Canonical API module location is review_process.api.

Endpoints:
  POST /review/start
  POST /review/{thread_id}/resume
  GET  /review/{thread_id}/status
  GET  /health
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .graph import build_review_graph
from .models import empty_review_state

app = FastAPI(
    title="Capital Market Risk Review API",
    description=(
        "Review-time multi-agent LangGraph service. "
        "Ingestion/embedding is handled by embedding_process batch jobs."
    ),
    version="1.0.0",
)

_review_graph = build_review_graph()


class ReviewStartRequest(BaseModel):
    fund_id: str
    query: str = "Summarize material market risk issues, control gaps, and limit breaches."


class ReviewStartResponse(BaseModel):
    thread_id: str
    status: str
    draft_summary: str
    findings_json: str
    compliance_report: Optional[str]
    market_sensitivity_report: Optional[str]
    escalation_log: list[str]
    escalation_required: bool


class ResumeRequest(BaseModel):
    human_decision: str
    edited_summary: Optional[str] = None


class ResumeResponse(BaseModel):
    thread_id: str
    status: str
    final_summary: Optional[str]


class StatusResponse(BaseModel):
    thread_id: str
    human_decision: Optional[str]
    final_summary: Optional[str]
    escalation_required: bool


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok"}


@app.post("/review/start", response_model=ReviewStartResponse, tags=["review"])
def start_review(req: ReviewStartRequest):
    thread_id = f"review-{req.fund_id}-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    state = {
        **empty_review_state(req.fund_id),
        "query": req.query,
    }

    try:
        paused = _review_graph.invoke(state, config=config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    status = "rejected" if req.human_decision == "reject" else "completed"
    return ResumeResponse(
        thread_id=thread_id,
        status=status,
        final_summary=final.get("final_summary"),
    )


@app.get("/review/{thread_id}/status", response_model=StatusResponse, tags=["review"])
def get_status(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = _review_graph.get_state(config)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Thread not found: {exc}")

    values = state.values if hasattr(state, "values") else {}
    return StatusResponse(
        thread_id=thread_id,
        human_decision=values.get("human_decision"),
        final_summary=values.get("final_summary"),
        escalation_required=values.get("escalation_required", False),
    )
