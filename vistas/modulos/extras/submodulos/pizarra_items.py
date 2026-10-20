import math
from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsTextItem, QDialog, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QGridLayout, QColorDialog
)
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QFont, QColor, QPen, QBrush

# ── Colores por defecto de la paleta ──────────────────────────
DEFAULT_COLORS = [
    "#FFFFFF", "#000000", "#FF3B30", "#FF9500", "#FFCC00",
    "#34C759", "#007AFF", "#5856D6", "#FF2D55", "#AF52DE",
    "#8E8E93", "#636366", "#3A3A3C", "#FF6B6B", "#4ECDC4",
]


# ──────────────────────────────────────────────
#  HANDLE DE REDIMENSIÓN / ROTACIÓN
# ──────────────────────────────────────────────
class Handle(QGraphicsItem):
    SIZE = 12

    def __init__(self, parent_smart, role):
        super().__init__(parent_smart)
        self.parent_smart = parent_smart
        self.role = role
        self.setZValue(10)
        self.setCursor(self._cursor_for_role(role))
        self.setAcceptHoverEvents(True)

    def _cursor_for_role(self, role):
        m = {
            'tl': Qt.CursorShape.SizeFDiagCursor, 'br': Qt.CursorShape.SizeFDiagCursor,
            'tr': Qt.CursorShape.SizeBDiagCursor, 'bl': Qt.CursorShape.SizeBDiagCursor,
            'tm': Qt.CursorShape.SizeVerCursor,   'bm': Qt.CursorShape.SizeVerCursor,
            'lm': Qt.CursorShape.SizeHorCursor,   'rm': Qt.CursorShape.SizeHorCursor,
            'rot': Qt.CursorShape.CrossCursor,
            'move': Qt.CursorShape.SizeAllCursor,
        }
        return m.get(role, Qt.CursorShape.PointingHandCursor)

    def boundingRect(self):
        h = self.SIZE
        if self.role == 'move':
            return QRectF(-h, -h/2, h*2, h)
        return QRectF(-h/2, -h/2, h, h)

    def paint(self, painter, option, widget):
        if self.role == 'move':
            painter.setBrush(QBrush(QColor("#10B981")))
            painter.setPen(QPen(Qt.GlobalColor.white, 1.2))
            painter.drawRoundedRect(self.boundingRect().adjusted(1, 1, -1, -1), 3, 3)
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, "✥ Mover")
            return
        color = QColor("#F59E0B") if self.role == 'rot' else QColor("#6366F1")
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.GlobalColor.white, 1.5))
        painter.drawEllipse(self.boundingRect().adjusted(1, 1, -1, -1))

    def mousePressEvent(self, event):
        if self.role == 'move':
            self._drag_start_pos = event.scenePos()
            self._item_start_pos = self.parent_smart.pos()
            event.accept()
            return
        event.accept()

    def mouseMoveEvent(self, event):
        if self.role == 'move':
            delta = event.scenePos() - self._drag_start_pos
            self.parent_smart.setPos(self._item_start_pos + delta)
            event.accept()
            return
        elif self.role == 'rot':
            self.parent_smart._do_rotate(event.scenePos())
        else:
            self.parent_smart._do_resize(self.role, event.scenePos())
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()


# ──────────────────────────────────────────────
#  WRAPPER INTELIGENTE
# ──────────────────────────────────────────────
class SmartItem(QGraphicsItem):
    MIN_SIZE = 15

    def __init__(self, child):
        super().__init__()
        self.child = child
        self.child.setParentItem(self)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self._handles = {}
        for role in ('tl', 'tr', 'bl', 'br', 'tm', 'bm', 'lm', 'rm', 'rot', 'move'):
            h = Handle(self, role)
            h.hide()
            self._handles[role] = h
        self._update_handles()

    def mouseDoubleClickEvent(self, event):
        if isinstance(self.child, QGraphicsTextItem):
            self.child.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
            self.child.setFocus()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if isinstance(self.child, QGraphicsTextItem) and not self.child.hasFocus():
            self.child.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        super().mousePressEvent(event)

    def boundingRect(self):
        return self.child.boundingRect().adjusted(-8, -8, 8, 8)

    def paint(self, painter, option, widget):
        visible = self.isSelected()
        for h in self._handles.values():
            h.setVisible(visible)
        if visible:
            painter.setPen(QPen(QColor("#6366F1"), 1, Qt.PenStyle.DashLine))
            painter.drawRect(self.child.boundingRect())

    def _update_handles(self):
        r = self.child.boundingRect()
        cx, cy = r.center().x(), r.center().y()
        pos = {
            'tl': (r.left(),   r.top()),    'tr': (r.right(),  r.top()),
            'bl': (r.left(),   r.bottom()), 'br': (r.right(),  r.bottom()),
            'tm': (cx,         r.top()),    'bm': (cx,         r.bottom()),
            'lm': (r.left(),   cy),         'rm': (r.right(),  cy),
            'rot': (cx,        r.top() - 30),
            'move': (cx,       r.bottom() + 16),
        }
        for role, (px, py) in pos.items():
            self._handles[role].setPos(px, py)

    # ── Resize  ────────────────────────────────────────────────
    def _do_resize(self, role, scene_pos):
        """
        Resize correcto sin saltos:
        - El borde opuesto permanece fijo en coordenadas de escena.
        - Solo se mueve el lado arrastrado.
        """
        local = self.mapFromScene(scene_pos)
        child = self.child

        # Para ítems con setRect (rect/ellipse)
        if hasattr(child, 'rect') and callable(child.rect):
            r = QRectF(child.rect())

            # Guardamos la esquina fija ANTES de cambiar el rect
            fixed_scene = None

            if 't' in role and 'b' not in role:
                # Borde superior: la esquina fija es la inferior en ESCENA
                fixed_scene = self.mapToScene(QPointF(r.left(), r.bottom()))
                new_top = local.y()
                if r.bottom() - new_top < self.MIN_SIZE:
                    return
                r.setTop(new_top)

            if 'b' in role and 't' not in role:
                new_bot = local.y()
                if new_bot - r.top() < self.MIN_SIZE:
                    return
                r.setBottom(new_bot)

            if 'l' in role and 'r' not in role:
                fixed_scene = self.mapToScene(QPointF(r.right(), r.top()))
                new_left = local.x()
                if r.right() - new_left < self.MIN_SIZE:
                    return
                r.setLeft(new_left)

            if 'r' in role and 'l' not in role:
                new_right = local.x()
                if new_right - r.left() < self.MIN_SIZE:
                    return
                r.setRight(new_right)

            # Esquinas (ej tl, br, tr, bl)
            if 't' in role and 'l' in role:
                fixed_scene = self.mapToScene(QPointF(r.right(), r.bottom()))
                if r.right() - local.x() < self.MIN_SIZE or r.bottom() - local.y() < self.MIN_SIZE:
                    return
                r.setTopLeft(local)
            elif 't' in role and 'r' in role:
                fixed_scene = self.mapToScene(QPointF(r.left(), r.bottom()))
                if local.x() - r.left() < self.MIN_SIZE or r.bottom() - local.y() < self.MIN_SIZE:
                    return
                r.setTopRight(local)
            elif 'b' in role and 'l' in role:
                fixed_scene = self.mapToScene(QPointF(r.right(), r.top()))
                if r.right() - local.x() < self.MIN_SIZE or local.y() - r.top() < self.MIN_SIZE:
                    return
                r.setBottomLeft(local)
            elif 'b' in role and 'r' in role:
                fixed_scene = self.mapToScene(QPointF(r.left(), r.top()))
                if local.x() - r.left() < self.MIN_SIZE or self.MIN_SIZE > local.y() - r.top():
                    return
                r.setBottomRight(local)

            child.setRect(r)

            # Universal: mover SmartItem de forma que la esquina opuesta al drag no cambie en la escena
            if fixed_scene is not None and role not in ('bm', 'rm'):
                new_pos_of_fixed = self.mapToScene(
                    self._get_opposite_local(role, r)
                )
                delta = fixed_scene - new_pos_of_fixed
                self.moveBy(delta.x(), delta.y())

        self._update_handles()
        self.update()

    def _get_opposite_local(self, role, r):
        """Devuelve el punto opuesto al handle arrastrado, en coordenadas locales."""
        if role == 'tm': return QPointF(r.center().x(), r.bottom())
        if role == 'bm': return QPointF(r.center().x(), r.top())
        if role == 'lm': return QPointF(r.right(),      r.center().y())
        if role == 'rm': return QPointF(r.left(),       r.center().y())
        if role == 'tl': return r.bottomRight()
        if role == 'tr': return r.bottomLeft()
        if role == 'bl': return r.topRight()
        if role == 'br': return r.topLeft()
        return r.center()

    # ── Rotación ──────────────────────────────
    def _do_rotate(self, scene_pos):
        center = self.mapToScene(self.child.boundingRect().center())
        dx = scene_pos.x() - center.x()
        dy = scene_pos.y() - center.y()
        angle = math.degrees(math.atan2(dy, dx)) + 90
        self.setTransformOriginPoint(self.child.boundingRect().center())
        self.setRotation(angle)


# ──────────────────────────────────────────────
#  DIÁLOGO DE PALETA DE COLORES
# ──────────────────────────────────────────────
class ColorPaletteDialog(QDialog):
    def __init__(self, parent, colores, color_actual, saved_colors):
        super().__init__(parent)
        self.setWindowTitle("Paleta de Colores")
        self.setFixedSize(380, 290)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colores['bg_secundario']};
                border-radius: 12px;
            }}
            QLabel {{
                color: white;
                font-family: 'Outfit';
            }}
        """)
        self.selected_color = color_actual
        self.saved_colors = list(saved_colors)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)

        lbl = QLabel("🎨 Colores Rápidos")
        lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        lay.addWidget(lbl)

        # Grid de colores
        grid = QGridLayout()
        grid.setSpacing(6)
        all_colors = DEFAULT_COLORS + [c for c in saved_colors if c not in DEFAULT_COLORS]
        for i, hex_c in enumerate(all_colors[:20]):
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {hex_c}; 
                    border-radius: 14px; 
                    border: 2px solid {'white' if QColor(hex_c) == color_actual else 'rgba(255,255,255,0.1)'};
                }}
                QPushButton:hover {{
                    border: 2px solid white;
                }}
            """)
            btn.clicked.connect(lambda _, c=hex_c: self._pick(c))
            grid.addWidget(btn, i // 10, i % 10)
        lay.addLayout(grid)

        # Color personalizado
        btn_custom = QPushButton("✏️ Color Personalizado")
        btn_custom.setStyleSheet(f"""
            QPushButton {{
                background: {colores['bg_terciario']};
                color: white;
                border-radius: 8px;
                padding: 8px;
                border: 1px solid rgba(255,255,255,0.05);
                font-family: 'Outfit';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.08);
            }}
        """)
        btn_custom.clicked.connect(self._pick_custom)
        lay.addWidget(btn_custom)

        # Preview y OK
        h = QHBoxLayout()
        self.preview = QLabel()
        self.preview.setFixedSize(40, 40)
        self._update_preview()
        h.addWidget(self.preview)
        h.addStretch()
        btn_ok = QPushButton("✓ Aceptar")
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background: {colores['acento']};
                color: white;
                border-radius: 8px;
                padding: 8px 20px;
                border: none;
                font-family: 'Outfit';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {colores['acento_hover']};
            }}
        """)
        btn_ok.clicked.connect(self.accept)
        h.addWidget(btn_ok)
        lay.addLayout(h)

    def _pick(self, hex_c):
        self.selected_color = QColor(hex_c)
        self._update_preview()

    def _pick_custom(self):
        c = QColorDialog.getColor(self.selected_color, self)
        if c.isValid():
            self.selected_color = c
            hex_c = c.name()
            if hex_c not in self.saved_colors:
                self.saved_colors.append(hex_c)
            self._update_preview()

    def _update_preview(self):
        self.preview.setStyleSheet(
            f"background:{self.selected_color.name()}; border-radius:8px; border:2px solid white;"
        )
