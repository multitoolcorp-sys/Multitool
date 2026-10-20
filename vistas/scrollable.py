import platform
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QScrollArea, 
    QFrame, QButtonGroup, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class ScrollableNavBar(QFrame):
    """
    Componente de navegación horizontal desplazable con botones de flecha.
    Optimizado para PyQt6 y multiplataforma.
    """
    tabSelected = pyqtSignal(int)

    def __init__(self, parent=None, colores=None):
        super().__init__(parent)
        self.colores = colores or {
            "bg_secundario": "#1E1E2E",
            "bg_terciario": "#2D2D3D",
            "fg_secundario": "#AAB0B8",
            "acento": "#6366F1",
            "acento_hover": "#818CF8"
        }
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.setFixedHeight(50)
        self.setStyleSheet(f"""
            QFrame {{ 
                background-color: {self.colores['bg_secundario']}; 
                border-bottom: 1px solid {self.colores['bg_terciario']};
            }}
        """)
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Botón Izquierdo
        self.btn_left = QPushButton("◀")
        self.btn_left.setFixedSize(30, 50)
        self.btn_left.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_left.setStyleSheet(f"border: none; color: {self.colores['fg_secundario']}; background: transparent; font-weight: bold;")
        self.btn_left.clicked.connect(lambda: self.scroll(-100))
        self.main_layout.addWidget(self.btn_left)

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_widget.setFixedHeight(50)
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 0, 10, 0)
        self.content_layout.setSpacing(5)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area, 1)

        # Botón Derecho
        self.btn_right = QPushButton("▶")
        self.btn_right.setFixedSize(30, 50)
        self.btn_right.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_right.setStyleSheet(f"border: none; color: {self.colores['fg_secundario']}; background: transparent; font-weight: bold;")
        self.btn_right.clicked.connect(lambda: self.scroll(100))
        self.main_layout.addWidget(self.btn_right)

        # Botón Pantalla Completa / Ocultar Barras (F11)
        self.btn_fullscreen = QPushButton("⛶")
        self.btn_fullscreen.setFixedSize(36, 50)
        self.btn_fullscreen.setToolTip("Pantalla Completa / Ocultar Barras (F11)")
        self.btn_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fullscreen.setStyleSheet(f"""
            QPushButton {{
                border: none;
                color: {self.colores['fg_secundario']};
                background: transparent;
                font-size: 15px;
                font-weight: bold;
                padding-right: 6px;
            }}
            QPushButton:hover {{
                color: {self.colores['acento']};
                background: rgba(255, 255, 255, 0.05);
            }}
        """)
        if parent and hasattr(parent, "toggle_pantalla_completa"):
            self.btn_fullscreen.clicked.connect(parent.toggle_pantalla_completa)
        self.main_layout.addWidget(self.btn_fullscreen)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = []

    def clear(self):
        """Limpia todos los botones"""
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            if item.widget():
                self.group.removeButton(item.widget())
                item.widget().deleteLater()
        self.buttons = []

    def add_tab(self, name, index, checked=False):
        """Agrega un botón de pestaña con soporte para Drag & Drop"""
        btn = NavButton(name, index, self)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_style = f"""
            QPushButton {{ 
                background: transparent; color: {self.colores['fg_secundario']}; 
                border-radius: 16px; padding: 6px 18px; font-size: 12px; font-weight: 600;
                font-family: '{self.font_family}';
                margin: 0 5px;
            }}
            QPushButton:hover {{ background: {self.colores['bg_terciario']}; color: white; }}
            QPushButton:checked {{ 
                background: {self.colores['acento']}; 
                color: white; 
                border: 1px solid {self.colores['acento_hover']};
            }}
        """
        btn.setStyleSheet(btn_style)
        btn.clicked.connect(lambda: self.tabSelected.emit(index))
        
        self.content_layout.addWidget(btn)
        self.buttons.append(btn)
        self.group.addButton(btn, index)
        return btn

    def select_tab(self, index):
        """Selecciona una pestaña visualmente"""
        btn = self.group.button(index)
        if btn:
            btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(False)
            self.scroll_area.ensureWidgetVisible(btn)

    def seleccionar_tab(self, index):
        """Alias en español para compatibilidad con llamadas existentes"""
        self.select_tab(index)

    def scroll(self, delta):
        hbar = self.scroll_area.horizontalScrollBar()
        hbar.setValue(hbar.value() + delta)

class NavButton(QPushButton):
    def __init__(self, name, index, parent_nav):
        super().__init__(name)
        self.index = index
        self.parent_nav = parent_nav
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
            # Cambiar a este módulo cuando se arrastra un archivo encima
            self.parent_nav.tabSelected.emit(self.index)
            
    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        # Si sueltan el archivo justo en el botón, no hacemos nada especial, 
        # pero permitimos que el drag termine limpiamente.
        event.ignore()


