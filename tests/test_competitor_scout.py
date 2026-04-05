import pytest
from unittest.mock import patch
from orchestrator.competitor_scout import discover_x_accounts


FAKE_SEARCH_RESULTS = [
    {"author_username": "aitools_daily", "author_followers": 45000, "like_count": 500, "retweet_count": 120},
    {"author_username": "sama", "author_followers": 800000, "like_count": 9000, "retweet_count": 3000},
    {"author_username": "ai_builder", "author_followers": 12000, "like_count": 300, "retweet_count": 80},
    {"author_username": "llm_tips", "author_followers": 30000, "like_count": 250, "retweet_count": 60},
    {"author_username": "aitools_daily", "author_followers": 45000, "like_count": 200, "retweet_count": 50},  # duplicate
    {"author_username": "gpt_hacks", "author_followers": 8000, "like_count": 180, "retweet_count": 40},
    {"author_username": "ai_workflow", "author_followers": 55000, "like_count": 160, "retweet_count": 35},
]


def test_discover_x_accounts_excludes_celebrities():
    with patch("orchestrator.competitor_scout.run_actor", return_value=FAKE_SEARCH_RESULTS):
        accounts = discover_x_accounts(top_n=5, max_followers=500_000)
    assert "sama" not in accounts


def test_discover_x_accounts_deduplicates():
    with patch("orchestrator.competitor_scout.run_actor", return_value=FAKE_SEARCH_RESULTS):
        accounts = discover_x_accounts(top_n=5, max_followers=500_000)
    assert accounts.count("aitools_daily") == 1


def test_discover_x_accounts_respects_top_n():
    with patch("orchestrator.competitor_scout.run_actor", return_value=FAKE_SEARCH_RESULTS):
        accounts = discover_x_accounts(top_n=3, max_followers=500_000)
    assert len(accounts) <= 3


def test_discover_x_accounts_ranks_by_engagement():
    with patch("orchestrator.competitor_scout.run_actor", return_value=FAKE_SEARCH_RESULTS):
        accounts = discover_x_accounts(top_n=5, max_followers=500_000)
    # aitools_daily has highest total engagement (500+120=620), should be first
    assert accounts[0] == "aitools_daily"


def test_discover_x_accounts_returns_empty_on_apify_error():
    from orchestrator.apify_client import ApifyError
    with patch("orchestrator.competitor_scout.run_actor", side_effect=ApifyError("timeout")):
        accounts = discover_x_accounts(top_n=5, max_followers=500_000)
    assert accounts == []
