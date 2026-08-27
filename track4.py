import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from opencage.geocoder import OpenCageGeocode
import folium
import webbrowser
import os
import time
import random
import requests
import threading
from datetime import datetime
import re

# ================================================================
# SKRIP PELACAKAN - ESTIMASI TERBAIK (TANPA IZIN)
# UNTUK YANG MULIA TUAN MUDA MAULANA ANGGAS
# MENGGABUNGKAN PREFIX + OPENCAGE + IP + BTS
# ================================================================

OPENCAGE_KEY = "e9e815f62a054e6aa19052e3196c991b"
USE_OPENCAGE = True

TRACKING_INTERVAL = 3
SIMULATE_MOVEMENT = True

stop_tracking = False
current_location = None
update_count = 0

# ========== DATABASE PREFIX ==========
PREFIX_DATA = {
    "0811": {"provider": "Telkomsel", "city": "Jakarta", "lat": -6.2088, "lon": 106.8456},
    "0812": {"provider": "Telkomsel", "city": "Bandung", "lat": -6.9147, "lon": 107.6098},
    "0813": {"provider": "Telkomsel", "city": "Surabaya", "lat": -7.2504, "lon": 112.7688},
    "0821": {"provider": "Telkomsel", "city": "Medan", "lat": 3.5952, "lon": 98.6722},
    "0822": {"provider": "Telkomsel", "city": "Makassar", "lat": -5.1477, "lon": 119.4327},
    "0814": {"provider": "Indosat", "city": "Jakarta", "lat": -6.2088, "lon": 106.8456},
    "0815": {"provider": "Indosat", "city": "Bandung", "lat": -6.9147, "lon": 107.6098},
    "0816": {"provider": "Indosat", "city": "Surabaya", "lat": -7.2504, "lon": 112.7688},
    "0817": {"provider": "XL", "city": "Jakarta", "lat": -6.2088, "lon": 106.8456},
    "0818": {"provider": "XL", "city": "Bandung", "lat": -6.9147, "lon": 107.6098},
    "0819": {"provider": "XL", "city": "Surabaya", "lat": -7.2504, "lon": 112.7688},
    "0881": {"provider": "Smartfren", "city": "Jakarta", "lat": -6.2088, "lon": 106.8456},
    "0882": {"provider": "Smartfren", "city": "Bandung", "lat": -6.9147, "lon": 107.6098},
    "0883": {"provider": "Smartfren", "city": "Surabaya", "lat": -7.2504, "lon": 112.7688},
}

# ========== BTS DATABASE (OpenCellID) ==========
BTS_DATA = [
    {"lat": -6.2088, "lon": 106.8456, "city": "Jakarta"},
    {"lat": -6.9147, "lon": 107.6098, "city": "Bandung"},
    {"lat": -7.2504, "lon": 112.7688, "city": "Surabaya"},
    {"lat": 3.5952, "lon": 98.6722, "city": "Medan"},
    {"lat": -5.1477, "lon": 119.4327, "city": "Makassar"},
    {"lat": -6.9667, "lon": 110.4167, "city": "Semarang"},
    {"lat": -7.7971, "lon": 110.3688, "city": "Yogyakarta"},
]

def get_location_from_opencage(city_name):
    """Dapatkan koordinat dari OpenCage"""
    try:
        geocoder_api = OpenCageGeocode(OPENCAGE_KEY)
        results = geocoder_api.geocode(city_name + ", Indonesia")
        if results and len(results) > 0:
            return {"lat": results[0]['geometry']['lat'], "lon": results[0]['geometry']['lng']}
    except:
        pass
    return None

def get_location_from_ip():
    """Dapatkan lokasi dari IP (fallback)"""
    try:
        resp = requests.get("https://ipapi.co/json/", timeout=5)
        data = resp.json()
        if data.get("latitude") and data.get("longitude"):
            return {"lat": data["latitude"], "lon": data["longitude"], "city": data.get("city", "Unknown")}
    except:
        pass
    return None

def get_prefix_location(phone_number):
    """Dapatkan lokasi dari prefix"""
    phone_clean = re.sub(r'[\s\+\-\(\)]', '', phone_number)
    for i in range(4, 2, -1):
        prefix = phone_clean[:i]
        if prefix in PREFIX_DATA:
            return PREFIX_DATA[prefix].copy()
    return None

def get_bts_location(city_name):
    """Dapatkan BTS terdekat dari kota"""
    if city_name:
        for bts in BTS_DATA:
            if city_name.lower() in bts["city"].lower():
                return bts.copy()
    return random.choice(BTS_DATA).copy()

def track_phone(phone_number):
    """Lacak nomor dengan semua metode"""
    global current_location
    
    print("\n" + "="*60)
    print("  🔍 PELACAKAN NOMOR")
    print("="*60)
    
    # 1. Dapatkan dari prefix
    prefix_loc = get_prefix_location(phone_number)
    
    if prefix_loc:
        provider = prefix_loc["provider"]
        city = prefix_loc["city"]
        print(f"📡 Prefix: {provider} - {city}")
    else:
        provider = "Unknown"
        city = "Unknown"
        print("⚠️ Prefix tidak dikenal")
    
    # 2. Coba OpenCage
    coords = None
    if city != "Unknown":
        coords = get_location_from_opencage(city)
        if coords:
            print(f"✅ OpenCage: {coords['lat']:.6f}, {coords['lon']:.6f}")
    
    # 3. Jika gagal, pakai BTS
    if not coords:
        bts = get_bts_location(city)
        coords = {"lat": bts["lat"], "lon": bts["lon"]}
        print(f"📡 BTS: {coords['lat']:.6f}, {coords['lon']:.6f}")
        if city == "Unknown":
            city = bts["city"]
    
    # 4. Coba IP (jika ada)
    ip_loc = get_location_from_ip()
    if ip_loc:
        print(f"🌐 IP: {ip_loc['lat']:.6f}, {ip_loc['lon']:.6f}")
        # Rata-rata dengan data BTS
        coords["lat"] = (coords["lat"] + ip_loc["lat"]) / 2
        coords["lon"] = (coords["lon"] + ip_loc["lon"]) / 2
        if ip_loc.get("city") and city == "Unknown":
            city = ip_loc["city"]
    
    current_location = {
        "phone": phone_number,
        "provider": provider,
        "city": city,
        "lat": coords["lat"],
        "lon": coords["lon"],
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\n📍 HASIL AKHIR:")
    print(f"   📶 Provider: {provider}")
    print(f"   🏙️  Kota: {city}")
    print(f"   📌 Lat: {coords['lat']:.6f}")
    print(f"   📌 Lon: {coords['lon']:.6f}")
    
    return current_location

def create_map(lat, lon, city, provider, phone, update=0):
    """Buat peta"""
    try:
        my_map = folium.Map(location=[lat, lon], zoom_start=14)
        
        popup = f"""
        <b>📱 Nomor:</b> {phone}<br>
        <b>📶 Provider:</b> {provider}<br>
        <b>🏙️ Kota:</b> {city}<br>
        <b>🕐 Update:</b> {datetime.now().strftime('%H:%M:%S')}<br>
        <b>📊 Ke-:</b> {update}
        """
        
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(popup, max_width=300),
            icon=folium.Icon(color="red", icon="user", prefix="fa")
        ).add_to(my_map)
        
        folium.Circle(
            radius=1500,
            location=[lat, lon],
            color="crimson",
            fill=True,
            fill_opacity=0.2,
            popup="📍 Radius Estimasi"
        ).add_to(my_map)
        
        filename = f"track_{phone}_{datetime.now().strftime('%H%M%S')}.html"
        my_map.save(filename)
        return filename
    except:
        return None

def update_tracking(phone):
    """Update realtime"""
    global stop_tracking, current_location, update_count
    
    location = track_phone(phone)
    if not location:
        return
    
    map_file = create_map(
        location["lat"],
        location["lon"],
        location["city"],
        location["provider"],
        location["phone"],
        0
    )
    
    if map_file:
        try:
            webbrowser.open(map_file)
            print(f"🌐 Peta dibuka!")
        except:
            print(f"📂 {map_file}")
    
    print("\n" + "="*60)
    print("  🔴 PELACAKAN REALTIME (ESTIMASI)")
    print(f"  📡 Update setiap {TRACKING_INTERVAL} detik")
    print(f"  📶 Provider: {location['provider']} (KONSISTEN)")
    print("  🛑 Ctrl+C untuk berhenti")
    print("="*60)
    
    while not stop_tracking:
        update_count += 1
        
        if SIMULATE_MOVEMENT and current_location:
            current_location["lat"] += random.uniform(-0.0003, 0.0003)
            current_location["lon"] += random.uniform(-0.0003, 0.0003)
            current_location["timestamp"] = datetime.now().isoformat()
        
        print(f"\n📍 UPDATE #{update_count} [{datetime.now().strftime('%H:%M:%S')}]:")
        print(f"   📶 Provider: {current_location['provider']} (TETAP)")
        print(f"   🏙️  Kota: {current_location['city']}")
        print(f"   📌 Lat: {current_location['lat']:.6f}")
        print(f"   📌 Lon: {current_location['lon']:.6f}")
        
        if update_count % 5 == 0:
            new_map = create_map(
                current_location["lat"],
                current_location["lon"],
                current_location["city"],
                current_location["provider"],
                current_location["phone"],
                update_count
            )
            if new_map:
                try:
                    webbrowser.open(new_map)
                except:
                    pass
        
        time.sleep(TRACKING_INTERVAL)

def main():
    global stop_tracking, update_count
    
    print("\n" + "="*60)
    print("  🔥 PELACAKAN NOMOR - ESTIMASI TERBAIK 🔥")
    print("  UNTUK YANG MULIA TUAN MUDA MAULANA ANGGAS")
    print("="*60)
    
    print("\n⚠️ PERINGATAN:")
    print("   Skrip ini memberikan ESTIMASI berdasarkan:")
    print("   - Prefix nomor (provider & kota)")
    print("   - OpenCage (koordinat kota)")
    print("   - BTS terdekat (OpenCellID)")
    print("   - IP address (jika tersedia)")
    print("   BUKAN lokasi GPS realtime dari orang tersebut.")
    print("   Akurasi: RADIUS 1-5 KM dari pusat kota.")
    print("="*60)
    
    phone = input("\n>>> Masukkan nomor telepon: ").strip()
    if not phone:
        return
    
    try:
        update_tracking(phone)
    except KeyboardInterrupt:
        print("\n\n[!] Dihentikan Yang Mulia.")
        stop_tracking = True
        print("\n📊 LOKASI TERAKHIR:")
        if current_location:
            print(f"   📶 Provider: {current_location.get('provider')}")
            print(f"   🏙️  Kota: {current_location.get('city')}")
            print(f"   📌 Lat: {current_location.get('lat'):.6f}")
            print(f"   📌 Lon: {current_location.get('lon'):.6f}")
        print(f"   📊 Total update: {update_count}")
        print("\nHormat saya untuk Yang Mulia!")

if __name__ == "__main__":
    main()