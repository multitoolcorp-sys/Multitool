"""
center_views.py - Ventana de widgets centrada en pantalla con animaciones de apertura/cierre, fijado y redimensión libre por bordes
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizeGrip
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QPoint, QEvent
from PyQt6.QtGui import QFont, QGuiApplication

from ..utils.dock_math import get_screen_geometry

class CenteredWidgetWindow(QWidget):
    """Ventana de widget centrada en pantalla con animaciones, minimización por botón o doble clic y redimensión libre por bordes"""
    TITLE_BAR_H = 32

    def __init__(self, key, widget, parent_window):
        super().__init__()
        self.key = key
        self.widget = widget
        self.parent_window = parent_window
        self.colores = parent_window.colores
        self._is_closing = False
        self._collapsed = False

        # Redimensionamiento libre por bordes (estilo notas adhesivas)
        self._resize_edge = None
        self._resize_start_geom = None
        self._resize_start_pos = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setMinimumSize(180, self.TITLE_BAR_H)

        self.drag_position = QPoint()

        sizes = {
            "notes": (380, 280), "calc": (240, 320), "terminal": (400, 240),
            "navegador": (380, 160), "seguridad": (350, 200), "archivos": (400, 350),
            "calendario": (360, 330), "sistema": (320, 220), "reproductor": (420, 360),
            "grabadora": (280, 160), "cuaderno": (450, 300), "chat": (350, 380),
            "extras": (380, 350), "tiempo": (350, 240), "traductor": (380, 240)
        }
        self.target_width, self.target_height = sizes.get(self.key, (350, 280))
        self._expanded_width = self.target_width
        self._expanded_height = self.target_height

        self.init_ui()

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(220)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self.on_animation_finished)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self.container = QFrame()
        self.container.setObjectName("CenteredWidgetFrame")
        self.container.setMouseTracking(True)
        self.container.setStyleSheet(f"""
            QFrame#CenteredWidgetFrame {{
                background-color: rgba(18, 18, 24, 0.98);
                border: 2px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 12px;
            }}
        """)
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(8, 8, 8, 6)
        self.container_layout.setSpacing(4)

        # Barra de título superior
        self.title_bar_widget = QWidget()
        self.title_bar_widget.setFixedHeight(26)
        self.title_bar_widget.installEventFilter(self)
        title_bar = QHBoxLayout(self.title_bar_widget)
        title_bar.setContentsMargins(4, 2, 4, 2)
        title_bar.setSpacing(6)

        self.lbl_title = QLabel(f"🛠️ {self.parent_window.get_widget_display_name(self.key)}")
        self.lbl_title.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        self.lbl_title.setToolTip("Doble clic en la barra para minimizar / restaurar tamaño")
        title_bar.addWidget(self.lbl_title)

        title_bar.addStretch()

        self.btn_door = QPushButton("▼")
        self.btn_door.setToolTip("Minimizar / Reducir tamaño (o doble clic en la barra)")
        self.btn_door.setFixedSize(20, 20)
        self.btn_door.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_door.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores.get('fg_secundario', '#9CA3AF')};
                font-weight: bold;
                border: none;
                font-size: 10px;
            }}
            QPushButton:hover {{ color: {self.colores.get('acento', '#6366F1')}; }}
        """)
        self.btn_door.clicked.connect(self.toggle_door)
        title_bar.addWidget(self.btn_door)

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
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.div = QFrame()
        self.div.setFrameShape(QFrame.Shape.HLine)
        self.div.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2A2A3C')}; max-height: 1px; border: none;")
        self.container_layout.addWidget(self.div)

        # Contenido del Widget
        self.container_layout.addWidget(self.widget, 1)
        self.widget.show()

        # Grip de redimensionamiento
        self.bottom_bar = QWidget()
        self.bottom_bar.setFixedHeight(12)
        bottom_bar_lay = QHBoxLayout(self.bottom_bar)
        bottom_bar_lay.setContentsMargins(0, 0, 0, 0)
        bottom_bar_lay.addStretch()
        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(12, 12)
        self.size_grip.setToolTip("Arrastra para redimensionar libremente")
        bottom_bar_lay.addWidget(self.size_grip)
        self.container_layout.addWidget(self.bottom_bar)

        layout.addWidget(self.container)

    def eventFilter(self, obj, event):
        # Doble clic en la barra de título personalizada para minimizar/expandir
        if obj == self.title_bar_widget and event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                self.toggle_door()
                return True
        return super().eventFilter(obj, event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos_y = event.position().y()
            if pos_y <= (self.TITLE_BAR_H + 8):
                self.toggle_door()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def _get_resize_edge(self, pos):
        """Detecta si el cursor está sobre algún borde exterior para estirar libremente"""
        if self._collapsed:
            return None
        margin = 8
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()

        on_left = x <= margin
        on_right = x >= w - margin
        on_top = y <= margin
        on_bottom = y >= h - margin

        if on_top and on_left: return "top_left"
        if on_top and on_right: return "top_right"
        if on_bottom and on_left: return "bottom_left"
        if on_bottom and on_right: return "bottom_right"
        if on_left: return "left"
        if on_right: return "right"
        if on_top: return "top"
        if on_bottom: return "bottom"
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            if not self._collapsed:
                edge = self._get_resize_edge(pos)
                if edge:
                    self._resize_edge = edge
                    self._resize_start_geom = self.geometry()
                    self._resize_start_pos = event.globalPosition().toPoint()
                    event.accept()
                    return

            if pos.y() <= (self.TITLE_BAR_H + 8):
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        g_pos = event.globalPosition().toPoint()

        # 1. Redimensionamiento libre por bordes
        if self._resize_edge and self._resize_start_geom and self._resize_start_pos:
            dx = g_pos.x() - self._resize_start_pos.x()
            dy = g_pos.y() - self._resize_start_pos.y()
            geom = QRect(self._resize_start_geom)
            min_w, min_h = 180, 100

            if "right" in self._resize_edge:
                geom.setWidth(max(min_w, self._resize_start_geom.width() + dx))
            elif "left" in self._resize_edge:
                new_w = max(min_w, self._resize_start_geom.width() - dx)
                geom.setLeft(self._resize_start_geom.right() - new_w)

            if "bottom" in self._resize_edge:
                geom.setHeight(max(min_h, self._resize_start_geom.height() + dy))
            elif "top" in self._resize_edge:
                new_h = max(min_h, self._resize_start_geom.height() - dy)
                geom.setTop(self._resize_start_geom.bottom() - new_h)

            self.setGeometry(geom)
            event.accept()
            return

        # 2. Arrastre de posición
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(g_pos - self.drag_position)
            event.accept()
            return

        # 3. Cursor dinámico según borde
        if not self._collapsed:
            edge = self._get_resize_edge(event.position().toPoint())
            if edge in ("left", "right"):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif edge in ("top", "bottom"):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif edge in ("top_left", "bottom_right"):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif edge in ("top_right", "bottom_left"):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_edge:
            self._resize_edge = None
            self._resize_start_geom = None
            self._resize_start_pos = None
            if not self._collapsed:
                self._expanded_width = self.width()
                self._expanded_height = self.height()
            event.accept()
            return

        self.drag_position = QPoint()
        super().mouseReleaseEvent(event)

    def toggle_door(self):
        """Alterna el modo persiana / colapso para reducir tamaño al mínimo"""
        cur_geom = self.geometry()
        if not self._collapsed:
            self._expanded_width = cur_geom.width()
            self._expanded_height = cur_geom.height()
            target_w = 180
            target_h = self.TITLE_BAR_H
            self.btn_door.setText("▲")
            self.btn_door.setToolTip("Expandir / Restaurar tamaño")
            self.container_layout.setContentsMargins(6, 4, 6, 4)
            self._collapsed = True
            if self.widget:
                self.widget.hide()
            self.div.hide()
            if hasattr(self, "bottom_bar"):
                self.bottom_bar.hide()
        else:
            target_w = getattr(self, "_expanded_width", self.target_width)
            target_h = getattr(self, "_expanded_height", self.target_height)
            self.btn_door.setText("▼")
            self.btn_door.setToolTip("Minimizar / Reducir tamaño")
            self.container_layout.setContentsMargins(8, 8, 8, 6)
            self._collapsed = False
            if self.widget:
                self.widget.show()
            self.div.show()
            if hasattr(self, "bottom_bar"):
                self.bottom_bar.show()

        target_geom = QRect(cur_geom.x(), cur_geom.y(), target_w, target_h)
        self.anim.stop()
        self.anim.setStartValue(cur_geom)
        self.anim.setEndValue(target_geom)
        self.anim.start()

    toggle_minimize = toggle_door

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
