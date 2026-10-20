"""
query_history.py - Historial persistente de consultas SQL y fragmentos (snippets) favoritos estilo DBeaver
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
    QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class QueryHistoryWidget(QWidget):
    """Componente para visualizar, buscar y reutilizar el historial de consultas ejecutadas"""
    query_selected = pyqtSignal(str)  # Emite el SQL seleccionado para inyectarlo en el editor

    def __init__(self, colores: dict, history_path: Path, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.history_path = history_path
        self.history_records: List[Dict[str, Any]] = []

        self.init_ui()
        self.load_history()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Barra superior de filtros
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        lbl_title = QLabel("📜  Historial de Consultas & Fragmentos")
        lbl_title.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        toolbar.addWidget(lbl_title)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍 Buscar en el historial...")
        self.txt_filter.setFixedHeight(28)
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
        self.txt_filter.textChanged.connect(self._filtrar_historial)
        toolbar.addWidget(self.txt_filter)

        btn_favs_only = QPushButton("⭐ Solo Favoritos")
        btn_favs_only.setCheckable(True)
        btn_favs_only.setFixedHeight(28)
        btn_favs_only.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #CBD5E1;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
                outline: none;
            }}
            QPushButton:checked {{
                background-color: rgba(251, 191, 36, 0.2);
                border-color: #FBBF24;
                color: #FBBF24;
                font-weight: bold;
            }}
        """)
        btn_favs_only.toggled.connect(self._filtrar_historial)
        self.btn_favs = btn_favs_only
        toolbar.addWidget(btn_favs_only)

        toolbar.addStretch()

        btn_load = QPushButton("▶ Cargar en Editor")
        btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_load.setFixedHeight(28)
        btn_load.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
                border: none;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        btn_load.clicked.connect(self._cargar_seleccionada)
        toolbar.addWidget(btn_load)

        btn_clear = QPushButton("🧹 Limpiar")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setFixedHeight(28)
        btn_clear.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #AAB0B8;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
                outline: none;
            }}
            QPushButton:hover {{
                color: #F87171;
            }}
        """)
        btn_clear.clicked.connect(self._limpiar_historial)
        toolbar.addWidget(btn_clear)

        layout.addLayout(toolbar)

        # Tabla del historial
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Fav", "Hora / Fecha", "Duración", "Estado", "Sentencia SQL"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                alternate-background-color: #171724;
                color: #F1F5F9;
                gridline-color: rgba(255, 255, 255, 0.05);
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
                font-size: 11px;
                selection-background-color: {self.colores.get('acento', '#6366F1')};
                selection-color: #FFFFFF;
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
            QTableCornerButton::section {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemDoubleClicked.connect(lambda it: self._cargar_seleccionada())
        layout.addWidget(self.table)

    def load_history(self):
        if self.history_path.exists():
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    self.history_records = json.load(f)
            except Exception:
                self.history_records = []
        self._render_table(self.history_records)

    def save_history(self):
        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(self.history_records[:500], f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def add_entry(self, sql: str, duration_ms: float, success: bool, rows: int):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sql": sql.strip(),
            "duration_ms": duration_ms,
            "success": success,
            "rows": rows,
            "favorite": False
        }
        self.history_records.insert(0, entry)
        self.save_history()
        self._filtrar_historial()

    def _render_table(self, records: List[Dict[str, Any]]):
        self.table.setRowCount(len(records))
        for r_idx, rec in enumerate(records):
            is_fav = rec.get("favorite", False)
            btn_fav = QPushButton("⭐" if is_fav else "☆")
            btn_fav.setFixedSize(26, 24)
            btn_fav.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_fav.setStyleSheet("background: transparent; border: none; font-size: 13px; color: #FBBF24;")
            btn_fav.clicked.connect(lambda _, idx=r_idx, r=rec: self._toggle_favorite(idx, r))
            self.table.setCellWidget(r_idx, 0, btn_fav)

            item_time = QTableWidgetItem(rec.get("timestamp", ""))
            item_time.setForeground(QColor("#94A3B8"))
            self.table.setItem(r_idx, 1, item_time)

            item_dur = QTableWidgetItem(f"{rec.get('duration_ms', 0)} ms")
            item_dur.setForeground(QColor("#CBD5E1"))
            self.table.setItem(r_idx, 2, item_dur)

            status_str = f"✅ {rec.get('rows', 0)} f" if rec.get("success") else "❌ Error"
            item_status = QTableWidgetItem(status_str)
            item_status.setForeground(QColor("#34D399" if rec.get("success") else "#F87171"))
            self.table.setItem(r_idx, 3, item_status)

            sql_clean = rec.get("sql", "").replace("\n", " ")
            item_sql = QTableWidgetItem(sql_clean[:180])
            item_sql.setData(Qt.ItemDataRole.UserRole, rec.get("sql", ""))
            self.table.setItem(r_idx, 4, item_sql)

    def _toggle_favorite(self, r_idx: int, rec: dict):
        rec["favorite"] = not rec.get("favorite", False)
        self.save_history()
        self._filtrar_historial()

    def _filtrar_historial(self):
        query = self.txt_filter.text().strip().lower()
        fav_only = self.btn_favs.isChecked()

        filtered = []
        for r in self.history_records:
            if fav_only and not r.get("favorite"):
                continue
            if query and query not in r.get("sql", "").lower():
                continue
            filtered.append(r)
        self._render_table(filtered)

    def _cargar_seleccionada(self):
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 4)
            if item:
                sql = item.data(Qt.ItemDataRole.UserRole) or item.text()
                self.query_selected.emit(sql)

    def _limpiar_historial(self):
        confirm = QMessageBox.question(
            self, "Limpiar Historial", "¿Deseas borrar todo el historial de consultas ejecutadas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.history_records = [r for r in self.history_records if r.get("favorite")]
            self.save_history()
            self._filtrar_historial()
