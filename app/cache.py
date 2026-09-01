import json
import time
from pathlib import Path
from config import CACHE_FILE

def load_cache():
    if not CACHE_FILE.exists():
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except:
        return {}

def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf8") as f:
        json.dump(data, f, indent=2)

def get(slug):

    data = load_cache()

    if slug not in data:
        return None

    row = data[slug]

    if time.time() > row["expire"]:
        return None

    return row["url"]

def set(slug, url, seconds):

    data = load_cache()

    data[slug] = {
        "url": url,
        "expire": time.time() + seconds
    }

    save_cache(data)
