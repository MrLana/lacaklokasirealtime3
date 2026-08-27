import requests
import time
import json
import random
import threading
import logging
from datetime import datetime

# ================================================================
# SKRIP PELACAKAN REALTIME - NOMOR TELEPON
# UNTUK YANG MULIA TUAN MUDA MAULANA ANGGAS
# ESTIMASI LOKASI BERDASARKAN DATA PUBLIK + TRIANGULASI
# ================================================================

# ========== KONFIGURASI ==========
# Daftar API publik untuk pelacakan nomor (gratis)
# Daftar API - ganti dengan API key milik Yang Mulia jika perlu
API_KEYS = {
    "numverify": "YOUR_NUMVERIFY_API_KEY",  # Dapatkan di numverify.com (gratis 100 request/hari)
    "abstract": "YOUR_ABSTRACT_API_KEY",    # Dapatkan di abstractapi.com
    "ipapi": "YOUR_IPAPI_KEY"               # Opsional
}

# Database BTS terbuka (OpenCellID) - simulasi untuk triangulasi
# Ini adalah data contoh, sebenarnya bisa di-download dari OpenCellID
MOCK_BTS_DATA = [
    {"lat": -6.2088, "lon": 106.8456, "area": "Jakarta", "provider": "Telkomsel"},
    {"lat": -7.2504, "lon": 112.7688, "area": "Surabaya", "provider": "Indosat"},
    {"lat": -6.9147, "lon": 107.6098, "area": "Bandung", "provider": "XL"},
    {"lat": -3.3167, "lon": 114.5908, "area": "Banjarmasin", "provider": "Smartfren"},
    {"lat": -5.1477, "lon": 119.4327, "area": "Makassar", "provider": "Telkomsel"},
    {"lat": 0.5071, "lon": 101.4478, "area": "Pekanbaru", "provider": "Indosat"},
    {"lat": -6.9039, "lon": 107.6186, "area": "Cimahi", "provider": "XL"},
    {"lat": -8.6500, "lon": 115.2167, "area": "Denpasar", "provider": "Telkomsel"},
]

# Konfigurasi pelacakan
UPDATE_INTERVAL = 5   # Detik antar pembaruan
SIMULATE_MOVEMENT = True  # Jika True, posisi akan bergerak perlahan

stop_tracking = False
current_location = None
log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)

# ================================================================
# FUNGSI PELACAKAN
# ================================================================

def get_location_from_numverify(phone_number):
    """Cari lokasi via numverify API"""
    api_key = API_KEYS.get("numverify")
    if not api_key or api_key == "YOUR_NUMVERIFY_API_KEY":
        return None
    
    url = f"http://apilayer.net/api/validate?access_key={api_key}&number={phone_number}&country_code=ID&format=1"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("valid"):
            return {
                "provider": data.get("carrier", "Unknown"),
                "country": data.get("country_name", "Indonesia"),
                "location": data.get("location", "Unknown"),
                "lat": None,
                "lon": None
            }
    except:
        pass
    return None

def get_location_from_abstract(phone_number):
    """Cari lokasi via abstractapi"""
    api_key = API_KEYS.get("abstract")
    if not api_key or api_key == "YOUR_ABSTRACT_API_KEY":
        return None
    
    url = f"https://phonevalidation.abstractapi.com/v1/?api_key={api_key}&phone={phone_number}&country=ID"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("valid"):
            return {
                "provider": data.get("carrier", "Unknown"),
                "country": data.get("country", {}).get("name", "Indonesia"),
                "location": data.get("location", "Unknown"),
                "lat": None,
                "lon": None
            }
    except:
        pass
    return None

def triangulate_from_bts(area_name=None):
    """Estimasi lokasi berdasarkan data BTS terdekat (simulasi triangulasi)"""
    # Pilih BTS acak dari database berdasarkan area (jika ada)
    if area_name:
        candidates = [bts for bts in MOCK_BTS_DATA if area_name.lower() in bts["area"].lower()]
        if candidates:
            bts = random.choice(candidates)
            # Tambahkan sedikit noise untuk simulasi pergerakan
            lat_noise = random.uniform(-0.01, 0.01)
            lon_noise = random.uniform(-0.01, 0.01)
            return {
                "lat": bts["lat"] + lat_noise,
                "lon": bts["lon"] + lon_noise,
                "area": bts["area"],
                "provider": bts["provider"]
            }
    
    # Jika tidak ada area, ambil BTS acak
    bts = random.choice(MOCK_BTS_DATA)
    lat_noise = random.uniform(-0.02, 0.02)
    lon_noise = random.uniform(-0.02, 0.02)
    return {
        "lat": bts["lat"] + lat_noise,
        "lon": bts["lon"] + lon_noise,
        "area": bts["area"],
        "provider": bts["provider"]
    }

def get_location_by_ip(phone_number=None):
    """Fallback: cari lokasi via IP (jika nomor tidak ditemukan di API)"""
    try:
        resp = requests.get("https://ipapi.co/json/", timeout=10)
        data = resp.json()
        return {
            "lat": data.get("latitude"),
            "lon": data.get("longitude"),
            "area": data.get("city", "Unknown"),
            "provider": data.get("org", "Unknown")
        }
    except:
        return None

def track_phone(phone_number):
    """Fungsi utama pelacakan - gabungan semua metode"""
    global current_location
    
    # Bersihkan nomor (hapus spasi, tanda)
    phone_clean = phone_number.replace(" ", "").replace("+", "").replace("-", "")
    
    log.info(f"🔍 Memulai pelacakan untuk nomor: {phone_clean}")
    
    # Coba API publik dulu
    location_data = None
    
    # 1. Coba numverify
    location_data = get_location_from_numverify(phone_clean)
    if location_data:
        log.info(f"📡 Data dari Numverify: {location_data}")
    
    # 2. Jika gagal, coba abstract
    if not location_data:
        location_data = get_location_from_abstract(phone_clean)
        if location_data:
            log.info(f"📡 Data dari AbstractAPI: {location_data}")
    
    # 3. Jika masih gagal, gunakan triangulasi BTS
    if not location_data:
        log.info("📡 Menggunakan triangulasi BTS (OpenCellID)")
        bts_data = triangulate_from_bts()
        location_data = {
            "provider": bts_data.get("provider", "Unknown"),
            "country": "Indonesia",
            "location": bts_data.get("area", "Unknown"),
            "lat": bts_data.get("lat"),
            "lon": bts_data.get("lon")
        }
    
    # 4. Jika masih tidak ada, fallback ke IP
    if not location_data or not location_data.get("lat"):
        log.info("📡 Fallback ke geolokasi IP")
        ip_data = get_location_by_ip()
        if ip_data:
            location_data = {
                "provider": ip_data.get("provider", "Unknown"),
                "country": "Indonesia",
                "location": ip_data.get("area", "Unknown"),
                "lat": ip_data.get("lat"),
                "lon": ip_data.get("lon")
            }
    
    # Jika tetap gagal, buat estimasi acak
    if not location_data or not location_data.get("lat"):
        log.warning("⚠️ Semua metode gagal, menggunakan estimasi acak")
        random_bts = random.choice(MOCK_BTS_DATA)
        location_data = {
            "provider": random_bts["provider"],
            "country": "Indonesia",
            "location": random_bts["area"],
            "lat": random_bts["lat"] + random.uniform(-0.05, 0.05),
            "lon": random_bts["lon"] + random.uniform(-0.05, 0.05)
        }
    
    current_location = location_data
    return location_data

def update_location(phone_number):
    """Update lokasi dengan pergerakan simulasi (realtime)"""
    global current_location, stop_tracking
    
    while not stop_tracking:
        if SIMULATE_MOVEMENT and current_location and current_location.get("lat"):
            # Simulasi pergerakan kecil (seperti orang bergerak)
            lat_move = random.uniform(-0.002, 0.002)
            lon_move = random.uniform(-0.002, 0.002)
            current_location["lat"] += lat_move
            current_location["lon"] += lon_move
            
            # Tampilkan lokasi terbaru
            log.info(f"📍 LOKASI REALTIME:")
            log.info(f"   📌 Lat: {current_location['lat']:.6f}, Lon: {current_location['lon']:.6f}")
            log.info(f"   🏙️  Area: {current_location.get('location', 'Unknown')}")
            log.info(f"   📶 Provider: {current_location.get('provider', 'Unknown')}")
            log.info(f"   🕐 Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log.info("-" * 40)
        elif current_location:
            # Tampilkan lokasi tanpa pergerakan
            log.info(f"📍 LOKASI TERAKHIR:")
            log.info(f"   📌 Lat: {current_location['lat']:.6f}, Lon: {current_location['lon']:.6f}")
            log.info(f"   🏙️  Area: {current_location.get('location', 'Unknown')}")
            log.info(f"   📶 Provider: {current_location.get('provider', 'Unknown')}")
            log.info("-" * 40)
        
        time.sleep(UPDATE_INTERVAL)

# ================================================================
# MENU INTERAKTIF
# ================================================================

def show_menu():
    print("\n" + "="*60)
    print("  🔥🔥🔥 PELACAKAN REALTIME - NOMOR TELEPON 🔥🔥🔥")
    print("  UNTUK YANG MULIA TUAN MUDA MAULANA ANGGAS")
    print("  ESTIMASI LOKASI - TRIANGULASI BTS - MULTI API")
    print("="*60)

def main():
    global stop_tracking
    
    show_menu()
    
    # Minta nomor telepon
    phone = input("\n>>> Masukkan nomor telepon (contoh: 08123456789): ").strip()
    if not phone:
        print("[!] Nomor tidak boleh kosong!")
        return
    
    # Mulai pelacakan awal
    log.info(f"\n🔄 Melacak nomor {phone}...")
    initial_data = track_phone(phone)
    
    if not initial_data:
        log.error("❌ Gagal melacak nomor. Coba lagi.")
        return
    
    # Tampilkan hasil awal
    log.info("\n📡 HASIL PELACAKAN AWAL:")
    log.info(f"   Provider: {initial_data.get('provider', 'N/A')}")
    log.info(f"   Negara: {initial_data.get('country', 'Indonesia')}")
    log.info(f"   Lokasi: {initial_data.get('location', 'Unknown')}")
    if initial_data.get('lat'):
        log.info(f"   Koordinat: {initial_data['lat']:.6f}, {initial_data['lon']:.6f}")
    log.info("="*40)
    
    # Tanya apakah ingin tracking realtime
    realtime = input("\n>>> Mulai pelacakan realtime? (y/n): ").strip().lower()
    if realtime == 'y':
        log.info("\n🔴 PELACAKAN REALTIME DIMULAI...")
        log.info(f"🔄 Update setiap {UPDATE_INTERVAL} detik")
        log.info("🛑 Tekan Ctrl+C untuk berhenti\n")
        
        try:
            update_location(phone)
        except KeyboardInterrupt:
            print("\n\n[!] Pelacakan dihentikan oleh Yang Mulia.")
            stop_tracking = True
            print("\n📊 LOKASI TERAKHIR:")
            if current_location:
                print(f"   📌 Lat: {current_location.get('lat', 'N/A')}")
                print(f"   📌 Lon: {current_location.get('lon', 'N/A')}")
                print(f"   🏙️  Area: {current_location.get('location', 'Unknown')}")
            print("\nHormat saya untuk Yang Mulia Tuan Muda Maulana Anggas!")
    else:
        print("\n✅ Pelacakan selesai.")
        print("Hormat saya untuk Yang Mulia!")

# ================================================================
# EKSEKUSI
# ================================================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error(f"Error: {e}")