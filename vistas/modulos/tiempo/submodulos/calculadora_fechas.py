import platform
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QDateEdit, QSpinBox, QComboBox, QTabWidget, 
    QRadioButton, QButtonGroup, QGridLayout, QApplication
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

class CalculadoraFechasSubmodule(QWidget):
    """Submódulo 7: Calculadora Integral de Fechas, Días Hábiles & Conversor de Tiempo"""
    def __init__(self, parent, context, manager, colores):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("🧮 CALCULADORA DE FECHAS, DÍAS HÁBILES Y TIEMPO")
        lbl_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()
        layout.addLayout(hdr)

        # Tabs internos: 1. Diferencia entre Fechas | 2. Sumar/Restar Fecha | 3. Conversor de Unidades
        self.subtabs = QTabWidget()
        self.subtabs.setFont(QFont(self.font_family, 9))
        self._estilizar_tabs()

        self.tab_dif = self._crear_tab_diferencia()
        self.tab_calc = self._crear_tab_sumar_restar()
        self.tab_conv = self._crear_tab_conversor()

        self.subtabs.addTab(self.tab_dif, "📏 Diferencia entre Fechas")
        self.subtabs.addTab(self.tab_calc, "➕➖ Sumar / Restar a Fecha")
        self.subtabs.addTab(self.tab_conv, "🔄 Conversor de Unidades")

        layout.addWidget(self.subtabs, 1)

    def _estilizar_tabs(self):
        self.subtabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid rgba(255, 255, 255, 0.05);
                background-color: {self.colores['bg_secundario']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background: {self.colores['bg_terciario']};
                color: #AAB0B8;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 10px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['acento']};
                color: white;
            }}
        """)

    # =========================================================================
    # TAB 1: DIFERENCIA ENTRE DOS FECHAS
    # =========================================================================
    def _crear_tab_diferencia(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(15)

        # Selectores de Fechas
        dates_row = QHBoxLayout()
        dates_row.setSpacing(15)

        # Fecha Inicio
        f1_box = QVBoxLayout()
        f1_box.setSpacing(4)
        lbl_f1 = QLabel("Fecha Inicial:")
        lbl_f1.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_f1.setStyleSheet("color: white;")
        f1_box.addWidget(lbl_f1)

        self.date_ini = QDateEdit(QDate.currentDate())
        self.date_ini.setCalendarPopup(True)
        self.date_ini.setFont(QFont(self.font_family, 10))
        self.date_ini.setStyleSheet(self._input_style())
        self.date_ini.dateChanged.connect(self._calcular_diferencia)
        f1_box.addWidget(self.date_ini)
        dates_row.addLayout(f1_box)

        # Fecha Fin
        f2_box = QVBoxLayout()
        f2_box.setSpacing(4)
        lbl_f2 = QLabel("Fecha Final:")
        lbl_f2.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_f2.setStyleSheet("color: white;")
        f2_box.addWidget(lbl_f2)

        self.date_fin = QDateEdit(QDate.currentDate().addDays(30))
        self.date_fin.setCalendarPopup(True)
        self.date_fin.setFont(QFont(self.font_family, 10))
        self.date_fin.setStyleSheet(self._input_style())
        self.date_fin.dateChanged.connect(self._calcular_diferencia)
        f2_box.addWidget(self.date_fin)
        dates_row.addLayout(f2_box)

        lay.addLayout(dates_row)

        # Resultados de la Diferencia
        res_grid = QGridLayout()
        res_grid.setSpacing(10)

        self.card_dias_totales = self._crear_res_card("📅 Días Totales", "0 días", self.colores['acento'])
        self.card_dias_habiles = self._crear_res_card("💼 Días Laborables (Hábiles)", "0 días", "#10B981")
        self.card_semanas = self._crear_res_card("🗓️ Semanas y Días", "0 sem, 0 d", "#F59E0B")
        self.card_meses = self._crear_res_card("📆 Meses Aproximados", "0 meses", "#8B5CF6")
        self.card_horas = self._crear_res_card("⏱️ Total en Horas", "0 horas", "#3B82F6")
        self.card_porcentaje = self._crear_res_card("📊 Fracción de Año", "0.0%", "#EC4899")

        res_grid.addWidget(self.card_dias_totales, 0, 0)
        res_grid.addWidget(self.card_dias_habiles, 0, 1)
        res_grid.addWidget(self.card_semanas, 1, 0)
        res_grid.addWidget(self.card_meses, 1, 1)
        res_grid.addWidget(self.card_horas, 2, 0)
        res_grid.addWidget(self.card_porcentaje, 2, 1)

        lay.addLayout(res_grid)
        lay.addStretch()

        self._calcular_diferencia()
        return widget

    def _calcular_diferencia(self):
        d1 = self.date_ini.date().toPyDate()
        d2 = self.date_fin.date().toPyDate()

        diff_days = abs((d2 - d1).days)
        start_d, end_d = min(d1, d2), max(d1, d2)

        # Días laborales (excluyendo sábados=5 y domingos=6)
        habiles = 0
        curr = start_d
        while curr < end_d:
            if curr.weekday() < 5:
                habiles += 1
            curr += datetime.timedelta(days=1)

        sems = diff_days // 7
        rem_days = diff_days % 7
        meses = diff_days / 30.4375
        horas = diff_days * 24
        frac_año = (diff_days / 365.25) * 100

        self._set_card_val(self.card_dias_totales, f"{diff_days:,} días")
        self._set_card_val(self.card_dias_habiles, f"{habiles:,} días hábiles")
        self._set_card_val(self.card_semanas, f"{sems} sem + {rem_days} d")
        self._set_card_val(self.card_meses, f"{meses:.1f} meses")
        self._set_card_val(self.card_horas, f"{horas:,} horas")
        self._set_card_val(self.card_porcentaje, f"{frac_año:.2f}% de 1 año")

    # =========================================================================
    # TAB 2: SUMAR O RESTAR TIEMPO A UNA FECHA
    # =========================================================================
    def _crear_tab_sumar_restar(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(15)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(12)

        # Fecha Base
        c1 = QVBoxLayout()
        lbl_b = QLabel("Fecha Base:")
        lbl_b.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_b.setStyleSheet("color: white;")
        c1.addWidget(lbl_b)
        self.date_calc_base = QDateEdit(QDate.currentDate())
        self.date_calc_base.setCalendarPopup(True)
        self.date_calc_base.setStyleSheet(self._input_style())
        self.date_calc_base.dateChanged.connect(self._calcular_sumar_restar)
        c1.addWidget(self.date_calc_base)
        ctrl_row.addLayout(c1)

        # Operación (+ o -)
        c2 = QVBoxLayout()
        lbl_op = QLabel("Operación:")
        lbl_op.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_op.setStyleSheet("color: white;")
        c2.addWidget(lbl_op)
        self.combo_op = QComboBox()
        self.combo_op.addItems(["➕ Sumar (+)", "➖ Restar (-)"])
        self.combo_op.setStyleSheet(self._input_style())
        self.combo_op.currentIndexChanged.connect(self._calcular_sumar_restar)
        c2.addWidget(self.combo_op)
        ctrl_row.addLayout(c2)

        # Cantidad
        c3 = QVBoxLayout()
        lbl_cant = QLabel("Cantidad:")
        lbl_cant.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_cant.setStyleSheet("color: white;")
        c3.addWidget(lbl_cant)
        self.spin_cant = QSpinBox()
        self.spin_cant.setRange(1, 10000)
        self.spin_cant.setValue(15)
        self.spin_cant.setStyleSheet(self._input_style())
        self.spin_cant.valueChanged.connect(self._calcular_sumar_restar)
        c3.addWidget(self.spin_cant)
        ctrl_row.addLayout(c3)

        # Unidad
        c4 = QVBoxLayout()
        lbl_u = QLabel("Unidad:")
        lbl_u.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_u.setStyleSheet("color: white;")
        c4.addWidget(lbl_u)
        self.combo_unidad = QComboBox()
        self.combo_unidad.addItems(["Días Calendario", "Días Hábiles (L-V)", "Semanas", "Meses", "Años"])
        self.combo_unidad.setStyleSheet(self._input_style())
        self.combo_unidad.currentIndexChanged.connect(self._calcular_sumar_restar)
        c4.addWidget(self.combo_unidad)
        ctrl_row.addLayout(c4)

        lay.addLayout(ctrl_row)

        # Tarjeta de Resultado Grande
        self.res_calc_card = QFrame()
        self.res_calc_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_terciario']};
                border: 2px solid {self.colores['acento']};
                border-radius: 12px;
            }}
        """)
        rc_lay = QVBoxLayout(self.res_calc_card)
        rc_lay.setContentsMargins(20, 20, 20, 20)
        rc_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_r_sub = QLabel("FECHA RESULTANTE")
        lbl_r_sub.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_r_sub.setStyleSheet("color: rgba(255,255,255,0.7);")
        lbl_r_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rc_lay.addWidget(lbl_r_sub)

        self.lbl_calc_res_grande = QLabel("--")
        self.lbl_calc_res_grande.setFont(QFont(self.font_family, 24, QFont.Weight.Bold))
        self.lbl_calc_res_grande.setStyleSheet("color: white;")
        self.lbl_calc_res_grande.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rc_lay.addWidget(self.lbl_calc_res_grande)

        self.lbl_calc_res_detalle = QLabel("--")
        self.lbl_calc_res_detalle.setFont(QFont(self.font_family, 10))
        self.lbl_calc_res_detalle.setStyleSheet(f"color: {self.colores['acento']};")
        self.lbl_calc_res_detalle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rc_lay.addWidget(self.lbl_calc_res_detalle)

        lay.addWidget(self.res_calc_card)
        lay.addStretch()

        self._calcular_sumar_restar()
        return widget

    def _calcular_sumar_restar(self):
        base_d = self.date_calc_base.date().toPyDate()
        es_suma = self.combo_op.currentIndex() == 0
        cant = self.spin_cant.value()
        unidad = self.combo_unidad.currentText()

        res_d = base_d

        if unidad == "Días Calendario":
            delta = datetime.timedelta(days=cant if es_suma else -cant)
            res_d = base_d + delta
        elif unidad == "Días Hábiles (L-V)":
            step = 1 if es_suma else -1
            added = 0
            curr = base_d
            while added < cant:
                curr += datetime.timedelta(days=step)
                if curr.weekday() < 5:
                    added += 1
            res_d = curr
        elif unidad == "Semanas":
            delta = datetime.timedelta(weeks=cant if es_suma else -cant)
            res_d = base_d + delta
        elif unidad == "Meses":
            # Cálculo de meses
            m = base_d.month + (cant if es_suma else -cant)
            y = base_d.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            import calendar
            max_d = calendar.monthrange(y, m)[1]
            res_d = datetime.date(y, m, min(base_d.day, max_d))
        elif unidad == "Años":
            y = base_d.year + (cant if es_suma else -cant)
            try:
                res_d = base_d.replace(year=y)
            except ValueError:
                res_d = base_d.replace(year=y, day=28)

        dias_esp = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses_esp = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        
        dia_nombre = dias_esp[res_d.weekday()]
        mes_nombre = meses_esp[res_d.month - 1]

        self.lbl_calc_res_grande.setText(f"{dia_nombre}, {res_d.day} de {mes_nombre} de {res_d.year}")
        dias_totales = abs((res_d - base_d).days)
        self.lbl_calc_res_detalle.setText(f"Diferencia: {dias_totales} días naturales desde la fecha base")

    # =========================================================================
    # TAB 3: CONVERSOR UNIVERSAL DE UNIDADES
    # =========================================================================
    def _crear_tab_conversor(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(15)

        # Entrada de valor y unidad
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        lbl_in = QLabel("Ingresa Cantidad:")
        lbl_in.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_in.setStyleSheet("color: white;")
        top_row.addWidget(lbl_in)

        self.spin_conv_val = QSpinBox()
        self.spin_conv_val.setRange(1, 10000000)
        self.spin_conv_val.setValue(1)
        self.spin_conv_val.setStyleSheet(self._input_style())
        self.spin_conv_val.valueChanged.connect(self._actualizar_conversor)
        top_row.addWidget(self.spin_conv_val)

        lbl_u_in = QLabel("Unidad:")
        lbl_u_in.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_u_in.setStyleSheet("color: white;")
        top_row.addWidget(lbl_u_in)

        self.combo_conv_unit = QComboBox()
        self.combo_conv_unit.addItems(["Días", "Horas", "Minutos", "Segundos", "Semanas", "Meses (30d)", "Años (365d)"])
        self.combo_conv_unit.setStyleSheet(self._input_style())
        self.combo_conv_unit.currentIndexChanged.connect(self._actualizar_conversor)
        top_row.addWidget(self.combo_conv_unit)
        top_row.addStretch()

        lay.addLayout(top_row)

        # Grid de Unidades Convertidas
        conv_grid = QGridLayout()
        conv_grid.setSpacing(8)

        self.conv_cards = {
            "seg": self._crear_res_card("⏱️ Segundos", "--", self.colores['acento']),
            "min": self._crear_res_card("⏳ Minutos", "--", "#10B981"),
            "hrs": self._crear_res_card("🕐 Horas", "--", "#3B82F6"),
            "dias": self._crear_res_card("📅 Días", "--", "#F59E0B"),
            "sem": self._crear_res_card("🗓️ Semanas", "--", "#8B5CF6"),
            "mes": self._crear_res_card("📆 Meses (30d)", "--", "#EC4899"),
            "año": self._crear_res_card("🌐 Años (365d)", "--", "#06B6D4"),
            "ms": self._crear_res_card("⚡ Milisegundos", "--", "#E2E2E2")
        }

        keys = list(self.conv_cards.keys())
        for i, k in enumerate(keys):
            row = i // 2
            col = i % 2
            conv_grid.addWidget(self.conv_cards[k], row, col)

        lay.addLayout(conv_grid)
        lay.addStretch()

        self._actualizar_conversor()
        return widget

    def _actualizar_conversor(self):
        val = self.spin_conv_val.value()
        unit = self.combo_conv_unit.currentText()

        # Convertir primero a segundos base
        factores_a_seg = {
            "Segundos": 1,
            "Minutos": 60,
            "Horas": 3600,
            "Días": 86400,
            "Semanas": 604800,
            "Meses (30d)": 2592000,
            "Años (365d)": 31536000
        }
        seg_base = val * factores_a_seg.get(unit, 86400)

        self._set_card_val(self.conv_cards["ms"], f"{int(seg_base * 1000):,} ms")
        self._set_card_val(self.conv_cards["seg"], f"{int(seg_base):,} s")
        self._set_card_val(self.conv_cards["min"], f"{seg_base / 60:,.2f} min")
        self._set_card_val(self.conv_cards["hrs"], f"{seg_base / 3600:,.2f} hrs")
        self._set_card_val(self.conv_cards["dias"], f"{seg_base / 86400:,.2f} días")
        self._set_card_val(self.conv_cards["sem"], f"{seg_base / 604800:,.2f} semanas")
        self._set_card_val(self.conv_cards["mes"], f"{seg_base / 2592000:,.2f} meses")
        self._set_card_val(self.conv_cards["año"], f"{seg_base / 31536000:,.4f} años")

    # =========================================================================
    # HELPERS
    # =========================================================================
    def _crear_res_card(self, titulo, valor, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-left: 3px solid {color};
                border-radius: 8px;
            }}
        """)
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(12, 8, 12, 8)
        c_lay.setSpacing(2)

        lbl_t = QLabel(titulo)
        lbl_t.setFont(QFont(self.font_family, 8))
        lbl_t.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        c_lay.addWidget(lbl_t)

        lbl_v = QLabel(valor)
        lbl_v.setObjectName("val")
        lbl_v.setFont(QFont(self.mono_font, 12, QFont.Weight.Bold))
        lbl_v.setStyleSheet(f"color: {color};")
        c_lay.addWidget(lbl_v)
        return card

    def _set_card_val(self, card, valor):
        lbl = card.findChild(QLabel, "val")
        if lbl: lbl.setText(valor)

    def _input_style(self):
        return f"""
            background-color: {self.colores['bg_terciario']};
            color: white; border: 1px solid rgba(255,255,255,0.1);
            border-radius: 4px; padding: 4px 8px;
        """

    def actualizar_tema(self, colores):
        self.colores = colores
        self._estilizar_tabs()
        self._calcular_diferencia()
        self._calcular_sumar_restar()
        self._actualizar_conversor()
