"""
Utilidades para manejo de rutas en la aplicación.
Separa las rutas de recursos (empaquetados) de las rutas de datos (usuario).
"""

import sys
import platform
from pathlib import Path


def get_resource_path():
    """Ruta de recursos empaquetados."""
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)

    return Path(__file__).resolve().parent.parent.parent


def get_data_path():
    """
    Ruta para datos persistentes.
    Compatible con Windows, Linux y macOS.
    """
    # Si es un ejecutable (PyInstaller)
    if getattr(sys, "frozen", False):
        if platform.system() == "Windows":
            return Path(sys.executable).parent
        else:
            # En Linux/Mac, si está en /bin o similar, mejor usar el home
            return Path.home() / ".multitool"

    # En desarrollo, la raíz del proyecto
    return Path(__file__).resolve().parent.parent.parent


def get_cuentas_path():
    """Ruta de carpeta de cuentas."""
    return get_data_path() / "cuentas"

def get_user_path(persona):
    """Ruta de usuario."""
    return get_cuentas_path() / persona


def reiniciar_aplicacion(parent=None):
    """
    Reinicia la aplicación MultiTool de forma robusta y multiplataforma.
    Soporta ejecutables compilados (PyInstaller/frozen), entornos de desarrollo,
    rutas relativas y directorios de trabajo alterados.
    Nunca propaga excepciones no controladas.
    """
    import os
    import shutil
    import subprocess
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import QProcess

    app_dir = get_resource_path()

    # 1. Caso: Aplicación compilada (Frozen / PyInstaller / cx_Freeze)
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        args = sys.argv[1:] if len(sys.argv) > 1 else []
        try:
            if QProcess.startDetached(exe_path, args, str(app_dir)):
                QApplication.quit()
                sys.exit(0)
        except Exception:
            pass

        try:
            subprocess.Popen([exe_path] + args, cwd=str(app_dir))
            QApplication.quit()
            sys.exit(0)
        except Exception as e:
            if parent:
                QMessageBox.warning(
                    parent, "Reinicio Manual Requerido",
                    "Los cambios se han guardado con éxito.\n\n"
                    f"No se pudo relanzar el ejecutable automáticamente ({e}).\n"
                    "Por favor, cierra y abre MultiTool manualmente para aplicar los cambios."
                )
            return False

    # 2. Caso: Ejecución como script de Python
    main_py = app_dir / "main.py"
    if not main_py.exists():
        if sys.argv and Path(sys.argv[0]).exists():
            main_py = Path(sys.argv[0]).resolve()
        else:
            main_py = Path.cwd() / "main.py"

    # Determinar el ejecutable de python real y existente
    python_candidates = [
        sys.executable,
        os.path.join(sys.exec_prefix, "python.exe") if os.name == "nt" else None,
        os.path.join(sys.base_exec_prefix, "python.exe") if os.name == "nt" else None,
        shutil.which("python"),
        shutil.which("python3"),
        shutil.which("py"),
    ]

    chosen_python = None
    for cand in python_candidates:
        if cand and os.path.exists(cand):
            chosen_python = cand
            break

    if not chosen_python:
        chosen_python = sys.executable or "python"

    extra_args = sys.argv[1:] if len(sys.argv) > 1 else []
    cmd = [str(chosen_python), str(main_py)] + extra_args

    try:
        if os.path.exists(str(chosen_python)) and QProcess.startDetached(str(chosen_python), [str(main_py)] + extra_args, str(app_dir)):
            QApplication.quit()
            sys.exit(0)
    except Exception:
        pass

    try:
        subprocess.Popen(cmd, cwd=str(app_dir))
        QApplication.quit()
        sys.exit(0)
    except Exception as e:
        if parent:
            QMessageBox.warning(
                parent, "Reinicio Manual Requerido",
                "Los cambios se han guardado con éxito.\n\n"
                f"No se pudo reiniciar automáticamente ({e}).\n"
                "Por favor, cierra y abre MultiTool manualmente para aplicar los cambios."
            )
        return False