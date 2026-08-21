#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import subprocess
import requests
from flask import Flask, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler

# -------------------- AYARLAR & TIMEOUT DEĞERLERİ --------------------
BASE_STREAM_DIR = "hls_stream"
USER_AGENT = "VLC/3.0.20"

PROXY_API_TIMEOUT_MS = 2000    # ProxyScrape API max yanıt süresi (ms)
PROXY_TEST_TIMEOUT = 1.5       # Seçilen proxy'nin YouTube test süresi (sn)
STREAMLINK_TIMEOUT = "3"       # Streamlink'in takılı kalma sınırı (sn)
FLASK_FILE_WAIT_TIMEOUT = 5.0  # Flask'in master.m3u8 bekletme süresi (sn)

os.makedirs(BASE_STREAM_DIR, exist_ok=True)
app = Flask(__name__)

# -------------------- BİRLEŞİK KANAL LİSTESİ --------------------
kanallar = [
    # --- Doğrudan MPEG-TS Akışları ---
    {"slug": "trthaber", "name": "TRT Haber", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/trthaber"},
    {"slug": "cnnturk", "name": "CNN Turk", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/cnnturk"},
    {"slug": "ntv", "name": "NTV", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/ntv"},
    {"slug": "ahaber", "name": "A Haber", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/Ahaber"},
    {"slug": "haberturk", "name": "Haber Turk", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/haberturktv"},
    {"slug": "halktv", "name": "Halk TV", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/Halktvkanali"},
    {"slug": "sozcutelevizyonu", "name": "Sozcu TV", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/Sozcutelevizyonu_2"},
    {"slug": "tgrthaber", "name": "TGRT Haber", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/tgrthaber"},
    {"slug": "flashhaber", "name": "Flash Haber", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/FlashHaberTV"},
    {"slug": "haberglobal", "name": "Haber Global", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/haberglobal"},
    {"slug": "tv100", "name": "TV 100", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/tv100_2"},
    {"slug": "akittv", "name": "Akit TV", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/akittv"},
    {"slug": "bloomberght", "name": "Bloomberg HT", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/bloomberght"},
    {"slug": "benguturk", "name": "Bengu Turk", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/tvbenguturk"},
    {"slug": "diyanetcocuk", "name": "Bengu Turk", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/DiyanetCocuk"},
    {"slug": "ulusalkanal", "name": "Ulusal Kanal", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/ulusalkanalTV"},
    {"slug": "vavtv", "name": "Vav TV", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/vavtv_1"},
    {"slug": "ekoturk", "name": "Eko Turk", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/EKOTURKTV"},
    {"slug": "tv24", "name": "24 TV", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/YirmidortTV_1"},
    {"slug": "aspor", "name": "A Spor", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/ASpor"},
    {"slug": "htspor", "name": "HT Spor", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/htspor"},
    {"slug": "tvnet", "name": "TV Net", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/TVNET"},
    {"slug": "beinsportshaber", "name": "Bein Spor Haber", "type": "direct_ts", "url": "http://193.123.61.120:3000/kanal/beINSPORTSTurkiye"},
    {"slug": "cnbce", "name": "CNBC-e", "type": "direct_ts", "url": "193.123.61.120:3000/kanal/cnbce"}
]

active_processes = {}
CURRENT_WORKING_PROXY = None

# -------------------- PROXY İŞLEMLERİ --------------------
def get_working_tr_proxy():
    global CURRENT_WORKING_PROXY
    api = f"https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout={PROXY_API_TIMEOUT_MS}&country=TR&ssl=all&anonymity=all"
    try:
        resp = requests.get(api, timeout=3)
        if resp.status_code == 200:
            for proxy in resp.text.splitlines():
                if proxy.strip():
                    try:
                        requests.get("https://www.youtube.com", proxies={"http": f"http://{proxy}"}, timeout=PROXY_TEST_TIMEOUT)
                        CURRENT_WORKING_PROXY = f"http://{proxy}"
                        print(f"✅ Hızlı TR Proxy Atandı: {CURRENT_WORKING_PROXY}")
                        return
                    except: continue
    except: pass
    print("⚠️ Çalışan/Hızlı TR Proxy bulunamadı. Doğrudan bağlantı deneniyor.")
    CURRENT_WORKING_PROXY = None

# -------------------- YARDIMCI FONKSİYONLAR --------------------
def wait_for_file(filepath, timeout):
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return True
        time.sleep(0.1)
    return False

def stop_channel_process(slug):
    if slug in active_processes:
        procs = active_processes[slug]
        for p in procs:
            try: p.kill()
            except: pass
        del active_processes[slug]

def start_stream(kanal):
    slug = kanal["slug"]
    kanal_dir = os.path.join(BASE_STREAM_DIR, slug)
    os.makedirs(kanal_dir, exist_ok=True)
    
    stop_channel_process(slug)
    master_path = os.path.join(kanal_dir, "master.m3u8")
    if os.path.exists(master_path):
        try: os.remove(master_path)
        except: pass

    # --- SENARYO 1: DOĞRUDAN MPEG-TS (Tekil FFmpeg Süreci) ---
    if kanal.get("type") == "direct_ts":
        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-fflags", "nobuffer+fastseek",
            "-i", kanal["url"],
            "-c", "copy",
            "-f", "hls",
            "-hls_time", "2",
            "-hls_list_size", "5",
            "-hls_flags", "delete_segments+append_list",
            master_path
        ]
        p_ffmpeg = subprocess.Popen(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        active_processes[slug] = [p_ffmpeg]

    # --- SENARYO 2: YOUTUBE (Streamlink + FFmpeg Süreci) ---
    else:
        cmd_stream = [
            "streamlink", "--stdout",
            "--hls-live-edge", "1",
            "--stream-segment-threads", "3",
            "--retry-max", "1",
            "--http-timeout", STREAMLINK_TIMEOUT,
            "--http-header", f"User-Agent={USER_AGENT}"
        ]
        if CURRENT_WORKING_PROXY:
            cmd_stream.extend(["--http-proxy", CURRENT_WORKING_PROXY])
            
        cmd_stream.extend([kanal["url"], "best,720p,480p,worst"])

        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-fflags", "nobuffer+fastseek",
            "-probesize", "32768",
            "-analyzeduration", "0",
            "-i", "pipe:0",
            "-c", "copy",
            "-f", "hls",
            "-hls_time", "1.5",
            "-hls_init_time", "1",
            "-hls_list_size", "5",
            "-hls_flags", "delete_segments+append_list",
            master_path
        ]

        p1 = subprocess.Popen(cmd_stream, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        p2 = subprocess.Popen(cmd_ffmpeg, stdin=p1.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p1.stdout.close()
        active_processes[slug] = [p1, p2]

# -------------------- FLASK ROUTES --------------------
@app.route("/")
def index():
    return f"<h1>HLS Canlı Yayın Dönüştürücü</h1><p>Toplam Kanal Sayısı: {len(kanallar)}</p><a href='/playlist.m3u'>Playlist İndir (.m3u)</a>"

@app.route("/stream/<slug>/master.m3u8")
def handle_manifest(slug):
    kanal = next((k for k in kanallar if k["slug"] == slug), None)
    if not kanal: return "Kanal Bulunamadı", 404

    # Yayın çalışmıyorsa veya kapandıysa başlat
    if slug not in active_processes or active_processes[slug][-1].poll() is not None:
        start_stream(kanal)
    
    # 5 saniye içinde .m3u8 dosyasının yazılmasını bekle
    if wait_for_file(os.path.join(BASE_STREAM_DIR, slug, "master.m3u8"), timeout=FLASK_FILE_WAIT_TIMEOUT):
        return send_from_directory(os.path.join(BASE_STREAM_DIR, slug), "master.m3u8")
    
    return "Yayın Başlatılamadı (Timeout)", 500

@app.route("/stream/<slug>/<filename>")
def stream_ts(slug, filename):
    return send_from_directory(os.path.join(BASE_STREAM_DIR, slug), filename)

@app.route("/playlist.m3u")
def playlist():
    host = os.environ.get("SERVER_HOST", "http://127.0.0.1:10000")
    m3u = "#EXTM3U\n"
    for k in kanallar:
        m3u += f'#EXTINF:-1 tvg-name="{k["name"]}" group-title="Canlı Haber",{k["name"]}\n{host}/stream/{k["slug"]}/master.m3u8\n'
    return m3u, 200, {'Content-Type': 'application/x-mpegURL'}

# -------------------- BAŞLATMA --------------------
if __name__ == "__main__":
    get_working_tr_proxy()
    scheduler = BackgroundScheduler()
    scheduler.add_job(get_working_tr_proxy, "interval", hours=2)
    scheduler.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
