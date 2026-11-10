"""
auto_clicker.py - Submódulo Auto Clicker Pro idéntico y mejorado de OP Auto Clicker 4.0.
Implementa todas las opciones clásicas: Click interval con Random offset ±ms,
Click options (Mouse button, Click type), Click repeat, Cursor position (Pick location),
y cuadrícula 2x2: Start, Stop, Hotkey setting y Record & Playback.
"""

import time
import random
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QRadioButton, QSpinBox, QSlider, QComboBox,
    QFrame, QCheckBox, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QObject
from PyQt6.QtGui import QFont

from ..utils.input_simulator import (
    mouse_click, get_cursor_pos, set_cursor_pos,
    lock_cursor_to_point, unlock_cursor, play_sound_feedback,
    GlobalHotkeyListener
)
from ..utils.hotkey_widget import HotkeySettingDialog


class ClickerSignals(QObject):
    clicked = pyqtSignal(int, float)  # total_clicks, actual_cps
    started = pyqtSignal()
    stopped = pyqtSignal()


class AutoClickerWorker:
    """Motor de clics en hilo separado para evitar cualquier congelamiento en la UI."""
    def __init__(self, signals: ClickerSignals):
        self.signals = signals
        self.running = False
        self.thread = None

        # Parámetros de clic
        self.mode = "interval"  # "interval" o "cps"
        self.target_cps = 50.0
        self.base_interval_sec = 0.1  # 100 ms por defecto
        self.random_offset_enabled = False
        self.random_offset_ms = 40  # ±40 ms
        self.button = "left"
        self.click_type = "single"  # single, double, triple, hold_down
        self.repeat_mode = "infinite"  # infinite o count
        self.target_count = 1
        self.location_mode = "dynamic"  # dynamic o fixed
        self.fixed_x = 0
        self.fixed_y = 0
        self.lock_cursor = False

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.signals.started.emit()

    def stop(self):
        self.running = False

    def _run(self):
        total_clicks = 0
        start_time = time.perf_counter()
        last_stat_time = start_time
        clicks_in_window = 0

        if self.lock_cursor and self.location_mode == "fixed":
            lock_cursor_to_point(self.fixed_x, self.fixed_y)

        if self.click_type == "hold_down":
            if self.location_mode == "fixed":
                set_cursor_pos(self.fixed_x, self.fixed_y)
            mouse_click(self.button, "hold_down")
            while self.running:
                time.sleep(0.05)
            mouse_click(self.button, "release")
            if self.lock_cursor:
                unlock_cursor()
            self.signals.stopped.emit()
            return

        try:
            while self.running:
                t0 = time.perf_counter()

                cx, cy = (self.fixed_x, self.fixed_y) if self.location_mode == "fixed" else (None, None)

                mouse_click(self.button, self.click_type, cx, cy)
                total_clicks += 1
                clicks_in_window += 1

                now = time.perf_counter()
                if now - last_stat_time >= 0.25:
                    curr_cps = clicks_in_window / (now - last_stat_time)
                    self.signals.clicked.emit(total_clicks, curr_cps)
                    clicks_in_window = 0
                    last_stat_time = now

                if self.repeat_mode == "count" and total_clicks >= self.target_count:
                    break

                if self.mode == "cps":
                    target_delay = 1.0 / max(1.0, float(self.target_cps))
                else:
                    target_delay = self.base_interval_sec

                if self.random_offset_enabled and self.random_offset_ms > 0:
                    offset_sec = random.uniform(-self.random_offset_ms, self.random_offset_ms) / 1000.0
                    target_delay = max(0.001, target_delay + offset_sec)

                elapsed = time.perf_counter() - t0
                sleep_needed = target_delay - elapsed
                if sleep_needed > 0.002:
                    time.sleep(sleep_needed - 0.001)
                while (time.perf_counter() - t0) < target_delay:
                    pass
        finally:
            if self.click_type == "hold_down":
                mouse_click(self.button, "release")
            if self.lock_cursor:
                unlock_cursor()
            self.running = False
            self.signals.stopped.emit()


class TabAutoClicker(QWidget):
    """Interfaz gráfica de Auto Clicker con diseño y funciones completas de OP Auto Clicker 4.0."""
    def __init__(self, parent=None, colores=None, context=None, **kwargs):
        super().__init__(parent)
        self.context = context
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#10B981", "error": "#EF4444",
        }
        self.font_family = "Segoe UI"

        self.signals = ClickerSignals()
        self.worker = AutoClickerWorker(self.signals)

        self.signals.clicked.connect(self._on_click_update)
        self.signals.started.connect(self._on_worker_started)
        self.signals.stopped.connect(self._on_worker_stopped)

        self.hotkey_listener = GlobalHotkeyListener()
        self.current_hotkey = "F6"

        self.picker_timer = QTimer(self)
        self.picker_countdown = 3
        self.picker_timer.timeout.connect(self._actualizar_cuenta_regresiva_picker)

        self._init_ui()
        self._registrar_hotkey(self.current_hotkey)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background-color: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {self.colores['bg_principal']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.colores['bg_terciario']};
                border-radius: 4px;
            }}
        """)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # ── HEADER CON PERFILES & ESTADO ─────────────────────────────────────
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_card.setStyleSheet(f"""
            QFrame#HeaderCard {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        h_lay = QHBoxLayout(header_card)
        h_lay.setContentsMargins(14, 10, 14, 10)

        lbl_title = QLabel("🖱️ Auto Clicker (OP & Speed Edition)")
        lbl_title.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        h_lay.addWidget(lbl_title)

        h_lay.addStretch()

        lbl_preset = QLabel("⚡ Perfil:")
        lbl_preset.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        h_lay.addWidget(lbl_preset)

        self.combo_presets = QComboBox()
        self.combo_presets.addItems([
            "Personalizado",
            "⚔️ Minecraft PvP (16 CPS)",
            "🤖 Roblox AFK (100 ms)",
            "⚡ Ultra Speed (500 CPS)",
            "🎯 Doble Clic Rápido",
            "🖱️ Clic Derecho Spammer"
        ])
        self.combo_presets.setStyleSheet(self._estilo_input())
        self.combo_presets.currentIndexChanged.connect(self._aplicar_preset)
        h_lay.addWidget(self.combo_presets)

        h_lay.addSpacing(10)

        self.lbl_status = QLabel("● DETENIDO")
        self.lbl_status.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(239, 68, 68, 0.15);
            color: {self.colores['error']};
            border: 1px solid {self.colores['error']};
            border-radius: 6px;
            padding: 4px 12px;
        """)
        h_lay.addWidget(self.lbl_status)
        main_layout.addWidget(header_card)

        # ── SECCIÓN 1: CLICK INTERVAL (Idéntico a OP Auto Clicker 4.0) ────────
        card_interval, ci_lay = self._crear_card("Click interval")

        # Fila 1: Horas, Mins, Secs, Milliseconds
        f_row1 = QHBoxLayout()
        f_row1.setSpacing(8)
        self.spin_hours = self._crear_subspin(0, 23, "", val=0, width=70)
        self.spin_mins = self._crear_subspin(0, 59, "", val=0, width=70)
        self.spin_secs = self._crear_subspin(0, 59, "", val=0, width=70)
        self.spin_ms = self._crear_subspin(0, 9999, "", val=100, width=85)

        f_row1.addWidget(self.spin_hours)
        f_row1.addWidget(self._crear_label("hours"))
        f_row1.addSpacing(8)
        f_row1.addWidget(self.spin_mins)
        f_row1.addWidget(self._crear_label("mins"))
        f_row1.addSpacing(8)
        f_row1.addWidget(self.spin_secs)
        f_row1.addWidget(self._crear_label("secs"))
        f_row1.addSpacing(8)
        f_row1.addWidget(self.spin_ms)
        f_row1.addWidget(self._crear_label("milliseconds"))
        f_row1.addStretch()

        # Botón para alternar a Modo CPS Speed
        self.btn_toggle_cps = QPushButton("⚡ Modo CPS")
        self.btn_toggle_cps.setStyleSheet(self._estilo_boton_secundario())
        self.btn_toggle_cps.setCheckable(True)
        self.btn_toggle_cps.toggled.connect(self._on_cps_mode_toggled)
        f_row1.addWidget(self.btn_toggle_cps)

        ci_lay.addLayout(f_row1)

        # Fila CPS Slider (opcional desplegable)
        self.frame_cps_slider = QFrame()
        self.frame_cps_slider.setVisible(False)
        cps_lay = QHBoxLayout(self.frame_cps_slider)
        cps_lay.setContentsMargins(0, 4, 0, 4)
        cps_lay.addWidget(self._crear_label("Velocidad CPS:"))
        self.slider_cps = QSlider(Qt.Orientation.Horizontal)
        self.slider_cps.setRange(1, 500)
        self.slider_cps.setValue(50)
        self.slider_cps.setStyleSheet(self._estilo_slider())
        self.slider_cps.valueChanged.connect(self._on_slider_cps_changed)
        cps_lay.addWidget(self.slider_cps, 1)

        self.spin_cps = QSpinBox()
        self.spin_cps.setRange(1, 2000)
        self.spin_cps.setValue(50)
        self.spin_cps.setSuffix(" CPS")
        self.spin_cps.setStyleSheet(self._estilo_input())
        self.spin_cps.valueChanged.connect(self._on_spin_cps_changed)
        cps_lay.addWidget(self.spin_cps)
        ci_lay.addWidget(self.frame_cps_slider)

        # Fila 2: [ ? ] [ ] Random offset ± [ 40 ] milliseconds
        f_row2 = QHBoxLayout()
        f_row2.setSpacing(8)
        btn_help = QPushButton("?")
        btn_help.setFixedSize(24, 24)
        btn_help.setToolTip("Añade una variación aleatoria en milisegundos a cada clic\npara simular pulsaciones humanas y evitar detección anti-cheat.")
        btn_help.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['acento']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 4px;
                font-weight: bold;
            }}
        """)
        f_row2.addWidget(btn_help)

        self.chk_random_offset = QCheckBox("Random offset ±")
        self.chk_random_offset.setChecked(False)
        self.chk_random_offset.setStyleSheet(f"color: {self.colores['fg_principal']}; font-size: 11px;")
        f_row2.addWidget(self.chk_random_offset)

        self.spin_random_offset = self._crear_subspin(1, 5000, "", val=40, width=80)
        f_row2.addWidget(self.spin_random_offset)
        f_row2.addWidget(self._crear_label("milliseconds"))
        f_row2.addStretch()

        ci_lay.addLayout(f_row2)
        main_layout.addWidget(card_interval)

        # ── SECCIÓN 2 & 3: CLICK OPTIONS & CLICK REPEAT EN 2 COLUMNAS ─────────
        mid_grid = QGridLayout()
        mid_grid.setSpacing(12)

        # CARD B: Click options
        card_options, opt_vbox = self._crear_card("Click options")
        o_lay = QGridLayout()
        o_lay.setSpacing(10)

        o_lay.addWidget(self._crear_label("Mouse button:"), 0, 0)
        self.combo_btn = QComboBox()
        self.combo_btn.addItems(["Left", "Right", "Middle"])
        self.combo_btn.setStyleSheet(self._estilo_input())
        o_lay.addWidget(self.combo_btn, 0, 1)

        o_lay.addWidget(self._crear_label("Click type:"), 1, 0)
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Single", "Double", "Triple", "Hold"])
        self.combo_type.setStyleSheet(self._estilo_input())
        o_lay.addWidget(self.combo_type, 1, 1)

        opt_vbox.addLayout(o_lay)
        mid_grid.addWidget(card_options, 0, 0)

        # CARD C: Click repeat
        card_repeat, rep_lay = self._crear_card("Click repeat")

        r_row1 = QHBoxLayout()
        r_row1.setSpacing(8)
        self.rb_rep_count = QRadioButton("Repeat")
        self.rb_rep_count.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: 500;")
        r_row1.addWidget(self.rb_rep_count)

        self.spin_target_count = self._crear_subspin(1, 1000000, "", val=1, width=90)
        r_row1.addWidget(self.spin_target_count)
        r_row1.addWidget(self._crear_label("times"))
        r_row1.addStretch()
        rep_lay.addLayout(r_row1)

        self.rb_rep_inf = QRadioButton("Repeat until stopped")
        self.rb_rep_inf.setChecked(True)
        self.rb_rep_inf.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: 500;")
        rep_lay.addWidget(self.rb_rep_inf)

        mid_grid.addWidget(card_repeat, 0, 1)
        main_layout.addLayout(mid_grid)

        # ── SECCIÓN 4: CURSOR POSITION ───────────────────────────────────────
        card_pos, pos_vbox = self._crear_card("Cursor position")
        p_lay = QHBoxLayout()
        p_lay.setSpacing(12)

        self.rb_pos_curr = QRadioButton("Current location")
        self.rb_pos_curr.setChecked(True)
        self.rb_pos_curr.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: 500;")
        p_lay.addWidget(self.rb_pos_curr)

        p_lay.addSpacing(16)

        self.rb_pos_fixed = QRadioButton("")
        self.rb_pos_fixed.setStyleSheet("color: white;")
        p_lay.addWidget(self.rb_pos_fixed)

        self.btn_pick_pos = QPushButton("🎯 Pick location")
        self.btn_pick_pos.setStyleSheet(self._estilo_boton_secundario())
        self.btn_pick_pos.clicked.connect(self._iniciar_captura_posicion)
        p_lay.addWidget(self.btn_pick_pos)

        p_lay.addWidget(self._crear_label("X"))
        self.spin_x = self._crear_subspin(0, 9999, "", val=0, width=75)
        p_lay.addWidget(self.spin_x)

        p_lay.addWidget(self._crear_label("Y"))
        self.spin_y = self._crear_subspin(0, 9999, "", val=0, width=75)
        p_lay.addWidget(self.spin_y)

        p_lay.addSpacing(10)

        self.chk_lock_cursor = QCheckBox("Lock cursor")
        self.chk_lock_cursor.setChecked(False)
        self.chk_lock_cursor.setToolTip("Congela el ratón en las coordenadas mientras cliquea.")
        self.chk_lock_cursor.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        p_lay.addWidget(self.chk_lock_cursor)

        p_lay.addStretch()
        pos_vbox.addLayout(p_lay)
        main_layout.addWidget(card_pos)

        # ── SECCIÓN 5: CUADRÍCULA DE ACCIÓN 2x2 (Idéntica a OP Auto Clicker) ──
        grid_actions = QGridLayout()
        grid_actions.setSpacing(10)

        # [ Start (F6) ]
        self.btn_start = QPushButton(f"Start ({self.current_hotkey})")
        self.btn_start.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setFixedHeight(46)
        self.btn_start.setStyleSheet(self._estilo_btn_start(activo=True))
        self.btn_start.clicked.connect(self.start_clicker)
        grid_actions.addWidget(self.btn_start, 0, 0)

        # [ Stop (F6) ]
        self.btn_stop = QPushButton(f"Stop ({self.current_hotkey})")
        self.btn_stop.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setFixedHeight(46)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(self._estilo_btn_stop(activo=False))
        self.btn_stop.clicked.connect(self.stop_clicker)
        grid_actions.addWidget(self.btn_stop, 0, 1)

        # [ Hotkey setting ]
        self.btn_hotkey_setting = QPushButton("Hotkey setting")
        self.btn_hotkey_setting.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_hotkey_setting.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hotkey_setting.setFixedHeight(38)
        self.btn_hotkey_setting.setStyleSheet(self._estilo_boton_cuadricula())
        self.btn_hotkey_setting.clicked.connect(self._abrir_dialogo_hotkey)
        grid_actions.addWidget(self.btn_hotkey_setting, 1, 0)

        # [ Record & Playback ] (usar && para que Qt muestre el carácter & real)
        self.btn_record_playback = QPushButton("Record && Playback")
        self.btn_record_playback.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_record_playback.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_record_playback.setFixedHeight(38)
        self.btn_record_playback.setStyleSheet(self._estilo_boton_cuadricula())
        self.btn_record_playback.clicked.connect(self._abrir_record_playback)
        grid_actions.addWidget(self.btn_record_playback, 1, 1)

        main_layout.addLayout(grid_actions)

        # ── BARRA INFERIOR DE ESTADO Y AJUSTES EXTRA ─────────────────────────
        footer = QFrame()
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(4, 0, 4, 0)

        self.chk_sound = QCheckBox("Sonido Beep")
        self.chk_sound.setChecked(True)
        self.chk_sound.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        footer_lay.addWidget(self.chk_sound)

        self.chk_minimize = QCheckBox("Minimizar al iniciar")
        self.chk_minimize.setChecked(False)
        self.chk_minimize.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        footer_lay.addWidget(self.chk_minimize)

        footer_lay.addStretch()

        self.lbl_stats_clicks = QLabel("Clics: 0")
        self.lbl_stats_cps = QLabel("CPS: 0.0")
        self.lbl_stats_pos = QLabel("Ratón: X=0, Y=0")

        for lbl in (self.lbl_stats_clicks, self.lbl_stats_cps, self.lbl_stats_pos):
            lbl.setFont(QFont(self.font_family, 9))
            lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
            footer_lay.addWidget(lbl)

        btn_reset_stats = QPushButton("🔄")
        btn_reset_stats.setToolTip("Reiniciar contador")
        btn_reset_stats.setStyleSheet(self._estilo_boton_secundario())
        btn_reset_stats.clicked.connect(self._reset_stats)
        footer_lay.addWidget(btn_reset_stats)

        main_layout.addWidget(footer)
        main_layout.addStretch()

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

        # Timer de coordenadas
        self.mouse_pos_timer = QTimer(self)
        self.mouse_pos_timer.timeout.connect(self._actualizar_mouse_pos_label)
        self.mouse_pos_timer.start(100)

    # ── ESTILOS Y CONSTRUCTORES DE TARJETAS ──────────────────────────────────
    def _crear_card(self, titulo: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("AutoCardFrame")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.setStyleSheet(f"""
            QFrame#AutoCardFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        lbl = QLabel(titulo)
        lbl.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        lay.addWidget(lbl)
        return card, lay

    def _crear_label(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent; font-size: 11px;")
        return lbl

    def _crear_subspin(self, minimo: int, maximo: int, suffix: str, val: int = 0, width: int = 75) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimo, maximo)
        spin.setValue(val)
        spin.setSuffix(suffix)
        spin.setMinimumWidth(width)
        spin.setStyleSheet(self._estilo_input())
        return spin

    def _estilo_input(self) -> str:
        return f"""
            QSpinBox, QComboBox {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 11px;
            }}
            QSpinBox:focus, QComboBox:focus {{
                border: 1px solid {self.colores['acento']};
            }}
        """

    def _estilo_btn_start(self, activo: bool) -> str:
        if activo:
            return f"""
                QPushButton {{
                    background-color: {self.colores['exito']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px;
                }}
                QPushButton:hover {{ background-color: #059669; }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.04);
                    color: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                    padding: 8px;
                }}
            """

    def _estilo_btn_stop(self, activo: bool) -> str:
        if activo:
            return f"""
                QPushButton {{
                    background-color: {self.colores['error']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px;
                }}
                QPushButton:hover {{ background-color: #DC2626; }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.04);
                    color: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                    padding: 8px;
                }}
            """

    def _estilo_boton_cuadricula(self) -> str:
        return f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: rgba(99, 102, 241, 0.2);
                border: 1px solid {self.colores['acento']};
                color: white;
            }}
        """

    def _estilo_boton_secundario(self) -> str:
        return f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.15); }}
        """

    def _estilo_slider(self) -> str:
        return f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: {self.colores['bg_terciario']};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.colores['acento']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: #FFFFFF;
                border: 1px solid {self.colores['acento']};
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }}
        """

    # ── ACCIONES Y LOGICA ────────────────────────────────────────────────────
    def _on_cps_mode_toggled(self, checked: bool):
        self.frame_cps_slider.setVisible(checked)
        if checked:
            self.worker.mode = "cps"
            self.btn_toggle_cps.setText("⏱️ Modo Intervalo")
        else:
            self.worker.mode = "interval"
            self.btn_toggle_cps.setText("⚡ Modo CPS")

    def _on_slider_cps_changed(self, val: int):
        self.spin_cps.blockSignals(True)
        self.spin_cps.setValue(val)
        self.spin_cps.blockSignals(False)

    def _on_spin_cps_changed(self, val: int):
        self.slider_cps.blockSignals(True)
        self.slider_cps.setValue(min(val, self.slider_cps.maximum()))
        self.slider_cps.blockSignals(False)

    def _aplicar_preset(self, index: int):
        if index == 0:
            return
        elif index == 1:  # Minecraft PvP 16 CPS
            self.spin_hours.setValue(0)
            self.spin_mins.setValue(0)
            self.spin_secs.setValue(0)
            self.spin_ms.setValue(62)
            self.chk_random_offset.setChecked(True)
            self.spin_random_offset.setValue(10)
            self.combo_btn.setCurrentText("Left")
            self.combo_type.setCurrentText("Single")
            self.rb_pos_curr.setChecked(True)
        elif index == 2:  # Roblox AFK 100 ms
            self.spin_hours.setValue(0)
            self.spin_mins.setValue(0)
            self.spin_secs.setValue(0)
            self.spin_ms.setValue(100)
            self.chk_random_offset.setChecked(False)
            self.combo_btn.setCurrentText("Left")
            self.combo_type.setCurrentText("Single")
            self.rb_pos_curr.setChecked(True)
        elif index == 3:  # Ultra Speed 500 CPS
            self.btn_toggle_cps.setChecked(True)
            self.spin_cps.setValue(500)
            self.combo_btn.setCurrentText("Left")
            self.combo_type.setCurrentText("Single")
        elif index == 4:  # Doble Clic
            self.spin_ms.setValue(80)
            self.combo_type.setCurrentText("Double")
        elif index == 5:  # Clic Derecho Spammer
            self.spin_ms.setValue(50)
            self.combo_btn.setCurrentText("Right")
            self.combo_type.setCurrentText("Single")

    def _iniciar_captura_posicion(self):
        self.rb_pos_fixed.setChecked(True)
        self.picker_countdown = 3
        self.btn_pick_pos.setText(f"Coloca el ratón ({self.picker_countdown}s)...")
        self.btn_pick_pos.setEnabled(False)
        self.picker_timer.start(1000)

    def _actualizar_cuenta_regresiva_picker(self):
        self.picker_countdown -= 1
        if self.picker_countdown > 0:
            self.btn_pick_pos.setText(f"Coloca el ratón ({self.picker_countdown}s)...")
        else:
            self.picker_timer.stop()
            x, y = get_cursor_pos()
            self.spin_x.setValue(x)
            self.spin_y.setValue(y)
            self.btn_pick_pos.setText("✓ Posición fijada")
            self.btn_pick_pos.setEnabled(True)
            QTimer.singleShot(2000, lambda: self.btn_pick_pos.setText("🎯 Pick location"))

    def _abrir_dialogo_hotkey(self):
        dlg = HotkeySettingDialog(
            current_key=self.current_hotkey,
            listener=self.hotkey_listener,
            colores=self.colores,
            parent=self
        )
        if dlg.exec():
            self._registrar_hotkey(dlg.selected_key)

    def _abrir_record_playback(self):
        """Salta directamente al submódulo Grabador de Macros en la suite."""
        p = self.parentWidget()
        while p:
            if hasattr(p, "tabs"):
                p.tabs.setCurrentIndex(2)
                break
            p = p.parentWidget()

    def _actualizar_mouse_pos_label(self):
        x, y = get_cursor_pos()
        self.lbl_stats_pos.setText(f"Ratón: X={x}, Y={y}")

    def _reset_stats(self):
        self.lbl_stats_clicks.setText("Clics: 0")
        self.lbl_stats_cps.setText("CPS: 0.0")

    def _registrar_hotkey(self, hotkey_name: str):
        if self.current_hotkey:
            self.hotkey_listener.unregister_hotkey(self.current_hotkey)
        self.current_hotkey = hotkey_name
        self.btn_start.setText(f"Start ({hotkey_name})")
        self.btn_stop.setText(f"Stop ({hotkey_name})")
        self.hotkey_listener.register_hotkey(hotkey_name, on_down=self._on_hotkey_toggle, on_up=None)

    def _on_hotkey_toggle(self):
        if self.worker.running:
            self.stop_clicker()
        else:
            self.start_clicker()

    def start_clicker(self):
        if self.worker.running:
            return
        self._aplicar_configuracion()
        self.worker.start()

    def stop_clicker(self):
        if not self.worker.running:
            return
        self.worker.stop()

    def _aplicar_configuracion(self):
        if self.btn_toggle_cps.isChecked():
            self.worker.mode = "cps"
            self.worker.target_cps = float(self.spin_cps.value())
        else:
            self.worker.mode = "interval"
            total_sec = (
                self.spin_hours.value() * 3600 +
                self.spin_mins.value() * 60 +
                self.spin_secs.value() +
                self.spin_ms.value() / 1000.0
            )
            self.worker.base_interval_sec = max(0.001, total_sec)

        self.worker.random_offset_enabled = self.chk_random_offset.isChecked()
        self.worker.random_offset_ms = self.spin_random_offset.value()

        btn_txt = self.combo_btn.currentText().lower()
        self.worker.button = btn_txt if btn_txt in ("left", "right", "middle") else "left"

        type_txt = self.combo_type.currentText().lower()
        if "single" in type_txt:
            self.worker.click_type = "single"
        elif "double" in type_txt:
            self.worker.click_type = "double"
        elif "triple" in type_txt:
            self.worker.click_type = "triple"
        else:
            self.worker.click_type = "hold_down"

        if self.rb_pos_fixed.isChecked():
            self.worker.location_mode = "fixed"
            self.worker.fixed_x = self.spin_x.value()
            self.worker.fixed_y = self.spin_y.value()
        else:
            self.worker.location_mode = "dynamic"

        if self.rb_rep_count.isChecked():
            self.worker.repeat_mode = "count"
            self.worker.target_count = self.spin_target_count.value()
        else:
            self.worker.repeat_mode = "infinite"

        self.worker.lock_cursor = self.chk_lock_cursor.isChecked()

    def _on_worker_started(self):
        self.lbl_status.setText("● EN EJECUCIÓN")
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(16, 185, 129, 0.15);
            color: {self.colores['exito']};
            border: 1px solid {self.colores['exito']};
            border-radius: 6px;
            padding: 4px 12px;
        """)

        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet(self._estilo_btn_start(activo=False))

        self.btn_stop.setEnabled(True)
        self.btn_stop.setStyleSheet(self._estilo_btn_stop(activo=True))

        if self.chk_sound.isChecked():
            play_sound_feedback("start")

        if self.chk_minimize.isChecked():
            top = self.window()
            if top:
                top.showMinimized()

    def _on_worker_stopped(self):
        self.lbl_status.setText("● DETENIDO")
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(239, 68, 68, 0.15);
            color: {self.colores['error']};
            border: 1px solid {self.colores['error']};
            border-radius: 6px;
            padding: 4px 12px;
        """)

        self.btn_start.setEnabled(True)
        self.btn_start.setStyleSheet(self._estilo_btn_start(activo=True))

        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(self._estilo_btn_stop(activo=False))

        if self.chk_sound.isChecked():
            play_sound_feedback("stop")

    def _on_click_update(self, total_clicks: int, actual_cps: float):
        self.lbl_stats_clicks.setText(f"Clics: {total_clicks:,}")
        self.lbl_stats_cps.setText(f"CPS: {actual_cps:.1f}")

    def cleanup(self):
        if hasattr(self, "worker") and self.worker.running:
            self.worker.stop()
        unlock_cursor()
        if hasattr(self, "hotkey_listener"):
            self.hotkey_listener.stop()
        if hasattr(self, "mouse_pos_timer"):
            self.mouse_pos_timer.stop()
