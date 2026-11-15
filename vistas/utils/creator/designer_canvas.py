# -*- coding: utf-8 -*-
"""Paleta Drag & Drop y Lienzo Visual interactivo con guías inteligentes de alineación."""

import json

from PyQt6.QtCore import QMimeData, QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
)

from vistas.utils.creator.helpers import WIDGET_PALETTE


class PaletteDragList(QListWidget):
    """Lista de widgets que permite arrastrar hacia el lienzo o hacer doble clic."""

    itemActivatedCustom = pyqtSignal(str, str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        for label, w_type, icon_lbl, w, h in WIDGET_PALETTE:
            it = QListWidgetItem(icon_lbl)
            it.setData(Qt.ItemDataRole.UserRole, (w_type, label, w, h))
            self.addItem(it)
        self.itemDoubleClicked.connect(self._on_double)

    def _on_double(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.itemActivatedCustom.emit(*data)

    def startDrag(self, _actions):
        item = self.currentItem()
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        mime = QMimeData()
        mime.setText(json.dumps({"tipo": data[0], "label": data[1], "w": data[2], "h": data[3]}))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class CanvasWidgetItem(QFrame):
    """Wrapper arrastrable y redimensionable sobre el lienzo visual."""

    selected = pyqtSignal(int)
    geometryChangedCustom = pyqtSignal(int, int, int, int, int)

    def __init__(self, idx: int, spec: dict, is_selected: bool, canvas_ref=None):
        super().__init__(canvas_ref)
        self.idx = idx
        self.spec = spec
        self.canvas_ref = canvas_ref
        self.is_selected = is_selected
        self._drag_start: QPoint | None = None
        self._resizing = False
        self._orig_geo = QRect()

        self.setGeometry(spec.get("x", 16), spec.get("y", 16), spec.get("w", 200), spec.get("h", 34))
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 3, 4, 3)
        lay.setSpacing(0)

        t = spec["tipo"]
        txt = spec.get("texto", "")
        fg = spec.get("fg_color") or "#ffffff"
        bg = spec.get("bg_color") or ""

        if t == "QLabel_title":
            w = QLabel(txt)
            w.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {fg}; border: none; background: transparent;")
        elif t == "QLabel":
            w = QLabel(txt)
            w.setStyleSheet(f"font-size: 12px; color: {fg}; border: none; background: transparent;")
        elif t == "QPushButton":
            w = QPushButton(txt)
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            w.setStyleSheet(f"background: {bg or '#4f46e5'}; color: {fg}; border-radius: 5px; font-size: 11px; padding: 4px;")
        elif t == "QLineEdit":
            w = QLineEdit(txt)
            w.setPlaceholderText(spec.get("placeholder", ""))
            w.setStyleSheet(f"background: {bg or '#181b28'}; color: {fg}; border: 1px solid #38405e; border-radius: 4px; padding: 3px;")
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QTextEdit":
            w = QTextEdit(txt)
            w.setStyleSheet(f"background: {bg or '#181b28'}; color: {fg}; border: 1px solid #38405e; border-radius: 4px;")
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QComboBox":
            w = QComboBox()
            w.addItems([txt or "Opción 1", "Opción 2"])
            w.setStyleSheet(f"background: {bg or '#181b28'}; color: {fg}; border: 1px solid #38405e;")
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QCheckBox":
            w = QCheckBox(txt)
            w.setStyleSheet(f"color: {fg};")
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QSpinBox":
            w = QSpinBox()
            w.setStyleSheet(f"background: {bg or '#181b28'}; color: {fg}; border: 1px solid #38405e;")
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QSlider":
            w = QSlider(Qt.Orientation.Horizontal)
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QTableWidget":
            w = QTableWidget(2, 3)
            w.setStyleSheet(f"background: {bg or '#181b28'}; color: {fg}; gridline-color: #2e344d;")
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QGroupBox":
            w = QGroupBox(txt or "Grupo")
            w.setStyleSheet(f"color: {fg}; border: 1px solid #38405e; border-radius: 5px;")
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QProgressBar":
            w = QProgressBar()
            w.setValue(50)
            w.setStyleSheet(f"color: {fg};")
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "SubmoduleSlot":
            target = spec.get("target_sub", "Sin asignar")
            w = QLabel(f"🧩 Submódulo: {target}\n({txt})")
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            w.setStyleSheet(f"color: {fg}; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        else:
            w = QLabel(txt)
            w.setStyleSheet(f"color: {fg};")
        lay.addWidget(w)

        self.handle = QFrame(self)
        self.handle.setFixedSize(12, 12)
        self.handle.setStyleSheet("background-color: #818cf8; border: 1px solid #ffffff; border-radius: 2px;")
        self.handle.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.set_selected_visual(is_selected)

    def set_selected_visual(self, selected: bool):
        self.is_selected = selected
        border = "2px solid #6366f1" if selected else "1px dashed #3b4261"
        bg = "rgba(99, 102, 241, 0.14)" if selected else "rgba(30, 34, 51, 0.45)"
        self.setStyleSheet(f"CanvasWidgetItem {{ border: {border}; background: {bg}; border-radius: 5px; }}")
        self.handle.setVisible(selected)
        self.handle.move(max(0, self.width() - 12), max(0, self.height() - 12))
        if selected:
            self.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "handle"):
            self.handle.move(max(0, self.width() - 12), max(0, self.height() - 12))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._orig_geo = self.geometry()
            self._resizing = (
                event.position().x() >= self.width() - 16
                and event.position().y() >= self.height() - 16
            )
            self.selected.emit(self.idx)
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_start is None:
            return
        delta = event.globalPosition().toPoint() - self._drag_start
        if self._resizing:
            nw = max(48, round((self._orig_geo.width() + delta.x()) / 8) * 8)
            nh = max(24, round((self._orig_geo.height() + delta.y()) / 8) * 8)
            self.resize(nw, nh)
        else:
            nx = max(0, round((self._orig_geo.x() + delta.x()) / 8) * 8)
            ny = max(0, round((self._orig_geo.y() + delta.y()) / 8) * 8)
            if self.canvas_ref:
                nx, ny = self.canvas_ref.compute_snap_guides(self.idx, nx, ny, self.width(), self.height())
            self.move(nx, ny)
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_start is not None:
            self._drag_start = None
            if self.canvas_ref:
                self.canvas_ref.clear_guides()
            g = self.geometry()
            self.geometryChangedCustom.emit(self.idx, g.x(), g.y(), g.width(), g.height())
            event.accept()


class DesignCanvas(QFrame):
    """Lienzo interactivo con cuadrícula, Drag & Drop y guías inteligentes de alineación."""

    widgetDropped = pyqtSignal(str, str, int, int, int, int)
    widgetSelected = pyqtSignal(int)
    widgetMovedResized = pyqtSignal(int, int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(520, 380)
        self.setStyleSheet("DesignCanvas { background-color: #0e1018; border: 1px solid #2e344d; border-radius: 6px; }")
        self._items_widgets: list[CanvasWidgetItem] = []
        self._guide_x: int | None = None
        self._guide_y: int | None = None

    def compute_snap_guides(self, active_idx: int, nx: int, ny: int, w: int, h: int) -> tuple[int, int]:
        """Calcula snap a ±6px respecto a bordes/centros de otros widgets y activa guías visuales."""
        gx, gy = None, None
        cx = nx + w // 2
        cy = ny + h // 2
        for i, cw in enumerate(self._items_widgets):
            if i == active_idx:
                continue
            og = cw.geometry()
            if abs(nx - og.x()) <= 6:
                nx, gx = og.x(), og.x()
            elif abs(cx - og.center().x()) <= 6:
                nx, gx = og.center().x() - w // 2, og.center().x()
            if abs(ny - og.y()) <= 6:
                ny, gy = og.y(), og.y()
            elif abs(cy - og.center().y()) <= 6:
                ny, gy = og.center().y() - h // 2, og.center().y()
        self._guide_x, self._guide_y = gx, gy
        self.update()
        return max(0, nx), max(0, ny)

    def clear_guides(self):
        if self._guide_x is not None or self._guide_y is not None:
            self._guide_x = None
            self._guide_y = None
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(QColor(255, 255, 255, 16))
        pen.setWidth(1)
        painter.setPen(pen)
        step = 16
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)

        # Guías inteligentes cian
        if self._guide_x is not None or self._guide_y is not None:
            gpen = QPen(QColor("#22d3ee"))
            gpen.setStyle(Qt.PenStyle.DashLine)
            gpen.setWidth(1)
            painter.setPen(gpen)
            if self._guide_x is not None:
                painter.drawLine(self._guide_x, 0, self._guide_x, self.height())
            if self._guide_y is not None:
                painter.drawLine(0, self._guide_y, self.width(), self._guide_y)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        try:
            payload = json.loads(event.mimeData().text())
            pos = event.position().toPoint()
            x = max(0, round(pos.x() / 8) * 8)
            y = max(0, round(pos.y() / 8) * 8)
            self.widgetDropped.emit(
                payload["tipo"],
                payload["label"],
                x,
                y,
                int(payload.get("w", 180)),
                int(payload.get("h", 32)),
            )
            event.acceptProposedAction()
        except Exception:
            pass

    def update_selection_only(self, selected_idx: int):
        for i, cw in enumerate(self._items_widgets):
            cw.set_selected_visual(i == selected_idx)

    def render_items(self, specs: list[dict], selected_idx: int):
        for w in self._items_widgets:
            w.deleteLater()
        self._items_widgets.clear()
        max_x, max_y = 520, 380
        for i, sp in enumerate(specs):
            cw = CanvasWidgetItem(i, sp, i == selected_idx, self)
            cw.selected.connect(self.widgetSelected.emit)
            cw.geometryChangedCustom.connect(self.widgetMovedResized.emit)
            cw.show()
            self._items_widgets.append(cw)
            max_x = max(max_x, sp.get("x", 0) + sp.get("w", 100) + 40)
            max_y = max(max_y, sp.get("y", 0) + sp.get("h", 40) + 40)
        self.setMinimumSize(max_x, max_y)
