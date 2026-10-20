import os
import sys
import time
import zipfile
import psutil
from PyQt6.QtCore import QThread, pyqtSignal

class ScanThread(QThread):
    progress_updated = pyqtSignal(int, str, int, int, float) # percent, current_file, scanned, threats, speed
    threat_detected = pyqtSignal(dict) # threat details
    scan_finished = pyqtSignal(bool, dict) # success, stats summary

    def __init__(self, scan_type, initial_path=None, exclusions=None, use_heuristics=True, scan_zip=True):
        super().__init__()
        self.scan_type = scan_type
        self.initial_path = initial_path
        self.exclusions = exclusions or []
        self.use_heuristics = use_heuristics
        self.scan_zip = scan_zip
        self._is_cancelled = False

        # EICAR test string signature
        self.eicar_signature = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            start_time = time.time()
            scanned_files = 0
            threats_found = 0
            
            # Determinar archivos a escanear
            files_to_scan = []
            processes_to_scan = []

            if self.scan_type == "quick":
                # Quick Scan: Procesos activos y carpetas clave
                # 1. Obtener procesos
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    if self._is_cancelled:
                        break
                    try:
                        exe = proc.info['exe']
                        if exe and os.path.exists(exe):
                            processes_to_scan.append(exe)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue

                # 2. Agregar carpetas de descargas del usuario, escritorio y temp
                paths_to_add = [
                    os.path.expanduser("~/Downloads"),
                    os.path.expanduser("~/Desktop"),
                    os.environ.get("TEMP", ""),
                    os.environ.get("TMP", "")
                ]
                for p in paths_to_add:
                    if p and os.path.exists(p):
                        self._collect_files(p, files_to_scan)
            
            elif self.scan_type == "full":
                # Full Scan: Directorio de trabajo y carpeta Home
                paths_to_add = [
                    os.getcwd(),
                    os.path.expanduser("~")
                ]
                for p in paths_to_add:
                    if p and os.path.exists(p):
                        self._collect_files(p, files_to_scan)
            
            elif self.scan_type == "custom":
                if self.initial_path and os.path.exists(self.initial_path):
                    self._collect_files(self.initial_path, files_to_scan)

            total_items = len(processes_to_scan) + len(files_to_scan)
            if total_items == 0:
                self.scan_finished.emit(True, {
                    "scanned": 0,
                    "threats": 0,
                    "elapsed": time.time() - start_time
                })
                return

            # Ejecutar escaneo de procesos primero
            for i, exe_path in enumerate(processes_to_scan):
                if self._is_cancelled:
                    break
                
                scanned_files += 1
                percent = int((scanned_files / total_items) * 100)
                speed = scanned_files / (time.time() - start_time + 0.001)
                
                self.progress_updated.emit(percent, f"Proceso: {os.path.basename(exe_path)}", scanned_files, threats_found, speed)
                
                threat = self._scan_single_file(exe_path, is_process=True)
                if threat:
                    threats_found += 1
                    self.threat_detected.emit(threat)

            # Escaneo de archivos
            for i, file_path in enumerate(files_to_scan):
                if self._is_cancelled:
                    break

                scanned_files += 1
                percent = int((scanned_files / total_items) * 100)
                speed = scanned_files / (time.time() - start_time + 0.001)

                self.progress_updated.emit(percent, file_path, scanned_files, threats_found, speed)

                threat = self._scan_single_file(file_path)
                if threat:
                    threats_found += 1
                    self.threat_detected.emit(threat)

            elapsed = time.time() - start_time
            self.scan_finished.emit(not self._is_cancelled, {
                "scanned": scanned_files,
                "threats": threats_found,
                "elapsed": elapsed
            })

        except Exception as e:
            self.scan_finished.emit(False, {"error": str(e)})

    def _collect_files(self, directory, file_list):
        # Exclusiones normalizadas
        normalized_exclusions = [os.path.abspath(p).lower() for p in self.exclusions]
        
        try:
            for root, dirs, files in os.walk(directory):
                if self._is_cancelled:
                    return

                # Filtrar directorios excluidos
                dirs[:] = [d for d in dirs if os.path.join(root, d).lower() not in normalized_exclusions]
                
                for f in files:
                    fp = os.path.join(root, f)
                    if fp.lower() not in normalized_exclusions:
                        # Saltar archivos de cuarentena para no dar falsos positivos sobre el almacén
                        if "quarantine_files" in fp:
                            continue
                        file_list.append(fp)
        except Exception:
            pass

    def _scan_single_file(self, file_path, is_process=False):
        try:
            # Comprobaciones básicas de acceso
            if not os.path.exists(file_path) or os.path.isdir(file_path):
                return None

            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Evitar escanear archivos gigantescos (>100MB) para mantener rendimiento, a menos que sean sospechosos
            if file_size > 100 * 1024 * 1024:
                return None

            # Leer archivo
            with open(file_path, 'rb') as f:
                content = f.read()

            # 1. Comprobar firma EICAR
            if self.eicar_signature in content:
                return {
                    "name": filename,
                    "path": file_path,
                    "type": "EICAR Test Signature",
                    "severity": "CRITICAL",
                    "reason": "Contiene la cadena estándar de prueba de antivirus (EICAR)."
                }

            # 2. Comprobar archivos comprimidos ZIP
            if self.scan_zip and filename.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(file_path) as z:
                        for name in z.namelist():
                            if self._is_cancelled:
                                break
                            # Leer miembro
                            try:
                                member_content = z.read(name)
                                if self.eicar_signature in member_content:
                                    return {
                                        "name": filename,
                                        "path": file_path,
                                        "type": "ZIP Malware Signature (EICAR)",
                                        "severity": "CRITICAL",
                                        "reason": f"Contiene archivo infectado '{name}' con firma EICAR dentro del ZIP."
                                    }
                            except Exception:
                                pass
                except Exception:
                    pass

            # 3. Comprobaciones heurísticas
            if self.use_heuristics:
                # A. Doble extensión sospechosa
                parts = filename.lower().split('.')
                if len(parts) > 2:
                    ext = parts[-1]
                    prev_ext = parts[-2]
                    # Extensiones ejecutables comunes ocultas detrás de extensiones inocuas
                    if ext in ['exe', 'scr', 'vbs', 'bat', 'ps1', 'cmd', 'js', 'jar', 'hta']:
                        if prev_ext in ['png', 'jpg', 'jpeg', 'pdf', 'docx', 'xlsx', 'txt', 'zip', 'mp4']:
                            return {
                                "name": filename,
                                "path": file_path,
                                "type": "Double Extension Exploit",
                                "severity": "ALTO",
                                "reason": f"Tiene extensión oculta sospechosa '{prev_ext}.{ext}' para engañar al usuario."
                            }

                # B. Script sospechoso en carpetas comunes
                if filename.lower().endswith(('.vbs', '.bat', '.ps1')):
                    # Comprobar si tiene APIs de ejecución o comandos ocultos
                    suspicious_keywords = [
                        b"wscript.shell", b"shell.application", b"eval(base64", 
                        b"bypass", b"-noprofile", b"iex(new-object", b"powershell.exe -e"
                    ]
                    content_lower = content.lower()
                    for kw in suspicious_keywords:
                        if kw in content_lower:
                            return {
                                "name": filename,
                                "path": file_path,
                                "type": "Suspicious Script Payload",
                                "severity": "ALTO",
                                "reason": f"Script contiene comandos de ejecución ofuscados o llamadas directas a shell."
                            }

                # C. Archivos ejecutables corruptos / diminutos
                if filename.lower().endswith('.exe') and file_size < 1000:
                    # Un .exe de menos de 1KB es muy inusual y suele ser un trigger/explotador
                    return {
                        "name": filename,
                        "path": file_path,
                        "type": "Suspicious Corrupt Executable",
                        "severity": "MEDIO",
                        "reason": "Archivo ejecutable (.exe) sospechosamente pequeño (< 1KB)."
                    }

            return None
        except Exception:
            return None
