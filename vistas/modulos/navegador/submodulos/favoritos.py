from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QLineEdit, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QGridLayout
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

class TabNavegadorFavoritos(QWidget):
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Barra superior con búsqueda y botón de nueva categoría
        top_bar = QHBoxLayout()
        lbl_title = QLabel("BIBLIOTECA DE MARCADORES")
        lbl_title.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: white;")
        top_bar.addWidget(lbl_title)
        
        top_bar.addStretch()
        
        self.txt_fav_search = QLineEdit()
        self.txt_fav_search.setPlaceholderText("🔍 Buscar en mis marcadores...")
        self.txt_fav_search.setFixedWidth(250)
        self.txt_fav_search.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px; padding: 8px 15px;
            }}
            QLineEdit:focus {{ border: 1px solid {self.colores['acento']}; }}
        """)
        self.txt_fav_search.textChanged.connect(self.callbacks["filtrar_favoritos"])
        top_bar.addWidget(self.txt_fav_search)
        
        btn_new_cat = QPushButton("+")
        btn_new_cat.setFixedSize(35, 35)
        btn_new_cat.setToolTip("Nueva Carpeta/Categoría")
        btn_new_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_cat.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 10px; font-weight: bold; font-size: 16px;")
        btn_new_cat.clicked.connect(self.callbacks["nueva_categoria"])
        top_bar.addWidget(btn_new_cat)
        
        layout.addLayout(top_bar)
        
        # Árbol de Favoritos
        self.tree_favoritos = QTreeWidget()
        self.tree_favoritos.setColumnCount(3)
        self.tree_favoritos.setHeaderLabels(["Nombre", "URL / Carpeta", "Fecha"])
        self.tree_favoritos.setIndentation(25)
        self.tree_favoritos.setAnimated(True)
        self.tree_favoritos.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_favoritos.header().setStretchLastSection(False)
        self.tree_favoritos.header().resizeSection(2, 120)
        
        self.tree_favoritos.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores['fg_secundario']};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 12px;
                border-bottom: 1px solid rgba(255,255,255,0.02);
            }}
            QTreeWidget::item:hover {{
                background-color: rgba(255,255,255,0.03);
                color: white;
            }}
            QTreeWidget::item:selected {{
                background-color: {self.colores['acento']}22;
                color: {self.colores['acento']};
            }}
            QHeaderView::section {{
                background-color: {self.colores['bg_terciario']};
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }}
        """)
        
        self.tree_favoritos.itemSelectionChanged.connect(self.callbacks["mostrar_detalles_favorito"])
        self.tree_favoritos.itemDoubleClicked.connect(lambda it, col: self.callbacks["abrir_desde_favoritos"]())
        layout.addWidget(self.tree_favoritos)
        
        # Botones de Acción inferior
        actions_lay = QHBoxLayout()
        actions_lay.setSpacing(10)
        
        configs = [
            ("Abrir 🚀", "abrir_favorito_seleccionado", self.colores['acento']), 
            ("Editar ⚙️", "editar_favorito", self.colores['bg_terciario']), 
            ("Eliminar 🗑️", "eliminar_favorito", "#EF4444")
        ]
        
        for t, cmd, color in configs:
            btn = QPushButton(t)
            btn.setFont(QFont("Inter", 8, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumWidth(110)
            btn.setFixedHeight(32)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {color}; color: white; border-radius: 8px; padding: 4px 12px; }}
                QPushButton:hover {{ background-color: {color}CC; }}
            """)
            btn.clicked.connect(self.callbacks[cmd])
            actions_lay.addWidget(btn)
            
        actions_lay.addStretch()
        layout.addLayout(actions_lay)
        
        # Panel de Detalles inferior estético
        det_f = QFrame()
        det_f.setFixedHeight(100)
        det_f.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']}; 
                border-radius: 12px; 
                border: 1px solid rgba(255,255,255,0.08);
            }}
        """)
        det_lay = QGridLayout(det_f)
        det_lay.setContentsMargins(20, 10, 20, 10)
        det_lay.setSpacing(10)
        
        labels = ["NOMBRE", "URL", "CATEGORÍA", "FECHA"]
        self.det_vals = []
        for i, text in enumerate(labels):
            l = QLabel(text)
            l.setFont(QFont("Inter", 7, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {self.colores['fg_secundario']}; ")
            det_lay.addWidget(l, i % 2, (i // 2) * 2)
            
            val = QLabel("---")
            val.setFont(QFont("Consolas", 9))
            val.setStyleSheet(f"color: {self.colores['fg_principal']};")
            det_lay.addWidget(val, i % 2, (i // 2) * 2 + 1)
            self.det_vals.append(val)
        
        self.lbl_det_nombre, self.lbl_det_url, self.lbl_det_cat, self.lbl_det_fecha = self.det_vals
        self.lbl_det_url.setStyleSheet(f"color: {self.colores['acento']};")
        layout.addWidget(det_f)

    def get_selected_fav_name(self):
        item = self.tree_favoritos.currentItem()
        if not item or item.parent() is None: # Si es nulo o es una carpeta principal
            return None
        return item.text(0)

    def get_selected_category_name(self):
        item = self.tree_favoritos.currentItem()
        if not item: return None
        if item.parent() is None: return item.text(0) # Es la categoría
        return item.parent().text(0) # Es el padre del favorito
