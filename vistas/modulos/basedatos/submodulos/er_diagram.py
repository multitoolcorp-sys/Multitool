"""
er_diagram.py - Visor y diseñador interactivo de Diagramas Entidad-Relación (ER) estilo DBeaver
Renderiza las tablas como tarjetas visuales interactivas con sus columnas, claves primarias y relaciones foráneas.
"""
import math
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsLineItem, QFileDialog, QMessageBox,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainter, QPainterPath, QImage
)


class TableNodeItem(QGraphicsItem):
    """Nodo gráfico interactivo que representa una tabla en el diagrama ER"""
    def __init__(self, table_name: str, columns: List[Dict[str, Any]], row_count: int = 0, colores: dict = None):
        super().__init__()
        self.table_name = table_name
        self.columns = columns
        self.row_count = row_count
        self.colores = colores or {}
        
        self.width = 220
        # Altura calculada: cabecera (36px) + 20px por columna + padding (14px)
        self.height = max(70, 38 + len(columns) * 22 + 10)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self.scene():
                self.scene().update()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fondo de la tarjeta
        border_color = QColor(self.colores.get("acento", "#6366F1")) if self.isSelected() else QColor("#2D2D3D")
        painter.setPen(QPen(border_color, 2 if self.isSelected() else 1.5))
        painter.setBrush(QBrush(QColor("#1E1E2E")))
        painter.drawRoundedRect(0, 0, self.width, self.height, 8, 8)

        # Cabecera de la tabla
        header_path = QPainterPath()
        header_path.addRoundedRect(0, 0, self.width, 34, 8, 8)
        # Recortar parte inferior para unir con el cuerpo
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(self.colores.get("bg_terciario", "#2D2D3D"))))
        painter.drawPath(header_path)
        painter.drawRect(0, 20, self.width, 14)

        # Línea divisoria de cabecera
        painter.setPen(QPen(QColor(self.colores.get("acento", "#6366F1")), 1.5))
        painter.drawLine(0, 34, self.width, 34)

        # Título de la tabla
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.setPen(QPen(QColor("#FFFFFF")))
        title_text = f"📄 {self.table_name}"
        painter.drawText(10, 22, title_text)

        # Contador de filas
        if self.row_count >= 0:
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QPen(QColor("#94A3B8")))
            cnt_text = f"({self.row_count})"
            painter.drawText(self.width - 45, 22, cnt_text)

        # Columnas
        y = 52
        for c in self.columns:
            is_pk = c.get("pk", False)
            col_name = c.get("name", "")
            col_type = c.get("type", "TEXT")

            # Icono PK o normal
            painter.setFont(QFont("Segoe UI", 9))
            if is_pk:
                painter.setPen(QPen(QColor("#FBBF24")))  # Dorado
                painter.drawText(10, y, "🔑")
            else:
                painter.setPen(QPen(QColor("#64748B")))
                painter.drawText(10, y, "•")

            # Nombre de la columna
            painter.setPen(QPen(QColor("#F8FAFC" if is_pk else "#E2E8F0")))
            if is_pk:
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            else:
                painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(26, y, col_name)

            # Tipo de dato (a la derecha)
            painter.setFont(QFont("Consolas", 8))
            painter.setPen(QPen(QColor("#A5B4FC" if is_pk else "#94A3B8")))
            painter.drawText(self.width - 70, y, col_type[:10])

            y += 22

    def get_connection_point(self, other_pos: QPointF) -> QPointF:
        """Calcula el punto de conexión óptimo (borde izquierdo o derecho) hacia otro nodo"""
        center = self.mapToScene(self.boundingRect().center())
        if other_pos.x() > center.x():
            return self.mapToScene(QPointF(self.width, self.height / 2))
        else:
            return self.mapToScene(QPointF(0, self.height / 2))


class RelationEdgeItem(QGraphicsItem):
    """Línea de relación conectora entre tablas (clave foránea)"""
    def __init__(self, source_node: TableNodeItem, target_node: TableNodeItem, label: str = ""):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.label = label
        self.setZValue(-1)  # Por detrás de las tablas

    def boundingRect(self) -> QRectF:
        p1 = self.source_node.get_connection_point(self.target_node.scenePos())
        p2 = self.target_node.get_connection_point(self.source_node.scenePos())
        return QRectF(p1, p2).normalized().adjusted(-20, -20, 20, 20)

    def paint(self, painter: QPainter, option, widget=None):
        p1 = self.source_node.get_connection_point(self.target_node.scenePos())
        p2 = self.target_node.get_connection_point(self.source_node.scenePos())

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#818CF8"), 1.8, Qt.PenStyle.DashLine)
        painter.setPen(pen)

        # Dibujar curva bezier suave
        path = QPainterPath(p1)
        dx = (p2.x() - p1.x()) / 2
        ctrl1 = QPointF(p1.x() + dx, p1.y())
        ctrl2 = QPointF(p2.x() - dx, p2.y())
        path.cubicTo(ctrl1, ctrl2, p2)
        painter.drawPath(path)

        # Flecha en el extremo p2
        angle = math.atan2(p2.y() - ctrl2.y(), p2.x() - ctrl2.x())
        arrow_size = 8
        arrow_p1 = p2 - QPointF(math.cos(angle - math.pi / 6) * arrow_size, math.sin(angle - math.pi / 6) * arrow_size)
        arrow_p2 = p2 - QPointF(math.cos(angle + math.pi / 6) * arrow_size, math.sin(angle + math.pi / 6) * arrow_size)
        
        arrow_head = QPainterPath()
        arrow_head.moveTo(p2)
        arrow_head.lineTo(arrow_p1)
        arrow_head.lineTo(arrow_p2)
        arrow_head.closeSubpath()
        painter.setBrush(QBrush(QColor("#818CF8")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(arrow_head)

        # Etiqueta con los campos relacionados en el centro de la línea
        if self.label:
            mid_pt = path.pointAtPercent(0.5)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            fm = painter.fontMetrics()
            txt_w = fm.horizontalAdvance(self.label) + 12
            txt_h = fm.height() + 4
            lbl_rect = QRectF(mid_pt.x() - txt_w / 2, mid_pt.y() - txt_h / 2, txt_w, txt_h)
            painter.setPen(QPen(QColor("#6366F1"), 1))
            painter.setBrush(QBrush(QColor("#1E1E2E")))
            painter.drawRoundedRect(lbl_rect, 4, 4)
            painter.setPen(QPen(QColor("#E2E8F0")))
            painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, self.label)


class ERDiagramWidget(QWidget):
    """Contenedor interactivo para visualizar el Diagrama Entidad-Relación de la base de datos"""
    table_double_clicked = pyqtSignal(str)

    def __init__(self, colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.nodes = {}
        self.edges = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Barra de herramientas superior
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        lbl_title = QLabel("📊  Diagrama Entidad-Relación (ER Diagram)")
        lbl_title.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        toolbar.addWidget(lbl_title)

        toolbar.addStretch()

        self.btn_refresh = QPushButton("🔄 Actualizar")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setFixedHeight(28)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
                outline: none;
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        toolbar.addWidget(self.btn_refresh)

        btn_zoom_in = QPushButton("🔍+")
        btn_zoom_in.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zoom_in.setFixedSize(28, 28)
        btn_zoom_in.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 4px; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')}; outline: none;")
        btn_zoom_in.clicked.connect(lambda: self.view.scale(1.15, 1.15))
        toolbar.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("🔍-")
        btn_zoom_out.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zoom_out.setFixedSize(28, 28)
        btn_zoom_out.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 4px; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')}; outline: none;")
        btn_zoom_out.clicked.connect(lambda: self.view.scale(0.85, 0.85))
        toolbar.addWidget(btn_zoom_out)

        btn_fit = QPushButton("↔️ Centrar")
        btn_fit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fit.setFixedHeight(28)
        btn_fit.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 4px; padding: 0 8px; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')}; outline: none;")
        btn_fit.clicked.connect(self._centrar_vista)
        toolbar.addWidget(btn_fit)

        btn_export_png = QPushButton("💾 Guardar PNG")
        btn_export_png.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export_png.setFixedHeight(28)
        btn_export_png.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border-radius: 4px; padding: 0 10px; font-weight: bold; border: none; outline: none;")
        btn_export_png.clicked.connect(self._exportar_png)
        toolbar.addWidget(btn_export_png)

        layout.addLayout(toolbar)

        # Escena y vista gráfica
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QBrush(QColor("#121218")))

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setStyleSheet(f"""
            QGraphicsView {{
                background-color: #121218;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
            }}
        """)
        layout.addWidget(self.view)

    def load_schema(self, db_conn):
        """Carga y dibuja las tablas y relaciones del esquema de base de datos"""
        self.scene.clear()
        self.nodes = {}
        self.edges = []

        if not db_conn or not db_conn.is_connected:
            text = self.scene.addText("Sin conexión activa para generar el diagrama ER.")
            text.setDefaultTextColor(QColor("#94A3B8"))
            return

        eng_type = getattr(db_conn, "engine_type", "relational")
        if eng_type == "kv":
            text = self.scene.addText("ℹ️ Redis es un almacén Clave-Valor en memoria.\nLos diagramas ER aplican a bases de datos Relacionales y Documentales (Colecciones).")
            text.setDefaultTextColor(QColor("#94A3B8"))
            return

        if not hasattr(db_conn, "get_tables"):
            text = self.scene.addText(f"El motor actual ({getattr(db_conn, 'engine', '')}) no admite diagramas ER.")
            text.setDefaultTextColor(QColor("#94A3B8"))
            return

        tables = db_conn.get_tables()
        tbls_only = [t for t in tables if t.get("type") == "table"]

        if not tbls_only:
            tipo_ent = "colecciones" if eng_type == "document" else "tablas"
            text = self.scene.addText(f"No se encontraron {tipo_ent} para generar el diagrama.")
            text.setDefaultTextColor(QColor("#94A3B8"))
            return

        # Distribuir tablas en una cuadrícula agradable
        cols_count = max(2, math.ceil(math.sqrt(len(tbls_only))))
        spacing_x = 280
        spacing_y = 220

        all_foreign_keys = []

        for idx, t in enumerate(tbls_only):
            t_name = t.get("name", "")
            schema = db_conn.get_table_schema(t_name)
            node = TableNodeItem(
                table_name=t_name,
                columns=schema.get("columns", []),
                row_count=t.get("row_count", 0),
                colores=self.colores
            )
            col_pos = idx % cols_count
            row_pos = idx // cols_count
            node.setPos(col_pos * spacing_x + 50, row_pos * spacing_y + 50)
            self.scene.addItem(node)
            self.nodes[t_name] = node

            # Recolectar relaciones foráneas
            if hasattr(db_conn, "get_foreign_keys"):
                fks = db_conn.get_foreign_keys(t_name)
                for fk in fks:
                    all_foreign_keys.append((t_name, fk.get("to_table"), fk.get("from"), fk.get("to_column")))

        # Conectar líneas de relaciones
        for from_tbl, to_tbl, from_col, to_col in all_foreign_keys:
            if from_tbl in self.nodes and to_tbl in self.nodes and from_tbl != to_tbl:
                edge = RelationEdgeItem(self.nodes[from_tbl], self.nodes[to_tbl], label=f"{from_col} -> {to_col}")
                self.scene.addItem(edge)
                self.edges.append(edge)

        self._centrar_vista()

    def _centrar_vista(self):
        items_rect = self.scene.itemsBoundingRect()
        if not items_rect.isEmpty():
            self.view.fitInView(items_rect.adjusted(-50, -50, 50, 50), Qt.AspectRatioMode.KeepAspectRatio)

    def _exportar_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Diagrama ER", "diagrama_er.png", "Imagen PNG (*.png)")
        if not path:
            return
        rect = self.scene.itemsBoundingRect().adjusted(-20, -20, 20, 20)
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
        image.fill(QColor("#121218"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene.render(painter, target=QRectF(image.rect()), source=rect)
        painter.end()
        image.save(path)
        QMessageBox.information(self, "Exportado", f"Diagrama ER guardado con éxito en:\n{path}")
