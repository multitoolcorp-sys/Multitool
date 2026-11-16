# -*- coding: utf-8 -*-
"""
Capa de compatibilidad multiplataforma (Windows, Linux y macOS).
Centraliza detección de SO, apertura nativa de archivos/carpetas, rutas de usuario,
shell por defecto y compatibilidad de módulos (`"os"` en `config.json`).
"""

import os
import platform
import subprocess
import sys
from pathlib import Path


def get_os_key() -> str:
    """Devuelve 'windows', 'macos' o 'linux'."""
    sys_name = platform.system().lower()
    if sys_name.startswith("win"):
        return "windows"
    if sys_name == "darwin":
        return "macos"
    return "linux"


def is_module_compatible(config_or_mod: dict) -> bool:
    """Comprueba si un módulo/submódulo es compatible con el SO actual según su campo `'os'`."""
    allowed = config_or_mod.get("os")
    if not allowed:
        return True
    if isinstance(allowed, str):
        allowed = [allowed]
    normalized = {str(x).strip().lower() for x in allowed if str(x).strip()}
    if not normalized or "all" in normalized or "todos" in normalized:
        return True
    return get_os_key() in normalized


def open_path_native(target: str | Path) -> bool:
    """Abre un archivo, carpeta o URL con la aplicación nativa del SO."""
    target_str = str(target)
    try:
        os_key = get_os_key()
        if os_key == "windows":
            os.startfile(target_str)  # type: ignore[attr-defined]
        elif os_key == "macos":
            subprocess.Popen(["open", target_str])
        else:
            subprocess.Popen(["xdg-open", target_str])
        return True
    except Exception:
        return False


def get_default_shell() -> str:
    """Devuelve la terminal por defecto según el sistema operativo."""
    if get_os_key() == "windows":
        return "powershell.exe"
    return os.environ.get("SHELL") or "/bin/bash"


def get_app_data_dir(app_name: str = "Multitool") -> Path:
    """Devuelve la carpeta estándar de datos de usuario según el SO."""
    os_key = get_os_key()
    if os_key == "windows":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif os_key == "macos":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    ruta = base / app_name
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def apply_native_dark_titlebar(win_id) -> bool:
    """Aplica barra de título oscura en Windows 10/11 sin afectar Linux/macOS."""
    if get_os_key() != "windows" or not win_id:
        return False
    try:
        import ctypes
        hwnd = int(win_id)
        val = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
        return True
    except Exception:
        return False
