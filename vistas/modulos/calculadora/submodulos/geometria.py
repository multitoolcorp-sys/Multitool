import math
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QComboBox, QGridLayout, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class TabCalculadoraGeometria(QWidget):
    """Calculadora Geométrica para figuras 2D y 3D"""
    def __init__(self, parent=None, colores=None, add_historial_callback=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.add_historial = add_historial_callback
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.init_ui()

    def init_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        fg_main = self.colores.get('fg_principal', '#E2E2E2')

        self.setStyleSheet(f"""
            QWidget {{ background-color: {bg_main}; color: {fg_main}; }}
            QLineEdit {{ background-color: {bg_terc}; color: white; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 6px; selection-background-color: {acento}; }}
            QComboBox {{ background-color: {bg_sec}; color: white; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 5px 10px; }}
            QComboBox QAbstractItemView {{ background-color: {bg_sec}; color: white; selection-background-color: {acento}; }}
            QLabel {{ color: {fg_main}; }}
        """)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(15, 15, 15, 15)
        main_lay.setSpacing(10)

        # Header
        lbl_head = QLabel("📐 CALCULADORA GEOMÉTRICA 2D & 3D")
        lbl_head.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_head.setStyleSheet(f"color: {acento};")
        main_lay.addWidget(lbl_head)

        # Selector de Figura
        fig_lay = QHBoxLayout()
        lbl_fig = QLabel("Seleccionar Figura/Cuerpo:")
        lbl_fig.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_fig.setStyleSheet("color: white;")
        fig_lay.addWidget(lbl_fig)

        self.combo_figuras = QComboBox()
        self.combo_figuras.setFont(QFont(self.font_family, 10))
        self.combo_figuras.addItems([
            "🔵 Círculo (2D)",
            "📐 Triángulo (2D)",
            "⬛ Rectángulo (2D)",
            "🌐 Esfera (3D)",
            "🛢️ Cilindro (3D)",
            "📐 Cono (3D)",
            "🎲 Cubo (3D)",
            "🔺 Teorema de Pitágoras"
        ])
        self.combo_figuras.currentIndexChanged.connect(self._on_figura_changed)
        fig_lay.addWidget(self.combo_figuras, 1)
        main_lay.addLayout(fig_lay)

        # Stack de paneles de cálculo
        self.stack = QStackedWidget()
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')

        # 0: Círculo
        self.stack.addWidget(self._crear_panel_circulo())
        # 1: Triángulo
        self.stack.addWidget(self._crear_panel_triangulo())
        # 2: Rectángulo
        self.stack.addWidget(self._crear_panel_rectangulo())
        # 3: Esfera
        self.stack.addWidget(self._crear_panel_esfera())
        # 4: Cilindro
        self.stack.addWidget(self._crear_panel_cilindro())
        # 5: Cono
        self.stack.addWidget(self._crear_panel_cono())
        # 6: Cubo
        self.stack.addWidget(self._crear_panel_cubo())
        # 7: Pitágoras
        self.stack.addWidget(self._crear_panel_pitagoras())

        main_lay.addWidget(self.stack, 1)

    def _on_figura_changed(self, idx):
        self.stack.setCurrentIndex(idx)

    def _crear_card_base(self, titulo):
        card = QFrame()
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        card.setStyleSheet(f"background: {bg_sec}; border-radius: 12px; padding: 15px;")
        lay = QVBoxLayout(card)
        lay.setSpacing(10)
        
        lbl_t = QLabel(titulo)
        lbl_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        lay.addWidget(lbl_t)
        return card, lay

    # 0: Círculo
    def _crear_panel_circulo(self):
        card, lay = self._crear_card_base("🔵 Círculo (Área y Perímetro)")
        
        txt_r = QLineEdit()
        txt_r.setPlaceholderText("Radio (r)")
        lay.addWidget(txt_r)

        lbl_res = QLabel("Área: - | Perímetro: -")
        lbl_res.setFont(QFont(self.mono_font, 11, QFont.Weight.Bold))
        lbl_res.setStyleSheet("color: #34D399;")
        lay.addWidget(lbl_res)

        btn = QPushButton("⚡ Calcular Círculo")
        acento = self.colores.get('acento', '#6366F1')
        btn.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 8px; font-weight: bold;")
        
        def calc():
            try:
                r = float(txt_r.text())
                area = math.pi * (r ** 2)
                per = 2 * math.pi * r
                lbl_res.setText(f"Área: {area:.4f} | Perímetro: {per:.4f}")
                if self.add_historial:
                    self.add_historial(f"Círculo (r={r})", f"Área: {area:.4f}, Perímetro: {per:.4f}")
            except:
                lbl_res.setText("⚠️ Ingresa un valor numérico válido")

        btn.clicked.connect(calc)
        lay.addWidget(btn)
        lay.addStretch()
        return card

    # 1: Triángulo
    def _crear_panel_triangulo(self):
        card, lay = self._crear_card_base("📐 Triángulo (Base y Altura)")
        
        txt_b = QLineEdit(); txt_b.setPlaceholderText("Base (b)")
        txt_h = QLineEdit(); txt_h.setPlaceholderText("Altura (h)")
        lay.addWidget(txt_b); lay.addWidget(txt_h)

        lbl_res = QLabel("Área: -")
        lbl_res.setFont(QFont(self.mono_font, 11, QFont.Weight.Bold))
        lay.addWidget(lbl_res)

        btn = QPushButton("⚡ Calcular Triángulo")
        acento = self.colores.get('acento', '#6366F1')
        btn.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 8px; font-weight: bold;")
        
        def calc():
            try:
                b, h = float(txt_b.text()), float(txt_h.text())
                area = (b * h) / 2
                lbl_res.setText(f"Área: {area:.4f}")
                if self.add_historial:
                    self.add_historial(f"Triángulo (b={b}, h={h})", f"Área: {area:.4f}")
            except:
                lbl_res.setText("⚠️ Ingresa valores válidos")

        btn.clicked.connect(calc)
        lay.addWidget(btn)
        lay.addStretch()
        return card

    # 2: Rectángulo
    def _crear_panel_rectangulo(self):
        card, lay = self._crear_card_base("⬛ Rectángulo (Base y Altura)")
        
        txt_b = QLineEdit(); txt_b.setPlaceholderText("Ancho / Base")
        txt_h = QLineEdit(); txt_h.setPlaceholderText("Largo / Altura")
        lay.addWidget(txt_b); lay.addWidget(txt_h)

        lbl_res = QLabel("Área: - | Perímetro: -")
        lbl_res.setFont(QFont(self.mono_font, 11, QFont.Weight.Bold))
        lay.addWidget(lbl_res)

        btn = QPushButton("⚡ Calcular Rectángulo")
        acento = self.colores.get('acento', '#6366F1')
        btn.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 8px; font-weight: bold;")
        
        def calc():
            try:
                b, h = float(txt_b.text()), float(txt_h.text())
                area = b * h
                per = 2 * (b + h)
                lbl_res.setText(f"Área: {area:.4f} | Perímetro: {per:.4f}")
                if self.add_historial:
                    self.add_historial(f"Rectángulo ({b}x{h})", f"Área: {area:.4f}, Perímetro: {per:.4f}")
            except:
                lbl_res.setText("⚠️ Ingresa valores válidos")

        btn.clicked.connect(calc)
        lay.addWidget(btn)
        lay.addStretch()
        return card

    # 3: Esfera
    def _crear_panel_esfera(self):
        card, lay = self._crear_card_base("🌐 Esfera (Volumen y Área Superficial)")
        
        txt_r = QLineEdit(); txt_r.setPlaceholderText("Radio (r)")
        lay.addWidget(txt_r)

        lbl_res = QLabel("Volumen: - | Área Superficial: -")
        lbl_res.setFont(QFont(self.mono_font, 11, QFont.Weight.Bold))
        lay.addWidget(lbl_res)

        btn = QPushButton("⚡ Calcular Esfera")
        acento = self.colores.get('acento', '#6366F1')
        btn.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 8px; font-weight: bold;")
        
        def calc():
            try:
                r = float(txt_r.text())
                vol = (4/3) * math.pi * (r ** 3)
                surf = 4 * math.pi * (r ** 2)
                lbl_res.setText(f"Volumen: {vol:.4f} | Área Sup.: {surf:.4f}")
                if self.add_historial:
                    self.add_historial(f"Esfera (r={r})", f"Vol: {vol:.4f}, Área Sup: {surf:.4f}")
            except:
                lbl_res.setText("⚠️ Ingresa un radio válido")

        btn.clicked.connect(calc)
        lay.addWidget(btn)
        lay.addStretch()
        return card

    # 4: Cilindro
    def _crear_panel_cilindro(self):
        card, lay = self._crear_card_base("🛢️ Cilindro (Radio y Altura)")
        
        txt_r = QLineEdit(); txt_r.setPlaceholderText("Radio de la base (r)")
        txt_h = QLineEdit(); txt_h.setPlaceholderText("Altura (h)")
        lay.addWidget(txt_r); lay.addWidget(txt_h)

        lbl_res = QLabel("Volumen: - | Área Total: -")
        lbl_res.setFont(QFont(self.mono_font, 11, QFont.Weight.Bold))
        lay.addWidget(lbl_res)

        btn = QPushButton("⚡ Calcular Cilindro")
        acento = self.colores.get('acento', '#6366F1')
        btn.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 8px; font-weight: bold;")
        
        def calc():
            try:
                r, h = float(txt_r.text()), float(txt_h.text())
                vol = math.pi * (r ** 2) * h
                area = 2 * math.pi * r * (r + h)
                lbl_res.setText(f"Volumen: {vol:.4f} | Área Total: {area:.4f}")
                if self.add_historial:
                    self.add_historial(f"Cilindro (r={r}, h={h})", f"Vol: {vol:.4f}, Área: {area:.4f}")
            except:
                lbl_res.setText("⚠️ Ingresa valores válidos")

        btn.clicked.connect(calc)
        lay.addWidget(btn)
        lay.addStretch()
        return card

    # 5: Cono
    def _crear_panel_cono(self):
        card, lay = self._crear_card_base("📐 Cono (Radio y Altura)")
        
        txt_r = QLineEdit(); txt_r.setPlaceholderText("Radio (r)")
        txt_h = QLineEdit(); txt_h.setPlaceholderText("Altura (h)")
        lay.addWidget(txt_r); lay.addWidget(txt_h)

        lbl_res = QLabel("Volumen: -")
        lbl_res.setFont(QFont(self.mono_font, 11, QFont.Weight.Bold))
        lay.addWidget(lbl_res)

        btn = QPushButton("⚡ Calcular Cono")
        acento = self.colores.get('acento', '#6366F1')
        btn.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 8px; font-weight: bold;")
        
        def calc():
            try:
                r, h = float(txt_r.text()), float(txt_h.text())
                vol = (1/3) * math.pi * (r ** 2) * h
                lbl_res.setText(f"Volumen: {vol:.4f}")
                if self.add_historial:
                    self.add_historial(f"Cono (r={r}, h={h})", f"Volumen: {vol:.4f}")
            except:
                lbl_res.setText("⚠️ Ingresa valores válidos")

        btn.clicked.connect(calc)
        lay.addWidget(btn)
        lay.addStretch()
        return card

    # 6: Cubo
    def _crear_panel_cubo(self):
        card, lay = self._crear_card_base("🎲 Cubo (Lado a)")
        
        txt_a = QLineEdit(); txt_a.setPlaceholderText("Longitud del lado (a)")
        lay.addWidget(txt_a)

        lbl_res = QLabel("Volumen: - | Área Superficial: -")
        lbl_res.setFont(QFont(self.mono_font, 11, QFont.Weight.Bold))
        lay.addWidget(lbl_res)

        btn = QPushButton("⚡ Calcular Cubo")
        acento = self.colores.get('acento', '#6366F1')
        btn.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 8px; font-weight: bold;")
        
        def calc():
            try:
                a = float(txt_a.text())
                vol = a ** 3
                surf = 6 * (a ** 2)
                lbl_res.setText(f"Volumen: {vol:.4f} | Área Sup.: {surf:.4f}")
                if self.add_historial:
                    self.add_historial(f"Cubo (a={a})", f"Vol: {vol:.4f}, Área Sup: {surf:.4f}")
            except:
                lbl_res.setText("⚠️ Ingresa un lado válido")

        btn.clicked.connect(calc)
        lay.addWidget(btn)
        lay.addStretch()
        return card

    # 7: Pitágoras
    def _crear_panel_pitagoras(self):
        card, lay = self._crear_card_base("🔺 Teorema de Pitágoras (a² + b² = c²)")
        
        txt_a = QLineEdit(); txt_a.setPlaceholderText("Cateto a")
        txt_b = QLineEdit(); txt_b.setPlaceholderText("Cateto b")
        lay.addWidget(txt_a); lay.addWidget(txt_b)

        lbl_res = QLabel("Hipotenusa (c): -")
        lbl_res.setFont(QFont(self.mono_font, 11, QFont.Weight.Bold))
        lay.addWidget(lbl_res)

        btn = QPushButton("⚡ Calcular Hipotenusa (c)")
        acento = self.colores.get('acento', '#6366F1')
        btn.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 8px; font-weight: bold;")
        
        def calc():
            try:
                a, b = float(txt_a.text()), float(txt_b.text())
                c = math.sqrt(a**2 + b**2)
                lbl_res.setText(f"Hipotenusa (c): {c:.4f}")
                if self.add_historial:
                    self.add_historial(f"Pitágoras (a={a}, b={b})", f"c = {c:.4f}")
            except:
                lbl_res.setText("⚠️ Ingresa catetos válidos")

        btn.clicked.connect(calc)
        lay.addWidget(btn)
        lay.addStretch()
        return card
