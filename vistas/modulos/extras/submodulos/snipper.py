import sys
import io
import re
import urllib.parse
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QHBoxLayout, QFrame, QColorDialog, QSlider, QComboBox,
                             QDialog, QTextEdit, QScrollArea)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal, QSize, QTimer, QPointF, QUrl, QBuffer
from PyQt6.QtGui import (QPainter, QPen, QColor, QPixmap, QScreen, QGuiApplication, 
                         QPainterPath, QCursor, QBrush, QImage, QDesktopServices)
from vistas.utils.hardware_manager import get_hardware_manager

from .snipper_ocr import CodeDetector, OcrManager, SnipperReadingModeDialog



class SnipperSidebar(QFrame):
    """Barra lateral para mostrar códigos QR y de barras detectados en la captura."""
    def __init__(self, colores, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.setFixedWidth(320)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"""
            QFrame#SnipperSidebar {{
                background: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
            QLabel {{
                color: white;
                font-family: 'Outfit', 'Segoe UI', sans-serif;
            }}
        """)
        self.setObjectName("SnipperSidebar")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Encabezado
        header = QHBoxLayout()
        self.lbl_title = QLabel("📱 Códigos Detectados")
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        header.addWidget(self.lbl_title)

        header.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent; color: #aaa; border: none; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover {
                color: white; background: rgba(255,255,255,0.1); border-radius: 4px;
            }
        """)
        btn_close.clicked.connect(self.hide)
        header.addWidget(btn_close)
        main_layout.addLayout(header)

        # Área desplazable para tarjetas de códigos
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

    def set_detected_codes(self, codes):
        # Limpiar tarjetas anteriores
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.lbl_title.setText(f"📱 Códigos Detectados ({len(codes)})")

        for idx, code in enumerate(codes):
            card = self._create_code_card(code, idx)
            self.cards_layout.insertWidget(idx, card)

    def _create_code_card(self, code, idx):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.06);
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)

        # Tipo de código
        t_header = QHBoxLayout()
        c_icon = "🌐" if code.get("is_url") else "🏷️"
        lbl_type = QLabel(f"{c_icon} {code.get('type', 'Código')}")
        lbl_type.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {self.colores['acento']};")
        t_header.addWidget(lbl_type)
        card_layout.addLayout(t_header)

        # Número de Serie / Contenido del Código
        data_text = code.get("data", "")
        data_box = QLabel(data_text)
        data_box.setWordWrap(True)
        data_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        is_url = code.get('is_url', False)
        text_color = "#34D399" if is_url else "#F3F4F6"
        data_box.setStyleSheet(f"""
            QLabel {{
                background: {self.colores['bg_secundario']};
                color: {text_color};
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.04);
            }}
        """)
        card_layout.addWidget(data_box)

        # Botones de Acción
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_copy = QPushButton("📋 Copiar")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.08);
                color: white;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                border: none;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.18);
            }}
        """)
        btn_copy.clicked.connect(lambda checked, t=data_text, b=btn_copy: self._copy_data(t, b))
        btn_row.addWidget(btn_copy)

        if is_url:
            btn_open = QPushButton("🌐 Abrir Enlace")
            btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_open.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores['acento']};
                    color: white;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 11px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{
                    background: {self.colores['acento_hover']};
                }}
            """)
            url_str = data_text if data_text.startswith(('http://', 'https://')) else f"http://{data_text}"
            btn_open.clicked.connect(lambda checked, u=url_str: QDesktopServices.openUrl(QUrl(u)))
            btn_row.addWidget(btn_open)

        card_layout.addLayout(btn_row)
        return card

    def _copy_data(self, text, btn):
        QGuiApplication.clipboard().setText(text)
        btn.setText("✅ Copiado")
        QTimer.singleShot(1500, lambda: btn.setText("📋 Copiar"))

class SnipperOverlay(QWidget):
    """Capa transparente para seleccionar el área de recorte en múltiples monitores."""
    area_selected = pyqtSignal(object)

    def __init__(self, mode="rectangular"):
        super().__init__()
        self.mode = mode
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        
        v_geo = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(v_geo)
        
        self.setWindowOpacity(1.0)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        
        self.begin = QPoint()
        self.end = QPoint()
        self.is_selecting = False
        self.screen_pixmap = self._grab_all_screens(v_geo)
        self.path = QPainterPath()

    def _grab_all_screens(self, virtual_geo):
        combined = QPixmap(virtual_geo.size())
        combined.fill(Qt.GlobalColor.black)
        painter = QPainter(combined)
        hw = get_hardware_manager()
        for s_info in hw.get_screens():
            screen = s_info["obj"]
            pix = screen.grabWindow(0)
            offset = screen.geometry().topLeft() - virtual_geo.topLeft()
            painter.drawPixmap(offset, pix)
        painter.end()
        return combined

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.area_selected.emit(None)
            self.close()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Dibujar captura original completa
        qp.drawPixmap(0, 0, self.screen_pixmap)
        
        # 2. Atenuar toda la pantalla
        qp.fillRect(self.rect(), QColor(10, 10, 15, 140))
        
        # 3. Dibujar zona seleccionada en brillo completo
        if self.mode == "rectangular":
            if self.is_selecting or not self.begin.isNull():
                rect = QRect(self.begin, self.end).normalized()
                if rect.isValid():
                    qp.save()
                    qp.setClipRect(rect)
                    qp.drawPixmap(0, 0, self.screen_pixmap)
                    qp.restore()
                    
                    # Borde de guía neón
                    qp.setPen(QPen(QColor("#6366F1"), 1.5, Qt.PenStyle.SolidLine))
                    qp.setBrush(Qt.BrushStyle.NoBrush)
                    qp.drawRect(rect)
                    
                    # Esquineros estilo visor de cámara
                    qp.setPen(QPen(QColor("#6366F1"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
                    l = min(12, rect.width() // 2, rect.height() // 2)
                    if l > 0:
                        qp.drawLine(rect.left(), rect.top(), rect.left() + l, rect.top())
                        qp.drawLine(rect.left(), rect.top(), rect.left(), rect.top() + l)
                        qp.drawLine(rect.right(), rect.top(), rect.right() - l, rect.top())
                        qp.drawLine(rect.right(), rect.top(), rect.right(), rect.top() + l)
                        qp.drawLine(rect.left(), rect.bottom(), rect.left() + l, rect.bottom())
                        qp.drawLine(rect.left(), rect.bottom(), rect.left(), rect.bottom() - l)
                        qp.drawLine(rect.right(), rect.bottom(), rect.right() - l, rect.bottom())
                        qp.drawLine(rect.right(), rect.bottom(), rect.right(), rect.bottom() - l)
                        
        elif self.mode == "freeform":
            if not self.path.isEmpty():
                qp.save()
                qp.setClipPath(self.path)
                qp.drawPixmap(0, 0, self.screen_pixmap)
                qp.restore()
                
                # Borde a mano alzada
                qp.setPen(QPen(QColor("#6366F1"), 1.5, Qt.PenStyle.DashLine))
                qp.setBrush(Qt.BrushStyle.NoBrush)
                qp.drawPath(self.path)
                
        elif self.mode == "fullscreen":
            v_geo = QGuiApplication.primaryScreen().virtualGeometry()
            cursor_pos = QCursor.pos()
            hovered_screen = None
            for screen in QGuiApplication.screens():
                if screen.geometry().contains(cursor_pos):
                    hovered_screen = screen
                    break
            if hovered_screen:
                rel_rect = hovered_screen.geometry().translated(-v_geo.topLeft())
                qp.save()
                qp.setClipRect(rel_rect)
                qp.drawPixmap(0, 0, self.screen_pixmap)
                qp.restore()
                
                # Resaltar la pantalla enfocada
                qp.setPen(QPen(QColor("#6366F1"), 3, Qt.PenStyle.SolidLine))
                qp.setBrush(Qt.BrushStyle.NoBrush)
                qp.drawRect(rel_rect)

    def mousePressEvent(self, event):
        if self.mode == "fullscreen":
            v_geo = QGuiApplication.primaryScreen().virtualGeometry()
            cursor_pos = QCursor.pos()
            hovered_screen = None
            for screen in QGuiApplication.screens():
                if screen.geometry().contains(cursor_pos):
                    hovered_screen = screen
                    break
            if hovered_screen:
                rel_rect = hovered_screen.geometry().translated(-v_geo.topLeft())
                self.hide()
                cropped = self.screen_pixmap.copy(rel_rect)
                self.area_selected.emit(cropped)
            else:
                self.area_selected.emit(None)
            self.close()
        else:
            self.begin = event.pos()
            self.end = self.begin
            self.is_selecting = True
            if self.mode == "freeform":
                self.path = QPainterPath()
                self.path.moveTo(QPointF(self.begin))
            self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        if self.is_selecting and self.mode == "freeform":
            self.path.lineTo(QPointF(event.pos()))
        self.update()

    def mouseReleaseEvent(self, event):
        if not self.is_selecting:
            return
        self.is_selecting = False
        
        if self.mode == "rectangular":
            rect = QRect(self.begin, self.end).normalized()
            if rect.width() > 5 and rect.height() > 5:
                self.hide()
                cropped = self.screen_pixmap.copy(rect)
                self.area_selected.emit(cropped)
            else:
                self.area_selected.emit(None)
            self.close()
            
        elif self.mode == "freeform":
            self.path.closeSubpath()
            rect = self.path.boundingRect().toRect().normalized()
            if rect.width() > 5 and rect.height() > 5:
                self.hide()
                cropped = QPixmap(rect.size())
                cropped.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(cropped)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                shifted_path = self.path.translated(QPointF(-rect.x(), -rect.y()))
                painter.setClipPath(shifted_path)
                painter.drawPixmap(QPoint(0, 0), self.screen_pixmap, rect)
                painter.end()
                
                self.area_selected.emit(cropped)
            else:
                self.area_selected.emit(None)
            self.close()

class SnipperEditor(QLabel):
    """Lienzo para dibujar sobre el recorte capturado."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = "none" # "pencil", "marker", "eraser", "none"
        self.color = QColor("red")
        self.weight = 3
        self.drawing = False
        self.last_point = QPoint()
        self.main_pixmap = None
        self.draw_layer = None
        self.final_pixmap = None

    def set_snip(self, pixmap):
        self.main_pixmap = pixmap
        self.draw_layer = QPixmap(pixmap.size())
        self.draw_layer.fill(Qt.GlobalColor.transparent)
        self.update_display()

    def update_display(self):
        if not self.main_pixmap: return
        combined = self.main_pixmap.copy()
        painter = QPainter(combined)
        painter.drawPixmap(0, 0, self.draw_layer)
        painter.end()
        
        self.final_pixmap = combined
        self.update()

    def paintEvent(self, event):
        if not self.main_pixmap or not self.final_pixmap:
            super().paintEvent(event)
            return
            
        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        qp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        s_size = self.final_pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        lbl_size = self.size()
        
        x = (lbl_size.width() - s_size.width()) // 2
        y = (lbl_size.height() - s_size.height()) // 2
        target_rect = QRect(x, y, s_size.width(), s_size.height())
        
        qp.drawPixmap(target_rect, self.final_pixmap)

    def mousePressEvent(self, event):
        if self.mode != "none" and self.main_pixmap:
            self.drawing = True
            self.last_point = self._map_to_pixmap(event.pos())

    def mouseMoveEvent(self, event):
        if self.drawing and self.main_pixmap:
            curr_point = self._map_to_pixmap(event.pos())
            painter = QPainter(self.draw_layer)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            if self.mode == "pencil":
                painter.setPen(QPen(self.color, self.weight, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            elif self.mode == "marker":
                m_color = QColor(self.color)
                m_color.setAlpha(120)
                pen = QPen(m_color, self.weight * 2 + 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin)
                painter.setPen(pen)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            else: # Eraser
                painter.setPen(QPen(Qt.GlobalColor.transparent, self.weight + 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            
            painter.drawLine(self.last_point, curr_point)
            painter.end()
            self.last_point = curr_point
            self.update_display()

    def mouseReleaseEvent(self, event):
        self.drawing = False

    def _map_to_pixmap(self, pos):
        if not self.main_pixmap: return pos
        s_size = self.main_pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        lbl_size = self.size()
        
        offset_x = (lbl_size.width() - s_size.width()) / 2
        offset_y = (lbl_size.height() - s_size.height()) / 2
        
        if s_size.width() <= 0 or s_size.height() <= 0:
            return pos
            
        rx = (pos.x() - offset_x) / s_size.width()
        ry = (pos.y() - offset_y) / s_size.height()
        
        px = int(rx * self.main_pixmap.width())
        py = int(ry * self.main_pixmap.height())
        px = max(0, min(px, self.main_pixmap.width() - 1))
        py = max(0, min(py, self.main_pixmap.height() - 1))
        return QPoint(px, py)

class SnipperGUI(QWidget):
    def __init__(self, parent, colores):
        super().__init__(parent)
        self.colores = colores
        self.current_codes = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Barra de Herramientas superior en un panel Glassmorphic
        tool_panel = QFrame()
        tool_panel.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            QLabel {{
                border: none;
                background: transparent;
                color: {self.colores['fg_secundario']};
                font-weight: bold;
            }}
        """)
        tool_bar = QHBoxLayout(tool_panel)
        tool_bar.setContentsMargins(12, 8, 12, 8)
        tool_bar.setSpacing(10)
        
        # 1. Nuevo Recorte (Icono)
        self.btn_new = self._icon_btn("✂️", self.start_snip, self.colores['acento'], "Nuevo Recorte")
        tool_bar.addWidget(self.btn_new)
        
        tool_bar.addSpacing(5)
        
        # 2. Modo (Combo con texto al lado)
        lbl_mode = QLabel("Modo:")
        lbl_mode.setStyleSheet("color: white; font-family: 'Outfit'; font-size: 13px; margin-left: 5px;")
        tool_bar.addWidget(lbl_mode)
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Rectangular", "rectangular")
        self.combo_mode.addItem("Forma Libre", "freeform")
        self.combo_mode.addItem("Pantalla Completa", "fullscreen")
        
        combo_style = f"""
            QComboBox {{
                background: {self.colores['bg_terciario']};
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 4px 24px 4px 8px;
                font-family: 'Outfit';
                font-size: 12px;
                min-width: 130px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 0px;
            }}
            QComboBox QAbstractItemView {{
                background: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                selection-background-color: {self.colores['acento']};
            }}
        """
        self.combo_mode.setStyleSheet(combo_style)
        tool_bar.addWidget(self.combo_mode)
        
        # 3. Aplazar (Combo con texto al lado)
        lbl_delay = QLabel("Aplazar:")
        lbl_delay.setStyleSheet("color: white; font-family: 'Outfit'; font-size: 13px; margin-left: 5px;")
        tool_bar.addWidget(lbl_delay)
        
        self.combo_delay = QComboBox()
        self.combo_delay.addItem("Sin espera", 0)
        self.combo_delay.addItem("1 segundo", 1)
        self.combo_delay.addItem("2 segundos", 2)
        self.combo_delay.addItem("3 segundos", 3)
        self.combo_delay.addItem("4 segundos", 4)
        self.combo_delay.addItem("5 segundos", 5)
        self.combo_delay.setStyleSheet(combo_style)
        tool_bar.addWidget(self.combo_delay)
        
        tool_bar.addSpacing(10)
        
        # Separador vertical sutil
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background: rgba(255, 255, 255, 0.08); width: 1px; border: none;")
        tool_bar.addWidget(sep)
        tool_bar.addSpacing(5)
        
        # 4. Herramientas de Dibujo (Iconos)
        self.btn_pencil = self._icon_btn("✏️", lambda: self.set_tool("pencil"), self.colores['bg_terciario'], "Pincel")
        tool_bar.addWidget(self.btn_pencil)
        
        self.btn_marker = self._icon_btn("🖍️", lambda: self.set_tool("marker"), self.colores['bg_terciario'], "Marcador Resaltador")
        tool_bar.addWidget(self.btn_marker)
        
        self.btn_eraser = self._icon_btn("🧼", lambda: self.set_tool("eraser"), self.colores['bg_terciario'], "Borrador de trazos")
        tool_bar.addWidget(self.btn_eraser)
        
        # Círculo de color
        self.btn_color = QPushButton()
        self.btn_color.setFixedSize(28, 28)
        self.btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_color.setToolTip("Elegir Color")
        self.btn_color.setStyleSheet("background: #FF3B30; border-radius: 14px; border: 2px solid white;")
        self.btn_color.clicked.connect(self.choose_color)
        tool_bar.addWidget(self.btn_color)
        
        # Grosor con regla icon
        lbl_w = QLabel("📏")
        lbl_w.setToolTip("Grosor del trazo")
        lbl_w.setStyleSheet("font-size: 14px; border: none; background: transparent; margin-left: 5px;")
        tool_bar.addWidget(lbl_w)
        
        self.slider_w = QSlider(Qt.Orientation.Horizontal)
        self.slider_w.setRange(1, 50)
        self.slider_w.setValue(3)
        self.slider_w.setFixedWidth(80)
        self.slider_w.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: {self.colores['bg_terciario']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {self.colores['acento']};
                width: 14px;
                height: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
                border: 1px solid rgba(255,255,255,0.2);
            }}
            QSlider::handle:horizontal:hover {{
                background: {self.colores['acento_hover']};
            }}
        """)
        self.slider_w.valueChanged.connect(self.change_weight)
        tool_bar.addWidget(self.slider_w)
        
        self.lbl_w_val = QLabel("3px")
        self.lbl_w_val.setStyleSheet("color: #aaa; min-width: 25px; font-weight: normal; font-size: 11px;")
        tool_bar.addWidget(self.lbl_w_val)
        
        tool_bar.addStretch()
        
        # 5. Botones de Acción (Modo Lectura + QR + Acciones finales)
        self.btn_ocr = self._icon_btn("📖", self.open_reading_mode, self.colores['bg_terciario'], "Modo Lectura (Extraer y Copiar Texto)")
        tool_bar.addWidget(self.btn_ocr)

        self.btn_qr = self._icon_btn("📱", self.toggle_sidebar, self.colores['bg_terciario'], "Códigos QR / Barras")
        self.btn_qr.setEnabled(False)
        self.btn_qr.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']}; color: rgba(255,255,255,0.3); border-radius: 8px; font-size: 16px;
                border: 1px solid rgba(255,255,255,0.03);
            }}
        """)
        tool_bar.addWidget(self.btn_qr)

        self.btn_clear = self._icon_btn("🗑️", self.clear_drawing, self.colores['bg_terciario'], "Limpiar dibujo")
        tool_bar.addWidget(self.btn_clear)
        
        self.btn_copy = self._icon_btn("📋", self.copy_to_clipboard, self.colores['bg_terciario'], "Copiar al portapapeles")
        tool_bar.addWidget(self.btn_copy)
        
        self.btn_save = self._icon_btn("💾", self.save_snip, self.colores['bg_terciario'], "Guardar recorte")
        tool_bar.addWidget(self.btn_save)
        
        layout.addWidget(tool_panel)
        
        # Área Principal: Editor Canvas + Sidebar Horizontal
        main_content = QHBoxLayout()
        main_content.setSpacing(12)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setMaximumHeight(500)
        self.scroll.setMinimumHeight(400)
        self.scroll.setStyleSheet(f"background: {self.colores['bg_principal']}; border: 1px solid rgba(255,255,255,0.05); border-radius: 12px;")
        
        self.editor = SnipperEditor()
        self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor.setText("Haz clic en ✂️ para empezar un recorte")
        self.editor.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 14px; background: transparent; border: none;")
        
        self.scroll.setWidget(self.editor)
        main_content.addWidget(self.scroll, stretch=1)

        # Sidebar para QR / Códigos de Barras
        self.sidebar = SnipperSidebar(self.colores, self)
        self.sidebar.hide()
        main_content.addWidget(self.sidebar)

        layout.addLayout(main_content)

    def _icon_btn(self, icon_text, func, bg, tooltip=""):
        btn = QPushButton(icon_text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(36, 36)
        btn.setToolTip(tooltip)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg}; color: white; border-radius: 8px; font-size: 16px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            QPushButton:hover {{
                background: {self.colores['acento_hover'] if bg == self.colores['acento'] else 'rgba(255, 255, 255, 0.15)'};
            }}
        """)
        btn.clicked.connect(func)
        return btn

    def set_tool(self, mode):
        self.editor.mode = mode
        active_style = f"background: {self.colores['acento']}; color: white; border-radius: 8px; font-size: 16px; border: 1px solid white;"
        inactive_style = f"background: {self.colores['bg_terciario']}; color: white; border-radius: 8px; font-size: 16px; border: 1px solid rgba(255,255,255,0.05);"
        
        self.btn_pencil.setStyleSheet(active_style if mode == 'pencil' else inactive_style)
        self.btn_marker.setStyleSheet(active_style if mode == 'marker' else inactive_style)
        self.btn_eraser.setStyleSheet(active_style if mode == 'eraser' else inactive_style)

    def change_weight(self, val):
        self.editor.weight = val
        self.lbl_w_val.setText(f"{val}px")

    def choose_color(self):
        c = QColorDialog.getColor(self.editor.color, self)
        if c.isValid():
            self.editor.color = c
            self.btn_color.setStyleSheet(f"background: {c.name()}; border-radius: 14px; border: 2px solid white;")

    def start_snip(self):
        delay = self.combo_delay.currentData()
        self.window().showMinimized()
        QTimer.singleShot(delay * 1000 if delay > 0 else 300, self._launch_overlay)

    def _launch_overlay(self):
        mode = self.combo_mode.currentData()
        self.overlay = SnipperOverlay(mode)
        self.overlay.area_selected.connect(self.on_captured)
        self.overlay.show()

    def on_captured(self, pixmap):
        self.window().showNormal()
        if pixmap is not None:
            self.editor.set_snip(pixmap)
            self.set_tool("pencil")
            
            # Escanear presencia de códigos QR o de barras
            codes = CodeDetector.detect(pixmap)
            self.current_codes = codes

            if codes:
                self.btn_qr.setEnabled(True)
                self.btn_qr.setToolTip(f"¡{len(codes)} código(s) detectado(s)! Haz clic para alternar la barra lateral.")
                self.btn_qr.setStyleSheet(f"""
                    QPushButton {{
                        background: #10B981; color: white; border-radius: 8px; font-size: 16px;
                        border: 1px solid #34D399;
                    }}
                    QPushButton:hover {{
                        background: #059669;
                    }}
                """)
                self.sidebar.set_detected_codes(codes)
                self.sidebar.show()
            else:
                self.btn_qr.setEnabled(False)
                self.btn_qr.setToolTip("No se detectaron códigos QR o de barras en la imagen")
                self.btn_qr.setStyleSheet(f"""
                    QPushButton {{
                        background: {self.colores['bg_terciario']}; color: rgba(255,255,255,0.3); border-radius: 8px; font-size: 16px;
                        border: 1px solid rgba(255,255,255,0.03);
                    }}
                """)
                self.sidebar.hide()

    def open_reading_mode(self):
        pix = getattr(self.editor, 'final_pixmap', None) or getattr(self.editor, 'main_pixmap', None)
        text = OcrManager.extract_text(pix) if pix else ""
        dialog = SnipperReadingModeDialog(text, self.colores, self)
        dialog.exec()

    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.hide()
        else:
            if self.current_codes:
                self.sidebar.set_detected_codes(self.current_codes)
                self.sidebar.show()

    def clear_drawing(self):
        if self.editor.main_pixmap:
            self.editor.draw_layer.fill(Qt.GlobalColor.transparent)
            self.editor.update_display()

    def copy_to_clipboard(self):
        if hasattr(self.editor, 'final_pixmap') and self.editor.final_pixmap:
            QGuiApplication.clipboard().setPixmap(self.editor.final_pixmap)
            
    def save_snip(self):
        if hasattr(self.editor, 'final_pixmap') and self.editor.final_pixmap:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar Recorte", "recorte.png", "PNG (*.png)")
            if path: self.editor.final_pixmap.save(path)
