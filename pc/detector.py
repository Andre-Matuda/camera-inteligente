"""Detector em tempo real: câmera -> MediaPipe -> classificador treinado -> MQTT -> ESP32.

Uso:  python pc/detector.py
      python pc/detector.py --camera ip --ip-url http://IP:PORTA/video
      python pc/detector.py --sem-mqtt        (testa sem enviar ao ESP32)
"""
import argparse
import sys
import time
from collections import deque

import cv2
import joblib
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

import config
import mqtt_cliente
from camera import Captura, abrir_camera, adicionar_args_camera, listar_cameras_usb
from desenho import desenhar_esqueleto, escrever
from features import extrair_vetor, features


def main():
    parser = argparse.ArgumentParser(description="Detector de movimentos repetitivos/bruscos")
    adicionar_args_camera(parser)
    parser.add_argument("--sem-mqtt", action="store_true", help="não envia comando ao ESP32")
    args = parser.parse_args()
    if args.list_usb:
        listar_cameras_usb()
        return

    if not config.MODELO_POSE.exists():
        sys.exit(f"ERRO: modelo não encontrado: {config.MODELO_POSE}\nRode: python baixar_modelos.py")
    if not config.MODELO_CLASSIFICADOR.exists():
        sys.exit(f"ERRO: classificador não encontrado: {config.MODELO_CLASSIFICADOR}\n"
                 "Rode o notebook treinamento/treino.ipynb (ou python treinamento/treino.py).")

    modelo = joblib.load(config.MODELO_CLASSIFICADOR)
    detector = vision.PoseLandmarker.create_from_options(
        vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(config.MODELO_POSE)),
            running_mode=vision.RunningMode.VIDEO, num_poses=1))

    if not args.sem_mqtt:
        mqtt_cliente.iniciar()

    try:
        cap, desc = abrir_camera(args)
    except RuntimeError as e:
        sys.exit(f"ERRO: {e}")
    print(f"Câmera aberta: {desc}. Pressione 'q' para sair.")

    captura = Captura(cap)
    buffer = deque(maxlen=config.JANELA)            # (tempo, vetor)
    confirmacoes = deque(maxlen=config.CONFIRMACOES)
    desde_ultima, classe, conf = 0, 0, 1.0
    ultimo_alerta, ultimo_ts, fps, t_ant = 0.0, 0, 0.0, None

    try:
        while True:
            ok, frame = captura.ler()
            if not ok:
                print("Falha ao ler a câmera. Tentando reconectar...")
                time.sleep(0.5)
                captura.parar()
                try:
                    cap, _ = abrir_camera(args)
                except RuntimeError as e:
                    print(f"ERRO: {e}")
                    time.sleep(2)
                    cap = cv2.VideoCapture()
                captura = Captura(cap)
                continue

            if config.LARGURA_PROCESSAMENTO and frame.shape[1] > config.LARGURA_PROCESSAMENTO:
                f = config.LARGURA_PROCESSAMENTO / frame.shape[1]
                frame = cv2.resize(frame, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)

            agora = time.time()
            if t_ant is not None:
                fps = 0.9 * fps + 0.1 / max(agora - t_ant, 1e-3)
            t_ant = agora
            ts = max(int(agora * 1000), ultimo_ts + 1)
            ultimo_ts = ts

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = detector.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
            h, w = frame.shape[:2]

            vec = None
            if res.pose_landmarks:
                lm = res.pose_landmarks[0]
                desenhar_esqueleto(frame, lm, w, h)
                vec = extrair_vetor(lm, w, h)

            if vec is None:                                  # sem pessoa/ombros: reinicia a análise
                buffer.clear()
                confirmacoes.clear()
                desde_ultima, classe, conf = 0, 0, 1.0
            else:
                buffer.append((agora, vec))
                desde_ultima += 1
                if len(buffer) == config.JANELA and desde_ultima >= config.PASSO:
                    desde_ultima = 0
                    tempos = [b[0] for b in buffer]
                    janela = [b[1] for b in buffer]
                    proba = modelo.predict_proba(features(janela, tempos)[None, :])[0]
                    i = int(np.argmax(proba))
                    classe, conf = int(modelo.classes_[i]), float(proba[i])
                    anormal = classe != 0 and conf >= config.CONFIANCA_MIN
                    confirmacoes.append(classe if anormal else 0)

                    if (len(confirmacoes) == confirmacoes.maxlen
                            and all(c != 0 for c in confirmacoes)
                            and agora - ultimo_alerta >= config.INTERVALO_ALERTA):
                        ultimo_alerta = agora
                        print(f"* ALERTA: {config.CLASSES[classe]} (confiança {conf:.0%}) *")
                        if not args.sem_mqtt:
                            mqtt_cliente.piscar_led()
                        confirmacoes.clear()

            alerta = classe != 0 and conf >= config.CONFIANCA_MIN
            escrever(frame, f"FPS:{fps:.0f}", (10, 28))
            escrever(frame, f"{config.CLASSES[classe]} ({conf:.0%})", (10, 58),
                     (0, 0, 255) if alerta else (0, 255, 0), 0.8)
            if agora - ultimo_alerta < 1.5:
                escrever(frame, "ALERTA ENVIADO", (10, 92), (0, 0, 255), 0.9)

            cv2.imshow("Detector", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        captura.parar()
        mqtt_cliente.parar()
        cv2.destroyAllWindows()
        print("Encerrado.")


if __name__ == "__main__":
    main()
