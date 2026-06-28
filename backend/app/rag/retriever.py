from pathlib import Path
from typing import List

from .loader import download_company_pdfs_from_s3, load_company_pdfs
from .vector_store import build_faiss_index, load_faiss_index, INDEX_FILE

LOCAL_COMPANY_DOCS_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "company_docs"
DEFAULT_S3_COMPANY_DOCS_PREFIX = "company-documents/"


def get_or_create_retriever(openai_api_key: str):
    """Load or build the FAISS index and return a retriever."""
    faiss_index = load_faiss_index(openai_api_key)
    if faiss_index is None or not INDEX_FILE.exists():
        docs = load_company_pdfs(str(LOCAL_COMPANY_DOCS_DIR))
        if not docs:
            return None
        faiss_index = build_faiss_index(docs, openai_api_key)

    return faiss_index.as_retriever(search_type="similarity", search_kwargs={"k": 3})


def rebuild_knowledge_base(openai_api_key: str, s3_bucket: str, s3_prefix: str = DEFAULT_S3_COMPANY_DOCS_PREFIX):
    """Download PDFs from S3 and rebuild the FAISS index."""
    if not s3_bucket:
        raise ValueError("S3 bucket is required to rebuild the knowledge base.")

    downloaded_count = download_company_pdfs_from_s3(
        bucket_name=s3_bucket,
        prefix=s3_prefix,
        download_dir=str(LOCAL_COMPANY_DOCS_DIR),
    )

    if downloaded_count == 0:
        raise ValueError("No PDFs were found in S3 at the provided bucket/prefix.")

    docs = load_company_pdfs(str(LOCAL_COMPANY_DOCS_DIR))
    if not docs:
        raise ValueError("Failed to load documents after S3 download.")

    faiss_index = build_faiss_index(docs, openai_api_key)
    return faiss_index, downloaded_count


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
