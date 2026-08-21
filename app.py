#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import subprocess
import requests
from flask import Flask, send_from_directory, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor

# -------------------- AYARLAR --------------------
BASE_STREAM_DIR = "hls_stream"
PLAYLIST_FILE = "playlist.m3u"
USER_AGENT = "VLC/3.0.20"

os.makedirs(BASE_STREAM_DIR, exist_ok=True)
app = Flask(__name__)

# Arka planda eşzamanlı kanal başlatma için Thread Pool
executor = ThreadPoolExecutor(max_workers=10)

# -------------------- KANAL LİSTESİ (23 KANAL) --------------------
kanallar = [
    {"slug": "trthaber", "name": "TRT Haber", "url": "https://www.youtube.com/@trthaber/live"},
    {"slug": "cnnturk", "name": "CNN Turk", "url": "https://www.youtube.com/@cnnturk/live"},
    {"slug": "ntv", "name": "NTV", "url": "https://www.youtube.com/@ntv/live"},
    {"slug": "ahaber", "name": "A Haber", "url": "https://www.youtube.com/@Ahaber/live"},
    {"slug": "haberturk", "name": "Haber Turk", "url": "https://www.youtube.com/@haberturktv/live"},
    {"slug": "halktv", "name": "Halk TV", "url": "https://www.youtube.com/@Halktvkanali/live"},
    {"slug": "sozcutelevizyonu", "name": "Sozcu TV", "url": "https://www.youtube.com/watch?v=ztmY_cCtUl0"},
    {"slug": "tgrthaber", "name": "TGRT Haber", "url": "https://www.youtube.com/@tgrthaber/live"},
    {"slug": "flashhaber", "name": "Flash Haber", "url": "https://www.youtube.com/@flashhabertv/live"},
    {"slug": "haberglobal", "name": "Haber Global", "url": "https://www.youtube.com/@haberglobal/live"},
    {"slug": "tv100", "name": "TV 100", "url": "https://www.youtube.com/@tv100/live"},
    {"slug": "akittv", "name": "Akit TV", "url": "https://www.youtube.com/@akittv/live"},
    {"slug": "bloomberght", "name": "Bloomberg HT", "url": "https://www.youtube.com/@bloomberght/live"},
    {"slug": "benguturk", "name": "Bengu Turk", "url": "https://www.youtube.com/@tvbenguturk/live"},
    {"slug": "diyanetcocuk", "name": "Diyanet Çocuk", "url": "https://www.youtube.com/watch?v=_VsMIRdOtXI"},
    {"slug": "krttv", "name": "KRT TV", "url": "https://www.youtube.com/@krtcanli/live"},
    {"slug": "ulusalkanal", "name": "Ulusal Kanal", "url": "https://www.youtube.com/@ulusalkanaltv/live"},
    {"slug": "ulketv", "name": "Ulke TV", "url": "https://www.youtube.com/@ulketv/live"},
    {"slug": "vavtv", "name": "Vav TV", "url": "https://www.youtube.com/@vavtv/live"},
    {"slug": "bizimevtv", "name": "Bizimev TV", "url": "https://www.youtube.com/@bizimevtv2000/live"},
    {"slug": "ekoturk", "name": "Eko Turk", "url": "https://www.youtube.com/@ekoturktv/live"},
    {"slug": "tv24", "name": "24 TV", "url": "https://www.youtube.com/@YirmidortTV/live"},
    {"slug": "aspor", "name": "A Spor", "url": "https://www.youtube.com/@aspor/live"},
    {"slug": "htspor", "name": "HT Spor", "url": "https://www.youtube.com/@htspor/live"},
    {"slug": "tvnet", "name": "TV Net", "url": "https://www.youtube.com/@tvnet/live"},
    {"slug": "beinsportshaber", "name": "Bein Spor Haber", "url": "https://www.youtube.com/@beINSPORTSTurkiye/live"},
    {"slug": "cnbce", "name": "CNBC-e", "url": "https://www.youtube.com/@cnbce/live"}
]

active_processes = {}
CURRENT_WORKING_PROXY = None

# -------------------- AKILLI TR PROXY TARAYICI --------------------
def get_working_tr_proxy():
    """ProxyScrape'den TR proxylerini indirir ve YouTube'a bağlanan ilk çalışan proxy'yi seçer."""
    global CURRENT_WORKING_PROXY
    api_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=3000&country=TR&ssl=all&anonymity=all"
    
    print("🌐 [Proxy Worker] ProxyScrape üzerinden TR Proxy aranıyor...")
    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 200:
            proxy_list = [line.strip() for line in resp.text.splitlines() if line.strip()]
            
            for proxy in proxy_list:
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                try:
                    r = requests.get("https://www.youtube.com", proxies=proxies, headers=headers, timeout=4)
                    if r.status_code == 200:
                        print(f"✅ [Proxy Worker] Çalışan TR Proxy Seçildi: {proxy}")
                        CURRENT_WORKING_PROXY = f"http://{proxy}"
                        return CURRENT_WORKING_PROXY
                except Exception:
                    continue
    except Exception as e:
        print(f"⚠️ [Proxy Worker] ProxyScrape hatası: {e}")
        
    print("⚠️ [Proxy Worker] Çalışan TR Proxy bulunamadı. Doğrudan bağlantı kullanılacak.")
    CURRENT_WORKING_PROXY = None
    return None

# -------------------- HIZLANDIRILMIŞ YAYIN MOTORU --------------------
def start_single_channel_stream(kanal):
    """Tekli kanal için optimize edilmiş Streamlink + FFmpeg borusunu başlatır."""
    slug = kanal["slug"]
    target_url = kanal["url"]
    
    kanal_dir = os.path.join(BASE_STREAM_DIR, slug)
    os.makedirs(kanal_dir, exist_ok=True)
    output_m3u8 = os.path.join(kanal_dir, "master.m3u8")

    # Fast-start Streamlink Ayarları
    streamlink_cmd = [
        "streamlink",
        "--stdout",
        "--stream-segment-threads", "3",
        "--retry-open", "1",
        "--http-timeout", "5",
        "--http-header", "User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "--http-header", "Accept-Language=tr-TR,tr;q=0.9,en-US;q=0.8"
    ]
    
    if CURRENT_WORKING_PROXY:
        streamlink_cmd.extend(["--http-proxy", CURRENT_WORKING_PROXY])
        
    streamlink_cmd.extend([target_url, "best,720p,480p,worst"])

    # Fast-probesize FFmpeg Ayarları (Anında HLS segment üretimi için)
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-probesize", "32768",
        "-analyzeduration", "0",
        "-i", "pipe:0",
        "-c:v", "copy",
        "-c:a", "copy",
        "-f", "hls",
        "-hls_time", "4",
        "-hls_list_size", "10",
        "-hls_flags", "delete_segments+append_list",
        output_m3u8
    ]

    try:
        p1 = subprocess.Popen(streamlink_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        p2 = subprocess.Popen(ffmpeg_cmd, stdin=p1.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p1.stdout.close()
        
        active_processes[slug] = (p1, p2)
        return True
    except Exception as e:
        print(f"Kanal Başlatma Hatası ({slug}): {e}")
        return False

def _async_start_worker(kanal):
    """Arka plan thread havuzu için yardımcı fonksiyon."""
    slug = kanal["slug"]
    if slug not in active_processes or active_processes[slug][0].poll() is not None:
        start_single_channel_stream(kanal)

# -------------------- 3 SAATTE BİR TETİKLENEN SCHEDULER --------------------
def periodic_refresh_job():
    """Her 3 saatte bir çalışan proxy ve yayın yenileme temizlik fonksiyonu."""
    print("⏰ [3 Saatlik Zamanlayıcı] Proxy güncelleniyor ve eski süreçler temizleniyor...")
    
    get_working_tr_proxy()
    
    for slug, (p1, p2) in list(active_processes.items()):
        try:
            if p1 and p1.poll() is None: p1.kill()
            if p2 and p2.poll() is None: p2.kill()
        except Exception:
            pass
    active_processes.clear()
    print("✅ [3 Saatlik Zamanlayıcı] Yenileme ve temizlik tamamlandı.")

scheduler = BackgroundScheduler()
scheduler.add_job(func=periodic_refresh_job, trigger="interval", hours=3)
scheduler.start()

# -------------------- FLASK ENDPOINTLERİ --------------------
@app.route("/")
def index():
    return f"<h1>YouTube HLS Proxy Servisi</h1><p>Toplam Kanal: {len(kanallar)}</p><p>UptimeRobot Ping Sayfasıdır.</p><p>Playlist URL: <a href='/playlist.m3u'>/playlist.m3u</a></p>"

@app.route("/start-all")
def start_all():
    """Tüm kanalları arka planda PARALEL (asenkron) olarak instant başlatır."""
    for kanal in kanallar:
        executor.submit(_async_start_worker, kanal)
        
    return jsonify({
        "status": "success",
        "message": f"Tüm {len(kanallar)} kanal arka planda eşzamanlı olarak başlatılıyor."
    })

@app.route("/stream/<slug>/master.m3u8")
def handle_manifest(slug):
    """İstemci yayını açmak istediğinde çalışır (On-Demand)."""
    kanal = next((k for k in kanallar if k["slug"] == slug), None)
    if not kanal:
        return "Kanal Bulunamadı", 404

    if slug not in active_processes or active_processes[slug][0].poll() is not None:
        print(f"🎬 {kanal['name']} için izleme isteği geldi. Yayın başlatılıyor...")
        start_single_channel_stream(kanal)
        time.sleep(30)

    kanal_dir = os.path.join(BASE_STREAM_DIR, slug)
    return send_from_directory(kanal_dir, "master.m3u8")

@app.route("/stream/<slug>/<filename>")
def stream_ts_files(slug, filename):
    """.ts segmentlerini servis eder."""
    kanal_dir = os.path.join(BASE_STREAM_DIR, slug)
    return send_from_directory(kanal_dir, filename)

@app.route("/playlist.m3u")
def playlist():
    """Tüm kanalların M3U oynatma listesini üretir."""
    host = os.environ.get("SERVER_HOST", "http://127.0.0.1:10000")
    m3u_content = "#EXTM3U\n"
    for kanal in kanallar:
        stream_url = f"{host}/stream/{kanal['slug']}/master.m3u8"
        m3u_content += f'#EXTINF:-1 tvg-name="{kanal["name"]}" group-title="Canlı Haber" http-user-agent="{USER_AGENT}",{kanal["name"]}\n{stream_url}\n'
    return m3u_content, 200, {'Content-Type': 'application/x-mpegURL'}

# -------------------- ÇALIŞTIRMA --------------------
if __name__ == "__main__":
    get_working_tr_proxy()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
