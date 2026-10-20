"""
navegador.py - Navegador de Alto Rendimiento con Microsoft Edge WebView2 para MultiTool
Permite reproducir YouTube Live, Twitch, DRM, WebRTC y contenido multimedia sin restricciones.
Mantiene las sesiones de Google, contraseñas y credenciales persistentes.
"""

import sys
import os
import logging
from pathlib import Path
import webview

# Silenciar errores benignos de cierre de archivos temporales de Crashpad en Windows
logging.getLogger("pywebview").setLevel(logging.CRITICAL)

def abrir_navegador(url=None, titulo="MultiTool - Navegador"):
    if not url or url.strip() == "":
        url = "https://www.google.com"

    url = url.strip()
    if not url.startswith(("http://", "https://", "about:", "file://")):
        if "." in url and " " not in url:
            url = "https://" + url
        else:
            url = f"https://www.google.com/search?q={url}"

    # Directorio persistente de datos de usuario para guardar sesiones y cookies de Google
    user_data_dir = Path.home() / ".multitool" / "webview2_data"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    # Configuración de WebView2
    webview.settings['ALLOW_DOWNLOADS'] = True
    webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = True

    # Crear ventana con Microsoft Edge WebView2 nativo
    window = webview.create_window(
        title=titulo,
        url=url,
        width=1280,
        height=820,
        resizable=True,
        fullscreen=False,
        min_size=(640, 480),
        background_color='#121218'
    )

    # Iniciar con el motor Edge Chromium persistente
    webview.start(
        gui='edgechromium',
        debug=False,
        private_mode=False,
        storage_path=str(user_data_dir)
    )

if __name__ == '__main__':
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.google.com"
    abrir_navegador(url=target_url)
