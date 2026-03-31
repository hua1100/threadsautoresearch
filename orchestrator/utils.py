import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from orchestrator.config import DATA_DIR


def load_recent_experiments(days: int = 7) -> list[dict]:
    """Load experiments from the last N days from data/experiments.json."""
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


def read_json(path: Path) -> list | dict:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: list | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sanitize_post_text(text: str) -> str:
    # Replace literal \n with actual newlines
    text = text.replace("\\n", "\n")
    # Collapse 3+ consecutive newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text
