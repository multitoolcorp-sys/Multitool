import datetime
import os
import platform
import stat
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from controlador.utils.platform_compat import open_path_native


def mostrar_propiedades_multiplataforma(ruta_archivo, parent_widget=None):
    """Muestra propiedades nativas en Windows y un diálogo detallado en Linux/macOS."""
    if platform.system() == "Windows":
        return mostrar_propiedades_windows(ruta_archivo)
    try:
        p = Path(ruta_archivo)
        st = p.stat()
        tipo = "Carpeta" if p.is_dir() else "Archivo"
        mod_t = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        perm = stat.filemode(st.st_mode)
        size_kb = max(1, st.st_size // 1024) if p.is_file() else 0
        tam_txt = f"{st.st_size:,} bytes ({size_kb:,} KB)" if p.is_file() else "Directorio"
        QMessageBox.information(
            parent_widget,
            f"Propiedades — {p.name}",
            f"<b>Nombre:</b> {p.name}<br>"
            f"<b>Tipo:</b> {tipo}<br>"
            f"<b>Ruta:</b> <code>{p.resolve()}</code><br>"
            f"<b>Tamaño:</b> {tam_txt}<br>"
            f"<b>Permisos:</b> <code>{perm}</code><br>"
            f"<b>Modificado:</b> {mod_t}",
        )
        return True
    except Exception:
        return False

def mostrar_propiedades_windows(ruta_archivo):
    """Invoca la ventana de propiedades nativa de Windows usando ShellExecuteExW"""
    if platform.system() != "Windows":
        return False
    import ctypes
    from ctypes import wintypes
    
    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", ctypes.c_ulong),
            ("hwnd", wintypes.HWND),
            ("lpVerb", ctypes.c_wchar_p),
            ("lpFile", ctypes.c_wchar_p),
            ("lpParameters", ctypes.c_wchar_p),
            ("lpDirectory", ctypes.c_wchar_p),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", ctypes.c_wchar_p),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIconOrMonitor", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]
        
    SEE_MASK_INVOKEIDLIST = 0x0000000C
    SEE_MASK_NOCLOSEPROCESS = 0x00000040
    
    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
    sei.fMask = SEE_MASK_INVOKEIDLIST | SEE_MASK_NOCLOSEPROCESS
    sei.lpVerb = "properties"
    sei.lpFile = str(Path(ruta_archivo).resolve())
    sei.nShow = 5 # SW_SHOW
    
    ret = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))
    return bool(ret)


def abrir_dispositivo_adb(dev_id, parent_widget=None):
    """Gestiona la interacción con un dispositivo móvil Android detectado por ADB"""
    try:
        msg = QMessageBox(parent_widget)
        msg.setWindowTitle("Dispositivo Android Conectado")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"<h3 style='color: #6366F1;'>📲 Dispositivo Móvil Detectado</h3>"
                    f"<p><b>Identificador / Serie:</b> <code>{dev_id}</code></p>"
                    f"<p>El teléfono está conectado y disponible mediante <b>ADB (Depuración USB)</b>.</p>"
                    f"<p>¿Qué acción deseas realizar?</p>")
        btn_espejo = msg.addButton("📱 Abrir en Espejo Celular", QMessageBox.ButtonRole.ActionRole)
        btn_explorar = msg.addButton("📂 Abrir Almacenamiento (Este equipo)", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        
        if msg.clickedButton() == btn_espejo:
            app = getattr(parent_widget, "main_window", None) or parent_widget
            while app and not hasattr(app, "notebook") and hasattr(app, "parent") and app.parent():
                app = app.parent()
            if hasattr(app, "notebook"):
                for i in range(app.notebook.count()):
                    txt = app.notebook.tabText(i).lower()
                    if "extra" in txt or "espejo" in txt:
                        app.notebook.setCurrentIndex(i)
                        if hasattr(app, "nav_bar"):
                            if hasattr(app.nav_bar, "select_tab"):
                                app.nav_bar.select_tab(i)
                            elif hasattr(app.nav_bar, "seleccionar_tab"):
                                app.nav_bar.seleccionar_tab(i)
                        break
        elif msg.clickedButton() == btn_explorar:
            sys_os = platform.system()
            if sys_os == "Windows":
                subprocess.Popen(["explorer.exe", "shell:MyComputerFolder"])
            elif sys_os == "Darwin":
                open_path_native("/Volumes")
            else:
                gvfs = Path(f"/run/user/{os.getuid()}/gvfs") if hasattr(os, "getuid") else Path("/media")
                open_path_native(gvfs if gvfs.exists() else Path("/media"))
    except Exception as e:
        print(f"[ShellUtils] Error al interactuar con dispositivo ADB: {e}")
