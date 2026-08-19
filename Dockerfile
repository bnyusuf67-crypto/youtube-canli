FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    streamlink \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=10000

# -w 1 yaparak arka plan thread'inin tek bir süreçte stabil çalışmasını sağlıyoruz
CMD gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT --timeout 60 app:app
