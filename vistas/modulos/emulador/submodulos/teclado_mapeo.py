import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class TecladoMapeoSubmodule(QWidget):
    """Submódulo 2: Teclado Virtual Hexadecimal CHIP-8 (4x4) & Mapeo de Teclas PC"""
    def __init__(self, parent, context, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.visual_buttons = {}

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D2D')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        lbl_tit = QLabel("🕹️ TECLADO VIRTUAL CHIP-8 Y MAPEO DE TECLAS PC")
        lbl_tit.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tit)

        # Panel Central
        self.box = QGroupBox("🎮 Distribución Teclas Hexadecimales (4x4)")
        self.box.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.box.setStyleSheet(f"""
            QGroupBox {{
                background: {bg_sec};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                padding: 20px;
                color: {acento};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 5px; }}
        """)
        b_lay = QVBoxLayout(self.box)
        b_lay.setSpacing(15)

        # Grid 4x4
        grid_w = QWidget()
        g_lay = QGridLayout(grid_w)
        g_lay.setSpacing(10)

        keys_layout = [
            ("1", "1", 0x1), ("2", "2", 0x2), ("3", "3", 0x3), ("C", "4", 0xC),
            ("4", "Q", 0x4), ("5", "W", 0x5), ("6", "E", 0x6), ("D", "R", 0xD),
            ("7", "A", 0x7), ("8", "S", 0x8), ("9", "D", 0x9), ("E", "F", 0xE),
            ("A", "Z", 0xA), ("0", "X", 0x0), ("B", "C", 0xB), ("F", "V", 0xF)
        ]

        set_key_cb = self.callbacks.get("set_key_state", lambda v, p: None)

        for idx, (lbl_c8, lbl_pc, val) in enumerate(keys_layout):
            btn = QPushButton(f"{lbl_c8}\n(Tecla PC: {lbl_pc})")
            btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            btn.setFixedSize(110, 65)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_terc};
                    color: white;
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 1px solid {acento};
                    background: rgba(99,102,241,0.25);
                }}
            """)
            btn.pressed.connect(lambda v=val: set_key_cb(v, True))
            btn.released.connect(lambda v=val: set_key_cb(v, False))

            r, c = idx // 4, idx % 4
            g_lay.addWidget(btn, r, c)
            self.visual_buttons[val] = btn

        b_lay.addWidget(grid_w, 0, Qt.AlignmentFlag.AlignCenter)

        # Guía de Mapeo
        guide = QLabel(
            "<b>💡 Guía de Mapeo del Teclado:</b><br>"
            "• La matriz del CHIP-8 usa 16 teclas hexadecimales (0-F).<br>"
            "• En tu teclado físico de PC se mapean en las filas superior e inferior: <b>[1 2 3 4]</b>, <b>[Q W E R]</b>, <b>[A S D F]</b>, <b>[Z X C V]</b>.<br>"
            "• En juegos como <b>Pong</b>, <i>1 y Q</i> mueven el jugador 1, mientras que <i>4 y R</i> mueven el jugador 2."
        )
        guide.setFont(QFont(self.font_family, 9))
        guide.setStyleSheet("color: rgba(255,255,255,0.6); line-height: 1.4;")
        guide.setWordWrap(True)
        b_lay.addWidget(guide)

        layout.addWidget(self.box, 1)

    def update_key_button(self, val, is_pressed):
        btn = self.visual_buttons.get(val)
        if btn:
            if is_pressed:
                acento = self.colores.get('acento', '#6366F1')
                btn.setStyleSheet(f"""
                    background-color: {acento};
                    color: white; border: 2px solid white; font-weight: bold;
                """)
            else:
                bg_terc = self.colores.get('bg_terciario', '#2D2D2D')
                acento = self.colores.get('acento', '#6366F1')
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_terc};
                        color: white;
                        border: 1px solid rgba(255,255,255,0.1);
                        border-radius: 10px;
                    }}
                    QPushButton:hover {{
                        border: 1px solid {acento};
                        background: rgba(99,102,241,0.25);
                    }}
                """)

    def actualizar_tema(self, colores):
        """Actualiza la paleta de colores dinámicamente."""
        self.colores = colores
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D2D')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        if hasattr(self, 'box'):
            self.box.setStyleSheet(f"""
                QGroupBox {{
                    background: {bg_sec};
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 12px;
                    padding: 20px;
                    color: {acento};
                }}
                QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 5px; }}
            """)
        for val, btn in self.visual_buttons.items():
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_terc};
                    color: white;
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 1px solid {acento};
                    background: rgba(99,102,241,0.25);
                }}
            """)

    def cleanup(self):
        """Libera recursos."""
        pass
