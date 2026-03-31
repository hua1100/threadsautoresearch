# orchestrator/harvest_browser.py
"""
Harvest metrics from Threads via headless Chromium (Playwright).
Scrapes likes, replies, reposts from embedded JSON on post pages.
Views (impressions) are not available without login.
"""
import json
import re
from orchestrator.threads_client import get_post_permalink


def _extract_metrics_from_page(page) -> dict:
    """Extract metrics from Threads post page embedded JSON."""
    scripts = page.query_selector_all('script[type="application/json"]')
    for script in scripts:
        text = script.text_content() or ""
        if "like_count" not in text:
            continue
        try:
            data = json.loads(text)
            return _parse_barcelona_json(data)
        except (json.JSONDecodeError, Exception):
            continue
    return {}


def _parse_barcelona_json(data: dict) -> dict:
    """Walk the nested Barcelona JSON to find post metrics."""
    text = json.dumps(data)

    likes = _find_first_int(text, r'"like_count"\s*:\s*(\d+)')
    replies = _find_first_int(text, r'"direct_reply_count"\s*:\s*(\d+)')
    reposts = _find_first_int(text, r'"repost_count"\s*:\s*(\d+)')

    return {
        "likes": likes,
        "replies": replies,
        "reposts": reposts,
    }


def _find_first_int(text: str, pattern: str) -> int:
    match = re.search(pattern, text)
    return int(match.group(1)) if match else 0


def _resolve_permalink(post_id: str, permalinks_cache: dict) -> str | None:
    """Get permalink from cache or API."""
    if post_id in permalinks_cache:
        return permalinks_cache[post_id]
    try:
        permalink = get_post_permalink(post_id)
        if permalink:
            # Threads moved to threads.com in April 2025
            permalink = permalink.replace("threads.net", "threads.com")
            permalinks_cache[post_id] = permalink
        return permalink
    except Exception:
        return None


def harvest_browser(post_ids: list[str], permalinks: dict | None = None) -> dict[str, dict]:
    """
    Scrape metrics for a list of Threads posts using headless Chromium.

    Args:
        post_ids: List of media_id strings.
        permalinks: Optional dict of {media_id: permalink_url} from posts.json.

    Returns:
        Dict mapping media_id to {likes, replies, reposts}.
    """
    if not post_ids:
        return {}

    permalinks_cache = dict(permalinks or {})
    results = {}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[HARVEST] playwright not installed, skipping browser harvest")
        return {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            page = context.new_page()

            for post_id in post_ids:
                permalink = _resolve_permalink(post_id, permalinks_cache)
                if not permalink:
                    print(f"[HARVEST] No permalink for {post_id}, skipping")
                    continue

                try:
                    page.goto(permalink, wait_until="networkidle", timeout=30000)
                    metrics = _extract_metrics_from_page(page)
                    if metrics:
                        results[post_id] = metrics
                        print(f"[HARVEST] {post_id}: {metrics}")
                    else:
                        print(f"[HARVEST] {post_id}: no metrics found on page")
                except Exception as e:
                    print(f"[HARVEST] Browser error for {post_id}: {e}")

            browser.close()
    except Exception as e:
        print(f"[HARVEST] Browser launch failed: {e}")

    return results
