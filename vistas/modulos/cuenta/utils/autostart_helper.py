import os
import sys
import json
import platform
import subprocess
from pathlib import Path

STARTUP_LINK_NAME = "MultiToolApp.lnk"
REGKEY_NAME = "MultiToolApp"

def get_startup_folder() -> Path:
    """Retorna la ruta de la carpeta Inicio de Windows"""
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return Path.home()

def get_executable_path() -> Path:
    """Obtiene la ruta absoluta del ejecutable principal resolviendo la ruta dinamica de instalacion"""
    # 1. Consultar el registro dinamico de instalacion (~/.multitool_install.json)
    manifest = Path.home() / ".multitool_install.json"
    if manifest.exists():
        try:
            with open(manifest, "r", encoding="utf-8") as f:
                data = json.load(f)
            exe_str = data.get("exe_path")
            if exe_str and Path(exe_str).exists():
                return Path(exe_str)
        except Exception: pass

    # 2. Si se ejecuta desde un binario compilado .exe
    main_exe = Path(sys.executable).resolve()
    if main_exe.suffix.lower() == ".exe" and main_exe.name.lower() not in ["python.exe", "pythonw.exe"]:
        return main_exe

    # 3. Chequear si existe Multitool.exe en Documents/Multitool/
    doc_exe = Path.home() / "Documents" / "Multitool" / "Multitool.exe"
    if doc_exe.exists():
        return doc_exe

    return doc_exe

def is_desktop_shortcut_present() -> bool:
    """Verifica si el acceso directo de escritorio ya existe"""
    desktop = Path(os.path.join(os.path.expanduser("~"), "Desktop"))
    sys_os = platform.system()
    if sys_os == "Windows":
        return (desktop / "Multitool.lnk").exists() or (desktop / "MultiToolApp.lnk").exists()
    elif sys_os == "Linux":
        return (desktop / "Multitool.desktop").exists()
    elif sys_os == "Darwin":
        return (desktop / "Multitool").exists()
    return False

def is_autostart_enabled() -> bool:
    """Verifica si el inicio automático con Windows está activado"""
    if platform.system() != "Windows":
        return False
        
    lnk_file = get_startup_folder() / STARTUP_LINK_NAME
    if lnk_file.exists():
        return True

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        val, _ = winreg.QueryValueEx(key, REGKEY_NAME)
        winreg.CloseKey(key)
        if val:
            return True
    except Exception: pass

    return False

def toggle_autostart(enable: bool) -> tuple[bool, str]:
    """Activa o desactiva el inicio automático con Windows"""
    if platform.system() != "Windows":
        return False, "La función de inicio automático solo está disponible en sistemas Windows."

    startup_dir = get_startup_folder()
    lnk_path = startup_dir / STARTUP_LINK_NAME
    target_path = get_executable_path()
    work_dir = target_path.parent

    try:
        if enable:
            ps_script = (
                f"$s = (New-Object -COM WScript.Shell).CreateShortcut('{lnk_path}'); "
                f"$s.TargetPath = '{target_path}'; "
                f"$s.WorkingDirectory = '{work_dir}'; "
                f"$s.WindowStyle = 1; "
                f"$s.Description = 'MultiTool AutoStart'; "
                f"$s.Save()"
            )
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_SET_VALUE
                )
                winreg.SetValueEx(key, REGKEY_NAME, 0, winreg.REG_SZ, f'"{target_path}"')
                winreg.CloseKey(key)
            except Exception: pass

            return True, "¡Función Activada! MultiTool se iniciará automáticamente con Windows."
        else:
            if lnk_path.exists():
                lnk_path.unlink()

            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_SET_VALUE
                )
                winreg.DeleteValue(key, REGKEY_NAME)
                winreg.CloseKey(key)
            except Exception: pass

            return True, "Función de inicio con Windows desactivada."
    except Exception as e:
        return False, f"No se pudo cambiar la configuración de inicio: {e}"
