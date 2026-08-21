#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import urllib.request
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

try:
    from fake_useragent import UserAgent
    ua = UserAgent()
except ImportError:
    ua = None

# -------------------- AYARLAR --------------------
STREAMS_DIR = "streams"
PLAYLIST_FILE = "playlist.m3u"
USER_AGENT_PLAYLIST = "VLC/3.0.20"
TIMEOUT = 8
MAX_WORKERS = 5  # PO Token üretimi kaynak kullandığı için worker sayısını makul tutuyoruz

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

def get_node_po_token():
    """Node.js betiğini çalıştırarak PO Token ve Visitor Data elde eder."""
    try:
        result = subprocess.run(
            ["node", "get_po_token.js"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        data = json.loads(result.stdout)
        return data.get("poToken"), data.get("visitorData")
    except Exception as e:
        print(f"⚠️ PO Token üretilemedi, varsayılan modda devam ediliyor. Hata: {e}")
        return None, None

def get_headers(po_token=None, visitor_data=None):
    """PO Token ve Visitor Data içeren istek başlıkları oluşturur."""
    user_agent = ua.random if ua else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
        "Cookie": "CONSENT=YES+cb; SOCS=CAI"
    }

    # PO Token ve Visitor Data varsa header'lara ekle
    if po_token:
        headers["X-Youtube-Po-Token"] = po_token
    if visitor_data:
        headers["X-Goog-Visitor-Id"] = visitor_data

    return headers

def fetch_live_stream(args):
    """Kanal canlı yayın linkini PO Token destekli header ile çeker."""
    kanal, po_token, visitor_data = args
    live_url = f"https://www.youtube.com/{kanal['handle']}/live"
    headers = get_headers(po_token, visitor_data)

    try:
        req = urllib.request.Request(live_url, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            html = response.read().decode('utf-8', errors='ignore')

            # Direct Manifest Taraması
            match = re.search(r'"hlsManifestUrl":"([^"]+)"', html)
            if match:
                kanal["manifest_url"] = match.group(1).replace(r'\/', '/')
                return kanal

            # Embed Fallback Taraması
            channel_match = re.search(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', html)
            if channel_match:
                channel_id = channel_match.group(1)
                embed_url = f"https://www.youtube.com/embed/live_stream?channel={channel_id}"
                embed_req = urllib.request.Request(embed_url, headers=headers)
                
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
    
    print("🔑 Node.js üzerinden PO Token alınıyor...")
    po_token, visitor_data = get_node_po_token()
    if po_token:
        print(f"✅ PO Token Başarıyla Alındı: {po_token[:15]}...")
    
    print(f"\n🚀 Canlı Yayın Taraması Başlatıldı ({len(kanallar)} kanal)...\n")
    baslangic = datetime.now()
    basarili_kanallar = []

    # Fonksiyona kanal + token parametrelerini demet (tuple) olarak gönderiyoruz
    tasks = [(kanal, po_token, visitor_data) for kanal in kanallar]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(fetch_live_stream, tasks)
        for res in results:
            if res:
                basarili_kanallar.append(res)
                print(f"✅ {res['name']} alındı.")
            else:
                print("❌ Kanal alınamadı.")

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
