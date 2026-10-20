import os
import sys
import json
import time
import psutil
import platform
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QPlainTextEdit, QFrame, QScrollArea, QCheckBox, QFileDialog, QMessageBox, QGridLayout,
    QApplication, QSizeGrip
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QPoint, QEvent, QRect
from PyQt6.QtGui import QFont, QColor, QDesktopServices

class QuickWidgetBase(QFrame):
    """Clase base para todos los widgets con soporte para anclaje"""
    def __init__(self, key, display_name, context, parent=None):
        super().__init__(parent)
        self.key = key
        self.display_name = display_name
        self.context = context
        self.is_pinned = False
        
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1"
        })
        self.init_base_ui()

    def init_base_ui(self):
        self.base_layout = QVBoxLayout(self)
        self.base_layout.setContentsMargins(10, 10, 10, 10)
        self.base_layout.setSpacing(6)
        
        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        
        self.lbl_title = QLabel(self.display_name)
        self.lbl_title.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; font-weight: bold; font-size: 13px;")
        header_layout.addWidget(self.lbl_title)
        
        header_layout.addStretch()
        
        self.btn_pin = QPushButton("📌")
        self.btn_pin.setToolTip("Fijar al escritorio")
        self.btn_pin.setFixedSize(22, 22)
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.setStyleSheet(f"background: transparent; color: {self.colores.get('fg_secundario', '#AAB0B8')}; border: none; font-size: 12px;")
        self.btn_pin.clicked.connect(self.toggle_pin)
        header_layout.addWidget(self.btn_pin)
        
        self.base_layout.addWidget(self.header)
        
        self.div = QFrame()
        self.div.setFrameShape(QFrame.Shape.HLine)
        self.div.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; max-height: 1px; border: none;")
        self.base_layout.addWidget(self.div)
        
        self.container = QWidget()
        self.layout_contenido = QVBoxLayout(self.container)
        self.layout_contenido.setContentsMargins(0, 4, 0, 0)
        self.layout_contenido.setSpacing(6)
        self.base_layout.addWidget(self.container)

    def toggle_pin(self):
        p = self.parent()
        while p:
            if hasattr(p, "pin_widget_from_center"):
                p.pin_widget_from_center(self.key)
                return
            p = p.parent()


# ==============================================================================
# SUBMÓDULO 1: STICKY POST-ITS (Notas Adhesivas de Escritorio Múltiples)
# ==============================================================================
POSTIT_COLORS = [
    ("#FEF08A", "#713F12", "🟡 Amarillo"),
    ("#BBF7D0", "#14532D", "🟢 Verde"),
    ("#FBCFE8", "#831843", "🩷 Rosa"),
    ("#BAE6FD", "#0C4A6E", "🔵 Azul"),
    ("#DDD6FE", "#4C1D95", "🟣 Morado")
]

class StickyNoteTrashOverlay(QWidget):
    """Papelera flotante interactiva en pantalla que aparece al arrastrar notas adhesivas"""
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = StickyNoteTrashOverlay()
        return cls._instance

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(270, 68)
        
        self.is_highlighted = False
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        
        self.frame = QFrame()
        self.frame_lay = QHBoxLayout(self.frame)
        self.frame_lay.setContentsMargins(18, 10, 18, 10)
        
        self.lbl_icon = QLabel("🗑️")
        self.lbl_icon.setFont(QFont("Segoe UI Emoji", 18))
        self.frame_lay.addWidget(self.lbl_icon)
        
        self.lbl_text = QLabel("Arrastra aquí para desanclar")
        self.lbl_text.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_text.setStyleSheet("color: white;")
        self.frame_lay.addWidget(self.lbl_text, 1)
        
        lay.addWidget(self.frame)
        self._update_style()

    def _update_style(self):
        if self.is_highlighted:
            self.frame.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EF4444, stop:1 #B91C1C);
                    border: 2px solid #FCA5A5;
                    border-radius: 34px;
                }
            """)
            self.lbl_text.setText("¡Soltar para desanclar!")
        else:
            self.frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(20, 20, 30, 0.94);
                    border: 2px dashed #EF4444;
                    border-radius: 34px;
                }
            """)
            self.lbl_text.setText("Arrastra aquí para desanclar")

    def show_trash(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 45
        self.move(x, y)
        self.is_highlighted = False
        self._update_style()
        self.show()
        self.raise_()

    def hide_trash(self):
        self.hide()

    def check_hover(self, global_pos: QPoint):
        inside = self.geometry().contains(global_pos)
        if inside != self.is_highlighted:
            self.is_highlighted = inside
            self._update_style()

    def is_hovering(self, global_pos: QPoint) -> bool:
        return self.geometry().contains(global_pos)


class StandaloneStickyNoteWindow(QWidget):
    """Nota adhesiva post-it flotante independiente pegada en la pantalla con ajuste libre de tamaño y fuente"""
    def __init__(self, note_dict: dict, parent_widget, colores: dict = None):
        super().__init__()
        self.note_dict = note_dict
        self.parent_widget = parent_widget
        self.colores = colores or {}
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start_geom = None
        self._resize_start_pos = None

        self.font_size = int(self.note_dict.get("font_size", 10))

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        # Tamaño mínimo flexible (permite notas muy anchas, muy altas o compactas)
        self.setMinimumSize(100, 70)

        # Restaurar dimensiones guardadas libremente
        saved_w = int(self.note_dict.get("width", 220))
        saved_h = int(self.note_dict.get("height", 180))
        self.resize(max(100, saved_w), max(70, saved_h))

        # Restaurar posición guardada si existe
        if "pos_x" in note_dict and "pos_y" in note_dict:
            self.move(int(note_dict["pos_x"]), int(note_dict["pos_y"]))
        else:
            screen = QApplication.primaryScreen().geometry()
            offset = len(parent_widget.floating_notes) * 30 if parent_widget else 0
            self.move(screen.width() - 280, 120 + offset)

        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)

        self.card = QFrame()
        self.card.setObjectName("StickyFrame")
        self.card.setMouseTracking(True)
        self.c_lay = QVBoxLayout(self.card)
        self.c_lay.setContentsMargins(10, 8, 10, 6)
        self.c_lay.setSpacing(4)

        # Header sutil de arrastre y cambio de color
        top_h = QHBoxLayout()
        top_h.setSpacing(4)
        
        self.lbl_pin = QLabel("📌")
        self.lbl_pin.setFont(QFont("Segoe UI Emoji", 10))
        top_h.addWidget(self.lbl_pin)

        lbl_drag_hint = QLabel("•••••")
        lbl_drag_hint.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        lbl_drag_hint.setStyleSheet("color: rgba(0,0,0,0.25);")
        lbl_drag_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_h.addWidget(lbl_drag_hint, 1)

        self.btn_color = QPushButton("🎨")
        self.btn_color.setToolTip("Cambiar color de la nota")
        self.btn_color.setFixedSize(20, 20)
        self.btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_color.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        self.btn_color.clicked.connect(self._cycle_color)
        top_h.addWidget(self.btn_color)

        self.c_lay.addLayout(top_h)

        # Campo de texto editable
        self.txt_edit = QPlainTextEdit(self.note_dict.get("text", ""))
        self.txt_edit.setStyleSheet("background: transparent; border: none;")
        self.txt_edit.textChanged.connect(self._on_text_changed)
        self.txt_edit.installEventFilter(self)
        self.c_lay.addWidget(self.txt_edit, 1)

        # Barra inferior con controles de tamaño de letra y redimensionamiento
        bottom_h = QHBoxLayout()
        bottom_h.setContentsMargins(0, 0, 0, 0)
        bottom_h.setSpacing(4)

        self.btn_font_dec = QPushButton("A-")
        self.btn_font_dec.setToolTip("Reducir tamaño de letra (Ctrl + Rueda abajo)")
        self.btn_font_dec.setFixedSize(22, 18)
        self.btn_font_dec.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_font_dec.clicked.connect(self._disminuir_fuente)
        bottom_h.addWidget(self.btn_font_dec)

        self.lbl_font_size = QLabel(f"{self.font_size}pt")
        self.lbl_font_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_h.addWidget(self.lbl_font_size)

        self.btn_font_inc = QPushButton("A+")
        self.btn_font_inc.setToolTip("Aumentar tamaño de letra (Ctrl + Rueda arriba)")
        self.btn_font_inc.setFixedSize(22, 18)
        self.btn_font_inc.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_font_inc.clicked.connect(self._aumentar_fuente)
        bottom_h.addWidget(self.btn_font_inc)

        bottom_h.addStretch()

        # Agarre visual de redimensionamiento nativo en esquina
        self.size_grip = QSizeGrip(self)
        self.size_grip.setToolTip("Arrastra para redimensionar libremente (ancho y alto)")
        self.size_grip.setFixedSize(14, 14)
        self.size_grip.setCursor(Qt.CursorShape.SizeFDiagCursor)
        bottom_h.addWidget(self.size_grip)

        self.c_lay.addLayout(bottom_h)

        lay.addWidget(self.card)
        self._apply_color()

    def eventFilter(self, obj, event):
        # Atajo cómodo: Ctrl + Rueda del ratón para agrandar/achicar letra
        if obj == self.txt_edit and event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                if delta > 0:
                    self._aumentar_fuente()
                elif delta < 0:
                    self._disminuir_fuente()
                return True
        return super().eventFilter(obj, event)

    def _aumentar_fuente(self):
        if self.font_size < 36:
            self.font_size += 1
            self._actualizar_tamano_fuente()

    def _disminuir_fuente(self):
        if self.font_size > 7:
            self.font_size -= 1
            self._actualizar_tamano_fuente()

    def _actualizar_tamano_fuente(self):
        self.note_dict["font_size"] = self.font_size
        if hasattr(self, "lbl_font_size"):
            self.lbl_font_size.setText(f"{self.font_size}pt")
        self._apply_color()
        if self.parent_widget:
            self.parent_widget.guardar_notas()

    def _apply_color(self):
        bg, fg, label = POSTIT_COLORS[self.note_dict.get("color_idx", 0) % len(POSTIT_COLORS)]
        self.card.setStyleSheet(f"""
            QFrame#StickyFrame {{
                background-color: {bg};
                color: {fg};
                border-radius: 10px;
                border: 1px solid rgba(0,0,0,0.15);
            }}
        """)
        self.txt_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                color: {fg};
                border: none;
                font-family: 'Segoe UI', sans-serif;
                font-size: {self.font_size}pt;
            }}
        """)
        btn_style = f"""
            QPushButton {{
                background: rgba(0, 0, 0, 0.12);
                color: {fg};
                border: none;
                border-radius: 3px;
                font-size: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(0, 0, 0, 0.22);
            }}
        """
        if hasattr(self, "btn_font_dec"):
            self.btn_font_dec.setStyleSheet(btn_style)
        if hasattr(self, "btn_font_inc"):
            self.btn_font_inc.setStyleSheet(btn_style)
        if hasattr(self, "lbl_font_size"):
            self.lbl_font_size.setStyleSheet(f"color: {fg}; font-size: 8px; font-weight: bold; background: transparent;")

    def _cycle_color(self):
        self.note_dict["color_idx"] = (self.note_dict.get("color_idx", 0) + 1) % len(POSTIT_COLORS)
        self._apply_color()
        if self.parent_widget:
            self.parent_widget.guardar_notas()
            self.parent_widget.cargar_notas()

    def _on_text_changed(self):
        self.note_dict["text"] = self.txt_edit.toPlainText()
        if self.parent_widget:
            self.parent_widget.guardar_notas()

    def _get_resize_edge(self, pos):
        """Detecta si el cursor está sobre algún borde para estirarlo libremente"""
        margin = 8
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()

        on_left = x <= margin
        on_right = x >= w - margin
        on_top = y <= margin
        on_bottom = y >= h - margin

        if on_top and on_left: return "top_left"
        if on_top and on_right: return "top_right"
        if on_bottom and on_left: return "bottom_left"
        if on_bottom and on_right: return "bottom_right"
        if on_left: return "left"
        if on_right: return "right"
        if on_top: return "top"
        if on_bottom: return "bottom"
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            edge = self._get_resize_edge(pos)
            if edge:
                self._resize_edge = edge
                self._resize_start_geom = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
                event.accept()
                return

            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            StickyNoteTrashOverlay.get_instance().show_trash()
            event.accept()

    def mouseMoveEvent(self, event):
        g_pos = event.globalPosition().toPoint()

        # Redimensionamiento por bordes (ancho, alto o ambos libremente)
        if self._resize_edge and self._resize_start_geom and self._resize_start_pos:
            dx = g_pos.x() - self._resize_start_pos.x()
            dy = g_pos.y() - self._resize_start_pos.y()
            geom = QRect(self._resize_start_geom)

            if "right" in self._resize_edge:
                geom.setWidth(max(100, self._resize_start_geom.width() + dx))
            elif "left" in self._resize_edge:
                new_w = max(100, self._resize_start_geom.width() - dx)
                geom.setLeft(self._resize_start_geom.right() - new_w)

            if "bottom" in self._resize_edge:
                geom.setHeight(max(70, self._resize_start_geom.height() + dy))
            elif "top" in self._resize_edge:
                new_h = max(70, self._resize_start_geom.height() - dy)
                geom.setTop(self._resize_start_geom.bottom() - new_h)

            self.setGeometry(geom)
            event.accept()
            return

        # Arrastre de posición de la nota
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = g_pos - self._drag_pos
            self.move(new_pos)
            StickyNoteTrashOverlay.get_instance().check_hover(g_pos)
            event.accept()
            return

        # Cursor dinámico de redimensionamiento
        edge = self._get_resize_edge(event.position().toPoint())
        if edge in ("left", "right"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge in ("top", "bottom"):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edge in ("top_left", "bottom_right"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge in ("top_right", "bottom_left"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_edge:
            self._resize_edge = None
            self._resize_start_geom = None
            self._resize_start_pos = None
            self.note_dict["width"] = self.width()
            self.note_dict["height"] = self.height()
            self.note_dict["pos_x"] = self.x()
            self.note_dict["pos_y"] = self.y()
            if self.parent_widget:
                self.parent_widget.guardar_notas()
            event.accept()
            return

        if self._drag_pos is not None:
            g_pos = event.globalPosition().toPoint()
            trash = StickyNoteTrashOverlay.get_instance()
            if trash.is_hovering(g_pos):
                trash.hide_trash()
                self.despegar_de_pantalla()
            else:
                trash.hide_trash()
                self.note_dict["pos_x"] = self.x()
                self.note_dict["pos_y"] = self.y()
                if self.parent_widget:
                    self.parent_widget.guardar_notas()
            self._drag_pos = None
            event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.note_dict["width"] = self.width()
        self.note_dict["height"] = self.height()
        if self.parent_widget:
            self.parent_widget.guardar_notas()

    def despegar_de_pantalla(self):
        if self.parent_widget and hasattr(self.parent_widget, "floating_notes"):
            note_id = id(self.note_dict)
            if note_id in self.parent_widget.floating_notes:
                del self.parent_widget.floating_notes[note_id]
        self.close()


class QuickStickyNotesWidget(QuickWidgetBase):
    """Submódulo de Notas Adhesivas Post-It Flotantes Múltiples"""
    def __init__(self, context, parent=None):
        super().__init__("postits", "📌 NOTAS ADHESIVAS", context, parent)
        self.ruta_json = Path(getattr(self.context, "ruta_usuario", ".")) / "sticky_notes.json"
        self.color_index = 0
        self.notes_data = []
        self.floating_notes = {}

        self.inicializar_ui()
        self.cargar_notas()

    def inicializar_ui(self):
        # Header de herramientas
        tb = QHBoxLayout()
        tb.setSpacing(6)

        btn_add = QPushButton("➕ Nueva Nota")
        btn_add.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border-radius: 5px; padding: 4px 10px; border: none;")
        btn_add.clicked.connect(self._agregar_nota)
        tb.addWidget(btn_add)

        tb.addStretch()

        self.lbl_count = QLabel("0 Notas")
        self.lbl_count.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px;")
        tb.addWidget(self.lbl_count)

        self.layout_contenido.addLayout(tb)

        # Scroll de notas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.container_w = QWidget()
        self.v_notes = QVBoxLayout(self.container_w)
        self.v_notes.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.v_notes.setSpacing(10)
        scroll.setWidget(self.container_w)

        self.layout_contenido.addWidget(scroll, 1)

    def cargar_notas(self):
        while self.v_notes.count():
            item = self.v_notes.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        self.notes_data = []
        if self.ruta_json.exists():
            try:
                with open(self.ruta_json, "r", encoding="utf-8") as f:
                    self.notes_data = json.load(f)
            except Exception: pass

        if not self.notes_data:
            self.notes_data = []

        for n in self.notes_data:
            self._render_card_nota(n)

        self._actualizar_contador()

    def guardar_notas(self):
        try:
            with open(self.ruta_json, "w", encoding="utf-8") as f:
                json.dump(self.notes_data, f, indent=4, ensure_ascii=False)
        except Exception: pass

    def _agregar_nota(self):
        c_idx = (len(self.notes_data)) % len(POSTIT_COLORS)
        nueva = {"text": "📝 Nueva nota adhesiva...", "color_idx": c_idx}
        self.notes_data.insert(0, nueva)
        self.guardar_notas()
        self.cargar_notas()

    def _render_card_nota(self, note_dict):
        bg, fg, label = POSTIT_COLORS[note_dict.get("color_idx", 0) % len(POSTIT_COLORS)]

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                color: {fg};
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        c_lay = QVBoxLayout(card)
        c_lay.setSpacing(4)

        top_r = QHBoxLayout()
        btn_color = QPushButton("🎨")
        btn_color.setFixedSize(20, 20)
        btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_color.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        btn_color.clicked.connect(lambda: self._cambiar_color_nota(note_dict))
        top_r.addWidget(btn_color)

        btn_pin_screen = QPushButton("📌 Pegar en pantalla")
        btn_pin_screen.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        btn_pin_screen.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pin_screen.setStyleSheet(f"background: rgba(0,0,0,0.12); color: {fg}; border-radius: 4px; padding: 2px 6px; border: none;")
        btn_pin_screen.clicked.connect(lambda: self._pegar_en_pantalla(note_dict))
        top_r.addWidget(btn_pin_screen)

        # Controles de tamaño de letra en la tarjeta
        font_sz = int(note_dict.get("font_size", 10))
        btn_dec = QPushButton("A-")
        btn_dec.setToolTip("Reducir tamaño de letra")
        btn_dec.setFixedSize(20, 18)
        btn_dec.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dec.setStyleSheet(f"background: rgba(0,0,0,0.1); color: {fg}; border: none; border-radius: 3px; font-size: 8px; font-weight: bold;")
        
        lbl_sz = QLabel(f"{font_sz}pt")
        lbl_sz.setStyleSheet(f"color: {fg}; font-size: 8px; font-weight: bold; background: transparent;")

        btn_inc = QPushButton("A+")
        btn_inc.setToolTip("Aumentar tamaño de letra")
        btn_inc.setFixedSize(20, 18)
        btn_inc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_inc.setStyleSheet(f"background: rgba(0,0,0,0.1); color: {fg}; border: none; border-radius: 3px; font-size: 8px; font-weight: bold;")

        def _cambiar_font_tarjeta(delta):
            actual = int(note_dict.get("font_size", 10))
            nuevo = max(7, min(36, actual + delta))
            note_dict["font_size"] = nuevo
            lbl_sz.setText(f"{nuevo}pt")
            txt_edit.setStyleSheet(f"background: transparent; color: {fg}; border: none; font-size: {nuevo}pt;")
            self.guardar_notas()
            n_id = id(note_dict)
            if n_id in self.floating_notes:
                win = self.floating_notes[n_id]
                win.font_size = nuevo
                win._actualizar_tamano_fuente()

        btn_dec.clicked.connect(lambda: _cambiar_font_tarjeta(-1))
        btn_inc.clicked.connect(lambda: _cambiar_font_tarjeta(1))

        top_r.addWidget(btn_dec)
        top_r.addWidget(lbl_sz)
        top_r.addWidget(btn_inc)

        top_r.addStretch()

        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(20, 20)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        btn_del.clicked.connect(lambda: self._borrar_nota(note_dict))
        top_r.addWidget(btn_del)

        c_lay.addLayout(top_r)

        txt_edit = QPlainTextEdit(note_dict.get("text", ""))
        txt_edit.setStyleSheet(f"background: transparent; color: {fg}; border: none; font-size: {font_sz}pt;")
        txt_edit.textChanged.connect(lambda: self._on_text_changed(note_dict, txt_edit.toPlainText()))
        c_lay.addWidget(txt_edit)

        self.v_notes.addWidget(card)

    def _pegar_en_pantalla(self, note_dict):
        note_id = id(note_dict)
        if note_id in self.floating_notes and self.floating_notes[note_id].isVisible():
            self.floating_notes[note_id].raise_()
            self.floating_notes[note_id].activateWindow()
            return
        win = StandaloneStickyNoteWindow(note_dict, self, self.colores)
        self.floating_notes[note_id] = win
        win.show()

    def _on_text_changed(self, note_dict, text):
        note_dict["text"] = text
        self.guardar_notas()

    def _cambiar_color_nota(self, note_dict):
        note_dict["color_idx"] = (note_dict.get("color_idx", 0) + 1) % len(POSTIT_COLORS)
        self.guardar_notas()
        self.cargar_notas()

    def _borrar_nota(self, note_dict):
        note_id = id(note_dict)
        if note_id in self.floating_notes:
            try:
                self.floating_notes[note_id].close()
            except Exception: pass
            del self.floating_notes[note_id]
        if note_dict in self.notes_data:
            self.notes_data.remove(note_dict)
            self.guardar_notas()
            self.cargar_notas()

    def _actualizar_contador(self):
        self.lbl_count.setText(f"{len(self.notes_data)} Notas")


# ==============================================================================
# SUBMÓDULO 2: QUICK LAUNCHER (Lanzador Rápido de Aplicaciones y Enlaces)
# ==============================================================================
DEFAULT_LAUNCHER = [
    {"name": "Explorador", "icon": "📁", "action": "cmd:explorer.exe"},
    {"name": "Calculadora", "icon": "🧮", "action": "cmd:calc.exe"},
    {"name": "Bloc de Notas", "icon": "📝", "action": "cmd:notepad.exe"},
    {"name": "Google Chrome", "icon": "🌐", "action": "url:https://google.com"},
    {"name": "YouTube", "icon": "▶️", "action": "url:https://youtube.com"},
    {"name": "Carpeta Usuario", "icon": "🏠", "action": "folder:home"}
]

class QuickLauncherWidget(QuickWidgetBase):
    """Submódulo Lanzador Rápido de Accesos Directos"""
    def __init__(self, context, parent=None):
        super().__init__("launcher", "🚀 LANZADOR RÁPIDO", context, parent)
        self.ruta_json = Path(getattr(self.context, "ruta_usuario", ".")) / "quick_launcher.json"
        self.items = []

        self.inicializar_ui()
        self.cargar_items()

    def inicializar_ui(self):
        tb = QHBoxLayout()
        btn_add = QPushButton("➕ Agregar Acceso")
        btn_add.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border-radius: 5px; padding: 4px 10px; border: none;")
        btn_add.clicked.connect(self._agregar_acceso)
        tb.addWidget(btn_add)
        tb.addStretch()

        self.layout_contenido.addLayout(tb)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.container_w = QWidget()
        self.grid = QGridLayout(self.container_w)
        self.grid.setSpacing(8)
        scroll.setWidget(self.container_w)

        self.layout_contenido.addWidget(scroll, 1)

    def cargar_items(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        self.items = []
        if self.ruta_json.exists():
            try:
                with open(self.ruta_json, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
            except Exception: pass

        if not self.items:
            self.items = list(DEFAULT_LAUNCHER)

        for idx, item_data in enumerate(self.items):
            btn = QPushButton(f"{item_data.get('icon', '⚡')}\n{item_data.get('name', 'Acceso')}")
            btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            btn.setFixedSize(110, 75)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores.get('bg_secundario', '#1E1E2E')};
                    color: white;
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    border: 1.5px solid {self.colores.get('acento', '#6366F1')};
                    background: rgba(99,102,241,0.15);
                }}
            """)
            btn.clicked.connect(lambda ch, data=item_data: self._ejecutar_acceso(data))
            r, c = idx // 3, idx % 3
            self.grid.addWidget(btn, r, c)

    def guardar_items(self):
        try:
            with open(self.ruta_json, "w", encoding="utf-8") as f:
                json.dump(self.items, f, indent=4, ensure_ascii=False)
        except Exception: pass

    def _ejecutar_acceso(self, item_data):
        action = item_data.get("action", "")
        try:
            if action.startswith("cmd:"):
                subprocess.Popen(action[4:], shell=True)
            elif action.startswith("url:"):
                QDesktopServices.openUrl(QUrl(action[4:]))
            elif action == "folder:home":
                os.startfile(str(self.context.ruta_usuario))
        except Exception as e:
            QMessageBox.warning(self, "Error Ejecución", f"No se pudo ejecutar:\n{e}")

    def _agregar_acceso(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Aplicación o Archivo", "", "Ejecutables (*.exe);;Todos (*.*)")
        if file_path:
            name = Path(file_path).stem.capitalize()
            self.items.append({"name": name, "icon": "⚙️", "action": f"cmd:\"{file_path}\""})
            self.guardar_items()
            self.cargar_items()


# ==============================================================================
# SUBMÓDULO 3: SYSTEM MONITOR HUD (HUD de Rendimiento de Recursos Minimalista)
# ==============================================================================
class QuickSystemHUDWidget(QuickWidgetBase):
    """Submódulo HUD de Rendimiento de Recursos de Sistema en Tiempo Real"""
    def __init__(self, context, parent=None):
        super().__init__("syshud", "💻 HUD DE SISTEMA", context, parent)
        self.inicializar_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._actualizar_metricas)
        self.timer.start(1000)
        self._actualizar_metricas()

    def inicializar_ui(self):
        main_box = QFrame()
        main_box.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; border-radius: 10px; padding: 10px;")
        box_lay = QVBoxLayout(main_box)
        box_lay.setSpacing(8)

        # Metrica CPU
        self.lbl_cpu = QLabel("🧠 CPU: 0%")
        self.lbl_cpu.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_cpu.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        box_lay.addWidget(self.lbl_cpu)

        # Metrica RAM
        self.lbl_ram = QLabel("💾 RAM: 0%")
        self.lbl_ram.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_ram.setStyleSheet("color: #34D399;")
        box_lay.addWidget(self.lbl_ram)

        # Metrica Disco / Batería
        self.lbl_disco = QLabel("💽 Disco C: 0%")
        self.lbl_disco.setFont(QFont("Segoe UI", 9))
        self.lbl_disco.setStyleSheet("color: #FBBF24;")
        box_lay.addWidget(self.lbl_disco)

        # Metrica Bateria
        self.lbl_bat = QLabel("🔋 Batería: --")
        self.lbl_bat.setFont(QFont("Segoe UI", 9))
        self.lbl_bat.setStyleSheet("color: #AAB0B8;")
        box_lay.addWidget(self.lbl_bat)

        self.layout_contenido.addWidget(main_box)

    def _actualizar_metricas(self):
        try:
            cpu_p = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            bat = psutil.sensors_battery()

            self.lbl_cpu.setText(f"🧠 CPU: {cpu_p:.1f}%")
            self.lbl_ram.setText(f"💾 RAM: {ram.percent:.1f}% ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)")
            self.lbl_disco.setText(f"💽 Disco C: {disk.percent:.1f}% libre: {disk.free // (1024**3)}GB")

            if bat:
                estado = "⚡ Cargando" if bat.power_plugged else "🔋 Batería"
                self.lbl_bat.setText(f"{estado}: {bat.percent:.0f}%")
            else:
                self.lbl_bat.setText("🔌 Conectado a AC")
        except Exception: pass
