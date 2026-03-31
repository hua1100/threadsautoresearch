import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


def test_load_recent_experiments_filters_by_date():
    from orchestrator.utils import load_recent_experiments

    now = datetime.now(timezone.utc)
    recent = now.isoformat()
    old = (now - timedelta(days=10)).isoformat()

    experiments = [
        {"harvested_at": recent, "results": [], "analysis": "new"},
        {"harvested_at": old, "results": [], "analysis": "old"},
    ]

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        (data_dir / "experiments.json").write_text(json.dumps(experiments))

        with patch("orchestrator.utils.DATA_DIR", data_dir):
            result = load_recent_experiments(days=7)

    assert len(result) == 1
    assert result[0]["analysis"] == "new"


def test_run_writes_strategy_md():
    from orchestrator.strategy_agent import run

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# 本週流量策略\n## 目標\n導流電子報")]

    with tempfile.TemporaryDirectory() as tmp:
        prompts_dir = Path(tmp) / "prompts"
        prompts_dir.mkdir()
        data_dir = Path(tmp) / "data"
        data_dir.mkdir()
        (data_dir / "experiments.json").write_text("[]")

        with patch("orchestrator.strategy_agent.anthropic") as mock_anthropic, \
             patch("orchestrator.utils.DATA_DIR", data_dir), \
             patch("orchestrator.strategy_agent.PROMPTS_DIR", prompts_dir):

            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.Anthropic.return_value = mock_client

            run()

        strategy_path = prompts_dir / "strategy.md"
        assert strategy_path.exists()
        assert "本週流量策略" in strategy_path.read_text(encoding="utf-8")
