import datetime
import time
import platform
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class PanelReloj(QFrame):
    """Panel de reloj digital premium con fecha dinámica"""
    def __init__(self, parent, config, colores):
        super().__init__(parent)
        self.config = config
        self.colores = colores
        self.running = False
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(45, 45, 45, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }}
            QFrame:hover {{
                background-color: rgba(45, 45, 45, 0.65);
                border: 1px solid rgba(99, 102, 241, 0.4);
            }}
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(10)
        
        # Título del Panel
        self.lbl_titulo = QLabel("⏰ TIEMPO ACTUAL")
        self.lbl_titulo.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_titulo.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        self.layout.addWidget(self.lbl_titulo)
        
        # Reloj
        self.lbl_reloj = QLabel("--:--:--")
        # Fuente monoespaciada para evitar saltos
        mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        self.lbl_reloj.setFont(QFont(mono_font, 48, QFont.Weight.Bold))
        self.lbl_reloj.setStyleSheet(f"color: white; border: none; background: transparent;")
        self.lbl_reloj.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.lbl_reloj)
        
        # Fecha
        self.lbl_fecha = QLabel("")
        self.lbl_fecha.setFont(QFont(self.font_family, 12))
        self.lbl_fecha.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        self.lbl_fecha.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.lbl_fecha)
        
        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar_reloj)
        self.iniciar_reloj()

    def iniciar_reloj(self):
        self.running = True
        self.timer.start(1000)
        self.actualizar_reloj()
        
    def detener_reloj(self):
        self.running = False
        self.timer.stop()

    def actualizar_reloj(self):
        ahora = datetime.datetime.now()
        hora_actual = ahora.strftime("%H:%M:%S")
        self.lbl_reloj.setText(hora_actual)
        
        # Formato de fecha localizado (manual o locale)
        # Por simplicidad mantenemos el formato strftime pero mejoramos la presentación
        fecha_texto = ahora.strftime("%A, %d de %B de %Y")
        if self.lbl_fecha.text() != fecha_texto:
            self.lbl_fecha.setText(fecha_texto)

    def crear(self): return self

