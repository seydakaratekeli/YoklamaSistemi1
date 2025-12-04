import cv2
import os
import csv
import numpy as np

def TakeImage(l1, l2, haarcasecade_path, trainimage_path, message, err_screen, text_to_speech):
    if (l1 == "") or (l2 == ""):
        text_to_speech("Lütfen tüm alanları doldurun")
        err_screen("Alanlar boş bırakılamaz!")
    else:
        try:
            cam = cv2.VideoCapture(0)
            detector = cv2.CascadeClassifier(haarcasecade_path)
            
            Enrollment = l1
            Name = l2
            sampleNum = 0
            
            if not os.path.exists(trainimage_path):
                os.makedirs(trainimage_path)
            
            print(f"Kayıt Başladı: {Name}")
            
            while True:
                ret, img = cam.read()
                if not ret:
                    break
                    
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = detector.detectMultiScale(gray, 1.3, 5)
                
                for (x, y, w, h) in faces:
                    sampleNum = sampleNum + 1
                    
                    # 1. Fotoğrafı klasöre kaydet
                    file_name = f"{Name}.{Enrollment}.{sampleNum}.jpg"
                    cv2.imwrite(os.path.join(trainimage_path, file_name), gray[y : y + h, x : x + w])
                    
                    # 2. Ekrana çizim yap (Çerçeve ve Yazı)
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    # Sayacı pencere ismine değil, resmin üzerine yazıyoruz!
                    cv2.putText(img, f"Kaydediliyor: {sampleNum}/60", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # 3. Görüntüyü Göster (Pencere ismi SABİT olmalı)
                cv2.imshow("Ogrenci Kayit Ekrani", img)
                
                # Çıkış koşulları (60 fotoğraf dolunca veya Q'ya basınca)
                if cv2.waitKey(50) & 0xFF == ord("q"):
                    break
                elif sampleNum >= 60:
                    break
            
            cam.release()
            cv2.destroyAllWindows()
            
            # --- CSV KAYDI ---
            row = [Enrollment, Name]
            csv_path = "StudentDetails\\studentdetails.csv"
            
            # Klasör yoksa oluştur
            if not os.path.exists("StudentDetails"):
                os.makedirs("StudentDetails")

            file_exists = os.path.isfile(csv_path)
            
            with open(csv_path, "a+", newline="") as csvFile:
                writer = csv.writer(csvFile)
                if not file_exists:
                    writer.writerow(["Enrollment", "Name"])
                writer.writerow(row)
            
            res = f"Kayıt Tamamlandı: {Name} ({sampleNum} Fotoğraf)"
            message.configure(text=res, fg="#2ecc71")
            text_to_speech("Kayıt işlemi başarıyla tamamlandı")
            
        except Exception as e:
            message.configure(text=f"Hata: {e}", fg="red")
            text_to_speech("Kayıt sırasında hata oluştu")
            print(f"Hata detayı: {e}")