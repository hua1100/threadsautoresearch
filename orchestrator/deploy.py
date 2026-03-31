from datetime import datetime, timezone
from orchestrator import threads_client
from orchestrator.config import DATA_DIR
from orchestrator.utils import read_json, write_json, sanitize_post_text


def schedule_posts(posts: list[dict], start_hour: int = 9, interval_hours: int = 2) -> list[dict]:
    scheduled = []
    for i, post in enumerate(posts):
        hour = start_hour + (i * interval_hours)
        scheduled.append({**post, "scheduled_hour": hour})
    return scheduled


def deploy(posts: list[dict]) -> list[dict]:
    published = []
    posts_db = read_json(DATA_DIR / "posts.json")
    if not isinstance(posts_db, list):
        posts_db = []

    for post in posts:
        text = sanitize_post_text(post["text"])

        if len(text) > 500:
            text = text[:497] + "..."

        try:
            media_id = threads_client.post_text(text)
        except Exception as e:
            print(f"[DEPLOY] Failed to publish: {e}")
            media_id = None

        permalink = None
        if media_id:
            try:
                permalink = threads_client.get_post_permalink(media_id)
            except Exception:
                pass

        record = {
            "media_id": media_id,
            "permalink": permalink,
            "text": text,
            "dimensions": post.get("dimensions", {}),
            "hypothesis": post.get("hypothesis", ""),
            "published_at": datetime.now(timezone.utc).isoformat(),
            "scheduled_hour": post.get("scheduled_hour"),
        }
        published.append(record)
        posts_db.append(record)

    write_json(DATA_DIR / "posts.json", posts_db)
    return published
