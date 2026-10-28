"""
descargas.py - Submódulo visual de Gestión de Descargas Asíncronas e Instalación de Archivos
Diseño responsivo de dos columnas lado a lado (QSplitter) con soporte para descargas
locales fuera del predeterminado, sincronización con WebView2 y botones de acción nunca ocultos.
"""
import os
import subprocess
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QProgressBar, QFrame, QScrollArea, QListWidget, QListWidgetItem,
    QMessageBox, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QTimer, QUrl
from PyQt6.QtGui import QFont, QDesktopServices

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
        self.active_cards = {} # {download_id: {"frame": ..., "pbar": ..., "lbl": ..., "is_browser": bool}}

        # Temporizador para mantener sincronizadas descargas activas del navegador integrado
        self.timer_sync = QTimer(self)
        self.timer_sync.setInterval(1200)
        self.timer_sync.timeout.connect(self._sincronizar_activas_en_vivo)

        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        # Sincronizar descargas de carpetas del sistema y descargas activas al abrir la pestaña
        try:
            self.mgr.sincronizar_descargas_locales()
        except Exception:
            pass
        self._refrescar_historial()
        self._sincronizar_activas_en_vivo()
        if not self.timer_sync.isActive():
            self.timer_sync.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.timer_sync.isActive():
            self.timer_sync.stop()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#1E1E1E')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        acento = self.colores.get('acento', '#6366F1')
        
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(14, 14, 14, 14)
        main_lay.setSpacing(12)

        # 1. Header y acciones rápidas
        header_bar = QHBoxLayout()
        header_bar.setSpacing(8)

        lbl_t = QLabel("⚡ GESTOR DE DESCARGAS E INSTALADORES")
        lbl_t.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {acento}; border: none;")
        header_bar.addWidget(lbl_t)
        header_bar.addStretch()

        # Botón para sincronizar descargas guardadas fuera de la carpeta predeterminada
        btn_sync = QPushButton("🔄 Sincronizar")
        btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sync.setToolTip("Buscar descargas recientes en tu carpeta Descargas del sistema y rutas personalizadas")
        btn_sync.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_sec};
                color: #A5B4FC;
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 6px;
                padding: 6px 13px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {acento};
                color: #FFFFFF;
            }}
        """)
        btn_sync.clicked.connect(self._sincronizar_descargas)
        header_bar.addWidget(btn_sync)

        btn_open_folder = QPushButton("📂 Abrir Carpeta")
        btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_folder.setToolTip("Abrir la carpeta principal de descargas")
        btn_open_folder.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_sec};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 6px 13px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
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
                padding: 6px 13px;
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

        # 2. Barra para iniciar descarga directa mediante enlace
        box_dl = QFrame()
        box_dl.setStyleSheet(f"background: {bg_sec}; border-radius: 8px; padding: 6px 10px; border: 1px solid rgba(255, 255, 255, 0.06);")
        b_lay = QHBoxLayout(box_dl)
        b_lay.setContentsMargins(6, 2, 6, 2)
        b_lay.setSpacing(8)

        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("Pega aquí el enlace directo (URL HTTP/HTTPS) para descargar...")
        self.txt_url.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#3D3D3D')}; color: white; border-radius: 6px; padding: 7px 10px; border: none; font-size: 12px;")
        self.txt_url.returnPressed.connect(self._iniciar_descarga)
        b_lay.addWidget(self.txt_url, 1)

        btn_dl = QPushButton("⬇️ Descargar")
        btn_dl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dl.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 7px 16px; font-weight: bold; border: none; font-size: 11px;")
        btn_dl.clicked.connect(self._iniciar_descarga)
        b_lay.addWidget(btn_dl)

        main_lay.addWidget(box_dl)

        # 3. SPLITTER PRINCIPAL: Dos Columnas Paralelas Lado a Lado
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

        lbl_act = QLabel("⏳ Descargas en Curso")
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
        self.lbl_empty_active = QLabel("No hay descargas en curso.\nLas descargas que inicies desde el navegador o pegues arriba aparecerán aquí en vivo.")
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
        self.txt_buscar_hist.setPlaceholderText("🔍 Filtrar descargas por nombre o carpeta...")
        self.txt_buscar_hist.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#3D3D3D')}; color: white; border-radius: 6px; padding: 6px 10px; border: none; font-size: 11px;")
        self.txt_buscar_hist.textChanged.connect(self._refrescar_historial)
        der_lay.addWidget(self.txt_buscar_hist)

        self.list_historial = QListWidget()
        self.list_historial.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
                margin-bottom: 6px;
            }}
        """)
        der_lay.addWidget(self.list_historial, 1)

        self.splitter.addWidget(col_der)
        self.splitter.setSizes([400, 560])

        main_lay.addWidget(self.splitter, 1)

        self._refrescar_historial()

    def _sincronizar_descargas(self):
        """Escanea las carpetas de descargas y actualiza el historial."""
        try:
            self.mgr.sincronizar_descargas_locales()
            self._refrescar_historial()
        except Exception as e:
            print(f"[Descargas] Error al sincronizar descargas: {e}")

    def _sincronizar_activas_en_vivo(self):
        """Mantiene sincronizadas las descargas que se están realizando desde el navegador integrado (WebView2)."""
        browser_active = {}
        try:
            p = self.parent()
            sub_int = getattr(p, "sub_integrado", None)
            if sub_int and hasattr(sub_int, "active_downloads"):
                browser_active = sub_int.active_downloads
        except Exception:
            pass

        # 1. Agregar o actualizar tarjetas de descargas del navegador
        for path, info in list(browser_active.items()):
            dl_id = f"wv2_{path}"
            recv = info.get("recv", 0)
            total = info.get("total", 0)
            url = info.get("url", "")

            if dl_id not in self.active_cards:
                self._crear_tarjeta_activa(dl_id, path, is_browser_dl=True)

            card_info = self.active_cards[dl_id]
            if total > 0:
                pct = int((recv / total) * 100)
                card_info["pbar"].setValue(min(100, pct))
                recv_mb = recv / (1024 * 1024)
                tot_mb = total / (1024 * 1024)
                if pct >= 100:
                    card_info["lbl"].setText(f"{recv_mb:.1f} MB • Finalizando y verificando...")
                else:
                    card_info["lbl"].setText(f"{recv_mb:.1f} MB de {tot_mb:.1f} MB ({pct}%)")
            else:
                recv_mb = recv / (1024 * 1024)
                card_info["lbl"].setText(f"{recv_mb:.1f} MB transferidos")

        # 2. Remover tarjetas de WebView2 que ya terminaron o fueron interrumpidas
        import os
        norm_active = {os.path.normcase(os.path.normpath(str(p))) for p in browser_active.keys()}
        wv2_keys_in_cards = [k for k in list(self.active_cards.keys()) if k.startswith("wv2_")]
        for k in wv2_keys_in_cards:
            orig_path = k.replace("wv2_", "", 1)
            norm_orig = os.path.normcase(os.path.normpath(str(orig_path)))
            if orig_path not in browser_active and norm_orig not in norm_active:
                self.active_cards[k]["frame"].deleteLater()
                del self.active_cards[k]

        has_active = len(self.active_cards) > 0
        self.lbl_empty_active.setVisible(not has_active)

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
        self._crear_tarjeta_activa(dl_id, url, is_browser_dl=False)
        self.txt_url.clear()

    def _crear_tarjeta_activa(self, dl_id, url_or_path, is_browser_dl=False):
        self.lbl_empty_active.setVisible(False)
        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; border-radius: 8px; padding: 10px; border: 1px solid rgba(255, 255, 255, 0.08);")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        if is_browser_dl:
            nom_archivo = Path(url_or_path).name or "descarga_web"
        else:
            nom_archivo = url_or_path.split("?")[0].rstrip("/").split("/")[-1] or "archivo_descarga"

        lbl_info = QLabel(f"⬇️ <b>{nom_archivo}</b>")
        lbl_info.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_info.setStyleSheet("color: white; border: none;")
        lbl_info.setToolTip(str(url_or_path))
        top_row.addWidget(lbl_info, 1)

        btn_cancelar = QPushButton("✕")
        btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancelar.setFixedSize(22, 22)
        btn_cancelar.setToolTip("Cancelar descarga")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 11px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #EF4444;
                color: #FFFFFF;
            }
        """)
        btn_cancelar.clicked.connect(lambda _, d=dl_id, is_b=is_browser_dl, p=url_or_path: self._cancelar_descarga(d, is_b, p))
        top_row.addWidget(btn_cancelar)
        lay.addLayout(top_row)

        pbar = QProgressBar()
        acento = self.colores.get('acento', '#6366F1')
        pbar.setFixedHeight(8)
        pbar.setTextVisible(False)
        pbar.setStyleSheet(f"""
            QProgressBar {{
                background: {self.colores.get('bg_principal', '#121218')};
                border-radius: 4px;
                border: none;
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
        self.active_cards[dl_id] = {"frame": card, "pbar": pbar, "lbl": lbl_speed, "is_browser": is_browser_dl}

    def _cancelar_descarga(self, dl_id, is_browser_dl=False, file_path=""):
        if is_browser_dl:
            try:
                p = self.parent()
                sub_int = getattr(p, "sub_integrado", None)
                if sub_int and hasattr(sub_int, "cancelar_descarga"):
                    sub_int.cancelar_descarga(file_path)
            except Exception as e:
                print(f"[Descargas] Error cancelando descarga en navegador: {e}")
        else:
            self.mgr.cancelar_descarga(dl_id)

        if dl_id in self.active_cards:
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
        """Renderiza las descargas del historial con diseño altamente responsivo y botones fijos."""
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
            f_size = item.get("size", "")
            f_id = item.get("id", f_path)

            widget_item = QListWidgetItem()
            # Altura fija garantizada para que cada item se muestre sin desbordarse
            widget_item.setSizeHint(QSize(0, 68))

            card = QFrame()
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            bg_c = self.colores.get('bg_secundario', '#2D2D3D')
            card.setStyleSheet(f"""
                QFrame {{
                    background: {bg_c};
                    border-radius: 6px;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                }}
                QFrame:hover {{
                    border-color: rgba(99, 102, 241, 0.35);
                    background: rgba(255, 255, 255, 0.03);
                }}
            """)

            lay = QHBoxLayout(card)
            lay.setContentsMargins(10, 8, 10, 8)
            lay.setSpacing(8)

            # 1. Icono temático según extensión
            ext = Path(f_nombre).suffix.lower()
            ico = "📄"
            if ext in (".exe", ".msi", ".bat", ".cmd"):
                ico = "⚙️"
            elif ext in (".zip", ".rar", ".7z", ".tar", ".gz"):
                ico = "📦"
            elif ext in (".mp4", ".mkv", ".avi", ".mov", ".webm"):
                ico = "🎬"
            elif ext in (".mp3", ".wav", ".flac", ".ogg"):
                ico = "🎵"
            elif ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
                ico = "🖼️"
            elif ext in (".pdf", ".docx", ".xlsx", ".txt"):
                ico = "📑"

            lbl_ico = QLabel(ico)
            lbl_ico.setStyleSheet("font-size: 16px; border: none; background: transparent;")
            lbl_ico.setFixedWidth(24)
            lay.addWidget(lbl_ico)

            # 2. Información del archivo (Nombre arriba, detalles abajo)
            info_layout = QVBoxLayout()
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(2)

            # Nombre recortado para que no ensanche el layout con tooltip completo
            display_name = f_nombre if len(f_nombre) <= 35 else (f_nombre[:32] + "...")
            lbl_nombre = QLabel(display_name)
            lbl_nombre.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl_nombre.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")
            lbl_nombre.setToolTip(f"{f_nombre}\nRuta: {f_path}")
            lbl_nombre.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            info_layout.addWidget(lbl_nombre)

            # Subtítulo con detalles y carpeta contenedora acortada
            folder_name = Path(f_path).parent.name if f_path else "Descargas"
            detalles_partes = []
            if f_size:
                detalles_partes.append(f_size)
            if f_fecha:
                short_fecha = f_fecha.split(" ")[0] if " " in f_fecha else f_fecha
                detalles_partes.append(short_fecha)
            detalles_partes.append(f"📁 {folder_name}")
            sub_texto = " • ".join(detalles_partes)

            lbl_sub = QLabel(sub_texto)
            lbl_sub.setStyleSheet("color: #94A3B8; font-size: 10px; border: none; background: transparent;")
            lbl_sub.setToolTip(f"Ruta completa:\n{f_path}")
            lbl_sub.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            info_layout.addWidget(lbl_sub)

            lay.addLayout(info_layout, 1)

            # 3. Botones de acción con dimensiones fijas (nunca aplastados ni ocultos)
            btn_box = QHBoxLayout()
            btn_box.setSpacing(6)
            btn_box.setContentsMargins(0, 0, 0, 0)

            is_executable = ext in (".exe", ".msi", ".bat", ".cmd")
            run_title = "⚙️ Instalar" if is_executable else "▶️ Abrir"
            btn_run = QPushButton(run_title)
            btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_run.setToolTip(f"Abrir o ejecutar {f_nombre}")
            btn_run.setFixedSize(70, 26)
            btn_run.setStyleSheet("""
                QPushButton {
                    background: #10B981;
                    color: #000000;
                    font-weight: bold;
                    border-radius: 4px;
                    font-size: 10px;
                    border: none;
                }
                QPushButton:hover {
                    background: #059669;
                    color: #FFFFFF;
                }
            """)
            btn_run.clicked.connect(lambda ch, p=f_path: self._ejecutar_instalador_asincrono(p))
            btn_box.addWidget(btn_run)

            btn_dir = QPushButton("📁 Carpeta")
            btn_dir.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_dir.setToolTip("Abrir la carpeta contenedora en el Explorador")
            btn_dir.setFixedSize(74, 26)
            btn_dir.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: #FFFFFF;
                    border-radius: 4px;
                    font-size: 10px;
                    border: none;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.18);
                }
            """)
            btn_dir.clicked.connect(lambda ch, p=f_path: self._abrir_carpeta(p))
            btn_box.addWidget(btn_dir)

            btn_del = QPushButton("🗑️")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setToolTip("Quitar del historial (el archivo se conservará en disco)")
            btn_del.setFixedSize(28, 26)
            btn_del.setStyleSheet("""
                QPushButton {
                    background: rgba(239, 68, 68, 0.12);
                    color: #EF4444;
                    border-radius: 4px;
                    font-size: 11px;
                    border: none;
                }
                QPushButton:hover {
                    background: #EF4444;
                    color: #FFFFFF;
                }
            """)
            btn_del.clicked.connect(lambda ch, target=f_id: self._eliminar_item_historial(target))
            btn_box.addWidget(btn_del)

            lay.addLayout(btn_box)

            self.list_historial.addItem(widget_item)
            self.list_historial.setItemWidget(widget_item, card)

    def _eliminar_item_historial(self, path_or_id):
        """Elimina una descarga del historial y refresca la lista."""
        self.mgr.eliminar_item_historial(path_or_id)
        self._refrescar_historial()

    def _abrir_directorio_descargas(self):
        """Abre la carpeta de descargas del usuario o la del sistema."""
        ruta_dl = getattr(self.mgr, "ruta_descargas", None)
        if ruta_dl and Path(ruta_dl).exists():
            try:
                os.startfile(str(ruta_dl))
                return
            except Exception:
                pass

        dl_sys = Path.home() / "Downloads"
        if dl_sys.exists():
            try:
                os.startfile(str(dl_sys))
            except Exception:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(dl_sys)))

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
        if not file_path or not Path(file_path).exists():
            QMessageBox.warning(self, "Error", f"El archivo '{file_path}' ya no existe en el disco.")
            return

        self.mgr.ejecutar_instalador_asincrono(
            file_path,
            started_cb=lambda i_id: QMessageBox.information(self, "Ejecución Iniciada", f"Se ha abierto en segundo plano:\n{os.path.basename(file_path)}"),
            finished_cb=lambda i_id, code: print(f"[INSTALL-OK] Código {code}"),
            error_cb=lambda i_id, err: QMessageBox.warning(self, "Error", f"No se pudo ejecutar: {err}")
        )

    def _abrir_carpeta(self, file_path):
        folder = os.path.dirname(file_path) if file_path else str(Path.home() / "Downloads")
        if os.path.exists(folder):
            try:
                subprocess.Popen(["explorer", "/select,", os.path.normpath(str(file_path))])
            except Exception:
                try:
                    os.startfile(folder)
                except Exception:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def actualizar_tema(self, colores):
        if isinstance(colores, dict):
            self.colores = colores
            bg_p = self.colores.get('bg_principal', '#1E1E1E')
            self.setStyleSheet(f"background-color: {bg_p}; color: white;")
            self._refrescar_historial()
