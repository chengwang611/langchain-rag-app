"""Review-time retrieval node backed by embedding_process vector backends."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from langchain_core.documents import Document

from ..embedding_process.vector_backend import (
    FileFundVectorStore,
    PGVectorFundStore,
    VectorStoreBackend,
)


def _default_top_k() -> int:
    raw = os.getenv("REVIEW_TOP_K", "8")
    try:
        return max(1, int(raw))
    except ValueError:
        return 8


def _build_backend(backend_name: str) -> VectorStoreBackend | None:
    """Return review retrieval backend from runtime config.

    REVIEW_VECTOR_BACKEND values:
    - auto (default): use file backend when file exists, else fallback to legacy store
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
        if Path(path).exists():
            return FileFundVectorStore(storage_path=path)
        return None

    raise ValueError(
        f"Unsupported REVIEW_VECTOR_BACKEND={backend_name!r}. "
        "Use one of: auto, file, pgvector"
    )


def _legacy_retrieve_from_ingest_store(state: dict, k: int) -> List[Document]:
    """Compatibility fallback for in-process demo runs.

    If the file backend is not present, this keeps the old behavior where
    ingest and review happen in one Python process.
    """
    from langchain_core.vectorstores import InMemoryVectorStore
    from langchain_openai import OpenAIEmbeddings

    from ..ingest import _FUND_DOCUMENT_STORE

    fund_id = state["fund_id"]
    query = state["query"]

    fund_chunks = _FUND_DOCUMENT_STORE.get(fund_id, [])
    if not fund_chunks:
        return []

    vector_store = InMemoryVectorStore.from_documents(
        fund_chunks,
        OpenAIEmbeddings(model="text-embedding-3-small"),
    )
    return vector_store.similarity_search(query, k=k)


def retrieve_node(state: dict) -> dict:
    """Retrieve top-k chunks for the requested fund_id at review time."""
    fund_id = state["fund_id"]
    query = state["query"]
    k = _default_top_k()

    backend_name = os.getenv("REVIEW_VECTOR_BACKEND", "auto").strip().lower()
    backend = _build_backend(backend_name)

    if backend is not None:
        retrieved = backend.similarity_search(fund_id=fund_id, query=query, k=k)
        if retrieved:
            print(f"[retrieve] backend={backend_name} | fund_id={fund_id} | hits={len(retrieved)}")
            return {**state, "retrieved": retrieved}

        print(f"[retrieve] backend={backend_name} | fund_id={fund_id} | no hits")
        return {**state, "retrieved": []}

    # auto mode fallback when no persisted file exists yet.
    retrieved = _legacy_retrieve_from_ingest_store(state, k)
    if not retrieved:
        print(
            "[retrieve] WARNING: no documents found. "
            "Run embedding_process ingestion first, or set REVIEW_VECTOR_BACKEND=file "
            "with REVIEW_FILE_BACKEND_PATH pointing to the persisted JSONL file."
        )
        return {**state, "retrieved": []}

    print(f"[retrieve] backend=legacy-in-memory | fund_id={fund_id} | hits={len(retrieved)}")
    return {**state, "retrieved": retrieved}
