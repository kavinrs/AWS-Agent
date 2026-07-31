from pathlib import Path
from typing import List

from .loader import download_company_pdfs_from_s3, load_company_pdfs
from .vector_store import build_faiss_index, load_faiss_index

LOCAL_COMPANY_DOCS_DIR = Path(__file__).resolve().parents[2] / "knowledge" / "company_docs"
DEFAULT_S3_COMPANY_DOCS_PREFIX = "company-documents/"


def get_or_create_retriever():
    """Load FAISS index. If it doesn't exist, download PDFs from S3 and build it."""

    faiss_index = load_faiss_index()

    if faiss_index is None:

        print("No FAISS index found.")
        print("Downloading PDFs from S3...")

        downloaded_count = download_company_pdfs_from_s3(
            bucket_name="aws-agent-bucket7946",
            prefix="company-documents/",
            download_dir=str(LOCAL_COMPANY_DOCS_DIR),
        )

        print(f"Downloaded {downloaded_count} PDFs.")

        docs = load_company_pdfs(str(LOCAL_COMPANY_DOCS_DIR))

        if not docs:
            print("No PDFs found after download.")
            return None

        print("Building FAISS index...")

        faiss_index = build_faiss_index(docs)

        print("FAISS index created.")

    return faiss_index.as_retriever(
        search_type="similarity",
        search_kwargs={"k":3},
    )


def rebuild_knowledge_base(
    s3_bucket: str,
    s3_prefix: str = DEFAULT_S3_COMPANY_DOCS_PREFIX,
):
    """Download the latest PDFs from S3 and rebuild the FAISS index."""

    if not s3_bucket:
        raise ValueError("S3 bucket is required.")

    downloaded_count = download_company_pdfs_from_s3(
        bucket_name="aws-agent-bucket7946",
        prefix="company-documents/",
        download_dir=str(LOCAL_COMPANY_DOCS_DIR),
    )

    if downloaded_count == 0:
        raise ValueError("No PDFs found in S3.")

    docs = load_company_pdfs(str(LOCAL_COMPANY_DOCS_DIR))
    print(f"Loaded {len(docs)} PDFs")

    if not docs:
        raise ValueError("No PDFs found after download.")

    faiss_index = build_faiss_index(docs)

    return faiss_index, downloaded_count


def retrieve_company_context(query: str) -> List[str]:
    """Retrieve the most relevant company document chunks."""

    retriever = get_or_create_retriever()

    if retriever is None:
        return []

    docs = retriever.invoke(query)

    return [
        f"Source: {doc.metadata.get('source', 'unknown')}\n{doc.page_content}"
        for doc in docs
    ]