import time
import requests
from orchestrator.config import THREADS_ACCESS_TOKEN, THREADS_USER_ID

BASE_URL = "https://graph.threads.net/v1.0"


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


def reply_to_post(media_id: str, text: str) -> str | None:
    """Reply to an existing post with a comment."""
    creation_id = create_post(text, reply_to_id=media_id)
    if not creation_id:
        return None
    time.sleep(30)
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


def get_post_permalink(media_id: str) -> str | None:
    url = f"{BASE_URL}/{media_id}"
    params = {
        "fields": "permalink",
        "access_token": THREADS_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return None
    return resp.json().get("permalink")


def get_user_insights() -> dict:
    """Fetch user-level insights (followers_count, etc.)."""
    url = f"{BASE_URL}/{THREADS_USER_ID}/threads_insights"
    params = {
        "metric": "followers_count",
        "access_token": THREADS_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return {}
    data = resp.json().get("data", [])
    result = {}
    for item in data:
        total = item.get("total_value", {})
        if "value" in total:
            result[item["name"]] = total["value"]
    return result


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
