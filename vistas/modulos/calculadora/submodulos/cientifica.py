import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLineEdit, 
    QPushButton, QLabel, QMessageBox, QSizePolicy, QFrame, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..utils.math_parser import MathParser

class TabCalculadoraCientifica(QWidget):
    """Calculadora avanzada con funciones trigonométricas y logarítmicas (Glassmorphism)"""
    def __init__(self, parent, colores, agregar_al_historial_callback):
        super().__init__(parent)
        self.colores = colores
        self.agregar_al_historial = agregar_al_historial_callback
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        # Parser unificado
        self.parser = MathParser()
        self.expresion = "0"
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.inicializar_ui()

    def inicializar_ui(self):
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(10, 10, 10, 10)
        self.layout_principal.setSpacing(8)
        
        # --- DISPLAY PREMIUM GLASS ---
        self.display_container = QFrame()
        self.display_container.setObjectName("display")
        self.display_container.setStyleSheet(f"""
            QFrame#display {{ 
                background-color: rgba(30, 30, 46, 0.8); 
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
        """)
        display_layout = QVBoxLayout(self.display_container)
        display_layout.setContentsMargins(12, 8, 12, 8)
        display_layout.setSpacing(5)
        
        self.lbl_preview = QLabel("")
        self.lbl_preview.setFont(QFont(self.mono_font, 11))
        self.lbl_preview.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; ")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignRight)
        display_layout.addWidget(self.lbl_preview)
        
        self.pantalla = QLineEdit("0")
        self.pantalla.setReadOnly(True)
        self.pantalla.setFont(QFont(self.mono_font, 22, QFont.Weight.Bold))
        self.pantalla.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.pantalla.setStyleSheet(f"color: white; background: transparent; border: none; padding: 0px;")
        display_layout.addWidget(self.pantalla)
        
        self.layout_principal.addWidget(self.display_container)
        
        # --- GRID DE BOTONES ---
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(6)
        
        botones = [
            ('sin', 0, 0, 1, 1, "bg_secundario"), ('cos', 0, 1, 1, 1, "bg_secundario"), ('tan', 0, 2, 1, 1, "bg_secundario"), ('sqrt', 0, 3, 1, 1, "acento"),
            ('log', 1, 0, 1, 1, "bg_secundario"), ('ln', 1, 1, 1, 1, "bg_secundario"), ('exp', 1, 2, 1, 1, "bg_secundario"), ('^', 1, 3, 1, 1, "acento"),
            ('π', 2, 0, 1, 1, "bg_secundario"), ('e', 2, 1, 1, 1, "bg_secundario"), ('abs', 2, 2, 1, 1, "bg_secundario"), ('fact', 2, 3, 1, 1, "acento"),
            ('7', 3, 0, 1, 1, "bg_terciario"), ('8', 3, 1, 1, 1, "bg_terciario"), ('9', 3, 2, 1, 1, "bg_terciario"), ('/', 3, 3, 1, 1, "acento"),
            ('4', 4, 0, 1, 1, "bg_terciario"), ('5', 4, 1, 1, 1, "bg_terciario"), ('6', 4, 2, 1, 1, "bg_terciario"), ('*', 4, 3, 1, 1, "acento"),
            ('1', 5, 0, 1, 1, "bg_terciario"), ('2', 5, 1, 1, 1, "bg_terciario"), ('3', 5, 2, 1, 1, "bg_terciario"), ('-', 5, 3, 1, 1, "acento"),
            ('0', 6, 0, 1, 1, "bg_terciario"), (',', 6, 1, 1, 1, "bg_terciario"), ('(', 6, 2, 1, 1, "bg_secundario"), (')', 6, 3, 1, 1, "bg_secundario"),
            ('C', 7, 0, 1, 1, "error"), ('←', 7, 1, 1, 1, "bg_terciario"), ('+', 7, 2, 1, 1, "acento"), ('=', 7, 3, 1, 1, "exito")
        ]
        
        for (text, r, c, rs, cs, color_key) in botones:
            btn = QPushButton(text)
            btn.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.setMinimumHeight(30)
            
            bg_color = self.colores.get(color_key, self.colores["bg_terciario"])
            qss_bg = bg_color
            if color_key in ["bg_terciario", "bg_secundario"]:
                qss_bg = "rgba(45, 45, 61, 0.5)" if color_key == "bg_terciario" else "rgba(30, 30, 46, 0.4)"
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {qss_bg};
                    color: white;
                    border: 1px solid rgba(255,255,255,0.05);
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    background-color: rgba(99, 102, 241, 0.2);
                    border: 1px solid rgba(255,255,255,0.15);
                }}
            """)
            
            btn.clicked.connect(lambda checked, t=text: self.accion(t))
            self.grid_layout.addWidget(btn, r, c, rs, cs)
            
        self.layout_principal.addLayout(self.grid_layout, 1)

    def keyPressEvent(self, event):
        key = event.text()
        if key in "0123456789+-*/%()^": self.accion(key)
        elif key in ".,": self.accion(",")
        elif key in "cC": self.limpiar()
        elif event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]: self.accion("=")
        elif event.key() == Qt.Key.Key_Backspace: self.borrar_ultimo()
        elif event.key() == Qt.Key.Key_Escape: self.limpiar()
        else: super().keyPressEvent(event)

    def accion(self, b):
        if self.expresion == "0" and b not in "=C←,+-*/%()^": self.expresion = ""
        
        if b == '=': self._calc()
        elif b == 'C': self.limpiar()
        elif b == '←': self.borrar_ultimo()
        elif b in ['sin', 'cos', 'tan', 'log', 'ln', 'sqrt', 'abs', 'fact', 'exp']:
            self.expresion += b + "("
            self._up()
        else:
            self.expresion += b
            self._up()

    def _up(self):
        self.pantalla.setText(self.expresion.replace(".", ","))

    def _calc(self):
        while self.expresion and self.expresion[-1] in "+-*/%":
            self.expresion = self.expresion[:-1]
            
        if not self.expresion:
            self.expresion = "0"
            
        try:
            res = self.parser.evaluate(self.expresion)
            self.lbl_preview.setText(f"{self.expresion} =")
            self.expresion = self.parser.format_number(res)
            self._up()
            self.agregar_al_historial(self.lbl_preview.text(), res)
        except Exception as e:
            QMessageBox.critical(self, "Error de Cálculo", str(e))
            self.limpiar()

    def limpiar(self):
        self.expresion = "0"
        self.lbl_preview.setText("")
        self._up()

    def borrar_ultimo(self):
        self.expresion = self.expresion[:-1] if len(self.expresion) > 1 else "0"
        self._up()
