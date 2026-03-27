import requests
from datetime import datetime, timedelta, timezone
from orchestrator.config import YOUTUBE_API_KEY

# Channel name -> YouTube channel ID mapping
CHANNEL_IDS = {
    "every.to": "UCjIMtrzxYc0lblGhmOgC_CA",
    "Lenny's Podcast": "UC6t1O76G0jYXOAoYCm153dA",
    "How I AI": "UCRYY7IEbkHLH_ScJCu9eWDQ",
    "a16z": "UC9cn0TuPq4dnbTY-CBsm8XA",
    "Greg Isenberg": "UCPjNBjflYl0-HQtUvOx0Ibw",
    "Stephen G. Pope": "UCIg2taLnC9X6LRP1k3kukOA",
    "Y Combinator": "UCcefcZRL2oaA_uBNeo5UOWg",
    "Nick Saraev": "UCbo-KbSjJDG6JWQ_MTZ_rNA",
}

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def fetch_recent_videos(channel_id: str, hours: int = 12) -> list[dict]:
    if not channel_id or not YOUTUBE_API_KEY:
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

    try:
        resp = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"[SOURCE] YouTube API error for {channel_id}: {resp.status_code}")
            return []
    except Exception as e:
        print(f"[SOURCE] YouTube API fetch error: {e}")
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
