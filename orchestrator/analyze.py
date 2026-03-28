import anthropic
from orchestrator.config import (
    ANTHROPIC_API_KEY,
    SCORE_WEIGHT_VIEWS,
    SCORE_WEIGHT_LIKES,
    SCORE_WEIGHT_REPLIES,
    DATA_DIR,
    PROMPTS_DIR,
)
from orchestrator.utils import read_json, write_json


def score_posts(posts: list[dict]) -> list[dict]:
    if not posts:
        return []

    views = [p.get("views", 0) for p in posts]
    likes = [p.get("likes", 0) for p in posts]
    replies = [p.get("replies", 0) for p in posts]

    max_views = max(views) if max(views) > 0 else 1
    max_likes = max(likes) if max(likes) > 0 else 1
    max_replies = max(replies) if max(replies) > 0 else 1

    for p in posts:
        norm_v = p.get("views", 0) / max_views
        norm_l = p.get("likes", 0) / max_likes
        norm_r = p.get("replies", 0) / max_replies
        p["score"] = round(
            norm_v * SCORE_WEIGHT_VIEWS
            + norm_l * SCORE_WEIGHT_LIKES
            + norm_r * SCORE_WEIGHT_REPLIES,
            4,
        )

    posts.sort(key=lambda x: x["score"], reverse=True)
    return posts


def analyze(posts: list[dict]) -> dict:
    scored = score_posts(posts)

    experiments = read_json(DATA_DIR / "experiments.json")
    round_number = len(experiments) + 1

    resource_path = PROMPTS_DIR / "resource.md"
    resource_text = resource_path.read_text(encoding="utf-8") if resource_path.exists() else ""

    post_summary = "\n".join(
        f"- [{p.get('dimensions', {}).get('content_type', '?')}] "
        f"score={p['score']} views={p.get('views',0)} likes={p.get('likes',0)} "
        f"replies={p.get('replies',0)} | hook={p.get('dimensions', {}).get('hook_style', '?')} "
        f"| text: {p.get('text', '')[:100]}"
        for p in scored
    )

    prompt = f"""你是一個 Threads 貼文優化分析師。以下是本輪發佈的貼文表現數據：

{post_summary}

目前累積學習：
{resource_text}

請分析：
1. 哪些維度（內容類型、hook 風格、格式、語氣、素材來源）跟表現正相關？
2. Top performer 為什麼表現好？Bottom performer 為什麼表現差？
3. 提取 2-3 條 actionable learnings，格式為：
   - 規則：[具體描述]
   - 依據：[本輪數據]
   - 信心度：高/中/低

4. 更新假設狀態（如有）

用繁體中文回答。"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    ai_text = response.content[0].text

    # The full analysis is the learnings — no keyword gating needed
    learnings = ai_text

    result = {
        "scored_posts": scored,
        "analysis": ai_text,
        "learnings": learnings,
        "round_number": round_number,
    }

    experiments.append({
        "round_number": round_number,
        "harvested_at": _now_iso(),
        "results": [
            {"media_id": p["media_id"], "score": p["score"], "views": p.get("views", 0),
             "likes": p.get("likes", 0), "replies": p.get("replies", 0)}
            for p in scored
        ],
        "analysis": ai_text,
        "learnings": learnings,
    })
    write_json(DATA_DIR / "experiments.json", experiments)

    _update_swipe_file(scored)

    return result


SWIPE_MIN_LIKES = 2  # minimum likes to qualify for swipe file


def _update_swipe_file(scored: list[dict]) -> None:
    """Auto-add top performer to swipe_file.md if it has real engagement."""
    if not scored:
        return

    top = scored[0]
    text = top.get("text", "").strip()
    likes = top.get("likes", 0)

    if not text or likes < SWIPE_MIN_LIKES:
        return

    swipe_path = PROMPTS_DIR / "swipe_file.md"
    current = swipe_path.read_text(encoding="utf-8") if swipe_path.exists() else ""

    # Skip if this post is already in the swipe file
    if text[:60] in current:
        return

    content_type = top.get("dimensions", {}).get("content_type", "未分類")
    views = top.get("views", 0)
    replies = top.get("replies", 0)
    score = top.get("score", 0)
    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry = (
        f"\n\n## 自動收錄（{date_str}）— {content_type}\n"
        f"表現：score={score} views={views} likes={likes} replies={replies}\n\n"
        f"「{text}」\n"
    )

    swipe_path.write_text(current + entry, encoding="utf-8")
    print(f"[ANALYZE] Top performer added to swipe_file.md (likes={likes}, score={score})")


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
