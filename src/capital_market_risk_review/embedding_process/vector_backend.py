"""Vector store backend abstraction for the embedding process.

Phase 1:
- InMemoryFundVectorStore is used for local validation and rapid iteration.
- FileFundVectorStore provides persistence without external databases.

Phase 2 (current):
- PGVectorFundStore is the production backend using PostgreSQL + pgvector.
  It provides persistent, scalable vector storage with fund_id-scoped retrieval.

Usage:
  # File backend (local dev, no external deps)
  backend = FileFundVectorStore(storage_path=".local_data/fund_chunks.jsonl")

  # PGVector backend (production)
  backend = PGVectorFundStore(
      connection_string="postgresql+psycopg://user:pass@host:5432/db"
  )
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Protocol

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

# PGVector is an optional dependency — file backend works without it.
try:
    from langchain_postgres import PGVector as LangChainPGVector

    _PGVECTOR_AVAILABLE = True
except ImportError:
    _PGVECTOR_AVAILABLE = False


class VectorStoreBackend(Protocol):
    """Contract used by the Spark embedding pipeline.

    Any backend implementation must support ingest and per-fund retrieval.

    The `requires_driver_local_write` flag tells the Spark pipeline whether
    this backend needs data collected to the driver (toLocalIterator) or
    can be written in parallel from executor tasks (foreachPartition).

    - File/InMemory backends → driver_local_write = True
    - PGVector backend      → driver_local_write = False

    EXTEND:
    - Add delete_by_fund_id() for retention policies.
    - Add upsert semantics keyed by chunk_id to support idempotent ingestion.
    - Add count_by_fund_id() for monitoring dashboards.
    """

    @property
    def requires_driver_local_write(self) -> bool:
        """If True, Spark must collect data to the driver before writing.

        Backends that store data in driver-local memory (dict, file) must
        return True. Backends that connect to an external database from
        executor tasks (PGVector) must return False.
        """
        ...

    def add_documents(self, documents: Iterable[Document]) -> int:
        """Persist a batch of chunk documents and return number persisted."""

    def similarity_search(self, fund_id: str, query: str, k: int = 8) -> List[Document]:
        """Retrieve top-k chunks for a specific fund."""

    def total_documents(self) -> int:
        """Return total stored chunk count across all funds."""


@dataclass
class InMemoryFundVectorStore:
    """Phase 1 backend: process-local in-memory store grouped by fund_id.

    Why keep this backend:
    - Fast developer loop for local testing.
    - No external infra dependency for phase 1.

    Known limitation:
    - Data is lost when process exits.
    - Not suitable for distributed Spark executors in production.
    """

    embedding_model: str = "text-embedding-3-small"
    _documents_by_fund: Dict[str, List[Document]] = field(default_factory=dict)

    @property
    def requires_driver_local_write(self) -> bool:
        """InMemory backend stores data in driver-local memory."""
        return True

    def add_documents(self, documents: Iterable[Document]) -> int:
        count = 0
        for doc in documents:
            fund_id = str(doc.metadata.get("fund_id", "UNKNOWN"))
            self._documents_by_fund.setdefault(fund_id, []).append(doc)
            count += 1
        return count

    def similarity_search(self, fund_id: str, query: str, k: int = 8) -> List[Document]:
        docs = self._documents_by_fund.get(fund_id, [])
        if not docs:
            return []

        # Build ephemeral vector index for this fund's docs only.
        # EXTEND: replace with persistent per-fund index in PGVector.
        embeddings = OpenAIEmbeddings(model=self.embedding_model)
        store = InMemoryVectorStore.from_documents(docs, embeddings)
        return store.similarity_search(query, k=k)

    def total_documents(self) -> int:
        return sum(len(v) for v in self._documents_by_fund.values())


@dataclass
class PGVectorFundStore:
    """Production PGVector backend for persistent, scalable vector storage.

    Uses langchain-postgres PGVector with fund_id metadata filtering.
    Each chunk is stored with fund_id in metadata for scoped retrieval.

    Requires:
      pip install langchain-postgres psycopg[binary]

    Connection string format:
      postgresql+psycopg://user:password@host:5432/database

    Example:
      store = PGVectorFundStore(
          connection_string="postgresql+psycopg://risk_user:risk_pass@localhost:5432/risk_review"
      )
      store.add_documents(docs)
      results = store.similarity_search(fund_id="FUND-001", query="VaR breach", k=8)
    """

    connection_string: str
    collection_name: str = "fund_risk_docs"
    embedding_model: str = "text-embedding-3-small"
    _vector_store: Optional["LangChainPGVector"] = field(default=None, init=False)

    @property
    def requires_driver_local_write(self) -> bool:
        """PGVector connects to an external database — can write from executors."""
        return False

    def _get_store(self) -> "LangChainPGVector":
        """Lazy-initialize the PGVector connection.

        The store is created once and reused across calls to avoid
        connection overhead on every add/query operation.
        """
        if self._vector_store is None:
            if not _PGVECTOR_AVAILABLE:
                raise ImportError(
                    "PGVector backend requires langchain-postgres and psycopg.\n"
                    "Install with: pip install langchain-postgres psycopg[binary]"
                )
            embeddings = OpenAIEmbeddings(model=self.embedding_model)
            self._vector_store = LangChainPGVector(
                embeddings=embeddings,
                collection_name=self.collection_name,
                connection=self.connection_string,
            )
        return self._vector_store

    def add_documents(self, documents: Iterable[Document]) -> int:
        """Persist a batch of chunk documents to PostgreSQL/pgvector."""
        docs = list(documents)
        if not docs:
            return 0
        store = self._get_store()
        store.add_documents(docs)
        return len(docs)


    def similarity_search(self, fund_id: str, query: str, k: int = 8) -> List[Document]:
        """Retrieve top-k chunks for a specific fund using metadata filtering.

        The filter uses PGVector's metadata JSONB query syntax to scope
        retrieval to a single fund_id, ensuring Fund A's documents never
        pollute Fund B's results.
        """
        store = self._get_store()
        return store.similarity_search(
            query,
            k=k,
            filter={"fund_id": {"$eq": fund_id}},
        )

    def total_documents(self) -> int:
        """Return total stored chunk count across all funds.

        Note: PGVector does not expose a direct document count through its
        standard API. This returns -1 as a sentinel value. For production
        monitoring, add a separate metadata table or use SQLAlchemy to
        query the underlying langchain_pg_collection directly.
        """
        return -1


@dataclass
class FileFundVectorStore:
    """Local file-backed backend for persistence without external databases.

    Storage format is JSONL where each row is one chunk document.
    This backend is intentionally simple and interview-defensible for phase 1.
    """

    storage_path: str = ".local_data/fund_chunks.jsonl"
    _documents_by_fund: Dict[str, List[Document]] = field(default_factory=dict)
    _loaded: bool = False

    @property
    def requires_driver_local_write(self) -> bool:
        """File backend writes to a local JSONL file on the driver."""
        return True

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        path = Path(self.storage_path)
        if not path.exists():
            self._loaded = True
            return

        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                doc = Document(
                    page_content=str(row.get("page_content", "")),
                    metadata=dict(row.get("metadata", {})),
                )
                fund_id = str(doc.metadata.get("fund_id", "UNKNOWN"))
                self._documents_by_fund.setdefault(fund_id, []).append(doc)

        self._loaded = True

    def _append_rows(self, rows: List[dict]) -> None:
        path = Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=True) + "\n")

    @staticmethod
    def _tokenize(text: str) -> Counter:
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        return Counter(tokens)

    def add_documents(self, documents: Iterable[Document]) -> int:
        self._ensure_loaded()
        rows: List[dict] = []
        count = 0
        for doc in documents:
            fund_id = str(doc.metadata.get("fund_id", "UNKNOWN"))
            self._documents_by_fund.setdefault(fund_id, []).append(doc)
            rows.append({"page_content": doc.page_content, "metadata": doc.metadata})
            count += 1

        if rows:
            self._append_rows(rows)
        return count

    def similarity_search(self, fund_id: str, query: str, k: int = 8) -> List[Document]:
        self._ensure_loaded()
        docs = self._documents_by_fund.get(fund_id, [])
        if not docs:
            return []

        query_counts = self._tokenize(query)
        if not query_counts:
            return docs[:k]

        scored = []
        for doc in docs:
            doc_counts = self._tokenize(doc.page_content)
            overlap = sum(min(query_counts[t], doc_counts[t]) for t in query_counts)
            if overlap > 0:
                scored.append((overlap, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:k]]

    def total_documents(self) -> int:
        self._ensure_loaded()
        return sum(len(v) for v in self._documents_by_fund.values())

