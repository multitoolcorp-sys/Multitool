"""
input_simulator.py
Motor de simulación de periféricos de ultra-baja latencia y captura global
para Windows usando la API Win32 nativa (user32.dll), con puente de señales
100% seguro para PyQt6 para evitar congelamientos de la interfaz gráfica.
"""

import sys
import time
import ctypes
from ctypes import wintypes, byref, Structure, c_long
import threading
from PyQt6.QtCore import QObject, pyqtSignal

# Cargar User32
try:
    user32 = ctypes.windll.user32
except Exception:
    user32 = None

# Constantes de Eventos de Ratón
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

# Constantes de Teclado
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# Mapeo Completo de Códigos Virtuales (VK) a Nombres
VK_TO_NAME = {
    0x08: "BACKSPACE", 0x09: "TAB", 0x0D: "ENTER", 0x10: "SHIFT",
    0x11: "CTRL", 0x12: "ALT", 0x13: "PAUSE", 0x14: "BLOQ MAYUS",
    0x1B: "ESC", 0x20: "ESPACIO", 0x21: "AV PAG", 0x22: "RE PAG",
    0x23: "FIN", 0x24: "INICIO", 0x25: "IZQUIERDA", 0x26: "ARRIBA",
    0x27: "DERECHA", 0x28: "ABAJO", 0x2C: "IMPR PANT", 0x2D: "INSERT",
    0x2E: "SUPR",
}

# F1 - F12
for i in range(1, 13):
    VK_TO_NAME[0x6F + i] = f"F{i}"

# Letras A-Z
for i in range(ord('A'), ord('Z') + 1):
    VK_TO_NAME[i] = chr(i)

# Números 0-9
for i in range(ord('0'), ord('9') + 1):
    VK_TO_NAME[i] = chr(i)

# Teclado Numérico (NumPad 0-9)
for i in range(10):
    VK_TO_NAME[0x60 + i] = f"NUMPAD {i}"
VK_TO_NAME[0x6A] = "NUMPAD *"
VK_TO_NAME[0x6B] = "NUMPAD +"
VK_TO_NAME[0x6D] = "NUMPAD -"
VK_TO_NAME[0x6E] = "NUMPAD ."
VK_TO_NAME[0x6F] = "NUMPAD /"

# Mapeo inverso de Nombres a VK
VK_MAP = {v: k for k, v in VK_TO_NAME.items()}
# Aliases comunes
VK_MAP.update({
    "SPACE": 0x20, "INTRO": 0x0D, "ESCAPE": 0x1B, "DELETE": 0x2E,
    "CONTROL": 0x11, "MAYUS": 0x10, "CAPSLOCK": 0x14, "PGUP": 0x21,
    "PGDN": 0x22, "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
})


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


def get_cursor_pos() -> tuple[int, int]:
    """Obtiene las coordenadas absolutas actuales del cursor (X, Y)."""
    if not user32:
        return (0, 0)
    pt = POINT()
    user32.GetCursorPos(byref(pt))
    return (int(pt.x), int(pt.y))


def set_cursor_pos(x: int, y: int):
    """Establece la posición del cursor en pantalla."""
    if user32:
        user32.SetCursorPos(int(x), int(y))


def mouse_click(button: str = "left", click_type: str = "single", x: int = None, y: int = None):
    """
    Ejecuta un clic del ratón de forma instantánea.
    - button: 'left', 'right', 'middle'
    - click_type: 'single', 'double', 'triple', 'hold_down', 'release'
    - x, y: opcionales, si se especifican se mueve el cursor antes de hacer clic.
    """
    if not user32:
        return

    if x is not None and y is not None:
        user32.SetCursorPos(int(x), int(y))

    btn = button.lower()
    if btn == "left":
        down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
    elif btn == "right":
        down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    elif btn == "middle":
        down_flag, up_flag = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
    else:
        down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP

    if click_type == "hold_down":
        user32.mouse_event(down_flag, 0, 0, 0, 0)
        return
    elif click_type == "release":
        user32.mouse_event(up_flag, 0, 0, 0, 0)
        return

    clicks = 1
    if click_type == "double":
        clicks = 2
    elif click_type == "triple":
        clicks = 3

    for _ in range(clicks):
        user32.mouse_event(down_flag, 0, 0, 0, 0)
        time.sleep(0.001)
        user32.mouse_event(up_flag, 0, 0, 0, 0)
        if clicks > 1:
            time.sleep(0.02)


def key_down(vk_code: int):
    """Presiona una tecla sin soltarla."""
    if user32:
        user32.keybd_event(vk_code, 0, 0, 0)


def key_up(vk_code: int):
    """Suelta una tecla presionada."""
    if user32:
        user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def key_press(vk_code: int, hold_duration: float = 0.01):
    """Presiona y suelta una tecla con un tiempo de sostenimiento configurable."""
    if user32:
        user32.keybd_event(vk_code, 0, 0, 0)
        if hold_duration > 0:
            time.sleep(hold_duration)
        user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def send_char(char: str):
    """Envía un carácter utilizando VK_KEYSCAN o Unicode directo."""
    if not user32:
        return
    res = user32.VkKeyScanW(ord(char))
    if res != -1:
        vk = res & 0xFF
        shift = (res >> 8) & 1
        ctrl = (res >> 8) & 2
        alt = (res >> 8) & 4

        if shift:
            key_down(VK_MAP["SHIFT"])
        if ctrl:
            key_down(VK_MAP["CTRL"])
        if alt:
            key_down(VK_MAP["ALT"])

        key_press(vk, hold_duration=0.005)

        if alt:
            key_up(VK_MAP["ALT"])
        if ctrl:
            key_up(VK_MAP["CTRL"])
        if shift:
            key_up(VK_MAP["SHIFT"])
    else:
        user32.keybd_event(0, ord(char), KEYEVENTF_UNICODE, 0)
        user32.keybd_event(0, ord(char), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)


def type_text(text: str, delay: float = 0.01):
    """Escribe una cadena de texto simulando pulsaciones de teclado reales."""
    for ch in text:
        if ch == "\n":
            key_press(VK_MAP["ENTER"])
        elif ch == "\t":
            key_press(VK_MAP["TAB"])
        else:
            send_char(ch)
        if delay > 0:
            time.sleep(delay)


class HotkeySignals(QObject):
    """Puente de señales Qt seguro para cruzar desde el hilo daemon al hilo principal de la GUI."""
    triggered = pyqtSignal(int, str)  # vk_code, key_name
    key_captured = pyqtSignal(int, str)  # Para captura interactiva de atajos


class GlobalHotkeyListener:
    """
    Monitor global de atajos de teclado en segundo plano para Windows.
    Emite señales Qt para garantizar que la UI se actualice de forma 100%
    segura en el hilo principal sin bloqueos ni errores de setParent.
    """
    def __init__(self):
        self.signals = HotkeySignals()
        self._callbacks = {}  # {vk_code: callable}
        self._running = False
        self._thread = None
        self._pressed_states = {}
        self._capturing_next_key = False

        # Conectar la señal de disparo con el despachador
        self.signals.triggered.connect(self._dispatch_callback)

    def register_hotkey(self, key_name_or_vk, callback):
        """Registra un atajo de teclado por nombre ('F6', 'X', etc.) o código VK."""
        if isinstance(key_name_or_vk, str):
            vk = VK_MAP.get(key_name_or_vk.upper(), None)
        else:
            vk = int(key_name_or_vk)

        if vk:
            self._callbacks[vk] = callback
            self._pressed_states[vk] = False
            self.start()

    def unregister_hotkey(self, key_name_or_vk):
        """Elimina el registro de un atajo."""
        if isinstance(key_name_or_vk, str):
            vk = VK_MAP.get(key_name_or_vk.upper(), None)
        else:
            vk = int(key_name_or_vk)

        if vk in self._callbacks:
            del self._callbacks[vk]
            self._pressed_states.pop(vk, None)

    def unregister_all(self):
        """Elimina todos los atajos registrados."""
        self._callbacks.clear()
        self._pressed_states.clear()

    def start_capturing(self):
        """Pone al listener en modo captura para registrar la próxima tecla pulsada."""
        self._capturing_next_key = True
        self.start()

    def cancel_capturing(self):
        """Cancela el modo de captura interactiva."""
        self._capturing_next_key = False

    def start(self):
        """Inicia el hilo de monitoreo si no está activo."""
        if self._running or not user32:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Detiene el hilo de monitoreo."""
        self._running = False

    def _loop(self):
        while self._running:
            # 1. Modo Captura Interactiva de Tecla
            if self._capturing_next_key:
                captured = False
                for vk in list(VK_TO_NAME.keys()):
                    state = user32.GetAsyncKeyState(vk)
                    if (state & 0x8000) != 0:
                        self._capturing_next_key = False
                        key_name = VK_TO_NAME.get(vk, f"VK_{vk}")
                        self.signals.key_captured.emit(vk, key_name)
                        captured = True
                        time.sleep(0.2)  # Pausa para evitar rebote
                        break
                if captured:
                    continue
                time.sleep(0.015)
                continue

            # 2. Monitoreo Normal de Atajos Registrados
            if not self._callbacks:
                time.sleep(0.05)
                continue

            for vk in list(self._callbacks.keys()):
                state = user32.GetAsyncKeyState(vk)
                is_pressed = (state & 0x8000) != 0

                prev_state = self._pressed_states.get(vk, False)
                if is_pressed and not prev_state:
                    self._pressed_states[vk] = True
                    key_name = VK_TO_NAME.get(vk, f"VK_{vk}")
                    # Emitir a través de la señal Qt hacia el hilo GUI principal
                    self.signals.triggered.emit(vk, key_name)
                elif not is_pressed and prev_state:
                    self._pressed_states[vk] = False

            time.sleep(0.015)

    def _dispatch_callback(self, vk: int, key_name: str):
        """Se ejecuta en el hilo principal de Qt de forma 100% segura."""
        cb = self._callbacks.get(vk)
        if cb:
            try:
                cb()
            except Exception as e:
                print(f"[GlobalHotkeyListener] Error ejecutando callback para {key_name}: {e}")
