"""
floating_dock.py - Controlador circular de escritorio y cajón flotante de widgets
Contiene DockedCircleWidget, FloatingWidgetCoordinator y FloatingWidgetWindow.
"""
import os
import sys
import json
import math
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QStackedWidget, QLineEdit, QApplication, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt6.QtGui import (
    QFont, QIcon, QColor, QPainter, QPen, QBrush, QCursor, QRegion, QPixmap
)

from .quick_widgets import (
    QuickNotesWidget, QuickCalculatorWidget, QuickCommandWidget,
    QuickBrowserWidget, QuickSecurityWidget, QuickFilesWidget,
    QuickCalendarWidget, QuickSystemWidget, QuickPlayerWidget,
    QuickRecorderWidget, QuickNotebookWidget, QuickChatWidget,
    QuickExtrasWidget, QuickMiniGamesWidget, QuickTimeWidget,
    QuickTranslatorWidget, GenericModuleWidget
)
from .new_widgets import (
    QuickStickyNotesWidget, QuickLauncherWidget, QuickSystemHUDWidget
)
from .center_views import CenteredWidgetWindow
from .floating_panel import DesktopWidgetWindow


class DockedCircleWidget(QWidget):
    """Círculo central y anillo exterior interactivo dibujado con QPainter"""
    def __init__(self, parent_window, context, colors):
        super().__init__(parent_window)
        self.win = parent_window
        self.context = context
        self.colores = colors
        self.setMouseTracking(True)
        
        icon_path = Path(__file__).resolve().parent.parent.parent.parent / "utils" / "icono.ico"
        self.app_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
        self.icon_pixmap = self.app_icon.pixmap(48, 48) if not self.app_icon.isNull() else QPixmap()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.win.state == "selector":
            painter.fillRect(self.rect(), QColor(10, 10, 15, 180))
            
        w = self.width()
        h = self.height()
        cx = w 
        cy = h // 2 
        
        if self.win.state == "minimized":
            painter.setBrush(QColor(self.colores.get("bg_secundario", "#1E1E2E")))
            painter.setPen(QPen(QColor(self.colores.get("bg_terciario", "#2D2D3D")), 2))
            painter.drawEllipse(cx - 40, cy - 40, 80, 80)
            
            if not self.icon_pixmap.isNull():
                painter.drawPixmap(cx - 24, cy - 24, self.icon_pixmap)
            else:
                painter.setPen(QColor("white"))
                painter.drawText(QRect(cx - 40, cy - 40, 80, 80), Qt.AlignmentFlag.AlignCenter, "🛠️")
            return
            
        N = len(self.win.active_keys)
        if N == 0:
            return
            
        for offset in [-1, 0, 1]:
            center_angle = 180 - offset * 50
            span = 40
            start_angle = center_angle - span / 2
            
            start_angle_16 = int(start_angle * 16)
            span_angle_16 = int(span * 16)
            
            if offset == 0:
                pen = QPen(QColor(self.colores.get("acento", "#6366F1")), 20)
            else:
                pen = QPen(QColor(self.colores.get("bg_terciario", "#2D2D3D")), 16)
                
            painter.setPen(pen)
            painter.drawArc(cx - 65, cy - 65, 130, 130, start_angle_16, span_angle_16)
            
        painter.setBrush(QColor(self.colores.get("bg_secundario", "#1E1E2E")))
        painter.setPen(QPen(QColor(self.colores.get("bg_terciario", "#2D2D3D")), 2))
        painter.drawEllipse(cx - 40, cy - 40, 80, 80)
        
        if not self.icon_pixmap.isNull():
            painter.drawPixmap(cx - 24, cy - 24, self.icon_pixmap)
        else:
            painter.setPen(QColor("white"))
            painter.drawText(QRect(cx - 40, cy - 40, 80, 80), Qt.AlignmentFlag.AlignCenter, "🛠️")
            
        active_key = self.win.active_keys[self.win.active_index % N]
        active_name = self.win.get_widget_display_name(active_key)
        
        prev_key = self.win.active_keys[(self.win.active_index - 1) % N]
        prev_name = self.win.get_widget_display_name(prev_key)
        
        next_key = self.win.active_keys[(self.win.active_index + 1) % N]
        next_name = self.win.get_widget_display_name(next_key)
        
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.setPen(QColor("white"))
        painter.drawText(QRect(cx - 220, cy - 20, 140, 40), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, active_name)
        
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor(255, 255, 255, 120))
        painter.drawText(QRect(cx - 220, cy - 65, 140, 30), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, prev_name)
        painter.drawText(QRect(cx - 220, cy + 35, 140, 30), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, next_name)

    def wheelEvent(self, event):
        N = len(self.win.active_keys)
        if N <= 1:
            return
            
        delta = event.angleDelta().y()
        if delta > 0:
            self.win.active_index = (self.win.active_index - 1) % N
        elif delta < 0:
            self.win.active_index = (self.win.active_index + 1) % N
            
        self.update()
        
    def mousePressEvent(self, event):
        pos = event.position()
        w = self.width()
        h = self.height()
        cx = w
        cy = h // 2
        dx = pos.x() - cx
        dy = cy - pos.y()
        d = math.sqrt(dx * dx + dy * dy)
        
        if event.button() == Qt.MouseButton.RightButton:
            menu = QMenu(self)
            menu.setStyleSheet(f"""
                QMenu {{
                    background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                    color: #E2E8F0;
                    border: 1px solid {self.colores.get('acento', '#6366F1')};
                    border-radius: 8px;
                    padding: 6px;
                }}
                QMenu::item {{
                    background-color: transparent;
                    color: #E2E8F0;
                    padding: 8px 22px 8px 14px;
                    border-radius: 5px;
                    font-size: 9.5pt;
                }}
                QMenu::item:selected {{
                    background-color: {self.colores.get('acento', '#6366F1')};
                    color: #FFFFFF !important;
                    font-weight: bold;
                }}
                QMenu::separator {{
                    height: 1px;
                    background: rgba(255, 255, 255, 0.08);
                    margin: 4px 6px;
                }}
            """)
            action_pin_all = menu.addAction("📌 Vincular todos los widgets")
            action_unpin_all = menu.addAction("🗑️ Desvincular todos los widgets")
            menu.addSeparator()
            action_exit = menu.addAction("🚪 Salir por completo")
            
            res = menu.exec(QCursor.pos())
            if res == action_pin_all:
                self.win.vincular_todos_los_widgets()
            elif res == action_unpin_all:
                self.win.desfijar_todos_los_widgets()
            elif res == action_exit:
                self.win.salir_por_completo()
            return

        if self.win.state == "minimized":
            if d <= 60:
                self.win.expand_to_selector()
            return
            
        if self.win.state == "selector":
            if d <= 40:
                self.win.restaurar_app_principal()
            elif 40 < d <= 100:
                angle_rad = math.atan2(dy, dx)
                angle_deg = math.degrees(angle_rad)
                if angle_deg < 0:
                    angle_deg += 360
                
                N = len(self.win.active_keys)
                if N > 0:
                    if 105 <= angle_deg <= 155:
                        self.win.active_index = (self.win.active_index - 1) % N
                        self.update()
                    elif 205 <= angle_deg <= 255:
                        self.win.active_index = (self.win.active_index + 1) % N
                        self.update()
                    elif 155 < angle_deg < 205:
                        active_key = self.win.active_keys[self.win.active_index % N]
                        self.win.abrir_widget_centro(active_key)
            else:
                self.win.collapse_to_minimized()


class FloatingWidgetCoordinator:
    """Coordinador global de widgets flotantes para evitar conflictos y superposiciones entre múltiples cuentas"""
    _active_widget = None
    _active_user = None

    @classmethod
    def request_display(cls, user_name: str, widget_instance, parent_window=None) -> bool:
        if cls._active_widget == widget_instance:
            return True
        if cls._active_widget is not None and cls._active_widget.isVisible() and cls._active_user and cls._active_user != user_name:
            resp = QMessageBox.question(
                parent_window or widget_instance,
                "👥 Conflicto de Widgets de Escritorio",
                f"Se detectó que la cuenta '{cls._active_user}' ya tiene su widget flotante activo en pantalla.\n\n"
                f"¿Deseas activar el widget de la cuenta actual '{user_name}' y ocultar el anterior?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.Yes:
                try:
                    cls._active_widget.hide()
                except Exception:
                    pass
                cls._active_widget = widget_instance
                cls._active_user = user_name
                return True
            else:
                return False
        cls._active_widget = widget_instance
        cls._active_user = user_name
        return True

    @classmethod
    def unregister(cls, widget_instance):
        if cls._active_widget == widget_instance:
            cls._active_widget = None
            cls._active_user = None


class FloatingWidgetWindow(QWidget):
    """Ventana flotante interactiva y animada de escritorio (Selector circular y ventanas centradas)"""
    def __init__(self, context, controller, parent=None):
        super().__init__(parent)
        self.context = context
        self.controller = controller
        
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1"
        })

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.state = "minimized"
        self.setMinimumSize(44, 84)
        self.setMaximumSize(44, 84)

        self.active_index = 0
        self.active_keys = []
        self.pinned_windows = {}
        self.center_windows = {}
        self.auto_pinned_key = None

        # Fábricas especializadas para módulos con mini-widgets optimizados
        self.specialized_factories = {
            "notes": lambda ctx: QuickNotesWidget(ctx),
            "notas": lambda ctx: QuickNotesWidget(ctx),
            "postits": lambda ctx: QuickStickyNotesWidget(ctx),
            "calc": lambda ctx: QuickCalculatorWidget(ctx),
            "calculadora": lambda ctx: QuickCalculatorWidget(ctx),
            "terminal": lambda ctx: QuickCommandWidget(ctx),
            "navegador": lambda ctx: QuickBrowserWidget(ctx),
            "launcher": lambda ctx: QuickLauncherWidget(ctx),
            "seguridad": lambda ctx: QuickSecurityWidget(ctx),
            "archivos": lambda ctx: QuickFilesWidget(ctx),
            "calendario": lambda ctx: QuickCalendarWidget(ctx),
            "sistema": lambda ctx: QuickSystemWidget(ctx),
            "syshud": lambda ctx: QuickSystemHUDWidget(ctx),
            "reproductor": lambda ctx: QuickPlayerWidget(ctx),
            "grabadora": lambda ctx: QuickRecorderWidget(ctx),
            "cuaderno": lambda ctx: QuickNotebookWidget(ctx),
            "chat": lambda ctx: QuickChatWidget(ctx),
            "extras": lambda ctx: QuickExtrasWidget(ctx),
            "minigames": lambda ctx: QuickMiniGamesWidget(ctx),
            "tiempo": lambda ctx: QuickTimeWidget(ctx),
            "traductor": lambda ctx: QuickTranslatorWidget(ctx),
        }

        self.discovered_modules = {}
        self.update_discovered_modules()
        self.config_widgets = self.controller.config.get("widgets", {})
        self.update_active_keys()

        self.widgets = {}
        self.init_ui()
        
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self.on_animation_finished)

    def update_discovered_modules(self):
        """Descubre directamente todos los módulos de la carpeta vistas/modulos/."""
        self.discovered_modules = {}
        try:
            from vistas.configurations import discover_modules_and_plugins
            ruta_usuario = getattr(self.context, "ruta_usuario", None)
            modules = discover_modules_and_plugins(ruta_usuario)
            for m in modules:
                m_name = m.get("name", "")
                m_folder = m.get("folder", m_name.lower())
                if m_folder.lower() == "widgets" or m_name.lower() == "widgets":
                    continue
                key = m_folder.lower()
                self.discovered_modules[key] = m
        except Exception as e:
            print(f"[FloatingWidgetWindow] Error descubriendo módulos: {e}")

    def update_active_keys(self):
        """Actualiza la lista de claves activas en función de los módulos detectados y la configuración."""
        self.active_keys = []
        if not hasattr(self, "discovered_modules") or not self.discovered_modules:
            self.update_discovered_modules()

        for key in self.discovered_modules.keys():
            if self.config_widgets.get(key, True):
                self.active_keys.append(key)

        for special_key in ["postits", "launcher", "syshud"]:
            if self.config_widgets.get(special_key, True) and special_key not in self.active_keys:
                self.active_keys.append(special_key)

        if not self.active_keys:
            if self.discovered_modules:
                self.active_keys = [list(self.discovered_modules.keys())[0]]
            else:
                self.active_keys = ["notes"]

    def get_widget_display_name(self, key):
        """Obtiene el nombre de visualización dinámicamente desde la metadata del módulo."""
        if hasattr(self, "discovered_modules") and key in self.discovered_modules:
            return self.discovered_modules[key].get("name", key).upper()
        names = {
            "notes": "NOTAS", "postits": "NOTAS ADHESIVAS", "calc": "CALCULADORA", "terminal": "TERMINAL",
            "navegador": "NAVEGADOR", "launcher": "LANZADOR RÁPIDO", "seguridad": "SEGURIDAD", "archivos": "ARCHIVOS",
            "calendario": "CALENDARIO", "sistema": "SISTEMA", "syshud": "HUD SISTEMA", "reproductor": "REPRODUCTOR",
            "grabadora": "GRABADORA", "cuaderno": "CUADERNO", "chat": "CHAT",
            "extras": "EXTRAS", "minigames": "MINIGAMES", "tiempo": "TIEMPO", "traductor": "TRADUCTOR"
        }
        return names.get(key, key.upper())

    def obtener_o_crear_widget(self, key):
        """Retorna la instancia del widget, creándola dinámicamente bajo demanda si aún no existe."""
        if not isinstance(key, str):
            key = str(key) if key is not None else ""
        if not key:
            return None

        if key in self.widgets:
            return self.widgets[key]

        display_name = self.get_widget_display_name(key)

        # 1. Si existe factory especializado y la clave coincide
        factory = self.specialized_factories.get(key.lower())
        if factory:
            try:
                w = factory(self.context)
                self.widgets[key] = w
                if self.drawer_stack.indexOf(w) == -1:
                    self.drawer_stack.addWidget(w)
                return w
            except Exception as e:
                print(f"[FloatingWidgetWindow] Error creando widget especializado para {key}: {e}")

        # 2. Si es un módulo descubierto dinámicamente
        mod_info = self.discovered_modules.get(key.lower())
        if not mod_info:
            for k, m in self.discovered_modules.items():
                if k.lower() == key.lower():
                    mod_info = m
                    break

        if mod_info:
            try:
                w = GenericModuleWidget(key, display_name, self.context, mod_info)
                self.widgets[key] = w
                if self.drawer_stack.indexOf(w) == -1:
                    self.drawer_stack.addWidget(w)
                return w
            except Exception as e:
                print(f"[FloatingWidgetWindow] Error creando GenericModuleWidget para {key}: {e}")

        return None

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetNoConstraint)

        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        self.docked_page = DockedCircleWidget(self, self.context, self.colores)
        self.stack.addWidget(self.docked_page)

        self.expanded_page = QFrame()
        self.expanded_page.setObjectName("DrawerFrame")
        self.expanded_page.setStyleSheet(f"""
            QFrame#DrawerFrame {{
                background-color: rgba(18, 18, 24, 0.95);
                border: 2px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 12px;
            }}
        """)
        
        drawer_layout = QVBoxLayout(self.expanded_page)
        drawer_layout.setContentsMargins(10, 10, 10, 10)
        drawer_layout.setSpacing(6)

        title_bar = QHBoxLayout()
        self.lbl_drawer_title = QLabel("🛠️ WIDGET")
        self.lbl_drawer_title.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        
        btn_collapse = QPushButton("»")
        btn_collapse.setFixedSize(20, 20)
        btn_collapse.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                font-weight: bold;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{ color: {self.colores.get('acento', '#6366F1')}; }}
        """)
        btn_collapse.clicked.connect(self.collapse_to_minimized)

        title_bar.addWidget(self.lbl_drawer_title)
        title_bar.addStretch()
        title_bar.addWidget(btn_collapse)
        drawer_layout.addLayout(title_bar)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #2D2D3D; max-height: 1px;")
        drawer_layout.addWidget(line)

        self.drawer_stack = QStackedWidget()
        self.drawer_stack.setStyleSheet("background: transparent;")
        drawer_layout.addWidget(self.drawer_stack)
        self.stack.addWidget(self.expanded_page)

    def apply_widgets_visibility(self, config_widgets):
        self.config_widgets = config_widgets
        self.update_active_keys()
        if hasattr(self, "docked_page"):
            self.docked_page.update()

    def abrir_widget_centro(self, key):
        if key in self.pinned_windows:
            self.pinned_windows[key].raise_()
            self.pinned_windows[key].activateWindow()
            return

        if not isinstance(key, str):
            key = str(key) if key is not None and not isinstance(key, bool) else ""
        if not key:
            return

        if key in self.center_windows:
            self.center_windows[key].animate_close()
            return

        for k, win in list(self.center_windows.items()):
            win.close()

        widget = self.obtener_o_crear_widget(key)
        if not widget:
            return

        if self.drawer_stack.indexOf(widget) != -1:
            self.drawer_stack.removeWidget(widget)

        win = CenteredWidgetWindow(key, widget, self)
        self.center_windows[key] = win
        if hasattr(win, "show_centered"):
            win.show_centered()
        elif hasattr(win, "animate_open"):
            win.animate_open()
        else:
            win.show()

    def pin_widget_from_center(self, key):
        if key in self.pinned_windows:
            return
            
        center_win = self.center_windows.pop(key, None)
        if center_win:
            widget = getattr(center_win, "widget", None)
            if hasattr(center_win, "take_widget"):
                widget = center_win.take_widget() or widget
            elif hasattr(center_win, "container_layout") and center_win.container_layout:
                if widget:
                    center_win.container_layout.removeWidget(widget)
            elif hasattr(center_win, "container") and center_win.container.layout():
                if widget:
                    center_win.container.layout().removeWidget(widget)
            if widget:
                widget.setParent(None)
            center_win.close()
        else:
            widget = self.obtener_o_crear_widget(key)
            if not widget:
                return
            if self.drawer_stack.indexOf(widget) != -1:
                self.drawer_stack.removeWidget(widget)
                
        widget.is_pinned = True
        widget.header.show()
        widget.div.show()
        widget.btn_pin.setText("📍")
        widget.btn_pin.setToolTip("Desfijar y re-acoplar")
        
        desktop_win = DesktopWidgetWindow(key, widget, self)
        cursor_pos = QCursor.pos()
        desktop_win.move(max(50, cursor_pos.x() - 150), max(50, cursor_pos.y() - 100))
        
        self.pinned_windows[key] = desktop_win
        desktop_win.show()
        
        if hasattr(widget, "on_pinned"):
            widget.on_pinned()
            
        self.collapse_to_minimized()

    def pin_widget(self, key):
        self.pin_widget_from_center(key)

    def redock_widget(self, key):
        if key not in self.pinned_windows:
            return
        desktop_win = self.pinned_windows.pop(key)
        widget = self.obtener_o_crear_widget(key)
        if not widget:
            return
            
        widget.is_pinned = False
        widget.btn_pin.setText("📌")
        widget.btn_pin.setToolTip("Fijar al escritorio")
        
        widget.header.hide()
        widget.div.hide()
        
        self.drawer_stack.addWidget(widget)
        
        if not getattr(desktop_win, "_is_closing", False):
            desktop_win._is_closing = True
            desktop_win.close()
        
        if hasattr(widget, "on_redocked"):
            widget.on_redocked()

    def vincular_todos_los_widgets(self):
        """Vincula/fija todas las ventanas de widgets activas directamente al escritorio."""
        for k in self.active_keys:
            if k not in self.pinned_windows:
                self.pin_widget(k)

    def desfijar_todos_los_widgets(self):
        """Desfija todas las ventanas de widgets y oculta todas las notas adhesivas flotantes del escritorio"""
        keys_pinned = list(self.pinned_windows.keys())
        for k in keys_pinned:
            self.redock_widget(k)
        
        quick_postits = self.widgets.get("postits")
        if quick_postits and hasattr(quick_postits, "floating_notes"):
            for w in list(quick_postits.floating_notes.values()):
                try:
                    w.close()
                except Exception:
                    pass
            quick_postits.floating_notes.clear()

    def salir_por_completo(self):
        """Cierra completamente los widgets y la aplicación principal"""
        FloatingWidgetCoordinator.unregister(self)
        try:
            self.close()
        except Exception:
            pass
        app = getattr(self.context, "app", None)
        if app and hasattr(app, "close"):
            try:
                app.close()
            except Exception:
                pass
        qapp = QApplication.instance()
        if qapp:
            qapp.quit()

    def keyPressEvent(self, event):
        if self.state == "selector" and event.key() == Qt.Key.Key_T:
            self.mostrar_buscador_rapido()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            if hasattr(self, "search_bar") and self.search_bar.isVisible():
                self.ocultar_buscador_rapido()
            else:
                self.collapse_to_minimized()
            event.accept()
        else:
            super().keyPressEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self.center_windows:
            return
        if self.geometry().contains(QCursor.pos()):
            return
        self.collapse_to_minimized()

    def closeEvent(self, event):
        for win in list(self.center_windows.values()):
            try:
                win.close()
            except Exception:
                pass
        for win in list(self.pinned_windows.values()):
            try:
                win.close()
            except Exception:
                pass
        super().closeEvent(event)

    def expand_to_selector(self):
        if self.state == "selector" or self.state == "expanded":
            return
        self.state = "selector"
        self.clearMask()
        
        screen = QApplication.primaryScreen().geometry()
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.setGeometry(screen)
        
        self.docked_page.update()
        self.activateWindow()
        self.setFocus()

    def expand(self):
        active_key = self.active_keys[self.active_index % len(self.active_keys)]
        self.abrir_widget_centro(active_key)

    def collapse(self):
        self.collapse_to_minimized()

    def collapse_to_minimized(self):
        if self.state == "minimized":
            return
            
        self.ocultar_buscador_rapido()
            
        p_widget = self.widgets.get("reproductor")
        if p_widget and p_widget.is_playing() and not p_widget.is_pinned:
            self.pin_widget_from_center("reproductor")
            self.auto_pinned_key = "reproductor"

        keys_to_close = list(self.center_windows.keys())
        for key in keys_to_close:
            if key == "reproductor" and self.auto_pinned_key == "reproductor":
                continue
            win = self.center_windows.get(key)
            if win:
                win.animate_close()

        self.state = "minimized"
        self.stack.setCurrentIndex(0)
        
        screen = QApplication.primaryScreen().geometry()
        cw, ch = 44, 84
        cx = screen.width() - cw
        cy = (screen.height() - ch) // 2
        
        self.setMinimumSize(0, 0)
        self.setMaximumSize(300, 240)
        self.setGeometry(cx, cy, cw, ch)
        self.setMinimumSize(cw, ch)
        self.setMaximumSize(cw, ch)
        self.setMask(QRegion(4, 2, 80, 80, QRegion.RegionType.Ellipse))
        
        self.docked_page.update()

    def on_animation_finished(self):
        if self.state == "minimized":
            self.setMinimumSize(44, 84)
            self.setMaximumSize(44, 84)
            self.setMask(QRegion(4, 2, 80, 80, QRegion.RegionType.Ellipse))
            self.docked_page.update()
        elif self.state == "selector":
            self.clearMask()
            self.docked_page.update()

    def restaurar_app_principal(self):
        self.ocultar_buscador_rapido()
        main_win = self.context.app
        main_win.showNormal()
        main_win.raise_()
        main_win.activateWindow()
        if hasattr(main_win, "_aplicar_modo_oscuro_windows"):
            main_win._aplicar_modo_oscuro_windows()

    def mostrar_buscador_rapido(self):
        if not hasattr(self, "search_bar"):
            self.search_bar = QLineEdit(self)
            self.search_bar.setPlaceholderText("🔍 Buscar módulo... (ej: notas, calc) + Enter")
            self.search_bar.setStyleSheet(f"""
                QLineEdit {{
                    background-color: rgba(18, 18, 24, 0.95);
                    color: white;
                    border: 2px solid {self.colores.get('acento', '#6366F1')};
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-family: 'Segoe UI';
                }}
            """)
            self.search_bar.textChanged.connect(self.filtrar_widgets_busqueda)
            self.search_bar.returnPressed.connect(self.ejecutar_seleccion_busqueda)
            self.search_bar.keyPressEvent = self.search_bar_key_press

        w, h = 320, 36
        screen_geom = self.geometry()
        x = (screen_geom.width() - w) // 2
        y = screen_geom.height() // 6
        self.search_bar.setGeometry(x, y, w, h)
        
        self.search_bar.clear()
        self.search_bar.show()
        self.search_bar.setFocus()

    def ocultar_buscador_rapido(self):
        if hasattr(self, "search_bar") and self.search_bar.isVisible():
            self.search_bar.hide()
            self.setFocus()

    def search_bar_key_press(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.ocultar_buscador_rapido()
            event.accept()
        else:
            QLineEdit.keyPressEvent(self.search_bar, event)

    def filtrar_widgets_busqueda(self, text):
        query = text.strip().lower()
        if not query:
            return
        for i, key in enumerate(self.active_keys):
            name = self.get_widget_display_name(key).lower()
            if query in name or query in key.lower():
                self.active_index = i
                if hasattr(self, "docked_page"):
                    self.docked_page.update()
                break

    def ejecutar_seleccion_busqueda(self):
        self.ocultar_buscador_rapido()
        active_key = self.active_keys[self.active_index % len(self.active_keys)]
        self.abrir_widget_centro(active_key)
