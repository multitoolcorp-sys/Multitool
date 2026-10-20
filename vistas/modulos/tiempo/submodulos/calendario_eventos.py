import platform
import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QCalendarWidget, QDialog, QLineEdit, 
    QComboBox, QTextEdit, QTimeEdit, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QFont, QTextCharFormat, QColor

class EventCard(QFrame):
    """Tarjeta de evento con contador regresivo a la fecha indicada"""
    def __init__(self, evento, colores, on_edit_cb, on_delete_cb, parent=None):
        super().__init__(parent)
        self.evento = evento
        self.colores = colores
        self.on_edit_cb = on_edit_cb
        self.on_delete_cb = on_delete_cb
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-left: 4px solid {evento.get('color', colores['acento'])};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: rgba(255, 255, 255, 0.15);
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Información del evento
        info_lay = QVBoxLayout()
        info_lay.setSpacing(3)

        hdr_row = QHBoxLayout()
        lbl_titulo = QLabel(evento.get("titulo", "Evento"))
        lbl_titulo.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet("color: white;")
        hdr_row.addWidget(lbl_titulo)

        cat = evento.get("categoria", "General")
        lbl_cat = QLabel(f"• {cat}")
        lbl_cat.setFont(QFont(self.font_family, 8))
        lbl_cat.setStyleSheet(f"color: {evento.get('color', colores['acento'])}; font-weight: bold;")
        hdr_row.addWidget(lbl_cat)
        hdr_row.addStretch()

        info_lay.addLayout(hdr_row)

        # Fecha y Hora
        fecha_str = evento.get("fecha", "")
        hora_str = evento.get("hora", "")
        desc = evento.get("descripcion", "")

        sub_info = f"🗓️ {fecha_str}" + (f" a las {hora_str}" if hora_str else "")
        lbl_sub = QLabel(sub_info)
        lbl_sub.setFont(QFont(self.font_family, 8))
        lbl_sub.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        info_lay.addWidget(lbl_sub)

        if desc:
            lbl_desc = QLabel(desc)
            lbl_desc.setFont(QFont(self.font_family, 8))
            lbl_desc.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
            lbl_desc.setWordWrap(True)
            info_lay.addWidget(lbl_desc)

        layout.addLayout(info_lay, 1)

        # Cálculo de Cuenta Regresiva (Días restantes)
        dias_diff = self._calcular_dias_restantes(fecha_str)
        lbl_countdown = QLabel()
        lbl_countdown.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if dias_diff == 0:
            lbl_countdown.setText("🚨 ¡HOY!")
            lbl_countdown.setStyleSheet("background-color: rgba(239, 68, 68, 0.2); color: #EF4444; border-radius: 6px; padding: 4px 8px; border: 1px solid rgba(239, 68, 68, 0.4);")
        elif dias_diff == 1:
            lbl_countdown.setText("⏳ Mañana")
            lbl_countdown.setStyleSheet("background-color: rgba(245, 158, 11, 0.2); color: #F59E0B; border-radius: 6px; padding: 4px 8px; border: 1px solid rgba(245, 158, 11, 0.4);")
        elif dias_diff > 1:
            lbl_countdown.setText(f"⏳ Faltan {dias_diff} d")
            lbl_countdown.setStyleSheet(f"background-color: rgba(99, 102, 241, 0.15); color: {colores['acento']}; border-radius: 6px; padding: 4px 8px; border: 1px solid {colores['acento']}44;")
        else:
            lbl_countdown.setText(f"✔️ Pasó ({abs(dias_diff)} d)")
            lbl_countdown.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); color: rgba(255,255,255,0.4); border-radius: 6px; padding: 4px 8px; border: 1px solid rgba(255, 255, 255, 0.08);")

        layout.addWidget(lbl_countdown)

        # Botón Editar ✏️
        btn_edit = QPushButton("✏️")
        btn_edit.setFixedSize(28, 28)
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setToolTip("Editar Evento")
        btn_edit.setStyleSheet(f"""
            QPushButton {{
                background-color: {colores['bg_terciario']}; color: white; border-radius: 4px; border: 1px solid rgba(255,255,255,0.06);
            }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.15); }}
        """)
        btn_edit.clicked.connect(lambda: self.on_edit_cb(self.evento))
        layout.addWidget(btn_edit)

        # Botón Eliminar 🗑️
        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(28, 28)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setToolTip("Eliminar Evento")
        btn_del.setStyleSheet("""
            QPushButton {{
                background-color: transparent; border: none; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: rgba(239, 68, 68, 0.2); }}
        """)
        btn_del.clicked.connect(lambda: self.on_delete_cb(self.evento.get("id")))
        layout.addWidget(btn_del)

    def _calcular_dias_restantes(self, fecha_str):
        try:
            ev_date = datetime.datetime.strptime(fecha_str, "%Y-%m-%d").date()
            hoy = datetime.date.today()
            return (ev_date - hoy).days
        except Exception:
            return 0


class CalendarioEventosSubmodule(QWidget):
    """Submódulo 5: Calendario Visual Mensual & Gestor de Eventos con Cuenta Regresiva"""
    def __init__(self, parent, context, manager, colores):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()
        self.refrescar_eventos()

    def inicializar_ui(self):
        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(15, 15, 15, 15)
        main_lay.setSpacing(15)

        # =========================================================================
        # COLUMNA IZQUIERDA: CALENDARIO INTERACTIVO
        # =========================================================================
        left_frame = QFrame()
        left_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }}
        """)
        left_lay = QVBoxLayout(left_frame)
        left_lay.setContentsMargins(12, 12, 12, 12)
        left_lay.setSpacing(10)

        # Header Calendario
        cal_hdr = QHBoxLayout()
        lbl_cal_title = QLabel("📅 CALENDARIO")
        lbl_cal_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_cal_title.setStyleSheet("color: white;")
        cal_hdr.addWidget(lbl_cal_title)
        cal_hdr.addStretch()

        btn_today = QPushButton("Hoy")
        btn_today.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_today.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_today.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: white; border-radius: 4px; padding: 3px 10px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            QPushButton:hover {{ background-color: {self.colores['acento']}; }}
        """)
        btn_today.clicked.connect(self._ir_a_hoy)
        cal_hdr.addWidget(btn_today)
        left_lay.addLayout(cal_hdr)

        # Widget de Calendario estilizado
        self.calendar = QCalendarWidget()
        self.calendar.setFont(QFont(self.font_family, 9))
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self._estilizar_calendario()
        self.calendar.selectionChanged.connect(self._on_fecha_seleccionada)
        left_lay.addWidget(self.calendar, 1)

        # Info de fecha seleccionada
        self.lbl_selected_date = QLabel()
        self.lbl_selected_date.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_selected_date.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        self.lbl_selected_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_lay.addWidget(self.lbl_selected_date)

        main_lay.addWidget(left_frame, 5)

        # =========================================================================
        # COLUMNA DERECHA: LISTA DE EVENTOS Y CUENTA REGRESIVA
        # =========================================================================
        right_frame = QFrame()
        right_frame.setStyleSheet("background: transparent;")
        right_lay = QVBoxLayout(right_frame)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(10)

        # Header de Eventos
        ev_hdr = QHBoxLayout()
        lbl_ev_title = QLabel("⏳ EVENTOS & HITOS PROGRAMADOS")
        lbl_ev_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_ev_title.setStyleSheet("color: white;")
        ev_hdr.addWidget(lbl_ev_title)
        ev_hdr.addStretch()

        btn_add = QPushButton("➕ Nuevo Evento")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white; border-radius: 6px; padding: 6px 14px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores.get('acento_hover', self.colores['acento'])}; }}
        """)
        btn_add.clicked.connect(lambda: self.mostrar_dialogo_evento())
        ev_hdr.addWidget(btn_add)
        right_lay.addLayout(ev_hdr)

        # Barra de Filtros
        filt_bar = QHBoxLayout()
        filt_bar.setSpacing(6)
        lbl_f = QLabel("Filtrar:")
        lbl_f.setFont(QFont(self.font_family, 8))
        lbl_f.setStyleSheet("color: rgba(255,255,255,0.6);")
        filt_bar.addWidget(lbl_f)

        self.combo_filtro = QComboBox()
        self.combo_filtro.setFont(QFont(self.font_family, 8))
        self.combo_filtro.addItems(["Todos los Eventos", "Solo Próximos", "Solo Fecha Seleccionada", "Trabajo", "Personal", "Estudio"])
        self.combo_filtro.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 3px 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
            }}
        """)
        self.combo_filtro.currentIndexChanged.connect(self.refrescar_eventos)
        filt_bar.addWidget(self.combo_filtro, 1)

        right_lay.addLayout(filt_bar)

        # Scroll Area de Eventos
        scroll_ev = QScrollArea()
        scroll_ev.setWidgetResizable(True)
        scroll_ev.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container_eventos = QWidget()
        self.container_eventos.setStyleSheet("background: transparent;")
        self.lay_eventos = QVBoxLayout(self.container_eventos)
        self.lay_eventos.setContentsMargins(0, 0, 0, 0)
        self.lay_eventos.setSpacing(8)
        self.lay_eventos.addStretch()

        scroll_ev.setWidget(self.container_eventos)
        right_lay.addWidget(scroll_ev, 1)

        main_lay.addWidget(right_frame, 6)

        self._on_fecha_seleccionada()

    def _estilizar_calendario(self):
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: transparent;
                color: white;
            }}
            QCalendarWidget QToolButton {{
                color: white;
                background-color: {self.colores['bg_terciario']};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px;
                padding: 4px 8px;
                margin: 2px;
                font-weight: bold;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {self.colores['acento']};
            }}
            QCalendarWidget QMenu {{
                background-color: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            QCalendarWidget QSpinBox {{
                background-color: {self.colores['bg_terciario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px;
            }}
            QCalendarWidget QTableView {{
                background-color: transparent;
                selection-background-color: {self.colores['acento']};
                selection-color: white;
                alternate-background-color: transparent;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: transparent;
            }}
        """)

    def _ir_a_hoy(self):
        hoy = QDate.currentDate()
        self.calendar.setSelectedDate(hoy)
        self._on_fecha_seleccionada()

    def _on_fecha_seleccionada(self):
        qdate = self.calendar.selectedDate()
        d_str = qdate.toString("yyyy-MM-dd")
        dias_esp = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dia_sem = dias_esp[qdate.dayOfWeek() - 1]
        self.lbl_selected_date.setText(f"📌 {dia_sem}, {qdate.day()} de {qdate.toString('MMMM yyyy')}")

        if self.combo_filtro.currentText() == "Solo Fecha Seleccionada":
            self.refrescar_eventos()

    def refrescar_eventos(self):
        # Limpiar lista anterior
        while self.lay_eventos.count() > 1:
            item = self.lay_eventos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        eventos = getattr(self.manager, "eventos", [])
        filtro = self.combo_filtro.currentText()
        sel_fecha = self.calendar.selectedDate().toString("yyyy-MM-dd")
        hoy = datetime.date.today()

        filtrados = []
        for ev in eventos:
            f_str = ev.get("fecha", "")
            try:
                ev_d = datetime.datetime.strptime(f_str, "%Y-%m-%d").date()
            except Exception:
                ev_d = hoy

            if filtro == "Solo Próximos" and ev_d < hoy:
                continue
            elif filtro == "Solo Fecha Seleccionada" and f_str != sel_fecha:
                continue
            elif filtro in ("Trabajo", "Personal", "Estudio") and ev.get("categoria") != filtro:
                continue

            filtrados.append(ev)

        # Ordenar por fecha ascendente
        filtrados.sort(key=lambda x: x.get("fecha", ""))

        if not filtrados:
            lbl_empty = QLabel("✨ No hay eventos programados para este filtro.")
            lbl_empty.setFont(QFont(self.font_family, 9))
            lbl_empty.setStyleSheet("color: rgba(255, 255, 255, 0.4); padding: 20px;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lay_eventos.insertWidget(0, lbl_empty)
            return

        for ev in filtrados:
            card = EventCard(ev, self.colores, self.mostrar_dialogo_evento, self._eliminar_evento)
            self.lay_eventos.insertWidget(self.lay_eventos.count() - 1, card)

    def mostrar_dialogo_evento(self, evento=None):
        dlg = QDialog(self)
        es_edicion = evento is not None
        dlg.setWindowTitle("✏️ Editar Evento" if es_edicion else "➕ Nuevo Evento")
        dlg.setFixedSize(400, 380)
        dlg.setStyleSheet(f"""
            QDialog {{ background-color: {self.colores['bg_principal']}; color: white; }}
            QLabel {{ color: white; }}
            QLineEdit, QTextEdit, QComboBox, QTimeEdit {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 4px;
            }}
        """)

        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)

        # Título
        lay.addWidget(QLabel("Título del Evento / Hito:"))
        txt_titulo = QLineEdit(evento.get("titulo", "") if es_edicion else "")
        txt_titulo.setPlaceholderText("Ej: Entrega de Proyecto, Cumpleaños, Reunión...")
        lay.addWidget(txt_titulo)

        # Fecha
        f_row = QHBoxLayout()
        lay.addWidget(QLabel("Fecha:"))
        cal_picker = QCalendarWidget()
        cal_picker.setFixedHeight(160)
        cal_picker.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        if es_edicion and evento.get("fecha"):
            try:
                parts = [int(p) for p in evento["fecha"].split("-")]
                cal_picker.setSelectedDate(QDate(parts[0], parts[1], parts[2]))
            except Exception:
                pass
        else:
            cal_picker.setSelectedDate(self.calendar.selectedDate())
        lay.addWidget(cal_picker)

        # Hora y Categoría
        hc_lay = QHBoxLayout()
        hc_lay.addWidget(QLabel("Hora:"))
        time_pick = QTimeEdit()
        time_pick.setDisplayFormat("HH:mm")
        if es_edicion and evento.get("hora"):
            try:
                hp = [int(p) for p in evento["hora"].split(":")]
                time_pick.setTime(QTime(hp[0], hp[1]))
            except Exception:
                time_pick.setTime(QTime(9, 0))
        else:
            time_pick.setTime(QTime(9, 0))
        hc_lay.addWidget(time_pick)

        hc_lay.addWidget(QLabel("Categoría:"))
        combo_cat = QComboBox()
        combo_cat.addItems(["General", "Trabajo", "Personal", "Estudio", "Finanzas", "Salud"])
        if es_edicion:
            idx = combo_cat.findText(evento.get("categoria", "General"))
            if idx >= 0: combo_cat.setCurrentIndex(idx)
        hc_lay.addWidget(combo_cat)
        lay.addLayout(hc_lay)

        # Descripción
        lay.addWidget(QLabel("Notas / Descripción:"))
        txt_desc = QLineEdit(evento.get("descripcion", "") if es_edicion else "")
        txt_desc.setPlaceholderText("Detalles adicionales...")
        lay.addWidget(txt_desc)

        # Botones
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; padding: 6px 14px; border-radius: 4px; border: none;")
        btn_cancel.clicked.connect(dlg.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Guardar Evento")
        btn_save.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 6px 16px; border-radius: 4px; border: none; font-weight: bold;")
        
        colores_cat = {
            "Trabajo": "#3B82F6", "Personal": "#EC4899", "Estudio": "#8B5CF6",
            "Finanzas": "#10B981", "Salud": "#EF4444", "General": self.colores['acento']
        }

        def on_guardar():
            tit = txt_titulo.text().strip()
            if not tit:
                QMessageBox.warning(dlg, "Campo Requerido", "Por favor ingresa un título para el evento.")
                return
            f_str = cal_picker.selectedDate().toString("yyyy-MM-dd")
            h_str = time_pick.time().toString("HH:mm")
            cat_sel = combo_cat.currentText()
            c_sel = colores_cat.get(cat_sel, self.colores['acento'])
            desc_val = txt_desc.text().strip()

            if es_edicion:
                self.manager.editar_evento(evento["id"], tit, f_str, h_str, cat_sel, desc_val, c_sel)
            else:
                self.manager.añadir_evento(tit, f_str, h_str, cat_sel, desc_val, c_sel)
            dlg.accept()
            self.refrescar_eventos()

        btn_save.clicked.connect(on_guardar)
        btn_box.addWidget(btn_save)
        lay.addLayout(btn_box)

        dlg.exec()

    def _eliminar_evento(self, eid):
        self.manager.eliminar_evento(eid)
        self.refrescar_eventos()

    def actualizar_tema(self, colores):
        self.colores = colores
        self._estilizar_calendario()
        self.refrescar_eventos()
