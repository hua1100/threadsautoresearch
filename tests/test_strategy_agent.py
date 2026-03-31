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
        "growth_sources": [{"source": "substack", "traffic": 15, "new_subscribers": 1}],
        "threads_funnel": {"traffic": 0, "new_subscribers": 0, "conversion_rate": 0.0},
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

    # Verify Substack section was injected into the prompt
    call_args = MockAnthropic.return_value.messages.create.call_args
    prompt_text = call_args[1]["messages"][0]["content"]
    assert "訂閱數：30" in prompt_text


def test_strategy_agent_skips_snapshot_without_sid(tmp_path, monkeypatch):
    """Strategy agent skips snapshot gracefully when SUBSTACK_SID is empty."""
    monkeypatch.setattr("orchestrator.strategy_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.SUBSTACK_SID", "")

    with patch("orchestrator.strategy_agent.SubstackClient") as MockClient, \
         patch("orchestrator.strategy_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.strategy_agent.anthropic.Anthropic") as MockAnthropic:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="# 本週流量策略")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp

        from orchestrator import strategy_agent
        strategy_agent.run()  # Should not raise
        assert MockClient.call_count == 0

    # No metrics file written
    assert not (tmp_path / "substack_metrics.json").exists()


def test_strategy_agent_includes_threads_funnel_in_prompt(tmp_path, monkeypatch):
    """Strategy prompt includes threads_funnel data when available."""
    monkeypatch.setattr("orchestrator.strategy_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.SUBSTACK_SID", "fake-sid")
    monkeypatch.setattr("orchestrator.strategy_agent.SUBSTACK_SUBDOMAIN", "hualeee")

    fake_snapshot = {
        "date": "2026-03-31",
        "subscribers": 31,
        "total_email": 27,
        "open_rate": 25.9,
        "growth_sources": [{"source": "threads.net", "traffic": 10, "new_subscribers": 2}],
        "threads_funnel": {"traffic": 10, "new_subscribers": 2, "conversion_rate": 20.0},
    }

    with patch("orchestrator.strategy_agent.SubstackClient") as MockClient, \
         patch("orchestrator.strategy_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.strategy_agent.anthropic.Anthropic") as MockAnthropic:

        MockClient.return_value.fetch_snapshot.return_value = fake_snapshot

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="# 本週流量策略\n## 本週電子報主題\nAI Agent 成本")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp

        from orchestrator import strategy_agent
        strategy_agent.run()

    prompt = MockAnthropic.return_value.messages.create.call_args[1]["messages"][0]["content"]
    assert "Threads → 電子報轉換漏斗" in prompt
    assert "轉換率：20.0%" in prompt


def test_strategy_agent_inits_newsletter_status(tmp_path, monkeypatch):
    """Strategy agent creates newsletter_status.json with topic from strategy.md."""
    monkeypatch.setattr("orchestrator.strategy_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.SUBSTACK_SID", "")

    with patch("orchestrator.strategy_agent.SubstackClient"), \
         patch("orchestrator.strategy_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.strategy_agent.anthropic.Anthropic") as MockAnthropic:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="# 本週流量策略\n## 目標\n衝觸及\n## 本週電子報主題\nAI 工具自動化實戰")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp

        from orchestrator import strategy_agent
        strategy_agent.run()

    status_path = tmp_path / "newsletter_status.json"
    assert status_path.exists()
    status = json.loads(status_path.read_text())
    assert status["status"] == "pending"
    assert status["topic"] == "AI 工具自動化實戰"
    assert "week" in status


def test_strategy_agent_triggers_lazy_pack_for_top_post(tmp_path, monkeypatch):
    """Strategy agent triggers lazy pack for top post when views >= threshold."""
    monkeypatch.setattr("orchestrator.strategy_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.SUBSTACK_SID", "")
    monkeypatch.setattr("orchestrator.strategy_agent.LAZY_PACK_MIN_VIEWS", 100)

    experiments = [
        {
            "harvested_at": datetime.now(timezone.utc).isoformat(),
            "results": [
                {"media_id": "top_1", "score": 1.0, "views": 5000, "likes": 50, "replies": 10},
                {"media_id": "low_1", "score": 0.2, "views": 50, "likes": 1, "replies": 0},
            ],
        }
    ]

    posts = [
        {"media_id": "top_1", "text": "高表現貼文", "dimensions": {"content_type": "工具分享", "source": "youtube"}},
        {"media_id": "low_1", "text": "低表現", "dimensions": {}},
    ]
    (tmp_path / "posts.json").write_text(json.dumps(posts))

    with patch("orchestrator.strategy_agent.SubstackClient"), \
         patch("orchestrator.strategy_agent.load_recent_experiments", return_value=experiments), \
         patch("orchestrator.strategy_agent.anthropic.Anthropic") as MockAnthropic, \
         patch("orchestrator.strategy_agent.generate_lazy_pack") as mock_lazy:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="# 本週流量策略\n## 本週電子報主題\n測試")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp

        from orchestrator import strategy_agent
        strategy_agent.run()

    mock_lazy.assert_called_once()
    call_post = mock_lazy.call_args[0][0]
    assert call_post["media_id"] == "top_1"


def test_strategy_agent_skips_lazy_pack_when_already_exists(tmp_path, monkeypatch):
    """Strategy agent skips lazy pack if media_id already in lazy_packs.json."""
    monkeypatch.setattr("orchestrator.strategy_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.SUBSTACK_SID", "")
    monkeypatch.setattr("orchestrator.strategy_agent.LAZY_PACK_MIN_VIEWS", 100)

    experiments = [
        {
            "harvested_at": datetime.now(timezone.utc).isoformat(),
            "results": [
                {"media_id": "top_1", "score": 1.0, "views": 5000, "likes": 50, "replies": 10},
            ],
        }
    ]

    posts = [{"media_id": "top_1", "text": "已有懶人包", "dimensions": {}}]
    (tmp_path / "posts.json").write_text(json.dumps(posts))

    (tmp_path / "lazy_packs.json").write_text(json.dumps([
        {"media_id": "top_1", "keyword": "old"}
    ]))

    with patch("orchestrator.strategy_agent.SubstackClient"), \
         patch("orchestrator.strategy_agent.load_recent_experiments", return_value=experiments), \
         patch("orchestrator.strategy_agent.anthropic.Anthropic") as MockAnthropic, \
         patch("orchestrator.strategy_agent.generate_lazy_pack") as mock_lazy:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="# 本週流量策略\n## 本週電子報主題\n測試")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp

        from orchestrator import strategy_agent
        strategy_agent.run()

    mock_lazy.assert_not_called()
