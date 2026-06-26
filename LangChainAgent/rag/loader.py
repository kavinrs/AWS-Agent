import os
from pathlib import Path
from langchain.document_loaders import PyPDFLoader


def load_company_pdfs(doc_dir: str) -> list[dict]:
    """Load PDF files from the company_docs folder."""
    docs = []
    folder = Path(doc_dir)
    for pdf_path in sorted(folder.glob("*.pdf")):
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        for page in pages:
            docs.append({
                "page_content": page.page_content,
                "metadata": {"source": str(pdf_path.name)},
            })
    return docs
