import platform
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut

from .submodulos.juegos_arcade import JuegosArcadeSubmodule
from .submodulos.juegos_tablero import JuegosTableroSubmodule
from .submodulos.juegos_combate_adivinanza import JuegosCombateAdivinanzaSubmodule
from .submodulos.juegos_mentales import JuegosMentalesSubmodule
from .submodulos.isaac_game import TabIsaacGame
from .submodulos.casino import CasinoSubmodule
from .submodulos.marcadores_records import MarcadoresRecordsSubmodule

class TabMiniGames(QWidget):
    """
    Módulo Core MiniGames: Agrupa los juegos interactivos, roguelike, multijugador 1v1 y Casino con puntos reales
    (Arcade Retro, Pacman, Tetris, Tablero Estratégico 1v1, Battleship & Adivina Quién, Ahorcado, Isaac Roguelike, Casino Royal y Salón de la Fama).
    """
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        })
        self.ruta_usuario = getattr(context, "ruta_usuario", ".")
        
        self.inicializar_ui()
        self._setup_shortcuts()

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Barra de cabecera arcade
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(14, 6, 14, 6)
        
        lbl_hub = QLabel("🎮 MINIGAMES ARCADE HUB")
        lbl_hub.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_hub.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; letter-spacing: 0.5px;")
        top_bar.addWidget(lbl_hub)
        top_bar.addStretch()
        self.main_layout.addLayout(top_bar)
        
        # QTabWidget Superior de Alto Contraste
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont(self.font_family, 9))
        self.aplicar_estilo_tabs()
        
        # Submódulos dinámicos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores)

        if self.tabs.count() == 0:
            self.tab_arcade = JuegosArcadeSubmodule(self, self.context, self.colores, self.ruta_usuario)
            self.tab_tablero = JuegosTableroSubmodule(self, self.context, self.colores, self.ruta_usuario)
            self.tab_combate = JuegosCombateAdivinanzaSubmodule(self, self.context, self.colores, self.ruta_usuario)
            self.tab_mentales = JuegosMentalesSubmodule(self, self.context, self.colores, self.ruta_usuario)
            self.tab_isaac = TabIsaacGame(self, self.context, self.colores, self.ruta_usuario)
            self.tab_casino = CasinoSubmodule(self, self.context, self.colores, self.ruta_usuario)
            self.tab_records = MarcadoresRecordsSubmodule(self, self.context, self.colores, self.ruta_usuario)

            self.tabs.addTab(self.tab_arcade, "🕹️ Juegos Arcade")
            self.tabs.addTab(self.tab_tablero, "♟️ Estrategia 1v1")
            self.tabs.addTab(self.tab_combate, "🧠 Batalla Naval & Adivinanza")
            self.tabs.addTab(self.tab_mentales, "🎴 Desafíos Mentales")
            self.tabs.addTab(self.tab_isaac, "🔥 Isaac Roguelike")
            self.tabs.addTab(self.tab_casino, "🎰 Casino & Apuestas")
            self.tabs.addTab(self.tab_records, "🏆 Marcadores & Récords")
        else:
            self.tab_arcade = self.submod_instances.get("JuegosArcadeSubmodule") or self.submod_instances.get("juegosarcadesubmodule")
            if not self.tab_arcade:
                self.tab_arcade = JuegosArcadeSubmodule(self, self.context, self.colores, self.ruta_usuario)
            self.tab_tablero = self.submod_instances.get("JuegosTableroSubmodule") or self.submod_instances.get("juegostablerosubmodule")
            if not self.tab_tablero:
                self.tab_tablero = JuegosTableroSubmodule(self, self.context, self.colores, self.ruta_usuario)
            self.tab_combate = self.submod_instances.get("JuegosCombateAdivinanzaSubmodule") or self.submod_instances.get("juegoscombateadivinanzasubmodule")
            if not self.tab_combate:
                self.tab_combate = JuegosCombateAdivinanzaSubmodule(self, self.context, self.colores, self.ruta_usuario)
            self.tab_mentales = self.submod_instances.get("JuegosMentalesSubmodule") or self.submod_instances.get("juegosmentalessubmodule")
            if not self.tab_mentales:
                self.tab_mentales = JuegosMentalesSubmodule(self, self.context, self.colores, self.ruta_usuario)
            self.tab_isaac = self.submod_instances.get("TabIsaacGame") or self.submod_instances.get("tabisaacgame")
            self.tab_casino = self.submod_instances.get("CasinoSubmodule") or self.submod_instances.get("casinosubmodule")
            if not self.tab_casino:
                self.tab_casino = CasinoSubmodule(self, self.context, self.colores, self.ruta_usuario)
            self.tab_records = self.submod_instances.get("MarcadoresRecordsSubmodule") or self.submod_instances.get("marcadoresrecordssubmodule")

        # Aliases Proxy para mantener 100% de compatibilidad con llamadas externas
        if self.tab_arcade:
            self.buscaminas_tab = getattr(self.tab_arcade, "buscaminas", None)
            self.snake_tab = getattr(self.tab_arcade, "snake", None)
            self.pacman_tab = getattr(self.tab_arcade, "pacman", None)
            self.tetris_tab = getattr(self.tab_arcade, "tetris", None)
        if self.tab_tablero:
            self.ajedrez_tab = getattr(self.tab_tablero, "ajedrez", None)
            self.damas_tab = getattr(self.tab_tablero, "damas", None)
        if self.tab_combate:
            self.battleship_tab = getattr(self.tab_combate, "battleship", None)
            self.adivina_quien_tab = getattr(self.tab_combate, "adivina_quien", None)
        if self.tab_mentales:
            self.memory_tab = getattr(self.tab_mentales, "memory", None)
            self.tres_raya_tab = getattr(self.tab_mentales, "tres_raya", None)
            self.ahorcado_tab = getattr(self.tab_mentales, "ahorcado", None)
        if hasattr(self, 'tab_casino') and self.tab_casino:
            self.casino_tab = self.tab_casino

        self.main_layout.addWidget(self.tabs)

    def aplicar_estilo_tabs(self):
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['acento']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.aplicar_estilo_tabs()
        for sub in [getattr(self, 'tab_arcade', None), getattr(self, 'tab_tablero', None),
                    getattr(self, 'tab_combate', None), getattr(self, 'tab_mentales', None),
                    getattr(self, 'tab_casino', None), getattr(self, 'tab_records', None)]:
            if sub and hasattr(sub, 'actualizar_tema'):
                sub.actualizar_tema(colores)

    def _setup_shortcuts(self):
        try:
            self.sc_slash = QShortcut(QKeySequence("/"), self)
            self.sc_slash.activated.connect(self.abrir_consola)
            self.sc_f1 = QShortcut(QKeySequence("F1"), self)
            self.sc_f1.activated.connect(self.abrir_consola)
        except Exception: pass

    def abrir_consola(self):
        try:
            try:
                from controlador.utils.console import MinecraftConsoleDialog
            except ImportError:
                from console import MinecraftConsoleDialog
            if not hasattr(self, "_console_dlg") or not self._console_dlg:
                self._console_dlg = MinecraftConsoleDialog(self)
            self._console_dlg.show()
            self._console_dlg.raise_()
            self._console_dlg.activateWindow()
            if hasattr(self._console_dlg, 'input_edit'):
                self._console_dlg.input_edit.setFocus()
        except Exception as e:
            print(f"[MiniGames] Error al abrir consola: {e}")

    def cleanup(self):
        for sub in [getattr(self, 'tab_arcade', None), getattr(self, 'tab_tablero', None),
                    getattr(self, 'tab_combate', None), getattr(self, 'tab_mentales', None),
                    getattr(self, 'tab_casino', None), getattr(self, 'tab_records', None)]:
            if sub and hasattr(sub, 'cleanup'):
                sub.cleanup()

TabMinigames = TabMiniGames
