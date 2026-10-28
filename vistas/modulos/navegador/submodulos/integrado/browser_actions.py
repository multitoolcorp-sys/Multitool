"""
browser_actions.py - Manejadores de acciones, menús contextuales, descargas y atajos para MultiTabBrowser
"""

import os
import time
from pathlib import Path
from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import QUrl, Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QActionGroup
from PyQt6.sip import isdeleted

from .container import generar_icono_por_defecto, obtener_o_generar_icono
from .dialogs import BrowserPopupWindow


class BrowserActionsHandler:
    """Manejador de acciones secundarias (menús contextuales, descargas, atajos y notificaciones)."""

    def __init__(self, browser):
        self.b = browser

    def mostrar_menu_pestanas(self, pos):
        """Muestra el menú contextual de la pestaña (fijar, política de reposo, cerrar, etc.)."""
        tab_bar = self.b.tabs.tabBar()
        tab_idx = tab_bar.tabAt(pos)
        if tab_idx < 0:
            tab_idx = self.b.tabs.currentIndex()

        container = self.b.tabs.widget(tab_idx)
        is_pinned = getattr(container, "is_pinned", False) if container else False
        is_sleeping = getattr(container, "is_sleeping", False) if container else False
        sleep_mode = getattr(container, "sleep_mode", "default") if container else "default"

        menu = QMenu(self.b)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {self.b.colores['bg_secundario']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', Arial;
            }}
            QMenu::item {{
                padding: 7px 22px;
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background: {self.b.colores['acento']};
                color: #FFFFFF;
            }}
            QMenu::separator {{
                height: 1px;
                background: rgba(255, 255, 255, 0.1);
                margin: 4px 8px;
            }}
        """)

        if is_pinned:
            act_pin = menu.addAction("📍 Desfijar Pestaña")
            act_pin.triggered.connect(lambda: self.b.toggle_pin_tab(tab_idx))
        else:
            act_pin = menu.addAction("📌 Fijar Pestaña")
            act_pin.triggered.connect(lambda: self.b.toggle_pin_tab(tab_idx))

        menu.addSeparator()

        # --- POLÍTICA DE MODO REPOSO POR PESTAÑA ---
        group_sleep = QActionGroup(menu)
        group_sleep.setExclusive(True)

        act_mode_default = menu.addAction("🌐 Modo reposo: General (según ajustes)")
        act_mode_default.setCheckable(True)
        act_mode_default.setChecked(sleep_mode == "default")
        act_mode_default.triggered.connect(lambda: self.b.establecer_modo_reposo_pestana(tab_idx, "default"))
        group_sleep.addAction(act_mode_default)

        act_mode_always = menu.addAction("🛡️ Modo reposo: Siempre activa (Sin reposo)")
        act_mode_always.setCheckable(True)
        act_mode_always.setChecked(sleep_mode == "always_active")
        act_mode_always.triggered.connect(lambda: self.b.establecer_modo_reposo_pestana(tab_idx, "always_active"))
        group_sleep.addAction(act_mode_always)

        menu.addSeparator()

        if is_sleeping:
            act_wake = menu.addAction("⚡ Despertar Pestaña")
            act_wake.triggered.connect(lambda: self.b.despertar_pestana(tab_idx))
        else:
            act_sleep = menu.addAction("💤 Poner en Reposo (Suspender)")
            act_sleep.triggered.connect(lambda: self.b.dormir_pestana(tab_idx))
            if sleep_mode == "always_active":
                act_sleep.setEnabled(False)
                act_sleep.setText("💤 Poner en Reposo (Deshabilitado: Siempre activa)")

        act_cfg_sleep = menu.addAction("⚙️ Configurar Ahorro de RAM...")
        act_cfg_sleep.triggered.connect(self.b.mostrar_dialogo_configuracion_reposo)

        menu.addSeparator()

        act_new = menu.addAction("➕ Nueva Pestaña (Ctrl+T)")
        act_new.triggered.connect(lambda: self.b.add_new_tab())

        act_reload = menu.addAction("🔄 Recargar Pestaña (Ctrl+R)")
        act_reload.triggered.connect(self.b.reload_page)

        menu.addSeparator()

        act_fav = menu.addAction("⭐ Guardar en Favoritos (Ctrl+D)")
        act_fav.triggered.connect(self.b.guardar_marcador_actual)

        menu.addSeparator()

        act_close = menu.addAction("✖ Cerrar Pestaña (Ctrl+W)")
        act_close.triggered.connect(lambda: self.b.close_tab(tab_idx))
        if self.b.tabs.count() <= 1:
            act_close.setEnabled(False)

        menu.exec(tab_bar.mapToGlobal(pos))

    def configurar_atajos_teclado(self):
        """Configura los atajos de teclado globales del navegador."""
        shortcuts = [
            ("Ctrl+T", lambda: self.b.add_new_tab()),
            ("Ctrl+W", lambda: self.b.close_tab(self.b.tabs.currentIndex())),
            ("Ctrl+R", self.b.reload_page),
            ("F5", self.b.reload_page),
            ("Ctrl+H", self.b.abrir_historial_submodulo),
            ("Ctrl+J", self.abrir_pestana_descargas),
            ("Ctrl+D", self.b.guardar_marcador_actual),
            ("Ctrl+F", self.b.mostrar_barra_busqueda),
            ("Ctrl+P", self.b.imprimir_pagina),
            ("F11", lambda: self.b.toggle_fullscreen_mode()),
            ("Ctrl++", self.b.zoom_in),
            ("Ctrl+=", self.b.zoom_in),
            ("Ctrl+-", self.b.zoom_out),
            ("Ctrl+0", self.b.reset_zoom),
            ("Alt+Left", self.b.navigate_back),
            ("Alt+Right", self.b.navigate_forward),
            ("Ctrl+Tab", self.siguiente_pestana),
            ("Ctrl+Shift+Tab", self.anterior_pestana),
        ]

        self.b._shortcuts = []
        for seq, callback in shortcuts:
            sc = QShortcut(QKeySequence(seq), self.b)
            sc.activated.connect(callback)
            self.b._shortcuts.append(sc)

    def siguiente_pestana(self):
        if self.b.tabs.count() > 1:
            idx = (self.b.tabs.currentIndex() + 1) % self.b.tabs.count()
            self.b.tabs.setCurrentIndex(idx)

    def anterior_pestana(self):
        if self.b.tabs.count() > 1:
            idx = (self.b.tabs.currentIndex() - 1) % self.b.tabs.count()
            self.b.tabs.setCurrentIndex(idx)

    def on_webview_hotkey(self, combo):
        """Maneja atajos de teclado propagados directamente desde el WebView2."""
        combo = str(combo).upper()
        if combo in ("CTRL+T", "COMMAND+T"):
            self.b.add_new_tab()
        elif combo in ("CTRL+W", "COMMAND+W"):
            self.b.close_tab(self.b.tabs.currentIndex())
        elif combo in ("CTRL+R", "F5", "COMMAND+R"):
            self.b.reload_page()
        elif combo in ("CTRL+H", "COMMAND+H"):
            self.b.abrir_historial_submodulo()
        elif combo in ("CTRL+J", "COMMAND+J"):
            self.abrir_pestana_descargas()
        elif combo in ("CTRL+D", "COMMAND+D"):
            self.b.guardar_marcador_actual()
        elif combo in ("CTRL+F", "COMMAND+F"):
            self.b.mostrar_barra_busqueda()
        elif combo in ("CTRL+P", "COMMAND+P"):
            self.b.imprimir_pagina()
        elif combo == "F11":
            self.b.toggle_fullscreen_mode()
        elif combo in ("CTRL+PLUS", "CTRL+=", "CTRL++"):
            self.b.zoom_in()
        elif combo in ("CTRL+MINUS", "CTRL+-"):
            self.b.zoom_out()
        elif combo in ("CTRL+0", "CTRL+NUMPAD0"):
            self.b.reset_zoom()
        elif combo in ("ALT+LEFT", "COMMAND+["):
            self.b.navigate_back()
        elif combo in ("ALT+RIGHT", "COMMAND+]"):
            self.b.navigate_forward()
        elif combo == "CTRL+TAB":
            self.siguiente_pestana()
        elif combo == "CTRL+SHIFT+TAB":
            self.anterior_pestana()

    def abrir_pestana_descargas(self):
        """Abre la pestaña de descargas del módulo navegador o la carpeta del sistema."""
        try:
            p = getattr(self.b, "parent_module", None)
            while p and not hasattr(p, "sub_descargas") and hasattr(p, "parent_module"):
                p = getattr(p, "parent_module", None)
            if p and hasattr(p, "tabs") and hasattr(p, "sub_descargas"):
                idx = p.tabs.indexOf(p.sub_descargas)
                if idx >= 0:
                    p.tabs.setCurrentIndex(idx)
                    p.sub_descargas._refrescar_historial()
                    return
        except Exception:
            pass
        from PyQt6.QtGui import QDesktopServices
        dl_dir = Path.home() / "Downloads"
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(dl_dir)))

    def _remover_descarga_activa(self, path):
        """Remueve la descarga de active_downloads con coincidencia flexible de ruta y mayúsculas."""
        if not path:
            return None
        norm_target = os.path.normcase(os.path.normpath(str(path)))
        keys_to_del = []
        info_encontrada = None
        for k, v in list(self.b.active_downloads.items()):
            norm_k = os.path.normcase(os.path.normpath(str(k)))
            if norm_k == norm_target or str(k) == str(path) or (Path(k).name.lower() == Path(path).name.lower() and Path(path).name):
                keys_to_del.append(k)
                info_encontrada = v
        for k in keys_to_del:
            if k in self.b.active_downloads:
                del self.b.active_downloads[k]
        return info_encontrada

    def on_download_starting(self, uri, path, browser):
        fname = Path(path).name if path else "descarga"
        self.b.active_downloads[path] = {"url": uri, "recv": 0, "total": 0, "name": fname, "time": time.time()}
        if hasattr(self.b, "toolbar") and hasattr(self.b.toolbar, "actualizar_descargas"):
            self.b.toolbar.actualizar_descargas(len(self.b.active_downloads))
        if hasattr(self.b, "downloads_flyout") and self.b.downloads_flyout:
            self.b.downloads_flyout.notificar_descarga_iniciada(path, uri)

    def on_download_progress(self, path, recv, total, browser):
        target_key = path
        if path not in self.b.active_downloads:
            norm_target = os.path.normcase(os.path.normpath(str(path)))
            for k in list(self.b.active_downloads.keys()):
                if os.path.normcase(os.path.normpath(str(k))) == norm_target:
                    target_key = k
                    break
        if target_key in self.b.active_downloads:
            self.b.active_downloads[target_key]["recv"] = recv
            self.b.active_downloads[target_key]["total"] = total
            if hasattr(self.b, "toolbar") and hasattr(self.b.toolbar, "actualizar_descargas"):
                self.b.toolbar.actualizar_descargas(len(self.b.active_downloads))
            if hasattr(self.b, "downloads_flyout") and self.b.downloads_flyout:
                self.b.downloads_flyout.notificar_progreso(target_key, recv, total)

    def on_download_completed(self, path, uri, browser):
        self._remover_descarga_activa(path)
        if hasattr(self.b, "toolbar") and hasattr(self.b.toolbar, "actualizar_descargas"):
            self.b.toolbar.actualizar_descargas(len(self.b.active_downloads))
        fname = Path(path).name if path else "archivo"

        # Registrar persistentemente en DownloadManager PRIMERO para que esté listo al refrescar
        try:
            from ...utils.download_manager import DownloadManager
            mgr = DownloadManager(self.b.ruta_usuario)
            mgr.registrar_descarga_externa(path, url=uri)
        except Exception as ex_mgr:
            print(f"[Navegador] Error registrando en DownloadManager: {ex_mgr}")

        try:
            p = getattr(self.b, "parent_module", None)
            while p and not hasattr(p, "sub_descargas") and hasattr(p, "parent_module"):
                p = getattr(p, "parent_module", None)
            if p and hasattr(p, "sub_descargas"):
                p.sub_descargas.mgr.registrar_descarga_externa(path, url=uri)
                p.sub_descargas._refrescar_historial()
        except Exception as e:
            print(f"[Navegador] Error registrando descarga en gestor: {e}")

        # Notificar al flyout en tiempo real cuando ya está en el historial
        if hasattr(self.b, "downloads_flyout") and self.b.downloads_flyout:
            self.b.downloads_flyout.notificar_completada(path, uri)

        try:
            from vistas.utils.notification import show_notification
        except ImportError:
            from .....utils.notification import show_notification

        def _abrir():
            from PyQt6.QtGui import QDesktopServices
            folder = Path(path).parent if path else Path.home() / "Downloads"
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

        show_notification(
            title=f"Descarga Completada: {fname}",
            message="Guardado en tu carpeta de descargas.\nHaz clic aquí para abrir la carpeta contenedora.",
            duration=6000,
            on_click=_abrir
        )

    def on_download_failed(self, path, reason, browser):
        self._remover_descarga_activa(path)
        if hasattr(self.b, "toolbar") and hasattr(self.b.toolbar, "actualizar_descargas"):
            self.b.toolbar.actualizar_descargas(len(self.b.active_downloads))
        if hasattr(self.b, "downloads_flyout") and self.b.downloads_flyout:
            if hasattr(self.b.downloads_flyout, "notificar_fallida"):
                self.b.downloads_flyout.notificar_fallida(path, reason)
            else:
                self.b.downloads_flyout.refrescar_contenido()

        if "usercanceled" in str(reason).lower() or "cancelado por el usuario" in str(reason).lower():
            return
        fname = Path(path).name if path else "archivo"
        try:
            from vistas.utils.notification import show_notification
        except ImportError:
            from .....utils.notification import show_notification
        show_notification(
            title=f"⚠️ Descarga Interrumpida: {fname}",
            message=f"{reason}",
            duration=7000
        )

    def handle_new_window_requested(self, sender, args, browser):
        """Maneja solicitudes de nuevas ventanas; si es un diálogo OAuth (Google, Discord, etc.) o popup modal,
        usa BrowserPopupWindow con CoreWebView2 deferral para preservar window.opener y cookies de sesión."""
        try:
            target_uri = str(getattr(args, "Uri", "") or "")
            target_lower = target_uri.lower()
            popup_features = getattr(args, "WindowFeatures", None)

            # 1. Detección por propiedades de ventana (dimensiones explícitas, popups JS)
            has_size = popup_features and (
                getattr(popup_features, "HasSize", False) or
                (getattr(popup_features, "Width", 0) > 0 and getattr(popup_features, "Height", 0) > 0)
            )
            has_pos = popup_features and getattr(popup_features, "HasPosition", False)
            no_chrome = popup_features and (
                not getattr(popup_features, "ShouldDisplayMenuBar", True) or
                not getattr(popup_features, "ShouldDisplayToolbar", True) or
                not getattr(popup_features, "ShouldDisplayScrollBars", True)
            )

            # 2. Detección exhaustiva de URLs de login / OAuth / SSO
            auth_keywords = (
                "accounts.google.com", "google.com/signin", "google.com/o/oauth2", "google.com/gsi",
                "appleid.apple.com", "login.live.com", "login.microsoftonline.com", "login.microsoft.com",
                "discord.com/oauth2", "discord.com/login", "facebook.com/v", "facebook.com/dialog/oauth",
                "github.com/login", "x.com/i/oauth", "twitter.com/i/oauth", "id.twitch.tv/oauth2",
                "oauth", "login", "auth", "signin", "signup", "sso", "authenticate"
            )
            is_auth_flow = any(kw in target_lower for kw in auth_keywords)
            is_dialog = has_size or has_pos or no_chrome or is_auth_flow

            # Si es un popup, ventana modal o flujo de autenticación, crear ventana nativa emergente BrowserPopupWindow
            if is_dialog:
                deferral = None
                try:
                    if hasattr(args, "GetDeferral") and callable(args.GetDeferral):
                        deferral = args.GetDeferral()
                except Exception:
                    deferral = None

                w = int(popup_features.Width) if popup_features and getattr(popup_features, "Width", 0) > 0 else 520
                h = int(popup_features.Height) if popup_features and getattr(popup_features, "Height", 0) > 0 else 660
                w = max(420, min(1200, w))
                h = max(480, min(900, h))

                popup = BrowserPopupWindow(
                    self.b,
                    width=w,
                    height=h,
                    user_data_folder=str(self.b.data_dir),
                    colores=self.b.colores
                )
                self.b._active_popups.append(popup)
                popup.finished.connect(lambda: self._limpiar_popup_activo(popup))

                def vincular_y_mostrar(core_wv):
                    try:
                        args.NewWindow = core_wv
                        args.Handled = True
                    except Exception as ex_bind:
                        print(f"[BrowserActions] Advertencia asignando NewWindow a popup: {ex_bind}")
                        if target_uri and target_uri != "about:blank":
                            popup.browser.load(QUrl(target_uri))
                    finally:
                        if deferral:
                            try:
                                deferral.Complete()
                            except Exception:
                                pass
                        popup.show()
                        popup.raise_()
                        popup.activateWindow()

                # Si el popup ya tiene su CoreWebView2 listo
                if hasattr(popup.browser, "is_ready") and popup.browser.is_ready and popup.browser.core_webview2:
                    vincular_y_mostrar(popup.browser.core_webview2)
                else:
                    # Esperar inicialización con temporizador de seguridad
                    safety_timer = QTimer(popup)
                    safety_timer.setSingleShot(True)

                    def on_timeout():
                        try:
                            if deferral:
                                deferral.Complete()
                        except Exception:
                            pass
                        if target_uri and target_uri != "about:blank":
                            popup.browser.load(QUrl(target_uri))
                        popup.show()
                        popup.raise_()
                        popup.activateWindow()

                    safety_timer.timeout.connect(on_timeout)
                    safety_timer.start(3500)

                    def on_core_ready(core_wv):
                        if safety_timer.isActive():
                            safety_timer.stop()
                        vincular_y_mostrar(core_wv)

                    popup.browser.coreWebView2Ready.connect(on_core_ready)

                return True

            # Si es un enlace común a otra pestaña
            self.b.add_new_tab(QUrl(target_uri), "Cargando...")
            args.Handled = True
            return True
        except Exception as e:
            print(f"[BrowserActions] Error en handle_new_window_requested: {e}")
            try:
                args.Handled = False
            except Exception:
                pass
            return False

    def _limpiar_popup_activo(self, popup):
        """Elimina la referencia del popup cerrado de la lista de ventanas activas."""
        try:
            if hasattr(self.b, "_active_popups") and popup in self.b._active_popups:
                self.b._active_popups.remove(popup)
        except Exception:
            pass

    def on_web_notification(self, container, title, body, icon_url, url):
        try:
            from vistas.utils.notification import show_notification

            source_icon = None
            if icon_url and icon_url.strip():
                source_icon = icon_url
            elif container and getattr(container, "cached_icon", None):
                source_icon = container.cached_icon
            else:
                source_icon = obtener_o_generar_icono(url, title, self.b.data_dir)

            def redirect_to_tab():
                try:
                    app_gui = None
                    curr = self.b
                    while curr:
                        from vistas.gui import BaseAppGUI
                        if isinstance(curr, BaseAppGUI):
                            app_gui = curr
                            break
                        curr = curr.parent() if hasattr(curr, "parent") else None

                    if app_gui:
                        if not app_gui.isVisible() or app_gui.isMinimized():
                            app_gui.showNormal()
                        app_gui.raise_()
                        app_gui.activateWindow()

                        if hasattr(app_gui, "notebook"):
                            for i in range(app_gui.notebook.count()):
                                w = app_gui.notebook.widget(i)
                                if w and ("Navegador" in w.__class__.__name__ or hasattr(w, "sub_integrado")):
                                    app_gui.notebook.setCurrentIndex(i)
                                    break

                    if self.b.parent_module and hasattr(self.b.parent_module, "tabs"):
                        self.b.parent_module.tabs.setCurrentWidget(self.b)

                    if container and not isdeleted(container):
                        idx = self.b.tabs.indexOf(container)
                        if idx != -1:
                            self.b.tabs.setCurrentIndex(idx)
                except Exception as ex:
                    print(f"[MultiTabBrowser] Error al redirigir pestaña: {ex}")

            show_notification(
                parent=self.b,
                title=title or "Notificación Web",
                message=body or "",
                type="info",
                colores=self.b.colores,
                duration=6000,
                on_click=redirect_to_tab,
                source_icon=source_icon
            )
        except Exception as e:
            print(f"[MultiTabBrowser] Error en on_web_notification: {e}")
