"""Backward-compatible API shim.

Canonical API module lives at capital_market_risk_review.review_process.api.
"""

from .review_process.api import (
    IngestRequest,
    IngestResponse,
    ResumeRequest,
    ResumeResponse,
    ReviewStartRequest,
    ReviewStartResponse,
    StatusResponse,
    app,
    get_status,
    health,
    ingest,
    resume_review,
    start_review,
)

__all__ = [
    "app",
    "IngestRequest",
    "IngestResponse",
    "ReviewStartRequest",
    "ReviewStartResponse",
    "ResumeRequest",
    "ResumeResponse",
    "StatusResponse",
    "health",
    "ingest",
    "start_review",
    "resume_review",
    "get_status",
]
