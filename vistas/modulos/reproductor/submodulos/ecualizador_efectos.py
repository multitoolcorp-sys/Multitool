import platform
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QSlider, QComboBox, QSpinBox, QGridLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class EcualizadorEfectosSubmodule(QWidget):
    """Submódulo 6: Ecualizador Gráfico, Control de Velocidad y Temporizador de Apagado (Sleep Timer)"""
    def __init__(self, parent, context, manager, colores, callbacks=None):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks or {}
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        # Estado Sleep Timer
        self.sleep_timer = QTimer(self)
        self.sleep_timer.setInterval(1000)
        self.sleep_timer.timeout.connect(self._on_sleep_tick)
        self.sleep_segundos_restantes = 0
        self.sleep_activo = False
        self._volumen_original = 1.0

        # Presets de EQ (60Hz, 250Hz, 1kHz, 4kHz, 12kHz en dB: -12 a +12)
        self.PRESETS = {
            "Plano (Flat)": [0, 0, 0, 0, 0],
            "Rock": [4, 2, -1, 3, 4],
            "Pop": [2, 1, 2, 1, 2],
            "Electrónica": [5, 3, 0, 2, 4],
            "Realce de Graves": [6, 4, 0, 0, 0],
            "Voces Claras": [-2, 0, 3, 4, 2],
            "Acústico": [3, 2, 1, 2, 3]
        }

        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("🎛️ ECUALIZADOR, VELOCIDAD & SLEEP TIMER")
        lbl_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()
        layout.addLayout(hdr)

        # Panel de Doble Columna:
        # Izquierda: Ecualizador Gráfico (5 Bandas)
        # Derecha: Velocidad de Reproducción y Sleep Timer
        panels_row = QHBoxLayout()
        panels_row.setSpacing(15)

        # =========================================================================
        # COLUMNA IZQUIERDA: ECUALIZADOR GRÁFICO
        # =========================================================================
        eq_frame = QFrame()
        eq_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }}
        """)
        eq_lay = QVBoxLayout(eq_frame)
        eq_lay.setContentsMargins(15, 15, 15, 15)
        eq_lay.setSpacing(12)

        # Selector de Presets
        top_eq = QHBoxLayout()
        lbl_p = QLabel("Perfil de Audio:")
        lbl_p.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_p.setStyleSheet("color: rgba(255,255,255,0.7);")
        top_eq.addWidget(lbl_p)

        self.combo_presets = QComboBox()
        self.combo_presets.setFont(QFont(self.font_family, 8))
        self.combo_presets.addItems(list(self.PRESETS.keys()))
        self.combo_presets.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 3px 8px;
            }}
        """)
        self.combo_presets.currentTextChanged.connect(self._aplicar_preset)
        top_eq.addWidget(self.combo_presets, 1)

        btn_reset_eq = QPushButton("↺ Plano")
        btn_reset_eq.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_eq.setFont(QFont(self.font_family, 8))
        btn_reset_eq.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: white; border-radius: 4px; padding: 3px 8px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            QPushButton:hover {{ background-color: {self.colores['acento']}; }}
        """)
        btn_reset_eq.clicked.connect(lambda: self.combo_presets.setCurrentText("Plano (Flat)"))
        top_eq.addWidget(btn_reset_eq)

        eq_lay.addLayout(top_eq)

        # Sliders Verticales de 5 Bandas
        sliders_box = QHBoxLayout()
        sliders_box.setSpacing(12)

        self.band_sliders = []
        self.band_labels_db = []
        band_names = ["60 Hz\n(Graves)", "250 Hz\n(Medio-G)", "1 kHz\n(Medios)", "4 kHz\n(Presencia)", "12 kHz\n(Agudos)"]

        for i, b_name in enumerate(band_names):
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.setSpacing(6)

            lbl_db = QLabel("0 dB")
            lbl_db.setFont(QFont(self.mono_font, 8, QFont.Weight.Bold))
            lbl_db.setStyleSheet(f"color: {self.colores['acento']};")
            lbl_db.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl_db)
            self.band_labels_db.append(lbl_db)

            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-12, 12)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TickPosition.TicksBothSides)
            slider.setTickInterval(3)
            slider.setMinimumHeight(140)
            slider.setStyleSheet(f"""
                QSlider::groove:vertical {{
                    background: {self.colores['bg_terciario']};
                    width: 6px; border-radius: 3px;
                }}
                QSlider::handle:vertical {{
                    background: {self.colores['acento']};
                    height: 16px; margin: 0 -5px; border-radius: 8px;
                }}
                QSlider::handle:vertical:hover {{
                    background: {self.colores.get('acento_hover', self.colores['acento'])};
                }}
            """)
            slider.valueChanged.connect(lambda val, idx=i: self._on_slider_eq_changed(idx, val))
            col.addWidget(slider, 1, Qt.AlignmentFlag.AlignCenter)
            self.band_sliders.append(slider)

            lbl_hz = QLabel(b_name)
            lbl_hz.setFont(QFont(self.font_family, 7))
            lbl_hz.setStyleSheet("color: rgba(255,255,255,0.6);")
            lbl_hz.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl_hz)

            sliders_box.addLayout(col)

        eq_lay.addLayout(sliders_box)
        panels_row.addWidget(eq_frame, 6)

        # =========================================================================
        # COLUMNA DERECHA: VELOCIDAD DE REPRODUCCIÓN & SLEEP TIMER
        # =========================================================================
        right_frame = QFrame()
        right_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }}
        """)
        r_lay = QVBoxLayout(right_frame)
        r_lay.setContentsMargins(15, 15, 15, 15)
        r_lay.setSpacing(14)

        # 1. Velocidad de Reproducción
        lbl_v_tit = QLabel("⚡ VELOCIDAD DE REPRODUCCIÓN")
        lbl_v_tit.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_v_tit.setStyleSheet("color: white;")
        r_lay.addWidget(lbl_v_tit)

        speeds_lay = QHBoxLayout()
        speeds_lay.setSpacing(4)
        self.speed_buttons = {}
        for sp in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
            btn_sp = QPushButton(f"{sp}x")
            btn_sp.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_sp.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
            btn_sp.setStyleSheet(self._speed_btn_style(sp == 1.0))
            btn_sp.clicked.connect(lambda ch, s=sp: self._cambiar_velocidad(s))
            speeds_lay.addWidget(btn_sp)
            self.speed_buttons[sp] = btn_sp
        r_lay.addLayout(speeds_lay)

        # Separador
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255, 255, 255, 0.05);")
        r_lay.addWidget(sep)

        # 2. Temporizador de Apagado (Sleep Timer)
        lbl_s_tit = QLabel("💤 TEMPORIZADOR DE APAGADO (SLEEP TIMER)")
        lbl_s_tit.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_s_tit.setStyleSheet("color: white;")
        r_lay.addWidget(lbl_s_tit)

        sleep_presets_lay = QHBoxLayout()
        sleep_presets_lay.setSpacing(6)
        presets_sleep = [("15m", 15), ("30m", 30), ("45m", 45), ("60m", 60)]
        for lbl, mins in presets_sleep:
            btn_sl = QPushButton(lbl)
            btn_sl.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_sl.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
            btn_sl.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colores['bg_terciario']};
                    color: white; border-radius: 4px; padding: 4px;
                    border: 1px solid rgba(255,255,255,0.06);
                }}
                QPushButton:hover {{ background-color: {self.colores['acento']}; }}
            """)
            btn_sl.clicked.connect(lambda ch, m=mins: self.spin_sleep_mins.setValue(m))
            sleep_presets_lay.addWidget(btn_sl)
        r_lay.addLayout(sleep_presets_lay)

        custom_s_lay = QHBoxLayout()
        lbl_m_in = QLabel("Minutos:")
        lbl_m_in.setFont(QFont(self.font_family, 8))
        lbl_m_in.setStyleSheet("color: rgba(255,255,255,0.7);")
        custom_s_lay.addWidget(lbl_m_in)

        self.spin_sleep_mins = QSpinBox()
        self.spin_sleep_mins.setRange(1, 240)
        self.spin_sleep_mins.setValue(30)
        self.spin_sleep_mins.setStyleSheet(f"""
            QSpinBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 2px 6px; font-weight: bold;
            }}
        """)
        custom_s_lay.addWidget(self.spin_sleep_mins)

        self.btn_toggle_sleep = QPushButton("▶ Activar Sleep Timer")
        self.btn_toggle_sleep.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_sleep.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self.btn_toggle_sleep.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white; border-radius: 4px; padding: 4px 10px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores.get('acento_hover', self.colores['acento'])}; }}
        """)
        self.btn_toggle_sleep.clicked.connect(self._toggle_sleep_timer)
        custom_s_lay.addWidget(self.btn_toggle_sleep)

        r_lay.addLayout(custom_s_lay)

        # Display Contador Sleep Timer
        self.lbl_sleep_countdown = QLabel("Apagado inactivo")
        self.lbl_sleep_countdown.setFont(QFont(self.mono_font, 12, QFont.Weight.Bold))
        self.lbl_sleep_countdown.setStyleSheet("color: rgba(255,255,255,0.4);")
        self.lbl_sleep_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r_lay.addWidget(self.lbl_sleep_countdown)

        r_lay.addStretch()
        panels_row.addWidget(right_frame, 5)

        layout.addLayout(panels_row)

    def _speed_btn_style(self, active=False):
        if active:
            return f"background-color: {self.colores['acento']}; color: white; border-radius: 4px; padding: 5px; border: none;"
        return f"background-color: {self.colores['bg_terciario']}; color: rgba(255,255,255,0.8); border-radius: 4px; padding: 5px; border: 1px solid rgba(255,255,255,0.06);"

    def _cambiar_velocidad(self, speed):
        for s, btn in self.speed_buttons.items():
            btn.setStyleSheet(self._speed_btn_style(s == speed))
        if hasattr(self.manager, "set_playback_rate"):
            self.manager.set_playback_rate(speed)

    def _on_slider_eq_changed(self, index, value):
        sign = "+" if value > 0 else ""
        self.band_labels_db[index].setText(f"{sign}{value} dB")

    def _aplicar_preset(self, preset_name):
        vals = self.PRESETS.get(preset_name, [0, 0, 0, 0, 0])
        for idx, v in enumerate(vals):
            self.band_sliders[idx].blockSignals(True)
            self.band_sliders[idx].setValue(v)
            self.band_sliders[idx].blockSignals(False)
            sign = "+" if v > 0 else ""
            self.band_labels_db[idx].setText(f"{sign}{v} dB")

    def _toggle_sleep_timer(self):
        if self.sleep_activo:
            # Desactivar
            self.sleep_timer.stop()
            self.sleep_activo = False
            self.btn_toggle_sleep.setText("▶ Activar Sleep Timer")
            self.btn_toggle_sleep.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; border-radius: 4px; padding: 4px 10px; border: none;")
            self.lbl_sleep_countdown.setText("Apagado inactivo")
            self.lbl_sleep_countdown.setStyleSheet("color: rgba(255,255,255,0.4);")
        else:
            # Activar
            mins = self.spin_sleep_mins.value()
            self.sleep_segundos_restantes = mins * 60
            self.sleep_activo = True
            self.sleep_timer.start()
            self.btn_toggle_sleep.setText("⏹ Cancelar Sleep")
            self.btn_toggle_sleep.setStyleSheet("background-color: #EF4444; color: white; border-radius: 4px; padding: 4px 10px; border: none;")
            self._actualizar_lbl_sleep()

    def _on_sleep_tick(self):
        if self.sleep_segundos_restantes > 0:
            self.sleep_segundos_restantes -= 1
            self._actualizar_lbl_sleep()

            # Fade-out en los últimos 10 segundos
            if self.sleep_segundos_restantes <= 10:
                frac = self.sleep_segundos_restantes / 10.0
                if hasattr(self.manager, "set_volumen_audio"):
                    self.manager.set_volumen_audio(max(0.0, frac * 0.8))

            if self.sleep_segundos_restantes == 0:
                self._ejecutar_apagado()

    def _actualizar_lbl_sleep(self):
        m = self.sleep_segundos_restantes // 60
        s = self.sleep_segundos_restantes % 60
        self.lbl_sleep_countdown.setText(f"⏳ Apagado en: {m:02d}:{s:02d}")
        self.lbl_sleep_countdown.setStyleSheet(f"color: {self.colores['acento']};")

    def _ejecutar_apagado(self):
        self.sleep_timer.stop()
        self.sleep_activo = False
        self.lbl_sleep_countdown.setText("😴 Reproducción Pausada")
        self.lbl_sleep_countdown.setStyleSheet("color: #10B981;")
        self.btn_toggle_sleep.setText("▶ Activar Sleep Timer")
        self.btn_toggle_sleep.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; border-radius: 4px; padding: 4px 10px; border: none;")
        
        # Pausar reproducción en PlayerManager
        if hasattr(self.manager, "pausar_audio"):
            self.manager.pausar_audio()
        if hasattr(self.manager, "pausar_video"):
            self.manager.pausar_video()

    def actualizar_tema(self, colores):
        self.colores = colores
        for s in self.band_sliders:
            s.setStyleSheet(f"""
                QSlider::groove:vertical {{
                    background: {self.colores['bg_terciario']};
                    width: 6px; border-radius: 3px;
                }}
                QSlider::handle:vertical {{
                    background: {self.colores['acento']};
                    height: 16px; margin: 0 -5px; border-radius: 8px;
                }}
            """)
        for lbl in self.band_labels_db:
            lbl.setStyleSheet(f"color: {self.colores['acento']};")

    def cleanup(self):
        if hasattr(self, "sleep_timer") and self.sleep_timer.isActive():
            self.sleep_timer.stop()
