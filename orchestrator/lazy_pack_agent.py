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
