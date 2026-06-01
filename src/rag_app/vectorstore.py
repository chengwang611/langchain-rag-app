from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_app import config


def get_embeddings() -> OpenAIEmbeddings:
    config.require_openai_key()
    return OpenAIEmbeddings(model=config.OPENAI_EMBEDDING_MODEL)


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        length_function=len,
    )


def get_vectorstore() -> Chroma:
    return Chroma(
        collection_name=config.COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(config.CHROMA_DIR),
    )


def ingest_documents(documents: list[Document]) -> int:
    """Split, embed, and persist documents. Returns chunk count."""
    if not documents:
        raise ValueError("No documents to ingest. Add files under data/.")

    splitter = get_text_splitter()
    chunks = splitter.split_documents(documents)

    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        collection_name=config.COLLECTION_NAME,
        persist_directory=str(config.CHROMA_DIR),
    )
    return len(chunks)


def get_retriever():
    return get_vectorstore().as_retriever(search_kwargs={"k": config.RETRIEVAL_K})
