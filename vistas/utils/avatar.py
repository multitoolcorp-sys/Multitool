from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QBrush, QColor
from PyQt6.QtCore import Qt, QRect

class AvatarUtils:
    @staticmethod
    def get_circular_pixmap(pixmap, size=64):
        """Convierte cualquier pixmap en uno circular con bordes suavizados"""
        if pixmap.isNull():
            return pixmap
            
        # Crear un pixmap de destino con transparencia
        target = QPixmap(size, size)
        target.fill(Qt.GlobalColor.transparent)
        
        # Redimensionar el original para que cubra el círculo
        scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        
        # Centrar el recorte
        offset_x = (scaled.width() - size) // 2
        offset_y = (scaled.height() - size) // 2
        
        painter = QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Crear el camino circular
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        # Dibujar la imagen escalada y centrada
        painter.drawPixmap(0, 0, scaled.copy(offset_x, offset_y, size, size))
        painter.end()
        
        return target

    @staticmethod
    def get_square_pixmap(pixmap, size=64):
        """Redimensiona un pixmap a un cuadrado perfecto sin recortes circulares"""
        if pixmap.isNull():
            return pixmap
        return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)

    @staticmethod
    def get_initials_avatar(initial, size=64, bg_color="#6366F1", fg_color="white", circular=True):
        """Genera un avatar con una inicial (circular o cuadrado)"""
        target = QPixmap(size, size)
        target.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(QBrush(QColor(bg_color)))
        painter.setPen(Qt.PenStyle.NoPen)
        
        if circular:
            painter.drawEllipse(0, 0, size, size)
        else:
            painter.drawRect(0, 0, size, size)
        
        painter.setPen(QColor(fg_color))
        font = painter.font()
        font.setPixelSize(int(size * 0.5))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, initial)
        
        painter.end()
        return target

