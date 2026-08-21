#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# -------------------- AYARLAR --------------------
STREAMS_DIR = "streams"
PLAYLIST_FILE = "playlist.m3u"
USER_AGENT_PLAYLIST = "VLC/3.0.20"
TIMEOUT = 8
MAX_WORKERS = 8

INNERTUBE_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"

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

def inner_tube_post(endpoint, payload, client_type="WEB"):
    """InnerTube API'sine doğrudan JSON POST isteği gönderir."""
    url = f"https://www.youtube.com/youtubei/v1/{endpoint}?key={INNERTUBE_KEY}"
    
    if client_type == "WEB":
        context = {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240212.00.00",
                "originalUrl": "https://www.youtube.com"
            }
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    else:  # ANDROID
        context = {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "19.29.37",
                "platform": "MOBILE"
            }
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/19.29.37 (Linux; U; Android 11)"
        }

    payload["context"] = context
    data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))

def fetch_live_video_id(handle):
    """
    Canlı yayının videoId değerini dinamik olarak YouTube istemci sorguları ile bulur.
    Yöntem 1: resolve_url
    Yöntem 2: WEB Browse API (Emin olmak için fallback)
    """
    # 1. YÖNTEM: WEB resolve_url
    try:
        res = inner_tube_post("navigation/resolve_url", {
            "url": f"https://www.youtube.com/{handle}/live"
        }, client_type="WEB")
        
        endpoint = res.get("endpoint", {})
        
        # Doğrudan watchEndpoint geldiyse videoId mevcuttur
        v_id = endpoint.get("watchEndpoint", {}).get("videoId")
        if v_id:
            return v_id
            
        # CommandMetadata yönlendirmesinde v= var mı kontrolü
        cmd_url = endpoint.get("commandMetadata", {}).get("webCommandMetadata", {}).get("url", "")
        if "v=" in cmd_url:
            return cmd_url.split("v=")[1].split("&")[0]
    except Exception:
        pass

    # 2. YÖNTEM: HTML Headless HTTP Redirect (Yönlendirilen Canonical URL'den bulma)
    try:
        req = urllib.request.Request(
            f"https://www.youtube.com/{handle}/live",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            method="HEAD"
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            final_url = resp.geturl()
            if "v=" in final_url:
                return final_url.split("v=")[1].split("&")[0]
    except Exception:
        pass

    return None

def fetch_live_stream(kanal):
    """Dynamic ID + InnerTube HLS Manifest akış adresi alma mantığı."""
    try:
        # Dinamik Video ID alma
        video_id = fetch_live_video_id(kanal["handle"])
        if not video_id:
            return None

        # Player API ile Akış URL'si Alma
        res_player = inner_tube_post("player", {
            "videoId": video_id,
            "contentCheckOk": True,
            "racyCheckOk": True
        }, client_type="ANDROID")

        manifest_url = res_player.get("streamingData", {}).get("hlsManifestUrl")
        if manifest_url:
            kanal["manifest_url"] = manifest_url
            return kanal
    except Exception:
        pass
    return None

def main():
    os.makedirs(STREAMS_DIR, exist_ok=True)
    print(f"🚀 Dinamik Web Parametre Bulucu Başlatıldı ({len(kanallar)} kanal)...\n")
    
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
