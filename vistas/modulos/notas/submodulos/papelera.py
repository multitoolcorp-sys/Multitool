import os
import json
import shutil
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class TabPapelera(QWidget):
    """Submódulo de Papelera de Reciclaje y Restauración de Notas"""
    def __init__(self, parent=None, context=None, colores=None, callback_restaurar=None):
        super().__init__(parent)
        self.context = context
        
        if isinstance(context, dict):
            self.colores = context
            self.context = colores
        elif isinstance(colores, dict):
            self.colores = colores
        else:
            self.colores = {}

        if not self.colores and self.context and hasattr(self.context, "app") and hasattr(self.context.app, "COLORES"):
            self.colores = self.context.app.COLORES

        self.callback_restaurar = callback_restaurar
        self.ruta_usuario = Path(getattr(self.context, "ruta_usuario", ".")) if self.context else Path(".")
        self.dir_papelera = self.ruta_usuario / "notas" / ".papelera"
        self.dir_papelera.mkdir(parents=True, exist_ok=True)
        self.font_family = "Segoe UI"

        bg_p = self.colores.get('bg_principal', '#121218') if isinstance(self.colores, dict) else '#121218'
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218') if isinstance(self.colores, dict) else '#121218'

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 8, 10, 8)
        main_lay.setSpacing(10)

        # Header
        lbl_head = QLabel("🗑️ PAPELERA DE RECICLAJE DE NOTAS")
        lbl_head.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_head.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1') if isinstance(self.colores, dict) else '#6366F1'}; margin-bottom: 2px;")
        main_lay.addWidget(lbl_head)

        lbl_sub = QLabel("Las notas eliminadas se conservan aquí de forma segura. Puedes restaurarlas en cualquier momento.")
        lbl_sub.setFont(QFont(self.font_family, 9))
        lbl_sub.setStyleSheet("color: #AAB0B8;")
        main_lay.addWidget(lbl_sub)

        # Acciones globales
        actions_lay = QHBoxLayout()
        actions_lay.setSpacing(10)

        btn_restore = QPushButton("🔄 Restaurar Nota Seleccionada")
        btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        acento = self.colores.get('acento', '#6366F1') if isinstance(self.colores, dict) else '#6366F1'
        btn_restore.setStyleSheet(f"background: {acento}; color: white; font-weight: bold; border-radius: 6px; padding: 7px 14px; border: none;")
        btn_restore.clicked.connect(self.restaurar_nota_seleccionada)

        btn_empty = QPushButton("🗑️ Vaciar Papelera por Completo")
        btn_empty.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_empty.setStyleSheet("background: #EF4444; color: white; font-weight: bold; border-radius: 6px; padding: 7px 14px; border: none;")
        btn_empty.clicked.connect(self.vaciar_papelera)

        actions_lay.addWidget(btn_restore)
        actions_lay.addWidget(btn_empty)
        actions_lay.addStretch()
        main_lay.addLayout(actions_lay)

        # Tabla de notas eliminadas
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Nombre de la Nota", "Fecha de Eliminación", "Ruta de Archivo"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        bg_ter = self.colores.get('bg_terciario', '#2D2D3D') if isinstance(self.colores, dict) else '#2D2D3D'
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {bg_ter};
                color: white;
                gridline-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
            }}
            QHeaderView::section {{
                background-color: #121218;
                color: {acento};
                font-weight: bold;
                padding: 5px;
                border: none;
            }}
        """)
        main_lay.addWidget(self.table, 1)

        self.cargar_papelera()

    def cargar_papelera(self):
        self.table.setRowCount(0)
        if not self.dir_papelera.exists():
            return

        files = sorted(list(self.dir_papelera.glob("*")), key=os.path.getmtime, reverse=True)
        self.table.setRowCount(len(files))

        for idx, f in enumerate(files):
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M:%S")
            item_name = QTableWidgetItem(f.stem)
            item_date = QTableWidgetItem(mtime)
            item_path = QTableWidgetItem(f.name)

            self.table.setItem(idx, 0, item_name)
            self.table.setItem(idx, 1, item_date)
            self.table.setItem(idx, 2, item_path)

    def restaurar_nota_seleccionada(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selección requerida", "Por favor selecciona una nota de la tabla para restaurarla.")
            return

        file_name_item = self.table.item(row, 2)
        if not file_name_item:
            return

        file_name = file_name_item.text()
        src_path = self.dir_papelera / file_name
        dst_path = self.ruta_usuario / "notas" / file_name

        if src_path.exists():
            try:
                shutil.move(src_path, dst_path)
                QMessageBox.information(self, "Nota Restaurada", f"¡La nota '{src_path.stem}' ha sido restaurada con éxito!")
                self.cargar_papelera()
                if self.callback_restaurar:
                    self.callback_restaurar()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo restaurar la nota:\n{e}")

    def vaciar_papelera(self):
        if not self.dir_papelera.exists() or not list(self.dir_papelera.glob("*")):
            QMessageBox.information(self, "Papelera vacía", "La papelera ya está completamente vacía.")
            return

        reply = QMessageBox.question(
            self, "Confirmar Vaciado",
            "¿Estás seguro de que deseas eliminar permanentemente todas las notas de la papelera?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for f in self.dir_papelera.glob("*"):
                    if f.is_file():
                        f.unlink()
                QMessageBox.information(self, "Papelera Vaciada", "¡Se han eliminado definitivamente todas las notas de la papelera!")
                self.cargar_papelera()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al vaciar papelera:\n{e}")
