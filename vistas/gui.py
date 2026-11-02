import platform
import datetime
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, 
    QMenuBar, QMenu, QMessageBox, QApplication, QPushButton, QFrame,
    QStackedWidget, QScrollArea, QButtonGroup, QSizePolicy, QSystemTrayIcon, QStyle,
    QDialog, QPlainTextEdit, QWidgetAction
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIcon, QAction, QFont, QKeySequence, QShortcut

from vistas.utils.titlebar_app import CustomTitleBarApp
from vistas.utils.notification import show_notification
from vistas.scrollable import ScrollableNavBar
from vistas.dashboard_layout import DashboardSidebar, DashboardTabBar, DashboardEmptyView
from vistas.utils.updates_log_dialog import UpdatesLogDialog

class BaseAppGUI(QMainWindow):
    """Interfaz Base Premium con Barra de Título integrada y Navegación Unificada EXTERNA"""
    def __init__(self, usuario, colores=None):
        super().__init__()
        self.usuario = usuario
        self.COLORES = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "error": "#F87171", "exito": "#34D399", "advertencia": "#FBBF24"
        }
        self.nav_buttons = []
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        
        self.setWindowTitle(f"Multitool - {usuario}")
        # Se elimina FramelessWindowHint para usar la barra de título nativa del SO
        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        # Estilo Global de la Ventana
        self.setStyleSheet(f"QMainWindow {{ background-color: {self.COLORES['bg_principal']}; border: none; }}")
        
        # Asegurar icono oficial de la aplicación
        app_icon_path = Path(__file__).resolve().parent / "utils" / "icono.ico"
        if app_icon_path.exists():
            self.setWindowIcon(QIcon(str(app_icon_path)))

        # Restaurar o calcular geometría de la ventana guardada
        self._restaurar_geometria_ventana()

        # Aplicar Modo Oscuro Nativo en la barra de Windows si es posible
        self._aplicar_modo_oscuro_windows()
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 2. Barra de Navegación de Módulos (Modo Clásico)
        self.nav_bar = ScrollableNavBar(self, self.COLORES)
        self.main_layout.addWidget(self.nav_bar)

        # 3. Contenedor Central Adaptable (Soporta Modo Clásico y Modo Dashboard)
        self.center_container = QWidget()
        self.center_container.setStyleSheet("background: transparent;")
        self.center_layout = QHBoxLayout(self.center_container)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.setSpacing(0)

        # Sidebar Lateral Izquierdo (Modo Dashboard)
        self.sidebar = DashboardSidebar(self, self.COLORES)
        self.center_layout.addWidget(self.sidebar)

        # Área de trabajo central
        self.work_area = QWidget()
        self.work_area.setStyleSheet("background: transparent;")
        self.work_layout = QVBoxLayout(self.work_area)
        self.work_layout.setContentsMargins(0, 0, 0, 0)
        self.work_layout.setSpacing(0)

        # Barra superior de pestañas editor estilo VS Code / Antigravity (Modo Dashboard)
        self.editor_tab_bar = DashboardTabBar(self, self.COLORES)
        self.work_layout.addWidget(self.editor_tab_bar)

        # Pantalla de Bienvenida / Empty Dashboard (cuando se cierran todas las pestañas)
        self.dashboard_empty_view = DashboardEmptyView(self, self.COLORES, app_name="Multitool")
        self.dashboard_empty_view.hide()
        self.work_layout.addWidget(self.dashboard_empty_view, 1)

        # Notebook principal contenedor de módulos
        self.notebook = QTabWidget()
        self.notebook.tabBar().hide() 
        self.notebook.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.notebook.setStyleSheet(f"QTabWidget::pane {{ border: 0; background: {self.COLORES['bg_principal']}; }}")
        self.work_layout.addWidget(self.notebook, 1)

        self.center_layout.addWidget(self.work_area, 1)
        self.main_layout.addWidget(self.center_container, 1)
        
        # Conexiones de sincronización
        self.nav_bar.tabSelected.connect(self.notebook.setCurrentIndex)
        self.notebook.currentChanged.connect(self.on_tab_changed)

        # Conexiones del modo Dashboard
        self.sidebar.submoduleSelected.connect(self._on_dashboard_submodule_selected)
        self.editor_tab_bar.tabSelected.connect(self._on_dashboard_editor_tab_selected)
        self.editor_tab_bar.tabClosed.connect(self._on_dashboard_editor_tab_closed)

        # 4. Barra de Estado Inferior con Botón Conmutador de Vista
        self.barra_estado_frame = QFrame()
        self.barra_estado_frame.setFixedHeight(28)
        self.barra_estado_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.COLORES['bg_secundario']};
                border-top: 1px solid {self.COLORES['bg_terciario']};
            }}
        """)
        be_layout = QHBoxLayout(self.barra_estado_frame)
        be_layout.setContentsMargins(12, 0, 10, 0)
        be_layout.setSpacing(8)

        self.barra_estado = QLabel(f"Conectado: {self.usuario}")
        self.barra_estado.setStyleSheet(f"background: transparent; color: {self.COLORES['fg_secundario']}; font-size: 11px; border: none;")
        be_layout.addWidget(self.barra_estado, 1)

        self.btn_toggle_view = None

        self.main_layout.addWidget(self.barra_estado_frame)

        # Modo de vista actual: 'clasico' o 'dashboard'
        self.modo_vista = "clasico"
        self.sidebar.hide()
        self.editor_tab_bar.hide()

        # Crear QMenuBar Estándar (Nativo)
        self.crear_menu()
        
        # Temporizador para el reloj de la barra de estado
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.actualizar_reloj_status)
        self.status_timer.start(1000)
        
        # Opciones de sistema
        self._force_close = False
        self.setup_system_tray()

        # Atajos y estado de Pantalla Completa (Ocultar barras)
        self.is_fullscreen_mode = False
        self.btn_exit_fullscreen = None
        self.shortcut_f11 = QShortcut(QKeySequence("F11"), self)
        self.shortcut_f11.activated.connect(self.toggle_pantalla_completa)
        self.shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_esc.activated.connect(self._on_escape_pressed)

        # Atajo Ctrl+T para búsqueda rápida / selector de módulos
        self.shortcut_ctrl_t = QShortcut(QKeySequence("Ctrl+T"), self)
        self.shortcut_ctrl_t.activated.connect(self.abrir_buscador_general_rapido)

        # Buffer para captura de números con Ctrl (Ctrl+1, Ctrl+10...)
        self._ctrl_digit_buffer = ""
        self._ctrl_digit_timer = QTimer(self)
        self._ctrl_digit_timer.setSingleShot(True)
        self._ctrl_digit_timer.timeout.connect(self._timeout_ctrl_digits)

        # Atajos de Terminal / Consola de Comandos estilo Minecraft (F1 y F12)
        try:
            self.shortcut_f1 = QShortcut(QKeySequence("F1"), self)
            self.shortcut_f1.activated.connect(self._toggle_minecraft_console)
            self.shortcut_f12 = QShortcut(QKeySequence("F12"), self)
            self.shortcut_f12.activated.connect(self._toggle_minecraft_console)
        except Exception: pass

        # Listener para adaptabilidad de la barra de tareas (Auto-hide Windows)
        app_inst = QApplication.instance()
        if app_inst and app_inst.primaryScreen():
            app_inst.primaryScreen().availableGeometryChanged.connect(self._on_work_area_changed)

    def _toggle_console(self):
        try:
            from console import ConsoleDialog
            if not hasattr(self, "_mc_console") or not self._mc_console:
                self._mc_console = ConsoleDialog(self)
            if self._mc_console.isVisible():
                self._mc_console.hide()
            else:
                self._mc_console.show()
                self._mc_console.raise_()
                self._mc_console.activateWindow()
                if hasattr(self._mc_console, "input_edit"):
                    self._mc_console.input_edit.setFocus()
        except Exception as e:
            print(f"[BaseAppGUI] Error al alternar consola: {e}")

    _toggle_minecraft_console = _toggle_console

    def _on_escape_pressed(self):
        if getattr(self, "is_fullscreen_mode", False):
            self.toggle_pantalla_completa()

    def toggle_pantalla_completa(self):
        """Alterna el modo Pantalla Completa ocultando la barra de módulos, submódulos y barra de estado respetando el modo de vista."""
        self.is_fullscreen_mode = not getattr(self, "is_fullscreen_mode", False)
        
        # 1. Ocultar o mostrar barras según fullscreen y modo de vista
        if self.is_fullscreen_mode:
            self.nav_bar.hide()
            self.barra_estado.hide()
            if hasattr(self, "sidebar"):
                self.sidebar.hide()
            if hasattr(self, "editor_tab_bar"):
                self.editor_tab_bar.hide()
            if self.menuBar():
                self.menuBar().hide()
            self.showFullScreen()
            self._mostrar_boton_flotante_salir_fullscreen()
        else:
            # Restaurar vista exacta según el modo actual (clasico / dashboard)
            self._aplicar_modo_vista(self.modo_vista)
            self.barra_estado.show()
            self.showNormal()
            self._ocultar_boton_flotante_salir_fullscreen()
        
        # 2. Ocultar o mostrar las barras de submódulos de todos los módulos
        try:
            if hasattr(self, "notebook"):
                for i in range(self.notebook.count()):
                    mod = self.notebook.widget(i)
                    if mod:
                        if hasattr(mod, "tabs") and hasattr(mod.tabs, "tabBar") and mod.tabs.tabBar():
                            debe_mostrar = (not self.is_fullscreen_mode) and (self.modo_vista == "clasico")
                            mod.tabs.tabBar().setVisible(debe_mostrar)
                        if hasattr(mod, "toggle_fullscreen_mode"):
                            try:
                                mod.toggle_fullscreen_mode(self.is_fullscreen_mode)
                            except Exception:
                                pass
        except Exception as e:
            print(f"[BaseAppGUI] Error alternando barras en submódulos: {e}")

    def _mostrar_boton_flotante_salir_fullscreen(self):
        if not hasattr(self, "btn_exit_fullscreen") or not self.btn_exit_fullscreen:
            self.btn_exit_fullscreen = QPushButton("✕ Salir de Pantalla Completa (F11)", self)
            self.btn_exit_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_exit_fullscreen.setStyleSheet("""
                QPushButton {
                    background-color: rgba(30, 30, 46, 0.94);
                    color: #FFFFFF;
                    border: 1px solid #6366F1;
                    border-radius: 14px;
                    padding: 6px 18px;
                    font-size: 11px;
                    font-weight: bold;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QPushButton:hover {
                    background-color: #6366F1;
                    color: #FFFFFF;
                }
            """)
            self.btn_exit_fullscreen.clicked.connect(self.toggle_pantalla_completa)
        
        w_btn = 220
        h_btn = 30
        self.btn_exit_fullscreen.setGeometry((self.width() - w_btn) // 2, 8, w_btn, h_btn)
        self.btn_exit_fullscreen.show()
        self.btn_exit_fullscreen.raise_()

    def _ocultar_boton_flotante_salir_fullscreen(self):
        if hasattr(self, "btn_exit_fullscreen") and self.btn_exit_fullscreen:
            self.btn_exit_fullscreen.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "is_fullscreen_mode", False) and hasattr(self, "btn_exit_fullscreen") and self.btn_exit_fullscreen:
            w_btn = 220
            h_btn = 30
            self.btn_exit_fullscreen.setGeometry((self.width() - w_btn) // 2, 8, w_btn, h_btn)
            self.btn_exit_fullscreen.raise_()

    def _get_window_state_path(self):
        try:
            from controlador.utils.paths import get_data_path
            p = get_data_path() / "browser_data" / "window_state.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            return Path("window_state.json")

    def _restaurar_geometria_ventana(self):
        state_file = self._get_window_state_path()
        restaurado = False
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                x = data.get("x")
                y = data.get("y")
                w = data.get("width")
                h = data.get("height")
                is_max = data.get("is_maximized", False)
                
                if w and h and w >= 400 and h >= 300:
                    screen = self.screen().geometry()
                    if x is not None and y is not None:
                        x = max(screen.left(), min(x, screen.right() - 250))
                        y = max(screen.top(), min(y, screen.bottom() - 250))
                        self.move(x, y)
                    self.resize(w, h)
                    if is_max:
                        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
                    restaurado = True
            except Exception as e:
                print(f"[BaseAppGUI] Error restaurando geometría: {e}")

        if not restaurado:
            screen = self.screen().geometry()
            w, h = int(screen.width() * 0.85), int(screen.height() * 0.85)
            self.resize(w, h)
            x = (screen.width() - w) // 2
            y = (screen.height() - h) // 2
            self.move(x, y)

    def _guardar_geometria_ventana(self):
        try:
            state_file = self._get_window_state_path()
            is_max = self.isMaximized()
            data = {"is_maximized": is_max}
            if not is_max:
                data["width"] = self.width()
                data["height"] = self.height()
                data["x"] = self.x()
                data["y"] = self.y()
            else:
                normal_geom = self.normalGeometry()
                if normal_geom.isValid() and normal_geom.width() > 300 and normal_geom.height() > 200:
                    data["width"] = normal_geom.width()
                    data["height"] = normal_geom.height()
                    data["x"] = normal_geom.x()
                    data["y"] = normal_geom.y()
            
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[BaseAppGUI] Error guardando geometría: {e}")

    def on_tab_changed(self, index):
        """Manejador base para registrar cambios de módulo en la auditoría."""
        if hasattr(self, "notebook") and 0 <= index < self.notebook.count():
            mod_title = self.notebook.tabText(index)
            try:
                from vistas.utils.logs import JsonLogger
                JsonLogger.log_global("INFO", f"Modulo: {mod_title}", modulo="Navegación")
            except Exception:
                pass

    def _aplicar_paleta_oscura_global(self):
        """Configura la paleta estándar de QApplication para evitar controles nativos en blanco"""
        try:
            from PyQt6.QtGui import QPalette, QColor
            app = QApplication.instance()
            if not app:
                return
            palette = QPalette()
            bg_p = QColor(self.COLORES.get('bg_principal', '#121218'))
            bg_s = QColor(self.COLORES.get('bg_secundario', '#1E1E2E'))
            bg_t = QColor(self.COLORES.get('bg_terciario', '#2D2D3D'))
            fg_p = QColor(self.COLORES.get('fg_principal', '#E2E2E2'))
            fg_s = QColor(self.COLORES.get('fg_secundario', '#AAB0B8'))
            ac = QColor(self.COLORES.get('acento', '#6366F1'))
            
            palette.setColor(QPalette.ColorRole.Window, bg_p)
            palette.setColor(QPalette.ColorRole.WindowText, fg_p)
            palette.setColor(QPalette.ColorRole.Base, bg_s)
            palette.setColor(QPalette.ColorRole.AlternateBase, bg_t)
            palette.setColor(QPalette.ColorRole.ToolTipBase, bg_s)
            palette.setColor(QPalette.ColorRole.ToolTipText, fg_p)
            palette.setColor(QPalette.ColorRole.Text, fg_p)
            palette.setColor(QPalette.ColorRole.Button, bg_s)
            palette.setColor(QPalette.ColorRole.ButtonText, fg_p)
            palette.setColor(QPalette.ColorRole.BrightText, QColor("#F87171"))
            palette.setColor(QPalette.ColorRole.Link, ac)
            palette.setColor(QPalette.ColorRole.Highlight, ac)
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
            app.setPalette(palette)
        except Exception as e:
            print(f"[Theme Warning] No se pudo aplicar la paleta oscura: {e}")

    def aplicar_fondo_e_estilo(self, colores=None, fondo_imagen=None):
        """Aplica la paleta de colores y/o la imagen de fondo extendida con estilos dark mode globales"""
        if colores:
            self.COLORES = colores
        if not fondo_imagen and hasattr(self, 'config') and isinstance(self.config, dict):
            fondo_imagen = self.config.get("fondo_imagen", "")

        self._aplicar_paleta_oscura_global()

        bg_p = self.COLORES.get('bg_principal', '#121218')
        bg_s = self.COLORES.get('bg_secundario', '#1E1E2E')
        bg_t = self.COLORES.get('bg_terciario', '#2D2D3D')
        fg_p = self.COLORES.get('fg_principal', '#E2E2E2')
        fg_s = self.COLORES.get('fg_secundario', '#AAB0B8')
        ac = self.COLORES.get('acento', '#6366F1')
        ac_h = self.COLORES.get('acento_hover', '#818CF8')

        common_subcontrol_styles = f"""
            QMainWindow, QWidget#central_widget {{
                background-color: {bg_p};
                color: {fg_p};
            }}
            QTabWidget::pane {{
                border: 0px;
                background: {bg_p};
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QPlainTextEdit, QTextEdit, QTableView, QTableWidget, QListWidget, QTreeWidget {{
                background-color: {bg_s};
                color: {fg_p};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
            }}
            QLineEdit {{
                background-color: {bg_s};
                color: {fg_p};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {ac};
            }}
            QScrollBar:vertical {{
                background: {bg_p};
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {bg_t};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {ac};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {bg_p};
                height: 8px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {bg_t};
                border-radius: 4px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {ac};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """

        from pathlib import Path as _Path
        if fondo_imagen and _Path(fondo_imagen).exists():
            img_posix = _Path(fondo_imagen).as_posix()
            self.setStyleSheet(f"""
                QMainWindow {{
                    border: none;
                    background-image: url("{img_posix}");
                    background-position: center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                }}
                {common_subcontrol_styles}
            """)
            if hasattr(self, 'notebook'):
                self.notebook.setStyleSheet("QTabWidget::pane { border: 0; background: transparent; }")
        else:
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {bg_p};
                    border: none;
                }}
                {common_subcontrol_styles}
            """)
            if hasattr(self, 'notebook'):
                self.notebook.setStyleSheet(f"QTabWidget::pane {{ border: 0; background: {bg_p}; }}")

    def _on_work_area_changed(self, geo):
        """Reajusta la ventana sin bordes si la barra de sistema se oculta o reaparece"""
        if getattr(self, "_is_maximized_manual", False):
            self.setGeometry(geo)

    def setup_system_tray(self):
        import os
        from vistas.utils.tray_manager import TrayControlManager
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "icono.ico")
        except Exception:
            icon_path = None

        self.tray_manager = TrayControlManager(self, icon_path)
        self.tray_manager.mostrar_ocultar_signal.connect(self._toggle_visibility)
        self.tray_manager.bloquear_pin_signal.connect(self._bloquear_con_pin)
        self.tray_manager.salir_signal.connect(self.salir_aplicacion_forzado)

    def _toggle_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _bloquear_con_pin(self):
        self.bloquear_pantalla()

    def bloquear_pantalla(self):
        """Bloquea la aplicación solicitando el PIN o permitiendo configurarlo si aún no existe."""
        import json
        from pathlib import Path
        ruta_usuario = getattr(self.context, "ruta_usuario", None)
        if not ruta_usuario:
            return

        cfg_file = Path(ruta_usuario) / "config.json"
        pin = None
        if cfg_file.exists():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    pin = data.get("pin_lock")
            except Exception:
                pass

        if not pin:
            from PyQt6.QtWidgets import QMessageBox, QInputDialog, QLineEdit
            resp = QMessageBox.question(
                self, "PIN no configurado",
                "No tienes un PIN de bloqueo configurado para esta cuenta.\n\n¿Deseas configurar un PIN de 4 dígitos ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.Yes:
                nuevo_pin, ok = QInputDialog.getText(self, "Configurar PIN", "Introduce un PIN de 4 dígitos:", QLineEdit.EchoMode.Password)
                if ok and nuevo_pin.strip():
                    import hashlib
                    pin_hash = hashlib.sha256(nuevo_pin.strip().encode("utf-8")).hexdigest()
                    try:
                        data = {}
                        if cfg_file.exists():
                            with open(cfg_file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                        data["pin_lock"] = pin_hash
                        with open(cfg_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=4)
                        pin = pin_hash
                        QMessageBox.information(self, "PIN Configurado", "¡PIN configurado exitosamente!")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"No se pudo guardar el PIN: {e}")
                        return
                else:
                    return
            else:
                return

        # Mostrar ventana y presentar diálogo modal estricto de PIN
        self.showNormal()
        self.raise_()
        self.activateWindow()

        from vistas.modulos.cuenta.submodulos.gui_user import QuickPinLockDialog
        colores = getattr(self, "COLORES", {})
        dlg = QuickPinLockDialog(pin, colores, self)
        dlg.exec()

    def tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            # Restaurar la ventana con su barra nativa
            self.showNormal()
            self.raise_()
            self.activateWindow()
            # Re-aplicar modo oscuro por si el cambio de estado lo reseteó
            self._aplicar_modo_oscuro_windows()
            self.activateWindow()

    def _aplicar_modo_oscuro_windows(self):
        """Usa el API de Windows (DWM) para forzar la barra de título a modo oscuro"""
        if platform.system() == "Windows":
            import ctypes
            try:
                # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11) o 19 (Windows 10 previo)
                hwnd = self.winId().__int__()
                value = ctypes.c_int(1)
                # Intentar con el atributo 20 (Win 11 / Win 10 20H1+)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
                # Intentar con el atributo 19 (Win 10 versiones anteriores)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
            except Exception: pass

    def set_status(self, text):
        self.barra_estado.setText(text)

    def mostrar_notificacion(self, titulo, mensaje, tipo="info"):
        from vistas.utils.notification import show_notification
        show_notification(self, titulo, mensaje, tipo, self.COLORES)

    # --- Mocks para compatibilidad ---
    def after(self, ms, func, *args): QTimer.singleShot(ms, lambda: func(*args))
    def update(self): QApplication.processEvents()
    def update_idletasks(self): QApplication.processEvents()

    def crear_menu(self):
        """Inicializa los menús en la QMenuBar nativa organizados en TOOLBAR y MODULES."""
        menubar = self.menuBar()
        menubar.setStyleSheet(f"""
            QMenuBar {{ background: {self.COLORES['bg_secundario']}; color: white; padding: 2px; }}
            QMenuBar::item {{ background: transparent; padding: 5px 12px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
            QMenuBar::item:selected {{ background: {self.COLORES['bg_terciario']}; color: {self.COLORES['acento']}; }}
            QMenu {{ background: {self.COLORES['bg_secundario']}; color: white; border: 1px solid {self.COLORES['bg_terciario']}; }}
            QMenu::item:selected {{ background: {self.COLORES['acento']}; color: #0A0A0F; font-weight: bold; }}
        """)

        # 1. Menú TOOLBAR (Herramientas del sistema: Archivo, Actualizaciones, Aclaraciones, Consola Dev, Reset Backup)
        self.menu_toolbar = menubar.addMenu("🛠️ TOOLBAR")

        # Submenú ARCHIVO dentro de Toolbar
        m_arc = self.menu_toolbar.addMenu("📁 ARCHIVO")
        self.menu_viewapp = m_arc.addMenu("Viewapp")
        self.act_view_mms = QAction("MMS (MultiModulesStatics - Modo Clásico)", self)
        self.act_view_mms.setCheckable(True)
        self.act_view_mms.setChecked(self.modo_vista == "clasico")
        self.act_view_mms.triggered.connect(lambda: self._set_modo_vista("clasico"))
        self.menu_viewapp.addAction(self.act_view_mms)

        self.act_view_ide = QAction("IDE (Modo Dashboard / Sidebar)", self)
        self.act_view_ide.setCheckable(True)
        self.act_view_ide.setChecked(self.modo_vista == "dashboard")
        self.act_view_ide.triggered.connect(lambda: self._set_modo_vista("dashboard"))
        self.menu_viewapp.addAction(self.act_view_ide)

        m_arc.addSeparator()
        m_arc.addAction("Instalar Actualización (.mtu)...", self.instalar_actualizacion_mtu)
        m_arc.addSeparator()
        import sys
        if not getattr(sys, "frozen", False):
            m_arc.addAction("Compilador de Actualizaciones...", self.abrir_compilador_actualizaciones)
            m_arc.addSeparator()
        m_arc.addAction("Salir", self.salir_aplicacion)

        # Opciones de Toolbar
        act_log = self.menu_toolbar.addAction("📋 ACTUALIZACIONES", self.mostrar_log_actualizaciones)
        act_aclara = self.menu_toolbar.addAction("⚠️ ACLARACIONES", self.mostrar_aclaraciones_sistema)

        # Consola Dev dentro de Toolbar
        self.act_dev_console = QAction("⚡ CONSOLA", self)
        self.act_dev_console.setToolTip("Abrir Terminal de Comandos y Automatización (Modo Programador)")
        self.act_dev_console.triggered.connect(self._toggle_console)
        self.act_dev_console.setVisible(getattr(self, "_dev_mode_activo", False))
        self.menu_toolbar.addAction(self.act_dev_console)

        self.menu_toolbar.addSeparator()
        act_reset_zip = self.menu_toolbar.addAction("🔄 Reiniciar Configuración (Backup .ZIP)...", self.reiniciar_configuracion_modulos_zip)
        self.menu_toolbar.addSeparator()
        self.menu_toolbar.addAction("❓ Acerca de", self.mostrar_acerca_de)

        # 2. Menú MODULES (Módulos y su gestión)
        self.menu_modules = menubar.addMenu("📦 MODULES")
        self.action_gestionar = QAction("⚙️ Gestionar Módulos...", self)
        self.action_gestionar.triggered.connect(self.abrir_gestor_modulos)
        self.menu_modules.addAction(self.action_gestionar)
        self.menu_modules.addSeparator()

        # 3. Menú VER (Se activa en modo MMS y se oculta en modo IDE)
        self.menu_ver = menubar.addMenu("👁️ VER")
        self.menu_ver.addAction(self.action_gestionar)
        self.menu_ver.addSeparator()
        self.menu_ver.menuAction().setVisible(self.modo_vista == "clasico")

        # Acciones directas visibles en la barra superior para acceso rápido
        self.act_bar_console = QAction("⚡ CONSOLA", self)
        self.act_bar_console.triggered.connect(self._toggle_console)
        self.act_bar_console.setVisible(getattr(self, "_dev_mode_activo", False))
        menubar.addAction(self.act_bar_console)
    def reiniciar_configuracion_modulos_zip(self):
        """Reinicia la configuración de módulos a fábrica generando un backup comprimido en .zip."""
        resp = QMessageBox.question(
            self,
            "Confirmar Reinicio de Configuración",
            "¿Está seguro de restablecer la configuración de los módulos a sus valores de fábrica?\n\n"
            "Se creará automáticamente una copia de respaldo comprimida (.zip) en la carpeta 'backups' "
            "de su cuenta con todas sus configuraciones e iconos personalizados actuales.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        from vistas.configurations import backup_and_reset_modulesconf
        from controlador.utils.paths import get_resource_path
        mod_dir = get_resource_path() / "vistas" / "modulos"

        ok, zip_path = backup_and_reset_modulesconf(self.ruta_usuario, mod_dir)
        if ok:
            QMessageBox.information(
                self,
                "Reinicio Exitoso",
                f"✅ Configuración restaurada con éxito a valores de fábrica.\n\n"
                f"📦 Copia de respaldo guardada en:\n{zip_path}\n\n"
                "Se recargarán las listas y vistas inmediatamente."
            )
            # Refrescar módulos en caliente
            from vistas.configurations import discover_modules_and_plugins
            self.modulos_cargados = discover_modules_and_plugins(self.ruta_usuario)
            if hasattr(self, "actualizar_menu_ver"):
                self.actualizar_menu_ver(self.modulos_cargados)
            if hasattr(self, "sidebar"):
                self.sidebar.set_modulos(self.modulos_cargados)
        else:
            QMessageBox.critical(self, "Error al Reiniciar", f"Ocurrió un error durante el reinicio: {zip_path}")


    def activar_modo_dev(self, activar=True):
        """Activa o desactiva el modo desarrollador y muestra/oculta el botón en la barra superior."""
        self._dev_mode_activo = bool(activar)
        if hasattr(self, "act_dev_console") and self.act_dev_console:
            self.act_dev_console.setVisible(self._dev_mode_activo)
        if hasattr(self, "act_bar_console") and self.act_bar_console:
            self.act_bar_console.setVisible(self._dev_mode_activo)
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.renderizar_arbol()
        return self._dev_mode_activo

    def crear_btn_aclaraciones(self):
        """Genera el botón de aviso con estilo destacado"""
        btn_style = f"""
            QPushButton {{ background: transparent; color: {self.COLORES['advertencia']}; border-radius: 4px; padding: 6px 13px; font-weight: bold; font-size: 11px; }}
            QPushButton:hover {{ background: {self.COLORES['bg_terciario']}; color: {self.COLORES['acento']}; }}
        """
        btn = QPushButton("⚠️ ACLARACIONES")
        btn.setStyleSheet(btn_style)
        btn.clicked.connect(self.mostrar_aclaraciones_sistema)
        return btn

    def mostrar_aclaraciones_sistema(self):
        """Muestra un aviso sobre el rendimiento debido a la arquitectura modular"""
        QMessageBox.information(
            self, "Aclaraciones de Sistema", 
            "⚠️ AVISO DE RENDIMIENTO\n\n"
            "Multitool es una suite integral con múltiples motores funcionando en paralelo. "
            "Debido a esta potencia modular, algunas acciones (especialmente la inicialización del navegador "
            "o el procesamiento de archivos grandes) pueden tardar unos segundos en ejecutarse.\n\n"
            "Si nota una breve demora, es parte del proceso de carga segura de los submódulos. "
            "Se recomienda paciencia al realizar tareas complejas."
        )

    def actualizar_menu_ver(self, modulos_cargados):
        """Actualiza los botones de navegación en la nav_bar (MMS) sincronizadamente con círculo de estado (🟢/🔴)."""
        print("[*] Sincronizando menú navegabilidad...")
        # 1. Limpiar menú 'Ver'
        for action in self.menu_ver.actions():
            if action != self.action_gestionar and not action.isSeparator():
                self.menu_ver.removeAction(action)
        
        # 2. Limpiar nav_bar
        self.nav_bar.clear()

        # 3. Solo agregar módulos que están REALMENTE en el notebook (visibles)
        tabs_reales = [mod for mod in modulos_cargados if mod.get("visible", True)]

        # Contenedor desplazable con barra vertical para el menú VER
        scroll_container = QWidget()
        scroll_container.setStyleSheet("background: transparent; border: none;")
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(4, 4, 4, 4)
        scroll_layout.setSpacing(2)

        for i, mod in enumerate(tabs_reales):
            name = mod['name'].capitalize()
            is_loaded = mod.get("loaded", False)
            status_circle = "🟢" if is_loaded else "🔴"
            btn_display_text = f"{name}  {status_circle}"

            # Botón estilizado dentro del menú scrollable
            btn_mod = QPushButton(f"  {btn_display_text}")
            btn_mod.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_mod.setFont(QFont(getattr(self, "font_family", "Segoe UI"), 9))
            btn_mod.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {self.COLORES.get('fg_secundario', '#E2E8F0')};
                    border: none;
                    text-align: left;
                    padding: 7px 14px;
                    border-radius: 5px;
                }}
                QPushButton:hover {{
                    background-color: {self.COLORES.get('acento', '#6366F1')};
                    color: #FFFFFF;
                    font-weight: bold;
                }}
            """)
            btn_mod.clicked.connect(lambda ch, idx=i: (self.notebook.setCurrentIndex(idx), self.menu_ver.close()))
            scroll_layout.addWidget(btn_mod)

            # Botón en nav_bar con nombre y círculo de estado
            self.nav_bar.add_tab(btn_display_text, i, checked=(self.notebook.currentIndex() == i))

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        altura_calculada = min(420, max(120, len(tabs_reales) * 34 + 12))
        scroll_area.setFixedSize(230, altura_calculada)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {self.COLORES.get('bg_secundario', '#1E1E2E')};
                border: none;
            }}
            QScrollBar:vertical {{
                background: rgba(0, 0, 0, 0.2);
                width: 7px;
                border-radius: 3px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.COLORES.get('acento', '#6366F1')};
                min-height: 25px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        scroll_area.setWidget(scroll_container)

        action_scroll = QWidgetAction(self.menu_ver)
        action_scroll.setDefaultWidget(scroll_area)
        self.menu_ver.addAction(action_scroll)
        
        print(f"[*] Menú de navegación sincronizado con {len(tabs_reales)} módulos.")

    def actualizar_reloj_status(self):
        ahora = datetime.datetime.now().strftime("%H:%M:%S")
        fecha = datetime.datetime.now().strftime("%d/%m/%Y")
        
        # Obtener nombre de pestaña de forma segura
        idx = self.notebook.currentIndex()
        pestaña = self.notebook.tabText(idx) if idx >= 0 else "---"
        if not pestaña: pestaña = "---"
        
        sistema = platform.system()
        self.barra_estado.setText(f"Usuario: {self.usuario} | ({ahora}) {fecha} | Módulo: {pestaña} | {sistema} {platform.release()}")

    def on_tab_changed(self, index):
        if index < 0: return

        # Sincronizar botones de la nav_bar
        self.nav_bar.select_tab(index)
        self.actualizar_reloj_status()

        modulo_nombre = self.notebook.tabText(index)

        # Registrar tiempo de actividad en module_log.json
        try:
            import time
            now = time.time()
            if hasattr(self, '_last_mod_name') and hasattr(self, '_last_mod_time'):
                elapsed = max(1, int(now - self._last_mod_time))
                ruta_usr = getattr(self, 'ruta_usuario', None)
                if not ruta_usr and hasattr(self, 'context') and hasattr(self.context, 'ruta_usuario'):
                    ruta_usr = self.context.ruta_usuario

                if ruta_usr:
                    mod_log_path = Path(ruta_usr) / "module_log.json"
                    m_data = {}
                    if mod_log_path.exists():
                        try:
                            with open(mod_log_path, "r", encoding="utf-8") as f:
                                m_data = json.load(f)
                        except Exception:
                            m_data = {}

                    prev_name = self._last_mod_name
                    if prev_name not in m_data:
                        m_data[prev_name] = {"visitas": 0, "tiempo_segundos": 0}

                    m_data[prev_name]["tiempo_segundos"] += elapsed

                    if modulo_nombre not in m_data:
                        m_data[modulo_nombre] = {"visitas": 0, "tiempo_segundos": 0}
                    m_data[modulo_nombre]["visitas"] += 1

                    with open(mod_log_path, "w", encoding="utf-8") as f:
                        json.dump(m_data, f, indent=4)

            self._last_mod_name = modulo_nombre
            self._last_mod_time = now
        except Exception:
            pass

        # Registrar acción en el log del usuario
        if hasattr(self, 'logger'):
            widget_actual = self.notebook.widget(index)
            sub_tab = self.buscar_sub_tabs(widget_actual)
            if sub_tab:
                sub_nombre = sub_tab.tabText(sub_tab.currentIndex())
                self.logger.log("INFO", f"Módulo: {modulo_nombre} > Pestaña: {sub_nombre}", modulo="Navegación")
            else:
                self.logger.log("INFO", f"Módulo: {modulo_nombre}", modulo="Navegación")

    def buscar_sub_tabs(self, widget):
        """Busca recursivamente el primer QTabWidget dentro de un widget"""
        if isinstance(widget, QTabWidget):
            return widget
        for child in widget.findChildren(QTabWidget):
            return child # Retornamos el primero que encontremos
        return None

    def scroll_nav(self, delta):
        self.nav_bar.scroll(delta)

    def re_sync_nav_buttons(self, index):
        # Deprecated: use self.nav_buttons in on_tab_changed
        pass

    def abrir_gestor_modulos(self):
        """Punto de entrada para el gestor de módulos. Debe ser sobrescrito por el cargador."""
        QMessageBox.information(
            self, "Personalización", 
            "El Gestor de Módulos permite organizar tu espacio de trabajo.\n\n"
            "Busca esta opción en el cargador de la aplicación."
        )

    def salir_aplicacion(self):
        resp = QMessageBox.question(self, "Salir", "¿Deseas cerrar la aplicación completamente?\n\nYes: Cerrar Completamente\nNo: Minimizar al Tray\nCancel: Cancelar", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        if resp == QMessageBox.StandardButton.Yes:
            self.salir_aplicacion_forzado()
        elif resp == QMessageBox.StandardButton.No:
            self.hide()
            self.mostrar_notificacion("Minimizando", "La aplicación seguirá ejecutándose en segundo plano.", "info")

    def _guardar_todo_el_estado(self):
        self._guardar_geometria_ventana()
        try:
            if hasattr(self, "notebook"):
                for i in range(self.notebook.count()):
                    w = self.notebook.widget(i)
                    if hasattr(w, "sub_integrado") and hasattr(w.sub_integrado, "guardar_estado_pestanas"):
                        w.sub_integrado.guardar_estado_pestanas()
        except Exception:
            pass

    def salir_aplicacion_forzado(self):
        self._guardar_todo_el_estado()
        self._force_close = True
        QApplication.quit()

    def closeEvent(self, event):
        if not self._force_close:
            event.ignore()
            self.hide()
            self.mostrar_notificacion("Minimizando", "La aplicación seguirá ejecutándose en segundo plano.", "info")
        else:
            self._guardar_todo_el_estado()
            event.accept()

    def cerrar_sesion(self):
        if QMessageBox.question(self, "Cerrar Sesión", "¿Estás seguro de que deseas cerrar la sesión actual?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self._guardar_todo_el_estado()
            self._force_close = True
            app = QApplication.instance()
            if app:
                app.setQuitOnLastWindowClosed(False)
            self.close()
            from PyQt6.QtCore import QTimer
            def _relaunch():
                from vistas.launcher import Launcher
                self._launcher = Launcher()
                self._launcher.start()
            QTimer.singleShot(100, _relaunch)

    def mostrar_acerca_de(self):
        try:
            import os
            path = os.path.join(os.path.dirname(__file__), "acerca_de.txt")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    contenido = f.read()
                QMessageBox.about(self, "Multitool - Información", contenido)
            else:
                QMessageBox.about(self, "Multitool", "Multitool PyQt6 Edition\nPremium Design.")
        except:
            QMessageBox.about(self, "Multitool", "Información no disponible.")

    def abrir_compilador_actualizaciones(self):
        try:
            from compilar_actualizacion import CompilerGUIDialog
            dialog = CompilerGUIDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el compilador de actualizaciones:\n{e}")

    def instalar_actualizacion_mtu(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox, QApplication
        import zipfile
        import os
        import sys
        import subprocess
        from pathlib import Path
        from controlador.utils.paths import get_resource_path

        archivo_zip, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Actualización (.mtu)", "", "Archivos de Actualización Multitool (*.mtu)"
        )
        if not archivo_zip:
            return

        base_dir = get_resource_path()
        mtu_path = Path(archivo_zip).resolve()

        # Validaciones previas de seguridad y contenido
        try:
            with zipfile.ZipFile(mtu_path, 'r') as zip_ref:
                lista_archivos = zip_ref.namelist()
                es_valido = (
                    "manifest.json" in lista_archivos or
                    any(name.startswith("vistas/modulos/") for name in lista_archivos) or
                    any(name.startswith("plugins/") for name in lista_archivos) or
                    any(name.endswith("Multitool.exe") or name.endswith("main.py") or name.endswith("Multitool") for name in lista_archivos)
                )
                if not es_valido:
                    QMessageBox.warning(
                        self, "Actualización Inválida",
                        "El archivo seleccionado no parece ser una actualización válida (.mtu) para Multitool."
                    )
                    return
        except Exception as e:
            QMessageBox.critical(self, "Error de Archivo", f"No se pudo leer el archivo .mtu:\n{e}")
            return

        # Buscar el ejecutable o script del Updater externo
        updater_exe = base_dir / "Updater.exe"
        updater_py = base_dir / "updater.py"
        
        current_pid = os.getpid()

        if updater_exe.exists():
            cmd = [str(updater_exe), "--mtu", str(mtu_path), "--app-dir", str(base_dir), "--pid", str(current_pid)]
        elif updater_py.exists():
            cmd = [sys.executable, str(updater_py), "--mtu", str(mtu_path), "--app-dir", str(base_dir), "--pid", str(current_pid)]
        else:
            QMessageBox.critical(
                self, "Actualizador no encontrado",
                "No se encontró el ejecutable 'Updater.exe' ni 'updater.py' en el directorio de la aplicación."
            )
            return

        # Confirmar con el usuario antes de reiniciar
        resp = QMessageBox.question(
            self, "Confirmar Actualización",
            "La actualización se instalará mediante el actualizador externo.\n\n"
            "Multitool se cerrará ahora para proceder con la instalación y se reiniciará automáticamente al terminar.\n\n"
            "¿Desea continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            # Ejecutar actualizador externo desacoplado del proceso principal
            if sys.platform == "win32":
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen(cmd)
                
            self._force_close = True
            QApplication.quit()
        except Exception as e:
            QMessageBox.critical(self, "Error al lanzar actualizador", f"No se pudo iniciar el proceso de actualización:\n{e}")

    def mostrar_log_actualizaciones(self):
        dialog = UpdatesLogDialog(self)
        dialog.exec()




    def _set_modo_vista(self, modo="clasico"):
        """Establece directamente el modo de vista (clasico o dashboard) y lo persiste."""
        self._aplicar_modo_vista(modo)
        if hasattr(self, "config") and isinstance(self.config, dict):
            self.config["modo_vista"] = modo
            if hasattr(self, "guardar_configuracion") and callable(self.guardar_configuracion):
                self.guardar_configuracion()
            elif hasattr(self, "context") and hasattr(self.context, "ruta_usuario"):
                try:
                    cfg_p = Path(self.context.ruta_usuario) / "config.json"
                    with open(cfg_p, "w", encoding="utf-8") as f:
                        json.dump(self.config, f, indent=4)
                except Exception:
                    pass

    def toggle_modo_vista(self):
        """Conmuta entre MMS (Clásico) e IDE (Dashboard)."""
        nuevo_modo = "dashboard" if getattr(self, "modo_vista", "clasico") == "clasico" else "clasico"
        self._set_modo_vista(nuevo_modo)

    def _aplicar_modo_vista(self, modo="clasico"):
        """Aplica la disposición visual según el modo: 'clasico' (MMS) o 'dashboard' (IDE)."""
        self.modo_vista = modo
        
        # Sincronizar checks del menú Viewapp
        if hasattr(self, "act_view_mms") and self.act_view_mms:
            self.act_view_mms.setChecked(modo == "clasico")
        if hasattr(self, "act_view_ide") and self.act_view_ide:
            self.act_view_ide.setChecked(modo == "dashboard")

        # Inyectar modulos_dir en el sidebar si no lo tenía
        if hasattr(self, "sidebar") and not self.sidebar.modulos_dir:
            from controlador.utils.paths import get_resource_path
            self.sidebar.modulos_dir = get_resource_path() / "vistas" / "modulos"
            self.sidebar.ruta_usuario = getattr(self, "ruta_usuario", None)

        # Ocultar o mostrar el menú VER según el modo
        if hasattr(self, "menu_ver") and self.menu_ver:
            self.menu_ver.menuAction().setVisible(modo == "clasico")

        if modo == "dashboard":
            # Ocultar barra superior en modo IDE para maximizar el espacio de trabajo (el Toolbar se integra en el Sidebar)
            if self.menuBar():
                self.menuBar().hide()
            self.nav_bar.hide()
            self.sidebar.show()
            self.editor_tab_bar.show()

            # Ocultar pestañas internas de submódulos para dar apariencia limpia estilo VS Code
            self._sincronizar_visibilidad_subtabs_dashboard(ocultar=True)
            self._sincronizar_dashboard_sidebar()
            
            # Sincronizar visibilidad del empty placeholder o notebook
            if len(self.editor_tab_bar.tabs) == 0:
                self.notebook.hide()
                if hasattr(self, "dashboard_empty_view"):
                    self.dashboard_empty_view.show()
            else:
                self.notebook.show()
                if hasattr(self, "dashboard_empty_view"):
                    self.dashboard_empty_view.hide()
        else:
            # Restaurar barra de menú superior en modo MMS (Clásico)
            if self.menuBar():
                self.menuBar().show()
            self.sidebar.hide()
            self.editor_tab_bar.hide()
            if hasattr(self, "dashboard_empty_view"):
                self.dashboard_empty_view.hide()
            self.notebook.show()
            self.nav_bar.show()

            # Restaurar visibilidad de pestañas internas de submódulos
            self._sincronizar_visibilidad_subtabs_dashboard(ocultar=False)

    def _sincronizar_visibilidad_subtabs_dashboard(self, ocultar=True):
        """Oculta o muestra la barra de pestañas interna de los submódulos de manera confiable según el modo de vista."""
        try:
            # 1. Recorrer instancias conocidas en clases_modulos
            for k, cont in getattr(self, "clases_modulos", {}).items():
                if cont:
                    if hasattr(cont, "tabs") and hasattr(cont.tabs, "tabBar") and cont.tabs.tabBar():
                        cont.tabs.tabBar().setVisible(not ocultar)

            # 2. Recorrer todos los widgets del notebook y buscar recursivamente QTabWidgets secundarios
            if hasattr(self, "notebook"):
                for i in range(self.notebook.count()):
                    w = self.notebook.widget(i)
                    if w:
                        for tw in w.findChildren(QTabWidget):
                            if tw != self.notebook and tw.tabBar():
                                tw.tabBar().setVisible(not ocultar)
        except Exception as e:
            print(f"[BaseAppGUI] Error sincronizando visibilidad de subtabs: {e}")

    def _sincronizar_dashboard_sidebar(self):
        """Actualiza el árbol del sidebar con los módulos cargados."""
        if hasattr(self, "sidebar") and hasattr(self, "modulos_cargados"):
            if not self.sidebar.modulos_dir:
                from controlador.utils.paths import get_resource_path
                self.sidebar.modulos_dir = get_resource_path() / "vistas" / "modulos"
            self.sidebar.ruta_usuario = getattr(self, "ruta_usuario", None)
            curr_mod = ""
            curr_sub = ""
            if 0 <= self.editor_tab_bar.current_index < len(self.editor_tab_bar.tabs):
                t = self.editor_tab_bar.tabs[self.editor_tab_bar.current_index]
                curr_mod = t["mod_name"]
                curr_sub = t["sub_name"]
            self.sidebar.set_modulos(self.modulos_cargados, curr_mod, curr_sub)

    def _on_dashboard_submodule_selected(self, mod_name, sub_name, mod_idx, sub_idx):
        """Manejador cuando el usuario hace doble clic en un módulo/submódulo del sidebar."""
        visibles = [m for m in getattr(self, "modulos_cargados", []) if m.get("visible", True)]
        if 0 <= mod_idx < len(visibles):
            mod = visibles[mod_idx]
            if not mod.get("loaded", False):
                self._instanciar_modulo(mod)

        # Cambiar el notebook al módulo
        for idx_m, m in enumerate(visibles):
            if m.get("name", "").lower() == mod_name.lower():
                self.notebook.setCurrentIndex(idx_m)
                break

        # Sincronizar el submódulo interno
        container = getattr(self, "clases_modulos", {}).get(mod_name)
        if container and hasattr(container, "tabs") and isinstance(container.tabs, QWidget):
            if hasattr(container.tabs, "tabBar") and container.tabs.tabBar():
                container.tabs.tabBar().hide()
            if 0 <= sub_idx < container.tabs.count():
                container.tabs.setCurrentIndex(sub_idx)

        # Mostrar el notebook y ocultar la pantalla de bienvenida
        self.notebook.show()
        if hasattr(self, "dashboard_empty_view"):
            self.dashboard_empty_view.hide()

        # Agregar o activar en la barra de pestañas editor
        clean_sub = sub_name.strip()
        display_title = f"{mod_name.capitalize()} › {clean_sub}" if clean_sub else mod_name.capitalize()
        self.editor_tab_bar.add_tab(mod_name, clean_sub, display_title, make_active=True)
        if hasattr(self, "logger"):
            self.logger.log("INFO", f"Módulo: {mod_name.capitalize()} > Pestaña: {clean_sub}", modulo="Navegación")

    def _on_dashboard_editor_tab_selected(self, idx):
        """Manejador cuando el usuario cambia de pestaña en la barra superior estilo editor."""
        if idx < 0 or idx >= len(self.editor_tab_bar.tabs):
            self.notebook.hide()
            if hasattr(self, "dashboard_empty_view"):
                self.dashboard_empty_view.show()
            return

        self.notebook.show()
        if hasattr(self, "dashboard_empty_view"):
            self.dashboard_empty_view.hide()

        tab_info = self.editor_tab_bar.tabs[idx]
        mod_name = tab_info["mod_name"]
        sub_name = tab_info["sub_name"]

        visibles = [m for m in getattr(self, "modulos_cargados", []) if m.get("visible", True)]
        for i, m in enumerate(visibles):
            if m.get("name", "").lower() == mod_name.lower():
                if not m.get("loaded", False):
                    self._instanciar_modulo(m)
                self.notebook.setCurrentIndex(i)
                break

        container = getattr(self, "clases_modulos", {}).get(mod_name)
        if container and hasattr(container, "tabs") and isinstance(container.tabs, QWidget):
            if hasattr(container.tabs, "tabBar") and container.tabs.tabBar():
                container.tabs.tabBar().hide()
            if sub_name:
                for s_i in range(container.tabs.count()):
                    txt = container.tabs.tabText(s_i).lower()
                    if sub_name.lower() in txt or txt in sub_name.lower():
                        container.tabs.setCurrentIndex(s_i)
                        break

        # Sincronizar selección en sidebar
        self.sidebar._active_mod_name = mod_name
        self.sidebar._active_sub_name = sub_name
        self.sidebar.renderizar_arbol()

    def _on_dashboard_editor_tab_closed(self, idx):
        """Manejador cuando el usuario cierra una pestaña con '✕'."""
        if len(self.editor_tab_bar.tabs) == 0:
            self.notebook.hide()
            if hasattr(self, "dashboard_empty_view"):
                self.dashboard_empty_view.show()
            self.sidebar._active_mod_name = ""
            self.sidebar._active_sub_name = ""
            self.sidebar.renderizar_arbol()

    def abrir_buscador_general_rapido(self):
        """Abre la búsqueda rápida / selector de módulos (Ctrl+T)."""
        if hasattr(self, "abrir_gestor_modulos"):
            self.abrir_gestor_modulos()

    def keyPressEvent(self, event):
        """Gestiona combinaciones de teclas globales como Ctrl + Números (1 a 99) con Enter."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            k = event.key()
            if Qt.Key.Key_0 <= k <= Qt.Key.Key_9:
                digit = str(k - Qt.Key.Key_0)
                self._ctrl_digit_buffer += digit
                if hasattr(self, "_ctrl_digit_timer"):
                    self._ctrl_digit_timer.start(1500)
                if hasattr(self, "barra_estado"):
                    self.set_status(f"Seleccionando Módulo #{self._ctrl_digit_buffer} (Presiona Enter para ir)...")
                event.accept()
                return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if getattr(self, "_ctrl_digit_buffer", ""):
                self._activar_modulo_por_numero(self._ctrl_digit_buffer)
                self._ctrl_digit_buffer = ""
                event.accept()
                return

        super().keyPressEvent(event)

    def _timeout_ctrl_digits(self):
        """Si el usuario no presiona Enter tras 1.5s, navega al número acumulado automáticamente."""
        if getattr(self, "_ctrl_digit_buffer", ""):
            self._activar_modulo_por_numero(self._ctrl_digit_buffer)
            self._ctrl_digit_buffer = ""

    def _activar_modulo_por_numero(self, num_str):
        try:
            val = int(num_str)
            target_idx = val - 1 # 1-based a 0-based
            visibles = [m for m in getattr(self, "modulos_cargados", []) if m.get("visible", True)]
            if 0 <= target_idx < len(visibles):
                mod = visibles[target_idx]
                if self.modo_vista == "dashboard":
                    self._on_dashboard_submodule_selected(mod["name"], "", target_idx, 0)
                else:
                    self.notebook.setCurrentIndex(target_idx)
                self.set_status(f"Módulo activo: {mod['name'].capitalize()} (#{val})")
            else:
                self.set_status(f"Número de módulo inválido: #{val} (Rango: 1-{len(visibles)})")
        except Exception as e:
            print(f"[BaseAppGUI] Error activando módulo por número: {e}")
