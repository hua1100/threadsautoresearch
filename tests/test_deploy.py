import json
from unittest.mock import patch, MagicMock
from orchestrator.deploy import deploy, schedule_posts


def test_schedule_posts_distributes_times():
    posts = [
        {"text": "Post 1", "dimensions": {}, "hypothesis": "h1"},
        {"text": "Post 2", "dimensions": {}, "hypothesis": "h2"},
        {"text": "Post 3", "dimensions": {}, "hypothesis": "h3"},
    ]
    scheduled = schedule_posts(posts, start_hour=9, interval_hours=2)
    assert len(scheduled) == 3
    assert scheduled[0]["scheduled_hour"] == 9
    assert scheduled[1]["scheduled_hour"] == 11
    assert scheduled[2]["scheduled_hour"] == 13


def test_deploy_publishes_and_records():
    posts = [
        {"text": "Hello Threads", "dimensions": {"content_type": "工具分享"}, "hypothesis": "test"},
    ]

    with patch("orchestrator.deploy.threads_client") as mock_tc:
        mock_tc.post_text.return_value = "media_123"
        with patch("orchestrator.deploy.read_json", return_value=[]):
            with patch("orchestrator.deploy.write_json") as mock_write:
                with patch("orchestrator.deploy.sanitize_post_text", side_effect=lambda x: x):
                    result = deploy(posts)

    assert len(result) == 1
    assert result[0]["media_id"] == "media_123"
    mock_write.assert_called_once()
