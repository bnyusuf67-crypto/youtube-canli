#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import shutil
from datetime import datetime

# -------------------- KANAL LİSTESİ --------------------
kanallar = [
    ("trthaber", "TRT Haber", "https://www.youtube.com/@trthaber/live"),
    ("cnnturk", "CNN Turk", "https://www.youtube.com/@cnnturk/live"),
    ("ntv", "NTV", "https://www.youtube.com/@ntv/live"),
    ("ahaber", "A Haber", "https://www.youtube.com/@Ahaber/live"),
    ("haberturk", "Haber Turk", "https://www.youtube.com/@haberturktv/live"),
    ("halktv", "Halk TV", "https://www.youtube.com/@Halktvkanali/live"),
    ("sozcutelevizyonu", "Sozcu TV", "https://www.youtube.com/@sozcutelevizyonu/live"),
    ("tgrthaber", "TGRT Haber", "https://www.youtube.com/@tgrthaber/live"),
    ("flashhaber", "Flash Haber", "https://www.youtube.com/@flashhabertv/live"),
    ("haberglobal", "Haber Global", "https://www.youtube.com/@haberglobal/live"),
    ("tv100", "TV 100", "https://www.youtube.com/@tv100/live"),
    ("bloomberght", "Bloomberg HT", "https://www.youtube.com/@bloomberght/live"),
    ("benguturk", "Bengu Turk", "https://www.youtube.com/@tvbenguturk/live"),
    ("krttv", "KRT TV", "https://www.youtube.com/@krtcanli/live"),
    ("ulusalkanal", "Ulusal Kanal", "https://www.youtube.com/@ulusalkanaltv/live"),
    ("ulketv", "Ulke TV", "https://www.youtube.com/@ulketv/live"),
    ("ekoturk", "Eko Turk", "https://www.youtube.com/@ekoturktv/live"),
    ("tv24", "24 TV", "https://www.youtube.com/@YirmidortTV/live"),
    ("aspor", "A Spor", "https://www.youtube.com/@aspor/live"),
    ("htspor", "HT Spor", "https://www.youtube.com/@htspor/live"),
    ("tvnet", "TV Net", "https://www.youtube.com/@tvnet/live"),
    ("beinsportshaber", "Bein Spor Haber", "https://www.youtube.com/@beINSPORTSTurkiye/live"),
    ("cnbce", "CNBC-e", "https://www.youtube.com/@cnbce/live")
]

# -------------------- AYARLAR --------------------
STREAMS_DIR = "streams"
PLAYLIST_FILE = "playlist.m3u"
USER_AGENT = "VLC/3.0.20"
YT_DLP_TIMEOUT = 30  # saniye

# yt-dlp yolunu bul
YT_DLP = shutil.which("yt-dlp")
if not YT_DLP:
    print("❌ yt-dlp bulunamadı! Lütfen yt-dlp'yi kurun: pip install yt-dlp")
    sys.exit(1)

# -------------------- FONKSİYONLAR --------------------
def get_live_url(youtube_url):
    """YouTube canlı yayın URL'sini alır."""
    try:
        result = subprocess.run(
            [YT_DLP, "-f", "best", "-g", youtube_url],
            capture_output=True,
            text=True,
            timeout=YT_DLP_TIMEOUT
        )
        if result.returncode != 0:
            return None, f"yt-dlp çıkış kodu {result.returncode}: {result.stderr.strip()}"
        link = result.stdout.strip()
        if not link or not link.startswith("http"):
            return None, f"Geçersiz link: {link}"
        return link, None
    except subprocess.TimeoutExpired:
        return None, "Zaman aşımı"
    except Exception as e:
        return None, str(e)

def write_channel_file(slug, name, url):
    """Her kanal için ayrı .m3u8 dosyası oluşturur."""
    content = f"""#EXTM3U
#EXTINF:-1 tvg-name="{name}" http-user-agent="{USER_AGENT}",{name}
{url}
"""
    filepath = os.path.join(STREAMS_DIR, f"{slug}.m3u8")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

# -------------------- ANA PROGRAM --------------------
def main():
    os.makedirs(STREAMS_DIR, exist_ok=True)
    ana_m3u = "#EXTM3U\n"
    print("📡 Kanal linkleri toplanıyor...\n")

    for slug, isim, url in kanallar:
        print(f"➡️  {isim} ... ", end="", flush=True)
        link, hata = get_live_url(url)
        if link is None:
            print(f"❌ {hata}")
            continue

        # Dosyayı yaz
        write_channel_file(slug, isim, link)

        # Ana playlist'e ekle
        ana_m3u += f'#EXTINF:-1 tvg-name="{isim}" group-title="Canlı" http-user-agent="{USER_AGENT}",{isim}\n{link}\n'
        print("✅ OK")

    # Ana playlist'i kaydet
    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(ana_m3u)

    print(f"\n📁 Dosyalar '{STREAMS_DIR}/' klasörüne ve '{PLAYLIST_FILE}' dosyasına kaydedildi.")


if __name__ == "__main__":
    main()
