import os
import platform
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTabWidget, QTextBrowser, QTreeWidget, QTreeWidgetItem, 
    QComboBox, QFrame, QInputDialog, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from ..utils.git_utils import (
    es_repositorio_git, obtener_estado_git, obtener_grafo_git, 
    obtener_ramas_git, obtener_status_archivos, ejecutar_comando_git
)
from ..utils.ansi_parser import AnsiParser

class GitViewerDialog(QDialog):
    """Visor gráfico avanzado de ramas, historial de commits y estado de Git"""
    def __init__(self, parent, cwd, colores, on_execute_cmd_callback=None):
        super().__init__(parent)
        self.cwd = cwd or os.getcwd()
        self.colores = colores
        self.on_execute_cmd = on_execute_cmd_callback
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.ansi_parser = AnsiParser(default_fg=self.colores.get("fg_principal", "#E2E2E2"), default_bg="#090d16")
        
        self.setWindowTitle("🌿 Explorador Visual de Git")
        self.resize(850, 580)
        self.inicializar_ui()
        self.cargar_datos()

    def inicializar_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores['bg_principal']};
                color: #FFFFFF;
            }}
            QTabWidget::pane {{
                border: 1px solid rgba(255, 255, 255, 0.06);
                background-color: {self.colores['bg_secundario']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                padding: 7px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: 600;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.colores['acento']};
                color: #FFFFFF;
            }}
        """)
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(16, 16, 16, 16)
        main_lay.setSpacing(10)

        # ── 1. Cabecera Informativa de Repositorio ──
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 8px 12px;
            }}
        """)
        h_lay = QHBoxLayout(hdr_frame)
        h_lay.setContentsMargins(8, 4, 8, 4)
        h_lay.setSpacing(10)

        self.lbl_repo_title = QLabel(f"📁 <b>{os.path.basename(self.cwd)}</b>")
        self.lbl_repo_title.setFont(QFont(self.font_family, 10))
        self.lbl_repo_title.setStyleSheet("color: white;")
        h_lay.addWidget(self.lbl_repo_title)

        self.badge_rama = QLabel("🌿 Rama: -")
        self.badge_rama.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.badge_rama.setStyleSheet(f"""
            background-color: {self.colores['acento']}22;
            color: {self.colores['acento']};
            border: 1px solid {self.colores['acento']}66;
            border-radius: 4px;
            padding: 3px 8px;
        """)
        h_lay.addWidget(self.badge_rama)

        self.badge_status = QLabel("Estado: -")
        self.badge_status.setFont(QFont(self.font_family, 9))
        self.badge_status.setStyleSheet("color: #10B981; padding: 3px 6px;")
        h_lay.addWidget(self.badge_status)

        h_lay.addStretch()

        # Selector rápido de rama
        lbl_switch = QLabel("Cambiar Rama:")
        lbl_switch.setFont(QFont(self.font_family, 8))
        lbl_switch.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#888')};")
        h_lay.addWidget(lbl_switch)

        self.combo_ramas = QComboBox()
        self.combo_ramas.setFixedWidth(160)
        self.combo_ramas.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border-radius: 6px; padding: 4px 8px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
            }}
        """)
        self.combo_ramas.currentTextChanged.connect(self._on_rama_seleccionada)
        h_lay.addWidget(self.combo_ramas)

        btn_nueva_rama = QPushButton("➕ Rama")
        btn_nueva_rama.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nueva_rama.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_nueva_rama.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']}; color: white;
                border-radius: 5px; padding: 4px 10px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento']}cc; }}
        """)
        btn_nueva_rama.clicked.connect(self._crear_nueva_rama)
        h_lay.addWidget(btn_nueva_rama)

        main_lay.addWidget(hdr_frame)

        # ── 2. Pestañas de Visualización ──
        self.tabs = QTabWidget()

        # Tab 1: Gráfico de Árbol de Commits
        tab_grafo = QFrame()
        lay_g = QVBoxLayout(tab_grafo)
        lay_g.setContentsMargins(10, 10, 10, 10)
        lay_g.setSpacing(8)

        g_ctrl = QHBoxLayout()
        lbl_g_info = QLabel("Visualización de Ramas y Commits (git log --graph)")
        lbl_g_info.setFont(QFont(self.font_family, 8))
        lbl_g_info.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAA')};")
        g_ctrl.addWidget(lbl_g_info)
        g_ctrl.addStretch()

        btn_refrescar_g = QPushButton("🔄 Actualizar")
        btn_refrescar_g.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refrescar_g.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; padding: 4px 10px; border-radius: 4px;")
        btn_refrescar_g.clicked.connect(self.cargar_datos)
        g_ctrl.addWidget(btn_refrescar_g)
        lay_g.addLayout(g_ctrl)

        self.txt_grafo = QTextBrowser()
        self.txt_grafo.setFont(QFont(self.mono_font, 10))
        self.txt_grafo.setStyleSheet("""
            QTextBrowser {
                background-color: #080c14;
                color: #C5D1DE;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
                padding: 10px;
            }
        """)
        lay_g.addWidget(self.txt_grafo, 1)
        self.tabs.addTab(tab_grafo, "🌳 Árbol de Ramas")

        # Tab 2: Archivos Modificados y Diff
        tab_cambios = QFrame()
        lay_c = QVBoxLayout(tab_cambios)
        lay_c.setContentsMargins(10, 10, 10, 10)
        
        split_cambios = QSplitter(Qt.Orientation.Horizontal)
        
        # Lista de archivos
        self.tree_archivos = QTreeWidget()
        self.tree_archivos.setHeaderLabels(["Estado", "Archivo"])
        self.tree_archivos.setColumnWidth(0, 70)
        self.tree_archivos.setFont(QFont(self.mono_font, 9))
        self.tree_archivos.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: none; border-radius: 6px;
            }}
            QTreeWidget::item:selected {{ background-color: {self.colores['acento']}; }}
        """)
        self.tree_archivos.itemClicked.connect(self._mostrar_diff_archivo)
        split_cambios.addWidget(self.tree_archivos)

        # Visor de Diff
        self.txt_diff = QTextBrowser()
        self.txt_diff.setFont(QFont(self.mono_font, 9))
        self.txt_diff.setStyleSheet("background-color: #080c14; color: #E2E2E2; border: none; border-radius: 6px; padding: 8px;")
        split_cambios.addWidget(self.txt_diff)
        split_cambios.setStretchFactor(0, 1)
        split_cambios.setStretchFactor(1, 2)

        lay_c.addWidget(split_cambios)
        self.tabs.addTab(tab_cambios, "📝 Cambios Pendientes")

        main_lay.addWidget(self.tabs, 1)

        # ── 3. Barra de Acciones Rápidas (Pull, Push, Fetch, Commit) ──
        act_bar = QHBoxLayout()
        act_bar.setSpacing(8)

        def _crear_act_btn(texto, cmd_args, tool_name):
            btn = QPushButton(texto)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colores['bg_secundario']}; color: white;
                    border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 6px 12px;
                }}
                QPushButton:hover {{
                    background-color: {self.colores['acento']}33;
                    border-color: {self.colores['acento']};
                }}
            """)
            btn.clicked.connect(lambda: self._ejecutar_accion_git(cmd_args, tool_name))
            return btn

        act_bar.addWidget(_crear_act_btn("📥 Pull", ["pull"], "git pull"))
        act_bar.addWidget(_crear_act_btn("📤 Push", ["push"], "git push"))
        act_bar.addWidget(_crear_act_btn("🔄 Fetch", ["fetch", "--all"], "git fetch"))
        act_bar.addWidget(_crear_act_btn("📦 Stash", ["stash"], "git stash"))
        act_bar.addStretch()

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFont(QFont(self.font_family, 9))
        btn_cerrar.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; padding: 6px 16px; border-radius: 6px;")
        btn_cerrar.clicked.connect(self.accept)
        act_bar.addWidget(btn_cerrar)

        main_lay.addLayout(act_bar)

    def cargar_datos(self):
        """Lee y renderiza la información de git en tiempo real"""
        if not es_repositorio_git(self.cwd):
            self.badge_rama.setText("⚠️ No es un repositorio Git")
            self.badge_status.setText("Abre una carpeta con Git inicializado")
            self.txt_grafo.setPlainText("El directorio activo no contiene un repositorio Git (.git).\n\nPuedes inicializarlo escribiendo 'git init' en la terminal.")
            return

        estado = obtener_estado_git(self.cwd)
        self.badge_rama.setText(f"🌿 Rama: {estado['rama']}")
        
        # Estado resumen
        if estado["es_limpio"]:
            self.badge_status.setText("✅ Repositorio Limpio")
            self.badge_status.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            total_cambios = estado["modificados"] + estado["staged"] + estado["untracked"]
            self.badge_status.setText(f"⚠️ {total_cambios} archivos con cambios")
            self.badge_status.setStyleSheet("color: #F59E0B; font-weight: bold;")

        # Ramas disponibles
        ramas = obtener_ramas_git(self.cwd)
        self.combo_ramas.blockSignals(True)
        self.combo_ramas.clear()
        idx_actual = 0
        for i, r in enumerate(ramas):
            nombre = r["nombre"]
            self.combo_ramas.addItem(f"{'● ' if r['actual'] else '  '}{nombre}", nombre)
            if r["actual"]:
                idx_actual = i
        self.combo_ramas.setCurrentIndex(idx_actual)
        self.combo_ramas.blockSignals(False)

        # Grafo de commits
        grafo_ansi = obtener_grafo_git(self.cwd, max_commits=45)
        self.txt_grafo.clear()
        if grafo_ansi:
            self.ansi_parser.append_ansi_text(self.txt_grafo, grafo_ansi, default_fg="#C5D1DE")
        else:
            self.txt_grafo.setPlainText("(Aún no hay commits en este repositorio)")

        # Cambios pendientes
        self.tree_archivos.clear()
        cambios = obtener_status_archivos(self.cwd)
        if not cambios:
            item_limpio = QTreeWidgetItem(self.tree_archivos)
            item_limpio.setText(0, "✓")
            item_limpio.setText(1, "Árbol de trabajo limpio")
            item_limpio.setForeground(0, QColor("#10B981"))
            self.txt_diff.setPlainText("No hay cambios pendientes en los archivos.")
        else:
            for cod, ruta in cambios:
                item = QTreeWidgetItem(self.tree_archivos)
                item.setText(0, cod)
                item.setText(1, ruta)
                if "M" in cod: item.setForeground(0, QColor("#3B82F6"))
                elif "A" in cod or "?" in cod: item.setForeground(0, QColor("#10B981"))
                elif "D" in cod: item.setForeground(0, QColor("#EF4444"))
                else: item.setForeground(0, QColor("#F59E0B"))

    def _mostrar_diff_archivo(self, item, col):
        ruta = item.text(1)
        if not ruta or ruta == "Árbol de trabajo limpio":
            return
        exito, salida = ejecutar_comando_git(self.cwd, ["diff", ruta])
        if exito and salida:
            self.txt_diff.clear()
            for line in salida.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    self.txt_diff.append(f"<span style='color: #10B981;'>{line}</span>")
                elif line.startswith("-") and not line.startswith("---"):
                    self.txt_diff.append(f"<span style='color: #EF4444;'>{line}</span>")
                elif line.startswith("@@"):
                    self.txt_diff.append(f"<span style='color: #6366F1;'>{line}</span>")
                else:
                    self.txt_diff.append(f"<span style='color: #9CA3AF;'>{line}</span>")
        else:
            self.txt_diff.setPlainText(f"(Sin diferencias en buffer para {ruta})")

    def _on_rama_seleccionada(self, text):
        rama = self.combo_ramas.currentData()
        if not rama:
            return
        if rama.startswith("remotes/"):
            rama = rama.split("/")[-1]
        
        exito, salida = ejecutar_comando_git(self.cwd, ["checkout", rama])
        if exito:
            self.cargar_datos()
        else:
            QMessageBox.warning(self, "Git Checkout", f"No se pudo cambiar a la rama '{rama}':\n\n{salida}")

    def _crear_nueva_rama(self):
        nombre, ok = QInputDialog.getText(self, "Nueva Rama Git", "Nombre de la nueva rama:")
        if ok and nombre.strip():
            nombre = nombre.strip().replace(" ", "-")
            exito, salida = ejecutar_comando_git(self.cwd, ["checkout", "-b", nombre])
            if exito:
                self.cargar_datos()
            else:
                QMessageBox.critical(self, "Error Creando Rama", salida)

    def _ejecutar_accion_git(self, cmd_args, display_name):
        exito, salida = ejecutar_comando_git(self.cwd, cmd_args)
        if exito:
            QMessageBox.information(self, f"Git {cmd_args[0].capitalize()}", salida or f"Acción '{display_name}' completada con éxito.")
            self.cargar_datos()
        else:
            QMessageBox.critical(self, f"Error en Git {cmd_args[0]}", salida or "Ocurrió un error al ejecutar la acción.")
