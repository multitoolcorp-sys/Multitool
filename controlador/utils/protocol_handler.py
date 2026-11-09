"""
protocol_handler.py - Gestor de registro de protocolos URL y navegador predeterminado para Windows.
Permite registrar MultiTool como navegador web predeterminado del sistema (http, https, html).
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

from controlador.utils.paths import get_resource_path


def obtener_comando_ejecucion() -> str:
    """Obtiene el comando exacto con el que Windows debe invocar a MultiTool al hacer clic en un enlace."""
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        return f'"{exe_path}" --url "%1"'
    
    main_py = (get_resource_path() / "main.py").resolve()
    py_exe = sys.executable
    pyw_cand = Path(py_exe).parent / "pythonw.exe"
    if pyw_cand.exists():
        py_exe = str(pyw_cand)
    return f'"{py_exe}" "{main_py}" --url "%1"'


def obtener_icono_ruta() -> str:
    """Retorna la ruta absoluta al icono .ico de la aplicación."""
    ico = (get_resource_path() / "vistas" / "utils" / "icono.ico").resolve()
    if ico.exists():
        return str(ico)
    return sys.executable


def registrar_navegador_predeterminado() -> bool:
    """
    Registra MultiTool en el Registro de Windows (HKCU) como cliente web reconocido.
    No requiere privilegios de administrador.
    Abre la configuración de 'Aplicaciones predeterminadas' de Windows para confirmación del usuario.
    """
    if platform.system() != "Windows":
        return False

    try:
        import winreg

        app_cmd = obtener_comando_ejecucion()
        icon_path = obtener_icono_ruta()
        app_name = "MultiTool"
        prog_id = "MultiToolHTML"

        # 1. Registrar ProgID: HKCU\Software\Classes\MultiToolHTML
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{prog_id}") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Documento HTML de MultiTool")
            winreg.SetValueEx(key, "AppUserModelId", 0, winreg.REG_SZ, "google.antigravity.multitool.v1")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{prog_id}\DefaultIcon") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{icon_path}",0')

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{prog_id}\shell\open\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, app_cmd)

        # 2. Registrar protocolos HTTP y HTTPS para el usuario actual
        for proto in ["http", "https"]:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{proto}") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"URL:{proto}")
                winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{proto}\DefaultIcon") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{icon_path}",0')
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{proto}\shell\open\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, app_cmd)

        # 3. Registrar cliente en StartMenuInternet (Estructura oficial para Windows 10/11)
        client_key_path = rf"Software\Clients\StartMenuInternet\{app_name}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, client_key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "MultiTool Navegador")

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{client_key_path}\DefaultIcon") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{icon_path}",0')

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{client_key_path}\shell\open\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, app_cmd)

        # 4. Capabilities (Permite a Windows listar a MultiTool en 'Aplicaciones Predeterminadas')
        cap_path = rf"{client_key_path}\Capabilities"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cap_path) as key:
            winreg.SetValueEx(key, "ApplicationName", 0, winreg.REG_SZ, "MultiTool")
            winreg.SetValueEx(key, "ApplicationDescription", 0, winreg.REG_SZ, "Navegador Web Integrado de MultiTool")
            winreg.SetValueEx(key, "ApplicationIcon", 0, winreg.REG_SZ, f'"{icon_path}",0')

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{cap_path}\FileAssociations") as key:
            winreg.SetValueEx(key, ".htm", 0, winreg.REG_SZ, prog_id)
            winreg.SetValueEx(key, ".html", 0, winreg.REG_SZ, prog_id)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{cap_path}\URLAssociations") as key:
            winreg.SetValueEx(key, "http", 0, winreg.REG_SZ, prog_id)
            winreg.SetValueEx(key, "https", 0, winreg.REG_SZ, prog_id)

        # 5. Registrar en RegisteredApplications
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications") as key:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, rf"{client_key_path}\Capabilities")

        # 6. Abrir configuración de Windows para que el usuario confirme
        try:
            # En Windows 10 y 11 abre directamente la configuración de aplicaciones por defecto
            os.system("start ms-settings:defaultapps")
        except Exception:
            pass

        return True

    except Exception as e:
        print(f"[ProtocolHandler] Error registrando navegador predeterminado: {e}")
        return False


def es_navegador_registrado() -> bool:
    """Verifica si MultiTool está registrado como cliente web en el registro del usuario."""
    if platform.system() != "Windows":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\MultiToolHTML\shell\open\command") as key:
            val, _ = winreg.QueryValueEx(key, "")
            return bool(val)
    except Exception:
        return False

