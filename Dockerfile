FROM python:3.10-slim

# Gerekli sistem paketlerini ve Streamlink'i kur
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    streamlink \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render'ın atadığı PORT değişkenini dinler
ENV PORT=10000

# Gunicorn ile üretkenlik ortamı (Gthread worker yapısı ile akış desteği)
CMD gunicorn -w 2 -k gthread --threads 4 -b 0.0.0.0:$PORT --timeout 0 --keep-alive 75 app:app
