from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document


def load_documents(data_dir: Path) -> list[Document]:
    """Load supported files from data_dir recursively."""
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    docs: list[Document] = []
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in {".md", ".txt"}:
            loader = TextLoader(str(path), encoding="utf-8")
            docs.extend(loader.load())
        elif suffix == ".pdf":
            docs.extend(PyPDFLoader(str(path)).load())
    return docs
