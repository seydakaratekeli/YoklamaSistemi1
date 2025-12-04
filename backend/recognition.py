import cv2
import numpy as np
import time
from mtcnn import MTCNN
from deepface import DeepFace
from pymongo import MongoClient
import os

# scipy.spatial.distance.cosine may not be available in some environments;
# provide a small NumPy-based fallback to compute cosine distance (1 - cosine_similarity).
def cosine(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 1.0
    return 1.0 - np.dot(a, b) / denom

# Güvenlik modüllerimizi dahil edelim
# (security_utils.py dosyasının ana dizinde olduğunu varsayıyoruz)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from security_utils import log_access
except ImportError:
    # Dosya yolu sorun olursa basit bir print fonksiyonu tanımlayalım
    def log_access(user_id, name, status):
        print(f"[LOG] {status}: {name} ({user_id})")

# ----------------- MongoDB Setup -----------------
# Not: URI'yi .env dosyasından çekmek en doğrusudur, şimdilik mevcut halini koruyoruz.
MONGODB_URI = "mongodb+srv://Kamlesh-21:Guru2004@attendencesystem.nlapsic.mongodb.net/Attendencesystem?retryWrites=true&w=majority&appName=Attendencesystem"
client = MongoClient(MONGODB_URI)
db = client['facerecognition_db']
collection = db['users']

# ----------------- Modelleri Yükle -----------------
detector = MTCNN()
# Göz kırpma tespiti için OpenCV'nin hazır modelini kullanacağız
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
if eye_cascade.empty():
    print("UYARI: 'haarcascade_eye.xml' bulunamadı! Göz kırpma çalışmayabilir.")
    # Manuel indirdiyseniz yolunu belirtin: cv2.CascadeClassifier('haarcascade_eye.xml')

# ----------------- Yardımcı Fonksiyonlar -----------------

def detect_faces(image):
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    faces = detector.detect_faces(rgb_image)
    face_data = []
    for face in faces:
        x, y, w, h = face['box']
        x, y = max(0, x), max(0, y)
        face_img = rgb_image[y:y+h, x:x+w]
        face_data.append({'box': (x, y, w, h), 'face': face_img})
    return face_data

def extract_embedding(face_img):
    try:
        # DeepFace analizi
        embedding = DeepFace.represent(face_img, model_name='Facenet512', detector_backend='skip')
        return embedding[0]['embedding']
    except Exception as e:
        return None

def check_blink(face_img_bgr):
    """
    Yüz bölgesinde gözleri arar.
    Göz bulunursa True (Göz Açık), bulunamazsa False (Göz Kapalı) döner.
    """
    gray_face = cv2.cvtColor(face_img_bgr, cv2.COLOR_BGR2GRAY)
    eyes = eye_cascade.detectMultiScale(gray_face, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20))
    return len(eyes) > 0

# ----------------- 1. Otomatik Kayıt (Değişmedi) -----------------
def auto_register_user(user_id, name, wait_time=5):
    cap = cv2.VideoCapture(0)
    print(f"{name} için yüz taranıyor. Lütfen {wait_time} saniye kameraya bakın...")
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret: break

        faces = detect_faces(frame)
        if len(faces) == 1:
            x, y, w, h = faces[0]['box']
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            if time.time() - start_time > wait_time:
                embedding = extract_embedding(faces[0]['face'])
                if embedding is not None:
                    user_data = {
                        'user_id': user_id,
                        'name': name,
                        'embedding': embedding
                    }
                    collection.insert_one(user_data)
                    print(f"Kayıt Başarılı: {name}")
                    log_access(user_id, name, "Registered") # Logla
                    break
        
        cv2.imshow("Kayit Ekrani", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

# ----------------- 2. Güvenli Canlı Tanıma (GÜNCELLENDİ) -----------------
def live_recognition():
    users = list(collection.find())
    if not users:
        print("Kayıtlı kullanıcı yok.")
        return

    threshold = 0.6 # Benzerlik eşiği (Daha güvenli olması için 0.7'den 0.6'ya çektim)
    cap = cv2.VideoCapture(0)
    
    # Canlılık Takibi için Değişkenler
    # Format: { 'track_id': { 'state': 'waiting', 'eyes_open_frames': 0, 'last_seen': time } }
    liveness_states = {} 
    
    print("Canlı Tanıma Başladı. Çıkış için 'q'.")

    while True:
        ret, frame = cap.read()
        if not ret: break

        faces = detect_faces(frame)

        for i, face_data in enumerate(faces):
            x, y, w, h = face_data['box']
            face_img_rgb = face_data['face'] # RGB formatında (MTCNN için)
            face_img_bgr = frame[y:y+h, x:x+w] # BGR formatında (OpenCV göz takibi için)

            # 1. Kimlik Tespiti
            embedding = extract_embedding(face_img_rgb)
            if embedding is None: continue

            best_match = None
            min_distance = float('inf')

            for user in users:
                dist = cosine(embedding, user['embedding'])
                if dist < min_distance:
                    min_distance = dist
                    best_match = user

            # Eşleşme Kontrolü
            if min_distance < threshold:
                user_id = best_match.get('user_id', 'Unknown')
                user_name = best_match['name']
                
                # --- CANLILIK (LIVENESS) MANTIĞI ---
                if user_id not in liveness_states:
                    liveness_states[user_id] = {'state': 'checking', 'frames': 0, 'blinked': False}
                
                state = liveness_states[user_id]
                eyes_open = check_blink(face_img_bgr)

                # Mantık: Gözler önce açık olmalı, sonra kapanmalı (blink), sonra tekrar açılmalı.
                # Basitleştirilmiş: Gözlerin kapalı olduğu bir an yakalamaya çalışıyoruz.
                
                if state['state'] == 'checking':
                    if not eyes_open: # Gözler kapalı (Blink yakalandı!)
                        state['blinked'] = True
                        state['state'] = 'verified'
                        # GÜVENLİK LOGU AT
                        log_access(user_id, user_name, "Granted")
                    
                    # Kullanıcıya Bilgi Ver
                    color = (0, 165, 255) # Turuncu (Bekliyor)
                    msg = "Goz Kirpin!"
                
                elif state['state'] == 'verified':
                    color = (0, 255, 0) # Yeşil (Onaylı)
                    msg = f"Hosgeldin {user_name}"
                    
                    # 5 saniye sonra durumu sıfırla ki tekrar kontrol etsin (veya bir kere yeterliyse kalabilir)
                    # state['frames'] += 1
                    # if state['frames'] > 100: liveness_states.pop(user_id)

                # Çizimler
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(frame, msg, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            else:
                # Tanınmayan Kişi
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, "Tanimsiz", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
                # Güvenlik Logu (Belli aralıklarla)
                # log_access("Unknown", "Bilinmeyen", "Denied")

        cv2.imshow("Guvenli Giris Sistemi", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

def main():
    while True:
        print("\n--- GÜVENLİ YÜZ TANIMA SİSTEMİ ---")
        print("1. Otomatik Kullanıcı Kaydı")
        print("2. Canlı Tanıma Başlat (Liveness Aktif)")
        print("3. Çıkış")
        choice = input("Seçiminiz: ")

        if choice == '1':
            uid = input("ID: ")
            name = input("İsim: ")
            auto_register_user(uid, name)
        elif choice == '2':
            live_recognition()
        elif choice == '3':
            break

if __name__ == "__main__":
    main()