import pytest
from unittest.mock import patch, MagicMock
from orchestrator.substack_client import SubstackClient


def test_fetch_snapshot_structure():
    """fetch_snapshot returns dict with required keys."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_summary = {
        "subscribers": 27,
        "totalEmail": 23,
        "openRate": 0.357,
    }
    mock_summary_v2 = {"subscribers": 27}
    mock_growth = {
        "sourceMetrics": [
            {"source": "substack", "category": "Traffic", "value": 12},
            {"source": "direct", "category": "Traffic", "value": 8},
        ]
    }

    with patch.object(client, "_get", side_effect=[mock_summary, mock_summary_v2, mock_growth]):
        snapshot = client.fetch_snapshot()

    assert snapshot["subscribers"] == 27
    assert snapshot["total_email"] == 23
    assert abs(snapshot["open_rate"] - 35.7) < 0.1
    assert isinstance(snapshot["growth_sources"], list)
    assert "date" in snapshot


def test_fetch_snapshot_missing_sid():
    """fetch_snapshot raises ValueError when sid is empty."""
    client = SubstackClient(subdomain="hualeee", sid="")
    with pytest.raises(ValueError, match="SUBSTACK_SID"):
        client.fetch_snapshot()


def test_growth_sources_filtered():
    """Only Traffic category sources are included."""
    client = SubstackClient(subdomain="hualeee", sid="fake-sid")
    mock_growth = {
        "sourceMetrics": [
            {"source": "substack", "category": "Traffic", "value": 12},
            {"source": "direct", "category": "Revenue", "value": 0},
            {"source": "email", "category": "Traffic", "value": 5},
        ]
    }
    with patch.object(client, "_get", side_effect=[{}, {}, mock_growth]):
        snapshot = client.fetch_snapshot()

    sources = {s["source"]: s["value"] for s in snapshot["growth_sources"]}
    assert "substack" in sources
    assert "email" in sources
    assert "direct" not in sources  # Revenue category excluded
