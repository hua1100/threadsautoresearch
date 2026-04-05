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


from orchestrator.competitor_scout import scrape_accounts


FAKE_THREADS_POSTS = [
    {
        "username": "prompt_case",
        "latestPosts": [
            {"caption": {"text": "AI 工具推薦第一篇"}, "taken_at": 1234},
            {"caption": {"text": "學 AI 的五個步驟"}, "taken_at": 1235},
        ],
    }
]

FAKE_X_POSTS = [
    {"full_text": "Top 5 AI tools this week", "created_at": "2026-04-01T08:00:00Z"},
    {"full_text": "How I use AI daily", "created_at": "2026-04-02T08:00:00Z"},
]


def test_scrape_accounts_threads_returns_posts():
    with patch("orchestrator.competitor_scout.run_actor", return_value=FAKE_THREADS_POSTS):
        result = scrape_accounts(["prompt_case"], platform="threads")
    assert "prompt_case" in result
    assert len(result["prompt_case"]) == 2
    assert result["prompt_case"][0]["text"] == "AI 工具推薦第一篇"


def test_scrape_accounts_x_returns_posts():
    with patch("orchestrator.competitor_scout.run_actor", return_value=FAKE_X_POSTS):
        result = scrape_accounts(["aitools_daily"], platform="x")
    assert "aitools_daily" in result
    assert result["aitools_daily"][0]["text"] == "Top 5 AI tools this week"


def test_scrape_accounts_skips_failed_account():
    from orchestrator.apify_client import ApifyError
    with patch("orchestrator.competitor_scout.run_actor", side_effect=ApifyError("timeout")):
        result = scrape_accounts(["bad_account"], platform="threads")
    assert result == {}


def test_scrape_accounts_multiple_accounts():
    call_count = 0
    def fake_run_actor(actor_id, actor_input, **kwargs):
        nonlocal call_count
        call_count += 1
        return FAKE_THREADS_POSTS

    with patch("orchestrator.competitor_scout.run_actor", side_effect=fake_run_actor):
        result = scrape_accounts(["acc1", "acc2"], platform="threads")
    assert len(result) == 2
    assert call_count == 2


from unittest.mock import MagicMock
from orchestrator.competitor_scout import analyze_competitors


FAKE_SCRAPED = {
    "prompt_case": [{"text": "AI 工具推薦\n✅ 第一點\n✅ 第二點", "raw": {}}] * 10,
    "aitools_daily": [{"text": "Top 3 AI tools 🔥\n1. Tool A\n2. Tool B", "raw": {}}] * 10,
}


def test_analyze_competitors_returns_report_string():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="## 競品格式分析\n規則一：使用條列式結構")]

    with patch("orchestrator.competitor_scout.anthropic.Anthropic") as MockClaude:
        MockClaude.return_value.messages.create.return_value = mock_response
        report = analyze_competitors(FAKE_SCRAPED)

    assert isinstance(report, str)
    assert len(report) > 0


def test_analyze_competitors_includes_account_names_in_prompt():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="analysis result")]
    captured_prompt = {}

    def fake_create(**kwargs):
        captured_prompt["content"] = kwargs["messages"][0]["content"]
        return mock_response

    with patch("orchestrator.competitor_scout.anthropic.Anthropic") as MockClaude:
        MockClaude.return_value.messages.create.side_effect = fake_create
        analyze_competitors(FAKE_SCRAPED)

    assert "prompt_case" in captured_prompt["content"]
    assert "aitools_daily" in captured_prompt["content"]


from orchestrator.competitor_scout import save_report, patch_strategy


def test_save_report_writes_markdown(tmp_path):
    report_path = tmp_path / "competitor_report.md"
    raw_path = tmp_path / "competitor_raw.json"

    save_report(
        report_text="## 分析結果\n規則一：條列式",
        scraped=FAKE_SCRAPED,
        report_path=report_path,
        raw_path=raw_path,
    )

    assert report_path.exists()
    assert "分析結果" in report_path.read_text()
    assert raw_path.exists()


def test_patch_strategy_appends_section(tmp_path):
    strategy_path = tmp_path / "strategy.md"
    strategy_path.write_text("# 本週流量策略\n## 目標\n衝觸及\n")

    patch_strategy("規則一：條列式\n規則二：短句", strategy_path=strategy_path)

    content = strategy_path.read_text()
    assert "競品格式觀察" in content
    assert "規則一：條列式" in content


def test_patch_strategy_does_not_duplicate(tmp_path):
    strategy_path = tmp_path / "strategy.md"
    strategy_path.write_text("# 本週流量策略\n## 競品格式觀察（2026-04-05）\n舊資料\n")

    patch_strategy("新規則", strategy_path=strategy_path)

    content = strategy_path.read_text()
    # Should append new section, not replace old
    assert "新規則" in content
