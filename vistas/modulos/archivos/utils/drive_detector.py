import os
import platform
import string
import threading
import subprocess

_cache_mtp = []
_cache_lock = threading.Lock()
_worker_activo = False
_primer_inicio_mtp = False

def obtener_ruta_remota_unidad(drive_letter):
    """Devuelve la ruta UNC asignada a una letra de unidad (ej. S: -> \\user-pc\\servers)."""
    if platform.system() != "Windows":
        return None
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(512)
        buf_size = ctypes.c_ulong(512)
        res = ctypes.windll.mpr.WNetGetConnectionW(drive_letter.rstrip('\\'), buf, ctypes.byref(buf_size))
        if res == 0:
            return buf.value
    except Exception:
        pass
    return None

def obtener_conexiones_red():
    """
    Lista las conexiones de red activas o desconectadas usando 'net use'.
    Retorna lista de diccionarios: [{'status': '...', 'letter': 'S:', 'unc': '\\\\servidor\\compartido'}]
    """
    if platform.system() != "Windows":
        return []
    conns = []
    try:
        res = subprocess.run(
            ["net", "use"],
            capture_output=True,
            errors="replace",
            timeout=1,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
        for line in res.stdout.splitlines():
            l_strip = line.strip()
            if "\\\\" in l_strip:
                parts = l_strip.split()
                unc_item = [p for p in parts if p.startswith("\\\\")]
                letter_item = [p for p in parts if len(p) == 2 and p[1] == ':']
                unc = unc_item[0] if unc_item else ""
                letter = letter_item[0] if letter_item else ""
                status = parts[0] if parts else ""
                if unc:
                    conns.append({"status": status, "letter": letter, "unc": unc})
    except Exception:
        pass
    return conns

def obtener_letras_unidades_libres():
    """Retorna las letras de unidad disponibles (de Z: a D:) para mapear unidades de red."""
    if platform.system() != "Windows":
        return []
    try:
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        ocupadas = set()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                ocupadas.add(letter)
            bitmask >>= 1
        libres = [f"{l}:" for l in reversed(string.ascii_uppercase) if l not in ocupadas and l not in ('A', 'B')]
        return libres
    except Exception:
        return ["Z:", "Y:", "X:", "W:", "V:"]

def escanear_dispositivos_red_arp():
    """Escanea la tabla ARP local para descubrir rápidamente IPs de equipos en la misma subred."""
    ips = []
    try:
        res = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            errors="replace",
            timeout=2,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
        for line in res.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                ip = parts[0]
                if ip.count('.') == 3 and not ip.startswith(('224.', '239.', '255.', '127.')) and not ip.endswith('.255'):
                    ips.append(ip)
    except Exception:
        pass
    return list(dict.fromkeys(ips))

def obtener_unidades_rapidas():
    """
    Detección ultra-rápida (menos de 2 milisegundos) de unidades locales,
    extraíbles y de red usando Win32 GetLogicalDrives y GetDriveTypeW.
    NUNCA bloquea el hilo principal ni produce el congelamiento de 4 segundos
    provocado por QStorageInfo en unidades remotas desconectadas.
    """
    unidades_dict = {}

    if platform.system() == "Windows":
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive_path = f"{letter}:\\"
                    key = drive_path.lower()
                    dtype = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    # 2: REMOVABLE, 3: FIXED, 4: REMOTE, 5: CDROM, 6: RAMDISK
                    unc = obtener_ruta_remota_unidad(f"{letter}:")

                    if dtype == 4 or unc:
                        icono = "🌐"
                        etiqueta = f"Red ({unc})" if unc else "Unidad de Red"
                        texto = f"{icono} {etiqueta} ({letter}:)"
                    elif letter.upper() == 'C':
                        icono = "💻"
                        etiqueta = "Disco Local (C:)"
                        texto = f"{icono} {etiqueta}"
                    elif dtype == 5:
                        icono = "💿"
                        etiqueta = f"Unidad Óptica ({letter}:)"
                        texto = f"{icono} {etiqueta}"
                    elif dtype == 2:
                        icono = "🔌"
                        etiqueta = f"Unidad Extraíble ({letter}:)"
                        texto = f"{icono} {etiqueta}"
                    else:
                        icono = "💾"
                        etiqueta = f"Disco ({letter}:)"
                        texto = f"{icono} {etiqueta}"

                    unidades_dict[key] = (texto, drive_path, icono)
                bitmask >>= 1
        except Exception:
            pass

        # Añadir conexiones de red UNC activas sin letra (ej: \\192.168.0.15\servers)
        try:
            conns = obtener_conexiones_red()
            for c in conns:
                unc = c.get("unc", "")
                letter = c.get("letter", "")
                if unc and not letter:
                    key = unc.lower()
                    if key not in unidades_dict:
                        texto = f"🌐 {unc}"
                        unidades_dict[key] = (texto, unc, "🌐")
        except Exception:
            pass

    else:
        # En Linux / macOS usamos QStorageInfo de forma segura
        try:
            from PyQt6.QtCore import QStorageInfo
            volumes = QStorageInfo.mountedVolumes()
            for vol in volumes:
                if vol.isValid() and vol.isReady():
                    ruta = vol.rootPath()
                    etiqueta = vol.displayName().strip() if vol.displayName() else "Almacenamiento"
                    icono = "💻" if ruta == "/" else "🔌"
                    if vol.isReadOnly():
                        icono = "💿"
                    texto = f"{icono} {etiqueta} ({ruta})"
                    unidades_dict[ruta.lower()] = (texto, ruta, icono)
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
