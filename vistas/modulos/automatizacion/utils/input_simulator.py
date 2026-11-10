"""
input_simulator.py
Motor de simulación de periféricos de ultra-baja latencia y captura global
para Windows usando la API Win32 nativa (user32.dll, winmm.dll, xinput),
con soporte completo para:
  - Todos los botones del ratón: LButton (Clic Izquierdo), RButton (Clic Derecho),
    MButton (Rueda Central), XButton1 (Lateral 1), XButton2 (Lateral 2).
  - Filtro de clics físicos vs inyectados (WH_MOUSE_LL con LLMHF_INJECTED) para que
    usar LButton o RButton como atajo no se interfiera con los propios clics del AutoClicker.
  - Todas las teclas del teclado y periféricos HID (0x08 a 0xFE, F1-F24, Multimedia, OEM).
  - Mandos, Joysticks, Volantes y Pedales USB (XInput y WinMM joyGetPosEx).
"""

import os
import sys
import time
import ctypes
from ctypes import wintypes, byref, Structure, c_long, WINFUNCTYPE, c_bool, c_int, c_uint32
import threading
from PyQt6.QtCore import QObject, pyqtSignal

# Cargar DLLs nativas de Windows
try:
    user32 = ctypes.windll.user32
except Exception:
    user32 = None

try:
    winmm = ctypes.windll.winmm
except Exception:
    winmm = None

xinput_dll = None
for _dll_name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
    try:
        xinput_dll = getattr(ctypes.windll, _dll_name)
        break
    except Exception:
        continue

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

# Mapeo Completo de Códigos Virtuales (VK) a Nombres (incluye TODOS los botones del ratón)
VK_TO_NAME = {
    # Botones de Ratón
    0x01: "LButton",
    0x02: "RButton",
    0x04: "MButton",
    0x05: "XButton1",
    0x06: "XButton2",

    # Teclas de Control y Navegación
    0x08: "BACKSPACE",
    0x09: "TAB",
    0x0C: "CLEAR",
    0x0D: "ENTER",
    0x10: "SHIFT",
    0x11: "CTRL",
    0x12: "ALT",
    0x13: "PAUSE",
    0x14: "BLOQ MAYUS",
    0x1B: "ESC",
    0x20: "ESPACIO",
    0x21: "RE PAG",
    0x22: "AV PAG",
    0x23: "FIN",
    0x24: "INICIO",
    0x25: "IZQUIERDA",
    0x26: "ARRIBA",
    0x27: "DERECHA",
    0x28: "ABAJO",
    0x2C: "IMPR PANT",
    0x2D: "INSERT",
    0x2E: "SUPR",
    0x2F: "HELP",

    # Teclas Windows y Menú
    0x5B: "LWin",
    0x5C: "RWin",
    0x5D: "AppsMenu",

    # Bloqueo
    0x90: "NUM LOCK",
    0x91: "SCROLL LOCK",

    # Modificadores Específicos Izquierdo / Derecho
    0xA0: "LShift",
    0xA1: "RShift",
    0xA2: "LCtrl",
    0xA3: "RCtrl",
    0xA4: "LAlt",
    0xA5: "RAlt",

    # Multimedia y Navegador (Teclados Gaming, StreamDeck, Ratones MMO)
    0xA6: "BrowserBack",
    0xA7: "BrowserForward",
    0xA8: "BrowserRefresh",
    0xA9: "BrowserStop",
    0xAA: "BrowserSearch",
    0xAB: "BrowserFavorites",
    0xAC: "BrowserHome",
    0xAD: "VolumeMute",
    0xAE: "VolumeDown",
    0xAF: "VolumeUp",
    0xB0: "MediaNext",
    0xB1: "MediaPrev",
    0xB2: "MediaStop",
    0xB3: "MediaPlayPause",
    0xB4: "LaunchMail",
    0xB5: "LaunchMedia",
    0xB6: "LaunchApp1",
    0xB7: "LaunchApp2",

    # Teclas OEM / Símbolos
    0xBA: "OEM_1 (;)",
    0xBB: "OEM_PLUS (+)",
    0xBC: "OEM_COMMA (,)",
    0xBD: "OEM_MINUS (-)",
    0xBE: "OEM_PERIOD (.)",
    0xBF: "OEM_2 (/)",
    0xC0: "OEM_3 (~)",
    0xDB: "OEM_4 ([)",
    0xDC: "OEM_5 (\\)",
    0xDD: "OEM_6 (])",
    0xDE: "OEM_7 (')",
    0xDF: "OEM_8",
    0xE2: "OEM_102 (<)",
}

# F1 - F24 (F13-F24 muy usados en ratones multitáctiles, macros y pedales)
for _i in range(1, 25):
    VK_TO_NAME[0x6F + _i] = f"F{_i}"

# Letras A-Z
for _i in range(ord('A'), ord('Z') + 1):
    VK_TO_NAME[_i] = chr(_i)

# Números 0-9
for _i in range(ord('0'), ord('9') + 1):
    VK_TO_NAME[_i] = chr(_i)

# Teclado Numérico (NumPad 0-9)
for _i in range(10):
    VK_TO_NAME[0x60 + _i] = f"NUMPAD {_i}"
VK_TO_NAME[0x6A] = "NUMPAD *"
VK_TO_NAME[0x6B] = "NUMPAD +"
VK_TO_NAME[0x6D] = "NUMPAD -"
VK_TO_NAME[0x6E] = "NUMPAD ."
VK_TO_NAME[0x6F] = "NUMPAD /"

# Códigos Virtuales Extendidos para Mandos XInput y Joysticks / Volantes / Pedales (0x1000+)
XINPUT_BUTTON_BITS = [
    (0x1000, "A"),
    (0x2000, "B"),
    (0x4000, "X"),
    (0x8000, "Y"),
    (0x0100, "LB"),
    (0x0200, "RB"),
    (0x0010, "Start"),
    (0x0020, "Back"),
    (0x0040, "LStick"),
    (0x0080, "RStick"),
    (0x0001, "DPadUp"),
    (0x0002, "DPadDown"),
    (0x0004, "DPadLeft"),
    (0x0008, "DPadRight"),
]

for _pad_idx in range(4):
    _base = 0x1000 + (_pad_idx * 0x100)
    for _b_idx, (_, _b_name) in enumerate(XINPUT_BUTTON_BITS):
        VK_TO_NAME[_base + _b_idx] = f"Pad{_pad_idx + 1}_{_b_name}"
    VK_TO_NAME[_base + 20] = f"Pad{_pad_idx + 1}_LT"
    VK_TO_NAME[_base + 21] = f"Pad{_pad_idx + 1}_RT"

    # Joysticks / Otros dispositivos DirectInput / WinMM (32 botones + 4 direcciones POV)
    _joy_base = 0x2000 + (_pad_idx * 0x100)
    for _btn_n in range(1, 33):
        VK_TO_NAME[_joy_base + _btn_n] = f"Joy{_pad_idx + 1}_Btn{_btn_n}"
    VK_TO_NAME[_joy_base + 40] = f"Joy{_pad_idx + 1}_POV_Up"
    VK_TO_NAME[_joy_base + 41] = f"Joy{_pad_idx + 1}_POV_Right"
    VK_TO_NAME[_joy_base + 42] = f"Joy{_pad_idx + 1}_POV_Down"
    VK_TO_NAME[_joy_base + 43] = f"Joy{_pad_idx + 1}_POV_Left"

# Mapeo inverso de Nombres a VK (mayúsculas y original)
VK_MAP = {}
for _k, _v in VK_TO_NAME.items():
    VK_MAP[_v] = _k
    VK_MAP[_v.upper()] = _k

# Aliases comunes
VK_MAP.update({
    "LBUTTON": 0x01, "LEFT CLICK": 0x01, "CLIC IZQUIERDO": 0x01,
    "RBUTTON": 0x02, "RIGHT CLICK": 0x02, "CLIC DERECHO": 0x02,
    "MBUTTON": 0x04, "MIDDLE CLICK": 0x04, "CLIC CENTRAL": 0x04,
    "XBUTTON1": 0x05, "XBUTTON2": 0x06,
    "SPACE": 0x20, "INTRO": 0x0D, "ESCAPE": 0x1B, "DELETE": 0x2E,
    "CONTROL": 0x11, "MAYUS": 0x10, "CAPSLOCK": 0x14, "PGUP": 0x21,
    "PGDN": 0x22, "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
})


def get_vk_display_name(vk: int) -> str:
    """Obtiene el nombre legible de cualquier código virtual o botón de dispositivo."""
    if vk in VK_TO_NAME:
        return VK_TO_NAME[vk]
    if user32 and 0x07 <= vk <= 0xFE:
        scan = user32.MapVirtualKeyW(vk, 0)
        if scan:
            buf = ctypes.create_unicode_buffer(64)
            if user32.GetKeyNameTextW(scan << 16, buf, 64) > 0:
                name = buf.value.strip()
                if name:
                    VK_TO_NAME[vk] = name
                    VK_MAP[name] = vk
                    VK_MAP[name.upper()] = vk
                    return name
    fallback = f"KEY_0x{vk:02X}"
    VK_TO_NAME[vk] = fallback
    VK_MAP[fallback] = vk
    return fallback


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


class RECT(Structure):
    _fields_ = [("left", c_long), ("top", c_long), ("right", c_long), ("bottom", c_long)]


class MSLLHOOKSTRUCT(Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class _PhysicalMouseTracker:
    """
    Rastreador global de botones físicos del ratón mediante WH_MOUSE_LL.
    Filtra los eventos inyectados (LLMHF_INJECTED = 0x01 / 0x02) generados por
    mouse_event para que si el usuario elige LButton o RButton como tecla de
    activación, los propios clics del AutoClicker no interfieran con su atajo.
    """
    def __init__(self):
        self.physical_down = {
            0x01: False,  # LButton
            0x02: False,  # RButton
            0x04: False,  # MButton
            0x05: False,  # XButton1
            0x06: False,  # XButton2
        }
        self.hook_active = False
        self._thread = None
        self._proc_ref = None

    def ensure_started(self):
        if self.hook_active or not user32:
            return
        self._thread = threading.Thread(target=self._hook_loop, daemon=True)
        self._thread.start()

    def _hook_loop(self):
        try:
            LowLevelMouseProc = WINFUNCTYPE(ctypes.c_ssize_t, c_int, wintypes.WPARAM, wintypes.LPARAM)
            user32.SetWindowsHookExW.restype = wintypes.HHOOK
            user32.SetWindowsHookExW.argtypes = [c_int, LowLevelMouseProc, wintypes.HINSTANCE, wintypes.DWORD]
            user32.CallNextHookEx.restype = ctypes.c_ssize_t
            user32.CallNextHookEx.argtypes = [wintypes.HHOOK, c_int, wintypes.WPARAM, wintypes.LPARAM]

            def _callback(nCode, wParam, lParam):
                # Ignorar WM_MOUSEMOVE (0x0200) inmediatamente para 0 latencia en el cursor
                if nCode >= 0 and wParam != 0x0200:
                    info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    # flags & 0x03 == 0 significa clic físico real del hardware (NO inyectado)
                    if (info.flags & 0x03) == 0:
                        if wParam == 0x0201:      # WM_LBUTTONDOWN
                            self.physical_down[0x01] = True
                        elif wParam == 0x0202:    # WM_LBUTTONUP
                            self.physical_down[0x01] = False
                        elif wParam == 0x0204:    # WM_RBUTTONDOWN
                            self.physical_down[0x02] = True
                        elif wParam == 0x0205:    # WM_RBUTTONUP
                            self.physical_down[0x02] = False
                        elif wParam == 0x0207:    # WM_MBUTTONDOWN
                            self.physical_down[0x04] = True
                        elif wParam == 0x0208:    # WM_MBUTTONUP
                            self.physical_down[0x04] = False
                        elif wParam == 0x020B:    # WM_XBUTTONDOWN
                            xbtn = (info.mouseData >> 16) & 0xFFFF
                            self.physical_down[0x05 if xbtn == 1 else 0x06] = True
                        elif wParam == 0x020C:    # WM_XBUTTONUP
                            xbtn = (info.mouseData >> 16) & 0xFFFF
                            self.physical_down[0x05 if xbtn == 1 else 0x06] = False
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            self._proc_ref = LowLevelMouseProc(_callback)
            hk = user32.SetWindowsHookExW(14, self._proc_ref, None, 0)
            if hk:
                self.hook_active = True
                msg = wintypes.MSG()
                while user32.GetMessageW(byref(msg), None, 0, 0) != 0:
                    user32.TranslateMessage(byref(msg))
                    user32.DispatchMessageW(byref(msg))
        except Exception:
            self.hook_active = False

    def is_mouse_vk_down(self, vk: int) -> bool:
        if self.hook_active and vk in self.physical_down:
            return self.physical_down[vk]
        if user32:
            return (user32.GetAsyncKeyState(vk) & 0x8000) != 0
        return False


_MOUSE_TRACKER = _PhysicalMouseTracker()


def _poll_controllers_pressed() -> dict[int, bool]:
    """
    Lee el estado actual de mandos XInput y Joysticks/Volantes/Pedales WinMM.
    Devuelve {virtual_code: True} para todos los botones actualmente presionados.
    """
    pressed = {}
    xinput_connected_pads = set()

    # 1. XInput (Mandos Xbox / PC modernos)
    if xinput_dll:
        buf = (ctypes.c_ubyte * 16)()
        for pad_idx in range(4):
            try:
                res = xinput_dll.XInputGetState(pad_idx, byref(buf))
                if res == 0:  # ERROR_SUCCESS
                    xinput_connected_pads.add(pad_idx)
                    wButtons = buf[4] | (buf[5] << 8)
                    bLeftTrigger = buf[6]
                    bRightTrigger = buf[7]
                    base = 0x1000 + (pad_idx * 0x100)
                    for b_idx, (bit_mask, _) in enumerate(XINPUT_BUTTON_BITS):
                        if (wButtons & bit_mask) != 0:
                            pressed[base + b_idx] = True
                    if bLeftTrigger > 120:
                        pressed[base + 20] = True
                    if bRightTrigger > 120:
                        pressed[base + 21] = True
            except Exception:
                pass

    # 2. WinMM joyGetPosEx (Joysticks, Volantes, Pedales USB, Mandos DirectInput)
    if winmm:
        # JOYINFOEX consta de 13 DWORDs (52 bytes); dwSize=52, dwFlags=0xFF (JOY_RETURNALL)
        joy_buf = (c_uint32 * 13)(52, 0xFF)
        for joy_idx in range(4):
            if joy_idx in xinput_connected_pads:
                continue
            try:
                joy_buf[0] = 52
                joy_buf[1] = 0xFF
                if winmm.joyGetPosEx(joy_idx, byref(joy_buf)) == 0:
                    dwButtons = joy_buf[8]
                    dwPOV = joy_buf[10]
                    joy_base = 0x2000 + (joy_idx * 0x100)
                    if dwButtons:
                        for btn_n in range(1, 33):
                            if (dwButtons & (1 << (btn_n - 1))) != 0:
                                pressed[joy_base + btn_n] = True
                    if dwPOV != 0xFFFF and dwPOV < 36000:
                        if dwPOV <= 4500 or dwPOV >= 31500:
                            pressed[joy_base + 40] = True  # Up
                        if 4500 <= dwPOV <= 13500:
                            pressed[joy_base + 41] = True  # Right
                        if 13500 <= dwPOV <= 22500:
                            pressed[joy_base + 42] = True  # Down
                        if 22500 <= dwPOV <= 31500:
                            pressed[joy_base + 43] = True  # Left
            except Exception:
                pass

    return pressed


def is_cursor_over_own_process() -> bool:
    """Comprueba si el cursor del ratón está sobre una ventana del propio MultiTool."""
    if not user32:
        return False
    pt = POINT()
    user32.GetCursorPos(byref(pt))
    hwnd = user32.WindowFromPoint(pt)
    if not hwnd:
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, byref(pid))
    return pid.value == os.getpid()


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


def lock_cursor_to_point(x: int, y: int):
    """Bloquea el cursor del ratón en una coordenada exacta de la pantalla."""
    if user32:
        r = RECT(int(x), int(y), int(x) + 1, int(y) + 1)
        user32.ClipCursor(byref(r))


def unlock_cursor():
    """Libera el cursor del ratón para permitir libre movimiento."""
    if user32:
        user32.ClipCursor(None)


def get_foreground_window_title() -> str:
    """Devuelve el título de la ventana activa en primer plano en Windows."""
    if not user32:
        return ""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value.strip()


def get_open_window_titles() -> list[str]:
    """Enumera los títulos de las ventanas visibles actualmente abiertas en Windows."""
    if not user32:
        return []
    titles = []
    EnumWindowsProc = WINFUNCTYPE(c_bool, wintypes.HWND, wintypes.LPARAM)

    def foreach_window(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                val = buf.value.strip()
                if val and val not in titles and val not in ("Program Manager", "Settings", "Configuración"):
                    titles.append(val)
        return True

    user32.EnumWindows(EnumWindowsProc(foreach_window), 0)
    return sorted(titles)


def play_sound_feedback(kind: str = "start"):
    """Emite un sonido de feedback en Windows."""
    try:
        import winsound
        if kind == "start":
            winsound.Beep(900, 75)
        else:
            winsound.Beep(500, 90)
    except Exception:
        pass


def mouse_click(button: str = "left", click_type: str = "single", x: int = None, y: int = None, hold_duration: float = 0.0):
    """
    Ejecuta un clic de ratón de ultra-baja latencia.
    - button: 'left', 'right', 'middle'
    - click_type: 'single', 'double', 'triple', 'hold_down', 'release'
    - hold_duration: tiempo en segundos entre mouse_down y mouse_up (para Click duty cycle de Speed AutoClicker)
    """
    if not user32:
        return

    if x is not None and y is not None:
        user32.SetCursorPos(int(x), int(y))

    btn = button.lower()
    if btn == "right":
        down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    elif btn == "middle":
        down_flag, up_flag = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
    else:
        down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP

    ctype = click_type.lower()
    if ctype == "hold_down":
        user32.mouse_event(down_flag, 0, 0, 0, 0)
    elif ctype == "release":
        user32.mouse_event(up_flag, 0, 0, 0, 0)
    elif ctype == "double":
        user32.mouse_event(down_flag | up_flag, 0, 0, 0, 0)
        time.sleep(0.01)
        user32.mouse_event(down_flag | up_flag, 0, 0, 0, 0)
    elif ctype == "triple":
        for _ in range(3):
            user32.mouse_event(down_flag | up_flag, 0, 0, 0, 0)
            time.sleep(0.008)
    else:
        if hold_duration > 0.0005:
            user32.mouse_event(down_flag, 0, 0, 0, 0)
            t0 = time.perf_counter()
            if hold_duration > 0.002:
                time.sleep(hold_duration - 0.001)
            while (time.perf_counter() - t0) < hold_duration:
                pass
            user32.mouse_event(up_flag, 0, 0, 0, 0)
        else:
            user32.mouse_event(down_flag | up_flag, 0, 0, 0, 0)


def mouse_scroll(amount: int = 120):
    """Simula giro de la rueda del ratón (+120 arriba, -120 abajo)."""
    if user32:
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(amount), 0)


def key_down(vk_code: int):
    """Mantiene presionada una tecla por su código virtual."""
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
    """Envía un carácter utilizando VkKeyScanW o Unicode directo."""
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
    triggered_down = pyqtSignal(int, str)  # vk_code, key_name (cuando se pulsa)
    triggered_up = pyqtSignal(int, str)    # vk_code, key_name (cuando se suelta)
    key_captured = pyqtSignal(int, str)    # Para captura interactiva de teclas, ratón o mando
    capture_cancelled = pyqtSignal()       # Cuando el usuario pulsa ESC durante captura


class GlobalHotkeyListener:
    """
    Monitor global de atajos de teclado, botones de ratón (LButton, RButton, MButton,
    XButton1, XButton2) y otros dispositivos (Mandos XInput, Joysticks, Pedales USB).
    """
    def __init__(self):
        self.signals = HotkeySignals()
        self._callbacks_down = {}  # {vk_code: callable}
        self._callbacks_up = {}    # {vk_code: callable}
        self._running = False
        self._thread = None
        self._pressed_states = {}
        self._capturing_next_key = False
        self._capture_prev_states = {}
        self._capture_ready_time = 0.0
        self.enabled = True

        self.signals.triggered_down.connect(self._dispatch_down)
        self.signals.triggered_up.connect(self._dispatch_up)

    def register_hotkey(self, key_name_or_vk, on_down, on_up=None):
        """Registra un atajo por nombre ('F6', 'LButton', 'RButton', 'MButton', 'Pad1_A', etc.) o código."""
        if isinstance(key_name_or_vk, str):
            vk = VK_MAP.get(key_name_or_vk, None) or VK_MAP.get(key_name_or_vk.upper(), None)
            if vk is None and key_name_or_vk.startswith("KEY_0x"):
                try:
                    vk = int(key_name_or_vk.replace("KEY_0x", ""), 16)
                except Exception:
                    vk = None
        else:
            vk = int(key_name_or_vk)

        if vk:
            if vk in (0x01, 0x02, 0x04, 0x05, 0x06):
                _MOUSE_TRACKER.ensure_started()
            self._callbacks_down[vk] = on_down
            if on_up:
                self._callbacks_up[vk] = on_up
            else:
                self._callbacks_up.pop(vk, None)
            # Inicializar con el estado actual para no disparar en falso al acabar de asignarlo
            self._pressed_states[vk] = self._is_code_pressed(vk)
            self.start()

    def unregister_hotkey(self, key_name_or_vk):
        """Elimina el registro de un atajo."""
        if isinstance(key_name_or_vk, str):
            vk = VK_MAP.get(key_name_or_vk, None) or VK_MAP.get(key_name_or_vk.upper(), None)
        else:
            vk = int(key_name_or_vk)

        self._callbacks_down.pop(vk, None)
        self._callbacks_up.pop(vk, None)
        self._pressed_states.pop(vk, None)

    def unregister_all(self):
        """Elimina todos los atajos registrados."""
        self._callbacks_down.clear()
        self._callbacks_up.clear()
        self._pressed_states.clear()

    def start_capturing(self):
        """
        Pone al listener en modo captura para detectar la próxima pulsación de:
          - Cualquier botón del ratón (LButton, RButton, MButton, XButton1, XButton2)
          - Cualquier tecla del teclado / periférico HID (0x08..0xFE)
          - Cualquier botón de Mando / Joystick / Volante / Pedal (XInput / WinMM)
        Toma una instantánea previa para ignorar el clic inicial con el que se abrió el botón selector.
        """
        _MOUSE_TRACKER.ensure_started()
        snapshot = {}
        if user32:
            for vk in range(0x01, 0xFF):
                if vk in (0x01, 0x02, 0x04, 0x05, 0x06):
                    snapshot[vk] = _MOUSE_TRACKER.is_mouse_vk_down(vk) or ((user32.GetAsyncKeyState(vk) & 0x8000) != 0)
                else:
                    snapshot[vk] = (user32.GetAsyncKeyState(vk) & 0x8000) != 0
        # Forzar que LButton figure como presionado inicialmente si se acaba de hacer clic en el botón selector
        snapshot[0x01] = snapshot.get(0x01, False)
        for c_vk, c_down in _poll_controllers_pressed().items():
            snapshot[c_vk] = c_down

        self._capture_prev_states = snapshot
        self._capture_ready_time = time.perf_counter() + 0.12
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

    def _is_code_pressed(self, vk: int, ctrl_snapshot: dict = None) -> bool:
        if vk in (0x01, 0x02, 0x04, 0x05, 0x06):
            return _MOUSE_TRACKER.is_mouse_vk_down(vk)
        if vk >= 0x1000:
            if ctrl_snapshot is not None:
                return ctrl_snapshot.get(vk, False)
            return _poll_controllers_pressed().get(vk, False)
        if user32:
            return (user32.GetAsyncKeyState(vk) & 0x8000) != 0
        return False

    def _loop(self):
        # Teclas genéricas de modificador que se omiten en captura si existe su versión específica L/R,
        # o se priorizan según orden
        skip_vks = {0x03, 0x07, 0x0A, 0x0B, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0xFF}

        while self._running:
            if not self.enabled and not self._capturing_next_key:
                time.sleep(0.05)
                continue

            # ── 1. MODO CAPTURA INTERACTIVA (RATÓN + TECLADO + OTROS DISPOSITIVOS) ──
            if self._capturing_next_key:
                now = time.perf_counter()
                ctrl_pressed = _poll_controllers_pressed()

                # Actualizar estados durante la ventana de debounce de 120ms (para soltar el clic que abrió el selector)
                if now < self._capture_ready_time:
                    for vk in (0x01, 0x02, 0x04, 0x05, 0x06):
                        self._capture_prev_states[vk] = _MOUSE_TRACKER.is_mouse_vk_down(vk) or ((user32.GetAsyncKeyState(vk) & 0x8000) != 0)
                    time.sleep(0.015)
                    continue

                # Comprobar ESC (0x1B) para cancelar la selección
                esc_down = (user32.GetAsyncKeyState(0x1B) & 0x8000) != 0
                was_esc = self._capture_prev_states.get(0x1B, False)
                self._capture_prev_states[0x1B] = esc_down
                if esc_down and not was_esc:
                    self._capturing_next_key = False
                    self.signals.capture_cancelled.emit()
                    time.sleep(0.15)
                    continue

                captured = False

                # A) Escanear botones del Ratón: LButton (0x01), RButton (0x02), MButton (0x04), XButton1 (0x05), XButton2 (0x06)
                for m_vk in (0x01, 0x02, 0x04, 0x05, 0x06):
                    is_down = _MOUSE_TRACKER.is_mouse_vk_down(m_vk) or ((user32.GetAsyncKeyState(m_vk) & 0x8000) != 0)
                    was_down = self._capture_prev_states.get(m_vk, False)
                    self._capture_prev_states[m_vk] = is_down
                    if is_down and not was_down:
                        self._capturing_next_key = False
                        key_name = get_vk_display_name(m_vk)
                        self._pressed_states[m_vk] = True
                        self.signals.key_captured.emit(m_vk, key_name)
                        captured = True
                        time.sleep(0.18)
                        break

                if captured:
                    continue

                # B) Escanear todas las teclas de teclado y periféricos HID (0x08 a 0xFE)
                for vk in range(0x08, 0xFE):
                    if vk in skip_vks or vk == 0x1B:
                        continue
                    is_down = (user32.GetAsyncKeyState(vk) & 0x8000) != 0
                    was_down = self._capture_prev_states.get(vk, False)
                    self._capture_prev_states[vk] = is_down
                    if is_down and not was_down:
                        self._capturing_next_key = False
                        key_name = get_vk_display_name(vk)
                        self._pressed_states[vk] = True
                        self.signals.key_captured.emit(vk, key_name)
                        captured = True
                        time.sleep(0.18)
                        break

                if captured:
                    continue

                # C) Escanear Mandos, Joysticks, Volantes y Pedales USB (XInput & WinMM)
                all_ctrl_keys = set(ctrl_pressed.keys()) | {k for k in self._capture_prev_states if k >= 0x1000}
                for c_vk in all_ctrl_keys:
                    is_down = ctrl_pressed.get(c_vk, False)
                    was_down = self._capture_prev_states.get(c_vk, False)
                    self._capture_prev_states[c_vk] = is_down
                    if is_down and not was_down:
                        self._capturing_next_key = False
                        key_name = get_vk_display_name(c_vk)
                        self._pressed_states[c_vk] = True
                        self.signals.key_captured.emit(c_vk, key_name)
                        captured = True
                        time.sleep(0.18)
                        break

                time.sleep(0.012)
                continue

            # ── 2. MONITOREO NORMAL DE ATAJOS REGISTRADOS ───────────────────────────
            if not self._callbacks_down:
                time.sleep(0.05)
                continue

            need_ctrl = any(vk >= 0x1000 for vk in self._callbacks_down)
            ctrl_snapshot = _poll_controllers_pressed() if need_ctrl else None

            for vk in list(self._callbacks_down.keys()):
                is_pressed = self._is_code_pressed(vk, ctrl_snapshot)
                prev_state = self._pressed_states.get(vk, False)

                if is_pressed and not prev_state:
                    self._pressed_states[vk] = True
                    # Si el atajo es LButton (Clic Izquierdo) y el usuario está haciendo clic
                    # dentro de la propia ventana de MultiTool (ej. botón Stop o SELECT...),
                    # no disparar el inicio para permitir operar la UI libremente.
                    if vk == 0x01 and is_cursor_over_own_process():
                        continue
                    key_name = get_vk_display_name(vk)
                    self.signals.triggered_down.emit(vk, key_name)
                elif not is_pressed and prev_state:
                    self._pressed_states[vk] = False
                    key_name = get_vk_display_name(vk)
                    self.signals.triggered_up.emit(vk, key_name)

            time.sleep(0.012)

    def _dispatch_down(self, vk: int, key_name: str):
        if not self.enabled:
            return
        cb = self._callbacks_down.get(vk)
        if cb:
            try:
                cb()
            except Exception as e:
                print(f"[GlobalHotkeyListener] Error en callback down {key_name}: {e}")

    def _dispatch_up(self, vk: int, key_name: str):
        if not self.enabled:
            return
        cb = self._callbacks_up.get(vk)
        if cb:
            try:
                cb()
            except Exception as e:
                print(f"[GlobalHotkeyListener] Error en callback up {key_name}: {e}")
