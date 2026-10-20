import os
import time
import datetime
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QComboBox, QCheckBox, 
    QFileDialog, QMessageBox, QScrollArea, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QImage, QGuiApplication

from .area_selector import AreaSelector

class CapturadorPantallaSubmodule(QWidget):
    """Submódulo 5: Captura Rápida de Pantalla, Recortes (Snipping), Retardo y Portapapeles"""
    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.area_seleccionada = None
        self.ultima_pixmap = None
        self.ultimo_path = None

        # Temporizador de cuenta regresiva
        self.timer_countdown = QTimer(self)
        self.timer_countdown.setInterval(1000)
        self.timer_countdown.timeout.connect(self._on_countdown_tick)
        self.segundos_restantes = 0
        self.modo_pendiente = "completa"

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#1E1E1E')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        bg_terc = self.colores.get('bg_terciario', '#3D3D3D')
        acento = self.colores.get('acento', '#4A86E8')
        exito = self.colores.get('exito', '#43A047')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        lbl_tit = QLabel("📸 CAPTURA DE PANTALLA & HERRAMIENTA DE RECORTES")
        lbl_tit.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 0.5px;")
        hdr.addWidget(lbl_tit)
        hdr.addStretch()
        layout.addLayout(hdr)

        # Barra de Controles y Opciones
        self.opts_frame = QFrame()
        self.opts_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 10px;")
        o_lay = QHBoxLayout(self.opts_frame)
        o_lay.setContentsMargins(12, 8, 12, 8)
        o_lay.setSpacing(12)

        # Monitor
        lbl_m = QLabel("🖥️ Monitor:")
        lbl_m.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        o_lay.addWidget(lbl_m)

        self.combo_pantalla = QComboBox()
        self.combo_pantalla.setFont(QFont(self.font_family, 9))
        self.combo_pantalla.setStyleSheet(f"""
            QComboBox {{ background: {bg_terc}; color: white; border-radius: 6px; padding: 5px 10px; border: none; }}
            QComboBox QAbstractItemView {{ background: {bg_sec}; color: white; selection-background-color: {acento}; }}
        """)
        screens = QGuiApplication.screens()
        for i, s in enumerate(screens):
            geo = s.geometry()
            self.combo_pantalla.addItem(f"Pantalla {i+1} ({geo.width()}x{geo.height()})")
        o_lay.addWidget(self.combo_pantalla)

        # Temporizador
        lbl_t = QLabel("⏱️ Retardo:")
        lbl_t.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        o_lay.addWidget(lbl_t)

        self.combo_retardo = QComboBox()
        self.combo_retardo.setFont(QFont(self.font_family, 9))
        self.combo_retardo.addItems(["Inmediato (0s)", "3 Segundos", "5 Segundos", "10 Segundos"])
        self.combo_retardo.setStyleSheet(self.combo_pantalla.styleSheet())
        o_lay.addWidget(self.combo_retardo)

        # Formato
        lbl_fmt = QLabel("💾 Formato:")
        lbl_fmt.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        o_lay.addWidget(lbl_fmt)

        self.combo_formato = QComboBox()
        self.combo_formato.setFont(QFont(self.font_family, 9))
        self.combo_formato.addItems(["PNG (Sin pérdida)", "JPG (Comprimido)", "BMP"])
        self.combo_formato.setStyleSheet(self.combo_pantalla.styleSheet())
        o_lay.addWidget(self.combo_formato)

        # Checkboxes
        self.chk_portapapeles = QCheckBox("📋 Copiar al Portapapeles")
        self.chk_portapapeles.setChecked(True)
        self.chk_portapapeles.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.chk_portapapeles.setStyleSheet("QCheckBox { color: white; background: transparent; }")
        o_lay.addWidget(self.chk_portapapeles)

        self.chk_ocultar_app = QCheckBox("🙈 Ocultar ventana")
        self.chk_ocultar_app.setChecked(True)
        self.chk_ocultar_app.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.chk_ocultar_app.setStyleSheet("QCheckBox { color: white; background: transparent; }")
        o_lay.addWidget(self.chk_ocultar_app)

        layout.addWidget(self.opts_frame)

        # Botones de Disparo
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_capturar_todo = QPushButton("📸 Capturar Pantalla Completa")
        self.btn_capturar_todo.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_capturar_todo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_capturar_todo.setStyleSheet(f"background: {acento}; color: white; border-radius: 8px; padding: 10px 18px; border: none;")
        self.btn_capturar_todo.clicked.connect(lambda: self._iniciar_captura("completa"))
        btn_bar.addWidget(self.btn_capturar_todo)

        self.btn_recortar_area = QPushButton("✂️ Seleccionar y Recortar Área")
        self.btn_recortar_area.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_recortar_area.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_recortar_area.setStyleSheet(f"background: {exito}; color: white; border-radius: 8px; padding: 10px 18px; border: none;")
        self.btn_recortar_area.clicked.connect(lambda: self._iniciar_captura("area"))
        btn_bar.addWidget(self.btn_recortar_area)

        self.lbl_countdown_status = QLabel("")
        self.lbl_countdown_status.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_countdown_status.setStyleSheet("color: #FBBF24;")
        btn_bar.addWidget(self.lbl_countdown_status)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        # ── Área Central de Visualización de la Captura ──
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #08080C;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        p_lay = QVBoxLayout(self.preview_frame)
        p_lay.setContentsMargins(10, 10, 10, 10)

        self.lbl_preview_img = QLabel()
        self.lbl_preview_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_img.setStyleSheet("background: transparent;")
        self.lbl_preview_img.hide()
        p_lay.addWidget(self.lbl_preview_img, 1)

        self.lbl_empty_preview = QLabel(f"""
            <div style='text-align: center;'>
                <span style='font-size: 38px;'>🖼️</span><br><br>
                <span style='font-size: 14px; font-weight: bold; color: {acento};'>SIN CAPTURA RECIENTE</span><br><br>
                <span style='font-size: 11px; color: rgba(255,255,255,0.6);'>Haz clic en 'Capturar Pantalla Completa' o 'Seleccionar y Recortar Área' para tomar una foto.</span>
            </div>
        """)
        self.lbl_empty_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_lay.addWidget(self.lbl_empty_preview, 1)

        layout.addWidget(self.preview_frame, 1)

        # Barra Inferior con Información de la Captura y Acciones
        self.bot_frame = QFrame()
        self.bot_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 8px 14px;")
        b_lay = QHBoxLayout(self.bot_frame)
        b_lay.setContentsMargins(10, 6, 10, 6)
        b_lay.setSpacing(10)

        self.lbl_info_captura = QLabel("Esperando captura...")
        self.lbl_info_captura.setFont(QFont(self.font_family, 8))
        self.lbl_info_captura.setStyleSheet("color: rgba(255,255,255,0.7);")
        b_lay.addWidget(self.lbl_info_captura)

        b_lay.addStretch()

        self.btn_copiar_portapapeles = QPushButton("📋 Copiar")
        self.btn_copiar_portapapeles.setEnabled(False)
        self.btn_copiar_portapapeles.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copiar_portapapeles.setStyleSheet(f"background: {bg_terc}; color: white; border-radius: 6px; padding: 6px 14px; border: none;")
        self.btn_copiar_portapapeles.clicked.connect(self._copiar_al_portapapeles)
        b_lay.addWidget(self.btn_copiar_portapapeles)

        self.btn_guardar_como = QPushButton("💾 Guardar Como...")
        self.btn_guardar_como.setEnabled(False)
        self.btn_guardar_como.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guardar_como.setStyleSheet(f"background: {bg_terc}; color: white; border-radius: 6px; padding: 6px 14px; border: none;")
        self.btn_guardar_como.clicked.connect(self._guardar_como)
        b_lay.addWidget(self.btn_guardar_como)

        self.btn_abrir_visor = QPushButton("👁️ Abrir en Visor")
        self.btn_abrir_visor.setEnabled(False)
        self.btn_abrir_visor.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abrir_visor.setStyleSheet(f"background: {bg_terc}; color: white; border-radius: 6px; padding: 6px 14px; border: none;")
        self.btn_abrir_visor.clicked.connect(self._abrir_en_visor)
        b_lay.addWidget(self.btn_abrir_visor)

        layout.addWidget(self.bot_frame)

    def _iniciar_captura(self, modo):
        self.modo_pendiente = modo
        retardos_map = {0: 0, 1: 3, 2: 5, 3: 10}
        idx = self.combo_retardo.currentIndex()
        segundos = retardos_map.get(idx, 0)

        if segundos > 0:
            self.segundos_restantes = segundos
            self.lbl_countdown_status.setText(f"⏳ Capturando en {self.segundos_restantes}s...")
            self.timer_countdown.start()
        else:
            self._ejecutar_captura()

    def _on_countdown_tick(self):
        self.segundos_restantes -= 1
        if self.segundos_restantes > 0:
            self.lbl_countdown_status.setText(f"⏳ Capturando en {self.segundos_restantes}s...")
        else:
            self.timer_countdown.stop()
            self.lbl_countdown_status.setText("")
            self._ejecutar_captura()

    def _ejecutar_captura(self):
        if self.modo_pendiente == "area":
            if self.chk_ocultar_app.isChecked():
                self.window().hide()
                QTimer.singleShot(250, self._abrir_selector_area)
            else:
                self._abrir_selector_area()
        else:
            if self.chk_ocultar_app.isChecked():
                self.window().hide()
                QTimer.singleShot(250, lambda: self._capturar_pantalla_completa(mostrar_ventana=True))
            else:
                self._capturar_pantalla_completa(mostrar_ventana=False)

    def _abrir_selector_area(self):
        p_idx = self.combo_pantalla.currentIndex()
        screens = QGuiApplication.screens()
        idx = p_idx if 0 <= p_idx < len(screens) else 0
        screen = screens[idx]

        # Tomar captura limpia de la pantalla antes de desplegar el selector
        desktop_pixmap = screen.grabWindow(0)
        self._desktop_pixmap_reciente = desktop_pixmap
        self.selector = AreaSelector(self._area_capturada_cb, pixmap_base=desktop_pixmap, screen_geo=screen.geometry())

    def _area_capturada_cb(self, x, y=None, w=None, h=None, crop_pixmap=None):
        try:
            if crop_pixmap is not None and not crop_pixmap.isNull():
                self._procesar_pixmap_final(crop_pixmap)
                return

            if y is not None and w is not None and h is not None and w > 10 and h > 10:
                area = (x, y, w, h)
            elif hasattr(x, 'width') and hasattr(x, 'height') and x.width() > 10 and x.height() > 10:
                area = (x.x(), x.y(), x.width(), x.height())
            else:
                return

            self._procesar_captura_area(area)
        finally:
            # Restaurar visibilidad de la ventana de la aplicación siempre al finalizar el recorte
            if self.chk_ocultar_app.isChecked():
                self.window().show()

    def _capturar_pantalla_completa(self, mostrar_ventana=False):
        try:
            p_idx = self.combo_pantalla.currentIndex()
            screens = QGuiApplication.screens()
            idx = p_idx if 0 <= p_idx < len(screens) else 0
            screen = screens[idx]

            pixmap = screen.grabWindow(0)
            self._procesar_pixmap_final(pixmap)
        finally:
            if mostrar_ventana:
                self.window().show()

    def _procesar_captura_area(self, area):
        x, y, w, h = area
        p_idx = self.combo_pantalla.currentIndex()
        screens = QGuiApplication.screens()
        idx = p_idx if 0 <= p_idx < len(screens) else 0
        screen = screens[idx]

        full_pix = getattr(self, '_desktop_pixmap_reciente', None)
        if full_pix is None or full_pix.isNull():
            full_pix = screen.grabWindow(0)

        # Recortar coordenadas relativas a la pantalla
        mx = screen.geometry().x()
        my = screen.geometry().y()
        rx = max(0, x - mx)
        ry = max(0, y - my)
        rw = min(full_pix.width() - rx, w)
        rh = min(full_pix.height() - ry, h)

        recorte = full_pix.copy(rx, ry, rw, rh)
        self._procesar_pixmap_final(recorte)

    def _procesar_pixmap_final(self, pixmap):
        if pixmap.isNull():
            QMessageBox.warning(self, "Error", "No se pudo obtener la captura de pantalla.")
            return

        self.ultima_pixmap = pixmap

        # Guardar archivo en disco
        fmt_idx = self.combo_formato.currentIndex()
        ext = "png" if fmt_idx == 0 else ("jpg" if fmt_idx == 1 else "bmp")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"captura_{ts}.{ext}"
        ruta_salida = self.manager.ruta_grabaciones / nombre_archivo

        pixmap.save(str(ruta_salida), ext.upper())
        self.ultimo_path = ruta_salida

        # Copiar al portapapeles si está seleccionado
        if self.chk_portapapeles.isChecked():
            QApplication.clipboard().setPixmap(pixmap)

        # Mostrar en previsualización
        self.lbl_empty_preview.hide()
        self.lbl_preview_img.show()
        scaled = pixmap.scaled(
            self.lbl_preview_img.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_preview_img.setPixmap(scaled)

        # Metadatos
        tam_kb = os.path.getsize(str(ruta_salida)) / 1024.0
        info_txt = f"✅ Guardado: {nombre_archivo}  •  Resolución: {pixmap.width()}×{pixmap.height()}  •  Tamaño: {tam_kb:.1f} KB"
        if self.chk_portapapeles.isChecked():
            info_txt += "  •  (Copiado al portapapeles)"
        self.lbl_info_captura.setText(info_txt)

        self.btn_copiar_portapapeles.setEnabled(True)
        self.btn_guardar_como.setEnabled(True)
        self.btn_abrir_visor.setEnabled(True)

        if "cargar_audios" in self.callbacks:
            self.callbacks["cargar_audios"]()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.ultima_pixmap and self.lbl_preview_img.isVisible():
            scaled = self.ultima_pixmap.scaled(
                self.lbl_preview_img.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_preview_img.setPixmap(scaled)

    def _copiar_al_portapapeles(self):
        if self.ultima_pixmap:
            QApplication.clipboard().setPixmap(self.ultima_pixmap)
            QMessageBox.information(self, "Portapapeles", "¡Imagen copiada al portapapeles del sistema!")

    def _guardar_como(self):
        if not self.ultima_pixmap:
            return
        ext_sug = self.ultimo_path.suffix if self.ultimo_path else ".png"
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Captura Como", str(Path.home() / f"captura{ext_sug}"),
            "Imágenes (*.png *.jpg *.bmp)"
        )
        if path:
            fmt = Path(path).suffix.replace(".", "").upper() or "PNG"
            self.ultima_pixmap.save(path, fmt)
            QMessageBox.information(self, "Guardado", f"Imagen guardada en:\n{path}")

    def _abrir_en_visor(self):
        if self.ultimo_path and self.ultimo_path.exists():
            if os.name == 'nt':
                os.startfile(str(self.ultimo_path))
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(self.ultimo_path)])

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#1E1E1E')
        bg_sec = colores.get('bg_secundario', '#2D2D2D')
        bg_terc = colores.get('bg_terciario', '#3D3D3D')
        acento = colores.get('acento', '#4A86E8')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        if hasattr(self, 'opts_frame'):
            self.opts_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 10px;")
        if hasattr(self, 'bot_frame'):
            self.bot_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 8px 14px;")

        combo_style = f"""
            QComboBox {{ background: {bg_terc}; color: white; border-radius: 6px; padding: 5px 10px; border: none; }}
            QComboBox QAbstractItemView {{ background: {bg_sec}; color: white; selection-background-color: {acento}; }}
        """
        self.combo_pantalla.setStyleSheet(combo_style)
        self.combo_retardo.setStyleSheet(combo_style)
        self.combo_formato.setStyleSheet(combo_style)
        self.btn_capturar_todo.setStyleSheet(f"background: {acento}; color: white; border-radius: 8px; padding: 10px 18px; border: none;")

    def cleanup(self):
        try:
            if hasattr(self, 'timer_countdown'):
                self.timer_countdown.stop()
        except Exception:
            pass
