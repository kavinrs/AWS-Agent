from typing import List
from .loader import load_company_pdfs
from .vector_store import build_faiss_index, load_faiss_index, INDEX_FILE


def get_or_create_retriever(openai_api_key: str):
    """Load or build the FAISS index and return a retriever."""
    faiss_index = load_faiss_index(openai_api_key)
    if faiss_index is None or not INDEX_FILE.exists():
        docs = load_company_pdfs("knowledge/company_docs")
        if not docs:
            return None
        faiss_index = build_faiss_index(docs, openai_api_key)

    # Return a simple similarity retriever that returns the top 3 matches.
    return faiss_index.as_retriever(search_type="similarity", search_kwargs={"k": 3})


def retrieve_company_context(query: str, openai_api_key: str) -> List[str]:
    """Return top 3 relevant document chunks for the provided query."""
    retriever = get_or_create_retriever(openai_api_key)
    if retriever is None:
        return []

    docs = retriever.get_relevant_documents(query)
    return [
        f"Source: {doc.metadata.get('source', 'unknown')}\n{doc.page_content}"
        for doc in docs
    ]
