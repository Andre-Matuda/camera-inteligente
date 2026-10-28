# Câmera inteligente: detecção de movimentos repetitivos e bruscos (ESP32 + IA)

Uma câmera (USB ou celular) filma a pessoa. O **MediaPipe** extrai os pontos do corpo, um **classificador
treinado por nós** (RandomForest) analisa janelas de ~1,5 s e, ao detectar movimento anormal, o PC envia
`B` por **MQTT**. O **ESP32** recebe e acende o LED por 3 s.

```
Câmera → MediaPipe (pontos) → janela → features → classificador → MQTT → ESP32 → LED
```

## Classes
`0 normal` · `1 repetitivo` · `2 brusco` · `3 golpe_cabeca`

## Estrutura
```
pc/            coleta.py, detector.py, features.py, config.py, camera.py, desenho.py, mqtt_cliente.py
treinamento/   treino.ipynb (e treino.py), gerar_dataset_sintetico.py, gerar_notebook.py
esp32/         esp32_led_mqtt/ (firmware .ino + secrets.h)
dados/         dataset.csv (gravado por nós) | dataset_sintetico.csv (só para testar)
modelos/       modelos do MediaPipe (.task) e modelo_movimento.joblib (gerado no treino)
testes/        registro_testes.md, evidências
docs/          analise.md, esquema de montagem
```

## Como usar
1. `pip install -r requirements.txt`
2. `python baixar_modelos.py` (baixa os modelos do MediaPipe para `modelos/`)
3. **Coletar dados reais:** `python pc/coleta.py`
   (teclas `0-3` escolhem a classe, `ESPAÇO` grava/pausa, `q` sai).
   Use `--camera ip --ip-url http://IP:PORTA/video` para o celular.
4. **Treinar:** abra `treinamento/treino.ipynb` e execute tudo (ou `python treinamento/treino.py`).
   Gera `modelos/modelo_movimento.joblib` e `testes/metricas_treino.txt`.
   Sem `dados/dataset.csv` ele usa o dataset sintético, só para testar o pipeline.
5. **ESP32:** instale a biblioteca *PubSubClient*, edite `secrets.h` (Wi-Fi), selecione a placa
   *ESP32 Wrover Module* (ou Dev Module) e grave `esp32_led_mqtt.ino`. LED no pino 2 (com resistor).
6. **Rodar:** `python pc/detector.py` (use `--sem-mqtt` para testar sem o ESP32).

## Dicas de coleta
- Grave vários minutos por classe, em sessões diferentes (luz, roupa, distância, pessoas).
- Em `normal` inclua andar, gesticular, coçar o rosto, beber água.
- Mostre da cintura para cima pelo menos (ombros e braços visíveis).
- Se mudar `JANELA`/`PASSO` em `config.py`, treine de novo.

## Limitações conhecidas
Ver `docs/analise.md`. O broker público (HiveMQ) é aberto: use tópico único e, em produção, broker próprio com autenticação/TLS.
