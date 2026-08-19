import os
import logging
import subprocess
import threading
import time
from flask import Flask, jsonify, redirect, request, Response

# UTF-8 Encoding
os.environ["PYTHONIOENCODING"] = "utf-8"

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -------------------------------------------------------------
# BİRLEŞİK KANAL LİSTESİ & GLOBAL CACHE
# -------------------------------------------------------------
CHANNELS = [
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
    {"slug": "diyanetcocuk", "name": "Diyanet Çocuk", "url": "https://m.youtube.com/watch?v=_VsMIRdOtXI"},
    {"slug": "krttv", "name": "KRT TV", "url": "https://www.youtube.com/@krtcanli/live"},
    {"slug": "ulusalkanal", "name": "Ulusal Kanal", "url": "https://www.youtube.com/@ulusalkanaltv/live"},
    {"slug": "ulketv", "name": "Ulke TV", "url": "https://www.youtube.com/@ulketv/live"},
    {"slug": "vavtv", "name": "Vav TV", "url": "https://m.youtube.com/@vavtv/live"},
    {"slug": "ekoturk", "name": "Eko Turk", "url": "https://www.youtube.com/@ekoturktv/live"},
    {"slug": "tv24", "name": "24 TV", "url": "https://www.youtube.com/@YirmidortTV/live"},
    {"slug": "aspor", "name": "A Spor", "url": "https://www.youtube.com/@aspor/live"},
    {"slug": "htspor", "name": "HT Spor", "url": "https://www.youtube.com/@htspor/live"},
    {"slug": "tvnet", "name": "TV Net", "url": "https://www.youtube.com/@tvnet/live"},
    {"slug": "beinsportshaber", "name": "Bein Spor Haber", "url": "https://www.youtube.com/@beINSPORTSTurkiye/live"},
    {"slug": "cnbce", "name": "CNBC-e", "url": "https://www.youtube.com/@cnbce/live"}
]

# Önbellek ve Durum Kilidi
URL_CACHE = {}
IS_UPDATING = False
LAST_UPDATE_TIME = 0

def get_stream_m3u8(source_url):
    """Streamlink ile YouTube canlı yayınının M3U8 bağlantısını çözer."""
    cmd = [
        "streamlink",
        "--stream-url",
        "--http-timeout", "25",
        "--retry-streams", "2",
        source_url,
        "best"
    ]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=30)
        
        if process.returncode == 0:
            direct_url = stdout.decode("utf-8").strip()
            if direct_url.startswith("http"):
                return direct_url
                
        logging.error(f"[STREAMLINK ERROR] {stderr.decode('utf-8', errors='replace')}")
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        logging.error(f"[TIMEOUT] {source_url} zaman aşımına uğradı.")
    except Exception as e:
        logging.error(f"[EXCEPTION] {e}")
    return None

# -------------------------------------------------------------
# ARKA PLAN GÜNCELLEME SÜRECİ
# -------------------------------------------------------------
def run_update_process():
    """Tüm kanalları sırayla tarar ve URL_CACHE sözlüğünü günceller."""
    global IS_UPDATING, LAST_UPDATE_TIME
    if IS_UPDATING:
        logging.info("[UPDATE] Zaten devam eden bir güncelleme var, atlanıyor.")
        return

    IS_UPDATING = True
    logging.info("[UPDATE START] Kanal güncelleme süreci başladı...")

    for ch in CHANNELS:
        slug = ch["slug"]
        logging.info(f"[RESOLVING] {ch['name']} ({slug})...")
        real_url = get_stream_m3u8(ch["url"])
        if real_url:
            URL_CACHE[slug] = real_url
            logging.info(f"[SUCCESS] {slug} -> Önbelleğe eklendi.")
        else:
            logging.warning(f"[FAILED] {slug} çözülemedi.")
        
        time.sleep(1)

    LAST_UPDATE_TIME = time.time()
    IS_UPDATING = False
    logging.info("[UPDATE END] Tüm kanallar güncellendi.")

def scheduled_worker():
    """Render portuna bağlanabilmek için 15sn bekler, ardından 3 saatte bir çalışır."""
    time.sleep(15)
    run_update_process()
    
    while True:
        time.sleep(3 * 3600)  # 3 Saat
        run_update_process()

# Arka plan thread'ini başlat
bg_thread = threading.Thread(target=scheduled_worker, daemon=True)
bg_thread.start()

# -------------------------------------------------------------
# ENDPOINT'LER
# -------------------------------------------------------------

@app.route("/start", methods=["GET"])
def manual_start():
    if IS_UPDATING:
        return jsonify({
            "status": "warning",
            "message": "Güncelleme süreci zaten arka planda devam ediyor."
        }), 200

    threading.Thread(target=run_update_process, daemon=True).start()
    
    return jsonify({
        "status": "success",
        "message": "Kanal güncelleme işlemi arka planda başlatıldı."
    }), 200

@app.route("/live/<channel_slug>.m3u8", methods=["GET"])
def get_channel_m3u8(channel_slug):
    clean_slug = channel_slug.lower().replace(".m3u8", "")
    
    channel = next((c for c in CHANNELS if c["slug"].lower() == clean_slug), None)
    if not channel:
        return jsonify({"error": f"'{clean_slug}' kanalı bulunamadı."}), 404

    cached_url = URL_CACHE.get(clean_slug)
    if cached_url:
        logging.info(f"[REDIRECT-CACHE] -> {clean_slug}")
        return redirect(cached_url, code=302)

    logging.info(f"[CACHE MISS] {clean_slug} anlık çözülüyor...")
    real_m3u8_url = get_stream_m3u8(channel["url"])

    if real_m3u8_url:
        URL_CACHE[clean_slug] = real_m3u8_url
        return redirect(real_m3u8_url, code=302)

    return jsonify({"error": f"'{channel['name']}' yayını şu anda çözülemiyor."}), 500

@app.route("/channels", methods=["GET"])
def list_channels():
    base_url = request.host_url.rstrip("/")
    response_data = []
    for ch in CHANNELS:
        slug = ch["slug"]
        response_data.append({
            "slug": slug,
            "name": ch["name"],
            "m3u8_url": f"{base_url}/live/{slug}.m3u8",
            "cached": slug in URL_CACHE
        })
    return jsonify({
        "is_updating": IS_UPDATING,
        "total_channels": len(CHANNELS),
        "cached_channels": len(URL_CACHE),
        "channels": response_data
    })

@app.route("/playlist.m3u", methods=["GET"])
def playlist():
    base_url = request.host_url.rstrip("/")
    m3u_content = "#EXTM3U\n"
    for ch in CHANNELS:
        stream_link = f"{base_url}/live/{ch['slug']}.m3u8"
        m3u_content += f'#EXTINF:-1 tvg-id="{ch["slug"]}" tvg-name="{ch["name"]}",{ch["name"]}\n{stream_link}\n'
    
    return Response(m3u_content, content_type="audio/x-mpegurl")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "is_updating": IS_UPDATING,
        "cached_count": len(URL_CACHE),
        "last_update": LAST_UPDATE_TIME
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6095))
    app.run(host="0.0.0.0", port=port, threaded=True)
