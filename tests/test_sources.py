from pathlib import Path
from unittest.mock import patch, MagicMock
from orchestrator.sources.youtube import fetch_recent_videos, CHANNEL_IDS
from orchestrator.sources.github import fetch_recent_activity
from orchestrator.sources.x_curated import fetch_x_content


def test_fetch_recent_videos_returns_list():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {
                "id": {"videoId": "abc123"},
                "snippet": {
                    "title": "AI Tools 2026",
                    "channelTitle": "every.to",
                    "publishedAt": "2026-03-27T10:00:00Z",
                    "description": "A great video about AI tools",
                }
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("orchestrator.sources.youtube.requests.get", return_value=mock_resp):
        videos = fetch_recent_videos("UC_channel_id", hours=12)

    assert len(videos) == 1
    assert videos[0]["video_id"] == "abc123"
    assert videos[0]["title"] == "AI Tools 2026"


def test_fetch_recent_activity_returns_list():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = """abc1234|feat: add new feature|2026-03-27
def5678|fix: resolve bug|2026-03-26"""

    with patch("orchestrator.sources.github.subprocess.run", return_value=mock_result):
        commits = fetch_recent_activity("/tmp/fake-repo")

    assert len(commits) == 2
    assert commits[0]["hash"] == "abc1234"
    assert commits[0]["message"] == "feat: add new feature"


def test_fetch_x_content_merges_telegram_and_file(tmp_path):
    curated_file = tmp_path / "x_curated.md"
    curated_file.write_text("## 策展內容\n\n好文1：AI agents 的未來\n\n好文2：LLM 成本下降趨勢")

    telegram_messages = [
        "https://x.com/karpathy/status/123 這個觀點很好",
        "剛看到一篇關於 AI coding 的長文",
    ]

    results = fetch_x_content(telegram_messages, str(curated_file))
    assert len(results) == 2
    assert results[0]["source"] == "telegram"
    assert "karpathy" in results[0]["text"]


def test_fetch_x_content_appends_to_curated_file(tmp_path):
    curated_file = tmp_path / "x_curated.md"
    curated_file.write_text("## 策展內容\n")

    telegram_messages = ["新的好內容"]
    fetch_x_content(telegram_messages, str(curated_file))

    updated = curated_file.read_text()
    assert "新的好內容" in updated
