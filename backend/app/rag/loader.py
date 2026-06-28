import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from langchain.document_loaders import PyPDFLoader


def download_company_pdfs_from_s3(bucket_name: str, prefix: str, download_dir: str) -> int:
    """Download PDFs from an S3 prefix into the local company_docs folder."""
    folder = Path(download_dir)
    folder.mkdir(parents=True, exist_ok=True)

    prefix = prefix.lstrip("/").rstrip("/") + "/"
    client = boto3.client("s3")

    downloaded_names = set()
    continuation_token = None

    while True:
        list_kwargs = {"Bucket": bucket_name, "Prefix": prefix}
        if continuation_token:
            list_kwargs["ContinuationToken"] = continuation_token

        try:
            response = client.list_objects_v2(**list_kwargs)
        except ClientError as exc:
            raise RuntimeError(f"S3 list/download failed: {exc}") from exc

        for obj in response.get("Contents", []):
            key = obj["Key"]
            if not key.lower().endswith(".pdf"):
                continue

            relative_key = key[len(prefix) :]
            if not relative_key or relative_key.endswith("/"):
                continue

            filename = Path(relative_key).name
            if not filename:
                continue

            download_path = folder / filename
            try:
                client.download_file(bucket_name, key, str(download_path))
            except ClientError as exc:
                raise RuntimeError(f"Failed to download {key} from S3: {exc}") from exc

            downloaded_names.add(filename)

        if not response.get("IsTruncated"):
            break
        continuation_token = response.get("NextContinuationToken")

    existing_files = {pdf.name for pdf in folder.glob("*.pdf")}
    for stale in existing_files - downloaded_names:
        try:
            (folder / stale).unlink()
        except OSError:
            pass

    return len(downloaded_names)


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
