"""
snapshot_dialog.py - Diálogo de Previsualización y Restauración de Snapshots/Versiones Anteriores de Notas.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, 
    QListWidget, QTextEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt


class SnapshotViewerDialog(QDialog):
    """Diálogo modal para inspeccionar y restaurar versiones guardadas de una nota"""
    def __init__(self, parent, nota_actual, storage, colores, editor, on_restored=None):
        super().__init__(parent)
        self.nota_actual = nota_actual
        self.storage = storage
        self.colores = colores or {}
        self.editor = editor
        self.on_restored = on_restored

        self.setWindowTitle(f"🕒 Historial de Versiones - {self.nota_actual}")
        self.resize(650, 440)
        self.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white;")
        
        self.init_ui()

    def init_ui(self):
        d_layout = QVBoxLayout(self)
        d_layout.setContentsMargins(16, 16, 16, 16)
        d_layout.setSpacing(12)
        
        lbl_info = QLabel("Selecciona una versión guardada para previsualizar su contenido o restaurarla:")
        lbl_info.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#A0A0A0')}; font-size: 11px;")
        d_layout.addWidget(lbl_info)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.list_snaps = QListWidget()
        bg_p = self.colores.get('bg_principal', '#121218')
        self.list_snaps.setStyleSheet(f"background: {bg_p}; color: white; border-radius: 6px; padding: 6px;")

        self.snaps = self.storage.listar_snapshots(self.nota_actual)
        for s in self.snaps:
            if isinstance(s, dict):
                raw = s.get("timestamp", s.get("file", ""))
                preview_text = s.get("preview", "")
            else:
                raw = str(s)
                preview_text = ""
            nombre_legible = str(raw).replace("snap_", "").replace(".json", "").replace(".txt", "").replace("_", " ")
            if preview_text:
                self.list_snaps.addItem(f"🕒 {nombre_legible}\n   ↳ {preview_text[:35]}...")
            else:
                self.list_snaps.addItem(f"🕒 {nombre_legible}")

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setStyleSheet(f"background: {bg_p}; color: {self.colores.get('fg_principal', '#FFFFFF')}; border-radius: 6px; padding: 10px;")

        split.addWidget(self.list_snaps)
        split.addWidget(self.preview)
        split.setSizes([200, 430])
        d_layout.addWidget(split, 1)

        self.list_snaps.currentRowChanged.connect(self._on_snap_selected)
        if self.snaps:
            self.list_snaps.setCurrentRow(0)

        row_actions = QHBoxLayout()
        btn_restaurar = QPushButton("⚡ Restaurar esta versión")
        btn_restaurar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restaurar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 18px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#4F46E5')};
            }}
        """)
        btn_restaurar.clicked.connect(self._restaurar)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cerrar.setStyleSheet("background: rgba(255,255,255,0.08); color: white; border-radius: 6px; padding: 8px 18px; border: none;")
        btn_cerrar.clicked.connect(self.reject)

        row_actions.addStretch()
        row_actions.addWidget(btn_restaurar)
        row_actions.addWidget(btn_cerrar)
        d_layout.addLayout(row_actions)

    def _on_snap_selected(self, row):
        if 0 <= row < len(self.snaps):
            html_snap = self.storage.restaurar_snapshot(self.nota_actual, self.snaps[row])
            self.preview.setHtml(html_snap or "<p><i>(Vacío)</i></p>")

    def _restaurar(self):
        row = self.list_snaps.currentRow()
        if 0 <= row < len(self.snaps):
            confirm = QMessageBox.question(
                self, "Confirmar Restauración",
                "¿Deseas reemplazar el contenido actual con esta versión anterior?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                html_restaurado = self.storage.restaurar_snapshot(self.nota_actual, self.snaps[row])
                if html_restaurado is not None and self.editor:
                    self.editor.setHtml(html_restaurado)
                    if callable(self.on_restored):
                        self.on_restored()
                    self.accept()
                    QMessageBox.information(self.parent(), "Restaurado", "¡Versión restaurada con éxito!")
