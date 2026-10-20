import random
import os
import platform
from PIL import Image, ImageDraw
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QGridLayout, QColorDialog,
    QFrame, QApplication
)
from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QFont, QColor, QPalette, QPainter, QBrush, QPen

class PixelCanvas(QWidget):
    """Canvas interactivo para Pixel Art con soporte de arrastre"""
    def __init__(self, size_px=16, parent=None):
        super().__init__(parent)
        self.grid_size = size_px
        self.setFixedSize(320, 320)
        self.pixels = [[None for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.current_color = "#000000"
        self.is_drawing = False
        self.setMouseTracking(True)

    def set_grid_size(self, size):
        self.grid_size = size
        self.pixels = [[None for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        cell_w = self.width() / self.grid_size
        cell_h = self.height() / self.grid_size
        
        # Fondo y Grid
        painter.fillRect(self.rect(), QColor("white"))
        painter.setPen(QPen(QColor("#E0E0E0"), 0.5))
        
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                rect = QRect(int(x * cell_w), int(y * cell_h), int(cell_w), int(cell_h))
                color_hex = self.pixels[y][x]
                if color_hex:
                    painter.fillRect(rect, QColor(color_hex))
                painter.drawRect(rect)

    def _get_pixel_at(self, pos):
        cell_w = self.width() / self.grid_size
        cell_h = self.height() / self.grid_size
        x = int(pos.x() // cell_w)
        y = int(pos.y() // cell_h)
        if 0 <= x < self.grid_size and 0 <= y < self.grid_size:
            return x, y
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = True
            pos = self._get_pixel_at(event.position())
            if pos:
                self.pixels[pos[1]][pos[0]] = self.current_color
                self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            pos = self._get_pixel_at(event.position())
            if pos:
                self.pixels[pos[1]][pos[0]] = self.current_color
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = False

class AvatarEditor(QDialog):
    """Editor de Avatar estilo PixelArt con soporte de arrastre y píxeles cuadrados"""
    def __init__(self, parent, callback_save):
        super().__init__(parent)
        self.setWindowTitle("Editor de Pixel Art")
        self.setFixedSize(450, 650)
        
        self.callback_save = callback_save
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        
        self.palette = [
            "#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF", 
            "#FFFF00", "#00FFFF", "#FF00FF", "#808080", "#C0C0C0",
            "#800000", "#808000", "#008000", "#800080", "#008080", "#000080"
        ]
        
        self.setup_ui()
        self.center_window()

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.left() + (screen.width() - self.width()) // 2
        y = screen.top() + (screen.height() - self.height()) // 2
        self.move(x, y)

    def setup_ui(self):
        self.setStyleSheet("background-color: #1E1E1E; color: white;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        header = QHBoxLayout()
        lbl_title = QLabel("Pixel Art Studio")
        lbl_title.setFont(QFont(self.font_family, 14, QFont.Weight.Bold))
        header.addWidget(lbl_title)
        
        self.btn_resize = QPushButton("16x16")
        self.btn_resize.setFixedSize(80, 25)
        self.btn_resize.clicked.connect(self.toggle_size)
        header.addWidget(self.btn_resize)
        main_layout.addLayout(header)

        # Canvas
        self.canvas = PixelCanvas(16, self)
        main_layout.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignCenter)

        # Hint
        lbl_hint = QLabel("Mantén click para dibujar • Cuadrados perfectos")
        lbl_hint.setStyleSheet("color: #888; font-size: 10px;")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(lbl_hint)

        # Paleta
        grid_pal = QGridLayout()
        grid_pal.setSpacing(5)
        for i, color in enumerate(self.palette):
            btn = QPushButton()
            btn.setFixedSize(35, 35)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {color}; border: 2px solid #333; border-radius: 4px;")
            btn.clicked.connect(lambda checked, c=color: self.set_color(c))
            grid_pal.addWidget(btn, i//8, i%8)
        main_layout.addLayout(grid_pal)

        # Acciones
        controls = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(40, 40)
        self.color_preview.setStyleSheet("background-color: #000; border: 2px solid white; border-radius: 20px;")
        controls.addWidget(self.color_preview)

        btn_pick = QPushButton("Color...")
        btn_pick.clicked.connect(self.pick_custom_color)
        controls.addWidget(btn_pick)

        btn_eraser = QPushButton("Borrador")
        btn_eraser.clicked.connect(lambda: self.set_color(None))
        controls.addWidget(btn_eraser)
        
        btn_clear = QPushButton("Limpiar")
        btn_clear.clicked.connect(lambda: self.canvas.set_grid_size(self.canvas.grid_size))
        controls.addWidget(btn_clear)
        main_layout.addLayout(controls)

        # Footer
        footer = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        footer.addWidget(btn_cancel)
        
        btn_save = QPushButton("LISTO")
        btn_save.setMinimumHeight(45)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("background-color: #6366F1; color: white; border-radius: 8px; font-weight: bold;")
        btn_save.clicked.connect(self.save_and_close)
        footer.addWidget(btn_save)
        main_layout.addLayout(footer)

    def set_color(self, color):
        self.canvas.current_color = color
        display_color = color if color else "white"
        self.color_preview.setStyleSheet(f"background-color: {display_color}; border: 2px solid white; border-radius: 20px;")

    def pick_custom_color(self):
        color = QColorDialog.getColor(QColor(self.canvas.current_color or "white"), self)
        if color.isValid():
            self.set_color(color.name())

    def toggle_size(self):
        new_size = 32 if self.canvas.grid_size == 16 else 16
        self.canvas.set_grid_size(new_size)
        self.btn_resize.setText(f"{new_size}x{new_size}")

    def save_and_close(self):
        grid = self.canvas.pixels
        res = self.canvas.grid_size
        img = Image.new('RGBA', (res, res), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for y in range(res):
            for x in range(res):
                if grid[y][x]:
                    draw.point((x, y), fill=grid[y][x])
        self.callback_save(img)
        self.accept()

class AvatarGenerator:
    @staticmethod
    def generate_letter_avatar(letter, background_color="#4A86E8", text_color="white", size=128):
        img = Image.new('RGB', (size, size), background_color)
        draw = ImageDraw.Draw(img)
        try:
            from PIL import ImageFont
            font_list = ["arial.ttf", "DejaVuSans.ttf", "Helvetica.ttf", "FreeSans.ttf", "Arial"]
            font = None
            for f_name in font_list:
                try:
                    font = ImageFont.truetype(f_name, int(size * 0.6))
                    break
                except:
                    continue
            if not font: font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), letter.upper(), font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(((size - w) / 2, (size - h) / 2 - (h*0.1)), letter.upper(), font=font, fill=text_color)
        except: pass
        return img

    @staticmethod
    def save_avatar_file(image, persona):
        from controlador.utils.paths import get_user_path
        user_path = get_user_path(persona)
        user_path.mkdir(parents=True, exist_ok=True)
        avatar_path = user_path / "avatar.png"
        image.save(str(avatar_path))
        return str(avatar_path)
