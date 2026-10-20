import platform
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QApplication, QWidget,
    QButtonGroup, QRadioButton, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsPathItem
)
from PyQt6.QtCore import Qt, QSize, QRectF, QPointF
from PyQt6.QtGui import (
    QPixmap, QFont, QImage, QPainter, QColor, QPen, QBrush, 
    QPainterPath, QTransform, QWheelEvent
)

class AvatarEditorView(QGraphicsView):
    """Vista personalizada para manejar el zoom y el arrastre directo de la imagen"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QBrush(QColor("#121218")))
        
        self._is_panning = False
        self._last_mouse_pos = QPointF()

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = True
            self._last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.position() - self._last_mouse_pos
            self._last_mouse_pos = event.position()
            
            # Mover el área visible (scroll)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._is_panning = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

class OverlayWidget(QWidget):
    """Widget de máscara que dibuja el hueco transparente"""
    def __init__(self, parent, shape_callback, colores):
        super().__init__(parent)
        self.shape_callback = shape_callback
        self.colores = colores
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Color del resto (atenuado)
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Todo el rectángulo
        full_path = QPainterPath()
        full_path.addRect(QRectF(self.rect()))
        
        # El "hueco" en el centro
        hole_path = QPainterPath()
        center_x, center_y = self.width() / 2, self.height() / 2
        size = 300.0
        shape = self.shape_callback()
        
        hole_rect = QRectF(center_x - size/2, center_y - size/2, size, size)
        
        if shape == "circle":
            hole_path.addEllipse(hole_rect)
        else:
            hole_path.addRect(hole_rect)
            
        # Unir para crear el hueco
        result_path = full_path.subtracted(hole_path)
        painter.drawPath(result_path)
        
        # Borde del hueco
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(self.colores['acento']), 2, Qt.PenStyle.DashLine))
        if shape == "circle":
            painter.drawEllipse(hole_rect)
        else:
            painter.drawRect(hole_rect)
        painter.end()

class ImageEditorDialog(QDialog):
    """Editor de imagen PRO para recorte de avatar (Fixed Hole + Drag & Zoom)"""
    def __init__(self, parent, image_path, callback_save, colores):
        super().__init__(parent)
        self.setWindowTitle("Encuadrar Avatar")
        self.setFixedSize(550, 680)
        self.image_path = image_path
        self.callback_save = callback_save
        self.colores = colores
        self.crop_shape = "circle"
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.setup_ui()
        self._load_image()
        self.center_window()

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.left() + (screen.width() - self.width()) // 2
        y = screen.top() + (screen.height() - self.height()) // 2
        self.move(x, y)

    def setup_ui(self):
        self.setStyleSheet(f"background-color: {self.colores['bg_principal']}; color: white;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        lbl_title = QLabel("AJUSTAR AVATAR")
        lbl_title.setFont(QFont(self.font_family, 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores['acento']};")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        lbl_hint = QLabel("Arrastra para mover • Ruedita para Zoom")
        lbl_hint.setFont(QFont(self.font_family, 9))
        lbl_hint.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_hint)

        # QGraphicsView para el encuadre
        self.scene = QGraphicsScene(self)
        self.view = AvatarEditorView(self)
        self.view.setScene(self.scene)
        self.view.setFixedSize(500, 500)
        self.view.setStyleSheet("border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);")
        layout.addWidget(self.view, alignment=Qt.AlignmentFlag.AlignCenter)

        # Overlay Layer
        self.overlay = OverlayWidget(self.view, lambda: self.crop_shape, self.colores)
        self.overlay.setFixedSize(500, 500)

        # Opciones de forma
        shape_layout = QHBoxLayout()
        shape_layout.setContentsMargins(0, 10, 0, 10)
        
        lbl_forma = QLabel("Forma:")
        lbl_forma.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        shape_layout.addWidget(lbl_forma)
        
        self.rb_circle = QRadioButton("Circular")
        self.rb_circle.setChecked(True)
        self.rb_circle.setStyleSheet("color: white;")
        self.rb_circle.toggled.connect(lambda: self._update_shape("circle"))
        shape_layout.addWidget(self.rb_circle)
        
        self.rb_square = QRadioButton("Cuadrado")
        self.rb_square.setStyleSheet("color: white;")
        self.rb_square.toggled.connect(lambda: self._update_shape("square"))
        shape_layout.addWidget(self.rb_square)
        shape_layout.addStretch()
        layout.addLayout(shape_layout)

        # Botones
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setMinimumHeight(40)
        btn_cancel.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("DEFINIR AVATAR")
        btn_ok.setMinimumHeight(40)
        btn_ok.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px; font-weight: bold;")
        btn_ok.clicked.connect(self._confirmar)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def _load_image(self):
        pixmap = QPixmap(self.image_path)
        if pixmap.isNull(): 
            return
        
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        
        # Hacemos la escena MUCHO más grande que la imagen para permitir libertad total de movimiento
        # Esto evita que la imagen "choque" con los bordes
        extra = 2000 
        rect = self.pixmap_item.boundingRect()
        self.scene.setSceneRect(-extra, -extra, rect.width() + extra*2, rect.height() + extra*2)
        
        # Colocar la imagen en el centro de esta gran escena
        self.pixmap_item.setPos(0, 0)
        
        # Escalar inicial para que cubra el hueco (300px)
        scale = 320 / min(rect.width(), rect.height())
        self.view.scale(scale, scale)
        
        # Centrar la vista en la imagen
        self.view.centerOn(self.pixmap_item)

    def _update_shape(self, shape):
        self.crop_shape = shape
        self.overlay.update()

    def _confirmar(self):
        # Capturar el área bajo el hueco (300x300 en el centro de la vista)
        size_crop = 300
        
        # 1. Obtener el rectángulo del viewport que corresponde al "hueco"
        # La vista es de 500x500, el hueco es de 300x300 centrado.
        viewport_rect = QRectF(
            (500 - size_crop) / 2, 
            (500 - size_crop) / 2, 
            size_crop, size_crop
        )
        
        # 2. Mapear ese rectángulo de píxeles de la pantalla a coordenadas de la escena
        scene_rect = self.view.mapToScene(viewport_rect.toRect()).boundingRect()
        
        # 3. Renderizar esa porción de la escena
        output_size = 512 # Mayor calidad para el guardado
        result_pixmap = QPixmap(output_size, output_size)
        result_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(result_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Mapeamos el scene_rect (que puede tener cualquier tamaño según el zoom) 
        # al tamaño fijo de salida 512x512
        self.scene.render(painter, QRectF(0, 0, output_size, output_size), scene_rect)
        painter.end()
        
        # 4. Convertir a PIL de forma segura (copiando datos para evitar crashes)
        from PIL import Image
        qimg = result_pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        width, height = qimg.width(), qimg.height()
        
        ptr = qimg.bits()
        ptr.setsize(qimg.sizeInBytes())
        # El .copy() es fundamental: crea una copia independiente en la memoria de Python
        img_pil = Image.frombuffer('RGBA', (width, height), ptr, 'raw', 'RGBA', 0, 1).copy()
        
        self.callback_save(img_pil, self.crop_shape)
        self.accept()
