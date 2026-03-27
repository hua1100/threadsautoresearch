import subprocess
from pathlib import Path


def fetch_recent_activity(repo_path: str, days: int = 1) -> list[dict]:
    try:
        result = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--pretty=format:%h|%s|%ai"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({
                    "hash": parts[0],
                    "message": parts[1],
                    "date": parts[2],
                })
        return commits
    except Exception as e:
        print(f"[SOURCE] GitHub error for {repo_path}: {e}")
        return []


def list_local_repos(base_path: str = "/Users/hua") -> list[str]:
    repos = []
    base = Path(base_path)
    if not base.exists():
        return []
    for candidate in base.iterdir():
        if candidate.is_dir() and (candidate / ".git").exists():
            repos.append(str(candidate))
    return repos
