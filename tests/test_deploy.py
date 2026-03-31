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


def test_deploy_replies_with_newsletter_link_on_cta():
    """When cta is 電子報CTA and newsletter is published, deploy auto-replies."""
    posts = [
        {
            "text": "AI 深度分析",
            "dimensions": {"cta": "電子報CTA"},
            "hypothesis": "test CTA",
        },
    ]
    newsletter_status = {"status": "published", "url": "https://hualeee.substack.com/p/test"}

    with patch("orchestrator.deploy.threads_client") as mock_tc, \
         patch("orchestrator.deploy.read_json") as mock_read, \
         patch("orchestrator.deploy.write_json"), \
         patch("orchestrator.deploy.sanitize_post_text", side_effect=lambda x: x):

        mock_tc.post_text.return_value = "media_cta"
        mock_tc.get_post_permalink.return_value = "https://threads.com/t/123"
        # First call: posts.json, second call: newsletter_status.json
        mock_read.side_effect = [[], newsletter_status]

        result = deploy(posts)

    mock_tc.reply_to_post.assert_called_once_with(
        "media_cta",
        "完整深度分析在這裡 👉 https://hualeee.substack.com/p/test",
    )


def test_deploy_skips_reply_when_newsletter_not_published():
    """When newsletter is not published, deploy does not reply."""
    posts = [
        {
            "text": "AI 深度分析",
            "dimensions": {"cta": "電子報CTA"},
            "hypothesis": "test CTA",
        },
    ]
    newsletter_status = {"status": "draft", "url": ""}

    with patch("orchestrator.deploy.threads_client") as mock_tc, \
         patch("orchestrator.deploy.read_json") as mock_read, \
         patch("orchestrator.deploy.write_json"), \
         patch("orchestrator.deploy.sanitize_post_text", side_effect=lambda x: x):

        mock_tc.post_text.return_value = "media_cta"
        mock_tc.get_post_permalink.return_value = "https://threads.com/t/123"
        mock_read.side_effect = [[], newsletter_status]

        deploy(posts)

    mock_tc.reply_to_post.assert_not_called()


def test_deploy_skips_reply_when_cta_is_not_newsletter():
    """When cta is not 電子報CTA, deploy does not attempt reply."""
    posts = [
        {
            "text": "Hello",
            "dimensions": {"cta": "留言互動"},
            "hypothesis": "test",
        },
    ]

    with patch("orchestrator.deploy.threads_client") as mock_tc, \
         patch("orchestrator.deploy.read_json", return_value=[]), \
         patch("orchestrator.deploy.write_json"), \
         patch("orchestrator.deploy.sanitize_post_text", side_effect=lambda x: x):

        mock_tc.post_text.return_value = "media_normal"
        mock_tc.get_post_permalink.return_value = "https://threads.com/t/456"

        deploy(posts)

    mock_tc.reply_to_post.assert_not_called()
