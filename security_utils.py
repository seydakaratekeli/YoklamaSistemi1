import os
import logging
from cryptography.fernet import Fernet
from datetime import datetime

# --- 1. LOGLAMA AYARLARI (YENİ) ---
# Log dosyasını ayarla
logging.basicConfig(
    filename='security_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_access(user_id, name, status):
    """Erişim denemelerini kaydeder."""
    if status == "Granted":
        logging.info(f"GIRIS BASARILI: Kullanici: {name} (ID: {user_id})")
        print(f"✔ [LOG] Giris Kaydedildi: {name}")
    elif status == "Denied":
        logging.warning(f"GIRIS REDDEDILDI: Taninmayan Yuz (ID: {user_id})")
        print(f"❌ [LOG] Reddedildi: Taninmayan Kisi")
    elif status == "Spoof":
        logging.critical(f"SALDIRI TESPITI! (Sahte Fotograf/Video)")
        print(f"⚠️ [LOG] SPOOF SALDIRISI LOGLANDI!")

# --- 2. ŞİFRELEME SİSTEMİ (ESKİ KODUN AYNISI) ---
KEY_FILE = "secret.key"

def load_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)
    else:
        with open(KEY_FILE, "rb") as key_file:
            key = key_file.read()
    return key

cipher = Fernet(load_key())

def encrypt_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        enc_data = cipher.encrypt(data)
        enc_file = file_path.replace(".yml", ".enc")
        with open(enc_file, "wb") as f:
            f.write(enc_data)
        os.remove(file_path)
        print(f"KİLİTLENDİ: {enc_file}")

def decrypt_file_temp(enc_path):
    yml_file = enc_path.replace(".enc", ".yml")
    if os.path.exists(enc_path):
        with open(enc_path, "rb") as f:
            data = f.read()
        dec_data = cipher.decrypt(data)
        with open(yml_file, "wb") as f:
            f.write(dec_data)
        return yml_file
    return None