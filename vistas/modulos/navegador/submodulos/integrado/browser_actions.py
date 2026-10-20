"""
browser_actions.py - Manejadores de acciones, menús contextuales, descargas y atajos para MultiTabBrowser
"""

from pathlib import Path
from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.sip import isdeleted

from .container import generar_icono_por_defecto, obtener_o_generar_icono
from .dialogs import BrowserPopupWindow


class BrowserActionsHandler:
    """Manejador de acciones secundarias (menús contextuales, descargas, atajos y notificaciones)."""

    def __init__(self, browser):
        self.b = browser

    def mostrar_menu_pestanas(self, pos):
        """Muestra el menú contextual de la pestaña (fijar, reposo, cerrar, etc.)."""
        tab_bar = self.b.tabs.tabBar()
        tab_idx = tab_bar.tabAt(pos)
        if tab_idx < 0:
            tab_idx = self.b.tabs.currentIndex()

        container = self.b.tabs.widget(tab_idx)
        is_pinned = getattr(container, "is_pinned", False) if container else False
        is_sleeping = getattr(container, "is_sleeping", False) if container else False

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

        if is_sleeping:
            act_wake = menu.addAction("⚡ Despertar Pestaña")
            act_wake.triggered.connect(lambda: self.b.despertar_pestana(tab_idx))
        else:
            act_sleep = menu.addAction("💤 Poner en Reposo (Suspender)")
            act_sleep.triggered.connect(lambda: self.b.dormir_pestana(tab_idx))

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

    def on_download_starting(self, uri, path, browser):
        fname = Path(path).name if path else "descarga"
        self.b.active_downloads[path] = {"url": uri, "recv": 0, "total": 0, "name": fname}
        if hasattr(self.b, "toolbar") and hasattr(self.b.toolbar, "actualizar_descargas"):
            self.b.toolbar.actualizar_descargas(len(self.b.active_downloads))

    def on_download_progress(self, path, recv, total, browser):
        if path in self.b.active_downloads:
            self.b.active_downloads[path]["recv"] = recv
            self.b.active_downloads[path]["total"] = total
            if hasattr(self.b, "toolbar") and hasattr(self.b.toolbar, "actualizar_descargas"):
                self.b.toolbar.actualizar_descargas(len(self.b.active_downloads))

    def on_download_completed(self, path, uri, browser):
        if path in self.b.active_downloads:
            del self.b.active_downloads[path]
        if hasattr(self.b, "toolbar") and hasattr(self.b.toolbar, "actualizar_descargas"):
            self.b.toolbar.actualizar_descargas(len(self.b.active_downloads))

        fname = Path(path).name if path else "archivo"
        try:
            p = getattr(self.b, "parent_module", None)
            while p and not hasattr(p, "sub_descargas") and hasattr(p, "parent_module"):
                p = getattr(p, "parent_module", None)
            if p and hasattr(p, "sub_descargas"):
                p.sub_descargas.mgr.registrar_descarga_externa(path)
                p.sub_descargas._refrescar_historial()
        except Exception as e:
            print(f"[Navegador] Error registrando descarga en gestor: {e}")

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
        if path in self.b.active_downloads:
            del self.b.active_downloads[path]
        if hasattr(self.b, "toolbar") and hasattr(self.b.toolbar, "actualizar_descargas"):
            self.b.toolbar.actualizar_descargas(len(self.b.active_downloads))
        if "usercanceled" in str(reason).lower() or "cancel" in str(reason).lower():
            return
        fname = Path(path).name if path else "archivo"
        try:
            from vistas.utils.notification import show_notification
        except ImportError:
            from .....utils.notification import show_notification
        show_notification(
            title=f"Descarga Interrumpida: {fname}",
            message=f"Motivo: {reason}",
            duration=5000
        )

    def handle_new_window_requested(self, sender, args, browser):
        try:
            target_uri = str(args.Uri)
            popup_features = getattr(args, "WindowFeatures", None)
            has_size = popup_features and (popup_features.HasSize or popup_features.Width > 0)

            if has_size or "login" in target_uri.lower() or "oauth" in target_uri.lower() or "auth" in target_uri.lower():
                w = int(popup_features.Width) if popup_features and popup_features.Width > 0 else 520
                h = int(popup_features.Height) if popup_features and popup_features.Height > 0 else 650
                popup = BrowserPopupWindow(self.b, width=w, height=h, user_data_folder=str(self.b.data_dir), colores=self.b.colores)
                self.b._active_popups.append(popup)
                if hasattr(popup.browser, "wv_control") and hasattr(popup.browser.wv_control, "CoreWebView2"):
                    args.NewWindow = popup.browser.wv_control.CoreWebView2
                    args.Handled = True
                    popup.show()
                    return True

            self.b.add_new_tab(QUrl(target_uri), "Cargando...")
            args.Handled = True
            return True
        except Exception:
            return False

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
