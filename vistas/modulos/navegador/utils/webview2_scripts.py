"""
webview2_scripts.py - Scripts inyectados, User-Agent y configuración de argumentos para Microsoft Edge WebView2
"""

import json
from pathlib import Path

EDGE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"

NOTIFICATION_INTERCEPTOR_SCRIPT = """
(function() {
    if (window.__multitool_notification_installed__) return;
    window.__multitool_notification_installed__ = true;

    function CustomNotification(title, options) {
        options = options || {};
        var iconUrl = options.icon || '';
        if (iconUrl && !iconUrl.startsWith('http://') && !iconUrl.startsWith('https://') && !iconUrl.startsWith('data:')) {
            try {
                iconUrl = new URL(iconUrl, window.location.href).href;
            } catch(e) {}
        }
        if (!iconUrl) {
            var link = document.querySelector("link[rel*='icon']");
            if (link && link.href) {
                iconUrl = link.href;
            }
        }

        var payload = {
            type: 'WEB_NOTIFICATION',
            title: String(title || ''),
            body: String(options.body || ''),
            icon: iconUrl,
            url: window.location.href
        };

        try {
            if (window.chrome && window.chrome.webview && window.chrome.webview.postMessage) {
                window.chrome.webview.postMessage(JSON.stringify(payload));
            }
        } catch(e) {}

        var self = this;
        this.title = title;
        this.body = options.body || '';
        this.icon = iconUrl;
        this.tag = options.tag || '';
        this.data = options.data || null;
        this.onclick = null;
        this.onclose = null;
        this.onerror = null;
        this.onshow = null;

        setTimeout(function() {
            if (typeof self.onshow === 'function') {
                try { self.onshow(new Event('show')); } catch(e) {}
            }
        }, 40);

        this.close = function() {
            if (typeof self.onclose === 'function') {
                try { self.onclose(new Event('close')); } catch(e) {}
            }
        };
    }

    CustomNotification.permission = 'granted';
    CustomNotification.requestPermission = function(cb) {
        if (typeof cb === 'function') cb('granted');
        return Promise.resolve('granted');
    };

    try {
        Object.defineProperty(window, 'Notification', {
            value: CustomNotification,
            writable: true,
            configurable: true
        });
    } catch(e) {
        window.Notification = CustomNotification;
    }

    if (typeof ServiceWorkerRegistration !== 'undefined' && ServiceWorkerRegistration.prototype) {
        try {
            ServiceWorkerRegistration.prototype.showNotification = function(title, options) {
                new CustomNotification(title, options);
                return Promise.resolve();
            };
        } catch(e) {}
    }

    // Interceptor global de atajos de teclado para que Ctrl+T, Ctrl+W, Ctrl+R siempre funcionen en MultiTool
    window.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            if (document.activeElement && typeof document.activeElement.blur === 'function') {
                document.activeElement.blur();
            }
            if (window.chrome && window.chrome.webview && window.chrome.webview.postMessage) {
                window.chrome.webview.postMessage(JSON.stringify({
                    type: 'WEBVIEW_ESCAPE'
                }));
            }
            return;
        }

        if (e.ctrlKey && !e.altKey) {
            var k = e.key.toLowerCase();
            if (k === 't' || k === 'w' || k === 'r' || k === 'd' || k === 'p' || k === '+' || k === '=' || k === '-') {
                if (window.chrome && window.chrome.webview && window.chrome.webview.postMessage) {
                    window.chrome.webview.postMessage(JSON.stringify({
                        type: 'WEBVIEW_HOTKEY',
                        key: k,
                        shift: !!e.shiftKey
                    }));
                    if (k === 't' || k === 'w' || k === 'd') {
                        e.preventDefault();
                        e.stopPropagation();
                    }
                }
            }
        }
    }, true);

    // Notificar clics ordinarios en la página para restablecer estado de menú contextual
    window.addEventListener('mousedown', function(e) {
        if (e.button === 0 && window.chrome && window.chrome.webview && window.chrome.webview.postMessage) {
            try {
                window.chrome.webview.postMessage(JSON.stringify({ type: 'PAGE_CLICK' }));
            } catch(ex) {}
        }
    }, true);

    // Preservar la selección natural de texto, botones, dropdowns e interacción nativa del usuario
    // --- DETECCIÓN DE IMAGEN EN IMAGEN (PiP) Y SALTO DE ANUNCIOS EN 10 SEGUNDOS ---
    var _lastPipState = false;
    function _notifyPip(active) {
        if (_lastPipState !== active) {
            _lastPipState = active;
            try {
                if (window.chrome && window.chrome.webview && window.chrome.webview.postMessage) {
                    window.chrome.webview.postMessage(JSON.stringify({
                        type: 'PIP_STATUS_CHANGED',
                        is_pip: active
                    }));
                }
            } catch(e) {}
        }
    }

    document.addEventListener('enterpictureinpicture', function(e) {
        _notifyPip(true);
    }, true);

    document.addEventListener('leavepictureinpicture', function(e) {
        _notifyPip(false);
    }, true);

    setInterval(function() {
        var isPip = !!(document.pictureInPictureElement || (window.documentPictureInPicture && window.documentPictureInPicture.window));
        _notifyPip(isPip);
    }, 1500);

    // Función universal para saltar anuncios de video (YouTube y reproductores web)
    function _intentarSaltarAnuncio() {
        var skipSelectors = [
            '.ytp-skip-ad-button',
            '.ytp-ad-skip-button',
            '.ytp-ad-skip-button-modern',
            'button.ytp-ad-skip-button-text',
            '.ytp-ad-skip-button-icon',
            '.videoAdUiSkipButton',
            '.ytp-ad-overlay-close-button',
            '[id*=\"skip-button\"] button',
            'button[class*=\"skip__button\"]'
        ];
        for (var i = 0; i < skipSelectors.length; i++) {
            var btn = document.querySelector(skipSelectors[i]);
            if (btn && (btn.offsetWidth > 0 || btn.offsetHeight > 0)) {
                try {
                    btn.click();
                    return true;
                } catch(e) {}
            }
        }
        var adContainer = document.querySelector('.ad-showing, .ad-interrupting');
        if (adContainer) {
            var v = adContainer.querySelector('video') || document.querySelector('video');
            if (v && !isNaN(v.duration) && isFinite(v.duration)) {
                try {
                    v.currentTime = v.duration;
                    return true;
                } catch(e) {}
            }
        }
        return false;
    }

    // Interceptar los botones de control de Picture-in-Picture / MediaSession (Adelantar 10s y Siguiente)
    if (navigator.mediaSession && typeof navigator.mediaSession.setActionHandler === 'function') {
        try {
            navigator.mediaSession.setActionHandler('seekforward', function(details) {
                if (_intentarSaltarAnuncio()) {
                    return;
                }
                var v = document.pictureInPictureElement || document.querySelector('video');
                if (v) {
                    var sec = (details && details.seekOffset) ? details.seekOffset : 10;
                    v.currentTime = Math.min(v.duration || Infinity, v.currentTime + sec);
                }
            });
        } catch(e) {}

        try {
            navigator.mediaSession.setActionHandler('nexttrack', function() {
                if (_intentarSaltarAnuncio()) {
                    return;
                }
            });
        } catch(e) {}
    }
})();
"""


def obtener_argumentos_navegador(user_data_folder):
    """Construye los argumentos Chromium incluyendo extensiones, UserAgent y Proxy."""
    args_list = [
        "--enable-features=msEdgeExtensions,msEdgeStoreExtensionInstall,Extensions",
        f'--user-agent="{EDGE_USER_AGENT}"'
    ]

    # Consultar configuración de proxy
    proxy_cfg_file = Path(user_data_folder).parent / "proxy_config.json"
    if not proxy_cfg_file.exists():
        proxy_cfg_file = Path.home() / ".multitool" / "browser_data" / "proxy_config.json"

    if proxy_cfg_file.exists():
        try:
            with open(proxy_cfg_file, "r", encoding="utf-8") as f:
                pcfg = json.load(f)
                modo = pcfg.get("modo", "directo")
                if modo == "manual":
                    tipo = pcfg.get("tipo", "http")
                    host = pcfg.get("host", "").strip()
                    puerto = pcfg.get("puerto", "").strip()
                    bypass = pcfg.get("bypass", "<local>;localhost;127.0.0.1").strip()
                    if host and puerto:
                        args_list.append(f'--proxy-server="{tipo}://{host}:{puerto}"')
                        if bypass:
                            args_list.append(f'--proxy-bypass-list="{bypass}"')
                elif modo == "directo":
                    args_list.append("--no-proxy-server")
        except Exception:
            pass

    return " ".join(args_list)


def desempaquetar_crx_en_perfil(crx_path, user_data_folder):
    """Desempaqueta un archivo CRX y devuelve la ruta de la carpeta resultante."""
    import io
    import zipfile
    import uuid

    crx_file = Path(crx_path)
    if not crx_file.exists():
        return None

    data = crx_file.read_bytes()
    zip_offset = data.find(b"PK\x03\x04")
    if zip_offset == -1:
        print("[WebView2Scripts] El archivo CRX descargado no tiene formato ZIP válido")
        return None

    ext_base = Path(user_data_folder) / "extensions"
    ext_base.mkdir(parents=True, exist_ok=True)

    zip_bytes = io.BytesIO(data[zip_offset:])
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        manifest_raw = zf.read("manifest.json").decode("utf-8", errors="ignore")
        manifest_data = json.loads(manifest_raw)
        ext_name = manifest_data.get("name", "extension").replace(" ", "_")
        ext_version = manifest_data.get("version", "1.0")
        dest_dir = ext_base / f"{ext_name}_{ext_version}_{uuid.uuid4().hex[:6]}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        zf.extractall(dest_dir)

    try:
        crx_file.unlink()
    except Exception:
        pass

    return str(dest_dir)


def cargar_ensamblados_webview2():
    """Carga los ensamblados CLR de Microsoft.Web.WebView2."""
    import os
    import sys

    base_paths = [
        Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None,
        Path(__file__).resolve().parents[4],
        Path.cwd()
    ]
    for bp in base_paths:
        if bp and bp.exists() and str(bp) not in sys.path:
            sys.path.insert(0, str(bp))

    try:
        import clr
        import webview
    except Exception as e:
        print(f"[WebView2Scripts] No se pudo importar clr/webview: {e}")
        return False, None, None, None, None

    try:
        webview_dir = os.path.dirname(webview.__file__)
        dll_core = os.path.join(webview_dir, "lib", "Microsoft.Web.WebView2.Core.dll")
        dll_winforms = os.path.join(webview_dir, "lib", "Microsoft.Web.WebView2.WinForms.dll")

        if not os.path.exists(dll_core):
            for bp in base_paths:
                if bp:
                    candidate = bp / "webview" / "lib" / "Microsoft.Web.WebView2.Core.dll"
                    if candidate.exists():
                        dll_core = str(candidate)
                        dll_winforms = str(bp / "webview" / "lib" / "Microsoft.Web.WebView2.WinForms.dll")
                        break

        clr.AddReference(dll_core)
        clr.AddReference(dll_winforms)
        clr.AddReference("System.Windows.Forms")
        import System
        import System.Windows.Forms as WinForms
        import Microsoft.Web.WebView2.WinForms as WV2
        import Microsoft.Web.WebView2.Core as CoreWV2
        return True, System, WinForms, WV2, CoreWV2
    except Exception as e:
        print(f"[WebView2Scripts] Error al cargar ensamblados WebView2: {e}")
        return False, None, None, None, None

