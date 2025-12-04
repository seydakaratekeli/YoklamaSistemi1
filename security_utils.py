import os
import logging
from logging.handlers import RotatingFileHandler
from cryptography.fernet import Fernet
import hashlib # Hash hesaplama için eklendi

# --- 1. LOGLAMA AYARLARI ---
logging.basicConfig(
    handlers=[RotatingFileHandler('security_log.txt', maxBytes=100000, backupCount=5)],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_access(user_id, name, status):
    if status == "Granted":
        logging.info(f"GIRIS BASARILI: {name} (ID: {user_id})")
        print(f"✔ [LOG] Giris Kaydedildi: {name}")
    elif status == "Denied":
        logging.warning(f"GIRIS REDDEDILDI: Taninmayan Yuz (ID: {user_id})")
    elif status == "Spoof":
        logging.critical(f"SALDIRI TESPITI! (Sahte Fotograf)")
        print(f"⚠️ [LOG] SPOOF SALDIRISI ENGELLENDI!")
    elif status == "Tampered":
        logging.critical(f"VERI BUTUNLUGU BOZULDU! Dosya kurcalanmis.")

# --- 2. ŞİFRELEME SİSTEMİ ---
KEY_FILE = "secret.key"

def load_key():
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "rb") as key_file:
                key = key_file.read()
            Fernet(key)
            return key
        except: pass
    
    print("🔒 Yeni güvenlik anahtarı oluşturuluyor...")
    new_key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(new_key)
    return new_key

try:
    cipher = Fernet(load_key())
except:
    cipher = Fernet(Fernet.generate_key())

def encrypt_file(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            enc_data = cipher.encrypt(data)
            enc_file = file_path.replace(".yml", ".enc")
            with open(enc_file, "wb") as f:
                f.write(enc_data)
            print(f"🔒 Dosya şifrelendi: {enc_file}")
        except Exception as e:
            print(f"Şifreleme Hatası: {e}")

def decrypt_file_temp(enc_path):
    yml_file = enc_path.replace(".enc", ".yml")
    if os.path.exists(enc_path):
        try:
            with open(enc_path, "rb") as f:
                data = f.read()
            dec_data = cipher.decrypt(data)
            with open(yml_file, "wb") as f:
                f.write(dec_data)
            return yml_file
        except:
            return None
    return None

# --- 3. YENİ: DOSYA BÜTÜNLÜK KONTROLÜ (INTEGRITY CHECK) ---
def calculate_hash(file_path):
    """Bir dosyanın SHA-256 parmak izini hesaplar."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Dosyayı parça parça oku (Büyük dosyalar için performanslı)
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def sign_file(file_path):
    """Dosyayı imzalar (Hash'ini .sig dosyasına kaydeder)."""
    if not os.path.exists(file_path): return
    file_hash = calculate_hash(file_path)
    sig_file = file_path + ".sig"
    with open(sig_file, "w") as f:
        f.write(file_hash)
    print(f"🔏 Dosya İmzalandı: {os.path.basename(file_path)}")

def verify_file_integrity(file_path):
    """Dosyanın değiştirilip değiştirilmediğini kontrol eder."""
    sig_file = file_path + ".sig"
    
    if not os.path.exists(sig_file):
        return False, "İMZA YOK (Güvenilmez)"
    
    current_hash = calculate_hash(file_path)
    with open(sig_file, "r") as f:
        stored_hash = f.read().strip()
        
    if current_hash == stored_hash:
        return True, "Doğrulandı"
    else:
        return False, "BOZUK/DEĞİŞTİRİLMİŞ!"