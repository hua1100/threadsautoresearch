"""Strategy Agent: 分析過去 7 天數據，更新 prompts/strategy.md"""
import json
import anthropic
from datetime import datetime, timezone, timedelta
from orchestrator.config import ANTHROPIC_API_KEY, DATA_DIR, PROMPTS_DIR


def load_recent_experiments(days: int = 7) -> list[dict]:
    path = DATA_DIR / "experiments.json"
    if not path.exists():
        return []
    experiments = json.loads(path.read_text(encoding="utf-8"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for exp in experiments:
        ts = exp.get("harvested_at", "")
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                recent.append(exp)
        except (ValueError, TypeError):
            pass
    return recent


def run() -> None:
    experiments = load_recent_experiments(days=7)
    resource = ""
    resource_path = PROMPTS_DIR / "resource.md"
    if resource_path.exists():
        resource = resource_path.read_text(encoding="utf-8")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    exp_summary = json.dumps(experiments, ensure_ascii=False, indent=2)

    prompt = f"""你是一個 Threads 內容策略師。分析過去 7 天的貼文數據，制定本週流量策略。

## 過去 7 天實驗數據
{exp_summary}

## 累積學習
{resource}

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
- [主題列表]"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    strategy = response.content[0].text.strip()
    (PROMPTS_DIR / "strategy.md").write_text(strategy, encoding="utf-8")
    print(f"[STRATEGY] strategy.md updated ({len(strategy)} chars)")


if __name__ == "__main__":
    run()
