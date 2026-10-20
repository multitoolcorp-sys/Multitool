"""
asistente_formulas.py — Diálogo Asistente de Fórmulas y Funciones matemáticas estilo Excel.
Permite explorar catálogo de funciones, filtrar por categoría o nombre, ver sintaxis/ejemplos
e insertar plantillas de fórmulas directamente en la hoja de cálculo.
"""
import platform
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QListWidget, QListWidgetItem, QPushButton,
    QFrame, QTextBrowser, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from ...utils.formula_engine import CATALOGO_FORMULAS, index_to_col_name


class AsistenteFormulasDialog(QDialog):
    """Diálogo interactivo para buscar e insertar fórmulas matemáticas estilo Excel."""

    def __init__(self, colores, celda_activa_coords=(0, 0), callback_insertar=None, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.celda_coords = celda_activa_coords
        self.callback_insertar = callback_insertar
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.setWindowTitle("𝑓(𝑥) Asistente de Fórmulas")
        self.setMinimumSize(680, 500)
        self.resize(720, 520)

        self._build_ui()
        self._cargar_catalogo()

    def _hex_to_rgb(self, hex_str):
        hex_str = str(hex_str).lstrip('#')
        if len(hex_str) == 3:
            hex_str = ''.join(c*2 for c in hex_str)
        try:
            return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"
        except Exception:
            return "99, 102, 241"

    def _build_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')
        rgb_acento = self._hex_to_rgb(acento)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_main};
                color: #FFFFFF;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # ── Header ──
        hdr = QHBoxLayout()
        lbl_icon = QLabel("𝑓(𝑥)")
        lbl_icon.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        lbl_icon.setStyleSheet(f"color: {acento}; padding-right: 6px;")
        hdr.addWidget(lbl_icon)

        v_hdr = QVBoxLayout()
        v_hdr.setSpacing(2)
        lbl_title = QLabel("Asistente de Fórmulas y Funciones")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #FFFFFF;")
        
        row, col = self.celda_coords
        col_letter = index_to_col_name(col)
        coord_str = f"{col_letter}{row+1}"
        lbl_sub = QLabel(f"Inserta cálculos matemáticos y estadísticos en la celda activa [{coord_str}]")
        lbl_sub.setFont(QFont(self.font_family, 9))
        lbl_sub.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        v_hdr.addWidget(lbl_title)
        v_hdr.addWidget(lbl_sub)
        hdr.addLayout(v_hdr, 1)

        layout.addLayout(hdr)

        # ── Filtros (Categoría y Buscador) ──
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.combo_cat = QComboBox()
        self.combo_cat.addItem("Todas las categorías")
        cats = sorted(list(set(f["categoria"] for f in CATALOGO_FORMULAS)))
        self.combo_cat.addItems(cats)
        self.combo_cat.setFixedWidth(200)
        self.combo_cat.setStyleSheet(f"""
            QComboBox {{
                background: {bg_sec};
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 11px;
            }}
            QComboBox QAbstractItemView {{
                background: {bg_sec};
                color: white;
                selection-background-color: {acento};
            }}
        """)
        self.combo_cat.currentTextChanged.connect(self._filtrar_formulas)
        filter_bar.addWidget(self.combo_cat)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Buscar función (ej: SUMA, PROMEDIO)...")
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background: {bg_sec};
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1px solid {acento};
            }}
        """)
        self.txt_search.textChanged.connect(self._filtrar_formulas)
        filter_bar.addWidget(self.txt_search, 1)

        layout.addLayout(filter_bar)

        # ── Panel Central (Lista + Detalles) ──
        body = QHBoxLayout()
        body.setSpacing(12)

        # Lista de Fórmulas
        self.list_formulas = QListWidget()
        self.list_formulas.setFixedWidth(210)
        self.list_formulas.setStyleSheet(f"""
            QListWidget {{
                background: {bg_sec};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 6px;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 6px;
                margin-bottom: 2px;
                font-weight: 500;
            }}
            QListWidget::item:selected {{
                background: rgba({rgb_acento}, 0.3);
                border: 1px solid {acento};
                color: #FFFFFF;
            }}
            QListWidget::item:hover:!selected {{
                background: rgba(255, 255, 255, 0.05);
            }}
        """)
        self.list_formulas.currentRowChanged.connect(self._mostrar_detalle_formula)
        self.list_formulas.itemDoubleClicked.connect(self._insertar_seleccionada)
        body.addWidget(self.list_formulas)

        # Tarjeta de Detalles
        self.card_detalle = QFrame()
        self.card_detalle.setStyleSheet(f"""
            QFrame {{
                background: {bg_sec};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 14px;
            }}
        """)
        c_lay = QVBoxLayout(self.card_detalle)
        c_lay.setContentsMargins(16, 16, 16, 16)
        c_lay.setSpacing(10)

        self.lbl_fn_nombre = QLabel("SUMA")
        self.lbl_fn_nombre.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.lbl_fn_nombre.setStyleSheet(f"color: {acento};")
        c_lay.addWidget(self.lbl_fn_nombre)

        self.lbl_fn_cat = QLabel("Categoría: Matemáticas & Aritmética")
        self.lbl_fn_cat.setFont(QFont(self.font_family, 9))
        self.lbl_fn_cat.setStyleSheet("color: rgba(255, 255, 255, 0.5);")
        c_lay.addWidget(self.lbl_fn_cat)

        lbl_sint_tit = QLabel("SINTAXIS:")
        lbl_sint_tit.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_sint_tit.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        c_lay.addWidget(lbl_sint_tit)

        self.lbl_fn_sintaxis = QLabel("=SUMA(A1:A10)")
        self.lbl_fn_sintaxis.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.lbl_fn_sintaxis.setStyleSheet(f"""
            background: rgba(0, 0, 0, 0.3);
            color: #34D399;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        """)
        c_lay.addWidget(self.lbl_fn_sintaxis)

        lbl_desc_tit = QLabel("DESCRIPCIÓN:")
        lbl_desc_tit.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_desc_tit.setStyleSheet("color: rgba(255, 255, 255, 0.6); margin-top: 4px;")
        c_lay.addWidget(lbl_desc_tit)

        self.txt_fn_desc = QLabel("Suma todos los números en un rango de celdas o lista de valores.")
        self.txt_fn_desc.setFont(QFont(self.font_family, 10))
        self.txt_fn_desc.setWordWrap(True)
        self.txt_fn_desc.setStyleSheet("color: #E2E2E2; line-height: 1.4;")
        c_lay.addWidget(self.txt_fn_desc)

        lbl_ejem_tit = QLabel("EJEMPLO DE USO:")
        lbl_ejem_tit.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_ejem_tit.setStyleSheet("color: rgba(255, 255, 255, 0.6); margin-top: 4px;")
        c_lay.addWidget(lbl_ejem_tit)

        self.lbl_fn_ejemplo = QLabel("=SUMA(A1:A10)")
        self.lbl_fn_ejemplo.setFont(QFont("Consolas", 10))
        self.lbl_fn_ejemplo.setStyleSheet(f"""
            background: rgba(0, 0, 0, 0.2);
            color: {acento};
            padding: 6px 10px;
            border-radius: 6px;
        """)
        c_lay.addWidget(self.lbl_fn_ejemplo)

        c_lay.addStretch()
        body.addWidget(self.card_detalle, 1)

        layout.addLayout(body, 1)

        # ── Botones de Acción Inferiores ──
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        btn_copiar = QPushButton("📋 Copiar Plantilla")
        btn_copiar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copiar.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.05);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.1);
            }}
        """)
        btn_copiar.clicked.connect(self._copiar_plantilla)
        btn_bar.addWidget(btn_copiar)

        btn_bar.addStretch()

        btn_cancelar = QPushButton("Cerrar")
        btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancelar.setStyleSheet("""
            QPushButton {{
                background: transparent;
                color: #AAB0B8;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.05);
                color: white;
            }}
        """)
        btn_cancelar.clicked.connect(self.reject)
        btn_bar.addWidget(btn_cancelar)

        self.btn_insertar = QPushButton("⚡ Insertar en Celda")
        self.btn_insertar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_insertar.setStyleSheet(f"""
            QPushButton {{
                background: {acento};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {self.colores.get('acento_hover', '#4F46E5')};
            }}
        """)
        self.btn_insertar.clicked.connect(self._insertar_seleccionada)
        btn_bar.addWidget(self.btn_insertar)

        layout.addLayout(btn_bar)

    def _cargar_catalogo(self):
        self._formulas_visibles = list(CATALOGO_FORMULAS)
        self._refrescar_lista()

    def _filtrar_formulas(self):
        cat = self.combo_cat.currentText()
        query = self.txt_search.text().strip().upper()

        filtradas = []
        for f in CATALOGO_FORMULAS:
            if cat != "Todas las categorías" and f["categoria"] != cat:
                continue
            if query and (query not in f["nombre"].upper() and query not in f["descripcion"].upper()):
                continue
            filtradas.append(f)

        self._formulas_visibles = filtradas
        self._refrescar_lista()

    def _refrescar_lista(self):
        self.list_formulas.clear()
        for f in self._formulas_visibles:
            it = QListWidgetItem(f["nombre"])
            it.setData(Qt.ItemDataRole.UserRole, f)
            self.list_formulas.addItem(it)

        if self.list_formulas.count() > 0:
            self.list_formulas.setCurrentRow(0)

    def _mostrar_detalle_formula(self, row):
        if row < 0 or row >= len(self._formulas_visibles):
            return
        f = self._formulas_visibles[row]
        self.lbl_fn_nombre.setText(f["nombre"])
        self.lbl_fn_cat.setText(f"Categoría: {f['categoria']}")
        self.lbl_fn_sintaxis.setText(f["sintaxis"])
        self.txt_fn_desc.setText(f["descripcion"])
        self.lbl_fn_ejemplo.setText(f["ejemplo"])

    def _get_formula_actual(self):
        it = self.list_formulas.currentItem()
        if it:
            return it.data(Qt.ItemDataRole.UserRole)
        return None

    def _generar_plantilla_formula(self, formula_info):
        r, c = self.celda_coords
        col_letter = index_to_col_name(c)
        rango_sug = f"{col_letter}1:{col_letter}{max(1, r)}" if r > 0 else f"{col_letter}2:{col_letter}10"
        celda_sug = f"{col_letter}1" if r > 0 else f"{col_letter}2"

        tmpl = formula_info.get("plantilla", formula_info["sintaxis"])
        return tmpl.replace("{rango}", rango_sug).replace("{celda}", celda_sug)

    def _insertar_seleccionada(self):
        f = self._get_formula_actual()
        if not f:
            return
        formula_txt = self._generar_plantilla_formula(f)
        if self.callback_insertar:
            self.callback_insertar(formula_txt)
        self.accept()

    def _copiar_plantilla(self):
        f = self._get_formula_actual()
        if not f:
            return
        formula_txt = self._generar_plantilla_formula(f)
        QApplication.clipboard().setText(formula_txt)
        self.lbl_fn_sintaxis.setText(f"{formula_txt} (¡Copiada!)")
