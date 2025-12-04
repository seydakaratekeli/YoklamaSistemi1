import tkinter as tk
from tkinter import *
import os
import csv
import time
import security_utils # Bütünlük kontrolü için şart

def subjectchoose(text_to_speech):
    def calculate_attendance():
        root = tk.Tk()
        root.title("Yoklama Listesi")
        root.geometry("600x500")
        root.configure(background="black")
        
        sub = tx.get()
        if sub == "":
            text_to_speech("Lütfen ders adını giriniz")
            root.destroy(); return

        attendance_path = os.path.join("Attendance", sub)
        
        if not os.path.exists(attendance_path):
            text_to_speech("Kayıt bulunamadı")
            root.destroy(); return

        file_list = [f for f in os.listdir(attendance_path) if f.endswith('.csv')]
        if not file_list:
            text_to_speech("Dosya yok")
            root.destroy(); return
            
        latest_file = max([os.path.join(attendance_path, f) for f in file_list], key=os.path.getmtime)
        
        # --- BÜTÜNLÜK KONTROLÜ ---
        is_valid, msg = security_utils.verify_file_integrity(latest_file)
        
        status_color = "green" if is_valid else "red"
        status_text = f"DOSYA DURUMU: {msg}"
        
        if not is_valid:
            text_to_speech("Uyarı! Dosya bütünlüğü bozulmuş.")
            try: security_utils.log_access("SYSTEM", os.path.basename(latest_file), "Tampered")
            except: pass
        # -------------------------

        try:
            frame = Frame(root); frame.pack(fill=BOTH, expand=1)
            canvas = Canvas(frame, bg="black"); canvas.pack(side=LEFT, fill=BOTH, expand=1)
            scrollbar = Scrollbar(frame, orient=VERTICAL, command=canvas.yview); scrollbar.pack(side=RIGHT, fill=Y)
            canvas.configure(yscrollcommand=scrollbar.set); canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            inner_frame = Frame(canvas, bg="black"); canvas.create_window((0,0), window=inner_frame, anchor="nw")

            # --- DÜZELTİLEN KISIM BURASI (Durum Başlığı Eklendi) ---
            # 1. Satır: Dosya Durumu (Yeşil veya Kırmızı)
            tk.Label(inner_frame, text=status_text, fg=status_color, bg="black", font=("arial", 12, "bold")).grid(row=0, column=0, columnspan=4, pady=10)
            
            # 2. Satır: Dosya Adı (Beyaz)
            tk.Label(inner_frame, text=f"Dosya: {os.path.basename(latest_file)}", fg="white", bg="black", font=("arial", 10)).grid(row=1, column=0, columnspan=4)
            # -------------------------------------------------------

            with open(latest_file, newline="") as file:
                reader = csv.reader(file)
                for r, col in enumerate(reader):
                    for c, row in enumerate(col):
                        label = tk.Label(inner_frame, width=15, height=1, fg="yellow", font=("times", 12, "bold"), bg="black", text=row, relief=tk.RIDGE)
                        # row+2 yapıyoruz çünkü üstte 2 satır başlık var
                        label.grid(row=r+2, column=c)

            text_to_speech("Liste açıldı")
            root.mainloop()

        except Exception as e:
            print(e)
            text_to_speech("Dosya okuma hatası")

    subject = Tk()
    subject.title("Ders Seçimi")
    subject.geometry("500x250")
    subject.configure(background="#2c3e50")
    subject.resizable(0,0)
    
    tk.Label(subject, text="Ders Adını Giriniz", bg="#2c3e50", fg="white", font=("Helvetica", 20, "bold")).pack(pady=20)
    tx = tk.Entry(subject, width=20, font=("Helvetica", 18)); tx.pack(pady=10)
    btn = tk.Button(subject, text="Listeyi Getir", command=calculate_attendance, bg="#3498db", fg="white", font=("Helvetica", 14), width=15)
    btn.pack(pady=20)
    
    subject.mainloop()