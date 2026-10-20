"""
schema_designer.py - Asistente visual de creación de tablas y visor de DDL estilo DBeaver
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTextEdit, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont


class SchemaDesignerWidget(QWidget):
    """Asistente para diseñar y crear tablas visualmente + Visor de DDL"""
    create_table_requested = pyqtSignal(str)  # Emite el script SQL CREATE TABLE

    def __init__(self, colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header con nombre de tabla
        top_bar = QHBoxLayout()
        lbl_tbl = QLabel("Nombre de la nueva tabla:")
        lbl_tbl.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        top_bar.addWidget(lbl_tbl)

        self.txt_table_name = QLineEdit()
        self.txt_table_name.setPlaceholderText("ej: usuarios, productos, ventas")
        self.txt_table_name.setFixedHeight(30)
        self.txt_table_name.setStyleSheet(f"""
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
        top_bar.addWidget(self.txt_table_name)

        self.btn_add_col = QPushButton("➕ Añadir Columna")
        self.btn_add_col.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_col.setFixedHeight(30)
        self.btn_add_col.setStyleSheet(f"""
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
        self.btn_add_col.clicked.connect(lambda: self._add_column_row())
        top_bar.addWidget(self.btn_add_col)

        self.btn_del_col = QPushButton("➖ Eliminar Columna")
        self.btn_del_col.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del_col.setFixedHeight(30)
        self.btn_del_col.setStyleSheet(f"""
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
                background-color: rgba(248, 113, 113, 0.15);
                color: #F87171;
                border-color: rgba(248, 113, 113, 0.3);
            }}
            QPushButton:pressed {{
                background-color: rgba(248, 113, 113, 0.3);
                color: #FFFFFF;
            }}
            QPushButton:focus {{
                outline: none;
            }}
        """)
        self.btn_del_col.clicked.connect(self._del_column_row)
        top_bar.addWidget(self.btn_del_col)

        layout.addLayout(top_bar)

        # Tabla de diseño de columnas
        self.table_cols = QTableWidget()
        self.table_cols.setColumnCount(5)
        self.table_cols.setHorizontalHeaderLabels([
            "Nombre Columna", "Tipo de Dato", "Clave Primaria (PK)", "No Nulo (NN)", "Autoincremental"
        ])
        self.table_cols.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_cols.setStyleSheet(f"""
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
        self.table_cols.setAlternatingRowColors(True)
        self.table_cols.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_cols)

        # Fila por defecto: id INTEGER PRIMARY KEY AUTOINCREMENT
        self._add_column_row("id", "INTEGER", is_pk=True, is_nn=True, is_auto=True)
        self._add_column_row("nombre", "TEXT", is_pk=False, is_nn=True, is_auto=False)
        self._add_column_row("creado_en", "TIMESTAMP", is_pk=False, is_nn=False, is_auto=False)

        # Botón para ejecutar la creación
        bot_bar = QHBoxLayout()
        bot_bar.addStretch()

        self.btn_create = QPushButton("🚀 Crear Tabla en Base de Datos")
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create.setFixedHeight(34)
        self.btn_create.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                font-size: 12px;
                border-radius: 6px;
                padding: 0 18px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        self.btn_create.clicked.connect(self._build_and_emit_create)
        bot_bar.addWidget(self.btn_create)

        layout.addLayout(bot_bar)

        # Separador y Visor DDL
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; max-height: 1px; border: none;")
        layout.addWidget(line)

        lbl_ddl = QLabel("📜 Vista Previa DDL de la Tabla Seleccionada:")
        lbl_ddl.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        layout.addWidget(lbl_ddl)

        self.txt_ddl = QTextEdit()
        self.txt_ddl.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.txt_ddl.setFont(font)
        self.txt_ddl.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #A5B4FC;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 8px;
                max-height: 120px;
            }}
        """)
        layout.addWidget(self.txt_ddl)

    def _add_column_row(self, *args, name="", col_type="TEXT", is_pk=False, is_nn=False, is_auto=False):
        if not isinstance(name, str):
            name = ""
        row = self.table_cols.rowCount()
        self.table_cols.insertRow(row)

        txt_name = QLineEdit(name)
        txt_name.setStyleSheet("background: transparent; color: white; border: none;")
        self.table_cols.setCellWidget(row, 0, txt_name)

        cb_type = QComboBox()
        cb_type.addItems(["INTEGER", "TEXT", "REAL", "BLOB", "NUMERIC", "TIMESTAMP", "BOOLEAN"])
        cb_type.setCurrentText(col_type)
        cb_type.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border-radius: 4px; padding: 2px 4px;")
        self.table_cols.setCellWidget(row, 1, cb_type)

        chk_pk = QCheckBox()
        chk_pk.setChecked(is_pk)
        chk_pk.setStyleSheet("margin-left: 20px;")
        self.table_cols.setCellWidget(row, 2, chk_pk)

        chk_nn = QCheckBox()
        chk_nn.setChecked(is_nn)
        chk_nn.setStyleSheet("margin-left: 20px;")
        self.table_cols.setCellWidget(row, 3, chk_nn)

        chk_auto = QCheckBox()
        chk_auto.setChecked(is_auto)
        chk_auto.setStyleSheet("margin-left: 20px;")
        self.table_cols.setCellWidget(row, 4, chk_auto)

    def _del_column_row(self):
        curr = self.table_cols.currentRow()
        if curr >= 0:
            self.table_cols.removeRow(curr)
        elif self.table_cols.rowCount() > 0:
            self.table_cols.removeRow(self.table_cols.rowCount() - 1)

    def _build_and_emit_create(self):
        tbl_name = self.txt_table_name.text().strip()
        if not tbl_name:
            QMessageBox.warning(self, "Diseñador", "Por favor ingresa un nombre para la tabla.")
            return

        rows = self.table_cols.rowCount()
        if rows == 0:
            QMessageBox.warning(self, "Diseñador", "Debes definir al menos una columna.")
            return

        cols_defs = []
        for r in range(rows):
            name_widget = self.table_cols.cellWidget(r, 0)
            type_widget = self.table_cols.cellWidget(r, 1)
            pk_widget = self.table_cols.cellWidget(r, 2)
            nn_widget = self.table_cols.cellWidget(r, 3)
            auto_widget = self.table_cols.cellWidget(r, 4)

            col_name = name_widget.text().strip() if name_widget else ""
            if not col_name:
                continue

            col_type = type_widget.currentText() if type_widget else "TEXT"
            is_pk = pk_widget.isChecked() if pk_widget else False
            is_nn = nn_widget.isChecked() if nn_widget else False
            is_auto = auto_widget.isChecked() if auto_widget else False

            col_def = f'"{col_name}" {col_type}'
            if is_pk:
                col_def += " PRIMARY KEY"
                if is_auto and col_type == "INTEGER":
                    col_def += " AUTOINCREMENT"
            if is_nn and not is_pk:
                col_def += " NOT NULL"

            cols_defs.append(col_def)

        if not cols_defs:
            QMessageBox.warning(self, "Diseñador", "Las columnas deben tener nombres válidos.")
            return

        sql = f'CREATE TABLE IF NOT EXISTS "{tbl_name}" (\n    ' + ",\n    ".join(cols_defs) + "\n);"
        self.create_table_requested.emit(sql)

    def show_ddl(self, ddl: str):
        self.txt_ddl.setPlainText(ddl if ddl else "-- No hay DDL disponible para el objeto seleccionado.")
