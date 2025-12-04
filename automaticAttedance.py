import tkinter as tk
from tkinter import *
import os, cv2
import shutil
import csv
import numpy as np
from PIL import ImageTk, Image
import pandas as pd
import datetime
import time
import tkinter.ttk as tkk
import tkinter.font as font
import security_utils  # <--- GUVENLIK MODULU EKLENDI

haarcasecade_path = "haarcascade_frontalface_default.xml"
trainimagelabel_path = "TrainingImageLabel\\Trainner.yml"
trainimage_path = "TrainingImage"
studentdetail_path = "StudentDetails\\studentdetails.csv"
attendance_path = "Attendance"

def subjectChoose(text_to_speech):
    def FillAttendance():
        sub = tx.get()
        now = time.time()
        future = now + 20
        print(now)
        print(future)
        if sub == "":
            t = "Please enter the subject name!!!"
            text_to_speech(t)
        else:
            try:
                # --- 1. SIFRELI MODELI COZME (AES-256) ---
                print("Model kilidi aciliyor...")
                recognizer = cv2.face.LBPHFaceRecognizer_create()
                
                # Şifreli ve normal dosya yolları
                enc_path = "TrainingImageLabel\\Trainner.enc"
                yml_path = "TrainingImageLabel\\Trainner.yml"
                temp_model_path = None
                
                # Eğer şifreli dosya varsa çöz
                if os.path.exists(enc_path):
                    temp_model_path = security_utils.decrypt_file_temp(enc_path)
                
                # Modeli yüklemeyi dene
                try:
                    if temp_model_path and os.path.exists(temp_model_path):
                        recognizer.read(temp_model_path)
                    elif os.path.exists(yml_path):
                        recognizer.read(yml_path) # Şifresiz varsa onu oku
                    else:
                        raise Exception("Model dosyasi bulunamadi!")
                except:
                    e = "Model not found, please train model"
                    Notifica.configure(text=e, bg="black", fg="yellow", width=33, font=("times", 15, "bold"))
                    Notifica.place(x=20, y=250)
                    text_to_speech(e)
                    return
                # ---------------------------------------------

                facecasCade = cv2.CascadeClassifier(haarcasecade_path)
                df = pd.read_csv(studentdetail_path)
                cam = cv2.VideoCapture(0)
                font = cv2.FONT_HERSHEY_SIMPLEX
                col_names = ["Enrollment", "Name"]
                attendance = pd.DataFrame(columns=col_names)
                
                # --- ANTI-SPOOFING DEGISKENLERI ---
                prev_face = None
                is_real_face = False
                # ----------------------------------

                while True:
                    ___, im = cam.read()
                    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
                    faces = facecasCade.detectMultiScale(gray, 1.2, 5)
                    
                    for (x, y, w, h) in faces:
                        
                        # --- 2. ANTI-SPOOFING (HAREKET KONTROLU) ---
                        face_roi = gray[y:y+h, x:x+w]
                        if prev_face is not None:
                            # Boyutları eşitle ve farkı al
                            prev_resize = cv2.resize(prev_face, (w, h))
                            diff = cv2.absdiff(face_roi, prev_resize)
                            motion_score = np.mean(diff)
                            
                            # Hareket eşiği (3.0 iyi bir başlangıçtır)
                            if motion_score > 3.0:
                                is_real_face = True
                                cv2.putText(im, "CANLI", (x, y-30), font, 0.8, (0, 255, 0), 2)
                            else:
                                is_real_face = False
                                cv2.putText(im, "SAHTE/FOTO", (x, y-30), font, 0.8, (0, 0, 255), 2)
                        prev_face = face_roi
                        # -------------------------------------------

                        global Id
                        Id, conf = recognizer.predict(gray[y : y + h, x : x + w])
                        
                        if conf < 70:
                            print(conf)
                            global Subject
                            global aa
                            global date
                            global timeStamp
                            Subject = tx.get()
                            ts = time.time()
                            date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                            timeStamp = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                            aa = df.loc[df["Enrollment"] == Id]["Name"].values
                            global tt
                            tt = str(Id) + "-" + aa
                            
                            # SADECE GERÇEK KİŞİYSE KAYDET
                            if is_real_face:
                                attendance.loc[len(attendance)] = [Id, aa]
                                cv2.rectangle(im, (x, y), (x + w, y + h), (0, 260, 0), 4)
                                cv2.putText(im, str(tt), (x + h, y), font, 1, (255, 255, 0,), 4)
                                
                                # --- 3. LOGLAMA (BASARILI) ---
                                try:
                                    clean_name = str(aa).replace("['","").replace("']","")
                                    security_utils.log_access(Id, clean_name, "Granted")
                                except: pass
                                # -----------------------------
                            else:
                                # SAHTE İSE UYARI VER
                                cv2.rectangle(im, (x, y), (x + w, y + h), (0, 0, 255), 4)
                                # --- 3. LOGLAMA (SALDIRI) ---
                                security_utils.log_access(Id, "Saldirgan", "Spoof")
                                
                        else:
                            Id = "Unknown"
                            tt = str(Id)
                            cv2.rectangle(im, (x, y), (x + w, y + h), (0, 25, 255), 7)
                            cv2.putText(im, str(tt), (x + h, y), font, 1, (0, 25, 255), 4)
                            
                            # --- 3. LOGLAMA (RED) ---
                            security_utils.log_access("Bilinmiyor", "Unknown", "Denied")
                            # ------------------------

                    if time.time() > future:
                        break

                    attendance = attendance.drop_duplicates(["Enrollment"], keep="first")
                    cv2.imshow("Filling Attendance...", im)
                    key = cv2.waitKey(30) & 0xFF
                    if key == 27:
                        break
                
                # --- GUVENLIK TEMIZLIGI: GEÇİCİ DOSYAYI SIL ---
                if temp_model_path and os.path.exists(temp_model_path):
                    os.remove(temp_model_path)
                    print("Gecici sifresiz model silindi.")
                # ----------------------------------------------

                ts = time.time()
                print(aa)
                attendance[date] = 1
                date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                timeStamp = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                Hour, Minute, Second = timeStamp.split(":")
                path = os.path.join(attendance_path, Subject)
                if not os.path.exists(path):
                    os.makedirs(path)
                fileName = (
                    f"{path}/"
                    + Subject
                    + "_"
                    + date
                    + "_"
                    + Hour
                    + "-"
                    + Minute
                    + "-"
                    + Second
                    + ".csv"
                )
                attendance = attendance.drop_duplicates(["Enrollment"], keep="first")
                print(attendance)
                attendance.to_csv(fileName, index=False)

                m = "Attendance Filled Successfully of " + Subject
                Notifica.configure(
                    text=m,
                    bg="black",
                    fg="yellow",
                    width=33,
                    relief=RIDGE,
                    bd=5,
                    font=("times", 15, "bold"),
                )
                text_to_speech(m)
                Notifica.place(x=20, y=250)

                cam.release()
                cv2.destroyAllWindows()

                import tkinter
                root = tkinter.Tk()
                root.title("Attendance of " + Subject)
                root.configure(background="black")
                cs = os.path.join(path, fileName)
                print(cs)
                with open(cs, newline="") as file:
                    reader = csv.reader(file)
                    r = 0
                    for col in reader:
                        c = 0
                        for row in col:
                            label = tkinter.Label(
                                root,
                                width=10,
                                height=1,
                                fg="yellow",
                                font=("times", 15, " bold "),
                                bg="black",
                                text=row,
                                relief=tkinter.RIDGE,
                            )
                            label.grid(row=r, column=c)
                            c += 1
                        r += 1
                root.mainloop()
                print(attendance)
            except Exception as e:
                f = "No Face found for attendance"
                print(f"HATA: {e}")
                text_to_speech(f)
                cv2.destroyAllWindows()

    ###windo is frame for subject chooser
    subject = Tk()
    subject.title("Subject...")
    subject.geometry("580x320")
    subject.resizable(0, 0)
    subject.configure(background="black")
    
    titl = tk.Label(subject, bg="black", relief=RIDGE, bd=10, font=("arial", 30))
    titl.pack(fill=X)
    
    titl = tk.Label(
        subject,
        text="Enter the Subject Name",
        bg="black",
        fg="green",
        font=("arial", 25),
    )
    titl.place(x=160, y=12)
    Notifica = tk.Label(
        subject,
        text="Attendance filled Successfully",
        bg="yellow",
        fg="black",
        width=33,
        height=2,
        font=("times", 15, "bold"),
    )

    def Attf():
        sub = tx.get()
        if sub == "":
            t = "Please enter the subject name!!!"
            text_to_speech(t)
        else:
            os.startfile(
                f"Attendance\\{sub}"
            )

    attf = tk.Button(
        subject,
        text="Check Sheets",
        command=Attf,
        bd=7,
        font=("times new roman", 15),
        bg="black",
        fg="yellow",
        height=2,
        width=10,
        relief=RIDGE,
    )
    attf.place(x=360, y=170)

    sub = tk.Label(
        subject,
        text="Enter Subject",
        width=10,
        height=2,
        bg="black",
        fg="yellow",
        bd=5,
        relief=RIDGE,
        font=("times new roman", 15),
    )
    sub.place(x=50, y=100)

    tx = tk.Entry(
        subject,
        width=15,
        bd=5,
        bg="black",
        fg="yellow",
        relief=RIDGE,
        font=("times", 30, "bold"),
    )
    tx.place(x=190, y=100)

    fill_a = tk.Button(
        subject,
        text="Fill Attendance",
        command=FillAttendance,
        bd=7,
        font=("times new roman", 15),
        bg="black",
        fg="yellow",
        height=2,
        width=12,
        relief=RIDGE,
    )
    fill_a.place(x=195, y=170)
    subject.mainloop()