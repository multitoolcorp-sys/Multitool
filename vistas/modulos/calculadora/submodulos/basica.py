import re
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QLineEdit, QPushButton, QLabel, QMessageBox, QSizePolicy, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from ..utils.math_parser import MathParser

class TabCalculadoraBasica(QWidget):
    """Interfaz de calculadora básica con soporte de teclado y memoria (Glassmorphism)"""
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
        
        # Estado
        self.expresion = "0"
        self.memoria = 0
        
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
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
        """)
        display_layout = QVBoxLayout(self.display_container)
        display_layout.setContentsMargins(12, 10, 12, 10)
        display_layout.setSpacing(5)
        
        # Preview (operación anterior)
        self.lbl_preview = QLabel("")
        self.lbl_preview.setFont(QFont(self.mono_font, 12))
        self.lbl_preview.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; ")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignRight)
        display_layout.addWidget(self.lbl_preview)
        
        # Pantalla principal
        self.pantalla = QLineEdit("0")
        self.pantalla.setReadOnly(True)
        self.pantalla.setFont(QFont(self.mono_font, 26, QFont.Weight.Bold))
        self.pantalla.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.pantalla.setStyleSheet(f"color: white; background: transparent; border: none; padding: 0px;")
        display_layout.addWidget(self.pantalla)
        
        self.layout_principal.addWidget(self.display_container)
        
        # --- BARRA DE MEMORIA ---
        mem_layout = QHBoxLayout()
        mem_layout.setSpacing(10)
        
        btns_mem = [
            ("MC", self.mem_clear), ("MR", self.mem_recall),
            ("M+", self.mem_add), ("M-", self.mem_sub),
            ("📋 Copiar", self.copiar_resultado)
        ]
        
        for text, cmd in btns_mem:
            btn = QPushButton(text)
            btn.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setMinimumHeight(32)
            btn.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: rgba(45, 45, 61, 0.4); 
                    color: {self.colores['fg_secundario']}; 
                    border-radius: 8px;
                    border: 1px solid rgba(255,255,255,0.03);
                }}
                QPushButton:hover {{ 
                    background-color: rgba(99, 102, 241, 0.15); 
                    color: {self.colores['acento']}; 
                    border: 1px solid {self.colores['acento']}44;
                }}
            """)
            btn.clicked.connect(cmd)
            mem_layout.addWidget(btn)
            
        self.layout_principal.addLayout(mem_layout)
        
        # --- GRID DE BOTONES ---
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(8)
        
        botones = [
            ('C', 0, 0, 1, 1, "error"), ('←', 0, 1, 1, 1, "bg_terciario"), ('(', 0, 2, 1, 1, "bg_terciario"), (')', 0, 3, 1, 1, "bg_terciario"),
            ('7', 1, 0, 1, 1, "bg_terciario"), ('8', 1, 1, 1, 1, "bg_terciario"), ('9', 1, 2, 1, 1, "bg_terciario"), ('/', 1, 3, 1, 1, "acento"),
            ('4', 2, 0, 1, 1, "bg_terciario"), ('5', 2, 1, 1, 1, "bg_terciario"), ('6', 2, 2, 1, 1, "bg_terciario"), ('*', 2, 3, 1, 1, "acento"),
            ('1', 3, 0, 1, 1, "bg_terciario"), ('2', 3, 1, 1, 1, "bg_terciario"), ('3', 3, 2, 1, 1, "bg_terciario"), ('-', 3, 3, 1, 1, "acento"),
            ('+/-', 4, 0, 1, 1, "bg_terciario"), ('0', 4, 1, 1, 1, "bg_terciario"), (',', 4, 2, 1, 1, "bg_terciario"), ('+', 4, 3, 1, 1, "acento"),
            ('%', 5, 0, 1, 1, "bg_terciario"), ('=', 5, 1, 1, 3, "exito")
        ]
        
        self.btn_equal = None
        for (text, r, c, rs, cs, color_key) in botones:
            btn = QPushButton(text)
            btn.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.setMinimumHeight(36)
            
            bg_color = self.colores.get(color_key, self.colores["bg_terciario"])
            # Si es un número (bg_terciario), usamos glass
            if color_key == "bg_terciario":
                qss_bg = "rgba(45, 45, 61, 0.6)"
                qss_hover = "rgba(255, 255, 255, 0.1)"
            else:
                qss_bg = bg_color
                qss_hover = bg_color # Se oscurece por defecto o mantenemos
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {qss_bg};
                    color: white;
                    border: 1px solid rgba(255,255,255,0.05);
                    border-radius: 14px;
                }}
                QPushButton:hover {{
                    background-color: {qss_hover};
                    border: 1px solid rgba(255,255,255,0.15);
                }}
                QPushButton:pressed {{
                    background-color: {self.colores['bg_principal']};
                }}
            """)
            
            btn.clicked.connect(lambda checked, t=text: self.accion(t))
            self.grid_layout.addWidget(btn, r, c, rs, cs)
            if text == '=': self.btn_equal = btn
            
        self.layout_principal.addLayout(self.grid_layout, 1)

    def keyPressEvent(self, event):
        key = event.text()
        if key in "0123456789+-*/%()": self.accion(key)
        elif key in ".,": self.accion(",")
        elif key in "cC": self.limpiar()
        elif event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]: self.accion("=")
        elif event.key() == Qt.Key.Key_Backspace: self.borrar_ultimo()
        elif event.key() == Qt.Key.Key_Escape: self.limpiar()
        else: super().keyPressEvent(event)

    def mem_clear(self): 
        self.memoria = 0
        self.lbl_preview.setText("Memoria borrada")
        QTimer.singleShot(2000, lambda: self.lbl_preview.setText("") if "Memoria" in self.lbl_preview.text() else None)

    def mem_recall(self): 
        self.expresion = str(self.memoria).replace(".", ",")
        self._up()

    def mem_add(self):
        try: 
            self.memoria += self.parser.evaluate(self.expresion)
            self.lbl_preview.setText(f"M: {self.parser.format_number(self.memoria)}")
        except: pass

    def mem_sub(self):
        try: 
            self.memoria -= self.parser.evaluate(self.expresion)
            self.lbl_preview.setText(f"M: {self.parser.format_number(self.memoria)}")
        except: pass

    def accion(self, b):
        if self.expresion == "0" and b not in "=C←,+-*/%()": self.expresion = ""
        
        if b == '=': self._calc()
        elif b == 'C': self.limpiar()
        elif b == '←': self.borrar_ultimo()
        elif b == '+/-': self._signo()
        elif b == ',': self._decimal()
        elif b in "+-*/%()": self._op(b)
        else: 
            self.expresion += b
            self._up()

    def _op(self, s):
        if self.expresion and self.expresion[-1] in "+-*/%" and s in "+-*/%": 
            self.expresion = self.expresion[:-1] + s
        else: 
            self.expresion += s
        self._up()

    def _decimal(self):
        # Separar por operadores para ver si el último número ya tiene coma
        ultimo_num = re.split(r'[\+\-\*\/\%\(\)]', self.expresion)[-1]
        if "," not in ultimo_num:
            self.expresion += "," if self.expresion else "0,"
            self._up()

    def _signo(self):
        if self.expresion == "0": return
        if self.expresion.startswith("-"): self.expresion = self.expresion[1:]
        else: self.expresion = "-" + self.expresion
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
            QMessageBox.critical(self, "Error Matemático", str(e))
            self.limpiar()

    def limpiar(self): 
        self.expresion = "0"
        self.lbl_preview.setText("")
        self._up()

    def borrar_ultimo(self):
        self.expresion = self.expresion[:-1] if len(self.expresion) > 1 else "0"
        self._up()

    def copiar_resultado(self):
        txt = self.pantalla.text().strip()
        if txt:
            app = QApplication.instance()
            if app:
                clipboard = app.clipboard()
                clipboard.setText(txt)
                self.lbl_preview.setText(f"📋 '{txt}' copiado al portapapeles")
