"""
ingest.py — Document loading, chunking, embedding, persistence, and retrieval.

Two-pipeline design
-------------------
INGESTION PIPELINE  (runs hourly / daily as a batch job)
  ingest_node  →  embed_and_persist_node

  - Loads raw documents for a given fund_id
  - Splits into overlapping chunks
  - Tags every chunk with fund_id + report_date metadata
  - Embeds and writes chunks to the persistent vector store
  - Supports incremental runs: new reports are appended, not re-embedded


REVIEW PIPELINE  (runs at query / review time)
  retrieve_node  →  analyze_node  →  ...

  - Loads the persisted vector store
  - Filters strictly by fund_id so Fund A's documents never pollute Fund B
  - Returns top-k semantically relevant chunks for the query

EXTEND:
- Swap _FUND_DOCUMENT_STORE for PGVector / Chroma / Azure AI Search
- Add LangChain RecordManager for idempotent deduplication across runs
- Add PDF/Word/Excel loaders (pypdf, python-docx, openpyxl)
- Add OCR for scanned documents (pytesseract, Azure Form Recognizer)
- Add metadata extraction: author, desk, document_type, page_number
- Add hybrid search: dense vector + BM25 sparse (LangChain EnsembleRetriever)
- Add re-ranking: Cohere Rerank or cross-encoder after retrieval
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.template.capital_market_risk_review.models import ReviewState


# ── Splitter config ──────────────────────────────────────────────────────────
# EXTEND: tune chunk_size / chunk_overlap per document type
#         e.g. larger chunks for narrative reports, smaller for tables
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# ── Embeddings ───────────────────────────────────────────────────────────────
# EXTEND: swap to AzureOpenAIEmbeddings, HuggingFaceEmbeddings, etc.
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# ── Demo-mode persistent store ────────────────────────────────────────────────
# Simulates a persistent vector store within a single process.
# Keyed by fund_id so each fund's documents are fully isolated.
#
# EXTEND: replace with pgvector:
#   from langchain_postgres.vectorstores import PGVector
#   vector_store = PGVector(
#       connection_string=os.environ["PGVECTOR_CONNECTION_STRING"],
#       embedding_function=embeddings,
#       collection_name="fund_risk_docs",
#   )
#   vector_store.add_documents(chunks)                    # ingest
#   vector_store.similarity_search(query, k=8,            # retrieve
#       filter={"fund_id": fund_id})
_FUND_DOCUMENT_STORE: dict[str, list[Document]] = {}


# ── Ingestion pipeline nodes ─────────────────────────────────────────────────

def ingest_node(state: ReviewState) -> ReviewState:
    """
    Split raw documents into overlapping chunks and tag each chunk
    with fund_id + report_date metadata.

    Part of the INGESTION PIPELINE (hourly / daily batch job).

    EXTEND:
    - Accept file paths and use PyPDFLoader / WebBaseLoader / AzureBlobLoader
    - Extract richer metadata: author, desk, doc_type, page_number, currency
    - Add document-level deduplication before splitting
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    fund_id = state["fund_id"]
    report_date = state.get("report_date") or "unknown"
    source_files = state.get("source_files", [])

    # Build LangChain Document objects from raw text
    # EXTEND: replace with loader.load() when reading real files
    docs = [
        Document(
            page_content=text,
            metadata={
                "source_id": f"{fund_id}_doc_{i}",
                "fund_id": fund_id,                    # ← scopes retrieval per fund
                "report_date": report_date,            # ← supports time-based filtering
                "source_file": source_files[i] if i < len(source_files) else "unknown",
                # EXTEND: "desk": "...", "doc_type": "...", "page_number": ...
            },
        )
        for i, text in enumerate(state["raw_docs"])
    ]

    chunks = splitter.split_documents(docs)
    return {"chunks": chunks}


def embed_and_persist_node(state: ReviewState) -> ReviewState:
    """
    Embed document chunks and persist them to the vector store, keyed by fund_id.

    - New reports are APPENDED to the existing fund store (supports hourly runs).
    - The same fund can have documents from multiple ingestion runs without
      losing historical context.

    Part of the INGESTION PIPELINE (hourly / daily batch job).

    EXTEND:
    - Replace _FUND_DOCUMENT_STORE with PGVector.add_documents() for real persistence
    - Add LangChain RecordManager for idempotent deduplication:
        from langchain.indexes import SQLRecordManager, index
        record_manager = SQLRecordManager(f"pgvector/{fund_id}", db_url=...)
        index(chunks, record_manager, vector_store, cleanup="incremental")
    - Add report_date TTL: purge chunks older than N days to control index size
    - Emit ingestion metrics: chunk count, embedding latency, fund_id
    """
    fund_id = state["fund_id"]
    chunks = state["chunks"]

    # Append new chunks to the fund's persistent store
    # EXTEND: replace with vector_store.add_documents(chunks) for pgvector
    existing = _FUND_DOCUMENT_STORE.get(fund_id, [])
    _FUND_DOCUMENT_STORE[fund_id] = existing + chunks

    total = len(_FUND_DOCUMENT_STORE[fund_id])
    print(
        f"[embed_and_persist] fund_id={fund_id} | "
        f"+{len(chunks)} new chunks | total={total} chunks in store"
    )

    return {}


# ── Review pipeline node ─────────────────────────────────────────────────────

def retrieve_node(state: ReviewState) -> ReviewState:
    """
    Retrieve top-k chunks for the given fund_id from the persistent store.

    - Filters strictly by fund_id — documents from other funds are never returned.
    - Builds a temporary similarity-search index from only this fund's chunks.

    Part of the REVIEW PIPELINE (runs at query / review time).

    EXTEND:
    - Replace with PGVector.similarity_search(query, k=8, filter={"fund_id": fund_id})
    - Add hybrid search: EnsembleRetriever(retrievers=[dense, bm25], weights=[0.7, 0.3])
    - Add re-ranking: CohereRerank or CrossEncoderReranker after initial retrieval
    - Add multi-query retrieval: generate N query variants for broader coverage
    - Add report_date filter: restrict to last N days for time-sensitive reviews
    """
    fund_id = state["fund_id"]
    query = state["query"]

    fund_chunks = _FUND_DOCUMENT_STORE.get(fund_id, [])

    if not fund_chunks:
        print(f"[retrieve] WARNING: No documents found for fund_id={fund_id}. "
              f"Run the ingestion pipeline first.")
        return {"retrieved": []}

    print(f"[retrieve] fund_id={fund_id} | searching {len(fund_chunks)} chunks")

    # Build ephemeral search index scoped to this fund's persisted chunks
    # EXTEND: replace with persistent PGVector store + filter={"fund_id": fund_id}
    vector_store = InMemoryVectorStore.from_documents(fund_chunks, embeddings)

    # EXTEND: increase k for larger document sets
    retrieved = vector_store.similarity_search(query, k=8)
    return {"retrieved": retrieved}
