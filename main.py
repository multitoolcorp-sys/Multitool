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
                if obj.property("is_nav_modulo"):
                    mod_nom = obj.property("modulo_nombre") or obj.text()
                    JsonLogger.log_global("INFO", f"Módulo: {mod_nom}", modulo="Navegación")
                elif obj.property("is_nav_submodulo"):
                    sub_nom = obj.property("submodulo_nombre") or obj.text()
                    mod_nom = obj.property("modulo_padre") or ""
                    JsonLogger.log_global("INFO", f"Módulo: {mod_nom} > Pestaña: {sub_nom}", modulo="Navegación")
                else:
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
    from controlador.utils.paths import get_data_path
    log_dir = get_data_path()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "multitool.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(str(log_file), encoding="utf-8"), logging.StreamHandler(sys.stdout)]
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

def extraer_url_de_argumentos(args):
    """Extrae una URL si la aplicación fue invocada como navegador predeterminado."""
    for i, arg in enumerate(args[1:], start=1):
        clean = arg.strip('"\'')
        if clean.startswith("http://") or clean.startswith("https://"):
            return clean
        if clean.startswith("--url="):
            return clean.split("=", 1)[1].strip('"\'')
        if clean == "--url" and i < len(args) - 1:
            return args[i + 1].strip('"\'')
    return None

def main():
    setup_logging()
    setup_error_handler()
    setup_platform_specific()

    # Manejo de enlaces web externos cuando MultiTool actúa como navegador
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    ipc_main_channel = "MultiTool_Browser_IPC"
    target_url = extraer_url_de_argumentos(sys.argv)

    # Si se invoca la aplicación pasando explícitamente una URL web (ej. clic en enlace externo):
    # intentamos despachar la pestaña a una instancia activa para no duplicar toda la suite.
    if target_url:
        client_socket = QLocalSocket()
        client_socket.connectToServer(ipc_main_channel)
        if client_socket.waitForConnected(300):
            msg = f"OPEN_URL:{target_url}"
            client_socket.write(msg.encode("utf-8"))
            client_socket.flush()
            client_socket.waitForBytesWritten(1000)
            client_socket.disconnectFromServer()
            sys.exit(0)

    # 1. Crear la Aplicación (Soporte Multi-instancia completo: permite múltiples usuarios y sesiones)
    app = QApplication(sys.argv)
    app.setApplicationName("Multitool")
    app.setOrganizationName("Antigravity")
    app.initial_url_to_open = target_url

    # Servidor IPC para recepción de enlaces externos en el navegador
    ipc_server = QLocalServer(app)
    is_primary_ipc = False

    if ipc_server.listen(ipc_main_channel):
        is_primary_ipc = True
    else:
        # Si había quedado un pipe inactivo, intentamos limpiar y escuchar una vez
        QLocalServer.removeServer(ipc_main_channel)
        if ipc_server.listen(ipc_main_channel):
            is_primary_ipc = True
        else:
            # Esta instancia funciona con su propio identificador de proceso independiente
            ipc_server.listen(f"MultiTool_IPC_{os.getpid()}")

    def _procesar_mensaje_ipc(data: str):
        main_win = getattr(app, "multitool_main_window", None)
        if data.startswith("OPEN_URL:"):
            url = data.split("OPEN_URL:", 1)[1].strip()
            if main_win and hasattr(main_win, "abrir_url_en_navegador"):
                main_win.abrir_url_en_navegador(url)
            else:
                app.initial_url_to_open = url
        elif data == "BRING_TO_FRONT":
            if main_win and hasattr(main_win, "traer_al_frente"):
                main_win.traer_al_frente()

    def on_ipc_connection():
        while ipc_server.hasPendingConnections():
            client = ipc_server.nextPendingConnection()
            if not client:
                continue

            def _leer_cliente(sock=client):
                data = sock.readAll().data().decode("utf-8", errors="ignore").strip()
                if data:
                    _procesar_mensaje_ipc(data)
                sock.disconnectFromServer()

            client.readyRead.connect(_leer_cliente)
            client.disconnected.connect(client.deleteLater)
            if client.bytesAvailable() > 0:
                _leer_cliente()

    ipc_server.newConnection.connect(on_ipc_connection)

    def cleanup_ipc():
        try:
            ipc_server.close()
            if is_primary_ipc:
                QLocalServer.removeServer(ipc_main_channel)
        except Exception:
            pass

    app.aboutToQuit.connect(cleanup_ipc)
    
    # Estilo base global para diálogos, mensajes emergentes (QMessageBox) y tooltips
    from vistas.estilos import generar_qss_global
    app.setStyleSheet(generar_qss_global())
    
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
