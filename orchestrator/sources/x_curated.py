"""
Content sourcing via Telegram messages.
User forwards interesting content (X posts, YouTube videos, etc.) to the bot.
YouTube URLs are automatically transcribed.
"""
import re
from datetime import datetime, timezone
from pathlib import Path
from orchestrator.config import PROMPTS_DIR


YOUTUBE_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([\w-]{11})"
)


def _extract_youtube_id(text: str) -> str | None:
    match = YOUTUBE_URL_PATTERN.search(text)
    return match.group(1) if match else None


def _fetch_transcript(video_id: str) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        fetcher = YouTubeTranscriptApi()
        transcript = fetcher.fetch(video_id, languages=["en", "zh-Hant", "zh-Hans", "zh"])
        return " ".join(snippet.text for snippet in transcript)
    except Exception as e:
        print(f"[SOURCE] Transcript error for {video_id}: {e}")
        return ""


def fetch_x_content(telegram_messages: list[str], curated_path: str | None = None) -> list[dict]:
    if curated_path is None:
        curated_path = str(PROMPTS_DIR / "x_curated.md")

    results = []
    enriched_messages = []

    for msg in telegram_messages:
        video_id = _extract_youtube_id(msg)
        if video_id:
            transcript = _fetch_transcript(video_id)
            if transcript:
                # Truncate long transcripts
                truncated = transcript[:3000] + "..." if len(transcript) > 3000 else transcript
                enriched = f"{msg}\n\n[逐字稿] {truncated}"
                enriched_messages.append(enriched)
                results.append({
                    "text": enriched,
                    "source": "telegram/youtube",
                    "video_id": video_id,
                    "received_at": datetime.now(timezone.utc).isoformat(),
                })
            else:
                enriched_messages.append(msg)
                results.append({
                    "text": msg,
                    "source": "telegram",
                    "received_at": datetime.now(timezone.utc).isoformat(),
                })
        else:
            enriched_messages.append(msg)
            results.append({
                "text": msg,
                "source": "telegram",
                "received_at": datetime.now(timezone.utc).isoformat(),
            })

    if enriched_messages:
        _append_to_curated(enriched_messages, curated_path)

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
    current = path.read_text(encoding="utf-8") if path.exists() else "# 策展內容\n"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    new_entries = f"\n\n## {date_str} (via Telegram)\n"
    for msg in messages:
        new_entries += f"- {msg}\n"
    path.write_text(current + new_entries, encoding="utf-8")
