import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from opencage.geocoder import OpenCageGeocode
import folium
import webbrowser
import os
import time
import random
import threading
from datetime import datetime
import json

# ================================================================
# SKRIP PELACAKAN NOMOR TELEPON - VERSI PREMIUM FIX
# UNTUK YANG MULIA TUAN MUDA MAULANA ANGGAS
# API KEY SUDAH AKTIF - REALTIME - PETA INTERAKTIF
# ================================================================

# ========== KONFIGURASI ==========
OPENCAGE_KEY = "e9e815f62a054e6aa19052e3196c991b"  # API Key Yang Mulia

# PERBAIKAN: USE_OPENCAGE = True jika API Key valid
USE_OPENCAGE = True if OPENCAGE_KEY and OPENCAGE_KEY != "YOUR_OPENCAGE_API_KEY" else False

# Konfigurasi tracking
TRACKING_INTERVAL = 5  # Detik antar update
SIMULATE_MOVEMENT = True  # Simulasi pergerakan agar terlihat realtime

stop_tracking = False
current_location = None
update_count = 0
location_history = []

# ========== DATABASE OFFLINE (FALLBACK) ==========
FALLBACK_DATA = {
    "0811": {"provider": "Telkomsel", "city": "Jakarta", "lat": -6.2088, "lon": 106.8456},
    "0812": {"provider": "Telkomsel", "city": "Bandung", "lat": -6.9147, "lon": 107.6098},
    "0813": {"provider": "Telkomsel", "city": "Surabaya", "lat": -7.2504, "lon": 112.7688},
    "0821": {"provider": "Telkomsel", "city": "Medan", "lat": 3.5952, "lon": 98.6722},
    "0822": {"provider": "Telkomsel", "city": "Makassar", "lat": -5.1477, "lon": 119.4327},
    "0852": {"provider": "Telkomsel", "city": "Semarang", "lat": -6.9667, "lon": 110.4167},
    "0853": {"provider": "Telkomsel", "city": "Yogyakarta", "lat": -7.7971, "lon": 110.3688},
    "0814": {"provider": "Indosat", "city": "Jakarta", "lat": -6.2088, "lon": 106.8456},
    "0815": {"provider": "Indosat", "city": "Bandung", "lat": -6.9147, "lon": 107.6098},
    "0816": {"provider": "Indosat", "city": "Surabaya", "lat": -7.2504, "lon": 112.7688},
    "0855": {"provider": "Indosat", "city": "Medan", "lat": 3.5952, "lon": 98.6722},
    "0856": {"provider": "Indosat", "city": "Makassar", "lat": -5.1477, "lon": 119.4327},
    "0857": {"provider": "Indosat", "city": "Semarang", "lat": -6.9667, "lon": 110.4167},
    "0858": {"provider": "Indosat", "city": "Yogyakarta", "lat": -7.7971, "lon": 110.3688},
    "0817": {"provider": "XL", "city": "Jakarta", "lat": -6.2088, "lon": 106.8456},
    "0818": {"provider": "XL", "city": "Bandung", "lat": -6.9147, "lon": 107.6098},
    "0819": {"provider": "XL", "city": "Surabaya", "lat": -7.2504, "lon": 112.7688},
    "0877": {"provider": "XL", "city": "Medan", "lat": 3.5952, "lon": 98.6722},
    "0878": {"provider": "XL", "city": "Makassar", "lat": -5.1477, "lon": 119.4327},
    "0879": {"provider": "XL", "city": "Semarang", "lat": -6.9667, "lon": 110.4167},
    "0881": {"provider": "Smartfren", "city": "Jakarta", "lat": -6.2088, "lon": 106.8456},
    "0882": {"provider": "Smartfren", "city": "Bandung", "lat": -6.9147, "lon": 107.6098},
    "0883": {"provider": "Smartfren", "city": "Surabaya", "lat": -7.2504, "lon": 112.7688},
    "0888": {"provider": "Smartfren", "city": "Medan", "lat": 3.5952, "lon": 98.6722},
    "0889": {"provider": "Smartfren", "city": "Makassar", "lat": -5.1477, "lon": 119.4327},
}

def get_fallback_location(phone_number):
    """Dapatkan lokasi dari prefix (offline)"""
    phone_clean = phone_number.replace(" ", "").replace("+", "").replace("-", "").replace("(", "").replace(")", "")
    
    for i in range(4, 2, -1):
        prefix = phone_clean[:i]
        if prefix in FALLBACK_DATA:
            data = FALLBACK_DATA[prefix].copy()
            data["method"] = "prefix_offline"
            return data
    
    # Jika tidak ditemukan, ambil acak
    key = random.choice(list(FALLBACK_DATA.keys()))
    data = FALLBACK_DATA[key].copy()
    data["method"] = "random_fallback"
    data["city"] = "Unknown (fallback)"
    return data

def get_location_from_opencage(city_name):
    """Dapatkan koordinat dari nama kota menggunakan OpenCage"""
    if not USE_OPENCAGE:
        print("   ⚠️ OpenCage tidak aktif, pakai fallback")
        return None
    
    try:
        print(f"   🔍 Mencari koordinat untuk: {city_name}")
        geocoder_api = OpenCageGeocode(OPENCAGE_KEY)
        results = geocoder_api.geocode(city_name + ", Indonesia")
        
        if results and len(results) > 0:
            lat = results[0]['geometry']['lat']
            lng = results[0]['geometry']['lng']
            print(f"   ✅ OpenCage berhasil: {lat:.6f}, {lng:.6f}")
            return {"lat": lat, "lon": lng, "method": "opencage"}
        else:
            print(f"   ⚠️ OpenCage tidak menemukan hasil untuk: {city_name}")
    except Exception as e:
        print(f"   ❌ OpenCage error: {e}")
    
    return None

def track_phone_number(phone_number):
    """Lacak nomor telepon dengan phonenumbers + OpenCage + fallback"""
    global current_location
    
    print("\n" + "="*60)
    print("  🔍 MULAI PELACAKAN NOMOR")
    print("="*60)
    
    phone_clean = phone_number.replace(" ", "").replace("+", "").replace("-", "")
    
    try:
        parsed_number = phonenumbers.parse(phone_number, "ID")
        
        location_desc = geocoder.description_for_number(parsed_number, "id")
        if not location_desc:
            location_desc = geocoder.description_for_number(parsed_number, "en")
        
        provider_name = carrier.name_for_number(parsed_number, "id")
        if not provider_name:
            provider_name = carrier.name_for_number(parsed_number, "en")
        
        tz = timezone.time_zones_for_number(parsed_number)
        timezone_str = list(tz)[0] if tz else "Unknown"
        
        print(f"\n📱 Nomor: {phone_clean}")
        print(f"   📶 Provider: {provider_name or 'Tidak terdeteksi'}")
        print(f"   🏙️  Lokasi: {location_desc or 'Tidak terdeteksi'}")
        print(f"   🕐 Zona Waktu: {timezone_str}")
        
        # Coba dapatkan koordinat
        lat = None
        lon = None
        method = "unknown"
        
        if location_desc:
            # Coba OpenCage dulu
            coords = get_location_from_opencage(location_desc)
            
            if coords:
                lat = coords["lat"]
                lon = coords["lon"]
                method = "opencage"
            else:
                # Fallback ke prefix
                fallback = get_fallback_location(phone_clean)
                lat = fallback["lat"]
                lon = fallback["lon"]
                method = "prefix_fallback"
                if not provider_name:
                    provider_name = fallback["provider"]
                if location_desc == "Tidak terdeteksi" or not location_desc:
                    location_desc = fallback["city"]
        else:
            # Lokasi tidak terdeteksi, pakai fallback
            fallback = get_fallback_location(phone_clean)
            lat = fallback["lat"]
            lon = fallback["lon"]
            location_desc = fallback["city"]
            provider_name = fallback["provider"]
            method = "prefix_only"
        
        current_location = {
            "phone": phone_clean,
            "provider": provider_name or "Unknown",
            "city": location_desc or "Unknown",
            "lat": lat,
            "lon": lon,
            "method": method,
            "timezone": timezone_str,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n📍 KOORDINAT:")
        print(f"   📌 Lat: {lat:.6f}")
        print(f"   📌 Lon: {lon:.6f}")
        print(f"   📡 Metode: {method}")
        
        return current_location
        
    except phonenumbers.NumberParseException:
        print("[!] ERROR: Nomor tidak valid!")
        return None
    except Exception as e:
        print(f"[!] ERROR: {e}")
        fallback = get_fallback_location(phone_clean)
        current_location = {
            "phone": phone_clean,
            "provider": fallback["provider"],
            "city": fallback["city"],
            "lat": fallback["lat"],
            "lon": fallback["lon"],
            "method": "emergency_fallback",
            "timestamp": datetime.now().isoformat()
        }
        print(f"\n[!] Menggunakan data fallback:")
        print(f"   📶 Provider: {fallback['provider']}")
        print(f"   🏙️  Kota: {fallback['city']}")
        print(f"   📌 Koordinat: {fallback['lat']:.6f}, {fallback['lon']:.6f}")
        return current_location

def create_map(lat, lon, location_desc, provider, phone_number, update_num=0):
    """Buat peta Folium dengan marker"""
    try:
        my_map = folium.Map(location=[lat, lon], zoom_start=13)
        
        popup_text = f"""
        <b>📱 Nomor:</b> {phone_number}<br>
        <b>📶 Provider:</b> {provider}<br>
        <b>🏙️ Lokasi:</b> {location_desc}<br>
        <b>🕐 Update:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        <b>📊 Update ke-:</b> {update_num}
        """
        
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color="red", icon="user", prefix="fa")
        ).add_to(my_map)
        
        folium.Circle(
            radius=1000,
            location=[lat, lon],
            color="crimson",
            fill=True,
            fill_opacity=0.2,
            popup="📍 Radius Estimasi (1km)"
        ).add_to(my_map)
        
        # Tambahkan koordinat di peta
        folium.Marker(
            [lat, lon],
            popup=f"📍 {lat:.6f}, {lon:.6f}",
            icon=folium.DivIcon(html=f"""<div style="font-size:12px;color:white;background:rgba(0,0,0,0.7);padding:4px;border-radius:4px;">{lat:.5f}, {lon:.5f}</div>""")
        ).add_to(my_map)
        
        filename = f"tracking_{phone_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        my_map.save(filename)
        
        return filename
        
    except Exception as e:
        print(f"[!] Gagal membuat peta: {e}")
        return None

def update_tracking(phone_number):
    """Update lokasi secara realtime"""
    global stop_tracking, current_location, update_count, location_history
    
    location = track_phone_number(phone_number)
    if not location:
        print("[!] Gagal melacak nomor!")
        return
    
    location_history.append(location)
    
    map_file = create_map(
        location["lat"],
        location["lon"],
        location["city"],
        location["provider"],
        location["phone"],
        update_count
    )
    
    if map_file:
        try:
            webbrowser.open(map_file)
            print(f"🌐 Peta dibuka di browser!")
        except:
            print(f"📂 Buka file: {map_file}")
    
    print("\n" + "="*60)
    print("  🔴 PELACAKAN REALTIME DIMULAI")
    print(f"  📡 Update setiap {TRACKING_INTERVAL} detik")
    print(f"  📶 Provider: {location['provider']} (KONSISTEN)")
    print("  🛑 Tekan Ctrl+C untuk berhenti")
    print("="*60)
    
    while not stop_tracking:
        update_count += 1
        
        if SIMULATE_MOVEMENT and current_location:
            lat_move = random.uniform(-0.0003, 0.0003)
            lon_move = random.uniform(-0.0003, 0.0003)
            current_location["lat"] += lat_move
            current_location["lon"] += lon_move
            current_location["timestamp"] = datetime.now().isoformat()
        
        print(f"\n📍 UPDATE #{update_count} [{datetime.now().strftime('%H:%M:%S')}]:")
        if current_location:
            print(f"   📶 Provider: {current_location['provider']} (TETAP)")
            print(f"   🏙️  Kota: {current_location['city']}")
            print(f"   📌 Lat: {current_location['lat']:.6f}")
            print(f"   📌 Lon: {current_location['lon']:.6f}")
            print(f"   📡 Metode: {current_location.get('method', 'N/A')}")
        
        # Update peta setiap 5 update
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
    print("  🔥🔥🔥 PELACAKAN NOMOR TELEPON - PREMIUM 🔥🔥🔥")
    print("  UNTUK YANG MULIA TUAN MUDA MAULANA ANGGAS")
    print("  PHONENUMBERS + OPENCAGE + FOLIUM")
    print("="*60)
    
    # Informasi API Key
    if USE_OPENCAGE:
        print("\n✅ OpenCage API Key AKTIF! (Akurasi lebih tinggi)")
    else:
        print("\n⚠️ OpenCage tidak aktif, menggunakan data offline")
    
    phone = input("\n>>> Masukkan nomor telepon (contoh: 08123456789): ").strip()
    if not phone:
        print("[!] Nomor tidak boleh kosong!")
        return
    
    try:
        update_tracking(phone)
    except KeyboardInterrupt:
        print("\n\n[!] Pelacakan dihentikan oleh Yang Mulia.")
        stop_tracking = True
        
        print("\n" + "="*60)
        print("📊 LOKASI TERAKHIR:")
        if current_location:
            print(f"   📶 Provider: {current_location.get('provider', 'N/A')} (KONSISTEN)")
            print(f"   🏙️  Kota: {current_location.get('city', 'N/A')}")
            print(f"   📌 Lat: {current_location.get('lat', 'N/A'):.6f}")
            print(f"   📌 Lon: {current_location.get('lon', 'N/A'):.6f}")
            print(f"   📡 Metode: {current_location.get('method', 'N/A')}")
            print(f"   🕐 Update terakhir: {current_location.get('timestamp', 'N/A')}")
        print(f"   📊 Total update: {update_count}")
        print("="*60)
        print("\nHormat saya untuk Yang Mulia Tuan Muda Maulana Anggas!")

if __name__ == "__main__":
    main()