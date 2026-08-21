#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import shutil
from datetime import datetime

# -------------------- KANAL LİSTESİ (Sabit Veriler) --------------------
kanallar = [
    {"slug": "trthaber", "name": "TRT Haber", "youtube_url": "https://www.youtube.com/@trthaber/live"},
    {"slug": "cnnturk", "name": "CNN Turk", "youtube_url": "https://www.youtube.com/@cnnturk/live"},
    {"slug": "ntv", "name": "NTV", "youtube_url": "https://www.youtube.com/@ntv/live"},
    {"slug": "ahaber", "name": "A Haber", "youtube_url": "https://www.youtube.com/@Ahaber/live"},
    {"slug": "haberturk", "name": "Haber Turk", "youtube_url": "https://www.youtube.com/@haberturktv/live"},
    {"slug": "halktv", "name": "Halk TV", "youtube_url": "https://www.youtube.com/@Halktvkanali/live"},
    {"slug": "sozcutelevizyonu", "name": "Sozcu TV", "youtube_url": "https://www.youtube.com/@sozcutelevizyonu/live"},
    {"slug": "tgrthaber", "name": "TGRT Haber", "youtube_url": "https://www.youtube.com/@tgrthaber/live"},
    {"slug": "flashhaber", "name": "Flash Haber", "youtube_url": "https://www.youtube.com/@flashhabertv/live"},
    {"slug": "haberglobal", "name": "Haber Global", "youtube_url": "https://www.youtube.com/@haberglobal/live"},
    {"slug": "tv100", "name": "TV 100", "youtube_url": "https://www.youtube.com/@tv100/live"},
    {"slug": "bloomberght", "name": "Bloomberg HT", "youtube_url": "https://www.youtube.com/@bloomberght/live"},
    {"slug": "benguturk", "name": "Bengu Turk", "youtube_url": "https://www.youtube.com/@tvbenguturk/live"},
    {"slug": "krttv", "name": "KRT TV", "youtube_url": "https://www.youtube.com/@krtcanli/live"},
    {"slug": "ulusalkanal", "name": "Ulusal Kanal", "youtube_url": "https://www.youtube.com/@ulusalkanaltv/live"},
    {"slug": "ulketv", "name": "Ulke TV", "youtube_url": "https://www.youtube.com/@ulketv/live"},
    {"slug": "ekoturk", "name": "Eko Turk", "youtube_url": "https://www.youtube.com/@ekoturktv/live"},
    {"slug": "tv24", "name": "24 TV", "youtube_url": "https://www.youtube.com/@YirmidortTV/live"},
    {"slug": "aspor", "name": "A Spor", "youtube_url": "https://www.youtube.com/@aspor/live"},
    {"slug": "htspor", "name": "HT Spor", "youtube_url": "https://www.youtube.com/@htspor/live"},
    {"slug": "tvnet", "name": "TV Net", "youtube_url": "https://www.youtube.com/@tvnet/live"},
    {"slug": "beinsportshaber", "name": "Bein Spor Haber", "youtube_url": "https://www.youtube.com/@beINSPORTSTurkiye/live"},
    {"slug": "cnbce", "name": "CNBC-e", "youtube_url": "https://www.youtube.com/@cnbce/live"}
]

# -------------------- AYARLAR --------------------
STREAMS_DIR = "streams"
PLAYLIST_FILE = "playlist.m3u"
USER_AGENT = "VLC/3.0.20"
YT_DLP_TIMEOUT = 60  # saniye

YT_DLP = shutil.which("yt-dlp")
if not YT_DLP:
    print("❌ yt-dlp bulunamadı! Lütfen yt-dlp'yi kurun: pip install yt-dlp")
    sys.exit(1)

# -------------------- FONKSİYONLAR --------------------
def get_live_url(youtube_url):
    """YouTube canlı yayın Google Manifest (m3u8) URL'sini çeker."""
    try:
        result = subprocess.run(
            [YT_DLP, "--geo-bypass", "-f", "best", "-g", youtube_url],
            capture_output=True,
            text=True,
            timeout=YT_DLP_TIMEOUT
        )
        if result.returncode == 0:
            link = result.stdout.strip()
            if link and link.startswith("http"):
                return link
        return None
    except Exception:
        return None

def write_channel_file(kanal_dict):
    """Bulunan Google Manifest linkini kanalın kendi .m3u8 dosyasına yazar."""
    content = f"""#EXTM3U
#EXTINF:-1 tvg-name="{kanal_dict['name']}" http-user-agent="{USER_AGENT}",{kanal_dict['name']}
{kanal_dict['manifest_url']}
"""
    filepath = os.path.join(STREAMS_DIR, f"{kanal_dict['slug']}.m3u8")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

# -------------------- ANA PROGRAM --------------------
def main():
    os.makedirs(STREAMS_DIR, exist_ok=True)
    ana_m3u = "#EXTM3U\n"
    print("📡 Google Manifest canlı yayın linkleri toplanıyor...\n")

    for kanal in kanallar:
        print(f"➡️  {kanal['name']} ... ", end="", flush=True)
        
        # 1. Google Manifest linkini al
        link = get_live_url(kanal["youtube_url"])
        
        if link is None:
            print("❌ Başarısız")
            continue

        # 2. Bulunan linki sözlüğe dynamically aktar
        kanal["manifest_url"] = link

        # 3. Kanal dosyasını (streams/slug.m3u8) yaz
        write_channel_file(kanal)

        # 4. Ana playlist.m3u içeriğine ekle
        ana_m3u += f'#EXTINF:-1 tvg-name="{kanal["name"]}" group-title="Canlı" http-user-agent="{USER_AGENT}",{kanal["name"]}\n{kanal["manifest_url"]}\n'
        print("✅ OK")

    # Ana playlist.m3u dosyasını kaydet
    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(ana_m3u)

    print(f"\n📁 Tekil akış dosyaları '{STREAMS_DIR}/' klasörüne kaydedildi.")
    print(f"📁 Ana liste '{PLAYLIST_FILE}' dosyasına kaydedildi.")


if __name__ == "__main__":
    main()
