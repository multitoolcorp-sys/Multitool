import re
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QMessageBox, QFrame, QScrollArea, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon

from ..utils.financiera_logic import CalculadoraFinancieraLogic

class TabCalculadoraFinanciera(QWidget):
    """Módulo de análisis financiero rediseñado con disposición lateral (Split Layout)"""
    def __init__(self, parent, colores, agregar_al_historial_callback):
        super().__init__(parent)
        self.colores = colores
        self.agregar_al_historial = agregar_al_historial_callback
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.campos = {}
        self.inicializar_ui()

    def inicializar_ui(self):
        self.layout_principal = QHBoxLayout(self) # Cambio a Horizontal
        self.layout_principal.setContentsMargins(12, 12, 12, 12)
        self.layout_principal.setSpacing(12)
        
        # --- COLUMNA IZQUIERDA: CONFIGURACIÓN ---
        col_izq = QVBoxLayout()
        col_izq.setSpacing(15)
        
        # 1. Selección de Métrica
        metric_card = QFrame()
        metric_card.setStyleSheet(f"background: rgba(30,30,46,0.5); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        metric_lay = QVBoxLayout(metric_card)
        metric_lay.setContentsMargins(12, 8, 12, 8)
        
        lbl_tipo = QLabel("SELECCIÓN DE ANÁLISIS")
        lbl_tipo.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_tipo.setStyleSheet(f"color: {self.colores['acento']};")
        metric_lay.addWidget(lbl_tipo)
        
        self.tipos = ["Interés Compuesto", "Amortización de Préstamo", "Valor Futuro", "Valor Presente", "Tasa Interna de Retorno (TIR)"]
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(self.tipos)
        self.combo_tipo.setFont(QFont(self.font_family, 10))
        self.combo_tipo.setMinimumHeight(32)
        self.combo_tipo.setStyleSheet(self._get_combo_style())
        self.combo_tipo.currentTextChanged.connect(self.actualizar_campos)
        metric_lay.addWidget(self.combo_tipo)
        col_izq.addWidget(metric_card)
        
        # 2. Área de Entradas (Scroll)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.container_campos = QWidget()
        self.container_campos.setStyleSheet("background: transparent;")
        self.layout_campos = QVBoxLayout(self.container_campos)
        self.layout_campos.setContentsMargins(0, 0, 5, 0)
        self.layout_campos.setSpacing(12)
        
        self.scroll.setWidget(self.container_campos)
        col_izq.addWidget(self.scroll, 1)
        
        self.layout_principal.addLayout(col_izq, 45) # 45% de ancho
        
        # --- COLUMNA DERECHA: RESULTADOS ---
        col_der = QVBoxLayout()
        col_der.setSpacing(20)
        
        # 4. Botón Ejecutar
        self.btn_calcular = QPushButton("CALCULAR AHORA")
        self.btn_calcular.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_calcular.setMinimumHeight(36)
        self.btn_calcular.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calcular.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white; border-radius: 12px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        self.btn_calcular.clicked.connect(self.calcular)
        col_der.addWidget(self.btn_calcular)
        
        # 5. Card de Resultado Premium
        self.res_card = QFrame()
        self.res_card.setStyleSheet(f"background: rgba(30, 30, 46, 0.9); border-radius: 16px; border: 1px solid {self.colores['acento']}44;")
        res_lay = QVBoxLayout(self.res_card)
        res_lay.setContentsMargins(12, 12, 12, 12)
        
        lbl_res_title = QLabel("RESULTADO DEL ANÁLISIS")
        lbl_res_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_res_title.setStyleSheet(f"color: white;")
        res_lay.addWidget(lbl_res_title)
        
        self.lbl_resultado = QLabel("Configura los campos de la izquierda para comenzar.")
        self.lbl_resultado.setFont(QFont(self.mono_font, 10))
        self.lbl_resultado.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.lbl_resultado.setWordWrap(True)
        self.lbl_resultado.setStyleSheet(f"color: {self.colores['fg_secundario']}; margin-top: 10px;")
        res_lay.addWidget(self.lbl_resultado, 1)
        
        col_der.addWidget(self.res_card, 1)
        
        self.layout_principal.addLayout(col_der, 55) # 55% de ancho
        
        self.actualizar_campos(self.tipos[0])

    def _get_combo_style(self):
        return f"""
            QComboBox {{
                background-color: rgba(45, 45, 61, 0.5);
                color: white; border: 1px solid rgba(255,255,255,0.05); border-radius: 8px;
                padding-left: 12px;
            }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid white; }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
                border: 1px solid rgba(255,255,255,0.1);
                outline: none; padding: 5px;
            }}
        """

    def actualizar_campos(self, tipo):
        while self.layout_campos.count():
            item = self.layout_campos.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        self.campos = {}
        self.lbl_resultado.setText("Configure los parámetros y pulse 'CALCULAR AHORA'.")
        
        if tipo == "Interés Compuesto":
            self.campos['cap'] = self._crear_entrada("CAPITAL INICIAL ($)")
            self.campos['tas'] = self._crear_entrada("TASA ANUAL (%)")
            self.campos['per'] = self._crear_entrada("PLAZO (AÑOS)")
            self.campos['fre'] = self._crear_selector("FRECUENCIA", ["Anual", "Semestral", "Trimestral", "Mensual", "Diaria"])
        elif tipo == "Amortización de Préstamo":
            self.campos['mon'] = self._crear_entrada("MONTO CRÉDITO ($)")
            self.campos['tas'] = self._crear_entrada("TASA ANUAL (%)")
            self.campos['pla'] = self._crear_entrada("PLAZO (AÑOS)")
            self.campos['pag'] = self._crear_selector("PAGO", ["Anual", "Semestral", "Trimestral", "Mensual"])
        elif tipo == "Valor Futuro":
            self.campos['pre'] = self._crear_entrada("VALOR ACTUAL ($)")
            self.campos['tas'] = self._crear_entrada("TASA ANUAL (%)")
            self.campos['per'] = self._crear_entrada("AÑOS")
            self.campos['apo'] = self._crear_entrada("APORTE REGULAR ($)")
            self.campos['fre'] = self._crear_selector("FRECUENCIA APORTE", ["Anual", "Semestral", "Trimestral", "Mensual"])
        elif tipo == "Valor Presente":
            self.campos['fut'] = self._crear_entrada("VALOR FUTURO ($)")
            self.campos['tas'] = self._crear_entrada("TASA DESCUENTO (%)")
            self.campos['per'] = self._crear_entrada("AÑOS")
        elif tipo == "Tasa Interna de Retorno (TIR)":
            self.campos['inv'] = self._crear_entrada("INVERSIÓN ($)")
            self.campos['flu'] = self._crear_entrada("FLUJOS (sep. comas)", placeholder="Ej: 500, 1200, 800")

        self.layout_campos.addStretch()

    def _crear_entrada(self, label_text, placeholder="0.00"):
        container = QFrame()
        container.setStyleSheet(f"background: rgba(30,30,46,0.4); border-radius: 12px; border: 1px solid rgba(255,255,255,0.03);")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 6, 10, 6)
        
        lbl = QLabel(label_text)
        lbl.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        layout.addWidget(lbl)
        
        txt = QLineEdit()
        txt.setPlaceholderText(placeholder)
        txt.setMinimumHeight(32)
        txt.setFont(QFont(self.mono_font, 10))
        txt.setStyleSheet(f"background-color: rgba(45, 45, 61, 0.6); color: white; border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding-left: 10px;")
        txt.returnPressed.connect(self.calcular)
        layout.addWidget(txt)
        self.layout_campos.addWidget(container)
        return txt

    def _crear_selector(self, label_text, items):
        container = QFrame()
        container.setStyleSheet(f"background: rgba(30,30,46,0.4); border-radius: 12px; border: 1px solid rgba(255,255,255,0.03);")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 6, 10, 6)
        
        lbl = QLabel(label_text)
        lbl.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        layout.addWidget(lbl)
        
        combo = QComboBox()
        combo.addItems(items)
        combo.setMinimumHeight(32)
        combo.setStyleSheet(self._get_combo_style())
        layout.addWidget(combo)
        self.layout_campos.addWidget(container)
        return combo



    def calcular(self):
        t = self.combo_tipo.currentText()
        try:
            res_full = ""
            if t == "Interés Compuesto":
                cap = float(self.campos['cap'].text())
                tas = float(self.campos['tas'].text())
                per = float(self.campos['per'].text())
                fre = self.campos['fre'].currentText()
                _, _, res_full = CalculadoraFinancieraLogic.calcular_interes_compuesto(cap, tas, per, fre)
            elif t == "Amortización de Préstamo":
                mon = float(self.campos['mon'].text())
                tas = float(self.campos['tas'].text())
                pla = float(self.campos['pla'].text())
                pag = self.campos['pag'].currentText()
                _, _, _, res_full = CalculadoraFinancieraLogic.calcular_amortizacion(mon, tas, pla, pag)
            elif t == "Valor Futuro":
                pre = float(self.campos['pre'].text())
                tas = float(self.campos['tas'].text())
                per = float(self.campos['per'].text())
                apo = float(self.campos['apo'].text() or 0)
                fre = self.campos['fre'].currentText()
                _, res_full = CalculadoraFinancieraLogic.calcular_valor_futuro(pre, tas, per, apo, fre)
            elif t == "Valor Presente":
                fut = float(self.campos['fut'].text())
                tas = float(self.campos['tas'].text())
                per = float(self.campos['per'].text())
                _, res_full = CalculadoraFinancieraLogic.calcular_valor_presente(fut, tas, per)
            elif t == "Tasa Interna de Retorno (TIR)":
                inv = float(self.campos['inv'].text())
                flujos_str = self.campos['flu'].text()
                flujos = [float(x.strip()) for x in flujos_str.split(',')]
                _, res_full = CalculadoraFinancieraLogic.calcular_tir(inv, flujos)
            
            self.lbl_resultado.setText(res_full)
            self.lbl_resultado.setStyleSheet("color: white; margin-top: 10px;")
            self.agregar_al_historial(t, res_full.split('\n')[0])
        except ValueError:
             QMessageBox.warning(self, "Entrada Inválida", "Ingresa valores numéricos correctos.")
        except Exception as e:
            QMessageBox.critical(self, "Error de Cálculo", str(e))
