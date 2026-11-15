# -*- coding: utf-8 -*-
"""Editor de código con números de línea, resaltado, autocompletado, linter AST y Ctrl+F."""

import ast
import re

from PyQt6.QtCore import QRect, QSize, QStringListModel, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PyQt6.QtWidgets import QCompleter, QPlainTextEdit, QTextEdit, QWidget

AUTOCOMPLETE_WORDS = [
    "QLabel", "QPushButton", "QLineEdit", "QTextEdit", "QComboBox", "QCheckBox",
    "QProgressBar", "QSpinBox", "QSlider", "QTableWidget", "QGroupBox", "QFrame",
    "QVBoxLayout", "QHBoxLayout", "QGridLayout", "QMessageBox", "QThread", "pyqtSignal",
    "self.context", "mostrar_notificacion", "set_status", "logger.log",
    "setGeometry", "setPlaceholderText", "setStyleSheet", "clicked.connect",
    "addWidget", "addItems", "def ", "class ", "import ", "from ", "return ",
]

AUTO_CLOSE_PAIRS = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}


class CodeHighlighter(QSyntaxHighlighter):
    """Resaltador ligero de sintaxis para Python y JSON."""

    def __init__(self, document, mode: str = "python"):
        super().__init__(document)
        self.mode = mode
        self.rules: list[tuple[re.Pattern, QTextCharFormat]] = []
        self._build_rules()

    def set_mode(self, mode: str):
        if self.mode != mode:
            self.mode = mode
            self._build_rules()
            self.rehighlight()

    def _fmt(self, color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def _build_rules(self):
        self.rules.clear()
        if self.mode == "json":
            self.rules.append((re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"\s*:'), self._fmt("#7dd3fc", bold=True)))
            self.rules.append((re.compile(r':\s*"[^"\\]*(?:\\.[^"\\]*)*"'), self._fmt("#86efac")))
            self.rules.append((re.compile(r'\b(true|false|null)\b'), self._fmt("#c084fc", bold=True)))
            self.rules.append((re.compile(r'\b-?\d+(\.\d+)?\b'), self._fmt("#fbbf24")))
            return

        keywords = (
            "and", "as", "assert", "async", "await", "break", "class", "continue",
            "def", "del", "elif", "else", "except", "False", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda", "None",
            "nonlocal", "not", "or", "pass", "raise", "return", "True", "try",
            "while", "with", "yield", "self",
        )
        kw_pattern = r"\b(" + "|".join(keywords) + r")\b"
        self.rules.append((re.compile(kw_pattern), self._fmt("#c084fc", bold=True)))
        self.rules.append((re.compile(r"\bclass\s+([A-Za-z_]\w*)"), self._fmt("#fde047", bold=True)))
        self.rules.append((re.compile(r"\bdef\s+([A-Za-z_]\w*)"), self._fmt("#60a5fa", bold=True)))
        self.rules.append((re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), self._fmt("#86efac")))
        self.rules.append((re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), self._fmt("#86efac")))
        self.rules.append((re.compile(r"\b\d+(\.\d+)?\b"), self._fmt("#fbbf24")))
        self.rules.append((re.compile(r"#[^\n]*"), self._fmt("#64748b", italic=True)))

    def highlightBlock(self, text: str):
        for pattern, fmt in self.rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class _LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """Editor monoespaciado IDE con números de línea, autocompletado, auto-cierre y linter AST."""

    syntaxErrorDetected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 9))
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.line_number_area = _LineNumberArea(self)
        self.highlighter = CodeHighlighter(self.document(), "python")
        self._error_line: int | None = None

        self._completer = QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setModel(QStringListModel(AUTOCOMPLETE_WORDS, self._completer))
        self._completer.activated.connect(self._insert_completion)
        self._completer.popup().setStyleSheet(
            "background-color: #181b28; color: #f8fafc; border: 1px solid #4f46e5;"
        )

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self._refresh_selections)
        self.textChanged.connect(self._check_syntax_live)

        self.update_line_number_area_width(0)
        self._refresh_selections()

    def _insert_completion(self, completion: str):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        tc.insertText(completion)
        self.setTextCursor(tc)

    def _word_under_cursor(self) -> str:
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def keyPressEvent(self, event):
        if self._completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                event.ignore()
                return

        ch = event.text()
        if ch in AUTO_CLOSE_PAIRS and not event.modifiers():
            super().keyPressEvent(event)
            tc = self.textCursor()
            tc.insertText(AUTO_CLOSE_PAIRS[ch])
            tc.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(tc)
            return

        super().keyPressEvent(event)
        if self.highlighter.mode == "python":
            prefix = self._word_under_cursor()
            if len(prefix) >= 2:
                self._completer.setCompletionPrefix(prefix)
                cr = self.cursorRect()
                cr.setWidth(self._completer.popup().sizeHintForColumn(0) + 24)
                self._completer.complete(cr)
            else:
                self._completer.popup().hide()

    def _check_syntax_live(self):
        if self.highlighter.mode != "python":
            self._error_line = None
            self._refresh_selections()
            return
        try:
            ast.parse(self.toPlainText())
            self._error_line = None
            self.syntaxErrorDetected.emit("")
        except SyntaxError as se:
            self._error_line = se.lineno
            self.syntaxErrorDetected.emit(f"Línea {se.lineno}: {se.msg}")
        self._refresh_selections()

    def line_number_area_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

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

    def _refresh_selections(self):
        extra = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor("#1f2437"))
            sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extra.append(sel)

        if self._error_line is not None:
            blk = self.document().findBlockByLineNumber(max(0, self._error_line - 1))
            if blk.isValid():
                err_sel = QTextEdit.ExtraSelection()
                err_sel.format.setBackground(QColor(248, 113, 113, 55))
                err_sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                c = QTextCursor(blk)
                c.clearSelection()
                err_sel.cursor = c
                extra.append(err_sel)
        self.setExtraSelections(extra)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#141622"))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                is_err = self._error_line == (block_number + 1)
                painter.setPen(QColor("#f87171") if is_err else QColor("#64748b"))
                painter.drawText(
                    0, top, self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
