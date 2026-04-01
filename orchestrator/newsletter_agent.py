"""Newsletter Agent (data-only): 收集數據並輸出，由 Claude Code agent 撰寫草稿"""
import json
from datetime import datetime, timezone
from orchestrator.config import PROMPTS_DIR, DRAFTS_DIR, DATA_DIR
from orchestrator.utils import load_recent_experiments, read_json


def run() -> None:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1. Load strategy
    strategy = ""
    strategy_path = PROMPTS_DIR / "strategy.md"
    if strategy_path.exists():
        strategy = strategy_path.read_text(encoding="utf-8")

    # 2. Load swipe file
    swipe = ""
    swipe_path = PROMPTS_DIR / "swipe_file.md"
    if swipe_path.exists():
        swipe = swipe_path.read_text(encoding="utf-8")

    # 3. Load top posts
    experiments = load_recent_experiments(days=7)
    all_posts = read_json(DATA_DIR / "posts.json")
    posts_map = {}
    if isinstance(all_posts, list):
        posts_map = {p.get("media_id"): p for p in all_posts}

    all_results = []
    for exp in experiments:
        for r in exp.get("results", []):
            post = posts_map.get(r.get("media_id"), {})
            r["text"] = post.get("text", "")
            r["dimensions"] = post.get("dimensions", {})
            all_results.append(r)

    top_posts = sorted(all_results, key=lambda x: x.get("score", 0), reverse=True)[:5]

    # 4. Load Substack funnel data
    newsletter_status = read_json(DATA_DIR / "newsletter_status.json")
    topic = ""
    if isinstance(newsletter_status, dict):
        topic = newsletter_status.get("topic", "")

    metrics_history = read_json(DATA_DIR / "substack_metrics.json")
    latest_metrics = None
    if isinstance(metrics_history, list) and metrics_history:
        latest_metrics = metrics_history[-1]

    # 5. Output data for agent
    print(f"\n{'='*60}")
    print(f"NEWSLETTER DATA ({date_str})")
    print(f"{'='*60}")

    if topic:
        print(f"\n## 本週電子報主題\n{topic}")

    print(f"\n## 本週策略\n{strategy}")

    print(f"\n## 本週 Top 5 貼文")
    for i, p in enumerate(top_posts, 1):
        dims = p.get("dimensions", {})
        print(f"\n### #{i} (score={p.get('score', 0):.4f}, views={p.get('views', 0)}, "
              f"likes={p.get('likes', 0)}, replies={p.get('replies', 0)})")
        print(f"類型: {dims.get('content_type', '?')} | 策略: {dims.get('strategy', '?')}")
        print(f"內容:\n{p.get('text', '')}")

    if swipe:
        print(f"\n## 高表現貼文範例庫\n{swipe[-1500:]}")

    if latest_metrics:
        print(f"\n## Substack 漏斗摘要（{latest_metrics.get('date', '')}）")
        print(f"  訂閱數：{latest_metrics.get('subscribers', 0)}")
        print(f"  Open Rate：{latest_metrics.get('open_rate', 0)}%")
        funnel = latest_metrics.get("threads_funnel")
        if funnel and funnel.get("traffic", 0) > 0:
            print(f"  Threads 導流：{funnel['traffic']} 次 → {funnel['new_subscribers']} 訂閱（轉換率 {funnel['conversion_rate']}%）")

    print(f"\n{'='*60}")
    print(f"請根據以上數據，撰寫電子報草稿並存到 drafts/newsletter_{date_str}.md")
    print(f"{'='*60}")


def send_telegram(message: str) -> None:
    """Utility for agent to send newsletter via Telegram."""
    from orchestrator.notify import send_notification
    MAX_LEN = 4000
    if len(message) <= MAX_LEN:
        send_notification(message)
    else:
        for i in range(0, len(message), MAX_LEN):
            send_notification(message[i:i + MAX_LEN])


if __name__ == "__main__":
    run()
