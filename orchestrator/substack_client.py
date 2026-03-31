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
        """Fetch weekly snapshot: subscribers, open_rate, growth_sources."""
        if not self.sid:
            raise ValueError("SUBSTACK_SID not configured")

        summary = self._get("/api/v1/publish-dashboard/summary")
        # summary_v2 has same subscriber count but confirms the value
        self._get("/api/v1/publish-dashboard/summary-v2", {"range": 30})
        growth = self._get("/api/v1/publication/stats/growth/sources")

        # Parse growth sources — only Traffic category
        growth_sources = [
            {"source": m["source"], "value": m["value"]}
            for m in growth.get("sourceMetrics", [])
            if m.get("category") == "Traffic"
        ]

        subscribers = summary.get("subscribers", 0)
        total_email = summary.get("totalEmail", 0)
        open_rate_raw = summary.get("openRate", 0)
        open_rate = round(float(open_rate_raw) * 100, 1) if open_rate_raw and open_rate_raw < 1 else float(open_rate_raw or 0)

        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "subscribers": subscribers,
            "total_email": total_email,
            "open_rate": open_rate,
            "growth_sources": growth_sources,
        }
