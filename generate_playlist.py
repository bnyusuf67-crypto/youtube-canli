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
TIMEOUT = 8
MAX_WORKERS = 8

# Varsayılan (Yedek) API Anahtarı
DEFAULT_INNERTUBE_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
INNERTUBE_KEY = None

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

def fetch_innertube_api_key():
    """
    YouTube ana sayfasını yükleyip HTML içindeki güncel INNERTUBE_API_KEY değerini çeker.
    """
    url = "https://www.youtube.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            html = response.read().decode("utf-8", errors="ignore")
            # "INNERTUBE_API_KEY":"AIzaSy..." desenini ara
            match = re.search(r'["\']INNERTUBE_API_KEY["\']\s*:\s*["\']([^"\'\s]+)["\']', html)
            if match:
                key = match.group(1)
                print(f"🔑 Güncel InnerTube API Key webden çekildi: {key[:10]}...")
                return key
    except Exception as e:
        print(f"⚠️ API Key çekilirken hata oluştu: {e}")
    
    print("⚠️ Webden API Key alınamadı, yedek varsayılan key kullanılıyor.")
    return DEFAULT_INNERTUBE_KEY

def inner_tube_post(endpoint, payload, api_key, client_type="WEB"):
    """InnerTube API'sine doğrudan JSON POST isteği gönderir."""
    url = f"https://www.youtube.com/youtubei/v1/{endpoint}?key={api_key}"
    
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

def fetch_live_video_id(handle, api_key):
    """Canlı yayının videoId değerini dinamik InnerTube istekleri ile çözer."""
    # 1. YÖNTEM: InnerTube resolve_url API
    try:
        res = inner_tube_post("navigation/resolve_url", {
            "url": f"https://www.youtube.com/{handle}/live"
        }, api_key=api_key, client_type="WEB")
        
        endpoint = res.get("endpoint", {})
        
        v_id = endpoint.get("watchEndpoint", {}).get("videoId")
        if v_id:
            return v_id
            
        cmd_url = endpoint.get("commandMetadata", {}).get("webCommandMetadata", {}).get("url", "")
        if "v=" in cmd_url:
            return cmd_url.split("v=")[1].split("&")[0]
    except Exception:
        pass

    # 2. YÖNTEM: Headless Redirect URL Kontrolü
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
    """Kanal için güncel videoId ve M3U8 adresini alır."""
    try:
        video_id = fetch_live_video_id(kanal["handle"], INNERTUBE_KEY)
        if not video_id:
            return None

        res_player = inner_tube_post("player", {
            "videoId": video_id,
            "contentCheckOk": True,
            "racyCheckOk": True
        }, api_key=INNERTUBE_KEY, client_type="ANDROID")

        manifest_url = res_player.get("streamingData", {}).get("hlsManifestUrl")
        if manifest_url:
            kanal["manifest_url"] = manifest_url
            return kanal
    except Exception:
        pass
    return None

def main():
    global INNERTUBE_KEY
    os.makedirs(STREAMS_DIR, exist_ok=True)
    
    print("🌐 YouTube dinamik yapılandırması yükleniyor...")
    INNERTUBE_KEY = fetch_innertube_api_key()
    
    print(f"\n🚀 Canlı Yayın Taraması Başlatıldı ({len(kanallar)} kanal)...\n")
    
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
