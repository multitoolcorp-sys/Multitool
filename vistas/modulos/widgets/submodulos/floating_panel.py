"""
floating_panel.py - Ventanas flotantes y panel acoplable para Quick Widgets
Contiene DesktopWidgetWindow y FloatingWidgetPanel con soporte para visibilidad siempre en primer plano (2º plano de Windows).
"""
import os
import json
import platform
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QMenu, QApplication, QSizeGrip
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QPoint, pyqtSignal, QEvent
from PyQt6.QtGui import QFont, QCursor, QGuiApplication, QAction

from ..utils.dock_math import calculate_dock_position, get_screen_geometry


class DesktopWidgetWindow(QWidget):
    """Ventana independiente para widgets fijados en el escritorio con modo puerta (roll-up) y redimensión libre por bordes"""
    TITLE_BAR_H = 26

    def __init__(self, key, widget, parent_drawer):
        super().__init__()
        self.key = key
        self.widget = widget
        self.parent_drawer = parent_drawer
        self.colores = parent_drawer.colores
        self._is_closing = False
        self._collapsed = False
        self._expanded_height = 280
        self._expanded_width = 370

        # Estados de redimensionamiento libre (estilo notas adhesivas)
        self._resize_edge = None
        self._resize_start_geom = None
        self._resize_start_pos = None

        # Ventana transparente siempre en primer plano con seguimiento de ratón
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setMinimumSize(160, self.TITLE_BAR_H)

        self.init_ui()
        self.drag_position = QPoint()

        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        self.container = QFrame()
        self.container.setObjectName("DesktopWidgetFrame")
        self.container.setMouseTracking(True)
        self.container.setStyleSheet(f"""
            QFrame#DesktopWidgetFrame {{
                background-color: rgba(18, 18, 24, 0.95);
                border: 1.5px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 8px;
            }}
        """)
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(8, 6, 8, 6)
        self.container_layout.setSpacing(4)

        # Barra de título personalizada
        self._title_bar_widget = QWidget()
        self._title_bar_widget.setFixedHeight(22)
        self._title_bar_widget.setStyleSheet("background: transparent;")
        self._title_bar_widget.installEventFilter(self)
        title_bar = QHBoxLayout(self._title_bar_widget)
        title_bar.setContentsMargins(0, 0, 0, 0)
        title_bar.setSpacing(4)

        self.lbl_title = QLabel(f"📌 {self.parent_drawer.get_widget_display_name(self.key)}")
        self.lbl_title.setStyleSheet("color: white; font-weight: bold; font-size: 10px;")
        self.lbl_title.setToolTip("Doble clic en la barra para minimizar / restaurar")

        self.btn_door = QPushButton("▼")
        self.btn_door.setFixedSize(18, 18)
        self.btn_door.setToolTip("Minimizar / Reducir tamaño (o doble clic en la barra)")
        self.btn_door.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_door.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores.get('fg_secundario', '#9CA3AF')};
                font-weight: bold;
                border: none;
                font-size: 9px;
            }}
            QPushButton:hover {{ color: {self.colores.get('acento', '#6366F1')}; }}
        """)
        self.btn_door.clicked.connect(self.toggle_door)

        btn_unpin = QPushButton("✕")
        btn_unpin.setFixedSize(18, 18)
        btn_unpin.setToolTip("Desfijar widget")
        btn_unpin.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_unpin.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #AAB0B8;
                font-weight: bold;
                border: none;
                font-size: 10px;
            }
            QPushButton:hover { color: #F87171; }
        """)
        btn_unpin.clicked.connect(self.close_and_redock)

        title_bar.addWidget(self.lbl_title)
        title_bar.addStretch()
        title_bar.addWidget(self.btn_door)
        title_bar.addWidget(btn_unpin)
        self.container_layout.addWidget(self._title_bar_widget)

        self._div = QFrame()
        self._div.setFrameShape(QFrame.Shape.HLine)
        self._div.setStyleSheet(
            f"background-color: {self.colores.get('bg_terciario', '#2A2A3C')}; max-height: 1px; border: none;"
        )
        self.container_layout.addWidget(self._div)

        self._content_wrapper = QWidget()
        self._content_wrapper.setStyleSheet("background: transparent;")
        cw_layout = QVBoxLayout(self._content_wrapper)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.setSpacing(0)
        cw_layout.addWidget(self.widget)
        self.widget.show()
        self.container_layout.addWidget(self._content_wrapper, 1)

        # Barra inferior con QSizeGrip para redimensionamiento en esquina
        self._bottom_bar = QWidget()
        self._bottom_bar.setFixedHeight(12)
        bb_layout = QHBoxLayout(self._bottom_bar)
        bb_layout.setContentsMargins(0, 0, 0, 0)
        bb_layout.addStretch()
        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(12, 12)
        self.size_grip.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.size_grip.setToolTip("Arrastra para redimensionar")
        bb_layout.addWidget(self.size_grip)
        self.container_layout.addWidget(self._bottom_bar)

        layout.addWidget(self.container)

        sizes = {
            "notes": (380, 300), "calc": (260, 340), "terminal": (420, 260),
            "navegador": (420, 340), "seguridad": (370, 280), "archivos": (420, 380),
            "calendario": (370, 360), "sistema": (340, 280), "reproductor": (440, 380),
            "grabadora": (300, 200), "cuaderno": (460, 320), "chat": (370, 400),
            "extras": (380, 340), "minigames": (420, 380), "tiempo": (360, 280), "traductor": (400, 260)
        }
        w, h = sizes.get(self.key, (370, 300))
        self._expanded_width = w
        self._expanded_height = h
        self.resize(w, h)

    def eventFilter(self, obj, event):
        # Doble clic en la barra de título personalizada para minimizar/expandir
        if obj == self._title_bar_widget and event.type() == QEvent.Type.MouseButtonDblClick:
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
        """Detecta si el cursor está sobre algún borde exterior para estirar libremente (estilo notas adhesivas)"""
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

        # 1. Redimensionamiento libre por bordes (ancho, alto o diagonales)
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

        # 2. Arrastre de posición por la barra superior
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            new_pos = g_pos - self.drag_position
            # Magnet Snap-to-Edge (Ajuste magnético de bordes)
            screen = QGuiApplication.primaryScreen().geometry()
            snap_dist = 15
            x, y = new_pos.x(), new_pos.y()
            w, h = self.width(), self.height()

            if abs(x - screen.left()) < snap_dist: x = screen.left()
            elif abs((x + w) - screen.right()) < snap_dist: x = screen.right() - w

            if abs(y - screen.top()) < snap_dist: y = screen.top()
            elif abs((y + h) - screen.bottom()) < snap_dist: y = screen.bottom() - h

            self.move(x, y)
            event.accept()
            return

        # 3. Cursor dinámico interactivo según borde
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
        cur_geom = self.geometry()
        if not self._collapsed:
            self._expanded_width = cur_geom.width()
            self._expanded_height = cur_geom.height()
            target_w = 160
            target_h = self.TITLE_BAR_H
            self.btn_door.setText("▲")
            self.btn_door.setToolTip("Expandir / Restaurar tamaño")
            self.container_layout.setContentsMargins(6, 2, 6, 2)
            self._title_bar_widget.setFixedHeight(20)
            self._collapsed = True
            self._content_wrapper.hide()
            self._div.hide()
            if hasattr(self, "_bottom_bar"):
                self._bottom_bar.hide()
        else:
            target_w = getattr(self, "_expanded_width", 370)
            target_h = self._expanded_height
            self.btn_door.setText("▼")
            self.btn_door.setToolTip("Minimizar / Reducir tamaño")
            self.container_layout.setContentsMargins(8, 6, 8, 6)
            self._title_bar_widget.setFixedHeight(22)
            self._collapsed = False
            self._content_wrapper.show()
            self._div.show()
            if hasattr(self, "_bottom_bar"):
                self._bottom_bar.show()

        target_geom = QRect(cur_geom.x(), cur_geom.y(), target_w, target_h)
        self._anim.stop()
        self._anim.setStartValue(cur_geom)
        self._anim.setEndValue(target_geom)
        self._anim.start()

    def toggle_always_on_top(self):
        is_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, not is_top)
        self.show()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #E2E8F0;
                border: 1px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: #E2E8F0;
                padding: 6px 14px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF !important;
                font-weight: bold;
            }}
            QMenu::item:disabled {{
                color: #64748B !important;
            }}
        """)
        
        is_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        act_pin_top = menu.addAction("📌 Fijar en primer plano (Always on Top)" if not is_top else "📍 Desfijar primer plano")
        act_door = menu.addAction("▲ Colapsar (Modo Puerta)" if not self._collapsed else "▼ Expandir")
        menu.addSeparator()
        act_redock = menu.addAction(f"✕ Desanclar '{self.parent_drawer.get_widget_display_name(self.key)}'")
        act_unpin_all = menu.addAction("🗑️ Desanclar todos los widgets del escritorio")

        chosen = menu.exec(event.globalPos())
        if chosen == act_pin_top:
            self.toggle_always_on_top()
        elif chosen == act_door:
            self.toggle_door()
        elif chosen == act_redock:
            self.close_and_redock()
        elif chosen == act_unpin_all:
            if hasattr(self.parent_drawer, "desanclar_todos_los_widgets"):
                self.parent_drawer.desanclar_todos_los_widgets()
            elif hasattr(self.parent_drawer, "parent_tab") and hasattr(self.parent_drawer.parent_tab, "desfijar_todos"):
                self.parent_drawer.parent_tab.desfijar_todos()

    def close_and_redock(self):
        if self._is_closing:
            return
        self._is_closing = True
        self.hide()
        if hasattr(self.parent_drawer, "redock_widget"):
            self.parent_drawer.redock_widget(self.key)
        self.close()

    def closeEvent(self, event):
        if not self._is_closing:
            self._is_closing = True
            self.hide()
            if hasattr(self.parent_drawer, "redock_widget"):
                self.parent_drawer.redock_widget(self.key)
        super().closeEvent(event)


class FloatingWidgetPanel(QWidget):
    """
    Panel de botón / lanzador flotante acoplable en el borde de la pantalla.
    Soporta la opción de mantenerse visible en 2º plano sobre otras ventanas de Windows.
    """
    def __init__(self, parent_tab, colores, config):
        super().__init__()
        self.parent_tab = parent_tab
        self.colores = colores
        self.config = config
        self.siempre_visible_top = self.config.get("siempre_visible_top", True)

        self._apply_window_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_ui()
        self.drag_position = QPoint()

    def _apply_window_flags(self):
        """Aplica o remueve la bandera WindowStaysOnTopHint según la configuración de 2º plano"""
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.siempre_visible_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn_floating = QPushButton("🧩")
        self.btn_floating.setFixedSize(48, 48)
        self.btn_floating.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_floating.setToolTip("Multitool Widgets\nClic derecho: Opciones de visibilidad en 2º plano")
        self.btn_floating.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 2px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 24px;
                font-size: 22px;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.btn_floating.clicked.connect(self._on_clicked)
        self.btn_floating.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_floating.customContextMenuRequested.connect(self.mostrar_menu_contextual)

        layout.addWidget(self.btn_floating)
        self.setFixedSize(54, 54)

    def mostrar_menu_contextual(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #E2E8F0;
                border: 1px solid {self.colores.get('bg_terciario', '#2A2A3C')};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: #E2E8F0;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF !important;
                font-weight: bold;
            }}
            QMenu::item:disabled {{
                color: #64748B !important;
            }}
            QMenu::indicator {{
                width: 14px;
                height: 14px;
                margin-left: 6px;
            }}
            QMenu::indicator:checked {{
                background-color: {self.colores.get('acento', '#6366F1')};
                border: 1px solid #818CF8;
                border-radius: 3px;
            }}
            QMenu::indicator:unchecked {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
            }}
        """)

        act_top = QAction("👁️ Mantener visible sobre otras ventanas (2º plano)", self)
        act_top.setCheckable(True)
        act_top.setChecked(self.siempre_visible_top)
        act_top.triggered.connect(self.toggle_siempre_visible)
        menu.addAction(act_top)

        menu.addSeparator()
        act_center = QAction("📍 Centrar en pantalla", self)
        act_center.triggered.connect(self.centrar_en_pantalla)
        menu.addAction(act_center)

        menu.exec(self.btn_floating.mapToGlobal(pos))

    def toggle_siempre_visible(self, checked):
        self.siempre_visible_top = checked
        self.config["siempre_visible_top"] = checked
        if hasattr(self.parent_tab, "guardar_configuracion"):
            self.parent_tab.guardar_configuracion()

        # Re-aplicar banderas de ventana en caliente
        self.hide()
        self._apply_window_flags()
        self.show()

    def centrar_en_pantalla(self):
        screen = get_screen_geometry()
        self.move(screen.center() - QPoint(27, 27))

    def _on_clicked(self):
        if hasattr(self.parent_tab, "toggle_floating_menu"):
            self.parent_tab.toggle_floating_menu()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            new_pos = calculate_dock_position(self.pos(), self.width(), self.height())
            self.move(new_pos)
            self.config["posicion_x"] = new_pos.x()
            self.config["posicion_y"] = new_pos.y()
            if hasattr(self.parent_tab, "guardar_configuracion"):
                self.parent_tab.guardar_configuracion()
            event.accept()
