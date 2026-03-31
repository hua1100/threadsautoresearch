# Lazy Pack Python System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python-side lazy pack system: R2 upload client, PDF generation, Claude content generation, Telegram trigger, auto-reply on Threads, and Strategy Agent integration.

**Architecture:** `lazy_pack_agent.py` orchestrates the flow: Claude generates content → `pdf_generator.py` converts to PDF → `r2_client.py` uploads to Cloudflare R2 and updates index → `threads_client.reply_to_post()` posts CTA comment → Telegram notification. Strategy Agent triggers auto-detection; Telegram messages trigger manual generation.

**Tech Stack:** Python 3.14, anthropic SDK, boto3 (S3-compatible R2), weasyprint (Markdown→PDF), existing orchestrator modules

**Spec:** `docs/superpowers/specs/2026-03-31-lazy-pack-design.md`

**Prerequisite:** Plan 1 (Cloudflare Worker + R2) must be deployed first. `WORKER_BASE_URL`, `R2_*` env vars must be set.

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `orchestrator/r2_client.py` | Upload PDF to R2, update index.json |
| Create | `orchestrator/pdf_generator.py` | Markdown → PDF conversion |
| Create | `orchestrator/lazy_pack_agent.py` | Main orchestration: generate content, produce PDF, upload, post CTA |
| Modify | `orchestrator/config.py` | New env vars (LINE, R2, WORKER_BASE_URL, LAZY_PACK_MIN_VIEWS) |
| Modify | `orchestrator/strategy_agent.py` | Auto-trigger Top 1 lazy pack, add funnel data to prompt |
| Modify | `orchestrator/main.py` | Parse Telegram "懶人包" trigger |
| Create | `tests/test_r2_client.py` | R2 upload + index update tests |
| Create | `tests/test_pdf_generator.py` | PDF generation tests |
| Create | `tests/test_lazy_pack_agent.py` | Full flow tests |

---

### Task 1: Config — new env vars

**Files:**
- Modify: `orchestrator/config.py:41-43`

- [ ] **Step 1: Add new config vars**

Add to the end of `orchestrator/config.py` (after the existing SUBSTACK vars):

```python
# LINE Messaging API
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_ADD_FRIEND_URL = os.environ.get("LINE_ADD_FRIEND_URL", "")

# Cloudflare R2
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "lazy-packs")

# Lazy Pack
WORKER_BASE_URL = os.environ.get("WORKER_BASE_URL", "")
LAZY_PACK_MIN_VIEWS = int(os.getenv("LAZY_PACK_MIN_VIEWS", "5000"))
LAZY_PACKS_DIR = BASE_DIR / "data" / "lazy_packs"
```

- [ ] **Step 2: Add env vars to .env**

Append to `.env`:

```
# LINE Messaging API
LINE_CHANNEL_ACCESS_TOKEN=你的token
LINE_CHANNEL_SECRET=你的secret
LINE_ADD_FRIEND_URL=https://line.me/R/ti/p/@你的帳號

# Cloudflare R2
R2_ACCOUNT_ID=你的account_id
R2_ACCESS_KEY_ID=你的access_key
R2_SECRET_ACCESS_KEY=你的secret_key
R2_BUCKET_NAME=lazy-packs

# Lazy Pack
WORKER_BASE_URL=https://lazy-pack-worker.你的subdomain.workers.dev
LAZY_PACK_MIN_VIEWS=5000
```

- [ ] **Step 3: Install new dependency**

Add `boto3>=1.34.0` and `weasyprint>=60.0` to `requirements.txt`, then:

```bash
.venv/bin/pip install boto3 weasyprint
```

- [ ] **Step 4: Commit**

```bash
git add orchestrator/config.py requirements.txt
git commit -m "feat: add LINE, R2, and lazy pack config vars"
```

---

### Task 2: R2 client — upload PDF + update index

**Files:**
- Create: `orchestrator/r2_client.py`
- Create: `tests/test_r2_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_r2_client.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from orchestrator.r2_client import upload_pdf, update_index


def test_upload_pdf_calls_s3_put():
    """upload_pdf uploads file to R2 via S3 API."""
    mock_s3 = MagicMock()

    with patch("orchestrator.r2_client._get_s3_client", return_value=mock_s3):
        url = upload_pdf("/tmp/test.pdf", "ai-agent")

    mock_s3.upload_file.assert_called_once_with(
        "/tmp/test.pdf",
        "lazy-packs",
        "lazy-packs/ai-agent.pdf",
        ExtraArgs={"ContentType": "application/pdf"},
    )
    assert "ai-agent.pdf" in url


def test_upload_pdf_returns_worker_url():
    """upload_pdf returns the Worker download URL."""
    mock_s3 = MagicMock()

    with patch("orchestrator.r2_client._get_s3_client", return_value=mock_s3), \
         patch("orchestrator.r2_client.WORKER_BASE_URL", "https://worker.example.com"):
        url = upload_pdf("/tmp/test.pdf", "ai-agent")

    assert url == "https://worker.example.com/lazy-packs/ai-agent.pdf"


def test_update_index_adds_new_entry():
    """update_index downloads index.json, appends entry, re-uploads."""
    mock_s3 = MagicMock()
    # Simulate existing index with one entry
    existing_body = MagicMock()
    existing_body.read.return_value = json.dumps([
        {"keyword": "old", "title": "Old Pack", "url": "https://example.com/old.pdf"}
    ]).encode()
    mock_s3.get_object.return_value = {"Body": existing_body}

    with patch("orchestrator.r2_client._get_s3_client", return_value=mock_s3):
        update_index("ai-agent", "AI Agent 攻略", "https://example.com/ai-agent.pdf")

    # Verify put_object was called with updated index
    put_call = mock_s3.put_object.call_args
    body = json.loads(put_call[1]["Body"])
    assert len(body) == 2
    assert body[1]["keyword"] == "ai-agent"
    assert body[1]["title"] == "AI Agent 攻略"


def test_update_index_creates_new_when_empty():
    """update_index creates index.json when it doesn't exist."""
    mock_s3 = MagicMock()
    from botocore.exceptions import ClientError
    mock_s3.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey"}}, "GetObject"
    )

    with patch("orchestrator.r2_client._get_s3_client", return_value=mock_s3):
        update_index("first", "First Pack", "https://example.com/first.pdf")

    put_call = mock_s3.put_object.call_args
    body = json.loads(put_call[1]["Body"])
    assert len(body) == 1
    assert body[0]["keyword"] == "first"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_r2_client.py -v`
Expected: ImportError

- [ ] **Step 3: Implement r2_client.py**

Create `orchestrator/r2_client.py`:

```python
"""Cloudflare R2 client — upload PDFs and manage index via S3-compatible API."""
import json
import boto3
from botocore.exceptions import ClientError
from orchestrator.config import (
    R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME, WORKER_BASE_URL,
)


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def upload_pdf(local_path: str, keyword: str) -> str:
    """Upload a PDF to R2 and return the Worker download URL."""
    s3 = _get_s3_client()
    r2_key = f"lazy-packs/{keyword}.pdf"
    s3.upload_file(
        local_path,
        R2_BUCKET_NAME,
        r2_key,
        ExtraArgs={"ContentType": "application/pdf"},
    )
    return f"{WORKER_BASE_URL}/lazy-packs/{keyword}.pdf"


def update_index(keyword: str, title: str, url: str) -> None:
    """Add a new entry to the lazy-packs/index.json in R2."""
    s3 = _get_s3_client()
    index_key = "lazy-packs/index.json"

    # Download existing index
    try:
        resp = s3.get_object(Bucket=R2_BUCKET_NAME, Key=index_key)
        index = json.loads(resp["Body"].read().decode())
    except ClientError:
        index = []

    # Remove existing entry with same keyword (update)
    index = [e for e in index if e["keyword"] != keyword]

    index.append({
        "keyword": keyword,
        "title": title,
        "url": url,
    })

    s3.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=index_key,
        Body=json.dumps(index, ensure_ascii=False),
        ContentType="application/json",
    )
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_r2_client.py -v`
Expected: All 4 PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/r2_client.py tests/test_r2_client.py
git commit -m "feat: add R2 client for PDF upload and index management"
```

---

### Task 3: PDF generator — Markdown to PDF

**Files:**
- Create: `orchestrator/pdf_generator.py`
- Create: `tests/test_pdf_generator.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_pdf_generator.py`:

```python
import os
import pytest
from pathlib import Path
from orchestrator.pdf_generator import generate_pdf


def test_generate_pdf_creates_file(tmp_path):
    """generate_pdf creates a PDF file from markdown content."""
    content = "# 測試懶人包\n\n## 核心概念\n這是一個測試。\n\n## 重點整理\n1. 第一點\n2. 第二點"
    title = "測試懶人包"
    output_path = tmp_path / "test.pdf"

    generate_pdf(content, title, str(output_path))

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    # PDF starts with %PDF
    with open(output_path, "rb") as f:
        header = f.read(4)
    assert header == b"%PDF"


def test_generate_pdf_handles_chinese(tmp_path):
    """generate_pdf correctly renders Chinese characters."""
    content = "# AI Agent 完整攻略\n\n短影音不是靠量取勝，是靠懂「你是誰」。"
    output_path = tmp_path / "chinese.pdf"

    generate_pdf(content, "AI Agent 完整攻略", str(output_path))

    assert output_path.exists()
    assert output_path.stat().st_size > 100  # non-trivial size
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_pdf_generator.py -v`
Expected: ImportError

- [ ] **Step 3: Implement pdf_generator.py**

Create `orchestrator/pdf_generator.py`:

```python
"""PDF generator — convert Markdown lazy pack content to styled PDF."""
import markdown
from weasyprint import HTML


CSS = """
@page {
    size: A4;
    margin: 2cm;
}
body {
    font-family: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
    font-size: 14px;
    line-height: 1.8;
    color: #333;
}
h1 {
    font-size: 24px;
    color: #1a1a1a;
    border-bottom: 2px solid #333;
    padding-bottom: 8px;
    margin-bottom: 16px;
}
h2 {
    font-size: 18px;
    color: #2c2c2c;
    margin-top: 24px;
    margin-bottom: 8px;
}
ol, ul {
    padding-left: 24px;
}
li {
    margin-bottom: 8px;
}
.footer {
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid #ccc;
    font-size: 12px;
    color: #666;
    text-align: center;
}
"""

FOOTER_HTML = """
<div class="footer">
    AI for…？ | Threads @hualeee | LINE 官方帳號
</div>
"""


def generate_pdf(content: str, title: str, output_path: str) -> None:
    """Convert Markdown content to a styled PDF file.

    Args:
        content: Markdown text (the lazy pack body).
        title: Pack title (used in HTML <title>).
        output_path: Where to save the PDF.
    """
    html_body = markdown.markdown(content, extensions=["extra"])

    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>{CSS}</style>
</head>
<body>
{html_body}
{FOOTER_HTML}
</body>
</html>"""

    HTML(string=full_html).write_pdf(output_path)
```

- [ ] **Step 4: Install markdown dependency**

```bash
.venv/bin/pip install markdown
```

Add `markdown>=3.5.0` to `requirements.txt`.

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_pdf_generator.py -v`
Expected: All 2 PASS

- [ ] **Step 6: Commit**

```bash
git add orchestrator/pdf_generator.py tests/test_pdf_generator.py requirements.txt
git commit -m "feat: add PDF generator for lazy pack content"
```

---

### Task 4: Lazy Pack Agent — main orchestration

**Files:**
- Create: `orchestrator/lazy_pack_agent.py`
- Create: `tests/test_lazy_pack_agent.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_lazy_pack_agent.py`:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from orchestrator.lazy_pack_agent import generate_lazy_pack, parse_telegram_trigger


def test_parse_telegram_trigger_with_media_id():
    """Parses '懶人包 12345' into media_id."""
    result = parse_telegram_trigger("懶人包 12345")
    assert result == "12345"


def test_parse_telegram_trigger_with_permalink():
    """Parses '懶人包 https://threads.com/t/...' and extracts ID."""
    result = parse_telegram_trigger("懶人包 https://www.threads.net/@hualeee/post/abc123")
    assert result == "https://www.threads.net/@hualeee/post/abc123"


def test_parse_telegram_trigger_no_match():
    """Returns None for non-trigger messages."""
    assert parse_telegram_trigger("hello") is None
    assert parse_telegram_trigger("懶人包") is None


def test_generate_lazy_pack_full_flow(tmp_path, monkeypatch):
    """Full generation flow: Claude → PDF → R2 → Threads reply → record."""
    monkeypatch.setattr("orchestrator.lazy_pack_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.lazy_pack_agent.LAZY_PACKS_DIR", tmp_path / "lazy_packs")
    monkeypatch.setattr("orchestrator.lazy_pack_agent.LINE_ADD_FRIEND_URL", "https://line.me/test")
    monkeypatch.setattr("orchestrator.lazy_pack_agent.WORKER_BASE_URL", "https://worker.test")

    post = {
        "media_id": "media_123",
        "text": "AI Agent 很厲害",
        "dimensions": {"content_type": "工具分享", "source": "youtube/test"},
    }

    claude_response = json.dumps({
        "keyword": "ai-agent",
        "title": "AI Agent 完整攻略",
        "content": "# AI Agent 完整攻略\n\n## 核心概念\n很重要\n\n## 重點\n1. 第一點",
    }, ensure_ascii=False)

    mock_anthropic_resp = MagicMock()
    mock_anthropic_resp.content = [MagicMock(text=claude_response)]

    with patch("orchestrator.lazy_pack_agent.anthropic.Anthropic") as MockAnthropic, \
         patch("orchestrator.lazy_pack_agent.generate_pdf") as mock_pdf, \
         patch("orchestrator.lazy_pack_agent.upload_pdf", return_value="https://worker.test/lazy-packs/ai-agent.pdf") as mock_upload, \
         patch("orchestrator.lazy_pack_agent.update_index") as mock_index, \
         patch("orchestrator.lazy_pack_agent.threads_client") as mock_tc, \
         patch("orchestrator.lazy_pack_agent.send_notification") as mock_notify:

        MockAnthropic.return_value.messages.create.return_value = mock_anthropic_resp

        result = generate_lazy_pack(post)

    assert result["keyword"] == "ai-agent"
    assert result["title"] == "AI Agent 完整攻略"
    assert "worker.test" in result["pdf_url"]

    # Verify PDF was generated
    mock_pdf.assert_called_once()

    # Verify R2 upload
    mock_upload.assert_called_once_with(str(tmp_path / "lazy_packs" / "ai-agent.pdf"), "ai-agent")

    # Verify index updated
    mock_index.assert_called_once_with("ai-agent", "AI Agent 完整攻略", "https://worker.test/lazy-packs/ai-agent.pdf")

    # Verify Threads reply
    mock_tc.reply_to_post.assert_called_once()
    reply_text = mock_tc.reply_to_post.call_args[0][1]
    assert "ai-agent" in reply_text
    assert "line.me" in reply_text

    # Verify lazy_packs.json updated
    packs = json.loads((tmp_path / "lazy_packs.json").read_text())
    assert len(packs) == 1
    assert packs[0]["keyword"] == "ai-agent"

    # Verify Telegram notification
    mock_notify.assert_called_once()


def test_generate_lazy_pack_skips_duplicate(tmp_path, monkeypatch):
    """Skips generation if keyword already exists in lazy_packs.json."""
    monkeypatch.setattr("orchestrator.lazy_pack_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.lazy_pack_agent.LAZY_PACKS_DIR", tmp_path / "lazy_packs")

    # Pre-existing pack
    (tmp_path / "lazy_packs.json").write_text(json.dumps([
        {"media_id": "media_123", "keyword": "ai-agent", "pdf_url": "https://example.com"}
    ]))

    post = {"media_id": "media_123", "text": "test", "dimensions": {}}

    result = generate_lazy_pack(post)

    assert result is None  # Skipped
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_lazy_pack_agent.py -v`
Expected: ImportError

- [ ] **Step 3: Implement lazy_pack_agent.py**

Create `orchestrator/lazy_pack_agent.py`:

```python
"""Lazy Pack Agent: 自動生成懶人包 PDF 並發佈到 R2 + Threads + LINE"""
import json
import anthropic
from datetime import datetime, timezone
from orchestrator.config import (
    ANTHROPIC_API_KEY, DATA_DIR, LAZY_PACKS_DIR,
    LINE_ADD_FRIEND_URL, WORKER_BASE_URL,
)
from orchestrator.utils import read_json, write_json
from orchestrator.pdf_generator import generate_pdf
from orchestrator.r2_client import upload_pdf, update_index
from orchestrator import threads_client
from orchestrator.notify import send_notification


def parse_telegram_trigger(text: str) -> str | None:
    """Parse a Telegram message for lazy pack trigger.

    Formats:
        '懶人包 <media_id>'
        '懶人包 <permalink>'

    Returns the media_id or permalink, or None if not a trigger.
    """
    if not text.startswith("懶人包 "):
        return None
    target = text[4:].strip()
    return target if target else None


def generate_lazy_pack(post: dict) -> dict | None:
    """Generate a lazy pack for a post. Returns pack record or None if skipped.

    Args:
        post: Dict with media_id, text, dimensions.
    """
    media_id = post.get("media_id", "")

    # Check for duplicates
    packs = read_json(DATA_DIR / "lazy_packs.json")
    if not isinstance(packs, list):
        packs = []
    if any(p.get("media_id") == media_id for p in packs):
        print(f"[LAZY_PACK] Already exists for {media_id}, skipping")
        return None

    # Generate content with Claude
    source = post.get("dimensions", {}).get("source", "")
    prompt = f"""你是一個 AI 內容整理師。根據以下 Threads 貼文，生成一份「懶人包」。

原貼文：{post.get('text', '')}
素材來源：{source}

格式要求：
1. 標題（吸引人的懶人包標題）
2. 核心概念（1-2 句話總結）
3. 重點整理（5-8 個，每個一句標題 + 2-3 句說明）
4. 行動建議（具體可執行的 1-3 步）
5. 一句話總結

繁體中文，800-1500 字。

回傳 JSON 格式：
{{"keyword": "簡短英文關鍵字（如 ai-agent）", "title": "懶人包標題", "content": "Markdown 格式的懶人包內容"}}

只輸出 JSON，不要其他文字。"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    data = json.loads(raw)
    keyword = data["keyword"]
    title = data["title"]
    content = data["content"]

    # Generate PDF
    LAZY_PACKS_DIR.mkdir(parents=True, exist_ok=True)
    local_pdf = str(LAZY_PACKS_DIR / f"{keyword}.pdf")
    generate_pdf(content, title, local_pdf)
    print(f"[LAZY_PACK] PDF generated: {local_pdf}")

    # Upload to R2
    pdf_url = upload_pdf(local_pdf, keyword)
    update_index(keyword, title, pdf_url)
    print(f"[LAZY_PACK] Uploaded to R2: {pdf_url}")

    # Reply on Threads
    try:
        reply_text = (
            f"🎁 這篇的完整懶人包整理好了！\n"
            f"加入我的 LINE 官方帳號，輸入「{keyword}」立刻領取 👇\n"
            f"{LINE_ADD_FRIEND_URL}"
        )
        threads_client.reply_to_post(media_id, reply_text)
        print(f"[LAZY_PACK] Threads reply posted on {media_id}")
    except Exception as e:
        print(f"[LAZY_PACK] Threads reply failed: {e}")

    # Record
    record = {
        "media_id": media_id,
        "keyword": keyword,
        "title": title,
        "pdf_url": pdf_url,
        "source_text": post.get("text", "")[:80],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    packs.append(record)
    write_json(DATA_DIR / "lazy_packs.json", packs)

    # Notify
    send_notification(
        f"📦 *懶人包已上線*\n"
        f"標題：{title}\n"
        f"關鍵字：{keyword}\n"
        f"連結：{pdf_url}"
    )

    return record
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_lazy_pack_agent.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/lazy_pack_agent.py tests/test_lazy_pack_agent.py
git commit -m "feat: add lazy pack agent with full generation flow"
```

---

### Task 5: Strategy Agent — auto-trigger Top 1 lazy pack

**Files:**
- Modify: `orchestrator/strategy_agent.py`
- Modify: `tests/test_strategy_agent.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_strategy_agent.py`:

```python
def test_strategy_agent_triggers_lazy_pack_for_top_post(tmp_path, monkeypatch):
    """Strategy agent triggers lazy pack for top post when views >= threshold."""
    monkeypatch.setattr("orchestrator.strategy_agent.DATA_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("orchestrator.strategy_agent.SUBSTACK_SID", "")
    monkeypatch.setattr("orchestrator.strategy_agent.LAZY_PACK_MIN_VIEWS", 100)

    # Create experiments with a high-performing post
    experiments = [
        {
            "harvested_at": datetime.now(timezone.utc).isoformat(),
            "results": [
                {"media_id": "top_1", "score": 1.0, "views": 5000, "likes": 50, "replies": 10},
                {"media_id": "low_1", "score": 0.2, "views": 50, "likes": 1, "replies": 0},
            ],
        }
    ]

    # Create posts.json so we can look up the full post
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

    # Verify lazy pack was triggered for the top post
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

    # Already exists
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_strategy_agent.py::test_strategy_agent_triggers_lazy_pack_for_top_post -v`
Expected: FAIL

- [ ] **Step 3: Add lazy pack trigger to strategy_agent.py**

Add import at the top of `orchestrator/strategy_agent.py`:

```python
from orchestrator.config import (
    ANTHROPIC_API_KEY, PROMPTS_DIR, DATA_DIR, SUBSTACK_SID, SUBSTACK_SUBDOMAIN,
    LAZY_PACK_MIN_VIEWS,
)
from orchestrator.lazy_pack_agent import generate_lazy_pack
```

Add this block at the end of `run()`, before `if __name__`:

```python
    # Auto-trigger lazy pack for top performing post
    try:
        all_results = [
            r for exp in experiments for r in exp.get("results", [])
        ]
        if all_results:
            top = max(all_results, key=lambda x: x.get("score", 0))
            if top.get("views", 0) >= LAZY_PACK_MIN_VIEWS:
                # Check if already generated
                existing_packs = read_json(DATA_DIR / "lazy_packs.json")
                if not isinstance(existing_packs, list):
                    existing_packs = []
                already_done = any(
                    p.get("media_id") == top.get("media_id") for p in existing_packs
                )
                if not already_done:
                    # Look up full post data from posts.json
                    all_posts = read_json(DATA_DIR / "posts.json")
                    if isinstance(all_posts, list):
                        full_post = next(
                            (p for p in all_posts if p.get("media_id") == top.get("media_id")),
                            None,
                        )
                        if full_post:
                            print(f"[STRATEGY] Triggering lazy pack for top post: {top.get('media_id')}")
                            generate_lazy_pack(full_post)
    except Exception as e:
        print(f"[STRATEGY] Lazy pack trigger failed: {e}")
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_strategy_agent.py -v`
Expected: All 8 PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/strategy_agent.py tests/test_strategy_agent.py
git commit -m "feat: auto-trigger lazy pack for top performing post in strategy agent"
```

---

### Task 6: Content Agent — Telegram trigger

**Files:**
- Modify: `orchestrator/main.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_main.py`:

```python
def test_process_lazy_pack_triggers(tmp_path, monkeypatch):
    """process_lazy_pack_triggers detects '懶人包' messages and triggers generation."""
    monkeypatch.setattr("orchestrator.main.DATA_DIR", tmp_path)

    posts = [{"media_id": "m_123", "text": "test post", "dimensions": {}}]
    (tmp_path / "posts.json").write_text(json.dumps(posts))

    messages = ["懶人包 m_123", "some other message", "懶人包 m_456"]

    with patch("orchestrator.main.generate_lazy_pack") as mock_gen:
        from orchestrator.main import process_lazy_pack_triggers
        process_lazy_pack_triggers(messages)

    # Only m_123 has a matching post in posts.json
    assert mock_gen.call_count == 1
    assert mock_gen.call_args[0][0]["media_id"] == "m_123"
```

- [ ] **Step 2: Run tests to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_main.py::test_process_lazy_pack_triggers -v`
Expected: ImportError

- [ ] **Step 3: Implement process_lazy_pack_triggers**

Add import to `orchestrator/main.py`:

```python
from orchestrator.lazy_pack_agent import generate_lazy_pack, parse_telegram_trigger
```

Add function before `run()`:

```python
def process_lazy_pack_triggers(messages: list[str]) -> None:
    """Check Telegram messages for lazy pack triggers and generate."""
    all_posts = read_json(DATA_DIR / "posts.json")
    if not isinstance(all_posts, list):
        return

    for msg in messages:
        target = parse_telegram_trigger(msg)
        if not target:
            continue

        # Find post by media_id or permalink
        post = next(
            (p for p in all_posts
             if p.get("media_id") == target or p.get("permalink") == target),
            None,
        )
        if post:
            print(f"[LAZY_PACK] Telegram trigger for {target}")
            try:
                generate_lazy_pack(post)
            except Exception as e:
                print(f"[LAZY_PACK] Generation failed: {e}")
        else:
            print(f"[LAZY_PACK] Post not found: {target}")
```

In the `run()` function, after `fetch_sources()` processes telegram messages, add a call. Find the line after `sources = fetch_sources()` and add:

```python
        sources = fetch_sources()

        # Check for lazy pack triggers in Telegram messages
        process_lazy_pack_triggers(telegram_msgs)
```

Wait — `telegram_msgs` is not accessible in `run()` because `fetch_sources()` processes them internally. We need to capture the raw messages. Modify `fetch_sources()` to return them:

Actually, looking at the code, `fetch_incoming_messages()` is called inside `fetch_sources()` and the messages are passed to `fetch_x_content()`. The raw messages are available as `telegram_msgs` inside `fetch_sources()` but not returned.

The simplest fix: call `process_lazy_pack_triggers` inside `fetch_sources()` before returning, or refactor slightly. Let's add it after `fetch_sources`:

In `run()`, the telegram messages are already consumed by `fetch_sources`. But we can re-process them. Better approach: have `fetch_sources` return the raw messages too, or just call `process_lazy_pack_triggers` from within `fetch_sources`.

Simplest: add it inside `fetch_sources`:

```python
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

    # Process lazy pack triggers from Telegram
    process_lazy_pack_triggers(telegram_msgs)

    x = fetch_x_content(telegram_msgs)
    print(f"  X.com: {len(x)} 則新素材（+ 策展檔案）")

    return {"youtube": youtube, "github": github, "x": x}
```

- [ ] **Step 4: Update test_run_executes_full_loop**

Add mock for `process_lazy_pack_triggers` in the existing full loop test:

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

Note: `process_lazy_pack_triggers` is called inside `fetch_sources`, which is already mocked. So no extra mock needed — it won't actually run.

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_main.py -v`
Expected: All 8 PASS

- [ ] **Step 6: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add orchestrator/main.py tests/test_main.py
git commit -m "feat: add Telegram lazy pack trigger in Content Agent"
```

---

### Task 7: Integration smoke test

**Files:**
- No new files

- [ ] **Step 1: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Dry-run lazy pack generation with mock**

```bash
.venv/bin/python -c "
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

print('=== Lazy Pack E2E Dry Run ===')

# Test parse_telegram_trigger
from orchestrator.lazy_pack_agent import parse_telegram_trigger
assert parse_telegram_trigger('懶人包 media_123') == 'media_123'
assert parse_telegram_trigger('hello') is None
print('✅ parse_telegram_trigger OK')

# Test generate_lazy_pack flow with mocks
from orchestrator.lazy_pack_agent import generate_lazy_pack
from orchestrator.config import DATA_DIR, LAZY_PACKS_DIR

claude_resp = json.dumps({
    'keyword': 'test-pack',
    'title': '測試懶人包',
    'content': '# 測試\n\n內容',
}, ensure_ascii=False)

mock_resp = MagicMock()
mock_resp.content = [MagicMock(text=claude_resp)]

with patch('orchestrator.lazy_pack_agent.anthropic.Anthropic') as M, \
     patch('orchestrator.lazy_pack_agent.generate_pdf'), \
     patch('orchestrator.lazy_pack_agent.upload_pdf', return_value='https://test/test.pdf'), \
     patch('orchestrator.lazy_pack_agent.update_index'), \
     patch('orchestrator.lazy_pack_agent.threads_client'), \
     patch('orchestrator.lazy_pack_agent.send_notification'):
    M.return_value.messages.create.return_value = mock_resp
    result = generate_lazy_pack({'media_id': 'test', 'text': 'test', 'dimensions': {}})

assert result['keyword'] == 'test-pack'
print(f'✅ generate_lazy_pack OK: {result[\"title\"]}')

# Clean up
import os
lp = DATA_DIR / 'lazy_packs.json'
if lp.exists():
    os.remove(lp)

print('\n=== All dry runs passed ===')
"
```

- [ ] **Step 3: Commit final state**

```bash
git add -A && git status
# If clean, skip. Otherwise:
git commit -m "chore: lazy pack integration verified"
```
