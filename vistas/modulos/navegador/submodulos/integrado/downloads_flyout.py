"""
downloads_flyout.py - Vista emergente flotante (Flyout/Popup) de descargas para MultiTabBrowser
Ofrece la experiencia idéntica a Google Chrome / Microsoft Edge con panel flotante anclado a la barra de herramientas.
Integrado armónicamente con la paleta de colores y tema de la aplicación.
"""
import os
import time
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QScrollArea, QFrame, QSizePolicy, QStyle, QStyleOption
)
from PyQt6.QtCore import Qt, QPoint, QUrl, QTimer
from PyQt6.QtGui import QFont, QDesktopServices, QIcon, QPainter



class DownloadItemWidget(QFrame):
    """Fila interactiva para una descarga (activa o completada) dentro del flyout emergente."""
    def __init__(self, data, is_active=False, is_failed=False, colores=None, on_cancel=None, parent=None):
        super().__init__(parent)
        self.setObjectName("DownloadItemWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.colores = colores or {}
        self.data = data
        self.is_active = is_active
        self.is_failed = is_failed
        self.on_cancel = on_cancel
        self.init_ui()

    def init_ui(self):
        bg_card = self.colores.get('bg_secundario', '#2D2D2D')
        bg_hover = self.colores.get('bg_terciario', '#3D3D3D')
        acento = self.colores.get('acento', '#6366F1')
        fg_p = self.colores.get('fg_principal', '#FFFFFF')
        fg_sec = self.colores.get('fg_secundario', '#A0A0A0')
        
        border_style = "1px solid rgba(239, 68, 68, 0.4)" if self.is_failed else "1px solid rgba(255, 255, 255, 0.08)"
        hover_border = "#EF4444" if self.is_failed else acento

        self.setStyleSheet(f"""
            QFrame#DownloadItemWidget {{
                background-color: {bg_card};
                border: {border_style};
                border-radius: 8px;
            }}
            QFrame#DownloadItemWidget:hover {{
                background-color: {bg_hover};
                border: 1px solid {hover_border};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Fila superior: Icono, Nombre y Botón de acción rápida
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Icono según tipo de archivo
        nombre = self.data.get("name") or self.data.get("nombre") or "archivo"
        ext = Path(nombre).suffix.lower()
        ico = "📄"
        if self.is_failed:
            ico = "⚠️"
        elif ext in (".exe", ".msi", ".bat", ".cmd"):
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
        lbl_ico.setStyleSheet("font-size: 14px; border: none; background: transparent;")
        top_row.addWidget(lbl_ico)

        # Nombre del archivo truncado elegantemente
        display_name = nombre if len(nombre) <= 26 else (nombre[:23] + "...")
        self.lbl_name = QLabel(display_name)
        self.lbl_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet(f"color: {fg_p}; border: none; background: transparent;")
        self.lbl_name.setToolTip(nombre)
        top_row.addWidget(self.lbl_name, 1)

        if self.is_failed:
            # Botón para descartar tarjeta de descarga interrumpida
            btn_dismiss = QPushButton("✕")
            btn_dismiss.setFixedSize(22, 22)
            btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_dismiss.setToolTip("Descartar")
            btn_dismiss.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: #A0A0A0;
                    border: none;
                    border-radius: 11px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background: rgba(239, 68, 68, 0.3);
                    color: #FFFFFF;
                }
            """)
            if self.on_cancel:
                btn_dismiss.clicked.connect(self.on_cancel)
            top_row.addWidget(btn_dismiss)
        elif self.is_active:
            # Botón cancelar para descargas activas
            btn_cancel = QPushButton("✕")
            btn_cancel.setFixedSize(22, 22)
            btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cancel.setToolTip("Cancelar descarga")
            btn_cancel.setStyleSheet("""
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
            if self.on_cancel:
                btn_cancel.clicked.connect(self.on_cancel)
            top_row.addWidget(btn_cancel)
        else:
            # Botones de abrir archivo y carpeta para descargas completadas
            fpath = self.data.get("path", "")
            btn_run = QPushButton("Abrir")
            btn_run.setFixedSize(54, 24)
            btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_run.setStyleSheet("""
                QPushButton {
                    background: #10B981;
                    color: #000000;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background: #059669;
                    color: #FFFFFF;
                }
            """)
            btn_run.clicked.connect(lambda: self._abrir_archivo(fpath))
            top_row.addWidget(btn_run)

            btn_folder = QPushButton("📁")
            btn_folder.setFixedSize(26, 24)
            btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_folder.setToolTip("Mostrar en carpeta")
            btn_folder.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: #FFFFFF;
                    border-radius: 4px;
                    font-size: 11px;
                    border: none;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.2);
                }
            """)
            btn_folder.clicked.connect(lambda: self._abrir_carpeta(fpath))
            top_row.addWidget(btn_folder)

        layout.addLayout(top_row)

        if self.is_failed:
            reason = self.data.get("reason", "Descarga interrumpida")
            lbl_fail = QLabel(f"⚠️ {reason}")
            lbl_fail.setStyleSheet("color: #F87171; font-size: 10px; border: none; background: transparent;")
            lbl_fail.setWordWrap(True)
            layout.addWidget(lbl_fail)
        elif self.is_active:
            # Barra de progreso
            self.pbar = QProgressBar()
            self.pbar.setFixedHeight(6)
            self.pbar.setTextVisible(False)
            self.pbar.setStyleSheet(f"""
                QProgressBar {{
                    background: {self.colores.get('bg_principal', '#1E1E1E')};
                    border-radius: 3px;
                    border: none;
                }}
                QProgressBar::chunk {{
                    background: {acento};
                    border-radius: 3px;
                }}
            """)
            layout.addWidget(self.pbar)

            # Subtítulo con progreso y velocidad
            self.lbl_status = QLabel("Descargando...")
            self.lbl_status.setStyleSheet(f"color: {fg_sec}; font-size: 10px; border: none; background: transparent;")
            layout.addWidget(self.lbl_status)
        else:
            # Estado de descarga completada
            f_size = self.data.get("size", "")
            f_fecha = self.data.get("fecha", "")
            info_str = "Completada"
            if f_size:
                info_str += f" • {f_size}"
            if f_fecha:
                short_fecha = f_fecha.split(" ")[-1] if " " in f_fecha else f_fecha
                info_str += f" • {short_fecha}"

            lbl_sub = QLabel(info_str)
            lbl_sub.setStyleSheet(f"color: {fg_sec}; font-size: 10px; border: none; background: transparent;")
            layout.addWidget(lbl_sub)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

    def actualizar_progreso(self, recv_bytes, total_bytes):
        if not self.is_active:
            return
        if total_bytes > 0:
            pct = int((recv_bytes / total_bytes) * 100)
            self.pbar.setValue(min(100, pct))
            recv_mb = recv_bytes / (1024 * 1024)
            tot_mb = total_bytes / (1024 * 1024)
            if pct >= 100:
                self.lbl_status.setText(f"{recv_mb:.1f} MB • Finalizando y verificando...")
            else:
                self.lbl_status.setText(f"{recv_mb:.1f} MB de {tot_mb:.1f} MB ({pct}%)")
        else:
            recv_mb = recv_bytes / (1024 * 1024)
            self.lbl_status.setText(f"{recv_mb:.1f} MB transferidos")

    def _abrir_archivo(self, path):
        if path and Path(path).exists():
            try:
                os.startfile(str(path))
            except Exception:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _abrir_carpeta(self, path):
        folder = Path(path).parent if path else Path.home() / "Downloads"
        if folder.exists():
            try:
                subprocess.Popen(["explorer", "/select,", os.path.normpath(str(path))])
            except Exception:
                try:
                    os.startfile(str(folder))
                except Exception:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))


class DownloadsFlyoutWidget(QFrame):
    """Ventana emergente tipo Flyout anclada al botón de descargas de la barra de navegación."""
    def __init__(self, parent_browser, colores=None):
        super().__init__(parent_browser, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.browser = parent_browser
        self.colores = colores or getattr(parent_browser, "colores", {})
        self.setObjectName("DownloadsFlyoutWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(380)
        self.active_items = {} # {path: DownloadItemWidget}
        self.failed_items = {} # {path: dict con info de error}

        # Temporizador para monitoreo en tiempo real mientras el panel esté visible
        self.timer_live = QTimer(self)
        self.timer_live.setInterval(1000)
        self.timer_live.timeout.connect(self._actualizar_en_vivo)

        self.init_ui()


    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#1E1E1E')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        acento = self.colores.get('acento', '#6366F1')
        fg_p = self.colores.get('fg_principal', '#FFFFFF')
        fg_sec = self.colores.get('fg_secundario', '#A0A0A0')

        self.setStyleSheet(f"""
            QFrame#DownloadsFlyoutWidget {{
                background-color: {bg_p};
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 12px;
            }}
        """)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(14, 14, 14, 14)
        main_lay.setSpacing(10)

        # 1. Cabecera del Flyout
        header_lay = QHBoxLayout()
        header_lay.setSpacing(6)

        lbl_tit = QLabel("📥 Descargas")
        lbl_tit.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {fg_p}; border: none; background: transparent;")
        header_lay.addWidget(lbl_tit)

        self.lbl_badge = QLabel("")
        self.lbl_badge.setStyleSheet(f"""
            background-color: {acento};
            color: #FFFFFF;
            font-size: 10px;
            font-weight: bold;
            padding: 2px 7px;
            border-radius: 10px;
            border: none;
        """)
        self.lbl_badge.setVisible(False)
        header_lay.addWidget(self.lbl_badge)

        header_lay.addStretch()

        btn_folder = QPushButton("📂")
        btn_folder.setFixedSize(26, 26)
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_folder.setToolTip("Abrir carpeta de descargas de Windows")
        btn_folder.setStyleSheet(f"""
            QPushButton {{
                background: {bg_sec};
                color: #FFFFFF;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.2);
            }}
        """)
        btn_folder.clicked.connect(self._abrir_carpeta_descargas)
        header_lay.addWidget(btn_folder)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {fg_sec};
                border-radius: 6px;
                border: none;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.12);
                color: #FFFFFF;
            }}
        """)
        btn_close.clicked.connect(self.hide)
        header_lay.addWidget(btn_close)

        main_lay.addLayout(header_lay)

        # 2. Contenedor con scroll para descargas activas y recientes
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {
                background: transparent;
                width: 5px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 2px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }}
        """.replace("}}", "}"))
        self.scroll.viewport().setStyleSheet("background: transparent; border: none;")
        self.scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent; border: none;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.scroll.setWidget(self.list_container)

        main_lay.addWidget(self.scroll, 1)

        # 3. Pie del Flyout: Botón para ver historial completo
        btn_ver_todas = QPushButton("Ver todas las descargas ↗")
        btn_ver_todas.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ver_todas.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_sec};
                color: {fg_p};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 7px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {acento};
                color: #FFFFFF;
                border-color: {acento};
            }}
        """)
        btn_ver_todas.clicked.connect(self._ir_al_submodulo_descargas)
        main_lay.addWidget(btn_ver_todas)

        self.setFixedHeight(380)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

    def actualizar_tema(self, colores):
        """Actualiza los colores del Flyout cuando cambia el tema de la aplicación."""
        if isinstance(colores, dict):
            self.colores = colores
            self.init_ui()
            self.refrescar_contenido()

    def mostrar_bajo_boton(self, target_widget):
        """Calcula las coordenadas y muestra el flyout flotante justo debajo del botón de descargas."""
        self.refrescar_contenido()
        if not self.timer_live.isActive():
            self.timer_live.start()

        if target_widget and target_widget.isVisible():
            geo = target_widget.geometry()
            bottom_left = target_widget.mapToGlobal(QPoint(0, geo.height()))
            # Alinear a la derecha del botón
            x = bottom_left.x() + geo.width() - self.width()
            y = bottom_left.y() + 6
            # Ajustar a pantalla si se desborda
            screen = target_widget.screen()
            if screen:
                screen_rect = screen.availableGeometry()
                x = max(screen_rect.left() + 8, min(x, screen_rect.right() - self.width() - 8))
            self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def hideEvent(self, event):
        if hasattr(self, "timer_live") and self.timer_live.isActive():
            self.timer_live.stop()
        super().hideEvent(event)

    def _actualizar_en_vivo(self):
        """Monitorea el progreso de descargas en vivo mientras el flyout está desplegado."""
        if hasattr(self.browser, "verificar_descargas_activas"):
            try:
                self.browser.verificar_descargas_activas()
            except Exception:
                pass

        active_dl = getattr(self.browser, "active_downloads", {})
        if len(active_dl) != len(self.active_items):
            self.refrescar_contenido()
            return
        for path, info in list(active_dl.items()):
            if path in self.active_items:
                self.active_items[path].actualizar_progreso(info.get("recv", 0), info.get("total", 0))
            else:
                self.refrescar_contenido()
                return

    def notificar_fallida(self, path, reason):
        """Registra una descarga interrumpida (ej. antivirus) para mostrar advertencia clara."""
        fname = Path(path).name if path else "Descarga"
        self.failed_items[path] = {
            "name": fname,
            "path": path,
            "reason": reason,
            "time": time.time()
        }
        self.refrescar_contenido()

    def _descartar_fallida(self, path):
        if path in self.failed_items:
            del self.failed_items[path]
        self.refrescar_contenido()

    def refrescar_contenido(self):
        """Reconstruye dinámicamente las tarjetas de descargas activas y las últimas completadas."""
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.active_items.clear()
        acento = self.colores.get('acento', '#6366F1')
        fg_sec = self.colores.get('fg_secundario', '#A0A0A0')

        # 1. Añadir descargas interrumpidas o bloqueadas por antivirus
        if self.failed_items:
            lbl_sec_fail = QLabel("⚠️ INTERRUMPIDAS / BLOQUEADAS")
            lbl_sec_fail.setStyleSheet("color: #EF4444; font-size: 9px; font-weight: bold; letter-spacing: 1px; border: none; background: transparent;")
            self.list_layout.addWidget(lbl_sec_fail)

            for fpath, finfo in list(self.failed_items.items()):
                item_widget = DownloadItemWidget(
                    data=finfo,
                    is_active=False,
                    is_failed=True,
                    colores=self.colores,
                    on_cancel=lambda p=fpath: self._descartar_fallida(p)
                )
                self.list_layout.addWidget(item_widget)

        # 2. Añadir descargas activas en curso
        active_dl = getattr(self.browser, "active_downloads", {})
        if active_dl:
            lbl_sec_act = QLabel("⏳ EN CURSO")
            lbl_sec_act.setStyleSheet(f"color: {acento}; font-size: 9px; font-weight: bold; letter-spacing: 1px; border: none; background: transparent;")
            self.list_layout.addWidget(lbl_sec_act)

            for path, info in active_dl.items():
                item_widget = DownloadItemWidget(
                    data=info,
                    is_active=True,
                    colores=self.colores,
                    on_cancel=lambda p=path: self._cancelar_descarga_activa(p)
                )
                self.list_layout.addWidget(item_widget)
                self.active_items[path] = item_widget
                recv = info.get("recv", 0)
                tot = info.get("total", 0)
                if tot > 0 or recv > 0:
                    item_widget.actualizar_progreso(recv, tot)

            self.lbl_badge.setText(str(len(active_dl)))
            self.lbl_badge.setVisible(True)
        else:
            self.lbl_badge.setVisible(False)

        # 2. Añadir descargas recientes completadas del historial
        historial = self._obtener_historial_reciente()
        if historial:
            lbl_sec_hist = QLabel("📁 RECIENTES")
            lbl_sec_hist.setStyleSheet(f"color: {fg_sec}; font-size: 9px; font-weight: bold; letter-spacing: 1px; margin-top: 6px; border: none; background: transparent;")
            self.list_layout.addWidget(lbl_sec_hist)

            for item_data in historial[:6]:
                if item_data.get("path") in active_dl:
                    continue
                item_widget = DownloadItemWidget(
                    data=item_data,
                    is_active=False,
                    colores=self.colores
                )
                self.list_layout.addWidget(item_widget)

        if not active_dl and not historial:
            lbl_empty = QLabel("No hay descargas recientes\nLos archivos que descargues aparecerán aquí.")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet(f"color: {fg_sec}; font-size: 11px; padding: 50px 10px; border: none; background: transparent;")
            self.list_layout.addWidget(lbl_empty)

        self.list_layout.addStretch()

    def notificar_descarga_iniciada(self, path, uri):
        """Llamado cuando comienza una nueva descarga: refresca y abre el flyout durante 3 segundos."""
        self.refrescar_contenido()
        if hasattr(self.browser, "toolbar") and hasattr(self.browser.toolbar, "btn_downloads"):
            btn = self.browser.toolbar.btn_downloads
            self.mostrar_bajo_boton(btn)

    def notificar_progreso(self, path, recv, total):
        """Actualiza el progreso en vivo de una tarjeta activa."""
        if path in self.active_items:
            self.active_items[path].actualizar_progreso(recv, total)

    def notificar_completada(self, path, uri):
        """Llamado al terminar una descarga: actualiza la lista inmediatamente en vivo."""
        self.refrescar_contenido()
        # Segundo refresco breve para garantizar lectura tras flush a disco
        QTimer.singleShot(250, self.refrescar_contenido)

    def _obtener_historial_reciente(self):
        try:
            p = getattr(self.browser, "parent_module", None)
            while p and not hasattr(p, "sub_descargas") and hasattr(p, "parent_module"):
                p = getattr(p, "parent_module", None)
            if p and hasattr(p, "sub_descargas") and hasattr(p.sub_descargas, "mgr"):
                if p.sub_descargas.mgr.historial_descargas:
                    return p.sub_descargas.mgr.historial_descargas
        except Exception:
            pass

        # Búsqueda en rutas potenciales de descargas.json
        candidatos = []
        if hasattr(self.browser, "ruta_usuario"):
            candidatos.append(Path(self.browser.ruta_usuario) / "descargas.json")
        if hasattr(self.browser, "data_dir"):
            candidatos.append(Path(self.browser.data_dir).parent / "descargas.json")
            candidatos.append(Path(self.browser.data_dir) / "descargas.json")
        candidatos.append(Path.cwd() / "descargas.json")

        import json
        for c in candidatos:
            if c.exists():
                try:
                    with open(c, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data and isinstance(data, list):
                            return data
                except Exception:
                    pass
        return []


    def _abrir_carpeta_descargas(self):
        dl_dir = Path.home() / "Downloads"
        if dl_dir.exists():
            try:
                os.startfile(str(dl_dir))
            except Exception:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(dl_dir)))

    def _cancelar_descarga_activa(self, path):
        if hasattr(self.browser, "cancelar_descarga"):
            self.browser.cancelar_descarga(path)
        if hasattr(self.browser, "actions_handler") and hasattr(self.browser.actions_handler, "_remover_descarga_activa"):
            self.browser.actions_handler._remover_descarga_activa(path)
        elif path in getattr(self.browser, "active_downloads", {}):
            del self.browser.active_downloads[path]
        self.refrescar_contenido()

    def _ir_al_submodulo_descargas(self):
        self.hide()
        try:
            p = getattr(self.browser, "parent_module", None)
            while p and not hasattr(p, "sub_descargas") and hasattr(p, "parent_module"):
                p = getattr(p, "parent_module", None)
            if p and hasattr(p, "tabs") and hasattr(p, "sub_descargas"):
                idx = p.tabs.indexOf(p.sub_descargas)
                if idx >= 0:
                    p.tabs.setCurrentIndex(idx)
                    p.sub_descargas._refrescar_historial()
        except Exception as e:
            print(f"[DownloadsFlyout] Error navegando al submódulo de descargas: {e}")
