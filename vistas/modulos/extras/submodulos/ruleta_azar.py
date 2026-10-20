import math
import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import (
    QFont, QColor, QBrush, QPen, QPainter, QPainterPath,
    QRadialGradient, QLinearGradient
)


# ─────────────────────────────────────────────────────────────────────────
# LANZADOR DE DADOS 3D (D4, D6, D8, D10, D12, D20 - LÍMITE D20 D&D)
# ─────────────────────────────────────────────────────────────────────────
class Dice3DWidget(QWidget):
    """
    Widget de animación 3D de Dado cerámico blanco con bordes redondeados y puntos (pips),
    inspirado en dados reales tridimensionales. Límite máximo: D20.
    """
    def __init__(self, colores, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.setMinimumSize(250, 230)

        self.rot_y = 0.3        # Ángulo isométrica Y
        self.rot_x = 0.3        # Ángulo isométrica X
        self.altura_z = 0.0      # Elevación en el aire
        self.val_top = 3
        self.val_left = 5
        self.val_right = 6
        self.caras = 6
        self.animando = False
        self.resultado_final = 6

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animar_step)
        self.frame_actual = 0
        self.total_frames = 60

    def iniciar_lanzamiento(self, caras, resultado):
        self.caras = min(20, caras)  # Límite máximo 20 caras (D&D)
        self.resultado_final = resultado
        self.animando = True
        self.frame_actual = 0
        self.total_frames = 60
        self.timer.start(16)  # 60 FPS

    def _animar_step(self):
        self.frame_actual += 1
        progress = self.frame_actual / self.total_frames

        # Elevación Z (parábola de salto)
        self.altura_z = 150.0 * math.sin(progress * math.pi)

        # Rotación rápida 3D isométrica
        ease = 1.0 - math.pow(1.0 - progress, 3)
        self.rot_y = ease * 6.0 * math.pi + 0.3
        self.rot_x = ease * 4.0 * math.pi + 0.3

        # Cambiar valores mostrados mientras gira
        if self.frame_actual % 3 == 0:
            self.val_top = random.randint(1, self.caras)
            self.val_left = random.randint(1, self.caras)
            self.val_right = random.randint(1, self.caras)

        self.update()

        if self.frame_actual >= self.total_frames:
            self.timer.stop()
            self.animando = False
            self.altura_z = 0.0
            self.rot_y = 0.3
            self.rot_x = 0.3
            self.val_top = self.resultado_final
            self.val_left = (self.resultado_final % self.caras) + 1
            self.val_right = ((self.resultado_final + 2) % self.caras) + 1
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0 + 20.0

        # ── 1. Sombra 3D Proyectada en el Suelo ──
        factor_sombra = max(0.2, 1.0 - (self.altura_z / 170.0))
        ancho_sombra = 95.0 * factor_sombra
        alto_sombra = 28.0 * factor_sombra
        opacidad_sombra = int(120 * factor_sombra)

        sombra_grad = QRadialGradient(QPointF(cx, cy + 30), ancho_sombra / 2.0)
        sombra_grad.setColorAt(0.0, QColor(0, 0, 0, opacidad_sombra))
        sombra_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(sombra_grad))
        painter.drawEllipse(QPointF(cx, cy + 30), ancho_sombra / 2.0, alto_sombra / 2.0)

        # ── 2. Dado Cerámico Blanco 3D (Cubo Redondeado) ──
        dice_cy = cy - self.altura_z
        sz = 46.0

        # Caras del Cubo Isométrico
        # Cara Superior (Top)
        top_p = [
            QPointF(cx, dice_cy - sz * 1.1),
            QPointF(cx + sz * 0.9, dice_cy - sz * 0.55),
            QPointF(cx, dice_cy - sz * 0.05),
            QPointF(cx - sz * 0.9, dice_cy - sz * 0.55)
        ]
        path_top = QPainterPath()
        path_top.moveTo(top_p[0])
        path_top.lineTo(top_p[1])
        path_top.lineTo(top_p[2])
        path_top.lineTo(top_p[3])
        path_top.closeSubpath()

        # Cara Izquierda (Left)
        left_p = [
            QPointF(cx - sz * 0.9, dice_cy - sz * 0.55),
            QPointF(cx, dice_cy - sz * 0.05),
            QPointF(cx, dice_cy + sz * 0.95),
            QPointF(cx - sz * 0.9, dice_cy + sz * 0.45)
        ]
        path_left = QPainterPath()
        path_left.moveTo(left_p[0])
        path_left.lineTo(left_p[1])
        path_left.lineTo(left_p[2])
        path_left.lineTo(left_p[3])
        path_left.closeSubpath()

        # Cara Derecha (Right)
        right_p = [
            QPointF(cx, dice_cy - sz * 0.05),
            QPointF(cx + sz * 0.9, dice_cy - sz * 0.55),
            QPointF(cx + sz * 0.9, dice_cy + sz * 0.45),
            QPointF(cx, dice_cy + sz * 0.95)
        ]
        path_right = QPainterPath()
        path_right.moveTo(right_p[0])
        path_right.lineTo(right_p[1])
        path_right.lineTo(right_p[2])
        path_right.lineTo(right_p[3])
        path_right.closeSubpath()

        # Estilo Cerámico Blanco / Marfil con sombras suaves
        grad_top = QLinearGradient(cx, dice_cy - sz * 1.1, cx, dice_cy)
        grad_top.setColorAt(0.0, QColor("#FFFFFF"))
        grad_top.setColorAt(1.0, QColor("#F1F5F9"))

        grad_left = QLinearGradient(cx - sz, dice_cy, cx, dice_cy + sz)
        grad_left.setColorAt(0.0, QColor("#E2E8F0"))
        grad_left.setColorAt(1.0, QColor("#CBD5E1"))

        grad_right = QLinearGradient(cx, dice_cy, cx + sz, dice_cy + sz)
        grad_right.setColorAt(0.0, QColor("#CBD5E1"))
        grad_right.setColorAt(1.0, QColor("#94A3B8"))

        border_pen = QPen(QColor("#94A3B8"), 1.8)

        # Dibujar caras en 3D
        painter.setPen(border_pen)

        painter.setBrush(QBrush(grad_top))
        painter.drawPath(path_top)

        painter.setBrush(QBrush(grad_left))
        painter.drawPath(path_left)

        painter.setBrush(QBrush(grad_right))
        painter.drawPath(path_right)

        # ── 3. Dibujar Puntos (Pips) o Números en las caras ──
        self._dibujar_contenido_cara(painter, cx, dice_cy - sz * 0.58, sz * 0.7, self.val_top, "#1E293B")
        self._dibujar_contenido_cara(painter, cx - sz * 0.45, dice_cy + sz * 0.2, sz * 0.6, self.val_left, "#334155")
        self._dibujar_contenido_cara(painter, cx + sz * 0.45, dice_cy + sz * 0.2, sz * 0.6, self.val_right, "#475569")

    def _dibujar_contenido_cara(self, painter, x, y, size, valor, color_hex):
        if self.caras == 6 and 1 <= valor <= 6:
            self._dibujar_pips_dado(painter, x, y, size, valor, color_hex)
        else:
            painter.setPen(QColor(color_hex))
            font_sz = int(size * 0.7)
            painter.setFont(QFont("Segoe UI", font_sz, QFont.Weight.Bold))
            rect = QRectF(x - size, y - size, size * 2, size * 2)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(valor))

    def _dibujar_pips_dado(self, painter, x, y, size, val, color_hex):
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(Qt.PenStyle.NoPen)
        r = size * 0.14
        d = size * 0.35

        coords = []
        if val == 1:
            coords = [(0, 0)]
        elif val == 2:
            coords = [(-d, -d), (d, d)]
        elif val == 3:
            coords = [(-d, -d), (0, 0), (d, d)]
        elif val == 4:
            coords = [(-d, -d), (d, -d), (-d, d), (d, d)]
        elif val == 5:
            coords = [(-d, -d), (d, -d), (0, 0), (-d, d), (d, d)]
        elif val == 6:
            coords = [(-d, -d), (d, -d), (-d, 0), (d, 0), (-d, d), (d, d)]

        for dx, dy in coords:
            painter.drawEllipse(QPointF(x + dx, y + dy * 0.5), r, r * 0.75)


class LanzadorDadosView(QWidget):
    def __init__(self, parent, colores):
        super().__init__(parent)
        self.colores = colores
        self.caras_actuales = 6
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl_tipo = QLabel("🎲 Selecciona el tipo de dado (Límite D20 D&D):")
        lbl_tipo.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(lbl_tipo)

        h_dados_btn = QHBoxLayout()
        h_dados_btn.setSpacing(8)

        self.tipo_btns = {}
        for d in [4, 6, 8, 10, 12, 20]:
            btn = QPushButton(f"D{d}")
            btn.setFixedSize(52, 38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._get_btn_style(d == 6))
            btn.clicked.connect(lambda checked, n=d: self.set_tipo_dado(n))
            h_dados_btn.addWidget(btn)
            self.tipo_btns[d] = btn

        h_dados_btn.addStretch()

        lbl_cant = QLabel("Cantidad:")
        lbl_cant.setStyleSheet("color: white; font-size: 11px;")
        h_dados_btn.addWidget(lbl_cant)

        self.spin_cant = QSpinBox()
        self.spin_cant.setRange(1, 6)
        self.spin_cant.setValue(1)
        self.spin_cant.setStyleSheet("QSpinBox { background: rgba(0,0,0,0.3); color: white; padding: 4px; border-radius: 4px; }")
        h_dados_btn.addWidget(self.spin_cant)

        layout.addLayout(h_dados_btn)

        # Widget 3D del Dado Cerámico
        self.dice_3d = Dice3DWidget(self.colores, self)
        layout.addWidget(self.dice_3d, 0, Qt.AlignmentFlag.AlignCenter)

        self.lbl_resultado_dado = QLabel("Resultado: D6")
        self.lbl_resultado_dado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_resultado_dado.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_resultado_dado.setStyleSheet("color: #FBBF24;")
        layout.addWidget(self.lbl_resultado_dado)

        self.lbl_detalle_dado = QLabel("Presiona para lanzar el dado")
        self.lbl_detalle_dado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_detalle_dado.setStyleSheet("color: #AAB0B8; font-size: 12px;")
        layout.addWidget(self.lbl_detalle_dado)

        btn_lanzar = QPushButton("🎲 LANZAR DADO")
        btn_lanzar.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        btn_lanzar.setFixedHeight(44)
        btn_lanzar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_lanzar.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']}; color: white; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_lanzar.clicked.connect(self.lanzar_dados)
        layout.addWidget(btn_lanzar)

    def _get_btn_style(self, selected=False):
        if selected:
            return f"background: {self.colores['acento']}; color: white; font-weight: bold; border-radius: 6px; border: none;"
        return "background: rgba(255,255,255,0.05); color: #AAA; font-weight: bold; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);"

    def set_tipo_dado(self, caras):
        self.caras_actuales = min(20, caras)
        for d, btn in self.tipo_btns.items():
            btn.setStyleSheet(self._get_btn_style(d == self.caras_actuales))
        self.lbl_resultado_dado.setText(f"Resultado: D{self.caras_actuales}")

    def lanzar_dados(self):
        if self.dice_3d.animando:
            return
        cant = self.spin_cant.value()
        res = [random.randint(1, self.caras_actuales) for _ in range(cant)]
        self.dice_3d.iniciar_lanzamiento(self.caras_actuales, res[0])

        def _on_finish():
            total = sum(res)
            if cant > 1:
                self.lbl_resultado_dado.setText(" ".join(str(v) for v in res))
                self.lbl_detalle_dado.setText(f"Suma Total: {total} (Valores: {', '.join(str(v) for v in res)})")
            else:
                self.lbl_resultado_dado.setText(f"¡Salió {res[0]}!")
                self.lbl_detalle_dado.setText(f"Resultado D{self.caras_actuales}: {res[0]}")

        QTimer.singleShot(1100, _on_finish)


# ─────────────────────────────────────────────────────────────────────────
# LANZAMIENTO DE MONEDA (CARA / CRUZ)
# ─────────────────────────────────────────────────────────────────────────
class Coin3DWidget(QWidget):
    """Widget de animación 3D de Lanzamiento de Moneda mediante perspectiva QPainter."""
    def __init__(self, colores, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.setMinimumSize(280, 240)

        self.angulo_rad = 0.0    # Ángulo de giro en el eje Y
        self.altura_z = 0.0      # Altura en el aire (parábola Z)
        self.es_cara = True      # Cara visible actual (True: Cara, False: Cruz)
        self.animando = False

        self.resultado_final = "CARA"  # "CARA" | "CRUZ"

        # Timer de 60 FPS
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animar_step)
        self.frame_actual = 0
        self.total_frames = 60

    def iniciar_lanzamiento(self, resultado):
        self.resultado_final = resultado
        self.animando = True
        self.frame_actual = 0
        self.total_frames = 70
        self.timer.start(16)  # ~60 FPS

    def _animar_step(self):
        self.frame_actual += 1
        progress = self.frame_actual / self.total_frames

        # Parábola de elevación Z (sube y cae)
        self.altura_z = 160.0 * math.sin(progress * math.pi)

        # Giro en eje Y (varias vueltas completas)
        vueltas = 6
        if self.resultado_final == "CARA":
            target_rot = vueltas * 2 * math.pi
        else:
            target_rot = (vueltas + 0.5) * 2 * math.pi

        # Easing cubic out para deceleración
        ease = 1.0 - math.pow(1.0 - progress, 3)
        self.angulo_rad = ease * target_rot

        # Determinar cara visible
        cos_val = math.cos(self.angulo_rad)
        self.es_cara = cos_val >= 0

        self.update()

        if self.frame_actual >= self.total_frames:
            self.timer.stop()
            self.animando = False
            self.altura_z = 0.0
            self.angulo_rad = 0.0 if self.resultado_final == "CARA" else math.pi
            self.es_cara = self.resultado_final == "CARA"
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0 + 30.0  # centro de suelo

        # ── 1. Sombra 3D Proyectada en el Suelo ──
        factor_sombra = max(0.2, 1.0 - (self.altura_z / 180.0))
        ancho_sombra = 90.0 * factor_sombra
        alto_sombra = 20.0 * factor_sombra
        opacidad_sombra = int(120 * factor_sombra)

        sombra_grad = QRadialGradient(QPointF(cx, cy + 20), ancho_sombra / 2.0)
        sombra_grad.setColorAt(0.0, QColor(0, 0, 0, opacidad_sombra))
        sombra_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(sombra_grad))
        painter.drawEllipse(QPointF(cx, cy + 20), ancho_sombra / 2.0, alto_sombra / 2.0)

        # ── 2. Moneda 3D ──
        coin_cy = cy - self.altura_z
        radius = 45.0
        cos_val = abs(math.cos(self.angulo_rad))
        scale_y = max(0.06, cos_val)  # Perspectiva 3D

        # Grosor metálico 3D (cuando está de canto)
        grosor_3d = 8.0 * (1.0 - cos_val)
        if grosor_3d > 1.0:
            painter.setBrush(QBrush(QColor("#B45309")))
            painter.drawEllipse(QPointF(cx, coin_cy + grosor_3d), radius, radius * scale_y)

        # Cuerpo de la Moneda
        if self.es_cara:
            grad = QLinearGradient(cx - radius, coin_cy - radius, cx + radius, coin_cy + radius)
            grad.setColorAt(0.0, QColor("#FBBF24"))
            grad.setColorAt(0.7, QColor("#F59E0B"))
            grad.setColorAt(1.0, QColor("#D97706"))
            border_color = QColor("#FEF3C7")
            text_val = "👑\nCARA"
        else:
            grad = QLinearGradient(cx - radius, coin_cy - radius, cx + radius, coin_cy + radius)
            grad.setColorAt(0.0, QColor("#9CA3AF"))
            grad.setColorAt(0.7, QColor("#6B7280"))
            grad.setColorAt(1.0, QColor("#374151"))
            border_color = QColor("#F3F4F6")
            text_val = "🦅\nCRUZ"

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(border_color, 2))
        painter.drawEllipse(QPointF(cx, coin_cy), radius, radius * scale_y)

        # Círculo interior grabado
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1.5, Qt.PenStyle.DashLine))
        painter.drawEllipse(QPointF(cx, coin_cy), radius * 0.82, radius * 0.82 * scale_y)

        # Texto/Icono Grabado 3D
        if scale_y > 0.3:
            painter.setPen(QColor("#FFFFFF" if self.es_cara else "#F9FAFB"))
            font_sz = int(14 * scale_y)
            if font_sz >= 6:
                painter.setFont(QFont("Segoe UI", font_sz, QFont.Weight.Bold))
                rect_text = QRectF(cx - radius, coin_cy - (radius * scale_y), radius * 2, radius * 2 * scale_y)
                painter.drawText(rect_text, Qt.AlignmentFlag.AlignCenter, text_val)


class LanzamientoMonedaView(QWidget):
    def __init__(self, parent, colores):
        super().__init__(parent)
        self.colores = colores
        self.caras_cnt = 0
        self.cruz_cnt = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Widget 3D de Moneda
        self.coin_3d = Coin3DWidget(self.colores, self)
        layout.addWidget(self.coin_3d, 0, Qt.AlignmentFlag.AlignCenter)

        self.lbl_resultado_coin = QLabel("Presiona para lanzar la moneda")
        self.lbl_resultado_coin.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.lbl_resultado_coin.setStyleSheet("color: white; margin-top: 10px; margin-bottom: 10px;")
        self.lbl_resultado_coin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_resultado_coin)

        btn_flip = QPushButton("🪙 LANZAR MONEDA")
        btn_flip.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        btn_flip.setFixedSize(240, 46)
        btn_flip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_flip.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']}; color: white; border-radius: 10px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_flip.clicked.connect(self.lanzar_moneda)
        layout.addWidget(btn_flip, 0, Qt.AlignmentFlag.AlignCenter)

        self.lbl_stats = QLabel("👑 Cara: 0  |  🦅 Cruz: 0")
        self.lbl_stats.setStyleSheet("color: #AAB0B8; font-size: 13px; font-weight: bold; margin-top: 12px;")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_stats)

    def lanzar_moneda(self):
        if self.coin_3d.animando:
            return
        resultado = random.choice(["CARA", "CRUZ"])
        self.coin_3d.iniciar_lanzamiento(resultado)

        def _on_finish():
            if resultado == "CARA":
                self.caras_cnt += 1
            else:
                self.cruz_cnt += 1
            self.lbl_resultado_coin.setText(f"¡Salió {'CARA 👑' if resultado == 'CARA' else 'CRUZ 🦅'}!")
            self.lbl_stats.setText(f"👑 Cara: {self.caras_cnt}  |  🦅 Cruz: {self.cruz_cnt}")

        QTimer.singleShot(1150, _on_finish)
