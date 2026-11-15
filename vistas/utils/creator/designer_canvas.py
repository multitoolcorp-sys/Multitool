# -*- coding: utf-8 -*-
"""Paleta Drag & Drop y Lienzo Visual interactivo para el Modo Creador."""

import json

from PyQt6.QtCore import QMimeData, QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
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

    def __init__(self, idx: int, spec: dict, is_selected: bool, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.spec = spec
        self.is_selected = is_selected
        self._drag_start: QPoint | None = None
        self._resizing = False
        self._orig_geo = QRect()

        self.setGeometry(spec.get("x", 16), spec.get("y", 16), spec.get("w", 200), spec.get("h", 34))
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        border = "2px solid #6366f1" if is_selected else "1px dashed #3b4261"
        bg = "rgba(99, 102, 241, 0.12)" if is_selected else "rgba(30, 34, 51, 0.45)"
        self.setStyleSheet(f"CanvasWidgetItem {{ border: {border}; background: {bg}; border-radius: 5px; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 3, 4, 3)
        lay.setSpacing(0)

        t = spec["tipo"]
        txt = spec.get("texto", "")
        if t == "QLabel_title":
            w = QLabel(txt)
            w.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff; border: none; background: transparent;")
        elif t == "QLabel":
            w = QLabel(txt)
            w.setStyleSheet("font-size: 12px; color: #e2e8f0; border: none; background: transparent;")
        elif t == "QPushButton":
            w = QPushButton(txt)
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            w.setStyleSheet("background: #4f46e5; color: #ffffff; border-radius: 5px; font-size: 11px; padding: 4px;")
        elif t == "QLineEdit":
            w = QLineEdit(txt)
            w.setPlaceholderText(spec.get("placeholder", ""))
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QTextEdit":
            w = QTextEdit(txt)
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QComboBox":
            w = QComboBox()
            w.addItems([txt or "Opción 1", "Opción 2"])
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QCheckBox":
            w = QCheckBox(txt)
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "QProgressBar":
            w = QProgressBar()
            w.setValue(50)
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif t == "SubmoduleSlot":
            target = spec.get("target_sub", "Sin asignar")
            w = QLabel(f"🧩 Submódulo: {target}\n({txt})")
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            w.setStyleSheet("color: #a5b4fc; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        else:
            w = QLabel(txt)
        lay.addWidget(w)

        if is_selected:
            self.handle = QFrame(self)
            self.handle.setFixedSize(10, 10)
            self.handle.setStyleSheet("background-color: #818cf8; border: 1px solid #ffffff; border-radius: 2px;")
            self.handle.move(max(0, self.width() - 10), max(0, self.height() - 10))
            self.handle.setCursor(Qt.CursorShape.SizeFDiagCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.idx)
            self._drag_start = event.globalPosition().toPoint()
            self._orig_geo = self.geometry()
            self._resizing = (
                event.position().x() >= self.width() - 14
                and event.position().y() >= self.height() - 14
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_start is None:
            return
        delta = event.globalPosition().toPoint() - self._drag_start
        if self._resizing:
            nw = max(60, round((self._orig_geo.width() + delta.x()) / 8) * 8)
            nh = max(24, round((self._orig_geo.height() + delta.y()) / 8) * 8)
            self.resize(nw, nh)
            if hasattr(self, "handle"):
                self.handle.move(max(0, nw - 10), max(0, nh - 10))
        else:
            nx = max(0, round((self._orig_geo.x() + delta.x()) / 8) * 8)
            ny = max(0, round((self._orig_geo.y() + delta.y()) / 8) * 8)
            self.move(nx, ny)
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_start is not None:
            self._drag_start = None
            g = self.geometry()
            self.geometryChangedCustom.emit(self.idx, g.x(), g.y(), g.width(), g.height())
            event.accept()


class DesignCanvas(QFrame):
    """Lienzo interactivo con cuadrícula y soporte Drag & Drop desde la paleta."""

    widgetDropped = pyqtSignal(str, str, int, int, int, int)
    widgetSelected = pyqtSignal(int)
    widgetMovedResized = pyqtSignal(int, int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(520, 380)
        self.setStyleSheet("DesignCanvas { background-color: #0e1018; border: 1px solid #2e344d; border-radius: 6px; }")
        self._items_widgets: list[CanvasWidgetItem] = []

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
