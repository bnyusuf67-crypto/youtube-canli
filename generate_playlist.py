#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import json
import urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# -------------------- AYARLAR --------------------
STREAMS_DIR = "streams"
PLAYLIST_FILE = "playlist.m3u"
USER_AGENT_PLAYLIST = "VLC/3.0.20"
TIMEOUT = 10
MAX_WORKERS = 8

# Dinamik Yapılandırma Global Değişkenleri
INNERTUBE_KEY = ""
VISITOR_DATA = ""
ANDROID_CLIENT_VERSION = "19.35.36"  # Varsayılan (Yedek)
WEB_CLIENT_VERSION = "2.20260101.00.00" # Varsayılan (Yedek)

kanallar = [
    {"slug": "trthaber", "name": "TRT Haber", "handle": "@trthaber"},
    {"slug": "cnnturk", "name": "CNN Turk", "handle": "@cnnturk"},
    {"slug": "ntv", "name": "NTV", "handle": "@ntv"},
    {"slug": "ahaber", "name": "A Haber", "handle": "@Ahaber"},
    {"slug": "haberturk", "name": "Haber Turk", "handle": "@haberturktv"},
    {"slug": "halktv", "name": "Halk TV", "handle": "@Halktvkanali"},
    {"slug": "sozcutelevizyonu", "name": "Sozcu TV", "handle": "@sozcutelevizyonu"},
    {"slug": "tgrthaber", "name": "TGRT Haber", "handle": "@tgrthaber"},
    {"slug": "haberglobal", "name": "Haber Global", "handle": "@HaberGlobal"},
    {"slug": "tv100", "name": "TV100", "handle": "@TV100"},
    {"slug": "bloomberght", "name": "Bloomberg HT", "handle": "@BloombergHT"},
    {"slug": "krttv", "name": "KRT TV", "handle": "@KRTVTV"},
    {"slug": "ulusalkanal", "name": "Ulusal Kanal", "handle": "@ulusal.kanal"},
    {"slug": "ulketv", "name": "Ülke TV", "handle": "@ulketv"},
    {"slug": "aspor", "name": "A Spor", "handle": "@aspor"},
    {"slug": "cnbce", "name": "CNBC-e", "handle": "@CNBCeTurkiye"}
]

def get_latest_android_version():
    """Google Play Store sayfasından en güncel Android YouTube clientVersion sürümünü çeker."""
    play_store_url = "https://play.google.com/store/apps/details?id=com.google.android.youtube&hl=en"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        req = urllib.request.Request(play_store_url, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            # Google Play sayfasındaki versiyon pattern'i
            match = re.search(r'\[\[\["(\d+\.\d+\.\d+)"\]\]', html)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None

def fetch_latest_youtube_config():
    """
    YouTube Web ve Play Store üzerinden:
    1. INNERTUBE_API_KEY
    2. VISITOR_DATA
    3. clientVersion (Android & Web)
    değerlerini otomatik günceller.
    """
    global INNERTUBE_KEY, VISITOR_DATA, ANDROID_CLIENT_VERSION, WEB_CLIENT_VERSION
    
    # 1. Play Store'dan Güncel Android Sürümünü Çek
    latest_android = get_latest_android_version()
    if latest_android:
        ANDROID_CLIENT_VERSION = latest_android
        print(f"📱 Dinamik Android Client Version: {ANDROID_CLIENT_VERSION}")

    # 2. YouTube Web'den API Key, Visitor Data ve Web Client Version Çek
    url = "https://www.youtube.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            
            # API Key
            key_match = re.search(r'["\']INNERTUBE_API_KEY["\']\s*:\s*["\']([^"\'\s]+)["\']', html)
            if key_match:
                INNERTUBE_KEY = key_match.group(1)
                print(f"🔑 Dinamik API Key: {INNERTUBE_KEY[:10]}...")

            # Visitor Data
            vis_match = re.search(r'["\']VISITOR_DATA["\']\s*:\s*["\']([^"\'\s]+)["\']', html)
            if vis_match:
                VISITOR_DATA = vis_match.group(1)
                print(f"👤 Dinamik Visitor Data: {VISITOR_DATA[:10]}...")

            # Web Client Version
            web_ver_match = re.search(r'["\']INNERTUBE_CONTEXT_CLIENT_VERSION["\']\s*:\s*["\']([^"\'\s]+)["\']', html)
            if web_ver_match:
                WEB_CLIENT_VERSION = web_ver_match.group(1)
                print(f"💻 Dinamik Web Client Version: {WEB_CLIENT_VERSION}")

    except Exception as e:
        print(f"⚠️ Yapılandırma güncellenirken hata: {e}")

def get_live_video_id(handle):
    """Kanalın canlı yayın sayfasından dinamik videoId bulur."""
    url = f"https://www.youtube.com/{handle}/live"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            
            match = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([\w-]{11})">', html)
            if match:
                return match.group(1)

            match_json = re.search(r'var ytInitialData = ({.*?});</script>', html, re.DOTALL)
            if match_json:
                v_match = re.search(r'"videoId"\s*:\s*"([\w-]{11})"', match_json.group(1))
                if v_match:
                    return v_match.group(1)
    except Exception:
        pass
    return None

def fetch_m3u8_url(video_id):
    """Otomatik güncellenmiş ANDROID clientVersion ile HLS Manifest URL'si çeker."""
    url = f"https://www.youtube.com/youtubei/v1/player?key={INNERTUBE_KEY}"
    
    payload = {
        "videoId": video_id,
        "contentCheckOk": True,
        "racyCheckOk": True,
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": ANDROID_CLIENT_VERSION,  # OTOMATİK GÜNCEL SÜRÜM
                "platform": "MOBILE",
                "osName": "Android",
                "osVersion": "12",
                "visitorData": VISITOR_DATA
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": f"com.google.android.youtube/{ANDROID_CLIENT_VERSION} (Linux; U; Android 12)"
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("streamingData", {}).get("hlsManifestUrl")
    except Exception:
        pass
    return None

def process_channel(kanal):
    video_id = get_live_video_id(kanal["handle"])
    if video_id:
        manifest_url = fetch_m3u8_url(video_id)
        if manifest_url:
            kanal["manifest_url"] = manifest_url
            return kanal
    return None

def main():
    os.makedirs(STREAMS_DIR, exist_ok=True)
    
    print("🌐 YouTube Dinamik Yapılandırması ve Client Version Yükleniyor...")
    fetch_latest_youtube_config()
    
    print(f"\n🚀 Canlı Yayın Taraması Başlatıldı ({len(kanallar)} kanal)...\n")
    
    baslangic = datetime.now()
    basarili_kanallar = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(process_channel, kanallar)
        for res in results:
            if res:
                basarili_kanallar.append(res)
                print(f"✅ {res['name']} alındı.")
            else:
                print("❌ Kanal alınamadı.")

    # M3U Dosyalarını Yaz
    ana_m3u = "#EXTM3U\n"
    for kanal in basarili_kanallar:
        filepath = os.path.join(STREAMS_DIR, f"{kanal['slug']}.m3u8")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"#EXTM3U\n#EXTINF:-1 tvg-name=\"{kanal['name']}\" http-user-agent=\"{USER_AGENT_PLAYLIST}\",{kanal['name']}\n{kanal['manifest_url']}\n")

        ana_m3u += f'#EXTINF:-1 tvg-name="{kanal["name"]}" group-title="Canlı" http-user-agent="{USER_AGENT_PLAYLIST}",{kanal["name"]}\n{kanal["manifest_url"]}\n'

    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(ana_m3u)

    gecen_sure = (datetime.now() - baslangic).total_seconds()
    print(f"\n⚡ İşlem tamamlandı! {gecen_sure:.2f} saniyede {len(basarili_kanallar)}/{len(kanallar)} kanal güncellendi.")

if __name__ == "__main__":
    main()
