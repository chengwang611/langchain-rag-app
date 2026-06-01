from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from rag_app import config
from rag_app.vectorstore import get_retriever


def format_docs(docs) -> str:
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def build_rag_chain():
    config.require_openai_key()
    retriever = get_retriever()
    llm = ChatOpenAI(model=config.OPENAI_MODEL, temperature=0)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You answer questions using only the provided context. "
                "If the context is insufficient, say you don't know. "
                "Cite relevant details from the context.",
            ),
            ("human", "Context:\n{context}\n\nQuestion: {question}"),
        ]
    )

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain
