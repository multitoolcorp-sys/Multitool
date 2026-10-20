"""
quick_widgets.py - Mini-widgets especializados y clases base para MultiTool Widgets
Contiene QuickWidgetBase, QuickExtraToolWindow, GenericModuleWidget y todos los Quick*Widgets especializados.
"""
import os
import sys
import json
import math
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QSizeGrip, QTabWidget, QGridLayout
)
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QFont, QColor, QCursor


class QuickExtraToolWindow(QWidget):
    """Ventana independiente para un submódulo de extras"""
    def __init__(self, title, widget_class, context, colores, size=(500, 400)):
        super().__init__()
        self.setWindowTitle(title)
        self.colores = colores
        self.context = context
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.drag_position = QPoint()
        self.init_ui(widget_class)
        self.resize(*size)
        
    def init_ui(self, widget_class):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(18, 18, 24, 0.98);
                border: 2px solid {self.colores['acento']};
                border-radius: 12px;
            }}
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(6)
        
        # Barra de título superior
        title_bar = QHBoxLayout()
        lbl_title = QLabel(self.windowTitle())
        lbl_title.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(18, 18)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #AAB0B8;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { color: #F87171; }
        """)
        btn_close.clicked.connect(self.close)
        
        title_bar.addWidget(lbl_title)
        title_bar.addStretch()
        title_bar.addWidget(btn_close)
        container_layout.addLayout(title_bar)
        
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; max-height: 1px; border: none;")
        container_layout.addWidget(div)
        
        try:
            if widget_class.__name__ in ["KanbanGUI", "PizarraGUI"]:
                self.sub_widget = widget_class(self, self.context, self.colores)
            else:
                self.sub_widget = widget_class(self, self.colores, self.context.ruta_usuario)
        except Exception:
            self.sub_widget = widget_class(self)
            
        self.sub_widget.setAutoFillBackground(True)
        palette = self.sub_widget.palette()
        palette.setColor(self.sub_widget.backgroundRole(), QColor(self.colores['bg_principal']))
        self.sub_widget.setPalette(palette)
        
        container_layout.addWidget(self.sub_widget)
        
        grip_layout = QHBoxLayout()
        grip_layout.setContentsMargins(0, 0, 0, 0)
        grip_layout.addStretch()
        sizegrip = QSizeGrip(self)
        sizegrip.setStyleSheet("QSizeGrip { width: 14px; height: 14px; }")
        grip_layout.addWidget(sizegrip)
        container_layout.addLayout(grip_layout)
        
        layout.addWidget(container)
        
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


class QuickWidgetBase(QFrame):
    """Clase base para todos los widgets con soporte para anclaje"""
    def __init__(self, key, display_name, context, parent=None):
        super().__init__(parent)
        self.key = key
        self.display_name = display_name
        self.context = context
        self.is_pinned = False
        
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "error": "#F87171", "exito": "#34D399"
        })
        
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(self.colores['bg_principal']))
        self.setPalette(palette)
        
        self.setObjectName("BaseWidget")
        self.setStyleSheet(f"""
            #BaseWidget {{
                background-color: {self.colores['bg_principal']};
                border: none;
            }}
        """)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.init_base_ui()

    def init_base_ui(self):
        self.base_layout = QVBoxLayout(self)
        self.base_layout.setContentsMargins(10, 10, 10, 10)
        self.base_layout.setSpacing(6)
        
        # Cabecera
        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        
        self.lbl_title = QLabel(self.display_name)
        self.lbl_title.setStyleSheet(f"color: {self.colores['acento']}; font-weight: bold; font-size: 13px;")
        header_layout.addWidget(self.lbl_title)
        
        header_layout.addStretch()
        
        # Botón Pin
        self.btn_pin = QPushButton("📌")
        self.btn_pin.setToolTip("Fijar al escritorio")
        self.btn_pin.setFixedSize(22, 22)
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores['fg_secundario']};
                border: none;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: white;
            }}
        """)
        self.btn_pin.clicked.connect(self.toggle_pin)
        header_layout.addWidget(self.btn_pin)
        
        self.base_layout.addWidget(self.header)
        
        self.div = QFrame()
        self.div.setFrameShape(QFrame.Shape.HLine)
        self.div.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; max-height: 1px; border: none;")
        self.base_layout.addWidget(self.div)
        
        self.container = QWidget()
        self.layout_contenido = QVBoxLayout(self.container)
        self.layout_contenido.setContentsMargins(0, 4, 0, 0)
        self.layout_contenido.setSpacing(6)
        self.base_layout.addWidget(self.container)

    def toggle_pin(self):
        p = self.parent()
        while p:
            if hasattr(p, "pin_widget") and hasattr(p, "redock_widget"):
                if self.is_pinned:
                    p.redock_widget(self.key)
                else:
                    p.pin_widget(self.key)
                return
            if hasattr(p, "parent_drawer"):
                drawer = getattr(p, "parent_drawer")
                if drawer and hasattr(drawer, "pin_widget") and hasattr(drawer, "redock_widget"):
                    if self.is_pinned:
                        drawer.redock_widget(self.key)
                    else:
                        drawer.pin_widget(self.key)
                    return
            p = p.parent()


class GenericModuleWidget(QuickWidgetBase):
    """
    Widget genérico y 100% modular que aloja directamente cualquier módulo de MultiTool
    descubierto en vistas/modulos/, utilizando DynamicModuleContainer.
    """
    def __init__(self, key, display_name, context, module_info, parent=None):
        self.module_info = module_info
        super().__init__(key, display_name, context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        self._instanciar_modulo_dinamico()

    def _instanciar_modulo_dinamico(self):
        try:
            from vistas.configurations import DynamicModuleContainer
            submodules = self.module_info.get("submodules", [])
            self._container = DynamicModuleContainer(
                self, self.context, self.display_name, submodules, self.colores
            )
            self.layout_contenido.addWidget(self._container)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando módulo '{self.display_name}':\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 11px; padding: 12px; background: transparent;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickNotesWidget(QuickWidgetBase):
    """Carga el módulo completo de Notas dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("notes", "📝 NOTAS", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.notas.notas import TabNotas
            self._real = TabNotas(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Notas:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickCalculatorWidget(QuickWidgetBase):
    """Carga el módulo completo de Calculadora dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("calc", "🧮 CALCULADORA", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.calculadora.calculadora import TabCalculadora
            self._real = TabCalculadora(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Calculadora:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickCommandWidget(QuickWidgetBase):
    """Carga el módulo completo de Terminal dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("terminal", "⌨️ TERMINAL", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.terminal.terminal_main import TabTerminal
            self._real = TabTerminal(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Terminal:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickBrowserWidget(QuickWidgetBase):
    """Carga el módulo completo de Navegador dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("navegador", "🌐 NAVEGADOR", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.navegador.navegador import TabNavegador
            self._real = TabNavegador(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Navegador:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickSecurityWidget(QuickWidgetBase):
    """Carga el módulo completo de Seguridad dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("seguridad", "🔒 SEGURIDAD", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.seguridad.seguridad_main import TabSeguridad
            self._real = TabSeguridad(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Seguridad:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickFilesWidget(QuickWidgetBase):
    """Carga el módulo completo de Archivos dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("archivos", "📁 ARCHIVOS", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.archivos.archivos import TabArchivos
            self._real = TabArchivos(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Archivos:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickCalendarWidget(QuickWidgetBase):
    """Carga el módulo completo de Calendario dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("calendario", "📅 CALENDARIO", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.calendario.calendario import TabCalendario
            self._real = TabCalendario(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Calendario:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickSystemWidget(QuickWidgetBase):
    """Carga el módulo completo de Sistema dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("sistema", "💻 SISTEMA", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.sistema.sistema import TabSistema
            self._real = TabSistema(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Sistema:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickPlayerWidget(QuickWidgetBase):
    """Carga el módulo completo de Reproductor dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("reproductor", "▶️ REPRODUCTOR", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        self._media_player = None
        try:
            from vistas.modulos.reproductor.reproductor import TabReproductor
            self._real = TabReproductor(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Reproductor:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)

    def is_playing(self):
        try:
            if hasattr(self, '_real') and hasattr(self._real, 'is_playing'):
                return self._real.is_playing()
        except Exception:
            pass
        return False


class QuickRecorderWidget(QuickWidgetBase):
    """Carga el módulo completo de Grabadora dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("grabadora", "🎙️ GRABADORA", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.grabadora.grabadora import TabGrabadora
            self._real = TabGrabadora(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Grabadora:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickNotebookWidget(QuickWidgetBase):
    """Carga el módulo completo de Cuaderno dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("cuaderno", "📓 CUADERNO", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.cuaderno.cuaderno import TabCuaderno
            self._real = TabCuaderno(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Cuaderno:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickChatWidget(QuickWidgetBase):
    """Carga el módulo completo de Chat Local/VPN dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("chat", "💬 CHAT LOCAL/VPN", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.chat.chat import TabChat
            self._real = TabChat(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Chat:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickExtrasWidget(QuickWidgetBase):
    """Sub-widget extras rápidos con Recorte y lanzador de herramientas independientes"""
    def __init__(self, context, parent=None):
        super().__init__("extras", "🛠️ EXTRAS", context, parent)
        self.tool_windows = {}
        self.init_ui()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: {self.colores['fg_secundario']};
                padding: 6px 12px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['bg_principal']};
                color: {self.colores['acento']};
                border-bottom: 2px solid {self.colores['acento']};
            }}
        """)
        
        # 1. Pestaña de Recortes
        self.recortes_widget = QWidget()
        rec_layout = QVBoxLayout(self.recortes_widget)
        rec_layout.setContentsMargins(0, 4, 0, 0)
        
        try:
            from vistas.modulos.extras.submodulos.snipper import SnipperGUI
            self.snipper_gui = SnipperGUI(self, self.colores)
            self.snipper_gui.start_snip = self.custom_start_snip
            rec_layout.addWidget(self.snipper_gui)
        except Exception:
            pass
        self.tabs.addTab(self.recortes_widget, "📸 Recortes")
        
        # 2. Pestaña de Herramientas
        self.tools_widget = QWidget()
        tools_layout = QVBoxLayout(self.tools_widget)
        tools_layout.setContentsMargins(4, 4, 4, 4)
        
        lbl_tools_desc = QLabel("Lanza herramientas en ventanas separadas:")
        lbl_tools_desc.setStyleSheet("color: white; font-weight: bold; font-size: 11px; margin-bottom: 4px;")
        tools_layout.addWidget(lbl_tools_desc)
        
        grid = QGridLayout()
        grid.setSpacing(6)
        
        try:
            from vistas.modulos.extras.submodulos.espejo_celular import EspejoCelularGUI
            from vistas.modulos.extras.submodulos.ruleta import RouletteGUI
            from vistas.modulos.extras.submodulos.soundboard import SoundboardGUI
            from vistas.modulos.extras.submodulos.kanban import KanbanGUI
            from vistas.modulos.extras.submodulos.pizarra import PizarraGUI
            from vistas.modulos.extras.submodulos.launcher import LauncherGUI

            herramientas_info = [
                ("📱 Espejo Celular", EspejoCelularGUI, (650, 520)),
                ("🎡 Ruleta", RouletteGUI, (550, 450)),
                ("🔊 Soundboard", SoundboardGUI, (450, 400)),
                ("📌 Kanban", KanbanGUI, (600, 450)),
                ("🎨 Pizarra", PizarraGUI, (600, 500)),
                ("🚀 Lanzador", LauncherGUI, (400, 300))
            ]
            
            for idx, (name, widget_cls, size) in enumerate(herramientas_info):
                btn = QPushButton(name)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedHeight(36)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colores['bg_secundario']};
                        color: white;
                        border: 1px solid {self.colores['bg_terciario']};
                        border-radius: 6px;
                        font-weight: bold;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.colores['bg_terciario']};
                        border: 1px solid {self.colores['acento']};
                    }}
                """)
                btn.clicked.connect(lambda checked, n=name, w_cls=widget_cls, sz=size: self.lanzar_herramienta(n, w_cls, sz))
                
                row = idx // 2
                col = idx % 2
                grid.addWidget(btn, row, col)
        except Exception:
            pass
            
        tools_layout.addLayout(grid)
        tools_layout.addStretch()
        
        self.tabs.addTab(self.tools_widget, "🛠️ Herramientas")
        self.layout_contenido.addWidget(self.tabs)

    def custom_start_snip(self):
        self.centered_win = self.window()
        self.floating_win = getattr(self.centered_win, "parent_window", None)
        if not self.floating_win:
            self.floating_win = getattr(self.centered_win, "parent_drawer", None)
        
        self.centered_win.hide()
        if self.floating_win:
            self.floating_win.hide()
            
        delay = getattr(self.snipper_gui, "combo_delay", None)
        delay_val = delay.currentData() if delay else 0
        QTimer.singleShot(delay_val * 1000 if delay_val > 0 else 300, self._custom_launch_overlay)

    def _custom_launch_overlay(self):
        try:
            from vistas.modulos.extras.submodulos.snipper import SnipperOverlay
            mode = self.snipper_gui.combo_mode.currentData()
            self.overlay = SnipperOverlay(mode)
            self.overlay.area_selected.connect(self.custom_on_captured)
            self.overlay.show()
        except Exception:
            pass

    def custom_on_captured(self, pixmap):
        if self.floating_win:
            self.floating_win.show()
        self.centered_win.show()
        
        if pixmap is not None:
            self.snipper_gui.editor.set_snip(pixmap)
            self.snipper_gui.set_tool("pencil")

    def lanzar_herramienta(self, title, widget_class, size):
        if title in self.tool_windows:
            try:
                self.tool_windows[title].close()
            except Exception:
                pass
            
        win = QuickExtraToolWindow(title, widget_class, self.context, self.colores, size)
        cursor_pos = QCursor.pos()
        win.move(max(50, cursor_pos.x() - size[0] // 2), max(50, cursor_pos.y() - size[1] // 2))
        self.tool_windows[title] = win
        win.show()


class QuickMiniGamesWidget(QuickWidgetBase):
    """Carga el módulo completo de MiniGames dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("minigames", "🎮 MINIGAMES", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.minigames.minigames import TabMiniGames
            self._real = TabMiniGames(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando MiniGames:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickTimeWidget(QuickWidgetBase):
    """Carga el módulo completo de Tiempo dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("tiempo", "⏱️ TIEMPO", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.tiempo.tiempo import TabTiempo
            self._real = TabTiempo(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Tiempo:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)


class QuickTranslatorWidget(QuickWidgetBase):
    """Carga el módulo completo de Traductor dentro del widget flotante"""
    def __init__(self, context, parent=None):
        super().__init__("traductor", "🌍 TRADUCTOR", context, parent)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        try:
            from vistas.modulos.traductor.traductor import TabTraductor
            self._real = TabTraductor(self, context)
            self.layout_contenido.addWidget(self._real)
        except Exception as e:
            lbl = QLabel(f"⚠️ Error cargando Traductor:\n{e}")
            lbl.setStyleSheet("color: #F87171; font-size: 10px;")
            lbl.setWordWrap(True)
            self.layout_contenido.addWidget(lbl)
