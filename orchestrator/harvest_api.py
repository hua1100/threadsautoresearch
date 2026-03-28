# orchestrator/harvest_api.py
from orchestrator.threads_client import get_post_insights


def harvest_api(post_ids: list[str]) -> dict[str, dict]:
    results = {}
    for media_id in post_ids:
        try:
            insights = get_post_insights(media_id)
            if insights:
                results[media_id] = {
                    "views": insights.get("views", 0),
                    "likes": insights.get("likes", 0),
                    "replies": insights.get("replies", 0),
                    "reposts": insights.get("reposts", 0),
                    "quotes": insights.get("quotes", 0),
                }
        except Exception as e:
            print(f"[HARVEST] API error for {media_id}: {e}")
    return results
