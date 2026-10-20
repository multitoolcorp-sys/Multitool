import os
import platform
import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QComboBox, QDialog, QLineEdit, QCheckBox, 
    QGridLayout, QDialogButtonBox, QFileDialog, QSpinBox
)
from PyQt6.QtCore import Qt, QTime
from PyQt6.QtGui import QFont

class AlarmCard(QFrame):
    """Tarjeta individual de alarma con botón de edición ✏️ y estado ON/OFF"""
    def __init__(self, alarma, colores, callbacks, parent_submodule, parent=None):
        super().__init__(parent)
        self.alarma = alarma
        self.colores = colores
        self.callbacks = callbacks
        self.parent_submodule = parent_submodule
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: rgba(255, 255, 255, 0.15);
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Formatear hora 12H AM/PM
        h24 = alarma.get("hora", 0)
        minuto = alarma.get("minuto", 0)
        ampm = "PM" if h24 >= 12 else "AM"
        h12 = h24 % 12
        if h12 == 0: h12 = 12
        hora_12h = f"{h12:02d}:{minuto:02d} {ampm}"

        # Display Hora
        lbl_hora = QLabel(hora_12h)
        lbl_hora.setFont(QFont("Consolas" if platform.system() == "Windows" else "Monospace", 16, QFont.Weight.Bold))
        lbl_hora.setStyleSheet("color: white;")
        layout.addWidget(lbl_hora)

        # Etiqueta y Días Activos
        info_lay = QVBoxLayout()
        info_lay.setSpacing(2)
        
        lbl_label = QLabel(alarma.get("label", "Alarma"))
        lbl_label.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_label.setStyleSheet("color: white;")
        info_lay.addWidget(lbl_label)

        # Cadena de días
        dias_nombres = ["L", "M", "Mi", "J", "V", "S", "D"]
        dias_sel = alarma.get("dias", list(range(7)))
        if len(dias_sel) == 7:
            dias_txt = "Todos los días"
        elif set(dias_sel) == {0, 1, 2, 3, 4}:
            dias_txt = "Días laborables (L-V)"
        elif set(dias_sel) == {5, 6}:
            dias_txt = "Fin de semana"
        else:
            dias_txt = ", ".join([dias_nombres[d] for d in sorted(dias_sel)])
            
        lbl_dias = QLabel(dias_txt)
        lbl_dias.setFont(QFont(self.font_family, 8))
        lbl_dias.setStyleSheet("color: rgba(255,255,255,0.6);")
        info_lay.addWidget(lbl_dias)

        layout.addLayout(info_lay, 1)

        # Botón Editar ✏️
        btn_edit = QPushButton("✏️ Editar")
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setFont(QFont(self.font_family, 8))
        btn_edit.setStyleSheet(f"""
            QPushButton {{
                background-color: {colores['bg_terciario']};
                color: white; border-radius: 6px; padding: 5px 10px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.1); }}
        """)
        btn_edit.clicked.connect(lambda: parent_submodule.mostrar_dialogo_alarma(alarma))
        layout.addWidget(btn_edit)

        # Toggle ON/OFF
        is_active = alarma.get("active", True)
        btn_toggle = QPushButton("🟢 ON" if is_active else "⚪ OFF")
        btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_toggle.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {colores['acento'] if is_active else colores['bg_terciario']};
                color: white; border-radius: 6px; padding: 5px 12px; border: none;
            }}
        """)
        aid = alarma["id"]
        btn_toggle.clicked.connect(lambda ch, a=aid: callbacks["alarm_toggle"](a))
        layout.addWidget(btn_toggle)

        # Botón Eliminar 🗑️
        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(28, 28)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(239,68,68,0.2); border-radius: 4px; }")
        btn_del.clicked.connect(lambda ch, a=aid: callbacks["alarm_del"](a))
        layout.addWidget(btn_del)


class AlarmasTimerSubmodule(QWidget):
    """Submódulo 1: Alarmas (con formulario rico de edición) & Temporizador Regresivo"""
    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        self.inicializar_ui()

    def inicializar_ui(self):
        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(15, 15, 15, 15)
        main_lay.setSpacing(15)

        # =========================================================================
        # COLUMNA IZQUIERDA: GESTOR DE ALARMAS
        # =========================================================================
        left_frame = QFrame()
        left_frame.setStyleSheet("background: transparent;")
        left_lay = QVBoxLayout(left_frame)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(10)

        # Header Alarmas
        hdr_lay = QHBoxLayout()
        lbl_a_title = QLabel("⏰ ALARMAS PROGRAMADAS")
        lbl_a_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_a_title.setStyleSheet("color: white;")
        hdr_lay.addWidget(lbl_a_title)
        hdr_lay.addStretch()

        btn_add_alarm = QPushButton("➕ Programar Alarma")
        btn_add_alarm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_alarm.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_add_alarm.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 6px 14px; border-radius: 6px; border: none;")
        btn_add_alarm.clicked.connect(lambda: self.mostrar_dialogo_alarma())
        hdr_lay.addWidget(btn_add_alarm)

        left_lay.addLayout(hdr_lay)

        # Barra de Configuración de Audio
        audio_bar = QHBoxLayout()
        audio_bar.setSpacing(8)

        self.lbl_sonido_actual = QLabel("🎵 Sonido: Predefinido")
        self.lbl_sonido_actual.setFont(QFont(self.font_family, 8))
        self.lbl_sonido_actual.setStyleSheet("color: rgba(255,255,255,0.7);")
        audio_bar.addWidget(self.lbl_sonido_actual, 1)

        btn_sound = QPushButton("🎵 Cambiar Tono")
        btn_sound.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sound.setFont(QFont(self.font_family, 8))
        btn_sound.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white; padding: 4px 8px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.1);")
        btn_sound.clicked.connect(lambda: self.callbacks["alarm_change_sound"]())
        audio_bar.addWidget(btn_sound)

        # Selector de Hardware de Audio
        self.combo_audio_hw = QComboBox()
        self.combo_audio_hw.setFont(QFont(self.font_family, 8))
        self.combo_audio_hw.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 4px 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
            }}
        """)
        self.combo_audio_hw.currentIndexChanged.connect(self._on_audio_hw_changed)
        audio_bar.addWidget(self.combo_audio_hw)

        left_lay.addLayout(audio_bar)

        # Scroll Area de Alarmas
        scroll_alarmas = QScrollArea()
        scroll_alarmas.setWidgetResizable(True)
        scroll_alarmas.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container_alarmas = QWidget()
        self.container_alarmas.setStyleSheet("background: transparent;")
        self.lay_alarmas = QVBoxLayout(self.container_alarmas)
        self.lay_alarmas.setContentsMargins(0, 0, 0, 0)
        self.lay_alarmas.setSpacing(8)
        self.lay_alarmas.addStretch()

        scroll_alarmas.setWidget(self.container_alarmas)
        left_lay.addWidget(scroll_alarmas, 1)

        main_lay.addWidget(left_frame, 1)

        # =========================================================================
        # COLUMNA DERECHA: TEMPORIZADOR REGRESIVO (COUNTDOWN)
        # =========================================================================
        right_frame = QFrame()
        right_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }}
        """)
        right_lay = QVBoxLayout(right_frame)
        right_lay.setContentsMargins(15, 15, 15, 15)
        right_lay.setSpacing(12)

        lbl_t_title = QLabel("⏳ TEMPORIZADOR REGRESIVO")
        lbl_t_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_t_title.setStyleSheet("color: white;")
        right_lay.addWidget(lbl_t_title)

        # Display Digital del Temporizador
        self.lbl_timer_digits = QLabel("00:00:00")
        self.lbl_timer_digits.setFont(QFont(self.mono_font, 36, QFont.Weight.Bold))
        self.lbl_timer_digits.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        self.lbl_timer_digits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_lay.addWidget(self.lbl_timer_digits)

        # Botones de Presets Rápidos
        presets_lay = QHBoxLayout()
        presets_lay.setSpacing(6)
        presets = [("1m", 60), ("5m", 300), ("10m", 600), ("15m", 900), ("30m", 1800), ("1h", 3600)]
        for label, segs in presets:
            btn_p = QPushButton(label)
            btn_p.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_p.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
            btn_p.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colores['bg_terciario']};
                    color: white; border-radius: 4px; border: 1px solid rgba(255,255,255,0.06); padding: 4px;
                }}
                QPushButton:hover {{ background-color: {self.colores['acento']}44; }}
            """)
            btn_p.clicked.connect(lambda ch, s=segs: self._set_timer_seconds(s))
            presets_lay.addWidget(btn_p)
        right_lay.addLayout(presets_lay)

        # Controles H:M:S Personalizables por el Usuario
        lbl_custom = QLabel("Duración Personalizada (H:M:S):")
        lbl_custom.setFont(QFont(self.font_family, 8))
        lbl_custom.setStyleSheet("color: rgba(255,255,255,0.7);")
        right_lay.addWidget(lbl_custom)

        custom_t_lay = QHBoxLayout()
        custom_t_lay.setSpacing(4)
        
        lbl_h = QLabel("H:")
        lbl_h.setStyleSheet("color: white; font-size: 10px;")
        self.spin_h = QSpinBox()
        self.spin_h.setRange(0, 23)
        self.spin_h.setValue(0)
        
        lbl_m = QLabel("M:")
        lbl_m.setStyleSheet("color: white; font-size: 10px;")
        self.spin_m = QSpinBox()
        self.spin_m.setRange(0, 59)
        self.spin_m.setValue(5)
        
        lbl_s = QLabel("S:")
        lbl_s.setStyleSheet("color: white; font-size: 10px;")
        self.spin_s = QSpinBox()
        self.spin_s.setRange(0, 59)
        self.spin_s.setValue(0)
        
        spin_style = f"""
            QSpinBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 2px 4px; font-weight: bold;
            }}
        """
        self.spin_h.setStyleSheet(spin_style)
        self.spin_m.setStyleSheet(spin_style)
        self.spin_s.setStyleSheet(spin_style)

        btn_set_custom = QPushButton("⚙️ Fijar")
        btn_set_custom.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_set_custom.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_set_custom.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; border-radius: 4px; padding: 4px 8px; border: none;")
        btn_set_custom.clicked.connect(self._set_custom_timer_from_spins)

        custom_t_lay.addWidget(lbl_h)
        custom_t_lay.addWidget(self.spin_h)
        custom_t_lay.addWidget(lbl_m)
        custom_t_lay.addWidget(self.spin_m)
        custom_t_lay.addWidget(lbl_s)
        custom_t_lay.addWidget(self.spin_s)
        custom_t_lay.addWidget(btn_set_custom)

        right_lay.addLayout(custom_t_lay)

        # Controles Iniciar / Pausa / Reiniciar
        ctrl_t_lay = QHBoxLayout()
        ctrl_t_lay.setSpacing(8)

        self.btn_timer_start = QPushButton("▶ Iniciar")
        self.btn_timer_start.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_timer_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_timer_start.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; border-radius: 6px; padding: 8px 14px;")
        self.btn_timer_start.clicked.connect(self._on_timer_start_click)
        ctrl_t_lay.addWidget(self.btn_timer_start)

        self.btn_timer_reset = QPushButton("🔄 Reiniciar")
        self.btn_timer_reset.setFont(QFont(self.font_family, 9))
        self.btn_timer_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_timer_reset.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px 14px;")
        self.btn_timer_reset.clicked.connect(lambda: self.callbacks["timer_reset"]())
        ctrl_t_lay.addWidget(self.btn_timer_reset)

        right_lay.addLayout(ctrl_t_lay)
        right_lay.addStretch()

        main_lay.addWidget(right_frame, 1)

        self.refrescar_alarmas()

    def refrescar_alarmas(self):
        while self.lay_alarmas.count() > 1:
            item = self.lay_alarmas.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for a in self.manager.alarmas:
            card = AlarmCard(a, self.colores, self.callbacks, parent_submodule=self)
            self.lay_alarmas.insertWidget(self.lay_alarmas.count() - 1, card)

    # ── Formulario Rico de Programación & Edición de Alarmas ─────────────────
    def mostrar_dialogo_alarma(self, a_obj=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("Editar Alarma" if a_obj else "Nueva Alarma")
        dialog.setMinimumWidth(340)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores['bg_secundario']};
                color: white;
            }}
            QLabel {{
                color: white;
            }}
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        lbl_h = QLabel("⏰ EDITAR ALARMA" if a_obj else "⏰ PROGRAMAR ALARMA")
        lbl_h.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_h.setStyleSheet(f"color: {self.colores['acento']}; letter-spacing: 1px;")
        layout.addWidget(lbl_h)
        
        grid = QGridLayout()
        grid.setSpacing(10)
        
        lbl_hora = QLabel("Hora de alarma:")
        lbl_hora.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_hora.setStyleSheet("color: rgba(255,255,255,0.7);")
        
        # Selección de hora 12h + AM/PM
        h_lay = QHBoxLayout()
        h_lay.setSpacing(6)
        
        combo_hora = QComboBox()
        combo_hora.addItems([f"{i:02d}" for i in range(1, 13)])
        
        combo_min = QComboBox()
        combo_min.addItems([f"{i:02d}" for i in range(60)])
        
        combo_ampm = QComboBox()
        combo_ampm.addItems(["AM", "PM"])
        
        combo_style = f"""
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; padding: 6px 10px; border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                font-family: 'Consolas', monospace; font-size: 13px; font-weight: bold;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
            }}
        """
        combo_hora.setStyleSheet(combo_style)
        combo_min.setStyleSheet(combo_style)
        combo_ampm.setStyleSheet(combo_style)
        
        if a_obj:
            h24 = a_obj.get("hora", 0)
            m = a_obj.get("minuto", 0)
            ampm = "PM" if h24 >= 12 else "AM"
            h12 = h24 % 12
            if h12 == 0: h12 = 12
            combo_hora.setCurrentText(f"{h12:02d}")
            combo_min.setCurrentText(f"{m:02d}")
            combo_ampm.setCurrentText(ampm)
        else:
            now = datetime.datetime.now()
            h24 = now.hour
            m = now.minute
            ampm = "PM" if h24 >= 12 else "AM"
            h12 = h24 % 12
            if h12 == 0: h12 = 12
            combo_hora.setCurrentText(f"{h12:02d}")
            combo_min.setCurrentText(f"{m:02d}")
            combo_ampm.setCurrentText(ampm)
            
        h_lay.addWidget(combo_hora)
        lbl_sep = QLabel(":")
        lbl_sep.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        lbl_sep.setStyleSheet("color: white;")
        h_lay.addWidget(lbl_sep)
        h_lay.addWidget(combo_min)
        h_lay.addWidget(combo_ampm)
        
        grid.addWidget(lbl_hora, 0, 0)
        grid.addLayout(h_lay, 0, 1)
        
        lbl_nota = QLabel("Etiqueta:")
        lbl_nota.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_nota.setStyleSheet("color: rgba(255,255,255,0.7);")
        
        label_edit = QLineEdit(a_obj.get("label", "Alarma") if a_obj else "Alarma")
        label_edit.setFont(QFont(self.font_family, 9))
        label_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores['bg_terciario']};
                color: white; padding: 6px 10px; border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        grid.addWidget(lbl_nota, 1, 0)
        grid.addWidget(label_edit, 1, 1)
        layout.addLayout(grid)
        
        lbl_dias = QLabel("Días Activos:")
        lbl_dias.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_dias.setStyleSheet("color: rgba(255,255,255,0.7);")
        layout.addWidget(lbl_dias)
        
        dias_lay = QHBoxLayout()
        dias_lay.setSpacing(4)
        dias_corto = ["L", "M", "Mi", "J", "V", "S", "D"]
        checks = []
        dias_sel = a_obj.get("dias", list(range(7))) if a_obj else list(range(7))
        
        checkbox_style = f"""
            QCheckBox {{
                color: white; font-weight: bold; font-size: 10px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px; border-radius: 3px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                background-color: {self.colores['bg_terciario']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colores['acento']};
                border-color: {self.colores['acento']};
            }}
        """
        
        for i, d in enumerate(dias_corto):
            chk = QCheckBox(d)
            chk.setChecked(i in dias_sel)
            chk.setStyleSheet(checkbox_style)
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
            dias_lay.addWidget(chk)
            checks.append(chk)
        layout.addLayout(dias_lay)
        
        layout.addSpacing(10)
        
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; padding: 6px 14px; border-radius: 6px;")
        btn_cancel.clicked.connect(dialog.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Guardar Alarma" if a_obj else "Programar Alarma")
        btn_save.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_save.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 6px 16px; border-radius: 6px;")
        
        def on_accept():
            ds = [i for i, c in enumerate(checks) if c.isChecked()]
            h12 = int(combo_hora.currentText())
            mi = int(combo_min.currentText())
            ampm = combo_ampm.currentText()
            if ampm == "AM":
                h24 = 0 if h12 == 12 else h12
            else:
                h24 = 12 if h12 == 12 else h12 + 12
            
            lbl_val = label_edit.text().strip() or "Alarma"
            aid = a_obj["id"] if a_obj else None

            if aid and "alarm_edit_save" in self.callbacks:
                self.callbacks["alarm_edit_save"](aid, h24, mi, lbl_val, None, ds)
            else:
                self.callbacks["alarm_add"](h24, mi, lbl_val, None, ds)
            dialog.accept()
            self.refrescar_alarmas()

        btn_save.clicked.connect(on_accept)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

        dialog.exec()

    def _set_timer_seconds(self, segs):
        self.manager.timer_remaining = segs
        self._update_timer_digits(segs)

    def _update_timer_digits(self, segs):
        h = int(segs // 3600)
        m = int((segs % 3600) // 60)
        s = int(segs % 60)
        self.lbl_timer_digits.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def _on_timer_start_click(self):
        if self.manager.timer_running:
            self.callbacks["timer_pause"]()
            self.btn_timer_start.setText("▶ Reanudar")
        else:
            self.callbacks["timer_start"]()
            self.btn_timer_start.setText("⏸️ Pausar")

    def _set_custom_timer_from_spins(self):
        segs = self.spin_h.value() * 3600 + self.spin_m.value() * 60 + self.spin_s.value()
        if segs > 0:
            self._set_timer_seconds(segs)

    def _on_audio_hw_changed(self, index):
        dev_id = self.combo_audio_hw.itemData(index)
        if "alarm_change_device" in self.callbacks:
            self.callbacks["alarm_change_device"](dev_id)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.lbl_timer_digits.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        self.refrescar_alarmas()
