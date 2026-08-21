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
USER_AGENT = "VLC/3.0.20"
TIMEOUT = 5             # Saniye bazında istek zaman aşımı
MAX_WORKERS = 10        # Eşzamanlı taranacak kanal sayısı

# Sadece kanalın @kullanıcı adını yazmanız yeterlidir
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8"
}

def extract_channel_id(handle):
    """Kanalın @kullaniciadi sayfasından UC... ile başlayan resmi Kanal ID'sini çıkarır."""
    url = f"https://www.youtube.com/{handle}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            html = response.read().decode('utf-8')
            
            # YouTube HTML kaynak kodundaki channelId değerini yakala
            match = re.search(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', html)
            if match:
                return match.group(1)
            
            # Alternatif meta etiket taraması
            meta_match = re.search(r'itemprop="channelId"\s+content="(UC[a-zA-Z0-9_-]{22})"', html)
            if meta_match:
                return meta_match.group(1)
    except Exception:
        pass
    return None

def fetch_live_stream(kanal):
    """Kanal ID'sini çıkarır ve Embed API üzerinden HLS Manifest (.m3u8) linkini alır."""
    # 1. Aşama: Kanal ID'sini otomatik tespit et
    channel_id = extract_channel_id(kanal["handle"])
    
    if not channel_id:
        return None
        
    kanal["channel_id"] = channel_id

    # 2. Aşama: Bulunan Kanal ID ile Embed API'den HLS URL'sini çek
    embed_url = f"https://www.youtube.com/embed/live_stream?channel={channel_id}"
    try:
        req = urllib.request.Request(embed_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            html = response.read().decode('utf-8')

            # Embed sayfasındaki hlsManifestUrl parametresini süz
            match = re.search(r'"hlsManifestUrl":"([^"]+)"', html)
            if match:
                manifest_url = match.group(1).replace(r'\/', '/')
                kanal["manifest_url"] = manifest_url
                return kanal
    except Exception:
        pass
    return None

def main():
    os.makedirs(STREAMS_DIR, exist_ok=True)
    print(f"🚀 Kanal ID Çıkarıcı & Embed Parser çalışıyor ({len(kanallar)} kanal)...\n")
    
    baslangic = datetime.now()
    basarili_kanallar = []

    # Paralel istekler
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(fetch_live_stream, kanallar)
        for res in results:
            if res:
                basarili_kanallar.append(res)
                print(f"✅ {res['name']} (ID: {res['channel_id']}) alındı.")
            else:
                print("❌ Bir kanal için ID veya yayın linki alınamadı.")

    # M3U Dosyalarını Yaz
    ana_m3u = "#EXTM3U\n"
    for kanal in basarili_kanallar:
        filepath = os.path.join(STREAMS_DIR, f"{kanal['slug']}.m3u8")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=7680000\n{kanal['manifest_url']}\n")

        ana_m3u += f'#EXTINF:-1 tvg-name="{kanal["name"]}" group-title="Canlı" http-user-agent="{USER_AGENT}",{kanal["name"]}\n{kanal["manifest_url"]}\n'

    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(ana_m3u)

    gecen_sure = (datetime.now() - baslangic).total_seconds()
    print(f"\n⚡ İşlem tamamlandı! {gecen_sure:.2f} saniyede {len(basarili_kanallar)}/{len(kanallar)} kanal güncellendi.")

if __name__ == "__main__":
    main()
