from unittest.mock import patch, MagicMock
from orchestrator.analyze import score_posts, analyze


def test_score_posts_weighted():
    posts = [
        {"media_id": "1", "views": 100, "likes": 10, "replies": 5, "reposts": 0},
        {"media_id": "2", "views": 50, "likes": 20, "replies": 2, "reposts": 0},
        {"media_id": "3", "views": 200, "likes": 5, "replies": 1, "reposts": 0},
    ]
    scored = score_posts(posts)
    assert scored[0]["media_id"] == "3"
    assert "score" in scored[0]


def test_score_posts_handles_all_zeros():
    posts = [
        {"media_id": "1", "views": 0, "likes": 0, "replies": 0, "reposts": 0},
    ]
    scored = score_posts(posts)
    assert scored[0]["score"] == 0.0


def test_analyze_returns_analysis_dict():
    posts = [
        {"media_id": "1", "views": 100, "likes": 10, "replies": 5, "reposts": 0,
         "text": "AI tool", "hypothesis": "test tools", "dimensions": {"content_type": "工具分享"}},
        {"media_id": "2", "views": 50, "likes": 2, "replies": 0, "reposts": 0,
         "text": "Dev log", "hypothesis": "test dev", "dimensions": {"content_type": "開發心得"}},
    ]

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="## 分析\n工具分享表現較好\n## 學習\n- 工具類觸及高")]

    with patch("orchestrator.analyze.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        result = analyze(posts)

    assert "scored_posts" in result
    assert "analysis" in result
    assert "learnings" in result
    assert "round_number" in result
