"""
dispositivos.py - Submódulo de Información de Dispositivo y Sesión Activa (con Scrollbar Responsivo)
"""
import os
import socket
import platform
import psutil
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class TabDispositivos(QWidget):
    """Submódulo para inspeccionar el dispositivo actual y los detalles de la sesión con Scrollbar responsivo"""
    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent)
        self.context = context
        self.colores = colores or {}
        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # QScrollArea para asegurar responsividad sin encoger texto
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {bg_p}; }}")

        content = QWidget()
        content.setStyleSheet(f"background-color: {bg_p};")
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(20, 20, 20, 20)
        content_lay.setSpacing(16)

        # Header
        lbl_tit = QLabel("📱 DISPOSITIVO Y SESIÓN ACTIVA")
        lbl_tit.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        content_lay.addWidget(lbl_tit)

        # Card 1: Datos del Dispositivo
        card_sys = QFrame()
        card_sys.setStyleSheet(f"""
            QFrame {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 16px;
            }}
        """)
        c_lay = QVBoxLayout(card_sys)
        c_lay.setSpacing(12)

        lbl_s_head = QLabel("💻 ESPECIFICACIONES DE HARDWARE Y SO")
        lbl_s_head.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_s_head.setStyleSheet("color: white;")
        c_lay.addWidget(lbl_s_head)

        grid = QGridLayout()
        grid.setSpacing(10)

        host_name = socket.gethostname()
        try:
            ip_local = socket.gethostbyname(host_name)
        except Exception:
            ip_local = "127.0.0.1"

        os_ver = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"
        cpu_name = platform.processor() or f"{psutil.cpu_count(logical=True)} Núcleos"
        ram_total = f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB"

        items = [
            ("💻 Nombre del Equipo:", host_name),
            ("🌐 Dirección IP Local:", ip_local),
            ("🖥️ Sistema Operativo:", os_ver),
            ("🧠 Procesador / CPU:", cpu_name),
            ("💾 Memoria RAM Total:", ram_total),
        ]

        for idx, (lbl, val) in enumerate(items):
            l = QLabel(lbl)
            l.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 11px; font-weight: bold;")
            v = QLabel(val)
            v.setStyleSheet("color: white; font-size: 11px;")
            v.setWordWrap(True)
            grid.addWidget(l, idx, 0)
            grid.addWidget(v, idx, 1)

        c_lay.addLayout(grid)
        content_lay.addWidget(card_sys)

        # Card 2: Sesión Activa
        card_ses = QFrame()
        card_ses.setStyleSheet(f"""
            QFrame {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 16px;
            }}
        """)
        cs_lay = QVBoxLayout(card_ses)
        cs_lay.setSpacing(8)

        lbl_ses_head = QLabel("🔑 ESTADO DE LA SESIÓN")
        lbl_ses_head.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_ses_head.setStyleSheet("color: white;")
        cs_lay.addWidget(lbl_ses_head)

        user_name = getattr(self.context, "usuario", "Usuario Actual") if self.context else "Usuario"
        lbl_user = QLabel(f"👤 Usuario Conectado: <b>{user_name}</b>")
        lbl_user.setStyleSheet("color: #34D399; font-size: 11px;")
        lbl_user.setWordWrap(True)
        cs_lay.addWidget(lbl_user)

        lbl_status = QLabel("🟢 Estado: Sesión Cifrada y Autenticada Localmente")
        lbl_status.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px;")
        lbl_status.setWordWrap(True)
        cs_lay.addWidget(lbl_status)

        content_lay.addWidget(card_ses)
        content_lay.addStretch()

        scroll.setWidget(content)
        main_lay.addWidget(scroll)
