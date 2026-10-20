import os
import sys
import platform
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QPushButton, QLabel, QFrame, QComboBox, QSplitter,
    QMenu, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut

from .submodulos.terminal_session import SingleTerminalSession
from .submodulos.snippets_panel import SnippetsPanel
from .submodulos.history_dialog import HistorySearchDialog

class TabTerminal(QWidget):
    """Módulo Principal de Terminal Emulada Multisesión e Interactiva con Soporte Git Avanzado"""
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8"
        })
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        
        # Historial global de comandos
        self.history = []
        self.ruta_history = None
        ruta_usuario = getattr(context, "ruta_usuario", None)
        if ruta_usuario:
            self.ruta_history = Path(ruta_usuario) / "terminal_history.txt"
            self._cargar_historial_persistente()

        # Paleta de temas
        self.temas = {
            "🟢 Hacker Esmeralda": {"bg": "#07090e", "fg": "#10B981", "accent": "#059669"},
            "🟦 Cyberpunk Neón": {"bg": "#090d16", "fg": "#06B6D4", "accent": "#0891B2"},
            "🟡 Matrix Ámbar": {"bg": "#0c0a07", "fg": "#F59E0B", "accent": "#D97706"},
            "🫥 Consola Clásica": {"bg": "#0f0f15", "fg": "#F3F4F6", "accent": "#9CA3AF"}
        }
        self.tema_actual = "🟢 Hacker Esmeralda"

        # Perfiles de shell
        self.perfiles_shell = self._detectar_perfiles_shell()
        self.perfil_actual = list(self.perfiles_shell.keys())[0] if self.perfiles_shell else "Default"

        self.inicializar_ui()
        self.crear_nueva_pestana()

    def inicializar_ui(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.colores['bg_principal']};
                color: #FFFFFF;
                border: none;
            }}
            QToolTip {{
                background-color: {self.colores['bg_secundario']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-family: '{self.font_family}';
            }}
            QComboBox {{
                background-color: {self.colores['bg_secundario']};
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: #FFFFFF;
                selection-background-color: {self.colores['acento']};
                selection-color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.15);
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                color: #FFFFFF;
                padding: 6px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {self.colores['acento']};
                color: #FFFFFF;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Barra de Controles Superior
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(8)

        lbl_title = QLabel("📟 TERMINAL INTEGRADA")
        lbl_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none; background: transparent;")
        ctrl_bar.addWidget(lbl_title)

        ctrl_bar.addStretch()

        # Botón Nueva Pestaña
        btn_add_tab = QPushButton("➕ Pestaña")
        btn_add_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_tab.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_add_tab.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']}; color: white;
                padding: 5px 12px; border-radius: 6px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores.get('acento_hover', self.colores['acento'])}; }}
        """)
        btn_add_tab.clicked.connect(lambda: self.crear_nueva_pestana())
        ctrl_bar.addWidget(btn_add_tab)

        # Botón Git Visual
        btn_git = QPushButton("🌿 Git")
        btn_git.setToolTip("Abrir Explorador Visual de Git y Ramas para la sesión activa")
        btn_git.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_git.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_git.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_secundario']}; color: #10B981;
                padding: 5px 12px; border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.4);
            }}
            QPushButton:hover {{
                background-color: rgba(16, 185, 129, 0.15);
                border-color: #10B981;
            }}
        """)
        btn_git.clicked.connect(self.abrir_dialogo_git_activo)
        ctrl_bar.addWidget(btn_git)

        # Selector de Perfil de Shell
        lbl_shell = QLabel("Shell:")
        lbl_shell.setStyleSheet("color: #AAA; font-size: 10px; border: none; background: transparent;")
        ctrl_bar.addWidget(lbl_shell)
        
        self.combo_shell = QComboBox()
        self.combo_shell.addItems(list(self.perfiles_shell.keys()) if self.perfiles_shell else ["Default"])
        self.combo_shell.setFont(QFont(self.font_family, 9))
        self.combo_shell.setFixedWidth(130)
        self.combo_shell.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px; padding: 4px 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
            }}
        """)
        self.combo_shell.currentTextChanged.connect(self._on_shell_changed)
        ctrl_bar.addWidget(self.combo_shell)

        # Selector de Tema
        self.combo_tema = QComboBox()
        self.combo_tema.addItems(list(self.temas.keys()))
        self.combo_tema.setFont(QFont(self.font_family, 9))
        self.combo_tema.setFixedWidth(160)
        self.combo_tema.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px; padding: 4px 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
            }}
        """)
        self.combo_tema.currentTextChanged.connect(self.cambiar_tema)
        ctrl_bar.addWidget(self.combo_tema)

        # Botón Snippets (Toggle Sidebar)
        btn_snippets = QPushButton("⚡ Snippets")
        btn_snippets.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_snippets.setFont(QFont(self.font_family, 9))
        btn_snippets.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white; padding: 5px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);")
        btn_snippets.clicked.connect(self.toggle_snippets_panel)
        ctrl_bar.addWidget(btn_snippets)

        # Botón Historial
        btn_history = QPushButton("📜 Historial")
        btn_history.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_history.setFont(QFont(self.font_family, 9))
        btn_history.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white; padding: 5px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);")
        btn_history.clicked.connect(self.abrir_dialogo_historial)
        ctrl_bar.addWidget(btn_history)

        # Botón Exportar Log
        btn_export = QPushButton("💾 Log")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setFont(QFont(self.font_family, 9))
        btn_export.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white; padding: 5px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);")
        btn_export.clicked.connect(self.exportar_log_activo)
        ctrl_bar.addWidget(btn_export)

        # Botón Limpiar
        btn_clear = QPushButton("🗑️")
        btn_clear.setToolTip("Limpiar consola (Ctrl+L)")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setFont(QFont(self.font_family, 9))
        btn_clear.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white; padding: 5px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);")
        btn_clear.clicked.connect(self.limpiar_consola_activa)
        ctrl_bar.addWidget(btn_clear)

        # Botón Reiniciar
        btn_restart = QPushButton("🔄")
        btn_restart.setToolTip("Reiniciar proceso de shell activo")
        btn_restart.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restart.setFont(QFont(self.font_family, 9))
        btn_restart.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white; padding: 5px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);")
        btn_restart.clicked.connect(self.reiniciar_shell_activo)
        ctrl_bar.addWidget(btn_restart)

        layout.addLayout(ctrl_bar)

        # Splitter Principal (Consola Pestañas vs Snippets)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setStyleSheet(f"""
            QSplitter::handle {{ 
                background: {self.colores['bg_terciario']}; width: 2px; 
            }}
        """)

        # Gestor de Pestañas
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setFont(QFont(self.font_family, 9))
        self.tab_widget.tabCloseRequested.connect(self.cerrar_pestana)
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self._on_tab_context_menu)
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background-color: {self.colores['bg_secundario']};
                color: #FFFFFF;
                padding: 6px 14px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.colores['acento']};
                color: #FFFFFF;
                font-weight: bold;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: rgba(255,255,255,0.15);
                color: #FFFFFF;
            }}
        """)
        self.main_splitter.addWidget(self.tab_widget)

        # Panel de Snippets con persistencia
        user_folder = self.ruta_history.parent if self.ruta_history else None
        self.snippets_panel = SnippetsPanel(self, self.colores, ruta_usuario=user_folder)
        self.snippets_panel.snippet_selected.connect(self.ejecutar_snippet)
        self.snippets_panel.hide()
        self.main_splitter.addWidget(self.snippets_panel)

        self.main_splitter.setStretchFactor(0, 4)
        self.main_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.main_splitter, 1)

        # Atajos globales de la terminal
        s_newtab = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        s_newtab.activated.connect(lambda: self.crear_nueva_pestana())

        s_hist = QShortcut(QKeySequence("Ctrl+R"), self)
        s_hist.activated.connect(self.abrir_dialogo_historial)

        s_git = QShortcut(QKeySequence("Ctrl+G"), self)
        s_git.activated.connect(self.abrir_dialogo_git_activo)

    def crear_nueva_pestana(self, nombre=None, shell_cmd=None, shell_args=None, cwd=None):
        """Crea una nueva pestaña de terminal independiente"""
        perfil = self.perfiles_shell.get(self.perfil_actual, None)
        if perfil and not shell_cmd:
            shell_cmd, shell_args = perfil

        p_name = nombre or f"{self.perfil_actual} #{self.tab_widget.count() + 1}"
        t_dict = self.temas.get(self.tema_actual, {"bg": "#07090e", "fg": "#10B981", "accent": "#059669"})

        if not cwd and hasattr(self.context, 'ruta_actual'):
            cwd = str(self.context.ruta_actual)

        session = SingleTerminalSession(
            parent=self.tab_widget,
            context=self.context,
            shell_cmd=shell_cmd,
            shell_args=shell_args,
            cwd=cwd,
            tema_dict=t_dict
        )

        idx = self.tab_widget.addTab(session, p_name)
        self.tab_widget.setCurrentIndex(idx)
        session.terminal.setFocus()

    def cerrar_pestana(self, index):
        if self.tab_widget.count() > 1:
            widget = self.tab_widget.widget(index)
            if widget:
                widget.close()
                self.tab_widget.removeTab(index)
        else:
            session = self.get_active_session()
            if session:
                session.reiniciar_proceso()

    def get_active_session(self) -> SingleTerminalSession:
        return self.tab_widget.currentWidget()

    def _on_shell_changed(self, nombre_perfil):
        self.perfil_actual = nombre_perfil
        session = self.get_active_session()
        if session:
            perfil = self.perfiles_shell.get(nombre_perfil)
            if perfil:
                session.shell_cmd, session.shell_args = perfil
                session.reiniciar_proceso()

    def cambiar_tema(self, nombre_tema):
        if nombre_tema not in self.temas:
            return
        self.tema_actual = nombre_tema
        t = self.temas[nombre_tema]
        for i in range(self.tab_widget.count()):
            session = self.tab_widget.widget(i)
            if session:
                session.aplicar_tema(t)

    def toggle_snippets_panel(self):
        if self.snippets_panel.isVisible():
            self.snippets_panel.hide()
        else:
            self.snippets_panel.show()

    def ejecutar_snippet(self, cmd):
        session = self.get_active_session()
        if session:
            session.enviar_comando(cmd)
            self._guardar_comando_en_historial(cmd)

    def abrir_dialogo_historial(self):
        session = self.get_active_session()
        hist = self.history + (session.history if session else [])
        dlg = HistorySearchDialog(self, hist, self.colores)
        if dlg.exec() and dlg.selected_command:
            cmd = dlg.selected_command
            if session:
                session.enviar_comando(cmd)
                self._guardar_comando_en_historial(cmd)

    def abrir_dialogo_git_activo(self):
        session = self.get_active_session()
        cwd = session.cwd if session else os.getcwd()
        from .submodulos.git_dialog import GitViewerDialog
        dlg = GitViewerDialog(self, cwd, self.colores, on_execute_cmd_callback=session.enviar_comando if session else None)
        dlg.exec()
        if session:
            session.actualizar_info_git()

    def exportar_log_activo(self):
        session = self.get_active_session()
        if session:
            session.exportar_log()

    def limpiar_consola_activa(self):
        session = self.get_active_session()
        if session:
            session.limpiar_consola()

    def reiniciar_shell_activo(self):
        session = self.get_active_session()
        if session:
            session.reiniciar_proceso()

    def _guardar_comando_en_historial(self, cmd):
        if cmd and cmd.strip():
            self.history.append(cmd.strip())
            self._guardar_historial_persistente()

    def _on_tab_context_menu(self, pos):
        tab_bar = self.tab_widget.tabBar()
        index = tab_bar.tabAt(pos)
        if index < 0:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 4px;
            }}
            QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {self.colores['acento']}; }}
        """)

        act_rename = menu.addAction("✏️ Renombrar Pestaña")
        act_dup = menu.addAction("📑 Duplicar Pestaña")
        act_git = menu.addAction("🌿 Abrir Git de esta Pestaña")
        act_open_folder = menu.addAction("📁 Abrir Carpeta en Explorador")
        menu.addSeparator()
        act_close = menu.addAction("❌ Cerrar Pestaña")
        act_close_others = menu.addAction("✖️ Cerrar Otras Pestañas")

        chosen = menu.exec(self.tab_widget.mapToGlobal(pos))
        session = self.tab_widget.widget(index)

        if chosen == act_rename:
            current_text = self.tab_widget.tabText(index)
            nuevo_nombre, ok = QInputDialog.getText(self, "Renombrar Pestaña", "Nombre:", text=current_text)
            if ok and nuevo_nombre.strip():
                self.tab_widget.setTabText(index, nuevo_nombre.strip())
        elif chosen == act_dup:
            if session:
                self.crear_nueva_pestana(
                    nombre=f"{self.tab_widget.tabText(index)} (Copia)",
                    shell_cmd=session.shell_cmd,
                    shell_args=session.shell_args,
                    cwd=session.cwd
                )
        elif chosen == act_git:
            if session:
                from .submodulos.git_dialog import GitViewerDialog
                dlg = GitViewerDialog(self, session.cwd, self.colores, on_execute_cmd_callback=session.enviar_comando)
                dlg.exec()
                session.actualizar_info_git()
        elif chosen == act_open_folder:
            if session and os.path.exists(session.cwd):
                if platform.system() == "Windows":
                    os.startfile(session.cwd)
                else:
                    import subprocess
                    subprocess.Popen(["xdg-open", session.cwd])
        elif chosen == act_close:
            self.cerrar_pestana(index)
        elif chosen == act_close_others:
            for i in reversed(range(self.tab_widget.count())):
                if i != index:
                    self.cerrar_pestana(i)

    # ── Historial Persistente ─────────────────────────────────────────────
    def _cargar_historial_persistente(self):
        try:
            if self.ruta_history and self.ruta_history.exists():
                lines = self.ruta_history.read_text(encoding="utf-8").splitlines()
                self.history = [l for l in lines if l.strip()][-500:]
        except Exception:
            pass

    def _guardar_historial_persistente(self):
        try:
            if self.ruta_history:
                self.ruta_history.write_text("\n".join(self.history[-500:]), encoding="utf-8")
        except Exception:
            pass

    # ── Perfiles de Shell ────────────────────────────────────────────────
    def _detectar_perfiles_shell(self):
        perfiles = {}
        if platform.system() == "Windows":
            if shutil.which("powershell.exe"):
                perfiles["⚡ PowerShell"] = ("powershell.exe", ["-NoLogo", "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass"])
            if shutil.which("cmd.exe"):
                perfiles["🖥️ CMD"] = ("cmd.exe", ["/Q"])
            if shutil.which("bash"):
                perfiles["🐧 Git Bash"] = ("bash", ["-i"])
        else:
            if shutil.which("bash"):
                perfiles["🐧 Bash"] = ("bash", ["-i"])
            if shutil.which("zsh"):
                perfiles["🐍 Zsh"] = ("zsh", ["-i"])
        if not perfiles:
            perfiles["Default"] = ("bash", ["-i"])
        return perfiles

    def actualizar_tema(self, colores):
        """Sincroniza los colores del módulo con el tema global de la aplicación"""
        self.colores = colores
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.colores['bg_principal']};
                color: #FFFFFF;
                border: none;
            }}
            QToolTip {{
                background-color: {self.colores['bg_secundario']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-family: '{self.font_family}';
            }}
        """)
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background-color: {self.colores['bg_secundario']};
                color: #FFFFFF;
                padding: 6px 14px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.colores['acento']};
                color: #FFFFFF;
                font-weight: bold;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: rgba(255,255,255,0.15);
                color: #FFFFFF;
            }}
        """)
        if hasattr(self, 'snippets_panel') and hasattr(self.snippets_panel, 'actualizar_tema'):
            self.snippets_panel.actualizar_tema(colores)
        for i in range(self.tab_widget.count()):
            session = self.tab_widget.widget(i)
            if hasattr(session, 'actualizar_tema'):
                session.actualizar_tema(colores)

    def cleanup(self):
        """Finaliza limpiamente todas las sesiones y procesos de consola activos para evitar zombis."""
        try:
            for i in range(self.tab_widget.count()):
                w = self.tab_widget.widget(i)
                if hasattr(w, "cleanup"):
                    w.cleanup()
        except Exception:
            pass

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
