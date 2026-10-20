import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QComboBox, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class TabCalculadoraProgramador(QWidget):
    """Calculadora para Programadores (Hex, Dec, Oct, Bin & Operaciones Bitwise)"""
    def __init__(self, parent=None, colores=None, add_historial_callback=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.add_historial = add_historial_callback
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.word_bits = 32  # 8, 16, 32, 64
        self.base_actual = 10  # 16 (HEX), 10 (DEC), 8 (OCT), 2 (BIN)
        
        self.init_ui()

    def init_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(15, 15, 15, 15)
        main_lay.setSpacing(10)

        # Header
        lbl_head = QLabel("💻 CALCULADORA PROGRAMADOR")
        lbl_head.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        acento = self.colores.get('acento', '#6366F1')
        lbl_head.setStyleSheet(f"color: {acento};")
        main_lay.addWidget(lbl_head)

        # Contenedor de Displays de Bases (HEX, DEC, OCT, BIN)
        card_bases = QFrame()
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        card_bases.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 10px;")
        lay_bases = QVBoxLayout(card_bases)
        lay_bases.setSpacing(6)

        self.txt_hex = self._crear_display_base("HEX", lay_bases, 16)
        self.txt_dec = self._crear_display_base("DEC", lay_bases, 10)
        self.txt_oct = self._crear_display_base("OCT", lay_bases, 8)
        self.txt_bin = self._crear_display_base("BIN", lay_bases, 2)

        main_lay.addWidget(card_bases)

        # Selector de tamaño de palabra (Bits) y operaciones
        ctrl_lay = QHBoxLayout()
        lbl_bits = QLabel("Tamaño de palabra:")
        lbl_bits.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        ctrl_lay.addWidget(lbl_bits)

        self.combo_bits = QComboBox()
        self.combo_bits.addItems(["64-bit (QWORD)", "32-bit (DWORD)", "16-bit (WORD)", "8-bit (BYTE)"])
        self.combo_bits.setCurrentIndex(1)
        self.combo_bits.currentIndexChanged.connect(self._on_bits_changed)
        ctrl_lay.addWidget(self.combo_bits)

        ctrl_lay.addStretch()
        main_lay.addLayout(ctrl_lay)

        # Grid de Botones
        grid = QGridLayout()
        grid.setSpacing(6)

        btn_specs = [
            ["AND", "OR", "XOR", "NOT", "CLEAR"],
            ["LSH (<<)", "RSH (>>)", "HEX", "DEC", "BIN"],
            ["A", "B", "7", "8", "9"],
            ["C", "D", "4", "5", "6"],
            ["E", "F", "1", "2", "3"],
            ["(", ")", "0", "+/-", "="]
        ]

        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')

        for r, row in enumerate(btn_specs):
            for c, text in enumerate(row):
                btn = QPushButton(text)
                btn.setFont(QFont(self.mono_font, 10, QFont.Weight.Bold))
                btn.setMinimumHeight(40)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                
                if text in ["=", "CLEAR"]:
                    btn.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; border: none;")
                elif text in ["AND", "OR", "XOR", "NOT", "LSH (<<)", "RSH (>>)", "HEX", "DEC", "BIN"]:
                    btn.setStyleSheet("background: rgba(99, 102, 241, 0.15); color: #A5B4FC; border-radius: 6px; border: 1px solid rgba(99, 102, 241, 0.3);")
                else:
                    btn.setStyleSheet(f"background: {bg_ter}; color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")

                btn.clicked.connect(lambda ch, t=text: self._on_btn_click(t))
                grid.addWidget(btn, r, c)

        main_lay.addLayout(grid, 1)

    def _crear_display_base(self, label_text, parent_lay, base):
        h_lay = QHBoxLayout()
        lbl = QLabel(f"{label_text}:")
        lbl.setFixedWidth(45)
        lbl.setFont(QFont(self.mono_font, 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        
        txt = QLineEdit("0")
        txt.setFont(QFont(self.mono_font, 11))
        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')
        txt.setStyleSheet(f"background: {bg_ter}; color: white; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 4px 8px;")
        txt.textEdited.connect(lambda val, b=base: self._actualizar_desde_base(val, b))
        
        h_lay.addWidget(lbl)
        h_lay.addWidget(txt, 1)
        parent_lay.addLayout(h_lay)
        return txt

    def _on_bits_changed(self, idx):
        bits_map = [64, 32, 16, 8]
        self.word_bits = bits_map[idx]
        self._actualizar_desde_base(self.txt_dec.text(), 10)

    def _actualizar_desde_base(self, texto_val, base_origen):
        if not texto_val.strip():
            texto_val = "0"
        try:
            val = int(texto_val, base_origen)
            max_val = (1 << self.word_bits) - 1
            val = val & max_val

            self.txt_hex.blockSignals(True)
            self.txt_dec.blockSignals(True)
            self.txt_oct.blockSignals(True)
            self.txt_bin.blockSignals(True)

            self.txt_hex.setText(hex(val)[2:].upper())
            self.txt_dec.setText(str(val))
            self.txt_oct.setText(oct(val)[2:])
            self.txt_bin.setText(bin(val)[2:])

            self.txt_hex.blockSignals(False)
            self.txt_dec.blockSignals(False)
            self.txt_oct.blockSignals(False)
            self.txt_bin.blockSignals(False)
        except Exception:
            pass

    def _on_btn_click(self, text):
        if text == "CLEAR":
            self._actualizar_desde_base("0", 10)
        elif text == "=":
            if self.add_historial:
                self.add_historial(f"DEC: {self.txt_dec.text()}", f"HEX: 0x{self.txt_hex.text()} | BIN: {self.txt_bin.text()}")
        elif text in ["AND", "OR", "XOR"]:
            pass
        elif text == "NOT":
            try:
                val = int(self.txt_dec.text(), 10)
                max_val = (1 << self.word_bits) - 1
                val = (~val) & max_val
                self._actualizar_desde_base(str(val), 10)
            except: pass
        elif text == "LSH (<<)":
            try:
                val = int(self.txt_dec.text(), 10) << 1
                self._actualizar_desde_base(str(val), 10)
            except: pass
        elif text == "RSH (>>)":
            try:
                val = int(self.txt_dec.text(), 10) >> 1
                self._actualizar_desde_base(str(val), 10)
            except: pass
        else:
            if text in "0123456789ABCDEF":
                curr = self.txt_dec.text()
                if curr == "0":
                    curr = text
                else:
                    curr += text
                self._actualizar_desde_base(curr, 10)
