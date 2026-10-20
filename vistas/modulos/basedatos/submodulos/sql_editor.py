"""
sql_editor.py - Editor y consola SQL interactiva con coloreado de sintaxis estilo DBeaver
"""
import re
from typing import Tuple, List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QPlainTextEdit, QMenu, QSplitter, QListWidget, QListWidgetItem,
    QFrame, QCompleter, QStyledItemDelegate, QStyle
)
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QKeySequence, QShortcut,
    QTextCursor, QPainter, QStandardItemModel, QStandardItem, QBrush, QPen
)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel, QRect, QSize, QModelIndex
from .terminal_console import SqlTerminalWidget


class SqlSyntaxHighlighter(QSyntaxHighlighter):
    """Resaltador de sintaxis SQL moderno y de alto contraste"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = []

        # Palabras clave SQL (Azul / Cian brillante)
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#60A5FA"))  # Tailwind Blue 400
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            r"\bSELECT\b", r"\bFROM\b", r"\bWHERE\b", r"\bAND\b", r"\bOR\b", r"\bNOT\b",
            r"\bINSERT\b", r"\bINTO\b", r"\bVALUES\b", r"\bUPDATE\b", r"\bSET\b", r"\bDELETE\b",
            r"\bCREATE\b", r"\bTABLE\b", r"\bVIEW\b", r"\bINDEX\b", r"\bDROP\b", r"\bALTER\b",
            r"\bJOIN\b", r"\bLEFT\b", r"\bRIGHT\b", r"\bINNER\b", r"\bOUTER\b", r"\bCROSS\b",
            r"\bON\b", r"\bAS\b", r"\bORDER\b", r"\bBY\b", r"\bGROUP\b", r"\bHAVING\b",
            r"\bLIMIT\b", r"\bOFFSET\b", r"\bDISTINCT\b", r"\bUNION\b", r"\bALL\b",
            r"\bCASE\b", r"\bWHEN\b", r"\bTHEN\b", r"\bELSE\b", r"\bEND\b",
            r"\bPRAGMA\b", r"\bPRIMARY\b", r"\bKEY\b", r"\bFOREIGN\b", r"\bREFERENCES\b",
            r"\bDEFAULT\b", r"\bNULL\b", r"\bIS\b", r"\bIN\b", r"\bLIKE\b", r"\bEXISTS\b",
            r"\bAUTOINCREMENT\b", r"\bUNIQUE\b", r"\bCHECK\b"
        ]
        for kw in keywords:
            self.rules.append((re.compile(kw, re.IGNORECASE), keyword_format))

        # Tipos de datos (Púrpura / Violeta claro)
        type_format = QTextCharFormat()
        type_format.setForeground(QColor("#C084FC"))  # Purple 400
        types = [
            r"\bINTEGER\b", r"\bINT\b", r"\bTEXT\b", r"\bVARCHAR\b", r"\bCHAR\b",
            r"\bREAL\b", r"\bFLOAT\b", r"\bDOUBLE\b", r"\bNUMERIC\b", r"\bDECIMAL\b",
            r"\bBLOB\b", r"\bBOOLEAN\b", r"\bDATE\b", r"\bDATETIME\b", r"\bTIMESTAMP\b"
        ]
        for t in types:
            self.rules.append((re.compile(t, re.IGNORECASE), type_format))

        # Funciones de agregación y útiles (Amarillo dorado)
        func_format = QTextCharFormat()
        func_format.setForeground(QColor("#FBBF24"))  # Amber 400
        funcs = [
            r"\bCOUNT\b", r"\bSUM\b", r"\bAVG\b", r"\bMIN\b", r"\bMAX\b",
            r"\bCOALESCE\b", r"\bIFNULL\b", r"\bNULLIF\b", r"\bUPPER\b", r"\bLOWER\b",
            r"\bLENGTH\b", r"\bSUBSTR\b", r"\bREPLACE\b", r"\bTRIM\b", r"\bROUND\b",
            r"\bSTRFTIME\b", r"\bDATE\b", r"\bTIME\b"
        ]
        for f in funcs:
            self.rules.append((re.compile(f, re.IGNORECASE), func_format))

        # Números (Naranja suave)
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#FB923C"))  # Orange 400
        self.rules.append((re.compile(r"\b\d+(\.\d+)?\b"), number_format))

        # Cadenas entre comillas simples o dobles (Verde esmeralda)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#34D399"))  # Emerald 400
        self.rules.append((re.compile(r"'(?:\\.|[^'\\])*'"), string_format))
        self.rules.append((re.compile(r'"(?:\\.|[^"\\])*"'), string_format))

        # Comentarios en línea: -- comentario (Gris)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#94A3B8"))  # Slate 400
        comment_format.setFontItalic(True)
        self.rules.append((re.compile(r"--[^\n]*"), comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


# Categorías de tokens SQL para autocompletado inteligente
SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "INSERT INTO", "VALUES", "UPDATE", "SET",
    "DELETE FROM", "CREATE TABLE", "DROP TABLE", "ALTER TABLE", "ADD COLUMN",
    "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "CROSS JOIN", "ON",
    "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "OFFSET", "DISTINCT", "AS",
    "UNION", "UNION ALL", "AND", "OR", "NOT", "IN", "BETWEEN", "LIKE", "IS NULL",
    "IS NOT NULL", "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END",
    "PRIMARY KEY", "FOREIGN KEY", "REFERENCES", "AUTOINCREMENT", "DEFAULT",
    "INTEGER", "TEXT", "VARCHAR", "BOOLEAN", "TIMESTAMP", "REAL", "BLOB",
    "PRAGMA", "SHOW TABLES", "SHOW DATABASES", "DESCRIBE", "EXPLAIN", "USE"
]

SQL_FUNCTIONS = [
    "COUNT", "SUM", "AVG", "MIN", "MAX", "COALESCE", "UPPER", "LOWER", "LENGTH",
    "SUBSTR", "REPLACE", "TRIM", "ROUND", "IFNULL", "NULLIF", "STRFTIME", "NOW"
]

SQL_SNIPPETS = [
    {"name": "SELECT * FROM ... LIMIT 50;", "insert": "SELECT * FROM  LIMIT 50;", "cursor_offset": -10},
    {"name": "SELECT COUNT(*) FROM ...;", "insert": "SELECT COUNT(*) AS total FROM ;", "cursor_offset": -1},
    {"name": "INSERT INTO ... VALUES (...);", "insert": "INSERT INTO  () VALUES ();", "cursor_offset": -13},
    {"name": "UPDATE ... SET ... WHERE ...;", "insert": "UPDATE  SET  =  WHERE ;", "cursor_offset": -14},
    {"name": "DELETE FROM ... WHERE ...;", "insert": "DELETE FROM  WHERE ;", "cursor_offset": -8},
    {"name": "CREATE TABLE ... (id INT PK...);", "insert": "CREATE TABLE IF NOT EXISTS  (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    nombre TEXT NOT NULL\n);", "cursor_offset": -50}
]


class SqlCompletionDelegate(QStyledItemDelegate):
    """Delegado personalizado que renderiza elementos de autocompletado con dos columnas e insignias (Badges)"""
    def __init__(self, colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores

    def paint(self, painter: QPainter, option, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)

        # Fondo del elemento
        bg_color = QColor(self.colores.get("acento", "#6366F1")) if is_selected else QColor(self.colores.get("bg_secundario", "#1E1E2E"))
        painter.fillRect(rect, bg_color)

        # Datos del elemento
        meta = index.data(Qt.ItemDataRole.UserRole) or {}
        display_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        category = meta.get("category", "KEYWORD")
        badge_bg = meta.get("badge_bg", "#3B82F6")
        badge_fg = meta.get("badge_fg", "#FFFFFF")
        icon = meta.get("icon", "🔤")

        # 1. Columna Izquierda: Icono y Nombre
        font = QFont("Consolas", 10)
        painter.setFont(font)
        text_color = QColor("#FFFFFF") if is_selected else QColor("#F8FAFC")
        painter.setPen(text_color)

        left_text = f"{icon} {display_text}"
        text_rect = QRect(rect.left() + 8, rect.top(), rect.width() - 100, rect.height())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, left_text)

        # 2. Columna Derecha: Badge / Pastilla de Categoría
        badge_w = 70
        badge_h = 16
        badge_rect = QRect(rect.right() - badge_w - 8, rect.top() + (rect.height() - badge_h) // 2, badge_w, badge_h)

        badge_color = QColor(badge_bg)
        if is_selected:
            badge_color = badge_color.lighter(115)
        
        painter.setBrush(QBrush(badge_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, 4, 4)

        # Texto del badge
        badge_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(badge_font)
        painter.setPen(QColor(badge_fg))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, category)

        painter.restore()

    def sizeHint(self, option, index: QModelIndex) -> QSize:
        return QSize(option.rect.width(), 26)


class SqlCodeEditor(QPlainTextEdit):
    """Editor de código SQL con soporte para autocompletado inteligente contextual (IntelliSense)"""
    def __init__(self, colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.tables: List[str] = []
        self.columns: List[str] = []
        self.table_columns_map: Dict[str, List[str]] = {}

        self.model = QStandardItemModel(self)
        self.completer = QCompleter(self.model, self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self._insert_completion)

        self.completer.setMaxVisibleItems(8)

        popup = self.completer.popup()
        popup.setMinimumHeight(200)
        popup.setMinimumWidth(320)
        popup.setItemDelegate(SqlCompletionDelegate(self.colores, popup))
        popup.setStyleSheet(f"""
            QListView {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #F1F5F9;
                border: 1px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 6px;
                padding: 4px;
                font-family: Consolas;
                font-size: 11px;
                outline: none;
            }}
            QScrollBar:vertical {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 3px;
            }}
        """)

        self._current_dot_qualifier = ""
        self._construir_candidatos_base()

    def _construir_candidatos_base(self):
        """Inicializa los candidatos fijos de palabras clave, funciones y snippets"""
        self.base_candidates = []
        for kw in SQL_KEYWORDS:
            self.base_candidates.append({
                "name": kw, "category": "KEYWORD", "icon": "🔤",
                "badge_bg": "#2563EB", "badge_fg": "#FFFFFF", "insert": kw + " "
            })
        for fn in SQL_FUNCTIONS:
            self.base_candidates.append({
                "name": fn, "category": "FUNCIÓN", "icon": "⚡",
                "badge_bg": "#D97706", "badge_fg": "#FFFFFF", "insert": fn + "()"
            })
        for sn in SQL_SNIPPETS:
            self.base_candidates.append({
                "name": sn["name"], "category": "SNIPPET", "icon": "📝",
                "badge_bg": "#059669", "badge_fg": "#FFFFFF", "insert": sn["insert"],
                "cursor_offset": sn.get("cursor_offset", 0)
            })

    def update_dictionary(self, tables: list, columns: list, table_columns_map: dict = None):
        """Actualiza el catálogo de tablas, columnas y esquema de relaciones para el autocompletado"""
        self.tables = [t for t in tables if t]
        self.columns = [c for c in columns if c]
        if table_columns_map:
            self.table_columns_map = table_columns_map
        else:
            self.table_columns_map = {}

    def _detectar_contexto_y_calificador(self) -> Tuple[str, str, str]:
        """
        Analiza el texto anterior al cursor para determinar:
        1. Si hay un calificador de tabla (ej: 'usuarios.' -> calificador='usuarios')
        2. El contexto semántico ('TABLE', 'COLUMN_FUNC', 'GENERAL')
        3. El prefijo activo a completar
        """
        tc = self.textCursor()
        block_text = tc.block().text()
        pos_in_block = tc.positionInBlock()
        preceding = block_text[:pos_in_block]

        # 1. Detectar trigger por punto (ej: 'tabla.col' o 't.')
        dot_match = re.search(r'([a-zA-Z0-9_`"]+)\.([a-zA-Z0-9_]*)$', preceding)
        if dot_match:
            qualifier = dot_match.group(1).strip('`"')
            prefix = dot_match.group(2)
            return "DOT", qualifier, prefix

        # 2. Obtener prefijo de palabra normal
        word_match = re.search(r'([a-zA-Z0-9_]+)$', preceding)
        prefix = word_match.group(1) if word_match else ""

        # 3. Detectar contexto semántico por la última palabra clave SQL
        before_prefix = preceding[:-len(prefix)] if prefix else preceding
        upper_before = before_prefix.upper().strip()

        # Si termina o precede con FROM, JOIN, INTO, UPDATE, TABLE
        if re.search(r'\b(FROM|JOIN|INTO|UPDATE|TABLE|DESCRIBE)\s*$', upper_before):
            return "TABLE", "", prefix

        # Si termina o precede con SELECT, WHERE, ON, ORDER BY, GROUP BY, SET, HAVING
        if re.search(r'\b(SELECT|WHERE|ON|BY|SET|HAVING|AND|OR)\s*$', upper_before):
            return "COLUMN_FUNC", "", prefix

        return "GENERAL", "", prefix

    def _recargar_modelo_autocompletado(self, mode: str, qualifier: str, prefix: str):
        """Reconstruye el modelo de autocompletado priorizando los elementos según el contexto"""
        self.model.clear()
        candidates = []

        # Caso 1: Tras un punto (ej: 'tabla.') -> mostrar únicamente columnas de esa tabla o generales
        if mode == "DOT":
            self._current_dot_qualifier = qualifier
            cols = self.table_columns_map.get(qualifier, self.columns)
            for c in cols:
                candidates.append({
                    "name": c, "category": "COLUMNA", "icon": "🔑",
                    "badge_bg": "#7C3AED", "badge_fg": "#FFFFFF", "insert": c
                })
        else:
            self._current_dot_qualifier = ""
            # Elementos de tablas
            table_items = []
            for t in self.tables:
                table_items.append({
                    "name": t, "category": "TABLA", "icon": "📁",
                    "badge_bg": "#0284C7", "badge_fg": "#FFFFFF", "insert": t + " "
                })

            # Elementos de columnas
            col_items = []
            for c in self.columns:
                col_items.append({
                    "name": c, "category": "COLUMNA", "icon": "📋",
                    "badge_bg": "#7C3AED", "badge_fg": "#FFFFFF", "insert": c + " "
                })

            # Ordenar según el contexto semántico detectado
            if mode == "TABLE":
                candidates = table_items + self.base_candidates + col_items
            elif mode == "COLUMN_FUNC":
                candidates = col_items + [c for c in self.base_candidates if c["category"] == "FUNCIÓN"] + table_items + [c for c in self.base_candidates if c["category"] != "FUNCIÓN"]
            else:
                candidates = self.base_candidates + table_items + col_items

        # Filtrar candidatos por prefijo si hay uno
        clean_prefix = prefix.lower()
        if clean_prefix:
            filtered = [c for c in candidates if clean_prefix in c["name"].lower()]
            # Priorizar coincidencias que comiencen exactamente con el prefijo
            filtered.sort(key=lambda c: (not c["name"].lower().startswith(clean_prefix), c.get("category") != mode, c["name"].lower()))
        else:
            filtered = candidates

        for c in filtered:
            item = QStandardItem(c["name"])
            item.setData(c, Qt.ItemDataRole.UserRole)
            self.model.appendRow(item)

    def _insert_completion(self, completion: str):
        # Localizar metadatos de inserción
        tc = self.textCursor()
        matched_item = None
        for r in range(self.model.rowCount()):
            it = self.model.item(r)
            if it and it.text() == completion:
                matched_item = it.data(Qt.ItemDataRole.UserRole)
                break

        insert_text = matched_item.get("insert", completion + " ") if matched_item else (completion + " ")

        if self._current_dot_qualifier:
            # Reemplazar únicamente el fragmento después del punto
            tc.select(QTextCursor.SelectionType.WordUnderCursor)
            tc.insertText(insert_text)
            self._current_dot_qualifier = ""
        else:
            # Reemplazar la palabra completa bajo el cursor limpiamente
            tc.select(QTextCursor.SelectionType.WordUnderCursor)
            tc.insertText(insert_text)

        # Si es un snippet con offset de cursor, reposicionarlo
        if matched_item and matched_item.get("cursor_offset"):
            offset = matched_item["cursor_offset"]
            tc.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, abs(offset))

        self.setTextCursor(tc)

    def keyPressEvent(self, event):
        if self.completer and self.completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                event.ignore()
                return

        # Atajo forzado: Ctrl+Espacio
        is_ctrl_space = (event.key() == Qt.Key.Key_Space and (event.modifiers() & Qt.KeyboardModifier.ControlModifier))

        # Pasar evento a la clase base si no es Ctrl+Espacio
        if not is_ctrl_space:
            super().keyPressEvent(event)

        if not self.completer:
            return

        # Analizar contexto actual tras pulsar la tecla
        mode, qualifier, prefix = self._detectar_contexto_y_calificador()

        # Disparador por punto (.) o Ctrl+Espacio o 2 caracteres de prefijo
        should_show = is_ctrl_space or (event.text() == ".") or mode == "DOT" or len(prefix) >= 2

        if should_show:
            self._recargar_modelo_autocompletado(mode, qualifier, prefix)
            if self.model.rowCount() > 0:
                self.completer.setCompletionPrefix(prefix)
                popup = self.completer.popup()
                cr = self.cursorRect()
                cr.moveTop(cr.bottom() + 4)
                popup_w = max(300, popup.sizeHintForColumn(0) + 60)
                cr.setWidth(popup_w)
                self.completer.complete(cr)
            else:
                self.completer.popup().hide()
        else:
            if self.completer.popup().isVisible() and len(prefix) < 2 and mode != "DOT":
                self.completer.popup().hide()


class SqlEditorWidget(QWidget):
    """Componente de edición y ejecución SQL"""
    query_executed = pyqtSignal(str)  # Emite el SQL a ejecutar
    explain_requested = pyqtSignal(str)  # Emite el SQL a analizar con EXPLAIN

    def __init__(self, colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.history = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Barra de herramientas superior
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_run = QPushButton("▶  Ejecutar (F5)")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setFixedHeight(32)
        self.btn_run.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 14px;
                border: none;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
            QPushButton:pressed {{
                background-color: {self.colores.get('acento', '#6366F1')};
            }}
            QPushButton:focus {{
                outline: none;
            }}
        """)
        self.btn_run.clicked.connect(self._on_run_clicked)
        toolbar.addWidget(self.btn_run)

        self.btn_templates = QPushButton("📋 Plantillas SQL ▾")
        self.btn_templates.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_templates.setFixedHeight(32)
        self.btn_templates.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #FFFFFF;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 12px;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
            }}
            QPushButton:focus {{
                outline: none;
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.btn_templates.clicked.connect(self._mostrar_menu_plantillas)
        toolbar.addWidget(self.btn_templates)

        self.btn_explain = QPushButton("🔍 Analizar (EXPLAIN)")
        self.btn_explain.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_explain.setFixedHeight(32)
        self.btn_explain.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #CBD5E1;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 12px;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
            }}
            QPushButton:focus {{
                outline: none;
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.btn_explain.clicked.connect(self._on_explain_clicked)
        toolbar.addWidget(self.btn_explain)

        self.btn_clear = QPushButton("🧹 Limpiar")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setFixedHeight(32)
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                font-size: 11px;
                border-radius: 6px;
                padding: 0 10px;
                border: 1px solid transparent;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #FFFFFF;
                border-color: {self.colores.get('bg_terciario', '#2D2D3D')};
            }}
            QPushButton:pressed {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
            }}
            QPushButton:focus {{
                outline: none;
            }}
        """)
        self.btn_clear.clicked.connect(self.clear_editor)
        toolbar.addWidget(self.btn_clear)

        toolbar.addStretch()

        self.lbl_target_db = QLabel("")
        self.lbl_target_db.setStyleSheet(f"""
            QLabel {{
                color: {self.colores.get('acento', '#6366F1')};
                background-color: rgba(99, 102, 241, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        self.lbl_target_db.setVisible(False)
        toolbar.addWidget(self.lbl_target_db)

        self.lbl_status = QLabel("Listo para ejecutar consultas.")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 11px;")
        toolbar.addWidget(self.lbl_status)

        layout.addLayout(toolbar)

        # Editor de texto SQL con autocompletado inteligente
        self.editor = SqlCodeEditor(self.colores)
        self.editor.setPlaceholderText(
            "-- Escribe tu consulta SQL aquí (ej: SELECT * FROM mi_tabla;)\n"
            "-- Presiona F5 o Ctrl+Enter para ejecutar. Usa Ctrl+Espacio para sugerencias."
        )
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.editor.setFont(font)
        self.editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #F8FAFC;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
                padding: 10px;
                selection-background-color: {self.colores.get('acento', '#6366F1')};
                selection-color: white;
            }}
            QScrollBar:vertical {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 4px;
            }}
        """)

        # Aplicar resaltador de sintaxis
        self.highlighter = SqlSyntaxHighlighter(self.editor.document())

        # Atajos de teclado: F5 y Ctrl+Return
        self.shortcut_f5 = QShortcut(QKeySequence(Qt.Key.Key_F5), self.editor)
        self.shortcut_f5.activated.connect(self._on_run_clicked)

        self.shortcut_ctrl_enter = QShortcut(QKeySequence("Ctrl+Return"), self.editor)
        self.shortcut_ctrl_enter.activated.connect(self._on_run_clicked)

        # Splitter vertical: Editor arriba, Terminal abajo
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                height: 3px;
            }}
        """)
        splitter.addWidget(self.editor)

        self.terminal = SqlTerminalWidget(self.colores)
        splitter.addWidget(self.terminal)
        splitter.setSizes([380, 160])

        layout.addWidget(splitter)

    def _on_run_clicked(self):
        # Si hay texto seleccionado, ejecutar solo la selección
        cursor = self.editor.textCursor()
        raw_selected = cursor.selectedText().replace('\u2029', '\n').strip()
        is_selection = bool(raw_selected)
        sql = raw_selected if is_selection else self.editor.toPlainText().strip()
        if not sql:
            self.lbl_status.setText("⚠️ El editor está vacío.")
            self.lbl_status.setStyleSheet("color: #FBBF24; font-size: 11px;")
            return

        db_desc = f" en [{self._target_db_name}]" if hasattr(self, "_target_db_name") and self._target_db_name else ""
        if is_selection:
            self.set_status(f"⚡ Ejecutando bloque seleccionado{db_desc}...", is_error=False)
        else:
            self.set_status(f"⚡ Ejecutando script SQL{db_desc}...", is_error=False)

        self.history.append(sql)
        self.query_executed.emit(sql)

    def _on_explain_clicked(self):
        cursor = self.editor.textCursor()
        raw_selected = cursor.selectedText().replace('\u2029', '\n').strip()
        sql = raw_selected if raw_selected else self.editor.toPlainText().strip()
        if not sql:
            self.lbl_status.setText("⚠️ Escribe o selecciona una consulta para analizar su plan de ejecución.")
            self.lbl_status.setStyleSheet("color: #FBBF24; font-size: 11px;")
            return
        self.explain_requested.emit(sql)

    def show_explain_results(self, sql: str, rows: list, columns: list, err: str):
        if err:
            self.terminal.log_error(f"EXPLAIN {sql}", err)
            self.set_status(f"❌ Error en EXPLAIN: {err}", is_error=True)
            return

        lines = [
            "================================================================================",
            f"🔍 PLAN DE EJECUCIÓN (EXPLAIN) PARA: {sql[:80]}",
            "================================================================================"
        ]

        has_index_search = False
        has_table_scan = False

        for r in (rows or []):
            detail = r.get("detail") or str(r)
            if "SCAN TABLE" in detail.upper():
                has_table_scan = True
                lines.append(f"  ⚠️  [ALTO COSTO] {detail}  <-- Se recomienda crear un índice")
            elif "SEARCH TABLE USING INDEX" in detail.upper() or "INDEX" in detail.upper():
                has_index_search = True
                lines.append(f"  ⚡  [ÓPTIMO]     {detail}  <-- Búsqueda rápida por índice")
            else:
                lines.append(f"  ℹ️  {detail}")

        lines.append("--------------------------------------------------------------------------------")
        if has_index_search and not has_table_scan:
            diag = "✅ Diagnóstico: Consulta óptima, utiliza índices correctamente."
        elif has_table_scan:
            diag = "⚠️ Diagnóstico: Realiza escaneo secuencial (SCAN TABLE). Evalúa crear índices en las columnas del WHERE/JOIN."
        else:
            diag = "ℹ️ Diagnóstico: Plan de ejecución generado sin alertas de rendimiento."
        lines.append(diag)
        lines.append("================================================================================")

        for l in lines:
            self.terminal.output.appendPlainText(l)
        self.set_status(diag[:75])

    def set_status(self, text: str, is_error: bool = False):
        self.lbl_status.setText(text)
        color = "#F87171" if is_error else "#34D399"
        self.lbl_status.setStyleSheet(f"color: {color}; font-size: 11px;")

    def set_target_db(self, name: str, path: str = ""):
        """Configura la base de datos objetivo sobre la que opera este editor"""
        self._target_db_name = name
        self._target_db_path = path
        if hasattr(self, "lbl_target_db"):
            if name:
                self.lbl_target_db.setText(f"🎯 BD: {name}")
                tip = f"Base de datos activa: {name}"
                if path and path != ":memory:":
                    tip += f"\nArchivo en disco: {path}\n💡 Todas las tablas, datos y ejecuciones SQL se guardan directamente en este archivo."
                elif path == ":memory:":
                    tip += "\nBase de datos volátil en memoria (:memory:). Los cambios se perderán al cerrar la sesión."
                self.lbl_target_db.setToolTip(tip)
                self.lbl_target_db.setVisible(True)
            else:
                self.lbl_target_db.setVisible(False)

    def log_query(self, sql: str, duration_ms: float, rows_count: int, is_select: bool, db_name: str = ""):
        target = db_name or getattr(self, "_target_db_name", "")
        self.terminal.log_query(sql, duration_ms, rows_count, is_select, target)

    def log_error(self, sql: str, error_msg: str, duration_ms: float = 0.0, db_name: str = ""):
        target = db_name or getattr(self, "_target_db_name", "")
        self.terminal.log_error(sql, error_msg, duration_ms, target)

    def log_info(self, text: str):
        if hasattr(self, "terminal") and self.terminal:
            self.terminal.log_info(text)

    def clear_terminal(self):
        if hasattr(self, "terminal") and self.terminal:
            self.terminal.clear()

    def set_sql(self, sql: str):
        self.editor.setPlainText(sql)
        self.editor.setFocus()

    def get_sql(self) -> str:
        return self.editor.toPlainText()

    def update_autocomplete_words(self, tables: list, columns: list, table_columns_map: dict = None):
        """Actualiza el diccionario de autocompletado con las tablas y columnas activas"""
        if hasattr(self.editor, "update_dictionary"):
            self.editor.update_dictionary(tables, columns, table_columns_map)

    def clear_editor(self):
        self.editor.clear()
        self.lbl_status.setText("Editor limpio.")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 11px;")

    def _mostrar_menu_plantillas(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        
        t1 = menu.addAction("SELECT * FROM ... LIMIT 50;")
        t2 = menu.addAction("SELECT COUNT(*) FROM ...;")
        t3 = menu.addAction("CREATE TABLE nueva_tabla (...)")
        t4 = menu.addAction("INSERT INTO tabla (col1, col2) VALUES (...);")
        t5 = menu.addAction("UPDATE tabla SET col = val WHERE id = ...;")
        t6 = menu.addAction("DELETE FROM tabla WHERE id = ...;")
        menu.addSeparator()
        t7 = menu.addAction("PRAGMA table_info('tabla');")

        action = menu.exec(self.btn_templates.mapToGlobal(self.btn_templates.rect().bottomLeft()))
        if action == t1:
            self.editor.insertPlainText("SELECT * FROM nombre_tabla LIMIT 50;\n")
        elif action == t2:
            self.editor.insertPlainText("SELECT COUNT(*) AS total FROM nombre_tabla;\n")
        elif action == t3:
            self.editor.insertPlainText(
                "CREATE TABLE IF NOT EXISTS nueva_tabla (\n"
                "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                "    nombre TEXT NOT NULL,\n"
                "    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
                ");\n"
            )
        elif action == t4:
            self.editor.insertPlainText("INSERT INTO nombre_tabla (columna1, columna2) VALUES ('valor1', 100);\n")
        elif action == t5:
            self.editor.insertPlainText("UPDATE nombre_tabla SET columna1 = 'nuevo_valor' WHERE id = 1;\n")
        elif action == t6:
            self.editor.insertPlainText("DELETE FROM nombre_tabla WHERE id = 1;\n")
        elif action == t7:
            self.editor.insertPlainText("PRAGMA table_info('nombre_tabla');\n")
