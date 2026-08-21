#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# -------------------- AYARLAR --------------------
STREAMS_DIR = "streams"
PLAYLIST_FILE = "playlist.m3u"
USER_AGENT = "VLC/3.0.20"
TIMEOUT = 5             # Saniye bazında web istek zaman aşımı
MAX_WORKERS = 10        # Eşzamanlı sorgulanacak kanal sayısı

# Public Invidious API Sunucuları (Biri yanıt vermezse diğeri denenir)
INVIDIOUS_INSTANCES = [
    "https://inv.hostux.net",
    "https://invidious.nerdvpn.de",
    "https://invidious.drgns.space",
    "https://vid.puppethead.com",
    "https://invidious.projectsegfau.lt"
]

# -------------------- KANAL LİSTESİ (Kanal ID'leri ile) --------------------
kanallar = [
    {"slug": "trthaber", "name": "TRT Haber", "channel_id": "UC30S91R2r_O4zBsoC33y2oA"},
    {"slug": "cnnturk", "name": "CNN Turk", "channel_id": "UCm9mO3211C1M3Aos_P32M_g"},
    {"slug": "ntv", "name": "NTV", "channel_id": "UC9110BsoRst3J8B5p20mAtA"},
    {"slug": "ahaber", "name": "A Haber", "channel_id": "UC4QO4iIsG_6S3bA5SjF6Urg"},
    {"slug": "haberturk", "name": "Haber Turk", "channel_id": "UCF4tSsnX_uVf12Y8mD__P2A"},
    {"slug": "halktv", "name": "Halk TV", "channel_id": "UCqX6v-5_bEilR8sLqJ3fllg"},
    {"slug": "sozcutelevizyonu", "name": "Sozcu TV", "channel_id": "UC2K3f_O8z6L8p6p-mH778gg"},
    {"slug": "tgrthaber", "name": "TGRT Haber", "channel_id": "UC8fO1M59I_z5mZ6R7A7vXqA"},
    {"slug": "flashhaber", "name": "Flash Haber", "channel_id": "UC7hG9yZ00M9y64d6NlM275g"},
    {"slug": "haberglobal", "name": "Haber Global", "channel_id": "UCY58q8uO-zE0Z1QvYpU4l8A"},
    {"slug": "tv100", "name": "TV 100", "channel_id": "UCGZ38B21kH3HhXpW73Uj-9w"},
    {"slug": "bloomberght", "name": "Bloomberg HT", "channel_id": "UC0A0O04YxHnK7fA3p7O5G_Q"},
    {"slug": "benguturk", "name": "Bengu Turk", "channel_id": "UC7Z45W_o5mN3H-59R6m8p5A"},
    {"slug": "krttv", "name": "KRT TV", "channel_id": "UCsJ38A0M8oR_9a22M_90qQg"},
    {"slug": "ulusalkanal", "name": "Ulusal Kanal", "channel_id": "UCqY7M8O_7JkZfQ5_5A5zWwA"},
    {"slug": "ulketv", "name": "Ulke TV", "channel_id": "UCWp6M2A4zH5n6x6W5g_8Q1A"},
    {"slug": "ekoturk", "name": "Eko Turk", "channel_id": "UC8sQ1X55O_G5J-6QxR1wM3w"},
    {"slug": "tv24", "name": "24 TV", "channel_id": "UC0k3h7Q0-P5_J-5wM8kZ6QA"},
    {"slug": "aspor", "name": "A Spor", "channel_id": "UC2y-Z_g7bQ3E1K85w9_zM2A"},
    {"slug": "htspor", "name": "HT Spor", "channel_id": "UCG0-W-K2hR195W8I6A_5RGA"},
    {"slug": "tvnet", "name": "TV Net", "channel_id": "UC9J4Z8O_833-K7z_g2P701A"},
    {"slug": "beinsportshaber", "name": "Bein Spor Haber", "channel_id": "UC-O6H2J1u36pM1-aK2E4fAg"},
    {"slug": "cnbce", "name": "CNBC-e", "channel_id": "UCQ2-k8hK_Z4S8N8P0Z9E6xA"}
]

# -------------------- FONKSİYONLAR --------------------
def get_live_url_from_invidious(kanal):
    """Invidious API üzerinden canlı yayın Google Manifest (HLS) linkini çeker."""
    for instance in INVIDIOUS_INSTANCES:
        try:
            api_url = f"{instance}/api/v1/channels/live/{kanal['channel_id']}"
            req = urllib.request.Request(
                api_url, 
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    hls_url = data.get("hlsUrl")
                    if hls_url:
                        kanal["manifest_url"] = hls_url
                        return kanal
        except Exception:
            # Sunucu yanıt vermezse sonraki Invidious sunucusuna geç
            continue
            
    return None

def main():
    os.makedirs(STREAMS_DIR, exist_ok=True)
    print(f"🚀 Invidious API ile {len(kanallar)} kanal taranıyor...\n")
    
    baslangic = datetime.now()
    basarili_kanallar = []

    # Paralel istekler (ThreadPoolExecutor)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(get_live_url_from_invidious, kanallar)
        for res in results:
            if res:
                basarili_kanallar.append(res)
                print(f"✅ {res['name']} alındı.")
            else:
                print("❌ Bir kanal için link alınamadı.")

    # M3U ve .m3u8 dosyalarını kaydet
    ana_m3u = "#EXTM3U\n"
    for kanal in basarili_kanallar:
        # Tekil .m3u8 dosyası oluştur
        filepath = os.path.join(STREAMS_DIR, f"{kanal['slug']}.m3u8")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"#EXTM3U\n#EXTINF:-1 tvg-name=\"{kanal['name']}\" http-user-agent=\"{USER_AGENT}\",{kanal['name']}\n{kanal['manifest_url']}\n")

        # Ana playlist.m3u içeriğine ekle
        ana_m3u += f'#EXTINF:-1 tvg-name="{kanal["name"]}" group-title="Canlı" http-user-agent="{USER_AGENT}",{kanal["name"]}\n{kanal["manifest_url"]}\n'

    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(ana_m3u)

    gecen_sure = (datetime.now() - baslangic).total_seconds()
    print(f"\n⚡ İşlem tamamlandı! {gecen_sure:.2f} saniyede {len(basarili_kanallar)}/{len(kanallar)} kanal güncellendi.")

if __name__ == "__main__":
    main()
