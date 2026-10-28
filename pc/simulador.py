"""Simulador: reproduz dados gravados/simulados pelo classificador e envia o alerta por MQTT.
NÃO usa câmera. Serve para testar o caminho completo: dados -> modelo -> MQTT -> ESP32 -> LED.

Uso:  python pc/simulador.py                      (usa dataset.csv se existir, senão o sintético)
      python pc/simulador.py --sessao 3           (escolhe outra sessão do arquivo)
      python pc/simulador.py --classe brusco      (reproduz só trechos dessa classe)
      python pc/simulador.py --rapido             (sem esperar o tempo real)
      python pc/simulador.py --sem-mqtt           (só mostra as previsões)
      python pc/simulador.py --demo               (toca normal, leve, médio e grave em sequência, com dados sintéticos)
"""
import argparse
import sys
import time
from collections import deque

import joblib
import numpy as np
import pandas as pd

import config
from features import features, NOMES_COLUNAS


def primeiro_trecho(d, rotulo):
    """Primeiro trecho contínuo de uma classe (ou None)."""
    rot = d["label"].to_numpy()
    if not (rot == rotulo).any():
        return None
    ini = int(np.argmax(rot == rotulo))
    fim = ini
    while fim < len(rot) and rot[fim] == rotulo:
        fim += 1
    return d.iloc[ini:fim]


def main():
    ap = argparse.ArgumentParser(description="Simulador de detecção com envio MQTT")
    ap.add_argument("--arquivo", default="", help="CSV a reproduzir (padrão: dataset.csv ou sintético)")
    ap.add_argument("--sessao", type=int, default=None,
                    help="posição da sessão no arquivo (padrão: a primeira que tiver a classe pedida)")
    ap.add_argument("--classe", default="todas", choices=["todas"] + config.CLASSES,
                    help="reproduz apenas trechos dessa classe")
    ap.add_argument("--rapido", action="store_true", help="não espera o tempo real entre frames")
    ap.add_argument("--demo", action="store_true",
                    help="demonstração: um trecho de cada gravidade em sequência (usa o dataset sintético)")
    ap.add_argument("--sintetico", action="store_true", help="força o dataset sintético")
    ap.add_argument("--sem-mqtt", action="store_true", help="não envia comando ao ESP32")
    args = ap.parse_args()

    if not config.MODELO_CLASSIFICADOR.exists():
        sys.exit(f"ERRO: classificador não encontrado: {config.MODELO_CLASSIFICADOR}\n"
                 "Rode antes: python treinamento/treino.py")

    if args.demo or args.sintetico:
        caminho = config.DATASET_SINTETICO
    else:
        caminho = args.arquivo or (config.DATASET if config.DATASET.exists() else config.DATASET_SINTETICO)
    df = pd.read_csv(caminho)
    sessoes = sorted(df["sessao"].unique())
    contagem = df["label"].map(dict(enumerate(config.CLASSES))).value_counts()
    resumo = ", ".join(f"{c}: {n}" for c, n in contagem.items())

    if args.demo:
        d0 = df[df["sessao"] == sessoes[0]].sort_values("t")
        partes = [primeiro_trecho(d0, r) for r in (0, 1, 2, 3)]     # normal, leve, médio, grave
        d = pd.concat([x.head(300) for x in partes if x is not None])
        d = d.copy()
        d["t"] = float(d["t"].iloc[0]) + np.arange(len(d)) / 30.0   # horários contínuos (30 FPS)
        args.classe, args.sessao = "todas", 0
    else:
        if args.sessao is None:
            if args.classe == "todas":
                args.sessao = 0
            else:
                rotulo = config.CLASSES.index(args.classe)
                com_classe = [i for i, sid in enumerate(sessoes)
                              if (df[df["sessao"] == sid]["label"] == rotulo).any()]
                if not com_classe:
                    sys.exit(f"Nada para reproduzir: o arquivo não tem nenhuma linha da classe '{args.classe}'.\n"
                             f"Linhas por classe neste arquivo -> {resumo}\n"
                             "Grave essa classe com coleta.py (tecla correspondente + ESPAÇO) ou use o dataset sintético "
                             "(renomeie/mova dados/dataset.csv).")
                args.sessao = com_classe[0]
        if not 0 <= args.sessao < len(sessoes):
            sys.exit(f"Sessão inválida. O arquivo tem {len(sessoes)} sessões (0 a {len(sessoes) - 1}).")
        d = df[df["sessao"] == sessoes[args.sessao]].sort_values("t")
        if args.classe != "todas":
            d = d[d["label"] == config.CLASSES.index(args.classe)]
        if d.empty:
            sys.exit(f"Nada para reproduzir: a sessão {args.sessao} não tem a classe '{args.classe}'.\n"
                     f"Linhas por classe no arquivo -> {resumo}\n"
                     "Rode sem --sessao (ele procura a classe em outra sessão) ou grave essa classe.")

    print("Frames por classe neste trecho: " +
          ", ".join(f"{c}: {n}" for c, n in d["label"].map(dict(enumerate(config.CLASSES))).value_counts().items()))
    if args.classe == "todas" and not args.demo and (d["label"] == 2).sum() == 0:
        print("AVISO: este trecho NÃO tem movimento brusco, então não haverá alerta médio. "
              "Use --demo, --sintetico ou --classe brusco.")

    modelo = joblib.load(config.MODELO_CLASSIFICADOR)
    if not args.sem_mqtt:
        import mqtt_cliente
        mqtt_cliente.iniciar()
        time.sleep(1.5)       # dá tempo de conectar ao broker

    print(f"Arquivo: {caminho.name if hasattr(caminho, 'name') else caminho} | "
          f"sessão {args.sessao} | {len(d)} frames | classe: {args.classe}")

    tempos_arq = d["t"].to_numpy()
    rotulos = d["label"].to_numpy()
    dados = d[NOMES_COLUNAS].to_numpy()

    buffer = deque(maxlen=config.JANELA)
    confirmacoes = deque(maxlen=config.CONFIRMACOES)
    desde, ultimo_alerta, alertas = 0, -1e9, 0

    try:
        for i in range(len(d)):
            t = float(tempos_arq[i])
            if i > 0 and not args.rapido:
                time.sleep(min(max(t - tempos_arq[i - 1], 0), 1.0))   # reproduz o ritmo (pausas limitadas a 1 s)
            if i > 0 and rotulos[i] != rotulos[i - 1]:                # novo trecho: reinicia a análise
                buffer.clear()
                confirmacoes.clear()
                desde = 0
                print(f"--- trecho real: {config.CLASSES[int(rotulos[i])]} ---")
            elif i == 0:
                print(f"--- trecho real: {config.CLASSES[int(rotulos[0])]} ---")

            buffer.append((t, dados[i]))
            desde += 1
            if len(buffer) < config.JANELA or desde < config.PASSO:
                continue
            desde = 0

            proba = modelo.predict_proba(
                features([b[1] for b in buffer], [b[0] for b in buffer])[None, :])[0]
            k = int(np.argmax(proba))
            classe, conf = int(modelo.classes_[k]), float(proba[k])
            anormal = classe != 0 and conf >= config.CONFIANCA_MIN
            confirmacoes.append(classe if anormal else 0)
            print(f"  previsto: {config.CLASSES[classe]:<13} ({conf:4.0%})  real: {config.CLASSES[int(rotulos[i])]}")

            if (len(confirmacoes) == confirmacoes.maxlen and all(c != 0 for c in confirmacoes)
                    and t - ultimo_alerta >= config.INTERVALO_ALERTA):
                ultimo_alerta = t
                alertas += 1
                print(f"* ALERTA: {config.CLASSES[classe]} (confiança {conf:.0%}) *")
                if not args.sem_mqtt:
                    mqtt_cliente.enviar_alerta(classe)
                confirmacoes.clear()
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        print(f"Fim. Alertas disparados: {alertas}")
        if not args.sem_mqtt:
            time.sleep(0.5)
            mqtt_cliente.parar()


if __name__ == "__main__":
    main()