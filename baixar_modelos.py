"""Baixa os modelos oficiais do MediaPipe para a pasta modelos/."""
import os
import urllib.request

BASE = "https://storage.googleapis.com/mediapipe-models"
ARQUIVOS = {
    "modelos/pose_landmarker_full.task":
        f"{BASE}/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task",
    # opcional (o classificador atual não usa as mãos):
    "modelos/hand_landmarker.task":
        f"{BASE}/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
}

os.makedirs("modelos", exist_ok=True)
for destino, url in ARQUIVOS.items():
    if os.path.exists(destino):
        print("Já existe:", destino)
        continue
    print("Baixando", destino, "...")
    urllib.request.urlretrieve(url, destino)
print("Pronto.")
