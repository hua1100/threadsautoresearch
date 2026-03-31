import pytest
from unittest.mock import patch, MagicMock
from orchestrator.substack_client import SubstackClient


def test_fetch_snapshot_structure():
    """fetch_snapshot returns dict with required keys."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_summary = {
        "subscribers": 0,
        "totalEmail": 23,
        "appSubscribers": 4,
        "openRate": 35.7,
    }
    mock_growth = {
        "sourceMetrics": [
            {
                "source": "substack",
                "metrics": [
                    {"name": "Traffic", "total": 12},
                    {"name": "Subscribers", "total": 1},
                ],
                "children": [],
            },
        ]
    }

    with patch.object(client, "_get", side_effect=[mock_summary, mock_growth]):
        snapshot = client.fetch_snapshot()

    assert snapshot["subscribers"] == 27  # totalEmail(23) + appSubscribers(4)
    assert snapshot["total_email"] == 23
    assert abs(snapshot["open_rate"] - 35.7) < 0.1
    assert len(snapshot["growth_sources"]) == 1
    assert snapshot["growth_sources"][0]["source"] == "substack"
    assert snapshot["growth_sources"][0]["traffic"] == 12
    assert snapshot["growth_sources"][0]["new_subscribers"] == 1
    assert "date" in snapshot
    assert "threads_funnel" in snapshot


def test_fetch_snapshot_missing_sid():
    """fetch_snapshot raises ValueError when sid is empty."""
    client = SubstackClient(subdomain="hualeee", sid="")
    with pytest.raises(ValueError, match="SUBSTACK_SID"):
        client.fetch_snapshot()



def test_fetch_snapshot_multidim_growth_sources():
    """growth_sources includes traffic and new_subscribers per source."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_summary = {
        "subscribers": 0,
        "totalEmail": 23,
        "appSubscribers": 4,
        "openRate": 35.7,
    }
    mock_growth = {
        "sourceMetrics": [
            {
                "source": "threads.net",
                "metrics": [
                    {"name": "Traffic", "total": 5},
                    {"name": "Subscribers", "total": 2},
                    {"name": "Revenue", "total": 0},
                ],
                "children": [],
            },
            {
                "source": "direct",
                "metrics": [
                    {"name": "Traffic", "total": 33},
                    {"name": "Subscribers", "total": 3},
                    {"name": "Revenue", "total": 0},
                ],
                "children": [],
            },
        ]
    }

    with patch.object(client, "_get", side_effect=[mock_summary, mock_growth]):
        snapshot = client.fetch_snapshot()

    # growth_sources now has traffic + new_subscribers
    sources = {s["source"]: s for s in snapshot["growth_sources"]}
    assert sources["threads.net"]["traffic"] == 5
    assert sources["threads.net"]["new_subscribers"] == 2
    assert sources["direct"]["traffic"] == 33
    assert sources["direct"]["new_subscribers"] == 3


def test_fetch_snapshot_threads_funnel():
    """threads_funnel extracts threads.net data with conversion rate."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_summary = {"totalEmail": 10, "appSubscribers": 0, "openRate": 0}
    mock_growth = {
        "sourceMetrics": [
            {
                "source": "threads.net",
                "metrics": [
                    {"name": "Traffic", "total": 20},
                    {"name": "Subscribers", "total": 4},
                ],
                "children": [],
            },
        ]
    }

    with patch.object(client, "_get", side_effect=[mock_summary, mock_growth]):
        snapshot = client.fetch_snapshot()

    funnel = snapshot["threads_funnel"]
    assert funnel["traffic"] == 20
    assert funnel["new_subscribers"] == 4
    assert abs(funnel["conversion_rate"] - 20.0) < 0.1  # 4/20 = 20%


def test_fetch_snapshot_threads_funnel_zero_traffic():
    """threads_funnel conversion_rate is 0 when traffic is 0."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_summary = {"totalEmail": 10, "appSubscribers": 0, "openRate": 0}
    mock_growth = {"sourceMetrics": []}

    with patch.object(client, "_get", side_effect=[mock_summary, mock_growth]):
        snapshot = client.fetch_snapshot()

    funnel = snapshot["threads_funnel"]
    assert funnel["traffic"] == 0
    assert funnel["new_subscribers"] == 0
    assert funnel["conversion_rate"] == 0.0
