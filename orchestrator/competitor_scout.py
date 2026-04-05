from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import anthropic
from orchestrator.config import (
    APIFY_API_TOKEN,
    ANTHROPIC_API_KEY,
    COMPETITOR_THREADS_ACCOUNTS,
    COMPETITOR_X_SEARCH_KEYWORDS,
    COMPETITOR_POSTS_PER_ACCOUNT,
    COMPETITOR_X_TOP_N,
    COMPETITOR_X_MAX_FOLLOWERS,
    DATA_DIR,
    PROMPTS_DIR,
)
from orchestrator.apify_client import run_actor, ApifyError
from orchestrator.notify import send_notification


def discover_x_accounts(
    top_n: int = COMPETITOR_X_TOP_N,
    max_followers: int = COMPETITOR_X_MAX_FOLLOWERS,
) -> list[str]:
    """Search X for high-engagement AI posts, return top non-celebrity account handles."""
    print("[SCOUT] Discovering top X AI accounts...")
    try:
        items = run_actor(
            "apify/twitter-scraper",
            {
                "searchTerms": COMPETITOR_X_SEARCH_KEYWORDS,
                "maxItems": 200,
                "sort": "Latest",
            },
        )
    except ApifyError as e:
        print(f"[SCOUT] X discovery failed: {e}")
        return []

    # Aggregate engagement per unique author
    engagement: dict[str, int] = {}
    followers: dict[str, int] = {}
    for item in items:
        username = item.get("author_username") or item.get("username") or ""
        if not username:
            continue
        follower_count = item.get("author_followers") or item.get("followers_count") or 0
        if follower_count > max_followers:
            continue
        score = (item.get("like_count") or 0) + (item.get("retweet_count") or 0)
        engagement[username] = engagement.get(username, 0) + score
        followers[username] = follower_count

    ranked = sorted(engagement.keys(), key=lambda u: engagement[u], reverse=True)
    result = ranked[:top_n]
    print(f"[SCOUT] Discovered X accounts: {result}")
    return result


def scrape_accounts(
    accounts: list[str],
    platform: str,  # "threads" or "x"
    posts_per_account: int = COMPETITOR_POSTS_PER_ACCOUNT,
) -> dict[str, list[dict]]:
    """Scrape posts from a list of accounts. Returns {username: [posts]}."""
    if platform == "threads":
        actor_id = "apify/threads-scraper"
    else:
        actor_id = "apify/twitter-scraper"

    results: dict[str, list[dict]] = {}
    for account in accounts:
        print(f"[SCOUT] Scraping {platform}/@{account}...")
        try:
            if platform == "threads":
                raw = run_actor(
                    actor_id,
                    {"usernames": [account], "resultsLimit": posts_per_account},
                )
            else:
                raw = run_actor(
                    actor_id,
                    {"handles": [account], "maxItems": posts_per_account},
                )
        except ApifyError as e:
            print(f"[SCOUT] Skipping @{account}: {e}")
            continue

        # Normalise text field (Threads uses "text", X uses "full_text")
        posts = []
        for item in raw:
            text = item.get("text") or item.get("full_text") or ""
            if text:
                posts.append({"text": text, "raw": item})
        results[account] = posts
        print(f"[SCOUT]   {len(posts)} posts collected")

    return results


def analyze_competitors(scraped: dict[str, list[dict]]) -> str:
    """Send scraped posts to Claude for format strategy analysis."""
    if not scraped:
        return "（無競品資料可分析）"

    # Build per-account text sample (max 30 posts each to stay within token limit)
    sections = []
    for account, posts in scraped.items():
        sample = posts[:30]
        texts = "\n---\n".join(p["text"] for p in sample)
        sections.append(f"### @{account}（{len(sample)} 篇）\n{texts}")

    all_posts_text = "\n\n".join(sections)

    prompt = f"""你是一個社群媒體格式策略分析師。以下是多個高表現 AI 內容帳號的近期貼文：

{all_posts_text}

請分析這些帳號的**發文格式與結構**，涵蓋：

1. **長度習慣**：平均字數區間，短文（<100字）vs 長文（>200字）比例
2. **換行/段落習慣**：單句換行、段落式、條列式各佔多少比例
3. **Emoji 使用**：使用頻率（每篇平均幾個）、位置（開頭/結尾/穿插）、常見類型
4. **Hook 句型分類**：提問型 / 數字型 / 預言型 / 故事型 / 衝突型，各帳號的偏好
5. **內容類型分佈**：工具介紹 / 教學步驟 / 趨勢新聞 / 觀點辯論
6. **CTA 模式**：有無 CTA、放哪裡、常見句式

最後請歸納 3-5 條「跨帳號共同格式規則」，格式為：
- 規則：[具體描述]
- 依據：[從哪些帳號觀察到]
- 建議應用：[如何套用到自己的貼文]

用繁體中文回答。"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def save_report(
    report_text: str,
    scraped: dict[str, list[dict]],
    report_path: Path | None = None,
    raw_path: Path | None = None,
) -> None:
    """Write competitor_report.md and competitor_raw.json."""
    if report_path is None:
        report_path = DATA_DIR / "competitor_report.md"
    if raw_path is None:
        raw_path = DATA_DIR / "competitor_raw.json"

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md = f"# 競品格式分析報告\n\n生成時間：{date_str}\n\n{report_text}\n"
    report_path.write_text(md, encoding="utf-8")
    print(f"[SCOUT] Report saved to {report_path}")

    raw_serializable = {
        account: [p["text"] for p in posts]
        for account, posts in scraped.items()
    }
    raw_path.write_text(
        json.dumps(raw_serializable, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[SCOUT] Raw data saved to {raw_path}")


def patch_strategy(report_text: str, strategy_path: Path | None = None) -> None:
    """Append competitor format observations to strategy.md."""
    if strategy_path is None:
        strategy_path = PROMPTS_DIR / "strategy.md"

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    section = f"\n\n## 競品格式觀察（{date_str}）\n\n{report_text}\n"

    current = strategy_path.read_text(encoding="utf-8") if strategy_path.exists() else ""
    strategy_path.write_text(current + section, encoding="utf-8")
    print(f"[SCOUT] strategy.md updated with competitor observations")


def run() -> None:
    """Main entry point. Run competitor scout end-to-end."""
    print("[SCOUT] === Competitor Scout Start ===")

    # 1. X account discovery
    x_accounts = discover_x_accounts()

    # 2. Scrape Threads seed accounts
    threads_scraped = scrape_accounts(COMPETITOR_THREADS_ACCOUNTS, platform="threads")

    # 3. Scrape discovered X accounts
    x_scraped = scrape_accounts(x_accounts, platform="x") if x_accounts else {}

    all_scraped = {**threads_scraped, **x_scraped}

    if not all_scraped:
        print("[SCOUT] No posts collected. Exiting.")
        send_notification("⚠️ Competitor Scout：無法抓取任何帳號資料")
        return

    total_posts = sum(len(v) for v in all_scraped.values())
    print(f"[SCOUT] Total posts collected: {total_posts} from {len(all_scraped)} accounts")

    if total_posts == 0:
        print("[SCOUT] All accounts returned zero usable posts. Exiting.")
        send_notification("⚠️ Competitor Scout：帳號已爬取但無有效貼文內容")
        return

    # 4. Analyze
    print("[SCOUT] Analyzing with Claude...")
    report_text = analyze_competitors(all_scraped)

    # 5. Save outputs
    save_report(report_text, all_scraped)

    # 6. Show report preview
    print("\n" + "=" * 60)
    print(report_text[:1000])
    print("=" * 60)

    # 7. CLI confirmation gate
    answer = input("\n是否將競品格式觀察更新到 prompts/strategy.md？[y/N] ").strip().lower()
    if answer == "y":
        patch_strategy(report_text)
        print("[SCOUT] strategy.md updated.")
    else:
        print("[SCOUT] strategy.md unchanged.")

    # 8. Telegram notification
    account_list = ", ".join(f"@{a}" for a in all_scraped.keys())
    send_notification(
        f"📊 *競品分析完成*\n"
        f"帳號：{account_list}\n"
        f"貼文總數：{total_posts}\n"
        f"報告：data/competitor_report.md"
    )

    print("[SCOUT] === Done ===")


if __name__ == "__main__":
    run()
