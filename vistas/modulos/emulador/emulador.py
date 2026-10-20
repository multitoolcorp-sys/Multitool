import os
import random
import threading
import time
import platform
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QSlider,
    QPushButton, QFrame, QGridLayout, QSizePolicy, QTabWidget, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont, QPen

from .submodulos.consola_arcade import ConsolaArcadeSubmodule
from .submodulos.teclado_mapeo import TecladoMapeoSubmodule
from .submodulos.gestor_roms import GestorRomsSubmodule
from .submodulos.opciones_retro import OpcionesRetroSubmodule, THEMES_EXTENDED

# --- TRADITIONAL ROMS CODED IN HEXADECIMAL ---
ROM_MAZE = bytes.fromhex("A21EC2013201A21AD014700430401200600071043120120012188040201020408010")
ROM_PONG = bytes.fromhex("6A026B0C6C3F6D0CA2EADAB6DCD66E0022D4660368026060F015F0073000121AC717770869FFA2F0D671A2EADAB6DCD66001E0A17BFE6004E0A17B02601F8B02DAB6600CE0A17DFE600DE0A17D02601F8D02DCD6A2F0D67186848794603F8602611F871246021278463F1282471F69FF47006901D671122A68026301807080B5128A68FE630A807080D53F0112A2610280153F0112BA80153F0112C880153F0112C26020F01822D48E3422D4663E3301660368FE33016802121679FF49FE69FF12C87901490269016004F0187601464076FE126CA2F2FE33F265F12964146500D4557415F229D45500EE808080808080800000000000")
ROM_BRIX = bytes.fromhex("6E0565006B066A00A30CDAB17A043A4012087B023B1212066C206D1FA310DCD122F660006100A312D0117008A30ED0116040F015F00730001234C60F671E680169FFA30ED671A310DCD16004E0A17CFE6006E0A17C02603F8C02DCD1A30ED67186848794603F8602611F8712471F12AC46006801463F68FF47006901D6713F0112AA471F12AA600580753F0012AA6001F018806061FC8012A30CD07160FE890322F6750122F6456012DE124669FF806080C53F0112CA610280153F0112E080153F0112EE80153F0112E86020F018A30E7EFF80E080046100D0113E00123012DE78FF48FE68FF12EE7801480268016004F01869FF1270A314F533F265F12963376400D3457305F229D34500EEE0008000FC00AA0000000000")
ROM_TETRIS = bytes.fromhex("A2B423E622B67001D0113025120671FFD011601AD01160253100120EC4704470121CC303601E6103225CF515D0143F01123CD01471FFD0142340121CE7A12272E8A12284E9A12296E29E12506600F615F6073600123CD0147101122AA2C4F41E660043016604430266084303660CF61E00EED01470FF23343F0100EED0147001233400EED014700123343F0100EED01470FF233400EED014730143046300225C23343F0100EED01473FF43FF6303225C233400EE8000670568066904611F6510620700EE40E0000040C0400000E04000406040004040600020E00000C040400000E080004040C00000E020006040400080E0000040C08000C060000040C08000C060000080C040000060C00080C040000060C000C0C00000C0C00000C0C00000C0C000004040404000F000004040404000F00000D014663576FF3600133800EEA2B48C103C1E7C013C1E7C013C1E7C01235E4B0A237291C000EE71011350601B6B00D0113F007B01D01170013025136200EE601BD0117001302513748E108DE07EFF601B6B00D0E13F001390D0E11394D0D17B017001302513864B0013A67DFF7EFF3D01138223C03F0123C07A0123C080A06D0780D2400475FE4502650400EEA700F255A804FA33F265F0296D326E00DDE57D05F129DDE57D05F229DDE5A700F265A2B400EE6A00601900EE3723")
ROM_INVADERS = bytes.fromhex("1225535041434520494E56414445525320302E39312042792044617669642057494E544552600061006208A3DDD0187108F21E3120122D700861003040122D69056C156E002391600AF015F0073000124B23917E0112456600681C69006A046B0A6C046D3C6E0F00E023752351FD156004E09E127D2375380078FF23756006E09E128B23753839780123753600129F6005E09E12E96601651B8480A3D9D451A3D9D45175FF35FF12AD660012E9D4513F0112E9D45166008340730383B562F883226208330012C9237D8206430812D3331012D5237D8206331812DD237D8206432012E7332812E9237D3E0013077906491869006A046B0A6C047DF46E0F00E023512375FD15126FF7073700126FFD1523518BA43B12131B7C026AFC3B0213237C026A0423513C18126F00E0A4DD60146108620FD01F7008F21E302C133360FFF015F00730001341F00A00E0A706FE651225A3C1F91E610823698106236981062369810623697BD000EE80E080123000DBC67B0C00EEA3D9601CD80400EE23518E2323516005F018F015F0073000138900EE6A008DE06B04E9A11257A60CFD1EF06530FF13AF6A006B046D016E011397A50AF01EDBC67B087D017A013A07139700EE3C7EFFFF99997EFFFF2424E77EFF3C3C7EDB81423C7EFFDB10387CFE00007F003F007F0000000101010303030300003F20202020202020203F0808FF0000FE00FC00FE0000007E4242626262620000FF0000000000000000FF0000FF007D00417D057D7D0000C2C2C6446C28380000FF0000000000000000FF0000FF00F71014F7F7040400007C44FEC2C2C2C20000FF0000000000000000FF0000FF00EF2028E8E82F2F0000F985C5C5C5C5F90000FF0000000000000000FF0000FF00BE00203020BEBE0000F704E7858584F40000FF0000000000000000FF0000FF00007F003F007F000000EF28EF00E0606F0000FF0000000000000000FF0000FF0000FE00FC00FE000000C000C0C0C0C0C00000FC0404040404040404FC1010FFF981B98B9A9AFA00FA8A9A9A9B99F8E62525F434343400171434373626C7DF50505CD8D8DF00DF111F121B19D97C44FE868686FC84FE8282FEFE80C0C0C0FEFC82C2C2C2FCFE80F8C0C0FEFE80F0C0C0C0FE80BE8686FE8686FE8686861010101010101818184848789C90B0C0B09C8080C0C0C0FEEE9292868686FE82868686867C828686867CFE82FEC0C0C07C82C2CAC47AFE86FE909C84FEC0FE0202FEFE10303030308282C2C2C2FE828282EE38108686969292EE8244383844828282FE303030FE021EF080FE0000000006060000006060C00000000000001818181800187CC60C1800180000FEFE0000FE82868686FE080808181818FE02FEC0C0FEFE021E0606FE84C4C4FE0404FE80FE0606FEC0C0C0FE82FEFE02020606067C44FE8686FEFE82FE06060644FE4444FE44A8A8A8A8A8A8A86C5A000C18A8304E7E001218666CA85A665424660048481812A80690A812007E3012A884304E721866A8A8A8A8A8A8905478A848786C72A812186C72665490A8722A18A8304E7E001218666CA87254A85A66187E184E72A8722A183066A8722A183066A8304E7E006C30544E9CA8A8A8A8A8A8A848547E18A890547866A86C2A305AA88430722AA8D8A8004E12A8E4A2A8004E12A86C2A545472A88430722AA8DE9CA8722A18A80C54485A78721866A866185A5466726CA8722A0072A8722A18A8304E7E001218666CA8006618A8304E0C6618006C304E24A8722A183066A81E54660C189CA824545412A842780C3CA8AEA8A8A8A8A8A8A8FF000000000000000000000000000000")

FONT_SET = [
    0xF0, 0x90, 0x90, 0x90, 0xF0, 0x20, 0x60, 0x20, 0x20, 0x70,
    0xF0, 0x10, 0xF0, 0x80, 0xF0, 0xF0, 0x10, 0xF0, 0x10, 0xF0,
    0x90, 0x90, 0xF0, 0x10, 0x10, 0xF0, 0x80, 0xF0, 0x10, 0xF0,
    0xF0, 0x80, 0xF0, 0x90, 0xF0, 0xF0, 0x10, 0x20, 0x40, 0x40,
    0xF0, 0x90, 0xF0, 0x90, 0xF0, 0xF0, 0x90, 0xF0, 0x10, 0xF0,
    0xF0, 0x90, 0xF0, 0x90, 0x90, 0xE0, 0x90, 0xE0, 0x90, 0xE0,
    0xF0, 0x80, 0x80, 0x80, 0xF0, 0xE0, 0x90, 0x90, 0x90, 0xE0,
    0xF0, 0x80, 0xF0, 0x80, 0xF0, 0xF0, 0x80, 0xF0, 0x80, 0x80
]

KEY_MAPPING = {
    Qt.Key.Key_1: 0x1, Qt.Key.Key_2: 0x2, Qt.Key.Key_3: 0x3, Qt.Key.Key_4: 0xC,
    Qt.Key.Key_Q: 0x4, Qt.Key.Key_W: 0x5, Qt.Key.Key_E: 0x6, Qt.Key.Key_R: 0xD,
    Qt.Key.Key_A: 0x7, Qt.Key.Key_S: 0x8, Qt.Key.Key_D: 0x9, Qt.Key.Key_F: 0xE,
    Qt.Key.Key_Z: 0xA, Qt.Key.Key_X: 0x0, Qt.Key.Key_C: 0xB, Qt.Key.Key_V: 0xF
}

try:
    import winsound
except ImportError:
    winsound = None


class Chip8Canvas(QWidget):
    """Lienzo de dibujo de alto rendimiento que simula un monitor CRT retro con zoom y scanlines"""
    def __init__(self, parent, theme):
        super().__init__(parent)
        self.theme = theme
        self.display = [0] * (64 * 32)
        self.has_focus = False
        self.scale_mode = "fit"  # "fit", "1x", "2x"
        self.scanlines_enabled = True

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(320, 160)

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def set_display_buffer(self, buffer):
        self.display = buffer
        self.update()

    def set_scale_mode(self, mode):
        """Modo de escalado: 'fit', '1x', '2x'"""
        self.scale_mode = mode
        self.update()

    def toggle_scanlines(self):
        """Alterna el filtro de líneas de barrido CRT de fósforo"""
        self.scanlines_enabled = not self.scanlines_enabled
        self.update()
        return self.scanlines_enabled

    def focusInEvent(self, event):
        self.has_focus = True
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.has_focus = False
        self.update()
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w, h = rect.width(), rect.height()

        # Fondo del chasis monitor CRT
        painter.fillRect(rect, QColor("#07070A"))

        # Determinar tamaño y centrado del área de visualización (64:32 aspect ratio)
        if self.scale_mode == "1x":
            pixel_size = 6.0
            disp_w = 64.0 * pixel_size
            disp_h = 32.0 * pixel_size
            # Si no cabe, ajustar proporcionalmente
            if disp_w > w or disp_h > h:
                pixel_size = min(w / 64.0, h / 32.0)
                disp_w = 64.0 * pixel_size
                disp_h = 32.0 * pixel_size
        elif self.scale_mode == "2x":
            pixel_size = 12.0
            disp_w = 64.0 * pixel_size
            disp_h = 32.0 * pixel_size
            if disp_w > w or disp_h > h:
                pixel_size = min(w / 64.0, h / 32.0)
                disp_w = 64.0 * pixel_size
                disp_h = 32.0 * pixel_size
        else:  # "fit"
            pixel_size = min(w / 64.0, h / 32.0)
            disp_w = 64.0 * pixel_size
            disp_h = 32.0 * pixel_size

        pixel_w = pixel_size
        pixel_h = pixel_size

        offset_x = (w - disp_w) / 2.0
        offset_y = (h - disp_h) / 2.0

        screen_rect = QRectF(offset_x, offset_y, disp_w, disp_h)
        # Pantalla de fósforo CRT
        painter.fillRect(screen_rect, QColor(self.theme.get("bg", "#0B120B")))

        # Píxeles activos con resplandor fluorescente (Glow)
        active_color = QColor(self.theme.get("active", "#10FF10"))
        glow_color = QColor(active_color)
        glow_color.setAlpha(60)

        for y in range(32):
            for x in range(64):
                if self.display[y * 64 + x]:
                    px = offset_x + x * pixel_w
                    py = offset_y + y * pixel_h
                    rect_f = QRectF(px + 0.5, py + 0.5, max(1.0, pixel_w - 1.0), max(1.0, pixel_h - 1.0))

                    # Resplandor Glow
                    painter.setBrush(QBrush(glow_color))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(rect_f.adjusted(-1.0, -1.0, 1.0, 1.0), 2, 2)

                    # Píxel central
                    painter.setBrush(QBrush(active_color))
                    painter.drawRoundedRect(rect_f, 1.0, 1.0)

        # Líneas de barrido CRT (Scanlines de fósforo retro)
        if self.scanlines_enabled:
            scanline_pen = QPen(QColor(0, 0, 0, 42), 1)
            painter.setPen(scanline_pen)
            start_y = int(offset_y)
            end_y = int(offset_y + disp_h)
            for sl_y in range(start_y, end_y, 2):
                painter.drawLine(int(offset_x), sl_y, int(offset_x + disp_w), sl_y)

        # Borde sutil del marco de pantalla CRT
        frame_pen = QPen(QColor(self.theme.get("accent", "#39FF14")), 1)
        frame_pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(frame_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(screen_rect)

        # Si no tiene foco, mostrar cartel retro de activación
        if not self.has_focus:
            overlay_color = QColor(0, 0, 0, 160)
            painter.fillRect(screen_rect, overlay_color)

            box_width = min(280, int(disp_w * 0.8))
            box_height = 70
            box_x = int(offset_x + (disp_w - box_width) / 2)
            box_y = int(offset_y + (disp_h - box_height) / 2)

            pen = QPen(QColor(self.theme.get("accent", "#6366F1")), 1.5)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor("#161622")))
            painter.drawRoundedRect(box_x, box_y, box_width, box_height, 8, 8)

            font = QFont("Consolas", 10, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor("#E2E2E2"))
            painter.drawText(
                box_x, box_y, box_width, box_height,
                Qt.AlignmentFlag.AlignCenter,
                "🎯 HAGA CLIC AQUÍ\nPARA ACTIVAR MANDOS"
            )


class TabEmulador(QWidget):
    """
    Módulo Principal de Emulador Retro CHIP-8 / N64 con QTabWidget y 4 Submódulos Desacoplados:
    1. Consola Arcade & Pantalla CRT
    2. Teclado Virtual & Mapeo de Teclas
    3. Biblioteca de ROMs de la Comunidad & Lanzador N64 (con Vista por Defecto / Sin Selección)
    4. Opciones Retro & Paletas de Color
    """
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        })

        self.current_theme_name = "Verde Matrix"
        self.chip8_theme = THEMES_EXTENDED[self.current_theme_name]

        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.roms_dir = self.ruta_usuario / "roms_emulador"
        self.roms_dir.mkdir(parents=True, exist_ok=True)
        self.comunidad_roms_files = []

        # Estado de la CPU CHIP-8
        self.memory = bytearray(4096)
        self.registers = bytearray(16)
        self.I = 0
        self.pc = 0x200
        self.stack = []
        self.delay_timer = 0
        self.sound_timer = 0
        self.keypad = [False] * 16
        self.display = [0] * (64 * 32)

        self.running = False
        self.paused = False
        self.sound_enabled = True
        self.cycles_per_tick = 10
        self.rom_data = ROM_MAZE

        self.cargar_fuentes()

        self.callbacks = {
            "on_game_changed": self.on_game_changed,
            "on_theme_changed": self.on_theme_changed,
            "on_speed_changed": self.on_speed_changed,
            "toggle_play": self.toggle_play,
            "reset_cpu": self.reset_cpu,
            "toggle_sound": self.toggle_sound,
            "play_beep": self.play_beep,
            "set_key_state": self.set_key_state,
            "escanear_roms": self.escanear_roms,
            "abrir_carpeta_roms": self.abrir_carpeta_roms,
            "play_comunidad_game": self.play_comunidad_game,
            "cargar_archivo_manual": self.cargar_archivo_manual,
            "configurar_emulador_n64": self.configurar_emulador_n64
        }

        self.canvas = Chip8Canvas(self, self.chip8_theme)
        self.canvas.set_display_buffer(self.display)

        self.inicializar_ui()

        # Timer principal a ~60 FPS
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.game_loop)
        self.timer.start(16)

        self.reset_cpu()
        self.escanear_roms()

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # QTabWidget Superior
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont(self.font_family, 9))
        self.aplicar_estilo_tabs()

        # Submódulos dinámicos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        extra_kwargs = {
            "callbacks": self.callbacks,
            "canvas": self.canvas,
            "canvas_widget": self.canvas
        }
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores, extra_kwargs)

        if self.tabs.count() == 0:
            self.tab_arcade = ConsolaArcadeSubmodule(self, self.context, self.colores, self.callbacks, self.canvas)
            self.tab_teclado = TecladoMapeoSubmodule(self, self.context, self.colores, self.callbacks)
            self.tab_roms = GestorRomsSubmodule(self, self.context, self.colores, self.callbacks)
            self.tab_opciones = OpcionesRetroSubmodule(self, self.context, self.colores, self.callbacks)

            self.tabs.addTab(self.tab_arcade, "🎮 Consola Arcade")
            self.tabs.addTab(self.tab_teclado, "🕹️ Teclado Virtual & Mapeo")
            self.tabs.addTab(self.tab_roms, "📁 Gestor de ROMs & N64")
            self.tabs.addTab(self.tab_opciones, "⚙️ Ajustes & Paletas CRT")
        else:
            self.tab_arcade = self.submod_instances.get("ConsolaArcadeSubmodule") or self.submod_instances.get("consolaarcadesubmodule")
            if not self.tab_arcade:
                self.tab_arcade = ConsolaArcadeSubmodule(self, self.context, self.colores, self.callbacks, self.canvas)
            self.tab_teclado = self.submod_instances.get("TecladoMapeoSubmodule") or self.submod_instances.get("tecladomapeosubmodule")
            if not self.tab_teclado:
                self.tab_teclado = TecladoMapeoSubmodule(self, self.context, self.colores, self.callbacks)
            self.tab_roms = self.submod_instances.get("GestorRomsSubmodule") or self.submod_instances.get("gestorromssubmodule")
            self.tab_opciones = self.submod_instances.get("OpcionesRetroSubmodule") or self.submod_instances.get("opcionesretrosubmodule")

        # Aliases Proxy para retro-compatibilidad
        if self.tab_arcade:
            self.status_bar = self.tab_arcade.status_bar
            self.cb_juegos = self.tab_arcade.cb_juegos
            self.btn_play = self.tab_arcade.btn_play
            self.btn_reset = self.tab_arcade.btn_reset
            self.slider_speed = self.tab_arcade.slider_speed
            self.speed_label = self.tab_arcade.speed_label
            self.btn_sound = self.tab_arcade.btn_sound
        if self.tab_roms:
            self.cb_comunidad = self.tab_roms.cb_comunidad
            self.btn_play_comunidad = self.tab_roms.btn_play_comunidad
        if self.tab_opciones:
            self.cb_temas = self.tab_opciones.cb_temas
        if self.tab_teclado:
            self.visual_buttons = self.tab_teclado.visual_buttons

        self.main_layout.addWidget(self.tabs)

    def aplicar_estilo_tabs(self):
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['acento']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)

    def set_key_state(self, val, pressed):
        self.keypad[val] = pressed
        if hasattr(self, 'tab_teclado') and self.tab_teclado:
            self.tab_teclado.update_key_button(val, pressed)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            # Si el usuario pulsa Esc en la pestaña de ROMs, volver a vista sin selección
            if hasattr(self, 'tab_roms') and self.tab_roms and self.tabs.currentWidget() == self.tab_roms:
                self.tab_roms.deseleccionar()
                event.accept()
                return
        if key in KEY_MAPPING:
            val = KEY_MAPPING[key]
            self.set_key_state(val, True)
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        key = event.key()
        if key in KEY_MAPPING:
            val = KEY_MAPPING[key]
            self.set_key_state(val, False)
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def on_game_changed(self, idx):
        if idx == 0: self.rom_data = ROM_MAZE
        elif idx == 1: self.rom_data = ROM_PONG
        elif idx == 2: self.rom_data = ROM_BRIX
        elif idx == 3: self.rom_data = ROM_TETRIS
        elif idx == 4: self.rom_data = ROM_INVADERS
        self.reset_cpu()

    def on_theme_changed(self, idx):
        if hasattr(self, 'cb_temas'):
            self.current_theme_name = self.cb_temas.currentText()
            if self.current_theme_name in THEMES_EXTENDED:
                self.chip8_theme = THEMES_EXTENDED[self.current_theme_name]
                self.canvas.set_theme(self.chip8_theme)

    def on_speed_changed(self, value):
        self.cycles_per_tick = value
        if hasattr(self, 'speed_label'):
            self.speed_label.setText(f"VELOCIDAD: {value * 60} Hz")

    def toggle_play(self):
        if not self.running:
            self.running = True
            self.paused = False
            self.btn_play.setText("⏸ PAUSA")
            self.status_bar.setText(f"Estado: Ejecutando {self.cb_juegos.currentText()}")
        else:
            self.paused = not self.paused
            if self.paused:
                self.btn_play.setText("▶ REANUDAR")
                self.status_bar.setText("Estado: Pausado")
            else:
                self.btn_play.setText("⏸ PAUSA")
                self.status_bar.setText(f"Estado: Ejecutando {self.cb_juegos.currentText()}")

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        if self.sound_enabled:
            self.btn_sound.setText("🔊 SONIDO: ACTIVO")
        else:
            self.btn_sound.setText("🔇 SONIDO: DESACTIVADO")

    def cargar_fuentes(self):
        for i in range(len(FONT_SET)):
            self.memory[0x50 + i] = FONT_SET[i]

    def reset_cpu(self):
        self.memory = bytearray(4096)
        self.registers = bytearray(16)
        self.I = 0
        self.pc = 0x200
        self.stack = []
        self.delay_timer = 0
        self.sound_timer = 0
        self.keypad = [False] * 16
        self.display = [0] * (64 * 32)
        
        self.cargar_fuentes()
        for i in range(len(self.rom_data)):
            self.memory[0x200 + i] = self.rom_data[i]

        self.paused = False
        self.running = False
        if hasattr(self, 'btn_play'):
            self.btn_play.setText("▶ INICIAR")
        if hasattr(self, 'status_bar'):
            self.status_bar.setText("Estado: Cargado y listo")
        self.canvas.set_display_buffer(self.display)

    def game_loop(self):
        if not self.running or self.paused: return
        self.display_updated = False
        for _ in range(self.cycles_per_tick):
            self.emulate_cycle()

        if self.delay_timer > 0: self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1
            if self.sound_timer == 0 and self.sound_enabled:
                threading.Thread(target=self.play_beep, daemon=True).start()

        if self.display_updated:
            self.canvas.set_display_buffer(self.display)

    def play_beep(self):
        if winsound:
            try: winsound.Beep(580, 70)
            except: pass

    def emulate_cycle(self):
        if self.pc < 0x200 or self.pc >= 4094:
            self.running = False
            if hasattr(self, 'btn_play'):
                self.btn_play.setText("▶ REINICIAR")
            if hasattr(self, 'status_bar'):
                self.status_bar.setText("Estado: Fin de ejecución (Overflow PC)")
            return

        opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc += 2

        op = opcode & 0xF000
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        n = opcode & 0x000F
        kk = opcode & 0x00FF
        nnn = opcode & 0x0FFF

        if op == 0x0000:
            if opcode == 0x00E0:
                self.display = [0] * (64 * 32)
                self.display_updated = True
            elif opcode == 0x00EE:
                if self.stack: self.pc = self.stack.pop()
                else: self.running = False
        elif op == 0x1000: self.pc = nnn
        elif op == 0x2000:
            self.stack.append(self.pc)
            self.pc = nnn
        elif op == 0x3000:
            if self.registers[x] == kk: self.pc += 2
        elif op == 0x4000:
            if self.registers[x] != kk: self.pc += 2
        elif op == 0x5000:
            if self.registers[x] == self.registers[y]: self.pc += 2
        elif op == 0x6000: self.registers[x] = kk
        elif op == 0x7000: self.registers[x] = (self.registers[x] + kk) & 0xFF
        elif op == 0x8000:
            sub = opcode & 0x000F
            if sub == 0x0: self.registers[x] = self.registers[y]
            elif sub == 0x1: self.registers[x] |= self.registers[y]
            elif sub == 0x2: self.registers[x] &= self.registers[y]
            elif sub == 0x3: self.registers[x] ^= self.registers[y]
            elif sub == 0x4:
                s_val = self.registers[x] + self.registers[y]
                self.registers[0xF] = 1 if s_val > 255 else 0
                self.registers[x] = s_val & 0xFF
            elif sub == 0x5:
                self.registers[0xF] = 1 if self.registers[x] >= self.registers[y] else 0
                self.registers[x] = (self.registers[x] - self.registers[y]) & 0xFF
            elif sub == 0x6:
                self.registers[0xF] = self.registers[x] & 1
                self.registers[x] = (self.registers[x] >> 1) & 0xFF
            elif sub == 0x7:
                self.registers[0xF] = 1 if self.registers[y] >= self.registers[x] else 0
                self.registers[x] = (self.registers[y] - self.registers[x]) & 0xFF
            elif sub == 0xE:
                self.registers[0xF] = (self.registers[x] >> 7) & 1
                self.registers[x] = (self.registers[x] << 1) & 0xFF
        elif op == 0x9000:
            if self.registers[x] != self.registers[y]: self.pc += 2
        elif op == 0xA000: self.I = nnn
        elif op == 0xB000: self.pc = (nnn + self.registers[0]) & 0xFFFF
        elif op == 0xC000: self.registers[x] = random.randint(0, 255) & kk
        elif op == 0xD000:
            vx = self.registers[x]
            vy = self.registers[y]
            self.registers[0xF] = 0
            for row in range(n):
                py = (vy + row) % 32
                sprite_byte = self.memory[(self.I + row) % 4096]
                for col in range(8):
                    px = (vx + col) % 64
                    pixel_bit = (sprite_byte >> (7 - col)) & 1
                    if pixel_bit:
                        idx = py * 64 + px
                        if self.display[idx] == 1: self.registers[0xF] = 1
                        self.display[idx] ^= 1
            self.display_updated = True
        elif op == 0xE000:
            if kk == 0x9E:
                key = self.registers[x] & 0xF
                if self.keypad[key]: self.pc += 2
            elif kk == 0xA1:
                key = self.registers[x] & 0xF
                if not self.keypad[key]: self.pc += 2
        elif op == 0xF000:
            if kk == 0x07: self.registers[x] = self.delay_timer
            elif kk == 0x0A:
                key_pressed = False
                for idx, is_down in enumerate(self.keypad):
                    if is_down:
                        self.registers[x] = idx
                        key_pressed = True
                        break
                if not key_pressed: self.pc -= 2
            elif kk == 0x15: self.delay_timer = self.registers[x]
            elif kk == 0x18: self.sound_timer = self.registers[x]
            elif kk == 0x1E: self.I = (self.I + self.registers[x]) & 0xFFFF
            elif kk == 0x29: self.I = 0x50 + (self.registers[x] & 0xF) * 5
            elif kk == 0x33:
                val = self.registers[x]
                self.memory[self.I % 4096] = val // 100
                self.memory[(self.I + 1) % 4096] = (val // 10) % 10
                self.memory[(self.I + 2) % 4096] = val % 10
            elif kk == 0x55:
                for idx in range(x + 1): self.memory[(self.I + idx) % 4096] = self.registers[idx]
            elif kk == 0x65:
                for idx in range(x + 1): self.registers[idx] = self.memory[(self.I + idx) % 4096]

    # --- COMUNIDAD ROMS METODOS ---
    def escanear_roms(self):
        self.comunidad_roms_files = []
        if hasattr(self, 'cb_comunidad'):
            self.cb_comunidad.clear()
        if self.roms_dir.exists():
            for item in self.roms_dir.iterdir():
                if item.is_file() and item.suffix.lower() in [".ch8", ".rom", ".bin", ".n64", ".z64"]:
                    self.comunidad_roms_files.append(item)
                    if hasattr(self, 'cb_comunidad'):
                        self.cb_comunidad.addItem(item.name)

        if hasattr(self, 'cb_comunidad'):
            if not self.comunidad_roms_files:
                self.cb_comunidad.addItem("Sin juegos (arrastra a la carpeta)")
                if hasattr(self, 'btn_play_comunidad'):
                    self.btn_play_comunidad.setEnabled(False)
            else:
                if hasattr(self, 'btn_play_comunidad'):
                    self.btn_play_comunidad.setEnabled(True)

        if hasattr(self, 'tab_roms') and self.tab_roms and hasattr(self.tab_roms, 'actualizar_lista_roms'):
            self.tab_roms.actualizar_lista_roms(self.comunidad_roms_files)

    def abrir_carpeta_roms(self):
        path = str(self.roms_dir.resolve())
        if platform.system() == "Windows": os.startfile(path)
        elif platform.system() == "Darwin": subprocess.Popen(["open", path])
        else: subprocess.Popen(["xdg-open", path])

    def play_comunidad_game(self):
        if not hasattr(self, 'cb_comunidad'): return
        idx = self.cb_comunidad.currentIndex()
        if 0 <= idx < len(self.comunidad_roms_files):
            file_path = self.comunidad_roms_files[idx]
            self.cargar_rom_desde_archivo(file_path)

    def cargar_archivo_manual(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Cargar ROM (CHIP-8 / N64)", "", 
            "Juegos CHIP-8 / N64 (*.ch8 *.rom *.bin *.n64 *.z64);;Todos los archivos (*)"
        )
        if file_path:
            self.cargar_rom_desde_archivo(Path(file_path))

    def cargar_rom_desde_archivo(self, path):
        suffix = path.suffix.lower()
        if suffix in [".n64", ".z64"]:
            self.lanzar_n64(path)
            return
        try:
            with open(path, "rb") as f: self.rom_data = f.read()
            self.reset_cpu()
            if hasattr(self, 'status_bar'):
                self.status_bar.setText(f"Estado: Cargado {path.name}")
            self.running = True
            self.paused = False
            if hasattr(self, 'btn_play'):
                self.btn_play.setText("⏸ PAUSA")
            self.tabs.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "Error al cargar ROM", f"No se pudo leer el archivo:\n{str(e)}")

    def lanzar_n64(self, path):
        config = getattr(self.context, "config", {})
        emulador_path = config.get("ruta_emulador_n64", "")
        if not emulador_path or not os.path.exists(emulador_path):
            QMessageBox.information(
                self, "Configurar Emulador N64",
                "Para jugar juegos de Nintendo 64 (.n64 / .z64), por favor selecciona el archivo ejecutable (.exe) de tu emulador favorito (ej. Project64, Mupen64Plus, RetroArch)."
            )
            self.configurar_emulador_n64()
            emulador_path = config.get("ruta_emulador_n64", "")
            if not emulador_path or not os.path.exists(emulador_path): return

        self.paused = True
        if hasattr(self, 'btn_play'):
            self.btn_play.setText("▶ REANUDAR")
        if hasattr(self, 'status_bar'):
            self.status_bar.setText(f"Estado: Ejecutando {path.name} en emulador N64 externo")
        try:
            subprocess.Popen([emulador_path, str(path.resolve())])
        except Exception as e:
            QMessageBox.critical(self, "Error al lanzar juego N64", f"No se pudo ejecutar el emulador:\n{str(e)}")

    def configurar_emulador_n64(self):
        filtro = "Ejecutable (*.exe)" if platform.system() == "Windows" else "Todos los archivos (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Ejecutable de Emulador N64", "",
            filtro + ";;Todos los archivos (*)"
        )
        if file_path:
            if not hasattr(self.context, "config"):
                self.context.config = {}
            self.context.config["ruta_emulador_n64"] = file_path
            if hasattr(self.context, "app") and hasattr(self.context.app, "guardar_configuracion"):
                self.context.app.guardar_configuracion()
            QMessageBox.information(self, "Emulador Configurado", f"Ruta establecida con éxito:\n{file_path}")
            return True
        return False

    def actualizar_tema(self, colores):
        """Propaga la actualización del tema a la consola y a todos los submódulos."""
        self.colores = colores
        self.aplicar_estilo_tabs()
        for submod in [getattr(self, 'tab_arcade', None), getattr(self, 'tab_teclado', None),
                       getattr(self, 'tab_roms', None), getattr(self, 'tab_opciones', None)]:
            if submod and hasattr(submod, 'actualizar_tema'):
                submod.actualizar_tema(colores)

    def cleanup(self):
        """Detiene timers y libera recursos al cambiar o cerrar el módulo."""
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        self.running = False
        self.paused = True
        for submod in [getattr(self, 'tab_arcade', None), getattr(self, 'tab_teclado', None),
                       getattr(self, 'tab_roms', None), getattr(self, 'tab_opciones', None)]:
            if submod and hasattr(submod, 'cleanup'):
                submod.cleanup()
