import os
import platform
import string
import threading
from PyQt6.QtCore import QStorageInfo

_cache_mtp = []
_cache_lock = threading.Lock()
_worker_activo = False
_primer_inicio_mtp = False

def obtener_unidades_rapidas():
    """
    Detección ultra-rápida (menos de 5 milisegundos) de unidades locales,
    extraíbles y de red usando QStorageInfo y Win32 GetLogicalDrives.
    NUNCA bloquea el hilo principal ni produce lag.
    """
    unidades_dict = {}
    
    # 1. Método multiplataforma: QStorageInfo
    try:
        volumes = QStorageInfo.mountedVolumes()
        for vol in volumes:
            if vol.isValid() and vol.isReady():
                ruta = vol.rootPath()
                etiqueta = vol.displayName().strip() if vol.displayName() else "Almacenamiento"
                icono = "🔌"
                if vol.isReadOnly():
                    icono = "💿"
                
                if (platform.system() == "Windows" and "C:" in ruta.upper()) or (platform.system() != "Windows" and ruta == "/"):
                    icono = "💻"
                elif "Phone" in etiqueta or "MTP" in etiqueta or "Android" in etiqueta or "Mobile" in etiqueta:
                    icono = "📲"
                
                texto = f"{icono} {etiqueta} ({ruta})"
                unidades_dict[ruta.lower()] = (texto, ruta, icono)
    except Exception:
        pass

    # 2. En Windows: Escanear letras de unidad A:\ a Z:\ para discos que QStorageInfo pudo omitir
    if platform.system() == "Windows":
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive_path = f"{letter}:\\"
                    key = drive_path.lower()
                    if key not in unidades_dict:
                        dtype = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                        # 2: REMOVABLE, 3: FIXED, 4: REMOTE, 5: CDROM, 6: RAMDISK
                        icono = "💻" if letter.upper() == 'C' else ("💿" if dtype == 5 else ("🌐" if dtype == 4 else "🔌"))
                        etiqueta = "Disco Local" if dtype == 3 else ("Unidad Extraíble" if dtype == 2 else "Unidad")
                        texto = f"{icono} {etiqueta} ({drive_path})"
                        unidades_dict[key] = (texto, drive_path, icono)
                bitmask >>= 1
        except Exception:
            pass

    return list(unidades_dict.values())

def _escanear_mtp_background():
    """Escanea dispositivos MTP/WPD mediante Shell Namespace 17 en segundo plano."""
    global _cache_mtp, _worker_activo
    if platform.system() != "Windows":
        _worker_activo = False
        return
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        shell = win32com.client.Dispatch("Shell.Application")
        my_computer = shell.NameSpace(17) # ssfDRIVES
        items_mtp = []
        if my_computer:
            user_home = os.path.expanduser("~").lower()
            ignorar = {"objetos 3d", "imágenes", "imagenes", "música", "musica", "escritorio", "documentos", "vídeos", "videos", "descargas", "papelera de reciclaje", "red"}
            for item in my_computer.Items():
                name = item.Name.strip()
                path = str(item.Path).strip() if item.Path else ""
                name_lower = name.lower()
                
                if name_lower in ignorar or path.lower().startswith(user_home):
                    continue
                
                is_drive_letter = len(path) >= 2 and path[0] in string.ascii_letters and path[1] == ':'
                if is_drive_letter:
                    continue
                    
                chips_encontrados = False
                if item.IsFolder:
                    try:
                        folder = item.GetFolder
                        if folder:
                            sub_items = list(folder.Items())
                            if sub_items:
                                chips_encontrados = True
                                for sub in sub_items:
                                    sub_name = sub.Name.strip()
                                    sub_path = str(sub.Path).strip() if sub.Path else path
                                    texto = f"📲 {name} - {sub_name}"
                                    target = sub_path if sub_path else path
                                    items_mtp.append((texto, target, "📲"))
                    except Exception:
                        pass
                
                if not chips_encontrados:
                    texto = f"📲 {name}"
                    items_mtp.append((texto, path if path else name, "📲"))
        with _cache_lock:
            _cache_mtp = items_mtp
        pythoncom.CoUninitialize()
    except Exception:
        pass
    finally:
        _worker_activo = False

def iniciar_escaneo_mtp_asincrono(on_finished=None):
    """Lanza el escaneo MTP en un hilo secundario sin congelar jamás la interfaz."""
    global _worker_activo
    if _worker_activo:
        return
    _worker_activo = True
    def run():
        _escanear_mtp_background()
        if on_finished:
            try:
                on_finished()
            except Exception:
                pass
    t = threading.Thread(target=run, daemon=True)
    t.start()

def obtener_todas_las_unidades(incluir_mtp_cache=True):
    """
    Retorna instantáneamente las unidades del sistema sin bloquear el hilo principal.
    Si se solicita MTP, utiliza la caché en memoria y programa una actualización asíncrona.
    """
    global _primer_inicio_mtp
    resultado = obtener_unidades_rapidas()
    
    if incluir_mtp_cache and platform.system() == "Windows":
        with _cache_lock:
            mtp_items = list(_cache_mtp)
        resultado.extend(mtp_items)
        
        # En la primera llamada, disparar escaneo en segundo plano para poblar la caché
        if not _primer_inicio_mtp:
            _primer_inicio_mtp = True
            iniciar_escaneo_mtp_asincrono()
            
    return resultado
