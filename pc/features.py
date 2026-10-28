"""Extração de pontos e cálculo das features.
Sem OpenCV/MediaPipe: é usado igual na coleta, no treino (notebook) e no detector."""
import math
import numpy as np
from config import VISIBILIDADE_MIN, ESCALA_MINIMA_PX

# Índices do MediaPipe Pose
NARIZ = 0
OMBRO_E, OMBRO_D = 11, 12
COTOVELO_E, COTOVELO_D = 13, 14
PULSO_E, PULSO_D = 15, 16
QUADRIL_E, QUADRIL_D = 23, 24
TORNOZELO_E, TORNOZELO_D = 27, 28

PONTOS = [NARIZ, PULSO_E, PULSO_D, COTOVELO_E, COTOVELO_D,
          TORNOZELO_E, TORNOZELO_D, OMBRO_E]
NOMES_PONTOS = ["nariz", "pulso_e", "pulso_d", "cotovelo_e", "cotovelo_d",
                "tornozelo_e", "tornozelo_d", "ombro_e"]
NOMES_COLUNAS = [f"{n}_{e}" for n in NOMES_PONTOS for e in "xy"]   # 16 colunas

NOMES_FEATURES = (
    [f"std_{c}" for c in NOMES_COLUNAS]
    + [f"amp_{c}" for c in NOMES_COLUNAS]
    + [f"velmed_{p}" for p in NOMES_PONTOS]
    + [f"velmax_{p}" for p in NOMES_PONTOS]
    + [f"inversoes_{c}" for c in NOMES_COLUNAS]
    + ["dmin_pulso_e_nariz", "dmin_pulso_d_nariz",
       "dmed_pulso_e_nariz", "dmed_pulso_d_nariz"]
)

AMPLITUDE_INVERSAO = 0.03   # em larguras de ombro


def visivel(lm, i):
    vis = lm[i].visibility
    return vis is None or vis >= VISIBILIDADE_MIN


def extrair_vetor(lm, w, h):
    """Devolve 16 números (x,y de 8 pontos) normalizados pelo centro e largura dos ombros.
    Assim não importa se a pessoa está perto ou longe da câmera. None se não der para medir."""
    if not (visivel(lm, OMBRO_E) and visivel(lm, OMBRO_D)):
        return None
    oe = (lm[OMBRO_E].x * w, lm[OMBRO_E].y * h)
    od = (lm[OMBRO_D].x * w, lm[OMBRO_D].y * h)
    escala = math.dist(oe, od)
    if escala < ESCALA_MINIMA_PX:
        return None
    cx, cy = (oe[0] + od[0]) / 2, (oe[1] + od[1]) / 2
    vec = []
    for i in PONTOS:
        vec += [(lm[i].x * w - cx) / escala, (lm[i].y * h - cy) / escala]
    return vec


def _inversoes(x, amp=AMPLITUDE_INVERSAO):
    """Conta mudanças de direção com amplitude mínima (ignora ruído pequeno)."""
    ext, direcao, n = x[0], 0, 0
    for v in x[1:]:
        if direcao == 0:
            if abs(v - ext) > amp:
                direcao = 1 if v > ext else -1
                ext = v
        elif direcao == 1:
            if v > ext:
                ext = v
            elif ext - v > amp:
                direcao, ext = -1, v
                n += 1
        else:
            if v < ext:
                ext = v
            elif v - ext > amp:
                direcao, ext = 1, v
                n += 1
    return n


def features(janela, tempos):
    """janela: (n, 16) | tempos: (n,) em segundos -> vetor de features da janela."""
    w = np.asarray(janela, dtype=float)
    t = np.asarray(tempos, dtype=float)
    dt = np.maximum(np.diff(t), 1e-3)[:, None]
    d = np.diff(w, axis=0)
    vel = np.linalg.norm(d.reshape(len(d), -1, 2), axis=2) / dt     # (n-1, 8)
    inv = np.array([_inversoes(w[:, j]) for j in range(w.shape[1])], dtype=float)
    pts = w.reshape(len(w), -1, 2)
    d_pe = np.linalg.norm(pts[:, 1] - pts[:, 0], axis=1)            # pulso E - nariz
    d_pd = np.linalg.norm(pts[:, 2] - pts[:, 0], axis=1)            # pulso D - nariz
    extra = np.array([d_pe.min(), d_pd.min(), d_pe.mean(), d_pd.mean()])
    return np.concatenate([w.std(0), np.ptp(w, axis=0),
                           vel.mean(0), vel.max(0), inv, extra])
