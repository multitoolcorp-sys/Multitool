import smtplib
import ssl
import datetime
import json
import re
from pathlib import Path
from email.message import EmailMessage
from email.mime.application import MIMEApplication

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QMessageBox, QScrollArea, 
    QTextEdit, QFileDialog, QStackedWidget, QSplitter, QListWidget, 
    QListWidgetItem, QTextBrowser
)
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..utils.email_helpers import EmailListItemWidget, EmailFetchThread



# --- INTERFAZ DE USUARIO PRINCIPAL DEL CLIENTE GMAIL ---
class EmailGUI(QWidget):
    def __init__(self, parent, colores, context):
        super().__init__(parent)
        self.colores = colores
        self.context = context
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.config_path = self.ruta_usuario / "chat" / "gmail.json"
        
        # Estado
        self.adjuntos = []
        self.cached_emails = []
        self.fetch_thread = None
        
        self.inicializar_ui()
        self.cargar_datos_vinculacion()

    def inicializar_ui(self):
        # Stack raíz: Alterna entre Formulario de Vinculación (0) y Bandeja Dual-Pane (1)
        self.root_stack = QStackedWidget(self)
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.addWidget(self.root_stack)

        # =====================================================================
        # PAGE 0: VISTA FORMULARIO DE VINCULACIÓN
        # =====================================================================
        self.page_form = QWidget()
        form_layout = QVBoxLayout(self.page_form)
        form_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea(self.page_form)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        content_width_limit = QWidget()
        content_width_limit.setFixedWidth(600)
        layout = QVBoxLayout(content_width_limit)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(25)
        
        # Header Vinculacion
        header_container = QWidget()
        h_lay = QVBoxLayout(header_container)
        header = QLabel("📨 GMAIL ULTIMATE")
        header.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        header.setStyleSheet("color: white; border: none; background: transparent;")
        h_lay.addWidget(header)
        sep = QFrame(); sep.setFixedHeight(4); sep.setFixedWidth(100)
        sep.setStyleSheet(f"background: {self.colores.get('acento')}; border-radius: 2px;")
        h_lay.addWidget(sep)
        layout.addWidget(header_container)

        # Info Card Links
        info_card = QFrame()
        info_card.setStyleSheet(f"background: rgba(99, 102, 241, 0.08); border-left: 4px solid {self.colores.get('acento')}; border-radius: 8px; padding: 20px;")
        info_lay = QVBoxLayout(info_card)
        inst = QLabel(
            "Configuración rápida:<br>"
            "1. <a href='https://myaccount.google.com/security' style='color:{self.colores.get('acento')}; text-decoration: none;'>Activar Verificación 2 Pasos</a><br>"
            "2. <a href='https://myaccount.google.com/apppasswords' style='color:{self.colores.get('acento')}; text-decoration: none;'>Obtener Contraseña de App</a> (16 caracteres)"
        )
        inst.setOpenExternalLinks(True)
        inst.setWordWrap(True)
        inst.setStyleSheet("color: #E2E2E2; font-size: 11px;")
        info_lay.addWidget(inst)
        layout.addWidget(info_card)

        # Formulario
        self.vista_form = QFrame()
        self.vista_form.setObjectName("VinculacionForm")
        self.vista_form.setStyleSheet(f"""
            QFrame#VinculacionForm {{
                background: {self.colores.get('bg_secundario')}; 
                border: 1px solid {self.colores.get('bg_terciario')};
                border-radius: 12px; 
                padding: 30px;
            }}
        """)
        form_lay = QVBoxLayout(self.vista_form); form_lay.setSpacing(15)
        
        style_form_label = f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 11px; font-weight: bold; border: none; background: transparent;"
        
        lbl_mail = QLabel("CUENTA GMAIL")
        lbl_mail.setStyleSheet(style_form_label)
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("ejemplo@gmail.com")
        self.txt_email.setStyleSheet(self._input_style())
        
        lbl_pass = QLabel("CONTRASEÑA DE APP")
        lbl_pass.setStyleSheet(style_form_label)
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("xxxx xxxx xxxx xxxx")
        self.txt_pass.setStyleSheet(self._input_style())
        self.btn_validar = QPushButton("🚀 VINCULAR CUENTA")
        self.btn_validar.setFixedHeight(36)
        self.btn_validar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validar.setStyleSheet(self._button_style())
        self.btn_validar.clicked.connect(self.enviar_correo_confirmacion)
        
        form_lay.addWidget(lbl_mail)
        form_lay.addWidget(self.txt_email)
        form_lay.addWidget(lbl_pass)
        form_lay.addWidget(self.txt_pass)
        form_lay.addWidget(self.btn_validar)
        
        layout.addWidget(self.vista_form)
        layout.addStretch()
        container_layout.addWidget(content_width_limit)
        scroll.setWidget(container)
        form_layout.addWidget(scroll)
        self.root_stack.addWidget(self.page_form)

        # =====================================================================
        # PAGE 1: VISTA DUAL-PANE (CLIENTE COMPLETO)
        # =====================================================================
        self.page_client = QWidget()
        client_lay = QHBoxLayout(self.page_client)
        client_lay.setContentsMargins(0, 0, 0, 0)
        client_lay.setSpacing(0)
        
        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: rgba(255, 255, 255, 0.05); }")
        
        # 1. Panel Izquierdo: Sidebar de Correos
        self.inbox_sidebar = QFrame()
        self.inbox_sidebar.setMinimumWidth(280)
        self.inbox_sidebar.setMaximumWidth(400)
        self.inbox_sidebar.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-right: 1px solid rgba(255, 255, 255, 0.05);")
        sb_lay = QVBoxLayout(self.inbox_sidebar)
        sb_lay.setContentsMargins(12, 12, 12, 12)
        sb_lay.setSpacing(12)
        
        # Titulo y Sincronizacion
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        lbl_sidebar_title = QLabel("📧 BANDEJA GMAIL")
        lbl_sidebar_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_sidebar_title.setStyleSheet("color: white; border: none; background: transparent;")
        
        self.lbl_acc = QLabel("---")
        self.lbl_acc.setFont(QFont("Segoe UI", 9))
        self.lbl_acc.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#888')}; border: none; background: transparent;")
        
        self.lbl_sync_status = QLabel("Sin sincronizar")
        self.lbl_sync_status.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_sync_status.setStyleSheet("color: #8A94A6; border: none; background: transparent;")
        
        header_lay.addWidget(lbl_sidebar_title)
        header_lay.addWidget(self.lbl_acc)
        header_lay.addWidget(self.lbl_sync_status)
        sb_lay.addLayout(header_lay)
        
        # Botones de Acción de Sidebar
        self.btn_redactar = QPushButton("📝 Redactar Correo")
        self.btn_redactar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_redactar.setFixedHeight(32)
        self.btn_redactar.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11px;
                border: none;
            }}
            QPushButton:hover {{
                background: #3b6fcb;
            }}
        """)
        self.btn_redactar.clicked.connect(self.abrir_compositor_vacio)
        sb_lay.addWidget(self.btn_redactar)
        
        self.btn_refresh = QPushButton("🔄 Sincronizar Inbox")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.05);
                color: white;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.15);
            }}
        """)
        self.btn_refresh.clicked.connect(self.sincronizar_inbox_background)
        sb_lay.addWidget(self.btn_refresh)
        
        # Separador visual
        sep_sb = QFrame()
        sep_sb.setFixedHeight(1)
        sep_sb.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; border: none;")
        sb_lay.addWidget(sep_sb)
        
        # Listado de correos
        self.list_emails = QListWidget()
        self.list_emails.setStyleSheet(f"""
            QListWidget {{ 
                background: transparent; 
                border: none; 
            }}
            QListWidget::item {{
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 8px;
                margin-bottom: 6px;
            }}
            QListWidget::item:hover {{
                background: rgba(255, 255, 255, 0.06);
            }}
            QListWidget::item:selected {{
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid {self.colores['acento']};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.08);
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {self.colores['acento']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self.list_emails.itemSelectionChanged.connect(self.on_email_selected)
        sb_lay.addWidget(self.list_emails)
        
        # Botón desvincular
        self.btn_desvincular = QPushButton("🚪 Desvincular Cuenta")
        self.btn_desvincular.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_desvincular.setFixedHeight(32)
        self.btn_desvincular.setStyleSheet(f"""
            QPushButton {{
                color: {self.colores.get('error', '#F44336')}; 
                background: transparent; 
                border: 1px solid {self.colores.get('error', '#F44336')}; 
                border-radius: 6px; 
                font-size: 11px; 
                font-weight: bold;
            }}
            QPushButton:hover {{ 
                background: rgba(244, 67, 54, 0.08); 
            }}
        """)
        self.btn_desvincular.clicked.connect(self.reset_form)
        sb_lay.addWidget(self.btn_desvincular)
        
        splitter.addWidget(self.inbox_sidebar)
        
        # 2. Panel Derecho: Stack de Contenido (Dashboard, Redactor, Lector)
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(f"background: {self.colores['bg_principal']};")
        
        # ==========================================
        # PAGE DUAL-PANE A: Vista Dashboard (Welcome)
        # ==========================================
        self.vista_dashboard = QWidget()
        dash_lay = QVBoxLayout(self.vista_dashboard)
        dash_lay.setContentsMargins(40, 40, 40, 40)
        dash_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_logo = QLabel("📨")
        lbl_logo.setFont(QFont("Segoe UI", 48))
        lbl_logo.setStyleSheet("border: none; background: transparent;")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_dash_title = QLabel("Gmail Client Ultimate")
        lbl_dash_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_dash_title.setStyleSheet("color: white; border: none; background: transparent;")
        lbl_dash_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_dash_desc = QLabel("Selecciona un correo electrónico de la bandeja de entrada para leer su contenido o pulsa 'Redactar Correo' para escribir uno nuevo.")
        lbl_dash_desc.setWordWrap(True)
        lbl_dash_desc.setFont(QFont("Segoe UI", 10))
        lbl_dash_desc.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#888')}; border: none; background: transparent; line-height: 1.6;")
        lbl_dash_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_dash_desc.setFixedWidth(400)
        
        dash_lay.addStretch()
        dash_lay.addWidget(lbl_logo)
        dash_lay.addSpacing(10)
        dash_lay.addWidget(lbl_dash_title)
        dash_lay.addSpacing(10)
        dash_lay.addWidget(lbl_dash_desc)
        dash_lay.addStretch()
        self.content_stack.addWidget(self.vista_dashboard)
        
        # ==========================================
        # PAGE DUAL-PANE B: Vista Compositor (Send)
        # ==========================================
        self.vista_compositor = QWidget()
        comp_main_lay = QVBoxLayout(self.vista_compositor)
        comp_main_lay.setContentsMargins(25, 25, 25, 25)
        comp_main_lay.setSpacing(15)
        
        lbl_comp_title = QLabel("📝 REDACTAR MENSAJE")
        lbl_comp_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_comp_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        comp_main_lay.addWidget(lbl_comp_title)
        
        # Formulario Compositor
        self.composer_card = QFrame()
        self.composer_card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border: 1px solid {self.colores['bg_terciario']}; border-radius: 10px;")
        comp_lay = QVBoxLayout(self.composer_card)
        comp_lay.setContentsMargins(20, 20, 20, 20)
        comp_lay.setSpacing(15)
        
        style_label = f"color: {self.colores.get('fg_principal', '#FFFFFF')}; font-size: 11px; font-weight: bold; border: none; background: transparent;"
        style_label_header = f"color: {self.colores.get('acento', '#6366F1')}; font-size: 11px; font-weight: bold; border: none; background: transparent;"
        
        # De:
        de_box = QHBoxLayout()
        lbl_de = QLabel("DE:")
        lbl_de.setFixedWidth(50)
        lbl_de.setStyleSheet(style_label_header)
        self.lbl_acc_composer = QLabel("---")
        self.lbl_acc_composer.setStyleSheet(f"color: {self.colores.get('exito', '#4CAF50')}; font-weight: bold; font-size: 12px; border: none; background: transparent;")
        de_box.addWidget(lbl_de)
        de_box.addWidget(self.lbl_acc_composer)
        de_box.addStretch()
        comp_lay.addLayout(de_box)

        # Para:
        para_box = QHBoxLayout()
        lbl_para = QLabel("PARA:")
        lbl_para.setFixedWidth(50)
        lbl_para.setStyleSheet(style_label)
        self.txt_to = QLineEdit()
        self.txt_to.setPlaceholderText("correo@destinatario.com")
        self.txt_to.setStyleSheet(self._input_style())
        para_box.addWidget(lbl_para)
        para_box.addWidget(self.txt_to)
        comp_lay.addLayout(para_box)

        # Asunto:
        asunto_box = QHBoxLayout()
        lbl_as = QLabel("ASUNTO:")
        lbl_as.setFixedWidth(50)
        lbl_as.setStyleSheet(style_label)
        self.txt_sub = QLineEdit()
        self.txt_sub.setPlaceholderText("Asunto del correo...")
        self.txt_sub.setStyleSheet(self._input_style())
        asunto_box.addWidget(lbl_as)
        asunto_box.addWidget(self.txt_sub)
        comp_lay.addLayout(asunto_box)

        # Mensaje:
        lbl_msg = QLabel("MENSAJE")
        lbl_msg.setStyleSheet(style_label)
        comp_lay.addWidget(lbl_msg)
        
        self.txt_msg = QTextEdit()
        self.txt_msg.setPlaceholderText("Escribe el cuerpo del mensaje aquí...")
        self.txt_msg.setStyleSheet(f"""
            QTextEdit {{ 
                background: {self.colores['bg_terciario']}; 
                color: white; 
                border-radius: 8px; 
                padding: 12px; 
                font-family: 'Segoe UI', Arial;
                font-size: 13px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            QTextEdit:focus {{ border: 1px solid {self.colores['acento']}; }}
        """)
        comp_lay.addWidget(self.txt_msg)
        
        # Barra Inferior (Adjuntos y Enviar)
        bottom_tools = QHBoxLayout()
        
        self.btn_attach = QPushButton("📎 Adjuntar Archivo")
        self.btn_attach.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_attach.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.05); 
                color: #FFFFFF; 
                padding: 8px 15px; 
                border-radius: 6px; 
                font-size: 11px;
                border: 1px solid {self.colores.get('bg_terciario', '#555')};
            }}
            QPushButton:hover {{ background: rgba(255, 255, 255, 0.12); }}
        """)
        self.btn_attach.clicked.connect(self.adjuntar_archivo)
        
        self.lbl_adjuntos = QLabel("Sin archivos adjuntos")
        self.lbl_adjuntos.setStyleSheet(f"font-size: 11px; color: {self.colores.get('fg_secundario', '#888')}; margin-left: 10px; border: none; background: transparent;")
        
        bottom_tools.addWidget(self.btn_attach)
        bottom_tools.addWidget(self.lbl_adjuntos)
        bottom_tools.addStretch()
        
        self.btn_send = QPushButton("🚀 ENVIAR CORREO")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setFixedWidth(160)
        self.btn_send.setFixedHeight(38)
        self.btn_send.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: #FFFFFF; font-weight: bold; border-radius: 8px; border: none; font-size: 12px;")
        self.btn_send.clicked.connect(self.enviar_mensaje_real)
        bottom_tools.addWidget(self.btn_send)
        
        comp_lay.addLayout(bottom_tools)
        comp_main_lay.addWidget(self.composer_card)
        self.content_stack.addWidget(self.vista_compositor)
        
        # ==========================================
        # PAGE DUAL-PANE C: Vista Lector (Read)
        # ==========================================
        self.vista_lector = QWidget()
        lector_lay = QVBoxLayout(self.vista_lector)
        lector_lay.setContentsMargins(25, 25, 25, 25)
        lector_lay.setSpacing(15)
        
        # Barra superior lector: Responder y Cerrar
        lbl_lector_header = QHBoxLayout()
        self.btn_volver = QPushButton("⬅️ Bandeja")
        self.btn_volver.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_volver.setFixedSize(90, 30)
        self.btn_volver.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.05);
                color: white;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.15);
            }}
        """)
        self.btn_volver.clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
        lbl_lector_header.addWidget(self.btn_volver)
        lbl_lector_header.addStretch()
        
        self.btn_responder = QPushButton("↩️ Responder")
        self.btn_responder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_responder.setFixedSize(110, 30)
        self.btn_responder.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                border: none;
            }}
            QPushButton:hover {{
                background: #3b6fcb;
            }}
        """)
        self.btn_responder.clicked.connect(self.responder_correo_actual)
        lbl_lector_header.addWidget(self.btn_responder)
        lector_lay.addLayout(lbl_lector_header)
        
        # Tarjeta de Detalles del Correo
        self.lector_card = QFrame()
        self.lector_card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border: 1px solid {self.colores['bg_terciario']}; border-radius: 10px;")
        card_lay = QVBoxLayout(self.lector_card)
        card_lay.setContentsMargins(20, 20, 20, 20)
        card_lay.setSpacing(12)
        
        # Campos de Cabecera
        self.lbl_reader_sub = QLabel("(Sin Asunto)")
        self.lbl_reader_sub.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_reader_sub.setStyleSheet("color: white; border: none; background: transparent;")
        self.lbl_reader_sub.setWordWrap(True)
        card_lay.addWidget(self.lbl_reader_sub)
        
        # Fila Remitente
        row_sender = QHBoxLayout()
        lbl_from_tag = QLabel("De:")
        lbl_from_tag.setFixedWidth(30)
        lbl_from_tag.setStyleSheet(style_label_header)
        self.lbl_reader_from = QLabel("---")
        self.lbl_reader_from.setStyleSheet("color: #E2E8F0; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        row_sender.addWidget(lbl_from_tag)
        row_sender.addWidget(self.lbl_reader_from)
        row_sender.addStretch()
        card_lay.addLayout(row_sender)
        
        # Fila Fecha
        row_date = QHBoxLayout()
        lbl_date_tag = QLabel("Fecha:")
        lbl_date_tag.setFixedWidth(40)
        lbl_date_tag.setStyleSheet(style_label)
        self.lbl_reader_date = QLabel("---")
        self.lbl_reader_date.setStyleSheet("color: #8A94A6; font-size: 11px; border: none; background: transparent;")
        row_date.addWidget(lbl_date_tag)
        row_date.addWidget(self.lbl_reader_date)
        row_date.addStretch()
        card_lay.addLayout(row_date)
        
        # Adjuntos
        self.lbl_reader_atts = QLabel("")
        self.lbl_reader_atts.setWordWrap(True)
        self.lbl_reader_atts.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_reader_atts.setStyleSheet(f"color: {self.colores.get('exito', '#4CAF50')}; border: none; background: transparent;")
        self.lbl_reader_atts.hide()
        card_lay.addWidget(self.lbl_reader_atts)
        
        # Separador visual
        sep_lector = QFrame()
        sep_lector.setFixedHeight(1)
        sep_lector.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; border: none;")
        card_lay.addWidget(sep_lector)
        
        # Visor del cuerpo
        self.reader_browser = QTextBrowser()
        self.reader_browser.setStyleSheet(f"""
            QTextBrowser {{ 
                background: {self.colores['bg_terciario']}; 
                color: #E2E8F0; 
                border-radius: 8px; 
                padding: 12px; 
                font-family: 'Segoe UI', Arial;
                font-size: 13px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.08);
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {self.colores['acento']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self.reader_browser.setOpenExternalLinks(True)
        card_lay.addWidget(self.reader_browser, 1)
        
        lector_lay.addWidget(self.lector_card, 1)
        self.content_stack.addWidget(self.vista_lector)
        
        # Agregar stack de contenido al splitter
        splitter.addWidget(self.content_stack)
        
        # Proporción splitter: 280px sidebar, resto expandible
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        client_lay.addWidget(splitter)
        self.root_stack.addWidget(self.page_client)

    # --- ACCIONES Y NAVEGACIÓN DUAL-PANE ---
    def abrir_compositor_vacio(self):
        self.list_emails.clearSelection()
        self.txt_to.clear()
        self.txt_sub.clear()
        self.txt_msg.clear()
        self.adjuntos = []
        self.lbl_adjuntos.setText("Sin archivos adjuntos")
        self.content_stack.setCurrentIndex(1)
        self.txt_to.setFocus()

    def responder_correo_actual(self):
        # Obtener correo seleccionado actualmente
        row = self.list_emails.currentRow()
        if row < 0 or row >= len(self.cached_emails):
            return
            
        mail_data = self.cached_emails[row]
        
        # Extraer email limpio
        sender = mail_data["sender"]
        match = re.search(r'<([^>]+)>', sender)
        recipient = match.group(1) if match else sender.strip()
        
        self.txt_to.setText(recipient)
        self.txt_sub.setText(f"Re: {mail_data['subject']}")
        self.adjuntos = []
        self.lbl_adjuntos.setText("Sin archivos adjuntos")
        
        # Formatear cuerpo original como cita
        quote_header = f"\n\n\n--- El {mail_data['date']}, {sender} escribió: ---\n"
        quote_body = "\n".join([f"> {line}" for line in mail_data["preview"].split("\n")])
        self.txt_msg.setPlainText(quote_header + quote_body)
        
        self.content_stack.setCurrentIndex(1)
        self.txt_msg.setFocus()

    def on_email_selected(self):
        row = self.list_emails.currentRow()
        if row < 0 or row >= len(self.cached_emails):
            return
            
        mail_data = self.cached_emails[row]
        self.lbl_reader_sub.setText(mail_data["subject"])
        self.lbl_reader_from.setText(mail_data["sender"])
        self.lbl_reader_date.setText(mail_data["date"])
        
        # Cuerpo
        body_content = mail_data["body"]
        if "<html>" in body_content.lower() or "<div>" in body_content.lower() or "<p>" in body_content.lower() or "<br>" in body_content.lower():
            self.reader_browser.setHtml(body_content)
        else:
            # Envolver texto plano para mantener saltos de linea y legibilidad
            escaped_body = body_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_wrapped = f"<html><body style='font-family: Segoe UI, sans-serif; color: #E2E8F0; line-height: 1.6; font-size: 13px;'><pre style='font-family: inherit; white-space: pre-wrap; margin:0;'>{escaped_body}</pre></body></html>"
            self.reader_browser.setHtml(html_wrapped)
            
        # Adjuntos
        atts = mail_data.get("attachments", [])
        if atts:
            self.lbl_reader_atts.setText(f"📎 Adjuntos: {', '.join(atts)}")
            self.lbl_reader_atts.show()
        else:
            self.lbl_reader_atts.hide()
            
        self.content_stack.setCurrentIndex(2)

    # --- LOGICA DE SINCRONIZACIÓN Y CACHÉ (IMAP) ---
    def cargar_cache_inbox(self):
        cache_file = self.ruta_usuario / "chat" / "gmail_inbox_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.cached_emails = json.load(f)
                self.actualizar_ui_lista_correos(self.cached_emails)
                now_str = datetime.datetime.fromtimestamp(cache_file.stat().st_mtime).strftime("%d/%m %H:%M")
                self.lbl_sync_status.setText(f"Cargado (caché: {now_str})")
            except:
                self.cached_emails = []
        else:
            self.cached_emails = []

    def actualizar_ui_lista_correos(self, emails_list):
        self.list_emails.clear()
        for mail in emails_list:
            subject = mail.get("subject", "(Sin Asunto)")
            sender = mail.get("sender", "Desconocido")
            date = mail.get("date", "")
            preview = mail.get("preview", "")
            
            item = QListWidgetItem()
            item.setSizeHint(QSize(240, 78))
            self.list_emails.addItem(item)
            
            widget = EmailListItemWidget(subject, sender, date, preview, self.colores)
            self.list_emails.setItemWidget(item, widget)

    def sincronizar_inbox_background(self):
        email = self.txt_email.text().strip()
        password = self.txt_pass.text().strip()
        if not email or not password:
            return
            
        self.btn_refresh.setEnabled(False)
        self.lbl_sync_status.setText("Sincronizando...")
        
        self.fetch_thread = EmailFetchThread(email, password)
        self.fetch_thread.emails_fetched.connect(self.on_emails_fetched)
        self.fetch_thread.error_occurred.connect(self.on_fetch_error)
        self.fetch_thread.start()

    def on_emails_fetched(self, emails_list):
        self.cached_emails = emails_list
        self.actualizar_ui_lista_correos(emails_list)
        
        # Guardar en caché local
        try:
            cache_file = self.ruta_usuario / "chat" / "gmail_inbox_cache.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(emails_list, f, indent=4)
        except: pass
        
        now = datetime.datetime.now().strftime("%H:%M")
        self.lbl_sync_status.setText(f"Sincronizado a las {now}")
        self.btn_refresh.setEnabled(True)

    def on_fetch_error(self, err_msg):
        self.lbl_sync_status.setText("Error al sincronizar")
        self.btn_refresh.setEnabled(True)
        print(f"[IMAP FETCH ERROR] {err_msg}")

    # --- LÓGICA EXISTENTE DE ENVÍO Y VINCULACIÓN (PRESERVADA) ---
    def adjuntar_archivo(self):
        file, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo")
        if file:
            self.adjuntos.append(Path(file))
            self.lbl_adjuntos.setText(f"{len(self.adjuntos)} archivos adjuntos")

    def guardar_datos_vinculacion(self, email, password):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump({"email": email, "pass": password}, f)
        except: pass

    def cargar_datos_vinculacion(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.txt_email.setText(data['email'])
                    self.txt_pass.setText(data['pass'])
                    self.lbl_acc.setText(data['email'])
                    self.lbl_acc_composer.setText(data['email'])
                    
                    # Cargar los correos cacheados primero para instant-load
                    self.cargar_cache_inbox()
                    
                    # Conmutar al panel dual-pane
                    self.root_stack.setCurrentIndex(1)
                    
                    # Sincronizar automáticamente en segundo plano
                    self.sincronizar_inbox_background()
            except: pass

    def reset_form(self):
        if self.config_path.exists(): 
            self.config_path.unlink()
        
        # Eliminar también la caché de correos
        cache_file = self.ruta_usuario / "chat" / "gmail_inbox_cache.json"
        if cache_file.exists():
            try: cache_file.unlink()
            except: pass
            
        self.root_stack.setCurrentIndex(0)
        self.txt_pass.clear()
        self.txt_msg.clear()
        self.adjuntos = []
        self.cached_emails = []
        self.list_emails.clear()
        self.lbl_sync_status.setText("Sin sincronizar")
        self.content_stack.setCurrentIndex(0)

    def enviar_mensaje_real(self):
        to = self.txt_to.text().strip(); sub = self.txt_sub.text().strip(); body = self.txt_msg.toPlainText()
        if not to or not body: return
        self.btn_send.setEnabled(False); self.btn_send.setText("ENVIANDO...")
        import threading
        t = threading.Thread(target=self._worker_enviar_real, args=(to, sub, body, list(self.adjuntos)))
        t.start()

    def _worker_enviar_real(self, to, sub, body, files):
        try:
            rem = self.txt_email.text(); pwd = self.txt_pass.text().replace(" ", "")
            msg = EmailMessage()
            msg.set_content(body); msg['Subject'] = sub or "(Sin Asunto)"; msg['From'] = rem; msg['To'] = to
            
            for f_path in files:
                with open(f_path, 'rb') as f:
                    msg.add_attachment(f.read(), maintype='application', subtype='octet-stream', filename=f_path.name)

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
                s.login(rem, pwd); s.send_message(msg)
            self._finalizar_envio_real(True, "¡Enviado!")
        except Exception as e: self._finalizar_envio_real(False, str(e))

    def _finalizar_envio_real(self, ex, msj):
        QMetaObject.invokeMethod(self, "_res_envio", Qt.ConnectionType.QueuedConnection, Q_ARG(bool, ex), Q_ARG(str, msj))

    @pyqtSlot(bool, str)
    def _res_envio(self, ex, msj):
        self.btn_send.setEnabled(True); self.btn_send.setText("📧 ENVIAR CORREO")
        if ex: 
            QMessageBox.information(self, "Éxito", msj)
            self.txt_to.clear(); self.txt_sub.clear(); self.txt_msg.clear(); self.adjuntos = []; self.lbl_adjuntos.setText("Sin adjuntos")
            self.content_stack.setCurrentIndex(0)
        else: QMessageBox.critical(self, "Error", msj)

    def _button_style(self):
        return f"background: {self.colores['acento']}; color: white; font-weight: bold; border-radius: 8px; border: none;"

    def _input_style(self):
        return f"background: {self.colores['bg_terciario']}; color: white; padding: 10px; border-radius: 6px; border: none; font-size: 13px;"

    def enviar_correo_confirmacion(self):
        import threading
        self.btn_validar.setEnabled(False)
        threading.Thread(target=self._worker_env, args=(self.txt_email.text(), self.txt_pass.text())).start()

    def _worker_env(self, rem, pwd):
        try:
            p = pwd.replace(" ", "")
            msg = EmailMessage(); msg.set_content("Vinculación exitosa."); msg['Subject'] = "Multitool OK"; msg['From'] = rem; msg['To'] = rem
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
                s.login(rem, p); s.send_message(msg)
            self.guardar_datos_vinculacion(rem, pwd)
            self._fin_vin(True, "Vinculado")
        except Exception as e: self._fin_vin(False, str(e))

    def _fin_vin(self, ex, msj):
        QMetaObject.invokeMethod(self, "_res_vin", Qt.ConnectionType.QueuedConnection, Q_ARG(bool, ex), Q_ARG(str, msj))

    @pyqtSlot(bool, str)
    def _res_vin(self, ex, msj):
        self.btn_validar.setEnabled(True)
        if ex: 
            self.lbl_acc.setText(self.txt_email.text())
            self.lbl_acc_composer.setText(self.txt_email.text())
            
            # Inicializar cache
            self.cargar_cache_inbox()
            
            # Sincronizar en background
            self.sincronizar_inbox_background()
            
            # Cambiar a la bandeja
            self.root_stack.setCurrentIndex(1)
            QMessageBox.information(self, "Gmail", msj)
        else: 
            QMessageBox.critical(self, "Error de Conexión", msj)
