# Autoresearch Threads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully automated Threads posting system that scrapes AI content from multiple sources, publishes 3-5 posts/day, harvests engagement metrics, and iteratively improves content direction using the autoresearch experiment loop pattern.

**Architecture:** Four-phase loop (source → harvest → analyze → generate → deploy) running every 12 hours via GitHub Actions. Phase 1 (< 100 followers) explores diverse content dimensions; Phase 2 (≥ 100) switches to tournament-style baseline vs challenger. All data stored in JSON files with git version control. Learnings accumulate in resource.md.

**Tech Stack:** Python 3.12, Threads API (publishing), Chrome DevTools MCP + threads-api (metrics harvesting), Claude API (analysis + generation), YouTube Data API + ShiFu MCP (transcripts), Telegram Bot API (notifications), GitHub Actions (scheduling)

---

## File Structure

```
autoresearch_threads/
├── orchestrator/
│   ├── main.py              # Entry point: phase detection, loop orchestration
│   ├── config.py            # Centralized env var config
│   ├── threads_client.py    # Threads API: publish posts, check status
│   ├── harvest.py           # Collect metrics from published posts
│   ├── harvest_browser.py   # Chrome DevTools MCP metric scraping
│   ├── harvest_api.py       # Unofficial threads-api metric scraping
│   ├── analyze.py           # Score posts, AI analysis, extract learnings
│   ├── generate.py          # AI content generation from sources + learnings
│   ├── deploy.py            # Publish posts with scheduling + format sanitizer
│   ├── notify.py            # Telegram Bot notifications
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── x_curated.py     # Read X.com content from Telegram messages + curated file
│   │   ├── youtube.py       # Check YouTube channels for new videos + transcripts
│   │   └── github.py        # Read recent GitHub activity via SSH
│   └── utils.py             # Shared: JSON read/write, date helpers
│
├── prompts/
│   ├── program.md           # Generation rules, dimension definitions, phase rules
│   ├── swipe_file.md        # High-performing post examples
│   ├── x_curated.md         # X.com curated content (auto + manual)
│   └── resource.md          # Accumulated learnings (auto-updated)
│
├── data/
│   ├── posts.json           # All published posts with metadata
│   ├── metrics.json         # Per-post engagement metrics over time
│   └── experiments.json     # Per-round experiment records
│
├── tests/
│   ├── test_config.py
│   ├── test_threads_client.py
│   ├── test_harvest.py
│   ├── test_analyze.py
│   ├── test_generate.py
│   ├── test_deploy.py
│   ├── test_notify.py
│   ├── test_sources.py
│   └── test_utils.py
│
├── .github/workflows/
│   └── autoresearch.yml
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

### Task 1: Project Scaffolding + Config

**Files:**
- Create: `orchestrator/config.py`
- Create: `orchestrator/utils.py`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Test: `tests/test_config.py`
- Test: `tests/test_utils.py`

- [ ] **Step 1: Initialize git repo and create .gitignore**

```bash
cd /Users/hua/autoresearch_threads
git init
```

```gitignore
# .gitignore
__pycache__/
*.pyc
.env
.venv/
data/
.DS_Store
```

- [ ] **Step 2: Create requirements.txt**

```txt
anthropic>=0.40.0
requests>=2.31.0
python-dotenv>=1.0.0
```

- [ ] **Step 3: Create .env.example**

```bash
# Threads API
THREADS_ACCESS_TOKEN=
THREADS_USER_ID=

# Claude API
ANTHROPIC_API_KEY=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# GitHub (SSH key should be configured on the machine)
# No env var needed — uses default SSH key

# YouTube Data API
YOUTUBE_API_KEY=

# Phase config
PHASE_SWITCH_FOLLOWER_THRESHOLD=100
SCORE_WEIGHT_VIEWS=0.6
SCORE_WEIGHT_LIKES=0.2
SCORE_WEIGHT_REPLIES=0.2
```

- [ ] **Step 4: Write failing test for config**

```python
# tests/test_config.py
import os
import pytest


def test_config_loads_required_vars(monkeypatch):
    monkeypatch.setenv("THREADS_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("THREADS_USER_ID", "12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    monkeypatch.setenv("YOUTUBE_API_KEY", "yt-key")

    # Force reimport
    import importlib
    import orchestrator.config as cfg
    importlib.reload(cfg)

    assert cfg.THREADS_ACCESS_TOKEN == "test_token"
    assert cfg.THREADS_USER_ID == "12345"
    assert cfg.ANTHROPIC_API_KEY == "sk-test"
    assert cfg.TELEGRAM_BOT_TOKEN == "bot123"
    assert cfg.TELEGRAM_CHAT_ID == "chat456"
    assert cfg.YOUTUBE_API_KEY == "yt-key"


def test_config_defaults():
    import orchestrator.config as cfg
    assert cfg.PHASE_SWITCH_FOLLOWER_THRESHOLD == 100
    assert cfg.SCORE_WEIGHT_VIEWS == 0.6
    assert cfg.SCORE_WEIGHT_LIKES == 0.2
    assert cfg.SCORE_WEIGHT_REPLIES == 0.2
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd /Users/hua/autoresearch_threads && python -m pytest tests/test_config.py -v`
Expected: FAIL (module not found)

- [ ] **Step 6: Implement config.py**

```python
# orchestrator/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Required
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
THREADS_USER_ID = os.environ.get("THREADS_USER_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# Phase config
PHASE_SWITCH_FOLLOWER_THRESHOLD = int(os.getenv("PHASE_SWITCH_FOLLOWER_THRESHOLD", "100"))

# Scoring weights
SCORE_WEIGHT_VIEWS = float(os.getenv("SCORE_WEIGHT_VIEWS", "0.6"))
SCORE_WEIGHT_LIKES = float(os.getenv("SCORE_WEIGHT_LIKES", "0.2"))
SCORE_WEIGHT_REPLIES = float(os.getenv("SCORE_WEIGHT_REPLIES", "0.2"))

# YouTube channels to monitor
YOUTUBE_CHANNELS = [
    "every.to",
    "Lenny's Podcast",
    "How I AI",
    "a16z",
    "Greg Isenberg",
    "Stephen G. Pope",
    "Y Combinator",
    "Nick Saraev",
]

# Paths
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
DATA_DIR = BASE_DIR / "data"
```

- [ ] **Step 7: Create orchestrator/__init__.py**

```python
# orchestrator/__init__.py
```

- [ ] **Step 8: Write failing test for utils**

```python
# tests/test_utils.py
import json
import tempfile
from pathlib import Path

from orchestrator.utils import read_json, write_json, sanitize_post_text


def test_read_write_json():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        path = Path(f.name)
    data = [{"id": "1", "text": "hello"}]
    write_json(path, data)
    result = read_json(path)
    assert result == data
    path.unlink()


def test_read_json_missing_file():
    result = read_json(Path("/tmp/nonexistent_12345.json"))
    assert result == []


def test_sanitize_post_text_removes_literal_newlines():
    raw = "Hello\\n\\nWorld"
    cleaned = sanitize_post_text(raw)
    assert "\\n" not in cleaned
    assert "Hello" in cleaned
    assert "World" in cleaned


def test_sanitize_post_text_trims_whitespace():
    raw = "  Hello World  "
    cleaned = sanitize_post_text(raw)
    assert cleaned == "Hello World"


def test_sanitize_post_text_collapses_blank_lines():
    raw = "Hello\n\n\n\nWorld"
    cleaned = sanitize_post_text(raw)
    assert "\n\n\n" not in cleaned
```

- [ ] **Step 9: Run test to verify it fails**

Run: `python -m pytest tests/test_utils.py -v`
Expected: FAIL (module not found)

- [ ] **Step 10: Implement utils.py**

```python
# orchestrator/utils.py
import json
import re
from pathlib import Path


def read_json(path: Path) -> list | dict:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: list | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sanitize_post_text(text: str) -> str:
    # Replace literal \n with actual newlines
    text = text.replace("\\n", "\n")
    # Collapse 3+ consecutive newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text
```

- [ ] **Step 11: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py tests/test_utils.py -v`
Expected: ALL PASS

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with config and utils"
```

---

### Task 2: Threads Client (Publishing)

**Files:**
- Create: `orchestrator/threads_client.py`
- Test: `tests/test_threads_client.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_threads_client.py
import json
from unittest.mock import patch, MagicMock

from orchestrator.threads_client import create_post, publish_post, get_user_profile


def test_create_post_returns_creation_id():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "container_123"}
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.threads_client.requests.post", return_value=mock_resp):
        result = create_post("Hello Threads!")
    assert result == "container_123"


def test_publish_post_returns_media_id():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "media_456"}
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.threads_client.requests.post", return_value=mock_resp):
        result = publish_post("container_123")
    assert result == "media_456"


def test_get_user_profile_returns_id_and_name():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "user_789", "username": "testuser", "threads_profile_picture_url": "https://example.com/pic.jpg"}
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.threads_client.requests.get", return_value=mock_resp):
        result = get_user_profile()
    assert result["id"] == "user_789"
    assert result["username"] == "testuser"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_threads_client.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement threads_client.py**

```python
# orchestrator/threads_client.py
import time
import requests
from orchestrator.config import THREADS_ACCESS_TOKEN, THREADS_USER_ID

BASE_URL = "https://graph.threads.net/v1.0"


def create_post(text: str) -> str | None:
    url = f"{BASE_URL}/{THREADS_USER_ID}/threads"
    payload = {
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN,
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json().get("id")


def publish_post(creation_id: str) -> str | None:
    url = f"{BASE_URL}/{THREADS_USER_ID}/threads_publish"
    payload = {
        "creation_id": creation_id,
        "access_token": THREADS_ACCESS_TOKEN,
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json().get("id")


def post_text(text: str, wait_seconds: int = 30) -> str | None:
    creation_id = create_post(text)
    if not creation_id:
        return None
    time.sleep(wait_seconds)
    return publish_post(creation_id)


def get_user_profile() -> dict:
    url = f"{BASE_URL}/me"
    params = {
        "fields": "id,username,threads_profile_picture_url",
        "access_token": THREADS_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def get_post_insights(media_id: str) -> dict:
    url = f"{BASE_URL}/{media_id}/insights"
    params = {
        "metric": "views,likes,replies,reposts,quotes",
        "access_token": THREADS_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return {}
    data = resp.json().get("data", [])
    return {item["name"]: item["values"][0]["value"] for item in data}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_threads_client.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/threads_client.py tests/test_threads_client.py
git commit -m "feat: Threads API client for publishing and insights"
```

---

### Task 3: Telegram Notifications

**Files:**
- Create: `orchestrator/notify.py`
- Test: `tests/test_notify.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_notify.py
from unittest.mock import patch, MagicMock

from orchestrator.notify import send_notification


def test_send_notification_calls_telegram():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("orchestrator.notify.requests.post", return_value=mock_resp) as mock_post:
        with patch("orchestrator.notify.TELEGRAM_BOT_TOKEN", "bot123"):
            with patch("orchestrator.notify.TELEGRAM_CHAT_ID", "chat456"):
                send_notification("Test message")

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "bot123" in call_args[0][0]
    assert call_args[1]["json"]["chat_id"] == "chat456"
    assert call_args[1]["json"]["text"] == "Test message"


def test_send_notification_falls_back_to_print_when_no_token(capsys):
    with patch("orchestrator.notify.TELEGRAM_BOT_TOKEN", ""):
        send_notification("Fallback message")

    captured = capsys.readouterr()
    assert "Fallback message" in captured.out


def test_fetch_incoming_messages_returns_texts():
    from orchestrator.notify import fetch_incoming_messages

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ok": True,
        "result": [
            {
                "update_id": 100,
                "message": {
                    "chat": {"id": 456},
                    "text": "https://x.com/karpathy/status/123 這篇很讚"
                }
            },
            {
                "update_id": 101,
                "message": {
                    "chat": {"id": 456},
                    "text": "另一篇好內容"
                }
            },
        ]
    }

    with patch("orchestrator.notify.requests.get", return_value=mock_resp):
        with patch("orchestrator.notify.TELEGRAM_BOT_TOKEN", "bot123"):
            with patch("orchestrator.notify.TELEGRAM_CHAT_ID", "456"):
                with patch("orchestrator.notify.DATA_DIR", Path("/tmp/test_notify")):
                    messages = fetch_incoming_messages()

    assert len(messages) == 2
    assert "karpathy" in messages[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_notify.py -v`
Expected: FAIL

- [ ] **Step 3: Implement notify.py**

```python
# orchestrator/notify.py
import json
import requests
from pathlib import Path
from orchestrator.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DATA_DIR


def send_notification(message: str) -> None:
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        _send_telegram(message)
    else:
        print(f"[NOTIFY] {message}")


def _send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            print(f"[NOTIFY] Telegram failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[NOTIFY] Telegram error: {e}")


def fetch_incoming_messages() -> list[str]:
    """Fetch new messages sent TO the bot via Telegram getUpdates.
    Used to receive X.com content the user forwards to the bot.
    Tracks last processed update_id in data/telegram_offset.json.
    """
    if not TELEGRAM_BOT_TOKEN:
        return []

    offset_path = DATA_DIR / "telegram_offset.json"
    offset = 0
    if offset_path.exists():
        with open(offset_path, "r") as f:
            offset = json.load(f).get("offset", 0)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": 5}

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception as e:
        print(f"[NOTIFY] getUpdates error: {e}")
        return []

    messages = []
    max_update_id = offset

    for update in data.get("result", []):
        update_id = update.get("update_id", 0)
        if update_id >= max_update_id:
            max_update_id = update_id + 1

        msg = update.get("message", {})
        # Only accept messages from our chat
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if chat_id != TELEGRAM_CHAT_ID:
            continue

        text = msg.get("text", "")
        if text:
            messages.append(text)

    # Save new offset
    if max_update_id > offset:
        offset_path.parent.mkdir(parents=True, exist_ok=True)
        with open(offset_path, "w") as f:
            json.dump({"offset": max_update_id}, f)

    return messages
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_notify.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/notify.py tests/test_notify.py
git commit -m "feat: Telegram notification module"
```

---

### Task 4: Source Scrapers (YouTube + GitHub + X)

**Files:**
- Create: `orchestrator/sources/__init__.py`
- Create: `orchestrator/sources/youtube.py`
- Create: `orchestrator/sources/github.py`
- Create: `orchestrator/sources/x_scraper.py`
- Test: `tests/test_sources.py`

- [ ] **Step 1: Write failing test for YouTube source**

```python
# tests/test_sources.py
from unittest.mock import patch, MagicMock
from orchestrator.sources.youtube import fetch_recent_videos, CHANNEL_IDS


def test_fetch_recent_videos_returns_list():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {
                "id": {"videoId": "abc123"},
                "snippet": {
                    "title": "AI Tools 2026",
                    "channelTitle": "every.to",
                    "publishedAt": "2026-03-27T10:00:00Z",
                    "description": "A great video about AI tools",
                }
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.sources.youtube.requests.get", return_value=mock_resp):
        videos = fetch_recent_videos("UC_channel_id", hours=12)

    assert len(videos) == 1
    assert videos[0]["video_id"] == "abc123"
    assert videos[0]["title"] == "AI Tools 2026"
```

- [ ] **Step 2: Write failing test for GitHub source**

```python
# tests/test_sources.py (append)
from orchestrator.sources.github import fetch_recent_activity


def test_fetch_recent_activity_returns_list():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = """abc1234|feat: add new feature|2026-03-27
def5678|fix: resolve bug|2026-03-26"""

    with patch("orchestrator.sources.github.subprocess.run", return_value=mock_result):
        commits = fetch_recent_activity("/tmp/fake-repo")

    assert len(commits) == 2
    assert commits[0]["hash"] == "abc1234"
    assert commits[0]["message"] == "feat: add new feature"
```

- [ ] **Step 3: Write failing test for X curated source**

```python
# tests/test_sources.py (append)
from orchestrator.sources.x_curated import fetch_x_content


def test_fetch_x_content_merges_telegram_and_file(tmp_path):
    curated_file = tmp_path / "x_curated.md"
    curated_file.write_text("## 策展內容\n\n好文1：AI agents 的未來\n\n好文2：LLM 成本下降趨勢")

    telegram_messages = [
        "https://x.com/karpathy/status/123 這個觀點很好",
        "剛看到一篇關於 AI coding 的長文",
    ]

    results = fetch_x_content(telegram_messages, str(curated_file))
    assert len(results) == 2  # telegram messages
    assert results[0]["source"] == "telegram"
    assert "karpathy" in results[0]["text"]


def test_fetch_x_content_appends_to_curated_file(tmp_path):
    curated_file = tmp_path / "x_curated.md"
    curated_file.write_text("## 策展內容\n")

    telegram_messages = ["新的好內容"]
    fetch_x_content(telegram_messages, str(curated_file))

    updated = curated_file.read_text()
    assert "新的好內容" in updated
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest tests/test_sources.py -v`
Expected: FAIL

- [ ] **Step 5: Implement sources/__init__.py**

```python
# orchestrator/sources/__init__.py
```

- [ ] **Step 6: Implement youtube.py**

```python
# orchestrator/sources/youtube.py
import requests
from datetime import datetime, timedelta, timezone
from orchestrator.config import YOUTUBE_API_KEY

# Channel name -> YouTube channel ID mapping
# These need to be filled with actual channel IDs
CHANNEL_IDS = {
    "every.to": "",
    "Lenny's Podcast": "",
    "How I AI": "",
    "a16z": "",
    "Greg Isenberg": "",
    "Stephen G. Pope": "",
    "Y Combinator": "",
    "Nick Saraev": "",
}

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def fetch_recent_videos(channel_id: str, hours: int = 12) -> list[dict]:
    if not channel_id or not YOUTUBE_API_KEY:
        return []

    published_after = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    params = {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "order": "date",
        "publishedAfter": published_after,
        "maxResults": 5,
        "key": YOUTUBE_API_KEY,
    }

    resp = requests.get(YOUTUBE_SEARCH_URL, params=params)
    if resp.status_code != 200:
        print(f"[SOURCE] YouTube API error: {resp.status_code}")
        return []

    items = resp.json().get("items", [])
    return [
        {
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
            "description": item["snippet"].get("description", ""),
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
        }
        for item in items
        if item.get("id", {}).get("videoId")
    ]


def fetch_all_channels(hours: int = 12) -> list[dict]:
    all_videos = []
    for name, channel_id in CHANNEL_IDS.items():
        if channel_id:
            videos = fetch_recent_videos(channel_id, hours)
            all_videos.extend(videos)
    return all_videos
```

- [ ] **Step 7: Implement github.py**

```python
# orchestrator/sources/github.py
import subprocess
from pathlib import Path


def fetch_recent_activity(repo_path: str, days: int = 1) -> list[dict]:
    try:
        result = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--pretty=format:%h|%s|%ai"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({
                    "hash": parts[0],
                    "message": parts[1],
                    "date": parts[2],
                })
        return commits
    except Exception as e:
        print(f"[SOURCE] GitHub error for {repo_path}: {e}")
        return []


def fetch_github_repos_via_ssh() -> list[dict]:
    try:
        result = subprocess.run(
            ["ssh", "-T", "git@github.com"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # SSH -T returns exit code 1 but prints username in stderr
        # We just verify connectivity here
        return []
    except Exception:
        return []


def list_local_repos(base_path: str = "/Users/hua") -> list[str]:
    repos = []
    base = Path(base_path)
    # Check common locations for git repos
    for candidate in base.iterdir():
        if candidate.is_dir() and (candidate / ".git").exists():
            repos.append(str(candidate))
    return repos
```

- [ ] **Step 8: Implement x_curated.py**

```python
# orchestrator/sources/x_curated.py
"""
X.com content sourcing via two channels:
1. Telegram messages — user forwards interesting X posts to the bot
2. x_curated.md — persistent curated file with accumulated good content
"""
from datetime import datetime, timezone
from pathlib import Path
from orchestrator.config import PROMPTS_DIR


def fetch_x_content(telegram_messages: list[str], curated_path: str | None = None) -> list[dict]:
    if curated_path is None:
        curated_path = str(PROMPTS_DIR / "x_curated.md")

    results = []

    # Process Telegram messages
    for msg in telegram_messages:
        results.append({
            "text": msg,
            "source": "telegram",
            "received_at": datetime.now(timezone.utc).isoformat(),
        })

    # Append new Telegram messages to curated file for persistence
    if telegram_messages:
        _append_to_curated(telegram_messages, curated_path)

    return results


def read_curated_file(curated_path: str | None = None) -> str:
    if curated_path is None:
        curated_path = str(PROMPTS_DIR / "x_curated.md")
    path = Path(curated_path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _append_to_curated(messages: list[str], curated_path: str) -> None:
    path = Path(curated_path)
    current = path.read_text(encoding="utf-8") if path.exists() else "# X.com 策展內容\n"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    new_entries = f"\n\n## {date_str} (via Telegram)\n"
    for msg in messages:
        new_entries += f"- {msg}\n"
    path.write_text(current + new_entries, encoding="utf-8")
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `python -m pytest tests/test_sources.py -v`
Expected: ALL PASS

- [ ] **Step 10: Commit**

```bash
git add orchestrator/sources/ tests/test_sources.py
git commit -m "feat: source scrapers for YouTube, GitHub, and X"
```

---

### Task 5: Harvest Module (Metrics Collection)

**Files:**
- Create: `orchestrator/harvest.py`
- Create: `orchestrator/harvest_browser.py`
- Create: `orchestrator/harvest_api.py`
- Test: `tests/test_harvest.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_harvest.py
from unittest.mock import patch
from orchestrator.harvest import harvest, merge_metrics


def test_merge_metrics_prefers_browser_views():
    browser = {"views": 150, "likes": 10, "replies": 2, "reposts": 1}
    api = {"views": 0, "likes": 12, "replies": 2, "reposts": 3}
    merged = merge_metrics(browser, api)
    assert merged["views"] == 150  # Browser has views
    assert merged["likes"] == 12   # Take max
    assert merged["reposts"] == 3  # Take max


def test_merge_metrics_falls_back_to_api():
    browser = {}  # Browser failed
    api = {"views": 0, "likes": 5, "replies": 1, "reposts": 0}
    merged = merge_metrics(browser, api)
    assert merged["likes"] == 5


def test_harvest_returns_list_of_post_metrics():
    fake_posts = [
        {"media_id": "post_1", "text": "Hello", "published_at": "2026-03-27T09:00:00"},
        {"media_id": "post_2", "text": "World", "published_at": "2026-03-27T11:00:00"},
    ]
    fake_browser = {"post_1": {"views": 100, "likes": 5, "replies": 1, "reposts": 0}}
    fake_api = {"post_2": {"views": 0, "likes": 3, "replies": 0, "reposts": 1}}

    with patch("orchestrator.harvest.read_json", return_value=fake_posts):
        with patch("orchestrator.harvest.harvest_browser", return_value=fake_browser):
            with patch("orchestrator.harvest.harvest_api", return_value=fake_api):
                results = harvest()

    assert len(results) == 2
    assert results[0]["media_id"] == "post_1"
    assert results[0]["views"] == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_harvest.py -v`
Expected: FAIL

- [ ] **Step 3: Implement harvest_browser.py**

```python
# orchestrator/harvest_browser.py
"""
Harvest metrics from Threads via Chrome DevTools MCP.
This module is designed to be called from the orchestrator
when running in an environment with Chrome DevTools MCP available.

In GitHub Actions, this will be skipped (no browser).
In local development, it can be used via Claude Code MCP.
"""


def harvest_browser(post_ids: list[str]) -> dict[str, dict]:
    # Chrome DevTools MCP interaction is done at the orchestrator level
    # via Claude Code agent. This module provides the data structure.
    # When running headless in CI, return empty dict (graceful fallback).
    return {}
```

- [ ] **Step 4: Implement harvest_api.py**

```python
# orchestrator/harvest_api.py
"""
Harvest metrics using unofficial threads-api or Threads official insights.
Falls back gracefully if API is unavailable.
"""
from orchestrator.threads_client import get_post_insights


def harvest_api(post_ids: list[str]) -> dict[str, dict]:
    results = {}
    for media_id in post_ids:
        try:
            insights = get_post_insights(media_id)
            if insights:
                results[media_id] = {
                    "views": insights.get("views", 0),
                    "likes": insights.get("likes", 0),
                    "replies": insights.get("replies", 0),
                    "reposts": insights.get("reposts", 0),
                }
        except Exception as e:
            print(f"[HARVEST] API error for {media_id}: {e}")
    return results
```

- [ ] **Step 5: Implement harvest.py**

```python
# orchestrator/harvest.py
from pathlib import Path
from orchestrator.config import DATA_DIR
from orchestrator.utils import read_json, write_json
from orchestrator.harvest_browser import harvest_browser
from orchestrator.harvest_api import harvest_api


def merge_metrics(browser: dict, api: dict) -> dict:
    merged = {
        "views": browser.get("views", 0) or api.get("views", 0),
        "likes": max(browser.get("likes", 0), api.get("likes", 0)),
        "replies": max(browser.get("replies", 0), api.get("replies", 0)),
        "reposts": max(browser.get("reposts", 0), api.get("reposts", 0)),
    }
    return merged


def harvest() -> list[dict]:
    posts = read_json(DATA_DIR / "posts.json")
    if not posts:
        return []

    post_ids = [p["media_id"] for p in posts if p.get("media_id")]

    browser_data = harvest_browser(post_ids)
    api_data = harvest_api(post_ids)

    results = []
    for post in posts:
        media_id = post.get("media_id", "")
        b = browser_data.get(media_id, {})
        a = api_data.get(media_id, {})
        merged = merge_metrics(b, a)

        results.append({
            "media_id": media_id,
            "text": post.get("text", ""),
            "hypothesis": post.get("hypothesis", ""),
            "dimensions": post.get("dimensions", {}),
            "published_at": post.get("published_at", ""),
            **merged,
        })

    # Save metrics snapshot
    metrics_path = DATA_DIR / "metrics.json"
    existing = read_json(metrics_path)
    if not isinstance(existing, list):
        existing = []
    existing.append({
        "harvested_at": _now_iso(),
        "posts": results,
    })
    write_json(metrics_path, existing)

    return results


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_harvest.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add orchestrator/harvest.py orchestrator/harvest_browser.py orchestrator/harvest_api.py tests/test_harvest.py
git commit -m "feat: harvest module with browser + API dual collection"
```

---

### Task 6: Analyze Module

**Files:**
- Create: `orchestrator/analyze.py`
- Test: `tests/test_analyze.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_analyze.py
from unittest.mock import patch, MagicMock
from orchestrator.analyze import score_posts, analyze


def test_score_posts_weighted():
    posts = [
        {"media_id": "1", "views": 100, "likes": 10, "replies": 5, "reposts": 0},
        {"media_id": "2", "views": 50, "likes": 20, "replies": 2, "reposts": 0},
        {"media_id": "3", "views": 200, "likes": 5, "replies": 1, "reposts": 0},
    ]
    scored = score_posts(posts)
    # Post 3 has most views (weight 0.6), should score highest
    assert scored[0]["media_id"] == "3"
    assert "score" in scored[0]


def test_score_posts_handles_all_zeros():
    posts = [
        {"media_id": "1", "views": 0, "likes": 0, "replies": 0, "reposts": 0},
    ]
    scored = score_posts(posts)
    assert scored[0]["score"] == 0.0


def test_analyze_returns_analysis_dict():
    posts = [
        {"media_id": "1", "views": 100, "likes": 10, "replies": 5, "reposts": 0,
         "text": "AI tool", "hypothesis": "test tools", "dimensions": {"content_type": "工具分享"}},
        {"media_id": "2", "views": 50, "likes": 2, "replies": 0, "reposts": 0,
         "text": "Dev log", "hypothesis": "test dev", "dimensions": {"content_type": "開發心得"}},
    ]

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="## 分析\n工具分享表現較好\n## 學習\n- 工具類觸及高")]

    with patch("orchestrator.analyze.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        result = analyze(posts)

    assert "scored_posts" in result
    assert "analysis" in result
    assert "learnings" in result
    assert "round_number" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analyze.py -v`
Expected: FAIL

- [ ] **Step 3: Implement analyze.py**

```python
# orchestrator/analyze.py
import anthropic
from orchestrator.config import (
    ANTHROPIC_API_KEY,
    SCORE_WEIGHT_VIEWS,
    SCORE_WEIGHT_LIKES,
    SCORE_WEIGHT_REPLIES,
    DATA_DIR,
    PROMPTS_DIR,
)
from orchestrator.utils import read_json, write_json


def score_posts(posts: list[dict]) -> list[dict]:
    if not posts:
        return []

    views = [p.get("views", 0) for p in posts]
    likes = [p.get("likes", 0) for p in posts]
    replies = [p.get("replies", 0) for p in posts]

    max_views = max(views) if max(views) > 0 else 1
    max_likes = max(likes) if max(likes) > 0 else 1
    max_replies = max(replies) if max(replies) > 0 else 1

    for p in posts:
        norm_v = p.get("views", 0) / max_views
        norm_l = p.get("likes", 0) / max_likes
        norm_r = p.get("replies", 0) / max_replies
        p["score"] = round(
            norm_v * SCORE_WEIGHT_VIEWS
            + norm_l * SCORE_WEIGHT_LIKES
            + norm_r * SCORE_WEIGHT_REPLIES,
            4,
        )

    posts.sort(key=lambda x: x["score"], reverse=True)
    return posts


def analyze(posts: list[dict]) -> dict:
    scored = score_posts(posts)

    # Determine round number
    experiments = read_json(DATA_DIR / "experiments.json")
    round_number = len(experiments) + 1

    # Read resource.md for context
    resource_path = PROMPTS_DIR / "resource.md"
    resource_text = resource_path.read_text(encoding="utf-8") if resource_path.exists() else ""

    # Build analysis prompt
    post_summary = "\n".join(
        f"- [{p.get('dimensions', {}).get('content_type', '?')}] "
        f"score={p['score']} views={p.get('views',0)} likes={p.get('likes',0)} "
        f"replies={p.get('replies',0)} | hook={p.get('dimensions', {}).get('hook_style', '?')} "
        f"| text: {p.get('text', '')[:100]}"
        for p in scored
    )

    prompt = f"""你是一個 Threads 貼文優化分析師。以下是本輪發佈的貼文表現數據：

{post_summary}

目前累積學習：
{resource_text}

請分析：
1. 哪些維度（內容類型、hook 風格、格式、語氣、素材來源）跟表現正相關？
2. Top performer 為什麼表現好？Bottom performer 為什麼表現差？
3. 提取 2-3 條 actionable learnings，格式為：
   - 規則：[具體描述]
   - 依據：[本輪數據]
   - 信心度：高/中/低

4. 更新假設狀態（如有）

用繁體中文回答。"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    ai_text = response.content[0].text

    # Split analysis and learnings
    learnings = ""
    if "learning" in ai_text.lower() or "學習" in ai_text or "規則" in ai_text:
        learnings = ai_text

    result = {
        "scored_posts": scored,
        "analysis": ai_text,
        "learnings": learnings,
        "round_number": round_number,
    }

    # Save experiment record
    experiments.append({
        "round_number": round_number,
        "harvested_at": _now_iso(),
        "results": [
            {"media_id": p["media_id"], "score": p["score"], "views": p.get("views", 0),
             "likes": p.get("likes", 0), "replies": p.get("replies", 0)}
            for p in scored
        ],
        "analysis": ai_text,
        "learnings": learnings,
    })
    write_json(DATA_DIR / "experiments.json", experiments)

    return result


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analyze.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/analyze.py tests/test_analyze.py
git commit -m "feat: analyze module with scoring and AI analysis"
```

---

### Task 7: Generate Module

**Files:**
- Create: `orchestrator/generate.py`
- Test: `tests/test_generate.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_generate.py
import json
from unittest.mock import patch, MagicMock
from orchestrator.generate import generate


def test_generate_returns_list_of_posts():
    analysis = {
        "scored_posts": [
            {"media_id": "1", "score": 0.8, "text": "AI tool post",
             "dimensions": {"content_type": "工具分享"}},
        ],
        "learnings": "工具類表現好",
        "round_number": 1,
    }

    sources = {
        "youtube": [{"title": "New AI Tool", "channel": "every.to", "url": "https://youtube.com/watch?v=abc"}],
        "github": [{"hash": "abc", "message": "feat: add RAG pipeline", "date": "2026-03-27"}],
        "x": [],
    }

    fake_ai_output = json.dumps([
        {
            "text": "分享一個超好用的 AI 工具",
            "dimensions": {
                "content_type": "工具分享",
                "hook_style": "送資源型",
                "format": "短句",
                "tone": "輕鬆口語",
                "cta": "追蹤我",
                "source": "youtube/every.to"
            },
            "hypothesis": "測試短句送資源型是否提升觸及"
        },
        {
            "text": "最近在做 RAG pipeline 踩了一個坑",
            "dimensions": {
                "content_type": "開發心得",
                "hook_style": "故事型",
                "format": "中篇",
                "tone": "輕鬆口語",
                "cta": "留言互動",
                "source": "github"
            },
            "hypothesis": "測試故事型 hook 的開發心得表現"
        }
    ], ensure_ascii=False)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=fake_ai_output)]

    with patch("orchestrator.generate.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        with patch("orchestrator.generate._read_prompt", return_value="test prompt"):
            posts = generate(analysis, sources)

    assert len(posts) == 2
    assert "text" in posts[0]
    assert "dimensions" in posts[0]
    assert "hypothesis" in posts[0]


def test_generate_returns_empty_on_error():
    analysis = {"scored_posts": [], "learnings": "", "round_number": 1}
    sources = {"youtube": [], "github": [], "x": []}

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json")]

    with patch("orchestrator.generate.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        with patch("orchestrator.generate._read_prompt", return_value="test"):
            posts = generate(analysis, sources)

    assert posts == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_generate.py -v`
Expected: FAIL

- [ ] **Step 3: Implement generate.py**

```python
# orchestrator/generate.py
import json
import anthropic
from pathlib import Path
from orchestrator.config import ANTHROPIC_API_KEY, PROMPTS_DIR


def _read_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _append_learnings(learnings: str, round_number: int) -> None:
    resource_path = PROMPTS_DIR / "resource.md"
    current = resource_path.read_text(encoding="utf-8") if resource_path.exists() else ""
    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_section = f"\n\n### Round {round_number} ({date_str})\n{learnings}\n"
    resource_path.write_text(current + new_section, encoding="utf-8")


def generate(analysis: dict, sources: dict) -> list[dict]:
    program = _read_prompt("program.md")
    swipe = _read_prompt("swipe_file.md")
    resource = _read_prompt("resource.md")

    round_number = analysis.get("round_number", 1)
    learnings = analysis.get("learnings", "")

    if learnings:
        _append_learnings(learnings, round_number)
        resource = _read_prompt("resource.md")  # Re-read after append

    # Format sources
    yt_summary = "\n".join(
        f"- [{v['channel']}] {v['title']} ({v['url']})"
        for v in sources.get("youtube", [])
    ) or "（本輪無新影片）"

    gh_summary = "\n".join(
        f"- {c['message']} ({c['hash']})"
        for c in sources.get("github", [])
    ) or "（本輪無新 commit）"

    x_new = "\n".join(
        f"- {p.get('text', '')}"
        for p in sources.get("x", [])
    ) or "（本輪無新轉發）"

    # Also read full curated file for accumulated X content
    from orchestrator.sources.x_curated import read_curated_file
    x_curated = read_curated_file()
    x_summary = f"### 本輪新轉發\n{x_new}\n\n### 累積策展內容\n{x_curated}" if x_curated else x_new

    # Format previous performance
    perf_summary = "\n".join(
        f"- score={p['score']} [{p.get('dimensions', {}).get('content_type', '?')}] "
        f"{p.get('text', '')[:80]}"
        for p in analysis.get("scored_posts", [])
    ) or "（首次運行，無歷史數據）"

    prompt = f"""{program}

## 高表現範例庫
{swipe}

## 累積學習
{resource}

## 本輪素材

### YouTube 新影片
{yt_summary}

### GitHub 最近活動
{gh_summary}

### X.com 熱門內容
{x_summary}

## 上一輪貼文表現
{perf_summary}

## 上一輪分析
{analysis.get('analysis', '（首次運行）')}

---

請產出 3-5 篇 Threads 貼文。每篇必須是自然流暢的繁體中文，不要有任何格式標記（如 \\n）。

輸出格式為 JSON array：
```json
[
  {{
    "text": "貼文內容（500字元以內）",
    "dimensions": {{
      "content_type": "工具分享|開發心得|教學知識點|新聞/趨勢|觀點/辯論",
      "hook_style": "提問型|數據型|故事型|爭議型|清單型|送資源型",
      "format": "短句|中篇|長文",
      "tone": "專業分析|輕鬆口語|急迫感|教學口吻",
      "cta": "無CTA|追蹤我|留言互動|分享給朋友",
      "source": "素材來源"
    }},
    "hypothesis": "這篇在測試什麼"
  }}
]
```

只輸出 JSON，不要加任何其他文字。"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code block if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        posts = json.loads(raw)
        if not isinstance(posts, list):
            return []
        return posts
    except json.JSONDecodeError:
        print(f"[GENERATE] Failed to parse AI output: {raw[:200]}")
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_generate.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/generate.py tests/test_generate.py
git commit -m "feat: generate module with AI content creation"
```

---

### Task 8: Deploy Module

**Files:**
- Create: `orchestrator/deploy.py`
- Test: `tests/test_deploy.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_deploy.py
import json
from unittest.mock import patch, MagicMock
from orchestrator.deploy import deploy, schedule_posts


def test_schedule_posts_distributes_times():
    posts = [
        {"text": "Post 1", "dimensions": {}, "hypothesis": "h1"},
        {"text": "Post 2", "dimensions": {}, "hypothesis": "h2"},
        {"text": "Post 3", "dimensions": {}, "hypothesis": "h3"},
    ]
    # Morning cycle starts at 09:00
    scheduled = schedule_posts(posts, start_hour=9, interval_hours=2)
    assert len(scheduled) == 3
    assert scheduled[0]["scheduled_hour"] == 9
    assert scheduled[1]["scheduled_hour"] == 11
    assert scheduled[2]["scheduled_hour"] == 13


def test_deploy_publishes_and_records():
    posts = [
        {"text": "Hello Threads", "dimensions": {"content_type": "工具分享"}, "hypothesis": "test"},
    ]

    with patch("orchestrator.deploy.threads_client") as mock_tc:
        mock_tc.post_text.return_value = "media_123"
        with patch("orchestrator.deploy.read_json", return_value=[]):
            with patch("orchestrator.deploy.write_json") as mock_write:
                with patch("orchestrator.deploy.sanitize_post_text", side_effect=lambda x: x):
                    result = deploy(posts)

    assert len(result) == 1
    assert result[0]["media_id"] == "media_123"
    mock_write.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_deploy.py -v`
Expected: FAIL

- [ ] **Step 3: Implement deploy.py**

```python
# orchestrator/deploy.py
from datetime import datetime, timezone
from orchestrator import threads_client
from orchestrator.config import DATA_DIR
from orchestrator.utils import read_json, write_json, sanitize_post_text


def schedule_posts(posts: list[dict], start_hour: int = 9, interval_hours: int = 2) -> list[dict]:
    scheduled = []
    for i, post in enumerate(posts):
        hour = start_hour + (i * interval_hours)
        scheduled.append({**post, "scheduled_hour": hour})
    return scheduled


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

        record = {
            "media_id": media_id,
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_deploy.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/deploy.py tests/test_deploy.py
git commit -m "feat: deploy module with scheduling and format sanitizer"
```

---

### Task 9: Main Orchestrator

**Files:**
- Create: `orchestrator/main.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_main.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL

- [ ] **Step 3: Implement main.py**

```python
# orchestrator/main.py
import sys
import traceback
from orchestrator.config import PHASE_SWITCH_FOLLOWER_THRESHOLD
from orchestrator.harvest import harvest
from orchestrator.analyze import analyze
from orchestrator.generate import generate
from orchestrator.deploy import deploy
from orchestrator.notify import send_notification
from orchestrator.threads_client import get_user_profile
from orchestrator.sources.youtube import fetch_all_channels
from orchestrator.sources.github import list_local_repos, fetch_recent_activity
from orchestrator.sources.x_curated import fetch_x_content, read_curated_file
from orchestrator.notify import fetch_incoming_messages


def detect_phase(follower_count: int) -> int:
    if follower_count >= PHASE_SWITCH_FOLLOWER_THRESHOLD:
        return 2
    return 1


def get_follower_count() -> int:
    try:
        profile = get_user_profile()
        # Follower count may not be in basic profile — fallback to 0
        return profile.get("follower_count", 0)
    except Exception:
        return 0


def fetch_sources() -> dict:
    print("[1/5] SOURCE: 抓取素材...")

    youtube = fetch_all_channels(hours=12)
    print(f"  YouTube: {len(youtube)} 部新影片")

    github = []
    for repo_path in list_local_repos():
        commits = fetch_recent_activity(repo_path, days=1)
        github.extend(commits)
    print(f"  GitHub: {len(github)} 個新 commit")

    telegram_msgs = fetch_incoming_messages()
    print(f"  Telegram: {len(telegram_msgs)} 則新訊息")
    x = fetch_x_content(telegram_msgs)
    print(f"  X.com: {len(x)} 則新素材（+ 策展檔案）")

    return {"youtube": youtube, "github": github, "x": x}


def run():
    try:
        follower_count = get_follower_count()
        phase = detect_phase(follower_count)
        print(f"[0/5] Phase {phase} | 追蹤者: {follower_count}")

        # Step 1: Source
        sources = fetch_sources()

        # Step 2: Harvest
        print("[2/5] HARVEST: 收割數據...")
        harvest_results = harvest()
        print(f"  收集到 {len(harvest_results)} 篇貼文數據")

        # Step 3: Analyze
        print("[3/5] ANALYZE: 分析表現...")
        analysis = analyze(harvest_results) if harvest_results else {
            "scored_posts": [],
            "analysis": "首次運行，無歷史數據",
            "learnings": "",
            "round_number": 1,
        }

        # Step 4: Generate
        print("[4/5] GENERATE: 產出新貼文...")
        new_posts = generate(analysis, sources)
        print(f"  產出 {len(new_posts)} 篇新貼文")

        # Step 5: Deploy
        print("[5/5] DEPLOY: 發佈貼文...")
        published = deploy(new_posts)
        published_count = sum(1 for p in published if p.get("media_id"))
        print(f"  成功發佈 {published_count} 篇")

        # Notification
        msg = (
            f"🔄 *AutoResearch Threads — Round {analysis.get('round_number', '?')}*\n"
            f"Phase: {phase} | 追蹤者: {follower_count}\n"
            f"素材: YT={len(sources['youtube'])} GH={len(sources['github'])} X={len(sources['x'])}\n"
            f"發佈: {published_count}/{len(new_posts)} 篇\n"
        )

        if harvest_results:
            top = analysis.get("scored_posts", [{}])[0] if analysis.get("scored_posts") else {}
            if top:
                msg += f"Top: score={top.get('score', 0)} views={top.get('views', 0)} | {top.get('text', '')[:50]}\n"

        if analysis.get("learnings"):
            msg += f"\n學習摘要:\n{analysis['learnings'][:300]}"

        send_notification(msg)
        print("\n✅ 迴圈完成")

    except Exception as e:
        error_msg = f"❌ AutoResearch Threads ERROR\n{type(e).__name__}: {e}"
        print(error_msg)
        traceback.print_exc()
        send_notification(error_msg)
        sys.exit(1)


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_main.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/main.py tests/test_main.py
git commit -m "feat: main orchestrator with 5-phase loop"
```

---

### Task 10: Prompt Files (Knowledge Base)

**Files:**
- Create: `prompts/program.md`
- Create: `prompts/swipe_file.md`
- Create: `prompts/resource.md`

- [ ] **Step 1: Create program.md**

```markdown
# Threads 貼文生成規則

## 你的角色
你是一個 AI 內容策略師，負責為一個 AI 主題的 Threads 帳號產出高觸及貼文。

## 核心目標
最大化貼文觸及（views），其次是互動（likes、replies）。

## 帳號定位
- 主題：AI 工具、AI 開發、AI 趨勢
- 語言：繁體中文
- 受眾：對 AI 有興趣的台灣用戶（開發者、創業者、知識工作者）

## 貼文維度

每篇貼文必須標記以下維度：

| 維度 | 選項 |
|------|------|
| content_type | 工具分享、開發心得、教學知識點、新聞/趨勢、觀點/辯論 |
| hook_style | 提問型、數據型、故事型、爭議型、清單型、送資源型 |
| format | 短句（<100字）、中篇（100-300字）、長文（300-500字） |
| tone | 專業分析、輕鬆口語、急迫感、教學口吻 |
| cta | 無CTA、追蹤我、留言互動、分享給朋友 |
| source | 素材來源（youtube/頻道名、github/repo名、x.com） |

## Phase 1 規則（探索模式）
- 每輪產出 3-5 篇，盡量覆蓋不同維度組合
- 不要連續兩篇用同一個 content_type
- 不要連續兩篇用同一個 hook_style
- 優先測試尚未嘗試過的維度組合

## Phase 2 規則（Tournament 模式）
- 基於當前 baseline（表現最好的貼文風格）產出 challenger
- 每次 challenger 只變 1-2 個維度
- 明確寫出 hypothesis：這次變了什麼，預期會怎樣

## 格式要求（Critical）
- 貼文內容必須是自然流暢的繁體中文
- 絕對不要出現 \n 或 \\n 等格式標記
- 不要用 markdown 語法（**粗體**、# 標題等）
- 換行就直接換行，不要加任何標記
- 500 字元以內

## 生成策略
1. 先讀累積學習（resource.md），遵守已驗證規則
2. 參考高表現範例（swipe_file.md）
3. 根據本輪素材選擇最適合的角度
4. 每篇附上 hypothesis 說明在測試什麼
```

- [ ] **Step 2: Create swipe_file.md**

```markdown
# 高表現貼文範例庫

## 送資源型（歷史表現較好）

範例 1：
「最近發現一個 AI 工具可以把任何 PDF 變成互動式筆記，重點是完全免費。
工具叫 NotebookLM，Google 出的。
丟一篇論文進去，它會自動整理重點、生成問答、甚至幫你做 podcast 風格的摘要。
學生、研究生、任何需要大量閱讀的人都該試試。」

範例 2：
「分享一個我每天都在用的 AI workflow：
用 Claude 寫初稿 → Cursor 寫程式 → v0 做 UI
三個工具串起來，一個人就能搞定以前三個人的工作量。
重點不是工具本身，是怎麼串。」

## 開發心得型

範例 1：
「昨天花了 4 小時 debug 一個 RAG pipeline 的問題。
最後發現原因超蠢：embedding model 和 retrieval model 用了不同的 tokenizer。
教訓：做 RAG 之前先確認整條 pipeline 的 tokenizer 一致。」

## 觀點型

範例 1：
「大家都在講 AI 要取代工程師，但我覺得真正會被取代的是不會用 AI 的工程師。
用 Claude Code 寫一天的程式量，等於我以前一週的輸出。
差距不是 AI 本身，是你願不願意改變工作流。」
```

- [ ] **Step 3: Create resource.md**

```markdown
# Threads Auto Research — 累積學習

## 已驗證規則
- 送資源型貼文（工具/模板/教學）觸及表現較好（來源：帳號經營者過去經驗）

## 待驗證假設
- H1: 提問型 hook > 數據型 hook（觸及）
- H2: 短句（<100字）> 長文（觸及優先場景）
- H3: 早上時段（09:00-13:00）> 晚上時段（21:00-23:00）
- H4: YouTube 熱門話題素材 > GitHub 開發心得素材
- H5: 送資源型 + 輕鬆口語 是最佳組合
- H6: 加 CTA「追蹤我」會降低觸及（演算法懲罰）
- H7: 爭議型 hook 觸及高但互動品質差

## 實驗記錄
（系統運行後自動累積）
```

- [ ] **Step 4: Create x_curated.md**

```markdown
# X.com 策展內容

透過 Telegram 轉發的 X.com 好內容會自動累積在這裡。
也可以手動編輯新增內容。

<!-- 系統每次迴圈會自動 append 新的 Telegram 訊息 -->
```

- [ ] **Step 5: Create data directory**

```bash
mkdir -p /Users/hua/autoresearch_threads/data
echo '[]' > /Users/hua/autoresearch_threads/data/posts.json
echo '[]' > /Users/hua/autoresearch_threads/data/metrics.json
echo '[]' > /Users/hua/autoresearch_threads/data/experiments.json
```

- [ ] **Step 6: Commit**

```bash
git add prompts/ data/
git commit -m "feat: prompt knowledge base and data directory"
```

---

### Task 11: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/autoresearch.yml`

- [ ] **Step 1: Create workflow file**

```yaml
# .github/workflows/autoresearch.yml
name: AutoResearch Threads Loop

on:
  schedule:
    - cron: '0 0 * * *'   # UTC 00:00 = 台灣 08:00
    - cron: '0 12 * * *'  # UTC 12:00 = 台灣 20:00
  workflow_dispatch:       # Manual trigger for testing

jobs:
  run-loop:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GH_PAT }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run orchestrator
        env:
          THREADS_ACCESS_TOKEN: ${{ secrets.THREADS_ACCESS_TOKEN }}
          THREADS_USER_ID: ${{ secrets.THREADS_USER_ID }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
        run: python -m orchestrator.main

      - name: Commit updated learnings and data
        run: |
          git config user.name "autoresearch-bot"
          git config user.email "bot@autoresearch.local"
          git add prompts/resource.md prompts/x_curated.md data/
          git diff --staged --quiet || git commit -m "chore: update learnings round $(date +%Y%m%d-%H%M)"
          git push
```

- [ ] **Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/autoresearch.yml
git commit -m "feat: GitHub Actions workflow for 12-hour loop"
```

---

### Task 12: Integration Test + First Dry Run

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
"""
Integration test: verifies the full loop runs end-to-end with mocks.
"""
from unittest.mock import patch, MagicMock
from orchestrator.main import run


def test_full_loop_first_run():
    """First run: no existing posts, no harvest data, generates and deploys."""

    mock_ai_response = MagicMock()
    mock_ai_response.content = [MagicMock(text='[{"text": "Test post", "dimensions": {"content_type": "工具分享", "hook_style": "送資源型", "format": "短句", "tone": "輕鬆口語", "cta": "無CTA", "source": "test"}, "hypothesis": "first test"}]')]

    with patch("orchestrator.main.get_follower_count", return_value=44), \
         patch("orchestrator.sources.youtube.requests.get") as mock_yt, \
         patch("orchestrator.harvest.harvest_browser", return_value={}), \
         patch("orchestrator.harvest.harvest_api", return_value={}), \
         patch("orchestrator.threads_client.requests.post") as mock_threads_post, \
         patch("orchestrator.threads_client.requests.get") as mock_threads_get, \
         patch("orchestrator.threads_client.time.sleep"), \
         patch("orchestrator.notify.requests.post") as mock_tg, \
         patch("orchestrator.analyze.anthropic") as mock_anthropic_analyze, \
         patch("orchestrator.generate.anthropic") as mock_anthropic_gen:

        # YouTube returns no videos
        mock_yt_resp = MagicMock()
        mock_yt_resp.status_code = 200
        mock_yt_resp.json.return_value = {"items": []}
        mock_yt.return_value = mock_yt_resp

        # Threads publish
        mock_create = MagicMock()
        mock_create.status_code = 200
        mock_create.json.return_value = {"id": "container_1"}
        mock_create.raise_for_status = MagicMock()

        mock_publish = MagicMock()
        mock_publish.status_code = 200
        mock_publish.json.return_value = {"id": "media_1"}
        mock_publish.raise_for_status = MagicMock()

        mock_threads_post.side_effect = [mock_create, mock_publish]

        # Telegram
        mock_tg_resp = MagicMock()
        mock_tg_resp.status_code = 200
        mock_tg.return_value = mock_tg_resp

        # AI generate
        mock_gen_client = MagicMock()
        mock_gen_client.messages.create.return_value = mock_ai_response
        mock_anthropic_gen.Anthropic.return_value = mock_gen_client

        run()

    # Verify Threads was called (create + publish)
    assert mock_threads_post.call_count >= 2
    # Verify Telegram was notified
    mock_tg.assert_called()
```

- [ ] **Step 2: Run integration test**

Run: `python -m pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "feat: integration test for full loop dry run"
```

---

### Task 13: Setup .env and First Real Run

- [ ] **Step 1: Copy .env.example to .env and fill in credentials**

```bash
cp .env.example .env
# User fills in: THREADS_ACCESS_TOKEN, THREADS_USER_ID, ANTHROPIC_API_KEY,
#                TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, YOUTUBE_API_KEY
```

- [ ] **Step 2: Fill in YouTube channel IDs in config**

Open `orchestrator/sources/youtube.py` and fill in the `CHANNEL_IDS` dict with actual YouTube channel IDs for all 8 channels.

- [ ] **Step 3: Create virtual environment and install deps**

```bash
cd /Users/hua/autoresearch_threads
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 4: Run the orchestrator locally**

```bash
python -m orchestrator.main
```

Expected: System runs through all 5 phases, generates posts, publishes to Threads, sends Telegram notification.

- [ ] **Step 5: Verify on Threads**

Check Threads app — new posts should be visible.

- [ ] **Step 6: Push to GitHub and configure secrets**

```bash
git remote add origin <your-repo-url>
git push -u origin main
```

Then go to GitHub → Settings → Secrets and add all env vars from `.env`.

- [ ] **Step 7: Manually trigger GitHub Action to verify**

```bash
gh workflow run autoresearch.yml
```

- [ ] **Step 8: Commit any final adjustments**

```bash
git add -A
git commit -m "chore: finalize setup and configuration"
```
