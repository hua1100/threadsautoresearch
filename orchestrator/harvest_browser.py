# orchestrator/harvest_browser.py
"""
Harvest metrics from Threads via Chrome DevTools MCP.
In GitHub Actions, this will be skipped (no browser).
"""


def harvest_browser(post_ids: list[str]) -> dict[str, dict]:
    return {}
