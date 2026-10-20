"""
area_selector.py
Ventana de selección de área de pantalla completa con fondo congelado atenuado.
Permite hacer clic y arrastrar para seleccionar una región exacta.
Llama a `on_select(x, y, w, h, crop_pixmap=None)`.
"""
import inspect
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QGuiApplication, QPixmap


class AreaSelector(QWidget):
    """
    Overlay de pantalla completa para seleccionar un área haciendo clic y arrastrando.
    Muestra la pantalla congelada con fondo atenuado y resalta en tiempo real
    el área seleccionada, garantizando recortes 100% nítidos y sin artefactos blancos.
    """

    def __init__(self, on_select=None, pixmap_base=None, screen_geo=None):
        super().__init__()
        self.on_select = on_select

        screen = QGuiApplication.primaryScreen()
        self.screen_geo = screen_geo if screen_geo is not None else screen.geometry()
        self.setGeometry(self.screen_geo)

        if pixmap_base is not None and not pixmap_base.isNull():
            self.pixmap_base = pixmap_base
        else:
            self.pixmap_base = screen.grabWindow(0)

        self._start = QPoint()
        self._end = QPoint()
        self._selecting = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.show()

    # ── Eventos de ratón ──────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            self._end = event.position().toPoint()
            self.close()

            rect = self._get_rect()
            if rect.width() > 5 and rect.height() > 5 and self.on_select:
                global_x = rect.x() + self.screen_geo.x()
                global_y = rect.y() + self.screen_geo.y()

                crop = None
                if self.pixmap_base and not self.pixmap_base.isNull():
                    rx = max(0, min(rect.x(), self.pixmap_base.width() - 1))
                    ry = max(0, min(rect.y(), self.pixmap_base.height() - 1))
                    rw = min(rect.width(), self.pixmap_base.width() - rx)
                    rh = min(rect.height(), self.pixmap_base.height() - ry)
                    if rw > 0 and rh > 0:
                        crop = self.pixmap_base.copy(rx, ry, rw, rh)

                try:
                    sig = inspect.signature(self.on_select)
                    params = list(sig.parameters.values())
                    if len(params) >= 5 or any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params):
                        self.on_select(global_x, global_y, rect.width(), rect.height(), crop)
                    else:
                        self.on_select(global_x, global_y, rect.width(), rect.height())
                except Exception:
                    self.on_select(global_x, global_y, rect.width(), rect.height())

    def keyPressEvent(self, event):
        # Cancelar con Escape
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    # ── Dibujo ───────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)

        # 1. Dibujar el fondo congelado de la pantalla
        if self.pixmap_base and not self.pixmap_base.isNull():
            painter.drawPixmap(0, 0, self.pixmap_base)

        # 2. Atenuación oscura sobre toda la pantalla
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        rect = self._get_rect()
        if not rect.isNull() and rect.width() > 1 and rect.height() > 1:
            # 3. Dibujar la región seleccionada iluminada (sin atenuar)
            if self.pixmap_base and not self.pixmap_base.isNull():
                painter.drawPixmap(rect, self.pixmap_base, rect)

            # 4. Borde del área
            pen = QPen(QColor(74, 134, 232), 2)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

            # 5. Badge con dimensiones
            info = f" {rect.width()} × {rect.height()} px "
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(info)
            th = fm.height()

            badge_y = rect.y() - th - 6 if rect.y() >= th + 8 else rect.y() + 6
            badge_x = rect.x() + 4

            painter.fillRect(badge_x, badge_y, tw + 6, th + 4, QColor(20, 20, 30, 220))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_x + 3, badge_y + th - 2, info)

        # Instrucciones centradas si aún no se seleccionó nada
        if not self._selecting and (rect.isNull() or (rect.width() < 5 and rect.height() < 5)):
            painter.setPen(QColor(240, 240, 240))
            painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Haz clic y arrastra con el ratón para recortar el área\nPresiona Escape para cancelar",
            )

    # ── Utilidades ───────────────────────────────────────────────────

    def _get_rect(self):
        return QRect(self._start, self._end).normalized()
