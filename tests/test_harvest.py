from unittest.mock import patch
from orchestrator.harvest import harvest, merge_metrics


def test_merge_metrics_prefers_browser_views():
    browser = {"views": 150, "likes": 10, "replies": 2, "reposts": 1}
    api = {"views": 0, "likes": 12, "replies": 2, "reposts": 3}
    merged = merge_metrics(browser, api)
    assert merged["views"] == 150
    assert merged["likes"] == 12
    assert merged["reposts"] == 3


def test_merge_metrics_falls_back_to_api():
    browser = {}
    api = {"views": 0, "likes": 5, "replies": 1, "reposts": 0}
    merged = merge_metrics(browser, api)
    assert merged["likes"] == 5


def test_harvest_returns_list_of_post_metrics():
    fake_posts = [
        {"media_id": "post_1", "text": "Hello", "published_at": "2026-03-27T09:00:00"},
        {"media_id": "post_2", "text": "World", "published_at": "2026-03-27T11:00:00"},
    ]
    fake_browser = {"post_1": {"views": 100, "likes": 5, "replies": 1, "reposts": 0}}
    fake_api = {"post_2": {"views": 0, "likes": 3, "replies": 0, "reposts": 1}}

    with patch("orchestrator.harvest.read_json", return_value=fake_posts):
        with patch("orchestrator.harvest.harvest_browser", return_value=fake_browser):
            with patch("orchestrator.harvest.harvest_api", return_value=fake_api):
                results = harvest()

    assert len(results) == 2
    assert results[0]["media_id"] == "post_1"
    assert results[0]["views"] == 100
