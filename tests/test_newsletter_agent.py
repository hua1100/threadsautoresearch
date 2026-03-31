import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


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
