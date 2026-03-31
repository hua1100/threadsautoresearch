import json
from unittest.mock import patch, MagicMock

from orchestrator.threads_client import create_post, publish_post, get_user_profile, reply_to_post


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


def test_create_post_with_reply_to_id():
    """create_post sends reply_to_id in payload when provided."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "container_reply"}
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.threads_client.requests.post", return_value=mock_resp) as mock_post:
        result = create_post("Reply text", reply_to_id="media_parent")

    assert result == "container_reply"
    payload = mock_post.call_args[1]["json"]
    assert payload["reply_to_id"] == "media_parent"


def test_create_post_without_reply_to_id():
    """create_post does not include reply_to_id when not provided."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "container_normal"}
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.threads_client.requests.post", return_value=mock_resp) as mock_post:
        result = create_post("Normal post")

    assert result == "container_normal"
    payload = mock_post.call_args[1]["json"]
    assert "reply_to_id" not in payload


def test_reply_to_post_creates_and_publishes():
    """reply_to_post calls create_post with reply_to_id then publish_post."""
    with patch("orchestrator.threads_client.create_post", return_value="container_r") as mock_create, \
         patch("orchestrator.threads_client.publish_post", return_value="media_r") as mock_publish, \
         patch("orchestrator.threads_client.time.sleep"):
        result = reply_to_post("parent_123", "回覆文字")

    mock_create.assert_called_once_with("回覆文字", reply_to_id="parent_123")
    mock_publish.assert_called_once_with("container_r")
    assert result == "media_r"


def test_reply_to_post_returns_none_on_create_failure():
    """reply_to_post returns None if create_post fails."""
    with patch("orchestrator.threads_client.create_post", return_value=None):
        result = reply_to_post("parent_123", "回覆文字")

    assert result is None
