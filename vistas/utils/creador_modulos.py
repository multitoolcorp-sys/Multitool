# -*- coding: utf-8 -*-
"""
Modo Creador de Módulos (mode MT) — Estudio Compacto estilo IntelliJ IDEA
- Persistencia del último módulo abierto + Salvapantallas (Welcome View)
- Lienzo Drag & Drop interactivo con posicionamiento/tamaño libre y sincronización en tiempo real
- Asistente Visual (Submódulo en config.json) vs Funcionalidad (Backend + Snippets Multitool)
- Gestor completo de archivos y carpetas + Compilación a .mtu + Hot-Reload
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QMimeData, QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QDrag,
    QFont,
    QKeySequence,
    QPainter,
    QPen,
    QShortcut,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextFormat,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vistas.utils.compilar_modulo import (
    ModuleCompilerDialog,
    abrir_compilador_modulos,
    obtener_raiz_proyecto,
)


def normalizar_id_modulo(nombre: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9_]+", "_", nombre.strip().lower())
    limpio = re.sub(r"_+", "_", limpio).strip("_")
    if not limpio or limpio[0].isdigit():
        limpio = f"mod_{limpio}" if limpio else "nuevo_modulo"
    return limpio


def a_pascal_case(texto: str) -> str:
    partes = [p for p in re.split(r"[^a-zA-Z0-9]+", texto) if p]
    if not partes:
        return "TabPrincipal"
    return "".join(p.capitalize() for p in partes)


# ─────────────────────────────────────────────────────────────
#  EDITOR DE CÓDIGO CON NÚMEROS DE LÍNEA Y RESALTADO
# ─────────────────────────────────────────────────────────────

class CodeHighlighter(QSyntaxHighlighter):
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 9))
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.line_number_area = _LineNumberArea(self)
        self.highlighter = CodeHighlighter(self.document(), "python")

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

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

    def highlight_current_line(self):
        extra = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor("#1f2437"))
            sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extra.append(sel)
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
                painter.setPen(QColor("#64748b"))
                painter.drawText(
                    0, top, self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())


# ─────────────────────────────────────────────────────────────
#  PALETA DRAG & DROP + LIENZO VISUAL INTERACTIVO
# ─────────────────────────────────────────────────────────────

WIDGET_PALETTE = [
    ("Título", "QLabel_title", "🏷️ Título", 260, 30),
    ("Etiqueta", "QLabel", "📝 Etiqueta", 240, 24),
    ("Botón", "QPushButton", "🔘 Botón", 160, 34),
    ("Campo Texto", "QLineEdit", "✏️ Campo Texto", 220, 32),
    ("Área Texto", "QTextEdit", "📄 Área Texto", 280, 90),
    ("Lista", "QComboBox", "🔽 Lista", 190, 30),
    ("Casilla", "QCheckBox", "☑️ Casilla", 180, 26),
    ("Progreso", "QProgressBar", "📊 Progreso", 240, 22),
    ("Submódulo", "SubmoduleSlot", "🧩 Contenedor Submódulo", 300, 140),
]

MULTITOOL_SNIPPETS = {
    "🔔 Notificación App": (
        '        app = getattr(self.context, "app", None) if self.context else None\n'
        '        if app and hasattr(app, "mostrar_notificacion"):\n'
        '            app.mostrar_notificacion("Título", "Mensaje de notificación", tipo="info")\n'
    ),
    "⚠️ Alerta / Confirmación": (
        '        from PyQt6.QtWidgets import QMessageBox\n'
        '        resp = QMessageBox.question(self, "Confirmar", "¿Deseas continuar?")\n'
        '        if resp == QMessageBox.StandardButton.Yes:\n'
        '            pass\n'
    ),
    "📝 Log en Consola": (
        '        app = getattr(self.context, "app", None) if self.context else None\n'
        '        if app and hasattr(app, "logger"):\n'
        '            app.logger.log("INFO", "Acción ejecutada", modulo="MiModulo")\n'
    ),
    "📊 Barra de Estado": (
        '        app = getattr(self.context, "app", None) if self.context else None\n'
        '        if app and hasattr(app, "set_status"):\n'
        '            app.set_status("Proceso completado correctamente")\n'
    ),
    "🧵 Hilo QThread": (
        'from PyQt6.QtCore import QThread, pyqtSignal\n\n'
        'class MiTareaWorker(QThread):\n'
        '    terminado = pyqtSignal(str)\n'
        '    def run(self):\n'
        '        self.terminado.emit("OK")\n'
    ),
}


class PaletteDragList(QListWidget):
    """Lista de widgets que permite arrastrar hacia el lienzo o hacer doble clic."""

    itemActivatedCustom = pyqtSignal(str, str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        for label, w_type, icon_lbl, w, h in WIDGET_PALETTE:
            it = QListWidgetItem(icon_lbl)
            it.setData(Qt.ItemDataRole.UserRole, (w_type, label, w, h))
            self.addItem(it)
        self.itemDoubleClicked.connect(self._on_double)

    def _on_double(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.itemActivatedCustom.emit(*data)

    def startDrag(self, _actions):
        item = self.currentItem()
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        mime = QMimeData()
        mime.setText(json.dumps({"tipo": data[0], "label": data[1], "w": data[2], "h": data[3]}))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class CanvasWidgetItem(QFrame):
    """Wrapper arrastrable y redimensionable sobre el lienzo visual."""

    selected = pyqtSignal(int)
    geometryChangedCustom = pyqtSignal(int, int, int, int, int)

    def __init__(self, idx: int, spec: dict, is_selected: bool, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.spec = spec
        self.is_selected = is_selected
        self._drag_start: QPoint | None = None
        self._resizing = False
        self._orig_geo = QRect()

        self.setGeometry(spec.get("x", 16), spec.get("y", 16), spec.get("w", 200), spec.get("h", 34))
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        border = "2px solid #6366f1" if is_selected else "1px dashed #3b4261"
        bg = "rgba(99, 102, 241, 0.12)" if is_selected else "rgba(30, 34, 51, 0.45)"
        self.setStyleSheet(f"CanvasWidgetItem {{ border: {border}; background: {bg}; border-radius: 5px; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 3, 4, 3)
        lay.setSpacing(0)

        t = spec["tipo"]
        txt = spec.get("texto", "")
        if t == "QLabel_title":
            w = QLabel(txt)
            w.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff; border: none; background: transparent;")
        elif t == "QLabel":
            w = QLabel(txt)
            w.setStyleSheet("font-size: 12px; color: #e2e8f0; border: none; background: transparent;")
        elif t == "QPushButton":
            w = QPushButton(txt)
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            w.setStyleSheet("background: #4f46e5; color: #ffffff; border-radius: 5px; font-size: 11px; padding: 4px;")
        elif t == "QLineEdit":
            w = QLineEdit(txt)
            w.setPlaceholderText(spec.get("placeholder", ""))
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QTextEdit":
            w = QTextEdit(txt)
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QComboBox":
            w = QComboBox()
            w.addItems([txt or "Opción 1", "Opción 2"])
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QCheckBox":
            w = QCheckBox(txt)
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QProgressBar":
            w = QProgressBar()
            w.setValue(50)
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "SubmoduleSlot":
            target = spec.get("target_sub", "Sin asignar")
            w = QLabel(f"🧩 Submódulo: {target}\n({txt})")
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            w.setStyleSheet("color: #a5b4fc; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        else:
            w = QLabel(txt)
        lay.addWidget(w)

        if is_selected:
            self.handle = QFrame(self)
            self.handle.setFixedSize(10, 10)
            self.handle.setStyleSheet("background-color: #818cf8; border: 1px solid #ffffff; border-radius: 2px;")
            self.handle.move(max(0, self.width() - 10), max(0, self.height() - 10))
            self.handle.setCursor(Qt.CursorShape.SizeFDiagCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.idx)
            self._drag_start = event.globalPosition().toPoint()
            self._orig_geo = self.geometry()
            self._resizing = (
                event.position().x() >= self.width() - 14
                and event.position().y() >= self.height() - 14
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_start is None:
            return
        delta = event.globalPosition().toPoint() - self._drag_start
        if self._resizing:
            nw = max(60, round((self._orig_geo.width() + delta.x()) / 8) * 8)
            nh = max(24, round((self._orig_geo.height() + delta.y()) / 8) * 8)
            self.resize(nw, nh)
            if hasattr(self, "handle"):
                self.handle.move(max(0, nw - 10), max(0, nh - 10))
        else:
            nx = max(0, round((self._orig_geo.x() + delta.x()) / 8) * 8)
            ny = max(0, round((self._orig_geo.y() + delta.y()) / 8) * 8)
            self.move(nx, ny)
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_start is not None:
            self._drag_start = None
            g = self.geometry()
            self.geometryChangedCustom.emit(self.idx, g.x(), g.y(), g.width(), g.height())
            event.accept()


class DesignCanvas(QFrame):
    """Lienzo interactivo con cuadrícula y soporte Drag & Drop desde la paleta."""

    widgetDropped = pyqtSignal(str, str, int, int, int, int)
    widgetSelected = pyqtSignal(int)
    widgetMovedResized = pyqtSignal(int, int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(520, 380)
        self.setStyleSheet("DesignCanvas { background-color: #0e1018; border: 1px solid #2e344d; border-radius: 6px; }")
        self._items_widgets: list[CanvasWidgetItem] = []

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(QColor(255, 255, 255, 16))
        pen.setWidth(1)
        painter.setPen(pen)
        step = 16
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        try:
            payload = json.loads(event.mimeData().text())
            pos = event.position().toPoint()
            x = max(0, round(pos.x() / 8) * 8)
            y = max(0, round(pos.y() / 8) * 8)
            self.widgetDropped.emit(
                payload["tipo"],
                payload["label"],
                x,
                y,
                int(payload.get("w", 180)),
                int(payload.get("h", 32)),
            )
            event.acceptProposedAction()
        except Exception:
            pass

    def render_items(self, specs: list[dict], selected_idx: int):
        for w in self._items_widgets:
            w.deleteLater()
        self._items_widgets.clear()
        max_x, max_y = 520, 380
        for i, sp in enumerate(specs):
            cw = CanvasWidgetItem(i, sp, i == selected_idx, self)
            cw.selected.connect(self.widgetSelected.emit)
            cw.geometryChangedCustom.connect(self.widgetMovedResized.emit)
            cw.show()
            self._items_widgets.append(cw)
            max_x = max(max_x, sp.get("x", 0) + sp.get("w", 100) + 40)
            max_y = max(max_y, sp.get("y", 0) + sp.get("h", 40) + 40)
        self.setMinimumSize(max_x, max_y)


# ─────────────────────────────────────────────────────────────
#  DIÁLOGO DE CREACIÓN DE ARCHIVO (VISUAL VS FUNCIONALIDAD)
# ─────────────────────────────────────────────────────────────

class NewFileTypeDialog(QDialog):
    """Pregunta si el nuevo archivo será Visual (Submódulo UI) o Funcionalidad (Backend)."""

    def __init__(self, base_dir_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Archivo en Módulo")
        self.setMinimumWidth(380)
        self.setStyleSheet("""
            QDialog, QWidget { background-color: #151824; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QLabel, QRadioButton { color: #f8fafc; }
            QLineEdit { background-color: #0f111a; color: #f8fafc; border: 1px solid #2e344d; border-radius: 5px; padding: 5px; }
            QPushButton { background-color: #252a3d; color: #f8fafc; border: 1px solid #38405e; border-radius: 5px; padding: 5px 12px; }
        """)
        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        lay.addWidget(QLabel(f"Crear dentro de <b>{base_dir_name}/</b>:"))
        self.ent_nombre = QLineEdit()
        self.ent_nombre.setPlaceholderText("Ej: tab_reportes.py  o  gestor_red.py")
        lay.addWidget(self.ent_nombre)

        self.rb_visual = QRadioButton("🎨 Visual (Submódulo / Pestaña UI — se añade a config.json)")
        self.rb_visual.setChecked(True)
        self.rb_func = QRadioButton("⚙️ Funcionalidad (Backend / Lógica — con snippets Multitool)")
        lay.addWidget(self.rb_visual)
        lay.addWidget(self.rb_func)

        self.box_visual = QFrame()
        v_lay = QFormLayout(self.box_visual)
        v_lay.setContentsMargins(16, 4, 4, 4)
        self.ent_sub_name = QLineEdit("Nueva Pestaña")
        self.ent_sub_icon = QLineEdit("🧩")
        v_lay.addRow("Nombre en pestaña:", self.ent_sub_name)
        v_lay.addRow("Icono:", self.ent_sub_icon)
        lay.addWidget(self.box_visual)

        self.rb_visual.toggled.connect(self.box_visual.setVisible)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)


# ─────────────────────────────────────────────────────────────
#  VENTANA PRINCIPAL DEL MODO CREADOR
# ─────────────────────────────────────────────────────────────

class ModuleCreatorDialog(QDialog):
    """Estudio compacto estilo IntelliJ IDEA para crear y editar módulos de Multitool."""

    def __init__(self, parent=None, app_ref=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.raiz = obtener_raiz_proyecto()
        self.modulos_dir = self.raiz / "vistas" / "modulos"
        self.modulo_actual: str | None = None
        self.archivo_actual: Path | None = None
        self._dirty_code = False
        self._bloqueando_signals = False
        self._selected_design_idx = 0
        self.design_items: list[dict] = [
            {"tipo": "QLabel_title", "var": "lbl_titulo", "texto": "Mi Módulo", "placeholder": "", "x": 16, "y": 16, "w": 280, "h": 32, "target_sub": ""},
            {"tipo": "QLabel", "var": "lbl_desc", "texto": "Arrastra o edita componentes en el lienzo.", "placeholder": "", "x": 16, "y": 56, "w": 320, "h": 24, "target_sub": ""},
            {"tipo": "QLineEdit", "var": "ent_entrada", "texto": "", "placeholder": "Escribe aquí...", "x": 16, "y": 88, "w": 240, "h": 32, "target_sub": ""},
            {"tipo": "QPushButton", "var": "btn_accion", "texto": "Ejecutar", "placeholder": "", "x": 16, "y": 132, "w": 150, "h": 34, "target_sub": ""},
        ]

        self.setWindowTitle("🎨 Modo Creador de Módulos (mode MT)")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(720, 480)
        self.resize(980, 620)

        self._aplicar_estilo()
        self._construir_ui()
        self._atajos()
        self._restaurar_ultimo_modulo()

    def _aplicar_estilo(self):
        self.setStyleSheet("""
            QDialog, QWidget {
                background-color: #11131c;
                color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
            }
            QLabel, QCheckBox, QRadioButton {
                color: #f8fafc;
                background: transparent;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QFrame#IdeBar, QFrame#Panel {
                background-color: #181b28;
                border: 1px solid #2a2f45;
                border-radius: 6px;
            }
            QLabel#HeaderTitle {
                font-size: 13px;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel#Section {
                font-size: 10px;
                font-weight: 700;
                color: #93c5fd;
                text-transform: uppercase;
            }
            QTreeWidget, QListWidget, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox {
                background-color: #0f111a;
                color: #f8fafc;
                border: 1px solid #2a2f45;
                border-radius: 5px;
                padding: 4px;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #181b28;
                color: #f8fafc;
                border: none;
                border-bottom: 1px solid #2a2f45;
                padding: 4px;
                font-weight: 600;
            }
            QTreeWidget::item, QListWidget::item {
                color: #f1f5f9;
                padding: 2px 4px;
            }
            QTreeWidget::item:selected, QListWidget::item:selected {
                background-color: #4f46e5;
                color: #ffffff;
            }
            QMenu {
                background-color: #181b28;
                color: #f8fafc;
                border: 1px solid #38405e;
            }
            QMenu::item:selected {
                background-color: #4f46e5;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #2a2f45;
                border-radius: 6px;
                background-color: #161925;
            }
            QTabBar::tab {
                background-color: #1e2233;
                color: #cbd5e1;
                padding: 5px 12px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
                font-weight: 600;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background-color: #4f46e5;
                color: #ffffff;
            }
            QPushButton {
                background-color: #252a3d;
                color: #f8fafc;
                border: 1px solid #38405e;
                border-radius: 5px;
                padding: 4px 9px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #323952;
            }
            QPushButton:disabled {
                background-color: #1b1e2b;
                color: #64748b;
                border-color: #232738;
            }
            QPushButton#Accent {
                background-color: #4f46e5;
                border-color: #6366f1;
                color: #ffffff;
            }
            QPushButton#Accent:hover {
                background-color: #6366f1;
            }
            QPushButton#Success {
                background-color: #059669;
                border-color: #10b981;
                color: #ffffff;
            }
            QPushButton#Success:hover {
                background-color: #10b981;
            }
        """)

    def _atajos(self):
        sc_save = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_save.activated.connect(self._guardar_archivo_actual)

    def _construir_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # Barra superior compacta estilo IDE
        top_bar = QFrame()
        top_bar.setObjectName("IdeBar")
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(8, 5, 8, 5)
        tb_lay.setSpacing(6)

        lbl_brand = QLabel("🎨 Modo Creador (mode MT)")
        lbl_brand.setObjectName("HeaderTitle")
        tb_lay.addWidget(lbl_brand)

        self.lbl_sync_badge = QLabel("● Sync en vivo")
        self.lbl_sync_badge.setStyleSheet("color: #34d399; font-weight: 600; font-size: 10px;")
        tb_lay.addWidget(self.lbl_sync_badge)

        tb_lay.addStretch(1)

        btn_home = QPushButton("🏠 Inicio")
        btn_home.setToolTip("Cerrar módulo activo y volver al salvapantallas")
        btn_home.clicked.connect(self._mostrar_salvapantallas)
        tb_lay.addWidget(btn_home)

        btn_nuevo = QPushButton("➕ Nuevo")
        btn_nuevo.setObjectName("Accent")
        btn_nuevo.clicked.connect(self._crear_nuevo_modulo_dialog)
        tb_lay.addWidget(btn_nuevo)

        self.btn_guardar = QPushButton("💾 Guardar")
        self.btn_guardar.clicked.connect(self._guardar_todo)
        tb_lay.addWidget(self.btn_guardar)

        self.btn_recargar = QPushButton("🔄 Hot-Reload")
        self.btn_recargar.clicked.connect(self._recargar_en_app)
        tb_lay.addWidget(self.btn_recargar)

        self.btn_compilar = QPushButton("📦 .mtu")
        self.btn_compilar.setObjectName("Success")
        self.btn_compilar.clicked.connect(self._abrir_compilador)
        tb_lay.addWidget(self.btn_compilar)

        root.addWidget(top_bar)

        # Splitter principal compacto
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Panel izquierdo: Selector + Gestor de Archivos
        left_panel = QFrame()
        left_panel.setObjectName("Panel")
        left_panel.setMinimumWidth(190)
        left_panel.setMaximumWidth(270)
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(7, 7, 7, 7)
        left_lay.setSpacing(5)

        lbl_proj = QLabel("Proyecto / Módulo")
        lbl_proj.setObjectName("Section")
        left_lay.addWidget(lbl_proj)

        self.cmb_modulos = QComboBox()
        self.cmb_modulos.currentTextChanged.connect(self._on_combo_modulo_cambiado)
        left_lay.addWidget(self.cmb_modulos)

        self.tree_archivos = QTreeWidget()
        self.tree_archivos.setHeaderLabel("Archivos")
        self.tree_archivos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_archivos.customContextMenuRequested.connect(self._menu_contextual_arbol)
        self.tree_archivos.itemDoubleClicked.connect(self._abrir_item_arbol)
        self.tree_archivos.itemClicked.connect(self._abrir_item_arbol)
        left_lay.addWidget(self.tree_archivos, 1)

        row_tree_btns = QHBoxLayout()
        row_tree_btns.setSpacing(3)
        self.tree_action_btns: list[QPushButton] = []
        for txt, tip, fn in [
            ("📄+", "Nuevo archivo (Visual o Funcionalidad)", self._crear_archivo_en_modulo),
            ("📁+", "Nueva carpeta", self._crear_carpeta_en_modulo),
            ("✏️", "Renombrar", self._renombrar_item_arbol),
            ("📦", "Mover", self._mover_item_arbol),
            ("🗑️", "Eliminar", self._eliminar_item_arbol),
            ("↻", "Refrescar", self._poblar_arbol_archivos),
        ]:
            b = QPushButton(txt)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row_tree_btns.addWidget(b)
            self.tree_action_btns.append(b)
        left_lay.addLayout(row_tree_btns)

        splitter.addWidget(left_panel)

        # Panel derecho: QStackedWidget (0 = Salvapantallas, 1 = Editor IDE)
        self.right_stack = QStackedWidget()
        self.right_stack.addWidget(self._crear_salvapantallas())

        self.tabs_editor = QTabWidget()
        self.tabs_editor.addTab(self._crear_tab_diseño(), "🎨 Diseño Visual")
        self.tabs_editor.addTab(self._crear_tab_codigo(), "💻 Código")
        self.tabs_editor.addTab(self._crear_tab_config(), "⚙️ Config & Reqs")
        self.right_stack.addWidget(self.tabs_editor)

        splitter.addWidget(self.right_stack)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        root.addWidget(splitter, 1)

        self.lbl_estado = QLabel("Listo.")
        self.lbl_estado.setStyleSheet("color: #94a3b8; font-size: 10px;")
        root.addWidget(self.lbl_estado)

    def _crear_salvapantallas(self) -> QWidget:
        w = QFrame()
        w.setObjectName("Panel")
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(10)

        lbl_ico = QLabel("🎨")
        lbl_ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_ico.setStyleSheet("font-size: 42px;")
        lay.addWidget(lbl_ico)

        lbl_t = QLabel("Estudio Creador de Módulos (mode MT)")
        lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_t.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        lay.addWidget(lbl_t)

        lbl_s = QLabel(
            "No hay ningún módulo abierto.\n"
            "Crea un módulo nuevo o selecciona uno del panel izquierdo para diseñar y programar."
        )
        lbl_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_s.setStyleSheet("color: #94a3b8; font-size: 11px;")
        lay.addWidget(lbl_s)

        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_new = QPushButton("➕ Crear Nuevo Módulo")
        btn_new.setObjectName("Accent")
        btn_new.clicked.connect(self._crear_nuevo_modulo_dialog)
        row.addWidget(btn_new)
        lay.addLayout(row)

        self.lista_recientes = QListWidget()
        self.lista_recientes.setMaximumWidth(340)
        self.lista_recientes.setMaximumHeight(160)
        self.lista_recientes.itemDoubleClicked.connect(
            lambda it: self._abrir_modulo(it.data(Qt.ItemDataRole.UserRole))
        )
        lay.addWidget(self.lista_recientes)
        return w

    def _crear_tab_diseño(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        # Paleta compacta
        pal_frame = QFrame()
        pal_frame.setObjectName("Panel")
        pal_frame.setMinimumWidth(145)
        pal_frame.setMaximumWidth(175)
        pal_lay = QVBoxLayout(pal_frame)
        pal_lay.setContentsMargins(6, 6, 6, 6)
        pal_lay.setSpacing(4)
        lbl_p = QLabel("Arrastra al Lienzo")
        lbl_p.setObjectName("Section")
        pal_lay.addWidget(lbl_p)

        self.palette_list = PaletteDragList()
        self.palette_list.itemActivatedCustom.connect(
            lambda t, l, pw, ph: self._agregar_widget_diseno(t, l, 16, 16 + len(self.design_items) * 38, pw, ph)
        )
        pal_lay.addWidget(self.palette_list, 1)
        lay.addWidget(pal_frame)

        # Lienzo Drag & Drop central
        center_frame = QFrame()
        center_frame.setObjectName("Panel")
        c_lay = QVBoxLayout(center_frame)
        c_lay.setContentsMargins(6, 6, 6, 6)
        c_lay.setSpacing(4)

        top_c = QHBoxLayout()
        top_c.addWidget(QLabel("Lienzo Interactivo (arrastra y redimensiona — Sync automático)"))
        top_c.addStretch(1)
        btn_del = QPushButton("🗑 Quitar")
        btn_del.clicked.connect(self._eliminar_widget_diseno)
        top_c.addWidget(btn_del)
        c_lay.addLayout(top_c)

        scroll_canvas = QScrollArea()
        scroll_canvas.setWidgetResizable(True)
        self.design_canvas = DesignCanvas()
        self.design_canvas.widgetDropped.connect(self._agregar_widget_diseno)
        self.design_canvas.widgetSelected.connect(self._on_widget_diseno_sel)
        self.design_canvas.widgetMovedResized.connect(self._on_widget_moved_resized)
        scroll_canvas.setWidget(self.design_canvas)
        c_lay.addWidget(scroll_canvas, 1)
        lay.addWidget(center_frame, 1)

        # Inspector compacto
        insp_frame = QFrame()
        insp_frame.setObjectName("Panel")
        insp_frame.setMinimumWidth(185)
        insp_frame.setMaximumWidth(230)
        insp = QFormLayout(insp_frame)
        insp.setContentsMargins(7, 7, 7, 7)
        insp.setSpacing(5)
        lbl_i = QLabel("Propiedades")
        lbl_i.setObjectName("Section")
        insp.addRow(lbl_i)

        self.ent_prop_var = QLineEdit()
        self.ent_prop_var.textEdited.connect(self._actualizar_prop_widget)
        insp.addRow("Var:", self.ent_prop_var)

        self.ent_prop_texto = QLineEdit()
        self.ent_prop_texto.textEdited.connect(self._actualizar_prop_widget)
        insp.addRow("Texto:", self.ent_prop_texto)

        self.ent_prop_placeholder = QLineEdit()
        self.ent_prop_placeholder.textEdited.connect(self._actualizar_prop_widget)
        insp.addRow("Hint:", self.ent_prop_placeholder)

        self.spn_x = QSpinBox(); self.spn_x.setRange(0, 2000); self.spn_x.valueChanged.connect(self._actualizar_geo_desde_insp)
        self.spn_y = QSpinBox(); self.spn_y.setRange(0, 2000); self.spn_y.valueChanged.connect(self._actualizar_geo_desde_insp)
        self.spn_w = QSpinBox(); self.spn_w.setRange(24, 2000); self.spn_w.valueChanged.connect(self._actualizar_geo_desde_insp)
        self.spn_h = QSpinBox(); self.spn_h.setRange(16, 2000); self.spn_h.valueChanged.connect(self._actualizar_geo_desde_insp)
        insp.addRow("X:", self.spn_x)
        insp.addRow("Y:", self.spn_y)
        insp.addRow("Ancho:", self.spn_w)
        insp.addRow("Alto:", self.spn_h)

        self.cmb_target_sub = QComboBox()
        self.cmb_target_sub.currentTextChanged.connect(self._actualizar_prop_widget)
        insp.addRow("Acción/Sub:", self.cmb_target_sub)

        lay.addWidget(insp_frame)
        self._refrescar_lienzo(sync_code=False)
        return w

    def _crear_tab_codigo(self) -> QWidget:
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        self.lbl_archivo_abierto = QLabel("Ningún archivo abierto")
        self.lbl_archivo_abierto.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        hdr.addWidget(self.lbl_archivo_abierto, 1)

        btn_save_code = QPushButton("💾 Guardar Archivo")
        btn_save_code.setObjectName("Accent")
        btn_save_code.clicked.connect(self._guardar_archivo_actual)
        hdr.addWidget(btn_save_code)
        lay.addLayout(hdr)

        # Barra de snippets rápidos de Multitool (para archivos de funcionalidad/backend)
        snip_bar = QHBoxLayout()
        snip_bar.setSpacing(4)
        snip_lbl = QLabel("Snippets:")
        snip_lbl.setStyleSheet("color: #93c5fd; font-weight: 600;")
        snip_bar.addWidget(snip_lbl)
        for name, code_snip in MULTITOOL_SNIPPETS.items():
            b = QPushButton(name)
            b.clicked.connect(lambda _c=False, s=code_snip: self._insertar_snippet(s))
            snip_bar.addWidget(b)
        snip_bar.addStretch(1)
        lay.addLayout(snip_bar)

        self.code_editor = CodeEditor()
        self.code_editor.textChanged.connect(self._on_code_changed)
        lay.addWidget(self.code_editor, 1)
        return cont

    def _crear_tab_config(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        meta_w = QWidget()
        m_lay = QVBoxLayout(meta_w)
        m_lay.setContentsMargins(8, 8, 8, 8)
        m_lay.setSpacing(8)

        cfg_box = QFrame()
        cfg_box.setObjectName("Panel")
        form = QFormLayout(cfg_box)
        form.setContentsMargins(10, 10, 10, 10)
        form.setSpacing(6)

        self.ent_cfg_name = QLineEdit()
        self.ent_cfg_icon = QLineEdit("🧩")
        self.ent_cfg_version = QLineEdit("1.0.0")
        self.spn_cfg_pos = QSpinBox()
        self.spn_cfg_pos.setRange(1, 999)
        self.chk_cfg_visible = QCheckBox("Visible en la barra de módulos")
        self.chk_cfg_visible.setChecked(True)

        form.addRow("Nombre visible:", self.ent_cfg_name)
        form.addRow("Icono:", self.ent_cfg_icon)
        form.addRow("Versión:", self.ent_cfg_version)
        form.addRow("Posición:", self.spn_cfg_pos)
        form.addRow("", self.chk_cfg_visible)

        btn_save_cfg = QPushButton("💾 Guardar config.json y requirements.txt")
        btn_save_cfg.setObjectName("Success")
        btn_save_cfg.clicked.connect(self._guardar_meta_modulo)
        form.addRow("", btn_save_cfg)
        m_lay.addWidget(cfg_box)

        req_box = QFrame()
        req_box.setObjectName("Panel")
        req_lay = QVBoxLayout(req_box)
        req_lay.setContentsMargins(10, 10, 10, 10)
        req_lay.setSpacing(5)
        req_lay.addWidget(QLabel("Dependencias Python (requirements.txt):"))
        self.txt_requirements = QPlainTextEdit()
        self.txt_requirements.setPlaceholderText("requests>=2.31.0\npsutil")
        self.txt_requirements.setMinimumHeight(110)
        req_lay.addWidget(self.txt_requirements, 1)
        m_lay.addWidget(req_box, 1)

        scroll.setWidget(meta_w)
        return scroll

    # ── Persistencia, Salvapantallas y Selección de Módulo ────────────────

    def _cargar_lista_modulos(self, seleccionar: str | None = None):
        self._bloqueando_signals = True
        self.cmb_modulos.clear()
        self.cmb_modulos.addItem("— Ninguno (Inicio) —")
        self.lista_recientes.clear()
        if self.modulos_dir.exists():
            dirs = sorted(
                [d.name for d in self.modulos_dir.iterdir() if d.is_dir() and not d.name.startswith("__")],
                key=str.lower,
            )
            self.cmb_modulos.addItems(dirs)
            for d in dirs:
                it = QListWidgetItem(f"📁  {d}")
                it.setData(Qt.ItemDataRole.UserRole, d)
                self.lista_recientes.addItem(it)
        self._bloqueando_signals = False

        if seleccionar and self.cmb_modulos.findText(seleccionar) >= 0:
            self._abrir_modulo(seleccionar)
        else:
            self._mostrar_salvapantallas()

    def _restaurar_ultimo_modulo(self):
        ultimo = None
        if self.app_ref and hasattr(self.app_ref, "config") and isinstance(self.app_ref.config, dict):
            ultimo = self.app_ref.config.get("creator_last_module")
        self._cargar_lista_modulos(seleccionar=ultimo)

    def _guardar_ultimo_modulo_config(self, nombre_mod: str | None):
        if self.app_ref and hasattr(self.app_ref, "config") and isinstance(self.app_ref.config, dict):
            self.app_ref.config["creator_last_module"] = nombre_mod or ""
            if hasattr(self.app_ref, "guardar_configuracion"):
                try:
                    self.app_ref.guardar_configuracion()
                except Exception:
                    pass

    def _set_acciones_habilitadas(self, habilitado: bool):
        for b in [self.btn_guardar, self.btn_recargar, self.btn_compilar, *self.tree_action_btns]:
            b.setEnabled(habilitado)

    def _mostrar_salvapantallas(self):
        self.modulo_actual = None
        self.archivo_actual = None
        self._bloqueando_signals = True
        self.cmb_modulos.setCurrentIndex(0)
        self._bloqueando_signals = False
        self.tree_archivos.clear()
        self.right_stack.setCurrentIndex(0)
        self._set_acciones_habilitadas(False)
        self._guardar_ultimo_modulo_config(None)
        self.lbl_estado.setText("Sin módulo activo. Selecciona o crea uno para comenzar.")

    def _on_combo_modulo_cambiado(self, texto: str):
        if self._bloqueando_signals:
            return
        if not texto or texto.startswith("—"):
            self._mostrar_salvapantallas()
        else:
            self._abrir_modulo(texto)

    def _abrir_modulo(self, nombre_mod: str):
        if not nombre_mod or not (self.modulos_dir / nombre_mod).exists():
            self._mostrar_salvapantallas()
            return
        self.modulo_actual = nombre_mod
        self._bloqueando_signals = True
        self.cmb_modulos.setCurrentText(nombre_mod)
        self._bloqueando_signals = False
        self.right_stack.setCurrentIndex(1)
        self._set_acciones_habilitadas(True)
        self._poblar_arbol_archivos()
        self._cargar_meta_modulo()
        self._abrir_archivo_principal_modulo()
        self._guardar_ultimo_modulo_config(nombre_mod)
        self.lbl_estado.setText(f"Editando: vistas/modulos/{nombre_mod}")

    # ── Árbol y Gestor de Archivos ────────────────────────────────────────

    def _poblar_arbol_archivos(self):
        self.tree_archivos.clear()
        if not self.modulo_actual:
            return
        mod_dir = self.modulos_dir / self.modulo_actual
        if not mod_dir.exists():
            return

        root_item = QTreeWidgetItem([f"📁 {self.modulo_actual}"])
        root_item.setData(0, Qt.ItemDataRole.UserRole, str(mod_dir))
        self.tree_archivos.addTopLevelItem(root_item)

        def _add_dir(parent_item: QTreeWidgetItem, current_dir: Path):
            entries = sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for entry in entries:
                if entry.name in {"__pycache__", ".git"} or entry.suffix in {".pyc", ".old"}:
                    continue
                if entry.is_dir():
                    dir_it = QTreeWidgetItem([f"📂 {entry.name}"])
                    dir_it.setData(0, Qt.ItemDataRole.UserRole, str(entry))
                    parent_item.addChild(dir_it)
                    _add_dir(dir_it, entry)
                else:
                    icon = "⚙️" if entry.name == "config.json" else ("📋" if entry.name == "requirements.txt" else "🐍")
                    file_it = QTreeWidgetItem([f"{icon} {entry.name}"])
                    file_it.setData(0, Qt.ItemDataRole.UserRole, str(entry))
                    parent_item.addChild(file_it)

        _add_dir(root_item, mod_dir)
        self.tree_archivos.expandAll()

    def _abrir_item_arbol(self, item: QTreeWidgetItem, _col: int = 0):
        ruta_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not ruta_str:
            return
        ruta = Path(ruta_str)
        if ruta.is_file():
            self._abrir_archivo_en_editor(ruta)

    def _abrir_archivo_principal_modulo(self):
        if not self.modulo_actual:
            return
        mod_dir = self.modulos_dir / self.modulo_actual
        cfg_path = mod_dir / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                subs = cfg.get("submodulos") or cfg.get("submodules") or []
                if subs and subs[0].get("file_name"):
                    cand = mod_dir / subs[0]["file_name"]
                    if cand.exists():
                        self._abrir_archivo_en_editor(cand)
                        return
            except Exception:
                pass
        for py in sorted(mod_dir.rglob("*.py")):
            if py.name != "__init__.py":
                self._abrir_archivo_en_editor(py)
                return

    def _abrir_archivo_en_editor(self, ruta: Path):
        if not ruta.exists() or not ruta.is_file():
            return
        self.archivo_actual = ruta
        contenido = ruta.read_text(encoding="utf-8", errors="replace")
        self._bloqueando_signals = True
        self.code_editor.highlighter.set_mode("json" if ruta.suffix.lower() == ".json" else "python")
        self.code_editor.setPlainText(contenido)
        self._bloqueando_signals = False
        self._dirty_code = False
        self.lbl_archivo_abierto.setText(str(ruta.relative_to(self.raiz)))

    def _on_code_changed(self):
        if not self._bloqueando_signals and self.archivo_actual:
            self._dirty_code = True
            self.lbl_archivo_abierto.setText(f"{self.archivo_actual.relative_to(self.raiz)} *")

    def _insertar_snippet(self, snippet: str):
        self.code_editor.insertPlainText(snippet)
        self.code_editor.setFocus()

    def _guardar_archivo_actual(self):
        if not self.archivo_actual:
            return
        self.archivo_actual.write_text(self.code_editor.toPlainText(), encoding="utf-8")
        self._dirty_code = False
        rel = str(self.archivo_actual.relative_to(self.raiz))
        self.lbl_archivo_abierto.setText(rel)
        self.lbl_estado.setText(f"Guardado: {rel}")
        if self.archivo_actual.name in {"config.json", "requirements.txt"}:
            self._cargar_meta_modulo()

    def _cargar_meta_modulo(self):
        if not self.modulo_actual:
            return
        mod_dir = self.modulos_dir / self.modulo_actual
        cfg_path = mod_dir / "config.json"
        cfg = {}
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                cfg = {}

        self.ent_cfg_name.setText(str(cfg.get("name") or cfg.get("nombre") or self.modulo_actual.capitalize()))
        self.ent_cfg_icon.setText(str(cfg.get("icon") or cfg.get("icono") or "🧩"))
        self.ent_cfg_version.setText(str(cfg.get("version") or "1.0.0"))
        self.spn_cfg_pos.setValue(int(cfg.get("position", 10) or 10))
        self.chk_cfg_visible.setChecked(bool(cfg.get("visible", True)))

        # Actualizar opciones de submódulos en el inspector
        self._bloqueando_signals = True
        self.cmb_target_sub.clear()
        self.cmb_target_sub.addItem("")
        self.cmb_target_sub.addItem("notificacion:info")
        for s in cfg.get("submodulos") or []:
            if s.get("name"):
                self.cmb_target_sub.addItem(f"submodulo:{s['name']}")
        self._bloqueando_signals = False

        req_path = mod_dir / "requirements.txt"
        self.txt_requirements.setPlainText(
            req_path.read_text(encoding="utf-8", errors="ignore") if req_path.exists() else ""
        )

    def _guardar_meta_modulo(self):
        if not self.modulo_actual:
            return
        mod_dir = self.modulos_dir / self.modulo_actual
        cfg_path = mod_dir / "config.json"
        cfg = {}
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                cfg = {}

        cfg["name"] = self.ent_cfg_name.text().strip() or self.modulo_actual.capitalize()
        cfg["icon"] = self.ent_cfg_icon.text().strip() or "🧩"
        cfg["version"] = self.ent_cfg_version.text().strip() or "1.0.0"
        cfg["position"] = self.spn_cfg_pos.value()
        cfg["visible"] = self.chk_cfg_visible.isChecked()
        if "submodulos" not in cfg:
            cfg["submodulos"] = []

        cfg_path.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")
        (mod_dir / "requirements.txt").write_text(self.txt_requirements.toPlainText().strip() + "\n", encoding="utf-8")
        self._poblar_arbol_archivos()
        if self.archivo_actual and self.archivo_actual.name in {"config.json", "requirements.txt"}:
            self._abrir_archivo_en_editor(self.archivo_actual)
        self.lbl_estado.setText(f"config.json y requirements.txt guardados en {self.modulo_actual}.")

    def _guardar_todo(self):
        self._guardar_archivo_actual()
        self._guardar_meta_modulo()

    def _crear_nuevo_modulo_dialog(self):
        nombre, ok = QInputDialog.getText(
            self, "Crear Nuevo Módulo", "Nombre del nuevo módulo (vistas/modulos/<nombre>):"
        )
        if not ok or not nombre.strip():
            return
        mod_id = normalizar_id_modulo(nombre)
        mod_dir = self.modulos_dir / mod_id
        if mod_dir.exists():
            QMessageBox.warning(self, "Ya existe", f"La carpeta '{mod_id}' ya existe.")
            return

        sub_dir = mod_dir / "submodulos"
        utils_dir = mod_dir / "utils"
        sub_dir.mkdir(parents=True, exist_ok=True)
        utils_dir.mkdir(parents=True, exist_ok=True)
        (mod_dir / "__init__.py").write_text("", encoding="utf-8")
        (sub_dir / "__init__.py").write_text("", encoding="utf-8")
        (utils_dir / "__init__.py").write_text("", encoding="utf-8")

        clase_tab = f"Tab{a_pascal_case(mod_id)}"
        clase_root = f"{a_pascal_case(mod_id)}App"

        (utils_dir / "backend.py").write_text(
            "# -*- coding: utf-8 -*-\n"
            f'"""Backend del módulo {nombre.strip()}."""\n\n\n'
            f"class {a_pascal_case(mod_id)}Backend:\n"
            "    def procesar(self, texto: str) -> str:\n"
            '        return f"Procesado: {texto}" if texto else "Listo."\n',
            encoding="utf-8",
        )
        (mod_dir / f"{mod_id}.py").write_text(
            "# -*- coding: utf-8 -*-\n"
            f'"""Archivo raíz del módulo {nombre.strip()}."""\n\n'
            f"from .submodulos.tab_{mod_id} import {clase_tab}\n"
            f"from .utils.backend import {a_pascal_case(mod_id)}Backend\n\n\n"
            f"class {clase_root}({clase_tab}):\n"
            "    pass\n",
            encoding="utf-8",
        )

        config_data = {
            "name": nombre.strip(),
            "icon": "🧩",
            "version": "1.0.0",
            "position": 25,
            "visible": True,
            "submodulos": [
                {
                    "name": "Principal",
                    "file_name": f"submodulos/tab_{mod_id}.py",
                    "class_name": clase_tab,
                    "visible": True,
                    "icon": "🧩",
                    "alias": mod_id,
                    "position": 1,
                }
            ],
        }
        (mod_dir / "config.json").write_text(json.dumps(config_data, indent=4, ensure_ascii=False), encoding="utf-8")
        (mod_dir / "commands.json").write_text("{}", encoding="utf-8")
        (mod_dir / "requirements.txt").write_text("# Dependencias pip\n", encoding="utf-8")
        (sub_dir / f"tab_{mod_id}.py").write_text(
            self._generar_codigo_pyqt(clase_tab, nombre.strip()), encoding="utf-8"
        )

        self._cargar_lista_modulos(seleccionar=mod_id)
        self.lbl_estado.setText(f"✅ Módulo '{mod_id}' creado con raíz, frontend y backend.")

    def _obtener_ruta_item_seleccionado(self) -> Path | None:
        item = self.tree_archivos.currentItem()
        if not item:
            return (self.modulos_dir / self.modulo_actual) if self.modulo_actual else None
        ruta_str = item.data(0, Qt.ItemDataRole.UserRole)
        return Path(ruta_str) if ruta_str else None

    def _obtener_directorio_destino_actual(self) -> Path | None:
        if not self.modulo_actual:
            return None
        ruta = self._obtener_ruta_item_seleccionado()
        if ruta is None:
            return self.modulos_dir / self.modulo_actual
        return ruta if ruta.is_dir() else ruta.parent

    def _menu_contextual_arbol(self, pos):
        if not self.modulo_actual:
            return
        menu = QMenu(self)
        for label, fn in [
            ("📄 Nuevo archivo (Visual / Funcionalidad)...", self._crear_archivo_en_modulo),
            ("📁 Nueva carpeta...", self._crear_carpeta_en_modulo),
            ("✏️ Renombrar...", self._renombrar_item_arbol),
            ("📦 Mover a otra carpeta...", self._mover_item_arbol),
            ("🗑️ Eliminar", self._eliminar_item_arbol),
            ("📂 Abrir en Explorador", self._abrir_en_explorador),
        ]:
            act = QAction(label, self)
            act.triggered.connect(fn)
            menu.addAction(act)
        menu.exec(self.tree_archivos.viewport().mapToGlobal(pos))

    def _crear_archivo_en_modulo(self):
        if not self.modulo_actual:
            return
        mod_dir = self.modulos_dir / self.modulo_actual
        base_dir = self._obtener_directorio_destino_actual() or mod_dir
        dlg = NewFileTypeDialog(base_dir.name, self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.ent_nombre.text().strip():
            return

        nombre = dlg.ent_nombre.text().strip().lstrip("/\\")
        if dlg.rb_visual.isChecked():
            if not nombre.endswith(".py"):
                nombre += ".py"
            destino = (mod_dir / "submodulos" / nombre) if base_dir == mod_dir else (base_dir / nombre)
        else:
            if "." not in Path(nombre).name:
                nombre += ".py"
            destino = (mod_dir / "utils" / nombre) if base_dir == mod_dir else (base_dir / nombre)

        if destino.exists():
            QMessageBox.warning(self, "Ya existe", f"'{destino.name}' ya existe.")
            return
        destino.parent.mkdir(parents=True, exist_ok=True)

        if dlg.rb_visual.isChecked():
            clase = a_pascal_case(destino.stem)
            destino.write_text(self._generar_codigo_pyqt(clase, dlg.ent_sub_name.text().strip()), encoding="utf-8")
            # Registrar submódulo en config.json automáticamente
            cfg_path = mod_dir / "config.json"
            if cfg_path.exists():
                try:
                    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                    subs = cfg.setdefault("submodulos", [])
                    rel_fn = destino.relative_to(mod_dir).as_posix()
                    subs.append({
                        "name": dlg.ent_sub_name.text().strip() or destino.stem,
                        "file_name": rel_fn,
                        "class_name": clase,
                        "visible": True,
                        "icon": dlg.ent_sub_icon.text().strip() or "🧩",
                        "alias": normalizar_id_modulo(destino.stem),
                        "position": len(subs) + 1,
                    })
                    cfg_path.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")
                    self._cargar_meta_modulo()
                except Exception:
                    pass
            self._poblar_arbol_archivos()
            self._abrir_archivo_en_editor(destino)
            self.tabs_editor.setCurrentIndex(0)
        else:
            destino.write_text(
                "# -*- coding: utf-8 -*-\n"
                f'"""Módulo de funcionalidad: {destino.stem}."""\n\n\n'
                f"def ejecutar(context=None, **kwargs):\n"
                '    app = getattr(context, "app", None) if context else None\n'
                '    if app and hasattr(app, "mostrar_notificacion"):\n'
                '        app.mostrar_notificacion("Módulo", "Función ejecutada", tipo="info")\n'
                '    return True\n',
                encoding="utf-8",
            )
            self._poblar_arbol_archivos()
            self._abrir_archivo_en_editor(destino)
            self.tabs_editor.setCurrentIndex(1)

    def _crear_carpeta_en_modulo(self):
        base_dir = self._obtener_directorio_destino_actual()
        if not base_dir:
            return
        nombre, ok = QInputDialog.getText(self, "Nueva Carpeta", f"Nombre dentro de {base_dir.name}/:")
        if not ok or not nombre.strip():
            return
        nueva = base_dir / nombre.strip().strip("/\\")
        if nueva.exists():
            QMessageBox.warning(self, "Ya existe", f"'{nueva.name}' ya existe.")
            return
        nueva.mkdir(parents=True, exist_ok=True)
        self._poblar_arbol_archivos()

    def _renombrar_item_arbol(self):
        ruta = self._obtener_ruta_item_seleccionado()
        mod_root = self.modulos_dir / self.modulo_actual if self.modulo_actual else None
        if not ruta or not mod_root or ruta == mod_root:
            return
        nuevo, ok = QInputDialog.getText(self, "Renombrar", "Nuevo nombre:", text=ruta.name)
        if not ok or not nuevo.strip() or nuevo.strip() == ruta.name:
            return
        destino = ruta.parent / nuevo.strip()
        if destino.exists():
            QMessageBox.warning(self, "Error", f"Ya existe '{destino.name}'.")
            return
        ruta.rename(destino)
        if self.archivo_actual == ruta:
            self.archivo_actual = destino
        self._poblar_arbol_archivos()

    def _mover_item_arbol(self):
        ruta = self._obtener_ruta_item_seleccionado()
        mod_root = self.modulos_dir / self.modulo_actual if self.modulo_actual else None
        if not ruta or not mod_root or ruta == mod_root:
            return
        carpetas = [mod_root] + [
            p for p in sorted(mod_root.rglob("*"))
            if p.is_dir() and p.name not in {"__pycache__", ".git"} and p != ruta and ruta not in p.parents
        ]
        opciones = [("." if c == mod_root else c.relative_to(mod_root).as_posix()) for c in carpetas]
        elegida, ok = QInputDialog.getItem(self, "Mover", f"Mover '{ruta.name}' a:", opciones, 0, False)
        if not ok or not elegida:
            return
        dest_dir = mod_root if elegida == "." else (mod_root / elegida)
        destino = dest_dir / ruta.name
        if destino.exists():
            QMessageBox.warning(self, "Conflicto", f"Ya existe '{ruta.name}' en '{elegida}'.")
            return
        shutil.move(str(ruta), str(destino))
        if self.archivo_actual == ruta:
            self.archivo_actual = destino
        self._poblar_arbol_archivos()

    def _eliminar_item_arbol(self):
        ruta = self._obtener_ruta_item_seleccionado()
        mod_root = self.modulos_dir / self.modulo_actual if self.modulo_actual else None
        if not ruta or not mod_root or ruta == mod_root:
            return
        resp = QMessageBox.question(self, "Confirmar", f"¿Eliminar '{ruta.name}'?")
        if resp != QMessageBox.StandardButton.Yes:
            return
        if ruta.is_dir():
            shutil.rmtree(ruta)
        else:
            ruta.unlink(missing_ok=True)
        if self.archivo_actual == ruta:
            self.archivo_actual = None
            self.code_editor.clear()
        self._poblar_arbol_archivos()

    def _abrir_en_explorador(self):
        if not self.modulo_actual:
            return
        mod_root = self.modulos_dir / self.modulo_actual
        if sys.platform.startswith("win"):
            os.startfile(str(mod_root))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(mod_root)])
        else:
            subprocess.Popen(["xdg-open", str(mod_root)])

    # ── Diseñador Drag & Drop + Sync en Tiempo Real ───────────────────────

    def _agregar_widget_diseno(self, tipo: str, label: str, x: int = 16, y: int = 16, w: int = 200, h: int = 32):
        idx = len(self.design_items) + 1
        var = f"{tipo.lower().replace('q', '')}_{idx}"
        self.design_items.append({
            "tipo": tipo,
            "var": var,
            "texto": f"{label} {idx}",
            "placeholder": "Escribe aquí..." if tipo == "QLineEdit" else "",
            "x": x, "y": y, "w": w, "h": h,
            "target_sub": "",
        })
        self._selected_design_idx = len(self.design_items) - 1
        self._refrescar_lienzo(sync_code=True)
        self._cargar_inspector(self._selected_design_idx)

    def _on_widget_diseno_sel(self, idx: int):
        self._selected_design_idx = idx
        self._refrescar_lienzo(sync_code=False)
        self._cargar_inspector(idx)

    def _on_widget_moved_resized(self, idx: int, x: int, y: int, w: int, h: int):
        if 0 <= idx < len(self.design_items):
            self.design_items[idx].update({"x": x, "y": y, "w": w, "h": h})
            self._cargar_inspector(idx)
            self._sincronizar_diseno_a_codigo()

    def _cargar_inspector(self, idx: int):
        if idx < 0 or idx >= len(self.design_items):
            return
        it = self.design_items[idx]
        self._bloqueando_signals = True
        self.ent_prop_var.setText(it["var"])
        self.ent_prop_texto.setText(it["texto"])
        self.ent_prop_placeholder.setText(it.get("placeholder", ""))
        self.spn_x.setValue(int(it.get("x", 16)))
        self.spn_y.setValue(int(it.get("y", 16)))
        self.spn_w.setValue(int(it.get("w", 180)))
        self.spn_h.setValue(int(it.get("h", 32)))
        self.cmb_target_sub.setCurrentText(it.get("target_sub", ""))
        self._bloqueando_signals = False

    def _actualizar_prop_widget(self):
        if self._bloqueando_signals:
            return
        idx = self._selected_design_idx
        if idx < 0 or idx >= len(self.design_items):
            return
        it = self.design_items[idx]
        it["var"] = normalizar_id_modulo(self.ent_prop_var.text() or it["var"])
        it["texto"] = self.ent_prop_texto.text()
        it["placeholder"] = self.ent_prop_placeholder.text()
        it["target_sub"] = self.cmb_target_sub.currentText()
        self._refrescar_lienzo(sync_code=True)

    def _actualizar_geo_desde_insp(self):
        if self._bloqueando_signals:
            return
        idx = self._selected_design_idx
        if idx < 0 or idx >= len(self.design_items):
            return
        self.design_items[idx].update({
            "x": self.spn_x.value(), "y": self.spn_y.value(),
            "w": self.spn_w.value(), "h": self.spn_h.value(),
        })
        self._refrescar_lienzo(sync_code=True)

    def _eliminar_widget_diseno(self):
        idx = self._selected_design_idx
        if 0 <= idx < len(self.design_items):
            self.design_items.pop(idx)
            self._selected_design_idx = max(0, idx - 1)
            self._refrescar_lienzo(sync_code=True)
            self._cargar_inspector(self._selected_design_idx)

    def _refrescar_lienzo(self, sync_code: bool = True):
        self.design_canvas.render_items(self.design_items, self._selected_design_idx)
        if sync_code:
            self._sincronizar_diseno_a_codigo()

    def _generar_codigo_pyqt(self, class_name: str, titulo: str) -> str:
        lines = [
            "# -*- coding: utf-8 -*-",
            "from PyQt6.QtWidgets import (",
            "    QCheckBox, QComboBox, QFrame, QLabel, QLineEdit,",
            "    QProgressBar, QPushButton, QTextEdit",
            ")",
            "",
            "",
            f"class {class_name}(QFrame):",
            f'    """Módulo {titulo} generado con Modo Creador (mode MT)."""',
            "",
            "    def __init__(self, parent=None, context=None, **kwargs):",
            "        super().__init__(parent)",
            "        self.context = context",
            "        self._init_ui()",
            "",
            "    def _init_ui(self):",
            '        self.setStyleSheet("QFrame { background: transparent; } QLabel, QCheckBox { color: #f8fafc; }")',
            "        self.setMinimumSize(560, 400)",
            "",
        ]
        for it in self.design_items:
            var = it["var"]
            txt = it["texto"].replace('"', '\\"')
            t = it["tipo"]
            x, y, w, h = it.get("x", 16), it.get("y", 16), it.get("w", 200), it.get("h", 32)
            target = it.get("target_sub", "")

            if t == "QLabel_title":
                lines.append(f'        self.{var} = QLabel("{txt}", self)')
                lines.append(f'        self.{var}.setStyleSheet("font-size: 17px; font-weight: 700; color: #ffffff;")')
            elif t == "QLabel":
                lines.append(f'        self.{var} = QLabel("{txt}", self)')
                lines.append(f'        self.{var}.setStyleSheet("font-size: 12px; color: #e2e8f0;")')
            elif t == "QPushButton":
                lines.append(f'        self.{var} = QPushButton("{txt}", self)')
                if target.startswith("notificacion:"):
                    lines.append(
                        f'        self.{var}.clicked.connect(lambda: getattr(self.context, "app", None) '
                        f'and self.context.app.mostrar_notificacion("{txt}", "Acción ejecutada", tipo="info"))'
                    )
            elif t == "QLineEdit":
                ph = it.get("placeholder", "").replace('"', '\\"')
                lines.append(f'        self.{var} = QLineEdit("{txt}", self)')
                if ph:
                    lines.append(f'        self.{var}.setPlaceholderText("{ph}")')
            elif t == "QTextEdit":
                lines.append(f'        self.{var} = QTextEdit("{txt}", self)')
            elif t == "QComboBox":
                lines.append(f"        self.{var} = QComboBox(self)")
                lines.append(f'        self.{var}.addItems(["{txt or "Opción 1"}", "Opción 2"])')
            elif t == "QCheckBox":
                lines.append(f'        self.{var} = QCheckBox("{txt}", self)')
            elif t == "QProgressBar":
                lines.append(f"        self.{var} = QProgressBar(self)")
                lines.append(f"        self.{var}.setValue(0)")
            elif t == "SubmoduleSlot":
                lines.append(f'        self.{var} = QFrame(self)')
                lines.append(f'        self.{var}.setStyleSheet("border: 1px dashed #6366f1; border-radius: 6px;")')
            lines.append(f"        self.{var}.setGeometry({x}, {y}, {w}, {h})")
            lines.append("")
        return "\n".join(lines)

    def _sincronizar_diseno_a_codigo(self):
        if not self.modulo_actual:
            return
        if not self.archivo_actual or self.archivo_actual.suffix != ".py":
            return

        clase = f"Tab{a_pascal_case(self.archivo_actual.stem)}"
        cfg_path = self.modulos_dir / self.modulo_actual / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                for s in cfg.get("submodulos") or []:
                    if s.get("file_name") and (self.modulos_dir / self.modulo_actual / s["file_name"]) == self.archivo_actual:
                        clase = s.get("class_name") or clase
                        break
            except Exception:
                pass

        codigo = self._generar_codigo_pyqt(clase, self.ent_cfg_name.text() or self.modulo_actual)
        self._bloqueando_signals = True
        self.code_editor.setPlainText(codigo)
        self._bloqueando_signals = False
        self._guardar_archivo_actual()
        self.lbl_estado.setText("● Sincronizado en tiempo real y guardado.")

    # ── Hot-Reload y Compilación ──────────────────────────────────────────

    def _recargar_en_app(self):
        self._guardar_todo()
        app = self.app_ref or self.parent()
        if not app:
            return
        import importlib
        if self.modulo_actual:
            prefijo = f"vistas.modulos.{self.modulo_actual.lower()}"
            for k in list(sys.modules.keys()):
                if k == prefijo or k.startswith(prefijo + "."):
                    sys.modules.pop(k, None)
            importlib.invalidate_caches()
        try:
            ya_registrado = any(
                m.get("folder", "").lower() == (self.modulo_actual or "").lower()
                or m.get("name", "").lower() == (self.modulo_actual or "").lower()
                for m in getattr(app, "modulos_cargados", [])
            )
            if ya_registrado and self.modulo_actual and hasattr(app, "recargar_modulo_en_caliente"):
                if app.recargar_modulo_en_caliente(self.modulo_actual):
                    self.lbl_estado.setText(f"🔥 Hot-Reload aplicado en '{self.modulo_actual}'.")
                    return
            if hasattr(app, "cargar_modulos"):
                app.cargar_modulos()
                self.lbl_estado.setText(f"🔄 Módulo '{self.modulo_actual}' recargado en Multitool.")
        except Exception as e:
            QMessageBox.warning(self, "Aviso", f"No se pudo recargar:\n{e}")

    def _abrir_compilador(self):
        self._guardar_todo()
        abrir_compilador_modulos(parent=self, modulo_preseleccionado=self.modulo_actual)


def abrir_creador_modulos(parent=None, app_ref=None):
    """Abre el estudio Modo Creador de Módulos (mode MT) como ventana independiente no bloqueante."""
    holder = app_ref or parent
    existing = getattr(holder, "_creador_modulos_win", None) if holder is not None else None
    if existing is not None:
        try:
            if existing.isMinimized():
                existing.showNormal()
            existing.show()
            existing.raise_()
            existing.activateWindow()
            return existing
        except RuntimeError:
            pass

    win = ModuleCreatorDialog(parent=None, app_ref=app_ref or parent)
    if holder is not None:
        holder._creador_modulos_win = win
    win.show()
    win.raise_()
    win.activateWindow()
    return win
