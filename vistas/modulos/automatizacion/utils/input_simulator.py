"""
input_simulator.py
Motor de simulación de periféricos de ultra-baja latencia y captura global
para Windows usando la API Win32 nativa (user32.dll).
"""

import sys
import time
import ctypes
from ctypes import wintypes, byref, Structure, c_long
import threading

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

# Mapeo de Códigos de Teclas Virtuales (VK)
VK_MAP = {
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    "ESPACIO": 0x20, "SPACE": 0x20,
    "ENTER": 0x0D, "INTRO": 0x0D,
    "ESCAPE": 0x1B, "ESC": 0x1B,
    "TAB": 0x09, "BACKSPACE": 0x08,
    "SHIFT": 0x10, "CONTROL": 0x11, "CTRL": 0x11, "ALT": 0x12,
    "PAUSE": 0x13, "CAPSLOCK": 0x14,
    "PAGEUP": 0x21, "PAGEDOWN": 0x22, "END": 0x23, "HOME": 0x24,
    "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    "INSERT": 0x2D, "DELETE": 0x2E,
}
# Añadir letras A-Z (0x41 - 0x5A) y números 0-9 (0x30 - 0x39)
for i in range(ord('A'), ord('Z') + 1):
    VK_MAP[chr(i)] = i
for i in range(ord('0'), ord('9') + 1):
    VK_MAP[chr(i)] = i

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
    - click_type: 'single', 'double', 'triple'
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
        # Fallback a Unicode event
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


class GlobalHotkeyListener:
    """
    Monitor de atajos de teclado globales en segundo plano para Windows.
    Permite capturar teclas como F6, F7, F8, F9 en cualquier ventana del SO.
    """
    def __init__(self):
        self._callbacks = {}  # {vk_code: callable}
        self._running = False
        self._thread = None
        self._pressed_states = {}

    def register_hotkey(self, key_name_or_vk, callback):
        """Registra un atajo de teclado por nombre ('F6') o por código VK."""
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
            if not self._callbacks:
                time.sleep(0.05)
                continue

            for vk, callback in list(self._callbacks.items()):
                # GetAsyncKeyState devuelve negativo si la tecla está presionada en este instante
                state = user32.GetAsyncKeyState(vk)
                is_pressed = (state & 0x8000) != 0

                prev_state = self._pressed_states.get(vk, False)
                if is_pressed and not prev_state:
                    # Flanco ascendente (se acaba de presionar)
                    self._pressed_states[vk] = True
                    try:
                        threading.Thread(target=callback, daemon=True).start()
                    except Exception as e:
                        print(f"[Hotkey Error] Callback falló: {e}")
                elif not is_pressed and prev_state:
                    # Se soltó la tecla
                    self._pressed_states[vk] = False

            time.sleep(0.015)  # 15 ms polling (~66 Hz) -> 0% CPU pero respuesta instantánea
