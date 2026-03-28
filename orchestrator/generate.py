import json
import anthropic
from pathlib import Path
from orchestrator.config import ANTHROPIC_API_KEY, PROMPTS_DIR


def _read_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _append_learnings(learnings: str, round_number: int) -> None:
    resource_path = PROMPTS_DIR / "resource.md"
    resource_path.parent.mkdir(parents=True, exist_ok=True)
    current = resource_path.read_text(encoding="utf-8") if resource_path.exists() else ""
    # Skip if this round was already appended (prevents duplicates)
    marker = f"### Round {round_number} ("
    if marker in current:
        return
    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_section = f"\n\n### Round {round_number} ({date_str})\n{learnings}\n"
    resource_path.write_text(current + new_section, encoding="utf-8")


def generate(analysis: dict, sources: dict) -> list[dict]:
    program = _read_prompt("program.md")
    swipe = _read_prompt("swipe_file.md")
    resource = _read_prompt("resource.md")

    round_number = analysis.get("round_number", 1)
    learnings = analysis.get("learnings", "")

    if learnings:
        _append_learnings(learnings, round_number)
        resource = _read_prompt("resource.md")

    yt_summary = "\n".join(
        f"- [{v['channel']}] {v['title']} ({v['url']})"
        for v in sources.get("youtube", [])
    ) or "（本輪無新影片）"

    gh_summary = "\n".join(
        f"- {c['message']} ({c['hash']})"
        for c in sources.get("github", [])
    ) or "（本輪無新 commit）"

    x_new = "\n".join(
        f"- {p.get('text', '')}"
        for p in sources.get("x", [])
    ) or "（本輪無新轉發）"

    from orchestrator.sources.x_curated import read_curated_file
    x_curated = read_curated_file()
    x_summary = f"### 本輪新轉發\n{x_new}\n\n### 累積策展內容\n{x_curated}" if x_curated else x_new

    perf_summary = "\n".join(
        f"- score={p['score']} [{p.get('dimensions', {}).get('content_type', '?')}] "
        f"{p.get('text', '')[:80]}"
        for p in analysis.get("scored_posts", [])
    ) or "（首次運行，無歷史數據）"

    prompt = f"""{program}

## 高表現範例庫
{swipe}

## 累積學習
{resource}

## 本輪素材

### YouTube 新影片
{yt_summary}

### GitHub 最近活動
{gh_summary}

### X.com 內容
{x_summary}

## 上一輪貼文表現
{perf_summary}

## 上一輪分析
{analysis.get('analysis', '（首次運行）')}

---

請產出 3-5 篇 Threads 貼文。每篇必須是自然流暢的繁體中文，不要有任何格式標記（如 \\n）。300 字以內。

輸出格式為 JSON array：
[
  {{
    "text": "貼文內容（300字以內）",
    "dimensions": {{
      "content_type": "工具分享|開發心得|教學知識點|新聞/趨勢|觀點/辯論",
      "strategy": "使用的策略編號，如 1+7",
      "tone": "專業分析|輕鬆口語|急迫感|教學口吻",
      "cta": "無CTA|留言互動|分享給朋友",
      "source": "素材來源"
    }},
    "hypothesis": "這篇在測試什麼策略"
  }}
]

只輸出 JSON，不要加任何其他文字。"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        posts = json.loads(raw)
        if not isinstance(posts, list):
            return []
        return posts
    except json.JSONDecodeError:
        print(f"[GENERATE] Failed to parse AI output: {raw[:200]}")
        return []
