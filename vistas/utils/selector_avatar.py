import sys
import platform
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedLayout, QFrame, QApplication
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QFont, QIcon

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent.parent
    return base_path / relative_path

class SelectorAvatar(QDialog):
    """Selector de origen de Avatar con diseño premium y soporte multiplataforma"""
    def __init__(self, parent, on_pixel_art_callback, on_desktop_callback, colores):
        super().__init__(parent)
        self.setWindowTitle("Elige tu destino...")
        self.setFixedSize(600, 400)
        self.on_pixel_art_callback = on_pixel_art_callback
        self.on_desktop_callback = on_desktop_callback
        self.colores = colores
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.bg_image_path = resource_path("vistas/utils/elige.png")
        self.setup_ui()
        self.center_window()

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.left() + (screen.width() - self.width()) // 2
        y = screen.top() + (screen.height() - self.height()) // 2
        self.move(x, y)

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Contenedor con fondo
        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("bgFrame")
        self.layout.addWidget(self.bg_frame)
        
        self.lbl_bg = QLabel(self.bg_frame)
        if self.bg_image_path.exists():
            pixmap = QPixmap(str(self.bg_image_path))
            self.lbl_bg.setPixmap(pixmap.scaled(600, 400, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        
        btn_layout = QHBoxLayout(self.lbl_bg)
        btn_layout.setContentsMargins(50, 0, 50, 50)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        self.btn_pixel = QPushButton("MODO PIXELART")
        self.btn_pixel.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_pixel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pixel.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white;
                padding: 15px;
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        self.btn_pixel.clicked.connect(self._choose_pixel)
        btn_layout.addWidget(self.btn_pixel)
        
        btn_layout.addStretch()
        
        self.btn_desktop = QPushButton("DESDE ESCRITORIO")
        self.btn_desktop.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_desktop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_desktop.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                padding: 15px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #444444; }
        """)
        self.btn_desktop.clicked.connect(self._choose_desktop)
        btn_layout.addWidget(self.btn_desktop)

    def _choose_pixel(self):
        self.accept()
        if self.on_pixel_art_callback:
            self.on_pixel_art_callback()

    def _choose_desktop(self):
        self.accept()
        if self.on_desktop_callback:
            self.on_desktop_callback()

