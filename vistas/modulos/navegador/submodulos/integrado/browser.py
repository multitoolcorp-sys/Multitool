"""
browser.py - Orquestador multipestaña MultiTabBrowser con WebView2
"""

import os
import platform
import json
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTabBar, QMessageBox, QMenu, QInputDialog, QApplication, QPushButton,
    QScrollBar, QToolButton
)
from PyQt6.QtCore import QUrl, Qt, QSize, QTimer, QEvent
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon

from ...utils.webview2_widget import WebView2Widget, WEBVIEW2_AVAILABLE
from .container import (
    BrowserContainer, BrowserTabBar, generar_icono_por_defecto,
    obtener_o_generar_icono, guardar_icono_en_cache
)
from .toolbar import BrowserToolbar
from .dialogs import (
    DialogoPermisos, DialogoProxy, BrowserPopupWindow,
    DialogoBorrarDatosNavegacion, DialogoConfiguracionReposo,
    DialogoConfiguracionDescargas
)
from .extensions_dialog import ExtensionsDialog
from .tab_session_manager import TabSessionManager
from .browser_actions import BrowserActionsHandler
from .downloads_flyout import DownloadsFlyoutWidget


class MultiTabBrowser(QWidget):
    """Navegador web multipestaña completo potenciado 100% por Microsoft Edge WebView2."""
    def __init__(self, parent, colores=None, callbacks=None, ruta_usuario=None):
        super().__init__(parent)
        self.parent_module = parent
        self.colores = colores or {
            "bg_principal": "#1E1E1E", "bg_secundario": "#2D2D2D", "bg_terciario": "#3D3D3D",
            "fg_principal": "#E0E0E0", "fg_secundario": "#A0A0A0", "acento": "#6366F1", 
            "acento_hover": "#818CF8", "exito": "#43A047", "error": "#E53935", "advertencia": "#FDD835"
        }
        self.callbacks = callbacks if isinstance(callbacks, dict) else {}
        if not ruta_usuario:
            try:
                from controlador.utils.paths import get_data_path
                self.ruta_usuario = get_data_path()
            except Exception:
                self.ruta_usuario = Path.cwd()
        else:
            self.ruta_usuario = Path(ruta_usuario)
            
        self.data_dir = self.ruta_usuario / "browser_data" / "webview2"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.ruta_usuario / "browser_data" / "tabs_state.json"
        self.sleep_config_file = self.ruta_usuario / "browser_data" / "sleep_config.json"
        
        self.pestanas_restauradas = False
        self.zoom_level = 1.0
        self._active_popups = []
        self.active_downloads = {}

        # Configuración de reposo y gestor de sesión de pestañas
        self.sleep_enabled = True
        self.sleep_timeout_minutes = 5
        self.session_manager = TabSessionManager(self)
        self.session_manager.cargar_config_reposo()
        self.actions_handler = BrowserActionsHandler(self)

        self.inicializar_ui()
        self.downloads_flyout = DownloadsFlyoutWidget(self, self.colores)
        self.actions_handler.configurar_atajos_teclado()
        self.restaurar_estado_pestanas()

        # Temporizador para comprobación periódica de inactividad de pestañas (cada 30 seg)
        self.timer_reposo = QTimer(self)
        self.timer_reposo.setInterval(30000)
        self.timer_reposo.timeout.connect(self._verificar_pestanas_para_reposo)
        self.timer_reposo.start()

    def toggle_downloads_flyout(self):
        """Muestra u oculta la vista emergente de descargas tipo Chrome/Edge anclada a la barra."""
        if hasattr(self, "downloads_flyout") and self.downloads_flyout:
            if self.downloads_flyout.isVisible():
                self.downloads_flyout.hide()
            else:
                btn = getattr(getattr(self, "toolbar", None), "btn_downloads", None)
                self.downloads_flyout.mostrar_bajo_boton(btn)

    def cancelar_descarga(self, path):
        """Cancela la descarga activa en los webviews."""
        for i in range(self.tabs.count()):
            container = self.tabs.widget(i)
            if container and hasattr(container, "browser") and hasattr(container.browser, "cancel_download"):
                if container.browser.cancel_download(path):
                    break


    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Barra de Herramientas Compacta (con botón ⋮ de 3 puntos)
        self.toolbar = BrowserToolbar(self, self.colores)
        self.toolbar_frame = self.toolbar  # Alias de compatibilidad
        self.url_bar = self.toolbar.url_bar
        self.btn_pin = self.toolbar.btn_pin
        self.btn_reload = self.toolbar.btn_reload
        self.main_layout.addWidget(self.toolbar)

        # 2. Barra de desplazamiento horizontal delgada para mover la lista de pestañas
        self.tab_scrollbar = QScrollBar(Qt.Orientation.Horizontal, self)
        self.tab_scrollbar.setFixedHeight(5)
        self.tab_scrollbar.setStyleSheet(f"""
            QScrollBar:horizontal {{
                background: {self.colores['bg_secundario']};
                height: 5px;
                margin: 0px;
                border: none;
                border-radius: 2px;
            }}
            QScrollBar::handle:horizontal {{
                background: {self.colores['acento']};
                min-width: 25px;
                border-radius: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {self.colores['acento_hover']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
                height: 0px;
                border: none;
            }}
        """)
        self.tab_scrollbar.valueChanged.connect(self._on_tab_scrollbar_value_changed)
        self.tab_scrollbar.hide()
        self.main_layout.addWidget(self.tab_scrollbar)

        # 3. Main TabWidget para Pestañas
        self.tabs = QTabWidget()
        self.tabs.setTabBar(BrowserTabBar(self))
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabBar().setMovable(True)
        self.tabs.installEventFilter(self)

        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores['fg_secundario']};
                padding: 4px 8px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-bottom: none;
                margin-right: 2px;
                font-family: 'Segoe UI', Arial;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.colores['bg_principal']};
                color: #FFFFFF;
                border-top: 2px solid {self.colores['acento']};
                font-weight: bold;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {self.colores['bg_terciario']};
                color: #FFFFFF;
            }}
            QTabBar::close-button {{
                subcontrol-position: right;
                margin-right: 2px;
                padding: 0px;
                border: none;
            }}
            QTabBar::scroller {{
                width: 26px;
            }}
            QTabBar QToolButton {{ background-color: rgba(255, 255, 255, 0.08); color: #FFFFFF; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 4px; margin: 2px 1px; width: 18px; height: 22px; }}
            QTabBar QToolButton:hover {{ background-color: {self.colores['acento']}; border-color: {self.colores['acento']}; }}
            QScrollBar:horizontal {{ background: transparent; height: 4px; margin: 0px; }}
            QScrollBar::handle:horizontal {{ background: {self.colores['acento']}; border-radius: 2px; min-width: 20px; }}
        """)

        self.tabs.setUsesScrollButtons(True)

        # Botón '+' para crear nueva pestaña ubicado sólidamente como Corner Widget (evita colisiones con pestañas y botones de scroll)
        self.btn_new_tab = QPushButton("+")
        self.btn_new_tab.setFixedSize(26, 24)
        self.btn_new_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_tab.setToolTip("Nueva Pestaña (Ctrl+T) / Doble clic en barra vacía")
        self.btn_new_tab.setStyleSheet(f"""
            QPushButton {{ background-color: rgba(255, 255, 255, 0.08); color: #E0E0E0; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 5px; font-size: 15px; font-weight: bold; padding-bottom: 2px; margin: 2px 4px; }}
            QPushButton:hover {{ background-color: {self.colores['acento']}; color: #FFFFFF; border-color: {self.colores['acento']}; }}
        """)
        self.btn_new_tab.clicked.connect(lambda: self.add_new_tab())
        self.tabs.setCornerWidget(self.btn_new_tab, Qt.Corner.TopLeftCorner)

        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.tabBar().tabMoved.connect(self._on_tab_moved)
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self._mostrar_menu_pestanas)

        self.main_layout.addWidget(self.tabs, 1)

    def _on_tab_moved(self, from_idx, to_idx):
        """Mantiene sincronizados los botones de cierre y el botón '+' tras reordenar pestañas."""
        self._actualizar_botones_pestanas()
        self._reposition_new_tab_button()
        self.guardar_estado_pestanas()

    def eventFilter(self, watched, event):
        """Captura doble clic en cualquier espacio vacío de la barra de pestañas para abrir una nueva."""
        if watched == self.tabs and event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
                tb = self.tabs.tabBar()
                if pos.y() <= tb.height() + 8:
                    tab_idx = tb.tabAt(tb.mapFrom(self.tabs, pos))
                    if tab_idx == -1:
                        self.add_new_tab()
                        return True
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.actualizar_barra_desplazamiento_pestanas()

    def _reposition_new_tab_button(self):
        """Mantiene sincronizada la barra de desplazamiento horizontal y la barra de pestañas."""
        self.actualizar_barra_desplazamiento_pestanas()

    def actualizar_barra_desplazamiento_pestanas(self):
        """Sincroniza la barra de desplazamiento horizontal delgada con el ancho de las pestañas."""
        if not hasattr(self, "tab_scrollbar") or not hasattr(self, "tabs"):
            return
        tb = self.tabs.tabBar()
        if not tb:
            return
        total_w = tb.sizeHint().width()
        vis_w = tb.width()
        if total_w > vis_w and vis_w > 0:
            max_val = max(0, total_w - vis_w)
            self.tab_scrollbar.blockSignals(True)
            self.tab_scrollbar.setRange(0, max_val)
            self.tab_scrollbar.setPageStep(vis_w)
            curr_offset = max(0, -tb.tabRect(0).x())
            self.tab_scrollbar.setValue(curr_offset)
            self.tab_scrollbar.blockSignals(False)
            self.tab_scrollbar.show()
        else:
            self.tab_scrollbar.hide()

    def _on_tab_scrollbar_value_changed(self, val):
        """Mueve la lista de pestañas al deslizar la barra de desplazamiento horizontal."""
        if not hasattr(self, "tabs"):
            return
        tb = self.tabs.tabBar()
        buttons = tb.findChildren(QToolButton)
        left_btn = next((b for b in buttons if b.objectName() == 'ScrollLeftButton'), None)
        right_btn = next((b for b in buttons if b.objectName() == 'ScrollRightButton'), None)
        curr = -tb.tabRect(0).x()
        diff = val - curr
        step = 0
        while diff > 25 and right_btn and right_btn.isEnabled() and step < 20:
            right_btn.click()
            step += 1
            new_curr = -tb.tabRect(0).x()
            if new_curr == curr:
                break
            curr = new_curr
            diff = val - curr
        step = 0
        while diff < -25 and left_btn and left_btn.isEnabled() and step < 20:
            left_btn.click()
            step += 1
            new_curr = -tb.tabRect(0).x()
            if new_curr == curr:
                break
            curr = new_curr
            diff = val - curr

    def current_browser(self):
        """Retorna el WebView2Widget de la pestaña activa."""
        curr_container = self.tabs.currentWidget()
        if curr_container and hasattr(curr_container, "_web_view"):
            return curr_container._web_view
        return None

    def toggle_fullscreen_mode(self, is_fullscreen=None):
        """Oculta o muestra la barra de herramientas y la barra de pestañas web en pantalla completa."""
        app_gui = None
        curr = self
        while curr:
            from vistas.gui import BaseAppGUI
            if isinstance(curr, BaseAppGUI):
                app_gui = curr
                break
            curr = curr.parent() if hasattr(curr, "parent") else None

        if is_fullscreen is None:
            if app_gui:
                app_gui.toggle_pantalla_completa()
                return

        target_fullscreen = bool(is_fullscreen)
        if hasattr(self, "toolbar"):
            self.toolbar.setVisible(not target_fullscreen)
        if hasattr(self, "tabs") and hasattr(self.tabs, "tabBar"):
            self.tabs.tabBar().setVisible(not target_fullscreen)

    def add_new_tab(self, qurl=None, label="Nueva Pestaña", is_pinned=False, zoom=None, start_sleeping=False, nav_history=None, nav_index=None, sleep_mode="default"):
        """Crea una nueva pestaña con WebView2 incrustado o suspendida en modo reposo."""
        if qurl is None:
            qurl = QUrl("https://www.google.com")

        url_str = qurl.toString() if hasattr(qurl, "toString") else str(qurl)
        if not url_str.startswith(("http://", "https://", "about:", "file://")):
            url_str = "https://" + url_str

        tab_zoom = float(zoom) if zoom is not None else self.zoom_level

        # Si está configurada como 'Siempre activa', no debe iniciar en reposo
        if sleep_mode == "always_active":
            start_sleeping = False

        # Si inicia suspendida (lazy loading al restaurar), no cargamos WebView2 para ahorrar RAM y CPU
        if start_sleeping:
            container = BrowserContainer(None, self, zoom=tab_zoom, is_sleeping=True, saved_url=url_str, nav_history=nav_history, nav_index=nav_index, sleep_mode=sleep_mode)
            container.full_title = label
            tab_ico = obtener_o_generar_icono(url_str, label, self.data_dir, callback=container.actualizar_icono)
            container.cached_icon = tab_ico
            idx = self.tabs.addTab(container, tab_ico, f"💤 {label}" if not is_pinned else "")
            self._actualizar_tooltip_pestana(idx)
            if is_pinned:
                self.toggle_pin_tab(idx)
            else:
                self._actualizar_botones_pestanas()
            self._reposition_new_tab_button()
            return None

        browser = WebView2Widget(self, url_str, str(self.data_dir), initial_zoom=tab_zoom)
        container = BrowserContainer(browser, self, zoom=tab_zoom, nav_history=nav_history, nav_index=nav_index, sleep_mode=sleep_mode)
        container.full_title = label

        tab_ico = obtener_o_generar_icono(url_str, label, self.data_dir, callback=container.actualizar_icono)
        container.cached_icon = tab_ico

        self._conectar_senales_webview(browser, container)

        idx = self.tabs.addTab(container, tab_ico, label)
        self.tabs.setCurrentIndex(idx)
        self._actualizar_tooltip_pestana(idx)

        if hasattr(browser, "setZoomFactor"):
            browser.setZoomFactor(tab_zoom)

        if is_pinned:
            self.toggle_pin_tab(idx)
        else:
            self._actualizar_botones_pestanas()

        self._reposition_new_tab_button()
        self.guardar_estado_pestanas()
        return browser

    def _conectar_senales_webview(self, browser, container):
        """Conecta las señales del WebView2 con el contenedor y navegador."""
        browser.urlChanged.connect(lambda u, b=browser: self._on_tab_url_changed(u, b))
        browser.titleChanged.connect(lambda t, b=browser: self._on_tab_title_changed(t, b))
        browser.iconChanged.connect(lambda ico, b=browser: self._on_tab_icon_changed(ico, b))
        browser.loadStarted.connect(lambda b=browser: self._on_tab_load_started(b))
        browser.loadFinished.connect(lambda ok, b=browser: self._on_tab_load_finished(ok, b))
        browser.newWindowRequested.connect(lambda target: self.add_new_tab(QUrl(target), "Cargando..."))
        if hasattr(browser, "windowCloseRequested"):
            browser.windowCloseRequested.connect(lambda b=browser: self._on_browser_close_requested(b))
        if hasattr(browser, "zoomFactorChanged"):
            browser.zoomFactorChanged.connect(lambda factor, b=browser: self._on_browser_zoom_changed(factor, b))
        if hasattr(browser, "webNotificationReceived"):
            browser.webNotificationReceived.connect(
                lambda title, body, icon_url, url, c=container: self._on_web_notification(c, title, body, icon_url, url)
            )
        if hasattr(browser, "fullscreenRequested"):
            browser.fullscreenRequested.connect(lambda is_fs: self.toggle_fullscreen_mode(is_fs))
        if hasattr(browser, "hotkeyPressed"):
            browser.hotkeyPressed.connect(self._on_webview_hotkey)
        if hasattr(browser, "downloadStarting"):
            browser.downloadStarting.connect(lambda u, p, b=browser: self._on_download_starting(u, p, b))
        if hasattr(browser, "downloadProgress"):
            browser.downloadProgress.connect(lambda p, r, t, b=browser: self._on_download_progress(p, r, t, b))
        if hasattr(browser, "downloadCompleted"):
            browser.downloadCompleted.connect(lambda p, u, b=browser: self._on_download_completed(p, u, b))
        if hasattr(browser, "downloadFailed"):
            browser.downloadFailed.connect(lambda p, r, b=browser: self._on_download_failed(p, r, b))
        if hasattr(browser, "pipStatusChanged"):
            browser.pipStatusChanged.connect(lambda is_pip, c=container: self._on_tab_pip_changed(is_pip, c))
        browser.new_window_handler = lambda sender, args, b=browser: self._handle_new_window_requested(sender, args, b)

    def _on_tab_pip_changed(self, is_pip, container):
        """Mantiene el estado de Imagen en Imagen (PiP) y actualiza la actividad para prevenir reposo."""
        if container:
            container.is_pip_active = is_pip
            if is_pip:
                container.last_active_time = time.time()

    def toggle_pin_current_tab(self):
        self.toggle_pin_tab(self.tabs.currentIndex())

    def toggle_pin_tab(self, tab_idx=None):
        """Fija o desfija la pestaña indicada. Al fijar, muestra ÚNICAMENTE el icono."""
        if tab_idx is None:
            tab_idx = self.tabs.currentIndex()
        if tab_idx < 0 or tab_idx >= self.tabs.count():
            return

        container = self.tabs.widget(tab_idx)
        if not container:
            return

        is_pinned = getattr(container, "is_pinned", False)

        if not is_pinned:
            container.is_pinned = True
            current_title = container.title() or container.full_title or "Página Web"
            container.full_title = current_title

            if self.tabs.tabIcon(tab_idx).isNull():
                u_str = container.url().toString() if hasattr(container, "url") else ""
                icon = obtener_o_generar_icono(u_str, current_title, self.data_dir, callback=container.actualizar_icono)
                self.tabs.setTabIcon(tab_idx, icon)
                container.cached_icon = icon

            self.tabs.setTabText(tab_idx, "")
            is_sleep = getattr(container, "is_sleeping", False)
            tip_prefix = "💤 " if is_sleep else ""
            self.tabs.setTabToolTip(tab_idx, f"{tip_prefix}📌 {container.full_title} (Pestaña Fijada)")
            self.tabs.tabBar().setTabButton(tab_idx, QTabBar.ButtonPosition.RightSide, None)

            num_pinned = sum(1 for i in range(self.tabs.count()) if getattr(self.tabs.widget(i), "is_pinned", False))
            target_idx = max(0, num_pinned - 1)
            if tab_idx != target_idx:
                self.tabs.tabBar().moveTab(tab_idx, target_idx)
                tab_idx = target_idx
        else:
            container.is_pinned = False
            full_title = getattr(container, "full_title", "Página Web")
            is_sleep = getattr(container, "is_sleeping", False)
            prefix = "💤 " if is_sleep else ""
            short_title = full_title[:18] + "..." if len(full_title) > 18 else full_title
            self.tabs.setTabText(tab_idx, f"{prefix}{short_title}")
            self.tabs.setTabToolTip(tab_idx, full_title)

            num_pinned = sum(1 for i in range(self.tabs.count()) if getattr(self.tabs.widget(i), "is_pinned", False))
            if tab_idx < num_pinned:
                self.tabs.tabBar().moveTab(tab_idx, num_pinned)
                tab_idx = num_pinned

        self._actualizar_botones_pestanas()
        self._actualizar_estado_boton_pin()
        self.tabs.tabBar().updateGeometry()
        self._reposition_new_tab_button()
        self.guardar_estado_pestanas()

    def _actualizar_botones_pestanas(self):
        """Asigna un botón '✕' estilizado a cada pestaña normal para cerrarla al instante."""
        bar = self.tabs.tabBar()
        for i in range(self.tabs.count()):
            container = self.tabs.widget(i)
            is_pinned = getattr(container, "is_pinned", False)
            if is_pinned:
                bar.setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
                continue

            btn_close = QPushButton("✕")
            btn_close.setFixedSize(16, 16)
            btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_close.setToolTip("Cerrar Pestaña (Ctrl+W)")
            btn_close.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #9CA3AF;
                    border: none;
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #EF4444;
                    color: #FFFFFF;
                }
            """)
            btn_close.clicked.connect(lambda _, c=container: self.close_tab_by_container(c))
            bar.setTabButton(i, QTabBar.ButtonPosition.RightSide, btn_close)

        self._reposition_new_tab_button()

    def close_tab_by_container(self, container):
        """Cierra la pestaña identificando de forma segura su contenedor."""
        if not container:
            return
        idx = self.tabs.indexOf(container)
        if idx != -1:
            self.close_tab(idx)

    def _actualizar_estado_boton_pin(self):
        if hasattr(self, "btn_pin"):
            curr_container = self.tabs.currentWidget()
            is_pinned = getattr(curr_container, "is_pinned", False) if curr_container else False
            if is_pinned:
                self.btn_pin.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px;")
                self.btn_pin.setToolTip("Desfijar Pestaña Actual")
            else:
                self.btn_pin.setStyleSheet(f"background: transparent; color: {self.colores['fg_principal']}; border-radius: 6px;")
                self.btn_pin.setToolTip("Fijar Pestaña Actual (Mostrar solo icono)")

    def close_tab(self, index):
        """Cierra la pestaña indicada liberando sus recursos."""
        if self.tabs.count() > 1:
            container = self.tabs.widget(index)
            if container:
                if hasattr(container, "dormir"):
                    container.dormir()
                elif hasattr(container, "_web_view") and hasattr(container._web_view, "dispose_browser"):
                    try:
                        container._web_view.dispose_browser()
                    except Exception:
                        pass
                container.deleteLater()
            self.tabs.removeTab(index)
            self._actualizar_botones_pestanas()
            self._actualizar_estado_boton_pin()
            self._reposition_new_tab_button()
            self.guardar_estado_pestanas()
        else:
            # Si solo queda 1 pestaña, navegar a Google
            b = self.current_browser()
            if b:
                b.setUrl(QUrl("https://www.google.com"))
            elif self.tabs.currentWidget() and hasattr(self.tabs.currentWidget(), "despertar"):
                self.tabs.currentWidget().saved_url = "https://www.google.com"
                self.tabs.currentWidget().despertar()

    def current_tab_changed(self, index):
        """Disparado al cambiar de pestaña; reactiva pestañas en reposo inmediatamente."""
        if index < 0 or index >= self.tabs.count():
            return
        container = self.tabs.widget(index)
        if container:
            container.last_active_time = time.time()
            if getattr(container, "is_sleeping", False):
                self.despertar_pestana(index)
            else:
                z = getattr(container, "zoom_level", 1.0)
                self.zoom_level = round(float(z), 2)
                if hasattr(self, "toolbar"):
                    self.toolbar.actualizar_badge_zoom(self.zoom_level)

                b = getattr(container, "_web_view", None)
                if b and hasattr(b, "url"):
                    u = b.url().toString()
                    self.url_bar.setText(u if u and not u.startswith("about:") else "")

        # Desenfocar las demás pestañas para que ningún campo web retenga foco
        for i in range(self.tabs.count()):
            if i != index:
                c = self.tabs.widget(i)
                if c:
                    wv = getattr(c, "_web_view", None)
                    if wv and hasattr(wv, "blur_web"):
                        wv.blur_web()

        self._actualizar_estado_boton_pin()
        self._reposition_new_tab_button()

    def desenfocar_todo(self):
        """Desenfoca todas las vistas web del navegador."""
        try:
            for i in range(self.tabs.count()):
                container = self.tabs.widget(i)
                if container:
                    wv = getattr(container, "_web_view", None)
                    if wv and hasattr(wv, "blur_web"):
                        wv.blur_web()
        except Exception:
            pass

    def hideEvent(self, event):
        super().hideEvent(event)
        self.desenfocar_todo()

    def establecer_modo_reposo_pestana(self, tab_idx, mode):
        """Establece la política de reposo de la pestaña: 'default' (general) o 'always_active' (siempre activa)."""
        if tab_idx < 0 or tab_idx >= self.tabs.count():
            return
        container = self.tabs.widget(tab_idx)
        if not container:
            return

        container.set_sleep_mode(mode)
        if mode == "always_active":
            if getattr(container, "is_sleeping", False):
                self.despertar_pestana(tab_idx)
            else:
                self._actualizar_tooltip_pestana(tab_idx)
        else:
            self._actualizar_tooltip_pestana(tab_idx)

        self.guardar_estado_pestanas()

    def _actualizar_tooltip_pestana(self, idx):
        """Genera y asigna un tooltip descriptivo con los estados de fijado, reposo y política activa."""
        if idx < 0 or idx >= self.tabs.count():
            return
        container = self.tabs.widget(idx)
        if not container:
            return

        title = getattr(container, "full_title", "Página Web")
        is_pinned = getattr(container, "is_pinned", False)
        is_sleeping = getattr(container, "is_sleeping", False)
        sleep_mode = getattr(container, "sleep_mode", "default")

        lines = []
        if is_sleeping:
            lines.append("💤 [En reposo para ahorrar RAM - Haz clic para reactivar]")
        elif sleep_mode == "always_active":
            lines.append("🛡️ [Modo Reposo: Siempre Activa (Nunca suspender)]")
        else:
            mins = getattr(self, "sleep_timeout_minutes", 15)
            lines.append(f"🌐 [Modo Reposo: General ({mins} min)]")

        pin_str = "📌 (Pestaña Fijada) " if is_pinned else ""
        lines.append(f"{pin_str}{title}")

        self.tabs.setTabToolTip(idx, "\n".join(lines))

    def dormir_pestana(self, tab_idx):
        """Pone una pestaña en reposo liberando recursos de WebView2."""
        if tab_idx < 0 or tab_idx >= self.tabs.count():
            return
        container = self.tabs.widget(tab_idx)
        if not container or getattr(container, "is_sleeping", False):
            return
        if getattr(container, "sleep_mode", "default") == "always_active":
            return # Pestaña configurada como 'Siempre activa'
        if getattr(container, "is_pip_active", False):
            return # Nunca suspender pestañas en modo Imagen en Imagen (PiP)

        container.dormir()

        is_pinned = getattr(container, "is_pinned", False)
        if not is_pinned:
            t = getattr(container, "full_title", "Página Web")
            prefix = "💤 " if not t.startswith("💤 ") else ""
            short = (t[:16] + "...") if len(t) > 16 else t
            self.tabs.setTabText(tab_idx, f"{prefix}{short}")

        self._actualizar_tooltip_pestana(tab_idx)
        self._actualizar_botones_pestanas()

    def despertar_pestana(self, tab_idx):
        """Reactiva una pestaña suspendida reconstruyendo su WebView2 de inmediato."""
        if tab_idx < 0 or tab_idx >= self.tabs.count():
            return
        container = self.tabs.widget(tab_idx)
        if not container or not getattr(container, "is_sleeping", False):
            return

        container.despertar()
        self._actualizar_estado_pestana_despertada(container)

    def _actualizar_estado_pestana_despertada(self, container):
        """Restaura la apariencia y enlaces de la pestaña reactivada."""
        idx = self.tabs.indexOf(container)
        if idx != -1:
            is_pinned = getattr(container, "is_pinned", False)
            if not is_pinned:
                t = getattr(container, "full_title", "Página Web").replace("💤 ", "").strip()
                short = (t[:18] + "...") if len(t) > 18 else t
                self.tabs.setTabText(idx, short)
            else:
                self.tabs.setTabText(idx, "")

            self._actualizar_tooltip_pestana(idx)
            self._actualizar_botones_pestanas()
            b = getattr(container, "_web_view", None)
            if b and hasattr(b, "url"):
                u = b.url().toString()
                if self.tabs.currentIndex() == idx:
                    self.url_bar.setText(u if u and not u.startswith("about:") else "")

        self._reposition_new_tab_button()
        self.guardar_estado_pestanas()

    def _cargar_config_reposo(self):
        """Carga la configuración del modo reposo de pestañas."""
        if hasattr(self, "session_manager"):
            self.session_manager.cargar_config_reposo()

    def _guardar_config_reposo(self):
        """Guarda la configuración del modo reposo de pestañas."""
        if hasattr(self, "session_manager"):
            self.session_manager.guardar_config_reposo()

    def _verificar_pestanas_para_reposo(self):
        """Comprueba periódicamente las pestañas inactivas y las suspende si superan el tiempo configurado."""
        if hasattr(self, "session_manager"):
            self.session_manager.verificar_pestanas_para_reposo()

    def mostrar_dialogo_configuracion_reposo(self):
        """Abre el diálogo modal de configuración de reposo de pestañas."""
        dlg = DialogoConfiguracionReposo(
            self, self.colores,
            sleep_enabled=self.sleep_enabled,
            sleep_timeout_minutes=self.sleep_timeout_minutes
        )
        if dlg.exec() and dlg.resultado_guardado:
            self.sleep_enabled = dlg.sleep_enabled
            self.sleep_timeout_minutes = dlg.sleep_timeout_minutes
            self._guardar_config_reposo()

    def mostrar_dialogo_configuracion_descargas(self):
        """Abre el diálogo modal de configuración de descargas."""
        cfg_file = self.data_dir.parent / "config.json"
        DialogoConfiguracionDescargas(self, cfg_file, self.colores).exec()

    # --- NAVEGACIÓN ---
    def navigate_to_url(self):
        q = self.url_bar.text().strip()
        if not q: return
        if not q.startswith(("http://", "https://", "about:", "file://")):
            if "." in q and " " not in q:
                q = "https://" + q
            else:
                q = f"https://www.google.com/search?q={q}"
        curr_container = self.tabs.currentWidget()
        if curr_container and hasattr(curr_container, "load"):
            curr_container.load(QUrl(q))
        else:
            b = self.current_browser()
            if b:
                b.setUrl(QUrl(q))

    def navigate_back(self):
        curr_container = self.tabs.currentWidget()
        if curr_container and hasattr(curr_container, "go_back"):
            curr_container.go_back()
        else:
            b = self.current_browser()
            if b and hasattr(b, "back"):
                b.back()

    def navigate_forward(self):
        curr_container = self.tabs.currentWidget()
        if curr_container and hasattr(curr_container, "go_forward"):
            curr_container.go_forward()
        else:
            b = self.current_browser()
            if b and hasattr(b, "forward"):
                b.forward()

    def reload_page(self):
        b = self.current_browser()
        if b and hasattr(b, "reload"):
            b.reload()

    def navigate_reload(self):
        self.reload_page()

    def go_home(self):
        b = self.current_browser()
        if b:
            b.setUrl(QUrl("https://www.google.com"))

    def navigate_home(self):
        self.go_home()

    # --- ZOOM DINÁMICO ---
    def set_zoom_direct(self, factor):
        factor = round(float(factor), 2)
        b = self.current_browser()
        if b and hasattr(b, "setZoomFactor"):
            b.setZoomFactor(factor)
        curr_container = self.tabs.currentWidget()
        if curr_container:
            curr_container.zoom_level = factor
        self.zoom_level = factor
        if hasattr(self, "toolbar"):
            self.toolbar.mostrar_burbuja_zoom(factor)
        self.guardar_estado_pestanas()

    def reset_zoom(self):
        self.set_zoom_direct(1.0)

    def adjust_zoom(self, delta):
        new_factor = max(0.25, min(5.0, round(self.zoom_level + delta, 2)))
        self.set_zoom_direct(new_factor)

    def zoom_in(self):
        """Aumenta el nivel de zoom."""
        self.adjust_zoom(0.1)

    def zoom_out(self):
        """Reduce el nivel de zoom."""
        self.adjust_zoom(-0.1)

    def _on_browser_zoom_changed(self, factor, browser, *args):
        factor = round(float(factor), 2)
        for i in range(self.tabs.count()):
            c = self.tabs.widget(i)
            if c and getattr(c, "_web_view", None) == browser:
                c.zoom_level = factor
                break
        if browser == self.current_browser():
            self.zoom_level = factor
            if hasattr(self, "toolbar"):
                self.toolbar.mostrar_burbuja_zoom(factor)
        self.guardar_estado_pestanas()

    # --- HISTORIAL Y EVENTOS DE CARGA ---
    def _registrar_en_historial(self, url, title=None):
        if not url: return
        url_str = url.toString() if hasattr(url, "toString") else str(url)
        url_str = url_str.strip()
        if not url_str or url_str.startswith(("about:", "data:", "chrome:", "edge:", "javascript:")):
            return

        title_str = str(title).strip() if title else None
        fn = self.callbacks.get("añadir_historial") or self.callbacks.get("guardar_historial")
        if fn:
            try:
                fn(url_str, title_str)
                return
            except Exception:
                pass
        if hasattr(self, "parent_module") and self.parent_module and hasattr(self.parent_module, "nav_manager"):
            try:
                self.parent_module.nav_manager.añadir_historial(url_str, title_str)
            except Exception:
                pass

    def _on_tab_url_changed(self, qurl, browser, *args):
        url_str = qurl.toString() if hasattr(qurl, "toString") else str(qurl)
        if browser == self.current_browser():
            self.url_bar.setText(url_str)
        for i in range(self.tabs.count()):
            c = self.tabs.widget(i)
            if c and getattr(c, "_web_view", None) == browser:
                if hasattr(c, "registrar_url"):
                    c.registrar_url(url_str)
                break
        self.guardar_estado_pestanas()
        title = browser.title() if hasattr(browser, "title") else getattr(browser, "_title", None)
        self._registrar_en_historial(qurl, title)

    def _on_tab_title_changed(self, title, browser, *args):
        for i in range(self.tabs.count()):
            container = self.tabs.widget(i)
            if container and getattr(container, "_web_view", None) == browser:
                container.full_title = title
                is_pinned = getattr(container, "is_pinned", False)
                if is_pinned:
                    self.tabs.setTabText(i, "")
                    self.tabs.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
                else:
                    short_title = title[:20] + "..." if len(title) > 20 else title
                    self.tabs.setTabText(i, short_title or "Página Web")
                self._actualizar_tooltip_pestana(i)
                break

        if hasattr(browser, "url"):
            self._registrar_en_historial(browser.url(), title)

    def _on_tab_icon_changed(self, icon, browser, *args):
        for i in range(self.tabs.count()):
            container = self.tabs.widget(i)
            if container and getattr(container, "_web_view", None) == browser:
                u_str = container.url().toString() if hasattr(container, "url") else ""
                if isinstance(icon, QIcon) and not icon.isNull():
                    self.tabs.setTabIcon(i, icon)
                    container.cached_icon = icon
                    guardar_icono_en_cache(u_str, icon, self.data_dir)
                else:
                    default_ico = obtener_o_generar_icono(u_str, container.title(), self.data_dir, callback=container.actualizar_icono)
                    self.tabs.setTabIcon(i, default_ico)
                    container.cached_icon = default_ico

                if getattr(container, "is_pinned", False):
                    self.tabs.setTabText(i, "")
                    self.tabs.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
                break

    def _on_tab_load_started(self, browser, *args):
        if browser == self.current_browser():
            self.btn_reload.setText("🛑")
            self.btn_reload.setToolTip("Detener carga")

    def _on_tab_load_finished(self, is_success, browser, *args):
        if is_success and hasattr(browser, "url"):
            title = browser.title() if hasattr(browser, "title") else getattr(browser, "_title", None)
            self._registrar_en_historial(browser.url(), title)

        if browser == self.current_browser():
            self.btn_reload.setText("🔄")
            self.btn_reload.setToolTip("Recargar página (Ctrl+R / F5)")

    def _on_browser_close_requested(self, browser, *args):
        for i in range(self.tabs.count()):
            container = self.tabs.widget(i)
            if container and getattr(container, "_web_view", None) == browser:
                self.close_tab(i)
                break

    def _handle_new_window_requested(self, sender, args, browser):
        return self.actions_handler.handle_new_window_requested(sender, args, browser)

    def _on_web_notification(self, container, title, body, icon_url, url):
        self.actions_handler.on_web_notification(container, title, body, icon_url, url)

    # --- MENÚ Y DIÁLOGOS AUXILIARES ---
    def mostrar_dialogo_extensiones(self):
        user_data = self.data_dir
        dlg = ExtensionsDialog(self, self.colores, user_data)
        dlg.exec()

    def mostrar_dialogo_permisos(self):
        dlg = DialogoPermisos(self, self.colores, self.ruta_usuario)
        dlg.exec()

    def mostrar_dialogo_proxy(self):
        dlg = DialogoProxy(self, self.colores, self.ruta_usuario)
        dlg.exec()

    def abrir_devtools(self):
        b = self.current_browser()
        if b and hasattr(b, "open_devtools"):
            b.open_devtools()

    def abrir_historial_submodulo(self):
        if hasattr(self.parent_module, "tabs"):
            for i in range(self.parent_module.tabs.count()):
                if "HISTORIAL" in self.parent_module.tabs.tabText(i).upper():
                    self.parent_module.tabs.setCurrentIndex(i)
                    break

    def guardar_marcador_actual(self):
        b = self.current_browser()
        if not b: return
        url = b.url().toString()
        title = b.title()
        fn = self.callbacks.get("guardar_link_integrado") or self.callbacks.get("guardar_link")
        if fn:
            try:
                fn(title, url)
                return
            except TypeError:
                try:
                    fn(url)
                    return
                except TypeError:
                    fn()
                    return
        if hasattr(self, "parent_module") and hasattr(self.parent_module, "mostrar_dialogo_guardar_favorito"):
            self.parent_module.mostrar_dialogo_guardar_favorito(url, title)

    def mostrar_barra_busqueda(self):
        txt, ok = QInputDialog.getText(self, "Buscar en la Página", "Palabra o frase a buscar:")
        if ok and txt.strip():
            b = self.current_browser()
            if b and hasattr(b, "runJavaScript"):
                b.runJavaScript(f"window.find('{txt.strip()}');")

    def imprimir_pagina(self):
        b = self.current_browser()
        if b and hasattr(b, "runJavaScript"):
            b.runJavaScript("window.print();")

    def limpiar_datos_navegacion(self):
        """Abre el diálogo completo de borrado de datos de navegación con casillas de selección."""
        dlg = DialogoBorrarDatosNavegacion(self, self.colores, self.ruta_usuario)
        dlg.exec()

    def _mostrar_menu_pestanas(self, pos):
        self.actions_handler.mostrar_menu_pestanas(pos)

    def _siguiente_pestana(self):
        self.actions_handler.siguiente_pestana()

    def _anterior_pestana(self):
        self.actions_handler.anterior_pestana()

    def _on_webview_hotkey(self, combo):
        self.actions_handler.on_webview_hotkey(combo)

    def abrir_pestana_descargas(self):
        self.actions_handler.abrir_pestana_descargas()

    def _on_download_starting(self, uri, path, browser):
        self.actions_handler.on_download_starting(uri, path, browser)

    def _on_download_progress(self, path, recv, total, browser):
        self.actions_handler.on_download_progress(path, recv, total, browser)

    def _on_download_completed(self, path, uri, browser):
        self.actions_handler.on_download_completed(path, uri, browser)

    def _on_download_failed(self, path, reason, browser):
        self.actions_handler.on_download_failed(path, reason, browser)

    # --- PERSISTENCIA DE ESTADO DE PESTAÑAS (DELEGADO A TABSESSIONMANAGER) ---
    def guardar_estado_pestanas(self):
        """Guarda el estado completo de pestañas, orden, zoom, URLs e historial propio por pestaña."""
        if hasattr(self, "session_manager"):
            return self.session_manager.guardar_estado_pestanas()

    def restaurar_estado_pestanas(self):
        """Restaura las pestañas de la sesión anterior con historial propio por pestaña."""
        if hasattr(self, "session_manager"):
            return self.session_manager.restaurar_estado_pestanas()
        self.add_new_tab(QUrl("https://www.google.com"), "Google")
        self.pestanas_restauradas = True

    def actualizar_tema(self, colores):
        """Actualiza la paleta de colores del navegador y componentes emergentes."""
        if isinstance(colores, dict):
            self.colores = colores
            if hasattr(self, "downloads_flyout") and self.downloads_flyout:
                try:
                    self.downloads_flyout.actualizar_tema(colores)
                except Exception:
                    pass

