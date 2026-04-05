from __future__ import annotations
import json
from pathlib import Path
from orchestrator.config import (
    APIFY_API_TOKEN,
    ANTHROPIC_API_KEY,
    COMPETITOR_THREADS_ACCOUNTS,
    COMPETITOR_X_SEARCH_KEYWORDS,
    COMPETITOR_POSTS_PER_ACCOUNT,
    COMPETITOR_X_TOP_N,
    COMPETITOR_X_MAX_FOLLOWERS,
    DATA_DIR,
    PROMPTS_DIR,
)
from orchestrator.apify_client import run_actor, ApifyError
from orchestrator.notify import send_notification


def discover_x_accounts(
    top_n: int = COMPETITOR_X_TOP_N,
    max_followers: int = COMPETITOR_X_MAX_FOLLOWERS,
) -> list[str]:
    """Search X for high-engagement AI posts, return top non-celebrity account handles."""
    print("[SCOUT] Discovering top X AI accounts...")
    try:
        items = run_actor(
            "apify/twitter-scraper",
            {
                "searchTerms": COMPETITOR_X_SEARCH_KEYWORDS,
                "maxItems": 200,
                "sort": "Latest",
            },
        )
    except ApifyError as e:
        print(f"[SCOUT] X discovery failed: {e}")
        return []

    # Aggregate engagement per unique author
    engagement: dict[str, int] = {}
    followers: dict[str, int] = {}
    for item in items:
        username = item.get("author_username") or item.get("username") or ""
        if not username:
            continue
        follower_count = item.get("author_followers") or item.get("followers_count") or 0
        if follower_count > max_followers:
            continue
        score = (item.get("like_count") or 0) + (item.get("retweet_count") or 0)
        if username not in engagement or score > engagement[username]:
            engagement[username] = engagement.get(username, 0) + score
            followers[username] = follower_count

    ranked = sorted(engagement.keys(), key=lambda u: engagement[u], reverse=True)
    result = ranked[:top_n]
    print(f"[SCOUT] Discovered X accounts: {result}")
    return result
