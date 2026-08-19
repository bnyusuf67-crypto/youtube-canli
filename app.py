import os
import re
import time
import logging
import threading
import subprocess
import requests
from flask import Flask, jsonify, redirect, request, Response

# UTF-8 Encoding
os.environ["PYTHONIOENCODING"] = "utf-8"

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# HTTP Oturumu
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8"
})

CHANNELS = [
    {"slug": "trthaber", "name": "TRT Haber", "url": "https://www.youtube.com/@trthaber/live"},
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
    """YouTube bulut IP engeline takılmadan videoId tespiti yapar."""
    # 1. URL'de video ID varsa
    match = re.search(r'(?:v=|\/embed\/|\/v\/|youtu\.be\/|\/shorts\/)([a-zA-Z0-9_-]{11})', source_url)
    if match:
        return match.group(1)

    # 2. Piped API üzerinden sorgula (Datacenter IP Korumasız)
    try:
        channel_name = source_url.split("@")[-1].replace("/live", "").strip()
        piped_res = session.get(f"https://pipedapi.kavin.rocks/channels/name/{channel_name}", timeout=4)
        if piped_res.status_code == 200:
            data = piped_res.json()
            # En güncel canlı yayını bul
            for item in data.get("relatedStreams", []):
                if item.get("isLive", False):
                    v_id = item.get("url", "").replace("/watch?v=", "")
                    if len(v_id) == 11:
                        logging.info(f"[PIPED SUCCESS] {channel_name} -> {v_id}")
                        return v_id
    except Exception as e:
        logging.warning(f"[PIPED FAIL] {source_url}: {e}")

    # 3. Invidious API Fallback
    try:
        channel_name = source_url.split("@")[-1].replace("/live", "").strip()
        inv_res = session.get(f"https://inv.tux.pizza/api/v1/channels/{channel_name}/search?q=live", timeout=4)
        if inv_res.status_code == 200:
            data = inv_res.json()
            if len(data) > 0 and "videoId" in data[0]:
                logging.info(f"[INVIDIOUS SUCCESS] {channel_name} -> {data[0]['videoId']}")
                return data[0]["videoId"]
    except Exception as e:
        logging.warning(f"[INVIDIOUS FAIL] {source_url}: {e}")

    # 4. Doğrudan YouTube HTML
    try:
        res = session.get(source_url, timeout=4, allow_redirects=True)
        if res.status_code == 200:
            patterns = [
                r'"videoId":"([a-zA-Z0-9_-]{11})"',
                r'href="https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]{11})"',
                r'link rel="canonical" href="https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]{11})"'
            ]
            for pat in patterns:
                m = re.search(pat, res.text)
                if m:
                    return m.group(1)
    except Exception:
        pass

    return None

def get_stream_m3u8(source_url):
    video_id = resolve_video_id(source_url)

    # --- 1. AŞAMA: InnerTube API (Mobil / VR İstemcileri) ---
    if video_id:
        innertube_url = "https://www.youtube.com/youtubei/v1/player"
        clients = [
            {
                "name": "IOS",
                "payload": {
                    "videoId": video_id,
                    "context": {"client": {"clientName": "IOS", "clientVersion": "19.29.1", "deviceMake": "Apple", "deviceModel": "iPhone16,2", "hl": "tr", "gl": "TR"}}
                }
            },
            {
                "name": "ANDROID_VR",
                "payload": {
                    "videoId": video_id,
                    "context": {"client": {"clientName": "ANDROID_VR", "clientVersion": "1.52.18", "deviceMake": "Oculus", "deviceModel": "Quest 3", "hl": "tr", "gl": "TR"}}
                }
            },
            {
                "name": "ANDROID_TESTSUITE",
                "payload": {
                    "videoId": video_id,
                    "context": {"client": {"clientName": "ANDROID_TESTSUITE", "clientVersion": "1.9", "hl": "tr", "gl": "TR"}}
                }
            }
        ]

        for target_client in clients:
            try:
                api_res = session.post(innertube_url, json=target_client["payload"], timeout=4)
                if api_res.status_code == 200:
                    data = api_res.json()
                    hls_url = data.get("streamingData", {}).get("hlsManifestUrl")
                    if hls_url:
                        logging.info(f"[INNERTUBE SUCCESS ({target_client['name']})] -> {source_url}")
                        return hls_url
            except Exception as e:
                logging.warning(f"[INNERTUBE {target_client['name']} FAIL] {e}")

    # --- 2. AŞAMA: yt-dlp (Bypass Argumentleri Eklendi) ---
    target_yt_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else source_url
    logging.info(f"[FALLBACK TO YT-DLP] {target_yt_url} deneniyor...")
    try:
        ytdlp_cmd = [
            "yt-dlp",
            "-g",
            "-f", "best",
            "--extractor-args", "youtube:player_client=ios,android_vr",
            "--socket-timeout", "10",
            target_yt_url
        ]
        process = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _ = process.communicate(timeout=12)
        if process.returncode == 0:
            direct_url = stdout.decode("utf-8").strip().split('\n')[0]
            if direct_url.startswith("http"):
                logging.info(f"[YT-DLP SUCCESS] -> {target_yt_url}")
                return direct_url
    except Exception as e:
        logging.warning(f"[YT-DLP FAIL] {target_yt_url}: {e}")

    # --- 3. AŞAMA: Streamlink ---
    logging.info(f"[FALLBACK TO STREAMLINK] {target_yt_url} deneniyor...")
    try:
        streamlink_cmd = [
            "streamlink",
            "--stream-url",
            "--http-timeout", "15",
            target_yt_url,
            "best"
        ]
        process = subprocess.Popen(streamlink_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _ = process.communicate(timeout=18)
        if process.returncode == 0:
            direct_url = stdout.decode("utf-8").strip()
            if direct_url.startswith("http"):
                logging.info(f"[STREAMLINK SUCCESS] -> {target_yt_url}")
                return direct_url
    except Exception as e:
        logging.error(f"[STREAMLINK FAIL] {target_yt_url}: {e}")

    return None

# -------------------------------------------------------------
# ARKA PLAN GÜNCELLEME SÜRECİ
# -------------------------------------------------------------
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

# -------------------------------------------------------------
# ENDPOINT'LER
# -------------------------------------------------------------

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
    if real_m3u8_url:
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
