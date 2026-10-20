import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QFrame, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

THEMES_EXTENDED = {
    "Verde Matrix": {"bg": "#0B120B", "active": "#10FF10", "accent": "#39FF14"},
    "Rosa Cyberpunk": {"bg": "#120216", "active": "#FF007F", "accent": "#00FFFF"},
    "Ámbar CRT": {"bg": "#0F0A00", "active": "#FFA500", "accent": "#FFD700"},
    "Frost Azul": {"bg": "#0B0F19", "active": "#60A5FA", "accent": "#3B82F6"},
    "Neon Vaporwave": {"bg": "#1A002C", "active": "#00F0FF", "accent": "#FF00AA"}
}

class OpcionesRetroSubmodule(QWidget):
    """Submódulo 4: Opciones Visuales, Paletas CRT Retro & Ajustes de Audio Sintetizado"""
    def __init__(self, parent, context, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        lbl_tit = QLabel("⚙️ AJUSTES RETRO Y PALETAS DE PANTALLA CRT")
        lbl_tit.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tit)

        # ── Paletas de Color ──
        self.box_theme = QGroupBox("🎨 Paleta de Color del Monitor CRT")
        self.box_theme.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.box_theme.setStyleSheet(f"""
            QGroupBox {{
                background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 15px; color: {acento};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 5px; }}
            QComboBox {{ background: {bg_terc}; color: white; border-radius: 6px; padding: 8px; border: none; }}
            QPushButton {{ background: {bg_terc}; color: white; border-radius: 6px; padding: 8px 14px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background: {acento}; }}
        """)
        t_lay = QVBoxLayout(self.box_theme)
        t_lay.setSpacing(10)

        self.cb_temas = QComboBox()
        self.cb_temas.addItems(list(THEMES_EXTENDED.keys()))
        self.cb_temas.currentIndexChanged.connect(self.callbacks.get("on_theme_changed", lambda i: None))
        t_lay.addWidget(self.cb_temas)

        lbl_desc = QLabel("Personaliza la iluminación de fósforo del monitor retro. Incluye resplandor fluorescente (Glow/Bloom) y líneas de barrido CRT.")
        lbl_desc.setFont(QFont(self.font_family, 9))
        lbl_desc.setStyleSheet("color: rgba(255,255,255,0.5);")
        t_lay.addWidget(lbl_desc)

        layout.addWidget(self.box_theme)

        # ── Ajustes de Audio Sintetizado ──
        self.box_audio = QGroupBox("🔊 Sintetizador de Audio BEEP")
        self.box_audio.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.box_audio.setStyleSheet(self.box_theme.styleSheet())
        a_lay = QVBoxLayout(self.box_audio)
        a_lay.setSpacing(10)

        self.btn_test_beep = QPushButton("🔔 PROBAR SONIDO BEEP (580 Hz)")
        self.btn_test_beep.clicked.connect(self.callbacks.get("play_beep", lambda: None))
        a_lay.addWidget(self.btn_test_beep)

        layout.addWidget(self.box_audio)
        layout.addStretch()

    def actualizar_tema(self, colores):
        """Actualiza la paleta de colores dinámicamente."""
        self.colores = colores
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        group_style = f"""
            QGroupBox {{
                background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 15px; color: {acento};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 5px; }}
            QComboBox {{ background: {bg_terc}; color: white; border-radius: 6px; padding: 8px; border: none; }}
            QPushButton {{ background: {bg_terc}; color: white; border-radius: 6px; padding: 8px 14px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background: {acento}; }}
        """
        if hasattr(self, 'box_theme'):
            self.box_theme.setStyleSheet(group_style)
        if hasattr(self, 'box_audio'):
            self.box_audio.setStyleSheet(group_style)

    def cleanup(self):
        """Libera recursos."""
        pass
