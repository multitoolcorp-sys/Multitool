import os
import platform
import difflib
from PyQt6.QtWidgets import QDialog, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

def html_escape(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(' ', '&nbsp;').replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')

class DiffViewerDialog(QDialog):
    """Diálogo premium para comparar dos archivos de texto en paralelo"""
    def __init__(self, parent, path1, path2, colores):
        super().__init__(parent)
        self.path1 = path1
        self.path2 = path2
        self.colores = colores
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        self.setWindowTitle(f"Comparador de Diferencias: {os.path.basename(path1)} vs {os.path.basename(path2)}")
        self.resize(1100, 700)
        self.setStyleSheet(f"background-color: {self.colores['bg_principal']}; color: white;")
        
        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Cabecera con los nombres
        header_lay = QHBoxLayout()
        header_lay.setSpacing(15)

        lbl1 = QLabel(f"📂 Archivo A: {os.path.basename(self.path1)}\n<span style='color:{self.colores['fg_secundario']}; font-size:10px;'>{self.path1}</span>")
        lbl1.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl1.setStyleSheet("color: #E2E2E2; border: none;")
        header_lay.addWidget(lbl1, 1)

        lbl2 = QLabel(f"📂 Archivo B: {os.path.basename(self.path2)}\n<span style='color:{self.colores['fg_secundario']}; font-size:10px;'>{self.path2}</span>")
        lbl2.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl2.setStyleSheet("color: #E2E2E2; border: none;")
        header_lay.addWidget(lbl2, 1)

        layout.addLayout(header_lay)

        # Contenedor de paneles
        panels_lay = QHBoxLayout()
        panels_lay.setSpacing(10)

        # Estilo común para los text edits
        text_style = f"""
            QTextEdit {{
                background-color: #121218;
                color: #CCCCCC;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
                padding: 10px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.15);
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 8px;
            }}
            QScrollBar::handle:horizontal {{
                background: rgba(255,255,255,0.15);
                border-radius: 4px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        """

        self.txt_left = QTextEdit()
        self.txt_left.setReadOnly(True)
        self.txt_left.setFont(QFont(self.mono_font, 10))
        self.txt_left.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.txt_left.setStyleSheet(text_style)
        panels_lay.addWidget(self.txt_left, 1)

        self.txt_right = QTextEdit()
        self.txt_right.setReadOnly(True)
        self.txt_right.setFont(QFont(self.mono_font, 10))
        self.txt_right.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.txt_right.setStyleSheet(text_style)
        panels_lay.addWidget(self.txt_right, 1)

        layout.addLayout(panels_lay, 1)

        # Sincronización del scroll vertical
        left_scroll = self.txt_left.verticalScrollBar()
        right_scroll = self.txt_right.verticalScrollBar()
        left_scroll.valueChanged.connect(right_scroll.setValue)
        right_scroll.valueChanged.connect(left_scroll.setValue)

        # Sincronización del scroll horizontal
        left_h_scroll = self.txt_left.horizontalScrollBar()
        right_h_scroll = self.txt_right.horizontalScrollBar()
        left_h_scroll.valueChanged.connect(right_h_scroll.setValue)
        right_h_scroll.valueChanged.connect(left_h_scroll.setValue)

        # Botón Cerrar
        btn_close = QPushButton("CERRAR COMPARADOR")
        btn_close.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_close.setFixedHeight(40)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: white; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);
            }}
            QPushButton:hover {{ background-color: {self.colores['acento']}; border-color: {self.colores['acento']}; }}
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        # Procesar comparación
        self.calcular_diff()

    def calcular_diff(self):
        try:
            with open(self.path1, "r", encoding="utf-8", errors="ignore") as f:
                lines1 = f.read().splitlines()
            with open(self.path2, "r", encoding="utf-8", errors="ignore") as f:
                lines2 = f.read().splitlines()
        except Exception as e:
            self.txt_left.setHtml(f"<div style='color:red;'>Error al leer archivos: {e}</div>")
            self.txt_right.setHtml(f"<div style='color:red;'>Error al leer archivos: {e}</div>")
            return

        # Generar comparación de secuencia alineada
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        left_html = []
        right_html = []
        
        # Estilos HTML
        font_style = f"font-family:'{self.mono_font}'; font-size:13px; line-height:1.2; white-space:pre;"
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for k in range(i1, i2):
                    l_txt = html_escape(lines1[k])
                    r_txt = html_escape(lines2[j1 + (k - i1)])
                    left_html.append(f"<div style='{font_style} padding: 1px 5px; color:#A0A0A0;'>  {l_txt}</div>")
                    right_html.append(f"<div style='{font_style} padding: 1px 5px; color:#A0A0A0;'>  {r_txt}</div>")
            elif tag == 'replace':
                l_len = i2 - i1
                r_len = j2 - j1
                max_len = max(l_len, r_len)
                for k in range(max_len):
                    if k < l_len:
                        l_txt = html_escape(lines1[i1 + k])
                        left_html.append(f"<div style='{font_style} background-color: rgba(248, 113, 113, 0.16); color: #FFAAAA; padding: 1px 5px;'>- {l_txt}</div>")
                    else:
                        left_html.append(f"<div style='{font_style} background-color: rgba(255, 255, 255, 0.02); color:transparent; padding: 1px 5px;'>&nbsp;</div>")
                    
                    if k < r_len:
                        r_txt = html_escape(lines2[j1 + k])
                        right_html.append(f"<div style='{font_style} background-color: rgba(52, 211, 153, 0.16); color: #AAFFAA; padding: 1px 5px;'>+ {r_txt}</div>")
                    else:
                        right_html.append(f"<div style='{font_style} background-color: rgba(255, 255, 255, 0.02); color:transparent; padding: 1px 5px;'>&nbsp;</div>")
            elif tag == 'delete':
                for k in range(i1, i2):
                    l_txt = html_escape(lines1[k])
                    left_html.append(f"<div style='{font_style} background-color: rgba(248, 113, 113, 0.16); color: #FFAAAA; padding: 1px 5px;'>- {l_txt}</div>")
                    right_html.append(f"<div style='{font_style} background-color: rgba(255, 255, 255, 0.02); color:transparent; padding: 1px 5px;'>&nbsp;</div>")
            elif tag == 'insert':
                for k in range(j1, j2):
                    r_txt = html_escape(lines2[k])
                    right_html.append(f"<div style='{font_style} background-color: rgba(52, 211, 153, 0.16); color: #AAFFAA; padding: 1px 5px;'>+ {r_txt}</div>")
                    left_html.append(f"<div style='{font_style} background-color: rgba(255, 255, 255, 0.02); color:transparent; padding: 1px 5px;'>&nbsp;</div>")

        self.txt_left.setHtml("".join(left_html))
        self.txt_right.setHtml("".join(right_html))


class TabDiffViewer(QWidget):
    """Submódulo inline para comparar dos archivos en paralelo"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.path1 = ""
        self.path2 = ""
        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Header y selectores de archivos
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        # Archivo 1
        self.lbl_f1 = QLabel("Archivo A: (No seleccionado)")
        self.lbl_f1.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_f1.setStyleSheet("color: white;")
        btn_sel1 = QPushButton("📂 Seleccionar A")
        btn_sel1.setFixedHeight(32)
        btn_sel1.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sel1.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 4px 10px;")
        btn_sel1.clicked.connect(self._seleccionar_file1)

        top_bar.addWidget(btn_sel1)
        top_bar.addWidget(self.lbl_f1, 1)

        # Archivo 2
        self.lbl_f2 = QLabel("Archivo B: (No seleccionado)")
        self.lbl_f2.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_f2.setStyleSheet("color: white;")
        btn_sel2 = QPushButton("📂 Seleccionar B")
        btn_sel2.setFixedHeight(32)
        btn_sel2.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sel2.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 4px 10px;")
        btn_sel2.clicked.connect(self._seleccionar_file2)

        top_bar.addWidget(btn_sel2)
        top_bar.addWidget(self.lbl_f2, 1)

        btn_compare = QPushButton("🔍 Comparar Diferencias")
        btn_compare.setFixedHeight(32)
        btn_compare.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_compare.setStyleSheet(f"background: {self.colores['acento']}; color: white; font-weight: bold; border-radius: 6px; padding: 4px 14px;")
        btn_compare.clicked.connect(self.calcular_diff)
        top_bar.addWidget(btn_compare)

        layout.addLayout(top_bar)

        # Paneles paralelos
        panels_lay = QHBoxLayout()
        panels_lay.setSpacing(10)

        text_style = f"""
            QTextEdit {{
                background-color: {self.colores['bg_secundario']};
                color: #CCCCCC;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
                padding: 10px;
            }}
        """

        self.txt_left = QTextEdit()
        self.txt_left.setReadOnly(True)
        self.txt_left.setFont(QFont(self.mono_font, 9))
        self.txt_left.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.txt_left.setStyleSheet(text_style)
        panels_lay.addWidget(self.txt_left, 1)

        self.txt_right = QTextEdit()
        self.txt_right.setReadOnly(True)
        self.txt_right.setFont(QFont(self.mono_font, 9))
        self.txt_right.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.txt_right.setStyleSheet(text_style)
        panels_lay.addWidget(self.txt_right, 1)

        layout.addLayout(panels_lay, 1)

        # Sync Scroll
        l_sb = self.txt_left.verticalScrollBar()
        r_sb = self.txt_right.verticalScrollBar()
        l_sb.valueChanged.connect(r_sb.setValue)
        r_sb.valueChanged.connect(l_sb.setValue)

    def _seleccionar_file1(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo A")
        if path:
            self.path1 = path
            self.lbl_f1.setText(f"Archivo A: {os.path.basename(path)}")

    def _seleccionar_file2(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo B")
        if path:
            self.path2 = path
            self.lbl_f2.setText(f"Archivo B: {os.path.basename(path)}")

    def calcular_diff(self):
        if not self.path1 or not self.path2:
            return
        try:
            with open(self.path1, "r", encoding="utf-8", errors="ignore") as f:
                lines1 = f.read().splitlines()
            with open(self.path2, "r", encoding="utf-8", errors="ignore") as f:
                lines2 = f.read().splitlines()
        except Exception as e:
            self.txt_left.setHtml(f"<div style='color:red;'>Error al leer archivos: {e}</div>")
            self.txt_right.setHtml(f"<div style='color:red;'>Error al leer archivos: {e}</div>")
            return

        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        left_html = []
        right_html = []
        font_style = f"font-family:'{self.mono_font}'; font-size:12px; line-height:1.2; white-space:pre;"

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for k in range(i1, i2):
                    l_txt = html_escape(lines1[k])
                    r_txt = html_escape(lines2[j1 + (k - i1)])
                    left_html.append(f"<div style='{font_style} padding: 1px 5px; color:#A0A0A0;'>  {l_txt}</div>")
                    right_html.append(f"<div style='{font_style} padding: 1px 5px; color:#A0A0A0;'>  {r_txt}</div>")
            elif tag == 'replace':
                l_len = i2 - i1
                r_len = j2 - j1
                max_len = max(l_len, r_len)
                for k in range(max_len):
                    if k < l_len:
                        l_txt = html_escape(lines1[i1 + k])
                        left_html.append(f"<div style='{font_style} background-color: rgba(248, 113, 113, 0.16); color: #FFAAAA; padding: 1px 5px;'>- {l_txt}</div>")
                    else:
                        left_html.append(f"<div style='{font_style} background-color: rgba(255, 255, 255, 0.02); color:transparent; padding: 1px 5px;'>&nbsp;</div>")
                    if k < r_len:
                        r_txt = html_escape(lines2[j1 + k])
                        right_html.append(f"<div style='{font_style} background-color: rgba(52, 211, 153, 0.16); color: #AAFFAA; padding: 1px 5px;'>+ {r_txt}</div>")
                    else:
                        right_html.append(f"<div style='{font_style} background-color: rgba(255, 255, 255, 0.02); color:transparent; padding: 1px 5px;'>&nbsp;</div>")
            elif tag == 'delete':
                for k in range(i1, i2):
                    l_txt = html_escape(lines1[k])
                    left_html.append(f"<div style='{font_style} background-color: rgba(248, 113, 113, 0.16); color: #FFAAAA; padding: 1px 5px;'>- {l_txt}</div>")
                    right_html.append(f"<div style='{font_style} background-color: rgba(255, 255, 255, 0.02); color:transparent; padding: 1px 5px;'>&nbsp;</div>")
            elif tag == 'insert':
                for k in range(j1, j2):
                    r_txt = html_escape(lines2[k])
                    right_html.append(f"<div style='{font_style} background-color: rgba(52, 211, 153, 0.16); color: #AAFFAA; padding: 1px 5px;'>+ {r_txt}</div>")
                    left_html.append(f"<div style='{font_style} background-color: rgba(255, 255, 255, 0.02); color:transparent; padding: 1px 5px;'>&nbsp;</div>")

        self.txt_left.setHtml("".join(left_html))
        self.txt_right.setHtml("".join(right_html))
