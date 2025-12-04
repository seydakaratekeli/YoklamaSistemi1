import tkinter as tk
from tkinter import *
import os
import cv2
import csv
import numpy as np
from PIL import ImageTk, Image
import pandas as pd
import datetime
import time
import tkinter.font as font
import pyttsx3
import hashlib
import re

# Modüller
import show_attendance
import takeImage
import trainImage
import automaticAttedance

# --- AYARLAR ---
ADMIN_PASS_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9" # Şifre: 'admin123'
AUTO_LOCK_TIME = 60 # 60 saniye hareketsizlikte kilitler

# --- GLOBAL DEĞİŞKENLER ---
last_activity_time = time.time()
is_locked = True 
login_window_ref = None 
engine = None

# --- SES MOTORU ---
try:
    engine = pyttsx3.init()
except:
    print("⚠️ Uyarı: Ses motoru başlatılamadı.")

def text_to_speech(user_text):
    if engine:
        try:
            engine.say(user_text)
            engine.runAndWait()
        except: pass
    else:
        print(f"Ses: {user_text}")

# --- DOSYA YOLLARI ---
haarcasecade_path = "haarcascade_frontalface_default.xml"
trainimagelabel_path = "./TrainingImageLabel/Trainner.yml"
trainimage_path = "TrainingImage"
if not os.path.exists(trainimage_path): os.makedirs(trainimage_path)
studentdetail_path = "./StudentDetails/studentdetails.csv"
attendance_path = "Attendance"

# --- ANA PENCERE ---
window = Tk()
window.title("Yüz Tanıma ile Yoklama Sistemi")
window.geometry("1280x720")
window.configure(background="#2c3e50")
window.withdraw() 

# --- GÜVENLİK FONKSİYONLARI ---
def validate_input(text):
    pattern = r'^[a-zA-Z0-9_ğüşıöçĞÜŞİÖÇ ]+$'
    return bool(re.match(pattern, text))

def check_password(password):
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return hashed == ADMIN_PASS_HASH

# --- OTO-KİLİT (AUTO-LOCK) MEKANİZMASI ---
def reset_timer(event=None):
    global last_activity_time
    last_activity_time = time.time()

def check_inactivity():
    global is_locked
    # Kilitli değilse ve süre dolmuşsa kilitle
    if not is_locked and (time.time() - last_activity_time > AUTO_LOCK_TIME):
        lock_session()
    # Her 1 saniyede bir kontrol et
    window.after(1000, check_inactivity)

def lock_session():
    global is_locked
    is_locked = True
    window.withdraw() 
    text_to_speech("Oturum zaman aşımına uğradı")
    # Eğer login penceresi açık değilse aç
    if login_window_ref is None or not login_window_ref.winfo_exists():
        login_screen()

# Kullanıcı hareketlerini dinle
window.bind_all('<Any-KeyPress>', reset_timer)
window.bind_all('<Any-Button>', reset_timer)
window.bind_all('<Motion>', reset_timer)

# --- LOGIN EKRANI (RATE LIMITING İLE) ---
def login_screen():
    global login_window_ref
    login_win = Toplevel()
    login_window_ref = login_win 
    
    login_win.title("Yönetici Girişi")
    login_win.geometry("400x350")
    login_win.configure(background="#34495e")
    login_win.resizable(False, False)
    
    # Ortala
    screen_width = login_win.winfo_screenwidth()
    screen_height = login_win.winfo_screenheight()
    x = (screen_width/2) - (400/2)
    y = (screen_height/2) - (350/2)
    login_win.geometry('%dx%d+%d+%d' % (400, 350, x, y))

    login_win.protocol("WM_DELETE_WINDOW", lambda: os._exit(0)) 

    tk.Label(login_win, text="GÜVENLİK KONTROLÜ", bg="#34495e", fg="#e74c3c", font=("Helvetica", 18, "bold")).pack(pady=20)
    tk.Label(login_win, text="Yönetici Şifresi:", bg="#34495e", fg="white", font=("Helvetica", 12)).pack()
    
    pass_entry = tk.Entry(login_win, show="*", width=20, font=("Helvetica", 16))
    pass_entry.pack(pady=10)
    pass_entry.focus()

    lbl_msg = tk.Label(login_win, text="", bg="#34495e", fg="yellow", font=("Helvetica", 10))
    lbl_msg.pack()

    # Rate Limiting Değişkenleri
    state = {'attempts': 0, 'lockout_time': 0, 'max_attempts': 3, 'lockout_duration': 30}

    def attempt_login(event=None):
        global is_locked, last_activity_time
        current_time = time.time()
        
        # Ceza Kontrolü
        if current_time < state['lockout_time']:
            remaining = int(state['lockout_time'] - current_time)
            lbl_msg.config(text=f"Çok deneme yaptınız! {remaining} sn bekleyin.", fg="#f39c12")
            return

        password = pass_entry.get()
        
        if check_password(password):
            # Giriş Başarılı
            is_locked = False
            last_activity_time = time.time()
            login_win.destroy()
            window.deiconify() 
            text_to_speech("Hoşgeldiniz")
        else:
            # Giriş Başarısız
            state['attempts'] += 1
            if state['attempts'] >= state['max_attempts']:
                state['lockout_time'] = time.time() + state['lockout_duration']
                state['attempts'] = 0
                lbl_msg.config(text=f"SİSTEM KİLİTLENDİ! {state['lockout_duration']} sn bekleyin.", fg="red")
                text_to_speech("Sistem geçici olarak kilitlendi")
                
                # Inputları kapat
                pass_entry.delete(0, END)
                pass_entry.config(state='disabled')
                
                def unlock():
                    if login_win.winfo_exists():
                        pass_entry.config(state='normal')
                        lbl_msg.config(text="Tekrar deneyebilirsiniz.", fg="#2ecc71")
                        pass_entry.focus()
                
                login_win.after(state['lockout_duration'] * 1000, unlock)
            else:
                lbl_msg.config(text=f"Hatalı Şifre! Kalan Hak: {state['max_attempts'] - state['attempts']}", fg="#e74c3c")
                pass_entry.delete(0, END)

    btn = tk.Button(login_win, text="GİRİŞ", command=attempt_login, bg="#2ecc71", fg="white", font=("Helvetica", 12, "bold"), width=15)
    btn.pack(pady=20)
    login_win.bind('<Return>', attempt_login)

# --- DİĞER FONKSİYONLAR ---
def add_button_hover(btn, color_enter, color_leave):
    btn.bind("<Enter>", func=lambda e: btn.config(background=color_enter))
    btn.bind("<Leave>", func=lambda e: btn.config(background=color_leave))

def del_sc1(): sc1.destroy()

def err_screen(msg="Hata Oluştu"):
    global sc1
    sc1 = tk.Toplevel(window)
    sc1.geometry("400x120")
    sc1.title("Uyarı")
    sc1.configure(background="#2c3e50")
    sc1.resizable(False, False)
    sc1.geometry(f"+{window.winfo_x() + 440}+{window.winfo_y() + 300}")
    tk.Label(sc1, text=msg, fg="#e74c3c", bg="#2c3e50", font=("Helvetica", 12, "bold")).pack(pady=20)
    tk.Button(sc1, text="Tamam", command=del_sc1, fg="white", bg="#e74c3c", width=10).pack()

def testVal(inStr, acttyp):
    if acttyp == "1": 
        if not inStr.isdigit(): return False
    return True

# --- ICON YÜKLEME ---
try:
    logo_img = Image.open("UI_Image/0001.png")
    logo_img = logo_img.resize((50, 50), Image.LANCZOS)
    logo_tk = ImageTk.PhotoImage(logo_img, master=window) # master=window EKLENDİ
    l1 = tk.Label(window, image=logo_tk, bg="#2c3e50")
    l1.place(x=40, y=10)
except: pass

title_frame = tk.Frame(window, bg="#34495e", height=80)
title_frame.pack(fill=X)
tk.Label(title_frame, text="YOKLAMA SİSTEMİ", bg="#34495e", fg="#ecf0f1", font=("Helvetica", 28, "bold")).place(relx=0.5, rely=0.5, anchor=CENTER)

tk.Label(window, text="Yönetici Paneli", bg="#2c3e50", fg="#f1c40f", font=("Helvetica", 20, "italic")).pack(pady=20)

def load_icon(path):
    try:
        img = Image.open(path)
        img = img.resize((180, 180), Image.LANCZOS)
        return ImageTk.PhotoImage(img, master=window) # master=window EKLENDİ
    except: return None

icon_reg = load_icon("UI_Image/register.png")
icon_ver = load_icon("UI_Image/verifyy.png")
icon_att = load_icon("UI_Image/attendance.png")

if icon_reg: tk.Label(window, image=icon_reg, bg="#2c3e50").place(x=150, y=200)
if icon_ver: tk.Label(window, image=icon_ver, bg="#2c3e50").place(x=550, y=200)
if icon_att: tk.Label(window, image=icon_att, bg="#2c3e50").place(x=950, y=200)

def TakeImageUI():
    ImageUI = Toplevel(window)
    ImageUI.title("Öğrenci Kaydı")
    ImageUI.geometry("800x500")
    ImageUI.configure(background="#34495e")
    
    tk.Label(ImageUI, text="Öğrenci Kayıt Formu", bg="#34495e", fg="#ecf0f1", font=("Helvetica", 24, "bold")).pack(pady=20)
    form_frame = tk.Frame(ImageUI, bg="#34495e")
    form_frame.pack(pady=20)

    tk.Label(form_frame, text="Öğrenci No:", bg="#34495e", fg="white", font=("Helvetica", 14)).grid(row=0, column=0, padx=10, pady=10, sticky=E)
    txt1 = tk.Entry(form_frame, width=20, font=("Helvetica", 14), validate="key")
    txt1["validatecommand"] = (txt1.register(testVal), "%P", "%d")
    txt1.grid(row=0, column=1, padx=10, pady=10)

    tk.Label(form_frame, text="Ad Soyad:", bg="#34495e", fg="white", font=("Helvetica", 14)).grid(row=1, column=0, padx=10, pady=10, sticky=E)
    txt2 = tk.Entry(form_frame, width=20, font=("Helvetica", 14))
    txt2.grid(row=1, column=1, padx=10, pady=10)

    message = tk.Label(form_frame, text="", bg="#34495e", fg="#f1c40f", font=("Helvetica", 12, "bold"))
    message.grid(row=2, column=1, padx=10, pady=10)

    def take_image():
        l1 = txt1.get()
        l2 = txt2.get()
        if not l1 or not l2:
            message.configure(text="Alanlar boş bırakılamaz!", fg="red")
            return
        if not validate_input(l2):
            err_screen("Sadece harf ve rakam kullanın!")
            return
        takeImage.TakeImage(l1, l2, haarcasecade_path, trainimage_path, message, err_screen, text_to_speech)
        txt1.delete(0, "end")
        txt2.delete(0, "end")

    def train_image():
        trainImage.TrainImage(haarcasecade_path, trainimage_path, trainimagelabel_path, message, text_to_speech)

    btn_frame = tk.Frame(ImageUI, bg="#34495e")
    btn_frame.pack(pady=30)
    b1 = tk.Button(btn_frame, text="Fotoğraf Çek", command=take_image, bg="#3498db", fg="white", font=("Helvetica", 14, "bold"), width=15, relief=FLAT)
    b1.pack(side=LEFT, padx=20)
    add_button_hover(b1, "#2980b9", "#3498db")
    b2 = tk.Button(btn_frame, text="Modeli Eğit", command=train_image, bg="#2ecc71", fg="white", font=("Helvetica", 14, "bold"), width=15, relief=FLAT)
    b2.pack(side=LEFT, padx=20)
    add_button_hover(b2, "#27ae60", "#2ecc71")

def automatic_attedance(): automaticAttedance.subjectChoose(text_to_speech)
def view_attendance(): show_attendance.subjectchoose(text_to_speech)

btn_font = ("Helvetica", 14, "bold")
b_reg = tk.Button(window, text="Yeni Öğrenci Kaydı", command=TakeImageUI, bg="#3498db", fg="white", font=btn_font, width=20, height=2, relief=FLAT)
b_reg.place(x=130, y=450)
add_button_hover(b_reg, "#2980b9", "#3498db")

b_att = tk.Button(window, text="Yoklama Başlat", command=automatic_attedance, bg="#2ecc71", fg="white", font=btn_font, width=20, height=2, relief=FLAT)
b_att.place(x=530, y=450)
add_button_hover(b_att, "#27ae60", "#2ecc71")

b_view = tk.Button(window, text="Listeyi Görüntüle", command=view_attendance, bg="#9b59b6", fg="white", font=btn_font, width=20, height=2, relief=FLAT)
b_view.place(x=930, y=450)
add_button_hover(b_view, "#8e44ad", "#9b59b6")

b_exit = tk.Button(window, text="ÇIKIŞ", command=window.destroy, bg="#e74c3c", fg="white", font=btn_font, width=15, height=1, relief=FLAT)
b_exit.place(relx=0.5, y=600, anchor=CENTER)
add_button_hover(b_exit, "#c0392b", "#e74c3c")

tk.Label(window, text="Gelişmiş Yüz Tanıma & Güvenlik Sistemi v3.0", bg="#2c3e50", fg="#95a5a6", font=("Helvetica", 10)).pack(side=BOTTOM, pady=10)

# --- BAŞLATMA ---
login_screen()
check_inactivity() # Zamanlayıcıyı başlat
window.mainloop()