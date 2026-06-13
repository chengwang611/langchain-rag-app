"""Review-time retrieval node backed by embedding_process vector backends."""

from __future__ import annotations

import os
from pathlib import Path

from ..embedding_process.vector_backend import (
    FileFundVectorStore,
    PGVectorFundStore,
    VectorStoreBackend,
)
from .models import ReviewState


def _default_top_k() -> int:
    raw = os.getenv("REVIEW_TOP_K", "8")
    try:
        return max(1, int(raw))
    except ValueError:
        return 8


def _build_backend(backend_name: str) -> VectorStoreBackend:
    """Return review retrieval backend from runtime config.

    REVIEW_VECTOR_BACKEND values:
    - auto (default): use file backend when local store exists
    - file: force local file-backed retrieval
    - pgvector: force pgvector retrieval (placeholder implementation)
    """
    if backend_name == "file":
        path = os.getenv("REVIEW_FILE_BACKEND_PATH", ".local_data/fund_chunks.jsonl")
        return FileFundVectorStore(storage_path=path)

    if backend_name == "pgvector":
        conn = os.getenv("PGVECTOR_CONNECTION_STRING", "")
        if not conn:
            raise ValueError(
                "PGVECTOR_CONNECTION_STRING is required when REVIEW_VECTOR_BACKEND=pgvector"
            )
        return PGVectorFundStore(connection_string=conn)

    if backend_name == "auto":
        path = os.getenv("REVIEW_FILE_BACKEND_PATH", ".local_data/fund_chunks.jsonl")
        if not Path(path).exists():
            print(
                "[retrieve] no persisted embedding store found at "
                f"{path}. Run embedding_process first or configure pgvector backend."
            )
            return FileFundVectorStore(storage_path=path)
        return FileFundVectorStore(storage_path=path)

    raise ValueError(
        f"Unsupported REVIEW_VECTOR_BACKEND={backend_name!r}. "
        "Use one of: auto, file, pgvector"
    )


def retrieve_node(state: ReviewState) -> dict:
    """Retrieve top-k chunks for the requested fund_id from embedding_process store."""
    fund_id = state["fund_id"]
    query = state["query"]
    k = _default_top_k()

    backend_name = os.getenv("REVIEW_VECTOR_BACKEND", "auto").strip().lower()
    backend = _build_backend(backend_name)

    retrieved = backend.similarity_search(fund_id=fund_id, query=query, k=k)
    if not retrieved:
        print(
            f"[retrieve] backend={backend_name} | fund_id={fund_id} | no hits. "
            "Ensure ingestion/embedding has persisted data for this fund_id."
        )
        return {"retrieved": []}

    print(f"[retrieve] backend={backend_name} | fund_id={fund_id} | hits={len(retrieved)}")
    return {"retrieved": retrieved}
