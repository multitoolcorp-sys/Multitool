import os
import platform
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QFrame, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class HistorialChatsSubmodule(QWidget):
    """Submódulo 4: Explorador & Gestor de Conversaciones Guardadas (Historial)"""
    def __init__(self, parent, context, colores, callbacks, manager):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.manager = manager
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#1E1E1E')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        bg_terc = self.colores.get('bg_terciario', '#3D3D3D')
        acento = self.colores.get('acento', '#6366F1')
        error = self.colores.get('error', '#F44336')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("📜 HISTORIAL Y REGISTRO DE CONVERSACIONES")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {acento}; background: transparent;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        btn_open_folder = QPushButton("📂 Abrir Carpeta de Historiales")
        btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_folder.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_open_folder.setStyleSheet(f"background: {acento}; color: white; padding: 6px 14px; border-radius: 6px; border: none;")
        btn_open_folder.clicked.connect(self._abrir_carpeta_historial)
        hdr.addWidget(btn_open_folder)

        layout.addLayout(hdr)

        # Lista de Sesiones Guardadas
        self.list_saved = QListWidget()
        self.list_saved.setFont(QFont(self.font_family, 9))
        self.list_saved.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_sec};
                color: white; border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
            }}
            QListWidget::item {{
                padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.05);
            }}
            QListWidget::item:selected {{
                background-color: #00A884; color: white;
            }}
        """)
        self.list_saved.itemDoubleClicked.connect(self.callbacks.get("cargar_chat", lambda: None))
        self.list_saved.itemSelectionChanged.connect(self._actualizar_botones_seleccion)
        layout.addWidget(self.list_saved, 1)

        # Banner de estado / sugerencia (sin selección)
        self.lbl_hint = QLabel("💡 Selecciona una conversación de la lista para habilitar las acciones (o presiona Esc para deseleccionar).")
        self.lbl_hint.setFont(QFont(self.font_family, 9))
        self.lbl_hint.setStyleSheet("color: rgba(255, 255, 255, 0.4); padding: 2px 4px;")
        layout.addWidget(self.lbl_hint)

        # Botones de Acción (Deshabilitados sin selección para evitar clics innecesarios)
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_load = QPushButton("📜 Cargar Chat Seleccionado")
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.setEnabled(False)
        self.btn_load.setStyleSheet(f"""
            QPushButton {{
                background: #00A884; color: white; padding: 8px 16px; border-radius: 6px; border: none; font-weight: bold;
            }}
            QPushButton:hover {{ background: #06CF9C; }}
            QPushButton:disabled {{
                background: rgba(255, 255, 255, 0.05); color: rgba(255, 255, 255, 0.25);
            }}
        """)
        self.btn_load.clicked.connect(self.callbacks.get("cargar_chat", lambda: None))
        btn_box.addWidget(self.btn_load)

        self.btn_delete = QPushButton("🗑️ Eliminar Chat")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background: {error}; color: white; padding: 8px 16px; border-radius: 6px; border: none; font-weight: bold;
            }}
            QPushButton:hover {{ background: #EF4444; }}
            QPushButton:disabled {{
                background: rgba(255, 255, 255, 0.05); color: rgba(255, 255, 255, 0.25);
            }}
        """)
        self.btn_delete.clicked.connect(self.callbacks.get("eliminar_chat", lambda: None))
        btn_box.addWidget(self.btn_delete)

        btn_box.addStretch()

        self.btn_refresh = QPushButton("🔄 Actualizar Lista")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: {bg_terc}; color: white; padding: 8px 16px; border-radius: 6px; border: none;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.15); }}
        """)
        self.btn_refresh.clicked.connect(self.callbacks.get("actualizar_lista_historial", lambda: None))
        btn_box.addWidget(self.btn_refresh)

        layout.addLayout(btn_box)

    def _actualizar_botones_seleccion(self):
        item = self.list_saved.currentItem()
        has_sel = item is not None and item.isSelected()
        self.btn_load.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)
        if has_sel:
            self.lbl_hint.setText(f"✅ Conversación seleccionada: <b>{item.text()}</b>. Lista para cargar o eliminar.")
            self.lbl_hint.setStyleSheet("color: #00A884; padding: 2px 4px;")
        else:
            self.lbl_hint.setText("💡 Selecciona una conversación de la lista para habilitar las acciones.")
            self.lbl_hint.setStyleSheet("color: rgba(255, 255, 255, 0.4); padding: 2px 4px;")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.list_saved.clearSelection()
            self._actualizar_botones_seleccion()
            event.accept()
            return
        super().keyPressEvent(event)

    def actualizar_tema(self, colores: dict = None):
        if colores:
            self.colores = colores

    def cleanup(self):
        pass

    def _abrir_carpeta_historial(self):
        folder = str(self.manager.ruta_chat) if hasattr(self.manager, 'ruta_chat') else str(Path.home() / "chats")
        if os.name == 'nt':
            os.startfile(folder)
        else:
            subprocess.Popen(["xdg-open", folder])
