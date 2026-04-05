import pytest
from unittest.mock import patch, MagicMock
from orchestrator.apify_client import run_actor, ApifyError


def test_run_actor_returns_items():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"text": "post 1", "author": "user1"},
        {"text": "post 2", "author": "user1"},
    ]

    with patch("orchestrator.apify_client.requests.post", return_value=mock_resp):
        items = run_actor("apify/fake-actor", {"key": "val"}, api_token="tok123")

    assert len(items) == 2
    assert items[0]["text"] == "post 1"


def test_run_actor_raises_on_http_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"

    with patch("orchestrator.apify_client.requests.post", return_value=mock_resp):
        with pytest.raises(ApifyError, match="400"):
            run_actor("apify/fake-actor", {}, api_token="tok123")


def test_run_actor_raises_on_timeout():
    import requests as req
    with patch("orchestrator.apify_client.requests.post", side_effect=req.Timeout):
        with pytest.raises(ApifyError, match="timeout"):
            run_actor("apify/fake-actor", {}, api_token="tok123", timeout=1)


def test_run_actor_returns_empty_list_on_empty_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []

    with patch("orchestrator.apify_client.requests.post", return_value=mock_resp):
        items = run_actor("apify/fake-actor", {}, api_token="tok123")

    assert items == []
