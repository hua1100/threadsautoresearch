# Competitor Scout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增獨立的競品帳號爬蟲分析模組，爬取 Threads 種子帳號與自動發現的 X 高互動 AI 帳號貼文，用 Claude 分析格式策略，輸出報告並提供 CLI 確認後 patch strategy.md。

**Architecture:** `apify_client.py` 封裝 Apify HTTP API（sync run）；`competitor_scout.py` 串接爬蟲 → 帳號發現 → 分析 → 輸出 → 確認閘。完全獨立，不進入 `main.py` 主輪迴。

**Tech Stack:** Python 3.12、requests（已有）、Apify HTTP API（`apify/threads-scraper`、`apify/twitter-scraper`）、Anthropic Claude API（已有）

---

## File Map

| 動作 | 路徑 | 職責 |
|------|------|------|
| Create | `orchestrator/apify_client.py` | Apify HTTP API 封裝，run_actor() → list[dict] |
| Create | `orchestrator/competitor_scout.py` | 主模組：發現 → 爬蟲 → 分析 → 輸出 → 確認閘 |
| Modify | `orchestrator/config.py` | 新增 APIFY 相關設定 |
| Modify | `.env.example` | 新增 APIFY_API_TOKEN |
| Create | `tests/test_apify_client.py` | apify_client 單元測試 |
| Create | `tests/test_competitor_scout.py` | competitor_scout 單元測試 |

---

## Task 1: 新增 config 設定與 .env.example

**Files:**
- Modify: `orchestrator/config.py`
- Modify: `.env.example`

- [ ] **Step 1: 在 config.py 尾端新增 Apify 設定**

在 `orchestrator/config.py` 最後加入：

```python
# Apify
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")

COMPETITOR_THREADS_ACCOUNTS = [
    "prompt_case",
    "iamraven.tw",
    "aiposthub",
]

COMPETITOR_X_SEARCH_KEYWORDS = [
    "AI tools",
    "AI tutorial",
    "AI workflow",
]

COMPETITOR_POSTS_PER_ACCOUNT = 50
COMPETITOR_X_TOP_N = 5
COMPETITOR_X_MAX_FOLLOWERS = 500_000
```

- [ ] **Step 2: 在 .env.example 新增 APIFY_API_TOKEN**

在 `.env.example` 尾端加入：

```
# Apify (competitor scout)
APIFY_API_TOKEN=
```

- [ ] **Step 3: 確認 config 可正常 import**

```bash
cd /Users/hua/autoresearch_threads
python -c "from orchestrator.config import APIFY_API_TOKEN, COMPETITOR_THREADS_ACCOUNTS; print(COMPETITOR_THREADS_ACCOUNTS)"
```

Expected output:
```
['prompt_case', 'iamraven.tw', 'aiposthub']
```

- [ ] **Step 4: Commit**

```bash
git add orchestrator/config.py .env.example
git commit -m "feat: add Apify config for competitor scout"
```

---

## Task 2: 實作 apify_client.py（TDD）

**Files:**
- Create: `tests/test_apify_client.py`
- Create: `orchestrator/apify_client.py`

### 2a — 寫失敗測試

- [ ] **Step 1: 建立測試檔案**

新增 `tests/test_apify_client.py`：

```python
import pytest
from unittest.mock import patch, MagicMock
from orchestrator.apify_client import run_actor, ApifyError


def test_run_actor_returns_items():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"text": "post 1", "author": "user1"},
        {"text": "post 2", "author": "user1"},
    ]

    with patch("orchestrator.apify_client.requests.post", return_value=mock_resp):
        items = run_actor("apify/fake-actor", {"key": "val"}, api_token="tok123")

    assert len(items) == 2
    assert items[0]["text"] == "post 1"


def test_run_actor_raises_on_http_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"

    with patch("orchestrator.apify_client.requests.post", return_value=mock_resp):
        with pytest.raises(ApifyError, match="400"):
            run_actor("apify/fake-actor", {}, api_token="tok123")


def test_run_actor_raises_on_timeout():
    import requests as req
    with patch("orchestrator.apify_client.requests.post", side_effect=req.Timeout):
        with pytest.raises(ApifyError, match="timeout"):
            run_actor("apify/fake-actor", {}, api_token="tok123", timeout=1)


def test_run_actor_returns_empty_list_on_empty_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []

    with patch("orchestrator.apify_client.requests.post", return_value=mock_resp):
        items = run_actor("apify/fake-actor", {}, api_token="tok123")

    assert items == []
```

- [ ] **Step 2: 確認測試失敗**

```bash
cd /Users/hua/autoresearch_threads
python -m pytest tests/test_apify_client.py -v
```

Expected: 4 errors（ImportError — module not found）

### 2b — 實作 apify_client.py

- [ ] **Step 3: 建立 orchestrator/apify_client.py**

```python
import requests
from orchestrator.config import APIFY_API_TOKEN


class ApifyError(Exception):
    pass


def run_actor(
    actor_id: str,
    actor_input: dict,
    api_token: str | None = None,
    timeout: int = 180,
) -> list[dict]:
    """
    Run an Apify actor synchronously and return dataset items.

    Uses the run-sync-get-dataset-items endpoint:
    POST /v2/acts/{actorId}/run-sync-get-dataset-items?token=...&timeout=...
    """
    token = api_token or APIFY_API_TOKEN
    url = (
        f"https://api.apify.com/v2/acts/{actor_id}"
        f"/run-sync-get-dataset-items"
        f"?token={token}&timeout={timeout}"
    )

    try:
        resp = requests.post(url, json=actor_input, timeout=timeout + 10)
    except requests.Timeout:
        raise ApifyError(f"timeout after {timeout}s running {actor_id}")
    except requests.RequestException as e:
        raise ApifyError(f"request error: {e}")

    if resp.status_code != 200:
        raise ApifyError(f"{resp.status_code} from Apify: {resp.text[:200]}")

    return resp.json() or []
```

- [ ] **Step 4: 確認測試通過**

```bash
python -m pytest tests/test_apify_client.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add orchestrator/apify_client.py tests/test_apify_client.py
git commit -m "feat: add Apify HTTP client with error handling"
```

---

## Task 3: X 帳號發現邏輯（TDD）

**Files:**
- Create: `tests/test_competitor_scout.py`（第一批測試）
- Create: `orchestrator/competitor_scout.py`（discover 函式）

### 3a — 寫失敗測試

- [ ] **Step 1: 建立 tests/test_competitor_scout.py，加入 discover 測試**

```python
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
```

- [ ] **Step 2: 確認測試失敗**

```bash
python -m pytest tests/test_competitor_scout.py::test_discover_x_accounts_excludes_celebrities -v
```

Expected: ImportError

### 3b — 實作 discover_x_accounts

- [ ] **Step 3: 建立 orchestrator/competitor_scout.py，加入 discover 函式**

```python
from __future__ import annotations
import json
from pathlib import Path
from orchestrator.config import (
    APIFY_API_TOKEN,
    ANTHROPIC_API_KEY,
    COMPETITOR_THREADS_ACCOUNTS,
    COMPETITOR_X_SEARCH_KEYWORDS,
    COMPETITOR_POSTS_PER_ACCOUNT,
    COMPETITOR_X_TOP_N,
    COMPETITOR_X_MAX_FOLLOWERS,
    DATA_DIR,
    PROMPTS_DIR,
)
from orchestrator.apify_client import run_actor, ApifyError
from orchestrator.notify import send_notification


def discover_x_accounts(
    top_n: int = COMPETITOR_X_TOP_N,
    max_followers: int = COMPETITOR_X_MAX_FOLLOWERS,
) -> list[str]:
    """Search X for high-engagement AI posts, return top non-celebrity account handles."""
    print("[SCOUT] Discovering top X AI accounts...")
    try:
        items = run_actor(
            "apify/twitter-scraper",
            {
                "searchTerms": COMPETITOR_X_SEARCH_KEYWORDS,
                "maxItems": 200,
                "sort": "Latest",
            },
        )
    except ApifyError as e:
        print(f"[SCOUT] X discovery failed: {e}")
        return []

    # Aggregate engagement per unique author
    engagement: dict[str, int] = {}
    followers: dict[str, int] = {}
    for item in items:
        username = item.get("author_username") or item.get("username") or ""
        if not username:
            continue
        follower_count = item.get("author_followers") or item.get("followers_count") or 0
        if follower_count > max_followers:
            continue
        score = (item.get("like_count") or 0) + (item.get("retweet_count") or 0)
        if username not in engagement or score > engagement[username]:
            engagement[username] = engagement.get(username, 0) + score
            followers[username] = follower_count

    ranked = sorted(engagement.keys(), key=lambda u: engagement[u], reverse=True)
    result = ranked[:top_n]
    print(f"[SCOUT] Discovered X accounts: {result}")
    return result
```

- [ ] **Step 4: 確認 discover 測試通過**

```bash
python -m pytest tests/test_competitor_scout.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add orchestrator/competitor_scout.py tests/test_competitor_scout.py
git commit -m "feat: add X account discovery by engagement ranking"
```

---

## Task 4: 爬蟲層（scrape Threads + X）

**Files:**
- Modify: `orchestrator/competitor_scout.py`（新增 scrape 函式）
- Modify: `tests/test_competitor_scout.py`（新增 scrape 測試）

- [ ] **Step 1: 在 tests/test_competitor_scout.py 尾端追加 scrape 測試**

```python
from orchestrator.competitor_scout import scrape_accounts


FAKE_THREADS_POSTS = [
    {"text": "AI 工具推薦第一篇", "timestamp": "2026-04-01T10:00:00Z"},
    {"text": "學 AI 的五個步驟", "timestamp": "2026-04-02T10:00:00Z"},
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
```

- [ ] **Step 2: 確認新測試失敗**

```bash
python -m pytest tests/test_competitor_scout.py::test_scrape_accounts_threads_returns_posts -v
```

Expected: ImportError（scrape_accounts not defined）

- [ ] **Step 3: 在 competitor_scout.py 加入 scrape_accounts 函式**

在 `discover_x_accounts` 之後加入：

```python
def scrape_accounts(
    accounts: list[str],
    platform: str,  # "threads" or "x"
    posts_per_account: int = COMPETITOR_POSTS_PER_ACCOUNT,
) -> dict[str, list[dict]]:
    """Scrape posts from a list of accounts. Returns {username: [posts]}."""
    if platform == "threads":
        actor_id = "apify/threads-scraper"
    else:
        actor_id = "apify/twitter-scraper"

    results: dict[str, list[dict]] = {}
    for account in accounts:
        print(f"[SCOUT] Scraping {platform}/@{account}...")
        try:
            if platform == "threads":
                raw = run_actor(
                    actor_id,
                    {"usernames": [account], "resultsLimit": posts_per_account},
                )
            else:
                raw = run_actor(
                    actor_id,
                    {"handles": [account], "maxItems": posts_per_account},
                )
        except ApifyError as e:
            print(f"[SCOUT] Skipping @{account}: {e}")
            continue

        # Normalise text field (Threads uses "text", X uses "full_text")
        posts = []
        for item in raw:
            text = item.get("text") or item.get("full_text") or ""
            if text:
                posts.append({"text": text, "raw": item})
        results[account] = posts
        print(f"[SCOUT]   {len(posts)} posts collected")

    return results
```

- [ ] **Step 4: 確認所有測試通過**

```bash
python -m pytest tests/test_competitor_scout.py -v
```

Expected: 9 PASSED

- [ ] **Step 5: Commit**

```bash
git add orchestrator/competitor_scout.py tests/test_competitor_scout.py
git commit -m "feat: add scrape_accounts for Threads and X"
```

---

## Task 5: Claude 分析層

**Files:**
- Modify: `orchestrator/competitor_scout.py`（新增 analyze_competitors 函式）
- Modify: `tests/test_competitor_scout.py`（新增分析測試）

- [ ] **Step 1: 在 tests/test_competitor_scout.py 尾端追加分析測試**

```python
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
```

- [ ] **Step 2: 確認測試失敗**

```bash
python -m pytest tests/test_competitor_scout.py::test_analyze_competitors_returns_report_string -v
```

Expected: ImportError

- [ ] **Step 3: 在 competitor_scout.py 加入 analyze_competitors 函式**

在 `scrape_accounts` 之後加入：

```python
import anthropic


def analyze_competitors(scraped: dict[str, list[dict]]) -> str:
    """Send scraped posts to Claude for format strategy analysis."""
    if not scraped:
        return "（無競品資料可分析）"

    # Build per-account text sample (max 30 posts each to stay within token limit)
    sections = []
    for account, posts in scraped.items():
        sample = posts[:30]
        texts = "\n---\n".join(p["text"] for p in sample)
        sections.append(f"### @{account}（{len(sample)} 篇）\n{texts}")

    all_posts_text = "\n\n".join(sections)

    prompt = f"""你是一個社群媒體格式策略分析師。以下是多個高表現 AI 內容帳號的近期貼文：

{all_posts_text}

請分析這些帳號的**發文格式與結構**，涵蓋：

1. **長度習慣**：平均字數區間，短文（<100字）vs 長文（>200字）比例
2. **換行/段落習慣**：單句換行、段落式、條列式各佔多少比例
3. **Emoji 使用**：使用頻率（每篇平均幾個）、位置（開頭/結尾/穿插）、常見類型
4. **Hook 句型分類**：提問型 / 數字型 / 預言型 / 故事型 / 衝突型，各帳號的偏好
5. **內容類型分佈**：工具介紹 / 教學步驟 / 趨勢新聞 / 觀點辯論
6. **CTA 模式**：有無 CTA、放哪裡、常見句式

最後請歸納 3-5 條「跨帳號共同格式規則」，格式為：
- 規則：[具體描述]
- 依據：[從哪些帳號觀察到]
- 建議應用：[如何套用到自己的貼文]

用繁體中文回答。"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
```

- [ ] **Step 4: 確認測試通過**

```bash
python -m pytest tests/test_competitor_scout.py -v
```

Expected: 11 PASSED

- [ ] **Step 5: Commit**

```bash
git add orchestrator/competitor_scout.py tests/test_competitor_scout.py
git commit -m "feat: add Claude-powered competitor format analysis"
```

---

## Task 6: 輸出層 + 確認閘 + run() 整合

**Files:**
- Modify: `orchestrator/competitor_scout.py`（新增 save_report、patch_strategy、run 函式）
- Modify: `tests/test_competitor_scout.py`（新增輸出測試）

- [ ] **Step 1: 在 tests/test_competitor_scout.py 尾端追加輸出測試**

```python
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
```

- [ ] **Step 2: 確認測試失敗**

```bash
python -m pytest tests/test_competitor_scout.py::test_save_report_writes_markdown -v
```

Expected: ImportError

- [ ] **Step 3: 在 competitor_scout.py 加入 save_report、patch_strategy、run 函式**

在 `analyze_competitors` 之後加入：

```python
from datetime import datetime, timezone


def save_report(
    report_text: str,
    scraped: dict[str, list[dict]],
    report_path: Path | None = None,
    raw_path: Path | None = None,
) -> None:
    """Write competitor_report.md and competitor_raw.json."""
    if report_path is None:
        report_path = DATA_DIR / "competitor_report.md"
    if raw_path is None:
        raw_path = DATA_DIR / "competitor_raw.json"

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md = f"# 競品格式分析報告\n\n生成時間：{date_str}\n\n{report_text}\n"
    report_path.write_text(md, encoding="utf-8")
    print(f"[SCOUT] Report saved to {report_path}")

    raw_serializable = {
        account: [p["text"] for p in posts]
        for account, posts in scraped.items()
    }
    raw_path.write_text(
        json.dumps(raw_serializable, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[SCOUT] Raw data saved to {raw_path}")


def patch_strategy(report_text: str, strategy_path: Path | None = None) -> None:
    """Append competitor format observations to strategy.md."""
    if strategy_path is None:
        strategy_path = PROMPTS_DIR / "strategy.md"

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    section = f"\n\n## 競品格式觀察（{date_str}）\n\n{report_text}\n"

    current = strategy_path.read_text(encoding="utf-8") if strategy_path.exists() else ""
    strategy_path.write_text(current + section, encoding="utf-8")
    print(f"[SCOUT] strategy.md updated with competitor observations")


def run() -> None:
    """Main entry point. Run competitor scout end-to-end."""
    print("[SCOUT] === Competitor Scout Start ===")

    # 1. X account discovery
    x_accounts = discover_x_accounts()

    # 2. Scrape Threads seed accounts
    threads_scraped = scrape_accounts(COMPETITOR_THREADS_ACCOUNTS, platform="threads")

    # 3. Scrape discovered X accounts
    x_scraped = scrape_accounts(x_accounts, platform="x") if x_accounts else {}

    all_scraped = {**threads_scraped, **x_scraped}

    if not all_scraped:
        print("[SCOUT] No posts collected. Exiting.")
        send_notification("⚠️ Competitor Scout：無法抓取任何帳號資料")
        return

    total_posts = sum(len(v) for v in all_scraped.values())
    print(f"[SCOUT] Total posts collected: {total_posts} from {len(all_scraped)} accounts")

    # 4. Analyze
    print("[SCOUT] Analyzing with Claude...")
    report_text = analyze_competitors(all_scraped)

    # 5. Save outputs
    save_report(report_text, all_scraped)

    # 6. Show report preview
    print("\n" + "=" * 60)
    print(report_text[:1000])
    print("=" * 60)

    # 7. CLI confirmation gate
    answer = input("\n是否將競品格式觀察更新到 prompts/strategy.md？[y/N] ").strip().lower()
    if answer == "y":
        patch_strategy(report_text)
        print("[SCOUT] strategy.md updated.")
    else:
        print("[SCOUT] strategy.md unchanged.")

    # 8. Telegram notification
    account_list = ", ".join(f"@{a}" for a in all_scraped.keys())
    send_notification(
        f"📊 *競品分析完成*\n"
        f"帳號：{account_list}\n"
        f"貼文總數：{total_posts}\n"
        f"報告：data/competitor_report.md"
    )

    print("[SCOUT] === Done ===")


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: 在 competitor_scout.py 頂部補上缺少的 import**

確認 `competitor_scout.py` 頂部有以下所有 import（合併進現有 import 區塊）：

```python
from __future__ import annotations
import json
import anthropic
from datetime import datetime, timezone
from pathlib import Path
from orchestrator.config import (
    APIFY_API_TOKEN,
    ANTHROPIC_API_KEY,
    COMPETITOR_THREADS_ACCOUNTS,
    COMPETITOR_X_SEARCH_KEYWORDS,
    COMPETITOR_POSTS_PER_ACCOUNT,
    COMPETITOR_X_TOP_N,
    COMPETITOR_X_MAX_FOLLOWERS,
    DATA_DIR,
    PROMPTS_DIR,
)
from orchestrator.apify_client import run_actor, ApifyError
from orchestrator.notify import send_notification
```

- [ ] **Step 5: 確認所有測試通過**

```bash
python -m pytest tests/test_competitor_scout.py -v
```

Expected: 14 PASSED

- [ ] **Step 6: Commit**

```bash
git add orchestrator/competitor_scout.py tests/test_competitor_scout.py
git commit -m "feat: add output layer, CLI confirmation gate, and run() entrypoint"
```

---

## Task 7: 加入 `__main__` 入口 + 全套測試最終確認

**Files:**
- Modify: `orchestrator/competitor_scout.py`（確認 `__main__` 區塊）
- No new files

- [ ] **Step 1: 確認 competitor_scout.py 底部有 `__main__` 區塊**

```python
if __name__ == "__main__":
    run()
```

（Task 6 Step 3 已加入，確認存在即可）

- [ ] **Step 2: 跑全套測試確認無回歸**

```bash
cd /Users/hua/autoresearch_threads
python -m pytest tests/ -v --tb=short
```

Expected: 全部 PASSED，無 FAILED

- [ ] **Step 3: 確認模組可正常 import（不執行）**

```bash
python -c "from orchestrator.competitor_scout import run, discover_x_accounts, scrape_accounts, analyze_competitors, save_report, patch_strategy; print('OK')"
```

Expected:
```
OK
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: competitor scout complete — Apify scraper + Claude analysis + CLI gate"
```

---

## 執行方式（實作完成後）

```bash
# 需先在 .env 填入 APIFY_API_TOKEN
python -m orchestrator.competitor_scout
```

執行後會：
1. 自動發現 X 高互動 AI 帳號
2. 爬取 Threads 種子帳號 + 發現的 X 帳號
3. 用 Claude 分析格式策略
4. 顯示報告預覽
5. 詢問是否更新 strategy.md
6. 傳送 Telegram 通知
