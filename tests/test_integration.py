"""
Integration test: verifies the full loop runs end-to-end with mocks.
"""
from unittest.mock import patch, MagicMock
from orchestrator.main import run


def test_full_loop_first_run():
    """First run: no existing posts, no harvest data, generates and deploys."""

    mock_ai_response = MagicMock()
    mock_ai_response.content = [MagicMock(text='[{"text": "Test post", "dimensions": {"content_type": "工具分享", "hook_style": "送資源型", "format": "短句", "tone": "輕鬆口語", "cta": "無CTA", "source": "test"}, "hypothesis": "first test"}]')]

    with patch("orchestrator.main.get_follower_count", return_value=44), \
         patch("orchestrator.sources.youtube.requests.get") as mock_yt, \
         patch("orchestrator.harvest.harvest_browser", return_value={}), \
         patch("orchestrator.harvest.harvest_api", return_value={}), \
         patch("orchestrator.threads_client.post_text", return_value="media_1") as mock_post_text, \
         patch("orchestrator.notify.requests.get") as mock_tg_get, \
         patch("orchestrator.main.send_notification") as mock_notify, \
         patch("orchestrator.generate.anthropic") as mock_anthropic_gen, \
         patch("orchestrator.deploy.write_json") as mock_write_json, \
         patch("orchestrator.deploy.read_json", return_value=[]), \
         patch("orchestrator.harvest.read_json", return_value=[]):

        # YouTube returns no videos
        mock_yt_resp = MagicMock()
        mock_yt_resp.status_code = 200
        mock_yt_resp.json.return_value = {"items": []}
        mock_yt.return_value = mock_yt_resp

        # Telegram getUpdates returns no messages
        mock_tg_get_resp = MagicMock()
        mock_tg_get_resp.status_code = 200
        mock_tg_get_resp.json.return_value = {"ok": True, "result": []}
        mock_tg_get.return_value = mock_tg_get_resp

        # AI generate
        mock_gen_client = MagicMock()
        mock_gen_client.messages.create.return_value = mock_ai_response
        mock_anthropic_gen.Anthropic.return_value = mock_gen_client

        run()

        # Verify Threads post_text was called (one call per post)
        assert mock_post_text.call_count >= 1
        # Verify notification was sent
        mock_notify.assert_called()
