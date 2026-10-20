from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QComboBox, QColorDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class ToolbarCuaderno(QFrame):
    """Barra de herramientas compacta de formateo, alineación, fórmulas y rejilla para Cuaderno."""
    def __init__(self, colores, tabla, parent=None):
        super().__init__(parent)
        self.parent_gui = parent
        self.colores = colores
        self.tabla = tabla
        self._build_ui()

    def _hex_to_rgb(self, hex_str):
        hex_str = str(hex_str).lstrip('#')
        if len(hex_str) == 3:
            hex_str = ''.join(c*2 for c in hex_str)
        try:
            return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"
        except Exception:
            return "99, 102, 241"

    def _build_ui(self):
        self.setMinimumHeight(45)
        self.setMaximumHeight(50)
        self.setStyleSheet(f"""
            QFrame {{ 
                background: rgba(30, 30, 46, 0.4); 
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px; 
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(5)

        rgb_acento = self._hex_to_rgb(self.colores.get('acento', '#6366F1'))

        # Tamaño fuente
        self.combo_size = QComboBox()
        self.combo_size.addItems([str(s) for s in range(8, 26, 2)])
        self.combo_size.setCurrentText("10")
        self.combo_size.setFixedWidth(52)
        self.combo_size.setToolTip("Tamaño de Fuente")
        self.combo_size.setStyleSheet(self._combo_style())
        self.combo_size.currentTextChanged.connect(lambda v: self.tabla.aplicar_formateo("size", v))
        lay.addWidget(self.combo_size)

        # Negrita / Cursiva
        self.btn_bold = self._create_btn("B", "bold", bold=True, tooltip="Negrita (Ctrl+B)")
        self.btn_italic = self._create_btn("I", "italic", italic=True, tooltip="Cursiva (Ctrl+I)")
        lay.addWidget(self.btn_bold)
        lay.addWidget(self.btn_italic)

        # Alineación
        btn_align_left = self._create_action_btn("⫷", lambda: self.tabla.aplicar_formateo("align", "left"), "Alinear Izquierda")
        btn_align_center = self._create_action_btn("≡", lambda: self.tabla.aplicar_formateo("align", "center"), "Alinear Centro")
        btn_align_right = self._create_action_btn("⫸", lambda: self.tabla.aplicar_formateo("align", "right"), "Alinear Derecha")
        lay.addWidget(btn_align_left)
        lay.addWidget(btn_align_center)
        lay.addWidget(btn_align_right)

        lay.addSpacing(6)

        # Colores (Texto y Fondo)
        btn_fg = QPushButton("Tex")
        btn_fg.setToolTip("Color de Texto")
        btn_fg.setFixedWidth(40)
        btn_fg.setFixedHeight(30)
        btn_fg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fg.setStyleSheet(f"""
            QPushButton {{ 
                color: white; 
                background: rgba(255, 255, 255, 0.03); 
                border: 1px solid rgba(255, 255, 255, 0.08); 
                border-bottom: 3px solid {self.colores.get('acento', '#6366F1')}; 
                font-weight: bold; 
                font-size: 11px;
                border-radius: 6px; 
            }}
            QPushButton:hover {{ 
                background: rgba({rgb_acento}, 0.15); 
            }}
        """)
        btn_fg.clicked.connect(self._select_fg)
        lay.addWidget(btn_fg)

        btn_bg = QPushButton("Fon")
        btn_bg.setToolTip("Color de Fondo")
        btn_bg.setFixedWidth(40)
        btn_bg.setFixedHeight(30)
        btn_bg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_bg.setStyleSheet(f"""
            QPushButton {{ 
                color: white; 
                background: rgba(255, 255, 255, 0.03); 
                border: 1px solid rgba(255, 255, 255, 0.08); 
                border-bottom: 3px solid #34D399; 
                font-weight: bold; 
                font-size: 11px;
                border-radius: 6px; 
            }}
            QPushButton:hover {{ 
                background: rgba(52, 211, 153, 0.15); 
            }}
        """)
        btn_bg.clicked.connect(self._select_bg)
        lay.addWidget(btn_bg)

        lay.addSpacing(6)

        # Formatos Numéricos & Autosuma
        btn_curr = self._create_action_btn("$", lambda: self.tabla.aplicar_formateo("currency"), "Formato Moneda ($)")
        btn_pct = self._create_action_btn("%", lambda: self.tabla.aplicar_formateo("percent"), "Formato Porcentaje (%)")
        btn_sum = self._create_action_btn("∑", self.tabla.sumar_columna_actual, "Autosuma Columna (=SUMA)")
        lay.addWidget(btn_curr)
        lay.addWidget(btn_pct)
        lay.addWidget(btn_sum)

        lay.addSpacing(6)

        # Undo / Redo
        btn_undo = self._create_action_btn("↶", self.tabla.undo, "Deshacer (Ctrl+Z)")
        btn_redo = self._create_action_btn("↷", self.tabla.redo, "Rehacer (Ctrl+Y)")
        lay.addWidget(btn_undo)
        lay.addWidget(btn_redo)

        # Filas / Columnas
        btn_add_row = self._create_action_btn("+R", self.tabla._insertar_fila, "Insertar fila abajo")
        btn_add_col = self._create_action_btn("+C", self.tabla._insertar_columna, "Insertar columna a la derecha")
        lay.addWidget(btn_add_row)
        lay.addWidget(btn_add_col)

        # Gráficos (Chart Studio)
        self.btn_chart = QPushButton("📊")
        self.btn_chart.setToolTip("Generar gráfico estadístico")
        self.btn_chart.setFixedWidth(40)
        self.btn_chart.setFixedHeight(30)
        self.btn_chart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_chart.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255, 255, 255, 0.03); 
                color: {self.colores.get('fg_principal', '#E2E2E2')}; 
                border-radius: 6px; 
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
            QPushButton:hover {{ 
                background: rgba({rgb_acento}, 0.2); 
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
        if self.parent_gui and hasattr(self.parent_gui, '_toggle_chart_studio'):
            self.btn_chart.clicked.connect(self.parent_gui._toggle_chart_studio)
        lay.addWidget(self.btn_chart)

        # Tipo de Rejilla
        self.combo_grid = QComboBox()
        self.combo_grid.addItems(["🏁 Cuadrícula", "📜 Líneas", "📄 Sin rejilla"])
        self.combo_grid.setFixedWidth(110)
        self.combo_grid.setToolTip("Estilo de rejilla")
        self.combo_grid.setStyleSheet(self._combo_style())
        self.combo_grid.currentIndexChanged.connect(self._on_grid_changed)
        lay.addWidget(self.combo_grid)

        lay.addStretch()

    def _on_grid_changed(self, idx):
        modos = ["cuadricula", "lineas", "sin_rejilla"]
        if 0 <= idx < len(modos):
            if hasattr(self.tabla, "cambiar_estilo_rejilla"):
                self.tabla.cambiar_estilo_rejilla(modos[idx])

    def _create_btn(self, text, logic_type, bold=False, italic=False, tooltip=None):
        btn = QPushButton(text)
        if tooltip: btn.setToolTip(tooltip)
        btn.setFixedWidth(36)
        btn.setFixedHeight(30)
        font = QFont("Segoe UI", 10)
        font.setBold(bold)
        font.setItalic(italic)
        btn.setFont(font)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rgb_acento = self._hex_to_rgb(self.colores.get('acento', '#6366F1'))
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255, 255, 255, 0.03); 
                color: {self.colores.get('fg_principal', '#E2E2E2')}; 
                border-radius: 6px; 
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
            QPushButton:hover {{ 
                background: rgba({rgb_acento}, 0.2); 
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
        if logic_type in ["bold", "italic"]:
            btn.clicked.connect(lambda: self.tabla.aplicar_formateo(logic_type))
        return btn

    def _create_action_btn(self, text, callback, tooltip=None):
        btn = QPushButton(text)
        if tooltip: btn.setToolTip(tooltip)
        btn.setFixedWidth(36)
        btn.setFixedHeight(30)
        font = QFont("Segoe UI", 9)
        btn.setFont(font)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rgb_acento = self._hex_to_rgb(self.colores.get('acento', '#6366F1'))
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255, 255, 255, 0.03); 
                color: {self.colores.get('fg_principal', '#E2E2E2')}; 
                border-radius: 6px; 
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
            QPushButton:hover {{ 
                background: rgba({rgb_acento}, 0.2); 
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def _combo_style(self):
        return f"""
            QComboBox {{
                background: rgba(45, 45, 61, 0.6);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 6px;
                font-size: 11px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 16px;
            }}
            QComboBox QAbstractItemView {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                selection-background-color: {self.colores.get('acento', '#6366F1')};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
            }}
        """

    def _select_fg(self):
        dlg = QColorDialog(Qt.GlobalColor.white, self)
        if dlg.exec(): self.tabla.aplicar_formateo("fg", dlg.selectedColor().name())

    def _select_bg(self):
        dlg = QColorDialog(QColor(self.colores.get('acento', '#6366F1')), self)
        if dlg.exec(): self.tabla.aplicar_formateo("bg", dlg.selectedColor().name())

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(f"""
            QFrame {{ 
                background: rgba(30, 30, 46, 0.4); 
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px; 
            }}
        """)
