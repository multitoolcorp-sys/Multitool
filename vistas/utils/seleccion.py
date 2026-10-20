import platform
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QHBoxLayout, QFrame, QApplication
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QFont, QPainter, QPainterPath, QPen, QColor

from vistas.utils.avatar import AvatarUtils

class AccountSelector(QDialog):
    """Selector de cuentas PRE-ESTABLECIDAS con diseño amplio, Avatar 80x80 y fecha de última conexión"""
    def __init__(self, parent, accounts, on_select_callback, colores):
        super().__init__(parent)
        self.setWindowTitle("Selector de Cuentas")
        self.setFixedSize(540, 660)
        self.accounts = accounts
        self.on_select_callback = on_select_callback
        self.colores = colores
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setStyleSheet(f"background-color: {self.colores['bg_principal']}; border: 1px solid {self.colores['bg_terciario']}; border-radius: 14px;")
        
        self.crear_widgets()
        self._center_window()

    def _center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.left() + (screen.width() - self.width()) // 2
        y = screen.top() + (screen.height() - self.height()) // 2
        self.move(x, y)

    def crear_widgets(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 35, 35, 35)
        layout.setSpacing(14)
        
        lbl_tit = QLabel("ACCESO RÁPIDO")
        lbl_tit.setFont(QFont(self.font_family, 22, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tit)
        
        lbl_sub = QLabel("Elige una cuenta guardada para acceder de inmediato")
        lbl_sub.setFont(QFont(self.font_family, 10))
        lbl_sub.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_sub)
        
        layout.addSpacing(15)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(container)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_layout.setSpacing(14)
        
        for acc in self.accounts:
            item = self._crear_item_cuenta(acc)
            scroll_layout.addWidget(item)
            
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        
        layout.addSpacing(15)
        
        btn_otra = QPushButton("👤 USAR OTRA CUENTA")
        btn_otra.setMinimumHeight(48)
        btn_otra.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_otra.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                font-family: '{self.font_family}';
            }}
            QPushButton:hover {{ background-color: {self.colores['bg_terciario']}; border-color: {self.colores['acento']}; }}
        """)
        btn_otra.clicked.connect(self.reject)
        layout.addWidget(btn_otra)
        
        btn_close = QPushButton("✕", self)
        btn_close.setGeometry(495, 12, 30, 30)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"background: transparent; color: {self.colores['fg_secundario']}; font-size: 18px; font-weight: bold; border: none;")
        btn_close.clicked.connect(self.close)

    def _crear_item_cuenta(self, acc):
        frame = QFrame()
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setStyleSheet(f"""
            QFrame {{ background-color: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); padding: 10px; }}
            QFrame:hover {{ background-color: {self.colores['bg_terciario']}; border: 1px solid {self.colores['acento']}; }}
        """)
        
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(16)
        
        lbl_av = QLabel()
        lbl_av.setFixedSize(100, 100)
        lbl_av.clearMask()
        lbl_av.setStyleSheet("background: transparent; border: none;")
        
        shape = acc.get("avatar_shape", "circle")
        
        raw_pix = None
        try:
            av_path = acc.get("avatar")
            if av_path and Path(av_path).exists():
                loaded = QPixmap(str(av_path))
                if not loaded.isNull():
                    raw_pix = loaded.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        except Exception:
            pass
        
        if not raw_pix:
            initial = acc["usuario"][0].upper() if acc.get("usuario") else "?"
            pix_final = AvatarUtils.get_initials_avatar(initial, size=90, bg_color=self.colores['acento'], circular=(shape=="circle"))
        else:
            out_pix = QPixmap(80, 80)
            out_pix.fill(Qt.GlobalColor.transparent)

            painter = QPainter(out_pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            
            path_obj = QPainterPath()
            if shape == "circle":
                path_obj.addEllipse(0, 0, 80, 80)
            elif shape == "square":
                path_obj.addRect(0, 0, 80, 80)
            else:
                path_obj.addRoundedRect(0, 0, 80, 80, 14, 14)
                
            painter.setClipPath(path_obj)
            x_off = (80 - raw_pix.width()) // 2
            y_off = (80 - raw_pix.height()) // 2
            painter.drawPixmap(x_off, y_off, raw_pix)
            
            pen = QPen(QColor(self.colores['acento']), 3)
            painter.setPen(pen)
            if shape == "circle":
                painter.drawEllipse(1, 1, 78, 78)
            elif shape == "square":
                painter.drawRect(1, 1, 78, 78)
            else:
                painter.drawRoundedRect(1, 1, 78, 78, 14, 14)
            painter.end()
            pix_final = out_pix
            
        lbl_av.setPixmap(pix_final)
        lbl_av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_av)
        
        # Información de la cuenta
        txt_l = QVBoxLayout()
        txt_l.setSpacing(3)
        
        usr = QLabel(acc["usuario"])
        usr.setFont(QFont(self.font_family, 15, QFont.Weight.Bold))
        usr.setStyleSheet("color: white; border: none; background: transparent;")
        txt_l.addWidget(usr)
        
        per_str = acc.get("persona") or acc.get("correo") or "Usuario registrado"
        per = QLabel(f"👤 {per_str}")
        per.setFont(QFont(self.font_family, 10))
        per.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        txt_l.addWidget(per)
        
        # Última conexión
        ult = acc.get("ultima_conexion")
        if not ult:
            hist = acc.get("historial", [])
            if hist:
                last_line = hist[-1]
                if "[" in last_line and "]" in last_line:
                    ult = last_line.split("]")[0].replace("[", "").strip()
        if not ult:
            ult = "Activo recientemente"
            
        lbl_ult = QLabel(f"🕒 Última sesión: {ult}")
        lbl_ult.setFont(QFont(self.font_family, 9))
        lbl_ult.setStyleSheet("color: #34D399; border: none; background: transparent;")
        txt_l.addWidget(lbl_ult)
        
        lay.addLayout(txt_l, 1)
        
        frame.mousePressEvent = lambda e: self.seleccionar(acc)
        return frame

    def seleccionar(self, acc):
        self.accept()
        if self.on_select_callback:
            self.on_select_callback(acc)

