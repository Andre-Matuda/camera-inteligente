"""Grava dados rotulados em dados/dataset.csv.

Teclas:  0 normal | 1 repetitivo | 2 brusco | 3 golpe_cabeca
         ESPAÇO liga/desliga a gravação | q sai
Uso:     python pc/coleta.py            (câmera USB 0)
         python pc/coleta.py --camera ip --ip-url http://IP:PORTA/video
"""
import argparse
import csv
import sys
import time
from collections import Counter

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

import config
from camera import Captura, abrir_camera, adicionar_args_camera, listar_cameras_usb
from desenho import desenhar_esqueleto, escrever
from features import extrair_vetor, NOMES_COLUNAS


def main():
    parser = argparse.ArgumentParser(description="Coleta de dados rotulados")
    adicionar_args_camera(parser)
    args = parser.parse_args()
    if args.list_usb:
        listar_cameras_usb()
        return

    if not config.MODELO_POSE.exists():
        sys.exit(f"ERRO: modelo não encontrado: {config.MODELO_POSE}\nRode: python baixar_modelos.py")

    detector = vision.PoseLandmarker.create_from_options(
        vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(config.MODELO_POSE)),
            running_mode=vision.RunningMode.VIDEO, num_poses=1))

    try:
        cap, desc = abrir_camera(args)
    except RuntimeError as e:
        sys.exit(f"ERRO: {e}")
    print(f"Câmera aberta: {desc}")
    print("0 normal | 1 repetitivo | 2 brusco | 3 golpe_cabeca | ESPAÇO grava/pausa | q sai")

    config.DATASET.parent.mkdir(exist_ok=True)
    novo = not config.DATASET.exists()
    arq = open(config.DATASET, "a", newline="")
    wr = csv.writer(arq)
    if novo:
        wr.writerow(["sessao", "t", "label"] + NOMES_COLUNAS)

    sessao = int(time.time())          # identifica esta gravação (usado para separar treino/teste)
    label, gravando, ultimo_ts = 0, False, 0
    contagem = Counter()
    captura = Captura(cap)

    try:
        while True:
            ok, frame = captura.ler()
            if not ok:
                print("Falha ao ler a câmera.")
                break
            if config.LARGURA_PROCESSAMENTO and frame.shape[1] > config.LARGURA_PROCESSAMENTO:
                f = config.LARGURA_PROCESSAMENTO / frame.shape[1]
                frame = cv2.resize(frame, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)

            agora = time.time()
            ts = max(int(agora * 1000), ultimo_ts + 1)
            ultimo_ts = ts
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = detector.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)

            h, w = frame.shape[:2]
            if res.pose_landmarks:
                lm = res.pose_landmarks[0]
                desenhar_esqueleto(frame, lm, w, h)
                vec = extrair_vetor(lm, w, h)
                if gravando and vec is not None:
                    wr.writerow([sessao, f"{agora:.4f}", label] + [f"{v:.5f}" for v in vec])
                    contagem[label] += 1

            cor = (0, 0, 255) if gravando else (0, 255, 255)
            escrever(frame, f"{'GRAVANDO' if gravando else 'PAUSADO'}  classe: {label} - {config.CLASSES[label]}",
                     (10, 28), cor)
            escrever(frame, "  ".join(f"{i}:{contagem[i]}" for i in range(len(config.CLASSES))),
                     (10, 56), (0, 255, 0))

            cv2.imshow("Coleta", frame)
            k = cv2.waitKey(1) & 0xFF
            if k == ord("q"):
                break
            if k == ord(" "):
                gravando = not gravando
            if k in (ord("0"), ord("1"), ord("2"), ord("3")):
                label = int(chr(k))
    finally:
        captura.parar()
        arq.close()
        cv2.destroyAllWindows()
        print("Linhas gravadas por classe:", dict(contagem))
        print(f"Arquivo: {config.DATASET}")


if __name__ == "__main__":
    main()
