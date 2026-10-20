import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QTextEdit, QFrame, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class TextPanel(QFrame):
    """Panel glassmórfico de texto con cabecera y botón TTS"""
    def __init__(self, placeholder, colores, read_only=False, tts_callback=None, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(f"""
            background-color: {colores['bg_terciario']};
            border-top-left-radius: 9px; border-top-right-radius: 9px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        """)
        h_lay = QHBoxLayout(self.header_frame)
        h_lay.setContentsMargins(12, 8, 12, 8)
        h_lay.setSpacing(8)

        icon = "📝" if not read_only else "🌐"
        self.lbl_header = QLabel(f"{icon} {'Texto Original' if not read_only else 'Traducción'}")
        self.lbl_header.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_header.setStyleSheet("color: white; border: none; background: transparent;")
        h_lay.addWidget(self.lbl_header)

        # Botón TTS (Voz)
        self.btn_tts = QPushButton("🔊")
        self.btn_tts.setFixedSize(26, 26)
        self.btn_tts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tts.setToolTip("Escuchar Pronunciación (TTS)")
        self.btn_tts.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; font-size: 13px; color: white; }}
            QPushButton:hover {{ background: rgba(255,255,255,0.1); border-radius: 4px; }}
        """)
        if tts_callback:
            self.btn_tts.clicked.connect(tts_callback)
        h_lay.addWidget(self.btn_tts)
        h_lay.addStretch()

        self.lbl_chars = QLabel("0 car.")
        self.lbl_chars.setFont(QFont("Consolas", 8))
        self.lbl_chars.setStyleSheet("color: rgba(255,255,255,0.6); border: none; background: transparent;")
        h_lay.addWidget(self.lbl_chars)

        layout.addWidget(self.header_frame)

        # Editor de texto
        self.editor = QTextEdit()
        self.editor.setPlaceholderText(placeholder)
        self.editor.setReadOnly(read_only)
        self.editor.setFont(QFont(self.font_family, 12))
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {colores['bg_secundario']};
                color: white; border: none; border-bottom-left-radius: 9px;
                border-bottom-right-radius: 9px; padding: 12px;
            }}
        """)
        self.editor.textChanged.connect(self._update_counter)
        layout.addWidget(self.editor, 1)

    def _update_counter(self):
        n = len(self.editor.toPlainText())
        self.lbl_chars.setText(f"{n} car.")

    def text(self): return self.editor.toPlainText()
    def set_text(self, t): self.editor.setPlainText(t)
    def clear(self): self.editor.clear()

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }}
        """)
        if hasattr(self, 'header_frame'):
            self.header_frame.setStyleSheet(f"""
                background-color: {colores['bg_terciario']};
                border-top-left-radius: 9px; border-top-right-radius: 9px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            """)
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {colores['bg_secundario']};
                color: white; border: none; border-bottom-left-radius: 9px;
                border-bottom-right-radius: 9px; padding: 12px;
            }}
        """)


class TraductorTextoSubmodule(QWidget):
    """Submódulo 1: Traducción de Texto & Pronunciación por Voz (TTS)"""
    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header superior
        top_row = QHBoxLayout()
        lbl_title = QLabel("🔤 TRADUCCIÓN DE TEXTO LIBRE")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        top_row.addWidget(lbl_title)
        top_row.addStretch()

        lbl_engine = QLabel("Motor:")
        lbl_engine.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_engine.setStyleSheet("color: rgba(255,255,255,0.7);")
        top_row.addWidget(lbl_engine)

        self.combo_modo = QComboBox()
        self.combo_modo.addItems(["🌐 En línea (Google)", "📴 Offline (Local)"])
        self.combo_modo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 4px 10px; font-weight: bold;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
            }}
        """)
        top_row.addWidget(self.combo_modo)

        layout.addLayout(top_row)

        # Barra de Selección de Idiomas
        self.lang_bar = QFrame()
        self.lang_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }}
        """)
        l_lay = QHBoxLayout(self.lang_bar)
        l_lay.setContentsMargins(10, 6, 10, 6)
        l_lay.setSpacing(8)

        lbl_de = QLabel("De:")
        lbl_de.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_de.setStyleSheet("color: white; border: none; background: transparent;")
        l_lay.addWidget(lbl_de)

        self.combo_origen = QComboBox()
        self.combo_origen.setStyleSheet(self.combo_modo.styleSheet())
        l_lay.addWidget(self.combo_origen, 2)

        btn_swap = QPushButton("⇄")
        btn_swap.setFixedSize(36, 32)
        btn_swap.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        btn_swap.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_swap.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white; border: none; border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        btn_swap.clicked.connect(self.callbacks["intercambiar"])
        l_lay.addWidget(btn_swap)

        lbl_a = QLabel("A:")
        lbl_a.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_a.setStyleSheet("color: white; border: none; background: transparent;")
        l_lay.addWidget(lbl_a)

        self.combo_destino = QComboBox()
        self.combo_destino.setStyleSheet(self.combo_modo.styleSheet())
        l_lay.addWidget(self.combo_destino, 2)

        layout.addWidget(self.lang_bar)

        # Splitter de Texto Original y Traducido
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.05); height: 6px; }")

        self.panel_original = TextPanel(
            "Escribe o pega el texto a traducir (Ctrl+Enter para traducir)...",
            self.colores, read_only=False, tts_callback=self.callbacks.get("pronunciar_original")
        )
        splitter.addWidget(self.panel_original)

        self.panel_traducido = TextPanel(
            "La traducción aparecerá aquí...",
            self.colores, read_only=True, tts_callback=self.callbacks.get("pronunciar_traducido")
        )
        splitter.addWidget(self.panel_traducido)

        layout.addWidget(splitter, 1)

        # Aliases de compatibilidad
        self.txt_original = self.panel_original.editor
        self.txt_traducido = self.panel_traducido.editor

        # Capturar Ctrl+Enter en el cuadro original
        self.txt_original.keyPressEvent = self._on_key_original

        # Barra de Acciones Inferior
        act_bar = QHBoxLayout()
        act_bar.setSpacing(8)

        btn_clean = QPushButton("🗑️ Limpiar")
        btn_clean.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clean.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; padding: 8px 14px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);")
        btn_clean.clicked.connect(self.callbacks["limpiar"])
        act_bar.addWidget(btn_clean)

        btn_detect = QPushButton("🔍 Detectar Idioma")
        btn_detect.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_detect.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; padding: 8px 14px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);")
        btn_detect.clicked.connect(self.callbacks["detectar"])
        act_bar.addWidget(btn_detect)

        btn_fav = QPushButton("⭐ Guardar en Favoritos")
        btn_fav.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fav.setStyleSheet(f"background-color: {self.colores['advertencia']}; color: #111; padding: 8px 14px; border-radius: 6px; font-weight: bold; border: none;")
        btn_fav.clicked.connect(self.callbacks.get("guardar_favorito"))
        act_bar.addWidget(btn_fav)

        act_bar.addStretch()

        btn_copy = QPushButton("📋 Copiar")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white; padding: 8px 14px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        btn_copy.clicked.connect(self.callbacks["copiar"])
        act_bar.addWidget(btn_copy)

        self.btn_translate = QPushButton("⚡ TRADUCIR")
        self.btn_translate.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_translate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_translate.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 10px 22px; border-radius: 6px; border: none;")
        self.btn_translate.clicked.connect(self.callbacks["traducir"])
        act_bar.addWidget(self.btn_translate)

        layout.addLayout(act_bar)

        self.lbl_estado = QLabel("Listo.")
        self.lbl_estado.setFont(QFont(self.font_family, 8))
        self.lbl_estado.setStyleSheet("color: rgba(255,255,255,0.6);")
        layout.addWidget(self.lbl_estado)

    def _on_key_original(self, event):
        if (event.key() == Qt.Key.Key_Return and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.callbacks["traducir"]()
        else:
            QTextEdit.keyPressEvent(self.txt_original, event)

    def actualizar_idiomas(self, origen, destino):
        self.combo_origen.clear()
        self.combo_origen.addItems(origen)
        self.combo_destino.clear()
        self.combo_destino.addItems(destino)
        self.combo_origen.setCurrentIndex(0)
        for i in range(self.combo_destino.count()):
            if "(en)" in self.combo_destino.itemText(i):
                self.combo_destino.setCurrentIndex(i)
                break

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#121218')
        bg_sec = colores.get('bg_secundario', '#1E1E2E')
        bg_terc = colores.get('bg_terciario', '#2D2D3D')
        acento = colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        if hasattr(self, 'lang_bar'):
            self.lang_bar.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_sec};
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                }}
            """)
        combo_style = f"""
            QComboBox {{
                background-color: {bg_terc};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 4px 10px; font-weight: bold;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg_sec};
                color: white; selection-background-color: {acento};
            }}
        """
        self.combo_modo.setStyleSheet(combo_style)
        self.combo_origen.setStyleSheet(combo_style)
        self.combo_destino.setStyleSheet(combo_style)
        self.panel_original.actualizar_tema(colores)
        self.panel_traducido.actualizar_tema(colores)
        if hasattr(self, 'btn_translate'):
            self.btn_translate.setStyleSheet(f"background-color: {acento}; color: white; padding: 10px 22px; border-radius: 6px; border: none;")

    def cleanup(self):
        pass
