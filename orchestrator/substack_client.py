"""Substack internal API client — weekly metrics snapshot."""
import time
import httpx
from datetime import datetime, timezone


class SubstackClient:
    def __init__(self, subdomain: str, sid: str):
        self.subdomain = subdomain
        self.sid = sid
        self.base_url = f"https://{subdomain}.substack.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Origin": "https://substack.com",
            "Referer": "https://substack.com/",
        }

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        url = f"{self.base_url}{path}"
        resp = httpx.get(
            url,
            headers=self.headers,
            cookies={"substack.sid": self.sid},
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        time.sleep(0.5)
        return resp.json()

    def fetch_snapshot(self) -> dict:
        """Fetch weekly snapshot: subscribers, open_rate, growth_sources, threads_funnel."""
        if not self.sid:
            raise ValueError("SUBSTACK_SID not configured")

        summary = self._get("/api/v1/publish-dashboard/summary")
        growth = self._get("/api/v1/publication/stats/growth/sources")

        # Parse growth sources — extract Traffic and Subscribers per source
        growth_sources = []
        threads_traffic = 0
        threads_subs = 0
        for m in growth.get("sourceMetrics", []):
            metrics_by_name = {
                metric["name"]: metric.get("total", 0)
                for metric in m.get("metrics", [])
            }
            traffic = metrics_by_name.get("Traffic", 0)
            new_subscribers = metrics_by_name.get("Subscribers", 0)
            source_name = m["source"]
            growth_sources.append({
                "source": source_name,
                "traffic": traffic,
                "new_subscribers": new_subscribers,
            })
            if source_name == "threads.net":
                threads_traffic = traffic
                threads_subs = new_subscribers

        subscribers = summary.get("totalEmail", 0) + summary.get("appSubscribers", 0)
        total_email = summary.get("totalEmail", 0)
        open_rate_raw = summary.get("openRate", 0)
        # Substack API returns open rate already as percentage (e.g. 25.9 = 25.9%)
        open_rate = round(float(open_rate_raw), 1) if open_rate_raw else 0.0

        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "subscribers": subscribers,
            "total_email": total_email,
            "open_rate": open_rate,
            "growth_sources": growth_sources,
            "threads_funnel": {
                "traffic": threads_traffic,
                "new_subscribers": threads_subs,
                "conversion_rate": round(threads_subs / threads_traffic * 100, 1) if threads_traffic > 0 else 0.0,
            },
        }

    def fetch_latest_post(self) -> dict | None:
        """Fetch the most recently published newsletter post."""
        posts = self._get("/api/v1/archive", params={"sort": "new", "limit": 1})
        if posts:
            return {
                "title": posts[0]["title"],
                "url": posts[0]["canonical_url"],
                "date": posts[0]["post_date"],
            }
        return None
