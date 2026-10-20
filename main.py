import sys
import os
import platform
import logging
import signal

# Startup configuration
try:
    from PyQt6.QtCore import Qt, QCoreApplication
    # Compartir contextos OpenGL si es requerido por widgets gráficos
    if hasattr(Qt.ApplicationAttribute, "AA_ShareOpenGLContexts"):
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
except Exception:
    pass

from PyQt6.QtWidgets import QApplication, QPushButton, QTabBar, QComboBox, QLineEdit
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QEvent, QObject

# Importaciones locales
from vistas.errors import setup_error_handler
from vistas.launcher import Launcher
from vistas.utils.logs import JsonLogger
from vistas.utils.startup_diagnostics import StartupDiagnostics

class GlobalActionFilter(QObject):
    """Filtro de eventos multiplataforma enriquecido para auditoría de acciones"""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonRelease:
            if isinstance(obj, QPushButton):
                texto = obj.text().replace("\n", " ").strip() or obj.toolTip() or "Botón"
                JsonLogger.log_global("INFO", f"Clic en Botón: {texto}", modulo="AcciónUsuario")
            elif isinstance(obj, QTabBar):
                idx = obj.currentIndex()
                txt = obj.tabText(idx) if idx >= 0 else "Pestaña"
                JsonLogger.log_global("INFO", f"Selección de Pestaña: {txt}", modulo="Navegación")
            elif isinstance(obj, QComboBox):
                txt = obj.currentText()
                JsonLogger.log_global("INFO", f"Selección Combo: {txt}", modulo="AcciónUsuario")
        return super().eventFilter(obj, event)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler("multitool.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)]
    )

def setup_platform_specific():
    """Mantiene la lógica para múltiples sistemas operativos (Windows/Linux/macOS)"""
    os_name = platform.system()
    
    if os_name == "Windows":
        # Evitar agrupación en barra de tareas de Windows
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('google.antigravity.multitool.v1')
        except: pass
    elif os_name == "Linux":
        pass
    elif os_name == "Darwin": # macOS
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, False)

    # Permitir Ctrl+C en terminal para todos los sistemas
    signal.signal(signal.SIGINT, signal.SIG_DFL)

def main():
    setup_logging()
    setup_error_handler()
    setup_platform_specific()

    # 1. Crear la Aplicación
    app = QApplication(sys.argv)
    app.setApplicationName("Multitool")
    app.setOrganizationName("Antigravity")
    
    # Estilo base global para diálogos, mensajes emergentes (QMessageBox) y tooltips
    app.setStyleSheet("""
        QMessageBox {
            background-color: #1E1E2E;
            color: #FFFFFF;
        }
        QMessageBox QLabel {
            color: #FFFFFF;
            background-color: transparent;
            font-size: 9.5pt;
        }
        QMessageBox QPushButton {
            background-color: #6366F1;
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 6px 16px;
            font-weight: bold;
            min-width: 75px;
        }
        QMessageBox QPushButton:hover {
            background-color: #4F46E5;
        }
        QToolTip {
            background-color: #2D2D3D;
            color: #FFFFFF;
            border: 1px solid #4B5563;
            padding: 5px 8px;
            border-radius: 4px;
            font-size: 9pt;
        }
        QMenu {
            background-color: #1E1E2E;
            color: #E2E8F0;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            padding: 6px;
        }
        QMenu::item {
            background-color: transparent;
            color: #E2E8F0;
            padding: 8px 24px 8px 14px;
            border-radius: 6px;
            font-size: 9.5pt;
        }
        QMenu::item:selected {
            background-color: #6366F1;
            color: #FFFFFF !important;
            font-weight: bold;
        }
        QMenu::item:disabled {
            background-color: transparent;
            color: #64748B !important;
        }
        QMenu::separator {
            height: 1px;
            background-color: rgba(255, 255, 255, 0.08);
            margin: 4px 6px;
        }
        QMenu::indicator {
            width: 16px;
            height: 16px;
            margin-left: 6px;
        }
        QMenu::indicator:checked {
            background-color: #6366F1;
            border: 1px solid #818CF8;
            border-radius: 3px;
        }
        QMenu::indicator:unchecked {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 3px;
        }
    """)
    
    # 2. Diagnósticos de Inicio (Pre-Flight Checks)
    is_ok, warnings = StartupDiagnostics.run_checks()
    for w in warnings:
        logging.warning(f"[StartupDiagnostics] {w}")
    
    # 3. Ícono de aplicación (Taskbar + Tray)
    try:
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vistas", "utils", "icono.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except Exception: pass
    
    # 4. Instalar filtros globales
    action_filter = GlobalActionFilter(app)
    app.installEventFilter(action_filter)
    
    # 5. Lanzar aplicación (Login/Selector)
    launcher = Launcher()
    launcher.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
