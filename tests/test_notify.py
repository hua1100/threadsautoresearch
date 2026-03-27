from pathlib import Path
from unittest.mock import patch, MagicMock

from orchestrator.notify import send_notification


def test_send_notification_calls_telegram():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("orchestrator.notify.requests.post", return_value=mock_resp) as mock_post:
        with patch("orchestrator.notify.TELEGRAM_BOT_TOKEN", "bot123"):
            with patch("orchestrator.notify.TELEGRAM_CHAT_ID", "chat456"):
                send_notification("Test message")

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "bot123" in call_args[0][0]
    assert call_args[1]["json"]["chat_id"] == "chat456"
    assert call_args[1]["json"]["text"] == "Test message"


def test_send_notification_falls_back_to_print_when_no_token(capsys):
    with patch("orchestrator.notify.TELEGRAM_BOT_TOKEN", ""):
        send_notification("Fallback message")

    captured = capsys.readouterr()
    assert "Fallback message" in captured.out


def test_fetch_incoming_messages_returns_texts():
    from orchestrator.notify import fetch_incoming_messages

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ok": True,
        "result": [
            {
                "update_id": 100,
                "message": {
                    "chat": {"id": 456},
                    "text": "https://x.com/karpathy/status/123 這篇很讚"
                }
            },
            {
                "update_id": 101,
                "message": {
                    "chat": {"id": 456},
                    "text": "另一篇好內容"
                }
            },
        ]
    }

    with patch("orchestrator.notify.requests.get", return_value=mock_resp):
        with patch("orchestrator.notify.TELEGRAM_BOT_TOKEN", "bot123"):
            with patch("orchestrator.notify.TELEGRAM_CHAT_ID", "456"):
                with patch("orchestrator.notify.DATA_DIR", Path("/tmp/test_notify")):
                    messages = fetch_incoming_messages()

    assert len(messages) == 2
    assert "karpathy" in messages[0]
