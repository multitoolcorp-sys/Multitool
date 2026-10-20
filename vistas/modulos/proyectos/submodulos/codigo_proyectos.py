"""
codigo_proyectos.py — Editor de Código / Code Studio estilo VS Code para Proyectos
Incluye explorador de archivos, pestañas múltiples, resaltado de sintaxis, números de línea y consola de ejecución.
"""
import os
import sys
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QPlainTextEdit, QTabWidget, QSplitter, QTreeView, QFileDialog,
    QMessageBox, QTextEdit, QToolButton, QMenu, QApplication
)
from PyQt6.QtCore import Qt, QSize, QRect, QProcess
from PyQt6.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter,
    QPainter, QTextFormat, QFileSystemModel, QIcon
)


# ── RESALTADOR DE SINTAXIS MULTI-LENGUAJE ─────────────────────────────────────
class CodeSyntaxHighlighter(QSyntaxHighlighter):
    """Resaltador de sintaxis versátil para Python, JavaScript, JSON, HTML, CSS y SQL."""
    def __init__(self, document, lang="python"):
        super().__init__(document)
        self.lang = lang.lower()
        self.rules = []
        self._setup_rules()

    def _setup_rules(self):
        self.rules.clear()

        # Palabras clave
        fmt_keyword = QTextCharFormat()
        fmt_keyword.setForeground(QColor("#C586C0"))  # Púrpura VS Code
        fmt_keyword.setFontWeight(QFont.Weight.Bold)

        keywords_py = [
            "and", "as", "assert", "async", "await", "break", "class", "continue",
            "def", "del", "elif", "else", "except", "finally", "for", "from",
            "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
            "or", "pass", "raise", "return", "try", "while", "with", "yield",
            "True", "False", "None", "self"
        ]
        keywords_js = [
            "function", "var", "let", "const", "return", "if", "else", "for",
            "while", "switch", "case", "break", "new", "this", "import", "export",
            "from", "default", "class", "extends", "async", "await", "try", "catch",
            "typeof", "null", "undefined", "true", "false"
        ]
        keywords_sql = [
            "SELECT", "FROM", "WHERE", "INSERT", "INTO", "UPDATE", "DELETE",
            "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "GROUP", "BY", "ORDER",
            "HAVING", "LIMIT", "CREATE", "TABLE", "DROP", "ALTER", "PRIMARY", "KEY"
        ]

        if self.lang in ("python", "py"):
            kw_list = keywords_py
        elif self.lang in ("javascript", "js", "ts", "typescript"):
            kw_list = keywords_js
        elif self.lang in ("sql", "sqlite"):
            kw_list = keywords_sql
        else:
            kw_list = keywords_py + keywords_js

        for kw in kw_list:
            pattern = re.compile(rf"\b{kw}\b", re.IGNORECASE if self.lang == "sql" else 0)
            self.rules.append((pattern, fmt_keyword))

        # Tipos y Builtins
        fmt_type = QTextCharFormat()
        fmt_type.setForeground(QColor("#4EC9B0"))  # Verde turquesa VS Code
        for t in ["int", "str", "float", "bool", "list", "dict", "tuple", "set", "object", "Promise", "Array", "String", "Number"]:
            self.rules.append((re.compile(rf"\b{t}\b"), fmt_type))

        # Strings (comillas dobles y simples)
        fmt_string = QTextCharFormat()
        fmt_string.setForeground(QColor("#CE9178"))  # Naranja marrón VS Code
        self.rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), fmt_string))
        self.rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), fmt_string))

        # Números
        fmt_number = QTextCharFormat()
        fmt_number.setForeground(QColor("#B5CEA8"))  # Verde claro VS Code
        self.rules.append((re.compile(r"\b\d+(\.\d+)?\b"), fmt_number))

        # Funciones
        fmt_func = QTextCharFormat()
        fmt_func.setForeground(QColor("#DCDCAA"))  # Amarillo VS Code
        self.rules.append((re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\()"), fmt_func))

        # Comentarios
        fmt_comment = QTextCharFormat()
        fmt_comment.setForeground(QColor("#6A9955"))  # Verde oliva comentarios VS Code
        fmt_comment.setFontItalic(True)
        self.rules.append((re.compile(r"#.*"), fmt_comment))
        self.rules.append((re.compile(r"//.*"), fmt_comment))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


# ── NÚMEROS DE LÍNEA EN EL EDITOR ─────────────────────────────────────────────
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditorWidget(QPlainTextEdit):
    """Editor de código con números de línea y estilos VS Code."""
    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.modificado = False

        self.setFont(QFont("Consolas", 10))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.textChanged.connect(self._on_text_changed)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        # Configurar resaltador según extensión
        lang = "python"
        if file_path:
            ext = Path(file_path).suffix.lower()
            lang = {"py": "python", "js": "javascript", "ts": "javascript", "json": "json", "sql": "sql", "html": "html", "css": "css"}.get(ext.strip("."), "python")
        self.highlighter = CodeSyntaxHighlighter(self.document(), lang=lang)

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                selection-background-color: #264F78;
                selection-color: #FFFFFF;
                line-height: 1.4;
            }
        """)

    def _on_text_changed(self):
        self.modificado = True

    def line_number_area_width(self):
        digits = 1
        max_b = max(1, self.blockCount())
        while max_b >= 10:
            max_b //= 10
            digits += 1
        space = 20 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#282828")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#1E1E1E"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                is_current = (block_number == self.textCursor().blockNumber())
                painter.setPen(QColor("#C6C6C6" if is_current else "#6E7681"))
                painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold if is_current else QFont.Weight.Normal))
                painter.drawText(0, top, self.line_number_area.width() - 8, self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1


# ── SUBMÓDULO PRINCIPAL: EDITOR DE CÓDIGO PROYECTOS ───────────────────────────
class TabEditorCodigoProyectos(QWidget):
    """Submódulo de Estudio de Código / Editor integrado estilo VS Code para Proyectos."""
    def __init__(self, parent=None, colores=None, callbacks=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.cb = callbacks or {}
        self.pid_activo = None
        self.ruta_raiz_proyecto = None
        self.editores_abiertos = {}  # ruta_str -> CodeEditorWidget
        self.proceso_run = None

        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Barra de Herramientas Superior ──
        tb = QFrame()
        tb.setFixedHeight(42)
        tb.setStyleSheet("background: #181818; border-bottom: 1px solid rgba(255,255,255,0.08);")
        tb_lay = QHBoxLayout(tb)
        tb_lay.setContentsMargins(12, 4, 12, 4)
        tb_lay.setSpacing(8)

        lbl_logo = QLabel("💻 CODE STUDIO")
        lbl_logo.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_logo.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        tb_lay.addWidget(lbl_logo)

        self.lbl_proyecto = QLabel("Proyecto: (Ninguno)")
        self.lbl_proyecto.setStyleSheet("color: #858585; font-size: 11px;")
        tb_lay.addWidget(self.lbl_proyecto)

        tb_lay.addStretch()

        btn_abrir_carpeta = QPushButton("📂 Abrir Carpeta")
        btn_abrir_carpeta.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_abrir_carpeta.setStyleSheet(self._btn_tb_style())
        btn_abrir_carpeta.clicked.connect(self._abrir_carpeta_dialogo)
        tb_lay.addWidget(btn_abrir_carpeta)

        btn_nuevo_archivo = QPushButton("📄 Nuevo Archivo")
        btn_nuevo_archivo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nuevo_archivo.setStyleSheet(self._btn_tb_style())
        btn_nuevo_archivo.clicked.connect(self._nuevo_archivo_dialogo)
        tb_lay.addWidget(btn_nuevo_archivo)

        btn_guardar = QPushButton("💾 Guardar (Ctrl+S)")
        btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guardar.setStyleSheet(self._btn_tb_style())
        btn_guardar.clicked.connect(self._guardar_archivo_actual)
        tb_lay.addWidget(btn_guardar)

        btn_run = QPushButton("▶️ Ejecutar Python")
        btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_run.setStyleSheet("background: #10B981; color: white; border: none; border-radius: 5px; padding: 5px 12px; font-weight: bold; font-size: 11px;")
        btn_run.clicked.connect(self._ejecutar_script_actual)
        tb_lay.addWidget(btn_run)

        lay.addWidget(tb)

        # ── Splitter Principal Horizontal (Sidebar vs Editor/Consola) ──
        self.splitter_h = QSplitter(Qt.Orientation.Horizontal)
        self.splitter_h.setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.06); }")

        # 1. Sidebar Izquierda: Árbol de Archivos
        sidebar = QFrame()
        sidebar.setMinimumWidth(200)
        sidebar.setMaximumWidth(360)
        sidebar.setStyleSheet("background: #181818; border-right: 1px solid rgba(255,255,255,0.06);")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(8, 8, 8, 8)
        sb_lay.setSpacing(6)

        sb_hdr = QHBoxLayout()
        lbl_exp = QLabel("EXPLORADOR")
        lbl_exp.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_exp.setStyleSheet("color: #BBBBBB; letter-spacing: 1px;")
        sb_hdr.addWidget(lbl_exp)
        sb_hdr.addStretch()

        btn_rf = QToolButton()
        btn_rf.setText("🔄")
        btn_rf.setStyleSheet("background: transparent; color: #888; border: none;")
        btn_rf.clicked.connect(self._refrescar_arbol)
        sb_hdr.addWidget(btn_rf)
        sb_lay.addLayout(sb_hdr)

        self.model_fs = QFileSystemModel()
        self.tree_fs = QTreeView()
        self.tree_fs.setModel(self.model_fs)
        self.tree_fs.setHeaderHidden(True)
        for col in [1, 2, 3]:
            self.tree_fs.hideColumn(col)
        self.tree_fs.setStyleSheet("""
            QTreeView {
                background: transparent; color: #CCCCCC; border: none;
                font-family: 'Segoe UI', sans-serif; font-size: 11px;
            }
            QTreeView::item:hover { background: rgba(255,255,255,0.05); }
            QTreeView::item:selected { background: #2A2D2E; color: white; }
        """)
        self.tree_fs.doubleClicked.connect(self._on_tree_item_double_clicked)
        sb_lay.addWidget(self.tree_fs, 1)

        self.splitter_h.addWidget(sidebar)

        # 2. Panel Derecho Vertical: Editor + Consola
        right_panel = QFrame()
        rp_lay = QVBoxLayout(right_panel)
        rp_lay.setContentsMargins(0, 0, 0, 0)
        rp_lay.setSpacing(0)

        self.splitter_v = QSplitter(Qt.Orientation.Vertical)
        self.splitter_v.setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.06); }")

        # Pestañas de archivos abiertos
        self.tabs_editor = QTabWidget()
        self.tabs_editor.setTabsClosable(True)
        self.tabs_editor.tabCloseRequested.connect(self._cerrar_pestana)
        self.tabs_editor.currentChanged.connect(self._on_pestana_cambiada)
        self.tabs_editor.setStyleSheet("""
            QTabWidget::pane { border: none; background: #1E1E1E; }
            QTabBar::tab {
                background: #181818; color: #969696; padding: 6px 14px;
                border-right: 1px solid rgba(255,255,255,0.05); font-size: 11px;
            }
            QTabBar::tab:selected { background: #1E1E1E; color: #FFFFFF; border-top: 2px solid #6366F1; }
        """)
        self.splitter_v.addWidget(self.tabs_editor)

        # Panel de Consola / Terminal
        console_panel = QFrame()
        console_panel.setStyleSheet("background: #181818; border-top: 1px solid rgba(255,255,255,0.06);")
        cp_lay = QVBoxLayout(console_panel)
        cp_lay.setContentsMargins(10, 6, 10, 6)
        cp_lay.setSpacing(4)

        cp_hdr = QHBoxLayout()
        lbl_cons = QLabel("TERMINAL / SALIDA DE EJECUCIÓN")
        lbl_cons.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        lbl_cons.setStyleSheet("color: #34D399;")
        cp_hdr.addWidget(lbl_cons)
        cp_hdr.addStretch()

        btn_clear_c = QPushButton("Limpiar")
        btn_clear_c.setStyleSheet("background: transparent; color: #888; border: none; font-size: 10px;")
        btn_clear_c.clicked.connect(lambda: self.txt_consola.clear())
        cp_hdr.addWidget(btn_clear_c)
        cp_lay.addLayout(cp_hdr)

        self.txt_consola = QTextEdit()
        self.txt_consola.setReadOnly(True)
        self.txt_consola.setFont(QFont("Consolas", 9))
        self.txt_consola.setStyleSheet("background: #141414; color: #D4D4D4; border: 1px solid rgba(255,255,255,0.05); border-radius: 4px; padding: 6px;")
        cp_lay.addWidget(self.txt_consola, 1)

        self.splitter_v.addWidget(console_panel)
        self.splitter_v.setSizes([450, 150])

        rp_lay.addWidget(self.splitter_v)
        self.splitter_h.addWidget(right_panel)
        self.splitter_h.setSizes([220, 780])

        lay.addWidget(self.splitter_h, 1)

        # ── Barra de Estado Inferior estilo VS Code ──
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(24)
        self.status_bar.setStyleSheet("background: #007ACC; color: white;")
        sb_lay_b = QHBoxLayout(self.status_bar)
        sb_lay_b.setContentsMargins(12, 0, 12, 0)
        sb_lay_b.setSpacing(16)

        self.lbl_st_branch = QLabel("🔀 main")
        self.lbl_st_branch.setStyleSheet("color: white; font-size: 10px; font-weight: bold;")
        sb_lay_b.addWidget(self.lbl_st_branch)

        self.lbl_st_status = QLabel("Listo")
        self.lbl_st_status.setStyleSheet("color: white; font-size: 10px;")
        sb_lay_b.addWidget(self.lbl_st_status)

        sb_lay_b.addStretch()

        self.lbl_st_pos = QLabel("Ln 1, Col 1")
        self.lbl_st_pos.setStyleSheet("color: white; font-size: 10px;")
        sb_lay_b.addWidget(self.lbl_st_pos)

        self.lbl_st_encoding = QLabel("UTF-8")
        self.lbl_st_encoding.setStyleSheet("color: white; font-size: 10px;")
        sb_lay_b.addWidget(self.lbl_st_encoding)

        self.lbl_st_lang = QLabel("Python")
        self.lbl_st_lang.setStyleSheet("color: white; font-size: 10px; font-weight: bold;")
        sb_lay_b.addWidget(self.lbl_st_lang)

        lay.addWidget(self.status_bar)

    def _btn_tb_style(self):
        return """
            QPushButton {
                background: rgba(255,255,255,0.06); color: #E0E0E0;
                border: 1px solid rgba(255,255,255,0.1); border-radius: 5px;
                padding: 4px 10px; font-size: 11px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.12); color: white; }
        """

    def configurar_proyecto(self, proyecto_dict):
        """Asocia y prepara el explorador para el proyecto activo."""
        if isinstance(proyecto_dict, str):
            if "get_proyectos" in self.cb:
                proys = self.cb["get_proyectos"]()
                proyecto_dict = next((x for x in proys if x["id"] == proyecto_dict), None)
            else:
                proyecto_dict = None

        if not proyecto_dict:
            self.pid_activo = None
            self.lbl_proyecto.setText("Proyecto: (Ninguno seleccionado)")
            return

        self.pid_activo = proyecto_dict["id"]
        nombre = proyecto_dict.get("nombre", "Proyecto")
        self.lbl_proyecto.setText(f"Proyecto: {nombre}")

        # Determinar carpeta de código (o carpeta por defecto del usuario/proyectos/nombre)
        carpeta = proyecto_dict.get("carpeta_codigo")
        if not carpeta or not Path(carpeta).exists():
            base_u = getattr(self.parent(), "ruta_usuario", None)
            if not base_u:
                base_u = Path.home() / ".multitool"
            ruta_defecto = Path(base_u) / "workspace_codigo" / nombre
            try:
                ruta_defecto.mkdir(parents=True, exist_ok=True)
                carpeta = str(ruta_defecto)
                proyecto_dict["carpeta_codigo"] = carpeta
                if "guardar_datos" in self.cb:
                    self.cb["guardar_datos"]()
            except Exception:
                carpeta = str(Path.cwd())

        self.cargar_carpeta(carpeta)

    def cargar_carpeta(self, ruta_dir):
        p = Path(ruta_dir)
        if not p.exists():
            return
        self.ruta_raiz_proyecto = str(p)
        self.model_fs.setRootPath(self.ruta_raiz_proyecto)
        self.tree_fs.setRootIndex(self.model_fs.index(self.ruta_raiz_proyecto))

        # Crear archivo main.py de muestra si la carpeta está vacía
        main_py = p / "main.py"
        if not any(p.iterdir()):
            main_py.write_text("# Código fuente del proyecto\n\ndef main():\n    print('¡Hola desde Code Studio Multitool!')\n\nif __name__ == '__main__':\n    main()\n", encoding="utf-8")

        if main_py.exists() and self.tabs_editor.count() == 0:
            self.abrir_archivo(str(main_py))

    def _refrescar_arbol(self):
        if self.ruta_raiz_proyecto:
            self.model_fs.setRootPath(self.ruta_raiz_proyecto)
            self.tree_fs.setRootIndex(self.model_fs.index(self.ruta_raiz_proyecto))

    def _abrir_carpeta_dialogo(self):
        d = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Código", self.ruta_raiz_proyecto or "")
        if d:
            self.cargar_carpeta(d)
            if self.pid_activo and "get_proyectos" in self.cb:
                proys = self.cb["get_proyectos"]()
                p = next((x for x in proys if x["id"] == self.pid_activo), None)
                if p:
                    p["carpeta_codigo"] = d
                    if "guardar_datos" in self.cb:
                        self.cb["guardar_datos"]()

    def _nuevo_archivo_dialogo(self):
        if not self.ruta_raiz_proyecto:
            QMessageBox.information(self, "Aviso", "Primero abre o selecciona una carpeta de proyecto.")
            return
        from PyQt6.QtWidgets import QInputDialog
        nombre, ok = QInputDialog.getText(self, "Nuevo Archivo", "Nombre del archivo (ej: script.py, index.html):")
        if ok and nombre.strip():
            dest = Path(self.ruta_raiz_proyecto) / nombre.strip()
            dest.touch(exist_ok=True)
            self._refrescar_arbol()
            self.abrir_archivo(str(dest))

    def _on_tree_item_double_clicked(self, index):
        path = self.model_fs.filePath(index)
        if os.path.isfile(path):
            self.abrir_archivo(path)

    def abrir_archivo(self, file_path):
        fpath = str(Path(file_path).resolve())
        if fpath in self.editores_abiertos:
            idx = self.tabs_editor.indexOf(self.editores_abiertos[fpath])
            if idx >= 0:
                self.tabs_editor.setCurrentIndex(idx)
                return

        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                contenido = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Error al abrir", f"No se pudo leer el archivo:\n{e}")
            return

        editor = CodeEditorWidget(file_path=fpath, parent=self)
        editor.setPlainText(contenido)
        editor.modificado = False
        editor.cursorPositionChanged.connect(self._actualizar_cursor_status)

        fname = Path(fpath).name
        tab_idx = self.tabs_editor.addTab(editor, fname)
        self.editores_abiertos[fpath] = editor
        self.tabs_editor.setCurrentIndex(tab_idx)
        self._on_pestana_cambiada(tab_idx)

    def _guardar_archivo_actual(self):
        cur = self.tabs_editor.currentWidget()
        if not isinstance(cur, CodeEditorWidget) or not cur.file_path:
            return
        try:
            with open(cur.file_path, "w", encoding="utf-8") as f:
                f.write(cur.toPlainText())
            cur.modificado = False
            fname = Path(cur.file_path).name
            idx = self.tabs_editor.currentIndex()
            self.tabs_editor.setTabText(idx, fname)
            self.lbl_st_status.setText(f"Guardado: {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", f"No se pudo guardar el archivo:\n{e}")

    def _cerrar_pestana(self, idx):
        widget = self.tabs_editor.widget(idx)
        if isinstance(widget, CodeEditorWidget):
            if widget.modificado:
                r = QMessageBox.question(self, "Guardar cambios", f"¿Deseas guardar cambios antes de cerrar '{Path(widget.file_path).name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
                if r == QMessageBox.StandardButton.Cancel:
                    return
                if r == QMessageBox.StandardButton.Yes:
                    self._guardar_archivo_actual()

            fpath = str(Path(widget.file_path).resolve())
            if fpath in self.editores_abiertos:
                del self.editores_abiertos[fpath]
        self.tabs_editor.removeTab(idx)

    def _on_pestana_cambiada(self, idx):
        cur = self.tabs_editor.widget(idx)
        if isinstance(cur, CodeEditorWidget) and cur.file_path:
            ext = Path(cur.file_path).suffix.lower().replace(".", "")
            self.lbl_st_lang.setText(ext.upper() if ext else "TEXT")
            self._actualizar_cursor_status()

    def _actualizar_cursor_status(self):
        cur = self.tabs_editor.currentWidget()
        if isinstance(cur, CodeEditorWidget):
            cursor = cur.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.lbl_st_pos.setText(f"Ln {line}, Col {col}")

    def _ejecutar_script_actual(self):
        cur = self.tabs_editor.currentWidget()
        if not isinstance(cur, CodeEditorWidget) or not cur.file_path:
            QMessageBox.information(self, "Aviso", "Abre un script para ejecutarlo.")
            return

        self._guardar_archivo_actual()
        fpath = cur.file_path

        if not fpath.endswith(".py"):
            QMessageBox.information(self, "Ejecutar", f"El archivo '{Path(fpath).name}' no es un script de Python ejecutable.")
            return

        self.txt_consola.append(f"\n[RUN] python \"{fpath}\"\n" + "-"*40)
        self.lbl_st_status.setText("Ejecutando script...")

        if self.proceso_run and self.proceso_run.state() == QProcess.ProcessState.Running:
            self.proceso_run.kill()

        self.proceso_run = QProcess(self)
        self.proceso_run.setWorkingDirectory(str(Path(fpath).parent))
        self.proceso_run.readyReadStandardOutput.connect(self._on_stdout_disponible)
        self.proceso_run.readyReadStandardError.connect(self._on_stderr_disponible)
        self.proceso_run.finished.connect(self._on_proceso_terminado)
        self.proceso_run.start(sys.executable, ["-u", fpath])

    def _on_stdout_disponible(self):
        if self.proceso_run:
            salida = bytes(self.proceso_run.readAllStandardOutput()).decode("utf-8", errors="replace")
            self.txt_consola.insertPlainText(salida)

    def _on_stderr_disponible(self):
        if self.proceso_run:
            err = bytes(self.proceso_run.readAllStandardError()).decode("utf-8", errors="replace")
            self.txt_consola.insertPlainText(err)

    def _on_proceso_terminado(self, code, status):
        self.txt_consola.append(f"\n[FIN] Proceso terminado con código {code}.\n")
        self.lbl_st_status.setText("Ejecución finalizada")

    def actualizar_tema(self, colores):
        self.colores = colores

    def cleanup(self):
        if self.proceso_run and self.proceso_run.state() == QProcess.ProcessState.Running:
            self.proceso_run.kill()
