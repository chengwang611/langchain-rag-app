"""Memory module — conversation history and RAG vector store.

Two memory systems:
1. ConversationMemory — chat history for multi-turn context
2. RAGMemory — document storage and semantic retrieval
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Memory — Conversation History
# ═══════════════════════════════════════════════════════════════════════════════

class ConversationMemory:
    """Persistent conversation history backed by SQLite.

    Stores (role, content, timestamp) per session_id.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(tempfile.gettempdir()) / "mini_claude_code_memory.db")
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)"
        )
        self._conn.commit()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Store a message in the conversation history."""
        self._conn.execute(
            "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.utcnow().isoformat()),
        )
        self._conn.commit()

    def get_history(self, session_id: str, limit: int = 50) -> List[dict]:
        """Retrieve recent conversation history for a session."""
        cursor = self._conn.execute(
            "SELECT role, content, created_at FROM conversations "
            "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        rows = cursor.fetchall()
        return [
            {"role": row[0], "content": row[1], "timestamp": row[2]}
            for row in reversed(rows)
        ]

    def clear_session(self, session_id: str) -> None:
        """Delete all history for a session."""
        self._conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        self._conn.commit()

    def format_for_llm(self, session_id: str, limit: int = 20) -> str:
        """Format history as a string for LLM context."""
        history = self.get_history(session_id, limit)
        if not history:
            return ""
        lines = ["<conversation_history>"]
        for msg in history:
            lines.append(f"  [{msg['role']}]: {msg['content'][:200]}")
        lines.append("</conversation_history>")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. RAG — Retrieval-Augmented Generation
# ═══════════════════════════════════════════════════════════════════════════════

class SimpleEmbeddings(Embeddings):
    """Minimal embeddings using character n-gram overlap for zero-dependency RAG.

    In production, replace with OpenAIEmbeddings or HuggingFaceEmbeddings.
    """

    def _ngrams(self, text: str, n: int = 3) -> set:
        return {text[i:i + n] for i in range(len(text) - n + 1)}

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        """Create a simple bag-of-ngrams vector."""
        ngrams = self._ngrams(text.lower())
        # Use a fixed vocabulary of 1000 hash buckets
        vec = [0.0] * 1000
        for ng in ngrams:
            vec[hash(ng) % 1000] += 1.0
        # Normalize
        mag = sum(v * v for v in vec) ** 0.5
        if mag > 0:
            vec = [v / mag for v in vec]
        return vec


class RAGMemory:
    """Document store with semantic retrieval.

    Stores documents with metadata and retrieves by similarity.
    """

    def __init__(self, embeddings: Optional[Embeddings] = None):
        self._embeddings = embeddings or SimpleEmbeddings()
        self._store = InMemoryVectorStore(self._embeddings)

    def add_document(self, content: str, metadata: Optional[dict] = None) -> None:
        """Add a document to the vector store."""
        doc = Document(page_content=content, metadata=metadata or {})
        self._store.add_documents([doc])

    def add_documents(self, documents: List[Document]) -> None:
        """Add multiple documents at once."""
        self._store.add_documents(documents)

    def search(self, query: str, k: int = 5) -> List[Document]:
        """Retrieve top-k documents similar to the query."""
        return self._store.similarity_search(query, k=k)

    def format_context(self, query: str, k: int = 5) -> str:
        """Retrieve and format documents as context string for LLM."""
        docs = self.search(query, k=k)
        if not docs:
            return ""
        lines = ["<retrieved_context>"]
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "unknown")
            lines.append(f"  [{i}] (source: {source}) {doc.page_content[:300]}")
        lines.append("</retrieved_context>")
        return "\n".join(lines)
