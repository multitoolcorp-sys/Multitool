"""
seguridad_main.py - Módulo Principal de Seguridad y Bóveda Cifrada para MultiTool
Implementa:
- Bóveda de secretos protegida con cifrado AES-256-CBC y derivación PBKDF2.
- Auto-bloqueo por inactividad tras 15 minutos sin interacción.
- Auto-limpieza de portapapeles tras 45 segundos para contraseñas sensibles.
- Categorización de secretos (Web, Aplicaciones, Servidores, Tarjetas, Notas).
- Interfaz responsiva con QSplitter y sincronización de temas visuales.
- Integración con Visor de Procesos, Calculadora de Hashes, Generador y Auditoría.
"""

import json
import base64
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QFrame, QStackedWidget,
    QDialog, QTextEdit, QApplication, QSplitter, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QDateTime, QUrl
from PyQt6.QtGui import QFont, QDesktopServices

from .utils.crypto import (
    derive_key, encrypt_vault, decrypt_vault, encrypt_decrypt_vigenere
)
from .submodulos.dialogos_seguridad import (
    PasswordGeneratorDialog, HashCalculatorDialog, VaultAuditDialog, ExportImportDialog
)
from .submodulos.procesos_view import ProcesosView


CATEGORIAS_DISPONIBLES = [
    "General",
    "Web / Online",
    "Aplicaciones",
    "Servidores / SSH",
    "Finanzas / Tarjetas",
    "Notas Seguras"
]


class TabSeguridad(QWidget):
    """Módulo Principal de Seguridad - Bóveda Cifrada con AES-256."""

    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.context = context
        self.usuario = getattr(context, "usuario", None) if context else None
        
        # Paleta de colores sincronizada
        self.colores = getattr(getattr(context, "app", None), "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "error": "#F87171", "exito": "#34D399", "advertencia": "#FBBF24"
        })
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", ".")) if context else Path(".")
        self.ruta_vault = self.ruta_usuario / "caja_fuerte.json"

        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin":
            self.font_family = ".AppleSystemUIFont"

        self.desbloqueada = False
        self.master_pwd: Optional[str] = None
        self.secretos: List[Dict[str, Any]] = []
        self.indice_secreto_actual = -1
        self.last_auth_time: Optional[QDateTime] = None
        self.auth_timeout_minutes = 15
        
        # Historial de texto copiado para limpieza de portapapeles
        self._clipboard_sensitive_text: Optional[str] = None

        self.inicializar_ui()

        # Timer de auto-bloqueo por inactividad
        self.timer_lock = QTimer(self)
        self.timer_lock.timeout.connect(self.check_auth_timeout)
        self.timer_lock.start(30000) # Chequeo cada 30 segundos

        # Timer de limpieza de portapapeles
        self.timer_clipboard = QTimer(self)
        self.timer_clipboard.setSingleShot(True)
        self.timer_clipboard.timeout.connect(self._limpiar_portapapeles_auto)

    def inicializar_ui(self):
        self.setStyleSheet(f"background-color: {self.colores['bg_principal']}; border: none;")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.stack = QStackedWidget(self)
        self.main_layout.addWidget(self.stack)

        # Página 1: Bloqueada
        self.page_locked = QWidget()
        self.setup_locked_page()
        self.stack.addWidget(self.page_locked)

        # Página 2: Desbloqueada (Bóveda)
        self.page_vault = QWidget()
        self.setup_vault_page()
        self.stack.addWidget(self.page_vault)

        # Página 3: Visor de Procesos
        self.page_procesos = ProcesosView(self, self.colores, self.font_family)
        self.page_procesos.volver_solicitado.connect(lambda: self.stack.setCurrentWidget(self.page_vault))
        self.stack.addWidget(self.page_procesos)

        self.stack.setCurrentWidget(self.page_locked)

    # ── Pantalla de Bloqueo ───────────────────────────────────────────
    def setup_locked_page(self):
        lay = QVBoxLayout(self.page_locked)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(18)

        lbl_icon = QLabel("🔐")
        lbl_icon.setFont(QFont(self.font_family, 58))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_icon)

        self.lbl_locked_title = QLabel("BÓVEDA DE SEGURIDAD")
        self.lbl_locked_title.setFont(QFont(self.font_family, 20, QFont.Weight.Bold))
        self.lbl_locked_title.setStyleSheet("color: white; border: none; background: transparent;")
        self.lbl_locked_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_locked_title)

        self.lbl_locked_desc = QLabel("Cifrado AES-256 militar para tus contraseñas y datos sensibles.")
        self.lbl_locked_desc.setFont(QFont(self.font_family, 10))
        self.lbl_locked_desc.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        self.lbl_locked_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_locked_desc)

        container = QFrame()
        container.setFixedWidth(360)
        c_lay = QVBoxLayout(container)
        c_lay.setSpacing(12)

        pass_lay = QHBoxLayout()
        pass_lay.setSpacing(6)

        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("Contraseña Maestra de MultiTool...")
        self.txt_pass.setFont(QFont(self.font_family, 10))
        self.txt_pass.setFixedHeight(42)
        self.txt_pass.setStyleSheet(f"""
            background-color: {self.colores['bg_secundario']}; 
            color: white; padding: 10px; 
            border-radius: 10px; border: 1px solid rgba(255,255,255,0.08);
        """)
        self.txt_pass.returnPressed.connect(self.desbloquear_boveda)
        pass_lay.addWidget(self.txt_pass, 1)

        self.btn_toggle_eye = QPushButton("👁️")
        self.btn_toggle_eye.setFixedSize(42, 42)
        self.btn_toggle_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_eye.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08);")
        self.btn_toggle_eye.clicked.connect(self._toggle_pass_visibility)
        pass_lay.addWidget(self.btn_toggle_eye)

        c_lay.addLayout(pass_lay)

        self.btn_unlock = QPushButton("🔓 DESBLOQUEAR BÓVEDA")
        self.btn_unlock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_unlock.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_unlock.setFixedHeight(42)
        self.btn_unlock.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']}; 
                color: white; padding: 8px 14px; 
                border-radius: 10px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        self.btn_unlock.clicked.connect(self.desbloquear_boveda)
        c_lay.addWidget(self.btn_unlock)

        lay.addWidget(container, 0, Qt.AlignmentFlag.AlignCenter)

    def _toggle_pass_visibility(self):
        if self.txt_pass.echoMode() == QLineEdit.EchoMode.Password:
            self.txt_pass.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_eye.setText("🙈")
        else:
            self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_eye.setText("👁️")

    # ── Pantalla Principal de Bóveda ──────────────────────────────────
    def setup_vault_page(self):
        lay = QVBoxLayout(self.page_vault)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(14)

        # Header superior con acciones
        header = QHBoxLayout()
        header.setSpacing(8)

        lbl_vault_t = QLabel("🛡️ CONTROL DE BÓVEDA")
        lbl_vault_t.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_vault_t.setStyleSheet("color: white; border: none; background: transparent;")
        header.addWidget(lbl_vault_t)

        header.addStretch()

        header_btns = [
            ("btn_backup", "📦 Respaldos", "white", "1px solid rgba(255,255,255,0.08)", self.abrir_dialogo_respaldo),
            ("btn_audit", "🛡️ Auditar", self.colores['acento'], f"1px solid {self.colores['acento']}55", self.auditar_boveda),
            ("btn_hash", "🔑 Hashes", "white", "1px solid rgba(255,255,255,0.08)", self.abrir_calculadora_hashes),
            ("btn_procesos", "🖥️ Procesos", "white", "1px solid rgba(255,255,255,0.08)", self._mostrar_procesos),
            ("btn_lock", "🔒 Bloquear", "white", "none", self.bloquear_boveda),
        ]
        for attr, text, color, border, callback in header_btns:
            bg = self.colores['error'] if attr == "btn_lock" else self.colores['bg_secundario']
            btn = QPushButton(text)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
            btn.setStyleSheet(f"background: {bg}; color: {color}; padding: 0 12px; border-radius: 6px; border: {border};")
            btn.clicked.connect(callback)
            setattr(self, attr, btn)
            header.addWidget(btn)

        lay.addLayout(header)

        # Splitter responsivo (Panel Izquierdo: Lista | Panel Derecho: Detalle)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self.page_vault)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(8)

        # ── Panel Izquierdo: Lista y Filtros ──
        left_widget = QWidget(self.splitter)
        left_lay = QVBoxLayout(left_widget)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(10)

        # Filtro de categoría y búsqueda
        self.cb_filtro_cat = QComboBox(left_widget)
        self.cb_filtro_cat.addItem("📂 Todas las categorías")
        for cat in CATEGORIAS_DISPONIBLES:
            self.cb_filtro_cat.addItem(cat)
        self.cb_filtro_cat.setFixedHeight(36)
        self.cb_filtro_cat.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_secundario']};
                color: white; border-radius: 8px; padding: 4px 10px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
            }}
        """)
        self.cb_filtro_cat.currentIndexChanged.connect(self.filtrar_secretos)
        left_lay.addWidget(self.cb_filtro_cat)

        self.txt_search = QLineEdit(left_widget)
        self.txt_search.setPlaceholderText("🔍 Buscar servicio, usuario...")
        self.txt_search.setFont(QFont(self.font_family, 9))
        self.txt_search.setFixedHeight(38)
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores['bg_secundario']};
                color: white; padding: 8px 12px;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }}
            QLineEdit:focus {{ border-color: {self.colores['acento']}; }}
        """)
        self.txt_search.textChanged.connect(self.filtrar_secretos)
        left_lay.addWidget(self.txt_search)

        self.btn_add = QPushButton("➕ NUEVO REGISTRO", left_widget)
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_add.setFixedHeight(40)
        self.btn_add.setStyleSheet(f"background-color: {self.colores['exito']}; color: white; padding: 10px; border-radius: 8px; border: none;")
        self.btn_add.clicked.connect(self.nuevo_registro)
        left_lay.addWidget(self.btn_add)

        self.lista = QListWidget(left_widget)
        self.lista.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lista.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.colores['bg_secundario']};
                border-radius: 10px;
                color: white; padding: 6px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
            QListWidget::item {{ padding: 10px; border-radius: 6px; margin-bottom: 4px; }}
            QListWidget::item:selected {{ background-color: {self.colores['acento']}; color: white; }}
            QListWidget::item:hover:!selected {{ background-color: rgba(255,255,255,0.05); }}
        """)
        self.lista.itemSelectionChanged.connect(self.mostrar_detalle)
        left_lay.addWidget(self.lista)

        self.splitter.addWidget(left_widget)

        # ── Panel Derecho: Editor Estructurado ──
        self.card_detail = QFrame(self.splitter)
        self.card_detail.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        d_lay = QVBoxLayout(self.card_detail)
        d_lay.setContentsMargins(18, 18, 18, 18)
        d_lay.setSpacing(10)

        # 0. Categoría
        lbl_cat = QLabel("CATEGORÍA:", self.card_detail)
        lbl_cat.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_cat.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        d_lay.addWidget(lbl_cat)

        self.cb_categoria = QComboBox(self.card_detail)
        for cat in CATEGORIAS_DISPONIBLES:
            self.cb_categoria.addItem(cat)
        self.cb_categoria.setFixedHeight(34)
        self.cb_categoria.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border-radius: 6px; padding: 4px 8px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        d_lay.addWidget(self.cb_categoria)

        # 1. Servicio
        self.row_srv, self.edit_service = self._crear_fila_formulario("SERVICIO:")
        d_lay.addWidget(self.row_srv)

        # 2. Usuario / Correo
        self.row_usr, self.edit_username = self._crear_fila_formulario("USUARIO / CORREO:", has_sub_layout=True)
        h_usr = QHBoxLayout()
        h_usr.setContentsMargins(0, 0, 0, 0)
        h_usr.addWidget(self.edit_username, 1)
        btn_copy_usr = self._crear_boton_icono("📋", "Copiar usuario al portapapeles")
        btn_copy_usr.clicked.connect(lambda: self.copiar_texto(self.edit_username.text(), "Usuario", sensible=False))
        h_usr.addWidget(btn_copy_usr)
        self.row_usr.layout().addLayout(h_usr)
        d_lay.addWidget(self.row_usr)

        # 3. Contraseña
        self.row_pwd, self.edit_password = self._crear_fila_formulario("CONTRASEÑA:", has_sub_layout=True)
        self.edit_password.setEchoMode(QLineEdit.EchoMode.Password)
        h_pwd = QHBoxLayout()
        h_pwd.setContentsMargins(0, 0, 0, 0)
        h_pwd.addWidget(self.edit_password, 1)

        self.btn_show_pwd = self._crear_boton_icono("👁️", "Revelar contraseña")
        self.btn_show_pwd.clicked.connect(self.toggle_reveal_password)
        h_pwd.addWidget(self.btn_show_pwd)

        btn_gen_pwd = self._crear_boton_icono("⚡", "Generar contraseña segura")
        btn_gen_pwd.clicked.connect(self.abrir_generador)
        h_pwd.addWidget(btn_gen_pwd)

        btn_copy_pwd = self._crear_boton_icono("📋", "Copiar contraseña (auto-limpieza en 45s)")
        btn_copy_pwd.clicked.connect(lambda: self.copiar_texto(self.edit_password.text(), "Contraseña", sensible=True))
        h_pwd.addWidget(btn_copy_pwd)

        self.row_pwd.layout().addLayout(h_pwd)
        d_lay.addWidget(self.row_pwd)

        # 4. URL
        self.row_url, self.edit_url = self._crear_fila_formulario("ENLACE / URL:", has_sub_layout=True)
        h_url = QHBoxLayout()
        h_url.setContentsMargins(0, 0, 0, 0)
        h_url.addWidget(self.edit_url, 1)

        btn_open_url = self._crear_boton_icono("🌐", "Abrir enlace en el navegador")
        btn_open_url.clicked.connect(self.abrir_url_navegador)
        h_url.addWidget(btn_open_url)

        btn_copy_url = self._crear_boton_icono("📋", "Copiar URL")
        btn_copy_url.clicked.connect(lambda: self.copiar_texto(self.edit_url.text(), "URL", sensible=False))
        h_url.addWidget(btn_copy_url)

        self.row_url.layout().addLayout(h_url)
        d_lay.addWidget(self.row_url)

        # 5. Notas
        lbl_notes = QLabel("NOTAS / COMENTARIOS:", self.card_detail)
        lbl_notes.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_notes.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        d_lay.addWidget(lbl_notes)

        self.edit_notes = QTextEdit(self.card_detail)
        self.edit_notes.setMinimumHeight(65)
        self.edit_notes.setFont(QFont(self.font_family, 9))
        self.edit_notes.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colores['bg_terciario']};
                color: white; padding: 8px;
                border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);
            }}
            QTextEdit:focus {{ border-color: {self.colores['acento']}; }}
        """)

        h_notes = QHBoxLayout()
        h_notes.addWidget(self.edit_notes, 1)
        btn_copy_notes = self._crear_boton_icono("📋", "Copiar notas")
        btn_copy_notes.clicked.connect(lambda: self.copiar_texto(self.edit_notes.toPlainText(), "Notas", sensible=False))
        h_notes.addWidget(btn_copy_notes)
        d_lay.addLayout(h_notes)

        # Botones de Acción inferior
        h_act = QHBoxLayout()
        self.btn_save_changes = QPushButton("💾 GUARDAR CAMBIOS", self.card_detail)
        self.btn_save_changes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_changes.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_save_changes.setFixedHeight(38)
        self.btn_save_changes.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 0 16px; border-radius: 8px; border: none;")
        self.btn_save_changes.clicked.connect(self.guardar_cambios_secreto)
        h_act.addWidget(self.btn_save_changes)

        self.btn_delete_secret = QPushButton("🗑️ Eliminar Permanente", self.card_detail)
        self.btn_delete_secret.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete_secret.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_delete_secret.setFixedHeight(38)
        self.btn_delete_secret.setStyleSheet(f"background-color: transparent; color: {self.colores['error']}; padding: 0 12px; border: none;")
        self.btn_delete_secret.clicked.connect(self.eliminar_secreto)
        h_act.addWidget(self.btn_delete_secret)

        d_lay.addLayout(h_act)

        # ── Stack Derecho: Página 0 = Vista por defecto, Página 1 = Detalle ──
        self._setup_widget_vacio()
        self.stack_right = QStackedWidget(self.splitter)
        self.stack_right.addWidget(self.widget_vacio) # 0: Vista por defecto
        self.stack_right.addWidget(self.card_detail)  # 1: Detalle y edición
        self.splitter.addWidget(self.stack_right)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)
        lay.addWidget(self.splitter, 1)

        self.set_detail_enabled(False)
        self.stack_right.setCurrentWidget(self.widget_vacio)

    def _setup_widget_vacio(self):
        """Construye la vista por defecto que se muestra cuando no hay ningún secreto seleccionado."""
        self.widget_vacio = QFrame()
        self.widget_vacio.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        v_lay = QVBoxLayout(self.widget_vacio)
        v_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_lay.setContentsMargins(30, 30, 30, 30)
        v_lay.setSpacing(14)

        lbl_shield = QLabel("🛡️")
        lbl_shield.setFont(QFont(self.font_family, 48))
        lbl_shield.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_shield.setStyleSheet("border: none; background: transparent;")
        v_lay.addWidget(lbl_shield)

        self.lbl_vacio_titulo = QLabel("BÓVEDA DE SEGURIDAD")
        self.lbl_vacio_titulo.setFont(QFont(self.font_family, 15, QFont.Weight.Bold))
        self.lbl_vacio_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vacio_titulo.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")
        v_lay.addWidget(self.lbl_vacio_titulo)

        self.lbl_vacio_desc = QLabel(
            "Selecciona un secreto de la lista izquierda para ver o editar sus credenciales cifradas,\n"
            "o utiliza los accesos rápidos para registrar nuevas cuentas o auditar tu seguridad."
        )
        self.lbl_vacio_desc.setFont(QFont(self.font_family, 9))
        self.lbl_vacio_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vacio_desc.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        v_lay.addWidget(self.lbl_vacio_desc)

        # Tarjeta de estado de seguridad
        self.card_status_boveda = QFrame()
        self.card_status_boveda.setStyleSheet(f"""
            background-color: {self.colores['bg_terciario']};
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.06);
        """)
        cs_lay = QHBoxLayout(self.card_status_boveda)
        cs_lay.setContentsMargins(16, 8, 16, 8)

        self.lbl_vacio_stats = QLabel("📊 Secretos Almacenados: 0")
        self.lbl_vacio_stats.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_vacio_stats.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        cs_lay.addWidget(self.lbl_vacio_stats)

        cs_lay.addStretch()

        self.lbl_vacio_cipher = QLabel("🔒 Cifrado: AES-256 Militar")
        self.lbl_vacio_cipher.setFont(QFont(self.font_family, 9))
        self.lbl_vacio_cipher.setStyleSheet(f"color: {self.colores['exito']}; border: none; background: transparent;")
        cs_lay.addWidget(self.lbl_vacio_cipher)
        v_lay.addWidget(self.card_status_boveda)

        # Acciones Rápidas
        row_quick = QHBoxLayout()
        row_quick.setSpacing(8)

        btn_q_nuevo = QPushButton("➕ Nuevo Registro")
        btn_q_nuevo.setFixedHeight(34)
        btn_q_nuevo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_nuevo.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_q_nuevo.setStyleSheet(f"background: {self.colores['exito']}; color: white; border-radius: 6px; padding: 0 12px; border: none;")
        btn_q_nuevo.clicked.connect(self.nuevo_registro)
        row_quick.addWidget(btn_q_nuevo)

        btn_q_gen = QPushButton("⚡ Generar Clave")
        btn_q_gen.setFixedHeight(34)
        btn_q_gen.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_gen.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_q_gen.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px; padding: 0 12px; border: none;")
        btn_q_gen.clicked.connect(self.abrir_generador)
        row_quick.addWidget(btn_q_gen)

        btn_q_audit = QPushButton("🛡️ Auditar")
        btn_q_audit.setFixedHeight(34)
        btn_q_audit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_audit.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_q_audit.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 0 12px; border: 1px solid rgba(255,255,255,0.1);")
        btn_q_audit.clicked.connect(self.auditar_boveda)
        row_quick.addWidget(btn_q_audit)

        btn_q_backup = QPushButton("📦 Respaldos")
        btn_q_backup.setFixedHeight(34)
        btn_q_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_backup.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_q_backup.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 0 12px; border: 1px solid rgba(255,255,255,0.1);")
        btn_q_backup.clicked.connect(self.abrir_dialogo_respaldo)
        row_quick.addWidget(btn_q_backup)

        v_lay.addLayout(row_quick)

        lbl_esc_hint = QLabel("💡 Presiona la tecla Esc para deseleccionar y volver a esta pantalla")
        lbl_esc_hint.setFont(QFont(self.font_family, 8))
        lbl_esc_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_esc_hint.setStyleSheet("color: rgba(255,255,255,0.35); margin-top: 8px; border: none; background: transparent;")
        v_lay.addWidget(lbl_esc_hint)

    def actualizar_vista_vacia(self):
        """Actualiza el resumen numérico de secretos en la vista por defecto."""
        total = len(self.secretos)
        if hasattr(self, "lbl_vacio_stats"):
            self.lbl_vacio_stats.setText(f"📊 Secretos Almacenados: {total}")

    def keyPressEvent(self, event):
        """Permite deseleccionar con Escape y volver a la vista por defecto."""
        if event.key() == Qt.Key.Key_Escape:
            self.lista.clearSelection()
            self.set_detail_enabled(False)
            self.actualizar_vista_vacia()
            if hasattr(self, "stack_right"):
                self.stack_right.setCurrentWidget(self.widget_vacio)
        super().keyPressEvent(event)

    def _crear_fila_formulario(self, label_text: str, has_sub_layout: bool = False):
        row_w = QWidget(self.card_detail)
        row_w.setStyleSheet("background: transparent; border: none;")
        row_lay = QVBoxLayout(row_w)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(4)

        lbl = QLabel(label_text, row_w)
        lbl.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        row_lay.addWidget(lbl)

        edit = QLineEdit(row_w)
        edit.setFont(QFont(self.font_family, 9))
        edit.setFixedHeight(36)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores['bg_terciario']};
                color: white; padding: 8px 10px;
                border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);
            }}
            QLineEdit:focus {{ border-color: {self.colores['acento']}; }}
        """)
        if not has_sub_layout:
            row_lay.addWidget(edit)
        return row_w, edit

    def _crear_boton_icono(self, texto: str, tooltip: str) -> QPushButton:
        btn = QPushButton(texto, self.card_detail)
        btn.setToolTip(tooltip)
        btn.setFixedSize(36, 36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                color: white;
            }}
            QPushButton:hover {{
                border-color: {self.colores['acento']};
            }}
        """)
        return btn

    def set_detail_enabled(self, enabled: bool):
        self.cb_categoria.setEnabled(enabled)
        self.edit_service.setEnabled(enabled)
        self.edit_username.setEnabled(enabled)
        self.edit_password.setEnabled(enabled)
        self.edit_url.setEnabled(enabled)
        self.edit_notes.setEnabled(enabled)
        self.btn_save_changes.setEnabled(enabled)
        self.btn_delete_secret.setEnabled(enabled)

        if not enabled:
            self.cb_categoria.setCurrentIndex(0)
            self.edit_service.clear()
            self.edit_username.clear()
            self.edit_password.clear()
            self.edit_url.clear()
            self.edit_notes.clear()
            self.edit_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_show_pwd.setText("👁️")

    # ── Autenticación y Carga de Datos ────────────────────────────────
    def desbloquear_boveda(self):
        pwd = self.txt_pass.text()
        if not pwd:
            return

        stored_password = ""
        if self.context and hasattr(self.context, "config"):
            stored_password = self.context.config.get("password", "")

        password_correcta = False
        if stored_password and ":" in stored_password:
            try:
                from controlador.auth.validation import AuthValidator
                password_correcta = AuthValidator.verify_password(stored_password, pwd)
            except Exception:
                password_correcta = (stored_password == pwd)
        else:
            password_correcta = (stored_password == pwd) or (not stored_password)

        if password_correcta:
            self.master_pwd = pwd
            self.desbloqueada = True
            self.last_auth_time = QDateTime.currentDateTime()
            self.txt_pass.clear()

            self.cargar_datos()
            self.actualizar_vista_vacia()
            if hasattr(self, "stack_right"):
                self.stack_right.setCurrentWidget(self.widget_vacio)
            self.stack.setCurrentWidget(self.page_vault)
            if self.context and hasattr(self.context, "app") and hasattr(self.context.app, "set_status"):
                self.context.app.set_status("Bóveda desbloqueada.")
        else:
            self._show_message("Acceso Denegado", "La contraseña maestra es incorrecta.", QMessageBox.Icon.Critical)
            self.txt_pass.clear()

    def bloquear_boveda(self):
        self.desbloqueada = False
        self.master_pwd = None
        self.last_auth_time = None
        self.secretos = []
        self.indice_secreto_actual = -1
        self.lista.clear()
        self.set_detail_enabled(False)
        if hasattr(self, "stack_right"):
            self.stack_right.setCurrentWidget(self.widget_vacio)
        self.stack.setCurrentWidget(self.page_locked)
        if self.context and hasattr(self.context, "app") and hasattr(self.context.app, "set_status"):
            self.context.app.set_status("Bóveda bloqueada.")

    def check_auth_timeout(self):
        if self.desbloqueada and self.last_auth_time:
            now = QDateTime.currentDateTime()
            secs = self.last_auth_time.secsTo(now)
            if secs >= self.auth_timeout_minutes * 60:
                self.bloquear_boveda()
                self._show_message("Seguridad", "La sesión de la bóveda ha caducado por inactividad.", QMessageBox.Icon.Warning)

    def cargar_datos(self):
        self.lista.clear()
        self.secretos = []
        self.indice_secreto_actual = -1
        self.set_detail_enabled(False)

        if not self.ruta_vault.exists():
            return

        try:
            with open(self.ruta_vault, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            if isinstance(raw_data, dict) and "ciphertext" in raw_data:
                try:
                    decrypted_str = decrypt_vault(raw_data, self.master_pwd or "")
                    self.secretos = json.loads(decrypted_str)
                except Exception as e:
                    print(f"[!] Error descifrando bóveda AES: {e}")
                    self._show_message("Error de Descifrado", "No se pudo descifrar la bóveda. Verifica la contraseña o integridad del archivo.", QMessageBox.Icon.Critical)
                    self.bloquear_boveda()
                    return
            else:
                # Formato legacy (Vigenere XOR y base64) - Migración automática a AES-256
                self.secretos = []
                for k, v in raw_data.items():
                    try:
                        dec_b64 = base64.b64decode(v.encode('utf-8')).decode('utf-8')
                        secreto_real = encrypt_decrypt_vigenere(dec_b64, self.master_pwd or "")
                    except Exception:
                        secreto_real = v

                    self.secretos.append({
                        "category": "General",
                        "service": k,
                        "username": "",
                        "password": secreto_real,
                        "url": "",
                        "notes": ""
                    })
                self.guardar_datos()

            self.filtrar_secretos()
        except Exception as e:
            print(f"[!] Error leyendo la bóveda: {e}")

    def guardar_datos(self):
        if not self.desbloqueada or self.master_pwd is None:
            return
        try:
            data_str = json.dumps(self.secretos, indent=4)
            enc_dict = encrypt_vault(data_str, self.master_pwd)
            with open(self.ruta_vault, "w", encoding="utf-8") as f:
                json.dump(enc_dict, f, indent=4)
        except Exception as e:
            self._show_message("Error al Guardar", f"No se pudo guardar la base de datos cifrada: {e}", QMessageBox.Icon.Critical)

    # ── Gestión de Secretos ───────────────────────────────────────────
    def filtrar_secretos(self):
        query = self.txt_search.text().lower().strip()
        filtro_cat = self.cb_filtro_cat.currentText()
        self.lista.clear()

        for idx, sec in enumerate(self.secretos):
            service = sec.get("service", "Desconocido")
            username = sec.get("username", "")
            cat = sec.get("category", "General")

            # Filtro por categoría
            if filtro_cat != "📂 Todas las categorías" and cat != filtro_cat:
                continue

            # Filtro por texto
            if not query or query in service.lower() or query in username.lower() or query in cat.lower():
                badge = f"[{cat}] " if cat != "General" else ""
                it = QListWidgetItem(f"{badge}{service}")
                it.setData(Qt.ItemDataRole.UserRole, idx)
                self.lista.addItem(it)

    def mostrar_detalle(self):
        items = self.lista.selectedItems()
        if not items:
            self.set_detail_enabled(False)
            self.indice_secreto_actual = -1
            self.actualizar_vista_vacia()
            if hasattr(self, "stack_right"):
                self.stack_right.setCurrentWidget(self.widget_vacio)
            return

        idx = items[0].data(Qt.ItemDataRole.UserRole)
        self.indice_secreto_actual = idx
        sec = self.secretos[idx]

        self.set_detail_enabled(True)
        if hasattr(self, "stack_right"):
            self.stack_right.setCurrentWidget(self.card_detail)
        cat = sec.get("category", "General")
        cat_idx = self.cb_categoria.findText(cat)
        self.cb_categoria.setCurrentIndex(cat_idx if cat_idx >= 0 else 0)

        self.edit_service.setText(sec.get("service", ""))
        self.edit_username.setText(sec.get("username", ""))
        self.edit_password.setText(sec.get("password", ""))
        self.edit_url.setText(sec.get("url", ""))
        self.edit_notes.setPlainText(sec.get("notes", ""))

        self.edit_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.btn_show_pwd.setText("👁️")
        self.last_auth_time = QDateTime.currentDateTime()

    def toggle_reveal_password(self):
        if self.edit_password.echoMode() == QLineEdit.EchoMode.Password:
            self.edit_password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_show_pwd.setText("🙈")
        else:
            self.edit_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_show_pwd.setText("👁️")
        self.last_auth_time = QDateTime.currentDateTime()

    def nuevo_registro(self):
        nueva = {
            "category": "General",
            "service": "Nuevo Servicio",
            "username": "",
            "password": "",
            "url": "",
            "notes": ""
        }
        self.secretos.append(nueva)
        idx = len(self.secretos) - 1

        self.filtrar_secretos()
        for i in range(self.lista.count()):
            it = self.lista.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == idx:
                self.lista.setCurrentItem(it)
                break

        self.edit_service.setFocus()
        self.edit_service.selectAll()
        if hasattr(self, "stack_right"):
            self.stack_right.setCurrentWidget(self.card_detail)
        self.last_auth_time = QDateTime.currentDateTime()

    def guardar_cambios_secreto(self):
        if self.indice_secreto_actual < 0 or self.indice_secreto_actual >= len(self.secretos):
            return

        service_name = self.edit_service.text().strip()
        if not service_name:
            self._show_message("Validación", "El nombre del servicio no puede estar vacío.", QMessageBox.Icon.Warning)
            return

        self.secretos[self.indice_secreto_actual] = {
            "category": self.cb_categoria.currentText(),
            "service": service_name,
            "username": self.edit_username.text().strip(),
            "password": self.edit_password.text().strip(),
            "url": self.edit_url.text().strip(),
            "notes": self.edit_notes.toPlainText().strip()
        }

        self.guardar_datos()
        sel_idx = self.indice_secreto_actual
        self.filtrar_secretos()

        for i in range(self.lista.count()):
            it = self.lista.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == sel_idx:
                self.lista.setCurrentItem(it)
                break

        self._show_message("Bóveda", "Registro actualizado y guardado correctamente.", QMessageBox.Icon.Information)
        self.last_auth_time = QDateTime.currentDateTime()

    def eliminar_secreto(self):
        if self.indice_secreto_actual < 0 or self.indice_secreto_actual >= len(self.secretos):
            return

        resp = self._show_message(
            "Confirmar Eliminación",
            "¿Estás seguro de que deseas eliminar este secreto permanentemente?\n⚠️ Esta acción no se puede deshacer.",
            QMessageBox.Icon.Question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.secretos.pop(self.indice_secreto_actual)
            self.guardar_datos()
            self.filtrar_secretos()
            self.set_detail_enabled(False)
            self.indice_secreto_actual = -1
            self.actualizar_vista_vacia()
            if hasattr(self, "stack_right"):
                self.stack_right.setCurrentWidget(self.widget_vacio)
            self.last_auth_time = QDateTime.currentDateTime()

    # ── Portapapeles y Enlaces ────────────────────────────────────────
    def copiar_texto(self, texto: str, label: str, sensible: bool = False):
        if texto:
            QApplication.clipboard().setText(texto)
            if sensible:
                self._clipboard_sensitive_text = texto
                self.timer_clipboard.start(45000) # Auto-limpiar en 45 segundos
                msg = f"{label} copiado al portapapeles. Se borrará automáticamente en 45 segundos."
            else:
                msg = f"{label} copiado al portapapeles."

            if self.context and hasattr(self.context, "app") and hasattr(self.context.app, "set_status"):
                self.context.app.set_status(msg)
        self.last_auth_time = QDateTime.currentDateTime()

    def _limpiar_portapapeles_auto(self):
        """Limpia el portapapeles si todavía contiene la clave sensible copiada."""
        if self._clipboard_sensitive_text:
            actual = QApplication.clipboard().text()
            if actual == self._clipboard_sensitive_text:
                QApplication.clipboard().clear()
                if self.context and hasattr(self.context, "app") and hasattr(self.context.app, "set_status"):
                    self.context.app.set_status("Portapapeles limpiado automáticamente por seguridad.")
            self._clipboard_sensitive_text = None

    def abrir_url_navegador(self):
        url = self.edit_url.text().strip()
        if url:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            QDesktopServices.openUrl(QUrl(url))
        self.last_auth_time = QDateTime.currentDateTime()

    def abrir_generador(self):
        diag = PasswordGeneratorDialog(self, self.colores, self.font_family)
        if diag.exec() == QDialog.DialogCode.Accepted:
            self.edit_password.setText(diag.get_password())
            self.edit_password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_show_pwd.setText("🙈")
        self.last_auth_time = QDateTime.currentDateTime()

    def auditar_boveda(self):
        if not self.desbloqueada:
            return
        dlg = VaultAuditDialog(self, self.colores, self.font_family, self.secretos)
        dlg.exec()

    def abrir_calculadora_hashes(self):
        dlg = HashCalculatorDialog(self, self.colores, self.font_family)
        dlg.exec()

    def abrir_dialogo_respaldo(self):
        if not self.desbloqueada or not self.master_pwd:
            return
        dlg = ExportImportDialog(self, self.colores, self.font_family, self.secretos, self.master_pwd)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.imported_secretos:
            # Añadir o reemplazar secretos importados
            resp = self._show_message(
                "Modo de Importación",
                "¿Deseas combinar los registros importados con los actuales (Sí), o reemplazar la bóveda completa (No)?",
                QMessageBox.Icon.Question,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.Yes:
                self.secretos.extend(dlg.imported_secretos)
            else:
                self.secretos = dlg.imported_secretos
            self.guardar_datos()
            self.filtrar_secretos()
            self.actualizar_vista_vacia()

    def _mostrar_procesos(self):
        self.stack.setCurrentWidget(self.page_procesos)
        self.page_procesos.cargar_procesos()

    def _show_message(self, title: str, text: str, icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok):
        msg = QMessageBox(self)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(buttons)
        msg.setStyleSheet(f"""
            QMessageBox {{ background-color: {self.colores['bg_secundario']}; }}
            QLabel {{ color: white; }}
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 6px 15px;
                min-width: 70px;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento']}; }}
        """)
        return msg.exec()

    def showEvent(self, event):
        super().showEvent(event)
        self.check_auth_timeout()

    def actualizar_tema(self, colores: Optional[Dict[str, str]] = None):
        """Actualiza la paleta de colores dinámicamente cuando el usuario cambia el tema."""
        if colores:
            self.colores = colores
        self.setStyleSheet(f"background-color: {self.colores['bg_principal']}; border: none;")
        self.page_procesos.actualizar_tema(self.colores)
        if hasattr(self, "widget_vacio"):
            self.widget_vacio.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.06);")
        if hasattr(self, "card_status_boveda"):
            self.card_status_boveda.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);")
