import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

CACHE_DIR = BASE_DIR / "cache"
LOG_DIR = BASE_DIR / "logs"

CACHE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

CACHE_FILE = CACHE_DIR / "cache.json"

YT_DLP = shutil.which("yt-dlp") or "/usr/local/bin/yt-dlp"

CACHE_SECONDS = 300        # 5 dakika
YT_TIMEOUT = 30            # saniye

HOST = "0.0.0.0"
PORT = 8000

USER_AGENT = "VLC/3.0.20"

DOMAIN = "https://yt.tecostream.xyz"
