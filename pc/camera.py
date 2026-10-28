"""Captura de vídeo (USB ou celular via IP Webcam), lendo sempre o frame mais recente."""
import sys
import threading
import time
import cv2
import config


class Captura:
    """Lê a câmera numa thread própria e guarda só o frame mais recente (sem atraso acumulado)."""

    def __init__(self, cap):
        self.cap = cap
        self.lock = threading.Lock()
        self.frame = None
        self.novo = False
        self.ok = True
        self.rodando = True
        self.thread = threading.Thread(target=self._ler, daemon=True)
        self.thread.start()

    def _ler(self):
        while self.rodando:
            ok, frame = self.cap.read()
            if not ok:
                self.ok = False
                return
            with self.lock:
                self.frame = frame
                self.novo = True

    def ler(self):
        while self.rodando and self.ok:
            with self.lock:
                if self.novo:
                    self.novo = False
                    return True, self.frame
            time.sleep(0.002)
        return False, None

    def parar(self):
        self.rodando = False
        self.thread.join(timeout=1.0)
        self.cap.release()


def adicionar_args_camera(parser):
    parser.add_argument("--camera", "-c", choices=["usb", "ip"], default="usb",
                        help="'usb' (padrão) ou 'ip' (celular na rede)")
    parser.add_argument("--usb-index", type=int, default=0, help="índice da câmera USB")
    parser.add_argument("--ip-url", type=str, default="",
                        help="URL do stream, ex: http://192.168.0.10:8080/video")
    parser.add_argument("--list-usb", action="store_true", help="lista câmeras USB e sai")


def _backend():
    return cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY


def listar_cameras_usb(max_test=10):
    print("Procurando câmeras USB...")
    achadas = []
    for i in range(max_test):
        cap = cv2.VideoCapture(i, _backend())
        if cap.isOpened() and cap.read()[0]:
            print(f"  Índice {i}: {int(cap.get(3))}x{int(cap.get(4))} - OK")
            achadas.append(i)
        cap.release()
    if not achadas:
        print("  Nenhuma câmera encontrada.")
    return achadas


def abrir_camera(args):
    if args.camera == "usb":
        cap = cv2.VideoCapture(args.usb_index, _backend())
        if not cap.isOpened():
            raise RuntimeError(f"Não foi possível abrir a câmera USB {args.usb_index}")
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.USB_LARGURA)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.USB_ALTURA)
        cap.set(cv2.CAP_PROP_FPS, config.USB_FPS)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap, f"USB {args.usb_index}"

    if not args.ip_url:
        raise RuntimeError("Use --ip-url http://IP:PORTA/video com a câmera IP")
    cap = cv2.VideoCapture(args.ip_url)
    if not cap.isOpened():
        raise RuntimeError(
            f"Não foi possível abrir {args.ip_url}\n"
            "  - PC e celular na mesma rede Wi-Fi?\n"
            "  - App IP Webcam rodando?\n"
            "  - URL termina em /video?")
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap, f"IP {args.ip_url}"
