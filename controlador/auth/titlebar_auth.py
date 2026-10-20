import platform
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QIcon

class CustomTitleBar(QWidget):
    """Barra de Título Personalizada para Diálogos de Autenticación"""
    def __init__(self, parent, title="", bg_color="#1E1E2E", fg_color="#E2E2E2", icon_path=None):
        super().__init__(parent)
        self.parent = parent
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 0, 0, 0)
        self.layout.setSpacing(5)
        
        self.setFixedHeight(35)
        self.setStyleSheet(f"background-color: {bg_color}; border-top-left-radius: 12px; border-top-right-radius: 12px;")
        
        # Icono
        if icon_path:
            self.icon_label = QLabel()
            self.icon_label.setFixedSize(20, 20)
            self.icon_label.setPixmap(QIcon(icon_path).pixmap(18, 18))
            self.icon_label.setStyleSheet("border: none; background: transparent;")
            self.layout.addWidget(self.icon_label)
        
        # Título
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {fg_color}; border: none; background: transparent; letter-spacing: 0.5px;")
        self.layout.addWidget(self.title_label)
        
        self.layout.addStretch()
        
        btn_style = """
            QPushButton { 
                border: none; background: transparent; color: #AAB0B8; 
                font-family: 'Arial'; font-weight: bold; width: 45px; height: 35px;
            }
        """

        # Botones
        self.min_btn = QPushButton("-")
        self.min_btn.setFont(QFont("Arial", 12))
        self.min_btn.setStyleSheet(btn_style + "QPushButton:hover { background-color: #3D3D4D; color: white; }")
        self.min_btn.clicked.connect(self.parent.showMinimized)
        self.layout.addWidget(self.min_btn)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFont(QFont("Arial", 10))
        self.close_btn.setStyleSheet(btn_style + "QPushButton:hover { background-color: #F87171; color: white; border-top-right-radius: 12px; }")
        self.close_btn.clicked.connect(self.parent.close)
        self.layout.addWidget(self.close_btn)
        
        self._is_tracking = False
        self._start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_tracking = True
            self._start_pos = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_tracking:
            self.parent.move(event.globalPosition().toPoint() - self._start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_tracking = False
        event.accept()
