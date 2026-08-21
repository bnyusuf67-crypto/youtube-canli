#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import subprocess
import requests
from flask import Flask, send_from_directory, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

# -------------------- AYARLAR --------------------
BASE_STREAM_DIR = "hls_stream"
USER_AGENT = "VLC/3.0.20"
os.makedirs(BASE_STREAM_DIR, exist_ok=True)
app = Flask(__name__)

# -------------------- KANAL LİSTESİ --------------------
kanallar = [
    {"slug": "trthaber", "name": "TRT Haber", "url": "https://www.youtube.com/@trthaber/live"},
    {"slug": "cnnturk", "name": "CNN Turk", "url": "https://www.youtube.com/@cnnturk/live"},
    {"slug": "ntv", "name": "NTV", "url": "https://www.youtube.com/@ntv/live"},
    {"slug": "ahaber", "name": "A Haber", "url": "https://www.youtube.com/@Ahaber/live"},
    {"slug": "haberturk", "name": "Haber Turk", "url": "https://www.youtube.com/@haberturktv/live"},
    {"slug": "halktv", "name": "Halk TV", "url": "https://www.youtube.com/@Halktvkanali/live"},
    {"slug": "sozcutelevizyonu", "name": "Sozcu TV", "url": "https://www.youtube.com/@sozcutelevizyonu/live"},
    {"slug": "tgrthaber", "name": "TGRT Haber", "url": "https://www.youtube.com/@tgrthaber/live"},
    {"slug": "flashhaber", "name": "Flash Haber", "url": "https://www.youtube.com/@flashhabertv/live"},
    {"slug": "haberglobal", "name": "Haber Global", "url": "https://www.youtube.com/@haberglobal/live"},
    {"slug": "tv100", "name": "TV 100", "url": "https://www.youtube.com/@tv100/live"},
    {"slug": "bloomberght", "name": "Bloomberg HT", "url": "https://www.youtube.com/@bloomberght/live"},
    {"slug": "benguturk", "name": "Bengu Turk", "url": "https://www.youtube.com/@tvbenguturk/live"},
    {"slug": "krttv", "name": "KRT TV", "url": "https://www.youtube.com/@krtcanli/live"},
    {"slug": "ulusalkanal", "name": "Ulusal Kanal", "url": "https://www.youtube.com/@ulusalkanaltv/live"},
    {"slug": "ulketv", "name": "Ulke TV", "url": "https://www.youtube.com/@ulketv/live"},
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

# -------------------- YARDIMCI FONKSİYONLAR --------------------
def get_working_tr_proxy():
    global CURRENT_WORKING_PROXY
    api = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=8000&country=TR&ssl=all&anonymity=all"
    try:
        resp = requests.get(api, timeout=10)
        if resp.status_code == 200:
            for proxy in resp.text.splitlines():
                if proxy.strip():
                    try:
                        requests.get("https://www.youtube.com", proxies={"http": f"http://{proxy}"}, timeout=3)
                        CURRENT_WORKING_PROXY = f"http://{proxy}"
                        return
                    except: continue
    except: pass
    CURRENT_WORKING_PROXY = None

def wait_for_file(filepath, timeout=4.0):
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(filepath): return True
        time.sleep(0.2)
    return False

def start_stream(kanal):
    slug = kanal["slug"]
    kanal_dir = os.path.join(BASE_STREAM_DIR, slug)
    os.makedirs(kanal_dir, exist_ok=True)
    
    # Eskileri temizle
    if os.path.exists(os.path.join(kanal_dir, "master.m3u8")):
        os.remove(os.path.join(kanal_dir, "master.m3u8"))

    cmd_stream = ["streamlink", "--stdout", "--hls-live-edge", "1", "--stream-segment-threads", "3"]
    if CURRENT_WORKING_PROXY: cmd_stream.extend(["--http-proxy", CURRENT_WORKING_PROXY])
    cmd_stream.extend([kanal["url"], "best"])

    cmd_ffmpeg = [
        "ffmpeg", "-y", "-fflags", "nobuffer+fastseek", "-probesize", "32768", "-analyzeduration", "0",
        "-i", "pipe:0", "-c", "copy", "-f", "hls", "-hls_time", "1.5", "-hls_init_time", "1", 
        "-hls_list_size", "6", "-hls_flags", "delete_segments+append_list", 
        os.path.join(kanal_dir, "master.m3u8")
    ]
    
    p1 = subprocess.Popen(cmd_stream, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    p2 = subprocess.Popen(cmd_ffmpeg, stdin=p1.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p1.stdout.close()
    active_processes[slug] = (p1, p2)

# -------------------- ROUTES --------------------
@app.route("/")
def index():
    return f"<h1>YouTube HLS Yayın Servisi</h1><p>Toplam {len(kanallar)} kanal mevcut.</p><a href='/playlist.m3u'>Playlist İndir</a>"

@app.route("/stream/<slug>/master.m3u8")
def handle_manifest(slug):
    kanal = next((k for k in kanallar if k["slug"] == slug), None)
    if not kanal: return "Kanal Bulunamadı", 404

    # Çalışmıyorsa başlat
    if slug not in active_processes or active_processes[slug][0].poll() is not None:
        start_stream(kanal)
    
    # 4 saniye içinde dosyanın oluşmasını bekle
    if wait_for_file(os.path.join(BASE_STREAM_DIR, slug, "master.m3u8")):
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
        m3u += f'#EXTINF:-1,{k["name"]}\n{host}/stream/{k["slug"]}/master.m3u8\n'
    return m3u, 200, {'Content-Type': 'application/x-mpegURL'}

if __name__ == "__main__":
    get_working_tr_proxy()
    scheduler = BackgroundScheduler()
    scheduler.add_job(get_working_tr_proxy, "interval", hours=3)
    scheduler.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
