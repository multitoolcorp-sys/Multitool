"""
data_importer.py - Asistente de importación de datos (CSV / JSON a Tabla) estilo DBeaver
Permite previsualizar, mapear tipos de datos, crear nuevas tablas o insertar en tablas existentes con barra de progreso.
"""
import csv
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QRadioButton, QButtonGroup, 
    QFileDialog, QMessageBox, QProgressBar, QTableWidget, 
    QTableWidgetItem, QHeaderView, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class ImportWorkerThread(QThread):
    """Hilo de importación para evitar bloquear la interfaz durante cargas grandes"""
    progress = pyqtSignal(int, int)  # procesadas, total
    finished = pyqtSignal(bool, str, int)  # exito, mensaje, total_insertadas

    def __init__(self, db_conn, target_table: str, create_table: bool, columns: List[str], col_types: Dict[str, str], rows_data: List[Dict[str, Any]]):
        super().__init__()
        self.db_conn = db_conn
        self.target_table = target_table
        self.create_table = create_table
        self.columns = columns
        self.col_types = col_types
        self.rows_data = rows_data

    def run(self):
        try:
            total = len(self.rows_data)
            engine = getattr(self.db_conn, "engine", "sqlite")
            q = '`' if engine == "mysql" else '"'

            # 1. Crear tabla si es requerido
            if self.create_table:
                col_defs = []
                for c in self.columns:
                    t = self.col_types.get(c, "TEXT")
                    col_defs.append(f"{q}{c}{q} {t}")
                create_sql = f"CREATE TABLE IF NOT EXISTS {q}{self.target_table}{q} ({', '.join(col_defs)});"
                _, _, _, _, err = self.db_conn.execute_query(create_sql)
                if err:
                    self.finished.emit(False, f"Error creando tabla: {err}", 0)
                    return

            # 2. Inserción por lotes
            cols_str = ", ".join([f"{q}{c}{q}" for c in self.columns])
            placeholder = "%s" if engine in ("mysql", "postgresql") else "?"
            placeholders_str = ", ".join([placeholder] * len(self.columns))
            insert_sql = f"INSERT INTO {q}{self.target_table}{q} ({cols_str}) VALUES ({placeholders_str});"

            inserted = 0
            batch_size = 150
            batch = []

            for idx, r in enumerate(self.rows_data):
                row_vals = tuple(r.get(c) for c in self.columns)
                batch.append(row_vals)

                if len(batch) >= batch_size:
                    for b_row in batch:
                        _, _, _, _, err = self.db_conn.execute_query(insert_sql, b_row)
                        if err:
                            self.finished.emit(False, f"Error insertando en fila {idx}: {err}", inserted)
                            return
                        inserted += 1
                    batch = []
                    self.progress.emit(inserted, total)

            # Insertar remanente
            for b_row in batch:
                _, _, _, _, err = self.db_conn.execute_query(insert_sql, b_row)
                if err:
                    self.finished.emit(False, f"Error insertando en fila {total}: {err}", inserted)
                    return
                inserted += 1

            self.progress.emit(inserted, total)
            self.finished.emit(True, f"Se importaron con éxito {inserted} filas en '{self.target_table}'.", inserted)
        except Exception as e:
            self.finished.emit(False, str(e), 0)


class DataImporterDialog(QDialog):
    """Diálogo interactivo para importar archivos CSV y JSON hacia la base de datos"""
    def __init__(self, db_conn, colores: dict, parent=None, default_table=""):
        super().__init__(parent)
        self.db_conn = db_conn
        self.colores = colores
        self.default_table = default_table
        self.parsed_columns: List[str] = []
        self.parsed_types: Dict[str, str] = {}
        self.parsed_rows: List[Dict[str, Any]] = []

        self.setWindowTitle("📥 Asistente de Importación de Datos (CSV / JSON)")
        self.setFixedSize(620, 560)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores.get('bg_principal', '#121218')};
                color: white;
            }}
            QLabel {{
                color: #CBD5E1;
                font-size: 11px;
            }}
            QLineEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }}
            QComboBox {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QRadioButton {{
                color: #F1F5F9;
                font-size: 11px;
            }}
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        lbl_title = QLabel("📥  Importar Archivo Externo a la Base de Datos")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        layout.addWidget(lbl_title)

        # 1. Selección de archivo
        file_box = QHBoxLayout()
        self.txt_file = QLineEdit()
        self.txt_file.setPlaceholderText("Selecciona un archivo .csv o .json...")
        self.txt_file.setReadOnly(True)
        file_box.addWidget(self.txt_file)

        btn_browse = QPushButton("Examinar...")
        btn_browse.setFixedHeight(28)
        btn_browse.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                border-radius: 4px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        btn_browse.clicked.connect(self._examinar_archivo)
        file_box.addWidget(btn_browse)
        layout.addLayout(file_box)

        # 2. Destino de los datos
        grp_dest = QFrame()
        grp_dest.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')}; border-radius: 6px; padding: 6px;")
        dest_lay = QVBoxLayout(grp_dest)
        dest_lay.setSpacing(6)

        self.rb_new = QRadioButton("Crear una nueva tabla:")
        self.rb_new.setChecked(True)
        dest_lay.addWidget(self.rb_new)

        self.txt_new_table = QLineEdit()
        self.txt_new_table.setPlaceholderText("Nombre de la nueva tabla...")
        dest_lay.addWidget(self.txt_new_table)

        self.rb_existing = QRadioButton("Insertar en tabla existente:")
        dest_lay.addWidget(self.rb_existing)

        self.cb_existing_table = QComboBox()
        if self.db_conn and self.db_conn.is_connected:
            tables = self.db_conn.get_tables() if hasattr(self.db_conn, "get_tables") else []
            for t in tables:
                if t.get("type") == "table":
                    self.cb_existing_table.addItem(t["name"])
        if self.default_table:
            self.cb_existing_table.setCurrentText(self.default_table)
            self.rb_existing.setChecked(True)
        dest_lay.addWidget(self.cb_existing_table)

        self.rb_new.toggled.connect(self._on_dest_mode_changed)
        layout.addWidget(grp_dest)

        # 3. Previsualización de los primeros registros
        lbl_prev = QLabel("Previsualización de datos detectados (Primeras filas):")
        lbl_prev.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 10px;")
        layout.addWidget(lbl_prev)

        self.table_preview = QTableWidget()
        self.table_preview.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                alternate-background-color: #171724;
                color: #F1F5F9;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                font-size: 10px;
            }}
            QHeaderView::section {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #CBD5E1;
                padding: 4px 6px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                font-weight: bold;
                font-size: 10px;
            }}
        """)
        self.table_preview.setAlternatingRowColors(True)
        self.table_preview.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_preview)

        # 4. Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {self.colores.get('acento', '#6366F1')};
                border-radius: 6px;
            }}
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        # Botones inferiores
        bot_bar = QHBoxLayout()
        bot_bar.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFixedHeight(30)
        btn_cancel.setStyleSheet("background: transparent; color: #AAB0B8; border: none; padding: 0 10px;")
        btn_cancel.clicked.connect(self.reject)
        bot_bar.addWidget(btn_cancel)

        self.btn_import = QPushButton("▶ Iniciar Importación")
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.setFixedHeight(30)
        self.btn_import.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 11px;
                border: none;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        self.btn_import.clicked.connect(self._iniciar_importacion)
        bot_bar.addWidget(self.btn_import)

        layout.addLayout(bot_bar)
        self._on_dest_mode_changed()

    def _on_dest_mode_changed(self):
        is_new = self.rb_new.isChecked()
        self.txt_new_table.setEnabled(is_new)
        self.cb_existing_table.setEnabled(not is_new)

    def _examinar_archivo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo de Datos", "",
            "Archivos de Datos (*.csv *.json);;Archivos CSV (*.csv);;Archivos JSON (*.json)"
        )
        if not path:
            return

        self.txt_file.setText(path)
        base_name = Path(path).stem.replace("-", "_").replace(" ", "_").lower()
        self.txt_new_table.setText(base_name)
        self._analizar_archivo(path)

    def _analizar_archivo(self, path: str):
        try:
            self.parsed_rows = []
            self.parsed_columns = []
            self.parsed_types = {}

            ext = Path(path).suffix.lower()
            if ext == ".csv":
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    # Sniffer para delimitador
                    sample = f.read(2048)
                    f.seek(0)
                    dialect = csv.excel
                    try:
                        dialect = csv.Sniffer().sniff(sample)
                    except Exception:
                        pass
                    reader = csv.DictReader(f, dialect=dialect)
                    self.parsed_columns = [c.strip() for c in (reader.fieldnames or []) if c]
                    for idx, row in enumerate(reader):
                        self.parsed_rows.append(row)
                        if idx >= 20000:  # Límite de seguridad
                            break
            elif ext == ".json":
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.parsed_rows = data
                    elif isinstance(data, dict):
                        # Si es un dict con clave 'data' o 'rows'
                        for k in ("data", "rows", "items", "results"):
                            if k in data and isinstance(data[k], list):
                                self.parsed_rows = data[k]
                                break
                        if not self.parsed_rows:
                            self.parsed_rows = [data]

                    if self.parsed_rows and isinstance(self.parsed_rows[0], dict):
                        self.parsed_columns = list(self.parsed_rows[0].keys())

            if not self.parsed_columns or not self.parsed_rows:
                self.lbl_status.setText("⚠️ No se pudieron detectar registros válidos en el archivo.")
                return

            # Inferir tipos de columnas
            for c in self.parsed_columns:
                is_int = True
                is_real = True
                for r in self.parsed_rows[:30]:
                    val = r.get(c)
                    if val is not None and str(val).strip() != "":
                        val_str = str(val).strip()
                        if not val_str.isdigit() and not (val_str.startswith("-") and val_str[1:].isdigit()):
                            is_int = False
                        try:
                            float(val_str)
                        except ValueError:
                            is_real = False
                if is_int:
                    self.parsed_types[c] = "INTEGER"
                elif is_real:
                    self.parsed_types[c] = "REAL"
                else:
                    self.parsed_types[c] = "TEXT"

            # Llenar previsualización
            preview_rows = self.parsed_rows[:10]
            self.table_preview.clear()
            self.table_preview.setColumnCount(len(self.parsed_columns))
            self.table_preview.setRowCount(len(preview_rows))
            headers = [f"{c} ({self.parsed_types.get(c, 'TEXT')})" for c in self.parsed_columns]
            self.table_preview.setHorizontalHeaderLabels(headers)

            for r_idx, row in enumerate(preview_rows):
                for c_idx, col in enumerate(self.parsed_columns):
                    val = row.get(col, "")
                    item = QTableWidgetItem(str(val) if val is not None else "")
                    self.table_preview.setItem(r_idx, c_idx, item)

            self.lbl_status.setText(f"✅ {len(self.parsed_rows)} registros detectados ({len(self.parsed_columns)} columnas).")
            self.lbl_status.setStyleSheet("color: #34D399; font-size: 11px;")
        except Exception as e:
            self.lbl_status.setText(f"❌ Error leyendo archivo: {e}")
            self.lbl_status.setStyleSheet("color: #F87171; font-size: 11px;")

    def _iniciar_importacion(self):
        if not self.parsed_rows or not self.parsed_columns:
            QMessageBox.warning(self, "Importar", "Primero selecciona un archivo con datos válidos.")
            return

        is_new = self.rb_new.isChecked()
        target_table = self.txt_new_table.text().strip() if is_new else self.cb_existing_table.currentText().strip()

        if not target_table:
            QMessageBox.warning(self, "Importar", "Por favor especifica el nombre de la tabla de destino.")
            return

        self.btn_import.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setRange(0, len(self.parsed_rows))
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Importando registros...")
        self.lbl_status.setStyleSheet("color: #60A5FA; font-size: 11px;")

        self.thread = ImportWorkerThread(
            db_conn=self.db_conn,
            target_table=target_table,
            create_table=is_new,
            columns=self.parsed_columns,
            col_types=self.parsed_types,
            rows_data=self.parsed_rows
        )
        self.thread.progress.connect(self._on_progress)
        self.thread.finished.connect(self._on_finished)
        self.thread.start()

    def _on_progress(self, current: int, total: int):
        self.progress_bar.setValue(current)
        self.lbl_status.setText(f"Importando {current} de {total} filas...")

    def _on_finished(self, success: bool, msg: str, count: int):
        self.btn_import.setEnabled(True)
        if success:
            QMessageBox.information(self, "Importación Exitosa", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Error de Importación", msg)
            self.lbl_status.setText(f"❌ Error: {msg}")
            self.lbl_status.setStyleSheet("color: #F87171; font-size: 11px;")
