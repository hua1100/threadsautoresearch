"""Newsletter Agent: 生成 Substack 草稿並 email 給作者"""
import json
import subprocess
import anthropic
from datetime import datetime, timezone
from orchestrator.config import (
    ANTHROPIC_API_KEY, PROMPTS_DIR, DRAFTS_DIR, NEWSLETTER_EMAIL, DATA_DIR
)
from orchestrator.utils import load_recent_experiments, read_json, write_json


def run() -> None:
    strategy = ""
    strategy_path = PROMPTS_DIR / "strategy.md"
    if strategy_path.exists():
        strategy = strategy_path.read_text(encoding="utf-8")

    swipe = ""
    swipe_path = PROMPTS_DIR / "swipe_file.md"
    if swipe_path.exists():
        swipe = swipe_path.read_text(encoding="utf-8")

    experiments = load_recent_experiments(days=7)
    top_posts = sorted(
        [post for exp in experiments for post in exp.get("results", [])],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )[:5]
    top_summary = json.dumps(top_posts, ensure_ascii=False, indent=2)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Read newsletter topic from status file
    newsletter_status = read_json(DATA_DIR / "newsletter_status.json")
    topic = ""
    if isinstance(newsletter_status, dict):
        topic = newsletter_status.get("topic", "")

    topic_instruction = (
        f"本週電子報主題是「{topic}」，以此為核心，參考相關的高表現貼文寫深度版本。"
        if topic
        else "根據本週最佳表現貼文寫電子報。"
    )

    prompt = f"""你是一個 AI 電子報作者，為 Substack 電子報（hualeee.substack.com）撰寫本週內容。

## 本週 Threads 策略
{strategy}

## 高表現貼文範例庫
{swipe}

## 本週最佳表現貼文數據
{top_summary}

{topic_instruction}

請撰寫一篇完整的電子報草稿：
- 繁體中文
- 格式：標題、引言、正文（3-5 個小節）、結語
- 字數：800-1200 字

只輸出電子報正文，不要額外說明。"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    draft = response.content[0].text.strip()

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = DRAFTS_DIR / f"newsletter_{date_str}.md"
    draft_path.write_text(draft, encoding="utf-8")
    print(f"[NEWSLETTER] Draft saved to {draft_path}")

    # Update newsletter_status to draft
    if isinstance(newsletter_status, dict):
        newsletter_status["status"] = "draft"
        write_json(DATA_DIR / "newsletter_status.json", newsletter_status)

    # Build funnel summary from latest Substack snapshot
    funnel_section = ""
    metrics_path = DATA_DIR / "substack_metrics.json"
    metrics_history = read_json(metrics_path)
    if isinstance(metrics_history, list) and metrics_history:
        latest = metrics_history[-1]
        prev = metrics_history[-2] if len(metrics_history) >= 2 else None
        delta = (
            latest.get("subscribers") - prev.get("subscribers")
            if prev
            and latest.get("subscribers") is not None
            and prev.get("subscribers") is not None
            else None
        )
        if delta is None:
            delta_str = "首次記錄"
        elif delta > 0:
            delta_str = f"+{delta}"
        elif delta < 0:
            delta_str = str(delta)
        else:
            delta_str = "±0"
        sources_str = ", ".join(
            f"{s['source']}: {s.get('traffic', s.get('value', 0))}"
            for s in latest.get("growth_sources", [])
        ) or "無資料"

        # Add threads funnel to summary
        threads_funnel_str = ""
        funnel = latest.get("threads_funnel")
        if funnel and funnel.get("traffic", 0) > 0:
            threads_funnel_str = (
                f"\n- Threads 導流：{funnel['traffic']} 次 → {funnel['new_subscribers']} 訂閱"
                f"（轉換率 {funnel['conversion_rate']}%）"
            )

        funnel_section = (
            f"\n\n## Substack 漏斗摘要（{latest.get('date', '')}）\n"
            f"- 訂閱數：{latest.get('subscribers', 0)}（{delta_str} 本週）\n"
            f"- Open Rate：{latest.get('open_rate', 0)}%\n"
            f"- 流量來源：{sources_str}"
            f"{threads_funnel_str}\n"
        )

    if not NEWSLETTER_EMAIL:
        print("[NEWSLETTER] NEWSLETTER_EMAIL not set, skipping email")
    else:
        subject = f"[電子報草稿] {date_str}"
        body = f"本週 Top 5 貼文數據：\n{top_summary[:500]}{funnel_section}\n\n---草稿---\n\n{draft}"
        result = subprocess.run(
            ["mail", "-s", subject, NEWSLETTER_EMAIL],
            input=body.encode("utf-8"),
            capture_output=True,
        )
        if result.returncode == 0:
            print(f"[NEWSLETTER] Email sent to {NEWSLETTER_EMAIL}")
        else:
            print(f"[NEWSLETTER] Email failed: {result.stderr.decode()}")


if __name__ == "__main__":
    run()
