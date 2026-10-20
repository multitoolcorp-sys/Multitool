import platform
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from .cards import UpcomingCard

class CalendarSidebar(QFrame):
    """Barra lateral para gestión de eventos próximos y acciones rápidas"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.inicializar_ui()

    def inicializar_ui(self):
        self.setFixedWidth(240)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border-right: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(12)
        
        # Título de Sección
        lbl_prox = QLabel("EVENTOS PRÓXIMOS")
        lbl_prox.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_prox.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        lbl_prox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(lbl_prox)
        
        # Botón Añadir con Estilo Premium
        self.btn_add = QPushButton("+ CREAR RECORDATORIO")
        self.btn_add.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setMinimumHeight(36)
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white; border-radius: 8px; border: none;
                padding: 6px 12px; margin-top: 2px;
            }}
            QPushButton:hover {{ 
                background-color: {self.colores['acento_hover']};
            }}
        """)
        self.btn_add.clicked.connect(lambda: self.callbacks["añadir_recordatorio"]())
        layout.addWidget(self.btn_add)

        btn_exportar = QPushButton("📄 Exportar Agenda")
        btn_exportar.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_exportar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exportar.setMinimumHeight(30)
        btn_exportar.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {self.colores['fg_secundario']};
                border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 4px 8px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.05); color: white; }}
        """)
        btn_exportar.clicked.connect(lambda: self.callbacks["exportar"]())
        layout.addWidget(btn_exportar)
        
        layout.addSpacing(5)
        
        # Área de Scroll para eventos
        scroll_proximos = QScrollArea()
        scroll_proximos.setWidgetResizable(True)
        scroll_proximos.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.container_proximos = QWidget()
        self.container_proximos.setStyleSheet("background: transparent;")
        self.layout_proximos = QVBoxLayout(self.container_proximos)
        self.layout_proximos.setContentsMargins(0, 4, 0, 4)
        self.layout_proximos.setSpacing(8)
        self.layout_proximos.addStretch()
        
        scroll_proximos.setWidget(self.container_proximos)
        layout.addWidget(scroll_proximos)

    def actualizar_proximos(self, proximos):
        # Limpiar anteriores (excepto el stretch final)
        while self.layout_proximos.count() > 1:
            item = self.layout_proximos.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not proximos:
            lbl_vacio = QLabel("No hay eventos\nen tu agenda.")
            lbl_vacio.setFont(QFont(self.font_family, 9))
            lbl_vacio.setStyleSheet(f"color: {self.colores['fg_secundario']}; padding: 20px;")
            lbl_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_vacio.setWordWrap(True)
            self.layout_proximos.insertWidget(0, lbl_vacio)
            return
            
        for rec in proximos:
            card = UpcomingCard(
                rec, 
                self.colores, 
                self.callbacks["get_cat_color"], 
                self.callbacks["ver_detalle"]
            )
            self.layout_proximos.insertWidget(self.layout_proximos.count()-1, card)
