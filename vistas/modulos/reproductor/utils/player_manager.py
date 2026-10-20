import os
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices, QAudioDevice
from PyQt6.QtCore import QUrl, pyqtSignal, QObject

try:
    from .reproductor_logger import ReproductorLogger
except Exception:
    try:
        from vistas.modulos.reproductor.utils.reproductor_logger import ReproductorLogger
    except Exception:
        class ReproductorLogger:
            @staticmethod
            def log(nivel, msg): pass
            @staticmethod
            def info(msg): pass
            @staticmethod
            def warning(msg): pass
            @staticmethod
            def error(msg): pass

class PlayerManager(QObject):
    # Señales para comunicar con la GUI
    posicion_cambiada = pyqtSignal(int)
    duracion_cambiada = pyqtSignal(int)
    estado_cambiado = pyqtSignal(QMediaPlayer.PlaybackState)
    status_cambiado = pyqtSignal(QMediaPlayer.MediaStatus)
    error_ocurrido = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        
        self.audio_player = None
        self.audio_output = None
        self.video_player = None
        self.video_output = None

        # Asegurar registro de rutas para plugins multimedia (FFmpeg y Windows Media Foundation)
        try:
            from PyQt6.QtCore import QCoreApplication
            import sys
            app_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.abspath(".")
            candidate_plugin_dirs = [
                os.path.join(app_dir, "PyQt6", "Qt6", "plugins"),
                os.path.join(app_dir, "plugins"),
                r"C:\Users\Yuiga_Nariyuki\Documents\Multitool\PyQt6\Qt6\plugins",
                r"C:\Users\Yuiga_Nariyuki\Documents\Multitool\plugins",
                r"C:\Users\Yuiga_Nariyuki\AppData\Local\Programs\Python\Python312\Lib\site-packages\PyQt6\Qt6\plugins"
            ]
            for cpd in candidate_plugin_dirs:
                if os.path.isdir(cpd):
                    QCoreApplication.addLibraryPath(cpd)
                    try:
                        os.add_dll_directory(cpd)
                    except Exception:
                        pass
            try:
                os.add_dll_directory(app_dir)
                os.add_dll_directory(r"C:\Users\Yuiga_Nariyuki\Documents\Multitool")
            except Exception:
                pass

            lib_paths = QCoreApplication.libraryPaths()
            ReproductorLogger.info(f"PlayerManager: Rutas de plugins Qt registradas: {lib_paths}")
        except Exception as e:
            ReproductorLogger.error(f"PlayerManager: Error registrando rutas de plugins: {e}")
        
        try:
            # Dispositivo por defecto
            default_dev = QMediaDevices.defaultAudioOutput()
            dev_name = default_dev.description() if default_dev and not default_dev.isNull() else "Dispositivo del Sistema"

            # Audio Player
            self.audio_player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            if default_dev and not default_dev.isNull():
                self.audio_output.setDevice(default_dev)
            self.audio_output.setVolume(0.85)
            self.audio_output.setMuted(False)
            self.audio_player.setAudioOutput(self.audio_output)
            
            # Conectar señales básicas audio
            self.audio_player.positionChanged.connect(self._on_audio_pos)
            self.audio_player.durationChanged.connect(self._on_audio_dur)
            self.audio_player.playbackStateChanged.connect(self._on_audio_state)
            self.audio_player.mediaStatusChanged.connect(self._on_audio_status)
            self.audio_player.errorOccurred.connect(self._on_audio_error)
            
            ReproductorLogger.info(f"PlayerManager: AudioPlayer listo con salida: '{dev_name}', Vol: 85%")
        except Exception as e:
            ReproductorLogger.error(f"PlayerManager: Error inicializando Audio: {e}")
        
        try:
            # Video Player
            self.video_player = QMediaPlayer()
            self.video_output = QAudioOutput()
            if default_dev and not default_dev.isNull():
                self.video_output.setDevice(default_dev)
            self.video_output.setVolume(0.85)
            self.video_output.setMuted(False)
            self.video_player.setAudioOutput(self.video_output)
            
            # Conectar señales video
            self.video_player.positionChanged.connect(self._on_video_pos)
            self.video_player.durationChanged.connect(self._on_video_dur)
            self.video_player.playbackStateChanged.connect(self._on_video_state)
            self.video_player.mediaStatusChanged.connect(self._on_video_status)
            self.video_player.errorOccurred.connect(self._on_video_error)
        except Exception as e:
            ReproductorLogger.error(f"PlayerManager: Error inicializando Video: {e}")
        
        self.archivo_audio = None
        self.archivo_video = None

        # Mapa de dispositivos de audio
        self.audio_devices = {}
        self.refrescar_devices()

    def _on_audio_pos(self, pos):
        if self.archivo_video is None:
            self.posicion_cambiada.emit(pos)

    def _on_audio_dur(self, dur):
        if self.archivo_video is None:
            ReproductorLogger.info(f"PlayerManager: [Audio Duración] {dur} ms ({dur // 1000}s)")
            self.duracion_cambiada.emit(dur)

    def _on_audio_state(self, state):
        state_name = str(state).split(".")[-1]
        ReproductorLogger.info(f"PlayerManager: [Audio Estado] PlaybackState -> {state_name}")
        if self.archivo_video is None:
            self.estado_cambiado.emit(state)

    def _on_audio_status(self, status):
        status_name = str(status).split(".")[-1]
        ReproductorLogger.info(f"PlayerManager: [Audio Estado] MediaStatus -> {status_name}")
        if self.archivo_video is None:
            self.status_cambiado.emit(status)

    def _on_audio_error(self, err, msg_err):
        err_msg = f"[Audio ERROR] Fallo de reproducción {err}: {msg_err} | Fuente: {self.archivo_audio}"
        ReproductorLogger.error(f"PlayerManager: {err_msg}")
        if self.archivo_video is None:
            self.error_ocurrido.emit(err_msg)

    def _on_video_pos(self, pos):
        if self.archivo_video is not None:
            self.posicion_cambiada.emit(pos)

    def _on_video_dur(self, dur):
        if self.archivo_video is not None:
            ReproductorLogger.info(f"PlayerManager: [Video Duración] {dur} ms ({dur // 1000}s)")
            self.duracion_cambiada.emit(dur)

    def _on_video_state(self, state):
        state_name = str(state).split(".")[-1]
        ReproductorLogger.info(f"PlayerManager: [Video Estado] PlaybackState -> {state_name}")
        if self.archivo_video is not None:
            self.estado_cambiado.emit(state)

    def _on_video_status(self, status):
        status_name = str(status).split(".")[-1]
        ReproductorLogger.info(f"PlayerManager: [Video Estado] MediaStatus -> {status_name}")
        if self.archivo_video is not None:
            self.status_cambiado.emit(status)

    def _on_video_error(self, err, msg_err):
        err_msg = f"[Video ERROR] Fallo de vídeo {err}: {msg_err} | Fuente: {self.archivo_video}"
        ReproductorLogger.error(f"PlayerManager: {err_msg}")
        if self.archivo_video is not None:
            self.error_ocurrido.emit(err_msg)

    def refrescar_devices(self):
        self.audio_devices.clear()
        for dev in QMediaDevices.audioOutputs():
            self.audio_devices[dev.description()] = dev

    def get_audio_devices(self):
        self.refrescar_devices()
        return list(self.audio_devices.keys())

    def set_audio_device(self, nombre):
        if not nombre:
            return
        self.refrescar_devices()
        nombre_limpio = nombre
        for prefix in ["🔊 ", "🎧 ", "🔈 ", "🎙️ "]:
            if nombre_limpio.startswith(prefix):
                nombre_limpio = nombre_limpio[len(prefix):]
        if ": " in nombre_limpio:
            nombre_limpio = nombre_limpio.split(": ", 1)[1]

        dev = self.audio_devices.get(nombre) or self.audio_devices.get(nombre_limpio)
        if not dev:
            for d in QMediaDevices.audioOutputs():
                if d.description().lower() in nombre_limpio.lower() or nombre_limpio.lower() in d.description().lower():
                    dev = d
                    break
        if not dev:
            dev = QMediaDevices.defaultAudioOutput()

        if dev and not dev.isNull():
            dev_desc = dev.description()
            if self.audio_output:
                try:
                    curr_dev = self.audio_output.device()
                    if not curr_dev or curr_dev.id() != dev.id():
                        ReproductorLogger.info(f"PlayerManager: Conmutando salida de audio a '{dev_desc}'")
                        self.audio_output.setDevice(dev)
                except Exception:
                    self.audio_output.setDevice(dev)
                if self.audio_output.volume() <= 0.05:
                    self.audio_output.setVolume(0.85)
                self.audio_output.setMuted(False)
            if self.video_output:
                try:
                    curr_vdev = self.video_output.device()
                    if not curr_vdev or curr_vdev.id() != dev.id():
                        self.video_output.setDevice(dev)
                except Exception:
                    self.video_output.setDevice(dev)
                if self.video_output.volume() <= 0.05:
                    self.video_output.setVolume(0.85)
                self.video_output.setMuted(False)
            ReproductorLogger.info(f"PlayerManager: [Audio Output] Dispositivo activo fijado a: '{dev_desc}'")
        else:
            ReproductorLogger.warning(f"PlayerManager: [Audio Output Advertencia] No se encontró dispositivo para '{nombre}'")

    def _activo(self):
        if self.archivo_video is not None:
            return self.video_player
        return self.audio_player

    def set_position(self, ms):
        p = self._activo()
        if p:
            ReproductorLogger.info(f"PlayerManager: [Seek] Posición cambiada a {ms} ms ({ms // 1000}s)")
            p.setPosition(ms)

    def saltar_tiempo(self, ms_offset):
        p = self._activo()
        if p:
            nueva = max(0, p.position() + ms_offset)
            ReproductorLogger.info(f"PlayerManager: [Skip] Offset {ms_offset} ms -> Posición: {nueva} ms")
            p.setPosition(nueva)

    # --- Métodos de Audio ---
    def cargar_audio(self, ruta):
        try:
            self.archivo_video = None
            self.archivo_audio = ruta
            if self.video_player:
                self.video_player.stop()

            # Diagnóstico de salida de audio
            dev_name = self.audio_output.device().description() if self.audio_output and self.audio_output.device() else "Default"
            vol = int(self.audio_output.volume() * 100) if self.audio_output else 0
            muted = self.audio_output.isMuted() if self.audio_output else False
            
            ReproductorLogger.info(f"PlayerManager: [Cargar Audio] Asignando fuente: '{ruta}' | Salida: {dev_name} | Vol: {vol}% | Muted: {muted}")

            if ruta.startswith("http://") or ruta.startswith("https://"):
                self.audio_player.setSource(QUrl(ruta))
            else:
                self.audio_player.setSource(QUrl.fromLocalFile(ruta))
            return True
        except Exception as e:
            err_msg = f"[Cargar Audio ERROR] Falló al cargar '{ruta}': {e}"
            ReproductorLogger.error(f"PlayerManager: {err_msg}")
            self.error_ocurrido.emit(err_msg)
            return False

    def reproducir_audio(self):
        if self.audio_player:
            # Asegurar volumen y desmutear
            if self.audio_output:
                if self.audio_output.isMuted():
                    self.audio_output.setMuted(False)
                if self.audio_output.volume() <= 0.05:
                    self.audio_output.setVolume(0.85)
                # Reconfirmar asignación de salida
                if self.audio_player.audioOutput() != self.audio_output:
                    self.audio_player.setAudioOutput(self.audio_output)
            vol = int(self.audio_output.volume() * 100) if self.audio_output else 0
            ReproductorLogger.info(f"PlayerManager: [Reproducir Audio] play() | Fuente: {self.archivo_audio} | Vol: {vol}%")
            self.audio_player.play()

    def pausar_audio(self):
        if self.audio_player:
            ReproductorLogger.info(f"PlayerManager: [Pausar Audio] pause() | Fuente: {self.archivo_audio}")
            self.audio_player.pause()

    def detener_audio(self):
        if self.audio_player:
            ReproductorLogger.info(f"PlayerManager: [Detener Audio] stop()")
            self.audio_player.stop()

    def set_volumen_audio(self, vol):
        if self.audio_output:
            self.audio_output.setVolume(vol)
            self.audio_output.setMuted(False)
            ReproductorLogger.info(f"PlayerManager: [Volumen Audio] Fijado a {int(vol * 100)}%")

    # --- Métodos de Video ---
    def cargar_video(self, ruta, video_widget):
        try:
            self.archivo_audio = None
            self.archivo_video = ruta
            if self.audio_player:
                self.audio_player.stop()
            self.video_player.setVideoOutput(video_widget)
            
            dev_name = self.video_output.device().description() if self.video_output and self.video_output.device() else "Default"
            vol = int(self.video_output.volume() * 100) if self.video_output else 0
            ReproductorLogger.info(f"PlayerManager: [Cargar Video] Asignando fuente: '{ruta}' | Salida: {dev_name} | Vol: {vol}%")

            if ruta.startswith("http://") or ruta.startswith("https://"):
                self.video_player.setSource(QUrl(ruta))
            else:
                self.video_player.setSource(QUrl.fromLocalFile(ruta))
            return True
        except Exception as e:
            err_msg = f"[Cargar Video ERROR] Falló al cargar vídeo '{ruta}': {e}"
            ReproductorLogger.error(f"PlayerManager: {err_msg}")
            self.error_ocurrido.emit(err_msg)
            return False

    def reproducir_video(self):
        if self.video_player:
            if self.video_output:
                if self.video_output.isMuted():
                    self.video_output.setMuted(False)
                if self.video_output.volume() <= 0.05:
                    self.video_output.setVolume(0.85)
                if self.video_player.audioOutput() != self.video_output:
                    self.video_player.setAudioOutput(self.video_output)
            vol = int(self.video_output.volume() * 100) if self.video_output else 0
            ReproductorLogger.info(f"PlayerManager: [Reproducir Video] play() | Fuente: {self.archivo_video} | Vol: {vol}%")
            self.video_player.play()

    def pausar_video(self):
        if self.video_player:
            ReproductorLogger.info(f"PlayerManager: [Pausar Video] pause()")
            self.video_player.pause()

    def detener_video(self):
        if self.video_player:
            ReproductorLogger.info(f"PlayerManager: [Detener Video] stop()")
            self.video_player.stop()

    def set_volumen_video(self, vol):
        if self.video_output:
            self.video_output.setVolume(vol)
            self.video_output.setMuted(False)
            ReproductorLogger.info(f"PlayerManager: [Volumen Video] Fijado a {int(vol * 100)}%")

    def obtener_info_video(self, ruta):
        try:
            import cv2
            cap = cv2.VideoCapture(ruta)
            if not cap.isOpened(): return None
            fps = cap.get(cv2.CAP_PROP_FPS)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duracion = frames / fps if fps > 0 else 0
            cap.release()
            return {"fps": fps, "frames": frames, "w": w, "h": h, "duracion": duracion}
        except Exception:
            return None

    def set_playback_rate(self, rate):
        try:
            r = float(rate)
            if self.audio_player: self.audio_player.setPlaybackRate(r)
            if self.video_player: self.video_player.setPlaybackRate(r)
            ReproductorLogger.info(f"PlayerManager: Velocidad de reproducción fijada a {r}x")
        except Exception as e:
            ReproductorLogger.error(f"PlayerManager: Error fijando velocidad: {e}")

    def get_playback_rate(self):
        p = self._activo()
        return p.playbackRate() if p else 1.0
