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
         patch("orchestrator.main.get_follower_count", return_value=44):

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
