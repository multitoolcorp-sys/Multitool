import os
import shutil
import base64
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QGridLayout,
    QFileDialog, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap

EMOJIS_CATEGORIAS = {
    "😀 Caras": ["😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚", "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🤩", "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣", "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬", "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰", "😥", "😓"],
    "👍 Gestos": ["👍", "👎", "👏", "🙌", "👐", "🤲", "🤝", "🙏", "✍️", "💅", "🤳", "💪", "🦾", "🦿", "🦵", "🦶", "👂", "🦻", "👃", "🧠", "🦷", "🦴", "👀", "👁️", "👅", "👄", "👶", "🧒", "👦", "👧", "🧑", "👱", "👨", "🧔", "👨‍🦰", "👨‍🦱", "👨‍🦳", "👨‍🦲", "👩", "👩‍🦰", "👩‍🦱", "👩‍🦳", "👩‍🦲"],
    "⚡ Símbolos": ["⚡", "🔥", "✨", "🌟", "💫", "💥", "💢", "💦", "💧", "💨", "🕊️", "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟", "☮️", "✝️", "☪️", "🕉️", "☸️", "✡️", "🔯", "🕎", "☯️", "☦️", "🛐", "⛎", "♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"],
    "📦 Objetos": ["📱", "📲", "💻", "⌨️", "🖥️", "🖨️", "🖱️", "🖲️", "🕹️", "🗜️", "💽", "💾", "💿", "📀", "📼", "📷", "📸", "📹", "🎥", "📽️", "🎞️", "📞", "☎️", "📟", "📠", "📺", "📻", "🎙️", "🎚️", "🎛️", "⏱️", "⏲️", "⏰", "🕰️", "⌛", "⏳", "📡", "🔋", "🔌", "💡", "🔦", "🕯️", "🧯", "🗑️", "🛢️", "🛒"]
}

class StickersEmojisSubmodule(QWidget):
    """Submódulo 3: Galería & Creador de Stickers Personalizados y Selector de Emojis"""
    def __init__(self, parent, context, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.ruta_stickers = self.ruta_usuario / "stickers"
        self.ruta_stickers.mkdir(parents=True, exist_ok=True)

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#1E1E1E')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#4CAF50')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_tit = QLabel("🎨 GALERÍA DE STICKERS Y EMOJIS")
        lbl_tit.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        hdr.addWidget(lbl_tit)
        hdr.addStretch()

        btn_add_sticker = QPushButton("➕ Crear Nuevo Sticker")
        btn_add_sticker.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_add_sticker.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_sticker.setStyleSheet(f"""
            QPushButton {{
                background: {exito}; color: white; border-radius: 8px; padding: 8px 16px; border: none;
            }}
            QPushButton:hover {{ background: #3b8e5c; }}
        """)
        btn_add_sticker.clicked.connect(self._crear_sticker_dialog)
        hdr.addWidget(btn_add_sticker)

        layout.addLayout(hdr)

        # Tab Widget Interno para Emojis vs Stickers
        self.tab_inner = QTabWidget()
        self.tab_inner.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; background: {bg_sec}; }}
            QTabBar::tab {{ background: {bg_sec}; color: #AAB0B8; padding: 8px 16px; font-weight: bold; font-size: 11px; }}
            QTabBar::tab:selected {{ background: {acento}; color: white; border-radius: 6px; }}
        """)

        # Pestaña 1: Emojis
        w_emojis = self._build_emojis_tab()
        self.tab_inner.addTab(w_emojis, "😀 Emojis")

        # Pestaña 2: Stickers Personalizados
        self.w_stickers = self._build_stickers_tab()
        self.tab_inner.addTab(self.w_stickers, "🏷️ Mis Stickers")

        layout.addWidget(self.tab_inner, 1)

    def _build_emojis_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(15, 15, 15, 15)

        tabs_cat = QTabWidget()
        tabs_cat.setStyleSheet("QTabBar::tab { font-size: 10px; padding: 6px 12px; }")

        for cat_name, list_emoji in EMOJIS_CATEGORIAS.items():
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("background: transparent; border: none;")
            
            grid_w = QWidget()
            g_lay = QGridLayout(grid_w)
            g_lay.setSpacing(8)

            row, col = 0, 0
            for emo in list_emoji:
                btn = QPushButton(emo)
                btn.setFont(QFont("Segoe UI Emoji", 16))
                btn.setFixedSize(45, 45)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; }
                    QPushButton:hover { background: rgba(99, 102, 241, 0.3); border: 1px solid #6366F1; }
                """)
                btn.clicked.connect(lambda ch, e=emo: self._on_emoji_click(e))
                g_lay.addWidget(btn, row, col)
                col += 1
                if col >= 10:
                    col = 0
                    row += 1

            scroll.setWidget(grid_w)
            tabs_cat.addTab(scroll, cat_name)

        lay.addWidget(tabs_cat)
        return w

    def _build_stickers_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(15, 15, 15, 15)

        self.scroll_stickers = QScrollArea()
        self.scroll_stickers.setWidgetResizable(True)
        self.scroll_stickers.setStyleSheet("background: transparent; border: none;")

        self.grid_stickers_w = QWidget()
        self.g_stickers_lay = QGridLayout(self.grid_stickers_w)
        self.g_stickers_lay.setSpacing(12)

        self.cargar_stickers_galeria()

        self.scroll_stickers.setWidget(self.grid_stickers_w)
        lay.addWidget(self.scroll_stickers)
        return w

    def cargar_stickers_galeria(self):
        # Limpiar grid anterior
        while self.g_stickers_lay.count():
            item = self.g_stickers_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        files = sorted(list(self.ruta_stickers.glob("*.*")))
        if not files:
            lbl_empty = QLabel("No tienes stickers guardados aún.\n¡Haz clic en '➕ Crear Nuevo Sticker' para agregar tus imágenes!")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 12px;")
            self.g_stickers_lay.addWidget(lbl_empty, 0, 0, 1, 4)
            return

        row, col = 0, 0
        for fpath in files:
            if fpath.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
                card = QFrame()
                card.setFixedSize(110, 110)
                card.setStyleSheet(f"""
                    QFrame {{
                        background: rgba(30, 30, 46, 0.6);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 10px;
                    }}
                    QFrame:hover {{
                        border: 1px solid {self.colores.get('acento', '#6366F1')};
                    }}
                """)
                c_lay = QVBoxLayout(card)
                c_lay.setContentsMargins(6, 6, 6, 6)

                btn_img = QPushButton()
                pix = QPixmap(str(fpath)).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                btn_img.setIcon(QIcon(pix))
                btn_img.setIconSize(QSize(80, 80))
                btn_img.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_img.setStyleSheet("background: transparent; border: none;")
                btn_img.clicked.connect(lambda ch, p=str(fpath): self._on_sticker_click(p))
                c_lay.addWidget(btn_img, 1, Qt.AlignmentFlag.AlignCenter)

                self.g_stickers_lay.addWidget(card, row, col)
                col += 1
                if col >= 6:
                    col = 0
                    row += 1

    def _crear_sticker_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen para Sticker", "",
            "Imágenes (*.png *.jpg *.jpeg *.webp *.gif)"
        )
        if path:
            dest = self.ruta_stickers / Path(path).name
            shutil.copy(path, dest)
            QMessageBox.information(self, "Sticker Creado", f"¡Sticker '{dest.name}' guardado con éxito en tu biblioteca!")
            self.cargar_stickers_galeria()
            self.tab_inner.setCurrentIndex(1)

    def guardar_sticker_externo(self, ruta_o_bytes):
        """Permite guardar un sticker recibido por chat directamente"""
        try:
            if isinstance(ruta_o_bytes, str) and os.path.exists(ruta_o_bytes):
                dest = self.ruta_stickers / Path(ruta_o_bytes).name
                shutil.copy(ruta_o_bytes, dest)
            elif isinstance(ruta_o_bytes, bytes):
                fname = f"sticker_{len(list(self.ruta_stickers.glob('*')))+1}.png"
                dest = self.ruta_stickers / fname
                with open(dest, "wb") as f:
                    f.write(ruta_o_bytes)
            self.cargar_stickers_galeria()
            return True
        except Exception as e:
            print(f"[Stickers] Error guardando sticker: {e}")
            return False

    def _on_emoji_click(self, emoji):
        if "insertar_emoji" in self.callbacks:
            self.callbacks["insertar_emoji"](emoji)

    def _on_sticker_click(self, path):
        if "enviar_sticker" in self.callbacks:
            self.callbacks["enviar_sticker"](path)
