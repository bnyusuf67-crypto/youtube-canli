FROM python:3.10-slim

# FFmpeg ve gerekli sistem araçlarını yüklüyoruz
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bağımlılıkları kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY . .

# Uygulamayı çalıştır
EXPOSE 10000
CMD ["python", "app.py"]
