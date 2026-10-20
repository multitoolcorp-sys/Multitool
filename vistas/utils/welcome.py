import platform
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont

from vistas.utils.avatar import AvatarUtils

class WelcomeScreen(QDialog):
    """Pantalla de Bienvenida con Avatar CUADRADO y efectos premium multiplataforma"""
    def __init__(self, parent, usuario, avatar_path, on_accept_callback, colores):
        super().__init__(parent)
        self.setWindowTitle("Bienvenido")
        self.setFixedSize(500, 500)
        self.usuario = usuario
        self.avatar_path = avatar_path
        self.on_accept_callback = on_accept_callback
        self.colores = colores
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(f"background-color: {self.colores['bg_principal']}; border: 1px solid {self.colores['bg_terciario']}; border-radius: 15px;")
        
        self.crear_widgets()
        self.center_window()
        
        self.setWindowOpacity(0.0)
        self.opacity = 0.0
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self._fade_in)
        self.fade_timer.start(30)

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.left() + (screen.width() - self.width()) // 2
        y = screen.top() + (screen.height() - self.height()) // 2
        self.move(x, y)

    def _fade_in(self):
        self.opacity += 0.05
        self.setWindowOpacity(self.opacity)
        if self.opacity >= 1.0:
            self.fade_timer.stop()

    def crear_widgets(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(15)
        
        # --- AVATAR CUADRADO ---
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(120, 120)
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_avatar.setStyleSheet(f"border: 2px solid {self.colores['acento']}; border-radius: 8px; background: transparent;")
        
        pix = None
        try:
            if self.avatar_path and Path(self.avatar_path).exists():
                pix = AvatarUtils.get_square_pixmap(QPixmap(str(self.avatar_path)), size=120)
        except: pass
            
        if not pix:
            initial = self.usuario[0].upper() if self.usuario else "?"
            pix = AvatarUtils.get_initials_avatar(initial, size=120, bg_color=self.colores['acento'], circular=False)
            
        self.lbl_avatar.setPixmap(pix)
        layout.addWidget(self.lbl_avatar, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addSpacing(10)
        
        # Bienvenida
        lbl_hola = QLabel("¡HOLA DE NUEVO!")
        lbl_hola.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_hola.setStyleSheet(f"color: {self.colores['fg_secundario']};  border: none; background: transparent;")
        lbl_hola.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_hola)
        
        lbl_user = QLabel(f"{self.usuario.upper()}")
        lbl_user.setFont(QFont(self.font_family, 32, QFont.Weight.Black))
        lbl_user.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        lbl_user.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_user)
        
        lbl_ready = QLabel("Estamos preparando todo para ti.")
        lbl_ready.setFont(QFont(self.font_family, 10))
        lbl_ready.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        lbl_ready.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_ready)
        
        layout.addStretch()
        
        # Botón Premium
        btn_aceptar = QPushButton("INGRESAR AHORA")
        btn_aceptar.setFixedHeight(55)
        btn_aceptar.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        btn_aceptar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_aceptar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        btn_aceptar.clicked.connect(self.aceptar)
        layout.addWidget(btn_aceptar)

    def aceptar(self):
        self.accept()
        if self.on_accept_callback:
            self.on_accept_callback()

