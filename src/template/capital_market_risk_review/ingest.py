"""
ingest.py — Document loading and chunking.

EXTEND:
- Swap InMemoryVectorStore for pgvector / Chroma / Azure AI Search
- Add metadata extraction (doc type, date, author, desk)
- Add PDF/Word/Excel loaders (pypdf, python-docx, openpyxl)
- Add OCR for scanned documents (pytesseract, Azure Form Recognizer)
- Add deduplication logic with LangChain RecordManager
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


def ingest_node(state: ReviewState) -> ReviewState:
    """
    Split raw documents into overlapping chunks for retrieval.

    EXTEND:
    - Accept file paths and use PyPDFLoader / WebBaseLoader
    - Tag chunks with desk, date, document_type metadata
    - Persist to a durable vector store (pgvector, Chroma, Azure AI Search)
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    # Build LangChain Document objects from raw text
    # EXTEND: replace with loader.load() when reading files
    docs = [
        Document(
            page_content=text,
            metadata={
                "source_id": f"doc_{i}",
                # EXTEND: "desk": "...", "date": "...", "doc_type": "..."
            },
        )
        for i, text in enumerate(state["raw_docs"])
    ]

    chunks = splitter.split_documents(docs)
    return {"chunks": chunks}


def retrieve_node(state: ReviewState) -> ReviewState:
    """
    Embed chunks and retrieve top-k most relevant to the query.

    EXTEND:
    - Use a persistent vector store instead of in-memory
    - Add hybrid search (dense + BM25 sparse)
    - Add re-ranking (Cohere Rerank, cross-encoder)
    - Add multi-query retrieval for broader coverage
    """
    # EXTEND: replace with persistent store loaded from connection string
    vector_store = InMemoryVectorStore.from_documents(
        state["chunks"],
        embeddings,
    )

    # EXTEND: increase k for larger document sets
    retrieved = vector_store.similarity_search(state["query"], k=8)
    return {"retrieved": retrieved}

