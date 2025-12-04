import tkinter as tk
from tkinter import *
import os, cv2
import csv
import numpy as np
import pandas as pd
import datetime
import time
import security_utils  # Guvenlik modulu

# --- AYARLAR ---
haarcasecade_path = "haarcascade_frontalface_default.xml"
eye_cascade_path = "haarcascade_eye.xml"
trainimagelabel_path = "TrainingImageLabel\\Trainner.yml"
studentdetail_path = "StudentDetails\\studentdetails.csv"
attendance_path = "Attendance"

def subjectChoose(text_to_speech):
    def FillAttendance():
        sub = tx.get()
        now = time.time()
        future = now + 40 # Yoklama süresi (saniye)
        
        if sub == "":
            text_to_speech("Lütfen ders adını giriniz")
            return
        
        # --- 1. MODEL YÜKLEME ---
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        temp_model_path = None
        
        try:
            enc_path = "TrainingImageLabel\\Trainner.enc"
            yml_path = "TrainingImageLabel\\Trainner.yml"
            
            if os.path.exists(enc_path):
                print("🔒 Şifreli model çözülüyor...")
                temp_model_path = security_utils.decrypt_file_temp(enc_path)
                if temp_model_path:
                    recognizer.read(temp_model_path)
                else:
                    raise Exception("Şifre çözülemedi")
            elif os.path.exists(yml_path):
                recognizer.read(yml_path)
            else:
                raise Exception("Model bulunamadı")
        except Exception as e:
            Notifica.configure(text="Model Hatasi", bg="black", fg="red")
            text_to_speech("Model hatası")
            return

        # --- KAMERA VE MODELLER ---
        facecasCade = cv2.CascadeClassifier(haarcasecade_path)
        eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
        
        if eye_cascade.empty():
            print("HATA: 'haarcascade_eye.xml' bulunamadı!")
            return

        # Öğrenci listesini yükle
        if os.path.exists(studentdetail_path):
            df = pd.read_csv(studentdetail_path)
        else:
            text_to_speech("Öğrenci listesi bulunamadı")
            return

        cam = cv2.VideoCapture(0)
        font = cv2.FONT_HERSHEY_SIMPLEX
        col_names = ["Enrollment", "Name", "Date", "Time"]
        attendance = pd.DataFrame(columns=col_names)
        
        # Canlılık takibi
        liveness_states = {} 
        
        try:
            while True:
                ret, im = cam.read()
                if not ret: break
                
                gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
                faces = facecasCade.detectMultiScale(gray, 1.2, 5)
                
                for (x, y, w, h) in faces:
                    Id, conf = recognizer.predict(gray[y:y+h, x:x+w])
                    roi_gray = gray[y:y+h, x:x+w]
                    
                    if conf < 70:
                        aa = df.loc[df["Enrollment"] == Id]["Name"].values
                        name_str = str(aa[0]) if len(aa) > 0 else "Unknown"
                        
                        # Güvenlik Mantığı
                        if Id not in liveness_states:
                            liveness_states[Id] = {'state': 0, 'counter': 0}
                        
                        user_data = liveness_states[Id]
                        state = user_data['state']
                        
                        if state != 3:
                            eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20))
                            eyes_detected = len(eyes) >= 1
                            
                            if state == 0: # Göz ara
                                if eyes_detected:
                                    user_data['counter'] += 1
                                    if user_data['counter'] >= 3:
                                        user_data['state'] = 1
                                        user_data['counter'] = 0
                                else: user_data['counter'] = 0

                            elif state == 1: # Kırpma bekle
                                if not eyes_detected: 
                                    user_data['counter'] += 1
                                    if user_data['counter'] >= 1:
                                        user_data['state'] = 2
                                        user_data['counter'] = 0
                                else: user_data['counter'] = 0

                            elif state == 2: # Açılmasını bekle
                                if eyes_detected:
                                    user_data['state'] = 3
                                    ts = time.time()
                                    date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                                    timeStamp = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                                    attendance.loc[len(attendance)] = [Id, name_str, date, timeStamp]
                                    try: security_utils.log_access(Id, name_str, "Granted")
                                    except: pass

                            # Mesajlar
                            if state == 0: msg, col = "KAMERAYA BAKIN", (0, 255, 255)
                            elif state == 1: msg, col = "GOZ KIRPIN!", (0, 165, 255)
                            elif state == 2: msg, col = "ACILIYOR...", (255, 0, 255)

                            cv2.rectangle(im, (x, y), (x + w, y + h), col, 3)
                            cv2.putText(im, msg, (x, y-30), font, 0.8, col, 2)
                        
                        else:
                            # Onaylı
                            cv2.rectangle(im, (x, y), (x + w, y + h), (0, 255, 0), 3)
                            cv2.putText(im, f"HOSGELDIN {name_str}", (x, y-30), font, 0.8, (0, 255, 0), 2)

                    else:
                        cv2.rectangle(im, (x, y), (x + w, y + h), (0, 0, 255), 3)
                        cv2.putText(im, "TANIMSIZ", (x, y+h), font, 1, (0, 0, 255), 2)

                if time.time() > future:
                    break
                
                cv2.imshow("Guvenli Yoklama Sistemi", im)
                if cv2.waitKey(1) & 0xFF == 27: break
        
        finally:
            # --- KRİTİK DÜZELTME: Kamerayı ve Pencereleri ÖNCE kapat ---
            cam.release()
            cv2.destroyAllWindows()
            cv2.waitKey(1) # Pencerelerin tamamen kapanması için minik bekleme

        # --- KAYDETME VE LİSTELEME ---
        if temp_model_path and os.path.exists(temp_model_path):
            try: os.remove(temp_model_path)
            except: pass
            
        if not attendance.empty:
            attendance = attendance.drop_duplicates(["Enrollment"], keep="first")
            
            sub_path = os.path.join(attendance_path, sub)
            if not os.path.exists(sub_path): os.makedirs(sub_path)
            
            ts = time.time()
            date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            timeStamp = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            file_name = f"{sub}_{date}_{timeStamp.replace(':','-')}.csv"
            save_path = os.path.join(sub_path, file_name)
            
            attendance.to_csv(save_path, index=False)
            
            # --- YENİ: DOSYAYI İMZALA (BÜTÜNLÜK KORUMASI) ---
            security_utils.sign_file(save_path)
            # ------------------------------------------------
            
            Notifica.configure(text=f"Yoklama Alındı: {sub}", bg="black", fg="yellow")
            text_to_speech("Yoklama tamamlandı")
            
            # --- LİSTE EKRANI (Kamera kapandıktan sonra açılıyor) ---
            root = tk.Tk()
            root.title(f"Yoklama Listesi - {sub}")
            root.configure(background="black")
            
            main_frame = Frame(root, bg="black")
            main_frame.pack(fill=BOTH, expand=1)
            
            canvas = Canvas(main_frame, bg="black")
            canvas.pack(side=LEFT, fill=BOTH, expand=1)
            
            scrollbar = Scrollbar(main_frame, orient=VERTICAL, command=canvas.yview)
            scrollbar.pack(side=RIGHT, fill=Y)
            
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            
            inner_frame = Frame(canvas, bg="black")
            canvas.create_window((0,0), window=inner_frame, anchor="nw")
            
            with open(save_path, newline="") as file:
                reader = csv.reader(file)
                for r, col in enumerate(reader):
                    for c, row in enumerate(col):
                        label = tk.Label(inner_frame, width=15, height=1, fg="yellow", bg="black", text=row, relief=tk.RIDGE)
                        label.grid(row=r, column=c)
            
            root.mainloop()
        else:
            Notifica.configure(text="Kimse tespit edilemedi", bg="black", fg="red")

    # --- ARAYÜZ ---
    subject = Tk()
    subject.title("Ders Seçimi")
    subject.geometry("580x320")
    subject.configure(background="black")
    
    tk.Label(subject, text="DERS ADINI GIRINIZ", bg="black", fg="green", font=("arial", 25)).pack(pady=20)
    tx = tk.Entry(subject, width=15, font=("times", 30, "bold"))
    tx.pack()
    
    Notifica = tk.Label(subject, text="", bg="black", fg="yellow", font=("times", 15, "bold"))
    Notifica.pack(pady=10)

    tk.Button(subject, text="Yoklamayı Başlat", command=FillAttendance, bg="green", fg="white", font=("arial", 15)).pack(pady=20)
    
    subject.mainloop()