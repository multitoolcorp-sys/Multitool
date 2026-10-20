import platform
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QListWidget, QStackedWidget,
    QFrame, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from ..utils.controlador_avanzado import ControladorAvanzado


class TabAvanzado(QWidget):
    """Pestaña de Herramientas Avanzadas y Diagnóstico"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.controlador = ControladorAvanzado(self)

        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "monospace"

        self.inicializar_ui()

    def inicializar_ui(self):
        self.setStyleSheet("color: white;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # ── Menú lateral (Sidebar) ──────────────────────────────
        self.sidebarMenu = QListWidget()
        self.sidebarMenu.setFixedWidth(210)
        self.sidebarMenu.setFont(QFont(self.font_family, 10))
        self.sidebarMenu.setSpacing(2)
        self.sidebarMenu.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.05);
                padding: 10px 6px;
                outline: none;
            }}
            QListWidget::item {{
                color: {self.colores['fg_secundario']};
                border-radius: 8px;
                padding: 12px 14px;
                margin-bottom: 2px;
            }}
            QListWidget::item:hover {{
                background-color: rgba(255,255,255,0.05);
                color: white;
            }}
            QListWidget::item:selected {{
                background-color: {self.colores['acento']}22;
                color: white;
                font-weight: bold;
                border-left: 3px solid {self.colores['acento']};
            }}
        """)

        self.sidebarMenu.addItem("💻  Entorno")
        self.sidebarMenu.addItem("🌐  Red Avanzada")
        self.sidebarMenu.addItem("🛡️  Seguridad")
        self.sidebarMenu.addItem("⚙️  Herramientas")
        self.sidebarMenu.currentRowChanged.connect(self.cambiar_pagina)
        layout.addWidget(self.sidebarMenu)

        # ── Stacked Widget para contenido ───────────────────────
        self.stacked = QStackedWidget()

        # Estilos compartidos
        btn_style = f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
            QPushButton:pressed {{ background: {self.colores['acento']}cc; }}
        """
        txt_style = f"""
            QTextEdit, QLineEdit {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
                padding: 12px;
                font-family: '{self.mono_font}';
                font-size: 10pt;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1.5px solid {self.colores['acento']};
                background-color: {self.colores['bg_terciario']};
            }}
        """

        # ────────────────────────────────────────────────────────
        # PAGINA 0: ENTORNO
        # ────────────────────────────────────────────────────────
        env_w = QFrame()
        env_w.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 12px;")
        env_l = QVBoxLayout(env_w)
        env_l.setContentsMargins(25, 25, 25, 25)
        env_l.setSpacing(12)

        btn_env = QPushButton("📋  Cargar Variables de Entorno")
        btn_env.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_env.setFixedHeight(40)
        btn_env.setStyleSheet(btn_style)
        btn_env.clicked.connect(self.controlador.cargar_entorno)
        env_l.addWidget(btn_env)

        self.txt_env = QTextEdit()
        self.txt_env.setReadOnly(True)
        self.txt_env.setStyleSheet(txt_style)
        env_l.addWidget(self.txt_env)
        self.stacked.addWidget(env_w)

        # ────────────────────────────────────────────────────────
        # PAGINA 1: RED AVANZADA  (layout horizontal dos paneles)
        # ────────────────────────────────────────────────────────
        red_w = QFrame()
        red_w.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 12px;")
        red_h = QHBoxLayout(red_w)
        red_h.setContentsMargins(14, 14, 14, 14)
        red_h.setSpacing(12)

        # Panel izquierdo — Detalles de Red
        left_red = QFrame()
        left_red.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        left_l = QVBoxLayout(left_red)
        left_l.setContentsMargins(16, 14, 16, 14)
        left_l.setSpacing(10)

        lbl_red_tit = QLabel("🔌  DETALLES DE RED")
        lbl_red_tit.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_red_tit.setStyleSheet(f"color: {self.colores['fg_secundario']}; letter-spacing: 1.5px;")
        left_l.addWidget(lbl_red_tit)

        btn_red = QPushButton("🔍  Obtener Detalles de Red")
        btn_red.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_red.setFixedHeight(38)
        btn_red.setStyleSheet(btn_style)
        btn_red.clicked.connect(self.controlador.cargar_red_avanzada)
        left_l.addWidget(btn_red)

        self.txt_red_info = QTextEdit()
        self.txt_red_info.setReadOnly(True)
        self.txt_red_info.setStyleSheet(txt_style)
        left_l.addWidget(self.txt_red_info, 1)

        # Panel derecho — Diagnóstico de Red
        right_red = QFrame()
        right_red.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        right_l = QVBoxLayout(right_red)
        right_l.setContentsMargins(16, 14, 16, 14)
        right_l.setSpacing(10)

        lbl_diag_tit = QLabel("📡  DIAGNÓSTICO DE RED")
        lbl_diag_tit.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_diag_tit.setStyleSheet(f"color: {self.colores['fg_secundario']}; letter-spacing: 1.5px;")
        right_l.addWidget(lbl_diag_tit)

        # Estilos de controles de diagnóstico
        ctrl_combo_style = f"""
            QComboBox {{
                background: {self.colores['bg_principal']};
                color: white;
                padding: 5px 10px;
                border-radius: 7px;
                border: 1px solid rgba(255,255,255,0.08);
                font-size: 9pt;
            }}
            QComboBox::drop-down {{ border: none; width: 18px; }}
            QComboBox QAbstractItemView {{
                background: {self.colores['bg_terciario']};
                color: white;
                selection-background-color: {self.colores['acento']}44;
            }}
        """
        ctrl_spin_style = f"""
            QSpinBox {{
                background: {self.colores['bg_principal']};
                color: white;
                padding: 5px 8px;
                border-radius: 7px;
                border: 1px solid rgba(255,255,255,0.08);
                font-size: 9pt;
            }}
            QSpinBox:focus {{ border: 1.5px solid {self.colores['acento']}; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: {self.colores['bg_terciario']};
                border-radius: 3px;
                width: 18px;
            }}
        """
        ctrl_input_style = f"""
            QLineEdit {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 7px;
                padding: 0px 10px;
                font-size: 9pt;
            }}
            QLineEdit:focus {{ border: 1.5px solid {self.colores['acento']}; }}
        """

        # Fila 1: tipo + host
        h_tipo = QHBoxLayout()
        h_tipo.setSpacing(8)
        self.combo_diag = QComboBox()
        self.combo_diag.addItems(["Ping", "Tracert", "NSLookup"])
        self.combo_diag.setFixedHeight(36)
        self.combo_diag.setStyleSheet(ctrl_combo_style)
        h_tipo.addWidget(self.combo_diag)

        self.txt_ping_host = QLineEdit("google.com")
        self.txt_ping_host.setFixedHeight(36)
        self.txt_ping_host.setStyleSheet(ctrl_input_style)
        h_tipo.addWidget(self.txt_ping_host, 1)
        right_l.addLayout(h_tipo)

        # Fila 2: repeticiones + botón ejecutar
        h_count = QHBoxLayout()
        h_count.setSpacing(8)

        lbl_count = QLabel("Repeticiones:")
        lbl_count.setFont(QFont(self.font_family, 9))
        lbl_count.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        h_count.addWidget(lbl_count)

        self.spin_ping_count = QSpinBox()
        self.spin_ping_count.setRange(1, 100)
        self.spin_ping_count.setValue(4)
        self.spin_ping_count.setFixedSize(80, 36)
        self.spin_ping_count.setToolTip(
            "Ping: número de paquetes\n"
            "Tracert: saltos máximos\n"
            "NSLookup: sin efecto"
        )
        self.spin_ping_count.setStyleSheet(ctrl_spin_style)
        h_count.addWidget(self.spin_ping_count)

        h_count.addStretch()

        self.btn_diag_run = QPushButton("▶  Ejecutar")
        self.btn_diag_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_diag_run.setFixedHeight(36)
        self.btn_diag_run.setStyleSheet(btn_style)
        self.btn_diag_run.clicked.connect(self._ejecutar_diagnostico_async)
        h_count.addWidget(self.btn_diag_run)
        right_l.addLayout(h_count)

        # Hint contextual
        self.lbl_diag_hint = QLabel(
            "Ping: N paquetes ICMP  •  Tracert: N saltos máx.  •  NSLookup: ignora repeticiones"
        )
        self.lbl_diag_hint.setFont(QFont(self.font_family, 8))
        self.lbl_diag_hint.setStyleSheet(
            f"color: {self.colores['fg_secundario']}; font-style: italic;"
        )
        self.lbl_diag_hint.setWordWrap(True)
        right_l.addWidget(self.lbl_diag_hint)

        self.txt_ping_res = QTextEdit()
        self.txt_ping_res.setReadOnly(True)
        self.txt_ping_res.setStyleSheet(txt_style)
        right_l.addWidget(self.txt_ping_res, 1)

        # Ensamblar los dos paneles
        red_h.addWidget(left_red, 1)
        red_h.addWidget(right_red, 1)
        self.stacked.addWidget(red_w)

        # ────────────────────────────────────────────────────────
        # PAGINA 2: SEGURIDAD
        # ────────────────────────────────────────────────────────
        sec_w = QFrame()
        sec_w.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 12px;")
        sec_l = QVBoxLayout(sec_w)
        sec_l.setContentsMargins(25, 25, 25, 25)
        sec_l.setSpacing(12)

        btn_sec = QPushButton("🛡️  Escanear Seguridad Local")
        btn_sec.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sec.setFixedHeight(40)
        btn_sec.setStyleSheet(btn_style)
        btn_sec.clicked.connect(self.controlador.escanear_seguridad)
        sec_l.addWidget(btn_sec)

        self.lbl_fw_status = QLabel("Estado del Firewall: Pendiente")
        self.lbl_fw_status.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_fw_status.setStyleSheet(
            f"background: {self.colores['bg_secundario']}; padding: 15px; "
            f"border-radius: 8px; color: {self.colores['exito']};"
        )
        sec_l.addWidget(self.lbl_fw_status)

        self.txt_sec_info = QTextEdit()
        self.txt_sec_info.setReadOnly(True)
        self.txt_sec_info.setStyleSheet(txt_style)
        sec_l.addWidget(self.txt_sec_info)
        self.stacked.addWidget(sec_w)

        # ────────────────────────────────────────────────────────
        # PAGINA 3: HERRAMIENTAS
        # ────────────────────────────────────────────────────────
        tools_w = QFrame()
        tools_w.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 12px;")
        tools_l = QVBoxLayout(tools_w)
        tools_l.setContentsMargins(40, 40, 40, 40)
        tools_l.setSpacing(20)

        lbl_tools = QLabel("MANTENIMIENTO")
        lbl_tools.setFont(QFont(self.font_family, 14, QFont.Weight.Bold))
        lbl_tools.setStyleSheet(f"color: {self.colores['acento']};")
        tools_l.addWidget(lbl_tools)

        btn_tools_style = f"""
            QPushButton {{
                background: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.05);
                text-align: left;
                padding: 20px;
            }}
            QPushButton:hover {{ background: {self.colores['acento']}; color: white; border: none; }}
        """

        items = [
            ("🗑️ Limpiar Archivos Temporales", "Liberar espacio en caché del sistema y usuario", self.controlador.limpiar_temp),
            ("🌐 Vaciar Caché DNS", "Resolver problemas de resolución de nombres de red", self.controlador.flush_dns),
            ("🔄 Reiniciar Interfaz / Shell", "Recuperar barra de tareas o entorno de escritorio", self.controlador.restart_shell),
        ]

        for title, description, callback in items:
            btn = QPushButton(f"{title}\n{description}")
            btn.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(btn_tools_style)
            btn.clicked.connect(callback)
            tools_l.addWidget(btn)

        self.txt_tools_info = QTextEdit()
        self.txt_tools_info.setReadOnly(True)
        self.txt_tools_info.setStyleSheet(txt_style)
        self.txt_tools_info.setPlaceholderText("Resultados del mantenimiento...")
        tools_l.addWidget(self.txt_tools_info)

        tools_l.addStretch()
        self.stacked.addWidget(tools_w)

        layout.addWidget(self.stacked, 1)
        self.sidebarMenu.setCurrentRow(0)

    # ──────────────────────────────────────────────────────────────
    #  Diagnóstico en tiempo real (streaming, thread-safe)
    # ──────────────────────────────────────────────────────────────
    def _ejecutar_diagnostico_async(self):
        """Lanza el diagnóstico en streaming: salida línea a línea en tiempo real."""
        self.btn_diag_run.setEnabled(False)
        self.btn_diag_run.setText("⏳  Ejecutando…")
        self.txt_ping_res.clear()
        self.txt_ping_res.setPlainText("")

        def _append_linea(linea: str):
            """Añade una línea al widget desde el hilo principal via QTimer."""
            QTimer.singleShot(0, lambda l=linea: self.txt_ping_res.append(l))

        def _fin():
            """Restaura el botón desde el hilo principal."""
            QTimer.singleShot(0, self._diagnostico_finalizado)

        def _run():
            self.controlador.ejecutar_diagnostico_streaming(_append_linea, _fin)

        threading.Thread(target=_run, daemon=True).start()

    def _diagnostico_finalizado(self):
        self.btn_diag_run.setEnabled(True)
        self.btn_diag_run.setText("▶  Ejecutar")

    def cambiar_pagina(self, idx):
        self.stacked.setCurrentIndex(idx)
