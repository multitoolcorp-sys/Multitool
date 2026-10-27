"""
container.py - Componentes de pestañas y contenedores de WebView2 para MultiTool
"""

import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTabBar, QToolButton
)
from PyQt6.QtCore import QUrl, Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QBrush, QPen



import hashlib

def _get_favicons_dir(data_dir=None):
    try:
        if data_dir:
            d = Path(data_dir) / "favicons"
        else:
            from controlador.utils.paths import get_data_path
            d = get_data_path() / "browser_data" / "favicons"
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception:
        d = Path("browser_data") / "favicons"
        d.mkdir(parents=True, exist_ok=True)
        return d

def _extract_domain(url_str):
    if not url_str:
        return ""
    try:
        if "://" in url_str:
            return url_str.split("://")[1].split("/")[0].split(":")[0].lower().replace("www.", "")
    except Exception:
        pass
    return url_str.lower().strip()

def guardar_icono_en_cache(url_str, icon, data_dir=None):
    domain = _extract_domain(url_str)
    if not domain or not icon or icon.isNull():
        return
    try:
        fav_dir = _get_favicons_dir(data_dir)
        dom_hash = hashlib.md5(domain.encode("utf-8")).hexdigest()
        file_path = fav_dir / f"{dom_hash}.png"
        pix = icon.pixmap(32, 32)
        if not pix.isNull():
            pix.save(str(file_path), "PNG")
    except Exception:
        pass

def obtener_icono_cached(url_str, data_dir=None):
    domain = _extract_domain(url_str)
    if not domain:
        return None
    try:
        fav_dir = _get_favicons_dir(data_dir)
        dom_hash = hashlib.md5(domain.encode("utf-8")).hexdigest()
        file_path = fav_dir / f"{dom_hash}.png"
        if file_path.exists():
            return QIcon(str(file_path))
    except Exception:
        pass
    return None

def generar_icono_por_defecto(url_str="", title=""):
    """Genera un icono QIcon nítido con color distintivo si la página no tiene favicon aún."""
    pix = QPixmap(24, 24)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Fondo redondeado
    painter.setBrush(QBrush(QColor("#6366F1")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 20, 20, 5, 5)

    # Letra inicial del título o dominio
    letra = "🌐"
    if title and title.strip() and not title.lower().startswith("cargando") and not title.lower().startswith("nueva"):
        letra = title.strip()[0].upper()
    elif url_str and "://" in url_str:
        dom = url_str.split("://")[1].split("/")[0].replace("www.", "")
        if dom: 
            letra = dom[0].upper()

    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, letra if len(letra) == 1 else "🌐")
    painter.end()
    return QIcon(pix)

def generar_icono_cargando(angulo=0, color_hex="#6366F1"):
    """Dibuja un spinner circular moderno y nítido para la pestaña en estado de carga."""
    pix = QPixmap(24, 24)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Anillo base translúcido
    pen_bg = QPen(QColor(255, 255, 255, 45), 2.5)
    pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen_bg)
    painter.drawArc(4, 4, 16, 16, 0, 360 * 16)

    # Arco giratorio acentuado
    pen_fg = QPen(QColor(color_hex), 2.5)
    pen_fg.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen_fg)
    painter.drawArc(4, 4, 16, 16, int(angulo * 16), 110 * 16)
    painter.end()
    return QIcon(pix)

def obtener_o_generar_icono(url_str="", title="", data_dir=None, callback=None):

    cached = obtener_icono_cached(url_str, data_dir)
    if cached and not cached.isNull():
        return cached
    domain = _extract_domain(url_str)
    if domain and "." in domain and not domain.startswith(("localhost", "127.", "about")):
        import threading
        def _fetch_icon():
            try:
                import urllib.request
                u = f"https://www.google.com/s2/favicons?domain={domain}&sz=32"
                req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=4) as r:
                    data = r.read()
                pix = QPixmap()
                if pix.loadFromData(data) and not pix.isNull():
                    ico = QIcon(pix)
                    guardar_icono_en_cache(url_str, ico, data_dir)
                    if callback and callable(callback):
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(0, lambda: callback(ico))
            except Exception:
                pass
        threading.Thread(target=_fetch_icon, daemon=True).start()
    return generar_icono_por_defecto(url_str, title)


class BrowserTabBar(QTabBar):
    """Barra de pestañas personalizada con soporte para pestañas fijadas, tamaño fluido y doble clic."""
    def __init__(self, browser_parent=None):
        super().__init__()
        self.browser_parent = browser_parent
        self.setDrawBase(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setMovable(True)

    def tabSizeHint(self, index):
        hint = super().tabSizeHint(index)
        if self.browser_parent and hasattr(self.browser_parent, "tabs"):
            container = self.browser_parent.tabs.widget(index)
            if container and getattr(container, "is_pinned", False):
                # Pestaña fijada compacta (icono centrado en 34x28 px)
                return QSize(34, 28)
        
        # Pestaña normal estilizada (espacio suficiente para título y botón de cierre '✕')
        w = min(190, max(hint.width() + 28, 95))
        return QSize(w, 28)

    def tabLayoutChange(self):
        super().tabLayoutChange()
        if self.browser_parent and hasattr(self.browser_parent, "actualizar_barra_desplazamiento_pestanas"):
            self.browser_parent.actualizar_barra_desplazamiento_pestanas()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.browser_parent and hasattr(self.browser_parent, "actualizar_barra_desplazamiento_pestanas"):
            self.browser_parent.actualizar_barra_desplazamiento_pestanas()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() or event.angleDelta().x()
        if delta != 0:
            buttons = self.findChildren(QToolButton)
            left_btn = next((b for b in buttons if b.objectName() == 'ScrollLeftButton'), None)
            right_btn = next((b for b in buttons if b.objectName() == 'ScrollRightButton'), None)
            if delta < 0 and right_btn and right_btn.isEnabled():
                right_btn.click()
                event.accept()
                if self.browser_parent and hasattr(self.browser_parent, "actualizar_barra_desplazamiento_pestanas"):
                    self.browser_parent.actualizar_barra_desplazamiento_pestanas()
                return
            elif delta > 0 and left_btn and left_btn.isEnabled():
                left_btn.click()
                event.accept()
                if self.browser_parent and hasattr(self.browser_parent, "actualizar_barra_desplazamiento_pestanas"):
                    self.browser_parent.actualizar_barra_desplazamiento_pestanas()
                return
        super().wheelEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            if self.tabAt(pos) == -1:
                if self.browser_parent and hasattr(self.browser_parent, "add_new_tab"):
                    self.browser_parent.add_new_tab()
                    event.accept()
                    return
        super().mouseDoubleClickEvent(event)


class BrowserContainer(QWidget):
    """Contenedor de pestaña individual que aloja el WebView2Widget o la pantalla de reposo con historial de navegación propio."""
    def __init__(self, web_view, parent_browser, zoom=1.0, is_sleeping=False, saved_url="", nav_history=None, nav_index=None, sleep_mode="default"):
        super().__init__()
        self._web_view = web_view
        self.parent_browser = parent_browser
        self.is_pinned = False
        self.full_title = "Página Web"
        self.cached_icon = None
        self.zoom_level = float(zoom)
        self.is_sleeping = is_sleeping
        self.sleep_mode = str(sleep_mode or "default") # 'default' (según modo reposo general) o 'always_active' (siempre activa)
        self.saved_url = saved_url or (web_view.url().toString() if web_view and hasattr(web_view, "url") else "")
        self.last_active_time = time.time()
        self.is_pip_active = False
        self._placeholder_widget = None

        # Estado de carga y animación de spinner independiente por pestaña
        self.is_loading = False
        self.loading_angle = 0
        self.timer_loading = QTimer(self)
        self.timer_loading.setInterval(40)
        self.timer_loading.timeout.connect(self._on_loading_tick)

        # Historial de navegación propio e independiente de esta pestaña

        self.nav_history_stack = list(nav_history or [])
        if self.saved_url and (not self.nav_history_stack or self.saved_url not in self.nav_history_stack):
            self.nav_history_stack.append(self.saved_url)
        self.nav_history_index = int(nav_index) if nav_index is not None and 0 <= int(nav_index) < len(self.nav_history_stack) else (len(self.nav_history_stack) - 1 if self.nav_history_stack else -1)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        if self.is_sleeping or not self._web_view:
            self._mostrar_pantalla_reposo()
        else:
            self.layout.addWidget(self._web_view)

    def set_sleep_mode(self, mode: str):
        """Configura el comportamiento de reposo de esta pestaña: 'default' o 'always_active'."""
        self.sleep_mode = str(mode or "default")
        self.last_active_time = time.time()
        if self.sleep_mode == "always_active" and self.is_sleeping:
            self.despertar()

    def _mostrar_pantalla_reposo(self):
        """Muestra una tarjeta elegante de reposo cuando la pestaña está suspendida para ahorrar RAM."""
        if self._placeholder_widget:
            return

        self._placeholder_widget = QFrame(self)
        self._placeholder_widget.setStyleSheet("""
            QFrame {
                background-color: #16161E;
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

        ph_layout = QVBoxLayout(self._placeholder_widget)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.setSpacing(12)

        card = QFrame(self._placeholder_widget)
        card.setFixedWidth(460)
        card.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 24px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.setSpacing(10)

        lbl_ico = QLabel("💤", card)
        lbl_ico.setFont(QFont("Segoe UI Emoji", 36))
        lbl_ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl_ico)

        lbl_tit = QLabel("Pestaña en Reposo", card)
        lbl_tit.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_tit.setStyleSheet("color: #FFFFFF;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl_tit)

        display_title = self.full_title.replace("💤 ", "").strip() or "Página Web"
        lbl_sub = QLabel(display_title, card)
        lbl_sub.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_sub.setStyleSheet("color: #818CF8;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setWordWrap(True)
        card_layout.addWidget(lbl_sub)

        url_str = self.saved_url or "https://www.google.com"
        lbl_url = QLabel(url_str, card)
        lbl_url.setFont(QFont("Segoe UI", 10))
        lbl_url.setStyleSheet("color: #9CA3AF;")
        lbl_url.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_url.setWordWrap(True)
        card_layout.addWidget(lbl_url)

        lbl_desc = QLabel(
            "Esta pestaña fue suspendida automáticamente para ahorrar memoria RAM y procesador.\n"
            "Haz clic para activarla de inmediato sin perder tu sesión.", card
        )
        lbl_desc.setFont(QFont("Segoe UI", 10))
        lbl_desc.setStyleSheet("color: #6B7280; margin-top: 6px;")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setWordWrap(True)
        card_layout.addWidget(lbl_desc)

        btn_wake = QPushButton("⚡ Activar Pestaña", card)
        btn_wake.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_wake.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #818CF8;
            }
        """)
        btn_wake.clicked.connect(self.despertar)
        card_layout.addWidget(btn_wake, 0, Qt.AlignmentFlag.AlignCenter)

        ph_layout.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self._placeholder_widget)

    def mousePressEvent(self, event):
        """Hacer clic en cualquier parte de la pestaña en reposo la reactiva inmediatamente."""
        if self.is_sleeping:
            self.despertar()
        super().mousePressEvent(event)

    def dormir(self):
        """Suspende el WebView2 liberando toda la memoria RAM y procesos Chromium."""
        if self.is_sleeping:
            return
        if getattr(self, "sleep_mode", "default") == "always_active":
            return # Esta pestaña está configurada para permanecer siempre activa

        if self._web_view:
            if hasattr(self._web_view, "url"):
                u = self._web_view.url().toString()
                if u and not u.startswith("about:"):
                    self.saved_url = u
            if hasattr(self._web_view, "title"):
                t = self._web_view.title()
                if t and t.strip():
                    self.full_title = t
            if hasattr(self._web_view, "zoomFactor"):
                self.zoom_level = self._web_view.zoomFactor()

            # Liberar control WebView2
            if hasattr(self._web_view, "dispose_browser"):
                try:
                    self._web_view.dispose_browser()
                except Exception:
                    pass
            self.layout.removeWidget(self._web_view)
            self._web_view.deleteLater()
            self._web_view = None

        self.is_sleeping = True
        self._mostrar_pantalla_reposo()

    def despertar(self):
        """Reactiva el WebView2 recargando la URL guardada."""
        if not self.is_sleeping:
            return

        if self._placeholder_widget:
            self.layout.removeWidget(self._placeholder_widget)
            self._placeholder_widget.deleteLater()
            self._placeholder_widget = None

        from ...utils.webview2_widget import WebView2Widget

        url_to_load = self.saved_url or "https://www.google.com"
        user_data = str(self.parent_browser.data_dir) if self.parent_browser else None

        new_wv = WebView2Widget(self.parent_browser, url_to_load, user_data, initial_zoom=self.zoom_level)
        self._web_view = new_wv
        self.layout.addWidget(self._web_view)
        self.is_sleeping = False
        self.last_active_time = time.time()

        if self.parent_browser and hasattr(self.parent_browser, "_conectar_senales_webview"):
            self.parent_browser._conectar_senales_webview(new_wv, self)

        if hasattr(new_wv, "setZoomFactor"):
            new_wv.setZoomFactor(self.zoom_level)

        if self.parent_browser and hasattr(self.parent_browser, "_actualizar_estado_pestana_despertada"):
            self.parent_browser._actualizar_estado_pestana_despertada(self)

    def iniciar_animacion_carga(self):
        """Inicia el spinner animado suave en la pestaña."""
        self.is_loading = True
        self.loading_angle = 0
        if not self.timer_loading.isActive():
            self.timer_loading.start()

    def detener_animacion_carga(self):
        """Detiene el spinner animado y restaura el favicon de la página."""
        self.is_loading = False
        if self.timer_loading.isActive():
            self.timer_loading.stop()

        # Restaurar icono real
        if self.parent_browser and hasattr(self.parent_browser, "tabs"):
            tabs = self.parent_browser.tabs
            idx = tabs.indexOf(self)
            if idx != -1:
                target_ico = self.cached_icon
                if not target_ico or target_ico.isNull():
                    u_str = self.url().toString()
                    target_ico = obtener_o_generar_icono(u_str, self.title(), self.parent_browser.data_dir, callback=self.actualizar_icono)
                tabs.setTabIcon(idx, target_ico)

    def _on_loading_tick(self):
        """Frame de rotación del spinner de carga."""
        if not self.is_loading:
            self.timer_loading.stop()
            return

        self.loading_angle = (self.loading_angle + 28) % 360
        acento = "#6366F1"
        if self.parent_browser and hasattr(self.parent_browser, "colores"):
            acento = self.parent_browser.colores.get("acento", "#6366F1")

        spin_ico = generar_icono_cargando(self.loading_angle, acento)
        if self.parent_browser and hasattr(self.parent_browser, "tabs"):
            idx = self.parent_browser.tabs.indexOf(self)
            if idx != -1:
                self.parent_browser.tabs.setTabIcon(idx, spin_ico)

    def actualizar_icono(self, ico):
        """Actualiza el icono de esta pestaña si se cargó o descargó dinámicamente."""
        if not ico or ico.isNull():
            return
        self.cached_icon = ico
        if not self.is_loading and self.parent_browser and hasattr(self.parent_browser, "tabs"):
            tabs = self.parent_browser.tabs
            idx = tabs.indexOf(self)
            if idx != -1:
                tabs.setTabIcon(idx, ico)


    def url(self):
        if self.is_sleeping or not self._web_view:
            return QUrl(self.saved_url)
        return self._web_view.url() if hasattr(self._web_view, "url") else QUrl(self.saved_url)

    def title(self):
        if self.is_sleeping or not self._web_view:
            return self.full_title
        return self._web_view.title() if hasattr(self._web_view, "title") else self.full_title

    def registrar_url(self, url_str):
        """Registra una URL en el historial propio de esta pestaña sin duplicados inmediatos."""
        if not url_str or url_str.startswith(("about:", "data:", "javascript:")):
            return
        
        self.saved_url = url_str
        # Si ya estábamos en esta URL, no duplicar
        if self.nav_history_stack and 0 <= self.nav_history_index < len(self.nav_history_stack):
            if self.nav_history_stack[self.nav_history_index] == url_str:
                return

        # Si el usuario navegó hacia atrás y luego cargó una nueva URL, descartar el futuro
        if 0 <= self.nav_history_index < len(self.nav_history_stack) - 1:
            self.nav_history_stack = self.nav_history_stack[:self.nav_history_index + 1]

        self.nav_history_stack.append(url_str)
        if len(self.nav_history_stack) > 50:
            self.nav_history_stack.pop(0)
        self.nav_history_index = len(self.nav_history_stack) - 1

    def can_go_back(self):
        if self._web_view and hasattr(self._web_view, "canGoBack") and self._web_view.canGoBack():
            return True
        return self.nav_history_index > 0

    def can_go_forward(self):
        if self._web_view and hasattr(self._web_view, "canGoForward") and self._web_view.canGoForward():
            return True
        return 0 <= self.nav_history_index < len(self.nav_history_stack) - 1

    def go_back(self):
        """Retrocede en el historial nativo o en el stack propio si la sesión fue recién restaurada."""
        if self.is_sleeping:
            self.despertar()

        if self._web_view and hasattr(self._web_view, "canGoBack") and self._web_view.canGoBack():
            self._web_view.back()
            if self.nav_history_index > 0:
                self.nav_history_index -= 1
            return

        # Fallback a pila propia de navegación persistida
        if self.nav_history_index > 0:
            self.nav_history_index -= 1
            prev_url = self.nav_history_stack[self.nav_history_index]
            self.saved_url = prev_url
            if self._web_view and hasattr(self._web_view, "load"):
                self._web_view.load(QUrl(prev_url))

    def go_forward(self):
        """Avanza en el historial nativo o en el stack propio."""
        if self.is_sleeping:
            self.despertar()

        if self._web_view and hasattr(self._web_view, "canGoForward") and self._web_view.canGoForward():
            self._web_view.forward()
            if self.nav_history_index < len(self.nav_history_stack) - 1:
                self.nav_history_index += 1
            return

        if 0 <= self.nav_history_index < len(self.nav_history_stack) - 1:
            self.nav_history_index += 1
            next_url = self.nav_history_stack[self.nav_history_index]
            self.saved_url = next_url
            if self._web_view and hasattr(self._web_view, "load"):
                self._web_view.load(QUrl(next_url))

    def reload(self):
        if self.is_sleeping:
            self.despertar()
        elif self._web_view and hasattr(self._web_view, "reload"):
            self._web_view.reload()

    def stop(self):
        if self._web_view and hasattr(self._web_view, "stop"):
            self._web_view.stop()

    def load(self, qurl):
        self.saved_url = qurl.toString()
        if self.is_sleeping:
            self.despertar()
        elif self._web_view and hasattr(self._web_view, "load"):
            self._web_view.load(qurl)

    def setUrl(self, qurl):
        self.load(qurl)

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "_web_view") and self._web_view and hasattr(self._web_view, "blur_web"):
            self._web_view.blur_web()
