"""
quimica.py - Submódulo de Calculadora Química Avanzada para MultiTool
Incluye:
1. Calculadora de Masa Molar, Composición Porcentual y Conversión de Peso/Moles.
2. Visualizador Gráfico Molecular 2D interactivo con bolas y varillas (CPK).
3. Tabla Periódica Interactiva Completa de los 118 Elementos Químicos.
4. Balanceador de Ecuaciones Químicas, Ley de Gases Ideales y pH.
"""

import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QTabWidget, QGridLayout, QScrollArea,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QCompleter, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QCursor

from ..utils.quimica_data import (
    ELEMENTOS, CATEGORIAS, CPK_COLORS, COMPUESTOS_COMUNES, SIMBOLO_A_ELEM
)
from ..utils.quimica_math import (
    calcular_masa_molar, convertir_estequiometria, calcular_solucion_molar,
    balancear_ecuacion_quimica, AVOGADRO, R_GAS
)
from ..utils.molecular_canvas import MolecularCanvas


class TabCalculadoraQuimica(QWidget):
    """Submódulo completo de Calculadora Química para MultiTool."""
    def __init__(self, parent, colores=None, add_hist_callback=None):
        super().__init__(parent)
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#FFFFFF", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#4F46E5", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }
        self.add_hist_callback = add_hist_callback
        self.masa_molar_actual = 18.015
        self.formula_actual = "H2O"

        self.inicializar_ui()

    def inicializar_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Notebook interno de Química
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid rgba(255, 255, 255, 0.08);
                background: {self.colores['bg_secundario']};
                border-radius: 10px;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {self.colores['fg_secundario']};
                padding: 8px 18px;
                font-family: 'Inter';
                font-weight: bold;
                font-size: 10pt;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                color: {self.colores['acento']};
                border-bottom: 2px solid {self.colores['acento']};
                background: rgba(99, 102, 241, 0.08);
            }}
        """)

        # 1. Pestaña: Masa Molar & Peso
        self.tab_masa = self._crear_tab_masa_molar()
        self.sub_tabs.addTab(self.tab_masa, "🧪 Masa Molar & Peso")

        # 2. Pestaña: Visualizador Molecular
        self.tab_visor = self._crear_tab_visualizador()
        self.sub_tabs.addTab(self.tab_visor, "🔬 Visualizador Molecular")

        # 3. Pestaña: Tabla Periódica
        self.tab_tabla = self._crear_tab_tabla_periodica()
        self.sub_tabs.addTab(self.tab_tabla, "⚛️ Tabla Periódica")

        # 4. Pestaña: Reacciones & Gases
        self.tab_reacciones = self._crear_tab_reacciones()
        self.sub_tabs.addTab(self.tab_reacciones, "⚖️ Reacciones & Gases")

        main_layout.addWidget(self.sub_tabs)

    # =========================================================================
    # 1. PESTAÑA: MASA MOLAR, DESGLOSE Y CONVERSIÓN DE PESO
    # =========================================================================
    def _crear_tab_masa_molar(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1.1 Entrada de Fórmula y Sugerencias
        input_card = QFrame()
        input_card.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 12px;
                padding: 12px;
            }}
        """)
        ic_layout = QVBoxLayout(input_card)
        ic_layout.setSpacing(10)

        lbl_tit = QLabel("FÓRMULA QUÍMICA O COMPUESTO")
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']}; font-weight: bold; font-size: 10pt; letter-spacing: 1px;")
        ic_layout.addWidget(lbl_tit)

        h_in = QHBoxLayout()
        self.txt_formula = QLineEdit("C6H12O6")
        self.txt_formula.setFont(QFont("Inter", 13, QFont.Weight.Bold))
        self.txt_formula.setPlaceholderText("Ej: H2O, C6H12O6, CuSO4*5H2O, Ca(OH)2...")
        self.txt_formula.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_principal']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 10px 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colores['acento']};
            }}
        """)
        self.txt_formula.textChanged.connect(self._calcular_masa_en_vivo)
        h_in.addWidget(self.txt_formula, 2)

        # Selector de Sugerencias Rápidas
        self.combo_sugerencias = QComboBox()
        self.combo_sugerencias.addItem("💡 Sugerencias Rápidas...")
        for comp in COMPUESTOS_COMUNES:
            self.combo_sugerencias.addItem(f"{comp['formula']} - {comp['nombre']}", comp['formula'])
        self.combo_sugerencias.setFont(QFont("Inter", 9))
        self.combo_sugerencias.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_principal']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 8px 12px;
            }}
        """)
        self.combo_sugerencias.currentIndexChanged.connect(self._on_sugerencia_seleccionada)
        h_in.addWidget(self.combo_sugerencias, 1)

        btn_limpiar = QPushButton("🧹")
        btn_limpiar.setToolTip("Limpiar campo")
        btn_limpiar.setFixedSize(38, 38)
        btn_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_limpiar.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 8px;")
        btn_limpiar.clicked.connect(lambda: self.txt_formula.clear())
        h_in.addWidget(btn_limpiar)

        ic_layout.addLayout(h_in)
        layout.addWidget(input_card)

        # 1.2 Tarjeta de Resultado de Masa Molar
        self.res_card = QFrame()
        self.res_card.setStyleSheet(f"""
            QFrame {{
                background: rgba(99, 102, 241, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        rc_layout = QHBoxLayout(self.res_card)

        v_res_info = QVBoxLayout()
        self.lbl_res_formula = QLabel("Glucosa (C6H12O6)")
        self.lbl_res_formula.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.lbl_res_formula.setStyleSheet("color: #FFFFFF;")
        v_res_info.addWidget(self.lbl_res_formula)

        self.lbl_res_masa = QLabel("180.156 g/mol")
        self.lbl_res_masa.setFont(QFont("Inter", 22, QFont.Weight.Bold))
        self.lbl_res_masa.setStyleSheet(f"color: {self.colores['acento']};")
        v_res_info.addWidget(self.lbl_res_masa)

        self.lbl_res_stats = QLabel("3 Elementos | 24 Átomos totales")
        self.lbl_res_stats.setStyleSheet("color: #AAB0B8; font-size: 9pt;")
        v_res_info.addWidget(self.lbl_res_stats)
        rc_layout.addLayout(v_res_info)

        rc_layout.addStretch()

        btn_ver_mol = QPushButton("🔬 Ver en 3D/2D")
        btn_ver_mol.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        btn_ver_mol.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ver_mol.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
            }}
            QPushButton:hover {{
                background: {self.colores['acento_hover']};
            }}
        """)
        btn_ver_mol.clicked.connect(self._ir_a_visualizador)
        rc_layout.addWidget(btn_ver_mol)

        layout.addWidget(self.res_card)

        # 1.3 Tabla de Desglose Elemental y Composición %
        self.tabla_elem = QTableWidget()
        self.tabla_elem.setColumnCount(5)
        self.tabla_elem.setHorizontalHeaderLabels(["Elemento", "Átomos", "Masa Atómica", "Subtotal (g/mol)", "% en Masa"])
        self.tabla_elem.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_elem.setMinimumHeight(150)
        self.tabla_elem.setStyleSheet(f"""
            QTableWidget {{
                background: {self.colores['bg_principal']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                gridline-color: rgba(255, 255, 255, 0.05);
            }}
            QHeaderView::section {{
                background: {self.colores['bg_terciario']};
                color: {self.colores['acento']};
                font-weight: bold;
                padding: 6px;
                border: none;
            }}
        """)
        layout.addWidget(self.tabla_elem)

        # 1.4 Sección de Opciones de Peso y Conversión Estequiométrica
        conv_frame = QFrame()
        conv_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        cf_layout = QVBoxLayout(conv_frame)
        cf_layout.setSpacing(12)

        lbl_c_tit = QLabel("⚖️ CONVERTIDOR DE CANTIDAD DE SUSTANCIA Y PESO")
        lbl_c_tit.setStyleSheet(f"color: {self.colores['acento']}; font-weight: bold; font-size: 10pt;")
        cf_layout.addWidget(lbl_c_tit)

        h_conv_in = QHBoxLayout()
        self.txt_conv_val = QLineEdit("100")
        self.txt_conv_val.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.txt_conv_val.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_principal']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 8px 12px;
            }}
        """)
        self.txt_conv_val.textChanged.connect(self._convertir_peso_en_vivo)
        h_conv_in.addWidget(self.txt_conv_val, 2)

        self.combo_unidad = QComboBox()
        self.combo_unidad.addItems(["Gramos (g)", "Kilogramos (kg)", "Miligramos (mg)", "Moles (mol)", "Milimoles (mmol)", "Moléculas (N)"])
        self.combo_unidad.setFont(QFont("Inter", 10))
        self.combo_unidad.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_principal']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 8px 12px;
            }}
        """)
        self.combo_unidad.currentIndexChanged.connect(self._convertir_peso_en_vivo)
        h_conv_in.addWidget(self.combo_unidad, 1)

        cf_layout.addLayout(h_conv_in)

        # Resultados de la conversión
        self.grid_conv_res = QGridLayout()
        self.lbl_g_res = QLabel("100.0 g")
        self.lbl_mol_res = QLabel("0.555 mol")
        self.lbl_molec_res = QLabel("3.34e+23 moléculas")
        self.lbl_mg_res = QLabel("100,000 mg")

        labels_data = [
            ("Gramos:", self.lbl_g_res),
            ("Moles:", self.lbl_mol_res),
            ("Nº Moléculas:", self.lbl_molec_res),
            ("Miligramos:", self.lbl_mg_res)
        ]

        for i, (tit, lbl) in enumerate(labels_data):
            r = i // 2
            c = (i % 2) * 2
            t_lbl = QLabel(tit)
            t_lbl.setStyleSheet("color: #AAB0B8; font-weight: bold;")
            lbl.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 10pt;")
            self.grid_conv_res.addWidget(t_lbl, r, c)
            self.grid_conv_res.addWidget(lbl, r, c + 1)

        cf_layout.addLayout(self.grid_conv_res)
        layout.addWidget(conv_frame)

        # 1.5 Preparación de Soluciones Molares (M = mol/L)
        sol_frame = QFrame()
        sol_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        sf_layout = QVBoxLayout(sol_frame)
        sf_layout.setSpacing(10)

        lbl_s_tit = QLabel("🧪 PREPARACIÓN DE SOLUCIONES (MOLARIDAD)")
        lbl_s_tit.setStyleSheet(f"color: {self.colores['acento']}; font-weight: bold; font-size: 10pt;")
        sf_layout.addWidget(lbl_s_tit)

        h_sol_inputs = QHBoxLayout()
        h_sol_inputs.addWidget(QLabel("Molaridad deseada (M):"))
        self.txt_sol_m = QLineEdit("0.5")
        self.txt_sol_m.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 6px; padding: 6px;")
        self.txt_sol_m.textChanged.connect(self._calcular_solucion_en_vivo)
        h_sol_inputs.addWidget(self.txt_sol_m)

        h_sol_inputs.addWidget(QLabel("Volumen de Solución (mL):"))
        self.txt_sol_v = QLineEdit("500")
        self.txt_sol_v.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 6px; padding: 6px;")
        self.txt_sol_v.textChanged.connect(self._calcular_solucion_en_vivo)
        h_sol_inputs.addWidget(self.txt_sol_v)

        sf_layout.addLayout(h_sol_inputs)

        self.lbl_sol_resultado = QLabel("Masa de soluto necesaria: 45.039 g (45,039 mg)")
        self.lbl_sol_resultado.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.lbl_sol_resultado.setStyleSheet(f"color: {self.colores['exito']}; padding-top: 4px;")
        sf_layout.addWidget(self.lbl_sol_resultado)

        layout.addWidget(sol_frame)

        scroll.setWidget(container)
        
        main_v = QVBoxLayout(widget)
        main_v.setContentsMargins(0, 0, 0, 0)
        main_v.addWidget(scroll)

        # Realizar cálculo inicial
        self._calcular_masa_en_vivo()
        return widget

    def _on_sugerencia_seleccionada(self, idx):
        if idx > 0:
            form = self.combo_sugerencias.itemData(idx)
            if form:
                self.txt_formula.setText(form)

    def _calcular_masa_en_vivo(self):
        txt = self.txt_formula.text().strip()
        if not txt:
            return

        try:
            res = calcular_masa_molar(txt)
            self.formula_actual = txt
            self.masa_molar_actual = res["masa_molar"]

            self.lbl_res_formula.setText(f"Fórmula: {res['formula']}")
            self.lbl_res_masa.setText(f"{res['masa_molar']:.4f} g/mol")
            self.lbl_res_stats.setText(f"{res['num_elementos']} Elementos | {int(res['num_atomos'])} Átomos totales")

            # Llenar tabla
            self.tabla_elem.setRowCount(len(res["desglose"]))
            for r, d in enumerate(res["desglose"]):
                self.tabla_elem.setItem(r, 0, QTableWidgetItem(f"{d['simbolo']} ({d['nombre']})"))
                self.tabla_elem.setItem(r, 1, QTableWidgetItem(str(int(d['cantidad']) if d['cantidad'].is_integer() else d['cantidad'])))
                self.tabla_elem.setItem(r, 2, QTableWidgetItem(f"{d['peso_atomico']:.3f}"))
                self.tabla_elem.setItem(r, 3, QTableWidgetItem(f"{d['peso_total']:.3f}"))
                self.tabla_elem.setItem(r, 4, QTableWidgetItem(f"{d['porcentaje']:.2f} %"))

            self._convertir_peso_en_vivo()
            self._calcular_solucion_en_vivo()

            if hasattr(self, "canvas_mol"):
                self.canvas_mol.cargar_molecula(txt)

        except Exception:
            pass

    def _convertir_peso_en_vivo(self):
        try:
            val_str = self.txt_conv_val.text().strip()
            if not val_str: return
            val = float(val_str)
            unidad = self.combo_unidad.currentText()

            if "Gramos" in unidad:
                res = convertir_estequiometria(self.masa_molar_actual, gramos=val)
            elif "Kilogramos" in unidad:
                res = convertir_estequiometria(self.masa_molar_actual, gramos=val * 1000.0)
            elif "Miligramos" in unidad:
                res = convertir_estequiometria(self.masa_molar_actual, gramos=val / 1000.0)
            elif "Moles" in unidad:
                res = convertir_estequiometria(self.masa_molar_actual, moles=val)
            elif "Milimoles" in unidad:
                res = convertir_estequiometria(self.masa_molar_actual, moles=val / 1000.0)
            else: # Moléculas
                res = convertir_estequiometria(self.masa_molar_actual, moleculas=val)

            self.lbl_g_res.setText(f"{res['gramos']:.4g} g")
            self.lbl_mol_res.setText(f"{res['moles']:.4g} mol")
            self.lbl_molec_res.setText(f"{res['moleculas']:.3e} moléculas")
            self.lbl_mg_res.setText(f"{res['miligramos']:.4g} mg")
        except Exception:
            pass

    def _calcular_solucion_en_vivo(self):
        try:
            m_str = self.txt_sol_m.text().strip()
            v_str = self.txt_sol_v.text().strip()
            if not m_str or not v_str: return
            m = float(m_str)
            v = float(v_str)
            res = calcular_solucion_molar(self.masa_molar_actual, m, v)
            self.lbl_sol_resultado.setText(f"Masa de soluto necesaria: {res['gramos']} g ({res['miligramos']} mg) en {res['volumen_l']} L")
        except Exception:
            pass

    def _ir_a_visualizador(self):
        self.sub_tabs.setCurrentWidget(self.tab_visor)

    # =========================================================================
    # 2. PESTAÑA: VISUALIZADOR MOLECULAR 2D INTERACTIVO
    # =========================================================================
    def _crear_tab_visualizador(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Barra superior de controles del visor
        top_bar = QHBoxLayout()
        lbl_v_tit = QLabel("🔬 ESTRUCTURA MOLECULAR Y MODELO ATÓMICO")
        lbl_v_tit.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        lbl_v_tit.setStyleSheet(f"color: {self.colores['acento']};")
        top_bar.addWidget(lbl_v_tit)

        top_bar.addStretch()

        self.btn_anim = QPushButton("▶ Auto-Rotar")
        self.btn_anim.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_anim.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {self.colores['acento']}; }}
        """)
        self.btn_anim.clicked.connect(self._toggle_rotacion_canvas)
        top_bar.addWidget(self.btn_anim)

        btn_reset = QPushButton("🎯 Centrar Vista")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{ background: {self.colores['acento']}; }}
        """)
        btn_reset.clicked.connect(lambda: self.canvas_mol.reset_view())
        top_bar.addWidget(btn_reset)

        layout.addLayout(top_bar)

        # Canvas Molecular
        self.canvas_mol = MolecularCanvas(self)
        self.canvas_mol.cargar_molecula(self.formula_actual)
        layout.addWidget(self.canvas_mol, 1)

        # Leyenda y Guía
        lbl_guide = QLabel("💡 Arrastra con clic izquierdo para desplazar • Clic derecho para rotar • Rueda del ratón para Zoom")
        lbl_guide.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_guide.setStyleSheet("color: #8E8E93; font-size: 9pt;")
        layout.addWidget(lbl_guide)

        return widget

    def _toggle_rotacion_canvas(self):
        is_active = self.canvas_mol.toggle_auto_rotate()
        self.btn_anim.setText("⏸ Pausar" if is_active else "▶ Auto-Rotar")

    # =========================================================================
    # 3. PESTAÑA: TABLA PERIÓDICA INTERACTIVA DE LOS 118 ELEMENTOS
    # =========================================================================
    def _crear_tab_tabla_periodica(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 3.1 Barra de Búsqueda y Filtros
        filter_bar = QHBoxLayout()
        self.txt_busca_elem = QLineEdit()
        self.txt_busca_elem.setPlaceholderText("🔍 Buscar elemento por nombre, símbolo o número atómico...")
        self.txt_busca_elem.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_terciario']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 12px;
            }}
        """)
        self.txt_busca_elem.textChanged.connect(self._filtrar_elementos_tabla)
        filter_bar.addWidget(self.txt_busca_elem, 2)

        self.combo_filtro_cat = QComboBox()
        self.combo_filtro_cat.addItem("Todas las categorías", "todas")
        for k, v in CATEGORIAS.items():
            self.combo_filtro_cat.addItem(v["nombre"], k)
        self.combo_filtro_cat.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_terciario']};
                color: #FFFFFF;
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        self.combo_filtro_cat.currentIndexChanged.connect(self._filtrar_elementos_tabla)
        filter_bar.addWidget(self.combo_filtro_cat, 1)

        layout.addLayout(filter_bar)

        # 3.2 Cuadrícula de la Tabla Periódica
        scroll_tabla = QScrollArea()
        scroll_tabla.setWidgetResizable(True)
        scroll_tabla.setFrameShape(QFrame.Shape.NoFrame)
        scroll_tabla.setStyleSheet("background: transparent;")

        grid_container = QWidget()
        self.grid_tabla = QGridLayout(grid_container)
        self.grid_tabla.setSpacing(4)
        self.grid_tabla.setContentsMargins(5, 5, 5, 5)

        self.elem_buttons = {}
        self._construir_rejilla_tabla_periodica()

        scroll_tabla.setWidget(grid_container)
        layout.addWidget(scroll_tabla, 2)

        # 3.3 Tarjeta de Detalle del Elemento Seleccionado
        self.drawer_elem = QFrame()
        self.drawer_elem.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 12px;
                padding: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        d_layout = QHBoxLayout(self.drawer_elem)

        # Símbolo gigante
        self.lbl_d_simbolo = QLabel("H")
        self.lbl_d_simbolo.setFont(QFont("Inter", 26, QFont.Weight.Bold))
        self.lbl_d_simbolo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_d_simbolo.setFixedSize(70, 70)
        self.lbl_d_simbolo.setStyleSheet("background: rgba(255, 255, 255, 0.1); border-radius: 10px; color: #FFFFFF;")
        d_layout.addWidget(self.lbl_d_simbolo)

        # Datos detallados
        v_d_info = QVBoxLayout()
        self.lbl_d_nombre = QLabel("1 - Hidrógeno (Hydrogen)")
        self.lbl_d_nombre.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        self.lbl_d_nombre.setStyleSheet("color: #FFFFFF;")
        v_d_info.addWidget(self.lbl_d_nombre)

        self.lbl_d_detalles = QLabel("Masa: 1.008 u • Estado: Gas • Config: 1s¹ • Electroneg: 2.20 • Oxidación: +1, -1")
        self.lbl_d_detalles.setStyleSheet("color: #AAB0B8; font-size: 9.5pt;")
        v_d_info.addWidget(self.lbl_d_detalles)
        d_layout.addLayout(v_d_info, 1)

        btn_insertar = QPushButton("➕ Insertar en Fórmula")
        btn_insertar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_insertar.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: #FFFFFF;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_insertar.clicked.connect(self._insertar_elemento_en_formula)
        d_layout.addWidget(btn_insertar)

        layout.addWidget(self.drawer_elem)
        return widget

    def _construir_rejilla_tabla_periodica(self):
        """Ubica cada uno de los 118 elementos en su periodo y grupo exacto."""
        for z, data in ELEMENTOS.items():
            per = data["periodo"]
            grp = data["grupo"]
            cat = data["cat"]
            col_info = CATEGORIAS.get(cat, CATEGORIAS["desconocido"])

            # Ajuste de posición para Lantánidos (57-71) y Actínidos (89-103)
            r = per - 1
            c = grp - 1
            if 57 <= z <= 71:
                r = 7  # Fila inferior lantánidos
                c = (z - 57) + 2
            elif 89 <= z <= 103:
                r = 8  # Fila inferior actínidos
                c = (z - 89) + 2

            btn = QPushButton()
            btn.setFixedSize(48, 48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Contenido visual: Número Z + Símbolo
            btn.setText(f"{z}\n{data['simbolo']}")
            btn.setFont(QFont("Inter", 8, QFont.Weight.Bold))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {col_info['bg']};
                    color: #FFFFFF;
                    border: 1px solid {col_info['color']};
                    border-radius: 6px;
                    line-height: 1.1;
                }}
                QPushButton:hover {{
                    background: {col_info['color']};
                    color: #000000;
                    border: 2px solid #FFFFFF;
                }}
            """)
            btn.clicked.connect(lambda _, z_val=z: self._seleccionar_elemento(z_val))
            self.grid_tabla.addWidget(btn, r, c)
            self.elem_buttons[z] = (btn, data)

    def _seleccionar_elemento(self, z):
        data = ELEMENTOS.get(z)
        if not data: return
        self.elemento_seleccionado = data

        self.lbl_d_simbolo.setText(data["simbolo"])
        cat_info = CATEGORIAS.get(data["cat"], CATEGORIAS["desconocido"])
        self.lbl_d_simbolo.setStyleSheet(f"background: {cat_info['color']}; color: #000000; font-weight: bold; border-radius: 10px;")
        self.lbl_d_nombre.setText(f"{z} - {data['nombre']} ({cat_info['nombre']})")
        
        electroneg_str = f"{data['electroneg']}" if data['electroneg'] is not None else "N/A"
        self.lbl_d_detalles.setText(
            f"Masa: {data['masa']} u  •  Estado: {data['estado']}  •  Config: {data['config']}  •  Electroneg: {electroneg_str}  •  Oxidación: {data['ox']}"
        )

    def _insertar_elemento_en_formula(self):
        if hasattr(self, "elemento_seleccionado") and self.elemento_seleccionado:
            sim = self.elemento_seleccionado["simbolo"]
            self.txt_formula.setText(self.txt_formula.text() + sim)
            self.sub_tabs.setCurrentWidget(self.tab_masa)

    def _filtrar_elementos_tabla(self):
        query = self.txt_busca_elem.text().strip().lower()
        cat_filtro = self.combo_filtro_cat.currentData()

        for z, (btn, data) in self.elem_buttons.items():
            match_query = (
                not query or 
                query in data["nombre"].lower() or 
                query in data["simbolo"].lower() or 
                query == str(z)
            )
            match_cat = (cat_filtro == "todas" or data["cat"] == cat_filtro)

            if match_query and match_cat:
                btn.setVisible(True)
                btn.setEnabled(True)
            else:
                btn.setVisible(False)

    # =========================================================================
    # 4. PESTAÑA: BALANCEADOR DE REACCIONES & CALCULADORA DE GASES / pH
    # =========================================================================
    def _crear_tab_reacciones(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 4.1 Balanceador de Ecuaciones Químicas
        bal_card = QFrame()
        bal_card.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        bc_layout = QVBoxLayout(bal_card)
        bc_layout.setSpacing(12)

        lbl_b_tit = QLabel("⚖️ BALANCEADOR DE ECUACIONES QUÍMICAS (ESTEQUIOMETRÍA)")
        lbl_b_tit.setStyleSheet(f"color: {self.colores['acento']}; font-weight: bold; font-size: 10pt;")
        bc_layout.addWidget(lbl_b_tit)

        h_bal_in = QHBoxLayout()
        self.txt_reaccion = QLineEdit("CH4 + O2 -> CO2 + H2O")
        self.txt_reaccion.setFont(QFont("Inter", 11))
        self.txt_reaccion.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_principal']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 8px 12px;
            }}
        """)
        h_bal_in.addWidget(self.txt_reaccion, 3)

        btn_bal = QPushButton("Balancear ⚡")
        btn_bal.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_bal.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: #FFFFFF;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
            }}
        """)
        btn_bal.clicked.connect(self._ejecutar_balanceo)
        h_bal_in.addWidget(btn_bal, 1)

        bc_layout.addLayout(h_bal_in)

        self.lbl_bal_res = QLabel("Ecuación Balanceada: 1 CH4 + 2 O2 ➔ 1 CO2 + 2 H2O")
        self.lbl_bal_res.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        self.lbl_bal_res.setStyleSheet(f"color: {self.colores['exito']}; padding-top: 5px;")
        bc_layout.addWidget(self.lbl_bal_res)

        layout.addWidget(bal_card)

        # 4.2 Ley de los Gases Ideales (P * V = n * R * T)
        gas_card = QFrame()
        gas_card.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        gc_layout = QVBoxLayout(gas_card)
        gc_layout.setSpacing(10)

        lbl_g_tit = QLabel("🎈 LEY DE LOS GASES IDEALES (P · V = n · R · T)")
        lbl_g_tit.setStyleSheet(f"color: {self.colores['acento']}; font-weight: bold; font-size: 10pt;")
        gc_layout.addWidget(lbl_g_tit)

        grid_gas = QGridLayout()
        self.txt_p = QLineEdit("1.0")
        self.txt_v = QLineEdit("22.414")
        self.txt_n = QLineEdit("1.0")
        self.txt_t = QLineEdit("273.15")

        for txt in (self.txt_p, self.txt_v, self.txt_n, self.txt_t):
            txt.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 6px; padding: 6px;")

        grid_gas.addWidget(QLabel("Presión (P en atm):"), 0, 0)
        grid_gas.addWidget(self.txt_p, 0, 1)
        grid_gas.addWidget(QLabel("Volumen (V en L):"), 0, 2)
        grid_gas.addWidget(self.txt_v, 0, 3)

        grid_gas.addWidget(QLabel("Moles (n en mol):"), 1, 0)
        grid_gas.addWidget(self.txt_n, 1, 1)
        grid_gas.addWidget(QLabel("Temperatura (T en K):"), 1, 2)
        grid_gas.addWidget(self.txt_t, 1, 3)

        gc_layout.addLayout(grid_gas)

        h_gas_btns = QHBoxLayout()
        btn_calc_p = QPushButton("Calcular P")
        btn_calc_v = QPushButton("Calcular V")
        btn_calc_n = QPushButton("Calcular n")
        btn_calc_t = QPushButton("Calcular T")

        for b in (btn_calc_p, btn_calc_v, btn_calc_n, btn_calc_t):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 6px; padding: 6px;")
            h_gas_btns.addWidget(b)

        btn_calc_p.clicked.connect(self._calc_gas_p)
        btn_calc_v.clicked.connect(self._calc_gas_v)
        btn_calc_n.clicked.connect(self._calc_gas_n)
        btn_calc_t.clicked.connect(self._calc_gas_t)

        gc_layout.addLayout(h_gas_btns)
        layout.addWidget(gas_card)

        # 4.3 Calculadora de pH y pOH
        ph_card = QFrame()
        ph_card.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        pc_layout = QVBoxLayout(ph_card)
        pc_layout.setSpacing(10)

        lbl_ph_tit = QLabel("🧪 CALCULADORA DE pH / pOH Y CONCENTRACIÓN [H+]")
        lbl_ph_tit.setStyleSheet(f"color: {self.colores['acento']}; font-weight: bold; font-size: 10pt;")
        pc_layout.addWidget(lbl_ph_tit)

        h_ph = QHBoxLayout()
        h_ph.addWidget(QLabel("pH (0 - 14):"))
        self.txt_ph = QLineEdit("7.0")
        self.txt_ph.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 6px; padding: 6px;")
        self.txt_ph.textChanged.connect(self._calc_ph_en_vivo)
        h_ph.addWidget(self.txt_ph)

        self.lbl_ph_info = QLabel("pOH: 7.00 | [H+] = 1.00e-07 M | [OH-] = 1.00e-07 M | Neutro")
        self.lbl_ph_info.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        h_ph.addWidget(self.lbl_ph_info)

        pc_layout.addLayout(h_ph)
        layout.addWidget(ph_card)

        scroll.setWidget(container)
        main_v = QVBoxLayout(widget)
        main_v.setContentsMargins(0, 0, 0, 0)
        main_v.addWidget(scroll)
        return widget

    def _ejecutar_balanceo(self):
        try:
            eq = self.txt_reaccion.text().strip()
            res = balancear_ecuacion_quimica(eq)
            self.lbl_bal_res.setText(f"Ecuación Balanceada: {res['ecuacion_balanceada']}")
            if self.add_hist_callback:
                self.add_hist_callback(f"Balanceo: {eq}", res['ecuacion_balanceada'])
        except Exception as e:
            self.lbl_bal_res.setText(f"⚠️ Error al balancear: {e}")

    def _calc_gas_p(self):
        try:
            v = float(self.txt_v.text())
            n = float(self.txt_n.text())
            t = float(self.txt_t.text())
            p = (n * R_GAS * t) / v
            self.txt_p.setText(f"{p:.4f}")
        except Exception: pass

    def _calc_gas_v(self):
        try:
            p = float(self.txt_p.text())
            n = float(self.txt_n.text())
            t = float(self.txt_t.text())
            v = (n * R_GAS * t) / p
            self.txt_v.setText(f"{v:.4f}")
        except Exception: pass

    def _calc_gas_n(self):
        try:
            p = float(self.txt_p.text())
            v = float(self.txt_v.text())
            t = float(self.txt_t.text())
            n = (p * v) / (R_GAS * t)
            self.txt_n.setText(f"{n:.4f}")
        except Exception: pass

    def _calc_gas_t(self):
        try:
            p = float(self.txt_p.text())
            v = float(self.txt_v.text())
            n = float(self.txt_n.text())
            t = (p * v) / (n * R_GAS)
            self.txt_t.setText(f"{t:.2f}")
        except Exception: pass

    def _calc_ph_en_vivo(self):
        try:
            ph_str = self.txt_ph.text().strip()
            if not ph_str: return
            ph = float(ph_str)
            if 0 <= ph <= 14:
                poh = 14.0 - ph
                h_conc = 10 ** (-ph)
                oh_conc = 10 ** (-poh)
                tipo = "Ácido" if ph < 6.8 else ("Básico / Alcalino" if ph > 7.2 else "Neutro")
                self.lbl_ph_info.setText(f"pOH: {poh:.2f} | [H+] = {h_conc:.2e} M | [OH-] = {oh_conc:.2e} M | {tipo}")
        except Exception:
            pass

