import os
import re
import time
import logging
import threading
import subprocess
import requests
from flask import Flask, jsonify, redirect, request, Response

os.environ["PYTHONIOENCODING"] = "utf-8"

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8"
})

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

URL_CACHE = {}
IS_UPDATING = False
LAST_UPDATE_TIME = 0

def resolve_video_id(source_url):
    """Bulut sunucu engelini aşarak videoId çeker."""
    match = re.search(r'(?:v=|\/embed\/|\/v\/|youtu\.be\/|\/shorts\/)([a-zA-Z0-9_-]{11})', source_url)
    if match:
        return match.group(1)

    try:
        res = session.get(source_url, timeout=4, allow_redirects=True)
        if res.status_code == 200:
            patterns = [
                r'"videoId":"([a-zA-Z0-9_-]{11})"',
                r'watch\?v=([a-zA-Z0-9_-]{11})',
                r'canonical" href="https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]{11})"'
            ]
            for pat in patterns:
                m = re.search(pat, res.text)
                if m:
                    return m.group(1)
    except Exception as e:
        logging.warning(f"[ID FETCH FAIL] {source_url}: {e}")

    return None

def is_valid_m3u8(url):
    """Linkin gerçek bir HLS / M3U8 yayını olup olmadığını doğrular."""
    if not url or not isinstance(url, str):
        return False
    if "youtube.com/watch" in url or "youtu.be" in url:
        return False
    return "googlevideo.com" in url or ".m3u8" in url or "manifest" in url

def get_stream_m3u8(source_url):
    video_id = resolve_video_id(source_url)

    # --- 1. AŞAMA: InnerTube API (Embedded & TV Clients) ---
    if video_id:
        innertube_url = "https://www.youtube.com/youtubei/v1/player"
        clients = [
            {
                "name": "WEB_EMBEDDED_PLAYER",
                "payload": {
                    "videoId": video_id,
                    "context": {"client": {"clientName": "WEB_EMBEDDED_PLAYER", "clientVersion": "5.20240308.01.00", "hl": "tr", "gl": "TR"}}
                }
            },
            {
                "name": "TVHTML5_SIMPLY_EMBEDDED_PLAYER",
                "payload": {
                    "videoId": video_id,
                    "context": {"client": {"clientName": "TVHTML5_SIMPLY_EMBEDDED_PLAYER", "clientVersion": "2.0", "hl": "tr", "gl": "TR"}}
                }
            },
            {
                "name": "ANDROID_VR",
                "payload": {
                    "videoId": video_id,
                    "context": {"client": {"clientName": "ANDROID_VR", "clientVersion": "1.52.18", "hl": "tr", "gl": "TR"}}
                }
            }
        ]

        for target_client in clients:
            try:
                api_res = session.post(innertube_url, json=target_client["payload"], timeout=4)
                if api_res.status_code == 200:
                    data = api_res.json()
                    hls_url = data.get("streamingData", {}).get("hlsManifestUrl")
                    if hls_url and is_valid_m3u8(hls_url):
                        logging.info(f"[INNERTUBE SUCCESS ({target_client['name']})] -> {video_id}")
                        return hls_url
            except Exception as e:
                logging.warning(f"[INNERTUBE {target_client['name']} FAIL] {e}")

    # --- 2. AŞAMA: yt-dlp (Sıkı URL Filtrelemeli) ---
    target_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else source_url
    logging.info(f"[FALLBACK TO YT-DLP] {target_url} deneniyor...")
    try:
        ytdlp_cmd = [
            "yt-dlp",
            "-g",
            "-f", "best",
            "--extractor-args", "youtube:player_client=web_embedded,tv",
            "--socket-timeout", "8",
            target_url
        ]
        process = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _ = process.communicate(timeout=10)
        if process.returncode == 0:
            lines = stdout.decode("utf-8").strip().split('\n')
            for line in lines:
                candidate = line.strip()
                if is_valid_m3u8(candidate):
                    logging.info(f"[YT-DLP SUCCESS] -> {candidate[:60]}...")
                    return candidate
    except Exception as e:
        logging.warning(f"[YT-DLP FAIL] {target_url}: {e}")

    # --- 3. AŞAMA: Streamlink ---
    logging.info(f"[FALLBACK TO STREAMLINK] {target_url} deneniyor...")
    try:
        streamlink_cmd = [
            "streamlink",
            "--stream-url",
            "--http-timeout", "10",
            target_url,
            "best"
        ]
        process = subprocess.Popen(streamlink_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _ = process.communicate(timeout=12)
        if process.returncode == 0:
            candidate = stdout.decode("utf-8").strip()
            if is_valid_m3u8(candidate):
                logging.info(f"[STREAMLINK SUCCESS] -> {candidate[:60]}...")
                return candidate
    except Exception as e:
        logging.error(f"[STREAMLINK FAIL] {target_url}: {e}")

    return None

def run_update_process():
    global IS_UPDATING, LAST_UPDATE_TIME
    if IS_UPDATING:
        logging.info("[UPDATE] Zaten devam eden bir güncelleme var, atlanıyor.")
        return

    IS_UPDATING = True
    logging.info("[UPDATE START] Kanal güncellemesi başladı...")

    for ch in CHANNELS:
        slug = ch["slug"]
        logging.info(f"[RESOLVING] {ch['name']} ({slug})...")
        real_url = get_stream_m3u8(ch["url"])
        if real_url:
            URL_CACHE[slug] = real_url
            logging.info(f"[SUCCESS] {slug} -> Önbelleğe eklendi.")
        else:
            logging.warning(f"[FAILED] {slug} çözülemedi.")

    LAST_UPDATE_TIME = time.time()
    IS_UPDATING = False
    logging.info("[UPDATE END] Tüm kanallar güncellendi.")

def scheduled_worker():
    time.sleep(5)
    run_update_process()
    while True:
        time.sleep(3 * 3600)

bg_thread = threading.Thread(target=scheduled_worker, daemon=True)
bg_thread.start()

@app.route("/start", methods=["GET"])
def manual_start():
    if IS_UPDATING:
        return jsonify({"status": "warning", "message": "Güncelleme zaten devam ediyor."}), 200
    threading.Thread(target=run_update_process, daemon=True).start()
    return jsonify({"status": "success", "message": "Güncelleme başlatıldı."}), 200

@app.route("/live/<channel_slug>.m3u8", methods=["GET"])
def get_channel_m3u8(channel_slug):
    clean_slug = channel_slug.lower().replace(".m3u8", "")
    channel = next((c for c in CHANNELS if c["slug"].lower() == clean_slug), None)
    if not channel:
        return jsonify({"error": f"'{clean_slug}' kanalı bulunamadı."}), 404

    cached_url = URL_CACHE.get(clean_slug)
    if cached_url:
        return redirect(cached_url, code=302)

    real_m3u8_url = get_stream_m3u8(channel["url"])
    if real_m3u8_url and is_valid_m3u8(real_m3u8_url):
        URL_CACHE[clean_slug] = real_m3u8_url
        return redirect(real_m3u8_url, code=302)

    return jsonify({"error": f"'{channel['name']}' yayını çözülemedi."}), 500

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
