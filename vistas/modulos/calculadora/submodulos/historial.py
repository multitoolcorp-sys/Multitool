import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QPushButton, QMessageBox, QApplication, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class TabCalculadoraHistorial(QWidget):
    """Módulo de consulta y gestión de registros de cálculos realizados"""
    def __init__(self, parent, colores, obtener_historial_callback, limpiar_historial_callback):
        super().__init__(parent)
        self.colores = colores
        self.obtener_historial = obtener_historial_callback
        self.limpiar_historial_callback = limpiar_historial_callback
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.inicializar_ui()

    def inicializar_ui(self):
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(12, 12, 12, 12)
        self.layout_principal.setSpacing(10)
        
        # --- ENCABEZADO ---
        header_card = QFrame()
        header_card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        header_lay = QVBoxLayout(header_card)
        header_lay.setContentsMargins(12, 8, 12, 8)
        
        lbl_titulo = QLabel("RECOPILACIÓN DE CÁLCULOS")
        lbl_titulo.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet(f"color: {self.colores['acento']}; ")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_lay.addWidget(lbl_titulo)
        
        self.layout_principal.addWidget(header_card)
        
        # --- LISTA DE REGISTROS PREMIUM ---
        self.lista_historial = QListWidget()
        self.lista_historial.setFont(QFont(self.mono_font, 10))
        self.lista_historial.setSpacing(4)
        self.lista_historial.setWordWrap(True)
        self.lista_historial.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.lista_historial.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                color: {self.colores['fg_principal']};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                background: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
                border-radius: 8px;
                padding: 8px 12px;
                margin-bottom: 3px;
                border: 1px solid rgba(255, 255, 255, 0.03);
            }}
            QListWidget::item:hover {{
                background-color: {self.colores['bg_terciario']};
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QListWidget::item:selected {{
                background-color: {self.colores['acento']}22;
                color: white;
                border: 1px solid {self.colores['acento']}44;
            }}
        """)
        self.layout_principal.addWidget(self.lista_historial)
        
        # --- BOTONES DE GESTIÓN ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_limpiar = QPushButton("🚮 LIMPIAR REGISTROS")
        btn_limpiar.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_limpiar.setMinimumHeight(34)
        btn_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_limpiar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['error']}22;
                color: {self.colores['error']};
                border: 1px solid {self.colores['error']}44;
                border-radius: 8px;
                padding: 0 15px;
            }}
            QPushButton:hover {{ 
                background-color: {self.colores['error']}; 
                color: white;
            }}
        """)
        btn_limpiar.clicked.connect(self.limpiar_historial_callback)
        btn_layout.addWidget(btn_limpiar, 1)
        
        btn_actualizar = QPushButton("🔄 ACTUALIZAR")
        btn_actualizar.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_actualizar.setMinimumHeight(34)
        btn_actualizar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_actualizar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.05);
                border-radius: 8px; padding: 0 15px;
            }}
            QPushButton:hover {{ background-color: {self.colores['bg_secundario']}; border-color: {self.colores['acento']}; }}
        """)
        btn_actualizar.clicked.connect(self.actualizar_lista)
        btn_layout.addWidget(btn_actualizar, 1)
        
        self.layout_principal.addLayout(btn_layout)
        
        # Carga inicial
        self.actualizar_lista()

    def actualizar_lista(self):
        self.lista_historial.clear()
        lista = self.obtener_historial()
        if not lista:
            item = QLabel("Aún no hay cálculos registrados en esta sesión.")
            item.setFont(QFont(self.font_family, 10))
            item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setStyleSheet(f"color: {self.colores['fg_secundario']}; padding: 30px;")
            self.lista_historial.addItem("") # Dummy
            self.lista_historial.setItemWidget(self.lista_historial.item(0), item)
        else:
            self.lista_historial.addItems(lista)

