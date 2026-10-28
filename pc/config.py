"""Configurações compartilhadas por coleta, treino e detector.
Se mudar JANELA ou PASSO, é preciso treinar o modelo de novo."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# ---------- arquivos ----------
MODELO_POSE = RAIZ / "modelos" / "pose_landmarker_full.task"
MODELO_CLASSIFICADOR = RAIZ / "modelos" / "modelo_movimento.joblib"
DATASET = RAIZ / "dados" / "dataset.csv"                      # gravado por vocês (coleta.py)
DATASET_SINTETICO = RAIZ / "dados" / "dataset_sintetico.csv"  # só para testar o pipeline

# ---------- classes ----------
CLASSES = ["normal", "repetitivo", "brusco", "golpe_cabeca"]

# ---------- janela de análise ----------
JANELA = 45   # frames por janela (~1,5 s a 30 FPS)
PASSO = 15    # a cada quantos frames o modelo é consultado

# ---------- decisão do alerta ----------
CONFIANCA_MIN = 0.70    # probabilidade mínima para considerar a classe
CONFIRMACOES = 2        # janelas seguidas "anormais" antes de alertar
INTERVALO_ALERTA = 5.0  # segundos entre alertas (o padrão mais longo do LED dura 5 s)

# ---------- visão ----------
VISIBILIDADE_MIN = 0.5
ESCALA_MINIMA_PX = 20          # largura mínima dos ombros (px) para analisar
LARGURA_PROCESSAMENTO = 640    # reduz o frame antes da IA (0 = não reduzir)
USB_LARGURA, USB_ALTURA, USB_FPS = 640, 480, 30

# ---------- MQTT (ESP32) ----------
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_LED = "camera-esp32-x7k2/led"
MQTT_CLIENT_ID = "detector-pc-x7k2"

# ---------- gravidade -> padrão de piscadas no ESP32 ----------
# classe detectada -> gravidade (mude aqui se quiser outra classificação)
GRAVIDADE_POR_CLASSE = {1: "leve", 2: "medio", 3: "grave"}   # repetitivo, brusco, golpe_cabeca
# gravidade -> comando enviado por MQTT ("1" pisca lento, "2" médio, "3" rápido)
COMANDO_POR_GRAVIDADE = {"leve": "1", "medio": "2", "grave": "3"}