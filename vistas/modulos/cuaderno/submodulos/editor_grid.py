import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QSplitter, QStackedWidget
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QFont, QKeySequence, QShortcut

from .components.sidebar_cuaderno import SidebarCuaderno
from .components.tabla_cuaderno import TablaCuaderno
from .components.toolbar_cuaderno import ToolbarCuaderno
from .components.chart_studio import ChartStudio
from .components.asistente_formulas import AsistenteFormulasDialog
from .components.formula_completer import FormulaCompleterPopup
from ..utils.formula_engine import index_to_col_name

class EditorGridSubmodule(QWidget):
    """Submódulo 1: Grid Excel, Barra de Fórmulas f(x), ChartStudio & Estadísticas de Selección"""
    def __init__(self, parent, context, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self._modo_seleccion_formula = False
        self._celda_objetivo_formula = (0, 0)
        self._formula_prefix = ""

        self.inicializar_ui()

    def inicializar_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar (Libros guardados)
        self.sidebar = SidebarCuaderno(self.colores, self.callbacks, self)
        main_layout.addWidget(self.sidebar)

        # 2. Área Central del Grid
        editor_frame = QFrame()
        editor_frame.setStyleSheet(f"background:{self.colores.get('bg_principal', '#121218')};")
        editor_lay = QVBoxLayout(editor_frame)
        editor_lay.setContentsMargins(15, 12, 15, 12)
        editor_lay.setSpacing(10)

        # ── Header & Campo de Nombre / Barra f(x) ──
        hdr_lay = QHBoxLayout()
        hdr_lay.setSpacing(10)

        lbl_nombre = QLabel("📘 Libro:")
        lbl_nombre.setStyleSheet(f"color:{self.colores.get('fg_secundario', '#AAB0B8')}; font-weight:bold; font-size:11px;")
        
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre del cuaderno...")
        self.txt_nombre.setFixedWidth(180)
        self.txt_nombre.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(45, 45, 61, 0.45);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colores.get('acento', '#6366F1')};
                background: rgba(45, 45, 61, 0.7);
            }}
        """)
        self.txt_nombre.textChanged.connect(self.callbacks.get("marcar_modificado", lambda: None))

        self.lbl_fx = QLabel("𝑓(𝑥):")
        self.lbl_fx.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.lbl_fx.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")

        self.btn_asistente_fx = QPushButton("𝑓(𝑥) Asistente")
        self.btn_asistente_fx.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_asistente_fx.setToolTip("Abrir Asistente de Fórmulas y Funciones Matemáticas estilo Excel")
        self.btn_asistente_fx.setStyleSheet(f"""
            QPushButton {{
                background: rgba(99, 102, 241, 0.16);
                color: {self.colores.get('acento', '#6366F1')};
                border: 1px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
            }}
        """)
        self.btn_asistente_fx.clicked.connect(self._abrir_asistente_formulas)

        self.txt_formula = QLineEdit()
        self.txt_formula.setPlaceholderText("Ingresa un valor o fórmula (ej: =SUMA(A1:A10), =PROMEDIO(B1:B5))...")
        self.txt_formula.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(30, 30, 46, 0.6);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 6px 12px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.txt_formula.returnPressed.connect(self._aplicar_formula_celda)
        self.txt_formula.textEdited.connect(self._on_formula_text_edited)
        self.txt_formula.installEventFilter(self)

        self.completer_popup = FormulaCompleterPopup(self.colores, self)
        self.completer_popup.funcion_seleccionada.connect(self._on_funcion_autocompletada)

        self.btn_toggle_chart = QPushButton("📊 Gráficos")
        self.btn_toggle_chart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_chart.setStyleSheet(f"""
            QPushButton {{
                background: rgba(99, 102, 241, 0.15);
                color: white;
                border: 1px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.btn_toggle_chart.clicked.connect(self._toggle_chart_studio)

        hdr_lay.addWidget(lbl_nombre)
        hdr_lay.addWidget(self.txt_nombre)
        hdr_lay.addWidget(self.lbl_fx)
        hdr_lay.addWidget(self.btn_asistente_fx)
        hdr_lay.addWidget(self.txt_formula, 1)
        hdr_lay.addWidget(self.btn_toggle_chart)

        editor_lay.addLayout(hdr_lay)

        # ── Tabla Grid & Toolbar ──
        self.tabla = TablaCuaderno(self.colores, self)
        self.tabla.installEventFilter(self)
        self.tabla.cambio_datos.connect(self.callbacks.get("marcar_modificado", lambda: None))
        self.tabla.itemSelectionChanged.connect(self._actualizar_estadisticas_seleccion)
        self.tabla.currentCellChanged.connect(self._on_current_cell_changed)

        self.toolbar = ToolbarCuaderno(self.colores, self.tabla, self)
        editor_lay.addWidget(self.toolbar)

        # QSplitter horizontal para Tabla y ChartStudio
        self.editor_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor_splitter.setStyleSheet("QSplitter::handle { background: rgba(255, 255, 255, 0.05); width: 4px; }")
        self.editor_splitter.addWidget(self.tabla)

        self.chart_studio = ChartStudio(self.tabla, self.colores)
        self.chart_studio.setVisible(False)
        self.editor_splitter.addWidget(self.chart_studio)

        editor_lay.addWidget(self.editor_splitter, 1)

        # ── Barra de Estado y Estadísticas Rápidas de Selección ──
        self.status_bar = QFrame()
        self.status_bar.setStyleSheet(f"""
            QFrame {{
                background: rgba(30, 30, 46, 0.5);
                border-radius: 8px;
                padding: 4px 10px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        st_lay = QHBoxLayout(self.status_bar)
        st_lay.setContentsMargins(8, 4, 8, 4)

        self.lbl_status = QLabel("Listo")
        self.lbl_status.setFont(QFont(self.font_family, 9))
        self.lbl_status.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        st_lay.addWidget(self.lbl_status)

        st_lay.addStretch()

        self.lbl_stats = QLabel("CONTEO: 0 | SUMA: 0 | PROMEDIO: 0")
        self.lbl_stats.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.lbl_stats.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        st_lay.addWidget(self.lbl_stats)

        editor_lay.addWidget(self.status_bar)

        # ── QStackedWidget: PÁGINA 0 (VISTA POR DEFECTO / ESPERA) Y PÁGINA 1 (EDITOR COMPLETO) ──
        self.stack_central = QStackedWidget()

        # ── PÁGINA 0: ESTADO VACÍO (Estilo Notas) ──
        self.widget_vacio = QWidget()
        self.widget_vacio.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')};")
        v_layout = QVBoxLayout(self.widget_vacio)
        v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.setContentsMargins(40, 40, 40, 40)
        v_layout.setSpacing(14)

        ico_empty = QLabel("📊")
        ico_empty.setFont(QFont("Segoe UI Emoji", 50))
        ico_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico_empty.setStyleSheet("background: transparent; color: rgba(255,255,255,0.2);")
        v_layout.addWidget(ico_empty)

        lbl_tit_empty = QLabel("Cuaderno de Cálculo MultiTool")
        lbl_tit_empty.setFont(QFont(self.font_family, 18, QFont.Weight.Bold))
        lbl_tit_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_tit_empty.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')};")
        v_layout.addWidget(lbl_tit_empty)

        lbl_sub_empty = QLabel("Selecciona un libro de la lista lateral o crea uno nuevo para comenzar a editar fórmulas, tablas y gráficos.")
        lbl_sub_empty.setFont(QFont(self.font_family, 11))
        lbl_sub_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub_empty.setWordWrap(True)
        lbl_sub_empty.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; max-width: 480px;")
        v_layout.addWidget(lbl_sub_empty)

        row_quick = QHBoxLayout()
        row_quick.setSpacing(12)
        row_quick.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_q_new = QPushButton("➕ Crear Nuevo Cuaderno")
        btn_q_new.setFixedHeight(36)
        btn_q_new.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_q_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_new.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')}; color: white; border-radius: 8px; padding: 0 20px; border: none; font-weight: bold;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        if "nuevo" in self.callbacks:
            btn_q_new.clicked.connect(self.callbacks["nuevo"])
        row_quick.addWidget(btn_q_new)

        btn_q_tpl = QPushButton("📋 Catálogo de Plantillas")
        btn_q_tpl.setFixedHeight(36)
        btn_q_tpl.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_q_tpl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_tpl.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.06); color: #FBBF24; border-radius: 8px; padding: 0 16px; border: 1px solid rgba(251,191,36,0.3); font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(251,191,36,0.15); }}
        """)
        if "ir_a_plantillas" in self.callbacks:
            btn_q_tpl.clicked.connect(self.callbacks["ir_a_plantillas"])
        row_quick.addWidget(btn_q_tpl)

        v_layout.addLayout(row_quick)

        lbl_esc_hint = QLabel("💡 Presiona la tecla Esc para deseleccionar y volver a esta pantalla de espera")
        lbl_esc_hint.setFont(QFont(self.font_family, 9))
        lbl_esc_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_esc_hint.setStyleSheet("color: rgba(255,255,255,0.35); margin-top: 15px;")
        v_layout.addWidget(lbl_esc_hint)

        self.stack_central.addWidget(self.widget_vacio)
        self.stack_central.addWidget(editor_frame)
        self.stack_central.setCurrentIndex(0)

        main_layout.addWidget(self.stack_central, 1)

        # Atajo global Esc para deseleccionar
        self.shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_esc.activated.connect(self._on_esc_pressed)

    def eventFilter(self, obj, event):
        if obj == self.txt_formula:
            if event.type() == QEvent.Type.FocusIn:
                if not self._modo_seleccion_formula:
                    r = self.tabla.currentRow()
                    c = self.tabla.currentColumn()
                    if r >= 0 and c >= 0:
                        self._celda_objetivo_formula = (r, c)
            elif event.type() == QEvent.Type.KeyPress:
                key = event.key()
                if hasattr(self, 'completer_popup') and self.completer_popup and self.completer_popup.isVisible():
                    if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                        self.completer_popup.navegar(1 if key == Qt.Key.Key_Down else -1)
                        return True
                    elif key in (Qt.Key.Key_Tab, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                        if self.completer_popup.seleccionar_actual():
                            return True
                    elif key == Qt.Key.Key_Escape:
                        self.completer_popup.hide()
                        return True
        elif obj == self.tabla:
            if event.type() == QEvent.Type.KeyPress and self._modo_seleccion_formula:
                key = event.key()
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._aplicar_formula_celda()
                    return True
                elif key == Qt.Key.Key_Escape:
                    self._modo_seleccion_formula = False
                    if hasattr(self, 'completer_popup') and self.completer_popup:
                        self.completer_popup.hide()
                    return True
        return super().eventFilter(obj, event)

    def mostrar_editor(self, habilitado=True):
        """Alterna entre la pantalla de espera (vacía) y el editor completo de hoja de cálculo."""
        if hasattr(self, 'stack_central'):
            self.stack_central.setCurrentIndex(1 if habilitado else 0)

    def _on_esc_pressed(self):
        """Manejador al presionar Esc: cancela fórmulas activas o vuelve a la pantalla de espera."""
        if hasattr(self, 'completer_popup') and self.completer_popup and self.completer_popup.isVisible():
            self.completer_popup.hide()
            return
        if self._modo_seleccion_formula:
            self._modo_seleccion_formula = False
            return
        if "deseleccionar" in self.callbacks and self.callbacks["deseleccionar"]:
            self.callbacks["deseleccionar"]()
        else:
            self.mostrar_editor(False)

    def _toggle_chart_studio(self):
        vis = not self.chart_studio.isVisible()
        self.chart_studio.setVisible(vis)
        if vis:
            self.editor_splitter.setSizes([600, 350])

    def _on_formula_text_edited(self, text: str):
        if not text.startswith("="):
            self._modo_seleccion_formula = False
            if hasattr(self, 'completer_popup') and self.completer_popup:
                self.completer_popup.hide()
            return

        r = self.tabla.currentRow()
        c = self.tabla.currentColumn()
        if r >= 0 and c >= 0 and not self._modo_seleccion_formula:
            self._celda_objetivo_formula = (r, c)

        # Comprobar si se está escribiendo nombre de función o argumentos de fórmula
        if any(text.endswith(op) for op in ['(', ',', ';', '+', '-', '*', '/']):
            self._modo_seleccion_formula = True
            self._formula_prefix = text
            if hasattr(self, 'completer_popup') and self.completer_popup:
                self.completer_popup.hide()
        elif '(' in text:
            # Dentro de argumentos: modo selección activo
            self._modo_seleccion_formula = True
            last_sep = max(text.rfind('('), text.rfind(','), text.rfind(';'), text.rfind('+'), text.rfind('-'), text.rfind('*'), text.rfind('/'))
            if last_sep != -1:
                self._formula_prefix = text[:last_sep + 1]
            if hasattr(self, 'completer_popup') and self.completer_popup:
                self.completer_popup.hide()
        elif text == "=":
            self._modo_seleccion_formula = False
            self._formula_prefix = "="
            if hasattr(self, 'completer_popup') and self.completer_popup:
                self.completer_popup.filtrar(text, self.txt_formula)
        else:
            # Usuario escribiendo nombre de función (ej: =S, =SUM, =PRO)
            self._modo_seleccion_formula = False
            if hasattr(self, 'completer_popup') and self.completer_popup:
                self.completer_popup.filtrar(text, self.txt_formula)

    def _on_funcion_autocompletada(self, fn_call: str):
        txt = self.txt_formula.text()
        if not txt.startswith("="):
            txt = "=" + txt

        last_sep_idx = -1
        for i, ch in enumerate(txt):
            if ch in ['=', '+', '-', '*', '/', '(', ',', ';']:
                last_sep_idx = i

        if last_sep_idx != -1:
            prefix = txt[:last_sep_idx + 1]
        else:
            prefix = "="

        nuevo_txt = prefix + fn_call
        self.txt_formula.blockSignals(True)
        self.txt_formula.setText(nuevo_txt)
        self.txt_formula.blockSignals(False)
        self.txt_formula.setFocus()

        r = self.tabla.currentRow()
        c = self.tabla.currentColumn()
        if r >= 0 and c >= 0 and self._celda_objetivo_formula == (0, 0):
            self._celda_objetivo_formula = (r, c)

        self._modo_seleccion_formula = True
        self._formula_prefix = nuevo_txt
        if hasattr(self, 'completer_popup') and self.completer_popup:
            self.completer_popup.hide()

    def _on_current_cell_changed(self, row, col, prev_row, prev_col):
        if row < 0 or col < 0:
            self.lbl_fx.setText("𝑓(𝑥):")
            return
        col_letter = index_to_col_name(col)
        coord = f"{col_letter}{row+1}"
        self.lbl_fx.setText(f"𝑓(𝑥) [{coord}]:")

        # Si estamos en modo selección interactiva para fórmula, NO sobreescribir txt_formula con el valor de la celda pulsada
        if self._modo_seleccion_formula:
            return

        formula_or_text = self.tabla.obtener_formula_celda(row, col)
        self.txt_formula.blockSignals(True)
        self.txt_formula.setText(formula_or_text)
        self.txt_formula.blockSignals(False)

    def _aplicar_formula_celda(self):
        txt = self.txt_formula.text().strip()
        if not txt:
            return

        # Balancear paréntesis no cerrados automáticamente (ej: =SUMA(A1:A5 -> =SUMA(A1:A5))
        if txt.startswith("="):
            n_open = txt.count("(")
            n_close = txt.count(")")
            if n_open > n_close:
                txt += ")" * (n_open - n_close)
                self.txt_formula.setText(txt)

        if self._modo_seleccion_formula:
            r, c = self._celda_objetivo_formula
        else:
            r = self.tabla.currentRow()
            c = self.tabla.currentColumn()

        if r < 0 or c < 0:
            r = max(0, self.tabla.currentRow())
            c = max(0, self.tabla.currentColumn())

        self.tabla.asignar_formula_celda(r, c, txt)
        self._modo_seleccion_formula = False
        if hasattr(self, 'completer_popup') and self.completer_popup:
            self.completer_popup.hide()
        self._actualizar_estadisticas_seleccion()
        self.tabla.setCurrentCell(r, c)

    def _abrir_asistente_formulas(self):
        r = max(0, self.tabla.currentRow())
        c = max(0, self.tabla.currentColumn())
        self._celda_objetivo_formula = (r, c)
        dlg = AsistenteFormulasDialog(
            self.colores,
            celda_activa_coords=(r, c),
            callback_insertar=self._insertar_formula_desde_asistente,
            parent=self
        )
        dlg.exec()

    def _insertar_formula_desde_asistente(self, formula_txt):
        r, c = self._celda_objetivo_formula
        self.txt_formula.blockSignals(True)
        self.txt_formula.setText(formula_txt)
        self.txt_formula.blockSignals(False)
        self.tabla.asignar_formula_celda(r, c, formula_txt)
        self._modo_seleccion_formula = False
        if hasattr(self, 'completer_popup') and self.completer_popup:
            self.completer_popup.hide()
        self._actualizar_estadisticas_seleccion()
        self.tabla.setCurrentCell(r, c)

    def _actualizar_estadisticas_seleccion(self):
        # Si estamos en modo de selección de fórmula, actualizar txt_formula con el rango seleccionado en el grid
        if self._modo_seleccion_formula:
            ranges = self.tabla.selectedRanges()
            if ranges:
                rng = ranges[0]
                c_left = index_to_col_name(rng.leftColumn())
                c_right = index_to_col_name(rng.rightColumn())
                r_top = rng.topRow() + 1
                r_bot = rng.bottomRow() + 1
                if rng.leftColumn() == rng.rightColumn() and rng.topRow() == rng.bottomRow():
                    ref = f"{c_left}{r_top}"
                else:
                    ref = f"{c_left}{r_top}:{c_right}{r_bot}"
                self.txt_formula.blockSignals(True)
                self.txt_formula.setText(f"{self._formula_prefix}{ref}")
                self.txt_formula.blockSignals(False)

        items = self.tabla.selectedItems()
        if not items:
            self.lbl_stats.setText("CONTEO: 0 | SUMA: 0 | PROMEDIO: 0")
            return

        valores = []
        for it in items:
            t = it.text().strip()
            if t:
                try:
                    val = float(t.replace('$', '').replace('%', '').replace(',', '.'))
                    valores.append(val)
                except ValueError:
                    pass

        conteo = len(items)
        if valores:
            suma = sum(valores)
            prom = suma / len(valores)
            v_max = max(valores)
            v_min = min(valores)
            self.lbl_stats.setText(f"CONTEO: {conteo} | SUMA: {suma:.2f} | PROMEDIO: {prom:.2f} | MÍN: {v_min:.2f} | MÁX: {v_max:.2f}")
        else:
            self.lbl_stats.setText(f"CONTEO: {conteo} | SUMA: -- | PROMEDIO: --")

    def actualizar_tema(self, colores):
        self.colores = colores
        if hasattr(self, 'tabla') and hasattr(self.tabla, 'actualizar_tema'):
            self.tabla.actualizar_tema(colores)
        if hasattr(self, 'toolbar') and hasattr(self.toolbar, 'actualizar_tema'):
            self.toolbar.actualizar_tema(colores)
        if hasattr(self, 'sidebar') and hasattr(self.sidebar, 'actualizar_tema'):
            self.sidebar.actualizar_tema(colores)
        if hasattr(self, 'chart_studio') and hasattr(self.chart_studio, 'actualizar_tema'):
            self.chart_studio.actualizar_tema(colores)
        self.lbl_fx.setStyleSheet(f"color: {colores.get('acento', '#6366F1')};")
        self.lbl_stats.setStyleSheet(f"color: {colores.get('acento', '#6366F1')};")
