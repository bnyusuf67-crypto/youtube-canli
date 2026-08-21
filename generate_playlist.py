#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# -------------------- AYARLAR --------------------
STREAMS_DIR = "streams"
PLAYLIST_FILE = "playlist.m3u"
USER_AGENT_PLAYLIST = "VLC/3.0.20"
TIMEOUT = 8
MAX_WORKERS = 8

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

def get_innertube_manifest(video_id):
    """InnerTube API'yi (ANDROID istemcisi) kullanarak HLS Manifest URL'sini alır."""
    url = "https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
    
    payload = {
        "videoId": video_id,
        "contentCheckOk": True,
        "racyCheckOk": True,
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "21.08.266",
                "platform": "MOBILE",
                "osName": "Android",
                "osVersion": "12"
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "com.google.android.youtube/21.08.266 (Linux; U; Android 12)"
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            
            # streamingData içindeki hlsManifestUrl'i çek
            streaming_data = res_json.get("streamingData", {})
            return streaming_data.get("hlsManifestUrl")
    except Exception:
        return None

def fetch_live_stream(kanal):
    """Kanalın yayın sayfasından video_id'yi bulup InnerTube ile akış adresi üretir."""
    live_url = f"https://www.youtube.com/{kanal['handle']}/live"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # Step 1: Kanalın canlı yayın sayfasından videoId bul
        req = urllib.request.Request(live_url, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
            # Canonical URL veya JSON içerisinden 11 haneli videoId tespiti
            match = re.search(r'href="https://www\.youtube\.com/watch\?v=([\w-]{11})"', html)
            if not match:
                match = re.search(r'"videoId":"([\w-]{11})"', html)

            if match:
                video_id = match.group(1)
                # Step 2: InnerTube API çağrısı yap
                manifest_url = get_innertube_manifest(video_id)
                if manifest_url:
                    kanal["manifest_url"] = manifest_url
                    return kanal
    except Exception:
        pass
    return None

def main():
    os.makedirs(STREAMS_DIR, exist_ok=True)
    print(f"🚀 Streamlink InnerTube Mantığı ile Canlı Yayın Taraması ({len(kanallar)} kanal)...\n")
    
    baslangic = datetime.now()
    basarili_kanallar = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(fetch_live_stream, kanallar)
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
            f.write(f"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=7680000\n{kanal['manifest_url']}\n")

        ana_m3u += f'#EXTINF:-1 tvg-name="{kanal["name"]}" group-title="Canlı" http-user-agent="{USER_AGENT_PLAYLIST}",{kanal["name"]}\n{kanal["manifest_url"]}\n'

    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(ana_m3u)

    gecen_sure = (datetime.now() - baslangic).total_seconds()
    print(f"\n⚡ İşlem tamamlandı! {gecen_sure:.2f} saniyede {len(basarili_kanallar)}/{len(kanallar)} kanal güncellendi.")

if __name__ == "__main__":
    main()
