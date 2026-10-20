"""
casino_widgets.py - Componentes visuales y gráficos animados para el Casino de MiniGames:
- RouletteWheelWidget: Ruleta circular europea realista con sectores rojo/negro/verde y bola animada.
- PlayingCardWidget: Carta de baraja francesa realista con diseño de casino, esquinas y figuras.
"""
import math
import random
from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, QRadialGradient, 
    QLinearGradient, QPainterPath
)

# Orden oficial de la Ruleta Europea (37 casillas)
EUROPEAN_ROULETTE_ORDER = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5,
    24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

ROULETTE_COLORS = {
    0: "#10B981", 32: "#EF4444", 15: "#1E293B", 19: "#EF4444", 4: "#1E293B",
    21: "#EF4444", 2: "#1E293B", 25: "#EF4444", 17: "#1E293B", 34: "#EF4444",
    6: "#1E293B", 27: "#EF4444", 13: "#1E293B", 36: "#EF4444", 11: "#1E293B",
    30: "#EF4444", 8: "#1E293B", 23: "#EF4444", 10: "#1E293B", 5: "#EF4444",
    24: "#1E293B", 16: "#EF4444", 33: "#1E293B", 1: "#EF4444", 20: "#1E293B",
    14: "#EF4444", 31: "#1E293B", 9: "#EF4444", 22: "#1E293B", 18: "#EF4444",
    29: "#1E293B", 7: "#EF4444", 28: "#1E293B", 12: "#EF4444", 35: "#1E293B",
    3: "#EF4444", 26: "#1E293B"
}


class RouletteWheelWidget(QWidget):
    """
    Ruleta circular interactiva dibujada con QPainter vectorial:
    - 37 casillas con números y colores europeos auténticos.
    - Giro de rueda y pelota independiente con física de desaceleración.
    - Centro metálico con cabezal dorado y visor del número ganador.
    """
    spinFinished = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(270, 270)
        self.wheel_angle = 0.0
        self.ball_angle = 0.0
        self.ball_radius_ratio = 0.85
        self.target_number = 0
        self.current_display_number = 0

        self.spinning = False
        self.spin_timer = QTimer(self)
        self.spin_timer.timeout.connect(self._on_spin_tick)

        self.spin_step = 0
        self.total_spin_steps = 75
        self.initial_wheel_speed = 14.0
        self.initial_ball_speed = -24.0
        self.wheel_speed = 0.0
        self.ball_speed = 0.0

    def spin_to(self, number: int):
        """Inicia la animación de lanzamiento de bola hacia el número ganador."""
        if self.spinning:
            return
        self.target_number = number
        self.spinning = True
        self.spin_step = 0
        self.wheel_speed = self.initial_wheel_speed
        self.ball_speed = self.initial_ball_speed
        self.ball_radius_ratio = 0.88
        self.spin_timer.start(30)

    def _on_spin_tick(self):
        self.spin_step += 1
        progress = self.spin_step / self.total_spin_steps

        # Desaceleración suave (Ease-Out)
        damping = max(0.0, 1.0 - (progress ** 1.8))
        self.wheel_angle = (self.wheel_angle + self.wheel_speed * damping) % 360.0
        self.ball_angle = (self.ball_angle + self.ball_speed * damping) % 360.0

        # La bola cae hacia la pista interior
        if progress > 0.65:
            self.ball_radius_ratio = max(0.64, 0.88 - (progress - 0.65) * 0.75)

        if self.spin_step >= self.total_spin_steps:
            self.spin_timer.stop()
            self.spinning = False

            # Fijar exactamente en el casillero ganador
            idx = EUROPEAN_ROULETTE_ORDER.index(self.target_number)
            slice_angle = 360.0 / 37.0
            # Posición angular del sector
            sector_center_angle = idx * slice_angle + slice_angle / 2.0
            self.ball_angle = (self.wheel_angle + sector_center_angle) % 360.0
            self.ball_radius_ratio = 0.65
            self.current_display_number = self.target_number

            col = ROULETTE_COLORS.get(self.target_number, "green")
            color_name = "red" if col == "#EF4444" else ("black" if col == "#1E293B" else "green")
            self.update()
            self.spinFinished.emit(self.target_number, color_name)
            return

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        size = min(w, h) - 10
        cx = w / 2.0
        cy = h / 2.0
        outer_r = size / 2.0

        # 1. Borde Exterior de Madera / Caoba de Casino
        wood_grad = QRadialGradient(cx, cy, outer_r)
        wood_grad.setColorAt(0.75, QColor("#2A120A"))
        wood_grad.setColorAt(0.92, QColor("#451A0D"))
        wood_grad.setColorAt(1.0, QColor("#170905"))
        painter.setBrush(QBrush(wood_grad))
        painter.setPen(QPen(QColor("#D97706"), 3))
        painter.drawEllipse(QPointF(cx, cy), outer_r, outer_r)

        # 2. Pista Dorada de Separación
        gold_r = outer_r * 0.91
        gold_grad = QLinearGradient(cx - gold_r, cy - gold_r, cx + gold_r, cy + gold_r)
        gold_grad.setColorAt(0.0, QColor("#FBBF24"))
        gold_grad.setColorAt(0.5, QColor("#92400E"))
        gold_grad.setColorAt(1.0, QColor("#FDE68A"))
        painter.setBrush(QBrush(gold_grad))
        painter.setPen(QPen(QColor("#78350F"), 1))
        painter.drawEllipse(QPointF(cx, cy), gold_r, gold_r)

        # 3. Pista de Sectores de Números (37 rebanadas)
        track_r = outer_r * 0.85
        inner_track_r = outer_r * 0.52
        slice_angle = 360.0 / 37.0

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.wheel_angle)

        font_numbers = QFont("Consolas", max(7, int(size * 0.034)), QFont.Weight.Bold)
        painter.setFont(font_numbers)

        for i, num in enumerate(EUROPEAN_ROULETTE_ORDER):
            start_ang = i * slice_angle
            col_hex = ROULETTE_COLORS.get(num, "#10B981")

            path = QPainterPath()
            path.arcMoveTo(QRectF(-track_r, -track_r, track_r * 2, track_r * 2), -start_ang)
            path.arcTo(QRectF(-track_r, -track_r, track_r * 2, track_r * 2), -start_ang, -slice_angle)
            path.arcTo(QRectF(-inner_track_r, -inner_track_r, inner_track_r * 2, inner_track_r * 2), -(start_ang + slice_angle), slice_angle)
            path.closeSubpath()

            painter.setBrush(QBrush(QColor(col_hex)))
            painter.setPen(QPen(QColor(217, 119, 6, 120), 1))
            painter.drawPath(path)

            # Dibujar número en el sector
            mid_angle_rad = math.radians(start_ang + slice_angle / 2.0)
            text_dist = outer_r * 0.70
            tx = text_dist * math.cos(mid_angle_rad)
            ty = text_dist * math.sin(mid_angle_rad)

            painter.save()
            painter.translate(tx, ty)
            painter.rotate(start_ang + slice_angle / 2.0 + 90)
            painter.setPen(QColor("white"))
            rect_txt = QRectF(-12, -8, 24, 16)
            painter.drawText(rect_txt, Qt.AlignmentFlag.AlignCenter, str(num))
            painter.restore()

        painter.restore()

        # 4. Centro / Cono Metálico Dorado del Eje
        hub_r = outer_r * 0.48
        hub_grad = QRadialGradient(cx - hub_r * 0.2, cy - hub_r * 0.2, hub_r)
        hub_grad.setColorAt(0.0, QColor("#FEF08A"))
        hub_grad.setColorAt(0.4, QColor("#F59E0B"))
        hub_grad.setColorAt(0.85, QColor("#78350F"))
        hub_grad.setColorAt(1.0, QColor("#1C1917"))
        painter.setBrush(QBrush(hub_grad))
        painter.setPen(QPen(QColor("#FBBF24"), 2))
        painter.drawEllipse(QPointF(cx, cy), hub_r, hub_r)

        # 5. Visor Central del Número Actual
        core_r = hub_r * 0.62
        painter.setBrush(QBrush(QColor("#09090E")))
        painter.setPen(QPen(QColor("#FBBF24"), 1.5))
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        num_color = ROULETTE_COLORS.get(self.current_display_number, "#10B981")
        painter.setFont(QFont("Consolas", max(13, int(size * 0.08)), QFont.Weight.Bold))
        painter.setPen(QColor(num_color))
        painter.drawText(QRectF(cx - core_r, cy - core_r, core_r * 2, core_r * 2),
                         Qt.AlignmentFlag.AlignCenter, str(self.current_display_number))

        # 6. Bola de Marfil / Pelota de la Ruleta (Pelota blanca con relieve)
        ball_dist = outer_r * self.ball_radius_ratio
        ball_ang_rad = math.radians(self.ball_angle)
        bx = cx + ball_dist * math.cos(ball_ang_rad)
        by = cy + ball_dist * math.sin(ball_ang_rad)
        ball_size = max(5.0, size * 0.026)

        # Sombra de la bola
        painter.setBrush(QBrush(QColor(0, 0, 0, 140)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(bx + 2, by + 2), ball_size, ball_size)

        # Bola 3D
        ball_grad = QRadialGradient(bx - ball_size * 0.3, by - ball_size * 0.3, ball_size)
        ball_grad.setColorAt(0.0, QColor("#FFFFFF"))
        ball_grad.setColorAt(0.7, QColor("#E2E8F0"))
        ball_grad.setColorAt(1.0, QColor("#94A3B8"))
        painter.setBrush(QBrush(ball_grad))
        painter.drawEllipse(QPointF(bx, by), ball_size, ball_size)


class PlayingCardWidget(QFrame):
    """
    Carta de baraja francesa realista con estética premium de casino:
    - Fondo blanco marfil, bordes biselados y sombra.
    - Rangos e iconos de palos en esquinas y figura central.
    - Reverso decorativo con grabado royal cuando está oculta.
    """
    def __init__(self, rank="A", suit="♠", hidden=False, parent=None):
        super().__init__(parent)
        self.rank = rank
        self.suit = suit
        self.hidden = hidden
        self.setFixedSize(68, 96)
        self.update()

    def set_card(self, rank, suit, hidden=False):
        self.rank = rank
        self.suit = suit
        self.hidden = hidden
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        rect = QRectF(1, 1, w - 2, h - 2)

        if self.hidden:
            # Reverso de Carta Royal Casino (Azul Profundo con grabado geométrico)
            back_grad = QLinearGradient(0, 0, w, h)
            back_grad.setColorAt(0.0, QColor("#1E3A8A"))
            back_grad.setColorAt(0.5, QColor("#172554"))
            back_grad.setColorAt(1.0, QColor("#0F172A"))
            painter.setBrush(QBrush(back_grad))
            painter.setPen(QPen(QColor("#38BDF8"), 1.5))
            painter.drawRoundedRect(rect, 8, 8)

            # Patrón interno
            inner_rect = rect.adjusted(5, 5, -5, -5)
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(inner_rect, 5, 5)

            painter.setFont(QFont("Segoe UI Emoji", 22))
            painter.setPen(QColor("#93C5FD"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🂠")
            return

        # Anverso de la Carta (Fondo Marfil con esquinas redondeadas)
        card_grad = QLinearGradient(0, 0, 0, h)
        card_grad.setColorAt(0.0, QColor("#FFFFFF"))
        card_grad.setColorAt(1.0, QColor("#F8FAFC"))
        painter.setBrush(QBrush(card_grad))
        painter.setPen(QPen(QColor("#CBD5E1"), 1.5))
        painter.drawRoundedRect(rect, 8, 8)

        is_red = self.suit in ["♥", "♦"]
        color = QColor("#DC2626" if is_red else "#0F172A")
        painter.setPen(color)

        # 1. Esquina Superior Izquierda (Rango + Palo)
        font_corner = QFont("Consolas", 10, QFont.Weight.Bold)
        painter.setFont(font_corner)
        painter.drawText(QRectF(5, 4, 24, 14), Qt.AlignmentFlag.AlignLeft, self.rank)
        font_mini_suit = QFont("Segoe UI Emoji", 9)
        painter.setFont(font_mini_suit)
        painter.drawText(QRectF(5, 17, 24, 14), Qt.AlignmentFlag.AlignLeft, self.suit)

        # 2. Icono Central Grande
        font_center = QFont("Segoe UI Emoji", 26)
        painter.setFont(font_center)
        painter.drawText(QRectF(0, 20, w, h - 35), Qt.AlignmentFlag.AlignCenter, self.suit)

        # 3. Esquina Inferior Derecha (Invertida)
        painter.setFont(font_corner)
        painter.drawText(QRectF(w - 28, h - 30, 24, 14), Qt.AlignmentFlag.AlignRight, self.suit)
        painter.drawText(QRectF(w - 28, h - 18, 24, 14), Qt.AlignmentFlag.AlignRight, self.rank)
