"""
automatizacion.py - Módulo Principal de Automatización y Macros para MultiTool Suite.
Integra Auto Clicker Pro (Speed & OP), Auto Teclado (Spammer & Typer) y Grabador de Macros.
"""

import json
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPushButton, QMenu
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QFont

from .submodulos.auto_clicker import TabAutoClicker
from .submodulos.auto_keyboard import TabAutoKeyboard
from .submodulos.macro_recorder import TabMacroRecorder

class TabAutomatizacion(QWidget):
    """Módulo Principal de Automatización y Tareas Programadas."""
    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.context = context
        self.colores = getattr(getattr(context, "app", None), "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171",
        })

        self.submod_instances = {}
        self._iniciando = True

        app_inst = QCoreApplication.instance()
        if app_inst:
            try:
                app_inst.aboutToQuit.connect(self.cleanup)
            except Exception:
                pass

        self.init_ui()
        self._iniciando = False

    def init_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"""
            TabAutomatizacion {{ background-color: {bg_main}; color: white; }}
            QWidget {{ background-color: transparent; color: white; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # QTabWidget principal
        self.tabs = QTabWidget()
        self._aplicar_estilo_tabs()

        # Carga dinámica desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent

        self.submod_instances = load_submodules_from_config(
            module_dir, self.tabs, self, self.context, self.colores
        )

        # Fallback si no cargó submódulos automáticamente
        if self.tabs.count() == 0:
            self.tab_autoclicker = TabAutoClicker(self, self.colores, self.context)
            self.tab_autokeyboard = TabAutoKeyboard(self, self.colores, self.context)
            self.tab_macrorecorder = TabMacroRecorder(self, self.colores, self.context)

            self.tabs.addTab(self.tab_autoclicker, "🖱️ Auto Clicker")
            self.tabs.addTab(self.tab_autokeyboard, "⌨️ Auto Teclado")
            self.tabs.addTab(self.tab_macrorecorder, "🎬 Grabador de Macros")

            self.submod_instances["TabAutoClicker"] = self.tab_autoclicker
            self.submod_instances["TabAutoKeyboard"] = self.tab_autokeyboard
            self.submod_instances["TabMacroRecorder"] = self.tab_macrorecorder
        else:
            self.tab_autoclicker = (
                self.submod_instances.get("TabAutoClicker") or
                self.submod_instances.get("tabautoclicker")
            )
            self.tab_autokeyboard = (
                self.submod_instances.get("TabAutoKeyboard") or
                self.submod_instances.get("tabautokeyboard")
            )
            self.tab_macrorecorder = (
                self.submod_instances.get("TabMacroRecorder") or
                self.submod_instances.get("tabmacrorecorder")
            )

        # Botón de menú de Vistas en la esquina superior derecha
        self.btn_vista_menu = QPushButton("⚙️ Opciones")
        self.btn_vista_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_vista_menu.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.05);
                color: #AAB0B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 10px;
                font-weight: bold;
                margin-right: 6px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.12);
                color: white;
            }}
        """)
        self._actualizar_menu_vista_btn()
        self.tabs.setCornerWidget(self.btn_vista_menu, Qt.Corner.TopRightCorner)

        layout.addWidget(self.tabs)

    def _aplicar_estilo_tabs(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        fg_sec = self.colores.get('fg_secundario', '#AAB0B8')
        acento = self.colores.get('acento', '#6366F1')
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {bg_main};
            }}
            QTabBar::tab {{
                background-color: {bg_sec};
                color: {fg_sec};
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: bold;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background-color: {acento};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
            }}
        """)

    def _actualizar_menu_vista_btn(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores['acento']};
            }}
        """)

        act_detener_todo = menu.addAction("🛑 Detener Todas las Automatizaciones")
        act_detener_todo.triggered.connect(self.detener_todo)
        self.btn_vista_menu.setMenu(menu)

    def detener_todo(self):
        """Detiene cualquier tarea activa en todos los submódulos."""
        for inst in self.submod_instances.values():
            if hasattr(inst, "worker") and hasattr(inst.worker, "stop"):
                inst.worker.stop()
            if hasattr(inst, "recorder") and hasattr(inst.recorder, "stop_recording"):
                inst.recorder.stop_recording()
            if hasattr(inst, "player") and hasattr(inst.player, "stop"):
                inst.player.stop()

    def seleccionar_submodulo(self, alias_o_nombre: str):
        """Permite cambiar a una pestaña específica mediante su alias o nombre."""
        alias_o_nombre = str(alias_o_nombre).lower()
        mapping = {
            "autoclicker": 0, "clicker": 0, "auto_clicker": 0, "auto clicker": 0,
            "autokeyboard": 1, "teclado": 1, "auto_keyboard": 1, "auto teclado": 1,
            "macros": 2, "macro": 2, "macro_recorder": 2, "grabador": 2
        }
        idx = mapping.get(alias_o_nombre, None)
        if idx is not None and 0 <= idx < self.tabs.count():
            self.tabs.setCurrentIndex(idx)

    def cleanup(self):
        """Limpieza al cerrar Multitool."""
        self.detener_todo()
        for inst in self.submod_instances.values():
            if hasattr(inst, "cleanup"):
                try:
                    inst.cleanup()
                except Exception:
                    pass

