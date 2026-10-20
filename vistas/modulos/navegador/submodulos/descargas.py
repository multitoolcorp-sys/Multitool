"""
descargas.py - Submódulo visual de Gestión de Descargas Asíncronas e Instalación de Archivos
Diseño responsivo de dos columnas lado a lado (QSplitter) para evitar colisiones.
"""
import os
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QProgressBar, QFrame, QScrollArea, QListWidget, QListWidgetItem,
    QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..utils.download_manager import DownloadManager


class TabNavegadorDescargas(QWidget):
    """Submódulo de Descargas & Gestor HTTP asíncrono con panel de 2 columnas paralelas"""
    def __init__(self, parent, colores=None, callbacks=None, context=None):
        super().__init__(parent)
        self.context = context
        self.colores = colores or {}
        self.callbacks = callbacks or {}
        
        ruta_usuario = getattr(context, "ruta_usuario", ".") if context else "."
        self.mgr = DownloadManager(ruta_usuario)
        self.active_cards = {} # {download_id: {"frame": ..., "pbar": ..., "lbl": ...}}

        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#1E1E1E')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        acento = self.colores.get('acento', '#6366F1')
        
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(14, 14, 14, 14)
        main_lay.setSpacing(12)

        # Header y acciones rápidas
        header_bar = QHBoxLayout()
        lbl_t = QLabel("⚡ GESTOR DE DESCARGAS E INSTALADORES HTTP")
        lbl_t.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {acento};")
        header_bar.addWidget(lbl_t)
        header_bar.addStretch()

        btn_open_folder = QPushButton("📂 Abrir Carpeta")
        btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_folder.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_sec};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {acento};
            }}
        """)
        btn_open_folder.clicked.connect(self._abrir_directorio_descargas)
        header_bar.addWidget(btn_open_folder)

        btn_limpiar_hist = QPushButton("🧹 Limpiar Historial")
        btn_limpiar_hist.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_limpiar_hist.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_sec};
                color: #AAB0B8;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                color: #EF4444;
                border-color: #EF4444;
            }}
        """)
        btn_limpiar_hist.clicked.connect(self._limpiar_historial)
        header_bar.addWidget(btn_limpiar_hist)

        main_lay.addLayout(header_bar)

        # Barra de inicio de descarga
        box_dl = QFrame()
        box_dl.setStyleSheet(f"background: {bg_sec}; border-radius: 8px; padding: 6px 10px; border: 1px solid rgba(255, 255, 255, 0.06);")
        b_lay = QHBoxLayout(box_dl)
        b_lay.setContentsMargins(6, 2, 6, 2)
        b_lay.setSpacing(8)

        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("Pega aquí el enlace directo (URL HTTP/HTTPS)...")
        self.txt_url.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#3D3D3D')}; color: white; border-radius: 6px; padding: 7px 10px; border: none;")
        self.txt_url.returnPressed.connect(self._iniciar_descarga)
        b_lay.addWidget(self.txt_url, 1)

        btn_dl = QPushButton("⬇️ Descargar")
        btn_dl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dl.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 7px 16px; font-weight: bold; border: none;")
        btn_dl.clicked.connect(self._iniciar_descarga)
        b_lay.addWidget(btn_dl)

        main_lay.addWidget(box_dl)

        # SPLITTER PRINCIPAL: Dos Columnas Paralelas Lado a Lado (Evita colisiones)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: rgba(255, 255, 255, 0.08);
                width: 3px;
                margin: 0px 4px;
                border-radius: 1px;
            }}
            QSplitter::handle:hover {{
                background-color: {acento};
            }}
        """)

        # --- COLUMNA IZQUIERDA: DESCARGAS ACTIVAS (45%) ---
        col_izq = QFrame()
        col_izq.setStyleSheet(f"background-color: {bg_sec}; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05);")
        izq_lay = QVBoxLayout(col_izq)
        izq_lay.setContentsMargins(10, 10, 10, 10)
        izq_lay.setSpacing(8)

        lbl_act = QLabel("⏳ Descargas Activas en Tiempo Real")
        lbl_act.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_act.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')}; border: none;")
        izq_lay.addWidget(lbl_act)

        self.scroll_active = QScrollArea()
        self.scroll_active.setWidgetResizable(True)
        self.scroll_active.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.active_container = QWidget()
        self.active_layout = QVBoxLayout(self.active_container)
        self.active_layout.setContentsMargins(0, 0, 0, 0)
        self.active_layout.setSpacing(8)

        # Placeholder cuando no hay descargas activas
        self.lbl_empty_active = QLabel("No hay descargas en curso.\nPega una URL arriba para comenzar.")
        self.lbl_empty_active.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_active.setStyleSheet("color: #7E7E8F; font-size: 11px; padding: 40px 10px; border: none;")
        self.active_layout.addWidget(self.lbl_empty_active)
        self.active_layout.addStretch()

        self.scroll_active.setWidget(self.active_container)
        izq_lay.addWidget(self.scroll_active, 1)

        self.splitter.addWidget(col_izq)

        # --- COLUMNA DERECHA: HISTORIAL DE DESCARGAS (55%) ---
        col_der = QFrame()
        col_der.setStyleSheet(f"background-color: {bg_sec}; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05);")
        der_lay = QVBoxLayout(col_der)
        der_lay.setContentsMargins(10, 10, 10, 10)
        der_lay.setSpacing(8)

        lbl_hist = QLabel("📁 Archivos Descargados & Historial")
        lbl_hist.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_hist.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')}; border: none;")
        der_lay.addWidget(lbl_hist)

        # Buscador en historial
        self.txt_buscar_hist = QLineEdit()
        self.txt_buscar_hist.setPlaceholderText("🔍 Filtrar historial...")
        self.txt_buscar_hist.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#3D3D3D')}; color: white; border-radius: 6px; padding: 5px 10px; border: none;")
        self.txt_buscar_hist.textChanged.connect(self._refrescar_historial)
        der_lay.addWidget(self.txt_buscar_hist)

        self.list_historial = QListWidget()
        self.list_historial.setStyleSheet(f"""
            QListWidget {{
                background: {bg_p};
                border-radius: 6px;
                padding: 6px;
                border: none;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
                margin-bottom: 4px;
            }}
        """)
        der_lay.addWidget(self.list_historial, 1)

        self.splitter.addWidget(col_der)
        self.splitter.setSizes([400, 520])

        main_lay.addWidget(self.splitter, 1)

        self._refrescar_historial()

    def _iniciar_descarga(self):
        url = self.txt_url.text().strip()
        if not url:
            return

        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        dl_id = self.mgr.iniciar_descarga(
            url,
            progress_cb=self._on_progress,
            completed_cb=self._on_completed,
            error_cb=self._on_error
        )
        self._crear_tarjeta_activa(dl_id, url)
        self.txt_url.clear()

    def _crear_tarjeta_activa(self, dl_id, url):
        self.lbl_empty_active.setVisible(False)
        card = QFrame()
        card.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; border-radius: 8px; padding: 8px; border: 1px solid rgba(255, 255, 255, 0.08);")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        top_row = QHBoxLayout()
        nom_archivo = url.split("?")[0].rstrip("/").split("/")[-1] or "archivo_descarga"
        lbl_info = QLabel(f"⬇️ <b>{nom_archivo}</b>")
        lbl_info.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_info.setStyleSheet("color: white; border: none;")
        top_row.addWidget(lbl_info, 1)

        btn_cancelar = QPushButton("✕")
        btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancelar.setFixedSize(20, 20)
        btn_cancelar.setStyleSheet("background: transparent; color: #EF4444; border: none; font-weight: bold;")
        btn_cancelar.clicked.connect(lambda _, d=dl_id: self._cancelar_descarga(d))
        top_row.addWidget(btn_cancelar)
        lay.addLayout(top_row)

        pbar = QProgressBar()
        acento = self.colores.get('acento', '#6366F1')
        pbar.setStyleSheet(f"""
            QProgressBar {{
                background: {self.colores.get('bg_principal', '#121218')};
                border-radius: 4px;
                text-align: center;
                height: 12px;
                font-size: 9px;
            }}
            QProgressBar::chunk {{
                background: {acento};
                border-radius: 4px;
            }}
        """)
        pbar.setValue(0)
        lay.addWidget(pbar)

        lbl_speed = QLabel("Iniciando descarga...")
        lbl_speed.setStyleSheet("color: #AAB0B8; font-size: 10px; border: none;")
        lay.addWidget(lbl_speed)

        # Insertar al inicio de la lista activa
        self.active_layout.insertWidget(0, card)
        self.active_cards[dl_id] = {"frame": card, "pbar": pbar, "lbl": lbl_speed}

    def _cancelar_descarga(self, dl_id):
        if dl_id in self.active_cards:
            self.mgr.cancelar_descarga(dl_id)
            self.active_cards[dl_id]["frame"].deleteLater()
            del self.active_cards[dl_id]
        if not self.active_cards:
            self.lbl_empty_active.setVisible(True)

    def _on_progress(self, dl_id, bytes_recv, total_bytes, speed_bytes_sec):
        if dl_id in self.active_cards:
            card = self.active_cards[dl_id]
            if total_bytes > 0:
                pct = int((bytes_recv / total_bytes) * 100)
                card["pbar"].setValue(pct)

            speed_kb = speed_bytes_sec / 1024.0
            if speed_kb > 1024:
                speed_str = f"{speed_kb / 1024.0:.1f} MB/s"
            else:
                speed_str = f"{speed_kb:.1f} KB/s"

            mb_recv = bytes_recv / (1024 * 1024)
            card["lbl"].setText(f"{mb_recv:.1f} MB transferidos • Velocidad: {speed_str}")

    def _on_completed(self, dl_id, file_path):
        if dl_id in self.active_cards:
            self.active_cards[dl_id]["frame"].deleteLater()
            del self.active_cards[dl_id]
        if not self.active_cards:
            self.lbl_empty_active.setVisible(True)
        self._refrescar_historial()

    def _on_error(self, dl_id, error_msg):
        if dl_id in self.active_cards:
            self.active_cards[dl_id]["frame"].deleteLater()
            del self.active_cards[dl_id]
        if not self.active_cards:
            self.lbl_empty_active.setVisible(True)
        QMessageBox.warning(self, "Error de Descarga", f"No se pudo completar la descarga:\n{error_msg}")

    def _refrescar_historial(self):
        self.list_historial.clear()
        filtro = self.txt_buscar_hist.text().strip().lower() if hasattr(self, "txt_buscar_hist") else ""

        items = self.mgr.historial_descargas
        if filtro:
            items = [it for it in items if filtro in it.get("nombre", "").lower() or filtro in it.get("path", "").lower()]

        if not items:
            empty_item = QListWidgetItem("Sin descargas en el historial")
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setForeground(Qt.GlobalColor.gray)
            self.list_historial.addItem(empty_item)
            return

        for item in items:
            f_path = item.get("path", "")
            f_nombre = item.get("nombre", "archivo")
            f_fecha = item.get("fecha", "")

            widget_item = QListWidgetItem()
            card = QFrame()
            bg_c = self.colores.get('bg_secundario', '#2D2D3D')
            card.setStyleSheet(f"background: {bg_c}; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.05);")
            lay = QHBoxLayout(card)
            lay.setContentsMargins(10, 8, 10, 8)
            lay.setSpacing(10)

            lbl_desc = QLabel(f"📄 <b>{f_nombre}</b><br><small style='color:#AAB0B8;'>{f_fecha} • {f_path}</small>")
            lbl_desc.setStyleSheet("border: none;")
            lay.addWidget(lbl_desc, 1)

            btn_run = QPushButton("▶️ Abrir")
            btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_run.setStyleSheet("background: #10B981; color: black; font-weight: bold; border-radius: 4px; padding: 5px 10px; font-size: 11px; border: none;")
            btn_run.clicked.connect(lambda ch, p=f_path: self._ejecutar_instalador_asincrono(p))
            lay.addWidget(btn_run)

            btn_dir = QPushButton("📁 Carpeta")
            btn_dir.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_dir.setStyleSheet("background: rgba(255,255,255,0.08); color: white; border-radius: 4px; padding: 5px 10px; font-size: 11px; border: none;")
            btn_dir.clicked.connect(lambda ch, p=f_path: self._abrir_carpeta(p))
            lay.addWidget(btn_dir)

            widget_item.setSizeHint(card.sizeHint())
            self.list_historial.addItem(widget_item)
            self.list_historial.setItemWidget(widget_item, card)

    def _abrir_directorio_descargas(self):
        ruta_dl = getattr(self.mgr, "ruta_descargas", None)
        if ruta_dl and Path(ruta_dl).exists():
            try:
                os.startfile(str(ruta_dl))
            except Exception:
                subprocess.Popen(["explorer", os.path.normpath(str(ruta_dl))])

    def _limpiar_historial(self):
        confirm = QMessageBox.question(
            self, "Confirmar Limpieza",
            "¿Deseas vaciar la lista del historial de descargas? (Los archivos descargados se conservarán en disco)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.mgr.historial_descargas = []
            if hasattr(self.mgr, "guardar_historial"):
                self.mgr.guardar_historial()
            self._refrescar_historial()

    def _ejecutar_instalador_asincrono(self, file_path):
        if not Path(file_path).exists():
            QMessageBox.warning(self, "Error", f"El archivo '{file_path}' ya no existe.")
            return

        self.mgr.ejecutar_instalador_asincrono(
            file_path,
            started_cb=lambda i_id: QMessageBox.information(self, "Ejecución Iniciada", f"Se ha abierto en segundo plano:\n{os.path.basename(file_path)}"),
            finished_cb=lambda i_id, code: print(f"[INSTALL-OK] Código {code}"),
            error_cb=lambda i_id, err: QMessageBox.warning(self, "Error", f"No se pudo ejecutar: {err}")
        )

    def _abrir_carpeta(self, file_path):
        folder = os.path.dirname(file_path)
        if os.path.exists(folder):
            try:
                os.startfile(folder)
            except Exception:
                subprocess.Popen(["explorer", os.path.normpath(folder)])

    def actualizar_tema(self, colores):
        if isinstance(colores, dict):
            self.colores = colores
            bg_p = self.colores.get('bg_principal', '#1E1E1E')
            self.setStyleSheet(f"background-color: {bg_p}; color: white;")
            self._refrescar_historial()
