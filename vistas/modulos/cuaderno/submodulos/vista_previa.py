import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QTextBrowser, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class VistaPreviaSubmodule(QWidget):
    """Submódulo 3: Vista Previa HD e Impresión con Toggle de Tema Claro/Oscuro"""
    def __init__(self, parent, context, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.zoom_level = 100
        self.modo_impresion = False

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # ── Controles de Vista Previa ──
        ctrl_frame = QFrame()
        ctrl_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 8px 14px;")
        c_lay = QHBoxLayout(ctrl_frame)
        c_lay.setContentsMargins(8, 4, 8, 4)
        c_lay.setSpacing(10)

        lbl_tit = QLabel("👁️ VISTA PREVIA & MAQUETACIÓN")
        lbl_tit.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento};")
        c_lay.addWidget(lbl_tit)

        c_lay.addStretch()

        self.btn_tema = QPushButton("🌙 Modo Lectura (Oscuro)")
        self.btn_tema.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_tema.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tema.setStyleSheet(f"background: rgba(255, 255, 255, 0.05); color: white; border-radius: 6px; padding: 6px 12px; border: 1px solid rgba(255,255,255,0.1);")
        self.btn_tema.clicked.connect(self._toggle_tema)
        c_lay.addWidget(self.btn_tema)

        self.btn_zoom_in = QPushButton("🔍+")
        self.btn_zoom_in.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zoom_in.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 6px; padding: 6px 10px; font-weight: bold;")
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        c_lay.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("🔍-")
        self.btn_zoom_out.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zoom_out.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 6px; padding: 6px 10px; font-weight: bold;")
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        c_lay.addWidget(self.btn_zoom_out)

        self.btn_refresh = QPushButton("🔄 Actualizar")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 6px 14px; font-weight: bold; border: none;")
        self.btn_refresh.clicked.connect(self._refresh_preview)
        c_lay.addWidget(self.btn_refresh)

        layout.addWidget(ctrl_frame)

        # ── Visor HTML ──
        self.preview_browser = QTextBrowser()
        self.preview_browser.setOpenExternalLinks(True)
        self.preview_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg_sec};
                color: #e2e2e2;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        layout.addWidget(self.preview_browser, 1)

    def _toggle_tema(self):
        self.modo_impresion = not self.modo_impresion
        if self.modo_impresion:
            self.btn_tema.setText("☀️ Modo Impresión (Claro)")
        else:
            self.btn_tema.setText("🌙 Modo Lectura (Oscuro)")
        self._refresh_preview()

    def _zoom_in(self):
        self.preview_browser.zoomIn(1)

    def _zoom_out(self):
        self.preview_browser.zoomOut(1)

    def _refresh_preview(self):
        if "generar_html" in self.callbacks:
            html = self.callbacks["generar_html"](for_print=self.modo_impresion)
            self.preview_browser.setHtml(html)

    def actualizar_tema(self, colores):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#121218')
        bg_sec = colores.get('bg_secundario', '#1E1E2E')
        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        if hasattr(self, 'preview_browser'):
            self.preview_browser.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: {bg_sec};
                    color: #e2e2e2;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    padding: 20px;
                }}
            """)
        self._refresh_preview()
