import os
import platform
import math
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGraphicsView, QGraphicsScene, QGraphicsPathItem,
    QColorDialog, QInputDialog, QGraphicsTextItem, QFileDialog,
    QGraphicsPixmapItem, QGraphicsLineItem, QGraphicsRectItem,
    QGraphicsEllipseItem, QMenu, QGraphicsItem, QSpinBox, QSlider,
    QDialog, QGridLayout, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QPointF, QLineF, QRectF, QSizeF, QSize
from PyQt6.QtGui import (
    QFont, QColor, QPainterPath, QPen, QPixmap, QPainter,
    QTransform, QBrush, QKeySequence, QShortcut, QPainterPathStroker
)

from .pizarra_items import DEFAULT_COLORS, Handle, SmartItem, ColorPaletteDialog


# ──────────────────────────────────────────────
#  VISTA
# ──────────────────────────────────────────────
class PizarraView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.undo_stack = []
        self.redo_stack = []
        self._zoom_level = 1.0

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor("#121218"))
        
        # Infinite dot grid
        grid_size = 28
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 18)))
        
        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                painter.drawEllipse(QPointF(x, y), 1.0, 1.0)
                y += grid_size
            x += grid_size

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        # Ignorar si es el cursor visual
        if hasattr(self.scene(), "_eraser_cursor_item") and item == self.scene()._eraser_cursor_item:
            item = None
        # Subir al nivel del SmartItem si es un hijo lo que se clicó
        while item and item.parentItem() and isinstance(item.parentItem(), SmartItem):
            item = item.parentItem()

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#1E1E2E;color:white;border:1px solid #444;padding:4px;}"
            "QMenu::item:selected{background:#6366F1;}"
        )
        if item:
            a_del   = menu.addAction("🗑️ Eliminar")
            a_front = menu.addAction("⏫ Traer al Frente")
            a_back  = menu.addAction("⏬ Enviar al Fondo")
            a_rot0  = menu.addAction("🔄 Reset Rotación")
            act = menu.exec(event.globalPos())
            if act == a_del:     self.scene().removeItem(item)
            elif act == a_front: item.setZValue(item.zValue() + 1)
            elif act == a_back:  item.setZValue(item.zValue() - 1)
            elif act == a_rot0:  item.setRotation(0)
        else:
            a_clr = menu.addAction("🧹 Limpiar Todo")
            a_rst = menu.addAction("🎯 Reset Vista")
            act = menu.exec(event.globalPos())
            if act == a_clr: 
                # Limpiar todo excepto el cursor
                for it in self.scene().items():
                    if it != getattr(self.scene(), "_eraser_cursor_item", None):
                        self.scene().removeItem(it)
                self.undo_stack.clear()
                self.redo_stack.clear()
            elif act == a_rst: self.resetTransform(); self._zoom_level = 1.0

    def keyPressEvent(self, event):
        mod = event.modifiers()
        key = event.key()
        if mod == Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Equal or key == Qt.Key.Key_Plus:
                self.zoom_in(); return
            elif key == Qt.Key.Key_Minus:
                self.zoom_out(); return
            elif key == Qt.Key.Key_0:
                self.resetTransform(); self._zoom_level = 1.0; return
            elif key == Qt.Key.Key_Z:
                self.undo(); return
            elif key == Qt.Key.Key_Y:
                self.redo(); return
            elif key == Qt.Key.Key_S:
                if hasattr(self.parent(), 'guardar_imagen'):
                    self.parent().guardar_imagen()
                return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def zoom_in(self):
        if self._zoom_level < 8.0:
            self.scale(1.25, 1.25)
            self._zoom_level *= 1.25

    def zoom_out(self):
        if self._zoom_level > 0.1:
            self.scale(0.8, 0.8)
            self._zoom_level *= 0.8

    def undo(self):
        if self.undo_stack:
            it = self.undo_stack.pop(); self.redo_stack.append(it); it.hide()

    def redo(self):
        if self.redo_stack:
            it = self.redo_stack.pop(); self.undo_stack.append(it); it.show()


# ──────────────────────────────────────────────
#  ESCENA
# ──────────────────────────────────────────────
class DibujoScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.modo_forma = "lapiz"
        self.color_actual = QColor(Qt.GlobalColor.white)
        self.grosor = 3
        self.grosor_borrador = 20
        self.dibujando = False
        self.start_pos = QPointF(0, 0)
        self.curr = None
        self._modo_texto_click = False
        self._eraser_cursor_item = QGraphicsEllipseItem()
        self._eraser_cursor_item.setPen(QPen(Qt.GlobalColor.white, 1, Qt.PenStyle.DashLine))
        self._eraser_cursor_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._eraser_cursor_item.setZValue(1000)
        self._eraser_cursor_item.hide()
        self.addItem(self._eraser_cursor_item)

    def activar_modo_texto(self):
        self._modo_texto_click = True
        self.modo_forma = "texto_click"

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Modo texto por clic
            if self._modo_texto_click:
                self._modo_texto_click = False
                self.modo_forma = "seleccion"
                pos = event.scenePos()
                t, ok = QInputDialog.getText(None, "Texto", "Contenido:")
                if ok and t:
                    it = QGraphicsTextItem(t)
                    it.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
                    it.setDefaultTextColor(self.color_actual)
                    it.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
                    smart = SmartItem(it)
                    smart.setPos(pos)
                    self.addItem(smart)
                return

            if self.modo_forma == "seleccion":
                super().mousePressEvent(event); return

            if self.modo_forma == "borrador":
                self._erase_at(event.scenePos())
                self.dibujando = True
                return

            self.dibujando = True
            self.start_pos = event.scenePos()
            pen = QPen(self.color_actual, self.grosor,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

            if self.modo_forma == "lapiz":
                self.curr = QGraphicsPathItem()
                p = QPainterPath(self.start_pos)
                self.curr.setPath(p)
                self.curr.setPen(pen)
                self.addItem(self.curr)
            elif self.modo_forma == "cuadrado":
                self.curr = QGraphicsRectItem(QRectF(self.start_pos, QSizeF(1, 1)))
                self.curr.setPen(pen)
                self.addItem(self.curr)
            elif self.modo_forma == "circulo":
                self.curr = QGraphicsEllipseItem(QRectF(self.start_pos, QSizeF(1, 1)))
                self.curr.setPen(pen)
                self.addItem(self.curr)
            elif self.modo_forma == "linea":
                self.curr = QGraphicsLineItem(QLineF(self.start_pos, self.start_pos))
                self.curr.setPen(pen)
                self.addItem(self.curr)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Actualizar cursor de pincel
        self._update_brush_cursor(event.scenePos())

        if self.dibujando:
            pos = event.scenePos()
            if self.modo_forma == "borrador":
                self._erase_at(pos)
                return
            if self.modo_forma == "lapiz":
                p = self.curr.path(); p.lineTo(pos); self.curr.setPath(p)
            elif self.modo_forma in ("cuadrado", "circulo"):
                self.curr.setRect(QRectF(self.start_pos, pos).normalized())
            elif self.modo_forma == "linea":
                self.curr.setLine(QLineF(self.start_pos, pos))
        super().mouseMoveEvent(event)

    def _update_brush_cursor(self, pos):
        try:
            # Verificar si el objeto C++ sigue vivo
            if not hasattr(self, "_eraser_cursor_item") or self._eraser_cursor_item is None:
                self._recrear_cursor()
            
            # Intentar acceder a una propiedad para disparar RuntimeError si está borrado
            _ = self._eraser_cursor_item.zValue()
        except (RuntimeError, AttributeError):
            self._recrear_cursor()

        if self.modo_forma in ("lapiz", "borrador", "cuadrado", "circulo", "linea"):
            size = self.grosor_borrador if self.modo_forma == "borrador" else self.grosor
            r = size / 2
            self._eraser_cursor_item.setRect(-r, -r, size, size)
            self._eraser_cursor_item.setPos(pos)
            self._eraser_cursor_item.show()
        else:
            self._eraser_cursor_item.hide()

    def _recrear_cursor(self):
        """Re-inicializa el cursor visual si fue destruido"""
        self._eraser_cursor_item = QGraphicsEllipseItem()
        self._eraser_cursor_item.setPen(QPen(Qt.GlobalColor.white, 1, Qt.PenStyle.DashLine))
        self._eraser_cursor_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._eraser_cursor_item.setZValue(1000)
        self._eraser_cursor_item.hide()
        self.addItem(self._eraser_cursor_item)

    def mouseLeaveEvent(self, event):
        self._eraser_cursor_item.hide()
        super().mouseLeaveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dibujando:
            self.dibujando = False
            if self.modo_forma == "borrador":
                return
            
            if not hasattr(self, 'curr') or self.curr is None:
                return

            raw = self.curr
            self.curr = None # Reset
            self.removeItem(raw)
            smart = SmartItem(raw)
            self.addItem(smart)
            if hasattr(self.parent(), "view"):
                self.parent().view.undo_stack.append(smart)
        super().mouseReleaseEvent(event)

    def _erase_at(self, pos):
        r = self.grosor_borrador / 2
        eraser_rect = QRectF(pos.x() - r, pos.y() - r, self.grosor_borrador, self.grosor_borrador)
        
        for item in self.items(eraser_rect):
            if item == self._eraser_cursor_item: continue
            
            target = item
            while target.parentItem() and isinstance(target.parentItem(), SmartItem):
                target = target.parentItem()
            
            # Borrar ítems vectoriales (Líneas/Puntos)
            if isinstance(target, SmartItem):
                child = target.child
                if isinstance(child, QGraphicsPathItem):
                    self._erase_path_item(child, pos, r)
                    target._update_handles()
                elif isinstance(child, (QGraphicsRectItem, QGraphicsEllipseItem)):
                    # Para formas sólidas, seguimos usando sustracción pero simplificada
                    p = QPainterPath()
                    if isinstance(child, QGraphicsRectItem): p.addRect(child.rect())
                    else: p.addEllipse(child.rect())
                    
                    eraser_path = QPainterPath()
                    eraser_path.addEllipse(pos, r, r)
                    new_p = p.subtracted(eraser_path).simplified()
                    
                    if new_p.isEmpty():
                        self.removeItem(target)
                    else:
                        new_item = QGraphicsPathItem(new_p)
                        # Mantener el relleno y contorno EXACTO del original para no 'rellenar' figuras huecas
                        new_item.setBrush(child.brush())
                        new_item.setPen(child.pen())
                        target.child = new_item
                        new_item.setParentItem(target)
                        self.removeItem(child)
                        target._update_handles()
            
            elif isinstance(item, QGraphicsPathItem):
                self._erase_path_item(item, pos, r)

    def _erase_path_item(self, item, erase_pos, radius):
        """Algoritmo de filtrado de segmentos para borrado rápido sin bloqueos"""
        path = item.path()
        new_path = QPainterPath()
        
        started = False
        last_point = None
        
        for i in range(path.elementCount()):
            el = path.elementAt(i)
            p = QPointF(el.x, el.y)
            
            # Distancia al centro del borrador
            dist = QLineF(p, erase_pos).length()
            
            if dist > radius:
                if el.isMoveTo() or not started:
                    new_path.moveTo(p)
                    started = True
                else:
                    new_path.lineTo(p)
            else:
                # Segmento borrado: el siguiente punto deberá ser un moveTo
                started = False
                
        if new_path.elementCount() < 2:
            self.removeItem(item)
            # Si el item estaba en un SmartItem, el SmartItem se queda vacío. 
            # Subimos para borrar el padre si no tiene más que un item vacío.
            if item.parentItem() and isinstance(item.parentItem(), SmartItem):
                self.removeItem(item.parentItem())
        else:
            item.setPath(new_path)




# ──────────────────────────────────────────────
#  GUI PRINCIPAL
# ──────────────────────────────────────────────
class PizarraGUI(QWidget):
    def __init__(self, parent, context, colores):
        super().__init__(parent)
        self.colores = colores
        self.context = context
        self.font_fam = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.buttons = {}
        self.saved_colors = []
        self.inicializar_ui()

    def inicializar_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(12)

        # Floating toolbar container
        self.toolbar_widget = QFrame()
        self.toolbar_widget.setObjectName("ToolbarWidget")
        self.toolbar_widget.setStyleSheet(f"""
            QFrame#ToolbarWidget {{
                background: rgba(30, 30, 46, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 6px 16px;
            }}
            QToolTip {{
                background-color: #2D2D3D;
                color: #FFFFFF;
                border: 1px solid #4B5563;
                padding: 4px 8px;
                border-radius: 4px;
                font-family: 'Segoe UI';
                font-size: 11px;
            }}
        """)
        toolbar = QHBoxLayout(self.toolbar_widget)
        toolbar.setContentsMargins(10, 4, 10, 4)
        toolbar.setSpacing(8)

        tools = [
            ("🏹", "seleccion", "Seleccionar [S]"),
            ("✍️",  "lapiz",     "Lápiz [P]"),
            ("⬜", "cuadrado",  "Cuadrado"),
            ("⭕", "circulo",   "Círculo"),
            ("➖", "linea",    "Línea"),
            ("⚪", "borrador",  "Borrador [E]"),
        ]
        for icon, key, tip in tools:
            b = self._btn(icon, lambda _, k=key: self.act_f(k), tip)
            self.buttons[key] = b
            toolbar.addWidget(b)

        toolbar.addSpacing(10)
        toolbar.addWidget(self._sep())

        # Color
        toolbar.addWidget(self._btn("🎨", self.abrir_paleta, "Paleta de Colores [C]"))

        # Swatch del color actual
        self.lbl_color = QLabel()
        self.lbl_color.setFixedSize(28, 28)
        self._refresh_color_swatch()
        toolbar.addWidget(self.lbl_color)

        toolbar.addWidget(self._sep())

        # Grosor
        lbl_gr = QLabel("Grosor:")
        lbl_gr.setStyleSheet("color:#AAB0B8; font-family:'Outfit'; font-size:11px; font-weight:bold;")
        toolbar.addWidget(lbl_gr)
        self.spin_grosor = QSpinBox()
        self.spin_grosor.setRange(1, 50)
        self.spin_grosor.setValue(3)
        self.spin_grosor.setFixedWidth(55)
        self.spin_grosor.setStyleSheet(f"""
            QSpinBox {{
                background: rgba(255, 255, 255, 0.05);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 4px 6px;
                font-family: 'Outfit';
                font-size: 11px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: transparent;
                border: none;
            }}
        """)
        self.spin_grosor.valueChanged.connect(self._on_grosor_changed)
        toolbar.addWidget(self.spin_grosor)

        toolbar.addWidget(self._sep())

        # Texto y Otros
        self.btn_texto = self._btn("T", lambda: self.act_f("texto"), "Texto (clic en pizarra)")
        self.buttons["texto"] = self.btn_texto
        toolbar.addWidget(self.btn_texto)
        
        toolbar.addWidget(self._btn("🖼️", self.agregar_imagen, "Imagen"))
        toolbar.addWidget(self._btn("💾", self.guardar_imagen, "Guardar Imagen [Ctrl+S]"))

        toolbar.addStretch()

        # Zoom
        toolbar.addWidget(self._btn("🔍+", self.view_zoom_in,  "Zoom + [Ctrl+=]"))
        toolbar.addWidget(self._btn("🔍-", self.view_zoom_out, "Zoom - [Ctrl+-]"))
        toolbar.addWidget(self._btn("1:1", self.view_zoom_reset, "Reset Zoom [Ctrl+0]"))

        toolbar.addSpacing(8)
        # Historial
        toolbar.addWidget(self._btn("↩️", self.view_undo, "Deshacer [Ctrl+Z]"))
        toolbar.addWidget(self._btn("↪️", self.view_redo, "Rehacer [Ctrl+Y]"))

        lay.addWidget(self.toolbar_widget)

        # ── Vista ─────────────────────────────────────
        self.scene = DibujoScene(self)
        self.scene.setSceneRect(0, 0, 5000, 5000)
        self.view = PizarraView(self.scene, self)
        self.view.setStyleSheet(f"""
            QGraphicsView {{
                background: {self.colores['bg_principal']}; 
                border: 1px solid rgba(255, 255, 255, 0.06); 
                border-radius: 14px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: rgba(255, 255, 255, 0.01);
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.08);
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 0.15);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                border: none;
                background: rgba(255, 255, 255, 0.01);
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: rgba(255, 255, 255, 0.08);
                min-width: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: rgba(255, 255, 255, 0.15);
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)
        self.view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        lay.addWidget(self.view)

        self.act_f("lapiz")

    def _sep(self):
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(24)
        sep.setStyleSheet("background: rgba(255, 255, 255, 0.12); border: none;")
        return sep

    def _btn(self, lab, func, tip=""):
        b = QPushButton(lab)
        b.setFixedSize(36, 36)
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores['fg_principal']};
                border-radius: 18px;
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.08);
                color: white;
            }}
        """)
        b.clicked.connect(func)
        return b

    def _refresh_color_swatch(self):
        c = self.scene.color_actual.name() if hasattr(self, 'scene') else "#FFFFFF"
        self.lbl_color.setStyleSheet(
            f"background:{c}; border-radius:14px; border:2px solid rgba(255,255,255,0.2);"
        )

    def _on_grosor_changed(self, val):
        if self.scene.modo_forma == "borrador":
            self.scene.grosor_borrador = val
        else:
            self.scene.grosor = val

    def act_f(self, f):
        self.scene.modo_forma = f
        self.scene._modo_texto_click = (f == "texto")
        
        # Grosor: borrador usa grosor_borrador, otros usan grosor estándar
        if hasattr(self, 'spin_grosor'):
            if f == "borrador":
                self.spin_grosor.setValue(self.scene.grosor_borrador)
            else:
                self.spin_grosor.setValue(self.scene.grosor)

        # Si no estamos en selección, deseleccionar ítems para evitar molestias visuales
        if f != "seleccion":
            self.scene.clearSelection()

        # Configurar DragMode
        drag = QGraphicsView.DragMode.RubberBandDrag if f == "seleccion" else QGraphicsView.DragMode.NoDrag
        self.view.setDragMode(drag)

        # Cursor contextual
        cursor = Qt.CursorShape.ArrowCursor
        if f == "lapiz":     cursor = Qt.CursorShape.CrossCursor
        elif f == "borrador": cursor = Qt.CursorShape.PointingHandCursor
        elif f == "texto":    cursor = Qt.CursorShape.IBeamCursor
        self.view.setCursor(cursor)

        # Resaltado de botones
        for k, btn in self.buttons.items():
            active = (k == f)
            if active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {self.colores['acento']};
                        color: white;
                        border-radius: 18px;
                        border: 2px solid rgba(255,255,255,0.2);
                        font-size: 14px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {self.colores['fg_secundario']};
                        border-radius: 18px;
                        border: none;
                        font-size: 14px;
                    }}
                    QPushButton:hover {{
                        background: rgba(255, 255, 255, 0.08);
                        color: white;
                    }}
                """)

    def abrir_paleta(self):
        dlg = ColorPaletteDialog(self, self.colores, self.scene.color_actual, self.saved_colors)
        if dlg.exec():
            self.scene.color_actual = dlg.selected_color
            self.saved_colors = dlg.saved_colors
            self._refresh_color_swatch()


    def agregar_imagen(self):
        p, _ = QFileDialog.getOpenFileName(self, "Imagen", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if p:
            it = QGraphicsPixmapItem(QPixmap(p))
            smart = SmartItem(it)
            self.scene.addItem(smart)

    def view_undo(self):      self.view.undo()
    def view_redo(self):      self.view.redo()
    def view_zoom_in(self):   self.view.zoom_in()
    def view_zoom_out(self):  self.view.zoom_out()
    def view_zoom_reset(self):
        self.view.resetTransform()
        self.view._zoom_level = 1.0

    def guardar_imagen(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar Pizarra", "", "Archivos de Imagen (*.png *.jpg *.jpeg *.bmp)")
        if not ruta:
            return

        # Ocultar visualmente ayudantes
        if hasattr(self.scene, "_eraser_cursor_item"):
            self.scene._eraser_cursor_item.hide()
        self.scene.clearSelection()

        # Calcular área ocupada
        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            rect = QRectF(0, 0, 800, 600)  # Área por defecto si está vacía
        else:
            rect.adjust(-20, -20, 20, 20)  # Margen

        pixmap = QPixmap(int(rect.width()), int(rect.height()))
        # Si 'bg_principal' tiene formato '#RRGGBB', QColor lo acepta
        bg_color = QColor(self.colores.get('bg_principal', '#1E1E2E'))
        pixmap.fill(bg_color)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene.render(painter, target=QRectF(pixmap.rect()), source=rect)
        painter.end()

        pixmap.save(ruta)
