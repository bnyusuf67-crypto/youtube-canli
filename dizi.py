import json
import re
import urllib.request
import os

channels = {
    "cennetmahallesi": "https://www.youtube.com/@cennetmahallesishowtv/live",
    "behzatc": "https://www.youtube.com/@Behzatc./live",
    "yenigelin": "https://www.youtube.com/@yenigelindizi/live",
    "sihirliannem": "https://www.youtube.com/@SihirliAnnemDizi/live",
    "eeesonra": "https://www.youtube.com/@EeeSonra/live",
    "sefirinkizi": "https://www.youtube.com/@sefirinkizidizi/live",
    "avlu": "https://www.youtube.com/@avludizi/live",
    "cilekkokusu": "https://www.youtube.com/@CilekKokusu/live",
    "fazilethanimvekizlari": "https://www.youtube.com/@fazilethanimvekizlaridizi/live",
    "hanimkoylu": "https://www.youtube.com/@HanimKoyluDizi/live",
    "hayatbazentatlidir": "https://www.youtube.com/@HayatBazenTatlidir/live",
    "ufaktefekcinayetler": "https://www.youtube.com/@ufaktefekcinayetlerdizi/live",
    "istanbullugelin": "https://www.youtube.com/@istanbullugelindizi/live"
}

os.makedirs("dizi", exist_ok=True)
with open("dizi/.gitkeep", "w") as f:
    f.write("")

playlist_content = "#EXTM3U\n"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

for name, url in channels.items():
    print(f"Yayın taranıyor: {name}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req).read().decode('utf-8')
        
        # HTML içinden hlsManifestUrl veya hls_playlist_url ara
        match = re.search(r'"hlsManifestUrl":"([^"]+)"', html)
        stream_url = None
        
        if match:
            stream_url = match.group(1).replace('\\/', '/')
        else:
            # Alternatif parsing
            match_vid = re.search(r'"videoId":"([^"]+)"', html)
            if match_vid:
                video_id = match_vid.group(1)
                # Invidious public instance fallback
                inv_url = f"https://inv.nadeko.net/api/v1/videos/{video_id}"
                try:
                    inv_req = urllib.request.Request(inv_url, headers=headers)
                    inv_res = json.loads(urllib.request.urlopen(inv_req).read().decode('utf-8'))
                    stream_url = inv_res.get("hlsUrl")
                except Exception:
                    pass

        if stream_url:
            # Tekil m3u8
            with open(f"dizi/{name}.m3u8", "w") as f:
                f.write(f"#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2560000\n{stream_url}\n")
            
            # Playlist
            playlist_content += f'#EXTINF:-1 tvg-name="{name}", {name}\n{stream_url}\n'
            print(f"✅ {name}.m3u8 başarıyla oluşturuldu.")
        else:
            print(f"❌ {name} için canlı yayın URL'si bulunamadı.")
            
    except Exception as e:
        print(f"❌ {name} taranırken hata: {e}")

with open("dizi/playlist.m3u8", "w") as f:
    f.write(playlist_content)
