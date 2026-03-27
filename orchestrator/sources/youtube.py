import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timedelta, timezone

# Channel name -> YouTube channel ID mapping
# RSS feed: https://www.youtube.com/feeds/videos.xml?channel_id=UC...
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

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "media": "http://search.yahoo.com/mrss/"}


def fetch_recent_videos(channel_id: str, hours: int = 12) -> list[dict]:
    if not channel_id:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    url = RSS_URL.format(channel_id=channel_id)

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"[SOURCE] YouTube RSS error for {channel_id}: {resp.status_code}")
            return []
    except Exception as e:
        print(f"[SOURCE] YouTube RSS fetch error: {e}")
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        print(f"[SOURCE] YouTube RSS parse error: {e}")
        return []

    channel_name = ""
    title_el = root.find("atom:title", NS)
    if title_el is not None:
        channel_name = title_el.text or ""

    videos = []
    for entry in root.findall("atom:entry", NS):
        published_el = entry.find("atom:published", NS)
        if published_el is None:
            continue

        published_str = published_el.text or ""
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if published < cutoff:
            continue

        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        media_group = entry.find("media:group", NS)
        description = ""
        if media_group is not None:
            desc_el = media_group.find("media:description", NS)
            if desc_el is not None:
                description = desc_el.text or ""

        video_id = video_id_el.text if video_id_el is not None else ""
        title = title_el.text if title_el is not None else ""

        videos.append({
            "video_id": video_id,
            "title": title,
            "channel": channel_name,
            "published_at": published_str,
            "description": description,
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })

    return videos


def fetch_all_channels(hours: int = 12) -> list[dict]:
    all_videos = []
    for name, channel_id in CHANNEL_IDS.items():
        if channel_id:
            videos = fetch_recent_videos(channel_id, hours)
            all_videos.extend(videos)
    return all_videos
