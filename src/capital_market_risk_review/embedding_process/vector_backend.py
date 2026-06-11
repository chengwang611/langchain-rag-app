"""Vector store backend abstraction for the embedding process.

Phase 1:
- InMemoryFundVectorStore is used for local validation and rapid iteration.

Future:
- PGVectorFundStore can be implemented without changing the Spark pipeline
  orchestration logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Protocol

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings


class VectorStoreBackend(Protocol):
    """Contract used by the Spark embedding pipeline.

    Any backend implementation must support ingest and per-fund retrieval.

    EXTEND:
    - Add delete_by_fund_id() for retention policies.
    - Add upsert semantics keyed by chunk_id to support idempotent ingestion.
    - Add count_by_fund_id() for monitoring dashboards.
    """

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
    """Production backend placeholder.

    This class intentionally leaves implementation as explicit TODO so migration
    path is clear while phase 1 stays in-memory.

    EXTEND suggestion (minimal implementation path):
    1) Install langchain-postgres + psycopg.
    2) Initialize PGVector with collection_name="fund_risk_docs".
    3) In add_documents(), call vector_store.add_documents(documents).
    4) In similarity_search(), call vector_store.similarity_search(
         query, k=k, filter={"fund_id": fund_id}
       ).
    5) Add idempotency with RecordManager or deterministic chunk_id metadata.
    """

    connection_string: str
    collection_name: str = "fund_risk_docs"

    def add_documents(self, documents: Iterable[Document]) -> int:
        raise NotImplementedError("PGVector backend not implemented in phase 1.")

    def similarity_search(self, fund_id: str, query: str, k: int = 8) -> List[Document]:
        raise NotImplementedError("PGVector backend not implemented in phase 1.")

    def total_documents(self) -> int:
        raise NotImplementedError("PGVector backend not implemented in phase 1.")

