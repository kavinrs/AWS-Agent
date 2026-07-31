from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from langchain.vectorstores import FAISS
import boto3



INDEX_FILE = Path(__file__).parent / "company_faiss.index"

bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1"      
)

embeddings = BedrockEmbeddings(
    client=bedrock_client,
    model_id="amazon.titan-embed-text-v2:0"
)

import logging

logger = logging.getLogger(__name__)
print("Building FAISS index...")

def build_faiss_index(documents: list[dict]) -> FAISS:
    """Split documents, generate embeddings, and build a FAISS index."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = []
    metadatas = []

    for doc in documents:
        raw_text = doc["page_content"]
        for chunk in text_splitter.split_text(raw_text):
            texts.append(chunk)
            metadatas.append(doc["metadata"])


    logger.info("Building FAISS index...")

    faiss_index = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
    logger.info(f"FAISS index created with {len(texts)} chunks.")

    faiss_index.save_local(str(INDEX_FILE))
    logger.info(f"FAISS index saved at {INDEX_FILE}")
    print("FAISS index saved successfully.")
    return faiss_index


def load_faiss_index() -> FAISS | None:
    """Load the FAISS index from disk if it exists."""
    if INDEX_FILE.exists():
        logger.info("Loading existing FAISS index...")

        index = FAISS.load_local(
            str(INDEX_FILE),
            embeddings,
            allow_dangerous_deserialization=True,
        )

        logger.info(f"Loaded FAISS index with {index.index.ntotal} vectors.")

        return index

    logger.warning("FAISS index not found.")
    return None
