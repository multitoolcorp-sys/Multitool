import threading
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class DiccionarioGlosarioSubmodule(QWidget):
    """Submódulo 3: Diccionario & Glosario Contextual (Integración con Free Dictionary API)"""
    diccionario_respuesta = pyqtSignal(str)

    def __init__(self, parent, context, manager, colores):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.diccionario_respuesta.connect(self._on_diccionario_respuesta)
        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("📖 DICCIONARIO & GLOSARIO CONTEXTUAL (FREE DICTIONARY API)")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        layout.addLayout(hdr)

        # Barra de búsqueda
        search_lay = QHBoxLayout()
        search_lay.setSpacing(8)

        self.txt_term = QLineEdit()
        self.txt_term.setPlaceholderText("Escribe una palabra o expresión para consultar (ej: hello, computer, world)...")
        self.txt_term.setFont(QFont(self.font_family, 10))
        self.txt_term.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 8px 12px;
            }}
        """)
        self.txt_term.returnPressed.connect(self._buscar_termino)
        search_lay.addWidget(self.txt_term, 1)

        self.btn_search = QPushButton("🔍 Consultar Diccionario")
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_search.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 8px 18px; border-radius: 6px; border: none;")
        self.btn_search.clicked.connect(self._buscar_termino)
        search_lay.addWidget(self.btn_search)

        layout.addLayout(search_lay)

        # Área de Información del Diccionario
        self.txt_dict_res = QTextEdit()
        self.txt_dict_res.setReadOnly(True)
        self.txt_dict_res.setPlaceholderText("Las definiciones enciclopédicas, pronunciación fonética, origen, categorías gramaticales, ejemplos de uso y sinónimos/antónimos aparecerán aquí...")
        self.txt_dict_res.setFont(QFont(self.font_family, 11))
        self.txt_dict_res.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px; padding: 16px; line-height: 1.6;
            }}
        """)
        layout.addWidget(self.txt_dict_res, 1)

    def _buscar_termino(self):
        term = self.txt_term.text().strip()
        if not term:
            return

        self.txt_dict_res.setPlainText(f"🔍 Consultando diccionario para '{term}'...")
        
        def run():
            try:
                res = self.manager.consultar_diccionario_api(term, "en")
                self.diccionario_respuesta.emit(res or f"No se encontraron resultados para '{term}'.")
            except Exception as e:
                self.diccionario_respuesta.emit(f"❌ Error al consultar diccionario: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _on_diccionario_respuesta(self, res):
        self.txt_dict_res.setPlainText(res)

    def set_diccionario_texto(self, texto):
        self.txt_dict_res.setPlainText(texto)

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#121218')
        bg_sec = colores.get('bg_secundario', '#1E1E2E')
        acento = colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        self.txt_term.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg_sec};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 8px 12px;
            }}
        """)
        self.txt_dict_res.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_sec};
                color: white; border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px; padding: 16px; line-height: 1.6;
            }}
        """)
        if hasattr(self, 'btn_search'):
            self.btn_search.setStyleSheet(f"background-color: {acento}; color: white; padding: 8px 18px; border-radius: 6px; border: none;")

    def cleanup(self):
        pass
