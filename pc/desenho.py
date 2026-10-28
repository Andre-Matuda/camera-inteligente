"""Funções de desenho na janela do OpenCV."""
import unicodedata
import cv2
from features import visivel

LIGACOES_CORPO = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32),
]


def sem_acento(texto):
    """O OpenCV não desenha acentos."""
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def _pt(lm, i, w, h):
    return (int(lm[i].x * w), int(lm[i].y * h))


def desenhar_esqueleto(frame, lm, w, h):
    for a, b in LIGACOES_CORPO:
        if visivel(lm, a) and visivel(lm, b):
            cv2.line(frame, _pt(lm, a, w, h), _pt(lm, b, w, h), (200, 200, 200), 2)
    for i in range(len(lm)):
        if visivel(lm, i):
            cv2.circle(frame, _pt(lm, i, w, h), 3, (255, 255, 0), -1)


def escrever(frame, texto, pos, cor=(0, 255, 0), escala=0.6, espessura=2):
    cv2.putText(frame, sem_acento(texto), pos, cv2.FONT_HERSHEY_SIMPLEX,
                escala, cor, espessura)
