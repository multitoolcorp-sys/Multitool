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

    def registrar_descarga_externa(self, file_path, url=""):
        """Registra una descarga completada desde el navegador en el historial general con cálculo de tamaño."""
        if not file_path:
            return
        norm_path = os.path.normpath(str(file_path))
        download_id = f"ext_{int(time.time() * 1000)}"

        size_str = ""
        try:
            p = Path(norm_path)
            if p.exists():
                sz = p.stat().st_size
                if sz >= 1024 * 1024 * 1024:
                    size_str = f"{sz / (1024**3):.2f} GB"
                elif sz >= 1024 * 1024:
                    size_str = f"{sz / (1024**2):.1f} MB"
                elif sz >= 1024:
                    size_str = f"{sz / 1024:.0f} KB"
                else:
                    size_str = f"{sz} B"
        except Exception:
            pass

        # Evitar duplicados del mismo archivo exacto; si ya existe, actualizar y mover al frente
        for i, it in enumerate(self.historial_descargas):
            if os.path.normpath(str(it.get("path", ""))) == norm_path:
                it["fecha"] = time.strftime("%Y-%m-%d %H:%M:%S")
                if size_str:
                    it["size"] = size_str
                if url:
                    it["url"] = url
                item = self.historial_descargas.pop(i)
                self.historial_descargas.insert(0, item)
                self.guardar_historial()
                return

        item = {
            "id": download_id,
            "path": norm_path,
            "nombre": os.path.basename(norm_path),
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
            "size": size_str,
            "url": url
        }
        self.historial_descargas.insert(0, item)
        self.guardar_historial()

    def sincronizar_descargas_locales(self):
        """Escanea las carpetas de descargas (predeterminada de Windows y local del usuario)
        para asegurar que todos los archivos descargados aparezcan en el historial."""
        carpetas = [self.ruta_descargas, Path.home() / "Downloads"]
        
        # Leer carpeta personalizada si existe en config
        try:
            cfg_path = self.ruta_usuario / "browser_data" / "config.json"
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    c_dir = cfg.get("download_dir")
                    if c_dir and Path(c_dir).exists():
                        carpetas.append(Path(c_dir))
        except Exception:
            pass

        rutas_registradas = {os.path.normpath(str(it.get("path", ""))) for it in self.historial_descargas}
        archivos_encontrados = []

        for carpeta in set(carpetas):
            if not carpeta.exists():
                continue
            try:
                for entry in carpeta.iterdir():
                    if entry.is_file() and not entry.name.endswith((".tmp", ".crdownload", ".part", ".lock")):
                        n_p = os.path.normpath(str(entry))
                        if n_p not in rutas_registradas:
                            try:
                                mtime = entry.stat().st_mtime
                                archivos_encontrados.append((entry, mtime))
                            except Exception:
                                pass
            except Exception:
                pass

        # Ordenar por fecha de modificación más reciente y agregar hasta los últimos 30 archivos
        archivos_encontrados.sort(key=lambda x: x[1], reverse=True)
        for entry, mtime in archivos_encontrados[:30]:
            sz = entry.stat().st_size
            if sz >= 1024 * 1024 * 1024:
                size_str = f"{sz / (1024**3):.2f} GB"
            elif sz >= 1024 * 1024:
                size_str = f"{sz / (1024**2):.1f} MB"
            elif sz >= 1024:
                size_str = f"{sz / 1024:.0f} KB"
            else:
                size_str = f"{sz} B"

            f_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
            self.historial_descargas.append({
                "id": f"sync_{int(mtime)}",
                "path": str(entry),
                "nombre": entry.name,
                "fecha": f_str,
                "size": size_str,
                "url": ""
            })

        if archivos_encontrados:
            self.guardar_historial()

    def eliminar_item_historial(self, path_or_id):
        """Elimina una descarga específica del historial guardado."""
        norm = os.path.normpath(str(path_or_id)).lower()
        self.historial_descargas = [
            it for it in self.historial_descargas
            if str(it.get("id")) != str(path_or_id) and os.path.normpath(str(it.get("path", ""))).lower() != norm
        ]
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
        size_str = ""
        try:
            sz = os.path.getsize(file_path)
            if sz >= 1024 * 1024 * 1024:
                size_str = f"{sz / (1024**3):.2f} GB"
            elif sz >= 1024 * 1024:
                size_str = f"{sz / (1024**2):.1f} MB"
            elif sz >= 1024:
                size_str = f"{sz / 1024:.0f} KB"
            else:
                size_str = f"{sz} B"
        except Exception:
            pass

        item = {
            "id": download_id,
            "path": file_path,
            "nombre": os.path.basename(file_path),
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
            "size": size_str,
            "url": ""
        }
        self.historial_descargas.insert(0, item)
        self.guardar_historial()
        if download_id in self.active_workers:
            del self.active_workers[download_id]
