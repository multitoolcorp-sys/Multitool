import os
import shutil
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QMessageBox, QFileDialog,
    QTabWidget, QScrollArea, QGridLayout, QStackedWidget
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap

from ..utils.chat_display import ChatDisplay

EMOJIS_RAPIDOS = {
    "😀 Caras": ["😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😋", "😛", "😜", "🤪", "😎", "🤩", "🥳", "😏", "😒", "😞", "😔", "😟", "😭", "😤", "😠", "😡", "🤯", "😳", "😱"],
    "👍 Gestos": ["👍", "👎", "👏", "🙌", "👐", "🤲", "🤝", "🙏", "✍️", "💪", "🦾", "👂", "👃", "🧠", "👀", "👁️", "👅", "👄"],
    "⚡ Símbolos": ["⚡", "🔥", "✨", "🌟", "💫", "💥", "💢", "💦", "💧", "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "💔", "❣️", "💕", "💞", "💓", "💗", "💖"],
    "📦 Objetos": ["📱", "💻", "⌨️", "🖥️", "📷", "📸", "🎥", "📺", "📻", "🎙️", "⏰", "📡", "🔋", "💡", "🔦", "🗑️", "🛒"]
}


class SalaChatSubmodule(QWidget):
    """Submódulo 1: Sala de Mensajería en Tiempo Real con Panel Flotante de Emojis/Stickers Integrado"""
    def __init__(self, parent, context, colores, callbacks, manager, chat_input_widget):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.manager = manager
        self.txt_input = chat_input_widget
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.ruta_stickers = self.ruta_usuario / "stickers"
        self.ruta_stickers.mkdir(parents=True, exist_ok=True)

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#1E1E1E')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        bg_terc = self.colores.get('bg_terciario', '#3D3D3D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#4CAF50')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Display del Chat (Fondo WhatsApp)
        self.display = ChatDisplay(colores=self.colores)

        # Header de Sala (Estilo WhatsApp)
        self.header = QFrame()
        self.header.setFixedHeight(50)
        self.header.setStyleSheet("""
            QFrame {
                background-color: #202C33;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        h_lay = QHBoxLayout(self.header)
        h_lay.setContentsMargins(16, 0, 16, 0)
        h_lay.setSpacing(10)

        icon_chat = QLabel("💬")
        icon_chat.setFont(QFont(self.font_family, 14))
        h_lay.addWidget(icon_chat)

        self.lbl_contacto = QLabel("CHAT DE RED LOCAL (LAN)")
        self.lbl_contacto.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_contacto.setStyleSheet("color: #E9EDEF; border: none;")
        h_lay.addWidget(self.lbl_contacto)

        h_lay.addStretch()

        # Controles de Zoom de Texto
        zoom_frame = QFrame()
        zoom_frame.setFixedHeight(28)
        zoom_frame.setStyleSheet("""
            QFrame {
                background: #2A3942;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
            }
            QPushButton {
                background: transparent;
                color: #E9EDEF;
                border: none;
                padding: 0 7px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #25D366;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
        """)
        z_lay = QHBoxLayout(zoom_frame)
        z_lay.setContentsMargins(4, 0, 4, 0)
        z_lay.setSpacing(2)

        self.btn_zoom_out = QPushButton("A-")
        self.btn_zoom_out.setToolTip("Disminuir tamaño de letra (Ctrl + - / Ctrl + Rueda)")
        self.btn_zoom_out.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zoom_out.clicked.connect(self.display.zoom_out)
        z_lay.addWidget(self.btn_zoom_out)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setToolTip("Tamaño actual de letra (Clic para restablecer a 100%)")
        self.lbl_zoom.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_zoom.setStyleSheet("color: #00A884; border: none; padding: 0 4px;")
        self.lbl_zoom.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_zoom.mousePressEvent = lambda e: self.display.reset_zoom()
        z_lay.addWidget(self.lbl_zoom)

        self.btn_zoom_in = QPushButton("A+")
        self.btn_zoom_in.setToolTip("Aumentar tamaño de letra (Ctrl + + / Ctrl + Rueda)")
        self.btn_zoom_in.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zoom_in.clicked.connect(self.display.zoom_in)
        z_lay.addWidget(self.btn_zoom_in)

        h_lay.addWidget(zoom_frame)
        self.display.zoom_changed.connect(lambda pct: self.lbl_zoom.setText(f"{pct}%"))

        btn_export = QPushButton("💾 Guardar Chat")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setFixedHeight(28)
        btn_export.setStyleSheet("""
            QPushButton {
                background: #2A3942; color: #E9EDEF;
                border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 14px;
                padding: 0 12px; font-size: 10px; font-weight: bold;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.15); }
        """)
        btn_export.clicked.connect(self.callbacks.get("exportar_chat", lambda: None))
        h_lay.addWidget(btn_export)

        self.lbl_estado = QLabel("🔴 DESCONECTADO")
        self.lbl_estado.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_estado.setStyleSheet("color: #F87171; border: none; padding-left: 6px;")
        h_lay.addWidget(self.lbl_estado)

        # ── DRAWER / PANEL INLINE DESPLEGABLE DE EMOJIS Y STICKERS ──
        self.drawer_panel = QFrame()
        self.drawer_panel.setFixedHeight(220)
        self.drawer_panel.setStyleSheet("""
            QFrame {
                background-color: #111B21;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
        """)
        self.drawer_panel.hide()  # Oculto por defecto

        d_lay = QVBoxLayout(self.drawer_panel)
        d_lay.setContentsMargins(10, 8, 10, 8)

        self.drawer_tabs = QTabWidget()
        self.drawer_tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab { background: #2A3942; color: #AAB0B8; padding: 5px 12px; font-weight: bold; font-size: 10px; border-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #00A884; color: white; }
        """)

        # Tab 1: Emojis Rápidos
        w_emo = self._build_inline_emojis()
        self.drawer_tabs.addTab(w_emo, "😀 Emojis")

        # Tab 2: Stickers Rápidos
        self.w_stk = self._build_inline_stickers()
        self.drawer_tabs.addTab(self.w_stk, "🏷️ Mis Stickers")

        d_lay.addWidget(self.drawer_tabs)

        # Panel Inferior de Entrada & Botones (Estilo Barra Inferior WhatsApp)
        input_container = QFrame()
        input_container.setStyleSheet("background-color: #202C33; border-top: 1px solid rgba(255, 255, 255, 0.08);")
        in_lay = QVBoxLayout(input_container)
        in_lay.setContentsMargins(14, 8, 14, 10)
        in_lay.setSpacing(6)

        # Fila de Acciones Rápidas (Adjuntar Foto, Archivo, Emojis/Stickers)
        act_lay = QHBoxLayout()
        act_lay.setSpacing(8)

        btn_foto = QPushButton("📷 Foto")
        btn_foto.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_foto.setStyleSheet("background: #2A3942; color: #E9EDEF; border-radius: 12px; padding: 4px 10px; font-size: 11px; border: none;")
        btn_foto.clicked.connect(self.callbacks.get("enviar_imagen", lambda: None))
        act_lay.addWidget(btn_foto)

        btn_file = QPushButton("📎 Archivo")
        btn_file.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_file.setStyleSheet("background: #2A3942; color: #E9EDEF; border-radius: 12px; padding: 4px 10px; font-size: 11px; border: none;")
        btn_file.clicked.connect(self.callbacks.get("enviar_archivo", lambda: None))
        act_lay.addWidget(btn_file)

        self.btn_toggle_drawer = QPushButton("😀 Emojis & Stickers")
        self.btn_toggle_drawer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_drawer.setStyleSheet("""
            QPushButton {
                background: #2A3942; color: #25D366;
                border-radius: 12px; padding: 4px 12px; font-size: 11px;
                border: 1px solid rgba(37, 211, 102, 0.3); font-weight: bold;
            }
            QPushButton:hover { background: rgba(37, 211, 102, 0.2); }
        """)
        self.btn_toggle_drawer.clicked.connect(self._toggle_drawer)
        act_lay.addWidget(self.btn_toggle_drawer)

        act_lay.addStretch()
        in_lay.addLayout(act_lay)

        # Fila del Editor de Texto & Botón Enviar WhatsApp
        msg_row = QHBoxLayout()
        msg_row.setSpacing(10)
        msg_row.addWidget(self.txt_input, 1)

        self.btn_send = QPushButton("➤")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setFixedSize(38, 38)
        self.btn_send.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        self.btn_send.setToolTip("Enviar mensaje")
        self.btn_send.setStyleSheet("""
            QPushButton {
                background: #00A884; color: white; border-radius: 19px; border: none;
            }
            QPushButton:hover { background: #06CF9C; }
            QPushButton:disabled { background: #2A3942; color: #777; }
        """)
        self.btn_send.clicked.connect(self.callbacks.get("enviar_mensaje", lambda: None))
        msg_row.addWidget(self.btn_send)

        in_lay.addLayout(msg_row)

        # ── PÁGINA 1: SALA DE CHAT ACTIVA (Header, Display, Drawer, Input) ──
        self.widget_chat_activo = QWidget()
        act_vlay = QVBoxLayout(self.widget_chat_activo)
        act_vlay.setContentsMargins(0, 0, 0, 0)
        act_vlay.setSpacing(0)
        act_vlay.addWidget(self.header)
        act_vlay.addWidget(self.display, 1)
        act_vlay.addWidget(self.drawer_panel)
        act_vlay.addWidget(input_container)

        # ── PÁGINA 0: VISTA VACÍA / POR DEFECTO (Estilo WhatsApp Desktop Sin Selección) ──
        self.widget_vacio = self._build_widget_vacio()

        # Stack Principal para alternar entre pantalla vacía y chat activo
        self.stack_sala = QStackedWidget()
        self.stack_sala.addWidget(self.widget_vacio)       # 0: Sin selección / por defecto
        self.stack_sala.addWidget(self.widget_chat_activo) # 1: Chat activo
        layout.addWidget(self.stack_sala)

        # Iniciar en vista vacía sin selección por defecto (estilo notas)
        self.stack_sala.setCurrentWidget(self.widget_vacio)

    def _build_widget_vacio(self):
        """Construye la vista de bienvenida sin conversación activa (estilo WhatsApp Desktop)"""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(14)

        ico_empty = QLabel("💬")
        ico_empty.setFont(QFont("Segoe UI Emoji", 48))
        ico_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico_empty.setStyleSheet("background: transparent; color: #00A884;")
        lay.addWidget(ico_empty)

        lbl_tit = QLabel("MultiTool Chat LAN")
        lbl_tit.setFont(QFont(self.font_family, 18, QFont.Weight.Bold))
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_tit.setStyleSheet("color: #E9EDEF; border: none;")
        lay.addWidget(lbl_tit)

        lbl_sub = QLabel(
            "Conéctate a una red LAN o inicia tu propia sala para comenzar a chatear en tiempo real, "
            "compartir archivos, fotos y stickers de forma segura sin salir de tu red local."
        )
        lbl_sub.setFont(QFont(self.font_family, 10))
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("color: #8696A0; max-width: 480px; border: none; line-height: 1.4;")
        lay.addWidget(lbl_sub)

        lay.addSpacing(6)

        # Botones de Acción Rápida (para no presionar botones innecesarios en la sala)
        row_quick = QHBoxLayout()
        row_quick.setSpacing(10)
        row_quick.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_q_lan = QPushButton("🌐 Iniciar / Unirse a LAN")
        btn_q_lan.setFixedHeight(36)
        btn_q_lan.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_q_lan.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_lan.setStyleSheet("""
            QPushButton {
                background: #00A884; color: white; border-radius: 18px; padding: 0 18px; border: none;
            }
            QPushButton:hover { background: #06CF9C; }
        """)
        btn_q_lan.clicked.connect(lambda: self.callbacks.get("cambiar_tab", lambda idx: None)(1))
        row_quick.addWidget(btn_q_lan)

        btn_q_hist = QPushButton("📜 Historial Guardado")
        btn_q_hist.setFixedHeight(36)
        btn_q_hist.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_q_hist.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_hist.setStyleSheet("""
            QPushButton {
                background: #202C33; color: #E9EDEF; border-radius: 18px; padding: 0 16px; border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover { background: #2A3942; }
        """)
        btn_q_hist.clicked.connect(lambda: self.callbacks.get("cambiar_tab", lambda idx: None)(3))
        row_quick.addWidget(btn_q_hist)

        btn_q_ai = QPushButton("🤖 Asistente IA")
        btn_q_ai.setFixedHeight(36)
        btn_q_ai.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_q_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_ai.setStyleSheet("""
            QPushButton {
                background: #202C33; color: #53BDEB; border-radius: 18px; padding: 0 16px; border: 1px solid rgba(83, 189, 235, 0.3);
            }
            QPushButton:hover { background: rgba(83, 189, 235, 0.15); }
        """)
        btn_q_ai.clicked.connect(lambda: self.callbacks.get("cambiar_tab", lambda idx: None)(4))
        row_quick.addWidget(btn_q_ai)

        lay.addLayout(row_quick)

        lay.addSpacing(10)

        lbl_sec = QLabel("🔒 Cifrado y comunicación directa punto a punto (P2P)")
        lbl_sec.setFont(QFont(self.font_family, 9))
        lbl_sec.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sec.setStyleSheet("color: rgba(255, 255, 255, 0.35); border: none;")
        lay.addWidget(lbl_sec)

        lbl_esc = QLabel("💡 Presiona la tecla Esc para volver a esta pantalla cuando lo desees")
        lbl_esc.setFont(QFont(self.font_family, 8))
        lbl_esc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_esc.setStyleSheet("color: rgba(255, 255, 255, 0.22); border: none;")
        lay.addWidget(lbl_esc)

        return w

    def mostrar_vista_vacia(self):
        """Muestra la vista por defecto (sin sala o conexión activa)"""
        self.stack_sala.setCurrentWidget(self.widget_vacio)

    def mostrar_chat_activo(self):
        """Muestra la sala de chat activa con todos los controles"""
        self.stack_sala.setCurrentWidget(self.widget_chat_activo)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.mostrar_vista_vacia()
            event.accept()
            return
        super().keyPressEvent(event)

    def _toggle_drawer(self):
        visible = not self.drawer_panel.isVisible()
        self.drawer_panel.setVisible(visible)
        if visible:
            self.recargar_stickers_inline()

    def _build_inline_emojis(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 5, 0, 0)

        tabs_cat = QTabWidget()
        tabs_cat.setStyleSheet("QTabBar::tab { font-size: 9px; padding: 3px 8px; }")

        for cat_name, list_emoji in EMOJIS_RAPIDOS.items():
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("background: transparent; border: none;")
            
            grid_w = QWidget()
            g_lay = QGridLayout(grid_w)
            g_lay.setSpacing(4)

            row, col = 0, 0
            for emo in list_emoji:
                btn = QPushButton(emo)
                btn.setFont(QFont("Segoe UI Emoji", 14))
                btn.setFixedSize(36, 36)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; }
                    QPushButton:hover { background: rgba(99, 102, 241, 0.3); border: 1px solid #6366F1; }
                """)
                btn.clicked.connect(lambda ch, e=emo: self._insertar_emoji(e))
                g_lay.addWidget(btn, row, col)
                col += 1
                if col >= 14:
                    col = 0
                    row += 1

            scroll.setWidget(grid_w)
            tabs_cat.addTab(scroll, cat_name)

        lay.addWidget(tabs_cat)
        return w

    def _build_inline_stickers(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 5, 0, 0)

        top_row = QHBoxLayout()
        lbl = QLabel("Tus Stickers Guardados:")
        lbl.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        top_row.addWidget(lbl)

        top_row.addStretch()

        btn_add = QPushButton("➕ Nuevo Sticker")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet("background: #4CAF50; color: white; border-radius: 4px; padding: 3px 10px; font-size: 10px; font-weight: bold;")
        btn_add.clicked.connect(self._crear_sticker_inline)
        top_row.addWidget(btn_add)

        lay.addLayout(top_row)

        self.scroll_inline_stk = QScrollArea()
        self.scroll_inline_stk.setWidgetResizable(True)
        self.scroll_inline_stk.setStyleSheet("background: transparent; border: none;")

        self.grid_inline_stk_w = QWidget()
        self.g_inline_stk_lay = QGridLayout(self.grid_inline_stk_w)
        self.g_inline_stk_lay.setSpacing(8)

        self.scroll_inline_stk.setWidget(self.grid_inline_stk_w)
        lay.addWidget(self.scroll_inline_stk)

        self.recargar_stickers_inline()
        return w

    def recargar_stickers_inline(self):
        while self.g_inline_stk_lay.count():
            item = self.g_inline_stk_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        files = sorted(list(self.ruta_stickers.glob("*.*")))
        if not files:
            lbl_e = QLabel("No tienes stickers. ¡Presiona '➕ Nuevo Sticker' para agregar!")
            lbl_e.setStyleSheet("color: #aaa; font-size: 11px;")
            self.g_inline_stk_lay.addWidget(lbl_e, 0, 0)
            return

        row, col = 0, 0
        for fpath in files:
            if fpath.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
                btn = QPushButton()
                pix = QPixmap(str(fpath)).scaled(55, 55, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                btn.setIcon(QIcon(pix))
                btn.setIconSize(QSize(55, 55))
                btn.setFixedSize(65, 65)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setToolTip(fpath.name)
                btn.setStyleSheet("""
                    QPushButton { background: rgba(30, 30, 46, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; }
                    QPushButton:hover { border: 1px solid #6366F1; background: rgba(99, 102, 241, 0.2); }
                """)
                btn.clicked.connect(lambda ch, p=str(fpath): self._enviar_sticker_inline(p))
                self.g_inline_stk_lay.addWidget(btn, row, col)
                col += 1
                if col >= 8:
                    col = 0
                    row += 1

    def _insertar_emoji(self, emoji):
        self.txt_input.insertPlainText(emoji)
        self.txt_input.setFocus()

    def _enviar_sticker_inline(self, path):
        if "enviar_sticker" in self.callbacks:
            self.callbacks["enviar_sticker"](path)
        self.drawer_panel.hide()

    def _crear_sticker_inline(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen para Sticker", "",
            "Imágenes (*.png *.jpg *.jpeg *.webp *.gif)"
        )
        if path:
            dest = self.ruta_stickers / Path(path).name
            shutil.copy(path, dest)
            self.recargar_stickers_inline()
            QMessageBox.information(self, "Sticker Creado", f"¡Sticker '{dest.name}' agregado a tu colección!")

    def actualizar_tema(self, colores: dict = None):
        """Actualiza el tema de la sala de chat manteniendo el look de WhatsApp."""
        if colores:
            self.colores.update(colores)
        if hasattr(self, 'display') and hasattr(self.display, 'actualizar_tema'):
            self.display.actualizar_tema(self.colores)

    def cleanup(self):
        """Liberación de recursos al cerrar la sala."""
        pass

