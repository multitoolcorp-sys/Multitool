import os
import threading
import time
import datetime
import queue
import numpy as np
import sounddevice as sd
import soundfile as sf
import cv2

from PyQt6.QtGui import QGuiApplication, QImage

class RecorderManager:
    def __init__(self, ruta_grabaciones):
        self.ruta_grabaciones = ruta_grabaciones
        self.ruta_grabaciones.mkdir(parents=True, exist_ok=True)

        self.grabando_audio = False
        self.pausado_audio  = False
        self.grabando_video = False
        self.pausado_video  = False
        self.grabando_webcam = False

        self.audio_frames = []
        self.audio_queue  = queue.Queue()
        self.frecuencia_muestreo = 44100
        self.canales = 2
        self.stream  = None

        # Para grabación de video+audio simultánea
        self._audio_frames_video = []
        self._stream_video_audio = None

    # ─────────────────────────────────────────
    #  Utilidades de pantallas y dispositivos
    # ─────────────────────────────────────────
    def obtener_pantallas(self):
        """Usa el HardwareManager centralizado"""
        from vistas.utils.hardware_manager import get_hardware_manager
        return get_hardware_manager().get_screens_strings()

    def obtener_geometria_pantalla(self, indice: int):
        """Devuelve (x, y, w, h) de la pantalla indicada."""
        try:
            from PyQt6.QtWidgets import QApplication
            screens = QApplication.screens()
            if 0 <= indice < len(screens):
                g = screens[indice].geometry()
                return g.x(), g.y(), g.width(), g.height()
        except Exception:
            pass
        try:
            import pyautogui
            w, h = pyautogui.size()
            return 0, 0, w, h
        except Exception:
            return 0, 0, 1920, 1080

    def obtener_dispositivos(self):
        """Lista de micrófonos disponibles."""
        try:
            devices = sd.query_devices()
            return [f"{i}: {d['name']}" for i, d in enumerate(devices) if d['max_input_channels'] > 0]
        except Exception:
            return ["Default"]

    def obtener_camaras_web(self):
        """Lista de cámaras web disponibles."""
        cams = []
        for i in range(4):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
            if cap.isOpened():
                cams.append(f"Cámara {i}")
                cap.release()
        if not cams:
            cams = ["Cámara Principal (0)"]
        return cams

    # ─────────────────────────────────────────
    #  GRABACIÓN DE AUDIO SOLO
    # ─────────────────────────────────────────
    def iniciar_audio(self, dispositivo_indice, update_cb):
        self.audio_frames = []
        self.audio_queue  = queue.Queue()
        self.grabando_audio = True
        self.pausado_audio  = False

        def callback(indata, frames, t, status):
            if not self.pausado_audio:
                self.audio_queue.put(indata.copy())
                self.audio_frames.append(indata.copy())

        try:
            self.stream = sd.InputStream(
                samplerate=self.frecuencia_muestreo,
                channels=self.canales,
                callback=callback,
                device=dispositivo_indice
            )
            self.stream.start()
            threading.Thread(target=self._audio_loop, args=(update_cb,), daemon=True).start()
            return True
        except Exception as e:
            print(f"[RecorderManager] Error audio: {e}")
            return False

    def _audio_loop(self, update_cb):
        while self.grabando_audio:
            if not self.audio_queue.empty():
                data = self.audio_queue.get()
                if update_cb:
                    try: update_cb(data)
                    except Exception: pass
            time.sleep(0.05)

    def detener_audio(self):
        self.grabando_audio = False
        self.pausado_audio  = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.audio_frames:
            return None

        audio_data = np.concatenate(self.audio_frames, axis=0)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"audio_{ts}.wav"
        ruta = self.ruta_grabaciones / nombre
        sf.write(str(ruta), audio_data, self.frecuencia_muestreo)
        return nombre

    def toggle_pausa_audio(self):
        if self.grabando_audio:
            self.pausado_audio = not self.pausado_audio
        return self.pausado_audio

    # ─────────────────────────────────────────
    #  GRABACIÓN DE VIDEO CON TIEMPO REAL 1:1
    # ─────────────────────────────────────────
    def capturar_frame_actual(self, area, pantalla_idx):
        frame = None
        try:
            screens = QGuiApplication.screens()
            idx = pantalla_idx if 0 <= pantalla_idx < len(screens) else 0
            screen = screens[idx]
            pix = screen.grabWindow(0)
            qimg = pix.toImage().convertToFormat(QImage.Format.Format_RGB32)
            w, h = qimg.width(), qimg.height()
            bpl = qimg.bytesPerLine()
            ptr = qimg.bits()
            ptr.setsize(h * bpl)
            arr = np.frombuffer(ptr, np.uint8).reshape((h, bpl // 4, 4))
            bgr = cv2.cvtColor(arr[:, :w], cv2.COLOR_BGRA2BGR)

            if area:
                ax, ay, aw, ah = area
                mx, my = screen.geometry().x(), screen.geometry().y()
                rx = max(0, ax - mx)
                ry = max(0, ay - my)
                rw = min(w - rx, aw)
                rh = min(h - ry, ah)
                if rw > 0 and rh > 0:
                    frame = bgr[ry:ry+rh, rx:rx+rw]
                else:
                    frame = bgr
            else:
                frame = bgr
        except Exception:
            try:
                import pyautogui
                if area:
                    x, y, w, h = area
                    img = pyautogui.screenshot(region=(x, y, w, h))
                else:
                    img = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            except Exception:
                pass

        if frame is not None:
            self._dibujar_cursor(frame, area, pantalla_idx)
            
        return frame

    def _dibujar_cursor(self, frame, area, pantalla_idx):
        try:
            import pyautogui
            cx, cy = pyautogui.position()
            if area:
                x, y, w, h = area
            else:
                x, y, w, h = self.obtener_geometria_pantalla(pantalla_idx)
                
            fh, fw = frame.shape[:2]
            scale_x = fw / w if w > 0 else 1.0
            scale_y = fh / h if h > 0 else 1.0
            
            rx = int((cx - x) * scale_x)
            ry = int((cy - y) * scale_y)
            
            if 0 <= rx < fw and 0 <= ry < fh:
                puntos = np.array([
                    [rx, ry],
                    [rx, ry + 15],
                    [rx + 4, ry + 11],
                    [rx + 9, ry + 16],
                    [rx + 11, ry + 14],
                    [rx + 6, ry + 9],
                    [rx + 11, ry + 9]
                ], dtype=np.int32)
                
                cv2.drawContours(frame, [puntos], 0, (255, 255, 255), -1)
                cv2.drawContours(frame, [puntos], 0, (0, 0, 0), 1)
        except Exception:
            pass

    def guardar_video_frames(self, frames, total_duration, area, pantalla_idx):
        if not frames:
            return "No se capturaron cuadros de video."
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_salida = self.ruta_grabaciones / f"grabacion_{ts}.mp4"

        real_fps = max(1.0, len(frames) / max(0.1, total_duration))
        h, w = frames[0].shape[:2]

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(ruta_salida), fourcc, real_fps, (w, h))
        for f in frames:
            out.write(f)
        out.release()

        return f"Video guardado a velocidad 1:1 ({len(frames)} cuadros a {real_fps:.1f} FPS)"

    def toggle_pausa_video(self):
        if self.grabando_video:
            self.pausado_video = not self.pausado_video
        return self.pausado_video

    # ─────────────────────────────────────────
    #  GRABACIÓN Y SNAPSHOTS DE CÁMARA WEB
    # ─────────────────────────────────────────
    def tomar_foto_webcam(self, cam_idx=0):
        try:
            cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre = f"foto_{ts}.png"
                ruta = self.ruta_grabaciones / nombre
                cv2.imwrite(str(ruta), frame)
                return nombre
        except Exception as e:
            print(f"[RecorderManager] Error al tomar foto webcam: {e}")
        return None

    def iniciar_webcam_video(self, cam_idx, fps, update_cb):
        self.grabando_webcam = True
        threading.Thread(target=self._webcam_video_loop, args=(cam_idx, fps, update_cb), daemon=True).start()

    def _webcam_video_loop(self, cam_idx, fps, update_cb):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_salida = self.ruta_grabaciones / f"webcam_{ts}.mp4"

        cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

        frames_buffer = []
        frame_time = 1.0 / fps
        t_start = time.perf_counter()

        while self.grabando_webcam:
            t0 = time.perf_counter()
            ret, frame = cap.read()
            if ret and frame is not None:
                frames_buffer.append(frame)
                try: update_cb(frame)
                except Exception: pass
            elapsed = time.perf_counter() - t0
            sleep_t = max(0, frame_time - elapsed)
            time.sleep(sleep_t)

        cap.release()
        total_time = max(0.1, time.perf_counter() - t_start)

        if frames_buffer:
            real_fps = max(1.0, len(frames_buffer) / total_time)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(ruta_salida), fourcc, real_fps, (w, h))
            for f in frames_buffer:
                out.write(f)
            out.release()

    def detener_webcam_video(self):
        self.grabando_webcam = False
        return "Video de cámara web guardado a velocidad 1:1"
