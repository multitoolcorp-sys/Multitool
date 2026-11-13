# -*- coding: utf-8 -*-
"""
Modo Creador de Módulos (mode MT) — Estudio estilo IntelliJ IDEA
Permite crear, diseñar visualmente (Modo Gráfico) y programar (Modo Código)
módulos nativos para Multitool dentro de `vistas/modulos/<nombre>/`,
editar su `config.json` y `requirements.txt`, recargarlos en la app y
compilarlos a `.mtu` para compartirlos.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QKeySequence,
    QPainter,
    QShortcut,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextFormat,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
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
    QScrollArea,
    QSpinBox,
    QSplitter,
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
    """Convierte un nombre arbitrario en un identificador válido de carpeta Python."""
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
    """Editor monoespaciado estilo IDE con números de línea y resaltado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 10))
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
        return 14 + self.fontMetrics().horizontalAdvance("9") * digits

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
                    0, top, self.line_number_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())


# ─────────────────────────────────────────────────────────────
#  DISEÑADOR VISUAL DE MÓDULOS (MODO GRÁFICO)
# ─────────────────────────────────────────────────────────────

WIDGET_PALETTE = [
    ("Título", "QLabel_title", "🏷️ Título"),
    ("Texto / Etiqueta", "QLabel", "📝 Etiqueta"),
    ("Botón de Acción", "QPushButton", "🔘 Botón"),
    ("Campo de Texto", "QLineEdit", "✏️ Campo de Texto"),
    ("Área Multilínea", "QTextEdit", "📄 Área de Texto"),
    ("Lista Desplegable", "QComboBox", "🔽 Lista Desplegable"),
    ("Casilla (Check)", "QCheckBox", "☑️ Casilla"),
    ("Barra de Progreso", "QProgressBar", "📊 Progreso"),
]


class ModuleCreatorDialog(QDialog):
    """Estudio completo estilo IntelliJ IDEA para crear y editar módulos de Multitool."""

    def __init__(self, parent=None, app_ref=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.raiz = obtener_raiz_proyecto()
        self.modulos_dir = self.raiz / "vistas" / "modulos"
        self.modulo_actual: str | None = None
        self.archivo_actual: Path | None = None
        self._dirty_code = False
        self._bloqueando_signals = False
        self.design_items: list[dict] = [
            {"tipo": "QLabel_title", "var": "lbl_titulo", "texto": "Mi Nuevo Módulo", "placeholder": ""},
            {"tipo": "QLabel", "var": "lbl_desc", "texto": "Descripción o instrucciones para el usuario.", "placeholder": ""},
            {"tipo": "QLineEdit", "var": "ent_entrada", "texto": "", "placeholder": "Escribe aquí..."},
            {"tipo": "QPushButton", "var": "btn_accion", "texto": "Ejecutar Acción", "placeholder": ""},
        ]

        self.setWindowTitle("🎨 Modo Creador de Módulos (mode MT) — Estudio Multitool")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(820, 560)
        self.resize(1180, 740)

        self._aplicar_estilo()
        self._construir_ui()
        self._atajos()
        self._cargar_lista_modulos()

    def _aplicar_estilo(self):
        self.setStyleSheet("""
            QDialog, QWidget {
                background-color: #11131c;
                color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
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
                border-radius: 8px;
            }
            QLabel#HeaderTitle {
                font-size: 14px;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel#Section {
                font-size: 11px;
                font-weight: 700;
                color: #93c5fd;
                text-transform: uppercase;
            }
            QTreeWidget, QListWidget, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox {
                background-color: #0f111a;
                color: #f8fafc;
                border: 1px solid #2a2f45;
                border-radius: 6px;
                padding: 5px;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #181b28;
                color: #f8fafc;
                border: none;
                border-bottom: 1px solid #2a2f45;
                padding: 5px;
                font-weight: 600;
            }
            QTreeWidget::item {
                color: #f1f5f9;
                padding: 3px;
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
                border-radius: 8px;
                background-color: #161925;
            }
            QTabBar::tab {
                background-color: #1e2233;
                color: #cbd5e1;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 3px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #4f46e5;
                color: #ffffff;
            }
            QPushButton {
                background-color: #252a3d;
                color: #f8fafc;
                border: 1px solid #38405e;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #323952;
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
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # Barra superior estilo IntelliJ IDEA
        top_bar = QFrame()
        top_bar.setObjectName("IdeBar")
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(10, 8, 10, 8)
        tb_lay.setSpacing(8)

        lbl_brand = QLabel("🎨 Estudio de Módulos (mode MT)")
        lbl_brand.setObjectName("HeaderTitle")
        tb_lay.addWidget(lbl_brand)

        tb_lay.addStretch(1)

        btn_nuevo = QPushButton("➕ Nuevo Módulo")
        btn_nuevo.setObjectName("Accent")
        btn_nuevo.clicked.connect(self._crear_nuevo_modulo_dialog)
        tb_lay.addWidget(btn_nuevo)

        self.btn_guardar = QPushButton("💾 Guardar (Ctrl+S)")
        self.btn_guardar.clicked.connect(self._guardar_todo)
        tb_lay.addWidget(self.btn_guardar)

        btn_recargar = QPushButton("🔄 Recargar en App")
        btn_recargar.clicked.connect(self._recargar_en_app)
        tb_lay.addWidget(btn_recargar)

        btn_compilar = QPushButton("📦 Compilar (.mtu)")
        btn_compilar.setObjectName("Success")
        btn_compilar.clicked.connect(self._abrir_compilador)
        tb_lay.addWidget(btn_compilar)

        root.addWidget(top_bar)

        # Splitter principal: Árbol de Proyecto | Área de Trabajo (Gráfico / Código)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Panel izquierdo: Selector de módulo + Árbol de archivos
        left_panel = QFrame()
        left_panel.setObjectName("Panel")
        left_panel.setMinimumWidth(220)
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(10, 10, 10, 10)
        left_lay.setSpacing(8)

        lbl_proj = QLabel("Proyecto / Módulo")
        lbl_proj.setObjectName("Section")
        left_lay.addWidget(lbl_proj)

        self.cmb_modulos = QComboBox()
        self.cmb_modulos.currentTextChanged.connect(self._seleccionar_modulo)
        left_lay.addWidget(self.cmb_modulos)

        self.tree_archivos = QTreeWidget()
        self.tree_archivos.setHeaderLabel("Gestor de Archivos del Módulo")
        self.tree_archivos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_archivos.customContextMenuRequested.connect(self._menu_contextual_arbol)
        self.tree_archivos.itemDoubleClicked.connect(self._abrir_item_arbol)
        self.tree_archivos.itemClicked.connect(self._abrir_item_arbol)
        left_lay.addWidget(self.tree_archivos, 1)

        row_tree_btns = QHBoxLayout()
        row_tree_btns.setSpacing(4)
        btn_new_file = QPushButton("📄+")
        btn_new_file.setToolTip("Nuevo archivo en la carpeta seleccionada")
        btn_new_file.clicked.connect(lambda: self._crear_archivo_en_modulo())
        row_tree_btns.addWidget(btn_new_file)

        btn_new_dir = QPushButton("📁+")
        btn_new_dir.setToolTip("Nueva carpeta en el módulo")
        btn_new_dir.clicked.connect(lambda: self._crear_carpeta_en_modulo())
        row_tree_btns.addWidget(btn_new_dir)

        btn_rename = QPushButton("✏️")
        btn_rename.setToolTip("Renombrar archivo o carpeta")
        btn_rename.clicked.connect(self._renombrar_item_arbol)
        row_tree_btns.addWidget(btn_rename)

        btn_move = QPushButton("📦")
        btn_move.setToolTip("Mover archivo o carpeta")
        btn_move.clicked.connect(self._mover_item_arbol)
        row_tree_btns.addWidget(btn_move)

        btn_del = QPushButton("🗑️")
        btn_del.setToolTip("Eliminar archivo o carpeta")
        btn_del.clicked.connect(self._eliminar_item_arbol)
        row_tree_btns.addWidget(btn_del)

        btn_ref_tree = QPushButton("↻")
        btn_ref_tree.setToolTip("Refrescar árbol")
        btn_ref_tree.clicked.connect(self._poblar_arbol_archivos)
        row_tree_btns.addWidget(btn_ref_tree)
        left_lay.addLayout(row_tree_btns)

        splitter.addWidget(left_panel)

        # Panel derecho: Tabs Duales (Modo Gráfico / Modo Código)
        self.tabs_editor = QTabWidget()
        self.tabs_editor.addTab(self._crear_tab_modo_grafico(), "🎨 Modo Gráfico (Visual + Config)")
        self.tabs_editor.addTab(self._crear_tab_modo_codigo(), "💻 Modo Código (Editor)")
        splitter.addWidget(self.tabs_editor)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        root.addWidget(splitter, 1)

        # Barra de estado inferior
        self.lbl_estado = QLabel("Listo. Selecciona o crea un módulo en vistas/modulos/.")
        self.lbl_estado.setStyleSheet("color: #94a3b8; font-size: 11px;")
        root.addWidget(self.lbl_estado)

    def _crear_tab_modo_grafico(self) -> QWidget:
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        subtabs = QTabWidget()

        # Subtab A: Diseñador Visual de Interfaz PyQt6
        designer_w = QWidget()
        d_lay = QHBoxLayout(designer_w)
        d_lay.setContentsMargins(8, 8, 8, 8)
        d_lay.setSpacing(8)

        # Paleta
        pal_frame = QFrame()
        pal_frame.setObjectName("Panel")
        pal_frame.setMinimumWidth(170)
        pal_frame.setMaximumWidth(210)
        pal_lay = QVBoxLayout(pal_frame)
        pal_lay.setContentsMargins(8, 8, 8, 8)
        pal_lay.setSpacing(6)
        pal_lay.addWidget(QLabel("Paleta de Widgets"))
        for label, w_type, icon_lbl in WIDGET_PALETTE:
            btn = QPushButton(icon_lbl)
            btn.clicked.connect(lambda _c=False, t=w_type, l=label: self._agregar_widget_diseno(t, l))
            pal_lay.addWidget(btn)
        pal_lay.addStretch(1)
        d_lay.addWidget(pal_frame)

        # Lienzo + Vista Previa
        canvas_frame = QFrame()
        canvas_frame.setObjectName("Panel")
        c_lay = QVBoxLayout(canvas_frame)
        c_lay.setContentsMargins(10, 10, 10, 10)
        c_lay.setSpacing(8)

        hdr_c = QHBoxLayout()
        hdr_c.addWidget(QLabel("Vista Previa en Vivo (Orden de Componentes)"))
        hdr_c.addStretch(1)
        btn_sync_code = QPushButton("✨ Sincronizar Diseño → Código")
        btn_sync_code.setObjectName("Accent")
        btn_sync_code.clicked.connect(self._sincronizar_diseno_a_codigo)
        hdr_c.addWidget(btn_sync_code)
        c_lay.addLayout(hdr_c)

        self.lista_diseno = QListWidget()
        self.lista_diseno.setMaximumHeight(140)
        self.lista_diseno.currentRowChanged.connect(self._on_widget_diseno_sel)
        c_lay.addWidget(self.lista_diseno)

        row_ord = QHBoxLayout()
        btn_up = QPushButton("⬆ Subir")
        btn_up.clicked.connect(lambda: self._mover_widget_diseno(-1))
        btn_down = QPushButton("⬇ Bajar")
        btn_down.clicked.connect(lambda: self._mover_widget_diseno(1))
        btn_del = QPushButton("🗑 Quitar")
        btn_del.clicked.connect(self._eliminar_widget_diseno)
        row_ord.addWidget(btn_up)
        row_ord.addWidget(btn_down)
        row_ord.addWidget(btn_del)
        row_ord.addStretch(1)
        c_lay.addLayout(row_ord)

        scroll_prev = QScrollArea()
        scroll_prev.setWidgetResizable(True)
        self.preview_box = QFrame()
        self.preview_box.setStyleSheet("background-color: #12141f; border: 1px dashed #3b4261; border-radius: 8px;")
        self.preview_layout = QVBoxLayout(self.preview_box)
        self.preview_layout.setContentsMargins(14, 14, 14, 14)
        self.preview_layout.setSpacing(8)
        scroll_prev.setWidget(self.preview_box)
        c_lay.addWidget(scroll_prev, 1)

        d_lay.addWidget(canvas_frame, 2)

        # Inspector de propiedades
        insp_frame = QFrame()
        insp_frame.setObjectName("Panel")
        insp_frame.setMinimumWidth(210)
        insp_frame.setMaximumWidth(270)
        insp_lay = QFormLayout(insp_frame)
        insp_lay.setContentsMargins(10, 10, 10, 10)
        insp_lay.setSpacing(8)
        insp_lay.addRow(QLabel("Propiedades del Widget"))

        self.ent_prop_var = QLineEdit()
        self.ent_prop_var.textEdited.connect(self._actualizar_prop_widget)
        insp_lay.addRow("Variable:", self.ent_prop_var)

        self.ent_prop_texto = QLineEdit()
        self.ent_prop_texto.textEdited.connect(self._actualizar_prop_widget)
        insp_lay.addRow("Texto:", self.ent_prop_texto)

        self.ent_prop_placeholder = QLineEdit()
        self.ent_prop_placeholder.textEdited.connect(self._actualizar_prop_widget)
        insp_lay.addRow("Placeholder:", self.ent_prop_placeholder)

        d_lay.addWidget(insp_frame)
        subtabs.addTab(designer_w, "🧩 Diseñador Visual de Interfaz")

        # Subtab B: Editor visual de config.json y requirements.txt
        meta_w = QWidget()
        meta_scroll = QScrollArea()
        meta_scroll.setWidgetResizable(True)
        meta_scroll.setFrameShape(QFrame.Shape.NoFrame)
        m_lay = QVBoxLayout(meta_w)
        m_lay.setContentsMargins(10, 10, 10, 10)
        m_lay.setSpacing(10)

        cfg_box = QFrame()
        cfg_box.setObjectName("Panel")
        form = QFormLayout(cfg_box)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(8)

        self.ent_cfg_name = QLineEdit()
        self.ent_cfg_icon = QLineEdit("🧩")
        self.ent_cfg_version = QLineEdit("1.0.0")
        self.spn_cfg_pos = QSpinBox()
        self.spn_cfg_pos.setRange(1, 999)
        self.chk_cfg_visible = QCheckBox("Visible en la barra de módulos")
        self.chk_cfg_visible.setChecked(True)

        form.addRow("Nombre visible (name):", self.ent_cfg_name)
        form.addRow("Icono (emoji):", self.ent_cfg_icon)
        form.addRow("Versión:", self.ent_cfg_version)
        form.addRow("Posición en menú:", self.spn_cfg_pos)
        form.addRow("", self.chk_cfg_visible)

        btn_save_cfg = QPushButton("💾 Guardar config.json y requirements.txt")
        btn_save_cfg.setObjectName("Success")
        btn_save_cfg.clicked.connect(self._guardar_meta_modulo)
        form.addRow("", btn_save_cfg)
        m_lay.addWidget(cfg_box)

        req_box = QFrame()
        req_box.setObjectName("Panel")
        req_lay = QVBoxLayout(req_box)
        req_lay.setContentsMargins(12, 12, 12, 12)
        req_lay.setSpacing(6)
        req_lay.addWidget(QLabel("Dependencias Python (requirements.txt — una por línea):"))
        self.txt_requirements = QPlainTextEdit()
        self.txt_requirements.setPlaceholderText("Ejemplo:\nrequests>=2.31.0\npsutil")
        self.txt_requirements.setMinimumHeight(140)
        req_lay.addWidget(self.txt_requirements, 1)
        m_lay.addWidget(req_box, 1)

        meta_scroll.setWidget(meta_w)
        subtabs.addTab(meta_scroll, "⚙️ config.json y requirements.txt")

        lay.addWidget(subtabs, 1)
        self._refrescar_preview_diseno()
        return cont

    def _crear_tab_modo_codigo(self) -> QWidget:
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        hdr = QHBoxLayout()
        self.lbl_archivo_abierto = QLabel("Ningún archivo abierto")
        self.lbl_archivo_abierto.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        hdr.addWidget(self.lbl_archivo_abierto, 1)

        btn_save_code = QPushButton("💾 Guardar Archivo")
        btn_save_code.setObjectName("Accent")
        btn_save_code.clicked.connect(self._guardar_archivo_actual)
        hdr.addWidget(btn_save_code)
        lay.addLayout(hdr)

        self.code_editor = CodeEditor()
        self.code_editor.textChanged.connect(self._on_code_changed)
        lay.addWidget(self.code_editor, 1)
        return cont

    # ── Gestión de Módulos y Archivos ─────────────────────────────────────

    def _cargar_lista_modulos(self, seleccionar: str | None = None):
        self._bloqueando_signals = True
        self.cmb_modulos.clear()
        if self.modulos_dir.exists():
            dirs = sorted(
                [d.name for d in self.modulos_dir.iterdir() if d.is_dir() and not d.name.startswith("__")],
                key=str.lower,
            )
            self.cmb_modulos.addItems(dirs)
        self._bloqueando_signals = False

        if seleccionar and self.cmb_modulos.findText(seleccionar) >= 0:
            self.cmb_modulos.setCurrentText(seleccionar)
        elif self.cmb_modulos.count() > 0:
            self._seleccionar_modulo(self.cmb_modulos.currentText())

    def _seleccionar_modulo(self, nombre_mod: str):
        if self._bloqueando_signals or not nombre_mod:
            return
        self.modulo_actual = nombre_mod
        self._poblar_arbol_archivos()
        self._cargar_meta_modulo()
        self._abrir_archivo_principal_modulo()
        self.lbl_estado.setText(f"Editando módulo: vistas/modulos/{nombre_mod}")

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
        try:
            contenido = ruta.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo leer el archivo:\n{e}")
            return

        self._bloqueando_signals = True
        self.code_editor.highlighter.set_mode("json" if ruta.suffix.lower() == ".json" else "python")
        self.code_editor.setPlainText(contenido)
        self._bloqueando_signals = False
        self._dirty_code = False
        self.lbl_archivo_abierto.setText(str(ruta.relative_to(self.raiz)))

    def _on_code_changed(self):
        if not self._bloqueando_signals and self.archivo_actual:
            self._dirty_code = True
            rel = str(self.archivo_actual.relative_to(self.raiz))
            self.lbl_archivo_abierto.setText(f"{rel} *")

    def _guardar_archivo_actual(self):
        if not self.archivo_actual:
            return
        try:
            self.archivo_actual.write_text(self.code_editor.toPlainText(), encoding="utf-8")
            self._dirty_code = False
            rel = str(self.archivo_actual.relative_to(self.raiz))
            self.lbl_archivo_abierto.setText(rel)
            self.lbl_estado.setText(f"Guardado: {rel}")
            if self.archivo_actual.name in {"config.json", "requirements.txt"}:
                self._cargar_meta_modulo()
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))

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

        req_path = mod_dir / "requirements.txt"
        if req_path.exists():
            self.txt_requirements.setPlainText(req_path.read_text(encoding="utf-8", errors="ignore"))
        else:
            self.txt_requirements.clear()

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
            self,
            "Crear Nuevo Módulo",
            "Nombre del nuevo módulo (se creará en vistas/modulos/<nombre>):",
        )
        if not ok or not nombre.strip():
            return
        mod_id = normalizar_id_modulo(nombre)
        mod_dir = self.modulos_dir / mod_id
        if mod_dir.exists():
            QMessageBox.warning(self, "Ya existe", f"La carpeta '{mod_id}' ya existe en vistas/modulos/.")
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

        # Backend del módulo (utils/backend.py)
        backend_code = (
            "# -*- coding: utf-8 -*-\n"
            f'"""Backend y lógica de negocio del módulo {nombre.strip()}."""\n\n\n'
            f"class {a_pascal_case(mod_id)}Backend:\n"
            "    def procesar(self, texto: str) -> str:\n"
            '        return f"Procesado: {texto}" if texto else "Listo."\n'
        )
        (utils_dir / "backend.py").write_text(backend_code, encoding="utf-8")

        # Archivo raíz del módulo (<mod_id>.py) que conecta frontend + backend
        root_code = (
            "# -*- coding: utf-8 -*-\n"
            f'"""Punto de entrada raíz del módulo {nombre.strip()}."""\n\n'
            f"from .submodulos.tab_{mod_id} import {clase_tab}\n"
            f"from .utils.backend import {a_pascal_case(mod_id)}Backend\n\n\n"
            f"class {clase_root}({clase_tab}):\n"
            "    pass\n"
        )
        (mod_dir / f"{mod_id}.py").write_text(root_code, encoding="utf-8")

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
        (mod_dir / "requirements.txt").write_text("# Agrega aquí las dependencias pip de tu módulo\n", encoding="utf-8")

        py_file = sub_dir / f"tab_{mod_id}.py"
        py_file.write_text(self._generar_codigo_pyqt(clase_tab, nombre.strip()), encoding="utf-8")

        self._cargar_lista_modulos(seleccionar=mod_id)
        self.lbl_estado.setText(f"✅ Módulo '{mod_id}' creado con raíz {mod_id}.py, frontend y backend.")

    # ── Gestor Completo de Archivos y Carpetas ────────────────────────────

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
        act_new_f = QAction("📄 Nuevo archivo aquí...", self)
        act_new_f.triggered.connect(self._crear_archivo_en_modulo)
        act_new_d = QAction("📁 Nueva carpeta aquí...", self)
        act_new_d.triggered.connect(self._crear_carpeta_en_modulo)
        act_ren = QAction("✏️ Renombrar...", self)
        act_ren.triggered.connect(self._renombrar_item_arbol)
        act_mov = QAction("📦 Mover a otra carpeta...", self)
        act_mov.triggered.connect(self._mover_item_arbol)
        act_del = QAction("🗑️ Eliminar", self)
        act_del.triggered.connect(self._eliminar_item_arbol)
        act_exp = QAction("📂 Abrir en Explorador", self)
        act_exp.triggered.connect(self._abrir_en_explorador)

        menu.addAction(act_new_f)
        menu.addAction(act_new_d)
        menu.addSeparator()
        menu.addAction(act_ren)
        menu.addAction(act_mov)
        menu.addAction(act_del)
        menu.addSeparator()
        menu.addAction(act_exp)
        menu.exec(self.tree_archivos.viewport().mapToGlobal(pos))

    def _crear_archivo_en_modulo(self):
        base_dir = self._obtener_directorio_destino_actual()
        if not base_dir:
            return
        nombre, ok = QInputDialog.getText(
            self,
            "Nuevo Archivo",
            f"Nombre o ruta relativa dentro de {base_dir.name}/ (ej: tab_extra.py):",
        )
        if not ok or not nombre.strip():
            return
        rel = nombre.strip().lstrip("/\\")
        destino = base_dir / rel
        if destino.exists():
            QMessageBox.warning(self, "Ya existe", f"El archivo '{rel}' ya existe.")
            return
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.suffix == ".py":
            clase = a_pascal_case(destino.stem)
            destino.write_text(self._generar_codigo_pyqt(clase, destino.stem), encoding="utf-8")
        else:
            destino.write_text("", encoding="utf-8")
        self._poblar_arbol_archivos()
        self._abrir_archivo_en_editor(destino)

    def _crear_carpeta_en_modulo(self):
        base_dir = self._obtener_directorio_destino_actual()
        if not base_dir:
            return
        nombre, ok = QInputDialog.getText(
            self,
            "Nueva Carpeta",
            f"Nombre de la carpeta dentro de {base_dir.name}/:",
        )
        if not ok or not nombre.strip():
            return
        nueva = base_dir / nombre.strip().strip("/\\")
        if nueva.exists():
            QMessageBox.warning(self, "Ya existe", f"La carpeta '{nueva.name}' ya existe.")
            return
        nueva.mkdir(parents=True, exist_ok=True)
        self._poblar_arbol_archivos()
        self.lbl_estado.setText(f"📁 Carpeta creada: {nueva.name}")

    def _renombrar_item_arbol(self):
        ruta = self._obtener_ruta_item_seleccionado()
        mod_root = self.modulos_dir / self.modulo_actual if self.modulo_actual else None
        if not ruta or not mod_root or ruta == mod_root:
            QMessageBox.information(self, "Selección", "Selecciona un archivo o subcarpeta para renombrar.")
            return
        nuevo_nombre, ok = QInputDialog.getText(self, "Renombrar", "Nuevo nombre:", text=ruta.name)
        if not ok or not nuevo_nombre.strip() or nuevo_nombre.strip() == ruta.name:
            return
        destino = ruta.parent / nuevo_nombre.strip()
        if destino.exists():
            QMessageBox.warning(self, "Error", f"Ya existe '{destino.name}'.")
            return
        ruta.rename(destino)
        if self.archivo_actual == ruta:
            self.archivo_actual = destino
        self._poblar_arbol_archivos()
        self.lbl_estado.setText(f"✏️ Renombrado a {destino.name}")

    def _mover_item_arbol(self):
        ruta = self._obtener_ruta_item_seleccionado()
        mod_root = self.modulos_dir / self.modulo_actual if self.modulo_actual else None
        if not ruta or not mod_root or ruta == mod_root:
            QMessageBox.information(self, "Selección", "Selecciona un archivo o subcarpeta para mover.")
            return
        carpetas = [mod_root] + [
            p for p in sorted(mod_root.rglob("*"))
            if p.is_dir() and p.name not in {"__pycache__", ".git"} and p != ruta and ruta not in p.parents
        ]
        opciones = [
            ("." if c == mod_root else c.relative_to(mod_root).as_posix())
            for c in carpetas
        ]
        elegida, ok = QInputDialog.getItem(
            self, "Mover elemento", f"Mover '{ruta.name}' a carpeta:", opciones, 0, False
        )
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
        self.lbl_estado.setText(f"📦 Movido '{ruta.name}' -> {elegida}")

    def _eliminar_item_arbol(self):
        ruta = self._obtener_ruta_item_seleccionado()
        mod_root = self.modulos_dir / self.modulo_actual if self.modulo_actual else None
        if not ruta or not mod_root or ruta == mod_root:
            QMessageBox.information(self, "Selección", "Selecciona un archivo o subcarpeta para eliminar.")
            return
        resp = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar '{ruta.name}' permanentemente?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        if ruta.is_dir():
            shutil.rmtree(ruta)
        else:
            ruta.unlink(missing_ok=True)
        if self.archivo_actual == ruta:
            self.archivo_actual = None
            self.code_editor.clear()
            self.lbl_archivo_abierto.setText("Ningún archivo abierto")
        self._poblar_arbol_archivos()
        self.lbl_estado.setText(f"🗑️ Eliminado: {ruta.name}")

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

    # ── Diseñador Visual ──────────────────────────────────────────────────

    def _agregar_widget_diseno(self, tipo: str, label: str):
        idx = len(self.design_items) + 1
        var = f"{tipo.lower().replace('q', '')}_{idx}"
        self.design_items.append({
            "tipo": tipo,
            "var": var,
            "texto": f"{label} {idx}",
            "placeholder": "Escribe aquí..." if tipo == "QLineEdit" else "",
        })
        self._refrescar_preview_diseno()
        self.lista_diseno.setCurrentRow(len(self.design_items) - 1)

    def _on_widget_diseno_sel(self, row: int):
        if row < 0 or row >= len(self.design_items):
            return
        item = self.design_items[row]
        self._bloqueando_signals = True
        self.ent_prop_var.setText(item["var"])
        self.ent_prop_texto.setText(item["texto"])
        self.ent_prop_placeholder.setText(item.get("placeholder", ""))
        self._bloqueando_signals = False

    def _actualizar_prop_widget(self):
        if self._bloqueando_signals:
            return
        row = self.lista_diseno.currentRow()
        if row < 0 or row >= len(self.design_items):
            return
        item = self.design_items[row]
        item["var"] = normalizar_id_modulo(self.ent_prop_var.text() or item["var"])
        item["texto"] = self.ent_prop_texto.text()
        item["placeholder"] = self.ent_prop_placeholder.text()
        self._refrescar_preview_diseno(keep_row=row)

    def _mover_widget_diseno(self, delta: int):
        row = self.lista_diseno.currentRow()
        nuevo = row + delta
        if row < 0 or nuevo < 0 or nuevo >= len(self.design_items):
            return
        self.design_items[row], self.design_items[nuevo] = self.design_items[nuevo], self.design_items[row]
        self._refrescar_preview_diseno(keep_row=nuevo)

    def _eliminar_widget_diseno(self):
        row = self.lista_diseno.currentRow()
        if row < 0 or row >= len(self.design_items):
            return
        self.design_items.pop(row)
        self._refrescar_preview_diseno(keep_row=max(0, row - 1))

    def _refrescar_preview_diseno(self, keep_row: int | None = None):
        self._bloqueando_signals = True
        self.lista_diseno.clear()
        for it in self.design_items:
            self.lista_diseno.addItem(f"[{it['tipo']}] {it['var']} — {it['texto']}")
        if keep_row is not None and 0 <= keep_row < len(self.design_items):
            self.lista_diseno.setCurrentRow(keep_row)
        self._bloqueando_signals = False

        while self.preview_layout.count():
            child = self.preview_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for it in self.design_items:
            t = it["tipo"]
            txt = it["texto"]
            if t == "QLabel_title":
                w = QLabel(txt)
                w.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
            elif t == "QLabel":
                w = QLabel(txt)
                w.setStyleSheet("font-size: 12px; color: #cbd5e1;")
            elif t == "QPushButton":
                w = QPushButton(txt)
                w.setStyleSheet("background-color: #4f46e5; color: white; border-radius: 6px; padding: 8px 14px;")
            elif t == "QLineEdit":
                w = QLineEdit(txt)
                w.setPlaceholderText(it.get("placeholder", ""))
            elif t == "QTextEdit":
                w = QTextEdit(txt)
                w.setMaximumHeight(80)
            elif t == "QComboBox":
                w = QComboBox()
                w.addItems([txt or "Opción 1", "Opción 2"])
            elif t == "QCheckBox":
                w = QCheckBox(txt)
            elif t == "QProgressBar":
                w = QProgressBar()
                w.setValue(45)
            else:
                w = QLabel(txt)
            self.preview_layout.addWidget(w)
        self.preview_layout.addStretch(1)

    def _generar_codigo_pyqt(self, class_name: str, titulo: str) -> str:
        lines = [
            "# -*- coding: utf-8 -*-",
            "from PyQt6.QtWidgets import (",
            "    QCheckBox, QComboBox, QFrame, QLabel, QLineEdit,",
            "    QProgressBar, QPushButton, QTextEdit, QVBoxLayout",
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
            "        layout = QVBoxLayout(self)",
            "        layout.setContentsMargins(16, 16, 16, 16)",
            "        layout.setSpacing(10)",
            "",
        ]
        for it in self.design_items:
            var = it["var"]
            txt = it["texto"].replace('"', '\\"')
            t = it["tipo"]
            if t == "QLabel_title":
                lines.append(f'        self.{var} = QLabel("{txt}")')
                lines.append(f'        self.{var}.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")')
            elif t == "QLabel":
                lines.append(f'        self.{var} = QLabel("{txt}")')
                lines.append(f'        self.{var}.setStyleSheet("font-size: 13px; color: #e2e8f0;")')
            elif t == "QPushButton":
                lines.append(f'        self.{var} = QPushButton("{txt}")')
            elif t == "QLineEdit":
                ph = it.get("placeholder", "").replace('"', '\\"')
                lines.append(f'        self.{var} = QLineEdit("{txt}")')
                if ph:
                    lines.append(f'        self.{var}.setPlaceholderText("{ph}")')
            elif t == "QTextEdit":
                lines.append(f'        self.{var} = QTextEdit("{txt}")')
            elif t == "QComboBox":
                lines.append(f"        self.{var} = QComboBox()")
                lines.append(f'        self.{var}.addItems(["{txt or "Opción 1"}", "Opción 2"])')
            elif t == "QCheckBox":
                lines.append(f'        self.{var} = QCheckBox("{txt}")')
            elif t == "QProgressBar":
                lines.append(f"        self.{var} = QProgressBar()")
                lines.append(f"        self.{var}.setValue(0)")
            lines.append(f"        layout.addWidget(self.{var})")
            lines.append("")
        lines.append("        layout.addStretch(1)")
        lines.append("")
        return "\n".join(lines)

    def _sincronizar_diseno_a_codigo(self):
        if not self.modulo_actual:
            QMessageBox.information(self, "Sin módulo", "Primero crea o selecciona un módulo.")
            return
        if not self.archivo_actual or self.archivo_actual.suffix != ".py":
            self._abrir_archivo_principal_modulo()
        if not self.archivo_actual or self.archivo_actual.suffix != ".py":
            QMessageBox.warning(self, "Sin archivo Python", "No se encontró un archivo .py principal para sincronizar.")
            return

        clase = f"Tab{a_pascal_case(self.modulo_actual)}"
        cfg_path = self.modulos_dir / self.modulo_actual / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                subs = cfg.get("submodulos") or []
                if subs and subs[0].get("class_name"):
                    clase = subs[0]["class_name"]
            except Exception:
                pass

        codigo = self._generar_codigo_pyqt(clase, self.ent_cfg_name.text() or self.modulo_actual)
        self.code_editor.setPlainText(codigo)
        self._guardar_archivo_actual()
        self.tabs_editor.setCurrentIndex(1)
        self.lbl_estado.setText("✨ Diseño visual sincronizado al código Python y guardado.")

    # ── Integración con App y Compilador ──────────────────────────────────

    def _recargar_en_app(self):
        self._guardar_todo()
        app = self.app_ref or self.parent()
        if not app:
            QMessageBox.information(
                self,
                "Guardado",
                "Cambios guardados en vistas/modulos/. Abre Multitool para ver el módulo.",
            )
            return

        import importlib
        if self.modulo_actual:
            prefijo = f"vistas.modulos.{self.modulo_actual.lower()}"
            for k in list(sys.modules.keys()):
                if k == prefijo or k.startswith(prefijo + "."):
                    sys.modules.pop(k, None)
            importlib.invalidate_caches()

        try:
            # 1. Intentar recarga en caliente si el módulo ya estaba registrado en la app
            ya_registrado = any(
                m.get("folder", "").lower() == (self.modulo_actual or "").lower()
                or m.get("name", "").lower() == (self.modulo_actual or "").lower()
                for m in getattr(app, "modulos_cargados", [])
            )
            if ya_registrado and self.modulo_actual and hasattr(app, "recargar_modulo_en_caliente"):
                if app.recargar_modulo_en_caliente(self.modulo_actual):
                    self.lbl_estado.setText(f"🔥 Cambios aplicados en caliente en '{self.modulo_actual}' (sin reiniciar).")
                    return

            # 2. Si es un módulo nuevo o cambió su estructura, redescubrir y cargar
            if hasattr(app, "cargar_modulos"):
                app.cargar_modulos()
                self.lbl_estado.setText(f"🔄 Módulo '{self.modulo_actual}' cargado en Multitool sin reiniciar.")
                return
        except Exception as e:
            QMessageBox.warning(self, "Aviso", f"No se pudo recargar automáticamente:\n{e}")

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

