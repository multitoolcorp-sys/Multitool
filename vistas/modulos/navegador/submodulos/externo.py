from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QLineEdit, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class TabNavegadorExterno(QWidget):
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Título y Botón Aclaraciones
        h_tit = QHBoxLayout()
        lbl_tit = QLabel("BROWSER")
        font_tit = QFont("Inter", 16, QFont.Weight.Bold)
        font_tit.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        lbl_tit.setFont(font_tit)
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']};")
        h_tit.addWidget(lbl_tit)
        
        h_tit.addStretch()
        
        btn_aclara = QPushButton("?")
        btn_aclara.setFixedSize(32, 32)
        btn_aclara.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_aclara.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']}; 
                color: {self.colores['fg_secundario']}; 
                font-weight: bold; 
                border-radius: 16px;
            }}
            QPushButton:hover {{ background: {self.colores['acento']}; color: white; }}
        """)
        btn_aclara.clicked.connect(self.callbacks["mostrar_aclaraciones"])
        h_tit.addWidget(btn_aclara)
        layout.addLayout(h_tit)
        
        # Barra de navegación externa
        nav_f = QFrame()
        nav_f.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']}; 
                border-radius: 12px; 
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        n_layout = QHBoxLayout(nav_f)
        n_layout.setContentsMargins(15, 10, 15, 10)
        
        self.txt_url = QLineEdit("https://www.google.com")
        self.txt_url.setFont(QFont("Inter", 9))
        self.txt_url.setFixedHeight(32)
        self.txt_url.setStyleSheet(f"background: {self.colores['bg_terciario']}; border: none; border-radius: 8px; padding: 4px 10px; color: white;")
        
        btn_home = QPushButton("🏠")
        btn_home.setFixedSize(32, 32)
        btn_home.setStyleSheet(f"background: transparent; border-radius: 16px;")
        btn_home.clicked.connect(lambda: self.callbacks["navegador_comando"]("home"))
        n_layout.addWidget(btn_home)
        
        n_layout.addWidget(self.txt_url, 1)
        
        btn_go_edge = QPushButton("⚡ EDGE (WEBVIEW2)")
        btn_go_edge.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        btn_go_edge.setFixedHeight(32)
        btn_go_edge.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_go_edge.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']}; 
                color: white; 
                padding: 0 14px; 
                border-radius: 8px;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_go_edge.clicked.connect(lambda: self.callbacks["navegador_comando"]("go_edge"))
        n_layout.addWidget(btn_go_edge)

        btn_go = QPushButton("🌐 NAVEGADOR SISTEMA")
        btn_go.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        btn_go.setFixedHeight(32)
        btn_go.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_go.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']}; 
                color: {self.colores['fg_principal']}; 
                padding: 0 12px; 
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.15); }}
        """)
        btn_go.clicked.connect(lambda: self.callbacks["navegador_comando"]("go"))
        n_layout.addWidget(btn_go)
        
        btn_save = QPushButton("💾")
        btn_save.setFixedSize(32, 32)
        btn_save.setStyleSheet(f"background: transparent;")
        btn_save.clicked.connect(self.callbacks["guardar_link"])
        n_layout.addWidget(btn_save)
        
        layout.addWidget(nav_f)
        
        # Historial Sección
        hist_f = QFrame()
        hist_f.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']}; 
                border-radius: 12px; 
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        h_layout = QVBoxLayout(hist_f)
        h_layout.setContentsMargins(20, 20, 20, 20)
        
        h_tit_lay = QHBoxLayout()
        lbl_h = QLabel("HISTORIAL")
        lbl_h.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        h_tit_lay.addWidget(lbl_h)
        
        self.txt_hist_search = QLineEdit()
        self.txt_hist_search.setPlaceholderText("Filtrar historial...")
        self.txt_hist_search.setFont(QFont("Inter", 9))
        self.txt_hist_search.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 6px; padding: 8px; margin: 0 10px;")
        self.txt_hist_search.textChanged.connect(self.callbacks["filtrar_historial"])
        h_tit_lay.addWidget(self.txt_hist_search, 1)
        
        btn_limpiar = QPushButton("Limpiar")
        btn_limpiar.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        btn_limpiar.setStyleSheet(f"background: {self.colores['error']}; color: white; padding: 8px 15px; border-radius: 6px;")
        btn_limpiar.clicked.connect(self.callbacks["limpiar_historial"])
        h_tit_lay.addWidget(btn_limpiar)
        h_layout.addLayout(h_tit_lay)
        
        self.tree_historial = QTreeWidget()
        self.tree_historial.setHeaderHidden(True)
        self.tree_historial.setFont(QFont("Consolas", 10))
        self.tree_historial.setStyleSheet(f"""
            QTreeWidget {{
                background: {self.colores['bg_terciario']}; 
                border: none; 
                border-radius: 10px; 
                color: {self.colores['fg_principal']};
                padding: 10px;
            }}
            QTreeWidget::item {{
                padding: 5px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.02);
            }}
            QTreeWidget::item:hover {{ background: rgba(255, 255, 255, 0.05); border-radius: 6px; }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: none;
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings  {{
                border-image: none;
                image: none;
            }}
        """)
        self.tree_historial.itemDoubleClicked.connect(lambda: self.callbacks["abrir_desde_historial"]())
        h_layout.addWidget(self.tree_historial)

        
        layout.addWidget(hist_f, 1)

