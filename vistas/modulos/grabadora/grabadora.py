import os
import time
import numpy as np
import cv2
import platform
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QMessageBox, QInputDialog
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QImage, QPixmap

from .submodulos.grabadora_audio import GrabadoraAudioSubmodule
from .submodulos.grabadora_pantalla import GrabadoraPantallaSubmodule
from .submodulos.grabadora_webcam import GrabadoraWebcamSubmodule
from .submodulos.historial_grabaciones import HistorialGrabacionesSubmodule
from .submodulos.capturador_pantalla import CapturadorPantallaSubmodule
from .submodulos.area_selector import AreaSelector
from .utils.recorder_manager import RecorderManager
from vistas.utils.hardware_manager import get_hardware_manager


class TabGrabadora(QWidget):
    """Módulo Principal de Grabadora Multimedia con QTabWidget y 4 Submódulos Desacoplados"""
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.ruta_grabaciones = self.ruta_usuario / "grabaciones"
        self.ruta_grabaciones.mkdir(parents=True, exist_ok=True)
        
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#1E1E1E", "bg_secundario": "#2D2D2D", "bg_terciario": "#3D3D3D",
            "fg_principal": "#E0E0E0", "fg_secundario": "#A0A0A0", "acento": "#4A86E8",
            "acento_hover": "#6366F1", "error": "#E53935", "exito": "#43A047", "advertencia": "#FDD835"
        })
        
        self.manager = RecorderManager(self.ruta_grabaciones)
        self.hw_manager = get_hardware_manager()
        self.hw_manager.devices_changed.connect(self._refrescar_hardware)
        
        self.callbacks = {
            "toggle_audio": self.toggle_grabar_audio,
            "pause_audio": self.pause_audio,
            "reproducir_audio": self.reproducir_audio,
            "eliminar_audio": self.eliminar_audio,
            "renombrar_audio": self.renombrar_audio,
            "cargar_audios": self.cargar_lista_audio,
            "seleccionar_area": self.seleccionar_area,
            "toggle_video": self.toggle_grabar_video,
            "pause_video": self.pause_video,
            "toggle_completa": self.toggle_pantalla_completa,
            "get_dispositivos": self.hw_manager.get_inputs_strings,
            "get_pantallas": self.hw_manager.get_screens_strings
        }
        
        self.video_frames_buffer = []
        self.tiempo_inicio_video_perf = 0.0

        self.inicializar_ui()
        
        # Configurar Timers
        self.timer_audio = QTimer(self)
        self.timer_audio.timeout.connect(self._update_timer_audio)
        self.tiempo_inicio_audio = 0
        
        self.timer_video = QTimer(self)
        self.timer_video.timeout.connect(self._update_timer_video)
        self.tiempo_inicio_video = 0
        
        self.timer_frame_record = QTimer(self)
        self.timer_frame_record.timeout.connect(self._capturar_frame_loop)

        self.area_seleccionada = None
        self.timer_preview = QTimer(self)
        self.timer_preview.timeout.connect(self._run_preview_once)
        self.timer_preview.start(200)
        
        self.cargar_lista_audio()

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # TabWidget Superior
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont(self.font_family, 9))
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['acento']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)

        # Submódulos dinámicos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        extra_kwargs = {
            "callbacks": self.callbacks,
            "manager": self.manager
        }
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores, extra_kwargs)

        if self.tabs.count() == 0:
            self.tab_audio = GrabadoraAudioSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.tab_video = GrabadoraPantallaSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.tab_webcam = GrabadoraWebcamSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.tab_historial = HistorialGrabacionesSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.tab_captura = CapturadorPantallaSubmodule(self, self.context, self.manager, self.colores, self.callbacks)

            self.tabs.addTab(self.tab_audio, "🎙️ Grabadora Audio")
            self.tabs.addTab(self.tab_video, "🎬 Grabadora Pantalla")
            self.tabs.addTab(self.tab_webcam, "🎥 Grabadora Cámara")
            self.tabs.addTab(self.tab_historial, "📁 Historial Grabaciones")
            self.tabs.addTab(self.tab_captura, "📸 Captura de Pantalla")
        else:
            self.tab_audio = self.submod_instances.get("GrabadoraAudioSubmodule") or self.submod_instances.get("grabadoraaudiosubmodule")
            if not self.tab_audio:
                self.tab_audio = GrabadoraAudioSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.tab_video = self.submod_instances.get("GrabadoraPantallaSubmodule") or self.submod_instances.get("grabadorapantallasubmodule")
            if not self.tab_video:
                self.tab_video = GrabadoraPantallaSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.tab_webcam = self.submod_instances.get("GrabadoraWebcamSubmodule")
            self.tab_historial = self.submod_instances.get("HistorialGrabacionesSubmodule")
            self.tab_captura = self.submod_instances.get("CapturadorPantallaSubmodule")
            if not self.tab_captura:
                self.tab_captura = CapturadorPantallaSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
                self.tabs.addTab(self.tab_captura, "📸 Captura de Pantalla")

        # Proxy GUI para compatibilidad
        self.gui = self
        self.main_layout.addWidget(self.tabs)
        self._refrescar_hardware()

    def _refrescar_hardware(self):
        # Micrófonos
        self.tab_audio.combo_dispositivo.blockSignals(True)
        self.tab_audio.combo_dispositivo.clear()
        self.tab_audio.combo_dispositivo.addItems(self.hw_manager.get_inputs_strings())
        self.tab_audio.combo_dispositivo.blockSignals(False)
        
        # Pantallas
        self.tab_video.combo_pantalla.blockSignals(True)
        self.tab_video.combo_pantalla.clear()
        self.tab_video.combo_pantalla.addItems(self.hw_manager.get_screens_strings())
        self.tab_video.combo_pantalla.blockSignals(False)

    # --- CONTROL AUDIO ---
    def toggle_grabar_audio(self):
        if not self.manager.grabando_audio:
            idx_str = self.tab_audio.combo_dispositivo.currentText()
            try: idx = int(idx_str.split(":")[0])
            except: idx = None
            if self.manager.iniciar_audio(idx, self._update_audio_visual):
                self.tab_audio.btn_grabar_audio.setText("⏹️ Detener")
                self.tab_audio.btn_grabar_audio.setStyleSheet(f"background: {self.colores['error']}; color: white; padding: 10px 20px; border-radius: 8px; border: none; font-weight: bold;")
                self.tab_audio.btn_pausar_audio.setEnabled(True)
                self.tab_audio.lbl_status_audio.setText("🔴 Grabando voz...")
                self.tiempo_inicio_audio = time.time()
                self.timer_audio.start(1000)
            else:
                QMessageBox.warning(self, "Error", "No se pudo iniciar la grabación de audio.")
        else:
            nombre = self.manager.detener_audio()
            self.timer_audio.stop()
            self.tab_audio.btn_grabar_audio.setText("🎙️ Iniciar Grabación")
            self.tab_audio.btn_grabar_audio.setStyleSheet(f"background: {self.colores['exito']}; color: white; padding: 10px 20px; border-radius: 8px; border: none; font-weight: bold;")
            self.tab_audio.btn_pausar_audio.setEnabled(False)
            self.tab_audio.btn_pausar_audio.setText("⏸️ Pausar")
            self.tab_audio.lbl_status_audio.setText("Listo para grabar")
            self.tab_audio.lbl_tiempo_audio.setText("00:00:00")
            if nombre:
                QMessageBox.information(self, "Éxito", f"Audio guardado como:\n🎙️ {nombre}")
                self.cargar_lista_audio()

    def pause_audio(self):
        pausado = self.manager.toggle_pausa_audio()
        if pausado:
            self.tab_audio.btn_pausar_audio.setText("▶️ Reanudar")
            self.tab_audio.lbl_status_audio.setText("⏸️ En pausa")
        else:
            self.tab_audio.btn_pausar_audio.setText("⏸️ Pausar")
            self.tab_audio.lbl_status_audio.setText("🔴 Grabando voz...")

    def _update_audio_visual(self, data):
        try:
            if len(data) > 0:
                audio_mono = data[:, 0]
                chunk = audio_mono[-100:] if len(audio_mono) >= 100 else np.pad(audio_mono, (0, 100 - len(audio_mono)))
                x = np.arange(len(chunk))
                self.tab_audio.line_audio.set_data(x, chunk)
                self.tab_audio.ax_audio.set_xlim(0, len(chunk))
                self.tab_audio.canvas_plot.draw_idle()
        except Exception: pass

    def _update_timer_audio(self):
        if self.manager.grabando_audio and not self.manager.pausado_audio:
            elapsed = int(time.time() - self.tiempo_inicio_audio)
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60
            self.tab_audio.lbl_tiempo_audio.setText(f"{h:02d}:{m:02d}:{s:02d}")

    # --- CONTROL VIDEO PANTALLA ---
    def seleccionar_area(self):
        self.selector = AreaSelector(self._area_seleccionada_cb)
        self.selector.show()

    def _area_seleccionada_cb(self, x, y=None, w=None, h=None):
        if y is not None and w is not None and h is not None:
            if w > 10 and h > 10:
                self.area_seleccionada = (x, y, w, h)
                self.tab_video.chk_completa.setChecked(False)
                self.tab_video.lbl_status_video.setText(f"Región seleccionada ({w}x{h})")
                return
        elif hasattr(x, 'width') and hasattr(x, 'height'):
            if x.width() > 10 and x.height() > 10:
                self.area_seleccionada = (x.x(), x.y(), x.width(), x.height())
                self.tab_video.chk_completa.setChecked(False)
                self.tab_video.lbl_status_video.setText(f"Región seleccionada ({x.width()}x{x.height()})")
                return

        self.area_seleccionada = None
        self.tab_video.chk_completa.setChecked(True)

    def toggle_pantalla_completa(self, checked):
        if checked:
            self.area_seleccionada = None
            self.tab_video.lbl_status_video.setText("Pantalla completa activa")

    def toggle_grabar_video(self):
        if not self.manager.grabando_video:
            fps_map = {"15 FPS": 15, "30 FPS": 30, "60 FPS": 60}
            target_fps = fps_map.get(self.tab_video.combo_fps.currentText(), 30)

            self.manager.grabando_video = True
            self.manager.pausado_video = False
            self.video_frames_buffer = []
            self.tiempo_inicio_video_perf = time.perf_counter()
            self.tiempo_inicio_video = time.time()

            interval_ms = max(15, int(1000 / target_fps))
            self.timer_frame_record.start(interval_ms)
            self.timer_video.start(1000)

            self.tab_video.btn_grabar_video.setText("⏹️ Detener Grabación")
            self.tab_video.btn_grabar_video.setStyleSheet(f"background: {self.colores['error']}; color: white; padding: 10px 20px; border-radius: 8px; border: none; font-weight: bold;")
            self.tab_video.btn_pausar_video.setEnabled(True)
            self.tab_video.lbl_status_video.setText("🔴 Grabando pantalla...")
            self.tab_video.lbl_no_preview.hide()
            self.tab_video.lbl_preview.show()
        else:
            self.manager.grabando_video = False
            self.timer_frame_record.stop()
            self.timer_video.stop()

            total_dur = time.perf_counter() - self.tiempo_inicio_video_perf
            p_idx = self.tab_video.combo_pantalla.currentIndex()
            if p_idx < 0: p_idx = 0
            area = None if self.tab_video.chk_completa.isChecked() else self.area_seleccionada

            res = self.manager.guardar_video_frames(self.video_frames_buffer, total_dur, area, p_idx)
            self.video_frames_buffer.clear()

            self.tab_video.btn_grabar_video.setText("🎥 Iniciar Grabación de Pantalla")
            self.tab_video.btn_grabar_video.setStyleSheet(f"background: {self.colores['exito']}; color: white; padding: 10px 20px; border-radius: 8px; border: none; font-weight: bold;")
            self.tab_video.btn_pausar_video.setEnabled(False)
            self.tab_video.lbl_status_video.setText("Listo")
            self.tab_video.lbl_tiempo_video.setText("00:00:00")
            if self.isVisible():
                QMessageBox.information(self, "Éxito", res)
            self.cargar_lista_audio()

    def _capturar_frame_loop(self):
        if self.manager.grabando_video and not self.manager.pausado_video:
            p_idx = self.tab_video.combo_pantalla.currentIndex()
            if p_idx < 0: p_idx = 0
            area = None if self.tab_video.chk_completa.isChecked() else self.area_seleccionada
            frame = self.manager.capturar_frame_actual(area, p_idx)
            if frame is not None:
                self.video_frames_buffer.append(frame)
                self._update_video_frame(frame)

    def pause_video(self):
        pausado = self.manager.toggle_pausa_video()
        if pausado:
            self.tab_video.btn_pausar_video.setText("▶️ Reanudar")
            self.tab_video.lbl_status_video.setText("⏸️ En pausa")
        else:
            self.tab_video.btn_pausar_video.setText("⏸️ Pausar")
            self.tab_video.lbl_status_video.setText("🔴 Grabando pantalla...")

    def _update_video_frame(self, frame):
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
            pix = QPixmap.fromImage(qimg).scaled(self.tab_video.lbl_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.tab_video.lbl_preview.setPixmap(pix)
        except Exception: pass

    def _update_timer_video(self):
        if self.manager.grabando_video and not self.manager.pausado_video:
            elapsed = int(time.time() - self.tiempo_inicio_video)
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60
            self.tab_video.lbl_tiempo_video.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def _run_preview_once(self):
        if (not self.manager.grabando_video and hasattr(self, 'tab_video') and 
            hasattr(self, 'tabs') and self.tabs.currentWidget() == self.tab_video and 
            self.tab_video.lbl_preview.isVisible()):
            p_idx = self.tab_video.combo_pantalla.currentIndex()
            if p_idx < 0: p_idx = 0
            area = None if self.tab_video.chk_completa.isChecked() else self.area_seleccionada
            frame = self.manager.capturar_frame_actual(area, p_idx)
            if frame is not None:
                self._update_video_frame(frame)

    # --- LISTA Y HISTORIAL ---
    def cargar_lista_audio(self):
        self.tab_historial.list_audio.clear()
        if self.ruta_grabaciones.exists():
            for f in sorted(os.listdir(self.ruta_grabaciones), reverse=True):
                ext = f.lower()
                if ext.endswith(('.wav', '.mp3', '.mp4', '.png', '.jpg')):
                    icon = "🎙️" if ext.endswith(('.wav', '.mp3')) else ("📷" if ext.endswith(('.png', '.jpg')) else "🎬")
                    self.tab_historial.list_audio.addItem(f"{icon} {f}")

    def reproducir_audio(self):
        item = self.tab_historial.list_audio.currentItem()
        if item:
            nombre = item.text().replace("🎙️ ", "").replace("🎬 ", "").replace("📷 ", "").strip()
            path = self.ruta_grabaciones / nombre
            if path.exists():
                if os.name == 'nt': os.startfile(str(path))

    def eliminar_audio(self):
        item = self.tab_historial.list_audio.currentItem()
        if item:
            nombre = item.text().replace("🎙️ ", "").replace("🎬 ", "").replace("📷 ", "").strip()
            path = self.ruta_grabaciones / nombre
            if path.exists():
                res = QMessageBox.question(self, "Eliminar", f"¿Seguro que deseas eliminar '{nombre}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if res == QMessageBox.StandardButton.Yes:
                    path.unlink()
                    self.cargar_lista_audio()

    def renombrar_audio(self):
        item = self.tab_historial.list_audio.currentItem()
        if item:
            nombre = item.text().replace("🎙️ ", "").replace("🎬 ", "").replace("📷 ", "").strip()
            path = self.ruta_grabaciones / nombre
            if path.exists():
                nuevo, ok = QInputDialog.getText(self, "Renombrar", "Nuevo nombre:", text=path.stem)
                if ok and nuevo.strip():
                    n_path = self.ruta_grabaciones / f"{nuevo.strip()}{path.suffix}"
                    path.rename(n_path)
                    self.cargar_lista_audio()

    def actualizar_tema(self, colores: dict):
        """Sincroniza y propaga el tema visual a todos los submódulos activos de la grabadora."""
        self.colores = colores
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores.get('bg_principal', '#1E1E1E')};
            }}
            QTabBar::tab {{
                background: {self.colores.get('bg_secundario', '#2D2D2D')};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores.get('acento', '#4A86E8')};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)

        submodulos = [
            getattr(self, 'tab_audio', None),
            getattr(self, 'tab_video', None),
            getattr(self, 'tab_webcam', None),
            getattr(self, 'tab_historial', None),
            getattr(self, 'tab_captura', None),
        ]
        for sub in submodulos:
            if sub and hasattr(sub, 'actualizar_tema'):
                try:
                    sub.actualizar_tema(colores)
                except Exception as e:
                    print(f"[TabGrabadora] Error actualizando tema en {sub.__class__.__name__}: {e}")

    def cleanup(self):
        """Libera de forma ordenada los recursos de grabación, timers, streams y hardware."""
        # Detener timers
        for t in [getattr(self, 'timer_preview', None), getattr(self, 'timer_audio', None), 
                  getattr(self, 'timer_video', None), getattr(self, 'timer_frame_record', None)]:
            if t and hasattr(t, 'stop'):
                try: t.stop()
                except Exception: pass

        # Detener grabaciones si estaban activas
        try:
            if hasattr(self, 'manager'):
                if getattr(self.manager, 'grabando_audio', False):
                    self.manager.detener_audio()
                if getattr(self.manager, 'grabando_video', False):
                    self.manager.grabando_video = False
                if getattr(self.manager, 'grabando_webcam', False):
                    self.manager.detener_webcam_video()
        except Exception as e:
            print(f"[TabGrabadora] Error en manager al hacer cleanup: {e}")

        # Desconectar hardware manager
        try:
            if hasattr(self, 'hw_manager') and hasattr(self, '_refrescar_hardware'):
                self.hw_manager.devices_changed.disconnect(self._refrescar_hardware)
        except Exception:
            pass

        # Cleanup en submódulos
        for sub in [getattr(self, 'tab_audio', None), getattr(self, 'tab_webcam', None), getattr(self, 'tab_captura', None)]:
            if sub and hasattr(sub, 'cleanup'):
                try: sub.cleanup()
                except Exception: pass

