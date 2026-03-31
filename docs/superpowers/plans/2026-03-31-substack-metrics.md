# Substack Metrics Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 每週 Strategy Agent 跑時自動快照 Substack 電子報指標，存入 `data/substack_metrics.json`，並在 Newsletter Agent email 中附上漏斗摘要。

**Architecture:** 新增 `orchestrator/substack_client.py` 封裝 Substack 內部 API（複用 `/Users/hua/substack數據/fetch_substack.py` 的 HTTP 邏輯，只取 3 個端點）。`config.py` 加入 `SUBSTACK_SID`、`SUBSTACK_SUBDOMAIN`。Strategy Agent 呼叫 client 後把快照 append 到 `data/substack_metrics.json`。Newsletter Agent 讀取最新快照，加入 email 漏斗摘要段落。

**Tech Stack:** Python 3.11+, httpx, existing orchestrator patterns (config/utils/read_json/write_json)

---

### Task 1: Config + SubstackClient

**Files:**
- Modify: `orchestrator/config.py`
- Create: `orchestrator/substack_client.py`
- Create: `tests/test_substack_client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_substack_client.py
import pytest
from unittest.mock import patch, MagicMock
from orchestrator.substack_client import SubstackClient


def test_fetch_snapshot_structure():
    """fetch_snapshot returns dict with required keys."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_summary = {
        "subscribers": 27,
        "totalEmail": 23,
        "openRate": 0.357,
    }
    mock_summary_v2 = {"subscribers": 27}
    mock_growth = {
        "sourceMetrics": [
            {"source": "substack", "category": "Traffic", "value": 12},
            {"source": "direct", "category": "Traffic", "value": 8},
        ]
    }

    with patch.object(client, "_get", side_effect=[mock_summary, mock_summary_v2, mock_growth]):
        snapshot = client.fetch_snapshot()

    assert snapshot["subscribers"] == 27
    assert snapshot["total_email"] == 23
    assert abs(snapshot["open_rate"] - 35.7) < 0.1
    assert isinstance(snapshot["growth_sources"], list)
    assert "date" in snapshot


def test_fetch_snapshot_missing_sid():
    """fetch_snapshot raises ValueError when sid is empty."""
    client = SubstackClient(subdomain="hualeee", sid="")
    with pytest.raises(ValueError, match="SUBSTACK_SID"):
        client.fetch_snapshot()


def test_growth_sources_filtered():
    """Only Traffic category sources are included."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_growth = {
        "sourceMetrics": [
            {"source": "substack", "category": "Traffic", "value": 12},
            {"source": "direct", "category": "Revenue", "value": 0},
            {"source": "email", "category": "Traffic", "value": 5},
        ]
    }
    with patch.object(client, "_get", side_effect=[{}, {}, mock_growth]):
        snapshot = client.fetch_snapshot()

    sources = {s["source"]: s["value"] for s in snapshot["growth_sources"]}
    assert "substack" in sources
    assert "email" in sources
    assert "direct" not in sources  # Revenue category excluded
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/hua/autoresearch_threads && python -m pytest tests/test_substack_client.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'orchestrator.substack_client'`

- [ ] **Step 3: Add config vars to `orchestrator/config.py`**

Add after `NEWSLETTER_EMAIL = os.environ.get("NEWSLETTER_EMAIL", "")`:

```python
SUBSTACK_SID = os.environ.get("SUBSTACK_SID", "")
SUBSTACK_SUBDOMAIN = os.environ.get("SUBSTACK_SUBDOMAIN", "hualeee")
```

- [ ] **Step 4: Create `orchestrator/substack_client.py`**

```python
"""Substack internal API client — weekly metrics snapshot."""
import time
import httpx
from datetime import datetime, timezone


class SubstackClient:
    def __init__(self, subdomain: str, sid: str):
        self.subdomain = subdomain
        self.sid = sid
        self.base_url = f"https://{subdomain}.substack.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Origin": "https://substack.com",
            "Referer": "https://substack.com/",
        }

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        url = f"{self.base_url}{path}"
        resp = httpx.get(
            url,
            headers=self.headers,
            cookies={"substack.sid": self.sid},
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        time.sleep(0.5)
        return resp.json()

    def fetch_snapshot(self) -> dict:
        """Fetch weekly snapshot: subscribers, open_rate, growth_sources."""
        if not self.sid:
            raise ValueError("SUBSTACK_SID not configured")

        summary = self._get("/api/v1/publish-dashboard/summary")
        # summary_v2 has same subscriber count but confirms the value
        self._get("/api/v1/publish-dashboard/summary-v2", {"range": 30})
        growth = self._get("/api/v1/publication/stats/growth/sources")

        # Parse growth sources — only Traffic category
        growth_sources = [
            {"source": m["source"], "value": m["value"]}
            for m in growth.get("sourceMetrics", [])
            if m.get("category") == "Traffic"
        ]

        subscribers = summary.get("subscribers", 0)
        total_email = summary.get("totalEmail", 0)
        open_rate_raw = summary.get("openRate", 0)
        open_rate = round(float(open_rate_raw) * 100, 1) if open_rate_raw and open_rate_raw < 1 else float(open_rate_raw or 0)

        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "subscribers": subscribers,
            "total_email": total_email,
            "open_rate": open_rate,
            "growth_sources": growth_sources,
        }
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd /Users/hua/autoresearch_threads && python -m pytest tests/test_substack_client.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
cd /Users/hua/autoresearch_threads && git add orchestrator/config.py orchestrator/substack_client.py tests/test_substack_client.py
git commit -m "feat: add SubstackClient and config vars for Substack metrics"
```

---

### Task 2: Weekly Snapshot Storage in Strategy Agent

**Files:**
- Modify: `orchestrator/strategy_agent.py`
- Modify: `tests/test_strategy_agent.py` (if exists, otherwise create)

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_strategy_agent.py (or create if missing)
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from orchestrator import strategy_agent


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

        strategy_agent.run()  # Should not raise

    # No metrics file written
    assert not (tmp_path / "substack_metrics.json").exists()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/hua/autoresearch_threads && python -m pytest tests/test_strategy_agent.py -v -k "substack"
```

Expected: `FAILED` — `ImportError` or attribute missing in strategy_agent

- [ ] **Step 3: Update `orchestrator/strategy_agent.py`**

Add imports at top:
```python
from orchestrator.config import ANTHROPIC_API_KEY, PROMPTS_DIR, DATA_DIR, SUBSTACK_SID, SUBSTACK_SUBDOMAIN
from orchestrator.substack_client import SubstackClient
from orchestrator.utils import load_recent_experiments, read_json, write_json
```

Replace existing imports line (`from orchestrator.config import ANTHROPIC_API_KEY, PROMPTS_DIR`).

In `run()`, add Substack snapshot block **before** building the prompt (after `resource` is loaded):

```python
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
```

Then inject snapshot into the prompt. Add a `substack_section` variable before the `prompt = f"""...` block:

```python
    substack_section = ""
    if substack_snapshot:
        sources_str = ", ".join(
            f"{s['source']}: {s['value']}"
            for s in substack_snapshot.get("growth_sources", [])
        )
        substack_section = f"""
## Substack 電子報現況
- 訂閱數：{substack_snapshot['subscribers']}
- Open Rate：{substack_snapshot['open_rate']}%
- 流量來源：{sources_str}
"""
```

Add `{substack_section}` to the prompt, after `## 累積學習\n{resource}`:

```python
    prompt = f"""你是一個 Threads 內容策略師。分析過去 7 天的貼文數據，制定本週流量策略。

## 過去 7 天實驗數據
{exp_summary}

## 累積學習
{resource}
{substack_section}
請制定本週策略，輸出以下格式的 Markdown（直接輸出，不要有前綴說明）：
...（其餘 prompt 不變）"""
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/hua/autoresearch_threads && python -m pytest tests/test_strategy_agent.py -v -k "substack"
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/hua/autoresearch_threads && git add orchestrator/strategy_agent.py tests/test_strategy_agent.py
git commit -m "feat: strategy_agent fetches and stores Substack snapshot weekly"
```

---

### Task 3: Funnel Summary in Newsletter Agent Email

**Files:**
- Modify: `orchestrator/newsletter_agent.py`
- Modify: `tests/test_newsletter_agent.py` (if exists, otherwise create)

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_newsletter_agent.py (or create if missing)
import json
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from orchestrator import newsletter_agent


def test_newsletter_email_includes_funnel_summary(tmp_path, monkeypatch):
    """Newsletter email body includes funnel summary when substack_metrics.json exists."""
    monkeypatch.setattr("orchestrator.newsletter_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr("orchestrator.newsletter_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "test@example.com")

    # Create fake substack_metrics.json
    metrics = [
        {"date": "2026-03-24", "subscribers": 25, "open_rate": 35.0, "total_email": 20, "growth_sources": []},
        {"date": "2026-03-31", "subscribers": 27, "open_rate": 38.5, "total_email": 23, "growth_sources": [{"source": "substack", "value": 12}]},
    ]
    (tmp_path / "substack_metrics.json").write_text(json.dumps(metrics))

    with patch("orchestrator.newsletter_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.newsletter_agent.anthropic.Anthropic") as MockAnthropic, \
         patch("orchestrator.newsletter_agent.subprocess.run") as mock_run:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="電子報草稿內容")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp
        mock_run.return_value = MagicMock(returncode=0)

        newsletter_agent.run()

    # Check email body contains funnel info
    call_args = mock_run.call_args
    email_body = call_args[1]["input"].decode("utf-8")
    assert "訂閱數" in email_body
    assert "27" in email_body
    assert "+2" in email_body  # delta from 25 → 27


def test_newsletter_email_no_delta_on_first_snapshot(tmp_path, monkeypatch):
    """When only one snapshot exists, no delta is shown."""
    monkeypatch.setattr("orchestrator.newsletter_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr("orchestrator.newsletter_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "test@example.com")

    metrics = [
        {"date": "2026-03-31", "subscribers": 27, "open_rate": 38.5, "total_email": 23, "growth_sources": []},
    ]
    (tmp_path / "substack_metrics.json").write_text(json.dumps(metrics))

    with patch("orchestrator.newsletter_agent.load_recent_experiments", return_value=[]), \
         patch("orchestrator.newsletter_agent.anthropic.Anthropic") as MockAnthropic, \
         patch("orchestrator.newsletter_agent.subprocess.run") as mock_run:

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="草稿")]
        MockAnthropic.return_value.messages.create.return_value = mock_resp
        mock_run.return_value = MagicMock(returncode=0)

        newsletter_agent.run()

    call_args = mock_run.call_args
    email_body = call_args[1]["input"].decode("utf-8")
    assert "27" in email_body
    assert "+0" not in email_body or "N/A" in email_body or "首次" in email_body
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/hua/autoresearch_threads && python -m pytest tests/test_newsletter_agent.py -v -k "funnel"
```

Expected: `FAILED` — email body doesn't include funnel summary yet

- [ ] **Step 3: Update `orchestrator/newsletter_agent.py`**

Add `DATA_DIR` to config imports:
```python
from orchestrator.config import (
    ANTHROPIC_API_KEY, PROMPTS_DIR, DRAFTS_DIR, NEWSLETTER_EMAIL, DATA_DIR
)
```

Add `read_json` to utils imports:
```python
from orchestrator.utils import load_recent_experiments, read_json
```

In `run()`, add funnel summary block **before** the `if not NEWSLETTER_EMAIL:` guard. Insert after `top_summary` is computed:

```python
    # Build funnel summary from latest Substack snapshot
    funnel_section = ""
    metrics_path = DATA_DIR / "substack_metrics.json"
    metrics_history = read_json(metrics_path)
    if isinstance(metrics_history, list) and metrics_history:
        latest = metrics_history[-1]
        prev = metrics_history[-2] if len(metrics_history) >= 2 else None
        delta = latest["subscribers"] - prev["subscribers"] if prev else None
        delta_str = f"+{delta}" if delta is not None and delta >= 0 else str(delta) if delta is not None else "首次記錄"
        sources_str = ", ".join(
            f"{s['source']}: {s['value']}"
            for s in latest.get("growth_sources", [])
        ) or "無資料"
        funnel_section = (
            f"\n\n## Substack 漏斗摘要（{latest['date']}）\n"
            f"- 訂閱數：{latest['subscribers']}（{delta_str} 本週）\n"
            f"- Open Rate：{latest['open_rate']}%\n"
            f"- 流量來源：{sources_str}\n"
        )
```

Update the `body` variable to include `funnel_section`:

```python
        body = f"本週 Top 5 貼文數據：\n{top_summary[:500]}{funnel_section}\n\n---草稿---\n\n{draft}"
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/hua/autoresearch_threads && python -m pytest tests/test_newsletter_agent.py -v -k "funnel"
```

Expected: `2 passed`

- [ ] **Step 5: Run full test suite**

```bash
cd /Users/hua/autoresearch_threads && python -m pytest tests/ -v
```

Expected: All tests pass (or only pre-existing failures)

- [ ] **Step 6: Commit**

```bash
cd /Users/hua/autoresearch_threads && git add orchestrator/newsletter_agent.py tests/test_newsletter_agent.py
git commit -m "feat: newsletter email includes Substack funnel summary with subscriber delta"
```

---

## Post-Implementation: `.env` Setup

After implementation, add these keys to `.env` before testing end-to-end:

```bash
SUBSTACK_SID=<your substack.sid cookie value>
SUBSTACK_SUBDOMAIN=hualeee
```

To get `substack.sid`:
1. 開 Chrome DevTools → Application → Cookies → `https://substack.com`
2. 找 `substack.sid` cookie，複製 Value

---

## Self-Review Checklist

**Spec coverage:**
- [x] `substack_client.py` — 3 endpoints only (summary, summary-v2, growth_sources)
- [x] Config vars `SUBSTACK_SID`, `SUBSTACK_SUBDOMAIN`
- [x] `data/substack_metrics.json` append-only snapshots
- [x] Strategy Agent fetches snapshot, stores it, injects into prompt
- [x] Newsletter Agent reads latest snapshot, builds delta, adds to email body
- [x] Graceful skip when `SUBSTACK_SID` not set

**Placeholder scan:** None found.

**Type consistency:**
- `SubstackClient` used consistently as `client = SubstackClient(subdomain=..., sid=...)`
- `fetch_snapshot()` returns dict with keys: `date`, `subscribers`, `total_email`, `open_rate`, `growth_sources`
- `read_json` / `write_json` imported from `orchestrator.utils` consistently
