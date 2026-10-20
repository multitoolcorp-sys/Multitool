"""
estadistica.py - Submódulo de Calculadora Estadística y Probabilidad para MultiTool
Incluye:
1. Estadística descriptiva completa (Media, Mediana, Moda, Varianza, Desviación Estándar, Cuartiles, IQR).
2. Regresión lineal simple bivariada (y = mx + b, Pearson r, R² y predictor de Y).
3. Distribución Normal Estándar y cálculo de valores Z.
"""
import math
from collections import Counter
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QFrame, QScrollArea, QGridLayout, QLineEdit,
    QTabWidget, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class TabCalculadoraEstadistica(QWidget):
    """Submódulo de análisis estadístico descriptivo y regresión para la suite Calculadora"""
    def __init__(self, parent=None, context=None, colores=None, **kwargs):
        super().__init__(parent if isinstance(parent, QWidget) else None)
        
        if isinstance(context, dict):
            self.colores = context
            self.context = colores
        elif isinstance(colores, dict):
            self.colores = colores
            self.context = context
        elif isinstance(parent, dict):
            self.colores = parent
            self.context = context
        else:
            self.context = context
            self.colores = colores if isinstance(colores, dict) else {}

        if not self.colores and self.context and hasattr(self.context, "app") and hasattr(self.context.app, "COLORES"):
            self.colores = self.context.app.COLORES

        if not isinstance(self.colores, dict):
            self.colores = {
                "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
                "fg_principal": "#FFFFFF", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
                "acento_hover": "#4F46E5", "exito": "#10B981", "advertencia": "#F59E0B"
            }

        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(12, 12, 12, 12)
        main_lay.setSpacing(10)

        # Tabs internos: 1. Descriptiva 1D, 2. Regresión 2D, 3. Distribución Normal
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {bg_p}; }}
            QTabBar::tab {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                padding: 8px 16px;
                border-radius: 6px;
                margin-right: 4px;
                font-weight: bold;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
        """)

        self.sub_tabs.addTab(self._crear_tab_descriptiva(), "📊 Estadística Descriptiva (1D)")
        self.sub_tabs.addTab(self._crear_tab_regresion(), "📈 Regresión Lineal (2D)")
        self.sub_tabs.addTab(self._crear_tab_distribucion(), "🔔 Distribución Normal (Z)")

        main_lay.addWidget(self.sub_tabs)

    # =========================================================================
    # 1. TAB ESTADÍSTICA DESCRIPTIVA (1D)
    # =========================================================================
    def _crear_tab_descriptiva(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(10)

        # Entrada de datos
        box_input = QFrame()
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        box_input.setStyleSheet(f"background-color: {bg_sec}; border-radius: 8px; padding: 10px; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};")
        in_lay = QVBoxLayout(box_input)
        in_lay.setSpacing(6)

        lbl_inst = QLabel("Introduce un conjunto de datos (números separados por comas, espacios o saltos de línea):")
        lbl_inst.setFont(QFont("Segoe UI", 10))
        lbl_inst.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')}; border: none;")
        in_lay.addWidget(lbl_inst)

        self.txt_datos_1d = QTextEdit()
        self.txt_datos_1d.setPlaceholderText("Ej: 12, 15, 14, 10, 18, 14, 15, 20, 22, 19, 14")
        self.txt_datos_1d.setFixedHeight(65)
        self.txt_datos_1d.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colores.get('bg_principal', '#121218')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 6px;
                font-family: Consolas, monospace;
            }}
        """)
        in_lay.addWidget(self.txt_datos_1d)

        # Botones de acción
        btn_row = QHBoxLayout()
        btn_calc = QPushButton("⚡ Calcular Métricas")
        btn_calc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_calc.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white; font-weight: bold; border-radius: 6px; padding: 7px 18px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores.get('acento_hover', '#4F46E5')}; }}
        """)
        btn_calc.clicked.connect(self.calcular_descriptiva)

        btn_ejemplo = QPushButton("🎲 Cargar Ejemplo")
        btn_ejemplo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ejemplo.setStyleSheet(f"background: transparent; color: {self.colores.get('acento', '#6366F1')}; border: 1px solid {self.colores.get('acento', '#6366F1')}; border-radius: 6px; padding: 6px 14px; font-weight: bold;")
        btn_ejemplo.clicked.connect(lambda: self.txt_datos_1d.setText("12, 15, 14, 10, 18, 14, 15, 20, 22, 19, 14, 25, 18, 16"))

        btn_limpiar = QPushButton("Limpiar")
        btn_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_limpiar.setStyleSheet("background: rgba(255,255,255,0.06); color: white; border-radius: 6px; padding: 6px 14px; border: none;")
        btn_limpiar.clicked.connect(lambda: (self.txt_datos_1d.clear(), self._limpiar_resultados_1d()))

        btn_copiar = QPushButton("📋 Copiar Resumen")
        btn_copiar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copiar.setStyleSheet("background: rgba(255,255,255,0.06); color: white; border-radius: 6px; padding: 6px 14px; border: none;")
        btn_copiar.clicked.connect(self._copiar_resumen_1d)

        btn_row.addWidget(btn_calc)
        btn_row.addWidget(btn_ejemplo)
        btn_row.addWidget(btn_limpiar)
        btn_row.addStretch()
        btn_row.addWidget(btn_copiar)
        in_lay.addLayout(btn_row)

        lay.addWidget(box_input)

        # Rejilla de tarjetas de resultados
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cont_res = QWidget()
        self.grid_1d = QGridLayout(cont_res)
        self.grid_1d.setSpacing(10)
        self.grid_1d.setContentsMargins(0, 4, 0, 4)

        self.cards_1d = {}
        metricas = [
            ("Muestra (N)", "n"),
            ("Media Aritmética (x̄)", "media"),
            ("Mediana (Me)", "mediana"),
            ("Moda (Mo)", "moda"),
            ("Desv. Estándar Muestral (s)", "desv_m"),
            ("Desv. Estándar Pob. (σ)", "desv_p"),
            ("Varianza Muestral (s²)", "var_m"),
            ("Varianza Poblacional (σ²)", "var_p"),
            ("Mínimo", "min"),
            ("Máximo", "max"),
            ("Rango Total", "rango"),
            ("Suma Total (∑x)", "suma"),
            ("Primer Cuartil (Q1)", "q1"),
            ("Tercer Cuartil (Q3)", "q3"),
            ("Rango Intercuartil (IQR)", "iqr")
        ]

        for idx, (label_txt, key) in enumerate(metricas):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_sec};
                    border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                    border-radius: 8px;
                    padding: 8px 12px;
                }}
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(4, 4, 4, 4)
            c_lay.setSpacing(2)

            lbl_t = QLabel(label_txt)
            lbl_t.setFont(QFont("Segoe UI", 9))
            lbl_t.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; border: none;")

            lbl_v = QLabel("-")
            lbl_v.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            lbl_v.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; border: none;")

            c_lay.addWidget(lbl_t)
            c_lay.addWidget(lbl_v)
            self.cards_1d[key] = lbl_v

            row, col = divmod(idx, 3)
            self.grid_1d.addWidget(card, row, col)

        scroll.setWidget(cont_res)
        lay.addWidget(scroll, 1)
        return widget

    def _parse_numeros(self, texto):
        t = texto.replace(";", ",").replace("\n", ",").replace(" ", ",")
        partes = [p.strip() for p in t.split(",") if p.strip()]
        numeros = []
        for p in partes:
            try:
                numeros.append(float(p))
            except ValueError:
                pass
        return sorted(numeros)

    def calcular_descriptiva(self):
        nums = self._parse_numeros(self.txt_datos_1d.toPlainText())
        if not nums:
            QMessageBox.warning(self, "Datos Insuficientes", "Por favor ingresa al menos 2 números válidos.")
            return

        n = len(nums)
        suma = sum(nums)
        media = suma / n

        # Mediana
        if n % 2 == 1:
            mediana = nums[n // 2]
        else:
            mediana = (nums[n // 2 - 1] + nums[n // 2]) / 2.0

        # Moda
        conteo = Counter(nums)
        max_freq = max(conteo.values())
        if max_freq > 1:
            modas = [k for k, v in conteo.items() if v == max_freq]
            str_moda = ", ".join(f"{m:g}" for m in modas[:4])
            if len(modas) > 4:
                str_moda += "..."
        else:
            str_moda = "No hay moda (Unimodal)"

        # Varianza y Desviación
        var_p = sum((x - media) ** 2 for x in nums) / n
        desv_p = math.sqrt(var_p)

        var_m = sum((x - media) ** 2 for x in nums) / (n - 1) if n > 1 else 0.0
        desv_m = math.sqrt(var_m)

        # Cuartiles
        def get_cuartil(data, q):
            k = (len(data) - 1) * q
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return data[int(k)]
            d0 = data[int(f)] * (c - k)
            d1 = data[int(c)] * (k - f)
            return d0 + d1

        q1 = get_cuartil(nums, 0.25)
        q3 = get_cuartil(nums, 0.75)
        iqr = q3 - q1

        # Actualizar display
        self.cards_1d["n"].setText(str(n))
        self.cards_1d["media"].setText(f"{media:.4g}")
        self.cards_1d["mediana"].setText(f"{mediana:.4g}")
        self.cards_1d["moda"].setText(str_moda)
        self.cards_1d["desv_m"].setText(f"{desv_m:.4g}")
        self.cards_1d["desv_p"].setText(f"{desv_p:.4g}")
        self.cards_1d["var_m"].setText(f"{var_m:.4g}")
        self.cards_1d["var_p"].setText(f"{var_p:.4g}")
        self.cards_1d["min"].setText(f"{nums[0]:g}")
        self.cards_1d["max"].setText(f"{nums[-1]:g}")
        self.cards_1d["rango"].setText(f"{nums[-1] - nums[0]:g}")
        self.cards_1d["suma"].setText(f"{suma:g}")
        self.cards_1d["q1"].setText(f"{q1:.4g}")
        self.cards_1d["q3"].setText(f"{q3:.4g}")
        self.cards_1d["iqr"].setText(f"{iqr:.4g}")

    def _limpiar_resultados_1d(self):
        for lbl in self.cards_1d.values():
            lbl.setText("-")

    def _copiar_resumen_1d(self):
        lineas = ["=== RESUMEN ESTADÍSTICO ==="]
        for k, lbl in self.cards_1d.items():
            lineas.append(f"{k.upper()}: {lbl.text()}")
        txt = "\n".join(lineas)
        QApplication.clipboard().setText(txt)
        QMessageBox.information(self, "Copiado", "Resumen estadístico copiado al portapapeles.")

    # =========================================================================
    # 2. TAB REGRESIÓN LINEAL (2D)
    # =========================================================================
    def _crear_tab_regresion(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(10)

        box_input = QFrame()
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        box_input.setStyleSheet(f"background-color: {bg_sec}; border-radius: 8px; padding: 12px; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};")
        in_lay = QVBoxLayout(box_input)

        lbl = QLabel("Ingresa pares de valores (X, Y) uno por línea o separados por comas (Ej: 1, 2.5):")
        lbl.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')}; font-size: 11px;")
        in_lay.addWidget(lbl)

        self.txt_regresion = QTextEdit()
        self.txt_regresion.setPlaceholderText("1, 2.1\n2, 3.8\n3, 6.2\n4, 8.0\n5, 10.2")
        self.txt_regresion.setFixedHeight(85)
        self.txt_regresion.setStyleSheet(f"background-color: {self.colores.get('bg_principal', '#121218')}; color: white; border-radius: 6px; padding: 6px; font-family: Consolas;")
        in_lay.addWidget(self.txt_regresion)

        row_btns = QHBoxLayout()
        btn_calc = QPushButton("⚡ Ajustar Recta de Regresión")
        btn_calc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_calc.setStyleSheet(f"background-color: {self.colores.get('acento', '#6366F1')}; color: white; font-weight: bold; border-radius: 6px; padding: 7px 16px; border: none;")
        btn_calc.clicked.connect(self.calcular_regresion)

        btn_ej = QPushButton("🎲 Cargar Ejemplo")
        btn_ej.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ej.setStyleSheet(f"background: transparent; color: {self.colores.get('acento', '#6366F1')}; border: 1px solid {self.colores.get('acento', '#6366F1')}; border-radius: 6px; padding: 6px 14px; font-weight: bold;")
        btn_ej.clicked.connect(lambda: self.txt_regresion.setText("1, 2.1\n2, 3.9\n3, 6.1\n4, 8.2\n5, 10.1\n6, 12.3"))

        row_btns.addWidget(btn_calc)
        row_btns.addWidget(btn_ej)
        row_btns.addStretch()
        in_lay.addLayout(row_btns)

        lay.addWidget(box_input)

        # Resultados de Regresión
        self.lbl_ec_recta = QLabel("Ecuación: y = mx + b")
        self.lbl_ec_recta.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_ec_recta.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; padding: 6px;")
        lay.addWidget(self.lbl_ec_recta)

        self.lbl_r_pearson = QLabel("Coeficiente de correlación de Pearson (r): - | R²: -")
        self.lbl_r_pearson.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')}; font-size: 11px;")
        lay.addWidget(self.lbl_r_pearson)

        # Predictor de Y dado X
        pred_box = QFrame()
        pred_box.setStyleSheet(f"background-color: {bg_sec}; border-radius: 8px; padding: 10px; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};")
        p_lay = QHBoxLayout(pred_box)
        p_lay.addWidget(QLabel("Predecir Y para X ="))
        self.txt_pred_x = QLineEdit()
        self.txt_pred_x.setPlaceholderText("Ej: 7.5")
        self.txt_pred_x.setFixedWidth(80)
        self.txt_pred_x.setStyleSheet(f"background-color: {self.colores.get('bg_principal', '#121218')}; color: white; border-radius: 4px; padding: 4px;")
        p_lay.addWidget(self.txt_pred_x)

        btn_pred = QPushButton("Calcular Ŷ")
        btn_pred.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pred.setStyleSheet(f"background-color: {self.colores.get('acento', '#6366F1')}; color: white; font-weight: bold; border-radius: 4px; padding: 6px 12px; border: none;")
        btn_pred.clicked.connect(self._predecir_y)
        p_lay.addWidget(btn_pred)

        self.lbl_res_pred = QLabel("Resultado: -")
        self.lbl_res_pred.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_res_pred.setStyleSheet(f"color: {self.colores.get('exito', '#10B981')}; margin-left: 10px;")
        p_lay.addWidget(self.lbl_res_pred)
        p_lay.addStretch()

        lay.addWidget(pred_box)
        lay.addStretch()
        return widget

    def calcular_regresion(self):
        lineas = self.txt_regresion.toPlainText().splitlines()
        puntos = []
        for l in lineas:
            partes = [p.strip() for p in l.replace(";", ",").split(",") if p.strip()]
            if len(partes) >= 2:
                try:
                    puntos.append((float(partes[0]), float(partes[1])))
                except ValueError:
                    pass

        if len(puntos) < 2:
            QMessageBox.warning(self, "Datos Insuficientes", "Se requieren al menos 2 pares (X, Y) para ajustar una recta.")
            return

        n = len(puntos)
        xs = [p[0] for p in puntos]
        ys = [p[1] for p in puntos]

        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xy = sum(x * y for x, y in puntos)
        sum_x2 = sum(x ** 2 for x in xs)
        sum_y2 = sum(y ** 2 for y in ys)

        denom = (n * sum_x2 - sum_x ** 2)
        if denom == 0:
            QMessageBox.warning(self, "Error", "No se puede calcular pendiente con todos los valores de X idénticos.")
            return

        m = (n * sum_xy - sum_x * sum_y) / denom
        b = (sum_y - m * sum_x) / n

        # Pearson r
        denom_r = math.sqrt((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2))
        r = (n * sum_xy - sum_x * sum_y) / denom_r if denom_r != 0 else 0.0
        r2 = r ** 2

        self.reg_m = m
        self.reg_b = b

        signo = "+" if b >= 0 else "-"
        self.lbl_ec_recta.setText(f"Ecuación: y = {m:.4f}x {signo} {abs(b):.4f}")
        self.lbl_r_pearson.setText(f"Pearson (r): {r:.4f}  |  Coeficiente de Determinación (R²): {r2:.4f} ({r2*100:.1f}% varianza explicada)")

    def _predecir_y(self):
        if not hasattr(self, "reg_m"):
            QMessageBox.information(self, "Aviso", "Primero calcula la recta de regresión.")
            return
        try:
            x_val = float(self.txt_pred_x.text())
            y_val = self.reg_m * x_val + self.reg_b
            self.lbl_res_pred.setText(f"Ŷ = {y_val:.4f}")
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingresa un número válido para X.")

    # =========================================================================
    # 3. TAB DISTRIBUCIÓN NORMAL (Z)
    # =========================================================================
    def _crear_tab_distribucion(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        card = QFrame()
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        card.setStyleSheet(f"background-color: {bg_sec}; border-radius: 8px; padding: 14px; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};")
        c_lay = QVBoxLayout(card)
        c_lay.setSpacing(10)

        lbl = QLabel("Cálculo de Probabilidad Acumulada P(Z ≤ z) para Distribución Normal N(μ, σ):")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')};")
        c_lay.addWidget(lbl)

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("Valor observado (x):"), 0, 0)
        self.txt_norm_x = QLineEdit("105")
        self.txt_norm_x.setStyleSheet(f"background-color: {self.colores.get('bg_principal', '#121218')}; color: white; border-radius: 4px; padding: 6px;")
        grid.addWidget(self.txt_norm_x, 0, 1)

        grid.addWidget(QLabel("Media poblacional (μ):"), 1, 0)
        self.txt_norm_mu = QLineEdit("100")
        self.txt_norm_mu.setStyleSheet(f"background-color: {self.colores.get('bg_principal', '#121218')}; color: white; border-radius: 4px; padding: 6px;")
        grid.addWidget(self.txt_norm_mu, 1, 1)

        grid.addWidget(QLabel("Desviación estándar (σ):"), 2, 0)
        self.txt_norm_sigma = QLineEdit("15")
        self.txt_norm_sigma.setStyleSheet(f"background-color: {self.colores.get('bg_principal', '#121218')}; color: white; border-radius: 4px; padding: 6px;")
        grid.addWidget(self.txt_norm_sigma, 2, 1)

        c_lay.addLayout(grid)

        btn_calc = QPushButton("⚡ Calcular Puntaje Z y Probabilidad")
        btn_calc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_calc.setStyleSheet(f"background-color: {self.colores.get('acento', '#6366F1')}; color: white; font-weight: bold; border-radius: 6px; padding: 8px 18px; border: none;")
        btn_calc.clicked.connect(self._calcular_normal)
        c_lay.addWidget(btn_calc)

        self.lbl_norm_res = QLabel("Puntaje Z = - | P(Z ≤ z) = -")
        self.lbl_norm_res.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_norm_res.setStyleSheet(f"color: {self.colores.get('exito', '#10B981')}; padding-top: 6px;")
        c_lay.addWidget(self.lbl_norm_res)

        lay.addWidget(card)
        lay.addStretch()
        return widget

    def _calcular_normal(self):
        try:
            x = float(self.txt_norm_x.text())
            mu = float(self.txt_norm_mu.text())
            sigma = float(self.txt_norm_sigma.text())

            if sigma <= 0:
                QMessageBox.warning(self, "Error", "La desviación estándar (σ) debe ser mayor a 0.")
                return

            z = (x - mu) / sigma
            # Función error de Gauss para CDF normal estándar
            cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
            cola_der = 1.0 - cdf

            self.lbl_norm_res.setText(
                f"Puntaje Z: {z:.4f}\n"
                f"P(X ≤ {x}) = {cdf * 100:.2f}% ({cdf:.4f})\n"
                f"P(X > {x}) = {cola_der * 100:.2f}% ({cola_der:.4f})"
            )
        except ValueError:
            QMessageBox.warning(self, "Error", "Por favor ingresa números válidos.")

    def actualizar_tema(self, colores):
        if isinstance(colores, dict):
            self.colores = colores
            bg_p = self.colores.get('bg_principal', '#121218')
            self.setStyleSheet(f"background-color: {bg_p}; color: white;")
