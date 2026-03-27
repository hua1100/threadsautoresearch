import requests
from datetime import datetime, timedelta, timezone
from orchestrator.config import YOUTUBE_API_KEY

CHANNEL_IDS = {
    "every.to": "",
    "Lenny's Podcast": "",
    "How I AI": "",
    "a16z": "",
    "Greg Isenberg": "",
    "Stephen G. Pope": "",
    "Y Combinator": "",
    "Nick Saraev": "",
}

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def fetch_recent_videos(channel_id: str, hours: int = 12) -> list[dict]:
    if not channel_id:
        return []

    published_after = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    params = {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "order": "date",
        "publishedAfter": published_after,
        "maxResults": 5,
        "key": YOUTUBE_API_KEY,
    }

    resp = requests.get(YOUTUBE_SEARCH_URL, params=params)
    if resp.status_code != 200:
        print(f"[SOURCE] YouTube API error: {resp.status_code}")
        return []

    items = resp.json().get("items", [])
    return [
        {
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
            "description": item["snippet"].get("description", ""),
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
        }
        for item in items
        if item.get("id", {}).get("videoId")
    ]


def fetch_all_channels(hours: int = 12) -> list[dict]:
    all_videos = []
    for name, channel_id in CHANNEL_IDS.items():
        if channel_id:
            videos = fetch_recent_videos(channel_id, hours)
            all_videos.extend(videos)
    return all_videos
