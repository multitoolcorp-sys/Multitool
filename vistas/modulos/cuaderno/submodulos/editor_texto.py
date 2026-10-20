import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class EditorTextoSubmodule(QWidget):
    """Submódulo 2: Editor de Texto Libre, Markdown & JSON Raw con Contador de Palabras"""
    def __init__(self, parent, context, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # ── Toolbar de Formato Markdown & Formatos Rápido ──
        tb_frame = QFrame()
        tb_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 6px 12px;")
        t_lay = QHBoxLayout(tb_frame)
        t_lay.setContentsMargins(8, 4, 8, 4)
        t_lay.setSpacing(8)

        lbl_title = QLabel("📝 EDITOR NOTAS & MARKDOWN")
        lbl_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {acento};")
        t_lay.addWidget(lbl_title)

        t_lay.addStretch()

        btn_h1 = self._create_fmt_btn("H1", "# ", "Título de nivel 1")
        btn_bold = self._create_fmt_btn("B", "**", "Texto en Negrita")
        btn_italic = self._create_fmt_btn("I", "*", "Texto en Cursiva")
        btn_list = self._create_fmt_btn("• Lista", "- ", "Lista con viñetas")
        btn_code = self._create_fmt_btn("</>", "```\n", "Bloque de código")

        t_lay.addWidget(btn_h1)
        t_lay.addWidget(btn_bold)
        t_lay.addWidget(btn_italic)
        t_lay.addWidget(btn_list)
        t_lay.addWidget(btn_code)

        layout.addWidget(tb_frame)

        # ── Area de Editor de Texto ──
        self.text_editor = QTextEdit()
        self.text_editor.setFont(QFont("Consolas", 11))
        self.text_editor.setPlaceholderText("Escribe aquí tus notas en formato Markdown o JSON...")
        self.text_editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_sec};
                color: #e2e2e2;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 15px;
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border: 1px solid {acento};
            }}
        """)
        self.text_editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_editor, 1)

        # ── Barra de Estado y Contador de Palabras ──
        st_frame = QFrame()
        st_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 8px; padding: 6px 12px;")
        s_lay = QHBoxLayout(st_frame)
        s_lay.setContentsMargins(8, 4, 8, 4)

        self.lbl_status = QLabel("Edición de texto activa")
        self.lbl_status.setFont(QFont(self.font_family, 9))
        self.lbl_status.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        s_lay.addWidget(self.lbl_status)

        s_lay.addStretch()

        self.lbl_counter = QLabel("Palabras: 0 | Caracteres: 0")
        self.lbl_counter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.lbl_counter.setStyleSheet(f"color: {acento};")
        s_lay.addWidget(self.lbl_counter)

        layout.addWidget(st_frame)

    def _create_fmt_btn(self, text, prefix, tooltip):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.05);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn.clicked.connect(lambda: self._insert_prefix(prefix))
        return btn

    def _insert_prefix(self, prefix):
        cursor = self.text_editor.textCursor()
        cursor.insertText(prefix)
        self.text_editor.setFocus()

    def _on_text_changed(self):
        text = self.text_editor.toPlainText()
        words = len(text.split())
        chars = len(text)
        self.lbl_counter.setText(f"Palabras: {words} | Caracteres: {chars}")
        if "marcar_modificado" in self.callbacks:
            self.callbacks["marcar_modificado"]()

    def actualizar_tema(self, colores):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#121218')
        bg_sec = colores.get('bg_secundario', '#1E1E2E')
        acento = colores.get('acento', '#6366F1')
        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        if hasattr(self, 'text_editor'):
            self.text_editor.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {bg_sec};
                    color: #e2e2e2;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    padding: 15px;
                    line-height: 1.5;
                }}
                QTextEdit:focus {{
                    border: 1px solid {acento};
                }}
            """)
        if hasattr(self, 'lbl_counter'):
            self.lbl_counter.setStyleSheet(f"color: {acento};")
