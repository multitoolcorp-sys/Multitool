"""
dock_math.py - Funciones auxiliares para bordes, acople (dock) y coordenadas de pantalla de widgets
"""
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QGuiApplication

DOCK_SNAP_THRESHOLD = 35

def get_screen_geometry():
    """Retorna la geometría de la pantalla principal"""
    screen = QGuiApplication.primaryScreen()
    if screen:
        return screen.geometry()
    return QRect(0, 0, 1920, 1080)

def calculate_dock_position(pos: QPoint, size_w: int, size_h: int, snap_margin: int = DOCK_SNAP_THRESHOLD):
    """Calcula la posición acoplada en el borde de la pantalla más cercano"""
    screen_rect = get_screen_geometry()
    x, y = pos.x(), pos.y()
    
    # Distancias a bordes
    dist_left = abs(x - screen_rect.left())
    dist_right = abs((screen_rect.right() - size_w) - x)
    dist_top = abs(y - screen_rect.top())
    dist_bottom = abs((screen_rect.bottom() - size_h) - y)

    min_dist = min(dist_left, dist_right, dist_top, dist_bottom)
    
    if min_dist == dist_left:
        x = screen_rect.left()
    elif min_dist == dist_right:
        x = screen_rect.right() - size_w
    elif min_dist == dist_top:
        y = screen_rect.top()
    elif min_dist == dist_bottom:
        y = screen_rect.bottom() - size_h

    # Clamping dentro de pantalla
    x = max(screen_rect.left(), min(x, screen_rect.right() - size_w))
    y = max(screen_rect.top(), min(y, screen_rect.bottom() - size_h))
    
    return QPoint(x, y)
