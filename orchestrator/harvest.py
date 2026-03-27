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
