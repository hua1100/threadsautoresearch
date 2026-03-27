import json
from unittest.mock import patch, MagicMock

from orchestrator.threads_client import create_post, publish_post, get_user_profile


def test_create_post_returns_creation_id():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "container_123"}
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.threads_client.requests.post", return_value=mock_resp):
        result = create_post("Hello Threads!")
    assert result == "container_123"


def test_publish_post_returns_media_id():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "media_456"}
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.threads_client.requests.post", return_value=mock_resp):
        result = publish_post("container_123")
    assert result == "media_456"


def test_get_user_profile_returns_id_and_name():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "user_789", "username": "testuser", "threads_profile_picture_url": "https://example.com/pic.jpg"}
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.threads_client.requests.get", return_value=mock_resp):
        result = get_user_profile()
    assert result["id"] == "user_789"
    assert result["username"] == "testuser"
