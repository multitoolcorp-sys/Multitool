"""
toolbar.py - Barra de herramientas moderna con botón de 3 puntos (⋮) y control de zoom flotante
"""

from PyQt6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, 
    QLabel, QMenu, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QIcon, QAction, QCursor, QKeySequence


class ZoomFloatingWidget(QFrame):
    """Burbuja flotante de zoom estilo Chrome/Edge que aparece al pulsar Ctrl+Rueda o Ctrl++/Ctrl--."""
    zoom_changed = pyqtSignal(float)
    reset_requested = pyqtSignal()

    def __init__(self, parent=None, colores=None):
        super().__init__(parent)
        self.colores = colores or {
            "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D", "acento": "#6366F1", "fg_principal": "#FFFFFF"
        }
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(f"""
            QFrame#ZoomBubble {{
                background-color: rgba(30, 30, 46, 0.95);
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 18px;
                padding: 4px 10px;
            }}
            QPushButton {{
                background: transparent;
                color: #FFFFFF;
                border: none;
                font-weight: bold;
                font-size: 13px;
                padding: 2px 6px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.12);
                color: #818CF8;
            }}
            QLabel {{
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial;
                font-size: 11px;
                font-weight: bold;
                padding: 0 4px;
            }}
        """)
        self.setObjectName("ZoomBubble")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        # Botón Menos
        self.btn_minus = QPushButton("➖")
        self.btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minus.clicked.connect(self._on_minus_clicked)
        layout.addWidget(self.btn_minus)

        # Etiqueta Porcentaje
        self.lbl_percent = QLabel("100%")
        self.lbl_percent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_percent)

        # Botón Más
        self.btn_plus = QPushButton("➕")
        self.btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plus.clicked.connect(self._on_plus_clicked)
        layout.addWidget(self.btn_plus)

        # Botón Restablecer
        self.btn_reset = QPushButton("↺")
        self.btn_reset.setToolTip("Restablecer a 100%")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.clicked.connect(self._on_reset_clicked)
        layout.addWidget(self.btn_reset)

        self.timer_autohide = QTimer(self)
        self.timer_autohide.setSingleShot(True)
        self.timer_autohide.timeout.connect(self.hide)

        self.current_factor = 1.0
        self.hide()

    def show_zoom(self, factor, target_global_pos):
        self.current_factor = factor
        percent = int(round(factor * 100))
        self.lbl_percent.setText(f"{percent}%")
        self.adjustSize()

        # Posicionar centrado respecto a la posición objetivo
        w = self.sizeHint().width()
        x = target_global_pos.x() - w // 2
        y = target_global_pos.y() + 6
        self.move(x, y)
        self.show()
        self.raise_()
        self.timer_autohide.start(3000)

    def _on_minus_clicked(self):
        new_factor = max(0.25, round(self.current_factor - 0.1, 2))
        self.zoom_changed.emit(new_factor)
        self.timer_autohide.start(3000)

    def _on_plus_clicked(self):
        new_factor = min(5.0, round(self.current_factor + 0.1, 2))
        self.zoom_changed.emit(new_factor)
        self.timer_autohide.start(3000)

    def _on_reset_clicked(self):
        self.reset_requested.emit()
        self.timer_autohide.start(3000)


class BrowserToolbar(QFrame):
    """Barra de navegación con botón de 3 puntos (⋮), URL bar y controles esenciales."""
    def __init__(self, browser_parent, colores):
        super().__init__(browser_parent)
        self.browser_parent = browser_parent
        self.colores = colores
        self.font_family = "Segoe UI"

        self.setStyleSheet(f"""
            QFrame#BrowserToolbar {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }}
        """)
        self.setObjectName("BrowserToolbar")

        self.layout_toolbar = QHBoxLayout(self)
        self.layout_toolbar.setContentsMargins(8, 4, 8, 4)
        self.layout_toolbar.setSpacing(6)

        # 1. Botones de Navegación Esenciales
        self.btn_back = self._crear_boton("◀", "Atrás (Alt+←)", self.browser_parent.navigate_back)
        self.layout_toolbar.addWidget(self.btn_back)

        self.btn_forward = self._crear_boton("▶", "Adelante (Alt+→)", self.browser_parent.navigate_forward)
        self.layout_toolbar.addWidget(self.btn_forward)

        self.btn_reload = self._crear_boton("🔄", "Recargar página (Ctrl+R / F5)", self.browser_parent.reload_page)
        self.layout_toolbar.addWidget(self.btn_reload)

        self.btn_home = self._crear_boton("🏠", "Página principal (Google)", self.browser_parent.go_home)
        self.layout_toolbar.addWidget(self.btn_home)

        # 2. Barra de Direcciones URL + Badge de Zoom integrado
        url_frame = QFrame()
        url_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_principal', '#121218')};
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
            }}
            QFrame:focus-within {{
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
        url_lay = QHBoxLayout(url_frame)
        url_lay.setContentsMargins(8, 2, 6, 2)
        url_lay.setSpacing(6)

        self.btn_site_info = QPushButton("🔒")
        self.btn_site_info.setFixedSize(22, 22)
        self.btn_site_info.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_site_info.setToolTip("Ver permisos y seguridad de este sitio")
        self.btn_site_info.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 11px;
                padding: 0px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
            }
        """)
        self.btn_site_info.clicked.connect(self.browser_parent.mostrar_permisos_sitio_actual)
        url_lay.addWidget(self.btn_site_info)


        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Busca en Google o escribe una dirección URL...")
        self.url_bar.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial;
                font-size: 12px;
                padding: 4px 0;
            }
        """)
        self.url_bar.returnPressed.connect(self.browser_parent.navigate_to_url)
        orig_focus_in = self.url_bar.focusInEvent
        def _on_url_focus(event):
            if hasattr(self.browser_parent, "get_current_browser"):
                cwv = self.browser_parent.get_current_browser()
                if cwv and hasattr(cwv, "blur_web"):
                    cwv.blur_web()
            orig_focus_in(event)
        self.url_bar.focusInEvent = _on_url_focus
        url_lay.addWidget(self.url_bar, 1)

        # Badge interactivo de Zoom (aparece en la barra cuando zoom != 100%)
        self.btn_zoom_badge = QPushButton("100%")
        self.btn_zoom_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zoom_badge.setToolTip("Zoom activo. Clic para ajustar.")
        self.btn_zoom_badge.setStyleSheet(f"""
            QPushButton {{
                background: rgba(99, 102, 241, 0.2);
                color: #A5B4FC;
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 10px;
                padding: 1px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
            }}
        """)
        self.btn_zoom_badge.clicked.connect(self._on_zoom_badge_clicked)
        self.btn_zoom_badge.setVisible(False)
        url_lay.addWidget(self.btn_zoom_badge)

        self.layout_toolbar.addWidget(url_frame, 1)

        # 3. Botones visibles en barra: Fijar, Descargas, Extensiones, Pantalla Completa y 3 Puntos
        self.btn_pin = self._crear_boton("📌", "Fijar / Desfijar pestaña actual", self.browser_parent.toggle_pin_current_tab)
        self.layout_toolbar.addWidget(self.btn_pin)

        self.btn_downloads = self._crear_boton("📥", "Descargas (Ctrl+J) / Clic para panel emergente", self.browser_parent.toggle_downloads_flyout)
        self.btn_downloads.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_downloads.customContextMenuRequested.connect(self._mostrar_menu_descargas)
        self.layout_toolbar.addWidget(self.btn_downloads)

        self.btn_extensions = self._crear_boton("🧩", "Extensiones instaladas", self.browser_parent.mostrar_dialogo_extensiones)
        self.layout_toolbar.addWidget(self.btn_extensions)

        self.btn_fullscreen = self._crear_boton("⛶", "Pantalla Completa (F11)", lambda: self.browser_parent.toggle_fullscreen_mode())
        self.layout_toolbar.addWidget(self.btn_fullscreen)

        # Botón de 3 Puntos (⋮)
        self.btn_menu = self._crear_boton("⋮", "Más herramientas y opciones", self._mostrar_menu_tres_puntos)
        self.btn_menu.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.layout_toolbar.addWidget(self.btn_menu)

        # Widget flotante de Zoom
        self.zoom_bubble = ZoomFloatingWidget(self.window(), self.colores)
        self.zoom_bubble.zoom_changed.connect(self.browser_parent.set_zoom_direct)
        self.zoom_bubble.reset_requested.connect(self.browser_parent.reset_zoom)

    def _crear_boton(self, text, tooltip, callback):
        btn = QPushButton(text)
        btn.setFixedSize(32, 30)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores.get('fg_principal', '#FFFFFF')};
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-family: 'Segoe UI Emoji', 'Segoe UI', Arial;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.08);
                color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def iniciar_animacion_recarga(self):
        """Inicia el spinner dinámico rotatorio en el botón de recarga en lugar de un icono estático."""
        if not hasattr(self, "_timer_reload_anim"):
            self._timer_reload_anim = QTimer(self)
            self._timer_reload_anim.setInterval(40)
            self._reload_angle = 0
            self._timer_reload_anim.timeout.connect(self._on_reload_anim_tick)
        self.btn_reload.setText("")
        self.btn_reload.setToolTip("Detener carga (Esc)")
        if not self._timer_reload_anim.isActive():
            self._reload_angle = 0
            self._timer_reload_anim.start()

    def detener_animacion_recarga(self):
        """Detiene el spinner y vuelve al icono estándar de recargar página."""
        if hasattr(self, "_timer_reload_anim") and self._timer_reload_anim.isActive():
            self._timer_reload_anim.stop()
        self.btn_reload.setIcon(QIcon())
        self.btn_reload.setText("🔄")
        self.btn_reload.setToolTip("Recargar página (Ctrl+R / F5)")

    def _on_reload_anim_tick(self):
        self._reload_angle = (self._reload_angle + 30) % 360
        from .container import generar_icono_cargando
        ico = generar_icono_cargando(self._reload_angle, self.colores.get("acento", "#6366F1"))
        self.btn_reload.setIcon(ico)

    def actualizar_badge_zoom(self, zoom_factor):
        factor = round(float(zoom_factor), 2)
        if factor != 1.0:
            percent = int(round(factor * 100))
            self.btn_zoom_badge.setText(f"🔍 {percent}%")
            self.btn_zoom_badge.setVisible(True)
        else:
            self.btn_zoom_badge.setVisible(False)

    def mostrar_burbuja_zoom(self, zoom_factor):
        self.actualizar_badge_zoom(zoom_factor)
        target_pos = self.btn_zoom_badge.mapToGlobal(QPoint(self.btn_zoom_badge.width() // 2, self.btn_zoom_badge.height()))
        self.zoom_bubble.show_zoom(zoom_factor, target_pos)

    def _on_zoom_badge_clicked(self):
        curr_zoom = getattr(self.browser_parent, "zoom_level", 1.0)
        target_pos = self.btn_zoom_badge.mapToGlobal(QPoint(self.btn_zoom_badge.width() // 2, self.btn_zoom_badge.height()))
        self.zoom_bubble.show_zoom(curr_zoom, target_pos)

    def actualizar_descargas(self, count):
        """Actualiza el indicador visual del botón de descargas en la barra."""
        if count > 0:
            self.btn_downloads.setText(f"📥 {count}")
            self.btn_downloads.setToolTip(f"Descargando {count} archivo(s)... Haz clic para ver detalles (Ctrl+J)")
            self.btn_downloads.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores.get('acento', '#6366F1')};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 2px 6px;
                }}
            """)
        else:
            self.btn_downloads.setText("📥")
            self.btn_downloads.setToolTip("Ver Descargas (Ctrl+J)")
            self.btn_downloads.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {self.colores.get('fg_principal', '#FFFFFF')};
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.08);
                    color: {self.colores.get('acento', '#6366F1')};
                }}
            """)

    def _mostrar_menu_tres_puntos(self):
        """Despliega el menú elegante de 3 puntos con las opciones del navegador."""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', Arial;
                font-size: 11px;
            }}
            QMenu::item {{
                padding: 7px 24px 7px 14px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
            }}
            QMenu::separator {{
                height: 1px;
                background: rgba(255, 255, 255, 0.08);
                margin: 4px 6px;
            }}
        """)

        # 1. Pestañas
        act_new_tab = menu.addAction("➕ Nueva Pestaña\tCtrl+T")
        act_new_tab.triggered.connect(lambda: self.browser_parent.add_new_tab())

        act_close_tab = menu.addAction("✖️ Cerrar Pestaña Actual\tCtrl+W")
        act_close_tab.triggered.connect(lambda: self.browser_parent.close_tab(self.browser_parent.tabs.currentIndex()))

        menu.addSeparator()

        # 2. Favoritos, Historial y Descargas
        act_fav = menu.addAction("⭐ Guardar en Favoritos...\tCtrl+D")
        act_fav.triggered.connect(self.browser_parent.guardar_marcador_actual)

        act_hist = menu.addAction("📜 Historial de Navegación\tCtrl+H")
        act_hist.triggered.connect(self.browser_parent.abrir_historial_submodulo)

        act_dl = menu.addAction("📥 Descargas Realizadas\tCtrl+J")
        act_dl.triggered.connect(self.browser_parent.abrir_pestana_descargas)

        menu.addSeparator()

        # 3. Herramientas de Página
        act_find = menu.addAction("🔍 Buscar en la Página...\tCtrl+F")
        act_find.triggered.connect(self.browser_parent.mostrar_barra_busqueda)

        act_print = menu.addAction("🖨️ Imprimir Página...\tCtrl+P")
        act_print.triggered.connect(self.browser_parent.imprimir_pagina)

        menu.addSeparator()

        # 4. Configuración y Seguridad
        act_perm = menu.addAction("🔒 Permisos de Sitios Web...")
        act_perm.triggered.connect(self.browser_parent.mostrar_dialogo_permisos)

        act_proxy = menu.addAction("🛡️ Servidores Proxy...")
        act_proxy.triggered.connect(self.browser_parent.mostrar_dialogo_proxy)

        act_devtools = menu.addAction("🛠️ Herramientas de Desarrollador\tF12")
        act_devtools.triggered.connect(self.browser_parent.abrir_devtools)

        menu.addSeparator()

        act_dl_cfg = menu.addAction("⚙️ Configuración de Descargas...")
        act_dl_cfg.triggered.connect(self.browser_parent.mostrar_dialogo_configuracion_descargas)

        menu.addSeparator()

        # 5. Mantenimiento y Rendimiento
        act_sleep = menu.addAction("💤 Ahorro de Memoria RAM (Modo Reposo)...")
        act_sleep.triggered.connect(self.browser_parent.mostrar_dialogo_configuracion_reposo)

        act_clear = menu.addAction("🧹 Borrar Datos de Navegación...")
        act_clear.triggered.connect(self.browser_parent.limpiar_datos_navegacion)

        # Posicionar bajo el botón de 3 puntos
        pos = self.btn_menu.mapToGlobal(QPoint(0, self.btn_menu.height() + 2))
        menu.exec(pos)

    def _mostrar_menu_descargas(self, pos):
        """Muestra opciones rápidas al hacer clic derecho sobre el botón de descargas."""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', Arial;
                font-size: 11px;
            }}
            QMenu::item {{ padding: 6px 18px 6px 12px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {self.colores.get('acento', '#6366F1')}; }}
        """)
        act_open = menu.addAction("📥 Ver Descargas (Ctrl+J)")
        act_open.triggered.connect(self.browser_parent.abrir_pestana_descargas)
        act_cfg = menu.addAction("⚙️ Configuración de Descargas...")
        act_cfg.triggered.connect(self.browser_parent.mostrar_dialogo_configuracion_descargas)
        menu.exec(self.btn_downloads.mapToGlobal(pos))

    def actualizar_descargas(self, count):
        """Actualiza el indicador visual del botón de descargas en la barra en tiempo real."""
        if not hasattr(self, "btn_downloads") or self.btn_downloads is None:
            return
        if count > 0:
            self.btn_downloads.setText(f"📥 {count}")
            self.btn_downloads.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores.get('acento', '#6366F1')};
                    color: #FFFFFF;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0px 4px;
                    border: none;
                }}
                QPushButton:hover {{
                    background: {self.colores.get('acento_hover', '#818CF8')};
                }}
            """)
            self.btn_downloads.setFixedWidth(48)
        else:
            self.btn_downloads.setText("📥")
            self.btn_downloads.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {self.colores.get('fg_principal', '#FFFFFF')};
                    border-radius: 6px;
                    font-size: 12px;
                    border: none;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.1);
                }}
            """)
            self.btn_downloads.setFixedWidth(32)
