import platform
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QFrame, QMenu, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QColor, QAction

class CustomTitleBarApp(QWidget):
    """Barra de título PREMIUM, minimalista y ultra-organizada para PyQt6"""
    def __init__(self, parent, title="", icon_path=None, allow_maximize=True, on_close=None):
        super().__init__(parent)
        self.parent = parent
        self.allow_maximize = allow_maximize
        self.on_close = on_close
        self.setObjectName("CustomTitleBar")
        
        # Sincronización de colores
        self.COLORES = getattr(parent, "COLORES", {
            "bg_secundario": "#1E1E2E",
            "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2",
            "fg_secundario": "#AAB0B8",
            "acento": "#6366F1",
            "error": "#F87171"
        })
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.setFixedHeight(48)
        # --- FIX: Asegurar que el fondo sea oscuro usando selector ID ---
        self.setStyleSheet(f"""
            QWidget#CustomTitleBar {{ 
                background-color: {self.COLORES['bg_secundario']}; 
                border-bottom: 1px solid {self.COLORES['bg_terciario']}; 
            }}
            QLabel {{ color: {self.COLORES['fg_principal']}; border: none; background: transparent; }}
        """)
        
        self.layout_principal = QHBoxLayout(self)
        self.layout_principal.setContentsMargins(15, 0, 0, 0)
        self.layout_principal.setSpacing(0)
        
        # --- SECCIÓN IZQUIERDA: LOGO Y TÍTULO ---
        self.seccion_logo = QFrame()
        self.seccion_logo.setStyleSheet("border: none; background: transparent;")
        layout_logo = QHBoxLayout(self.seccion_logo)
        layout_logo.setContentsMargins(0, 0, 15, 0)
        layout_logo.setSpacing(10)
        
        # Icono (opcional)
        if icon_path:
            self.lbl_icon = QLabel()
            self.lbl_icon.setPixmap(QIcon(icon_path).pixmap(20, 20))
            layout_logo.addWidget(self.lbl_icon)
        
        # Título con estilo tipográfico premium
        self.lbl_titulo = QLabel(title.upper())
        self.lbl_titulo.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self.lbl_titulo.setStyleSheet(f"color: {self.COLORES['acento']};  border: none;")
        layout_logo.addWidget(self.lbl_titulo)
        
        self.layout_principal.addWidget(self.seccion_logo)
        
        # Separador vertical estético
        self.sep_vertical = QFrame()
        self.sep_vertical.setFixedWidth(1)
        self.sep_vertical.setFixedHeight(22)
        self.sep_vertical.setStyleSheet(f"background-color: {self.COLORES['bg_terciario']}; border: none;")
        self.layout_principal.addWidget(self.sep_vertical)
        
        # --- SECCIÓN CENTRAL: MENÚS ---
        self.menu_container = QFrame()
        self.menu_container.setStyleSheet("border: none; background: transparent;")
        self.menu_layout = QHBoxLayout(self.menu_container)
        self.menu_layout.setContentsMargins(10, 0, 10, 0)
        self.menu_layout.setSpacing(5) 
        self.layout_principal.addWidget(self.menu_container)
        
        # Espacio flexible que empuja los controles a la derecha
        self.layout_principal.addStretch()
        
        # --- SECCIÓN DERECHA: CONTROLES DE VENTANA ---
        self.seccion_controles = QFrame()
        self.seccion_controles.setStyleSheet("border: none; background: transparent;")
        layout_controles = QHBoxLayout(self.seccion_controles)
        layout_controles.setContentsMargins(0, 0, 0, 0)
        layout_controles.setSpacing(0)
        
        estilo_btns = f"""
            QPushButton {{
                border: none;
                background-color: transparent;
                color: {self.COLORES['fg_secundario']};
                width: 48px;
                height: 48px;
                font-family: '{self.font_family}';
                font-size: 13px;
            }}
            QPushButton:hover {{ 
                background-color: {self.COLORES['bg_terciario']}; 
                color: white; 
            }}
        """

        # Botón Minimizar
        self.btn_min = QPushButton("—")
        self.btn_min.setStyleSheet(estilo_btns)
        self.btn_min.clicked.connect(self.parent.showMinimized)
        layout_controles.addWidget(self.btn_min)
        
        # Botón Maximizar/Restaurar
        if self.allow_maximize:
            self.btn_max = QPushButton("□")
            self.btn_max.setStyleSheet(estilo_btns)
            self.btn_max.clicked.connect(self.toggle_maximize)
            layout_controles.addWidget(self.btn_max)
            
        # Botón Cerrar (con hover rojo destructivo)
        self.btn_close = QPushButton("✕")
        self.btn_close.setStyleSheet(estilo_btns + f" QPushButton:hover {{ background-color: {self.COLORES['error']}; }}")
        self.btn_close.clicked.connect(self.close_window)
        layout_controles.addWidget(self.btn_close)
        
        self.layout_principal.addWidget(self.seccion_controles)
        
        # --- Lógica de arrastre de ventana ---
        self._tracking = False
        self._start_pos = None

    def toggle_maximize(self):
        if not hasattr(self.parent, "_is_maximized_manual"):
            self.parent._is_maximized_manual = False
            self.parent._normal_geometry = self.parent.geometry()

        if self.parent.isMaximized() or self.parent._is_maximized_manual:
            self.parent.showNormal()
            if self.parent._is_maximized_manual:
                self.parent.setGeometry(self.parent._normal_geometry)
            self.parent._is_maximized_manual = False
            self.btn_max.setText("□")
        else:
            self.parent._normal_geometry = self.parent.geometry()
            
            # Maximizado manual que respeta la barra de tareas (especialmente en Windows)
            # En lugar de showMaximized(), usamos el área disponible para evitar tapar la barra auto-ocultable
            screen_geo = self.parent.screen().availableGeometry()
            self.parent.showNormal() # Asegurar que esté en estado normal para poder moverlo/redimensionarlo manual
            self.parent.setGeometry(screen_geo)
            self.parent._is_maximized_manual = True
            
            self.btn_max.setText("❐")
    def close_window(self):
        if self.on_close: self.on_close()
        else: self.parent.close()

    # Eventos de Mouse para arrastrar la ventana frameless
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._tracking = True
            self._start_pos = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._tracking:
            # Si intentamos arrastrar estando maximizado, restaurar primero
            if getattr(self.parent, "_is_maximized_manual", False):
                self.toggle_maximize()
                # Recalcular start_pos para que el arrastre sea fluido
                self._start_pos = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
                
            self.parent.move(event.globalPosition().toPoint() - self._start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._tracking = False
        event.accept()

    def mouseReleaseEvent(self, event):
        self._tracking = False
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if self.allow_maximize and event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()

