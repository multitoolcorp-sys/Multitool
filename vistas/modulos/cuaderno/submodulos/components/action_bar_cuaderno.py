from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

class ActionBarCuaderno(QFrame):
    def __init__(self, colores, callbacks, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self._build_ui()

    def _build_ui(self):
        # Rediseñado para un estilo profesional y compacto (estilo Office)
        self.setMinimumHeight(60)
        self.setStyleSheet(f"QFrame {{ background:transparent; border:none; }}")
        
        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(0, 5, 0, 5)
        main_lay.setSpacing(10)

        # 1. Botón Guardar (Pequeño y con Icono)
        self.btn_guardar = QPushButton(" 💾 ")
        self.btn_guardar.setToolTip("Guardar cambios actuales (Ctrl+S)")
        self.btn_guardar.setEnabled(False)
        self.btn_guardar.setFixedSize(50, 44)
        self.btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        # Símbolo diskette en el texto para máxima compatibilidad
        self.btn_guardar.setFont(QFont("Segoe UI Emoji", 15)) 
        self.apply_style_guardar("disabled")
        self.btn_guardar.clicked.connect(self.callbacks["guardar"])
        main_lay.addWidget(self.btn_guardar)

        # Separador visual
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("background: #444;")
        line.setFixedWidth(1)
        line.setFixedHeight(30)
        main_lay.addWidget(line)

        # 2. Sección de Exportación (Mejorada)
        exp_lay = QHBoxLayout()
        exp_lay.setSpacing(6)
        
        lbl_exp = QLabel("EXPORTAR A:")
        lbl_exp.setStyleSheet(f"color:{self.colores['fg_secundario']}; font-weight:bold; font-size:9px;")
        exp_lay.addWidget(lbl_exp)

        # Botones de exportación (HTML, EXCEL, PDF)
        self.export_btns = {}
        
        # HTML
        btn_html = self._create_export_btn("🌐 HTML", self.callbacks["exportar_html"])
        exp_lay.addWidget(btn_html)
        self.export_btns["html"] = btn_html

        # EXCEL
        btn_excel = self._create_export_btn("📊 EXCEL", self.callbacks["exportar_excel"])
        exp_lay.addWidget(btn_excel)
        self.export_btns["excel"] = btn_excel

        # PDF
        btn_pdf = self._create_export_btn("📄 PDF", self.callbacks["exportar_pdf"])
        exp_lay.addWidget(btn_pdf)
        self.export_btns["pdf"] = btn_pdf
        
        main_lay.addLayout(exp_lay)
        main_lay.addStretch()

    def _hex_to_rgb(self, hex_str):
        hex_str = hex_str.lstrip('#')
        if len(hex_str) == 3:
            hex_str = ''.join(c*2 for c in hex_str)
        return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"

    def _create_export_btn(self, text, callback):
        btn = QPushButton(text)
        btn.setEnabled(False)
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255, 255, 255, 0.02); 
                color: {self.colores['fg_secundario']}; 
                border-radius: 8px; 
                padding: 6px 15px; 
                font-weight: bold; 
                font-size: 11px; 
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            QPushButton:enabled {{ 
                background: rgba(255, 255, 255, 0.04); 
                color: white; 
                border: 1px solid rgba(255, 255, 255, 0.12); 
            }}
            QPushButton:enabled:hover {{ 
                background: rgba({{self._hex_to_rgb('{self.colores['acento']}')}}, 0.2); 
                color: white; 
                border: 1px solid {self.colores['acento']}; 
            }}
            QPushButton:enabled:pressed {{
                background: rgba({{self._hex_to_rgb('{self.colores['acento']}')}}, 0.35); 
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def apply_style_guardar(self, state):
        # State can be: modified, saved, disabled
        color = "rgba(255, 255, 255, 0.02)"
        border = "rgba(255, 255, 255, 0.05)"
        fg = self.colores['fg_secundario']
        
        if state == "saved":
            color = "rgba(52, 211, 153, 0.12)"
            border = self.colores['exito']
            fg = self.colores['exito']
        elif state == "modified":
            color = f"rgba({{self._hex_to_rgb('{self.colores['acento']}')}}, 0.25)"
            border = self.colores['acento']
            fg = "white"
        elif state == "disabled":
            color = "rgba(255, 255, 255, 0.01)"
            border = "rgba(255, 255, 255, 0.03)"
            fg = "rgba(255, 255, 255, 0.15)"
            
        self.btn_guardar.setStyleSheet(f"""
            QPushButton {{ 
                background: {color}; 
                color: {fg}; 
                border: 1px solid {border}; 
                border-radius: 8px; 
            }}
            QPushButton:hover:enabled {{
                background: rgba({{self._hex_to_rgb('{self.colores['acento']}')}}, 0.35); 
                border: 1px solid {self.colores['acento']}; 
                color: white;
            }}
        """)

    def set_enabled_all(self, enabled):
        self.btn_guardar.setEnabled(enabled)
        for btn in self.export_btns.values():
            btn.setEnabled(enabled)
        if not enabled:
            self.apply_style_guardar("disabled")
        else:
            self.apply_style_guardar("saved")
