import datetime
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGridLayout, QScrollArea, QLineEdit, QCheckBox, 
    QProgressBar, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

class MiniMonthCard(QFrame):
    """Tarjeta individual de mini-mes (1 de 12)"""
    month_selected = pyqtSignal(int, int) # (año, mes)

    def __init__(self, año, mes, mes_nombre, cant_eventos, colores, parent=None):
        super().__init__(parent)
        self.año = año
        self.mes = mes
        self.mes_nombre = mes_nombre
        self.colores = colores
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(110)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 1px solid {colores['acento']};
                background-color: {colores['bg_terciario']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Nombre de Mes
        lbl_mes = QLabel(mes_nombre.upper())
        lbl_mes.setFont(QFont("Segoe UI" if platform.system() == "Windows" else "Inter", 10, QFont.Weight.Bold))
        lbl_mes.setStyleSheet("color: white;")
        layout.addWidget(lbl_mes)

        # Indicador de eventos
        lbl_ev = QLabel(f"📅 {cant_eventos} evento(s)")
        lbl_ev.setFont(QFont("Segoe UI" if platform.system() == "Windows" else "Inter", 9))
        lbl_ev.setStyleSheet(f"color: {colores['acento'] if cant_eventos > 0 else colores['fg_secundario']};")
        layout.addWidget(lbl_ev)

        # Badge de intensidad
        intensity = "⚪ Tranquilo"
        if cant_eventos > 10:
            intensity = "🔴 Muy Concurrido"
        elif cant_eventos > 5:
            intensity = "🟡 Concurrido"
        elif cant_eventos > 0:
            intensity = "🟢 Activo"

        lbl_badge = QLabel(intensity)
        lbl_badge.setFont(QFont("Segoe UI" if platform.system() == "Windows" else "Inter", 8))
        lbl_badge.setStyleSheet("color: rgba(255,255,255,0.6);")
        layout.addWidget(lbl_badge)

    def mouseDoubleClickEvent(self, event):
        self.month_selected.emit(self.año, self.mes)
        super().mouseDoubleClickEvent(event)


class PlanificadorAnual(QWidget):
    """Submódulo 2: Planificador Anual de 12 Meses & Gestor de Objetivos del Año"""
    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.año_actual = datetime.datetime.now().year

        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Header de Navegación Anual
        hdr = QHBoxLayout()
        lbl_title = QLabel(f"🗓️ PLANIFICADOR ANUAL - {self.año_actual}")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        btn_prev = QPushButton("❮ Año Anterior")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; padding: 5px 12px; border-radius: 6px;")
        btn_prev.clicked.connect(self._prev_year)
        hdr.addWidget(btn_prev)

        btn_next = QPushButton("Año Siguiente ❯")
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; padding: 5px 12px; border-radius: 6px;")
        btn_next.clicked.connect(self._next_year)
        hdr.addWidget(btn_next)

        layout.addLayout(hdr)

        # Splitter Principal (Matriz de 12 Meses vs Objetivos del Año)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- SECCIÓN IZQUIERDA: MATRIZ DE 12 MESES (4x3) ---
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background: transparent;")
        grid_lay = QGridLayout(grid_frame)
        grid_lay.setContentsMargins(0, 0, 0, 0)
        grid_lay.setSpacing(10)

        self.month_cards = []
        for idx in range(12):
            mes_num = idx + 1
            row = idx // 4
            col = idx % 4
            m_name = self.manager.get_mes_nombre(mes_num)
            card = MiniMonthCard(self.año_actual, mes_num, m_name, 0, self.colores)
            card.month_selected.connect(self._on_month_double_clicked)
            grid_lay.addWidget(card, row, col)
            self.month_cards.append(card)

        splitter.addWidget(grid_frame)

        # --- SECCIÓN DERECHA: OBJETIVOS ANUALES ---
        goals_frame = QFrame()
        goals_frame.setFixedWidth(280)
        goals_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border-left: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }}
        """)
        goals_lay = QVBoxLayout(goals_frame)
        goals_lay.setContentsMargins(12, 12, 12, 12)
        goals_lay.setSpacing(8)

        lbl_g_title = QLabel("🎯 OBJETIVOS DEL AÑO")
        lbl_g_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_g_title.setStyleSheet(f"color: {self.colores['acento']};")
        goals_lay.addWidget(lbl_g_title)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.colores['bg_terciario']};
                border-radius: 6px; text-align: center; color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {self.colores['acento']};
                border-radius: 6px;
            }}
        """)
        goals_lay.addWidget(self.progress_bar)

        self.lbl_progress_txt = QLabel("0% Completado")
        self.lbl_progress_txt.setFont(QFont(self.font_family, 8))
        self.lbl_progress_txt.setStyleSheet("color: rgba(255,255,255,0.6);")
        self.lbl_progress_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        goals_lay.addWidget(self.lbl_progress_txt)

        # Input nuevo objetivo
        input_lay = QHBoxLayout()
        self.txt_goal = QLineEdit()
        self.txt_goal.setPlaceholderText("Añadir nuevo objetivo...")
        self.txt_goal.setFont(QFont(self.font_family, 9))
        self.txt_goal.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 4px 8px;
            }}
        """)
        self.txt_goal.returnPressed.connect(self._agregar_objetivo)
        input_lay.addWidget(self.txt_goal, 1)

        btn_add_g = QPushButton("➕")
        btn_add_g.setFixedSize(26, 26)
        btn_add_g.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_g.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; border-radius: 4px;")
        btn_add_g.clicked.connect(self._agregar_objetivo)
        input_lay.addWidget(btn_add_g)

        goals_lay.addLayout(input_lay)

        # Lista Scroll de objetivos
        scroll_goals = QScrollArea()
        scroll_goals.setWidgetResizable(True)
        scroll_goals.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container_goals = QWidget()
        self.container_goals.setStyleSheet("background: transparent;")
        self.layout_goals = QVBoxLayout(self.container_goals)
        self.layout_goals.setContentsMargins(0, 0, 0, 0)
        self.layout_goals.setSpacing(6)
        self.layout_goals.addStretch()

        scroll_goals.setWidget(self.container_goals)
        goals_lay.addWidget(scroll_goals)

        splitter.addWidget(goals_frame)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

        self.refrescar()

    def refrescar(self):
        # Actualizar recuentos de la matriz de 12 meses
        for idx, card in enumerate(self.month_cards):
            mes_num = idx + 1
            cant = 0
            for f_str, recs in self.manager.recordatorios.items():
                if f_str.startswith(f"{self.año_actual}-{mes_num:02d}"):
                    cant += len(recs)
            card.año = self.año_actual
            card.mes = mes_num
            card.findChild(QLabel).setText(self.manager.get_mes_nombre(mes_num).upper())
            # Actualizar label de eventos
            labels = card.findChildren(QLabel)
            if len(labels) >= 2:
                labels[1].setText(f"📅 {cant} evento(s)")
                labels[1].setStyleSheet(f"color: {self.colores['acento'] if cant > 0 else self.colores['fg_secundario']};")

        # Actualizar lista de Objetivos
        while self.layout_goals.count() > 1:
            item = self.layout_goals.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        objetivos = self.manager.get_objetivos(self.año_actual)
        completados = 0
        for obj in objetivos:
            if obj.get("completado"): completados += 1
            row = QFrame()
            row.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 4px; padding: 2px;")
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(6, 2, 6, 2)
            
            chk = QCheckBox(obj.get("titulo", ""))
            chk.setChecked(obj.get("completado", False))
            chk.setFont(QFont(self.font_family, 9))
            chk.setStyleSheet("QCheckBox { color: white; } QCheckBox::indicator { width: 14px; height: 14px; }")
            o_id = obj.get("id")
            chk.stateChanged.connect(lambda state, i=o_id: self._toggle_objetivo(i))
            r_lay.addWidget(chk, 1)

            btn_del = QPushButton("✖")
            btn_del.setFixedSize(18, 18)
            btn_del.setStyleSheet("QPushButton { background: transparent; color: #888; border: none; } QPushButton:hover { color: #EF4444; }")
            btn_del.clicked.connect(lambda ch, i=o_id: self._eliminar_objetivo(i))
            r_lay.addWidget(btn_del)

            self.layout_goals.insertWidget(self.layout_goals.count() - 1, row)

        pct = int((completados / len(objetivos) * 100)) if objetivos else 0
        self.progress_bar.setValue(pct)
        self.lbl_progress_txt.setText(f"{pct}% Completado ({completados}/{len(objetivos)})")

    def _agregar_objetivo(self):
        txt = self.txt_goal.text().strip()
        if txt:
            self.manager.añadir_objetivo(txt, año=self.año_actual)
            self.txt_goal.clear()
            self.refrescar()

    def _toggle_objetivo(self, obj_id):
        self.manager.toggle_objetivo(obj_id)
        self.refrescar()

    def _eliminar_objetivo(self, obj_id):
        self.manager.eliminar_objetivo(obj_id)
        self.refrescar()

    def _prev_year(self):
        self.año_actual -= 1
        self.findChild(QLabel).setText(f"🗓️ PLANIFICADOR ANUAL - {self.año_actual}")
        self.refrescar()

    def _next_year(self):
        self.año_actual += 1
        self.findChild(QLabel).setText(f"🗓️ PLANIFICADOR ANUAL - {self.año_actual}")
        self.refrescar()

    def _on_month_double_clicked(self, año, mes):
        if "ir_a_fecha" in self.callbacks:
            self.callbacks["ir_a_fecha"](año, mes)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.refrescar()
