"""Gera dados/dataset_sintetico.csv: movimentos SIMULADOS por equações.

ATENÇÃO: serve só para testar se o pipeline (treino -> modelo -> detector) funciona.
NÃO use como dataset final: o resultado dá quase 100% porque os dados são "limpos".
Para a entrega, grave dados reais com pc/coleta.py.
"""
import sys
from pathlib import Path
from pc import config

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pc"))
import CLASSES
import DATASET_SINTETICO
import NOMES_COLUNAS

rng = np.random.default_rng(42)
FPS = 30
# nariz, pulso_e, pulso_d, cotovelo_e, cotovelo_d, tornozelo_e, tornozelo_d, ombro_e  (x, y)
BASE = np.array([0, -0.9, 0.6, 1.6, -0.6, 1.6, 0.8, 0.9, -0.8, 0.9, 0.4, 5.0, -0.4, 5.0, 0.5, 0.0])
NARIZ, PUL_E, PUL_D, COT_E, COT_D, TOR_E, TOR_D = range(7)


def idx(p):
    return slice(2 * p, 2 * p + 2)


def base_com_ruido(n, sigma):
    x = np.zeros((n, 16))
    for i in range(1, n):                      # deriva lenta
        x[i] = 0.98 * x[i - 1] + rng.normal(0, 0.004, 16)
    return BASE + x + rng.normal(0, sigma, (n, 16))


def perfil(subida, parado, descida):
    return np.concatenate([np.linspace(0, 1, subida), np.ones(parado), np.linspace(1, 0, descida)])


def aplicar_evento(dados, inicio, p, deslocamento, prof, coef_cotovelo=0.5):
    fim = min(inicio + len(prof), len(dados))
    pr = prof[: fim - inicio, None]
    dados[inicio:fim, idx(p)] += pr * deslocamento
    cot = COT_E if p == PUL_E else COT_D if p == PUL_D else None
    if cot is not None:
        dados[inicio:fim, idx(cot)] += pr * deslocamento * coef_cotovelo


def seg_normal(n, sigma, esc):
    d = base_com_ruido(n, sigma)
    tt = np.arange(n) / FPS
    if rng.random() < 0.5:                                      # andando
        f, a = rng.uniform(0.8, 1.2), rng.uniform(0.08, 0.2) * esc
        d[:, idx(TOR_E).start] += a * np.sin(2 * np.pi * f * tt)
        d[:, idx(TOR_D).start] -= a * np.sin(2 * np.pi * f * tt)
    for _ in range(rng.integers(1, 3)):                         # gesto lento
        p = rng.choice([PUL_E, PUL_D])
        f, a = rng.uniform(0.2, 0.6), rng.uniform(0.2, 0.5) * esc
        fase = rng.uniform(0, 6.28)
        d[:, idx(p)] += a * np.sin(2 * np.pi * f * tt + fase)[:, None] * rng.uniform(-1, 1, 2)
    for _ in range(rng.integers(1, 3)):                         # mão lenta até o rosto (coçar/beber)
        p = rng.choice([PUL_E, PUL_D])
        ini = rng.integers(0, max(1, n - 90))
        alvo = BASE[idx(NARIZ)] - BASE[idx(p)] + rng.normal(0, 0.15, 2)
        aplicar_evento(d, ini, p, alvo, perfil(rng.integers(35, 55), rng.integers(10, 30), rng.integers(35, 55)))
    return d


def seg_repetitivo(n, sigma, esc):
    d = base_com_ruido(n, sigma)
    tt = np.arange(n) / FPS
    parte = rng.choice(["cabeca", "braco", "perna"])
    if parte == "cabeca":
        p, a, f = NARIZ, rng.uniform(0.05, 0.12), rng.uniform(1.5, 3.5)
    elif parte == "braco":
        p, a, f = rng.choice([PUL_E, PUL_D]), rng.uniform(0.25, 0.6), rng.uniform(2, 4)
    else:
        p, a, f = rng.choice([TOR_E, TOR_D]), rng.uniform(0.2, 0.4), rng.uniform(2, 4)
    direcao = rng.choice([[1, 0], [0, 1], [1, 1]])
    onda = a * esc * np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28))[:, None] * direcao
    d[:, idx(p)] += onda
    if p in (PUL_E, PUL_D):
        d[:, idx(COT_E if p == PUL_E else COT_D)] += 0.5 * onda
    return d


def seg_brusco(n, sigma, esc):
    d = base_com_ruido(n, sigma)
    for ini in np.sort(rng.choice(np.arange(0, n - 25), size=rng.integers(3, 6), replace=False)):
        p = rng.choice([PUL_E, PUL_D])
        ang = rng.uniform(0, 6.28)
        mag = rng.uniform(1.2, 2.5) * esc
        aplicar_evento(d, ini, p, mag * np.array([np.cos(ang), np.sin(ang)]), perfil(6, 3, 8))
    return d


def seg_golpe(n, sigma, esc):
    d = base_com_ruido(n, sigma)
    for ini in np.sort(rng.choice(np.arange(0, n - 25), size=rng.integers(4, 7), replace=False)):
        p = rng.choice([PUL_E, PUL_D])
        alvo = BASE[idx(NARIZ)] - BASE[idx(p)] + rng.normal(0, 0.15, 2)
        aplicar_evento(d, ini, p, alvo, perfil(5, 2, 10))
    return d


GERADORES = [seg_normal, seg_repetitivo, seg_brusco, seg_golpe]

linhas = []
for s in range(10):                                   # 10 "sessões" de gravação
    sessao = 1_700_000_000 + s * 1000
    esc, sigma = rng.uniform(0.8, 1.2), rng.uniform(0.005, 0.015)
    ordem = rng.permutation(np.repeat(np.arange(4), 2))
    t = float(sessao)
    for label in ordem:
        n = int(rng.integers(240, 420))
        dados = GERADORES[label](n, sigma, esc)
        tempos = t + np.cumsum(1 / FPS + rng.normal(0, 0.002, n))
        df = pd.DataFrame(np.round(dados, 5), columns=NOMES_COLUNAS)
        df.insert(0, "label", label)
        df.insert(0, "t", np.round(tempos, 4))
        df.insert(0, "sessao", sessao)
        linhas.append(df)
        t = tempos[-1] + 1.0                           # pausa entre trechos

saida = pd.concat(linhas, ignore_index=True)
DATASET_SINTETICO.parent.mkdir(exist_ok=True)
saida.to_csv(DATASET_SINTETICO, index=False)
print(f"Gerado {DATASET_SINTETICO} com {len(saida)} linhas")
print(saida["label"].map(dict(enumerate(CLASSES))).value_counts())
