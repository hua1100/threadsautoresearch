import json
import pytest
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


def test_strategy_agent_saves_substack_snapshot(tmp_path, monkeypatch):
    """Strategy agent saves a Substack snapshot to data/substack_metrics.json."""
    monkeypatch.setattr("orchestrator.strategy_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.SUBSTACK_SID", "fake-sid")
    monkeypatch.setattr("orchestrator.strategy_agent.SUBSTACK_SUBDOMAIN", "hualeee")

    fake_snapshot = {
        "date": "2026-03-31",
        "subscribers": 30,
        "total_email": 23,
        "open_rate": 38.5,
        "growth_sources": [{"source": "substack", "value": 15}],
    }

    with patch("orchestrator.strategy_agent.SubstackClient") as MockClient, \
         patch("orchestrator.strategy_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.strategy_agent.anthropic.Anthropic") as MockAnthropic:

        mock_instance = MockClient.return_value
        mock_instance.fetch_snapshot.return_value = fake_snapshot

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="# 本週流量策略")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp

        from orchestrator import strategy_agent
        strategy_agent.run()

    metrics_path = tmp_path / "substack_metrics.json"
    assert metrics_path.exists()
    data = json.loads(metrics_path.read_text())
    assert isinstance(data, list)
    assert data[-1]["subscribers"] == 30


def test_strategy_agent_skips_snapshot_without_sid(tmp_path, monkeypatch):
    """Strategy agent skips snapshot gracefully when SUBSTACK_SID is empty."""
    monkeypatch.setattr("orchestrator.strategy_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.SUBSTACK_SID", "")

    with patch("orchestrator.strategy_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.strategy_agent.anthropic.Anthropic") as MockAnthropic:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="# 本週流量策略")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp

        from orchestrator import strategy_agent
        strategy_agent.run()  # Should not raise

    # No metrics file written
    assert not (tmp_path / "substack_metrics.json").exists()
