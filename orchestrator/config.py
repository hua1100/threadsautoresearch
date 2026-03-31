import os
from dotenv import load_dotenv

load_dotenv()

# Required
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
THREADS_USER_ID = os.environ.get("THREADS_USER_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# Phase config
PHASE_SWITCH_FOLLOWER_THRESHOLD = int(os.getenv("PHASE_SWITCH_FOLLOWER_THRESHOLD", "100"))

# Scoring weights
SCORE_WEIGHT_VIEWS = float(os.getenv("SCORE_WEIGHT_VIEWS", "0.6"))
SCORE_WEIGHT_LIKES = float(os.getenv("SCORE_WEIGHT_LIKES", "0.2"))
SCORE_WEIGHT_REPLIES = float(os.getenv("SCORE_WEIGHT_REPLIES", "0.2"))

# YouTube channels to monitor
YOUTUBE_CHANNELS = [
    "every.to",
    "Lenny's Podcast",
    "How I AI",
    "a16z",
    "Greg Isenberg",
    "Stephen G. Pope",
    "Y Combinator",
    "Nick Saraev",
]

# Paths
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
DATA_DIR = BASE_DIR / "data"
DRAFTS_DIR = BASE_DIR / "drafts"
LOGS_DIR = BASE_DIR / "logs"
NEWSLETTER_EMAIL = os.environ.get("NEWSLETTER_EMAIL", "")
SUBSTACK_SID = os.environ.get("SUBSTACK_SID", "")
SUBSTACK_SUBDOMAIN = os.environ.get("SUBSTACK_SUBDOMAIN", "hualeee")

# LINE Messaging API
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_ADD_FRIEND_URL = os.environ.get("LINE_ADD_FRIEND_URL", "")

# Cloudflare R2
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "lazy-packs")

# Lazy Pack
WORKER_BASE_URL = os.environ.get("WORKER_BASE_URL", "")
LAZY_PACK_MIN_VIEWS = int(os.getenv("LAZY_PACK_MIN_VIEWS", "5000"))
LAZY_PACKS_DIR = BASE_DIR / "data" / "lazy_packs"
