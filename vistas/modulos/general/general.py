"""
general.py - Módulo contenedor General con carga dinámica basada en config.json
"""
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtCore import Qt
from controlador.utils.submodule_loader import load_submodules_from_config

class GeneralTab(QWidget):
    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent)
        self.context = context
        self.colores = colores or (getattr(context.app, "COLORES", {}) if context and hasattr(context, "app") else {})

        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # TabWidget Principal del Módulo General
        self.tabs = QTabWidget()
        self._aplicar_estilo_tabs()

        # Carga dinámica desde config.json
        module_dir = Path(__file__).resolve().parent
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores)

        # Fallback de seguridad si config.json no existiera
        if self.tabs.count() == 0:
            try:
                from .submodulos.dashboard import TabInicioGUI
                self.tab_dashboard = TabInicioGUI(self, self.context)
                self.tabs.addTab(self.tab_dashboard, "🏠 Inicio & Dashboard")
            except Exception as e:
                print(f"[ERROR] Al instanciar Dashboard fallback: {e}")

        main_lay.addWidget(self.tabs)

    def _aplicar_estilo_tabs(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {bg_p};
            }}
            QTabBar::tab {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
            QTabBar::tab:hover {{
                color: white;
            }}
        """)

    def actualizar_tema(self, colores):
        if isinstance(colores, dict):
            self.colores = colores
            self._aplicar_estilo_tabs()
            for instance in getattr(self, "submod_instances", {}).values():
                if hasattr(instance, "actualizar_tema") and callable(instance.actualizar_tema):
                    try:
                        instance.actualizar_tema(colores)
                    except Exception as e:
                        print(f"[WARN] Error actualizando tema en submódulo de General: {e}")

TabGeneral = GeneralTab

