"""
graficador.py - Submódulo de Graficación GeoGebra Pro Multi-Función con Analizador Sintáctico y Álgebra Matricial
"""
import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QLineEdit, QComboBox, QTabWidget, QGridLayout, QMessageBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QPainter, QPen, QColor, QPainterPath

from ..utils.geogebra_parser import GeoGebraParser

PALETA_COLORES_GRAFICO = ["#6366F1", "#34D399", "#FBBF24", "#F87171", "#C084FC", "#38BDF8", "#F472B6"]


class CanvasGraficador(QWidget):
    """Lienzo interactivo de dibujo con QPainter, Zoom adaptativo y Arrastre Pan"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(340)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        
        self.funciones = [] # [{"expr": "f(x) = 2x + 3", "color": "#6366F1", "activo": True}]
        
        # Transformación de Vista
        self.scale = 40.0 # Píxeles por unidad matemática
        self.offset_x = 0.0 # Desfasaje en X (px)
        self.offset_y = 0.0 # Desfasaje en Y (px)
        self.last_mouse_pos = None

    def set_funciones(self, lista):
        self.funciones = lista
        self.update()

    def reset_vista(self):
        self.scale = 40.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.update()

    def zoom_in(self):
        self.scale = min(500.0, self.scale * 1.25)
        self.update()

    def zoom_out(self):
        self.scale = max(5.0, self.scale / 1.25)
        self.update()

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        if angle > 0:
            self.scale = min(500.0, self.scale * 1.15)
        else:
            self.scale = max(5.0, self.scale / 1.15)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.last_mouse_pos and (event.buttons() & Qt.MouseButton.LeftButton):
            delta = event.pos() - self.last_mouse_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.last_mouse_pos = None

    def _calcular_paso_adaptativo(self):
        meta_px = 60.0
        raw_step = meta_px / self.scale
        potencia = 10 ** math.floor(math.log10(raw_step)) if raw_step > 0 else 1
        rel = raw_step / potencia
        
        if rel < 1.5: factor = 1
        elif rel < 3.5: factor = 2
        elif rel < 7.5: factor = 5
        else: factor = 10
        
        return factor * potencia

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        w = self.width()
        h = self.height()
        cx = (w / 2.0) + self.offset_x
        cy = (h / 2.0) + self.offset_y
        scale = self.scale

        # Fondo oscuro
        painter.fillRect(0, 0, w, h, QColor("#121218"))

        step = self._calcular_paso_adaptativo()

        min_x = (0 - cx) / scale
        max_x = (w - cx) / scale
        min_y = (cy - h) / scale
        max_y = (cy - 0) / scale

        # --- DIBUJAR REJILLA Y MARCAS NUMÉRICAS EN EJE X ---
        pen_grid = QPen(QColor(255, 255, 255, 18), 1, Qt.PenStyle.DashLine)
        pen_tick = QPen(QColor("#818CF8"), 2)
        font_num = QFont("Segoe UI", 8)
        
        painter.setFont(font_num)

        start_x_unit = math.floor(min_x / step) * step
        end_x_unit = math.ceil(max_x / step) * step

        curr_x_unit = start_x_unit
        while curr_x_unit <= end_x_unit:
            px = cx + (curr_x_unit * scale)
            if 0 <= px <= w:
                painter.setPen(pen_grid)
                painter.drawLine(int(px), 0, int(px), h)
                
                painter.setPen(pen_tick)
                painter.drawLine(int(px), int(cy) - 4, int(px), int(cy) + 4)

                if abs(curr_x_unit) > 1e-9:
                    val_str = f"{curr_x_unit:g}"
                    painter.setPen(QPen(QColor("#AAB0B8")))
                    label_y = min(h - 5, max(15, cy + 18))
                    painter.drawText(int(px) - 15, int(label_y), 30, 15, Qt.AlignmentFlag.AlignCenter, val_str)
            curr_x_unit += step

        # --- DIBUJAR REJILLA Y MARCAS NUMÉRICAS EN EJE Y ---
        start_y_unit = math.floor(min_y / step) * step
        end_y_unit = math.ceil(max_y / step) * step

        curr_y_unit = start_y_unit
        while curr_y_unit <= end_y_unit:
            py = cy - (curr_y_unit * scale)
            if 0 <= py <= h:
                painter.setPen(pen_grid)
                painter.drawLine(0, int(py), w, int(py))

                painter.setPen(pen_tick)
                painter.drawLine(int(cx) - 4, int(py), int(cx) + 4, int(py))

                if abs(curr_y_unit) > 1e-9:
                    val_str = f"{curr_y_unit:g}"
                    painter.setPen(QPen(QColor("#AAB0B8")))
                    label_x = min(w - 35, max(5, cx - 35))
                    painter.drawText(int(label_x), int(py) - 8, 30, 15, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, val_str)
            curr_y_unit += step

        # --- EJES PRINCIPALES X e Y ---
        pen_axis = QPen(QColor("#E2E8F0"), 2)
        painter.setPen(pen_axis)
        painter.drawLine(0, int(cy), w, int(cy))
        painter.drawLine(int(cx), 0, int(cx), h)

        # Origen (0,0)
        painter.setPen(QPen(QColor("#6366F1")))
        painter.drawText(int(cx) + 6, int(cy) + 16, "(0,0)")

        # --- DIBUJAR CURVAS DE FUNCIONES CON PARSER GEOGEBRA ---
        for func in self.funciones:
            if not func.get("activo", True):
                continue
            raw_expr = func.get("expr", "").strip()
            if not raw_expr:
                continue

            color_hex = func.get("color", "#6366F1")
            pen_curve = QPen(QColor(color_hex), 3)
            painter.setPen(pen_curve)

            path = QPainterPath()
            first = True

            curve_data = GeoGebraParser.parse_curve_input(raw_expr)
            if curve_data:
                # Curva Paramétrica estilo Curve(t, 2 sin(3t), t, -10, 10)
                t_min = curve_data["t_min"]
                t_max = curve_data["t_max"]
                num_steps = 600
                dt = (t_max - t_min) / num_steps
                for i in range(num_steps + 1):
                    t_val = t_min + (i * dt)
                    try:
                        x_val = GeoGebraParser.evaluar(curve_data["expr_x"], t_val, curve_data["var"])
                        y_val = GeoGebraParser.evaluar(curve_data["expr_y"], t_val, curve_data["var"])
                        px = cx + (x_val * scale)
                        py = cy - (y_val * scale)
                        if -500 <= px <= w + 500 and -500 <= py <= h + 500:
                            if first:
                                path.moveTo(px, py)
                                first = False
                            else:
                                path.lineTo(px, py)
                        else:
                            first = True
                    except Exception:
                        first = True
            else:
                # Función Cartesiana estándar y = f(x)
                nombre, body = GeoGebraParser.parse_function_input(raw_expr)
                for px in range(0, w, 2):
                    x_val = (px - cx) / scale
                    try:
                        y_val = GeoGebraParser.evaluar(body, x_val)
                        py = cy - (y_val * scale)
                        if -500 <= py <= h + 500:
                            if first:
                                path.moveTo(px, py)
                                first = False
                            else:
                                path.lineTo(px, py)
                        else:
                            first = True
                    except Exception:
                        first = True

            painter.drawPath(path)


class TabCalculadoraGraficador(QWidget):
    """Submódulo principal de Graficador GeoGebra Pro & Álgebra Matricial"""
    def __init__(self, parent=None, colores=None, add_hist_callback=None, context=None):
        super().__init__(parent)
        self.context = context
        self.colores = colores or (getattr(context, "colores", {}) if context else {})
        self.add_hist = add_hist_callback
        
        if isinstance(colores, dict): self.colores = colores
        elif isinstance(parent, dict): self.colores = parent
        
        self.posicion_panel = "izquierda"
        self.lista_funciones = [
            {"expr": "f(x) = 2x + 1", "color": PALETA_COLORES_GRAFICO[0], "activo": True},
            {"expr": "g(x) = x^2 - 4", "color": PALETA_COLORES_GRAFICO[1], "activo": True}
        ]

        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218') if isinstance(self.colores, dict) else '#121218'
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self.tabs = QTabWidget()
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E') if isinstance(self.colores, dict) else '#1E1E2E'
        acento = self.colores.get('acento', '#6366F1') if isinstance(self.colores, dict) else '#6366F1'
        
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background-color: {bg_p}; }}
            QTabBar::tab {{
                background: {bg_sec}; color: #AAB0B8; padding: 8px 16px; font-weight: bold;
                font-size: 11px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px;
            }}
            QTabBar::tab:selected {{ background: {acento}; color: white; }}
            QTabBar::tab:hover {{ color: white; }}
        """)

        # Pestaña 1: Graficador GeoGebra Pro
        tab_graf = self._crear_tab_graficador()
        self.tabs.addTab(tab_graf, "📈 Graficador GeoGebra Pro")

        # Pestaña 2: Matrices
        tab_mat = self._crear_tab_matrices()
        self.tabs.addTab(tab_mat, "📐 Calculadora de Matrices (2x2 & 3x3)")

        main_lay.addWidget(self.tabs)

    def _crear_tab_graficador(self):
        w = QWidget()
        self.lay_graf = QHBoxLayout(w)
        self.lay_graf.setContentsMargins(10, 10, 10, 10)
        self.lay_graf.setSpacing(10)

        # 1. Container Canvas y Toolbar Zoom
        canvas_box = QWidget()
        c_lay = QVBoxLayout(canvas_box)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(6)

        tb_zoom = QFrame()
        tb_zoom.setFixedHeight(36)
        tb_zoom.setStyleSheet("background: #1E1E2E; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);")
        tb_l = QHBoxLayout(tb_zoom)
        tb_l.setContentsMargins(10, 0, 10, 0)
        tb_l.setSpacing(8)

        lbl_h = QLabel("🔍 GeoGebra (Rueda Zoom / Clic Arrastre / Notación f(x) = mx + b)")
        lbl_h.setFont(QFont("Segoe UI", 9))
        lbl_h.setStyleSheet("color: #AAB0B8;")
        tb_l.addWidget(lbl_h, 1)

        btn_in = QPushButton("🔍+ Acercar")
        btn_in.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_in.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 4px; padding: 4px 8px; font-size: 10px; font-weight: bold;")
        btn_in.clicked.connect(lambda: self.canvas.zoom_in())
        tb_l.addWidget(btn_in)

        btn_out = QPushButton("🔍- Alejar")
        btn_out.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_out.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 4px; padding: 4px 8px; font-size: 10px; font-weight: bold;")
        btn_out.clicked.connect(lambda: self.canvas.zoom_out())
        tb_l.addWidget(btn_out)

        btn_rst = QPushButton("🏠 Reset")
        btn_rst.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rst.setStyleSheet("background: #6366F1; color: white; border-radius: 4px; padding: 4px 8px; font-size: 10px; font-weight: bold;")
        btn_rst.clicked.connect(lambda: self.canvas.reset_vista())
        tb_l.addWidget(btn_rst)

        c_lay.addWidget(tb_zoom)

        self.canvas = CanvasGraficador()
        self.canvas.set_funciones(self.lista_funciones)
        c_lay.addWidget(self.canvas, 1)

        # 2. Panel Lateral
        self.panel_lateral = QFrame()
        self.panel_lateral.setMinimumWidth(320)
        self.panel_lateral.setMaximumWidth(360)
        self.panel_lateral.setStyleSheet("background: #1E1E2E; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08);")
        
        p_lay = QVBoxLayout(self.panel_lateral)
        p_lay.setContentsMargins(12, 12, 12, 12)
        p_lay.setSpacing(10)

        hdr_lay = QHBoxLayout()
        lbl_p_t = QLabel("⚙️ FUNCIONES Y(X)")
        lbl_p_t.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_p_t.setStyleSheet("color: #818CF8;")
        hdr_lay.addWidget(lbl_p_t)
        hdr_lay.addStretch()

        self.btn_posicion = QPushButton("⬅️ Izquierda")
        self.btn_posicion.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_posicion.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 6px; padding: 4px 8px; font-size: 10px; font-weight: bold;")
        self.btn_posicion.clicked.connect(self._toggle_posicion_panel)
        hdr_lay.addWidget(self.btn_posicion)

        p_lay.addLayout(hdr_lay)

        # Sub-pestañas dentro del panel lateral (Edición vs Análisis & Tabla)
        self.sub_panel_tabs = QTabWidget()
        self.sub_panel_tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab { background: #2D2D3D; color: #AAB0B8; padding: 5px 10px; font-size: 10px; font-weight: bold; border-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #6366F1; color: white; }
        """)

        # Sub-pestaña Funciones
        w_funcs = QWidget()
        lay_f = QVBoxLayout(w_funcs)
        lay_f.setContentsMargins(0, 8, 0, 0)
        lay_f.setSpacing(8)

        btn_add = QPushButton("➕ Agregar Función")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet("background: #6366F1; color: white; border-radius: 6px; padding: 6px 12px; font-weight: bold; font-size: 11px;")
        btn_add.clicked.connect(self._agregar_nueva_funcion)
        lay_f.addWidget(btn_add)

        scroll_f = QScrollArea()
        scroll_f.setWidgetResizable(True)
        scroll_f.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.func_container_widget = QWidget()
        self.func_container_layout = QVBoxLayout(self.func_container_widget)
        self.func_container_layout.setContentsMargins(0, 0, 0, 0)
        self.func_container_layout.setSpacing(8)

        scroll_f.setWidget(self.func_container_widget)
        lay_f.addWidget(scroll_f, 1)

        self.sub_panel_tabs.addTab(w_funcs, "📝 Funciones")

        # Sub-pestaña Análisis & Tabla
        w_analisis = QWidget()
        lay_a = QVBoxLayout(w_analisis)
        lay_a.setContentsMargins(0, 8, 0, 0)
        lay_a.setSpacing(8)

        self.lbl_info_analisis = QLabel("Selecciona una función arriba")
        self.lbl_info_analisis.setFont(QFont("Segoe UI", 9))
        self.lbl_info_analisis.setStyleSheet("background: #2D2D3D; color: #34D399; padding: 8px; border-radius: 6px;")
        self.lbl_info_analisis.setWordWrap(True)
        lay_a.addWidget(self.lbl_info_analisis)

        self.tbl_valores = QTableWidget(0, 2)
        self.tbl_valores.setHorizontalHeaderLabels(["x", "f(x)"])
        self.tbl_valores.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_valores.setStyleSheet("""
            QTableWidget { background: #2D2D3D; color: white; border-radius: 6px; gridline-color: rgba(255,255,255,0.1); }
            QHeaderView::section { background: #1E1E2E; color: #818CF8; font-weight: bold; padding: 4px; }
        """)
        lay_a.addWidget(self.tbl_valores, 1)

        self.sub_panel_tabs.addTab(w_analisis, "📊 Análisis & Tabla")

        p_lay.addWidget(self.sub_panel_tabs, 1)

        self.lay_graf.addWidget(self.panel_lateral)
        self.lay_graf.addWidget(canvas_box, 1)

        self._refrescar_panel_funciones()
        return w

    def _toggle_posicion_panel(self):
        if self.posicion_panel == "izquierda":
            self.posicion_panel = "derecha"
            self.btn_posicion.setText("➡️ Derecha")
        else:
            self.posicion_panel = "izquierda"
            self.btn_posicion.setText("⬅️ Izquierda")

    def _agregar_nueva_funcion(self):
        c_idx = len(self.lista_funciones) % len(PALETA_COLORES_GRAFICO)
        self.lista_funciones.append({
            "expr": f"f_{len(self.lista_funciones)+1}(x) = 2x",
            "color": PALETA_COLORES_GRAFICO[c_idx],
            "activo": True
        })
        self._refrescar_panel_funciones()
        self.canvas.set_funciones(self.lista_funciones)

    def _eliminar_funcion(self, idx):
        if 0 <= idx < len(self.lista_funciones):
            self.lista_funciones.pop(idx)
            self._refrescar_panel_funciones()
            self.canvas.set_funciones(self.lista_funciones)

    def _refrescar_panel_funciones(self):
        while self.func_container_layout.count():
            item = self.func_container_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for idx, func in enumerate(self.lista_funciones):
            card = QFrame()
            card.setStyleSheet("background: #2D2D3D; border-radius: 8px; padding: 6px;")
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(6, 4, 6, 4)
            c_lay.setSpacing(6)

            chk = QCheckBox()
            chk.setChecked(func.get("activo", True))
            chk.toggled.connect(lambda checked, i=idx: self._toggle_activa_funcion(i, checked))
            c_lay.addWidget(chk)

            lbl_color = QLabel("  ")
            lbl_color.setFixedSize(14, 14)
            lbl_color.setStyleSheet(f"background-color: {func.get('color', '#6366F1')}; border-radius: 7px;")
            c_lay.addWidget(lbl_color)

            txt_expr = QLineEdit(func.get("expr", ""))
            txt_expr.setStyleSheet("background: #1E1E2E; color: white; border-radius: 4px; padding: 4px; font-weight: bold;")
            txt_expr.textChanged.connect(lambda text, i=idx: self._actualizar_expr_funcion(i, text))
            c_lay.addWidget(txt_expr, 1)

            btn_del = QPushButton("🗑️")
            btn_del.setFixedSize(22, 22)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background: transparent; border: none; font-size: 10px;")
            btn_del.clicked.connect(lambda ch, i=idx: self._eliminar_funcion(i))
            c_lay.addWidget(btn_del)

            self.func_container_layout.addWidget(card)

        self.func_container_layout.addStretch()
        self._actualizar_analisis_funcion_activa()

    def _toggle_activa_funcion(self, idx, checked):
        if 0 <= idx < len(self.lista_funciones):
            self.lista_funciones[idx]["activo"] = checked
            self.canvas.set_funciones(self.lista_funciones)

    def _actualizar_expr_funcion(self, idx, text):
        if 0 <= idx < len(self.lista_funciones):
            self.lista_funciones[idx]["expr"] = text
            self.canvas.set_funciones(self.lista_funciones)
            self._actualizar_analisis_funcion_activa()

    def _actualizar_analisis_funcion_activa(self):
        if not self.lista_funciones:
            self.lbl_info_analisis.setText("No hay funciones para analizar")
            self.tbl_valores.setRowCount(0)
            return

        func = self.lista_funciones[0]
        raw_expr = func.get("expr", "x")

        prop = GeoGebraParser.calcular_propiedades(raw_expr)
        raices_txt = ", ".join([str(r) for r in prop["raices"]]) if prop["raices"] else "Ninguna en [-20, 20]"

        self.lbl_info_analisis.setText(
            f"📌 <b>Función:</b> {prop['nombre']}(x)<br>"
            f"🔹 <b>Expresión:</b> {prop['expresion_limpia']}<br>"
            f"🎯 <b>Intersección Y f(0):</b> {prop['interseccion_y']}<br>"
            f"🌱 <b>Ceros / Raíces:</b> {raices_txt}"
        )

        puntos = GeoGebraParser.generar_tabla_valores(raw_expr, -5, 5, 1)
        self.tbl_valores.setRowCount(len(puntos))
        for row, (x_val, y_val) in enumerate(puntos):
            self.tbl_valores.setItem(row, 0, QTableWidgetItem(str(x_val)))
            self.tbl_valores.setItem(row, 1, QTableWidgetItem(str(y_val)))

    def _crear_tab_matrices(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(12)

        lbl_t = QLabel("📐 Operaciones con Matrices 2x2")
        lbl_t.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_t.setStyleSheet("color: #818CF8;")
        lay.addWidget(lbl_t)

        grid = QGridLayout()
        grid.setSpacing(8)

        self.m11 = QLineEdit("2"); self.m12 = QLineEdit("1")
        self.m21 = QLineEdit("4"); self.m22 = QLineEdit("3")

        for line_edit in [self.m11, self.m12, self.m21, self.m22]:
            line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            line_edit.setStyleSheet("background: #2D2D3D; color: white; font-weight: bold; padding: 8px; border-radius: 6px; font-size: 14px;")

        grid.addWidget(self.m11, 0, 0); grid.addWidget(self.m12, 0, 1)
        grid.addWidget(self.m21, 1, 0); grid.addWidget(self.m22, 1, 1)
        lay.addLayout(grid)

        row_ops = QHBoxLayout()
        btn_det = QPushButton("Determinante |A|")
        btn_det.setStyleSheet("background: #6366F1; color: white; font-weight: bold; padding: 8px; border-radius: 6px;")
        btn_det.clicked.connect(self._calc_determinante_2x2)

        btn_inv = QPushButton("Matriz Inversa A⁻¹")
        btn_inv.setStyleSheet("background: #818CF8; color: white; font-weight: bold; padding: 8px; border-radius: 6px;")
        btn_inv.clicked.connect(self._calc_inversa_2x2)

        btn_trans = QPushButton("Traspuesta Aᵀ")
        btn_trans.setStyleSheet("background: #34D399; color: white; font-weight: bold; padding: 8px; border-radius: 6px;")
        btn_trans.clicked.connect(self._calc_traspuesta_2x2)

        row_ops.addWidget(btn_det); row_ops.addWidget(btn_inv); row_ops.addWidget(btn_trans)
        lay.addLayout(row_ops)

        self.lbl_res_mat = QLabel("Resultado: Selecciona una operación arriba")
        self.lbl_res_mat.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_res_mat.setStyleSheet("background: #1E1E2E; color: white; padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);")
        self.lbl_res_mat.setWordWrap(True)
        lay.addWidget(self.lbl_res_mat)

        lay.addStretch()
        scroll.setWidget(content)

        w_lay = QVBoxLayout(w)
        w_lay.setContentsMargins(0, 0, 0, 0)
        w_lay.addWidget(scroll)
        return w

    def _calc_determinante_2x2(self):
        try:
            a = float(self.m11.text())
            b = float(self.m12.text())
            c = float(self.m21.text())
            d = float(self.m22.text())

            det = (a * d) - (b * c)
            self.lbl_res_mat.setText(f"Determinante |A| = ({a} × {d}) - ({b} × {c}) = {det:g}")
            if callable(self.add_hist):
                self.add_hist(f"Determinante [[{a},{b}],[{c},{d}]]", f"{det:g}")
        except ValueError:
            QMessageBox.warning(self, "Error", "Por favor ingresa números válidos en la matriz.")

    def _calc_traspuesta_2x2(self):
        try:
            a = float(self.m11.text())
            b = float(self.m12.text())
            c = float(self.m21.text())
            d = float(self.m22.text())

            self.lbl_res_mat.setText(f"Matriz Traspuesta Aᵀ:\n[ {a:g}   {c:g} ]\n[ {b:g}   {d:g} ]")
        except ValueError:
            QMessageBox.warning(self, "Error", "Por favor ingresa números válidos.")

    def _calc_inversa_2x2(self):
        try:
            a = float(self.m11.text())
            b = float(self.m12.text())
            c = float(self.m21.text())
            d = float(self.m22.text())

            det = (a * d) - (b * c)
            if det == 0:
                self.lbl_res_mat.setText("Matriz Inversa A⁻¹: No existe (Determinante es 0)")
                return

            inv_a = d / det
            inv_b = -b / det
            inv_c = -c / det
            inv_d = a / det

            self.lbl_res_mat.setText(f"Matriz Inversa A⁻¹ (Det = {det:g}):\n[ {inv_a:.2f}   {inv_b:.2f} ]\n[ {inv_c:.2f}   {inv_d:.2f} ]")
        except ValueError:
            QMessageBox.warning(self, "Error", "Por favor ingresa números válidos.")
