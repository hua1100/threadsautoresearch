import sys
import traceback
from orchestrator.config import PHASE_SWITCH_FOLLOWER_THRESHOLD
from orchestrator.harvest import harvest
from orchestrator.analyze import analyze
from orchestrator.generate import generate
from orchestrator.deploy import deploy
from orchestrator.notify import send_notification
from orchestrator.threads_client import get_user_insights
from orchestrator.sources.youtube import fetch_all_channels
from orchestrator.sources.github import list_local_repos, fetch_recent_activity
from orchestrator.sources.x_curated import fetch_x_content, read_curated_file
from orchestrator.notify import fetch_incoming_messages


def detect_phase(follower_count: int) -> int:
    if follower_count >= PHASE_SWITCH_FOLLOWER_THRESHOLD:
        return 2
    return 1


def get_follower_count() -> int:
    try:
        insights = get_user_insights()
        return insights.get("followers_count", 0)
    except Exception:
        return 0


def fetch_sources() -> dict:
    print("[1/5] SOURCE: 抓取素材...")

    youtube = fetch_all_channels(hours=12)
    print(f"  YouTube: {len(youtube)} 部新影片")

    github = []
    for repo_path in list_local_repos():
        commits = fetch_recent_activity(repo_path, days=1)
        github.extend(commits)
    print(f"  GitHub: {len(github)} 個新 commit")

    telegram_msgs = fetch_incoming_messages()
    print(f"  Telegram: {len(telegram_msgs)} 則新訊息")
    x = fetch_x_content(telegram_msgs)
    print(f"  X.com: {len(x)} 則新素材（+ 策展檔案）")

    return {"youtube": youtube, "github": github, "x": x}


def run():
    try:
        follower_count = get_follower_count()
        phase = detect_phase(follower_count)
        print(f"[0/5] Phase {phase} | 追蹤者: {follower_count}")

        sources = fetch_sources()

        print("[2/5] HARVEST: 收割數據...")
        harvest_results = harvest()
        print(f"  收集到 {len(harvest_results)} 篇貼文數據")

        print("[3/5] ANALYZE: 分析表現...")
        analysis = analyze(harvest_results) if harvest_results else {
            "scored_posts": [],
            "analysis": "首次運行，無歷史數據",
            "learnings": "",
            "round_number": 1,
        }

        print("[4/5] GENERATE: 產出新貼文...")
        new_posts = generate(analysis, sources)
        print(f"  產出 {len(new_posts)} 篇新貼文")

        print("[5/5] DEPLOY: 發佈貼文...")
        published = deploy(new_posts)
        published_count = sum(1 for p in published if p.get("media_id"))
        print(f"  成功發佈 {published_count} 篇")

        msg = (
            f"🔄 *AutoResearch Threads — Round {analysis.get('round_number', '?')}*\n"
            f"Phase: {phase} | 追蹤者: {follower_count}\n"
            f"素材: YT={len(sources['youtube'])} GH={len(sources['github'])} X={len(sources['x'])}\n"
            f"發佈: {published_count}/{len(new_posts)} 篇\n"
        )

        if harvest_results:
            top = analysis.get("scored_posts", [{}])[0] if analysis.get("scored_posts") else {}
            if top:
                msg += f"Top: score={top.get('score', 0)} views={top.get('views', 0)} | {top.get('text', '')[:50]}\n"

        if analysis.get("learnings"):
            msg += f"\n學習摘要:\n{analysis['learnings'][:300]}"

        send_notification(msg)
        print("\n✅ 迴圈完成")

    except Exception as e:
        error_msg = f"❌ AutoResearch Threads ERROR\n{type(e).__name__}: {e}"
        print(error_msg)
        traceback.print_exc()
        send_notification(error_msg)
        sys.exit(1)


if __name__ == "__main__":
    run()
