"""
TabClipboard — Gestor de Portapapeles (Clipboard Manager)
Controlador principal. Monitorea el portapapeles del sistema, gestiona snippets y herramientas de formateo de texto.
"""
import json
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPushButton, QMenu
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QFont

from .submodulos.historial_clip import TabHistorialClipboard
from .submodulos.snippets_clip import TabSnippetsClipboard
from .submodulos.herramientas_texto import TabHerramientasTextoClipboard


class TabClipboard(QWidget):
    """Módulo Principal del Gestor de Portapapeles"""
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171",
        })
        ruta = Path(getattr(context, "ruta_usuario", "."))
        self.ruta_data = ruta / "clipboard_historial.json"
        self.ruta_state = ruta / "config_clipboard_vista.json"
        self._iniciando = True

        app_inst = QCoreApplication.instance()
        if app_inst:
            try:
                app_inst.aboutToQuit.connect(self.cleanup)
            except Exception:
                pass

        self.init_ui()
        self._restaurar_vista_inicial()
        self._iniciando = False

    def init_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"""
            TabClipboard {{ background-color: {bg_main}; color: white; }}
            QWidget {{ background-color: transparent; color: white; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # QTabWidget principal
        self.tabs = QTabWidget()
        self._aplicar_estilo_tabs()

        # Submódulos dinámicos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        extra_kwargs = {
            "ruta_data": self.ruta_data,
            "ruta_carpeta": self.ruta_data.parent
        }
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores, extra_kwargs)

        if self.tabs.count() == 0:
            self.tab_historial = TabHistorialClipboard(self, self.colores, self.ruta_data)
            self.tab_snippets = TabSnippetsClipboard(self, self.colores, self.ruta_data.parent)
            self.tab_tools = TabHerramientasTextoClipboard(self, self.colores)

            self.tabs.addTab(self.tab_historial, "🗃️ Historial")
            self.tabs.addTab(self.tab_snippets, "📌 Snippets & Plantillas")
            self.tabs.addTab(self.tab_tools, "⚙️ Herramientas de Texto")
        else:
            self.tab_historial = self.submod_instances.get("TabHistorialClipboard") or self.submod_instances.get("tabhistorialclipboard")
            if not self.tab_historial:
                self.tab_historial = TabHistorialClipboard(self, self.colores, self.ruta_data)
            self.tab_snippets = self.submod_instances.get("TabSnippetsClipboard") or self.submod_instances.get("tabsnippetsclipboard")
            if not self.tab_snippets:
                self.tab_snippets = TabSnippetsClipboard(self, self.colores, self.ruta_data.parent)
            self.tab_tools = self.submod_instances.get("TabHerramientasTextoClipboard") or self.submod_instances.get("tabherramientastextoclipboard")
            if not self.tab_tools:
                self.tab_tools = TabHerramientasTextoClipboard(self, self.colores)

        # Conectar señales entre submódulos
        if hasattr(self.tab_historial, 'enviar_a_herramientas'):
            self.tab_historial.enviar_a_herramientas.connect(self._on_enviar_a_herramientas)
        if hasattr(self.tab_historial, 'guardar_como_snippet'):
            self.tab_historial.guardar_como_snippet.connect(self._on_guardar_como_snippet)

        # Menú contextual en el TabBar para fijar pestaña de inicio predeterminada
        self.tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.tabBar().customContextMenuRequested.connect(self._mostrar_menu_tab)

        # Botón de menú de Vistas en la esquina superior derecha
        self.btn_vista_menu = QPushButton("⚙️ Vista")
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

        self.tabs.currentChanged.connect(self._on_tab_changed)
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
        v_menu = QMenu(self)
        for i in range(self.tabs.count()):
            t_text = self.tabs.tabText(i)
            v_menu.addAction(f"Ir a: {t_text}", lambda idx=i: self.tabs.setCurrentIndex(idx))
        v_menu.addSeparator()
        v_menu.addAction("⭐ Fijar pestaña actual como Vista Inicial", lambda: self._fijar_vista_inicial(self.tabs.currentIndex()))
        self.btn_vista_menu.setMenu(v_menu)

    def _mostrar_menu_tab(self, pos):
        idx = self.tabs.tabBar().tabAt(pos)
        if idx < 0:
            return
        menu = QMenu(self)
        tab_name = self.tabs.tabText(idx)
        act_fijar = menu.addAction(f"⭐ Establecer '{tab_name}' como Vista Inicial Predeterminada")
        act_fijar.triggered.connect(lambda: self._fijar_vista_inicial(idx))
        menu.exec(self.tabs.tabBar().mapToGlobal(pos))

    def _fijar_vista_inicial(self, idx):
        self._guardar_vista_estado(idx)

    def _guardar_vista_estado(self, index=None):
        if index is None:
            index = self.tabs.currentIndex()
        try:
            state = {
                "vista_inicial": int(index),
                "recordar_ultima": True
            }
            with open(self.ruta_state, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception:
            pass

    def _restaurar_vista_inicial(self):
        if not self.ruta_state.exists():
            return
        try:
            with open(self.ruta_state, "r", encoding="utf-8") as f:
                state = json.load(f)
            vista_idx = state.get("vista_inicial", 0)
            if 0 <= vista_idx < self.tabs.count():
                self.tabs.setCurrentIndex(vista_idx)
        except Exception as e:
            print(f"[TabClipboard] Error restaurando vista inicial: {e}")

    def _on_tab_changed(self, idx):
        if not self._iniciando:
            self._guardar_vista_estado(idx)
        if idx == 0 and hasattr(self, 'tab_historial') and self.tab_historial:
            self.tab_historial.refrescar_lista()
        elif idx == 1 and hasattr(self, 'tab_snippets') and self.tab_snippets:
            self.tab_snippets.refrescar_lista()

    def _on_enviar_a_herramientas(self, texto: str):
        """Recibe texto desde el historial y lo carga directamente en las herramientas de texto."""
        if hasattr(self, 'tab_tools') and self.tab_tools:
            self.tab_tools.cargar_texto(texto)
        # Cambiar a la pestaña de herramientas
        for i in range(self.tabs.count()):
            if "Herramientas" in self.tabs.tabText(i):
                self.tabs.setCurrentIndex(i)
                break
        else:
            self.tabs.setCurrentIndex(2)

    def _on_guardar_como_snippet(self, texto: str):
        """Transfiere una copia al submódulo de plantillas y snippets para guardarla."""
        for i in range(self.tabs.count()):
            if "Snippets" in self.tabs.tabText(i):
                self.tabs.setCurrentIndex(i)
                break
        else:
            self.tabs.setCurrentIndex(1)
        if hasattr(self, 'tab_snippets') and self.tab_snippets:
            self.tab_snippets.agregar_desde_historial(texto)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.init_ui()
        if hasattr(self, 'tab_historial') and hasattr(self.tab_historial, 'actualizar_tema'):
            self.tab_historial.actualizar_tema(colores)
        if hasattr(self, 'tab_snippets') and hasattr(self.tab_snippets, 'actualizar_tema'):
            self.tab_snippets.actualizar_tema(colores)
        if hasattr(self, 'tab_tools') and hasattr(self.tab_tools, 'actualizar_tema'):
            self.tab_tools.actualizar_tema(colores)

    def cleanup(self):
        """Detiene timers y libera recursos al cerrar."""
        if hasattr(self, 'tab_historial') and self.tab_historial:
            try:
                self.tab_historial.cleanup()
            except Exception:
                pass
