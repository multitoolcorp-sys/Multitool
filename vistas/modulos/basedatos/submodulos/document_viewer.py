"""
document_viewer.py - Visor y editor interactivo de documentos NoSQL (MongoDB y NoSQL Local)
Soporta vista dual (Tabla Aplanada y Árbol JSON jerárquico), paginación, filtros JSON y CRUD.
"""
import json
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QDialog, QTextEdit, QMessageBox, QFileDialog,
    QComboBox, QHeaderView, QMenu, QApplication, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon


class JsonDocumentEditDialog(QDialog):
    """Diálogo modal con validación de sintaxis JSON en tiempo real para insertar o editar documentos"""
    def __init__(self, initial_doc: dict = None, is_new: bool = True, colores: dict = None, parent=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.is_new = is_new
        self.result_doc = None
        self.setWindowTitle("➕ Nuevo Documento JSON" if is_new else "✏️ Editar Documento JSON")
        self.setMinimumSize(540, 480)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores.get('bg_principal', '#121218')};
                color: white;
            }}
            QLabel {{
                color: #CBD5E1;
                font-size: 11px;
            }}
            QTextEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #F8FAFC;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 8px;
                font-family: Consolas;
                font-size: 11px;
            }}
            QTextEdit:focus {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        lbl_desc = QLabel(
            "Ingresa el documento en formato JSON válido:" if is_new else "Modifica los campos del documento JSON:"
        )
        lbl_desc.setStyleSheet("font-weight: bold; color: white;")
        layout.addWidget(lbl_desc)

        self.txt_json = QTextEdit()
        if initial_doc:
            clean_initial = dict(initial_doc)
            self.txt_json.setText(json.dumps(clean_initial, indent=2, ensure_ascii=False))
        else:
            self.txt_json.setText(json.dumps({
                "nombre": "Nuevo Registro",
                "activo": True,
                "detalles": {
                    "categoria": "General",
                    "valor": 100
                }
            }, indent=2, ensure_ascii=False))
        self.txt_json.textChanged.connect(self._validar_sintaxis)
        layout.addWidget(self.txt_json)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #34D399; font-size: 10px;")
        layout.addWidget(self.lbl_error)

        btn_box = QHBoxLayout()
        self.btn_format = QPushButton("✨ Formatear JSON")
        self.btn_format.setFixedHeight(30)
        self.btn_format.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.btn_format.clicked.connect(self._formatear_json)
        btn_box.addWidget(self.btn_format)

        btn_box.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFixedHeight(30)
        btn_cancel.setStyleSheet("background: transparent; color: #AAB0B8; border: none; padding: 0 12px;")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        self.btn_save = QPushButton("Guardar Documento")
        self.btn_save.setFixedHeight(30)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 0 16px;
                font-size: 11px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        self.btn_save.clicked.connect(self._guardar)
        btn_box.addWidget(self.btn_save)

        layout.addLayout(btn_box)
        self._validar_sintaxis()

    def _validar_sintaxis(self):
        text = self.txt_json.toPlainText().strip()
        if not text:
            self.lbl_error.setText("⚠️ El documento está vacío.")
            self.lbl_error.setStyleSheet("color: #FBBF24; font-size: 10px;")
            self.btn_save.setEnabled(False)
            return

        try:
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                self.lbl_error.setText("⚠️ La raíz del documento debe ser un objeto JSON (ej: {...}).")
                self.lbl_error.setStyleSheet("color: #FBBF24; font-size: 10px;")
                self.btn_save.setEnabled(False)
                return
            self.lbl_error.setText("✅ JSON válido.")
            self.lbl_error.setStyleSheet("color: #34D399; font-size: 10px;")
            self.btn_save.setEnabled(True)
        except json.JSONDecodeError as err:
            self.lbl_error.setText(f"❌ Error de sintaxis JSON: {err.msg} (línea {err.lineno}, col {err.colno})")
            self.lbl_error.setStyleSheet("color: #F87171; font-size: 10px;")
            self.btn_save.setEnabled(False)

    def _formatear_json(self):
        try:
            parsed = json.loads(self.txt_json.toPlainText().strip())
            self.txt_json.setText(json.dumps(parsed, indent=2, ensure_ascii=False))
        except Exception:
            pass

    def _guardar(self):
        try:
            parsed = json.loads(self.txt_json.toPlainText().strip())
            if isinstance(parsed, dict):
                self.result_doc = parsed
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Sintaxis JSON inválida:\n{e}")


class DocumentViewerWidget(QWidget):
    """Visor completo y gestor NoSQL para colecciones de MongoDB y NoSQL Local"""
    data_changed = pyqtSignal()

    def __init__(self, colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.active_db = None
        self.database_name = ""
        self.collection_name = ""
        self.raw_documents: List[Dict[str, Any]] = []
        self.total_count = 0
        self.page = 1
        self.page_size = 50
        self.filter_dict = {}

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ── Barra Superior de Colección y Modo de Vista ───────────────
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.lbl_col_title = QLabel("🍃 Colección: (sin seleccionar)")
        self.lbl_col_title.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        top_bar.addWidget(self.lbl_col_title)

        self.lbl_count = QLabel("(0 documentos)")
        self.lbl_count.setStyleSheet("color: #94A3B8; font-size: 11px;")
        top_bar.addWidget(self.lbl_count)

        top_bar.addStretch()

        self.btn_view_table = QPushButton("📋 Vista Tabla")
        self.btn_view_table.setCheckable(True)
        self.btn_view_table.setChecked(True)
        self.btn_view_table.setFixedHeight(28)
        self.btn_view_table.setStyleSheet(self._btn_mode_style(True))
        self.btn_view_table.clicked.connect(lambda: self._set_view_mode(0))
        top_bar.addWidget(self.btn_view_table)

        self.btn_view_tree = QPushButton("🌳 Vista Árbol JSON")
        self.btn_view_tree.setCheckable(True)
        self.btn_view_tree.setChecked(False)
        self.btn_view_tree.setFixedHeight(28)
        self.btn_view_tree.setStyleSheet(self._btn_mode_style(False))
        self.btn_view_tree.clicked.connect(lambda: self._set_view_mode(1))
        top_bar.addWidget(self.btn_view_tree)

        layout.addLayout(top_bar)

        # ── Barra de Búsqueda / Filtro JSON y Paginación ───────────────
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        lbl_filter = QLabel("Filtro:")
        lbl_filter.setStyleSheet("color: #CBD5E1; font-size: 11px;")
        filter_bar.addWidget(lbl_filter)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText('Filtro JSON (ej: {"nombre": "Alice"} o vacío para todos)')
        self.txt_filter.setFixedHeight(30)
        self.txt_filter.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 10px;
                font-family: Consolas;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.txt_filter.returnPressed.connect(self._aplicar_filtro)
        filter_bar.addWidget(self.txt_filter, 3)

        btn_search = QPushButton("🔍 Filtrar")
        btn_search.setFixedHeight(30)
        btn_search.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        btn_search.clicked.connect(self._aplicar_filtro)
        filter_bar.addWidget(btn_search)

        btn_clear_flt = QPushButton("Limpiar")
        btn_clear_flt.setFixedHeight(30)
        btn_clear_flt.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #CBD5E1;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn_clear_flt.clicked.connect(self._limpiar_filtro)
        filter_bar.addWidget(btn_clear_flt)

        filter_bar.addSpacing(12)

        self.cb_page_size = QComboBox()
        self.cb_page_size.addItems(["25 docs", "50 docs", "100 docs", "250 docs"])
        self.cb_page_size.setCurrentIndex(1)
        self.cb_page_size.setFixedHeight(30)
        self.cb_page_size.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 8px;
                font-size: 11px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                selection-background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.cb_page_size.currentIndexChanged.connect(self._on_page_size_changed)
        filter_bar.addWidget(self.cb_page_size)

        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedSize(30, 30)
        self.btn_prev.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')}; border-radius: 6px;")
        self.btn_prev.clicked.connect(self._pagina_anterior)
        filter_bar.addWidget(self.btn_prev)

        self.lbl_page = QLabel("Pág 1 / 1")
        self.lbl_page.setStyleSheet("color: white; font-size: 11px; padding: 0 4px;")
        filter_bar.addWidget(self.lbl_page)

        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedSize(30, 30)
        self.btn_next.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')}; border-radius: 6px;")
        self.btn_next.clicked.connect(self._pagina_siguiente)
        filter_bar.addWidget(self.btn_next)

        layout.addLayout(filter_bar)

        # ── Stack de Vistas: Página 0 (Tabla) / Página 1 (Árbol JSON) ─
        self.stack = QStackedWidget()

        # 0. Vista Tabla
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._on_table_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #F8FAFC;
                gridline-color: rgba(255,255,255,0.06);
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
                font-size: 11px;
            }}
            QTableWidget::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #CBD5E1;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 10px;
                border: none;
                border-right: 1px solid rgba(255,255,255,0.08);
            }}
        """)
        self.stack.addWidget(self.table)

        # 1. Vista Árbol
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Propiedad / Documento", "Valor"])
        self.tree.setColumnWidth(0, 300)
        self.tree.header().setStretchLastSection(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #F8FAFC;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
                padding: 4px;
                font-family: Consolas;
                font-size: 11px;
            }}
            QTreeWidget::item {{
                padding: 4px;
            }}
            QTreeWidget::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #CBD5E1;
                font-weight: bold;
                padding: 6px;
                border: none;
            }}
        """)
        self.stack.addWidget(self.tree)

        layout.addWidget(self.stack, 1)

        # ── Barra Inferior de Acciones CRUD y Estado ───────────────────
        bot_bar = QHBoxLayout()
        bot_bar.setSpacing(8)

        self.btn_add_doc = QPushButton("➕ Nuevo Documento")
        self.btn_add_doc.setFixedHeight(30)
        self.btn_add_doc.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #34D399;
                font-weight: bold;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(52, 211, 153, 0.15);
                border-color: #34D399;
            }}
        """)
        self.btn_add_doc.clicked.connect(self._nuevo_documento)
        bot_bar.addWidget(self.btn_add_doc)

        self.btn_edit_doc = QPushButton("✏️ Editar")
        self.btn_edit_doc.setFixedHeight(30)
        self.btn_edit_doc.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #CBD5E1;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
        """)
        self.btn_edit_doc.clicked.connect(self._editar_seleccionado)
        bot_bar.addWidget(self.btn_edit_doc)

        self.btn_del_doc = QPushButton("🗑️ Eliminar")
        self.btn_del_doc.setFixedHeight(30)
        self.btn_del_doc.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #F87171;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(248, 113, 113, 0.15);
                border-color: #F87171;
            }}
        """)
        self.btn_del_doc.clicked.connect(self._eliminar_seleccionado)
        bot_bar.addWidget(self.btn_del_doc)

        self.btn_refresh = QPushButton("🔄 Refrescar")
        self.btn_refresh.setFixedHeight(30)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #CBD5E1;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
        """)
        self.btn_refresh.clicked.connect(self.cargar_datos)
        bot_bar.addWidget(self.btn_refresh)

        self.btn_export = QPushButton("📤 Exportar JSON")
        self.btn_export.setFixedHeight(30)
        self.btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #CBD5E1;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
        """)
        self.btn_export.clicked.connect(self._exportar_json)
        bot_bar.addWidget(self.btn_export)

        bot_bar.addStretch()

        self.lbl_status = QLabel("Listo.")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 11px;")
        bot_bar.addWidget(self.lbl_status)

        layout.addLayout(bot_bar)

    def _btn_mode_style(self, active: bool) -> str:
        if active:
            return f"""
                QPushButton {{
                    background-color: {self.colores.get('acento', '#6366F1')};
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 0 10px;
                    font-size: 11px;
                    border: none;
                }}
            """
        return f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #CBD5E1;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
        """

    def _set_view_mode(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self.btn_view_table.setChecked(idx == 0)
        self.btn_view_table.setStyleSheet(self._btn_mode_style(idx == 0))
        self.btn_view_tree.setChecked(idx == 1)
        self.btn_view_tree.setStyleSheet(self._btn_mode_style(idx == 1))

    def set_collection(self, db_conn, database_name: str, collection_name: str):
        """Asigna la conexión y colección activa y carga los datos"""
        self.active_db = db_conn
        self.database_name = database_name
        self.collection_name = collection_name
        icon = "🍃" if getattr(db_conn, "engine", "") == "mongodb" else "📁"
        self.lbl_col_title.setText(f"{icon} Colección: {collection_name}")
        self.page = 1
        self.cargar_datos()

    def cargar_datos(self):
        """Carga los documentos desde MongoDB o NoSQL Local usando paginación y filtros"""
        if not self.active_db or not self.collection_name:
            return

        limit = self.page_size
        skip = (self.page - 1) * self.page_size

        docs, total, duration_ms, err = self.active_db.find_documents(
            database=self.database_name,
            collection=self.collection_name,
            filter_dict=self.filter_dict,
            limit=limit,
            skip=skip
        )

        if err:
            self.lbl_status.setText(f"❌ Error: {err}")
            self.lbl_status.setStyleSheet("color: #F87171; font-size: 11px;")
            return

        self.raw_documents = docs
        self.total_count = total

        # Actualizar indicadores de paginación
        max_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        self.lbl_page.setText(f"Pág {self.page} / {max_pages}")
        self.btn_prev.setEnabled(self.page > 1)
        self.btn_next.setEnabled(self.page < max_pages)

        self.lbl_count.setText(f"({self.total_count} docs en total)")
        self.lbl_status.setText(f"⏱️ {duration_ms} ms | {len(docs)} cargados")
        self.lbl_status.setStyleSheet("color: #34D399; font-size: 11px;")

        # Renderizar en ambas vistas
        self._render_table_view()
        self._render_tree_view()

    def _render_table_view(self):
        self.table.clear()
        if not self.raw_documents:
            self.table.setRowCount(0)
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["Mensaje"])
            item = QTableWidgetItem("No se encontraron documentos en esta colección o filtro.")
            item.setForeground(QColor("#94A3B8"))
            self.table.setRowCount(1)
            self.table.setItem(0, 0, item)
            return

        # Descubrir columnas comunes manteniendo _id en primera posición
        cols = []
        for doc in self.raw_documents:
            for k in doc.keys():
                if k not in cols:
                    cols.append(k)
        if "_id" in cols:
            cols.remove("_id")
            cols.insert(0, "_id")

        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setRowCount(len(self.raw_documents))

        for row_idx, doc in enumerate(self.raw_documents):
            for col_idx, col_name in enumerate(cols):
                val = doc.get(col_name)
                if val is None:
                    txt = "NULL"
                    color = "#64748B"
                elif isinstance(val, (dict, list)):
                    txt = json.dumps(val, ensure_ascii=False)
                    color = "#F59E0B"
                elif isinstance(val, bool):
                    txt = "true" if val else "false"
                    color = "#34D399" if val else "#F87171"
                elif isinstance(val, (int, float)):
                    txt = str(val)
                    color = "#60A5FA"
                else:
                    txt = str(val)
                    color = "#F8FAFC"

                item = QTableWidgetItem(txt)
                item.setForeground(QColor(color))
                item.setData(Qt.ItemDataRole.UserRole, doc)
                self.table.setItem(row_idx, col_idx, item)

        self.table.resizeColumnsToContents()

    def _render_tree_view(self):
        self.tree.clear()
        if not self.raw_documents:
            root = QTreeWidgetItem(self.tree)
            root.setText(0, "Sin documentos")
            return

        for idx, doc in enumerate(self.raw_documents):
            doc_id = str(doc.get("_id", f"doc_{idx}"))
            root = QTreeWidgetItem(self.tree)
            root.setText(0, f"📄 [{idx+1}] Documento (_id: {doc_id})")
            root.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
            root.setData(0, Qt.ItemDataRole.UserRole, doc)
            self._populate_tree_node(root, doc)

    def _populate_tree_node(self, parent_item: QTreeWidgetItem, data: Any):
        if isinstance(data, dict):
            for k, v in data.items():
                child = QTreeWidgetItem(parent_item)
                child.setText(0, str(k))
                if isinstance(v, (dict, list)):
                    child.setText(1, f"[{type(v).__name__}] ({len(v)} elementos)")
                    child.setForeground(1, QColor("#F59E0B"))
                    self._populate_tree_node(child, v)
                else:
                    child.setText(1, str(v))
                    color = "#34D399" if isinstance(v, bool) else ("#60A5FA" if isinstance(v, (int, float)) else "#F8FAFC")
                    child.setForeground(1, QColor(color))
        elif isinstance(data, list):
            for idx, v in enumerate(data):
                child = QTreeWidgetItem(parent_item)
                child.setText(0, f"[{idx}]")
                if isinstance(v, (dict, list)):
                    child.setText(1, f"[{type(v).__name__}] ({len(v)} elementos)")
                    child.setForeground(1, QColor("#F59E0B"))
                    self._populate_tree_node(child, v)
                else:
                    child.setText(1, str(v))
                    child.setForeground(1, QColor("#F8FAFC"))

    def _aplicar_filtro(self):
        raw = self.txt_filter.text().strip()
        if not raw:
            self.filter_dict = {}
        else:
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    QMessageBox.warning(self, "Filtro no válido", "El filtro debe ser un objeto JSON (ej: {\"campo\": \"valor\"}).")
                    return
                self.filter_dict = parsed
            except Exception as e:
                QMessageBox.warning(self, "Error de Sintaxis JSON", f"El filtro no es un JSON válido:\n{e}")
                return
        self.page = 1
        self.cargar_datos()

    def _limpiar_filtro(self):
        self.txt_filter.clear()
        self.filter_dict = {}
        self.page = 1
        self.cargar_datos()

    def _on_page_size_changed(self, idx: int):
        sizes = [25, 50, 100, 250]
        self.page_size = sizes[idx]
        self.page = 1
        self.cargar_datos()

    def _pagina_anterior(self):
        if self.page > 1:
            self.page -= 1
            self.cargar_datos()

    def _pagina_siguiente(self):
        max_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        if self.page < max_pages:
            self.page += 1
            self.cargar_datos()

    def _obtener_documento_seleccionado(self) -> Optional[dict]:
        if self.stack.currentIndex() == 0:
            # Vista Tabla
            row = self.table.currentRow()
            if 0 <= row < len(self.raw_documents):
                return self.raw_documents[row]
        else:
            # Vista Árbol
            item = self.tree.currentItem()
            while item and item.parent():
                item = item.parent()
            if item:
                return item.data(0, Qt.ItemDataRole.UserRole)
        return None

    def _on_table_double_clicked(self, model_idx):
        self._editar_seleccionado()

    def _nuevo_documento(self):
        if not self.active_db or not self.collection_name:
            return
        dlg = JsonDocumentEditDialog(initial_doc=None, is_new=True, colores=self.colores, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_doc:
            ok, res_id = self.active_db.insert_document(self.database_name, self.collection_name, dlg.result_doc)
            if ok:
                self.lbl_status.setText(f"✅ Documento insertado con _id: {res_id}")
                self.lbl_status.setStyleSheet("color: #34D399; font-size: 11px;")
                self.cargar_datos()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error al insertar", f"No se pudo guardar el documento:\n{res_id}")

    def _editar_seleccionado(self):
        doc = self._obtener_documento_seleccionado()
        if not doc:
            QMessageBox.information(self, "Seleccionar", "Selecciona un documento para editar.")
            return

        dlg = JsonDocumentEditDialog(initial_doc=doc, is_new=False, colores=self.colores, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_doc:
            doc_id = doc.get("_id")
            ok, msg = self.active_db.update_document(self.database_name, self.collection_name, doc_id, dlg.result_doc)
            if ok:
                self.lbl_status.setText(f"✅ Documento actualizado (_id: {doc_id})")
                self.lbl_status.setStyleSheet("color: #34D399; font-size: 11px;")
                self.cargar_datos()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error al actualizar", f"No se pudo actualizar el documento:\n{msg}")

    def _eliminar_seleccionado(self):
        doc = self._obtener_documento_seleccionado()
        if not doc:
            QMessageBox.information(self, "Seleccionar", "Selecciona un documento para eliminar.")
            return

        doc_id = doc.get("_id")
        confirm = QMessageBox.question(
            self, "Eliminar Documento",
            f"¿Estás seguro de eliminar el documento con _id '{doc_id}' de '{self.collection_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            ok, msg = self.active_db.delete_document(self.database_name, self.collection_name, doc_id)
            if ok:
                self.lbl_status.setText(f"✅ Documento eliminado.")
                self.lbl_status.setStyleSheet("color: #34D399; font-size: 11px;")
                self.cargar_datos()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error al eliminar", f"No se pudo eliminar el documento:\n{msg}")

    def _mostrar_menu_contextual(self, pos):
        doc = self._obtener_documento_seleccionado()
        if not doc:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 18px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)

        a_edit = menu.addAction("✏️ Editar Documento...")
        a_copy = menu.addAction("📋 Copiar JSON al Portapapeles")
        menu.addSeparator()
        a_del = menu.addAction("🗑️ Eliminar Documento")

        widget = self.table if self.stack.currentIndex() == 0 else self.tree
        act = menu.exec(widget.viewport().mapToGlobal(pos))
        if act == a_edit:
            self._editar_seleccionado()
        elif act == a_copy:
            QApplication.clipboard().setText(json.dumps(doc, indent=2, ensure_ascii=False))
            self.lbl_status.setText("📋 JSON copiado al portapapeles.")
        elif act == a_del:
            self._eliminar_seleccionado()

    def _exportar_json(self):
        if not self.raw_documents:
            QMessageBox.information(self, "Exportar", "No hay documentos para exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Colección a JSON", f"{self.collection_name}.json", "Archivos JSON (*.json);;Todos (*.*)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.raw_documents, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Exportación Exitosa", f"Se exportaron {len(self.raw_documents)} documentos a:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error al Exportar", f"No se pudo guardar el archivo:\n{e}")
