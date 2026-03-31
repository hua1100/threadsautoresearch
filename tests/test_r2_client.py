import json
import pytest
from unittest.mock import patch, MagicMock
from orchestrator.r2_client import upload_pdf, update_index


def test_upload_pdf_calls_s3_put():
    """upload_pdf uploads file to R2 via S3 API."""
    mock_s3 = MagicMock()

    with patch("orchestrator.r2_client._get_s3_client", return_value=mock_s3):
        url = upload_pdf("/tmp/test.pdf", "ai-agent")

    mock_s3.upload_file.assert_called_once_with(
        "/tmp/test.pdf",
        "lazy-packs",
        "lazy-packs/ai-agent.pdf",
        ExtraArgs={"ContentType": "application/pdf"},
    )
    assert "ai-agent.pdf" in url


def test_upload_pdf_returns_worker_url():
    """upload_pdf returns the Worker download URL."""
    mock_s3 = MagicMock()

    with patch("orchestrator.r2_client._get_s3_client", return_value=mock_s3), \
         patch("orchestrator.r2_client.WORKER_BASE_URL", "https://worker.example.com"):
        url = upload_pdf("/tmp/test.pdf", "ai-agent")

    assert url == "https://worker.example.com/lazy-packs/ai-agent.pdf"


def test_update_index_adds_new_entry():
    """update_index downloads index.json, appends entry, re-uploads."""
    mock_s3 = MagicMock()
    existing_body = MagicMock()
    existing_body.read.return_value = json.dumps([
        {"keyword": "old", "title": "Old Pack", "url": "https://example.com/old.pdf"}
    ]).encode()
    mock_s3.get_object.return_value = {"Body": existing_body}

    with patch("orchestrator.r2_client._get_s3_client", return_value=mock_s3):
        update_index("ai-agent", "AI Agent 攻略", "https://example.com/ai-agent.pdf")

    put_call = mock_s3.put_object.call_args
    body = json.loads(put_call[1]["Body"])
    assert len(body) == 2
    assert body[1]["keyword"] == "ai-agent"
    assert body[1]["title"] == "AI Agent 攻略"


def test_update_index_creates_new_when_empty():
    """update_index creates index.json when it doesn't exist."""
    mock_s3 = MagicMock()
    from botocore.exceptions import ClientError
    mock_s3.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey"}}, "GetObject"
    )

    with patch("orchestrator.r2_client._get_s3_client", return_value=mock_s3):
        update_index("first", "First Pack", "https://example.com/first.pdf")

    put_call = mock_s3.put_object.call_args
    body = json.loads(put_call[1]["Body"])
    assert len(body) == 1
    assert body[0]["keyword"] == "first"
