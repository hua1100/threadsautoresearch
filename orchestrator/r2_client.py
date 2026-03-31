"""Cloudflare R2 client — upload PDFs and manage index via S3-compatible API."""
import json
import boto3
from botocore.exceptions import ClientError
from orchestrator.config import (
    R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME, WORKER_BASE_URL,
)


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def upload_pdf(local_path: str, keyword: str) -> str:
    """Upload a PDF to R2 and return the Worker download URL."""
    s3 = _get_s3_client()
    r2_key = f"lazy-packs/{keyword}.pdf"
    s3.upload_file(
        local_path,
        R2_BUCKET_NAME,
        r2_key,
        ExtraArgs={"ContentType": "application/pdf"},
    )
    return f"{WORKER_BASE_URL}/lazy-packs/{keyword}.pdf"


def update_index(keyword: str, title: str, url: str) -> None:
    """Add a new entry to the lazy-packs/index.json in R2."""
    s3 = _get_s3_client()
    index_key = "lazy-packs/index.json"

    try:
        resp = s3.get_object(Bucket=R2_BUCKET_NAME, Key=index_key)
        index = json.loads(resp["Body"].read().decode())
    except ClientError:
        index = []

    index = [e for e in index if e["keyword"] != keyword]

    index.append({
        "keyword": keyword,
        "title": title,
        "url": url,
    })

    s3.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=index_key,
        Body=json.dumps(index, ensure_ascii=False),
        ContentType="application/json",
    )
