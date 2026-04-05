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
        engagement[username] = engagement.get(username, 0) + score
        followers[username] = follower_count

    ranked = sorted(engagement.keys(), key=lambda u: engagement[u], reverse=True)
    result = ranked[:top_n]
    print(f"[SCOUT] Discovered X accounts: {result}")
    return result


def scrape_accounts(
    accounts: list[str],
    platform: str,  # "threads" or "x"
    posts_per_account: int = COMPETITOR_POSTS_PER_ACCOUNT,
) -> dict[str, list[dict]]:
    """Scrape posts from a list of accounts. Returns {username: [posts]}."""
    if platform == "threads":
        actor_id = "apify/threads-scraper"
    else:
        actor_id = "apify/twitter-scraper"

    results: dict[str, list[dict]] = {}
    for account in accounts:
        print(f"[SCOUT] Scraping {platform}/@{account}...")
        try:
            if platform == "threads":
                raw = run_actor(
                    actor_id,
                    {"usernames": [account], "resultsLimit": posts_per_account},
                )
            else:
                raw = run_actor(
                    actor_id,
                    {"handles": [account], "maxItems": posts_per_account},
                )
        except ApifyError as e:
            print(f"[SCOUT] Skipping @{account}: {e}")
            continue

        # Normalise text field (Threads uses "text", X uses "full_text")
        posts = []
        for item in raw:
            text = item.get("text") or item.get("full_text") or ""
            if text:
                posts.append({"text": text, "raw": item})
        results[account] = posts
        print(f"[SCOUT]   {len(posts)} posts collected")

    return results
