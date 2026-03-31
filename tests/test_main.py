import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from orchestrator.main import detect_phase, run


def test_detect_phase_returns_1_under_threshold():
    assert detect_phase(44) == 1


def test_detect_phase_returns_2_at_threshold():
    assert detect_phase(100) == 2


def test_detect_phase_returns_2_above_threshold():
    assert detect_phase(500) == 2


def test_run_executes_full_loop():
    with patch("orchestrator.main.fetch_sources") as mock_sources, \
         patch("orchestrator.main.harvest") as mock_harvest, \
         patch("orchestrator.main.analyze") as mock_analyze, \
         patch("orchestrator.main.generate") as mock_generate, \
         patch("orchestrator.main.deploy") as mock_deploy, \
         patch("orchestrator.main.send_notification") as mock_notify, \
         patch("orchestrator.main.get_follower_count", return_value=44), \
         patch("orchestrator.main.check_newsletter_status"):

        mock_sources.return_value = {"youtube": [], "github": [], "x": []}
        mock_harvest.return_value = [{"media_id": "1", "views": 10, "likes": 1, "replies": 0}]
        mock_analyze.return_value = {"scored_posts": [], "analysis": "ok", "learnings": "", "round_number": 1}
        mock_generate.return_value = [{"text": "Hello", "dimensions": {}, "hypothesis": "test"}]
        mock_deploy.return_value = [{"media_id": "new_1"}]

        run()

    mock_sources.assert_called_once()
    mock_harvest.assert_called_once()
    mock_analyze.assert_called_once()
    mock_generate.assert_called_once()
    mock_deploy.assert_called_once()
    mock_notify.assert_called()


def test_check_newsletter_status_detects_new_publication(tmp_path, monkeypatch):
    """check_newsletter_status updates status to published when new post detected."""
    monkeypatch.setattr("orchestrator.main.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.main.SUBSTACK_SID", "fake-sid")
    monkeypatch.setattr("orchestrator.main.SUBSTACK_SUBDOMAIN", "hualeee")

    (tmp_path / "newsletter_status.json").write_text(json.dumps({
        "week": "2026-03-31",
        "topic": "AI Agent",
        "status": "draft",
        "url": "",
    }))

    with patch("orchestrator.main.SubstackClient") as MockClient:
        MockClient.return_value.fetch_latest_post.return_value = {
            "title": "AI Agent 深度分析",
            "url": "https://hualeee.substack.com/p/ai-agent",
            "date": "2026-03-31T10:30:00Z",
        }

        from orchestrator.main import check_newsletter_status
        check_newsletter_status()

    status = json.loads((tmp_path / "newsletter_status.json").read_text())
    assert status["status"] == "published"
    assert status["url"] == "https://hualeee.substack.com/p/ai-agent"


def test_check_newsletter_status_skips_when_already_published(tmp_path, monkeypatch):
    """check_newsletter_status does not re-check when already published."""
    monkeypatch.setattr("orchestrator.main.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.main.SUBSTACK_SID", "fake-sid")
    monkeypatch.setattr("orchestrator.main.SUBSTACK_SUBDOMAIN", "hualeee")

    (tmp_path / "newsletter_status.json").write_text(json.dumps({
        "week": "2026-03-31",
        "status": "published",
        "url": "https://hualeee.substack.com/p/old",
    }))

    with patch("orchestrator.main.SubstackClient") as MockClient:
        from orchestrator.main import check_newsletter_status
        check_newsletter_status()

    MockClient.assert_not_called()


def test_check_newsletter_status_skips_without_sid(tmp_path, monkeypatch):
    """check_newsletter_status does nothing when SUBSTACK_SID is empty."""
    monkeypatch.setattr("orchestrator.main.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.main.SUBSTACK_SID", "")

    with patch("orchestrator.main.SubstackClient") as MockClient:
        from orchestrator.main import check_newsletter_status
        check_newsletter_status()

    MockClient.assert_not_called()
