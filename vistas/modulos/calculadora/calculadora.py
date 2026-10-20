import json
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTabWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Lógica de Backend
from .utils.historial_logic import HistorialLogic


class TabCalculadora(QWidget):
    """Módulo principal de Calculadora con suite matemática, científica, financiera y de conversión"""
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        colores_app = getattr(getattr(context, "app", None), "COLORES", None)
        self.colores = colores_app if isinstance(colores_app, dict) else {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#FFFFFF", "fg_secundario": "#AAB0B8", "acento": "#6366F1", "acento_hover": "#4F46E5",
            "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        ruta_usuario = getattr(context, "ruta_usuario", None)
        self.ruta_usuario = Path(ruta_usuario) if ruta_usuario else None
        self.logic_historial = HistorialLogic(self.ruta_usuario)
        
        self.inicializar_ui()

    def _aplicar_estilo_tabs(self):
        """Aplica la hoja de estilos reactiva para el QTabWidget sin recrear componentes"""
        if not hasattr(self, "calc_notebook"):
            return
        self.calc_notebook.setStyleSheet(f"""
            QTabWidget::pane {{ 
                border: 0px; 
                background: {self.colores.get('bg_principal', '#121218')};
                border-radius: 12px;
                padding: 5px;
            }}
            QTabBar {{
                background: transparent;
            }}
            QTabBar::tab {{ 
                background: transparent; 
                color: {self.colores.get('fg_secundario', '#AAB0B8')}; 
                padding: 12px 20px; 
                margin-right: 4px;
                font-family: '{self.font_family}';
                font-weight: bold;
                font-size: 11px;
            }}
            QTabBar::tab:hover {{ 
                color: white;
                background: rgba(255,255,255,0.02);
                border-top-left-radius: 8px; border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{ 
                color: {self.colores.get('acento', '#6366F1')}; 
                border-bottom: 2px solid {self.colores.get('acento', '#6366F1')};
                background: rgba(99, 102, 241, 0.05);
            }}
        """)

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(0)
        
        # Notebook principal con diseño moderno
        self.calc_notebook = QTabWidget()
        self.calc_notebook.setUsesScrollButtons(True)
        self._aplicar_estilo_tabs()
        self.main_layout.addWidget(self.calc_notebook, 1)
        
        # Callbacks de historial
        def add_hist(exp, res):
            self.logic_historial.agregar(exp, res)
            if hasattr(self, 'sub_historial') and self.sub_historial:
                self.sub_historial.actualizar_lista()

        def clean_hist():
            res = QMessageBox.question(
                self, "Limpiar Historial", "¿Estás seguro de que quieres borrar todos los cálculos anteriores?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.Yes:
                self.logic_historial.limpiar()
                if hasattr(self, 'sub_historial') and self.sub_historial:
                    self.sub_historial.actualizar_lista()

        # Carga dinámica y modular desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        extra_kwargs = {
            "add_hist": add_hist,
            "agregar_al_historial_callback": add_hist,
            "obtener_historial_callback": self.logic_historial.obtener_lista,
            "get_hist_callback": self.logic_historial.obtener_lista,
            "limpiar_historial_callback": clean_hist,
            "clean_hist_callback": clean_hist
        }
        self.submod_instances = load_submodules_from_config(
            module_dir, self.calc_notebook, self, self.context, self.colores, extra_kwargs
        )

        # Fallback si no hubiese pestañas configuradas
        if self.calc_notebook.count() == 0:
            try:
                from .submodulos.basica import TabCalculadoraBasica
                self.sub_basica = TabCalculadoraBasica(self.calc_notebook, self.colores, add_hist)
                self.calc_notebook.addTab(self.sub_basica, "🔢 Básica")
            except Exception as e:
                print(f"[!] Error cargando submódulo fallback: {e}")
        else:
            self.sub_historial = self.submod_instances.get("TabCalculadoraHistorial") or self.submod_instances.get("tabcalculadorahistorial")

    def actualizar_tema(self, colores):
        """Actualiza la paleta visual de la calculadora sin duplicar pestañas ni layouts"""
        if isinstance(colores, dict):
            self.colores = colores
        self._aplicar_estilo_tabs()

        # Propagar tema a submódulos instanciados
        for i in range(self.calc_notebook.count()):
            w = self.calc_notebook.widget(i)
            if hasattr(w, "actualizar_tema") and callable(w.actualizar_tema):
                try:
                    w.actualizar_tema(self.colores)
                except Exception:
                    pass
            elif hasattr(w, "colores"):
                w.colores = self.colores
