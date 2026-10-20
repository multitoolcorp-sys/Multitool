import socket
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QListWidget, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication

class ConexionLanSubmodule(QWidget):
    """Submódulo 2: Servidor Host, Conexión LAN & Gestión de Usuarios en Línea"""
    def __init__(self, parent, context, colores, callbacks, manager):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.manager = manager
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#1E1E1E')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        bg_terc = self.colores.get('bg_terciario', '#3D3D3D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#4CAF50')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        lbl_tit = QLabel("🌐 SERVIDOR HOST Y CONEXIÓN A RED LOCAL (LAN)")
        lbl_tit.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tit)

        # ── Panel 1: Parámetros de Conexión ──
        conn_box = QGroupBox("📡 Parámetros de Red y Servidor")
        conn_box.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        conn_box.setStyleSheet(f"""
            QGroupBox {{
                background: {bg_sec};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                margin-top: 10px;
                padding: 15px;
                color: {acento};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 5px; }}
            QLabel {{ color: {self.colores.get('fg_secundario', '#A0A0A0')}; font-size: 11px; font-weight: bold; }}
            QLineEdit {{
                background: {bg_terc}; border: 1px solid rgba(255, 255, 255, 0.08);
                color: white; border-radius: 6px; padding: 6px 10px; font-family: Consolas, monospace; font-size: 11px;
            }}
            QLineEdit:focus {{ border: 1px solid {acento}; }}
        """)
        c_lay = QHBoxLayout(conn_box)
        c_lay.setSpacing(15)

        v_user = QVBoxLayout()
        v_user.addWidget(QLabel("MI USUARIO:"))
        self.txt_usuario = QLineEdit(getattr(self.context, "usuario", "Usuario"))
        self.txt_usuario.setFixedWidth(130)
        v_user.addWidget(self.txt_usuario)
        c_lay.addLayout(v_user)

        v_ip = QVBoxLayout()
        v_ip.addWidget(QLabel("IP HOST (PARA UNIRSE):"))
        self.txt_ip = QLineEdit("127.0.0.1")
        self.txt_ip.setFixedWidth(140)
        v_ip.addWidget(self.txt_ip)
        c_lay.addLayout(v_ip)

        v_port = QVBoxLayout()
        v_port.addWidget(QLabel("PUERTO LAN:"))
        self.txt_port = QLineEdit("55400")
        self.txt_port.setFixedWidth(80)
        v_port.addWidget(self.txt_port)
        c_lay.addLayout(v_port)

        c_lay.addStretch()

        # Botones de Acción
        self.btn_host = QPushButton("📡 CREAR HOST")
        self.btn_host.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_host.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_host.setFixedSize(130, 36)
        self.btn_host.setStyleSheet(f"""
            QPushButton {{ background: {exito}; color: white; border-radius: 8px; border: none; }}
            QPushButton:hover {{ background: #3b8e5c; }}
        """)
        self.btn_host.clicked.connect(self.callbacks.get("iniciar_host", lambda: None))
        c_lay.addWidget(self.btn_host, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.btn_join = QPushButton("🔗 UNIRSE A HOST")
        self.btn_join.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_join.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_join.setFixedSize(130, 36)
        self.btn_join.setStyleSheet(f"""
            QPushButton {{ background: {acento}; color: white; border-radius: 8px; border: none; }}
            QPushButton:hover {{ background: #4f46e5; }}
        """)
        self.btn_join.clicked.connect(self.callbacks.get("unirse_host", lambda: None))
        c_lay.addWidget(self.btn_join, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.btn_disconnect = QPushButton("❌ DESCONECTAR")
        self.btn_disconnect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_disconnect.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_disconnect.setFixedSize(130, 36)
        self.btn_disconnect.hide()
        self.btn_disconnect.setStyleSheet(f"""
            QPushButton {{ background: {self.colores.get('error', '#F44336')}; color: white; border-radius: 8px; border: none; }}
            QPushButton:hover {{ background: #d32f2f; }}
        """)
        self.btn_disconnect.clicked.connect(self.callbacks.get("desconectar", lambda: None))
        c_lay.addWidget(self.btn_disconnect, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(conn_box)

        # ── Panel 2: Diagnóstico de IP Local y Usuarios Conectados ──
        diag_box = QGroupBox("👥 Estado de Red & Usuarios Conectados")
        diag_box.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        diag_box.setStyleSheet(conn_box.styleSheet())
        d_lay = QVBoxLayout(diag_box)
        d_lay.setSpacing(10)

        ip_row = QHBoxLayout()
        self.lbl_ip_local = QLabel("📍 Mi Dirección IP Local: Detectando...")
        self.lbl_ip_local.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.lbl_ip_local.setStyleSheet(f"color: {acento};")
        ip_row.addWidget(self.lbl_ip_local)

        ip_row.addStretch()

        btn_copy_ip = QPushButton("📋 Copiar IP Local")
        btn_copy_ip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_ip.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
        btn_copy_ip.clicked.connect(self._copiar_ip_local)
        ip_row.addWidget(btn_copy_ip)

        d_lay.addLayout(ip_row)

        self.list_online = QListWidget()
        self.list_online.setFont(QFont(self.font_family, 9))
        self.list_online.setStyleSheet(f"""
            QListWidget {{
                background: {bg_terc}; color: white; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); padding: 5px;
            }}
            QListWidget::item {{ padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.05); }}
        """)
        d_lay.addWidget(self.list_online, 1)

        layout.addWidget(diag_box, 1)
        self._detectar_ip_local()

    def _detectar_ip_local(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            try: ip = socket.gethostbyname(socket.gethostname())
            except Exception: ip = "127.0.0.1"
        self.lbl_ip_local.setText(f"📍 Mi Dirección IP Local (LAN): {ip}")
        self.txt_ip.setText(ip)

    def _copiar_ip_local(self):
        ip = self.txt_ip.text()
        QGuiApplication.clipboard().setText(ip)
        QMessageBox.information(self, "Copiado", f"IP '{ip}' copiada al portapapeles.")
