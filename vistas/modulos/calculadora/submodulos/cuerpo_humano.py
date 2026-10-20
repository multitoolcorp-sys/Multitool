"""
cuerpo_humano.py - Submódulo de Calculadora de Masa Corporal, Composición & Salud
Permite calcular:
- IMC (Índice de Masa Corporal) con clasificación OMS.
- Peso Ideal según fórmulas clínicas (Devine, Robinson, Miller, Hamwi).
- Porcentaje de Grasa Corporal (% Fat) y Masa Grasa en kg (Deurenberg).
- Masa Magra / Libre de Grasa (LBM - Ecuación de Boer).
- Agua Corporal Total (TBW - Fórmula de Watson).
- Tasa Metabólica Basal (TMB - Mifflin-St Jeor) y Gasto Diario Total (TDEE).
- Composición Química Elemental del Cuerpo (kg de O, C, H, N, Ca, P, K, S, Na, Cl, Mg).
- Recomendaciones personalizadas de Macronutrientes, Hidratación, Ejercicio y Salud.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QGridLayout, QScrollArea,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class TabCalculadoraCuerpoHumano(QWidget):
    """Submódulo independiente de Masa Corporal, Composición y Salud para Calculadora."""
    def __init__(self, parent=None, colores=None, add_hist_callback=None):
        super().__init__(parent)
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#FFFFFF", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#4F46E5", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }
        self.add_hist_callback = add_hist_callback
        self.inicializar_ui()

    def inicializar_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Tarjeta de Entrada de Parámetros Corporales
        in_frame = QFrame()
        in_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        if_layout = QVBoxLayout(in_frame)
        if_layout.setSpacing(12)

        lbl_tit = QLabel("🏃 PARÁMETROS BIOMÉTRICOS DEL CUERPO HUMANO")
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']}; font-weight: bold; font-size: 10pt; letter-spacing: 0.5px;")
        if_layout.addWidget(lbl_tit)

        grid_in = QGridLayout()
        grid_in.setSpacing(10)

        # Fila 0: Peso y Altura
        grid_in.addWidget(QLabel("Peso actual (kg):"), 0, 0)
        self.txt_corp_peso = QLineEdit("70.0")
        self.txt_corp_peso.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 6px; padding: 7px; font-weight: bold;")
        self.txt_corp_peso.textChanged.connect(self._calcular_en_vivo)
        grid_in.addWidget(self.txt_corp_peso, 0, 1)

        grid_in.addWidget(QLabel("Altura (cm):"), 0, 2)
        self.txt_corp_altura = QLineEdit("175.0")
        self.txt_corp_altura.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 6px; padding: 7px; font-weight: bold;")
        self.txt_corp_altura.textChanged.connect(self._calcular_en_vivo)
        grid_in.addWidget(self.txt_corp_altura, 0, 3)

        # Fila 1: Edad y Sexo
        grid_in.addWidget(QLabel("Edad (años):"), 1, 0)
        self.txt_corp_edad = QLineEdit("25")
        self.txt_corp_edad.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 6px; padding: 7px; font-weight: bold;")
        self.txt_corp_edad.textChanged.connect(self._calcular_en_vivo)
        grid_in.addWidget(self.txt_corp_edad, 1, 1)

        grid_in.addWidget(QLabel("Sexo Biológico:"), 1, 2)
        self.combo_corp_sexo = QComboBox()
        self.combo_corp_sexo.addItems(["Masculino (Hombre)", "Femenino (Mujer)"])
        self.combo_corp_sexo.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 6px; padding: 6px;")
        self.combo_corp_sexo.currentIndexChanged.connect(self._calcular_en_vivo)
        grid_in.addWidget(self.combo_corp_sexo, 1, 3)

        # Fila 2: Nivel de Actividad y Objetivo
        grid_in.addWidget(QLabel("Nivel de Actividad:"), 2, 0)
        self.combo_corp_actividad = QComboBox()
        self.combo_corp_actividad.addItems([
            "Sedentario (Poco o ningún ejercicio)",
            "Ligero (Ejercicio 1-3 días/semana)",
            "Moderado (Ejercicio 3-5 días/semana)",
            "Intenso (Ejercicio 6-7 días/semana)",
            "Muy Intenso / Atleta (Doble sesión)"
        ])
        self.combo_corp_actividad.setCurrentIndex(2)
        self.combo_corp_actividad.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 6px; padding: 6px;")
        self.combo_corp_actividad.currentIndexChanged.connect(self._calcular_en_vivo)
        grid_in.addWidget(self.combo_corp_actividad, 2, 1)

        grid_in.addWidget(QLabel("Objetivo Actual:"), 2, 2)
        self.combo_corp_objetivo = QComboBox()
        self.combo_corp_objetivo.addItems([
            "Mantenimiento Saludable",
            "Pérdida de Grasa / Definición (-500 kcal)",
            "Pérdida Acelerada (-750 kcal)",
            "Ganancia Muscular Limpia (+300 kcal)",
            "Volumen Máximo (+500 kcal)"
        ])
        self.combo_corp_objetivo.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 6px; padding: 6px;")
        self.combo_corp_objetivo.currentIndexChanged.connect(self._calcular_en_vivo)
        grid_in.addWidget(self.combo_corp_objetivo, 2, 3)

        if_layout.addLayout(grid_in)
        layout.addWidget(in_frame)

        # 2. Tarjeta Principal de Diagnóstico y Composición
        diag_frame = QFrame()
        diag_frame.setStyleSheet(f"""
            QFrame {{
                background: rgba(99, 102, 241, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        df_layout = QVBoxLayout(diag_frame)
        df_layout.setSpacing(10)

        h_diag_top = QHBoxLayout()
        v_diag_imc = QVBoxLayout()
        self.lbl_corp_imc_val = QLabel("22.86 kg/m²")
        self.lbl_corp_imc_val.setFont(QFont("Inter", 22, QFont.Weight.Bold))
        self.lbl_corp_imc_val.setStyleSheet(f"color: {self.colores['exito']};")
        v_diag_imc.addWidget(self.lbl_corp_imc_val)

        self.lbl_corp_imc_cat = QLabel("Estado: Peso Normal / Saludable (OMS)")
        self.lbl_corp_imc_cat.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.lbl_corp_imc_cat.setStyleSheet("color: #FFFFFF;")
        v_diag_imc.addWidget(self.lbl_corp_imc_cat)
        h_diag_top.addLayout(v_diag_imc)

        h_diag_top.addStretch()

        v_diag_ideal = QVBoxLayout()
        self.lbl_corp_ideal = QLabel("Peso Ideal Promedio: 68.2 kg")
        self.lbl_corp_ideal.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.lbl_corp_ideal.setStyleSheet(f"color: {self.colores['acento']};")
        v_diag_ideal.addWidget(self.lbl_corp_ideal)

        self.lbl_corp_rango = QLabel("Rango Saludable OMS: 56.7 kg - 76.3 kg")
        self.lbl_corp_rango.setStyleSheet("color: #AAB0B8; font-size: 9pt;")
        v_diag_ideal.addWidget(self.lbl_corp_rango)
        h_diag_top.addLayout(v_diag_ideal)

        df_layout.addLayout(h_diag_top)

        # Rejilla con métricas avanzadas (Grasa, Masa Magra, Agua, Calorías)
        grid_metrics = QGridLayout()
        grid_metrics.setSpacing(8)

        self.lbl_m_grasa = QLabel("16.8% (11.8 kg)")
        self.lbl_m_magra = QLabel("58.2 kg (83.2%)")
        self.lbl_m_agua = QLabel("42.5 L (60.7%)")
        self.lbl_m_tmb = QLabel("1,680 kcal/día")
        self.lbl_m_tdee = QLabel("2,520 kcal/día")
        self.lbl_m_obj_cal = QLabel("2,520 kcal/día")

        metrics_list = [
            ("Grasa Corporal Est.:", self.lbl_m_grasa),
            ("Masa Magra (LBM):", self.lbl_m_magra),
            ("Agua Corporal (TBW):", self.lbl_m_agua),
            ("Metabolismo Basal (TMB):", self.lbl_m_tmb),
            ("Gasto Diario (TDEE):", self.lbl_m_tdee),
            ("Meta Calórica Diaria:", self.lbl_m_obj_cal)
        ]

        for i, (t, l) in enumerate(metrics_list):
            r = i // 3
            c = (i % 3) * 2
            t_lbl = QLabel(t)
            t_lbl.setStyleSheet("color: #AAB0B8; font-weight: bold; font-size: 9pt;")
            l.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 10pt;")
            grid_metrics.addWidget(t_lbl, r, c)
            grid_metrics.addWidget(l, r, c + 1)

        df_layout.addLayout(grid_metrics)
        layout.addWidget(diag_frame)

        # 3. Composición Química Elemental del Cuerpo Humano
        elem_corp_frame = QFrame()
        elem_corp_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        ecf_layout = QVBoxLayout(elem_corp_frame)
        ecf_layout.setSpacing(10)

        lbl_ec_tit = QLabel("⚛️ COMPOSICIÓN QUÍMICA ELEMENTAL DE TU CUERPO")
        lbl_ec_tit.setStyleSheet(f"color: {self.colores['acento']}; font-weight: bold; font-size: 10pt;")
        ecf_layout.addWidget(lbl_ec_tit)

        self.tabla_elem_cuerpo = QTableWidget()
        self.tabla_elem_cuerpo.setColumnCount(4)
        self.tabla_elem_cuerpo.setHorizontalHeaderLabels(["Elemento", "% Masa Corporal", "Masa en tu Cuerpo (kg)", "Función Biológica Principal"])
        self.tabla_elem_cuerpo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_elem_cuerpo.setMinimumHeight(140)
        self.tabla_elem_cuerpo.setStyleSheet(f"""
            QTableWidget {{
                background: {self.colores['bg_principal']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }}
            QHeaderView::section {{
                background: {self.colores['bg_terciario']};
                color: {self.colores['acento']};
                font-weight: bold;
                padding: 5px;
                border: none;
            }}
        """)
        ecf_layout.addWidget(self.tabla_elem_cuerpo)
        layout.addWidget(elem_corp_frame)

        # 4. Guía y Recomendaciones Personalizadas de Nutrición, Ejercicio y Salud
        recom_frame = QFrame()
        recom_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        rf_layout = QVBoxLayout(recom_frame)
        rf_layout.setSpacing(12)

        lbl_r_tit = QLabel("📋 RECOMENDACIONES NUTRICIONALES, DE EJERCICIO Y SALUD")
        lbl_r_tit.setStyleSheet(f"color: {self.colores['acento']}; font-weight: bold; font-size: 10pt;")
        rf_layout.addWidget(lbl_r_tit)

        self.lbl_recom_macros = QLabel()
        self.lbl_recom_macros.setStyleSheet("color: #FFFFFF; font-size: 9.5pt; line-height: 1.4;")
        self.lbl_recom_macros.setWordWrap(True)
        rf_layout.addWidget(self.lbl_recom_macros)

        self.lbl_recom_salud = QLabel()
        self.lbl_recom_salud.setStyleSheet("color: #D1D5DB; font-size: 9pt; line-height: 1.4; padding-top: 4px;")
        self.lbl_recom_salud.setWordWrap(True)
        rf_layout.addWidget(self.lbl_recom_salud)

        layout.addWidget(recom_frame)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Cálculo inicial
        self._calcular_en_vivo()

    def _calcular_en_vivo(self):
        try:
            peso_str = self.txt_corp_peso.text().strip()
            alt_str = self.txt_corp_altura.text().strip()
            edad_str = self.txt_corp_edad.text().strip()
            if not peso_str or not alt_str or not edad_str: return

            peso = float(peso_str)
            altura_cm = float(alt_str)
            edad = float(edad_str)
            es_hombre = "Masculino" in self.combo_corp_sexo.currentText()
            altura_m = altura_cm / 100.0

            if peso <= 0 or altura_m <= 0 or edad <= 0: return

            # 1. IMC (BMI)
            imc = peso / (altura_m ** 2)
            if imc < 18.5:
                cat_imc = "Bajo Peso (Delgadez)"
                color_imc = self.colores["advertencia"]
            elif imc < 25.0:
                cat_imc = "Peso Normal / Saludable"
                color_imc = self.colores["exito"]
            elif imc < 30.0:
                cat_imc = "Sobrepeso (Pre-obesidad)"
                color_imc = self.colores["advertencia"]
            elif imc < 35.0:
                cat_imc = "Obesidad Grado I (Moderada)"
                color_imc = self.colores["error"]
            elif imc < 40.0:
                cat_imc = "Obesidad Grado II (Severa)"
                color_imc = self.colores["error"]
            else:
                cat_imc = "Obesidad Grado III (Mórbida)"
                color_imc = self.colores["error"]

            self.lbl_corp_imc_val.setText(f"{imc:.2f} kg/m²")
            self.lbl_corp_imc_val.setStyleSheet(f"color: {color_imc};")
            self.lbl_corp_imc_cat.setText(f"Estado: {cat_imc} (OMS)")

            # 2. Rangos de Peso Saludable y Peso Ideal Clínico
            min_peso_salud = 18.5 * (altura_m ** 2)
            max_peso_salud = 24.9 * (altura_m ** 2)
            self.lbl_corp_rango.setText(f"Rango Saludable OMS: {min_peso_salud:.1f} kg - {max_peso_salud:.1f} kg")

            pulgadas_sobre_5ft = max(0.0, (altura_cm / 2.54) - 60.0)
            if es_hombre:
                devine = 50.0 + 2.3 * pulgadas_sobre_5ft
                robinson = 52.0 + 1.9 * pulgadas_sobre_5ft
            else:
                devine = 45.5 + 2.3 * pulgadas_sobre_5ft
                robinson = 49.0 + 1.7 * pulgadas_sobre_5ft
            peso_ideal_prom = (devine + robinson) / 2.0
            self.lbl_corp_ideal.setText(f"Peso Ideal Promedio: {peso_ideal_prom:.1f} kg")

            # 3. % Grasa Corporal (Fórmula Deurenberg)
            sex_factor = 1 if es_hombre else 0
            porc_grasa = (1.20 * imc) + (0.23 * edad) - (10.8 * sex_factor) - 5.4
            porc_grasa = max(3.0, min(65.0, porc_grasa))
            kg_grasa = peso * (porc_grasa / 100.0)
            self.lbl_m_grasa.setText(f"{porc_grasa:.1f}% ({kg_grasa:.1f} kg)")

            # 4. Masa Magra (LBM - Ecuación de Boer)
            if es_hombre:
                lbm = (0.407 * peso) + (0.267 * altura_cm) - 19.2
            else:
                lbm = (0.252 * peso) + (0.473 * altura_cm) - 48.3
            lbm = max(10.0, min(peso, lbm))
            lbm_pct = (lbm / peso) * 100.0
            self.lbl_m_magra.setText(f"{lbm:.1f} kg ({lbm_pct:.1f}%)")

            # 5. Agua Corporal Total (TBW - Fórmula de Watson)
            if es_hombre:
                tbw = 2.447 - (0.09156 * edad) + (0.1074 * altura_cm) + (0.3362 * peso)
            else:
                tbw = -2.097 + (0.1069 * altura_cm) + (0.2466 * peso)
            tbw_pct = (tbw / peso) * 100.0
            self.lbl_m_agua.setText(f"{tbw:.1f} L ({tbw_pct:.1f}%)")

            # 6. Tasa Metabólica Basal (TMB - Mifflin-St Jeor) y TDEE
            if es_hombre:
                tmb = (10.0 * peso) + (6.25 * altura_cm) - (5.0 * edad) + 5.0
            else:
                tmb = (10.0 * peso) + (6.25 * altura_cm) - (5.0 * edad) - 161.0

            factores_act = [1.2, 1.375, 1.55, 1.725, 1.9]
            idx_act = self.combo_corp_actividad.currentIndex()
            factor_act = factores_act[idx_act] if 0 <= idx_act < len(factores_act) else 1.55
            tdee = tmb * factor_act

            # Ajuste según objetivo
            idx_obj = self.combo_corp_objetivo.currentIndex()
            ajustes = [0, -500, -750, +300, +500]
            ajuste = ajustes[idx_obj] if 0 <= idx_obj < len(ajustes) else 0
            cal_objetivo = max(1200.0, tdee + ajuste)

            self.lbl_m_tmb.setText(f"{int(tmb):,} kcal/día".replace(",", "."))
            self.lbl_m_tdee.setText(f"{int(tdee):,} kcal/día".replace(",", "."))
            self.lbl_m_obj_cal.setText(f"{int(cal_objetivo):,} kcal/día".replace(",", "."))

            # 7. Llenar Tabla de Elementos Químicos en el Cuerpo
            elementos_cuerpo = [
                ("Oxígeno (O)", 65.0, "Respiración celular, agua corporal y moléculas orgánicas."),
                ("Carbono (C)", 18.5, "Estructura base de proteínas, carbohidratos, lípidos y ADN."),
                ("Hidrógeno (H)", 9.5, "Presente en agua corporal, pH y enlaces moleculares."),
                ("Nitrógeno (N)", 3.2, "Componente de aminoácidos, proteínas y ácidos nucleicos."),
                ("Calcio (Ca)", 1.5, "Estructura ósea, dientes, contracción muscular y sinapsis."),
                ("Fósforo (P)", 1.0, "Huesos, membranas celulares (fosfolípidos) y energía (ATP)."),
                ("Potasio (K)", 0.4, "Principal catión intracelular y conducción nerviosa."),
                ("Azufre (S)", 0.3, "Aminoácidos esenciales (cisteína/metionina) y queratina."),
                ("Sodio (Na)", 0.2, "Balance hídrico, presión osmótica y potencial de acción."),
                ("Cloro (Cl)", 0.2, "Ácido clorhídrico estomacal y balance aniónico extracelular."),
                ("Magnesio (Mg)", 0.1, "Cofactor en más de 300 reacciones enzimáticas y síntesis de ATP.")
            ]

            self.tabla_elem_cuerpo.setRowCount(len(elementos_cuerpo))
            for r, (el_nom, pct, func) in enumerate(elementos_cuerpo):
                kg_elem = peso * (pct / 100.0)
                self.tabla_elem_cuerpo.setItem(r, 0, QTableWidgetItem(el_nom))
                self.tabla_elem_cuerpo.setItem(r, 1, QTableWidgetItem(f"{pct:.1f} %"))
                self.tabla_elem_cuerpo.setItem(r, 2, QTableWidgetItem(f"{kg_elem:.3f} kg ({kg_elem*1000:.0f} g)"))
                self.tabla_elem_cuerpo.setItem(r, 3, QTableWidgetItem(func))

            # 8. Recomendaciones Personalizadas de Nutrición y Salud
            factor_prot = 2.0 if idx_obj in (1, 3, 4) else 1.6
            gramos_prot = int(peso * factor_prot)
            kcal_prot = gramos_prot * 4

            gramos_grasas = int(peso * 0.9)
            kcal_grasas = gramos_grasas * 9

            kcal_carbos = max(0.0, cal_objetivo - (kcal_prot + kcal_grasas))
            gramos_carbos = int(kcal_carbos / 4)

            litros_agua = max(2.0, round((peso * 35.0) / 1000.0, 1))

            self.lbl_recom_macros.setText(
                f"🎯 <b>Distribución de Macronutrientes Sugerida ({int(cal_objetivo)} kcal):</b><br>"
                f"• <b>Proteínas:</b> {gramos_prot} g ({kcal_prot} kcal) — Para preservar y reparar tejido muscular.<br>"
                f"• <b>Carbohidratos:</b> {gramos_carbos} g ({int(kcal_carbos)} kcal) — Fuente de energía y glucógeno.<br>"
                f"• <b>Grasas Saludables:</b> {gramos_grasas} g ({kcal_grasas} kcal) — Regulación hormonal y absorción de vitaminas.<br>"
                f"• <b>Hidratación Diaria Recomendada:</b> {litros_agua} Litros de agua pura al día."
            )

            consejo_act = "150 a 300 min/semana de cardio moderado + 2-3 sesiones de fuerza (OMS)." if idx_act <= 1 else "Mantén tu excelente rutina combinando ejercicios multiarticulares con descanso adecuado."
            self.lbl_recom_salud.setText(
                f"💡 <b>Pautas de Salud y Rendimiento:</b><br>"
                f"• <b>Actividad Física:</b> {consejo_act}<br>"
                f"• <b>Sueño & Regeneración:</b> 7 a 9 horas de descanso nocturno para optimizar la síntesis proteica y el balance hormonal.<br>"
                f"• <b>Consejo Clínico:</b> Para tu altura de {altura_cm:.0f} cm, tu peso óptimo se sitúa entre {min_peso_salud:.1f} kg y {max_peso_salud:.1f} kg. {('¡Estás en un rango ideal!' if 18.5 <= imc <= 24.9 else 'Se aconseja un reajuste calórico progresivo.')}"
            )

        except Exception:
            pass
