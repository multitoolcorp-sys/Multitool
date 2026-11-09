"""
auto_clicker.py - Submódulo Pro de Auto Clicker de Alta Velocidad (Speed & OP AutoClicker).
Soporta desde 1 hasta más de 1000 CPS, clic simple/doble/triple, posición fija o dinámica,
y atajo global de teclado (F6) que funciona incluso con Multitool en segundo plano.
"""

import time
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QRadioButton, QButtonGroup, QSpinBox, QSlider,
    QComboBox, QFrame, QGroupBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QObject
from PyQt6.QtGui import QFont, QColor

from ..utils.input_simulator import (
    mouse_click, get_cursor_pos, set_cursor_pos,
    GlobalHotkeyListener, VK_MAP
)

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
        self.click_type = "single"
        self.repeat_mode = "infinite"  # "infinite" o "count"
        self.target_count = 100
        self.location_mode = "dynamic"  # "dynamic" o "fixed"
        self.fixed_x = 0
        self.fixed_y = 0

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

        # Calcular delay inicial
        if self.mode == "cps":
            delay = 1.0 / max(1.0, float(self.target_cps))
        else:
            delay = max(0.001, self.interval_sec)

        while self.running:
            t0 = time.perf_counter()

            # Posición del clic
            if self.location_mode == "fixed":
                mouse_click(self.button, self.click_type, self.fixed_x, self.fixed_y)
            else:
                mouse_click(self.button, self.click_type)

            total_clicks += 1
            clicks_in_window += 1

            # Medición de CPS real
            now = time.perf_counter()
            if now - last_stat_time >= 0.25:
                curr_cps = clicks_in_window / (now - last_stat_time)
                self.signals.clicked.emit(total_clicks, curr_cps)
                clicks_in_window = 0
                last_stat_time = now

            # Comprobar límite de repeticiones
            if self.repeat_mode == "count" and total_clicks >= self.target_count:
                break

            # Precisión milimétrica de timing
            elapsed = time.perf_counter() - t0
            sleep_needed = delay - elapsed
            if sleep_needed > 0.002:
                time.sleep(sleep_needed - 0.001)
            # Micro-bucle para precisión sub-milisegundo en CPS alto
            while (time.perf_counter() - t0) < delay:
                pass

        self.running = False
        self.signals.stopped.emit()


class TabAutoClicker(QWidget):
    """Interfaz gráfica de usuario para el Auto Clicker Pro."""
    def __init__(self, parent=None, colores=None, context=None, **kwargs):
        super().__init__(parent)
        self.context = context
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171",
        }
        self.font_family = "Segoe UI"

        self.signals = ClickerSignals()
        self.worker = AutoClickerWorker(self.signals)

        self.signals.clicked.connect(self._on_click_update)
        self.signals.started.connect(self._on_worker_started)
        self.signals.stopped.connect(self._on_worker_stopped)

        # Hotkey global (F6 por defecto)
        self.hotkey_listener = GlobalHotkeyListener()
        self.current_hotkey = "F6"

        # Timer para captura de posición
        self.picker_timer = QTimer(self)
        self.picker_countdown = 3
        self.picker_timer.timeout.connect(self._actualizar_cuenta_regresiva_picker)

        self._init_ui()
        self._registrar_hotkey(self.current_hotkey)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # ── 1. HEADER CARD CON ESTADO ──────────────────────────────────────────
        header_card = QFrame()
        header_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        h_lay = QHBoxLayout(header_card)
        h_lay.setContentsMargins(10, 8, 10, 8)

        lbl_title = QLabel("🖱️ Auto Clicker Pro (Speed & OP)")
        lbl_title.setFont(QFont(self.font_family, 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none;")
        h_lay.addWidget(lbl_title)

        h_lay.addStretch()

        self.lbl_status = QLabel("● DETENIDO")
        self.lbl_status.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(248, 113, 113, 0.15);
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

        # Radio selector de modo
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
        o_lay.setSpacing(10)

        o_lay.addWidget(self._crear_label("Botón del Ratón:"), 0, 0)
        self.combo_btn = QComboBox()
        self.combo_btn.addItems(["Izquierdo (Left)", "Derecho (Right)", "Central (Middle)"])
        self.combo_btn.setStyleSheet(self._estilo_input())
        o_lay.addWidget(self.combo_btn, 0, 1)

        o_lay.addWidget(self._crear_label("Tipo de Clic:"), 1, 0)
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Simple (1x)", "Doble (2x)", "Triple (3x)"])
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
        grid.addWidget(card_pos, 1, 0)

        # CARD D: Repetición y Límites
        card_repeat = self._crear_card("🔁 Repetición y Límite")
        rep_lay = QVBoxLayout(card_repeat)

        self.rb_rep_inf = QRadioButton("Repetir indefinidamente (hasta detener)")
        self.rb_rep_count = QRadioButton("Repetir cantidad fija de veces")
        self.rb_rep_inf.setChecked(True)
        self.rb_rep_inf.toggled.connect(self._on_repeat_mode_toggled)

        for rb in (self.rb_rep_inf, self.rb_rep_count):
            rb.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: 500;")
            rep_lay.addWidget(rb)

        self.frame_rep_count = QFrame()
        self.frame_rep_count.setVisible(False)
        rc_lay = QHBoxLayout(self.frame_rep_count)
        rc_lay.setContentsMargins(0, 4, 0, 4)
        rc_lay.addWidget(QLabel("Número de clics:"))
        self.spin_target_count = self._crear_subspin(1, 1000000, " clics", val=100)
        rc_lay.addWidget(self.spin_target_count)
        rep_lay.addWidget(self.frame_rep_count)

        grid.addWidget(card_repeat, 1, 1)

        main_layout.addLayout(grid)

        # ── 3. CONTROLES DE EJECUCIÓN Y BOTÓN GIGANTE ──────────────────────────
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 14px;
            }}
        """)
        c_lay = QHBoxLayout(ctrl_card)

        # Selector de Hotkey
        hk_box = QVBoxLayout()
        lbl_hk = QLabel("Atajo Global de Inicio / Parada:")
        lbl_hk.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        hk_box.addWidget(lbl_hk)

        self.combo_hotkey = QComboBox()
        self.combo_hotkey.addItems(["F6", "F7", "F8", "F9", "F10", "F11", "F12"])
        self.combo_hotkey.setCurrentText("F6")
        self.combo_hotkey.setStyleSheet(self._estilo_input())
        self.combo_hotkey.currentTextChanged.connect(self._on_hotkey_changed)
        hk_box.addWidget(self.combo_hotkey)
        c_lay.addLayout(hk_box)

        c_lay.addSpacing(20)

        # Botón Principal de Inicio / Parada
        self.btn_toggle = QPushButton("▶ INICIAR (F6)")
        self.btn_toggle.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setFixedHeight(50)
        self.btn_toggle.setStyleSheet(self._estilo_boton_accion(activo=False))
        self.btn_toggle.clicked.connect(self.toggle_clicker)
        c_lay.addWidget(self.btn_toggle, 1)

        main_layout.addWidget(ctrl_card)

        # ── 4. BARRA DE ESTADÍSTICAS EN VIVO ──────────────────────────────────
        stats_frame = QFrame()
        stats_lay = QHBoxLayout(stats_frame)
        stats_lay.setContentsMargins(10, 0, 10, 0)

        self.lbl_stats_clicks = QLabel("Clics: 0")
        self.lbl_stats_cps = QLabel("CPS Real: 0.0")
        self.lbl_stats_pos = QLabel("Ratón: X=0, Y=0")

        for lbl in (self.lbl_stats_clicks, self.lbl_stats_cps, self.lbl_stats_pos):
            lbl.setFont(QFont(self.font_family, 10))
            lbl.setStyleSheet(f"color: {self.colores['fg_secundario']};")
            stats_lay.addWidget(lbl)

        btn_reset_stats = QPushButton("🔄 Reiniciar Contador")
        btn_reset_stats.setStyleSheet(self._estilo_boton_secundario())
        btn_reset_stats.clicked.connect(self._reset_stats)
        stats_lay.addWidget(btn_reset_stats)

        main_layout.addWidget(stats_frame)
        main_layout.addStretch()

        # Timer para actualizar posición del cursor en barra de estado
        self.mouse_pos_timer = QTimer(self)
        self.mouse_pos_timer.timeout.connect(self._actualizar_mouse_pos_label)
        self.mouse_pos_timer.start(100)

    # ── HELPERS DE ESTILO Y UI ───────────────────────────────────────────────
    def _crear_card(self, titulo: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        lbl = QLabel(titulo)
        lbl.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {self.colores['acento']}; border: none; margin-bottom: 6px;")
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
                padding: 5px 8px;
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

    def _estilo_boton_accion(self, activo: bool) -> str:
        if activo:
            return f"""
                QPushButton {{
                    background-color: {self.colores['error']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px;
                }}
                QPushButton:hover {{
                    background-color: #EF4444;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: {self.colores['acento']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px;
                }}
                QPushButton:hover {{
                    background-color: {self.colores['acento_hover']};
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
                font-size: 10px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
        """

    # ── GESTIÓN DE EVENTOS Y ACCIONES ─────────────────────────────────────────
    def _on_mode_toggled(self, checked: bool):
        self.frame_cps.setVisible(self.rb_mode_cps.isChecked())
        self.frame_interval.setVisible(self.rb_mode_interval.isChecked())

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

    def _on_hotkey_changed(self, new_hk: str):
        self._registrar_hotkey(new_hk)

    def _registrar_hotkey(self, hotkey_name: str):
        if self.current_hotkey:
            self.hotkey_listener.unregister_hotkey(self.current_hotkey)
        self.current_hotkey = hotkey_name
        self.btn_toggle.setText(f"▶ INICIAR ({hotkey_name})" if not self.worker.running else f"⏹ DETENER ({hotkey_name})")
        self.hotkey_listener.register_hotkey(hotkey_name, self.toggle_clicker)

    def toggle_clicker(self):
        """Alterna el estado de ejecución (llamado desde botón o atajo de teclado)."""
        if self.worker.running:
            self.worker.stop()
        else:
            self._aplicar_configuracion_al_worker()
            self.worker.start()

    def _aplicar_configuracion_al_worker(self):
        # Modo
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

        # Botón
        btn_idx = self.combo_btn.currentIndex()
        self.worker.button = "left" if btn_idx == 0 else ("right" if btn_idx == 1 else "middle")

        # Tipo
        type_idx = self.combo_type.currentIndex()
        self.worker.click_type = "single" if type_idx == 0 else ("double" if type_idx == 1 else "triple")

        # Posición
        if self.rb_pos_fixed.isChecked():
            self.worker.location_mode = "fixed"
            self.worker.fixed_x = self.spin_x.value()
            self.worker.fixed_y = self.spin_y.value()
        else:
            self.worker.location_mode = "dynamic"

        # Repetición
        if self.rb_rep_count.isChecked():
            self.worker.repeat_mode = "count"
            self.worker.target_count = self.spin_target_count.value()
        else:
            self.worker.repeat_mode = "infinite"

    def _on_worker_started(self):
        self.lbl_status.setText("● EN EJECUCIÓN")
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(52, 211, 153, 0.15);
            color: {self.colores['exito']};
            border: 1px solid {self.colores['exito']};
            border-radius: 6px;
            padding: 4px 12px;
        """)
        self.btn_toggle.setText(f"⏹ DETENER ({self.current_hotkey})")
        self.btn_toggle.setStyleSheet(self._estilo_boton_accion(activo=True))

    def _on_worker_stopped(self):
        self.lbl_status.setText("● DETENIDO")
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(248, 113, 113, 0.15);
            color: {self.colores['error']};
            border: 1px solid {self.colores['error']};
            border-radius: 6px;
            padding: 4px 12px;
        """)
        self.btn_toggle.setText(f"▶ INICIAR ({self.current_hotkey})")
        self.btn_toggle.setStyleSheet(self._estilo_boton_accion(activo=False))

    def _on_click_update(self, total_clicks: int, actual_cps: float):
        self.lbl_stats_clicks.setText(f"Clics: {total_clicks:,}")
        self.lbl_stats_cps.setText(f"CPS Real: {actual_cps:.1f}")

    def cleanup(self):
        """Detiene listeners e hilos al cerrar la aplicación."""
        if hasattr(self, "worker") and self.worker.running:
            self.worker.stop()
        if hasattr(self, "hotkey_listener"):
            self.hotkey_listener.stop()
        if hasattr(self, "mouse_pos_timer"):
            self.mouse_pos_timer.stop()
