import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from orchestrator import newsletter_agent


def test_run_saves_draft_file():
    from orchestrator.newsletter_agent import run

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# 電子報標題\n\n這是草稿內容")]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        (data_dir / "experiments.json").write_text("[]")
        (prompts_dir / "strategy.md").write_text("# 策略\n## 目標\n導流電子報")
        (prompts_dir / "swipe_file.md").write_text("# Swipe File\n範例貼文")

        with patch("orchestrator.newsletter_agent.anthropic") as mock_anthropic, \
             patch("orchestrator.utils.DATA_DIR", data_dir), \
             patch("orchestrator.newsletter_agent.PROMPTS_DIR", prompts_dir), \
             patch("orchestrator.newsletter_agent.DRAFTS_DIR", drafts_dir), \
             patch("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "test@test.com"), \
             patch("orchestrator.newsletter_agent.subprocess.run") as mock_run:

            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.Anthropic.return_value = mock_client
            mock_run.return_value = MagicMock(returncode=0)

            run()

        draft_files = list(drafts_dir.glob("newsletter_*.md"))
        assert len(draft_files) == 1
        content = draft_files[0].read_text(encoding="utf-8")
        assert "電子報標題" in content


def test_run_sends_email():
    from orchestrator.newsletter_agent import run

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# 電子報\n草稿內容")]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        (data_dir / "experiments.json").write_text("[]")
        (prompts_dir / "strategy.md").write_text("# 策略")
        (prompts_dir / "swipe_file.md").write_text("")

        with patch("orchestrator.newsletter_agent.anthropic") as mock_anthropic, \
             patch("orchestrator.utils.DATA_DIR", data_dir), \
             patch("orchestrator.newsletter_agent.PROMPTS_DIR", prompts_dir), \
             patch("orchestrator.newsletter_agent.DRAFTS_DIR", drafts_dir), \
             patch("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "test@test.com"), \
             patch("orchestrator.newsletter_agent.subprocess.run") as mock_run:

            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.Anthropic.return_value = mock_client
            mock_run.return_value = MagicMock(returncode=0)

            run()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0][0] == "mail"
        assert "test@test.com" in call_args[0][0]


def test_newsletter_email_includes_funnel_summary(tmp_path, monkeypatch):
    """Newsletter email body includes funnel summary when substack_metrics.json exists."""
    monkeypatch.setattr("orchestrator.newsletter_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr("orchestrator.newsletter_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "test@example.com")

    # Create fake substack_metrics.json with 2 snapshots (to test delta)
    metrics = [
        {"date": "2026-03-24", "subscribers": 25, "open_rate": 35.0, "total_email": 20, "growth_sources": []},
        {"date": "2026-03-31", "subscribers": 27, "open_rate": 38.5, "total_email": 23, "growth_sources": [{"source": "substack", "value": 12}]},
    ]
    (tmp_path / "substack_metrics.json").write_text(json.dumps(metrics))

    with patch("orchestrator.newsletter_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.newsletter_agent.anthropic.Anthropic") as MockAnthropic, \
         patch("orchestrator.newsletter_agent.subprocess.run") as mock_run:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="電子報草稿內容")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp
        mock_run.return_value = MagicMock(returncode=0)

        newsletter_agent.run()

    # Check email body contains funnel info
    call_args = mock_run.call_args
    email_body = call_args[1]["input"].decode("utf-8")
    assert "訂閱數" in email_body
    assert "27" in email_body
    assert "+2" in email_body  # delta from 25 → 27


def test_newsletter_email_no_delta_on_first_snapshot(tmp_path, monkeypatch):
    """When only one snapshot exists, delta shows 首次記錄."""
    monkeypatch.setattr("orchestrator.newsletter_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr("orchestrator.newsletter_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "test@example.com")

    metrics = [
        {"date": "2026-03-31", "subscribers": 27, "open_rate": 38.5, "total_email": 23, "growth_sources": []},
    ]
    (tmp_path / "substack_metrics.json").write_text(json.dumps(metrics))

    with patch("orchestrator.newsletter_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.newsletter_agent.anthropic.Anthropic") as MockAnthropic, \
         patch("orchestrator.newsletter_agent.subprocess.run") as mock_run:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="草稿")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp
        mock_run.return_value = MagicMock(returncode=0)

        newsletter_agent.run()

    call_args = mock_run.call_args
    email_body = call_args[1]["input"].decode("utf-8")
    assert "27" in email_body
    assert "首次記錄" in email_body


def test_newsletter_email_zero_delta(tmp_path, monkeypatch):
    """When subscriber count is unchanged between snapshots, delta shows ±0."""
    monkeypatch.setattr("orchestrator.newsletter_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr("orchestrator.newsletter_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "test@example.com")

    metrics = [
        {"date": "2026-03-24", "subscribers": 27, "open_rate": 35.0, "total_email": 20, "growth_sources": []},
        {"date": "2026-03-31", "subscribers": 27, "open_rate": 38.5, "total_email": 23, "growth_sources": []},
    ]
    (tmp_path / "substack_metrics.json").write_text(json.dumps(metrics))

    with patch("orchestrator.newsletter_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.newsletter_agent.anthropic.Anthropic") as MockAnthropic, \
         patch("orchestrator.newsletter_agent.subprocess.run") as mock_run:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="草稿")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp
        mock_run.return_value = MagicMock(returncode=0)

        newsletter_agent.run()

    call_args = mock_run.call_args
    email_body = call_args[1]["input"].decode("utf-8")
    assert "±0" in email_body


def test_newsletter_email_no_funnel_when_no_metrics(tmp_path, monkeypatch):
    """When substack_metrics.json does not exist, email sends without funnel section."""
    monkeypatch.setattr("orchestrator.newsletter_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr("orchestrator.newsletter_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "test@example.com")
    # Note: no substack_metrics.json created in tmp_path

    with patch("orchestrator.newsletter_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.newsletter_agent.anthropic.Anthropic") as MockAnthropic, \
         patch("orchestrator.newsletter_agent.subprocess.run") as mock_run:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="草稿")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp
        mock_run.return_value = MagicMock(returncode=0)

        newsletter_agent.run()  # Must not raise

    # Email was sent (subprocess.run was called)
    assert mock_run.called
    call_args = mock_run.call_args
    email_body = call_args[1]["input"].decode("utf-8")
    # Funnel section should be absent
    assert "訂閱數" not in email_body
    assert "Substack 漏斗" not in email_body


def test_newsletter_uses_topic_from_status(tmp_path, monkeypatch):
    """Newsletter prompt is driven by topic from newsletter_status.json."""
    monkeypatch.setattr("orchestrator.newsletter_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr("orchestrator.newsletter_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "")

    (tmp_path / "newsletter_status.json").write_text(
        json.dumps({"week": "2026-03-31", "topic": "AI Agent 自動化實戰", "status": "pending"})
    )

    with patch("orchestrator.newsletter_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.newsletter_agent.anthropic.Anthropic") as MockAnthropic:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="草稿內容")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp

        newsletter_agent.run()

    prompt = MockAnthropic.return_value.messages.create.call_args[1]["messages"][0]["content"]
    assert "AI Agent 自動化實戰" in prompt


def test_newsletter_updates_status_to_draft(tmp_path, monkeypatch):
    """After generating draft, newsletter_status.json is updated to draft."""
    monkeypatch.setattr("orchestrator.newsletter_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr("orchestrator.newsletter_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "")

    (tmp_path / "newsletter_status.json").write_text(
        json.dumps({"week": "2026-03-31", "topic": "測試主題", "status": "pending"})
    )

    with patch("orchestrator.newsletter_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.newsletter_agent.anthropic.Anthropic") as MockAnthropic:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="草稿")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp

        newsletter_agent.run()

    status = json.loads((tmp_path / "newsletter_status.json").read_text())
    assert status["status"] == "draft"
    assert status["topic"] == "測試主題"
