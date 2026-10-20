import platform
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtGui import QFont

from .launcher import LauncherGUI
from .soundboard import SoundboardGUI

class LanzadorSoundboardSubmodule(QWidget):
    """Submódulo 4: Hub de Lanzador de Apps & Soundboard Audio"""
    def __init__(self, parent, context, colores, ruta_usuario):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.ruta_usuario = ruta_usuario
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # TabWidget Interno
        self.tabs_inner = QTabWidget()
        self.tabs_inner.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.tabs_inner.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {bg_main}; }}
            QTabBar {{ background: {bg_sec}; border-bottom: 1px solid rgba(255,255,255,0.08); }}
            QTabBar::tab {{ 
                background: {bg_sec}; color: #AAB0B8; 
                padding: 8px 16px; font-weight: bold; border-top-left-radius: 6px; border-top-right-radius: 6px; 
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{ 
                background: {acento}; color: white; 
            }}
        """)

        # 1. Lanzador
        self.launcher = LauncherGUI(self, self.colores, self.ruta_usuario)
        self.tabs_inner.addTab(self.launcher, "🚀 Lanzador de Aplicaciones")

        # 2. Soundboard
        self.soundboard = SoundboardGUI(self, self.colores, self.ruta_usuario)
        self.tabs_inner.addTab(self.soundboard, "🔊 Soundboard de Efectos Audio")

        layout.addWidget(self.tabs_inner)
