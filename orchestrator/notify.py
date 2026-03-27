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
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if chat_id != TELEGRAM_CHAT_ID:
            continue

        text = msg.get("text", "")
        if text:
            messages.append(text)

    if max_update_id > offset:
        offset_path.parent.mkdir(parents=True, exist_ok=True)
        with open(offset_path, "w") as f:
            json.dump({"offset": max_update_id}, f)

    return messages
