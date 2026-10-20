import datetime
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QMessageBox, QDateEdit, QCheckBox, QLineEdit, QScrollArea, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QIcon

from ..utils.fechas_logic import CalculadoraFechasLogic

class TabCalculadoraFechas(QWidget):
    """Módulo especializado en cálculos cronológicos y laborales"""
    def __init__(self, parent, colores, agregar_al_historial_callback):
        super().__init__(parent)
        self.colores = colores
        self.agregar_al_historial = agregar_al_historial_callback
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.campos = {}
        self.inicializar_ui()

    def inicializar_ui(self):
        self.layout_principal = QHBoxLayout(self)
        self.layout_principal.setContentsMargins(12, 12, 12, 12)
        self.layout_principal.setSpacing(12)
        
        # Panel izquierdo para configuraciones
        panel_izq = QWidget()
        layout_izq = QVBoxLayout(panel_izq)
        layout_izq.setContentsMargins(0, 0, 0, 0)
        layout_izq.setSpacing(15)
        
        # --- ENCABEZADO DE SELECCIÓN ---
        header_card = QFrame()
        header_card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        header_lay = QVBoxLayout(header_card)
        header_lay.setContentsMargins(12, 8, 12, 8)
        
        lbl_tipo = QLabel("OPERACIÓN CRONOLÓGICA")
        lbl_tipo.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_tipo.setStyleSheet(f"color: {self.colores['acento']}; ")
        header_lay.addWidget(lbl_tipo)
        
        self.tipos = ["Diferencia entre fechas", "Añadir/Restar días", "Días laborables", "Día de la semana"]
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(self.tipos)
        self.combo_tipo.setFont(QFont(self.font_family, 10))
        self.combo_tipo.setMinimumHeight(32)
        self.combo_tipo.setStyleSheet(self._get_combo_style())
        self.combo_tipo.currentTextChanged.connect(self.actualizar_campos)
        header_lay.addWidget(self.combo_tipo)
        
        layout_izq.addWidget(header_card)
        
        # --- ÁREA DE CONFIGURACIÓN ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.container_campos = QWidget()
        self.container_campos.setStyleSheet("background: transparent;")
        self.layout_campos = QVBoxLayout(self.container_campos)
        self.layout_campos.setContentsMargins(5, 5, 5, 5)
        self.layout_campos.setSpacing(15)
        
        self.scroll.setWidget(self.container_campos)
        layout_izq.addWidget(self.scroll, 1)
        
        # Anidar el panel izquierdo (Toma ~65% del ancho)
        self.layout_principal.addWidget(panel_izq, 65)
        
        # Panel derecho para Procesar y Resultados
        panel_der = QWidget()
        layout_der = QVBoxLayout(panel_der)
        layout_der.setContentsMargins(0, 0, 0, 0)
        layout_der.setSpacing(15)
        
        # --- ACCIÓN Y RESULTADO ---
        self.btn_calcular = QPushButton("⚡ PROCESAR CÁLCULO")
        self.btn_calcular.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calcular.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_calcular.setMinimumHeight(36)
        self.btn_calcular.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white; border-radius: 12px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        self.btn_calcular.clicked.connect(self.calcular)
        layout_der.addWidget(self.btn_calcular)
        
        self.res_card = QFrame()
        self.res_card.setMinimumHeight(80)
        self.res_card.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 12px; border: 1px solid {self.colores['exito']}44;")
        res_lay = QVBoxLayout(self.res_card)
        
        self.lbl_resultado = QLabel("El resultado se mostrará aquí")
        self.lbl_resultado.setTextFormat(Qt.TextFormat.MarkdownText)
        self.lbl_resultado.setFont(QFont(self.font_family, 11, QFont.Weight.Medium))
        self.lbl_resultado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_resultado.setWordWrap(True)
        self.lbl_resultado.setStyleSheet(f"color: {self.colores['exito']}; border: none;")
        res_lay.addWidget(self.lbl_resultado)
        
        layout_der.addWidget(self.res_card)
        layout_der.addStretch()
        
        # Anidar panel derecho (Toma ~35% del ancho)
        self.layout_principal.addWidget(panel_der, 35)
        
        self.actualizar_campos(self.tipos[0])

    def _get_combo_style(self):
        return f"""
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: none; border-radius: 8px;
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
        
        if tipo == "Diferencia entre fechas":
            self.campos['f1'] = self._crear_fecha("INICIO")
            self.campos['f2'] = self._crear_fecha("FIN")
            self.campos['fmt'] = self._crear_selector("FORMATO", ["Días", "Semanas y días", "Meses y días", "Años, meses y días", "Todo detallado"])
            
        elif tipo == "Añadir/Restar días":
            self.campos['f_base'] = self._crear_fecha("FECHA BASE")
            self.campos['op'] = self._crear_selector("OPERACIÓN", ["Añadir", "Restar"])
            self.campos['dias'] = self._crear_entrada("CANTIDAD DÍAS")
            self.campos['solo_lab'] = self._crear_check("Omitir fines de semana (solo laborables)")
            
        elif tipo == "Días laborables":
            self.campos['f1'] = self._crear_fecha("FECHA INICIO")
            self.campos['f2'] = self._crear_fecha("FECHA FIN")
            self.campos['inc_sab'] = self._crear_check("Incluir Sábados")
            self.campos['inc_dom'] = self._crear_check("Incluir Domingos")
            
        elif tipo == "Día de la semana":
            self.campos['f'] = self._crear_fecha("SELECCIONAR DÍA")
            
        self.layout_campos.addStretch()

    def _crear_fecha(self, label_text):
        container = QFrame()
        container.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 10px; border: 1px solid rgba(255,255,255,0.03);")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 6, 10, 6)
        
        lbl = QLabel(label_text)
        lbl.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl.setMinimumWidth(120)
        lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        layout.addWidget(lbl)
        
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDateTime(datetime.datetime.now())
        date_edit.setFont(QFont(self.mono_font, 11))
        date_edit.setMinimumHeight(32)
        date_edit.setStyleSheet(f"""
            QDateEdit {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: none; border-radius: 8px; padding-left: 10px;
            }}
            QDateEdit::drop-down {{ border: none; width: 25px; }}
            QCalendarWidget QWidget {{ background-color: {self.colores['bg_secundario']}; color: white; }}
        """)
        layout.addWidget(date_edit, 1)
        self.layout_campos.addWidget(container)
        return date_edit

    def _crear_selector(self, label_text, items):
        container = QFrame()
        container.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 10px; border: 1px solid rgba(255,255,255,0.03);")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 6, 10, 6)
        
        lbl = QLabel(label_text)
        lbl.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl.setMinimumWidth(120)
        lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        layout.addWidget(lbl)
        
        combo = QComboBox()
        combo.addItems(items)
        combo.setMinimumHeight(32)
        combo.setStyleSheet(self._get_combo_style())
        layout.addWidget(combo, 1)
        self.layout_campos.addWidget(container)
        return combo

    def _crear_entrada(self, label_text):
        container = QFrame()
        container.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 10px; border: 1px solid rgba(255,255,255,0.03);")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 6, 10, 6)
        
        lbl = QLabel(label_text)
        lbl.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl.setMinimumWidth(120)
        lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        layout.addWidget(lbl)
        
        txt = QLineEdit()
        txt.setPlaceholderText("0")
        txt.setMinimumHeight(32)
        txt.setFont(QFont(self.mono_font, 11))
        txt.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; border: none; border-radius: 8px; padding-left: 12px;")
        txt.returnPressed.connect(self.calcular)
        layout.addWidget(txt, 1)
        self.layout_campos.addWidget(container)
        return txt

    def _crear_check(self, label_text):
        check = QCheckBox(label_text)
        check.setFont(QFont(self.font_family, 10))
        check.setCursor(Qt.CursorShape.PointingHandCursor)
        check.setStyleSheet(f"""
            QCheckBox {{ color: {self.colores['fg_principal']}; padding: 8px; background: {self.colores['bg_secundario']}44; border-radius: 10px; }}
            QCheckBox::indicator {{ width: 22px; height: 22px; border-radius: 6px; border: 2px solid {self.colores['bg_terciario']}; }}
            QCheckBox::indicator:checked {{ background: {self.colores['acento']}; border: none; image: url(none); }}
        """)
        self.layout_campos.addWidget(check)
        return check

    def calcular(self):
        t = self.combo_tipo.currentText()
        try:
            if t == "Diferencia entre fechas":
                q1, q2 = self.campos['f1'].date(), self.campos['f2'].date()
                f1 = datetime.date(q1.year(), q1.month(), q1.day())
                f2 = datetime.date(q2.year(), q2.month(), q2.day())
                res, inv = CalculadoraFechasLogic.calcular_diferencia(f1, f2, self.campos['fmt'].currentText())
                if inv: res = "⚠️ (Fechas invertidas)\n" + res
                self.lbl_resultado.setText(res)
                self.agregar_al_historial(t, res.split('\n')[0])
                
            elif t == "Añadir/Restar días":
                qb = self.campos['f_base'].date()
                fb = datetime.date(qb.year(), qb.month(), qb.day())
                dias = int(self.campos['dias'].text() or 0)
                if self.campos['op'].currentText() == "Restar": dias = -dias
                res_date = CalculadoraFechasLogic.calcular_añadir_dias(fb, dias, self.campos['solo_lab'].isChecked())
                res_str = f"Nueva fecha: {res_date.strftime('%d/%m/%Y')}"
                self.lbl_resultado.setText(res_str)
                self.agregar_al_historial(t, res_str)
                
            elif t == "Días laborables":
                q1, q2 = self.campos['f1'].date(), self.campos['f2'].date()
                f1 = datetime.date(q1.year(), q1.month(), q1.day())
                f2 = datetime.date(q2.year(), q2.month(), q2.day())
                d_lab, d_tot = CalculadoraFechasLogic.calcular_dias_laborables(f1, f2, self.campos['inc_sab'].isChecked(), self.campos['inc_dom'].isChecked())
                res_str = f"Días útiles: {d_lab} de {d_tot} totales"
                self.lbl_resultado.setText(res_str)
                self.agregar_al_historial(t, res_str)
                
            elif t == "Día de la semana":
                q = self.campos['f'].date()
                f = datetime.date(q.year(), q.month(), q.day())
                nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                res_str = f"La fecha seleccionada cae en **{nombres[f.weekday()]}**"
                self.lbl_resultado.setText(res_str)
                self.agregar_al_historial(t, f"{f.strftime('%d/%m/%Y')} ➔ {nombres[f.weekday()]}")

        except ValueError:
            QMessageBox.warning(self, "Entrada Incorrecta", "Por favor ingresa un número válido de días.")
        except Exception as e:
            QMessageBox.critical(self, "Error Cronológico", f"No se pudo realizar el cálculo: {e}")

