"""
center_views.py - Ventana de widgets centrada en pantalla con animaciones de apertura/cierre y fijado
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizeGrip
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt6.QtGui import QFont

from ..utils.dock_math import get_screen_geometry

class CenteredWidgetWindow(QWidget):
    """Ventana de widget centrada en pantalla con animaciones de apertura/cierre y redimensionable"""
    def __init__(self, key, widget, parent_window):
        super().__init__()
        self.key = key
        self.widget = widget
        self.parent_window = parent_window
        self.colores = parent_window.colores
        self._is_closing = False
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.drag_position = QPoint()
        
        sizes = {
            "notes": (380, 280), "calc": (240, 320), "terminal": (400, 240),
            "navegador": (380, 160), "seguridad": (350, 200), "archivos": (400, 350),
            "calendario": (360, 330), "sistema": (320, 220), "reproductor": (420, 360),
            "grabadora": (280, 160), "cuaderno": (450, 300), "chat": (350, 380),
            "extras": (380, 350), "tiempo": (350, 240), "traductor": (380, 240)
        }
        self.target_width, self.target_height = sizes.get(self.key, (350, 280))
        
        self.init_ui()
        
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self.on_animation_finished)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        self.container = QFrame()
        self.container.setObjectName("CenteredWidgetFrame")
        self.container.setStyleSheet(f"""
            QFrame#CenteredWidgetFrame {{
                background-color: rgba(18, 18, 24, 0.98);
                border: 2px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 12px;
            }}
        """)
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(8, 8, 8, 8)
        self.container_layout.setSpacing(4)
        
        # Barra de título superior
        self.title_bar_widget = QWidget()
        title_bar = QHBoxLayout(self.title_bar_widget)
        title_bar.setContentsMargins(4, 4, 4, 4)
        title_bar.setSpacing(6)
        
        self.lbl_title = QLabel(f"🛠️ {self.parent_window.get_widget_display_name(self.key)}")
        self.lbl_title.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        title_bar.addWidget(self.lbl_title)
        
        title_bar.addStretch()
        
        self.btn_pin = QPushButton("📌")
        self.btn_pin.setToolTip("Fijar al escritorio")
        self.btn_pin.setFixedSize(20, 20)
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores.get('fg_secundario', '#9CA3AF')};
                border: none;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: white; }}
        """)
        self.btn_pin.clicked.connect(self.toggle_pin)
        title_bar.addWidget(self.btn_pin)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("Cerrar")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #AAB0B8;
                font-weight: bold;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover { color: #F87171; }
        """)
        self.btn_close.clicked.connect(self.animate_close)
        title_bar.addWidget(self.btn_close)
        
        self.container_layout.addWidget(self.title_bar_widget)
        
        # Separador horizontal
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2A2A3C')}; max-height: 1px; border: none;")
        self.container_layout.addWidget(div)
        
        # Contenido del Widget
        self.container_layout.addWidget(self.widget, 1)
        self.widget.show()
        
        # Grip de redimensionamiento
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        size_grip = QSizeGrip(self)
        size_grip.setFixedSize(12, 12)
        bottom_bar.addWidget(size_grip)
        self.container_layout.addLayout(bottom_bar)
        
        layout.addWidget(self.container)

    def take_widget(self):
        """Desvincula el widget contenido para que pueda ser re-acoplado o fijado al escritorio"""
        w = self.widget
        if w is not None:
            if hasattr(self, "container_layout") and self.container_layout:
                self.container_layout.removeWidget(w)
            elif hasattr(self, "container") and self.container.layout():
                self.container.layout().removeWidget(w)
            w.setParent(None)
            self.widget = None
        return w

    takeWidget = take_widget

    def animate_open(self):
        screen = get_screen_geometry()
        center_point = screen.center()
        
        try:
            btn_pos = self.parent_window.mapToGlobal(QPoint(0, 0))
            btn_center = QPoint(btn_pos.x() + self.parent_window.width() // 2, btn_pos.y() + self.parent_window.height() // 2)
        except Exception:
            btn_center = center_point
        
        target_x = center_point.x() - (self.target_width // 2)
        target_y = center_point.y() - (self.target_height // 2)
        
        start_rect = QRect(btn_center.x(), btn_center.y(), 0, 0)
        target_rect = QRect(target_x, target_y, self.target_width, self.target_height)
        
        self.setGeometry(start_rect)
        self.show()
        
        self.anim.stop()
        self.anim.setStartValue(start_rect)
        self.anim.setEndValue(target_rect)
        self.anim.start()

    show_centered = animate_open

    def animate_close(self):
        self._is_closing = True
        btn_pos = self.parent_window.mapToGlobal(QPoint(0, 0))
        btn_center = QPoint(btn_pos.x() + self.parent_window.width() // 2, btn_pos.y() + self.parent_window.height() // 2)
        
        start_rect = self.geometry()
        target_rect = QRect(btn_center.x(), btn_center.y(), 0, 0)
        
        self.anim.stop()
        self.anim.setStartValue(start_rect)
        self.anim.setEndValue(target_rect)
        self.anim.start()

    def on_animation_finished(self):
        if self._is_closing:
            if self.key in self.parent_window.center_windows:
                del self.parent_window.center_windows[self.key]
            self.close()

    def toggle_pin(self):
        self._is_closing = True
        self.parent_window.pin_widget_from_center(self.key)
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos_y = event.position().y()
            if pos_y <= 36:
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = QPoint()
        super().mouseReleaseEvent(event)
