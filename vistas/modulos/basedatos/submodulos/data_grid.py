"""
data_grid.py - Cuadrícula de datos interactiva estilo DBeaver con edición, filtrado y exportación
"""
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTableWidget, QTableWidgetItem, QLineEdit, QFileDialog, 
    QMessageBox, QMenu, QHeaderView, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class DataGridWidget(QWidget):
    """Componente de visualización y edición tabular estilo DBeaver"""
    data_changed = pyqtSignal(str, str, object, str, object)  # table, pk_col, pk_val, col_name, new_val
    delete_row_requested = pyqtSignal(str, str, object)      # table, pk_col, pk_val
    refresh_requested = pyqtSignal()

    def __init__(self, colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.current_table = ""
        self.pk_column = ""
        self.raw_columns: List[str] = []
        self.raw_rows: List[Dict[str, Any]] = []
        self._is_loading = False

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Barra de herramientas superior
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍 Filtrar en resultados...")
        self.txt_filter.setFixedHeight(30)
        self.txt_filter.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.txt_filter.textChanged.connect(self._filtrar_resultados)
        toolbar.addWidget(self.txt_filter)

        self.btn_refresh = QPushButton("🔄 Refrescar")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setFixedHeight(30)
        self.btn_refresh.setStyleSheet(f"""
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
        self.btn_refresh.clicked.connect(lambda: self.refresh_requested.emit())
        toolbar.addWidget(self.btn_refresh)

        self.btn_export = QPushButton("📤 Exportar ▾")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setFixedHeight(30)
        self.btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #FFFFFF;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 14px;
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
        self.btn_export.clicked.connect(self._mostrar_menu_exportar)
        toolbar.addWidget(self.btn_export)

        toolbar.addStretch()

        self.lbl_info = QLabel("0 filas")
        self.lbl_info.setStyleSheet("color: #94A3B8; font-size: 11px;")
        toolbar.addWidget(self.lbl_info)

        layout.addLayout(toolbar)

        # Tabla interactiva
        self.table = QTableWidget()
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                alternate-background-color: #171724;
                color: #F1F5F9;
                gridline-color: rgba(255, 255, 255, 0.06);
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
                font-size: 11px;
                selection-background-color: {self.colores.get('acento', '#6366F1')};
                selection-color: #FFFFFF;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
            }}
            QHeaderView {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: none;
            }}
            QHeaderView::section {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #CBD5E1;
                padding: 6px 10px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                font-weight: bold;
                font-size: 11px;
            }}
            QHeaderView::section:horizontal {{
                border-top: none;
            }}
            QHeaderView::section:vertical {{
                border-left: none;
            }}
            QTableCornerButton::section {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            QScrollBar:vertical, QScrollBar:horizontal {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                width: 8px;
                height: 8px;
            }}
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 4px;
            }}
        """)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        layout.addWidget(self.table)

    def load_data(self, columns: List[str], rows: List[Dict[str, Any]], table_name: str = "", pk_col: str = "", duration_ms: float = 0.0):
        self._is_loading = True
        self.current_table = table_name
        self.pk_column = pk_col
        self.raw_columns = columns
        self.raw_rows = rows

        self.table.clear()
        self.table.setColumnCount(len(columns))
        self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels(columns)

        for r_idx, row_dict in enumerate(rows):
            for c_idx, col in enumerate(columns):
                val = row_dict.get(col)
                val_str = "" if val is None else str(val)
                item = QTableWidgetItem(val_str)
                if val is None:
                    item.setForeground(QColor("#64748B"))  # NULL en gris tenue
                    item.setText("NULL")
                self.table.setItem(r_idx, c_idx, item)

        self.table.resizeColumnsToContents()
        self._is_loading = False

        self.lbl_info.setText(f"{len(rows)} filas | {duration_ms} ms")

    def _on_cell_changed(self, row: int, col: int):
        if self._is_loading or not self.current_table or not self.pk_column:
            return

        col_name = self.raw_columns[col]
        item = self.table.item(row, col)
        new_val = item.text() if item else ""
        if new_val == "NULL":
            new_val = None

        # Obtener el valor de la clave primaria para esta fila
        if self.pk_column in self.raw_columns:
            pk_col_idx = self.raw_columns.index(self.pk_column)
            pk_item = self.table.item(row, pk_col_idx)
            pk_val = pk_item.text() if pk_item else None
            if pk_val is not None:
                self.data_changed.emit(self.current_table, self.pk_column, pk_val, col_name, new_val)

    def _filtrar_resultados(self, text: str):
        query = text.strip().lower()
        visible_count = 0
        for r in range(self.table.rowCount()):
            row_match = False
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item and query in item.text().lower():
                    row_match = True
                    break
            self.table.setRowHidden(r, not row_match)
            if row_match:
                visible_count += 1

        total = self.table.rowCount()
        self.lbl_info.setText(f"{visible_count}/{total} filas coincidentes")

    def _mostrar_menu_exportar(self):
        if not self.raw_rows or not self.raw_columns:
            QMessageBox.information(self, "Exportar", "No hay datos para exportar.")
            return

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
        a_csv = menu.addAction("📄 Exportar a CSV (.csv)")
        a_json = menu.addAction("📋 Exportar a JSON (.json)")
        a_sql = menu.addAction("📜 Exportar a SQL Inserts (.sql)")

        action = menu.exec(self.btn_export.mapToGlobal(self.btn_export.rect().bottomLeft()))
        if not action:
            return

        default_name = f"{self.current_table or 'export'}"
        if action == a_csv:
            path, _ = QFileDialog.getSaveFileName(self, "Exportar CSV", f"{default_name}.csv", "Archivos CSV (*.csv)")
            if path:
                import csv
                with open(path, "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=self.raw_columns)
                    w.writeheader()
                    w.writerows(self.raw_rows)
                QMessageBox.information(self, "Éxito", f"Datos exportados a CSV:\n{path}")
        elif action == a_json:
            path, _ = QFileDialog.getSaveFileName(self, "Exportar JSON", f"{default_name}.json", "Archivos JSON (*.json)")
            if path:
                import json
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.raw_rows, f, indent=4, ensure_ascii=False)
                QMessageBox.information(self, "Éxito", f"Datos exportados a JSON:\n{path}")
        elif action == a_sql:
            path, _ = QFileDialog.getSaveFileName(self, "Exportar SQL", f"{default_name}.sql", "Archivos SQL (*.sql)")
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    t_name = self.current_table or "tabla"
                    cols = ", ".join([f'"{c}"' for c in self.raw_columns])
                    for r in self.raw_rows:
                        vals = []
                        for c in self.raw_columns:
                            v = r.get(c)
                            if v is None:
                                vals.append("NULL")
                            elif isinstance(v, (int, float)):
                                vals.append(str(v))
                            else:
                                vals.append(f"'{str(v).replace('\'', '\'\'')}'")
                        f.write(f'INSERT INTO "{t_name}" ({cols}) VALUES ({", ".join(vals)});\n')
                QMessageBox.information(self, "Éxito", f"Sentencias SQL exportadas:\n{path}")

    def _mostrar_menu_contextual(self, pos):
        item = self.table.itemAt(pos)
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
                color: #FFFFFF !important;
            }}
        """)
        
        act_copy_cell = menu.addAction("📋 Copiar Celda")
        act_copy_row = menu.addAction("📑 Copiar Fila (JSON)")
        menu.addSeparator()
        act_del_row = menu.addAction("➖ Eliminar Fila Seleccionada")
        menu.addSeparator()
        act_refresh = menu.addAction("🔄 Refrescar Datos")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if not action:
            return

        row = self.table.currentRow()
        if action == act_copy_cell and item:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(item.text())
        elif action == act_copy_row and row >= 0:
            from PyQt6.QtWidgets import QApplication
            import json
            row_data = {}
            for c in range(self.table.columnCount()):
                col_name = self.raw_columns[c] if c < len(self.raw_columns) else f"col_{c}"
                it = self.table.item(row, c)
                row_data[col_name] = it.text() if it else None
            QApplication.clipboard().setText(json.dumps(row_data, indent=2, ensure_ascii=False))
        elif action == act_del_row and row >= 0 and self.current_table and self.pk_column:
            pk_col_idx = self.raw_columns.index(self.pk_column) if self.pk_column in self.raw_columns else -1
            if pk_col_idx >= 0:
                pk_it = self.table.item(row, pk_col_idx)
                if pk_it:
                    self.delete_row_requested.emit(self.current_table, self.pk_column, pk_it.text())
        elif action == act_refresh:
            self.refresh_requested.emit()

