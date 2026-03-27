import os
import pytest


def test_config_loads_required_vars(monkeypatch):
    monkeypatch.setenv("THREADS_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("THREADS_USER_ID", "12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")

    import importlib
    import orchestrator.config as cfg
    importlib.reload(cfg)

    assert cfg.THREADS_ACCESS_TOKEN == "test_token"
    assert cfg.THREADS_USER_ID == "12345"
    assert cfg.ANTHROPIC_API_KEY == "sk-test"
    assert cfg.TELEGRAM_BOT_TOKEN == "bot123"
    assert cfg.TELEGRAM_CHAT_ID == "chat456"


def test_config_defaults():
    import orchestrator.config as cfg
    assert cfg.PHASE_SWITCH_FOLLOWER_THRESHOLD == 100
    assert cfg.SCORE_WEIGHT_VIEWS == 0.6
    assert cfg.SCORE_WEIGHT_LIKES == 0.2
    assert cfg.SCORE_WEIGHT_REPLIES == 0.2
