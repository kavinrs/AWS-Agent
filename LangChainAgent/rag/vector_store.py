import json
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS


INDEX_FILE = Path(__file__).parent / "company_faiss.index"


def build_faiss_index(documents: list[dict], openai_api_key: str) -> FAISS:
    """Split documents, generate embeddings, and build a FAISS index."""
    # Split text into manageable chunks for better retrieval quality.
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = []
    metadatas = []

    for doc in documents:
        raw_text = doc["page_content"]
        for chunk in text_splitter.split_text(raw_text):
            texts.append(chunk)
            metadatas.append(doc["metadata"])

    # Use OpenAI embeddings to convert text chunks into vectors.
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    faiss_index = FAISS.from_texts(texts, embeddings, metadatas=metadatas)

    # Save the index locally so it can be reused on app startup.
    faiss_index.save_local(str(INDEX_FILE))
    return faiss_index


def load_faiss_index(openai_api_key: str) -> FAISS | None:
    """Load the FAISS index from disk if it exists."""
    if INDEX_FILE.exists():
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        # This index is created locally from trusted company PDFs.
        # Allowing deserialization is safe in this controlled project context.
        return FAISS.load_local(
            str(INDEX_FILE),
            embeddings,
            allow_dangerous_deserialization=True,
        )
    return None
