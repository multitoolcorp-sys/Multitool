"""
molecular_canvas.py - Lienzo Gráfico 2D Interactivo de Estructuras Moleculares con QPainter
Permite visualizar átomos (CPK colors), enlaces químicos (simples, dobles, triples),
rotación interactiva, zoom, paneo y generación procedural para fórmulas arbitrarias.
"""

import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPointF, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QRadialGradient,
    QPainterPath
)

from .quimica_data import CPK_COLORS, ESTRUCTURAS_PREDEFINIDAS, SIMBOLO_A_ELEM
from .quimica_math import parse_formula


class MolecularCanvas(QWidget):
    """Lienzo 2D interactivo para visualización molecular en tiempo real."""
    atomHovered = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 260)
        self.setMouseTracking(True)

        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.angle_deg = 0.0
        self.auto_rotate = False

        self._last_mouse_pos = None
        self._hovered_atom = None

        self.atomos = []
        self.enlaces = []
        self.formula_actual = "H2O"

        # Timer de auto-rotación suave
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(30)
        self.anim_timer.timeout.connect(self._step_rotation)

        self.cargar_molecula("H2O")

    def toggle_auto_rotate(self):
        self.auto_rotate = not self.auto_rotate
        if self.auto_rotate:
            self.anim_timer.start()
        else:
            self.anim_timer.stop()
        return self.auto_rotate

    def reset_view(self):
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.angle_deg = 0.0
        self.update()

    def _step_rotation(self):
        self.angle_deg = (self.angle_deg + 1.2) % 360.0
        self.update()

    def cargar_molecula(self, formula_str):
        """Carga una molécula desde recetas predefinidas o genera una estructura procedural."""
        formula_clean = formula_str.strip()
        self.formula_actual = formula_clean
        
        # 1. Comprobar si existe receta exacta
        if formula_clean in ESTRUCTURAS_PREDEFINIDAS:
            data = ESTRUCTURAS_PREDEFINIDAS[formula_clean]
            self.atomos = [dict(a) for a in data["atomos"]]
            self.enlaces = list(data["enlaces"])
            self.update()
            return

        # 2. Generar estructura procedural para fórmulas arbitrarias
        try:
            counts = parse_formula(formula_clean)
            self._generar_estructura_procedural(counts)
        except Exception:
            # Fallback simple
            self.atomos = [{"elem": "C", "x": 0, "y": 0, "r": 18}]
            self.enlaces = []
            
        self.update()

    def _generar_estructura_procedural(self, counts):
        """Genera una disposición 2D armónica para fórmulas no catalogadas."""
        self.atomos = []
        self.enlaces = []

        # Ordenar: átomos pesados/centrales primero (C, N, P, S, Fe, Ca...), luego O, luego H
        def _prioridad(elem):
            if elem in ("C", "Si", "Fe", "Cu", "Zn", "Ca", "Na", "K", "Mg", "Al"):
                return 0
            if elem in ("N", "P", "S"):
                return 1
            if elem in ("O", "Cl", "Br", "I", "F"):
                return 2
            return 3

        elementos_ordenados = []
        for el, cnt in counts.items():
            for _ in range(int(cnt)):
                elementos_ordenados.append(el)
        elementos_ordenados.sort(key=_prioridad)

        total_atomos = len(elementos_ordenados)
        if total_atomos == 0:
            return

        if total_atomos == 1:
            self.atomos.append({"elem": elementos_ordenados[0], "x": 0, "y": 0, "r": 18})
            return

        if total_atomos == 2:
            self.atomos.append({"elem": elementos_ordenados[0], "x": -45, "y": 0, "r": 16})
            self.atomos.append({"elem": elementos_ordenados[1], "x": 45, "y": 0, "r": 16})
            self.enlaces.append((0, 1, 1))
            return

        # Átomo central y orbitales en anillo/estrella
        centro = elementos_ordenados[0]
        self.atomos.append({"elem": centro, "x": 0, "y": 0, "r": 18})

        perifericos = elementos_ordenados[1:]
        num_perif = len(perifericos)
        radio_dist = 60 if num_perif <= 6 else 85

        for i, elem in enumerate(perifericos):
            angulo = (2 * math.pi / num_perif) * i
            px = radio_dist * math.cos(angulo)
            py = radio_dist * math.sin(angulo)
            r_atom = 12 if elem == "H" else 15
            self.atomos.append({"elem": elem, "x": px, "y": py, "r": r_atom})
            self.enlaces.append((0, i + 1, 1))

    # --- Renderizado con QPainter ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0 + self.pan_x
        cy = h / 2.0 + self.pan_y

        # Fondo con cuadrícula sutil
        painter.fillRect(0, 0, w, h, QColor("#121218"))
        self._dibujar_cuadricula(painter, w, h)

        # Aplicar Transformación (Paneo, Rotación, Zoom)
        painter.save()
        painter.translate(cx, cy)
        painter.scale(self.zoom, self.zoom)
        painter.rotate(self.angle_deg)

        # 1. Dibujar Enlaces Químicos (Bonds)
        pen_bond = QPen(QColor(180, 185, 200, 200), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bond)

        for b_from, b_to, orden in self.enlaces:
            if b_from < len(self.atomos) and b_to < len(self.atomos):
                a1 = self.atomos[b_from]
                a2 = self.atomos[b_to]
                self._dibujar_enlace(painter, a1["x"], a1["y"], a2["x"], a2["y"], orden)

        # 2. Dibujar Átomos (Spheres / CPK)
        font_atom = QFont("Inter", 9, QFont.Weight.Bold)
        painter.setFont(font_atom)

        for i, atom in enumerate(self.atomos):
            ax = atom["x"]
            ay = atom["y"]
            ar = atom.get("r", 15)
            elem = atom["elem"]

            # Color CPK del elemento
            hex_color = CPK_COLORS.get(elem, "#9E9E9E")
            base_col = QColor(hex_color)

            # Gradiente radial con sombra e iluminación especular 3D
            grad = QRadialGradient(ax - ar * 0.35, ay - ar * 0.35, ar * 1.3)
            grad.setColorAt(0.0, base_col.lighter(170))
            grad.setColorAt(0.6, base_col)
            grad.setColorAt(1.0, base_col.darker(160))

            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(base_col.darker(190), 1.5))
            painter.drawEllipse(QPointF(ax, ay), ar, ar)

            # Símbolo Químico
            text_color = QColor("#000000") if elem in ("H", "S", "Al", "Na", "K", "Mg") else QColor("#FFFFFF")
            painter.setPen(text_color)
            painter.drawText(int(ax - ar), int(ay - ar), int(ar * 2), int(ar * 2), Qt.AlignmentFlag.AlignCenter, elem)

        painter.restore()

        # Marca de agua / Título de la molécula
        painter.setPen(QColor(255, 255, 255, 180))
        painter.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        painter.drawText(15, 25, f"Molécula: {self.formula_actual} ({len(self.atomos)} átomos)")

    def _dibujar_cuadricula(self, painter, w, h):
        pen_grid = QPen(QColor(255, 255, 255, 8), 1, Qt.PenStyle.DotLine)
        painter.setPen(pen_grid)
        step = 30
        for x in range(0, w, step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            painter.drawLine(0, y, w, y)

    def _dibujar_enlace(self, painter, x1, y1, x2, y2, orden):
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist == 0: return

        # Vector perpendicular
        px = -dy / dist
        py = dx / dist

        if orden == 1:
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        elif orden == 2:
            offset = 3.5
            painter.drawLine(int(x1 + px * offset), int(y1 + py * offset), int(x2 + px * offset), int(y2 + py * offset))
            painter.drawLine(int(x1 - px * offset), int(y1 - py * offset), int(x2 - px * offset), int(y2 - py * offset))
        elif orden >= 3:
            offset = 5.0
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.drawLine(int(x1 + px * offset), int(y1 + py * offset), int(x2 + px * offset), int(y2 + py * offset))
            painter.drawLine(int(x1 - px * offset), int(y1 - py * offset), int(x2 - px * offset), int(y2 - py * offset))

    # --- Interacción del Mouse ---
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom = min(3.5, self.zoom * 1.12)
        else:
            self.zoom = max(0.35, self.zoom / 1.12)
        self.update()

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self._last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self._last_mouse_pos and event.buttons() & Qt.MouseButton.LeftButton:
            dx = event.pos().x() - self._last_mouse_pos.x()
            dy = event.pos().y() - self._last_mouse_pos.y()
            self.pan_x += dx
            self.pan_y += dy
            self._last_mouse_pos = event.pos()
            self.update()
        elif self._last_mouse_pos and event.buttons() & Qt.MouseButton.RightButton:
            dx = event.pos().x() - self._last_mouse_pos.x()
            self.angle_deg = (self.angle_deg + dx * 0.8) % 360.0
            self._last_mouse_pos = event.pos()
            self.update()
