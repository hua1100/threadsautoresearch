import json
from unittest.mock import patch, MagicMock
from orchestrator.generate import generate


def test_generate_returns_list_of_posts():
    analysis = {
        "scored_posts": [
            {"media_id": "1", "score": 0.8, "text": "AI tool post",
             "dimensions": {"content_type": "工具分享"}},
        ],
        "learnings": "工具類表現好",
        "round_number": 1,
    }

    sources = {
        "youtube": [{"title": "New AI Tool", "channel": "every.to", "url": "https://youtube.com/watch?v=abc"}],
        "github": [{"hash": "abc", "message": "feat: add RAG pipeline", "date": "2026-03-27"}],
        "x": [],
    }

    fake_ai_output = json.dumps([
        {
            "text": "分享一個超好用的 AI 工具",
            "dimensions": {
                "content_type": "工具分享",
                "hook_style": "送資源型",
                "format": "短句",
                "tone": "輕鬆口語",
                "cta": "追蹤我",
                "source": "youtube/every.to"
            },
            "hypothesis": "測試短句送資源型是否提升觸及"
        },
        {
            "text": "最近在做 RAG pipeline 踩了一個坑",
            "dimensions": {
                "content_type": "開發心得",
                "hook_style": "故事型",
                "format": "中篇",
                "tone": "輕鬆口語",
                "cta": "留言互動",
                "source": "github"
            },
            "hypothesis": "測試故事型 hook 的開發心得表現"
        }
    ], ensure_ascii=False)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=fake_ai_output)]

    with patch("orchestrator.generate.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        with patch("orchestrator.generate._read_prompt", return_value="test prompt"):
            posts = generate(analysis, sources)

    assert len(posts) == 2
    assert "text" in posts[0]
    assert "dimensions" in posts[0]
    assert "hypothesis" in posts[0]


def test_generate_returns_empty_on_error():
    analysis = {"scored_posts": [], "learnings": "", "round_number": 1}
    sources = {"youtube": [], "github": [], "x": []}

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json")]

    with patch("orchestrator.generate.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        with patch("orchestrator.generate._read_prompt", return_value="test"):
            posts = generate(analysis, sources)

    assert posts == []
