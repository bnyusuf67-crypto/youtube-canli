FROM python:3.10-slim

# FFmpeg ve curl kurulumu
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bağımlılıkları yükleme
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını aktarma
COPY . .

# Flask portu
EXPOSE 10000

CMD ["python", "app.py"]
