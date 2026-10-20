import sys
import json
import datetime
import logging
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QTabWidget, QApplication
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QScreen

# Importaciones internas
from .utils.titlebar_app import CustomTitleBarApp
from controlador.auth.gui_auth import AuthGUI
from vistas.cargar import AppMultitareasGUI
from vistas.pantalla_carga import PantallaCarga
from vistas.utils.welcome import WelcomeScreen
from controlador.utils.paths import get_data_path

# Definición de colores premium
COLORES = {
    "bg_principal": "#121218",
    "bg_secundario": "#1E1E2E",
    "bg_terciario": "#2D2D3D",
    "fg_principal": "#E2E2E2",
    "fg_secundario": "#AAB0B8",
    "acento": "#6366F1",
    "acento_hover": "#818CF8"
}

class AppMultitoolGUI(QMainWindow):
    def __init__(self, auto_login=False):
        super().__init__()
        self.setWindowTitle("Multitool - Acceso")
        
        # Se elimina la ventana sin bordes para usar la nativa del sistema
        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        
        # Tamaño responsivo inicial
        self.setFixedSize(450, 650)
        self.center_window()
        
        self.setStyleSheet(f"background-color: {COLORES['bg_principal']}; color: {COLORES['fg_principal']};")
        self.intentos_login = {}
        
        if not auto_login:
            self.setup_ui()

    def center_window(self):
        """Centra la ventana de forma robusta en el monitor actual"""
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2 + screen.left()
        y = (screen.height() - size.height()) // 2 + screen.top()
        self.move(x, y)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Se elimina la barra de título personalizada
        # self.title_bar = CustomTitleBarApp(self, title="MULTITOOL - Acceso")
        # main_layout.addWidget(self.title_bar)
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(25, 30, 25, 30)
        content_layout.setSpacing(10)
        
        # Fuente adaptable según el sistema
        font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": font_family = ".AppleSystemUIFont"

        title_label = QLabel("MULTITOOL")
        title_label.setFont(QFont(font_family, 28, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {COLORES['acento']};")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Tu suite de herramientas personal")
        subtitle_label.setFont(QFont(font_family, 10))
        subtitle_label.setStyleSheet(f"color: {COLORES['fg_secundario']}; margin-bottom: 20px;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(subtitle_label)
        
        self.auth_tabs = QTabWidget()
        self.auth_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 0px; }}
            QTabBar::tab {{ 
                background: {COLORES['bg_secundario']}; 
                color: {COLORES['fg_secundario']}; 
                padding: 12px 20px; 
                font-weight: bold; 
                border-top-left-radius: 8px; 
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{ 
                background: {COLORES['bg_terciario']}; 
                color: {COLORES['acento']}; 
                border-bottom: 2px solid {COLORES['acento']};
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(99, 102, 241, 0.1);
            }}
        """)
        
        self.login_tab = QWidget()
        self.register_tab = QWidget()
        
        self.auth_tabs.addTab(self.login_tab, " INICIAR SESIÓN ")
        self.auth_tabs.addTab(self.register_tab, " REGISTRARSE ")
        
        # Inicializar UI de Auth
        AuthGUI.init_login_tab(self)
        AuthGUI.init_register_tab(self)
        
        content_layout.addWidget(self.auth_tabs)
        main_layout.addLayout(content_layout)
        
        self._aplicar_modo_oscuro_windows()

    def _aplicar_modo_oscuro_windows(self):
        """Usa el API de Windows (DWM) para forzar la barra de título a modo oscuro"""
        if platform.system() == "Windows":
            import ctypes
            try:
                hwnd = self.winId().__int__()
                value = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
            except Exception: pass

    def show_tab(self, tab):
        from controlador.auth.show_tabs_auth import show_tab
        show_tab(self, tab)

    def cargar_aplicacion(self, usuario, persona, avatar_path):
        """Flujo de acceso: Bienvenida -> Pantalla de Carga (async) -> Aplicación Principal"""
        self.hide()

        def iniciar_carga():
            try:
                base_path = get_data_path()
                ruta_usuario = Path(base_path) / "cuentas" / persona
                config_path = ruta_usuario / "config.json"
                if config_path.exists():
                    from controlador.auth.crypto_utils import process_config_for_load, process_config_for_save
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = process_config_for_load(json.load(f))
                    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    historial = config.get("historial", [])
                    historial.append(f"[{ahora}] Inicio de sesión.")
                    config["historial"] = historial
                    config["ultimo_acceso"] = ahora
                    config_guardar = process_config_for_save(config)
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(config_guardar, f, indent=4)
            except Exception as e:
                logging.error(f"[!] No se pudo actualizar historial: {e}")

            # Pantalla de carga
            self.loading = PantallaCarga(auto_play=False)
            self.loading.show()
            QApplication.processEvents()

            def _on_progreso(porcentaje, mensaje):
                self.loading.actualizar(porcentaje, mensaje)
                QApplication.processEvents()
                if porcentaje >= 100:
                    self.loading.close()
                    self.app_main.show()

            try:
                self.app_main = AppMultitareasGUI(
                    usuario, persona, callback_progreso=_on_progreso
                )
            except Exception as e:
                logging.error(f"Error fatal al iniciar la aplicación principal: {e}")
                if hasattr(self, 'loading') and self.loading:
                    self.loading.close()
                self.show()
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error de Inicio", f"No se pudo cargar la aplicación:\n{e}")

        self.welcome = WelcomeScreen(
            None, usuario, avatar_path,
            on_accept_callback=iniciar_carga,
            colores=COLORES
        )
        self.welcome.show()

