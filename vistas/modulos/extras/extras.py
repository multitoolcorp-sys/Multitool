import json
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QPushButton,
    QMenu, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor

from .submodulos.espejo_celular import EspejoCelularGUI
from .submodulos.snipper import SnipperGUI
from .submodulos.kanban_pizarra import KanbanPizarraSubmodule
from .submodulos.lanzador_soundboard import LanzadorSoundboardSubmodule
from .submodulos.ruleta import RouletteGUI


class TabExtras(QWidget):
    """
    Módulo Principal de Herramientas Extras con QTabWidget y Submódulos Desacoplados:
    1. 📱 Espejo Celular (Transmisión Móvil)
    2. 📸 Recortes & OCR (Lector OCR & Escáner QR)
    3. 📌 Suite de Productividad (Tablero Kanban & Pizarra Vectorial)
    4. 🚀 Hub de Utilidades (Lanzador de Apps & Soundboard Audio)
    5. 🎡 Ruleta de Decisiones Animada & Mini-juegos de Azar
    """
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.colores = getattr(getattr(context, "app", None), "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        })
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.ruta_config_vista = self.ruta_usuario / "config_extras_vista.json"

        self.inicializar_ui()

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # TabWidget Superior
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont(self.font_family, 9))
        self._aplicar_estilos_tabs()

        # Botón de menú de vista en esquina derecha superior
        self.btn_vista_menu = QPushButton("⚙️ Vista")
        self.btn_vista_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_vista_menu.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
                margin: 4px 6px;
            }}
            QPushButton:hover {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.btn_vista_menu.clicked.connect(self._mostrar_menu_vista)
        self.tabs.setCornerWidget(self.btn_vista_menu, Qt.Corner.TopRightCorner)

        # Menú contextual sobre la barra de pestañas
        tab_bar = self.tabs.tabBar()
        tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tab_bar.customContextMenuRequested.connect(self._mostrar_menu_pestana)

        # Submódulos dinámicos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores)

        if self.tabs.count() == 0:
            self.tab_espejo = EspejoCelularGUI(self, self.colores, str(self.ruta_usuario))
            self.tab_snipper = SnipperGUI(self, self.colores)
            self.tab_productividad = KanbanPizarraSubmodule(self, self.context, self.colores)
            self.tab_utilidades = LanzadorSoundboardSubmodule(self, self.context, self.colores, str(self.ruta_usuario))
            self.tab_ruleta = RouletteGUI(self, self.colores, str(self.ruta_usuario))

            self.tabs.addTab(self.tab_espejo, "📱 Espejo Celular")
            self.tabs.addTab(self.tab_snipper, "📸 Recortes & OCR")
            self.tabs.addTab(self.tab_productividad, "📌 Kanban & Pizarra")
            self.tabs.addTab(self.tab_utilidades, "🚀 Lanzador & Sonidos")
            self.tabs.addTab(self.tab_ruleta, "🎡 Ruleta")
        else:
            self.tab_espejo = self.submod_instances.get("EspejoCelularGUI") or self.submod_instances.get("espejocelulargui")
            if not self.tab_espejo:
                self.tab_espejo = EspejoCelularGUI(self, self.colores, str(self.ruta_usuario))
            
            self.tab_snipper = self.submod_instances.get("SnipperGUI") or self.submod_instances.get("snippergui")
            if not self.tab_snipper:
                self.tab_snipper = SnipperGUI(self, self.colores)
            
            self.tab_productividad = self.submod_instances.get("KanbanPizarraSubmodule") or self.submod_instances.get("kanbanpizarrasubmodule")
            if not self.tab_productividad:
                self.tab_productividad = KanbanPizarraSubmodule(self, self.context, self.colores)
            
            self.tab_utilidades = self.submod_instances.get("LanzadorSoundboardSubmodule")
            self.tab_ruleta = self.submod_instances.get("RouletteGUI")

        # Aliases Proxy para mantener 100% de compatibilidad con llamadas externas
        self.espejo_tab = self.tab_espejo
        self.snipper_tab = self.tab_snipper
        if self.tab_productividad:
            self.kanban_tab = getattr(self.tab_productividad, "kanban", None)
            self.pizarra_tab = getattr(self.tab_productividad, "pizarra", None)
        else:
            self.kanban_tab = None
            self.pizarra_tab = None

        if self.tab_utilidades:
            self.launcher_tab = getattr(self.tab_utilidades, "launcher", None)
            self.sound_tab = getattr(self.tab_utilidades, "soundboard", None)
        else:
            self.launcher_tab = None
            self.sound_tab = None

        self.ruleta_tab = self.tab_ruleta

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.main_layout.addWidget(self.tabs)

        # Restaurar vista guardada
        self.cargar_config_vista()

    def _aplicar_estilos_tabs(self):
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores.get('bg_principal', '#121218')};
            }}
            QTabBar::tab {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
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
            QTabBar::tab:hover:!selected {{
                background: rgba(255, 255, 255, 0.08);
                color: white;
            }}
        """)

    def _on_tab_changed(self, idx):
        self.guardar_config_vista()

    def _mostrar_menu_vista(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QMenu::item {{
                color: white;
                padding: 6px 16px;
            }}
            QMenu::item:selected {{
                background: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        for i in range(self.tabs.count()):
            texto = self.tabs.tabText(i)
            action = menu.addAction(f"Ir a: {texto}")
            action.triggered.connect(lambda checked, idx=i: self.tabs.setCurrentIndex(idx))

        menu.addSeparator()
        def_action = menu.addAction("📌 Fijar pestaña actual como vista por defecto")
        def_action.triggered.connect(lambda: self.guardar_config_vista(forzar_defecto=True))

        menu.exec(QCursor.pos())

    def _mostrar_menu_pestana(self, pos):
        idx = self.tabs.tabBar().tabAt(pos)
        if idx < 0:
            return
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QMenu::item {{
                color: white;
                padding: 6px 16px;
            }}
            QMenu::item:selected {{
                background: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        act_sel = menu.addAction(f"Ir a {self.tabs.tabText(idx)}")
        act_sel.triggered.connect(lambda: self.tabs.setCurrentIndex(idx))

        act_def = menu.addAction("📌 Abrir siempre en esta pestaña")
        act_def.triggered.connect(lambda: self._fijar_pestana_defecto(idx))

        menu.exec(self.tabs.tabBar().mapToGlobal(pos))

    def _fijar_pestana_defecto(self, idx):
        self.tabs.setCurrentIndex(idx)
        self.guardar_config_vista(forzar_defecto=True)
        QMessageBox.information(self, "Vista Configurada", f"'{self.tabs.tabText(idx)}' se abrirá de manera predeterminada.")

    def cargar_config_vista(self):
        if self.ruta_config_vista.exists():
            try:
                with open(self.ruta_config_vista, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                pestana = cfg.get("pestana_activa", 0)
                if 0 <= pestana < self.tabs.count():
                    self.tabs.setCurrentIndex(pestana)
            except Exception:
                pass

    def guardar_config_vista(self, forzar_defecto=False):
        try:
            cfg = {
                "pestana_activa": self.tabs.currentIndex()
            }
            with open(self.ruta_config_vista, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
        except Exception:
            pass

    def actualizar_tema(self, colores):
        self.colores = colores
        self._aplicar_estilos_tabs()
        for submod in [self.tab_espejo, self.tab_snipper, self.tab_productividad, self.tab_utilidades, self.tab_ruleta]:
            if submod and hasattr(submod, "actualizar_tema"):
                try:
                    submod.actualizar_tema(colores)
                except Exception:
                    pass

    def cleanup(self):
        for submod in [self.tab_espejo, self.tab_snipper, self.tab_productividad, self.tab_utilidades, self.tab_ruleta]:
            if submod and hasattr(submod, "cleanup"):
                try:
                    submod.cleanup()
                except Exception:
                    pass
