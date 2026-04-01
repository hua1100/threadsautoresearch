"""Strategy Agent (data-only): 收集數據並輸出，由 Claude Code agent 分析並寫 strategy.md"""
import json
from datetime import datetime, timezone
from orchestrator.config import (
    PROMPTS_DIR, DATA_DIR, SUBSTACK_SID, SUBSTACK_SUBDOMAIN,
    LAZY_PACK_MIN_VIEWS,
)
from orchestrator.lazy_pack_agent import generate_lazy_pack
from orchestrator.substack_client import SubstackClient
from orchestrator.utils import load_recent_experiments, read_json, write_json


def run() -> None:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1. Fetch Substack snapshot
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

    # 2. Load experiments and resource
    experiments = load_recent_experiments(days=7)
    resource = ""
    resource_path = PROMPTS_DIR / "resource.md"
    if resource_path.exists():
        resource = resource_path.read_text(encoding="utf-8")

    # 3. Output data for agent
    print(f"\n{'='*60}")
    print(f"STRATEGY DATA ({date_str})")
    print(f"{'='*60}")

    print(f"\n## 過去 7 天實驗數據（{len(experiments)} 輪）")
    for exp in experiments:
        results = exp.get("results", [])
        if results:
            top = max(results, key=lambda x: x.get("score", 0))
            print(f"  Round {exp.get('round_number', '?')}: "
                  f"{len(results)} posts | "
                  f"top score={top.get('score', 0):.4f} "
                  f"views={top.get('views', 0)} likes={top.get('likes', 0)} replies={top.get('replies', 0)}")

    print(f"\n## 所有貼文表現（按 score 排序）")
    all_results = []
    all_posts = read_json(DATA_DIR / "posts.json")
    posts_map = {}
    if isinstance(all_posts, list):
        posts_map = {p.get("media_id"): p for p in all_posts}

    for exp in experiments:
        for r in exp.get("results", []):
            post = posts_map.get(r.get("media_id"), {})
            r["text"] = post.get("text", "")[:100]
            r["dimensions"] = post.get("dimensions", {})
            all_results.append(r)

    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    for r in all_results[:20]:
        dims = r.get("dimensions", {})
        print(f"  score={r.get('score', 0):.4f} | "
              f"views={r.get('views', 0)} likes={r.get('likes', 0)} replies={r.get('replies', 0)} | "
              f"[{dims.get('content_type', '?')}] [{dims.get('strategy', '?')}] "
              f"{r.get('text', '')[:60]}")

    if substack_snapshot:
        print(f"\n## Substack 電子報現況")
        print(f"  訂閱數：{substack_snapshot.get('subscribers', 0)}（email: {substack_snapshot.get('total_email', 0)}）")
        print(f"  Open Rate：{substack_snapshot.get('open_rate', 0)}%")
        sources_str = ", ".join(
            f"{s['source']}: {s.get('traffic', 0)}" for s in substack_snapshot.get("growth_sources", [])
        )
        print(f"  流量來源：{sources_str}")
        funnel = substack_snapshot.get("threads_funnel")
        if funnel:
            print(f"  Threads 導流：{funnel['traffic']} 次 → {funnel['new_subscribers']} 訂閱（轉換率 {funnel['conversion_rate']}%）")

    if resource:
        # Only show last 2 rounds of learnings to keep output manageable
        lines = resource.split("\n")
        recent_start = None
        round_count = 0
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith("### Round"):
                round_count += 1
                if round_count == 2:
                    recent_start = i
                    break
        if recent_start is not None:
            print(f"\n## 最近累積學習")
            print("\n".join(lines[recent_start:]))
        else:
            print(f"\n## 累積學習")
            print(resource[-1500:])

    print(f"\n{'='*60}")
    print("請根據以上數據，撰寫 prompts/strategy.md")
    print(f"{'='*60}")

    # 4. Auto-trigger lazy pack for top performing post
    try:
        all_exp_results = [r for exp in experiments for r in exp.get("results", [])]
        if all_exp_results:
            top = max(all_exp_results, key=lambda x: x.get("score", 0))
            if top.get("views", 0) >= LAZY_PACK_MIN_VIEWS:
                existing_packs = read_json(DATA_DIR / "lazy_packs.json")
                if not isinstance(existing_packs, list):
                    existing_packs = []
                already_done = any(
                    p.get("media_id") == top.get("media_id") for p in existing_packs
                )
                if not already_done:
                    if isinstance(all_posts, list):
                        full_post = next(
                            (p for p in all_posts if p.get("media_id") == top.get("media_id")),
                            None,
                        )
                        if full_post:
                            print(f"[STRATEGY] Triggering lazy pack for top post: {top.get('media_id')}")
                            generate_lazy_pack(full_post)
    except Exception as e:
        print(f"[STRATEGY] Lazy pack trigger failed: {e}")


if __name__ == "__main__":
    run()
