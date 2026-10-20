"""
download_manager.py - Gestor de Descargas Asíncronas en Hilos Secundarios (QThread) sin Congelamiento de UI
"""
import os
import time
import json
import urllib.request
import subprocess
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, QObject


class DownloadWorker(QThread):
    """Hilo secundario para descargar archivos vía HTTP por streaming sin congelar la UI"""
    progress_signal = pyqtSignal(str, int, int, float) # (download_id, bytes_recv, total_bytes, speed_bytes_sec)
    completed_signal = pyqtSignal(str, str) # (download_id, file_path)
    error_signal = pyqtSignal(str, str) # (download_id, error_msg)

    def __init__(self, download_id, url, dest_folder, cookies_str=None, custom_headers=None):
        super().__init__()
        self.download_id = download_id
        self.url = url
        self.dest_folder = Path(dest_folder)
        self.dest_folder.mkdir(parents=True, exist_ok=True)
        self.cookies_str = cookies_str
        self.custom_headers = custom_headers or {}
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            filename = self.url.split("/")[-1].split("?")[0]
            if not filename or len(filename) > 80:
                filename = f"descarga_{int(time.time())}.bin"

            file_path = self.dest_folder / filename

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "*/*"
            }
            if self.cookies_str:
                headers["Cookie"] = self.cookies_str
            if self.custom_headers:
                headers.update(self.custom_headers)

            req = urllib.request.Request(self.url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                total_bytes = int(response.headers.get("Content-Length", 0))
                bytes_recv = 0
                chunk_size = 65536 # 64KB por bloque

                start_time = time.time()
                last_time = start_time
                last_bytes = 0
                speed = 0.0

                with open(file_path, "wb") as f:
                    while True:
                        if self._is_cancelled:
                            f.close()
                            if file_path.exists():
                                os.remove(file_path)
                            self.error_signal.emit(self.download_id, "Descarga cancelada por el usuario")
                            return

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        bytes_recv += len(chunk)

                        now = time.time()
                        if now - last_time >= 0.5:
                            speed = (bytes_recv - last_bytes) / (now - last_time)
                            last_time = now
                            last_bytes = bytes_recv

                        self.progress_signal.emit(self.download_id, bytes_recv, total_bytes, speed)

            self.completed_signal.emit(self.download_id, str(file_path))
        except Exception as e:
            self.error_signal.emit(self.download_id, str(e))


class InstallWorker(QThread):
    """Hilo secundario para ejecutar instaladores o procesos en segundo plano sin congelar la UI"""
    started_signal = pyqtSignal(str) # (install_id)
    finished_signal = pyqtSignal(str, int) # (install_id, return_code)
    error_signal = pyqtSignal(str, str) # (install_id, error_msg)

    def __init__(self, install_id, executable_path, args=None):
        super().__init__()
        self.install_id = install_id
        self.executable_path = executable_path
        self.args = args or []

    def run(self):
        try:
            self.started_signal.emit(self.install_id)
            cmd = [self.executable_path] + self.args
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return_code = process.wait()
            self.finished_signal.emit(self.install_id, return_code)
        except Exception as e:
            self.error_signal.emit(self.install_id, str(e))


class DownloadManager(QObject):
    """Gestor principal de hilos de descargas y persistencia del historial"""
    def __init__(self, ruta_usuario):
        super().__init__()
        self.ruta_usuario = Path(ruta_usuario)
        self.ruta_descargas = self.ruta_usuario / "descargas"
        self.ruta_descargas.mkdir(parents=True, exist_ok=True)
        
        self.active_workers = {}
        self.historial_descargas = self.cargar_historial()

    def cargar_historial(self):
        ruta_json = self.ruta_usuario / "descargas.json"
        if ruta_json.exists():
            try:
                with open(ruta_json, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def guardar_historial(self):
        ruta_json = self.ruta_usuario / "descargas.json"
        try:
            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump(self.historial_descargas, f, indent=4)
        except Exception:
            pass

    def iniciar_descarga(self, url, progress_cb=None, completed_cb=None, error_cb=None, cookies_str=None, custom_headers=None):
        download_id = f"dl_{int(time.time() * 1000)}"
        worker = DownloadWorker(download_id, url, self.ruta_descargas, cookies_str=cookies_str, custom_headers=custom_headers)

        if progress_cb: worker.progress_signal.connect(progress_cb)
        if completed_cb: worker.completed_signal.connect(completed_cb)
        if error_cb: worker.error_signal.connect(error_cb)

        worker.completed_signal.connect(self._on_download_completed_internal)

        self.active_workers[download_id] = worker
        worker.start()
        return download_id

    def registrar_descarga_externa(self, file_path):
        """Registra una descarga completada desde el navegador en el historial general"""
        download_id = f"ext_{int(time.time() * 1000)}"
        item = {
            "id": download_id,
            "path": str(file_path),
            "nombre": os.path.basename(str(file_path)),
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.historial_descargas.insert(0, item)
        self.guardar_historial()

    def ejecutar_instalador_asincrono(self, file_path, started_cb=None, finished_cb=None, error_cb=None):
        install_id = f"inst_{int(time.time() * 1000)}"
        worker = InstallWorker(install_id, file_path)

        if started_cb: worker.started_signal.connect(started_cb)
        if finished_cb: worker.finished_signal.connect(finished_cb)
        if error_cb: worker.error_signal.connect(error_cb)

        self.active_workers[install_id] = worker
        worker.start()
        return install_id

    def _on_download_completed_internal(self, download_id, file_path):
        item = {
            "id": download_id,
            "path": file_path,
            "nombre": os.path.basename(file_path),
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.historial_descargas.insert(0, item)
        self.guardar_historial()
        if download_id in self.active_workers:
            del self.active_workers[download_id]
