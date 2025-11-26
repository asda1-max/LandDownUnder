# config_manager.py
import os
import json

CONFIG_FILE = "app_config.json"
DEFAULT_API_URL = "https://lmaopoiasda.notazeroth.site" # Default fallback

def get_api_url():
    """Membaca API URL dari config file. Jika tidak ada, gunakan default."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                url = data.get("api_url", DEFAULT_API_URL)
                print(url)
                return url.rstrip('/') # Hapus slash di akhir untuk konsistensi
        except:
            return DEFAULT_API_URL
    return DEFAULT_API_URL

def save_api_url(url):
    """Menyimpan API URL baru ke config file."""
    # Pastikan format URL valid (bisa ditambahkan validasi regex jika mau)
    clean_url = url.strip().rstrip('/')
    if not clean_url.startswith("http"):
        clean_url = "https://" + clean_url
        
    data = {"api_url": clean_url}
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f)
        return True
    except:
        return False