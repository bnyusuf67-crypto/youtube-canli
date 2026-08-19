import os
import json
import logging
import subprocess
import time
from urllib.parse import unquote
from flask import Flask, request, Response, jsonify

# UTF-8 Standartlaştırması
os.environ["PYTHONIOENCODING"] = "utf-8"

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

STREAMLINK_PATH = "streamlink"

COMMON_HEADERS = [
    "--http-header",
    "User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
    "--http-header",
    "Accept-Language=en-US,en;q=0.9"
]

def get_stream_info(url, retries=2):
    """Yayın bilgilerini çeker, başarısız olursa süreci derhal kapatır."""
    for attempt in range(retries):
        cmd = [STREAMLINK_PATH, "--json"] + COMMON_HEADERS + [url]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        try:
            stdout, stderr = process.communicate(timeout=10)
            if process.returncode == 0:
                return json.loads(stdout.decode("utf-8", errors="replace"))
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            logging.error(f"[TIMEOUT] Stream info timeout on attempt {attempt+1}")
        time.sleep(0.5)
    return None

def kill_process(process):
    """Alt süreci (Subprocess) bellek sızıntısı oluşturmadan tamamen sonlandırır."""
    if process and process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        
    if process.stdout:
        process.stdout.close()
    if process.stderr:
        process.stderr.close()

@app.route("/stream", methods=["GET"])
def stream():
    raw_url = request.args.get("url")
    if not raw_url:
        return jsonify({"error": "URL parameter is required"}), 400

    url = unquote(raw_url)
    client_ip = request.remote_addr
    logging.info(f"[CLIENT CONNECT] {client_ip} -> {url}")

    stream_info = get_stream_info(url)
    if not stream_info or "streams" not in stream_info or "best" not in stream_info["streams"]:
        return jsonify({"error": "Failed to retrieve stream info or no stream available"}), 500

    command = [
        STREAMLINK_PATH,
        "--hls-live-restart",
    ] + COMMON_HEADERS + [
        url,
        "best",
        "--stdout"
    ]

    # bufsize=0 ile veriyi tampon bellekte biriktirmeden doğrudan aktarır (RAM Tasarrufu)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, # stderr log dosyasını şişirmemesi için devre dışı bırakıldı
        bufsize=0
    )

    def generate():
        try:
            logging.info(f"[STREAM START] {client_ip}")
            # Chunk boyutunu 64KB yaparak CPU ve I/O yükünü dengeleriz
            while True:
                chunk = process.stdout.read(65536)
                if not chunk:
                    break
                yield chunk
        except (GeneratorExit, ConnectionResetError):
            logging.info(f"[CLIENT DISCONNECTED] {client_ip}")
        except Exception as e:
            logging.error(f"[STREAM ERROR] {e}")
        finally:
            kill_process(process)

    # Chunked Transfer Encoding ve doğru İçerik Tipi
    return Response(
        generate(),
        content_type="video/mp2t",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff"
        }
    )

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6095))
    app.run(host="0.0.0.0", port=port, threaded=True)
