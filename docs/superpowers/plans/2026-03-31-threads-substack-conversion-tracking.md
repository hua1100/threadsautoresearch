# Threads → Substack 轉換追蹤閉環 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated closed loop: track Threads→Substack conversion rates, coordinate newsletter topics with CTA posts, auto-reply with Substack links, and feed conversion data back into strategy decisions.

**Architecture:** Extend SubstackClient to capture per-source traffic+subscribers and detect new publications. Strategy Agent outputs a weekly newsletter topic; Newsletter Agent generates a topic-driven draft; Content Agent auto-detects publication and enables CTA posts that auto-reply with the link. All conversion data feeds back into the next Strategy Agent cycle.

**Tech Stack:** Python 3.14, anthropic SDK, httpx, Threads Graph API, Substack internal API, pytest

**Spec:** `docs/superpowers/specs/2026-03-31-threads-substack-conversion-tracking-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `orchestrator/substack_client.py` | Multi-dim growth sources, threads_funnel, fetch_latest_post |
| Modify | `orchestrator/threads_client.py` | reply_to_id on create_post, new reply_to_post |
| Modify | `orchestrator/deploy.py` | Auto-reply with newsletter link on 電子報CTA posts |
| Modify | `orchestrator/strategy_agent.py` | threads_funnel in prompt, newsletter topic output, init newsletter_status |
| Modify | `orchestrator/newsletter_agent.py` | Topic-driven draft, update newsletter_status to draft |
| Modify | `orchestrator/main.py` | Auto-detect new Substack publication, update newsletter_status |
| Modify | `prompts/program.md` | Add 電子報CTA to cta dimension |
| Modify | `tests/test_substack_client.py` | Tests for new snapshot format + fetch_latest_post |
| Modify | `tests/test_threads_client.py` | Tests for reply_to_id + reply_to_post |
| Modify | `tests/test_deploy.py` | Tests for CTA auto-reply logic |
| Modify | `tests/test_strategy_agent.py` | Tests for threads_funnel prompt + newsletter_status init |
| Modify | `tests/test_newsletter_agent.py` | Tests for topic-driven draft + status update |
| Modify | `tests/test_main.py` | Tests for check_newsletter_status |

---

### Task 1: SubstackClient — multi-dim growth sources + threads_funnel

**Files:**
- Modify: `orchestrator/substack_client.py:32-59`
- Modify: `tests/test_substack_client.py`

- [ ] **Step 1: Write failing tests for new snapshot format**

Add to `tests/test_substack_client.py`:

```python
def test_fetch_snapshot_multidim_growth_sources():
    """growth_sources includes traffic and new_subscribers per source."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_summary = {
        "subscribers": 0,
        "totalEmail": 23,
        "appSubscribers": 4,
        "openRate": 35.7,
    }
    mock_growth = {
        "sourceMetrics": [
            {
                "source": "threads.net",
                "metrics": [
                    {"name": "Traffic", "total": 5},
                    {"name": "Subscribers", "total": 2},
                    {"name": "Revenue", "total": 0},
                ],
                "children": [],
            },
            {
                "source": "direct",
                "metrics": [
                    {"name": "Traffic", "total": 33},
                    {"name": "Subscribers", "total": 3},
                    {"name": "Revenue", "total": 0},
                ],
                "children": [],
            },
        ]
    }

    with patch.object(client, "_get", side_effect=[mock_summary, mock_growth]):
        snapshot = client.fetch_snapshot()

    # growth_sources now has traffic + new_subscribers
    sources = {s["source"]: s for s in snapshot["growth_sources"]}
    assert sources["threads.net"]["traffic"] == 5
    assert sources["threads.net"]["new_subscribers"] == 2
    assert sources["direct"]["traffic"] == 33
    assert sources["direct"]["new_subscribers"] == 3


def test_fetch_snapshot_threads_funnel():
    """threads_funnel extracts threads.net data with conversion rate."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_summary = {"totalEmail": 10, "appSubscribers": 0, "openRate": 0}
    mock_growth = {
        "sourceMetrics": [
            {
                "source": "threads.net",
                "metrics": [
                    {"name": "Traffic", "total": 20},
                    {"name": "Subscribers", "total": 4},
                ],
                "children": [],
            },
        ]
    }

    with patch.object(client, "_get", side_effect=[mock_summary, mock_growth]):
        snapshot = client.fetch_snapshot()

    funnel = snapshot["threads_funnel"]
    assert funnel["traffic"] == 20
    assert funnel["new_subscribers"] == 4
    assert abs(funnel["conversion_rate"] - 20.0) < 0.1  # 4/20 = 20%


def test_fetch_snapshot_threads_funnel_zero_traffic():
    """threads_funnel conversion_rate is 0 when traffic is 0."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_summary = {"totalEmail": 10, "appSubscribers": 0, "openRate": 0}
    mock_growth = {"sourceMetrics": []}

    with patch.object(client, "_get", side_effect=[mock_summary, mock_growth]):
        snapshot = client.fetch_snapshot()

    funnel = snapshot["threads_funnel"]
    assert funnel["traffic"] == 0
    assert funnel["new_subscribers"] == 0
    assert funnel["conversion_rate"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_substack_client.py -v`
Expected: 3 new tests FAIL (old growth_sources format doesn't match)

- [ ] **Step 3: Update fetch_snapshot with multi-dim growth sources + threads_funnel**

Replace the growth_sources parsing and return block in `orchestrator/substack_client.py`. The full `fetch_snapshot` method becomes:

```python
    def fetch_snapshot(self) -> dict:
        """Fetch weekly snapshot: subscribers, open_rate, growth_sources, threads_funnel."""
        if not self.sid:
            raise ValueError("SUBSTACK_SID not configured")

        summary = self._get("/api/v1/publish-dashboard/summary")
        growth = self._get("/api/v1/publication/stats/growth/sources")

        # Parse growth sources — extract Traffic and Subscribers per source
        growth_sources = []
        threads_traffic = 0
        threads_subs = 0
        for m in growth.get("sourceMetrics", []):
            metrics_by_name = {
                metric["name"]: metric.get("total", 0)
                for metric in m.get("metrics", [])
            }
            traffic = metrics_by_name.get("Traffic", 0)
            new_subscribers = metrics_by_name.get("Subscribers", 0)
            source_name = m["source"]
            growth_sources.append({
                "source": source_name,
                "traffic": traffic,
                "new_subscribers": new_subscribers,
            })
            if source_name == "threads.net":
                threads_traffic = traffic
                threads_subs = new_subscribers

        subscribers = summary.get("totalEmail", 0) + summary.get("appSubscribers", 0)
        total_email = summary.get("totalEmail", 0)
        open_rate_raw = summary.get("openRate", 0)
        # Substack API returns open rate already as percentage (e.g. 25.9 = 25.9%)
        open_rate = round(float(open_rate_raw), 1) if open_rate_raw else 0.0

        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "subscribers": subscribers,
            "total_email": total_email,
            "open_rate": open_rate,
            "growth_sources": growth_sources,
            "threads_funnel": {
                "traffic": threads_traffic,
                "new_subscribers": threads_subs,
                "conversion_rate": round(threads_subs / threads_traffic * 100, 1) if threads_traffic > 0 else 0.0,
            },
        }
```

- [ ] **Step 4: Update existing tests for new growth_sources format**

The existing `test_fetch_snapshot_structure` and `test_growth_sources_filtered` use the old flat format. Replace them entirely in `tests/test_substack_client.py`:

```python
def test_fetch_snapshot_structure():
    """fetch_snapshot returns dict with required keys."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_summary = {
        "subscribers": 0,
        "totalEmail": 23,
        "appSubscribers": 4,
        "openRate": 35.7,
    }
    mock_growth = {
        "sourceMetrics": [
            {
                "source": "substack",
                "metrics": [
                    {"name": "Traffic", "total": 12},
                    {"name": "Subscribers", "total": 1},
                ],
                "children": [],
            },
        ]
    }

    with patch.object(client, "_get", side_effect=[mock_summary, mock_growth]):
        snapshot = client.fetch_snapshot()

    assert snapshot["subscribers"] == 27  # totalEmail(23) + appSubscribers(4)
    assert snapshot["total_email"] == 23
    assert abs(snapshot["open_rate"] - 35.7) < 0.1
    assert len(snapshot["growth_sources"]) == 1
    assert snapshot["growth_sources"][0]["source"] == "substack"
    assert snapshot["growth_sources"][0]["traffic"] == 12
    assert snapshot["growth_sources"][0]["new_subscribers"] == 1
    assert "date" in snapshot
    assert "threads_funnel" in snapshot
```

Remove `test_growth_sources_filtered` — it tested the old `category == "Traffic"` filter which no longer applies. The new `test_fetch_snapshot_multidim_growth_sources` covers this.

- [ ] **Step 5: Run all tests**

Run: `.venv/bin/python -m pytest tests/test_substack_client.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add orchestrator/substack_client.py tests/test_substack_client.py
git commit -m "feat: multi-dim growth sources and threads_funnel in SubstackClient"
```

---

### Task 2: SubstackClient — fetch_latest_post

**Files:**
- Modify: `orchestrator/substack_client.py`
- Modify: `tests/test_substack_client.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_substack_client.py`:

```python
def test_fetch_latest_post_returns_dict():
    """fetch_latest_post returns title, url, date from archive API."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_archive = [
        {
            "title": "AI Agent 深度分析",
            "canonical_url": "https://hualeee.substack.com/p/ai-agent",
            "post_date": "2026-03-31T01:48:41.971Z",
            "type": "newsletter",
        }
    ]

    with patch.object(client, "_get", return_value=mock_archive):
        result = client.fetch_latest_post()

    assert result["title"] == "AI Agent 深度分析"
    assert result["url"] == "https://hualeee.substack.com/p/ai-agent"
    assert result["date"] == "2026-03-31T01:48:41.971Z"


def test_fetch_latest_post_empty_archive():
    """fetch_latest_post returns None when archive is empty."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")

    with patch.object(client, "_get", return_value=[]):
        result = client.fetch_latest_post()

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_substack_client.py::test_fetch_latest_post_returns_dict tests/test_substack_client.py::test_fetch_latest_post_empty_archive -v`
Expected: FAIL — `SubstackClient` has no attribute `fetch_latest_post`

- [ ] **Step 3: Implement fetch_latest_post**

Add to `orchestrator/substack_client.py` after the `fetch_snapshot` method:

```python
    def fetch_latest_post(self) -> dict | None:
        """Fetch the most recently published newsletter post."""
        posts = self._get("/api/v1/archive", params={"sort": "new", "limit": 1})
        if posts:
            return {
                "title": posts[0]["title"],
                "url": posts[0]["canonical_url"],
                "date": posts[0]["post_date"],
            }
        return None
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_substack_client.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/substack_client.py tests/test_substack_client.py
git commit -m "feat: add fetch_latest_post to SubstackClient"
```

---

### Task 3: threads_client — reply_to_id + reply_to_post

**Files:**
- Modify: `orchestrator/threads_client.py:8-36`
- Modify: `tests/test_threads_client.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_threads_client.py`:

```python
from orchestrator.threads_client import reply_to_post


def test_create_post_with_reply_to_id():
    """create_post sends reply_to_id in payload when provided."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "container_reply"}
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.threads_client.requests.post", return_value=mock_resp) as mock_post:
        result = create_post("Reply text", reply_to_id="media_parent")

    assert result == "container_reply"
    payload = mock_post.call_args[1]["json"]
    assert payload["reply_to_id"] == "media_parent"


def test_create_post_without_reply_to_id():
    """create_post does not include reply_to_id when not provided."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "container_normal"}
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.threads_client.requests.post", return_value=mock_resp) as mock_post:
        result = create_post("Normal post")

    assert result == "container_normal"
    payload = mock_post.call_args[1]["json"]
    assert "reply_to_id" not in payload


def test_reply_to_post_creates_and_publishes():
    """reply_to_post calls create_post with reply_to_id then publish_post."""
    with patch("orchestrator.threads_client.create_post", return_value="container_r") as mock_create, \
         patch("orchestrator.threads_client.publish_post", return_value="media_r") as mock_publish, \
         patch("orchestrator.threads_client.time.sleep"):
        result = reply_to_post("parent_123", "回覆文字")

    mock_create.assert_called_once_with("回覆文字", reply_to_id="parent_123")
    mock_publish.assert_called_once_with("container_r")
    assert result == "media_r"


def test_reply_to_post_returns_none_on_create_failure():
    """reply_to_post returns None if create_post fails."""
    with patch("orchestrator.threads_client.create_post", return_value=None):
        result = reply_to_post("parent_123", "回覆文字")

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_threads_client.py -v`
Expected: ImportError on `reply_to_post`, signature error on `create_post`

- [ ] **Step 3: Implement changes**

In `orchestrator/threads_client.py`, modify `create_post` to accept `reply_to_id`:

```python
def create_post(text: str, reply_to_id: str | None = None) -> str | None:
    url = f"{BASE_URL}/{THREADS_USER_ID}/threads"
    payload = {
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN,
    }
    if reply_to_id:
        payload["reply_to_id"] = reply_to_id
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json().get("id")
```

Add `reply_to_post` after `post_text`:

```python
def reply_to_post(media_id: str, text: str) -> str | None:
    """Reply to an existing post with a comment."""
    creation_id = create_post(text, reply_to_id=media_id)
    if not creation_id:
        return None
    time.sleep(30)
    return publish_post(creation_id)
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_threads_client.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/threads_client.py tests/test_threads_client.py
git commit -m "feat: add reply_to_id support and reply_to_post in threads_client"
```

---

### Task 4: deploy — auto-reply with newsletter link

**Files:**
- Modify: `orchestrator/deploy.py:15-53`
- Modify: `tests/test_deploy.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_deploy.py`:

```python
def test_deploy_replies_with_newsletter_link_on_cta():
    """When cta is 電子報CTA and newsletter is published, deploy auto-replies."""
    posts = [
        {
            "text": "AI 深度分析",
            "dimensions": {"cta": "電子報CTA"},
            "hypothesis": "test CTA",
        },
    ]
    newsletter_status = {"status": "published", "url": "https://hualeee.substack.com/p/test"}

    with patch("orchestrator.deploy.threads_client") as mock_tc, \
         patch("orchestrator.deploy.read_json") as mock_read, \
         patch("orchestrator.deploy.write_json"), \
         patch("orchestrator.deploy.sanitize_post_text", side_effect=lambda x: x):

        mock_tc.post_text.return_value = "media_cta"
        mock_tc.get_post_permalink.return_value = "https://threads.com/t/123"
        # First call: posts.json, second call: newsletter_status.json
        mock_read.side_effect = [[], newsletter_status]

        result = deploy(posts)

    mock_tc.reply_to_post.assert_called_once_with(
        "media_cta",
        "完整深度分析在這裡 👉 https://hualeee.substack.com/p/test",
    )


def test_deploy_skips_reply_when_newsletter_not_published():
    """When newsletter is not published, deploy does not reply."""
    posts = [
        {
            "text": "AI 深度分析",
            "dimensions": {"cta": "電子報CTA"},
            "hypothesis": "test CTA",
        },
    ]
    newsletter_status = {"status": "draft", "url": ""}

    with patch("orchestrator.deploy.threads_client") as mock_tc, \
         patch("orchestrator.deploy.read_json") as mock_read, \
         patch("orchestrator.deploy.write_json"), \
         patch("orchestrator.deploy.sanitize_post_text", side_effect=lambda x: x):

        mock_tc.post_text.return_value = "media_cta"
        mock_tc.get_post_permalink.return_value = "https://threads.com/t/123"
        mock_read.side_effect = [[], newsletter_status]

        deploy(posts)

    mock_tc.reply_to_post.assert_not_called()


def test_deploy_skips_reply_when_cta_is_not_newsletter():
    """When cta is not 電子報CTA, deploy does not attempt reply."""
    posts = [
        {
            "text": "Hello",
            "dimensions": {"cta": "留言互動"},
            "hypothesis": "test",
        },
    ]

    with patch("orchestrator.deploy.threads_client") as mock_tc, \
         patch("orchestrator.deploy.read_json", return_value=[]), \
         patch("orchestrator.deploy.write_json"), \
         patch("orchestrator.deploy.sanitize_post_text", side_effect=lambda x: x):

        mock_tc.post_text.return_value = "media_normal"
        mock_tc.get_post_permalink.return_value = "https://threads.com/t/456"

        deploy(posts)

    mock_tc.reply_to_post.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_deploy.py -v`
Expected: New tests FAIL — deploy doesn't call reply_to_post or read newsletter_status.json

- [ ] **Step 3: Implement auto-reply in deploy**

Replace the `deploy` function in `orchestrator/deploy.py`:

```python
def deploy(posts: list[dict]) -> list[dict]:
    published = []
    posts_db = read_json(DATA_DIR / "posts.json")
    if not isinstance(posts_db, list):
        posts_db = []

    for post in posts:
        text = sanitize_post_text(post["text"])

        if len(text) > 500:
            text = text[:497] + "..."

        try:
            media_id = threads_client.post_text(text)
        except Exception as e:
            print(f"[DEPLOY] Failed to publish: {e}")
            media_id = None

        permalink = None
        if media_id:
            try:
                permalink = threads_client.get_post_permalink(media_id)
            except Exception:
                pass

        # Auto-reply with newsletter link for 電子報CTA posts
        if media_id and post.get("dimensions", {}).get("cta") == "電子報CTA":
            newsletter = read_json(DATA_DIR / "newsletter_status.json")
            if isinstance(newsletter, dict) and newsletter.get("status") == "published":
                try:
                    url = newsletter["url"]
                    reply_text = f"完整深度分析在這裡 👉 {url}"
                    threads_client.reply_to_post(media_id, reply_text)
                    print(f"[DEPLOY] Auto-replied with newsletter link: {url}")
                except Exception as e:
                    print(f"[DEPLOY] Failed to reply with newsletter link: {e}")

        record = {
            "media_id": media_id,
            "permalink": permalink,
            "text": text,
            "dimensions": post.get("dimensions", {}),
            "hypothesis": post.get("hypothesis", ""),
            "published_at": datetime.now(timezone.utc).isoformat(),
            "scheduled_hour": post.get("scheduled_hour"),
        }
        published.append(record)
        posts_db.append(record)

    write_json(DATA_DIR / "posts.json", posts_db)
    return published
```

- [ ] **Step 4: Fix existing test to handle new read_json call**

The existing `test_deploy_publishes_and_records` mocks `read_json` to return `[]`. The deploy function now calls `read_json` potentially twice (posts.json + newsletter_status.json). Since the existing test post has `cta: undefined` (no dimensions.cta), the second call won't happen. No change needed for the existing test.

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_deploy.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add orchestrator/deploy.py tests/test_deploy.py
git commit -m "feat: auto-reply with newsletter link on 電子報CTA posts"
```

---

### Task 5: program.md — add 電子報CTA option

**Files:**
- Modify: `prompts/program.md:50`

- [ ] **Step 1: Update cta dimension**

In `prompts/program.md`, change line 50 from:

```
| cta | 無CTA、留言互動、分享給朋友 |
```

to:

```
| cta | 無CTA、留言互動、分享給朋友、電子報CTA |
```

- [ ] **Step 2: Commit**

```bash
git add prompts/program.md
git commit -m "feat: add 電子報CTA to cta dimension options"
```

---

### Task 6: strategy_agent — threads_funnel + newsletter topic + init status

**Files:**
- Modify: `orchestrator/strategy_agent.py`
- Modify: `tests/test_strategy_agent.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_strategy_agent.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_strategy_agent.py::test_strategy_agent_includes_threads_funnel_in_prompt tests/test_strategy_agent.py::test_strategy_agent_inits_newsletter_status -v`
Expected: FAIL

- [ ] **Step 3: Implement strategy_agent changes**

Replace the full `run()` function in `orchestrator/strategy_agent.py`:

```python
"""Strategy Agent: 分析過去 7 天數據，更新 prompts/strategy.md"""
import json
import re
import anthropic
from datetime import datetime, timezone
from orchestrator.config import ANTHROPIC_API_KEY, PROMPTS_DIR, DATA_DIR, SUBSTACK_SID, SUBSTACK_SUBDOMAIN
from orchestrator.substack_client import SubstackClient
from orchestrator.utils import load_recent_experiments, read_json, write_json


def _extract_newsletter_topic(strategy_text: str) -> str:
    """Extract newsletter topic from strategy.md content."""
    match = re.search(r"## 本週電子報主題\s*\n(.+)", strategy_text)
    return match.group(1).strip() if match else ""


def run() -> None:
    experiments = load_recent_experiments(days=7)
    resource = ""
    resource_path = PROMPTS_DIR / "resource.md"
    if resource_path.exists():
        resource = resource_path.read_text(encoding="utf-8")

    # Fetch and store Substack snapshot (skip if not configured)
    substack_snapshot = None
    if SUBSTACK_SID:
        try:
            client = SubstackClient(subdomain=SUBSTACK_SUBDOMAIN, sid=SUBSTACK_SID)
            substack_snapshot = client.fetch_snapshot()
            metrics_path = DATA_DIR / "substack_metrics.json"
            existing = read_json(metrics_path)
            if not isinstance(existing, list):
                existing = []
            existing.append(substack_snapshot)
            write_json(metrics_path, existing)
            print(f"[STRATEGY] Substack snapshot saved: {substack_snapshot['subscribers']} subscribers")
        except Exception as e:
            print(f"[STRATEGY] Substack snapshot failed (skipping): {e}")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    exp_summary = json.dumps(experiments, ensure_ascii=False, indent=2)

    substack_section = ""
    if substack_snapshot:
        sources_str = ", ".join(
            f"{s['source']}: {s.get('traffic', s.get('value', 0))}"
            for s in substack_snapshot.get("growth_sources", [])
        )
        substack_section = (
            f"\n## Substack 電子報現況\n"
            f"- 訂閱數：{substack_snapshot.get('subscribers', 0)}\n"
            f"- Open Rate：{substack_snapshot.get('open_rate', 0)}%\n"
            f"- 流量來源：{sources_str}\n"
        )

        funnel = substack_snapshot.get("threads_funnel")
        if funnel:
            substack_section += (
                f"\n## Threads → 電子報轉換漏斗\n"
                f"- Threads 導流：{funnel['traffic']} 次點擊\n"
                f"- 新增訂閱：{funnel['new_subscribers']}\n"
                f"- 轉換率：{funnel['conversion_rate']}%\n"
            )

    prompt = f"""你是一個 Threads 內容策略師。分析過去 7 天的貼文數據，制定本週流量策略。

## 過去 7 天實驗數據
{exp_summary}

## 累積學習
{resource}
{substack_section}

請制定本週策略，輸出以下格式的 Markdown（直接輸出，不要有前綴說明）：

# 本週流量策略（{date_str} 更新）

## 目標
[衝觸及 / 導流電子報（主題：XXX）] 以及原因（1-2 句）

## CTA 使用時機
當貼文主題涉及以下任一時加電子報 CTA：
- [主題 A]
- [主題 B]

## CTA 文案參考
- [範例 1]
- [範例 2]

## 本週不加 CTA 的主題
- [主題列表]

## 本週電子報主題
[一句話描述本週電子報要寫的主題，基於最高互動的貼文方向]"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    strategy = response.content[0].text.strip()
    (PROMPTS_DIR / "strategy.md").write_text(strategy, encoding="utf-8")
    print(f"[STRATEGY] strategy.md updated ({len(strategy)} chars)")

    # Initialize newsletter_status.json
    topic = _extract_newsletter_topic(strategy)
    newsletter_status = {
        "week": date_str,
        "topic": topic,
        "status": "pending",
    }
    write_json(DATA_DIR / "newsletter_status.json", newsletter_status)
    print(f"[STRATEGY] newsletter_status.json initialized (topic: {topic})")


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Update existing snapshot test for new growth_sources format**

In `test_strategy_agent_saves_substack_snapshot`, update `fake_snapshot` to include the new fields:

```python
    fake_snapshot = {
        "date": "2026-03-31",
        "subscribers": 30,
        "total_email": 23,
        "open_rate": 38.5,
        "growth_sources": [{"source": "substack", "traffic": 15, "new_subscribers": 1}],
        "threads_funnel": {"traffic": 0, "new_subscribers": 0, "conversion_rate": 0.0},
    }
```

And update the prompt assertion to use the new format (`traffic` instead of `value`):

```python
    prompt_text = call_args[1]["messages"][0]["content"]
    assert "訂閱數：30" in prompt_text
```

This assertion still works because the substack_section format hasn't changed for the subscriber count line.

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_strategy_agent.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add orchestrator/strategy_agent.py tests/test_strategy_agent.py
git commit -m "feat: add threads_funnel to strategy prompt and init newsletter_status"
```

---

### Task 7: newsletter_agent — topic-driven draft + status update

**Files:**
- Modify: `orchestrator/newsletter_agent.py`
- Modify: `tests/test_newsletter_agent.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_newsletter_agent.py`:

```python
def test_newsletter_uses_topic_from_status(tmp_path, monkeypatch):
    """Newsletter prompt is driven by topic from newsletter_status.json."""
    monkeypatch.setattr("orchestrator.newsletter_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr("orchestrator.newsletter_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "")

    (tmp_path / "newsletter_status.json").write_text(
        json.dumps({"week": "2026-03-31", "topic": "AI Agent 自動化實戰", "status": "pending"})
    )

    with patch("orchestrator.newsletter_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.newsletter_agent.anthropic.Anthropic") as MockAnthropic:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="草稿內容")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp

        newsletter_agent.run()

    prompt = MockAnthropic.return_value.messages.create.call_args[1]["messages"][0]["content"]
    assert "AI Agent 自動化實戰" in prompt


def test_newsletter_updates_status_to_draft(tmp_path, monkeypatch):
    """After generating draft, newsletter_status.json is updated to draft."""
    monkeypatch.setattr("orchestrator.newsletter_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr("orchestrator.newsletter_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "")

    (tmp_path / "newsletter_status.json").write_text(
        json.dumps({"week": "2026-03-31", "topic": "測試主題", "status": "pending"})
    )

    with patch("orchestrator.newsletter_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.newsletter_agent.anthropic.Anthropic") as MockAnthropic:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="草稿")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp

        newsletter_agent.run()

    status = json.loads((tmp_path / "newsletter_status.json").read_text())
    assert status["status"] == "draft"
    assert status["topic"] == "測試主題"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_newsletter_agent.py::test_newsletter_uses_topic_from_status tests/test_newsletter_agent.py::test_newsletter_updates_status_to_draft -v`
Expected: FAIL

- [ ] **Step 3: Implement newsletter_agent changes**

Replace `orchestrator/newsletter_agent.py`:

```python
"""Newsletter Agent: 生成 Substack 草稿並 email 給作者"""
import json
import subprocess
import anthropic
from datetime import datetime, timezone
from orchestrator.config import (
    ANTHROPIC_API_KEY, PROMPTS_DIR, DRAFTS_DIR, NEWSLETTER_EMAIL, DATA_DIR
)
from orchestrator.utils import load_recent_experiments, read_json, write_json


def run() -> None:
    strategy = ""
    strategy_path = PROMPTS_DIR / "strategy.md"
    if strategy_path.exists():
        strategy = strategy_path.read_text(encoding="utf-8")

    swipe = ""
    swipe_path = PROMPTS_DIR / "swipe_file.md"
    if swipe_path.exists():
        swipe = swipe_path.read_text(encoding="utf-8")

    experiments = load_recent_experiments(days=7)
    top_posts = sorted(
        [post for exp in experiments for post in exp.get("results", [])],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )[:5]
    top_summary = json.dumps(top_posts, ensure_ascii=False, indent=2)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Read newsletter topic from status file
    newsletter_status = read_json(DATA_DIR / "newsletter_status.json")
    topic = ""
    if isinstance(newsletter_status, dict):
        topic = newsletter_status.get("topic", "")

    topic_instruction = (
        f"本週電子報主題是「{topic}」，以此為核心，參考相關的高表現貼文寫深度版本。"
        if topic
        else "根據本週最佳表現貼文寫電子報。"
    )

    prompt = f"""你是一個 AI 電子報作者，為 Substack 電子報（hualeee.substack.com）撰寫本週內容。

## 本週 Threads 策略
{strategy}

## 高表現貼文範例庫
{swipe}

## 本週最佳表現貼文數據
{top_summary}

{topic_instruction}

請撰寫一篇完整的電子報草稿：
- 繁體中文
- 格式：標題、引言、正文（3-5 個小節）、結語
- 字數：800-1200 字

只輸出電子報正文，不要額外說明。"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    draft = response.content[0].text.strip()

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = DRAFTS_DIR / f"newsletter_{date_str}.md"
    draft_path.write_text(draft, encoding="utf-8")
    print(f"[NEWSLETTER] Draft saved to {draft_path}")

    # Update newsletter_status to draft
    if isinstance(newsletter_status, dict):
        newsletter_status["status"] = "draft"
        write_json(DATA_DIR / "newsletter_status.json", newsletter_status)

    # Build funnel summary from latest Substack snapshot
    funnel_section = ""
    metrics_path = DATA_DIR / "substack_metrics.json"
    metrics_history = read_json(metrics_path)
    if isinstance(metrics_history, list) and metrics_history:
        latest = metrics_history[-1]
        prev = metrics_history[-2] if len(metrics_history) >= 2 else None
        delta = (
            latest.get("subscribers") - prev.get("subscribers")
            if prev
            and latest.get("subscribers") is not None
            and prev.get("subscribers") is not None
            else None
        )
        if delta is None:
            delta_str = "首次記錄"
        elif delta > 0:
            delta_str = f"+{delta}"
        elif delta < 0:
            delta_str = str(delta)
        else:
            delta_str = "±0"
        sources_str = ", ".join(
            f"{s['source']}: {s.get('traffic', s.get('value', 0))}"
            for s in latest.get("growth_sources", [])
        ) or "無資料"

        # Add threads funnel to summary
        threads_funnel_str = ""
        funnel = latest.get("threads_funnel")
        if funnel and funnel.get("traffic", 0) > 0:
            threads_funnel_str = (
                f"\n- Threads 導流：{funnel['traffic']} 次 → {funnel['new_subscribers']} 訂閱"
                f"（轉換率 {funnel['conversion_rate']}%）"
            )

        funnel_section = (
            f"\n\n## Substack 漏斗摘要（{latest.get('date', '')}）\n"
            f"- 訂閱數：{latest.get('subscribers', 0)}（{delta_str} 本週）\n"
            f"- Open Rate：{latest.get('open_rate', 0)}%\n"
            f"- 流量來源：{sources_str}"
            f"{threads_funnel_str}\n"
        )

    if not NEWSLETTER_EMAIL:
        print("[NEWSLETTER] NEWSLETTER_EMAIL not set, skipping email")
    else:
        subject = f"[電子報草稿] {date_str}"
        body = f"本週 Top 5 貼文數據：\n{top_summary[:500]}{funnel_section}\n\n---草稿---\n\n{draft}"
        result = subprocess.run(
            ["mail", "-s", subject, NEWSLETTER_EMAIL],
            input=body.encode("utf-8"),
            capture_output=True,
        )
        if result.returncode == 0:
            print(f"[NEWSLETTER] Email sent to {NEWSLETTER_EMAIL}")
        else:
            print(f"[NEWSLETTER] Email failed: {result.stderr.decode()}")


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Update existing tests for newsletter_status.json side effects**

The existing tests (`test_run_saves_draft_file`, `test_run_sends_email`) use `tmp_path` via `patch`. They don't create `newsletter_status.json`, so `read_json` will return `[]` (default), topic will be empty, and status update will be skipped. This is the correct fallback — no changes needed to existing tests.

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_newsletter_agent.py -v`
Expected: All 8 tests PASS

- [ ] **Step 6: Commit**

```bash
git add orchestrator/newsletter_agent.py tests/test_newsletter_agent.py
git commit -m "feat: topic-driven newsletter draft and status update"
```

---

### Task 8: main.py — auto-detect new Substack publication

**Files:**
- Modify: `orchestrator/main.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_main.py`:

```python
import json
import tempfile
from pathlib import Path


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_main.py::test_check_newsletter_status_detects_new_publication -v`
Expected: ImportError — `check_newsletter_status` doesn't exist

- [ ] **Step 3: Implement check_newsletter_status in main.py**

Add these imports at the top of `orchestrator/main.py`:

```python
from orchestrator.config import PHASE_SWITCH_FOLLOWER_THRESHOLD, DATA_DIR, SUBSTACK_SID, SUBSTACK_SUBDOMAIN
from orchestrator.substack_client import SubstackClient
from orchestrator.utils import read_json, write_json
```

Add the `check_newsletter_status` function before `run()`:

```python
def check_newsletter_status():
    """Auto-detect new Substack publication, update newsletter_status.json."""
    if not SUBSTACK_SID:
        return
    newsletter = read_json(DATA_DIR / "newsletter_status.json")
    if not isinstance(newsletter, dict):
        return
    if newsletter.get("status") == "published":
        return

    try:
        client = SubstackClient(subdomain=SUBSTACK_SUBDOMAIN, sid=SUBSTACK_SID)
        latest = client.fetch_latest_post()
    except Exception as e:
        print(f"[NEWSLETTER] Failed to check Substack: {e}")
        return

    if not latest:
        return

    if latest["url"] != newsletter.get("url"):
        newsletter["status"] = "published"
        newsletter["url"] = latest["url"]
        newsletter["published_at"] = latest["date"]
        write_json(DATA_DIR / "newsletter_status.json", newsletter)
        print(f"[NEWSLETTER] 偵測到新電子報: {latest['title']}")
```

Add a call to it in `run()`, after phase detection and before fetch_sources:

```python
        print(f"[0/5] Phase {phase} | 追蹤者: {follower_count}")

        check_newsletter_status()

        sources = fetch_sources()
```

- [ ] **Step 4: Update test_run_executes_full_loop**

Add `check_newsletter_status` mock to the existing full loop test:

```python
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
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_main.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS (should be ~60+ tests now)

- [ ] **Step 7: Commit**

```bash
git add orchestrator/main.py tests/test_main.py
git commit -m "feat: auto-detect new Substack publication in Content Agent"
```

---

### Task 9: Integration smoke test

**Files:**
- No new files — manual validation

- [ ] **Step 1: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v --tb=short`
Expected: All tests PASS, no warnings

- [ ] **Step 2: Dry-run the full 3-agent chain with mocks**

```bash
.venv/bin/python -c "
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from orchestrator.utils import write_json

DATA = Path('data')

# 1. Strategy Agent
print('--- Strategy Agent ---')
mock_resp = MagicMock()
mock_resp.content = [MagicMock(text='# 本週流量策略\n## 目標\n導流電子報\n## 本週電子報主題\nAI Agent 自動化')]

with patch('orchestrator.strategy_agent.anthropic.Anthropic') as MockAnthropic:
    MockAnthropic.return_value.messages.create.return_value = mock_resp
    from orchestrator.strategy_agent import run as strategy_run
    strategy_run()

status = json.loads((DATA / 'newsletter_status.json').read_text())
print(f'  newsletter_status: {status}')
assert status['status'] == 'pending'
assert status['topic'] == 'AI Agent 自動化'
print('  ✅ OK')

# 2. Newsletter Agent
print('--- Newsletter Agent ---')
mock_draft = MagicMock()
mock_draft.content = [MagicMock(text='# AI Agent 自動化深度分析\n\n草稿內容')]

with patch('orchestrator.newsletter_agent.anthropic.Anthropic') as MockAnthropic:
    MockAnthropic.return_value.messages.create.return_value = mock_draft
    from orchestrator.newsletter_agent import run as newsletter_run
    newsletter_run()

status = json.loads((DATA / 'newsletter_status.json').read_text())
assert status['status'] == 'draft'
print(f'  newsletter_status: {status}')
print('  ✅ OK')

# 3. Content Agent detects publication
print('--- Content Agent: detect publication ---')
with patch('orchestrator.main.SubstackClient') as MockClient:
    MockClient.return_value.fetch_latest_post.return_value = {
        'title': 'AI Agent 自動化',
        'url': 'https://hualeee.substack.com/p/ai-agent-auto',
        'date': '2026-03-31T12:00:00Z',
    }
    from orchestrator.main import check_newsletter_status
    check_newsletter_status()

status = json.loads((DATA / 'newsletter_status.json').read_text())
assert status['status'] == 'published'
assert 'substack.com' in status['url']
print(f'  newsletter_status: {status}')
print('  ✅ OK')

print('\n=== Full 3-agent chain: PASSED ===')
"
```

Expected: All 3 agents chain correctly, status transitions pending → draft → published

- [ ] **Step 3: Clean up test artifacts**

```bash
git checkout -- prompts/strategy.md
rm -f drafts/newsletter_*.md
git checkout -- data/newsletter_status.json 2>/dev/null || rm -f data/newsletter_status.json
```

- [ ] **Step 4: Final commit with all changes**

```bash
git add -A
git status
# If there are any remaining unstaged changes, commit them
git commit -m "chore: integration smoke test cleanup"
```
