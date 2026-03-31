import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from orchestrator.lazy_pack_agent import generate_lazy_pack, parse_telegram_trigger


def test_parse_telegram_trigger_with_media_id():
    """Parses '懶人包 12345' into media_id."""
    result = parse_telegram_trigger("懶人包 12345")
    assert result == "12345"


def test_parse_telegram_trigger_with_permalink():
    """Parses '懶人包 https://threads.com/t/...' and extracts ID."""
    result = parse_telegram_trigger("懶人包 https://www.threads.net/@hualeee/post/abc123")
    assert result == "https://www.threads.net/@hualeee/post/abc123"


def test_parse_telegram_trigger_no_match():
    """Returns None for non-trigger messages."""
    assert parse_telegram_trigger("hello") is None
    assert parse_telegram_trigger("懶人包") is None


def test_generate_lazy_pack_full_flow(tmp_path, monkeypatch):
    """Full generation flow: Claude → PDF → R2 → Threads reply → record."""
    monkeypatch.setattr("orchestrator.lazy_pack_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.lazy_pack_agent.LAZY_PACKS_DIR", tmp_path / "lazy_packs")
    monkeypatch.setattr("orchestrator.lazy_pack_agent.LINE_ADD_FRIEND_URL", "https://line.me/test")
    monkeypatch.setattr("orchestrator.lazy_pack_agent.WORKER_BASE_URL", "https://worker.test")

    post = {
        "media_id": "media_123",
        "text": "AI Agent 很厲害",
        "dimensions": {"content_type": "工具分享", "source": "youtube/test"},
    }

    claude_response = json.dumps({
        "keyword": "ai-agent",
        "title": "AI Agent 完整攻略",
        "content": "# AI Agent 完整攻略\n\n## 核心概念\n很重要\n\n## 重點\n1. 第一點",
    }, ensure_ascii=False)

    mock_anthropic_resp = MagicMock()
    mock_anthropic_resp.content = [MagicMock(text=claude_response)]

    with patch("orchestrator.lazy_pack_agent.anthropic.Anthropic") as MockAnthropic, \
         patch("orchestrator.lazy_pack_agent.generate_pdf") as mock_pdf, \
         patch("orchestrator.lazy_pack_agent.upload_pdf", return_value="https://worker.test/lazy-packs/ai-agent.pdf") as mock_upload, \
         patch("orchestrator.lazy_pack_agent.update_index") as mock_index, \
         patch("orchestrator.lazy_pack_agent.threads_client") as mock_tc, \
         patch("orchestrator.lazy_pack_agent.send_notification") as mock_notify:

        MockAnthropic.return_value.messages.create.return_value = mock_anthropic_resp

        result = generate_lazy_pack(post)

    assert result["keyword"] == "ai-agent"
    assert result["title"] == "AI Agent 完整攻略"
    assert "worker.test" in result["pdf_url"]

    # Verify PDF was generated
    mock_pdf.assert_called_once()

    # Verify R2 upload
    mock_upload.assert_called_once_with(str(tmp_path / "lazy_packs" / "ai-agent.pdf"), "ai-agent")

    # Verify index updated
    mock_index.assert_called_once_with("ai-agent", "AI Agent 完整攻略", "https://worker.test/lazy-packs/ai-agent.pdf")

    # Verify Threads reply
    mock_tc.reply_to_post.assert_called_once()
    reply_text = mock_tc.reply_to_post.call_args[0][1]
    assert "ai-agent" in reply_text
    assert "line.me" in reply_text

    # Verify lazy_packs.json updated
    packs = json.loads((tmp_path / "lazy_packs.json").read_text())
    assert len(packs) == 1
    assert packs[0]["keyword"] == "ai-agent"

    # Verify Telegram notification
    mock_notify.assert_called_once()


def test_generate_lazy_pack_skips_duplicate(tmp_path, monkeypatch):
    """Skips generation if keyword already exists in lazy_packs.json."""
    monkeypatch.setattr("orchestrator.lazy_pack_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.lazy_pack_agent.LAZY_PACKS_DIR", tmp_path / "lazy_packs")

    # Pre-existing pack
    (tmp_path / "lazy_packs.json").write_text(json.dumps([
        {"media_id": "media_123", "keyword": "ai-agent", "pdf_url": "https://example.com"}
    ]))

    post = {"media_id": "media_123", "text": "test", "dimensions": {}}

    result = generate_lazy_pack(post)

    assert result is None  # Skipped
