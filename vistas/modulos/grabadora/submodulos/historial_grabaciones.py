import os
import platform
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QInputDialog, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class HistorialGrabacionesSubmodule(QWidget):
    """Submódulo 4: Historial & Gestor de Biblioteca de Grabaciones (Audio, Video y Fotos)"""
    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.filtro_categoria = "todos"
        self.cat_buttons = {}

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#1E1E1E')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        bg_terc = self.colores.get('bg_terciario', '#3D3D3D')
        acento = self.colores.get('acento', '#4A86E8')
        error = self.colores.get('error', '#E53935')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("📁 HISTORIAL & BIBLIOTECA DE GRABACIONES")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {acento}; background: transparent;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        btn_open_folder = QPushButton("📂 Abrir Carpeta en Explorador")
        btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_folder.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_open_folder.setStyleSheet(f"background: {acento}; color: white; padding: 6px 14px; border-radius: 6px; border: none;")
        btn_open_folder.clicked.connect(self._abrir_carpeta_explorador)
        hdr.addWidget(btn_open_folder)

        layout.addLayout(hdr)

        # Barra de Búsqueda y Filtros
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self.inp_buscar = QLineEdit()
        self.inp_buscar.setPlaceholderText("🔍 Buscar grabación por nombre...")
        self.inp_buscar.setFont(QFont(self.font_family, 9))
        self.inp_buscar.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 6px 12px; color: white;")
        self.inp_buscar.textChanged.connect(self.filtrar_elementos)
        filter_bar.addWidget(self.inp_buscar, 1)

        for cat_key, cat_name in [("todos", "Todos"), ("audio", "🎙️ Audios"), ("video", "🎬 Videos"), ("fotos", "📷 Fotos")]:
            btn_cat = QPushButton(cat_name)
            btn_cat.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cat.setFont(QFont(self.font_family, 8, QFont.Weight.Bold if cat_key == "todos" else QFont.Weight.Medium))
            self._estilar_btn_filtro(btn_cat, cat_key == "todos")
            btn_cat.clicked.connect(lambda ch, k=cat_key: self._set_filtro_cat(k))
            filter_bar.addWidget(btn_cat)
            self.cat_buttons[cat_key] = btn_cat

        layout.addLayout(filter_bar)

        # Lista de Archivos
        self.list_audio = QListWidget()
        self.list_audio.setFont(QFont(self.font_family, 9))
        self.list_audio.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_sec};
                color: white; border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
            }}
            QListWidget::item {{
                padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.05);
            }}
            QListWidget::item:selected {{
                background-color: {acento}; color: white;
            }}
        """)
        self.list_audio.itemDoubleClicked.connect(self._reproducir_seleccionado)
        layout.addWidget(self.list_audio, 1)

        # Botones de Acción
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        btn_play = QPushButton("▶ Reproducir / Ver")
        btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_play.setStyleSheet(f"background: {bg_terc}; color: white; padding: 8px 16px; border-radius: 6px; border: none;")
        btn_play.clicked.connect(self._reproducir_seleccionado)
        btn_box.addWidget(btn_play)

        btn_rename = QPushButton("✏️ Renombrar")
        btn_rename.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rename.setStyleSheet(f"background: {bg_terc}; color: white; padding: 8px 16px; border-radius: 6px; border: none;")
        btn_rename.clicked.connect(self.callbacks.get("renombrar_audio", lambda: None))
        btn_box.addWidget(btn_rename)

        btn_delete = QPushButton("🗑️ Eliminar Archivo")
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setStyleSheet(f"background: {error}; color: white; padding: 8px 16px; border-radius: 6px; border: none;")
        btn_delete.clicked.connect(self.callbacks.get("eliminar_audio", lambda: None))
        btn_box.addWidget(btn_delete)

        btn_box.addStretch()

        self.lbl_stats = QLabel("Total: 0 grabaciones")
        self.lbl_stats.setFont(QFont(self.font_family, 8))
        self.lbl_stats.setStyleSheet("color: rgba(255,255,255,0.6);")
        btn_box.addWidget(self.lbl_stats)

        btn_refresh = QPushButton("🔄 Actualizar Lista")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(f"background: {bg_terc}; color: white; padding: 8px 16px; border-radius: 6px; border: none;")
        btn_refresh.clicked.connect(self._on_refresh_clicked)
        btn_box.addWidget(btn_refresh)

        layout.addLayout(btn_box)

    def _estilar_btn_filtro(self, btn, activo):
        acento = self.colores.get('acento', '#4A86E8')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        if activo:
            btn.setStyleSheet(f"background-color: {acento}; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: bold;")
        else:
            btn.setStyleSheet(f"background-color: {bg_sec}; color: rgba(255,255,255,0.7); border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 6px 12px;")

    def _set_filtro_cat(self, cat_key):
        self.filtro_categoria = cat_key
        for k, btn in self.cat_buttons.items():
            self._estilar_btn_filtro(btn, k == cat_key)
        self.filtrar_elementos()

    def filtrar_elementos(self):
        query = self.inp_buscar.text().strip().lower()
        cat = getattr(self, "filtro_categoria", "todos")
        total = self.list_audio.count()
        visibles = 0
        for i in range(total):
            item = self.list_audio.item(i)
            txt = item.text().lower()
            coincide_txt = (not query) or (query in txt)
            coincide_cat = True
            if cat == "audio":
                coincide_cat = "🎙️" in item.text()
            elif cat == "video":
                coincide_cat = "🎬" in item.text()
            elif cat == "fotos":
                coincide_cat = "📷" in item.text()
            show = coincide_txt and coincide_cat
            item.setHidden(not show)
            if show:
                visibles += 1
        self.lbl_stats.setText(f"Mostrando {visibles} de {total} grabaciones")

    def _on_refresh_clicked(self):
        if "cargar_audios" in self.callbacks:
            self.callbacks["cargar_audios"]()
        self.filtrar_elementos()

    def _abrir_carpeta_explorador(self):
        folder = str(self.manager.ruta_grabaciones)
        if os.name == 'nt':
            os.startfile(folder)
        else:
            subprocess.Popen(["xdg-open", folder])

    def _reproducir_seleccionado(self):
        item = self.list_audio.currentItem()
        if item:
            nombre = item.text().replace("🎙️ ", "").replace("🎬 ", "").replace("📷 ", "").strip()
            path = os.path.join(self.manager.ruta_grabaciones, nombre)
            if os.path.exists(path):
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    subprocess.Popen(["xdg-open", path])

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#1E1E1E')
        bg_sec = colores.get('bg_secundario', '#2D2D2D')
        acento = colores.get('acento', '#4A86E8')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        self.inp_buscar.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 6px 12px; color: white;")
        self.list_audio.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_sec};
                color: white; border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
            }}
            QListWidget::item {{
                padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.05);
            }}
            QListWidget::item:selected {{
                background-color: {acento}; color: white;
            }}
        """)
        for k, btn in self.cat_buttons.items():
            self._estilar_btn_filtro(btn, k == self.filtro_categoria)

