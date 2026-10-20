from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

def center_window(window):
    """
    Centra una ventana de forma robusta en la pantalla donde se encuentra actualmente.
    Compatible con configuraciones multi-monitor.
    """
    screen = QApplication.primaryScreen().availableGeometry()
    if window.parent() and hasattr(window.parent(), 'screen'):
        screen = window.parent().screen().availableGeometry()
    
    size = window.geometry()
    x = screen.left() + (screen.width() - size.width()) // 2
    y = screen.top() + (screen.height() - size.height()) // 2
    window.move(x, y)

def set_appwindow(window):
    """
    Asigna flags de ventana para asegurar que el comportamiento sea consistente
    en diferentes gestores de ventanas (Windows, GNOME, etc).
    """
    window.setWindowFlags(window.windowFlags() | Qt.WindowType.Window)

