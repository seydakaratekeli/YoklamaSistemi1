import csv
import os, cv2
import numpy as np
import pandas as pd
import datetime
import time
from PIL import ImageTk, Image
import security_utils

import csv
import os, cv2
import numpy as np
import pandas as pd
import datetime
import time
from PIL import ImageTk, Image
import security_utils  # <--- Şifreleme modülü eklendi

# Train Image
def TrainImage(haarcasecade_path, trainimage_path, trainimagelabel_path, message, text_to_speech):
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    detector = cv2.CascadeClassifier(haarcasecade_path)
    
    # Yüzleri ve etiketleri al
    faces, Id = getImagesAndLables(trainimage_path)
    
    # Modeli eğit
    recognizer.train(faces, np.array(Id))
    
    # 1. Modeli normal olarak kaydet
    recognizer.save(trainimagelabel_path)
    
    # 2. Şifreleme İşlemi (YENİ EKLENEN KISIM)
    try:
        print("Şifreleme başlatılıyor...")
        security_utils.encrypt_file(trainimagelabel_path)
        print(f"Model şifrelendi: {trainimagelabel_path} -> .enc")
        res = "Model Egitildi ve Sifrelendi (AES-256)"
    except Exception as e:
        print(f"Sifreleme Hatasi: {str(e)}")
        res = "Model Egitildi ama Sifreleme BASARISIZ"

    # Mesajı ekrana yaz ve seslendir
    message.configure(text=res)
    text_to_speech(res)

def getImagesAndLables(path):
    # imagePath = [os.path.join(path, f) for d in os.listdir(path) for f in d]
    newdir = [os.path.join(path, d) for d in os.listdir(path)]
    imagePath = [
        os.path.join(newdir[i], f)
        for i in range(len(newdir))
        for f in os.listdir(newdir[i])
    ]
    faces = []
    Ids = []
    for imagePath in imagePath:
        pilImage = Image.open(imagePath).convert("L")
        imageNp = np.array(pilImage, "uint8")
        Id = int(os.path.split(imagePath)[-1].split("_")[1])
        faces.append(imageNp)
        Ids.append(Id)
    return faces, Ids