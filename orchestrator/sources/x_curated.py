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

    for msg in telegram_messages:
        results.append({
            "text": msg,
            "source": "telegram",
            "received_at": datetime.now(timezone.utc).isoformat(),
        })

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
