import platform
import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QFont

class WeekEventCard(QFrame):
    """Bloque de evento dentro de una casilla horaria de la vista semanal"""
    def __init__(self, evento, fecha, colores, on_click_cb, parent=None):
        super().__init__(parent)
        self.evento = evento
        self.fecha = fecha
        self.colores = colores
        self.on_click_cb = on_click_cb
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        cat_col = evento.get("categoria_color") or colores.get("acento", "#6366F1")
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {cat_col}22;
                border-left: 3px solid {cat_col};
                border-radius: 4px;
                padding: 2px 4px;
            }}
            QFrame:hover {{
                background-color: {cat_col}44;
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(1)

        hora_str = evento.get("hora", "00:00")
        lbl_h = QLabel(hora_str)
        lbl_h.setFont(QFont(self.font_family, 7, QFont.Weight.Bold))
        lbl_h.setStyleSheet(f"color: {cat_col};")
        lay.addWidget(lbl_h)

        tit = evento.get("titulo", "Evento")
        lbl_tit = QLabel(tit)
        lbl_tit.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_tit.setStyleSheet("color: white;")
        lbl_tit.setWordWrap(True)
        lay.addWidget(lbl_tit)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_click_cb(self.fecha, self.evento)
        super().mousePressEvent(event)


class VistaSemanalSubmodule(QWidget):
    """Submódulo de Vista Semanal con Bloques Horarios (07:00 a 22:00)"""
    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        # Fecha base para la semana actual
        self.fecha_actual = datetime.date.today()
        # Inicio de semana (Lunes = weekday 0)
        self.inicio_semana = self.fecha_actual - datetime.timedelta(days=self.fecha_actual.weekday())

        self.inicializar_ui()
        self.refrescar()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(10)

        # ── Barra de Navegación de la Semana ──
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(8)

        lbl_tit = QLabel("📆 AGENDA SEMANAL")
        lbl_tit.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_tit.setStyleSheet("color: white;")
        nav_bar.addWidget(lbl_tit)

        nav_bar.addSpacing(10)

        btn_prev = QPushButton("◀ Anterior")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_prev.setStyleSheet(self._btn_style())
        btn_prev.clicked.connect(self._semana_anterior)
        nav_bar.addWidget(btn_prev)

        btn_hoy = QPushButton("Hoy")
        btn_hoy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_hoy.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_hoy.setStyleSheet(self._btn_style(is_accent=True))
        btn_hoy.clicked.connect(self._ir_a_hoy)
        nav_bar.addWidget(btn_hoy)

        btn_next = QPushButton("Siguiente ▶")
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_next.setStyleSheet(self._btn_style())
        btn_next.clicked.connect(self._semana_siguiente)
        nav_bar.addWidget(btn_next)

        nav_bar.addStretch()

        self.lbl_rango_semana = QLabel()
        self.lbl_rango_semana.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_rango_semana.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        nav_bar.addWidget(self.lbl_rango_semana)

        layout.addLayout(nav_bar)

        # ── Área con Scroll para la Cuadrícula Horaria ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_lay = QGridLayout(self.grid_container)
        self.grid_lay.setContentsMargins(0, 0, 0, 0)
        self.grid_lay.setSpacing(2)

        scroll.setWidget(self.grid_container)
        layout.addWidget(scroll, 1)

    def _btn_style(self, is_accent=False):
        bg = self.colores['acento'] if is_accent else self.colores['bg_secundario']
        return f"""
            QPushButton {{
                background-color: {bg};
                color: white; border-radius: 4px; padding: 4px 12px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            QPushButton:hover {{ background-color: {self.colores.get('acento_hover', self.colores['acento'])}; }}
        """

    def _semana_anterior(self):
        self.inicio_semana -= datetime.timedelta(days=7)
        self.refrescar()

    def _semana_siguiente(self):
        self.inicio_semana += datetime.timedelta(days=7)
        self.refrescar()

    def _ir_a_hoy(self):
        hoy = datetime.date.today()
        self.inicio_semana = hoy - datetime.timedelta(days=hoy.weekday())
        self.refrescar()

    def refrescar(self):
        # Actualizar texto de rango
        fin_semana = self.inicio_semana + datetime.timedelta(days=6)
        meses_esp = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        m1 = meses_esp[self.inicio_semana.month - 1]
        m2 = meses_esp[fin_semana.month - 1]
        if m1 == m2:
            rango_txt = f"{self.inicio_semana.day} - {fin_semana.day} de {m1}, {fin_semana.year}"
        else:
            rango_txt = f"{self.inicio_semana.day} {m1} - {fin_semana.day} {m2}, {fin_semana.year}"
        self.lbl_rango_semana.setText(f"📅 {rango_txt}")

        # Limpiar grid
        while self.grid_lay.count() > 0:
            item = self.grid_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        hoy = datetime.date.today()
        dias_nombres = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]

        # ── Header de Columnas (Días) ──
        # Celda vacía para esquina superior izquierda
        corner = QLabel("")
        corner.setFixedWidth(55)
        self.grid_lay.addWidget(corner, 0, 0)

        for col_idx in range(7):
            d_date = self.inicio_semana + datetime.timedelta(days=col_idx)
            is_today = (d_date == hoy)

            header_frame = QFrame()
            header_frame.setFixedHeight(44)
            c_bg = f"{self.colores['acento']}33" if is_today else self.colores['bg_secundario']
            c_bdr = self.colores['acento'] if is_today else "rgba(255,255,255,0.06)"
            header_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {c_bg};
                    border: 1px solid {c_bdr};
                    border-radius: 6px;
                }}
            """)
            h_lay = QVBoxLayout(header_frame)
            h_lay.setContentsMargins(4, 4, 4, 4)
            h_lay.setSpacing(1)

            lbl_d_nom = QLabel(dias_nombres[col_idx])
            lbl_d_nom.setFont(QFont(self.font_family, 7, QFont.Weight.Bold))
            lbl_d_nom.setStyleSheet(f"color: {self.colores['acento'] if is_today else 'rgba(255,255,255,0.6)'};")
            lbl_d_nom.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h_lay.addWidget(lbl_d_nom)

            lbl_d_num = QLabel(str(d_date.day))
            lbl_d_num.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
            lbl_d_num.setStyleSheet("color: white;")
            lbl_d_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h_lay.addWidget(lbl_d_num)

            self.grid_lay.addWidget(header_frame, 0, col_idx + 1)

        # ── Filas Horarias (07:00 a 22:00) ──
        horas = list(range(7, 23))

        for row_idx, h_num in enumerate(horas, start=1):
            # Etiqueta de hora en columna 0
            lbl_hora = QLabel(f"{h_num:02d}:00")
            lbl_hora.setFont(QFont(self.mono_font, 8))
            lbl_hora.setStyleSheet("color: rgba(255,255,255,0.4);")
            lbl_hora.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            lbl_hora.setFixedWidth(50)
            self.grid_lay.addWidget(lbl_hora, row_idx, 0)

            # Casillas para cada día
            for col_idx in range(7):
                d_date = self.inicio_semana + datetime.timedelta(days=col_idx)
                f_str = d_date.strftime("%Y-%m-%d")

                slot = QFrame()
                slot.setMinimumHeight(42)
                slot.setStyleSheet(f"""
                    QFrame {{
                        background-color: rgba(255, 255, 255, 0.015);
                        border: 1px solid rgba(255, 255, 255, 0.03);
                        border-radius: 4px;
                    }}
                    QFrame:hover {{
                        background-color: rgba(255, 255, 255, 0.05);
                        border-color: rgba(255, 255, 255, 0.1);
                    }}
                """)
                slot_lay = QVBoxLayout(slot)
                slot_lay.setContentsMargins(2, 2, 2, 2)
                slot_lay.setSpacing(2)

                # Obtener eventos que coincidan en esta fecha y hora
                recs_dia = self.manager.get_recordatorios_por_fecha(f_str)
                eventos_hora = []
                for r in recs_dia:
                    h_r = int(r.get("hora", "00:00").split(":")[0])
                    if h_r == h_num:
                        eventos_hora.append(r)

                for ev in eventos_hora:
                    card = WeekEventCard(ev, d_date, self.colores, self._on_card_click)
                    slot_lay.addWidget(card)

                # Si no hay eventos, habilitar clic para añadir nuevo evento en esta fecha y hora
                if not eventos_hora:
                    slot.setCursor(Qt.CursorShape.PointingHandCursor)
                    slot.mousePressEvent = lambda e, d=d_date, h=h_num: self._on_empty_slot_click(d, h)

                self.grid_lay.addWidget(slot, row_idx, col_idx + 1)

    def _on_card_click(self, fecha, evento):
        if self.callbacks.get("ver_detalle"):
            self.callbacks["ver_detalle"](fecha)

    def _on_empty_slot_click(self, fecha, hora_num):
        if self.callbacks.get("añadir_recordatorio"):
            self.callbacks["añadir_recordatorio"](fecha)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.refrescar()
