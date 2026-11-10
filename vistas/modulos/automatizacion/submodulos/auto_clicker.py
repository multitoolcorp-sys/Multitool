"""
auto_clicker.py - Submódulo Pro de Auto Clicker de Alta Velocidad (Speed & OP AutoClicker).
Cuenta con 2 botones separados para Iniciar y Detener (evita clics accidentales),
atajo interactivo, perfiles/presets preconfigurados, bloqueo de cursor, jitter y modo hold-to-click.
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
from PyQt6.QtGui import QFont, QColor

from ..utils.input_simulator import (
    mouse_click, get_cursor_pos, set_cursor_pos,
    lock_cursor_to_point, unlock_cursor, play_sound_feedback,
    GlobalHotkeyListener, VK_MAP
)
from ..utils.hotkey_widget import HotkeyCaptureButton

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
        self.mode = "cps"  # "cps" o "interval"
        self.target_cps = 50.0
        self.interval_sec = 0.02
        self.button = "left"
        self.click_type = "single"  # single, double, triple, hold_down
        self.repeat_mode = "infinite"  # infinite o count
        self.target_count = 100
        self.location_mode = "dynamic"  # dynamic o fixed
        self.fixed_x = 0
        self.fixed_y = 0
        self.jitter_enabled = False
        self.jitter_radius = 5  # pixels
        self.jitter_time_pct = 15  # %
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

        # Bloquear cursor si está habilitado en modo coordenadas fijas
        if self.lock_cursor and self.location_mode == "fixed":
            lock_cursor_to_point(self.fixed_x, self.fixed_y)

        # Manejo especial de Modo Mantener Presionado (Hold Mouse Button)
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

        # Calcular delay base
        if self.mode == "cps":
            base_delay = 1.0 / max(1.0, float(self.target_cps))
        else:
            base_delay = max(0.001, self.interval_sec)

        try:
            while self.running:
                t0 = time.perf_counter()

                # Coordenadas con dispersión opcional
                cx, cy = None, None
                if self.location_mode == "fixed":
                    cx, cy = self.fixed_x, self.fixed_y
                    if self.jitter_enabled and self.jitter_radius > 0:
                        cx += random.randint(-self.jitter_radius, self.jitter_radius)
                        cy += random.randint(-self.jitter_radius, self.jitter_radius)
                elif self.jitter_enabled and self.jitter_radius > 0:
                    curr_x, curr_y = get_cursor_pos()
                    cx = curr_x + random.randint(-self.jitter_radius, self.jitter_radius)
                    cy = curr_y + random.randint(-self.jitter_radius, self.jitter_radius)

                # Ejecutar Clic
                mouse_click(self.button, self.click_type, cx, cy)
                total_clicks += 1
                clicks_in_window += 1

                # Actualización periódica de estadísticas (cada 250ms)
                now = time.perf_counter()
                if now - last_stat_time >= 0.25:
                    curr_cps = clicks_in_window / (now - last_stat_time)
                    self.signals.clicked.emit(total_clicks, curr_cps)
                    clicks_in_window = 0
                    last_stat_time = now

                # Comprobar límite de repeticiones
                if self.repeat_mode == "count" and total_clicks >= self.target_count:
                    break

                # Intervalo con factor de jitter aleatorio opcional
                target_delay = base_delay
                if self.jitter_enabled and self.jitter_time_pct > 0:
                    var = self.jitter_time_pct / 100.0
                    target_delay *= random.uniform(1.0 - var, 1.0 + var)

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
    """Interfaz gráfica responsiva para el Auto Clicker Pro con 2 botones de acción independientes."""
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

        # Hotkey global interactivo (F6 por defecto)
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

        # Área de Scroll Responsiva
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
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # ── 1. HEADER CARD ───────────────────────────────────────────────────
        header_card = QFrame()
        header_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        h_lay = QHBoxLayout(header_card)
        h_lay.setContentsMargins(10, 6, 10, 6)

        lbl_title = QLabel("🖱️ Auto Clicker Pro (Speed & OP)")
        lbl_title.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none;")
        h_lay.addWidget(lbl_title)

        h_lay.addStretch()

        # Selector de Presets Rápidos
        lbl_preset = QLabel("⚡ Perfil:")
        lbl_preset.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        h_lay.addWidget(lbl_preset)

        self.combo_presets = QComboBox()
        self.combo_presets.addItems([
            "Personalizado",
            "⚔️ Minecraft PvP (16 CPS)",
            "🤖 Roblox AFK (5 CPS)",
            "⚡ Ultra Speed (500 CPS)",
            "🎯 Doble Clic Rápido (12 CPS)",
            "🖱️ Clic Derecho Spammer (20 CPS)",
            "⛏️ Modo Minero (Hold)"
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

        # ── 2. GRID DE CONFIGURACIÓN ───────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(12)

        # CARD A: Frecuencia / CPS
        card_freq = self._crear_card("⚡ Frecuencia y Velocidad de Clic")
        f_lay = QVBoxLayout(card_freq)

        r_box = QHBoxLayout()
        self.rb_mode_cps = QRadioButton("Modo CPS (Clicks por Segundo)")
        self.rb_mode_interval = QRadioButton("Modo Intervalo (Tiempo exacto)")
        self.rb_mode_cps.setChecked(True)
        self.rb_mode_cps.toggled.connect(self._on_mode_toggled)

        for rb in (self.rb_mode_cps, self.rb_mode_interval):
            rb.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: 500;")
            r_box.addWidget(rb)
        f_lay.addLayout(r_box)

        # Controles Modo CPS
        self.frame_cps = QFrame()
        cps_lay = QHBoxLayout(self.frame_cps)
        cps_lay.setContentsMargins(0, 4, 0, 4)

        lbl_cps = QLabel("Velocidad:")
        lbl_cps.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        cps_lay.addWidget(lbl_cps)

        self.slider_cps = QSlider(Qt.Orientation.Horizontal)
        self.slider_cps.setRange(1, 500)
        self.slider_cps.setValue(50)
        self.slider_cps.setStyleSheet(f"""
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
        """)
        self.slider_cps.valueChanged.connect(self._on_slider_cps_changed)
        cps_lay.addWidget(self.slider_cps, 1)

        self.spin_cps = QSpinBox()
        self.spin_cps.setRange(1, 2000)
        self.spin_cps.setValue(50)
        self.spin_cps.setSuffix(" CPS")
        self.spin_cps.setStyleSheet(self._estilo_input())
        self.spin_cps.valueChanged.connect(self._on_spin_cps_changed)
        cps_lay.addWidget(self.spin_cps)
        f_lay.addWidget(self.frame_cps)

        # Controles Modo Intervalo
        self.frame_interval = QFrame()
        self.frame_interval.setVisible(False)
        int_lay = QHBoxLayout(self.frame_interval)
        int_lay.setContentsMargins(0, 4, 0, 4)

        self.spin_hours = self._crear_subspin(0, 23, " h")
        self.spin_mins = self._crear_subspin(0, 59, " m")
        self.spin_secs = self._crear_subspin(0, 59, " s")
        self.spin_ms = self._crear_subspin(1, 9999, " ms", val=20)

        int_lay.addWidget(QLabel("H:"))
        int_lay.addWidget(self.spin_hours)
        int_lay.addWidget(QLabel("M:"))
        int_lay.addWidget(self.spin_mins)
        int_lay.addWidget(QLabel("S:"))
        int_lay.addWidget(self.spin_secs)
        int_lay.addWidget(QLabel("MS:"))
        int_lay.addWidget(self.spin_ms)
        f_lay.addWidget(self.frame_interval)

        grid.addWidget(card_freq, 0, 0)

        # CARD B: Opciones de Clic
        card_options = self._crear_card("🖱️ Tipo y Botón de Clic")
        o_lay = QGridLayout(card_options)
        o_lay.setSpacing(8)

        o_lay.addWidget(self._crear_label("Botón del Ratón:"), 0, 0)
        self.combo_btn = QComboBox()
        self.combo_btn.addItems(["Izquierdo (Left)", "Derecho (Right)", "Central (Middle)"])
        self.combo_btn.setStyleSheet(self._estilo_input())
        o_lay.addWidget(self.combo_btn, 0, 1)

        o_lay.addWidget(self._crear_label("Tipo de Clic:"), 1, 0)
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Simple (1x)", "Doble (2x)", "Triple (3x)", "Mantener Presionado (Hold)"])
        self.combo_type.setStyleSheet(self._estilo_input())
        o_lay.addWidget(self.combo_type, 1, 1)

        grid.addWidget(card_options, 0, 1)

        # CARD C: Posición del Cursor
        card_pos = self._crear_card("🎯 Ubicación del Clic")
        p_lay = QVBoxLayout(card_pos)

        self.rb_pos_curr = QRadioButton("Posición actual del ratón (Sigue al cursor)")
        self.rb_pos_fixed = QRadioButton("Coordenadas fijas en pantalla (X, Y)")
        self.rb_pos_curr.setChecked(True)
        self.rb_pos_curr.toggled.connect(self._on_pos_mode_toggled)

        for rb in (self.rb_pos_curr, self.rb_pos_fixed):
            rb.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: 500;")
            p_lay.addWidget(rb)

        self.frame_fixed_coords = QFrame()
        self.frame_fixed_coords.setVisible(False)
        fc_lay = QHBoxLayout(self.frame_fixed_coords)
        fc_lay.setContentsMargins(0, 4, 0, 4)

        fc_lay.addWidget(QLabel("X:"))
        self.spin_x = self._crear_subspin(0, 9999, "", val=500)
        fc_lay.addWidget(self.spin_x)

        fc_lay.addWidget(QLabel("Y:"))
        self.spin_y = self._crear_subspin(0, 9999, "", val=500)
        fc_lay.addWidget(self.spin_y)

        self.btn_pick_pos = QPushButton("📍 Capturar en 3s")
        self.btn_pick_pos.setStyleSheet(self._estilo_boton_secundario())
        self.btn_pick_pos.clicked.connect(self._iniciar_captura_posicion)
        fc_lay.addWidget(self.btn_pick_pos)

        p_lay.addWidget(self.frame_fixed_coords)

        self.chk_lock_cursor = QCheckBox("Bloquear cursor en coordenadas mientras cliquea")
        self.chk_lock_cursor.setChecked(False)
        self.chk_lock_cursor.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        p_lay.addWidget(self.chk_lock_cursor)

        grid.addWidget(card_pos, 1, 0)

        # CARD D: Repetición y Límites
        card_repeat = self._crear_card("🔁 Repetición y Disparo")
        rep_lay = QVBoxLayout(card_repeat)

        # Modo de activación (Toggle vs Hold-to-Click)
        act_box = QHBoxLayout()
        self.rb_act_toggle = QRadioButton("Alternar (Toggle on/off)")
        self.rb_act_hold = QRadioButton("Mantener (Hold-to-Click)")
        self.rb_act_toggle.setChecked(True)
        self.rb_act_toggle.toggled.connect(self._on_activation_mode_changed)

        for rb in (self.rb_act_toggle, self.rb_act_hold):
            rb.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: 500;")
            act_box.addWidget(rb)
        rep_lay.addLayout(act_box)

        self.rb_rep_inf = QRadioButton("Repetir indefinidamente")
        self.rb_rep_count = QRadioButton("Repetir cantidad fija")
        self.rb_rep_inf.setChecked(True)
        self.rb_rep_count.toggled.connect(self._on_repeat_mode_toggled)

        for rb in (self.rb_rep_inf, self.rb_rep_count):
            rb.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: 500;")
            rep_lay.addWidget(rb)

        self.frame_rep_count = QFrame()
        self.frame_rep_count.setVisible(False)
        rc_lay = QHBoxLayout(self.frame_rep_count)
        rc_lay.setContentsMargins(0, 4, 0, 4)
        rc_lay.addWidget(QLabel("Cantidad:"))
        self.spin_target_count = self._crear_subspin(1, 1000000, " clics", val=100)
        rc_lay.addWidget(self.spin_target_count)
        rep_lay.addWidget(self.frame_rep_count)

        grid.addWidget(card_repeat, 1, 1)

        # CARD E: Opciones Pro Anti-Detección, Sonido y Ventana
        card_extra = self._crear_card("🛡️ Opciones Adicionales Pro")
        ex_lay = QHBoxLayout(card_extra)
        ex_lay.setSpacing(12)

        self.chk_jitter = QCheckBox("Dispersión aleatoria (Jitter)")
        self.chk_jitter.setChecked(False)
        self.chk_jitter.setStyleSheet(f"color: {self.colores['fg_principal']}; font-size: 11px;")
        ex_lay.addWidget(self.chk_jitter)

        ex_lay.addWidget(QLabel("Radio:"))
        self.spin_jitter_rad = self._crear_subspin(1, 50, " px", val=5)
        ex_lay.addWidget(self.spin_jitter_rad)

        ex_lay.addWidget(QLabel("Jitter %:"))
        self.spin_jitter_time = self._crear_subspin(5, 50, " %", val=15)
        ex_lay.addWidget(self.spin_jitter_time)

        self.chk_sound = QCheckBox("Sonido Beep")
        self.chk_sound.setChecked(True)
        self.chk_sound.setStyleSheet(f"color: {self.colores['fg_principal']}; font-size: 11px;")
        ex_lay.addWidget(self.chk_sound)

        self.chk_minimize = QCheckBox("Minimizar al iniciar")
        self.chk_minimize.setChecked(False)
        self.chk_minimize.setStyleSheet(f"color: {self.colores['fg_principal']}; font-size: 11px;")
        ex_lay.addWidget(self.chk_minimize)

        ex_lay.addStretch()
        grid.addWidget(card_extra, 2, 0, 1, 2)
        main_layout.addLayout(grid)

        # ── 3. CONTROLES DE ACCIÓN CON 2 BOTONES INDEPENDIENTES ───────────────
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        c_lay = QHBoxLayout(ctrl_card)
        c_lay.setSpacing(12)

        # Selector de Atajo
        hk_box = QVBoxLayout()
        lbl_hk = QLabel("Atajo Teclado:")
        lbl_hk.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        hk_box.addWidget(lbl_hk)

        self.btn_hotkey = HotkeyCaptureButton(
            default_key="F6",
            listener=self.hotkey_listener,
            colores=self.colores,
            parent=self
        )
        self.btn_hotkey.hotkey_changed.connect(self._on_hotkey_captured)
        hk_box.addWidget(self.btn_hotkey)
        c_lay.addLayout(hk_box)

        c_lay.addSpacing(6)

        # BOTÓN 1: INICIAR (Habilitado cuando está detenido, se apaga al hacer clic)
        self.btn_start = QPushButton(f"▶ INICIAR ({self.current_hotkey})")
        self.btn_start.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setFixedHeight(48)
        self.btn_start.setStyleSheet(self._estilo_btn_iniciar(habilitado=True))
        self.btn_start.clicked.connect(self.start_clicker)
        c_lay.addWidget(self.btn_start, 1)

        # BOTÓN 2: DETENER (Deshabilitado cuando está detenido, se enciende al iniciar)
        self.btn_stop = QPushButton(f"⏹ DETENER ({self.current_hotkey})")
        self.btn_stop.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setFixedHeight(48)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(self._estilo_btn_detener(habilitado=False))
        self.btn_stop.clicked.connect(self.stop_clicker)
        c_lay.addWidget(self.btn_stop, 1)

        main_layout.addWidget(ctrl_card)

        # ── 4. BARRA DE ESTADÍSTICAS EN VIVO ──────────────────────────────────
        stats_frame = QFrame()
        stats_lay = QHBoxLayout(stats_frame)
        stats_lay.setContentsMargins(10, 0, 10, 0)

        self.lbl_stats_clicks = QLabel("Clics: 0")
        self.lbl_stats_cps = QLabel("CPS Real: 0.0")
        self.lbl_stats_pos = QLabel("Ratón: X=0, Y=0")

        for lbl in (self.lbl_stats_clicks, self.lbl_stats_cps, self.lbl_stats_pos):
            lbl.setFont(QFont(self.font_family, 9))
            lbl.setStyleSheet(f"color: {self.colores['fg_secundario']};")
            stats_lay.addWidget(lbl)

        btn_reset_stats = QPushButton("🔄 Reiniciar Contador")
        btn_reset_stats.setStyleSheet(self._estilo_boton_secundario())
        btn_reset_stats.clicked.connect(self._reset_stats)
        stats_lay.addWidget(btn_reset_stats)

        main_layout.addWidget(stats_frame)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

        # Timer para actualizar posición del cursor en barra de estado
        self.mouse_pos_timer = QTimer(self)
        self.mouse_pos_timer.timeout.connect(self._actualizar_mouse_pos_label)
        self.mouse_pos_timer.start(100)

    # ── HELPERS DE ESTILO Y UI ───────────────────────────────────────────────
    def _crear_card(self, titulo: str) -> QFrame:
        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        lbl = QLabel(titulo)
        lbl.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {self.colores['acento']}; border: none; margin-bottom: 4px;")
        card.layout = QVBoxLayout(card)
        card.layout.addWidget(lbl)
        return card

    def _crear_label(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        return lbl

    def _crear_subspin(self, minimo: int, maximo: int, suffix: str, val: int = 0) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimo, maximo)
        spin.setValue(val)
        spin.setSuffix(suffix)
        spin.setStyleSheet(self._estilo_input())
        return spin

    def _estilo_input(self) -> str:
        return f"""
            QSpinBox, QComboBox {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QSpinBox:focus, QComboBox:focus {{
                border: 1px solid {self.colores['acento']};
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
                selection-background-color: {self.colores['acento']};
            }}
        """

    def _estilo_btn_iniciar(self, habilitado: bool) -> str:
        if habilitado:
            return f"""
                QPushButton {{
                    background-color: {self.colores['exito']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px;
                }}
                QPushButton:hover {{
                    background-color: #059669;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.05);
                    color: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                    padding: 8px;
                }}
            """

    def _estilo_btn_detener(self, habilitado: bool) -> str:
        if habilitado:
            return f"""
                QPushButton {{
                    background-color: {self.colores['error']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px;
                }}
                QPushButton:hover {{
                    background-color: #DC2626;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.05);
                    color: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                    padding: 8px;
                }}
            """

    def _estilo_boton_secundario(self) -> str:
        return f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 10px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
        """

    # ── GESTIÓN DE EVENTOS Y PRESETS ─────────────────────────────────────────
    def _aplicar_preset(self, index: int):
        if index == 0:
            return  # Personalizado
        elif index == 1:  # Minecraft PvP 16 CPS
            self.rb_mode_cps.setChecked(True)
            self.spin_cps.setValue(16)
            self.combo_btn.setCurrentIndex(0)
            self.combo_type.setCurrentIndex(0)
            self.rb_pos_curr.setChecked(True)
            self.chk_jitter.setChecked(True)
            self.spin_jitter_rad.setValue(3)
        elif index == 2:  # Roblox AFK 5 CPS
            self.rb_mode_cps.setChecked(True)
            self.spin_cps.setValue(5)
            self.combo_btn.setCurrentIndex(0)
            self.combo_type.setCurrentIndex(0)
            self.rb_pos_curr.setChecked(True)
            self.chk_jitter.setChecked(False)
        elif index == 3:  # Ultra Speed 500 CPS
            self.rb_mode_cps.setChecked(True)
            self.spin_cps.setValue(500)
            self.combo_btn.setCurrentIndex(0)
            self.combo_type.setCurrentIndex(0)
        elif index == 4:  # Doble Clic 12 CPS
            self.rb_mode_cps.setChecked(True)
            self.spin_cps.setValue(12)
            self.combo_btn.setCurrentIndex(0)
            self.combo_type.setCurrentIndex(1)
        elif index == 5:  # Clic Derecho Spammer 20 CPS
            self.rb_mode_cps.setChecked(True)
            self.spin_cps.setValue(20)
            self.combo_btn.setCurrentIndex(1)
            self.combo_type.setCurrentIndex(0)
        elif index == 6:  # Modo Minero Hold
            self.combo_btn.setCurrentIndex(0)
            self.combo_type.setCurrentIndex(3)

    def _on_mode_toggled(self, checked: bool):
        self.frame_cps.setVisible(self.rb_mode_cps.isChecked())
        self.frame_interval.setVisible(self.rb_mode_interval.isChecked())

    def _on_activation_mode_changed(self, checked: bool):
        self._registrar_hotkey(self.current_hotkey)

    def _on_slider_cps_changed(self, val: int):
        self.spin_cps.blockSignals(True)
        self.spin_cps.setValue(val)
        self.spin_cps.blockSignals(False)

    def _on_spin_cps_changed(self, val: int):
        self.slider_cps.blockSignals(True)
        self.slider_cps.setValue(min(val, self.slider_cps.maximum()))
        self.slider_cps.blockSignals(False)

    def _on_pos_mode_toggled(self, checked: bool):
        self.frame_fixed_coords.setVisible(self.rb_pos_fixed.isChecked())

    def _on_repeat_mode_toggled(self, checked: bool):
        self.frame_rep_count.setVisible(self.rb_rep_count.isChecked())

    def _iniciar_captura_posicion(self):
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
            self.btn_pick_pos.setText("✓ ¡Posición Fijada!")
            self.btn_pick_pos.setEnabled(True)
            QTimer.singleShot(2000, lambda: self.btn_pick_pos.setText("📍 Capturar en 3s"))

    def _actualizar_mouse_pos_label(self):
        x, y = get_cursor_pos()
        self.lbl_stats_pos.setText(f"Ratón: X={x}, Y={y}")

    def _reset_stats(self):
        self.lbl_stats_clicks.setText("Clics: 0")
        self.lbl_stats_cps.setText("CPS Real: 0.0")

    def _on_hotkey_captured(self, new_hk: str, vk: int):
        self._registrar_hotkey(new_hk)

    def _registrar_hotkey(self, hotkey_name: str):
        if self.current_hotkey:
            self.hotkey_listener.unregister_hotkey(self.current_hotkey)
        self.current_hotkey = hotkey_name
        self.btn_start.setText(f"▶ INICIAR ({hotkey_name})")
        self.btn_stop.setText(f"⏹ DETENER ({hotkey_name})")

        if self.rb_act_toggle.isChecked():
            # Modo Toggle: presionar tecla alterna on/off
            self.hotkey_listener.register_hotkey(hotkey_name, on_down=self._on_hotkey_toggle, on_up=None)
        else:
            # Modo Hold-to-Click: presionar tecla inicia, soltarla detiene
            self.hotkey_listener.register_hotkey(hotkey_name, on_down=self.start_clicker, on_up=self.stop_clicker)

    def _on_hotkey_toggle(self):
        if self.worker.running:
            self.stop_clicker()
        else:
            self.start_clicker()

    def start_clicker(self):
        """Inicia el autoclicker: apaga el botón de inicio y enciende el de parada."""
        if self.worker.running:
            return
        self._aplicar_configuracion_al_worker()
        self.worker.start()

    def stop_clicker(self):
        """Detiene el autoclicker: apaga el botón de parada y enciende el de inicio."""
        if not self.worker.running:
            return
        self.worker.stop()

    def _aplicar_configuracion_al_worker(self):
        if self.rb_mode_cps.isChecked():
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
            self.worker.interval_sec = max(0.001, total_sec)

        btn_idx = self.combo_btn.currentIndex()
        self.worker.button = "left" if btn_idx == 0 else ("right" if btn_idx == 1 else "middle")

        type_idx = self.combo_type.currentIndex()
        if type_idx == 0:
            self.worker.click_type = "single"
        elif type_idx == 1:
            self.worker.click_type = "double"
        elif type_idx == 2:
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

        self.worker.jitter_enabled = self.chk_jitter.isChecked()
        self.worker.jitter_radius = self.spin_jitter_rad.value()
        self.worker.jitter_time_pct = self.spin_jitter_time.value()
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

        # Separación clara de 2 botones: apagar Iniciar y encender Detener
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet(self._estilo_btn_iniciar(habilitado=False))

        self.btn_stop.setEnabled(True)
        self.btn_stop.setStyleSheet(self._estilo_btn_detener(habilitado=True))

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

        # Separación clara de 2 botones: encender Iniciar y apagar Detener
        self.btn_start.setEnabled(True)
        self.btn_start.setStyleSheet(self._estilo_btn_iniciar(habilitado=True))

        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(self._estilo_btn_detener(habilitado=False))

        if self.chk_sound.isChecked():
            play_sound_feedback("stop")

    def _on_click_update(self, total_clicks: int, actual_cps: float):
        self.lbl_stats_clicks.setText(f"Clics: {total_clicks:,}")
        self.lbl_stats_cps.setText(f"CPS Real: {actual_cps:.1f}")

    def cleanup(self):
        """Detiene listeners e hilos al cerrar la aplicación."""
        if hasattr(self, "worker") and self.worker.running:
            self.worker.stop()
        unlock_cursor()
        if hasattr(self, "hotkey_listener"):
            self.hotkey_listener.stop()
        if hasattr(self, "mouse_pos_timer"):
            self.mouse_pos_timer.stop()
