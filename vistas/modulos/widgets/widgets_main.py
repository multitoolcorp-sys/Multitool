"""
widgets_main.py — Módulo Principal de Widgets Flotantes y de Escritorio de MultiTool
Controlador central que orquesta la galería de widgets, modos de ejecución, perfiles y panel flotante.
"""
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QRadioButton, QCheckBox, QLabel,
    QPushButton, QLineEdit, QStackedWidget, QScrollArea, QFrame, QGridLayout,
    QApplication, QButtonGroup
)
from PyQt6.QtCore import Qt, QTimer, QCoreApplication
from PyQt6.QtGui import QRegion

# Submódulos modulares
from .submodulos.center_views import CenteredWidgetWindow
from .submodulos.floating_panel import DesktopWidgetWindow, FloatingWidgetPanel
from .submodulos.window_cards import ModuleWindowCard
from .submodulos.floating_dock import (
    DockedCircleWidget, FloatingWidgetCoordinator, FloatingWidgetWindow
)
from .submodulos.quick_widgets import (
    QuickWidgetBase, QuickExtraToolWindow, GenericModuleWidget,
    QuickNotesWidget, QuickCalculatorWidget, QuickCommandWidget,
    QuickBrowserWidget, QuickSecurityWidget, QuickFilesWidget,
    QuickCalendarWidget, QuickSystemWidget, QuickPlayerWidget,
    QuickRecorderWidget, QuickNotebookWidget, QuickChatWidget,
    QuickExtrasWidget, QuickMiniGamesWidget, QuickTimeWidget,
    QuickTranslatorWidget
)
from .submodulos.new_widgets import (
    QuickStickyNotesWidget, QuickLauncherWidget, QuickSystemHUDWidget
)


class TabWidgets(QWidget):
    """Módulo Principal de Widgets Flotantes de Escritorio"""
    def __init__(self, parent, context, colores=None):
        super().__init__(parent)
        self.context = context
        ruta = getattr(context, "ruta_usuario", ".")
        self.config_path = Path(ruta) / "widgets_config.json"
        
        self.colores = colores or getattr(getattr(context, "app", None), "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171"
        })

        self.floating_widget = None
        self._module_cards = {}
        
        self.cargar_configuracion()
        self.init_ui()

        self.actualizar_floating_widget_state()

        self.background_timer = QTimer(self)
        self.background_timer.timeout.connect(self.monitorear_segundo_plano)
        self.background_timer.start(500)

        app_inst = QCoreApplication.instance()
        if app_inst:
            app_inst.aboutToQuit.connect(self.cleanup)

    def cargar_configuracion(self):
        self.config = {
            "mode": "background",
            "widgets": {
                "notas": True, "notes": True, "calc": True, "calculadora": True,
                "terminal": True, "navegador": True, "seguridad": True,
                "archivos": True, "calendario": True, "sistema": True,
                "reproductor": True, "grabadora": True, "cuaderno": True,
                "chat": True, "extras": True, "minigames": True,
                "tiempo": True, "traductor": True, "proyectos": True,
                "postits": True, "launcher": True, "syshud": True
            }
        }
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                    if "mode" in user_cfg:
                        self.config["mode"] = user_cfg["mode"]
                    if "widgets" in user_cfg:
                        self.config["widgets"].update(user_cfg["widgets"])
            except Exception:
                pass

    def guardar_configuracion(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception:
            pass

    def _open_module_in_app(self, key):
        """Abre el módulo correspondiente dentro de la aplicación principal si está disponible"""
        main_win = getattr(self.context, "app", None) or getattr(self.context, "main_window", None)
        if main_win:
            if hasattr(main_win, "modulos_cargados"):
                visibles = [m for m in main_win.modulos_cargados if m.get("visible", True)]
                for idx, mod in enumerate(visibles):
                    if mod.get("name", "").lower() == key.lower() or mod.get("folder", "").lower() == key.lower():
                        if hasattr(main_win, "stack_modulos"):
                            main_win.stack_modulos.setCurrentIndex(idx)
                        if hasattr(main_win, "menu_list"):
                            main_win.menu_list.setCurrentRow(idx)
                        return
            notebook = getattr(main_win, "notebook", None)
            if notebook:
                for i in range(notebook.count()):
                    tab_text = notebook.tabText(i).lower().strip()
                    if tab_text == key.lower() or tab_text == key.capitalize().lower():
                        notebook.setCurrentIndex(i)
                        return
        self._launch_floating(key)

    def _launch_floating(self, key):
        """Abre el widget como ventana flotante centrada"""
        if not isinstance(key, str) or not key.strip():
            return
        if self.floating_widget is None:
            self.actualizar_floating_widget_state()
        if self.floating_widget:
            self.floating_widget.show()
            self.floating_widget.abrir_widget_centro(key)

    def _pin_to_desktop(self, key):
        """Fija el widget al escritorio"""
        if not isinstance(key, str) or not key.strip():
            return
        if self.floating_widget is None:
            self.actualizar_floating_widget_state()
        if self.floating_widget:
            self.floating_widget.show()
            self.floating_widget.pin_widget_from_center(key)

    def _aplicar_perfil(self, keys):
        """Aplica un paquete/perfil de widgets fijados al escritorio"""
        for k in keys:
            self._pin_to_desktop(k)

    def desfijar_todos(self):
        """Desfija todos los widgets del escritorio"""
        if self.floating_widget:
            self.floating_widget.desfijar_todos_los_widgets()

    def init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Barra superior moderna ─────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setFixedHeight(64)
        header_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.colores['bg_secundario']},
                    stop:1 {self.colores['bg_principal']});
                border-bottom: 1px solid {self.colores['bg_terciario']};
            }}
        """)
        header_lay = QHBoxLayout(header_frame)
        header_lay.setContentsMargins(20, 0, 20, 0)
        header_lay.setSpacing(10)

        lbl_title = QLabel("🧩 Módulos & Quick Widgets")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        header_lay.addWidget(lbl_title)

        header_lay.addStretch()

        # Botones de Perfiles de Escritorio
        lbl_presets = QLabel("Perfiles:")
        lbl_presets.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        header_lay.addWidget(lbl_presets)

        presets = [
            ("💼 Trabajo", ["notas", "postits", "cuaderno", "calendario"]),
            ("🎵 Multimedia", ["reproductor", "tiempo", "chat"]),
            ("🎮 Gaming", ["minigames", "syshud", "reproductor"]),
            ("🚀 Código", ["proyectos", "terminal", "archivos"])
        ]
        for pname, pkeys in presets:
            btn_p = QPushButton(pname)
            btn_p.setFixedHeight(28)
            btn_p.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_p.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores['bg_terciario']}; color: white;
                    border-radius: 6px; padding: 0 10px; font-size: 11px; font-weight: bold;
                    border: 1px solid rgba(255,255,255,0.06);
                }}
                QPushButton:hover {{
                    background: {self.colores['acento']}; border-color: transparent;
                }}
            """)
            btn_p.clicked.connect(lambda checked, ks=pkeys: self._aplicar_perfil(ks))
            header_lay.addWidget(btn_p)

        btn_unpin_all = QPushButton("🗑️ Desfijar Todo")
        btn_unpin_all.setFixedHeight(28)
        btn_unpin_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_unpin_all.setStyleSheet(f"""
            QPushButton {{
                background: rgba(248, 113, 113, 0.15); color: #F87171;
                border: 1px solid rgba(248, 113, 113, 0.3); border-radius: 6px;
                padding: 0 10px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover {{
                background: #F87171; color: white;
            }}
        """)
        btn_unpin_all.clicked.connect(self.desfijar_todos)
        header_lay.addWidget(btn_unpin_all)

        btn_settings = QPushButton("⚙ Configuración")
        btn_settings.setFixedHeight(30)
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.setCheckable(True)
        btn_settings.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores['fg_secundario']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover {{ color: white; border-color: {self.colores['acento']}; }}
            QPushButton:checked {{ background: {self.colores['acento']}; color: white; border-color: transparent; }}
        """)
        header_lay.addWidget(btn_settings)
        outer.addWidget(header_frame)

        # ── Stacked area: cards / settings ──────────────────────────────
        self.view_stack = QStackedWidget()
        outer.addWidget(self.view_stack)

        # ── Page 0: Module cards ─────────────────────────────────────────
        cards_page = QWidget()
        cards_page.setStyleSheet(f"background: {self.colores['bg_principal']};")
        cards_outer = QVBoxLayout(cards_page)
        cards_outer.setContentsMargins(20, 16, 20, 16)
        cards_outer.setSpacing(12)

        top_cards_bar = QHBoxLayout()
        lbl_sub = QLabel("Haz clic en cualquier tarjeta para abrir su vista flotante o fijarla al escritorio:")
        lbl_sub.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        top_cards_bar.addWidget(lbl_sub)
        top_cards_bar.addStretch()

        self.txt_filter_cards = QLineEdit()
        self.txt_filter_cards.setPlaceholderText("🔍 Filtrar widgets...")
        self.txt_filter_cards.setFixedWidth(200)
        self.txt_filter_cards.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_secundario']}; color: white;
                border: 1px solid {self.colores['bg_terciario']}; border-radius: 6px;
                padding: 4px 10px; font-size: 11px;
            }}
            QLineEdit:focus {{ border-color: {self.colores['acento']}; }}
        """)
        self.txt_filter_cards.textChanged.connect(self._filtrar_tarjetas)
        top_cards_bar.addWidget(self.txt_filter_cards)
        cards_outer.addLayout(top_cards_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical { border: none; background: rgba(0,0,0,0.08); width: 6px; margin: 0; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); min-height: 20px; border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { background: none; border: none; }
        """)

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 6, 0)

        # Descubrimiento dinámico de módulos
        from vistas.configurations import discover_modules_and_plugins
        ruta_usuario = getattr(self.context, "ruta_usuario", None)
        try:
            discovered = discover_modules_and_plugins(ruta_usuario)
        except Exception:
            discovered = []

        DEFAULT_META = {
            "notas": ("📝", "Notas", "Crea y edita notas rápidas"),
            "notes": ("📝", "Notas", "Crea y edita notas rápidas"),
            "postits": ("📌", "Notas Adhesivas", "Post-Its flotantes de colores"),
            "calculadora": ("🧮", "Calculadora", "Calculadora científica de acceso rápido"),
            "calc": ("🧮", "Calculadora", "Calculadora científica de acceso rápido"),
            "terminal": ("⌨️", "Terminal", "Ejecuta comandos del sistema"),
            "navegador": ("🌐", "Navegador", "Abre y gestiona enlaces web"),
            "launcher": ("🚀", "Lanzador Rápido", "Accesos a apps, carpetas y URLs"),
            "seguridad": ("🔒", "Seguridad", "Estado y copias de seguridad"),
            "archivos": ("📁", "Archivos", "Explora tu directorio de usuario"),
            "calendario": ("📅", "Calendario", "Eventos y recordatorios"),
            "sistema": ("💻", "Sistema", "Conexiones y estado del sistema"),
            "syshud": ("📈", "HUD Sistema", "Monitor de CPU, RAM y red"),
            "reproductor": ("▶️", "Reproductor", "Reproduce video con flotación"),
            "grabadora": ("🎙️", "Grabadora", "Graba audio y video"),
            "cuaderno": ("📓", "Cuaderno", "Cuaderno y hojas de cálculo"),
            "chat": ("💬", "Chat", "Conversa con el asistente bot"),
            "extras": ("🛠️", "Extras", "Herramientas adicionales y recortes"),
            "minigames": ("🎮", "MiniGames", "Juegos: Buscaminas, Snake y Ruleta"),
            "tiempo": ("⏱️", "Tiempo", "Reloj, cronómetro y temporizador"),
            "traductor": ("🌍", "Traductor", "Traduce texto entre idiomas"),
            "proyectos": ("💼", "Proyectos", "Gestión Kanban y Scrum"),
            "general": ("📊", "General", "Dashboard general y métricas"),
            "cuenta": ("👤", "Cuenta", "Perfil y bóveda del usuario"),
        }

        MODULE_INFO = []
        seen_keys = set()
        for m in discovered:
            folder = m.get("folder", "").lower()
            name = m.get("name", folder.capitalize())
            if folder == "widgets" or name.lower() == "widgets":
                continue
            key = folder if folder else name.lower()
            if key in seen_keys:
                continue
            seen_keys.add(key)
            meta = DEFAULT_META.get(key)
            if meta:
                emoji, d_name, desc = meta
            else:
                emoji = "🧩"
                d_name = name
                desc = m.get("description", f"Módulo {name}")
            MODULE_INFO.append((key, emoji, d_name, desc))

        SPECIAL_WIDGETS = [
            ("postits", "📌", "Notas Adhesivas", "Post-Its flotantes de colores"),
            ("launcher", "🚀", "Lanzador Rápido", "Accesos a apps, carpetas y URLs"),
            ("syshud", "📈", "HUD Sistema", "Monitor de CPU, RAM y red")
        ]
        for skey, semoji, sname, sdesc in SPECIAL_WIDGETS:
            if skey not in seen_keys:
                seen_keys.add(skey)
                MODULE_INFO.append((skey, semoji, sname, sdesc))

        COLS = 3
        self._module_cards = {}
        for idx, (key, emoji, name, desc) in enumerate(MODULE_INFO):
            visible = self.config.get("widgets", {}).get(key, True)
            card = ModuleWindowCard(
                key, name, emoji, desc, self.colores,
                on_open=lambda *args, k=key: self._open_module_in_app(k),
                on_pin=lambda *args, k=key: self._pin_to_desktop(k)
            )
            card.setVisible(visible)
            self._module_cards[key] = card
            row, col = divmod(idx, COLS)
            grid.addWidget(card, row, col)

        scroll.setWidget(grid_widget)
        cards_outer.addWidget(scroll)
        self.view_stack.addWidget(cards_page)

        # ── Page 1: Settings ─────────────────────────────────────────────
        settings_page = QWidget()
        settings_page.setStyleSheet(f"background: {self.colores['bg_principal']};")
        settings_lay = QVBoxLayout(settings_page)
        settings_lay.setContentsMargins(24, 20, 24, 20)
        settings_lay.setSpacing(16)

        # Behavior group
        group_behavior = QFrame()
        group_behavior.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 8px;
            }}
        """)
        behavior_lay = QVBoxLayout(group_behavior)
        behavior_lay.setContentsMargins(15, 15, 15, 15)
        behavior_lay.setSpacing(8)

        lbl_beh_title = QLabel("⚙ Comportamiento del Widget Flotante:")
        lbl_beh_title.setStyleSheet("font-weight: bold; font-size: 13px; color: white; border: none;")
        behavior_lay.addWidget(lbl_beh_title)

        self.btn_group_beh = QButtonGroup(self)
        self.rad_hidden = QRadioButton("Ocultar – no mostrar nada")
        self.rad_hidden.setStyleSheet("color: #AAA; border: none;")
        self.btn_group_beh.addButton(self.rad_hidden)
        behavior_lay.addWidget(self.rad_hidden)

        self.rad_always = QRadioButton("Siempre visible en el escritorio")
        self.rad_always.setStyleSheet("color: #AAA; border: none;")
        self.btn_group_beh.addButton(self.rad_always)
        behavior_lay.addWidget(self.rad_always)

        self.rad_bg = QRadioButton("Solo cuando la app esté minimizada")
        self.rad_bg.setStyleSheet("color: #AAA; border: none;")
        self.btn_group_beh.addButton(self.rad_bg)
        behavior_lay.addWidget(self.rad_bg)

        self.rad_focus = QRadioButton("Al perder foco / Alt+Tab (Aparece al cambiar de ventana o minimizar)")
        self.rad_focus.setStyleSheet("color: #AAA; border: none;")
        self.btn_group_beh.addButton(self.rad_focus)
        behavior_lay.addWidget(self.rad_focus)

        mode = self.config.get("mode", "background")
        if mode == "hidden":
            self.rad_hidden.setChecked(True)
        elif mode == "always":
            self.rad_always.setChecked(True)
        elif mode == "focus_loss":
            self.rad_focus.setChecked(True)
        else:
            self.rad_bg.setChecked(True)
        self.btn_group_beh.buttonClicked.connect(self.comportamiento_cambiado)
        settings_lay.addWidget(group_behavior)

        # Visibility group
        group_widgets = QFrame()
        group_widgets.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 8px;
            }}
        """)
        widgets_lay = QVBoxLayout(group_widgets)
        widgets_lay.setContentsMargins(15, 15, 15, 15)
        widgets_lay.setSpacing(8)

        lbl_wid_title = QLabel("Módulos visibles en el panel de escritorio:")
        lbl_wid_title.setStyleSheet("font-weight: bold; font-size: 13px; color: white; border: none;")
        widgets_lay.addWidget(lbl_wid_title)

        grid_cb = QGridLayout()
        grid_cb.setSpacing(10)
        self.checkboxes = {}
        widgets_info_cfg = [(key, f"{emoji} {name}") for key, emoji, name, desc in MODULE_INFO]
        for idx, (key, label) in enumerate(widgets_info_cfg):
            cb = QCheckBox(label)
            cb.setStyleSheet("color: #CCC; border: none; font-size: 11px;")
            cb.setChecked(self.config.get("widgets", {}).get(key, True))
            cb.stateChanged.connect(self.widgets_visibles_cambiados)
            self.checkboxes[key] = cb
            grid_cb.addWidget(cb, idx // 3, idx % 3)
        widgets_lay.addLayout(grid_cb)
        settings_lay.addWidget(group_widgets)
        settings_lay.addStretch()
        self.view_stack.addWidget(settings_page)

        def toggle_settings(checked):
            self.view_stack.setCurrentIndex(1 if checked else 0)
        btn_settings.toggled.connect(toggle_settings)

    def _filtrar_tarjetas(self, text):
        query = text.strip().lower()
        for key, card in self._module_cards.items():
            if not query:
                card.setVisible(self.config.get("widgets", {}).get(key, True))
            else:
                match = query in key or query in card.objectName().lower()
                card.setVisible(match)

    def comportamiento_cambiado(self):
        if self.rad_hidden.isChecked():
            self.config["mode"] = "hidden"
        elif self.rad_always.isChecked():
            self.config["mode"] = "always"
        elif self.rad_focus.isChecked():
            self.config["mode"] = "focus_loss"
        else:
            self.config["mode"] = "background"

        self.guardar_configuracion()
        self.actualizar_floating_widget_state()

    def widgets_visibles_cambiados(self):
        self.config["widgets"] = {
            key: cb.isChecked() for key, cb in self.checkboxes.items()
        }
        self.guardar_configuracion()
        if self.floating_widget:
            self.floating_widget.apply_widgets_visibility(self.config["widgets"])
        for key, card in self._module_cards.items():
            card.setVisible(self.config["widgets"].get(key, True))

    def actualizar_floating_widget_state(self):
        app = QApplication.instance()
        if app and getattr(app, '_pin_lock_active', False):
            if self.floating_widget:
                self.floating_widget.hide()
            return

        mode = self.config.get("mode", "background")

        if mode == "hidden":
            if self.floating_widget:
                FloatingWidgetCoordinator.unregister(self.floating_widget)
                self.floating_widget.close()
                self.floating_widget = None
        else:
            if not self.floating_widget:
                self.floating_widget = FloatingWidgetWindow(self.context, self)
                self.floating_widget.apply_widgets_visibility(self.config["widgets"])
                
                screen = QApplication.primaryScreen().geometry()
                cw, ch = 44, 84
                cx = screen.width() - cw
                cy = (screen.height() - ch) // 2
                self.floating_widget.setGeometry(cx, cy, cw, ch)
                self.floating_widget.setMask(QRegion(4, 2, 80, 80, QRegion.RegionType.Ellipse))

            if mode == "always":
                user_name = getattr(self.context, 'usuario', self.config.get('usuario', 'Usuario'))
                if FloatingWidgetCoordinator.request_display(user_name, self.floating_widget, self.context.app):
                    self.floating_widget.show()

    def monitorear_segundo_plano(self):
        app = QApplication.instance()
        if app and getattr(app, '_pin_lock_active', False):
            if self.floating_widget and self.floating_widget.isVisible():
                self.floating_widget.hide()
            return

        mode = self.config.get("mode", "background")
        if mode not in ("background", "focus_loss"):
            return
            
        if not self.floating_widget:
            return

        main_win = self.context.app
        if not main_win:
            return

        if mode == "focus_loss":
            is_background = main_win.isHidden() or main_win.isMinimized() or not main_win.isActiveWindow()
        else:
            is_background = main_win.isHidden() or main_win.isMinimized()

        if is_background:
            if not self.floating_widget.isVisible():
                user_name = getattr(self.context, 'usuario', self.config.get('usuario', 'Usuario'))
                if FloatingWidgetCoordinator.request_display(user_name, self.floating_widget, main_win):
                    self.floating_widget.show()
        else:
            if self.floating_widget.isVisible():
                self.floating_widget.collapse_to_minimized()
                self.floating_widget.hide()

    def actualizar_tema(self, colores):
        self.colores = colores
        if self.floating_widget:
            self.floating_widget.colores = colores

    def cleanup(self):
        if self.floating_widget:
            FloatingWidgetCoordinator.unregister(self.floating_widget)
            self.floating_widget.close()
            self.floating_widget = None
