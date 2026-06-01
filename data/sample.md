# Sample knowledge base

This file is indexed when you run `rag-ingest`. Replace or add files under `data/` (`.md`, `.txt`, `.pdf`).

## What is RAG?

Retrieval-Augmented Generation (RAG) combines a vector search step with an LLM. The app:

1. **Ingests** documents — load, split into chunks, embed, store in Chroma.
2. **Queries** — embed the question, retrieve relevant chunks, pass them to the model as context.

## Tips

- Keep chunks focused; tune `CHUNK_SIZE` and `CHUNK_OVERLAP` in `src/rag_app/config.py`.
- Add your own docs to `data/` before re-running ingest.
- Use a fresh collection name or delete `.chroma/` when switching corpora.
