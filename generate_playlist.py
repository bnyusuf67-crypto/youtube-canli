#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# fake-useragent kontrolü ve yüklenmesi
try:
    from fake_useragent import UserAgent
    ua = UserAgent()
except ImportError:
    print("❌ 'fake-useragent' kütüphanesi bulunamadı! Yüklemek için: pip install fake-useragent")
    sys.exit(1)

# -------------------- AYARLAR --------------------
STREAMS_DIR = "streams"
PLAYLIST_FILE = "playlist.m3u"
USER_AGENT_PLAYLIST = "VLC/3.0.20"  # Playlist içi varsayılan oynatıcı UA
TIMEOUT = 6
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

def get_dynamic_headers():
    """Her istek için dinamik ve rastgele User-Agent başlığı üretir."""
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cookie": "CONSENT=YES+cb; SOCS=CAI"
    }

def fetch_live_stream(kanal):
    """Canlı yayın HLS Manifest URL'sini dinamik User-Agent ile çeker."""
    live_url = f"https://www.youtube.com/{kanal['handle']}/live"
    headers = get_dynamic_headers()
    
    try:
        req = urllib.request.Request(live_url, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            html = response.read().decode('utf-8', errors='ignore')

            # 1. Yöntem: Direct Regex Taraması
            match = re.search(r'"hlsManifestUrl":"([^"]+)"', html)
            if match:
                manifest_url = match.group(1).replace(r'\/', '/')
                kanal["manifest_url"] = manifest_url
                return kanal

            # 2. Yöntem: ChannelID bulup Embed Player üzerinden deneme
            channel_match = re.search(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', html)
            if channel_match:
                channel_id = channel_match.group(1)
                embed_url = f"https://www.youtube.com/embed/live_stream?channel={channel_id}"
                embed_req = urllib.request.Request(embed_url, headers=get_dynamic_headers())
                
                with urllib.request.urlopen(embed_req, timeout=TIMEOUT) as embed_res:
                    embed_html = embed_res.read().decode('utf-8', errors='ignore')
                    embed_match = re.search(r'"hlsManifestUrl":"([^"]+)"', embed_html)
                    if embed_match:
                        kanal["manifest_url"] = embed_match.group(1).replace(r'\/', '/')
                        return kanal

    except Exception:
        pass
    return None

def main():
    os.makedirs(STREAMS_DIR, exist_ok=True)
    print(f"🚀 Dinamik User-Agent ile Canlı Yayın Taraması ({len(kanallar)} kanal)...\n")
    
    baslangic = datetime.now()
    basarili_kanallar = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(fetch_live_stream, kanallar)
        for res in results:
            if res:
                basarili_kanallar.append(res)
                print(f"✅ {res['name']} alındı.")
            else:
                print(f"❌ Kanal alınamadı.")

    # M3U Dosyalarını Yaz
    ana_m3u = "#EXTM3U\n"
    for kanal in basarili_kanallar:
        # Tekil M3U8 Dosyası
        filepath = os.path.join(STREAMS_DIR, f"{kanal['slug']}.m3u8")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=7680000\n{kanal['manifest_url']}\n")

        # Toplu Playlist
        ana_m3u += f'#EXTINF:-1 tvg-name="{kanal["name"]}" group-title="Canlı" http-user-agent="{USER_AGENT_PLAYLIST}",{kanal["name"]}\n{kanal["manifest_url"]}\n'

    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(ana_m3u)

    gecen_sure = (datetime.now() - baslangic).total_seconds()
    print(f"\n⚡ İşlem tamamlandı! {gecen_sure:.2f} saniyede {len(basarili_kanallar)}/{len(kanallar)} kanal güncellendi.")

if __name__ == "__main__":
    main()
