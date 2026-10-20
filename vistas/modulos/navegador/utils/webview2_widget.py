"""
webview2_widget.py - Control nativo embebido de Microsoft Edge WebView2 para PyQt6
Permite incrustar el motor Chromium Evergreen oficial de Windows directamente
dentro de las pestañas e interfaces de PyQt6 sin ventanas flotantes separadas.
Incluye soporte para:
- Instalación de extensiones de Chrome Web Store y Edge Addons.
- Identificación auténtica de Microsoft Edge para Edge Rewards.
- Gestión de permisos web (notificaciones, geolocalización, cámara, micrófono, portapapeles).
- Configuración de servidores proxy (directo, sistema, manual HTTP/HTTPS/SOCKS5).
"""

import os
import sys
import json
import time
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QUrl, pyqtSignal, QObject, Qt, QTimer
from PyQt6.QtGui import QWindow, QIcon, QPixmap

from .webview2_scripts import (
    cargar_ensamblados_webview2,
    EDGE_USER_AGENT,
    NOTIFICATION_INTERCEPTOR_SCRIPT,
    obtener_argumentos_navegador,
    desempaquetar_crx_en_perfil
)

WEBVIEW2_AVAILABLE, System, WinForms, WV2, CoreWV2 = cargar_ensamblados_webview2()




class WebView2Widget(QWidget):
    """Widget de PyQt6 que contiene un control WebView2 nativo de Microsoft Edge."""

    urlChanged = pyqtSignal(QUrl)
    titleChanged = pyqtSignal(str)
    iconChanged = pyqtSignal(object)
    loadStarted = pyqtSignal()
    loadFinished = pyqtSignal(bool)
    newWindowRequested = pyqtSignal(str)
    downloadStarting = pyqtSignal(str, str)
    downloadProgress = pyqtSignal(str, int, int)
    downloadCompleted = pyqtSignal(str, str)
    downloadFailed = pyqtSignal(str, str)
    windowCloseRequested = pyqtSignal()
    zoomFactorChanged = pyqtSignal(float)
    webNotificationReceived = pyqtSignal(str, str, str, str)
    fullscreenRequested = pyqtSignal(bool)
    hotkeyPressed = pyqtSignal(str, bool)
    pipStatusChanged = pyqtSignal(bool)

    def __init__(self, parent=None, initial_url="https://www.google.com", user_data_folder=None, initial_zoom=1.0):
        super().__init__(parent)
        self.is_pip_active = False
        self._current_url = QUrl(initial_url)
        self._title = "Página Web"
        self._is_ready = False
        self._pending_url = initial_url
        self._zoom_factor = float(initial_zoom) if initial_zoom else 1.0
        self.is_fullscreen = False
        self.new_window_handler = None
        self._context_menu_opened_time = 0
        
        # Ruta de datos persistentes para sesión de Google / YouTube / Cookies
        if user_data_folder is None:
            try:
                from controlador.utils.paths import get_data_path
                user_data_folder = str(get_data_path() / "browser_data" / "webview2_profile")
            except Exception:
                user_data_folder = str(Path.cwd() / "browser_data" / "webview2_profile")
        self.user_data_folder = user_data_folder
        Path(self.user_data_folder).mkdir(parents=True, exist_ok=True)

        self.bridge = self
        self._init_ui()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        if not WEBVIEW2_AVAILABLE:
            from PyQt6.QtWidgets import QLabel
            lbl_err = QLabel("Microsoft Edge WebView2 no está disponible en este sistema.", self)
            lbl_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(lbl_err)
            return

        # Control WinForms WebView2
        self.wv_control = WV2.WebView2()
        self.wv_control.Dock = WinForms.DockStyle.Fill
        self.wv_control.TabStop = False

        # Panel contenedor WinForms
        self.panel = WinForms.Panel()
        self.panel.Dock = WinForms.DockStyle.Fill
        self.panel.TabStop = False
        self.panel.Controls.Add(self.wv_control)
        self.panel_handle = self.panel.Handle.ToInt64()

        # Incrustar en PyQt6
        self.qwindow = QWindow.fromWinId(self.panel_handle)
        self.container = QWidget.createWindowContainer(self.qwindow, self)
        self.container.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.layout.addWidget(self.container)

        # Conectar eventos de WebView2
        self._conectar_eventos_net()

        # Inicializar entorno persistente con opciones avanzadas (extensiones, proxy, SSO)
        self._inicializar_entorno_async()

    def _conectar_eventos_net(self):
        try:
            self.wv_control.NavigationStarting += self._on_nav_starting
            self.wv_control.NavigationCompleted += self._on_nav_completed
            self.wv_control.SourceChanged += self._on_source_changed
            self.wv_control.CoreWebView2InitializationCompleted += self._on_core_init_completed
            self.wv_control.ZoomFactorChanged += self._on_zoom_factor_changed
            self.wv_control.MouseLeave += self._on_net_mouse_leave
            self.wv_control.MouseUp += self._on_net_mouse_up
            self.panel.MouseLeave += self._on_net_mouse_leave
            self.panel.MouseUp += self._on_net_mouse_up
        except Exception as e:
            print(f"[WebView2Widget] Error al conectar eventos: {e}")

    def _on_net_mouse_leave(self, sender, args):
        try:
            if hasattr(self, "wv_control") and self.wv_control:
                self.wv_control.Capture = False
            if hasattr(self, "panel") and self.panel:
                self.panel.Capture = False
        except Exception:
            pass

    def _on_net_mouse_up(self, sender, args):
        try:
            if hasattr(self, "wv_control") and self.wv_control:
                self.wv_control.Capture = False
            if hasattr(self, "panel") and self.panel:
                self.panel.Capture = False
        except Exception:
            pass

    def _on_zoom_factor_changed(self, sender, args):
        try:
            factor = float(self.wv_control.ZoomFactor)
            self._zoom_factor = factor
            self.bridge.zoomFactorChanged.emit(factor)
        except Exception as e:
            pass

    def _on_nav_starting(self, sender, args):
        self.bridge.loadStarted.emit()

    def _on_nav_completed(self, sender, args):
        success = getattr(args, "IsSuccess", True)
        if self.wv_control and hasattr(self.wv_control, "CoreWebView2") and self.wv_control.CoreWebView2:
            self._title = self.wv_control.CoreWebView2.DocumentTitle or "Página Web"
            self.bridge.titleChanged.emit(self._title)
        if hasattr(self, "_zoom_factor") and self._zoom_factor != 1.0:
            try:
                self.wv_control.ZoomFactor = self._zoom_factor
            except Exception:
                pass
        self.bridge.loadFinished.emit(success)

    def _on_source_changed(self, sender, args):
        if self.wv_control and self.wv_control.Source:
            u_str = self.wv_control.Source.ToString()
            self._current_url = QUrl(u_str)
            self.bridge.urlChanged.emit(self._current_url)

    def _cargar_config_permisos(self):
        """Lee la configuración de permisos del navegador."""
        config_path = Path(self.user_data_folder).parent / "permisos_config.json"
        if not config_path.exists():
            config_path = Path.home() / ".multitool" / "browser_data" / "permisos_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    def _cargar_config_permisos(self):
        cfg_file = Path(self.user_data_folder).parent / "permisos_config.json"
        if cfg_file.exists():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"sitios": {}, "predeterminados": {
            "notificaciones": False,
            "geolocalizacion": False,
            "microfono": False,
            "camara": False,
            "portapapeles": False
        }}

    def _guardar_permiso_sitio(self, origin, key, permitido):
        cfg_file = Path(self.user_data_folder).parent / "permisos_config.json"
        cfg = self._cargar_config_permisos()
        if "sitios" not in cfg:
            cfg["sitios"] = {}
        if origin not in cfg["sitios"]:
            cfg["sitios"][origin] = {}
        cfg["sitios"][origin][key] = bool(permitido)
        try:
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            print(f"[WebView2Widget] Error guardando permiso de sitio: {e}")

    def _on_permission_requested(self, sender, args):
        """Gestiona las solicitudes de permisos de páginas. Por defecto ninguno está activo hasta que el usuario lo permita."""
        try:
            kind_str = str(args.PermissionKind)
            uri = str(getattr(args, "Uri", "") or "")
            
            import urllib.parse
            origin = uri
            try:
                parsed = urllib.parse.urlparse(uri)
                if parsed.scheme and parsed.netloc:
                    origin = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                pass

            key = None
            recurso_nombre = "un recurso del sistema"
            if "Notification" in kind_str:
                key = "notificaciones"
                recurso_nombre = "🔔 Notificaciones"
            elif "Geolocation" in kind_str:
                key = "geolocalizacion"
                recurso_nombre = "📍 Ubicación geográfica"
            elif "Microphone" in kind_str:
                key = "microfono"
                recurso_nombre = "🎤 Micrófono"
            elif "Camera" in kind_str:
                key = "camara"
                recurso_nombre = "📷 Cámara Web"
            elif "Clipboard" in kind_str:
                key = "portapapeles"
                recurso_nombre = "📋 Acceso al Portapapeles"

            cfg = self._cargar_config_permisos()
            sitios = cfg.get("sitios", {})
            sitio_perms = sitios.get(origin, {})

            if key in sitio_perms:
                if sitio_perms[key]:
                    args.State = CoreWV2.CoreWebView2PermissionState.Allow
                else:
                    args.State = CoreWV2.CoreWebView2PermissionState.Deny
                return

            deferral = args.GetDeferral()
            from PyQt6.QtWidgets import QMessageBox

            def _solicitar_usuario():
                try:
                    win = self.window()
                    msg = f"El sitio web:\n{origin}\n\nEstá solicitando permiso para:\n{recurso_nombre}\n\n¿Deseas conceder el permiso a este sitio?"
                    resp = QMessageBox.question(
                        win, "Solicitud de Permiso Web", msg,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    concedido = (resp == QMessageBox.StandardButton.Yes)
                    if concedido:
                        args.State = CoreWV2.CoreWebView2PermissionState.Allow
                    else:
                        args.State = CoreWV2.CoreWebView2PermissionState.Deny
                    self._guardar_permiso_sitio(origin, key, concedido)
                except Exception:
                    try: args.State = CoreWV2.CoreWebView2PermissionState.Deny
                    except: pass
                finally:
                    try: deferral.Complete()
                    except: pass

            QTimer.singleShot(50, _solicitar_usuario)
        except Exception as e:
            try:
                args.State = CoreWV2.CoreWebView2PermissionState.Deny
            except Exception:
                pass

    def _on_core_init_completed(self, sender, args):
        try:
            self._is_ready = getattr(args, "IsSuccess", True)
            if self.wv_control and self.wv_control.CoreWebView2:
                core = self.wv_control.CoreWebView2
                core.NewWindowRequested += self._on_new_window_requested
                core.WindowCloseRequested += self._on_window_close_requested
                core.DownloadStarting += self._on_download_starting
                core.FaviconChanged += self._on_favicon_changed
                core.PermissionRequested += self._on_permission_requested
                core.WebMessageReceived += self._on_web_message_received
                core.ContainsFullScreenElementChanged += self._on_contains_fullscreen_element_changed
                core.ContextMenuRequested += self._on_context_menu_requested
                
                settings = core.Settings
                if settings:
                    settings.AreDevToolsEnabled = True
                    settings.IsScriptEnabled = True
                    settings.IsWebMessageEnabled = True
                    # Configurar User-Agent oficial de Microsoft Edge para Edge Rewards
                    settings.UserAgent = EDGE_USER_AGENT

                # Inyectar interceptor de Notificaciones web para ToastNotification con icono y navegación exacta
                try:
                    core.AddScriptToExecuteOnDocumentCreatedAsync(NOTIFICATION_INTERCEPTOR_SCRIPT)
                except Exception as ex_script:
                    print(f"[WebView2Widget] Advertencia inyectando interceptor de notificaciones: {ex_script}")

                # Aplicar el factor de zoom configurado inicialmente si difiere de 1.0
                if hasattr(self, "_zoom_factor") and self._zoom_factor != 1.0:
                    try:
                        self.wv_control.ZoomFactor = self._zoom_factor
                    except Exception:
                        pass
                    try:
                        self.runJavaScript(f"document.body.style.zoom = '{self._zoom_factor}';")
                    except Exception:
                        pass

                # Cargar URL pendiente si existía
                if self._pending_url:
                    target = self._pending_url
                    self._pending_url = None
                    self.load(target)
        except Exception as e:
            print(f"[WebView2Widget] Error en _on_core_init_completed: {e}")

    def _on_web_message_received(self, sender, args):
        """Intercepta mensajes de JavaScript, procesando notificaciones web para mostrarlas en MultiTool."""
        try:
            raw = None
            try:
                raw = args.TryGetWebMessageAsString()
            except Exception:
                pass
            if not raw and hasattr(args, "WebMessageAsJson"):
                raw = str(args.WebMessageAsJson)
            if raw:
                try:
                    data = json.loads(raw)
                except Exception:
                    data = None
                if isinstance(data, dict) and data.get("type") == "WEB_NOTIFICATION":
                    title = data.get("title", "Notificación Web")
                    body = data.get("body", "")
                    icon = data.get("icon", "")
                    url = data.get("url", "")
                    self.bridge.webNotificationReceived.emit(title, body, icon, url)
                elif isinstance(data, dict) and data.get("type") == "WEBVIEW_HOTKEY":
                    key = str(data.get("key", "")).lower()
                    shift = bool(data.get("shift", False))
                    if key == "s":
                        self._context_menu_opened_time = time.time()
                    self.bridge.hotkeyPressed.emit(key, shift)
                elif isinstance(data, dict) and data.get("type") == "PIP_STATUS_CHANGED":
                    is_pip = bool(data.get("is_pip", False))
                    self.is_pip_active = is_pip
                    self.pipStatusChanged.emit(is_pip)
                elif isinstance(data, dict) and data.get("type") == "PAGE_CLICK":
                    self._context_menu_opened_time = 0
                elif isinstance(data, dict) and data.get("type") == "WEBVIEW_ESCAPE":
                    self.blur_web()
        except Exception as e:
            print(f"[WebView2Widget] Error en _on_web_message_received: {e}")

    def _on_context_menu_requested(self, sender, args):
        """Registra la apertura de menús contextuales para detectar acciones como Guardar imagen/vínculo como..."""
        try:
            self._context_menu_opened_time = time.time()
        except Exception:
            pass

    def _on_window_close_requested(self, sender, args):
        """Disparado cuando la página web solicita cerrar su ventana con window.close()"""
        try:
            self.bridge.windowCloseRequested.emit()
        except Exception as e:
            print(f"[WebView2Widget] Error en WindowCloseRequested: {e}")

    def _on_favicon_changed(self, sender, args):
        try:
            if self.wv_control and hasattr(self.wv_control, "CoreWebView2") and self.wv_control.CoreWebView2:
                uri = self.wv_control.CoreWebView2.FaviconUri
                if uri:
                    self._cargar_favicon_async(str(uri))
        except Exception:
            pass

    def _cargar_favicon_async(self, uri_str):
        import urllib.request
        import threading

        def _fetch():
            try:
                req = urllib.request.Request(uri_str, headers={'User-Agent': EDGE_USER_AGENT})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = resp.read()
                    pix = QPixmap()
                    if pix.loadFromData(data):
                        icon = QIcon(pix)
                        self.bridge.iconChanged.emit(icon)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _on_new_window_requested(self, sender, args):
        try:
            # Si se configuró un manejador delegado para preservar window.opener (OAuth, popups, etc.)
            if hasattr(self, "new_window_handler") and callable(self.new_window_handler):
                try:
                    handled = self.new_window_handler(sender, args)
                    if handled:
                        return
                except Exception as ex:
                    print(f"[WebView2Widget] Error en new_window_handler: {ex}")

            # Fallback convencional
            args.Handled = True
            uri = args.Uri
            if uri:
                self.bridge.newWindowRequested.emit(str(uri))
        except Exception as e:
            print(f"[WebView2Widget] Error en NewWindowRequested: {e}")

    def _on_download_starting(self, sender, args):
        try:
            mime = str(getattr(args.DownloadOperation, "MimeType", "") or "").lower()
            uri = str(getattr(args.DownloadOperation, "Uri", "") or "").lower()
            result_path = str(getattr(args, "ResultFilePath", "") or "")

            # Si es una extensión (.crx o de Web Store), interceptar la descarga hacia temporal,
            # desempaquetar su contenido e instalarla automáticamente en el perfil WebView2
            es_extension = (
                mime == "application/x-chrome-extension" or
                result_path.lower().endswith(".crx") or
                "chromewebstore" in uri or
                "clients2.google.com/service/update2/crx" in uri or
                "edge.microsoft.com/extensionwebstorebase" in uri
            )
            if es_extension:
                args.Cancel = True
                args.Handled = True
                
                original_uri = getattr(args.DownloadOperation, "Uri", None) or uri
                self._descargar_e_instalar_crx_en_segundo_plano(str(original_uri))
                return

            # Cargar configuración de descargas
            config_file = Path(self.user_data_folder).parent / "config.json"
            auto_save = False
            download_dir = str(Path.home() / "Downloads")
            remember_last_dir = True
            last_download_dir = ""

            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        auto_save = cfg.get("auto_save_downloads", False)
                        download_dir = cfg.get("download_dir", str(Path.home() / "Downloads"))
                        remember_last_dir = cfg.get("remember_last_dir", True)
                        last_download_dir = cfg.get("last_download_dir", "")
                except Exception:
                    pass

            filename = Path(result_path).name if result_path else "descarga"

            # Conectar eventos de progreso y finalización
            dl_op = getattr(args, "DownloadOperation", None)
            if dl_op:
                try:
                    dl_op.BytesReceivedChanged += self._on_download_bytes_received
                    dl_op.StateChanged += self._on_download_state_changed
                except Exception as ex_hook:
                    print(f"[WebView2Widget] Error conectando DownloadOperation: {ex_hook}")

            # 1. Detectar si el usuario ya eligió una ruta explícita mediante "Guardar como..." / "Guardar imagen como..."
            now = time.time()
            from_context_menu = (now - getattr(self, "_context_menu_opened_time", 0)) < 120
            is_custom_path = (
                result_path and Path(result_path).parent.exists() and
                str(Path(result_path).parent) != download_dir and
                str(Path(result_path).parent) != str(Path.home() / "Downloads")
            )

            if from_context_menu or is_custom_path:
                self._context_menu_opened_time = 0
                args.Handled = True
                if remember_last_dir and result_path:
                    try:
                        self._guardar_ultima_carpeta_descarga(config_file, str(Path(result_path).parent))
                    except Exception:
                        pass
                self.bridge.downloadStarting.emit(uri, result_path)
                return

            # 2. Descarga regular iniciada por clic en página:
            if auto_save:
                dest_dir = download_dir if (download_dir and Path(download_dir).exists()) else str(Path.home() / "Downloads")
                Path(dest_dir).mkdir(parents=True, exist_ok=True)
                target_file = str(Path(dest_dir) / filename)
                args.ResultFilePath = target_file
                result_path = target_file
                args.Handled = True
                self.bridge.downloadStarting.emit(uri, result_path)
            else:
                deferral = args.GetDeferral()
                win_parent = self.window() or self
                try:
                    from PyQt6.QtWidgets import QFileDialog
                    if remember_last_dir and last_download_dir and Path(last_download_dir).exists():
                        initial_folder = last_download_dir
                    elif download_dir and Path(download_dir).exists():
                        initial_folder = download_dir
                    else:
                        initial_folder = str(Path.home() / "Downloads")

                    initial_path = str(Path(initial_folder) / filename)
                    suffix = Path(filename).suffix
                    filtro = f"Archivos (*{suffix});;Todos los archivos (*.*)" if suffix else "Todos los archivos (*.*)"

                    target_file, _ = QFileDialog.getSaveFileName(
                        win_parent, "Guardar archivo como...", initial_path, filtro
                    )
                    if target_file:
                        target_file = os.path.normpath(target_file)
                        args.ResultFilePath = target_file
                        result_path = target_file
                        args.Handled = True
                        if remember_last_dir:
                            self._guardar_ultima_carpeta_descarga(config_file, str(Path(target_file).parent))
                        self.bridge.downloadStarting.emit(uri, result_path)
                    else:
                        args.Cancel = True
                        args.Handled = True
                finally:
                    if deferral:
                        try:
                            deferral.Complete()
                        except Exception:
                            pass
                    try:
                        if win_parent:
                            win_parent.activateWindow()
                            win_parent.raise_()
                    except Exception:
                        pass
        except Exception as e:
            print(f"[WebView2Widget] Error en _on_download_starting: {e}")

    def _on_download_bytes_received(self, sender, args):
        """Notifica el progreso de bytes descargados en tiempo real."""
        try:
            recv = int(sender.BytesReceived)
            total = int(sender.TotalBytesToReceive)
            fpath = str(sender.ResultFilePath or "")
            self.bridge.downloadProgress.emit(fpath, recv, total)
        except Exception:
            pass

    def _on_download_state_changed(self, sender, args):
        """Notifica cuando la descarga se completa exitosamente o es interrumpida."""
        try:
            state_str = str(sender.State)
            fpath = str(sender.ResultFilePath or "")
            uri = str(sender.Uri or "")
            if "Completed" in state_str:
                self.bridge.downloadCompleted.emit(fpath, uri)
            elif "Interrupted" in state_str:
                reason = str(getattr(sender, "InterruptReason", "Cancelado o Error"))
                self.bridge.downloadFailed.emit(fpath, reason)
        except Exception:
            pass

    def _on_contains_fullscreen_element_changed(self, sender, args):
        try:
            is_fs = bool(self.wv_control.CoreWebView2.ContainsFullScreenElement)
            self.bridge.fullscreenRequested.emit(is_fs)
        except Exception as e:
            print(f"[WebView2Widget] Error en ContainsFullScreenElementChanged: {e}")


    def _guardar_ultima_carpeta_descarga(self, config_file, folder_path):
        try:
            cfg = {}
            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                except Exception:
                    pass
            cfg["last_download_dir"] = str(folder_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def _descargar_e_instalar_crx_en_segundo_plano(self, uri):
        """Descarga una extensión .CRX en segundo plano usando endpoints de Chrome y Edge."""
        import threading
        def _worker():
            try:
                import urllib.request, io, zipfile, uuid, json, re
                from pathlib import Path
                m = re.search(r'([a-z]{32})', str(uri).lower())
                ext_id = m.group(1) if m else ""
                cands = [uri] if str(uri).startswith("http") else []
                if ext_id:
                    cands.append(f"https://clients2.google.com/service/update2/crx?response=redirect&prodversion=120.0.6099.130&acceptformat=crx2,crx3&x=id%3D{ext_id}%26uc")
                    cands.append(f"https://edge.microsoft.com/extensionwebstorebase/v1/crx?response=redirect&prod=chromiumcrx&prodchannel=&x=id%3D{ext_id}%26installsource%3Dondemand%26uc")
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                data = None
                for u in cands:
                    try:
                        req = urllib.request.Request(u, headers=headers)
                        with urllib.request.urlopen(req, timeout=25) as resp:
                            res = resp.read()
                            if res and res.find(b"PK\x03\x04") != -1:
                                data = res
                                break
                    except Exception:
                        pass
                if not data:
                    print(f"[WebView2Widget] No se pudo descargar la extensión: {uri}")
                    return
                ext_base = Path(self.user_data_folder) / "extensions"
                ext_base.mkdir(parents=True, exist_ok=True)
                zf = zipfile.ZipFile(io.BytesIO(data[data.find(b"PK\x03\x04"):]))
                manifest = json.loads(zf.read("manifest.json").decode("utf-8", errors="ignore"))
                raw_name = manifest.get("name", ext_id or "extension")
                if str(raw_name).startswith("__MSG_"):
                    raw_name = manifest.get("short_name", ext_id or "extension")
                ext_name = re.sub(r'[\\/*?:"<>| ]', "_", str(raw_name))
                dest_dir = ext_base / f"{ext_name}_{manifest.get('version', '1.0')}_{uuid.uuid4().hex[:6]}"
                dest_dir.mkdir(parents=True, exist_ok=True)
                zf.extractall(dest_dir)
                self.add_unpacked_extension_async(str(dest_dir))
            except Exception as e:
                print(f"[WebView2Widget] Error en descarga segura de extensión: {e}")
        threading.Thread(target=_worker, daemon=True).start()

    def clear_browsing_data_async(self, data_kinds_mask, callback=None):
        """Borra datos de navegación en el perfil CoreWebView2 según la máscara seleccionada."""
        try:
            if self.wv_control and self.wv_control.CoreWebView2 and hasattr(self.wv_control.CoreWebView2, "Profile"):
                profile = self.wv_control.CoreWebView2.Profile
                task = profile.ClearBrowsingDataAsync(data_kinds_mask)
                def _on_cleared(t):
                    try:
                        if callback and callable(callback):
                            callback(True)
                    except Exception:
                        pass
                task.ContinueWith(System.Action[System.Threading.Tasks.Task](_on_cleared))
                return True
        except Exception as e:
            print(f"[WebView2Widget] Error en clear_browsing_data_async: {e}")
            if callback and callable(callback):
                callback(False)
        return False

    def open_download_dialog(self):
        """Abre el menú flotante nativo de descargas de Microsoft Edge WebView2."""
        try:
            if self.wv_control and hasattr(self.wv_control, "CoreWebView2") and self.wv_control.CoreWebView2:
                self.wv_control.CoreWebView2.OpenDefaultDownloadDialog()
                return True
        except Exception as e:
            print(f"[WebView2Widget] Error al abrir diálogo de descargas: {e}")
        return False

    def _instalar_extension_desde_crx_async(self, crx_path):
        """Desempaqueta un archivo CRX y lo instala en el perfil de CoreWebView2."""
        import threading
        def _worker():
            try:
                dest_dir = desempaquetar_crx_en_perfil(crx_path, self.user_data_folder)
                if dest_dir:
                    self.add_unpacked_extension_async(dest_dir)
            except Exception as e:
                print(f"[WebView2Widget] Error instalando extensión desde CRX: {e}")
        threading.Thread(target=_worker, daemon=True).start()

    def add_unpacked_extension_async(self, folder_path, callback=None):
        """Instala una extensión desempaquetada en el Profile de WebView2."""
        try:
            if self.wv_control and self.wv_control.CoreWebView2 and hasattr(self.wv_control.CoreWebView2, "Profile"):
                profile = self.wv_control.CoreWebView2.Profile
                task = profile.AddBrowserExtensionAsync(str(Path(folder_path).resolve()))

                def _on_done(t):
                    try:
                        ext = t.Result
                        ext_name = ext.Name if hasattr(ext, "Name") else Path(folder_path).name
                        print(f"[WebView2Widget] Extensión instalada con éxito en WebView2: {ext_name}")
                        try:
                            from vistas.utils.notification import show_notification
                            show_notification("MultiTool - Extensiones", f"✅ Extensión instalada: {ext_name}", "info")
                        except Exception:
                            pass
                        if callback and callable(callback):
                            callback(True)
                    except Exception as ex:
                        print(f"[WebView2Widget] Error en AddBrowserExtensionAsync: {ex}")
                        if callback and callable(callback):
                            callback(False)

                task.ContinueWith(System.Action[System.Threading.Tasks.Task[CoreWV2.CoreWebView2BrowserExtension]](_on_done))
                return True
        except Exception as e:
            print(f"[WebView2Widget] Error al invocar AddBrowserExtensionAsync: {e}")
        return False

    def remove_browser_extension_by_folder(self, folder_path):
        """Elimina una extensión del Profile de WebView2 por carpeta."""
        try:
            if self.wv_control and self.wv_control.CoreWebView2 and hasattr(self.wv_control.CoreWebView2, "Profile"):
                profile = self.wv_control.CoreWebView2.Profile
                task = profile.GetBrowserExtensionsAsync()
                def _on_got(t):
                    try:
                        exts = t.Result
                        f_name = Path(folder_path).name.lower()
                        for ext in exts:
                            if ext.Name.lower() in f_name or f_name in ext.Name.lower():
                                ext.RemoveAsync()
                    except Exception:
                        pass
                task.ContinueWith(System.Action[System.Threading.Tasks.Task[System.Collections.Generic.IReadOnlyList[CoreWV2.CoreWebView2BrowserExtension]]](_on_got))
        except Exception as e:
            print(f"[WebView2Widget] Error en remove_browser_extension_by_folder: {e}")

    def _obtener_argumentos_navegador(self):
        """Construye los argumentos Chromium incluyendo extensiones, UserAgent y Proxy."""
        return obtener_argumentos_navegador(self.user_data_folder)

    def _inicializar_entorno_async(self):
        """Crea el entorno CoreWebView2Environment con soporte de extensiones, proxy y SSO."""
        try:
            opts = CoreWV2.CoreWebView2EnvironmentOptions()
            opts.AreBrowserExtensionsEnabled = True
            opts.AllowSingleSignOnUsingOSPrimaryAccount = True
            opts.AdditionalBrowserArguments = self._obtener_argumentos_navegador()

            task = CoreWV2.CoreWebView2Environment.CreateAsync(None, self.user_data_folder, opts)

            def _on_env_created(t):
                try:
                    env = t.Result
                    def _invoke_ensure():
                        try:
                            self.wv_control.EnsureCoreWebView2Async(env)
                        except Exception as ex:
                            print(f"[WebView2Widget] Error al invocar EnsureCoreWebView2Async: {ex}")
                    self.wv_control.BeginInvoke(System.Action(_invoke_ensure))
                except Exception as ex:
                    print(f"[WebView2Widget] Error al resolver entorno: {ex}")
                    # Fallback directo en UI thread
                    def _fallback_ensure():
                        try:
                            self.wv_control.EnsureCoreWebView2Async(None)
                        except Exception:
                            pass
                    self.wv_control.BeginInvoke(System.Action(_fallback_ensure))

            task.ContinueWith(System.Action[System.Threading.Tasks.Task[CoreWV2.CoreWebView2Environment]](_on_env_created))
        except Exception as e:
            print(f"[WebView2Widget] Fallback a inicialización básica: {e}")
            try:
                self.wv_control.EnsureCoreWebView2Async(None)
            except Exception:
                pass

    # --- API Compatible con QWebEngineView / Navegador ---

    def load(self, url):
        url_str = url.toString() if isinstance(url, QUrl) else str(url)
        url_str = url_str.strip()
        if not url_str.startswith(("http://", "https://", "about:", "file://")):
            if "." in url_str and " " not in url_str:
                url_str = "https://" + url_str
            else:
                url_str = f"https://www.google.com/search?q={url_str}"
        self._current_url = QUrl(url_str)
        try:
            if hasattr(self, "wv_control") and self.wv_control:
                if self._is_ready:
                    self.wv_control.Source = System.Uri(url_str)
                else:
                    self._pending_url = url_str
        except Exception as e:
            print(f"[WebView2Widget] Error al cargar URL ({url_str}): {e}")

    def setUrl(self, url):
        self.load(url)

    def url(self):
        if hasattr(self, "wv_control") and self.wv_control and self.wv_control.Source:
            return QUrl(self.wv_control.Source.ToString())
        return self._current_url

    def title(self):
        if hasattr(self, "wv_control") and hasattr(self.wv_control, "CoreWebView2") and self.wv_control.CoreWebView2:
            return self.wv_control.CoreWebView2.DocumentTitle or self._title
        return self._title

    def back(self):
        try:
            if hasattr(self, "wv_control") and self.wv_control.CanGoBack:
                self.wv_control.GoBack()
        except Exception:
            pass

    def forward(self):
        try:
            if hasattr(self, "wv_control") and self.wv_control.CanGoForward:
                self.wv_control.GoForward()
        except Exception:
            pass

    def reload(self):
        try:
            if hasattr(self, "wv_control") and self.wv_control:
                self.wv_control.Reload()
        except Exception:
            pass

    def stop(self):
        try:
            if hasattr(self, "wv_control") and self.wv_control:
                self.wv_control.Stop()
        except Exception:
            pass

    def runJavaScript(self, code, callback=None):
        try:
            if self.wv_control and hasattr(self.wv_control, "CoreWebView2") and self.wv_control.CoreWebView2:
                task = self.wv_control.CoreWebView2.ExecuteScriptAsync(code)
                if callback:
                    def _on_done(t):
                        try:
                            res = t.Result
                            if callback:
                                callback(res)
                        except Exception:
                            if callback:
                                callback(None)
                    task.ContinueWith(System.Action[System.Threading.Tasks.Task[System.String]](_on_done))
        except Exception as e:
            print(f"[WebView2Widget] Error al ejecutar JavaScript: {e}")

    def dispose_browser(self):
        """Detiene la reproducción, silencia buffers de audio/video y libera el control."""
        try:
            if self.wv_control:
                if hasattr(self.wv_control, "CoreWebView2") and self.wv_control.CoreWebView2:
                    try:
                        self.wv_control.CoreWebView2.IsMuted = True
                        self.wv_control.CoreWebView2.ExecuteScriptAsync("""
                            document.querySelectorAll('video, audio').forEach(el => {
                                el.pause();
                                el.src = '';
                            });
                        """)
                    except Exception:
                        pass
                self.wv_control.Stop()
                self.wv_control.Source = System.Uri("about:blank")
                self.wv_control.Dispose()
                self.wv_control = None
            if hasattr(self, "panel") and self.panel:
                self.panel.Dispose()
                self.panel = None
        except Exception as e:
            print(f"[WebView2Widget] Error al liberar control: {e}")

    def setZoomFactor(self, factor):
        """Establece el nivel de zoom del control WebView2 (1.0 = 100%)."""
        try:
            factor = max(0.25, min(5.0, float(factor)))
            self._zoom_factor = factor
            if hasattr(self, "wv_control") and self.wv_control:
                try:
                    self.wv_control.ZoomFactor = factor
                except Exception:
                    pass
            self.runJavaScript(f"document.body.style.zoom = '{factor}';")
        except Exception:
            pass

    def zoomFactor(self):
        """Retorna el nivel de zoom actual."""
        try:
            if hasattr(self, "wv_control") and hasattr(self.wv_control, "ZoomFactor"):
                zf = float(self.wv_control.ZoomFactor)
                if zf > 0:
                    return zf
        except Exception:
            pass
        return getattr(self, "_zoom_factor", 1.0)

    def open_devtools(self):
        """Abre las Herramientas de Desarrollador de Chromium."""
        try:
            if self.wv_control and hasattr(self.wv_control, "CoreWebView2") and self.wv_control.CoreWebView2:
                self.wv_control.CoreWebView2.OpenDevToolsWindow()
        except Exception as e:
            print(f"[WebView2Widget] Error al abrir DevTools: {e}")

    def findText(self, text):
        pass

    def page(self):
        return self

    def blur_web(self):
        """Desenfoca cualquier campo de texto activo en la página web y libera capturas de mouse/teclado."""
        try:
            if hasattr(self, "wv_control") and self.wv_control:
                self.wv_control.Capture = False
                if hasattr(self.wv_control, "CoreWebView2") and self.wv_control.CoreWebView2:
                    self.wv_control.CoreWebView2.ExecuteScriptAsync(
                        "if (document.activeElement && typeof document.activeElement.blur === 'function') { document.activeElement.blur(); }"
                    )
        except Exception:
            pass

        try:
            if hasattr(self, "panel") and self.panel:
                self.panel.Capture = False
                self.panel.Select()
        except Exception:
            pass

        if hasattr(self, "container") and self.container:
            try:
                self.container.clearFocus()
            except Exception:
                pass

        try:
            self.clearFocus()
        except Exception:
            pass

        try:
            win = self.window()
            if win and win != self:
                win.setFocus()
                win.activateWindow()
        except Exception:
            pass

    def hideEvent(self, event):
        super().hideEvent(event)
        self.blur_web()
        try:
            if hasattr(self, "wv_control") and self.wv_control:
                self.wv_control.Capture = False
                self.wv_control.Visible = False
            if hasattr(self, "panel") and self.panel:
                self.panel.Capture = False
                self.panel.Visible = False
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        try:
            if hasattr(self, "panel") and self.panel:
                self.panel.Visible = True
            if hasattr(self, "wv_control") and self.wv_control:
                self.wv_control.Visible = True
        except Exception:
            pass

