# LangChain RAG Starter

A minimal Python starter for **Retrieval-Augmented Generation (RAG)** using [LangChain](https://python.langchain.com/), **OpenAI** (embeddings + chat), and **Chroma** (local vector store).

## Quick start

```bash
cd ~/Projects/langchain-rag-app
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# Edit .env and set OPENAI_API_KEY

# Index sample docs in data/
rag-ingest

# Single question
rag-query "What is RAG?"

# Interactive REPL
rag-query -i
```

## Project layout

```
data/              # Put .md, .txt, .pdf files here
src/rag_app/
  config.py        # Env-based settings
  loaders.py       # Document loading
  vectorstore.py   # Chunking, Chroma ingest/retrieve
  chain.py         # RAG LCEL chain
  cli.py           # rag-ingest / rag-query entrypoints
.chroma/           # Local vector DB (gitignored)
```

## Workflow

1. **Add documents** under `data/` (or set `DATA_DIR` in `.env`).
2. **Ingest**: `rag-ingest` splits text, embeds chunks, writes to Chroma.
3. **Query**: `rag-query` retrieves top-k chunks and answers with the LLM.

Re-run ingest after changing files. Delete `.chroma/` or change `COLLECTION_NAME` for a clean index.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embeddings |
| `CHUNK_SIZE` | `1000` | Characters per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `RETRIEVAL_K` | `4` | Chunks retrieved per query |
| `COLLECTION_NAME` | `rag_docs` | Chroma collection |

## Next steps

- Add a **FastAPI** or **Streamlit** UI around `build_rag_chain()`.
- Swap **OpenAI** for local models (Ollama + `langchain-ollama`).
- Use **metadata filters** on the retriever for multi-tenant or tagged docs.
- Evaluate with **RAGAS** or LangSmith tracing.

## License

MIT (use freely for your projects).
