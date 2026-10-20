"""
webview2_runner.py - Lanzador de ventanas Microsoft Edge WebView2 para MultiTool
Provee soporte 100% nativo para YouTube Live, transmisiones en directo, DRM, códecs H.264/AAC/VP9/AV1
y autenticación completa de Google sin bloqueos de seguridad.
"""
import sys
import os
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

def lanzar_ventana_webview2(url="https://www.youtube.com", titulo="MultiTool - Navegador Edge WebView2"):
    """Lanza una ventana de navegación con motor nativo Microsoft Edge WebView2 en un proceso independiente y aislado."""
    url_str = url.toString() if hasattr(url, "toString") else str(url)
    if not url_str.startswith(("http://", "https://", "about:", "file://")):
        url_str = "https://" + url_str

    candidates_python = []
    if not getattr(sys, 'frozen', False):
        candidates_python.append(sys.executable)
    
    if shutil.which("python"):
        candidates_python.append(shutil.which("python"))
    if shutil.which("pythonw"):
        candidates_python.append(shutil.which("pythonw"))
    
    candidates_python.extend(["python", "pythonw"])
    
    # Rutas típicas en Windows
    localapp = os.environ.get("LOCALAPPDATA", "")
    if localapp:
        candidates_python.append(os.path.join(localapp, "Programs", "Python", "Python312", "python.exe"))
        candidates_python.append(os.path.join(localapp, "Programs", "Python", "Python311", "python.exe"))

    script_candidates = [
        Path(__file__).resolve().parents[4] / "navegador.py",
        Path(sys.executable).resolve().parent / "navegador.py",
        Path.cwd() / "navegador.py"
    ]
    script_path = next((p for p in script_candidates if p.exists()), None)

    for py in candidates_python:
        if not py: continue
        try:
            if script_path and script_path.exists():
                subprocess.Popen([str(py), str(script_path), url_str])
                return
            else:
                code = (
                    "import sys, webview; "
                    f"webview.create_window('{titulo}', '{url_str}', width=1280, height=800, background_color='#121218'); "
                    "webview.start(gui='edgechromium', debug=False)"
                )
                subprocess.Popen([str(py), "-c", code])
                return
        except Exception:
            continue

    print(f"[WebView2 Runner] Abriendo en navegador del sistema: {url_str}")
    QDesktopServices.openUrl(QUrl(url_str))
