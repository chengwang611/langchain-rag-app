import argparse

from rag_app import config
from rag_app.chain import build_rag_chain
from rag_app.loaders import load_documents
from rag_app.vectorstore import ingest_documents


def ingest_main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into Chroma")
    parser.parse_args()
    docs = load_documents(config.DATA_DIR)
    count = ingest_documents(docs)
    print(f"Ingested {len(docs)} file(s) -> {count} chunk(s) in {config.CHROMA_DIR}")


def query_main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question against the RAG index")
    parser.add_argument("question", nargs="?", help="Question to ask")
    parser.add_argument("-i", "--interactive", action="store_true", help="REPL mode")
    args = parser.parse_args()

    chain = build_rag_chain()

    def ask(q: str) -> None:
        answer = chain.invoke(q)
        print(answer)

    if args.interactive:
        print("RAG query (empty line to exit)")
        while True:
            try:
                q = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not q:
                break
            ask(q)
        return

    if not args.question:
        parser.error("Provide a question or use --interactive")
    ask(args.question)
