import cv2
import os
import numpy as np
from PIL import Image
import security_utils # Şifreleme için

def getImagesAndLabels(path):
    imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
    faces = []
    Ids = []
    
    for imagePath in imagePaths:
        try:
            # Görüntüyü yükle ve griye çevir
            pilImage = Image.open(imagePath).convert("L")
            imageNp = np.array(pilImage, "uint8")
            
            # Dosya adından ID'yi al (Isim.ID.Numara.jpg)
            Id = int(os.path.split(imagePath)[-1].split(".")[1])
            
            faces.append(imageNp)
            Ids.append(Id)
        except:
            continue
            
    return faces, Ids

def TrainImage(haarcasecade_path, trainimage_path, trainimagelabel_path, message, text_to_speech):
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        detector = cv2.CascadeClassifier(haarcasecade_path)
        
        faces, Id = getImagesAndLabels(trainimage_path)
        
        if len(faces) == 0:
            message.configure(text="Eğitilecek fotoğraf bulunamadı!", fg="red")
            text_to_speech("Klasör boş")
            return

        recognizer.train(faces, np.array(Id))
        
        # Modeli kaydet (Önce normal .yml olarak)
        if not os.path.exists("TrainingImageLabel"):
            os.makedirs("TrainingImageLabel")
            
        recognizer.save(trainimagelabel_path)
        
        # --- MODELİ ŞİFRELE (GÜVENLİK) ---
        try:
            security_utils.encrypt_file(trainimagelabel_path)
            msg_add = " (ve Şifrelendi)"
        except:
            msg_add = ""
        # ---------------------------------
        
        res = f"Model Eğitildi{msg_add}. Toplam Öğrenci: {len(np.unique(Id))}"
        message.configure(text=res, fg="#2ecc71")
        text_to_speech("Model başarıyla eğitildi")
        
    except Exception as e:
        message.configure(text=f"Eğitim Hatası: {str(e)}", fg="red")
        text_to_speech("Model eğitimi başarısız")