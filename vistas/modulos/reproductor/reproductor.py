import os
import ctypes
import string
import platform
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaPlayer

from .submodulos.reproductor_multimedia import ReproductorMultimediaSubmodule
from .submodulos.descargas_snaptube import DescargasSnaptubeSubmodule
from .submodulos.listas_reproduccion import ListasReproduccionSubmodule
from .submodulos.radio_streaming import RadioStreamingSubmodule
from .submodulos.television_online import TelevisionOnlineSubmodule
from .submodulos.ecualizador_efectos import EcualizadorEfectosSubmodule
from .utils.player_manager import PlayerManager
from vistas.utils.hardware_manager import get_hardware_manager

try:
    from .utils.reproductor_logger import ReproductorLogger
except Exception:
    class ReproductorLogger:
        @staticmethod
        def log(n, m): pass
        @staticmethod
        def info(m): pass
        @staticmethod
        def warning(m): pass
        @staticmethod
        def error(m): pass


class TabReproductor(QWidget):
    """Módulo Principal de Reproductor Multimedia con QTabWidget y 4 Submódulos Desacoplados"""
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.save_dir = self.ruta_usuario / "descargas"
        os.makedirs(self.save_dir, exist_ok=True)
        
        default_colores = {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }
        app_col = getattr(getattr(context, "app", None), "COLORES", None) or {}
        self.colores = {**default_colores, **(app_col if isinstance(app_col, dict) else {})}
        
        self.manager = PlayerManager()
        
        self.callbacks = {
            "toggle_play": self.toggle_play,
            "cambiar_volumen": self.cambiar_volumen,
            "reproducir_archivo": self.reproducir_local,
            "reproducir_directo": self.reproducir_directo,
            "seek_tiempo": self.manager.set_position,
            "skip_tiempo": self.manager.saltar_tiempo,
            "cambiar_dispositivo": self.manager.set_audio_device,
            "modo_cine": self.toggle_fullscreen
        }

        self.inicializar_ui()
        
        # Hardware Manager Centralizado
        self.hw_manager = get_hardware_manager()
        self.hw_manager.devices_changed.connect(self._refrescar_hardware_audio)
        self._refrescar_hardware_audio()

        self.manager.posicion_cambiada.connect(self._actualizar_posicion)
        self.manager.duracion_cambiada.connect(self._actualizar_duracion)
        self.manager.estado_cambiado.connect(self._on_estado_cambiado)
        self.manager.status_cambiado.connect(self._on_status_cambiado)
        self.manager.error_ocurrido.connect(self._on_error_ocurrido)
        
        self._is_fullscreen = False

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
            self.submod_player = ReproductorMultimediaSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.submod_snaptube = DescargasSnaptubeSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.submod_playlists = ListasReproduccionSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.submod_radio = RadioStreamingSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.submod_tv = TelevisionOnlineSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.submod_eq = EcualizadorEfectosSubmodule(self, self.context, self.manager, self.colores, self.callbacks)

            self.tabs.addTab(self.submod_player, "🎬 Reproductor ARK")
            self.tabs.addTab(self.submod_snaptube, "🔍 Buscador & Descargas")
            self.tabs.addTab(self.submod_playlists, "🎵 Playlists & Biblioteca")
            self.tabs.addTab(self.submod_radio, "📻 Radio Online")
            self.tabs.addTab(self.submod_tv, "📺 Televisión Online")
            self.tabs.addTab(self.submod_eq, "🎛️ Ecualizador & Efectos")
        else:
            self.submod_player = self.submod_instances.get("ReproductorMultimediaSubmodule") or self.submod_instances.get("reproductormultimediasubmodule")
            if not self.submod_player:
                self.submod_player = ReproductorMultimediaSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.submod_snaptube = self.submod_instances.get("DescargasSnaptubeSubmodule")
            self.submod_playlists = self.submod_instances.get("ListasReproduccionSubmodule")
            self.submod_radio = self.submod_instances.get("RadioStreamingSubmodule")
            self.submod_tv = self.submod_instances.get("TelevisionOnlineSubmodule")
            self.submod_eq = self.submod_instances.get("EcualizadorEfectosSubmodule")
            if not self.submod_eq:
                self.submod_eq = EcualizadorEfectosSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
                self.tabs.addTab(self.submod_eq, "🎛️ Ecualizador & Efectos")

        self.gui = self.submod_player # Alias para compatibilidad
        self.main_layout.addWidget(self.tabs)

    def _refrescar_hardware_audio(self):
        """Refresca la lista de parlantes usando el HardwareManager central"""
        self.submod_player.cb_audio.blockSignals(True)
        prev = self.submod_player.cb_audio.currentText()
        self.submod_player.cb_audio.clear()
        self.submod_player.cb_audio.addItems(self.hw_manager.get_outputs_strings())
        idx = self.submod_player.cb_audio.findText(prev)
        if idx >= 0:
            self.submod_player.cb_audio.setCurrentIndex(idx)
        self.submod_player.cb_audio.blockSignals(False)

        current = self.submod_player.cb_audio.currentText()
        if current:
            self.manager.set_audio_device(current)

    def reproducir_directo(self, path, titulo_radio=None, es_video=False):
        msg = f"[Reproducir Directo] Solicitud: '{path}' | Título: {titulo_radio} | es_video: {es_video}"
        ReproductorLogger.info(f"TabReproductor: {msg}")

        self.manager.detener_audio()
        self.manager.detener_video()

        # Feedback visual inmediato: indicando al usuario que la conexión/carga está en curso
        if hasattr(self, "submod_player") and hasattr(self.submod_player, "btn_play"):
            self.submod_player.btn_play.setText("⏳ CONECTANDO...")
            self.submod_player.btn_play.setStyleSheet(f"background-color: {self.colores.get('advertencia', '#FBBF24')}; color: black; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")

        p_low = path.lower()
        is_vid = (
            es_video or 
            p_low.endswith(('.mp4', '.avi', '.mkv', '.mov', '.webm', '.m3u8')) or 
            '.m3u8' in p_low or 
            ('/m3u8' in p_low)
        )
        nombre_mostrar = titulo_radio or os.path.basename(path)
        
        if is_vid:
            if self.submod_player.video_widget is None:
                from PyQt6.QtMultimediaWidgets import QVideoWidget
                from PyQt6.QtWidgets import QSizePolicy
                self.submod_player.video_widget = QVideoWidget()
                self.submod_player.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                self.submod_player.video_widget.setMinimumSize(100, 100)
                self.submod_player.video_widget.setStyleSheet("background-color: black;")
                self.submod_player.v_lay.addWidget(self.submod_player.video_widget)

            self.submod_player.lbl_no_media.hide()
            self.submod_player.video_widget.show()
            self.manager.cargar_video(path, self.submod_player.video_widget)
            self.manager.reproducir_video()
            self.submod_player.lbl_current_title.setText(nombre_mostrar)
        else:
            if self.submod_player.video_widget:
                self.submod_player.video_widget.hide()
            acento = self.colores.get('acento', '#6366F1')
            self.submod_player.lbl_no_media.setText(f"""
                <div style='text-align: center;'>
                    <span style='font-size: 32px;'>🎶</span><br><br>
                    <span style='font-size: 16px; font-weight: bold; color: {acento}; letter-spacing: 1px;'>CONECTANDO Y REPRODUCIENDO</span><br><br>
                    <span style='font-size: 13px; color: white; font-weight: 500;'>{nombre_mostrar}</span>
                </div>
            """)
            self.submod_player.lbl_no_media.show()
            self.manager.cargar_audio(path)
            self.manager.reproducir_audio()
            self.submod_player.lbl_current_title.setText(nombre_mostrar)

        if hasattr(self.submod_player, "slider_vol"):
            self.cambiar_volumen(self.submod_player.slider_vol.value())

        self.tabs.setCurrentIndex(0) # Cambiar al reproductor principal

    def _on_status_cambiado(self, status):
        """Maneja los cambios de buffer/conexión y actualiza el botón y aviso visual"""
        if not hasattr(self, "submod_player") or not hasattr(self.submod_player, "btn_play"):
            return
        
        status_name = str(status).split(".")[-1]
        ReproductorLogger.info(f"TabReproductor: [UI MediaStatus] {status_name}")

        acento = self.colores.get('acento', '#6366F1')
        adv = self.colores.get('advertencia', '#FBBF24')
        err_col = self.colores.get('error', '#F87171')

        p = self.manager._activo()
        state = p.playbackState() if p else QMediaPlayer.PlaybackState.StoppedState

        # Si el usuario ha pausado el audio, NUNCA sobreescribir el botón con "BUFFERING"
        if state == QMediaPlayer.PlaybackState.PausedState:
            self.submod_player.btn_play.setText("▶ REANUDAR")
            self.submod_player.btn_play.setStyleSheet(f"background-color: {acento}; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
            return

        if status == QMediaPlayer.MediaStatus.LoadingMedia:
            self.submod_player.btn_play.setText("⏳ CONECTANDO...")
            self.submod_player.btn_play.setStyleSheet(f"background-color: {adv}; color: black; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
        elif status == QMediaPlayer.MediaStatus.BufferingMedia:
            if state == QMediaPlayer.PlaybackState.PlayingState:
                self.submod_player.btn_play.setText("⏳ BUFFERING (⏸)")
                self.submod_player.btn_play.setStyleSheet(f"background-color: {adv}; color: black; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
            else:
                self.submod_player.btn_play.setText("⏳ BUFFERING...")
                self.submod_player.btn_play.setStyleSheet(f"background-color: {adv}; color: black; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
        elif status in [QMediaPlayer.MediaStatus.BufferedMedia, QMediaPlayer.MediaStatus.LoadedMedia]:
            if state == QMediaPlayer.PlaybackState.PlayingState:
                self.submod_player.btn_play.setText("⏸ PAUSAR")
                self.submod_player.btn_play.setStyleSheet(f"background-color: {acento}; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
            elif state == QMediaPlayer.PlaybackState.PausedState:
                self.submod_player.btn_play.setText("▶ REANUDAR")
                self.submod_player.btn_play.setStyleSheet(f"background-color: {acento}; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
            else:
                self.submod_player.btn_play.setText("▶ REPRODUCIR")
                self.submod_player.btn_play.setStyleSheet(f"background-color: {acento}; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.submod_player.btn_play.setText("❌ ERROR DE MEDIO")
            self.submod_player.btn_play.setStyleSheet(f"background-color: {err_col}; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")

    def _on_estado_cambiado(self, state):
        if hasattr(self, "submod_player") and hasattr(self.submod_player, "btn_play"):
            acento = self.colores.get('acento', '#6366F1')
            if state == QMediaPlayer.PlaybackState.PlayingState:
                self.submod_player.btn_play.setText("⏸ PAUSAR")
                self.submod_player.btn_play.setStyleSheet(f"background-color: {acento}; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
            elif state == QMediaPlayer.PlaybackState.PausedState:
                self.submod_player.btn_play.setText("▶ REANUDAR")
                self.submod_player.btn_play.setStyleSheet(f"background-color: {acento}; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
            else:
                self.submod_player.btn_play.setText("▶ REPRODUCIR")
                self.submod_player.btn_play.setStyleSheet(f"background-color: {acento}; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")

    def _on_error_ocurrido(self, err_msg):
        ReproductorLogger.error(f"TabReproductor: Notificación de error recibida: {err_msg}")
        if hasattr(self, "submod_player") and hasattr(self.submod_player, "lbl_current_title"):
            self.submod_player.lbl_current_title.setText(f"❌ {err_msg}")

    def reproducir_local(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Abrir Multimedia (Audio o Video)", str(Path.home() / "Music"),
            "Archivos Multimedia (*.mp3 *.wav *.ogg *.flac *.m4a *.mp4 *.avi *.mkv *.mov);;Todos los archivos (*.*)"
        )
        if f:
            self.reproducir_directo(f)

    def toggle_play(self):
        if not self.manager.archivo_audio and not self.manager.archivo_video:
            self.reproducir_local()
            return

        p = self.manager._activo()
        if not p:
            return

        state = p.playbackState()
        status = p.mediaStatus()
        msg = f"[Toggle Play Clic] Estado: {state} | Status: {status} | Archivo: {self.manager.archivo_audio or self.manager.archivo_video}"
        ReproductorLogger.info(f"TabReproductor: {msg}")

        # Ejecutar inmediatamente la acción de play/pause sin bloqueos
        if state == QMediaPlayer.PlaybackState.PlayingState:
            p.pause()
        else:
            p.play()

    def cambiar_volumen(self, v):
        self.manager.set_volumen_audio(v / 100.0)
        self.manager.set_volumen_video(v / 100.0)

    def _format_ms(self, ms):
        s = ms // 1000
        m = s // 60
        s = s % 60
        h = m // 60
        m = m % 60
        if h > 0: return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _actualizar_posicion(self, pos):
        is_down = False
        if hasattr(self, "submod_player") and hasattr(self.submod_player, "slider_seek"):
            is_down = self.submod_player.slider_seek.isSliderDown() or getattr(self.submod_player, "is_seeking", False)
        if not is_down and hasattr(self, "submod_player") and hasattr(self.submod_player, "slider_seek"):
            self.submod_player.slider_seek.blockSignals(True)
            self.submod_player.slider_seek.setValue(pos)
            self.submod_player.slider_seek.blockSignals(False)
            dur = self.submod_player.slider_seek.maximum()
            self.submod_player.lbl_time.setText(f"{self._format_ms(pos)} / {self._format_ms(dur)}")

    def _actualizar_duracion(self, dur):
        self.submod_player.slider_seek.setRange(0, dur)

    def toggle_fullscreen(self):
        if hasattr(self.window(), "toggle_pantalla_completa"):
            self.window().toggle_pantalla_completa()
            return
        if not self._is_fullscreen:
            self.window().showFullScreen()
            self._is_fullscreen = True
        else:
            self.window().showNormal()
            self._is_fullscreen = False

    def toggle_fullscreen_mode(self, is_fullscreen):
        """Oculta o muestra la barra de pestañas de submódulos en pantalla completa."""
        if hasattr(self, "tabs") and hasattr(self.tabs, "tabBar"):
            self.tabs.tabBar().setVisible(not is_fullscreen)

    def actualizar_tema(self, colores: dict):
        """Sincroniza y propaga el tema visual a todos los submódulos activos."""
        self.colores = colores
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores.get('bg_principal', '#121218')};
            }}
            QTabBar::tab {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)

        submodulos = [
            getattr(self, 'submod_player', None),
            getattr(self, 'submod_snaptube', None),
            getattr(self, 'submod_playlists', None),
            getattr(self, 'submod_radio', None),
            getattr(self, 'submod_tv', None),
            getattr(self, 'submod_eq', None),
        ]
        for sub in submodulos:
            if sub and hasattr(sub, 'actualizar_tema'):
                try:
                    sub.actualizar_tema(colores)
                except Exception as e:
                    ReproductorLogger.warning(f"Error actualizando tema en submódulo {sub.__class__.__name__}: {e}")

    def cleanup(self):
        """Libera de forma ordenada los recursos de audio, video, hardware y temporizadores."""
        try:
            if hasattr(self, 'manager'):
                self.manager.detener_audio()
                self.manager.detener_video()
        except Exception as e:
            ReproductorLogger.warning(f"TabReproductor.cleanup error deteniendo playback: {e}")

        try:
            if hasattr(self, 'hw_manager') and hasattr(self, '_refrescar_hardware_audio'):
                self.hw_manager.devices_changed.disconnect(self._refrescar_hardware_audio)
        except Exception:
            pass

        try:
            if hasattr(self, 'submod_eq') and hasattr(self.submod_eq, 'cleanup'):
                self.submod_eq.cleanup()
        except Exception as e:
            ReproductorLogger.warning(f"TabReproductor.cleanup error en ecualizador: {e}")

