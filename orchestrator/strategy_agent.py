"""Strategy Agent: 分析過去 7 天數據，更新 prompts/strategy.md"""
import json
import re
import anthropic
from datetime import datetime, timezone
from orchestrator.config import ANTHROPIC_API_KEY, PROMPTS_DIR, DATA_DIR, SUBSTACK_SID, SUBSTACK_SUBDOMAIN
from orchestrator.substack_client import SubstackClient
from orchestrator.utils import load_recent_experiments, read_json, write_json


def _extract_newsletter_topic(strategy_text: str) -> str:
    """Extract newsletter topic from strategy.md content."""
    match = re.search(r"## 本週電子報主題\s*\n(.+)", strategy_text)
    return match.group(1).strip() if match else ""


def run() -> None:
    experiments = load_recent_experiments(days=7)
    resource = ""
    resource_path = PROMPTS_DIR / "resource.md"
    if resource_path.exists():
        resource = resource_path.read_text(encoding="utf-8")

    # Fetch and store Substack snapshot (skip if not configured)
    substack_snapshot = None
    if SUBSTACK_SID:
        try:
            client = SubstackClient(subdomain=SUBSTACK_SUBDOMAIN, sid=SUBSTACK_SID)
            substack_snapshot = client.fetch_snapshot()
            metrics_path = DATA_DIR / "substack_metrics.json"
            existing = read_json(metrics_path)
            if not isinstance(existing, list):
                existing = []
            existing.append(substack_snapshot)
            write_json(metrics_path, existing)
            print(f"[STRATEGY] Substack snapshot saved: {substack_snapshot['subscribers']} subscribers")
        except Exception as e:
            print(f"[STRATEGY] Substack snapshot failed (skipping): {e}")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    exp_summary = json.dumps(experiments, ensure_ascii=False, indent=2)

    substack_section = ""
    if substack_snapshot:
        sources_str = ", ".join(
            f"{s['source']}: {s.get('traffic', s.get('value', 0))}"
            for s in substack_snapshot.get("growth_sources", [])
        )
        substack_section = (
            f"\n## Substack 電子報現況\n"
            f"- 訂閱數：{substack_snapshot.get('subscribers', 0)}\n"
            f"- Open Rate：{substack_snapshot.get('open_rate', 0)}%\n"
            f"- 流量來源：{sources_str}\n"
        )

        funnel = substack_snapshot.get("threads_funnel")
        if funnel:
            substack_section += (
                f"\n## Threads → 電子報轉換漏斗\n"
                f"- Threads 導流：{funnel['traffic']} 次點擊\n"
                f"- 新增訂閱：{funnel['new_subscribers']}\n"
                f"- 轉換率：{funnel['conversion_rate']}%\n"
            )

    prompt = f"""你是一個 Threads 內容策略師。分析過去 7 天的貼文數據，制定本週流量策略。

## 過去 7 天實驗數據
{exp_summary}

## 累積學習
{resource}
{substack_section}

請制定本週策略，輸出以下格式的 Markdown（直接輸出，不要有前綴說明）：

# 本週流量策略（{date_str} 更新）

## 目標
[衝觸及 / 導流電子報（主題：XXX）] 以及原因（1-2 句）

## CTA 使用時機
當貼文主題涉及以下任一時加電子報 CTA：
- [主題 A]
- [主題 B]

## CTA 文案參考
- [範例 1]
- [範例 2]

## 本週不加 CTA 的主題
- [主題列表]

## 本週電子報主題
[一句話描述本週電子報要寫的主題，基於最高互動的貼文方向]"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    strategy = response.content[0].text.strip()
    (PROMPTS_DIR / "strategy.md").write_text(strategy, encoding="utf-8")
    print(f"[STRATEGY] strategy.md updated ({len(strategy)} chars)")

    # Initialize newsletter_status.json
    topic = _extract_newsletter_topic(strategy)
    newsletter_status = {
        "week": date_str,
        "topic": topic,
        "status": "pending",
    }
    write_json(DATA_DIR / "newsletter_status.json", newsletter_status)
    print(f"[STRATEGY] newsletter_status.json initialized (topic: {topic})")


if __name__ == "__main__":
    run()
