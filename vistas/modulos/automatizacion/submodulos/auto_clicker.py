"""
auto_clicker.py - Submódulo Auto Clicker Dual:
Permite alternar entre:
  1. OP Auto Clicker 4.0 (Interfaz clásica por intervalos H/M/S/MS, Random offset ±ms, Pick location, 2x2 Grid)
  2. Speed AutoClicker (Interfaz por CPS, Activation Mode Hold/Toggle, Choose Apps, Gráfico interactivo del Ratón LButton/MButton/RButton, Duty Cycle % y Click/Wait ms)
Cuando se selecciona uno de los dos modos, el otro se detiene y desactiva por completo para evitar duplicación.
"""

import time
import random
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QRadioButton, QSpinBox, QDoubleSpinBox, QComboBox,
    QFrame, QCheckBox, QScrollArea, QSizePolicy, QStackedWidget,
    QButtonGroup, QDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QObject, QRectF
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient

from ..utils.input_simulator import (
    mouse_click, get_cursor_pos, set_cursor_pos,
    lock_cursor_to_point, unlock_cursor, play_sound_feedback,
    get_foreground_window_title, get_open_window_titles,
    GlobalHotkeyListener
)
from ..utils.hotkey_widget import HotkeySettingDialog


class ClickerSignals(QObject):
    clicked = pyqtSignal(int, float)  # total_clicks, actual_cps
    started = pyqtSignal()
    stopped = pyqtSignal()


class AutoClickerWorker:
    """Motor de clics de alta precisión compatible con OP Auto Clicker 4.0 y Speed AutoClicker."""
    def __init__(self, signals: ClickerSignals):
        self.signals = signals
        self.running = False
        self.thread = None

        # Modo general: "op" o "speed"
        self.engine_type = "op"

        # Parámetros compartidos / OP Auto Clicker
        self.base_interval_sec = 0.1  # 100 ms por defecto
        self.random_offset_enabled = False
        self.random_offset_ms = 40
        self.button = "left"          # left, right, middle
        self.click_type = "single"    # single, double, triple, hold_down
        self.repeat_mode = "infinite" # infinite o count
        self.target_count = 1
        self.location_mode = "dynamic" # dynamic o fixed
        self.fixed_x = 0
        self.fixed_y = 0
        self.lock_cursor = False

        # Parámetros exclusivos de Speed AutoClicker
        self.speed_cps = 10.0
        self.speed_unlimited = False
        self.speed_random = False
        self.speed_duty_cycle = 50.0  # Porcentaje (1% - 99%)
        self.speed_limit_enabled = False
        self.speed_max_clicks = 1000
        self.allowed_apps = []        # Lista de títulos de ventana permitidos (vacío = todas)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.signals.started.emit()

    def stop(self):
        self.running = False

    def _is_foreground_app_allowed(self) -> bool:
        if not self.allowed_apps:
            return True
        fg_title = get_foreground_window_title().lower()
        if not fg_title:
            return False
        for app_title in self.allowed_apps:
            if app_title.lower() in fg_title:
                return True
        return False

    def _run(self):
        total_clicks = 0
        start_time = time.perf_counter()
        last_stat_time = start_time
        clicks_in_window = 0

        if self.engine_type == "op" and self.lock_cursor and self.location_mode == "fixed":
            lock_cursor_to_point(self.fixed_x, self.fixed_y)

        if self.engine_type == "op" and self.click_type == "hold_down":
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

                if self.engine_type == "speed":
                    # Verificar filtro CHOOSE APPS si está activo
                    if not self._is_foreground_app_allowed():
                        time.sleep(0.05)
                        continue

                    if self.speed_unlimited:
                        click_sec = 0.0005
                        wait_sec = 0.0005
                    else:
                        cps = max(0.1, float(self.speed_cps))
                        period_sec = 1.0 / cps
                        if self.speed_random:
                            period_sec *= random.uniform(0.75, 1.25)
                        duty = max(1.0, min(99.0, float(self.speed_duty_cycle))) / 100.0
                        click_sec = period_sec * duty
                        wait_sec = period_sec * (1.0 - duty)

                    mouse_click(self.button, "single", None, None, hold_duration=click_sec)
                    total_clicks += 1
                    clicks_in_window += 1

                    now = time.perf_counter()
                    if now - last_stat_time >= 0.25:
                        curr_cps = clicks_in_window / (now - last_stat_time)
                        self.signals.clicked.emit(total_clicks, curr_cps)
                        clicks_in_window = 0
                        last_stat_time = now

                    if self.speed_limit_enabled and total_clicks >= self.speed_max_clicks:
                        break

                    # Espera precisa del tramo Wait
                    t_wait_start = time.perf_counter()
                    if wait_sec > 0.002:
                        time.sleep(wait_sec - 0.001)
                    while self.running and (time.perf_counter() - t_wait_start) < wait_sec:
                        pass

                else:
                    # Motor OP Auto Clicker 4.0
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

                    target_delay = self.base_interval_sec
                    if self.random_offset_enabled and self.random_offset_ms > 0:
                        offset_sec = random.uniform(-self.random_offset_ms, self.random_offset_ms) / 1000.0
                        target_delay = max(0.001, target_delay + offset_sec)

                    elapsed = time.perf_counter() - t0
                    sleep_needed = target_delay - elapsed
                    if sleep_needed > 0.002:
                        time.sleep(sleep_needed - 0.001)
                    while self.running and (time.perf_counter() - t0) < target_delay:
                        pass
        finally:
            if self.engine_type == "op" and self.lock_cursor:
                unlock_cursor()
            self.running = False
            self.signals.stopped.emit()


class MouseVisualWidget(QWidget):
    """
    Gráfico vectorial interactivo del ratón idéntico a Speed AutoClicker.
    Resalta en rojo coral el botón seleccionado (LButton, MButton o RButton)
    y también permite seleccionarlo haciendo clic directamente en el dibujo.
    """
    button_clicked = pyqtSignal(str)  # "left", "middle", "right"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_button = "left"  # "left", "middle", "right"
        self.setFixedSize(130, 155)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Haz clic en el botón izquierdo, central o derecho del ratón para seleccionarlo")

    def set_selected_button(self, btn: str):
        self.selected_button = btn
        self.update()

    def mousePressEvent(self, event):
        pos = event.position()
        x, y = pos.x(), pos.y()
        if y < 75:
            if 52 <= x <= 78 and 18 <= y <= 65:
                self.set_selected_button("middle")
                self.button_clicked.emit("middle")
            elif x < 65:
                self.set_selected_button("left")
                self.button_clicked.emit("left")
            else:
                self.set_selected_button("right")
                self.button_clicked.emit("right")
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        body_rect = QRectF(18, 10, w - 36, h - 20)

        # Sombra exterior suave
        shadow_rect = QRectF(21, 14, w - 36, h - 20)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 90))
        painter.drawRoundedRect(shadow_rect, 44, 48)

        # Cuerpo principal del ratón con degradado metálico claro (como Speed AutoClicker)
        grad_body = QLinearGradient(body_rect.topLeft(), body_rect.bottomRight())
        grad_body.setColorAt(0.0, QColor("#F8FAFC"))
        grad_body.setColorAt(0.7, QColor("#E2E8F0"))
        grad_body.setColorAt(1.0, QColor("#94A3B8"))

        painter.setPen(QPen(QColor("#475569"), 2))
        painter.setBrush(QBrush(grad_body))
        painter.drawRoundedRect(body_rect, 44, 48)

        # Colores de resaltado rojo (Speed AutoClicker style)
        grad_active = QLinearGradient(0, 10, 0, 72)
        grad_active.setColorAt(0.0, QColor("#FCA5A5"))
        grad_active.setColorAt(0.5, QColor("#EF4444"))
        grad_active.setColorAt(1.0, QColor("#B91C1C"))

        # Botón Izquierdo (LButton)
        left_path = QPainterPath()
        left_path.moveTo(65, 10)
        left_path.quadTo(20, 10, 18, 55)
        left_path.lineTo(18, 66)
        left_path.quadTo(42, 62, 65, 62)
        left_path.closeSubpath()

        if self.selected_button == "left":
            painter.setBrush(QBrush(grad_active))
        else:
            painter.setBrush(QBrush(grad_body))
        painter.setPen(QPen(QColor("#475569"), 1.8))
        painter.drawPath(left_path)

        # Botón Derecho (RButton)
        right_path = QPainterPath()
        right_path.moveTo(65, 10)
        right_path.quadTo(w - 20, 10, w - 18, 55)
        right_path.lineTo(w - 18, 66)
        right_path.quadTo(w - 42, 62, 65, 62)
        right_path.closeSubpath()

        if self.selected_button == "right":
            painter.setBrush(QBrush(grad_active))
        else:
            painter.setBrush(QBrush(grad_body))
        painter.setPen(QPen(QColor("#475569"), 1.8))
        painter.drawPath(right_path)

        # Rueda Central (Scroll Wheel - MButton)
        wheel_rect = QRectF(56, 20, 18, 36)
        if self.selected_button == "middle":
            painter.setBrush(QBrush(grad_active))
            painter.setPen(QPen(QColor("#7F1D1D"), 2))
        else:
            painter.setBrush(QColor("#64748B"))
            painter.setPen(QPen(QColor("#334155"), 1.5))
        painter.drawRoundedRect(wheel_rect, 8, 8)


class ChooseAppsDialog(QDialog):
    """Diálogo 'CHOOSE APPS' de Speed AutoClicker para restringir clics a aplicaciones específicas."""
    def __init__(self, current_apps: list[str], colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.selected_apps = list(current_apps)

        self.setWindowTitle("Choose Apps - Speed AutoClicker")
        self.setFixedSize(440, 340)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
            }}
            QLabel {{ color: {self.colores['fg_principal']}; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lbl = QLabel(
            "Selecciona las ventanas donde Speed AutoClicker tiene permitido hacer clic.\n"
            "(Si no marcas ninguna, funcionará en todas las aplicaciones):"
        )
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        lay.addWidget(lbl)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.colores['bg_principal']};
                color: white;
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget::item {{ padding: 5px; }}
        """)
        lay.addWidget(self.list_widget, 1)

        self._poblar_ventanas()

        btn_row = QHBoxLayout()
        btn_clear = QPushButton("Permitir Todas (Limpiar)")
        btn_clear.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
            }}
        """)
        btn_clear.clicked.connect(self._limpiar_seleccion)
        btn_row.addWidget(btn_clear)

        btn_row.addStretch()

        btn_ok = QPushButton("Guardar")
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background-color: #0284C7;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }}
        """)
        btn_ok.clicked.connect(self._guardar)
        btn_row.addWidget(btn_ok)

        lay.addLayout(btn_row)

    def _poblar_ventanas(self):
        titles = get_open_window_titles()
        for t in titles:
            item = QListWidgetItem(t)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if t in self.selected_apps:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)

    def _limpiar_seleccion(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _guardar(self):
        res = []
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                res.append(it.text())
        self.selected_apps = res
        self.accept()


class TabAutoClicker(QWidget):
    """
    Submódulo Auto Clicker con selector superior para alternar entre:
      - OP Auto Clicker 4.0
      - Speed AutoClicker
    Garantiza exclusión mutua: al elegir uno, el otro se detiene y desactiva.
    """
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

        # Hotkey listeners independientes para cada modo (solo 1 activo a la vez)
        self.op_hotkey_listener = GlobalHotkeyListener()
        self.op_hotkey = "F6"

        self.speed_hotkey_listener = GlobalHotkeyListener()
        self.speed_hotkey_listener.enabled = False  # Desactivado inicialmente porque inicia en OP
        self.speed_hotkey = "MButton"
        self.speed_is_capturing_key = False
        self._last_speed_capture_ts = 0.0
        self.speed_allowed_apps = []

        self.speed_hotkey_listener.signals.key_captured.connect(self._on_speed_key_captured)
        self.speed_hotkey_listener.signals.capture_cancelled.connect(self._cancel_speed_key_select)

        self.picker_timer = QTimer(self)
        self.picker_countdown = 3
        self.picker_timer.timeout.connect(self._actualizar_cuenta_regresiva_picker)

        self._init_ui()
        self._registrar_op_hotkey(self.op_hotkey)
        self._registrar_speed_hotkey(self.speed_hotkey)
        self._actualizar_label_click_wait()

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
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        # ── BARRA SUPERIOR: SELECTOR DE TIPO DE AUTOCLICKER (OP vs SPEED) ────
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
        h_lay.setSpacing(10)

        lbl_mode = QLabel("🖱️ Tipo de Auto Clicker:")
        lbl_mode.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_mode.setStyleSheet("color: white;")
        h_lay.addWidget(lbl_mode)

        self.combo_clicker_mode = QComboBox()
        self.combo_clicker_mode.addItems([
            "🅰️ OP Auto Clicker 4.0",
            "⚡ Speed AutoClicker"
        ])
        self.combo_clicker_mode.setMinimumWidth(210)
        self.combo_clicker_mode.setStyleSheet(self._estilo_input())
        self.combo_clicker_mode.currentIndexChanged.connect(self._on_clicker_mode_changed)
        h_lay.addWidget(self.combo_clicker_mode)

        h_lay.addStretch()

        self.lbl_preset = QLabel("⚡ Perfil:")
        self.lbl_preset.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        h_lay.addWidget(self.lbl_preset)

        self.combo_presets = QComboBox()
        self.combo_presets.addItems([
            "Personalizado",
            "⚔️ Minecraft PvP (16 CPS)",
            "🤖 Roblox AFK (100 ms)",
            "⚡ Ultra Speed (100 CPS)",
            "🎯 Doble Clic Rápido",
            "🖱️ Clic Derecho Spammer"
        ])
        self.combo_presets.setStyleSheet(self._estilo_input())
        self.combo_presets.currentIndexChanged.connect(self._aplicar_preset)
        h_lay.addWidget(self.combo_presets)

        h_lay.addSpacing(8)

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

        # ── QSTACKEDWIDGET PARA LOS 2 MODOS (EXCLUSIÓN MUTUA) ────────────────
        self.stacked_modes = QStackedWidget()
        self.page_op = self._build_op_autoclicker_page()
        self.page_speed = self._build_speed_autoclicker_page()

        self.stacked_modes.addWidget(self.page_op)     # Index 0: OP Auto Clicker 4.0
        self.stacked_modes.addWidget(self.page_speed)  # Index 1: Speed AutoClicker
        main_layout.addWidget(self.stacked_modes)

        # ── BARRA INFERIOR DE ESTADÍSTICAS Y OPCIONES GLOBALES ───────────────
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

    # =========================================================================
    # PÁGINA 0: OP AUTO CLICKER 4.0
    # =========================================================================
    def _build_op_autoclicker_page(self) -> QWidget:
        page = QWidget()
        op_layout = QVBoxLayout(page)
        op_layout.setContentsMargins(0, 0, 0, 0)
        op_layout.setSpacing(12)

        # 1. Click interval
        card_interval, ci_lay = self._crear_card("Click interval")

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
        ci_lay.addLayout(f_row1)

        f_row2 = QHBoxLayout()
        f_row2.setSpacing(8)
        btn_help = QPushButton("?")
        btn_help.setFixedSize(24, 24)
        btn_help.setToolTip("Añade un desfase aleatorio (±ms) entre clics para simular comportamiento humano.")
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

        op_layout.addWidget(card_interval)

        # 2 & 3. Click options & Click repeat
        mid_grid = QGridLayout()
        mid_grid.setSpacing(12)

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
        op_layout.addLayout(mid_grid)

        # 4. Cursor position
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
        self.chk_lock_cursor.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        p_lay.addWidget(self.chk_lock_cursor)

        p_lay.addStretch()
        pos_vbox.addLayout(p_lay)
        op_layout.addWidget(card_pos)

        # 5. Cuadrícula 2x2 de OP Auto Clicker
        grid_actions = QGridLayout()
        grid_actions.setSpacing(10)

        self.btn_op_start = QPushButton(f"Start ({self.op_hotkey})")
        self.btn_op_start.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_op_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_op_start.setFixedHeight(44)
        self.btn_op_start.setStyleSheet(self._estilo_btn_start(activo=True))
        self.btn_op_start.clicked.connect(self.start_clicker)
        grid_actions.addWidget(self.btn_op_start, 0, 0)

        self.btn_op_stop = QPushButton(f"Stop ({self.op_hotkey})")
        self.btn_op_stop.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_op_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_op_stop.setFixedHeight(44)
        self.btn_op_stop.setEnabled(False)
        self.btn_op_stop.setStyleSheet(self._estilo_btn_stop(activo=False))
        self.btn_op_stop.clicked.connect(self.stop_clicker)
        grid_actions.addWidget(self.btn_op_stop, 0, 1)

        self.btn_hotkey_setting = QPushButton("Hotkey setting")
        self.btn_hotkey_setting.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_hotkey_setting.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hotkey_setting.setFixedHeight(38)
        self.btn_hotkey_setting.setStyleSheet(self._estilo_boton_cuadricula())
        self.btn_hotkey_setting.clicked.connect(self._abrir_dialogo_hotkey)
        grid_actions.addWidget(self.btn_hotkey_setting, 1, 0)

        self.btn_record_playback = QPushButton("Record && Playback")
        self.btn_record_playback.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_record_playback.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_record_playback.setFixedHeight(38)
        self.btn_record_playback.setStyleSheet(self._estilo_boton_cuadricula())
        self.btn_record_playback.clicked.connect(self._abrir_record_playback)
        grid_actions.addWidget(self.btn_record_playback, 1, 1)

        op_layout.addLayout(grid_actions)
        return page

    # =========================================================================
    # PÁGINA 1: SPEED AUTOCLICKER (Idéntico a la captura de Speed AutoClicker)
    # =========================================================================
    def _build_speed_autoclicker_page(self) -> QWidget:
        page = QWidget()
        sp_layout = QVBoxLayout(page)
        sp_layout.setContentsMargins(0, 0, 0, 0)
        sp_layout.setSpacing(12)

        # ── 1. ACTIVATION ────────────────────────────────────────────────────
        card_act, act_vbox = self._crear_card("Activation")
        act_grid = QGridLayout()
        act_grid.setSpacing(10)

        act_grid.addWidget(self._crear_label("Activation Key:"), 0, 0)

        self.lbl_speed_key_box = QLabel(self.speed_hotkey)
        self.lbl_speed_key_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_speed_key_box.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_speed_key_box.setFixedHeight(32)
        self.lbl_speed_key_box.setStyleSheet(f"""
            background-color: {self.colores['bg_principal']};
            color: white;
            border: 1px solid {self.colores['bg_terciario']};
            border-radius: 5px;
            padding: 4px 16px;
        """)
        act_grid.addWidget(self.lbl_speed_key_box, 0, 1)

        self.btn_speed_select_key = QPushButton("SELECT...")
        self.btn_speed_select_key.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_speed_select_key.setFixedHeight(32)
        self.btn_speed_select_key.setMinimumWidth(140)
        self.btn_speed_select_key.setStyleSheet(self._estilo_btn_speed_azul())
        self.btn_speed_select_key.clicked.connect(self._toggle_speed_key_select)
        act_grid.addWidget(self.btn_speed_select_key, 0, 2)

        act_grid.addWidget(self._crear_label("Activation Mode:"), 1, 0)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(18)
        mode_row.addStretch()
        self.rb_speed_hold = QRadioButton("hold")
        self.rb_speed_toggle = QRadioButton("toggle")
        self.rb_speed_hold.setChecked(True)

        self.grp_speed_act_mode = QButtonGroup(self)
        for rb in (self.rb_speed_hold, self.rb_speed_toggle):
            rb.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: 500;")
            self.grp_speed_act_mode.addButton(rb)
            mode_row.addWidget(rb)
        mode_row.addStretch()
        act_grid.addLayout(mode_row, 1, 1)

        self.btn_choose_apps = QPushButton("CHOOSE APPS")
        self.btn_choose_apps.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_choose_apps.setFixedHeight(32)
        self.btn_choose_apps.setMinimumWidth(140)
        self.btn_choose_apps.setStyleSheet(self._estilo_btn_speed_azul())
        self.btn_choose_apps.clicked.connect(self._abrir_choose_apps)
        act_grid.addWidget(self.btn_choose_apps, 1, 2)

        act_grid.setColumnStretch(1, 1)
        act_vbox.addLayout(act_grid)
        sp_layout.addWidget(card_act)

        # ── 2. CLICKS (CON DIBUJO INTERACTIVO DEL RATÓN) ─────────────────────
        card_clicks, clicks_vbox = self._crear_card("Clicks")

        self.grp_speed_mouse_btn = QButtonGroup(self)

        # Opción superior: middle Mouse Button (Scroll Wheel) MButton
        top_btn_lay = QHBoxLayout()
        top_btn_lay.addStretch()
        self.rb_speed_mbutton = QRadioButton("middle Mouse Button (Scroll Wheel) — MButton")
        self.rb_speed_mbutton.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: bold;")
        self.grp_speed_mouse_btn.addButton(self.rb_speed_mbutton)
        top_btn_lay.addWidget(self.rb_speed_mbutton)
        top_btn_lay.addStretch()
        clicks_vbox.addLayout(top_btn_lay)

        # Fila central: [left Mouse Button LButton] + [Gráfico Ratón] + [right Mouse Button RButton]
        center_mouse_lay = QHBoxLayout()
        center_mouse_lay.setSpacing(18)
        center_mouse_lay.addStretch()

        self.rb_speed_lbutton = QRadioButton("left Mouse Button\nLButton")
        self.rb_speed_lbutton.setChecked(True)
        self.rb_speed_lbutton.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: bold;")
        self.grp_speed_mouse_btn.addButton(self.rb_speed_lbutton)
        center_mouse_lay.addWidget(self.rb_speed_lbutton)

        self.mouse_visual = MouseVisualWidget(self)
        self.mouse_visual.button_clicked.connect(self._on_mouse_graphic_clicked)
        center_mouse_lay.addWidget(self.mouse_visual)

        self.rb_speed_rbutton = QRadioButton("right Mouse Button\nRButton")
        self.rb_speed_rbutton.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: bold;")
        self.grp_speed_mouse_btn.addButton(self.rb_speed_rbutton)
        center_mouse_lay.addWidget(self.rb_speed_rbutton)

        center_mouse_lay.addStretch()
        clicks_vbox.addLayout(center_mouse_lay)

        self.rb_speed_lbutton.toggled.connect(lambda c: c and self.mouse_visual.set_selected_button("left"))
        self.rb_speed_mbutton.toggled.connect(lambda c: c and self.mouse_visual.set_selected_button("middle"))
        self.rb_speed_rbutton.toggled.connect(lambda c: c and self.mouse_visual.set_selected_button("right"))

        sp_layout.addWidget(card_clicks)

        # ── 3. CLICK RATE & CLICK LIMIT (2 COLUMNAS) ─────────────────────────
        rate_limit_grid = QGridLayout()
        rate_limit_grid.setSpacing(12)

        # Columna Izquierda: Click rate
        card_rate, rate_vbox = self._crear_card("Click rate")

        cps_row = QHBoxLayout()
        self.spin_speed_cps = QDoubleSpinBox()
        self.spin_speed_cps.setRange(0.10, 10000.00)
        self.spin_speed_cps.setDecimals(2)
        self.spin_speed_cps.setValue(10.00)
        self.spin_speed_cps.setMinimumWidth(95)
        self.spin_speed_cps.setStyleSheet(self._estilo_input())
        self.spin_speed_cps.valueChanged.connect(self._actualizar_label_click_wait)
        cps_row.addWidget(self.spin_speed_cps)
        cps_row.addWidget(self._crear_label("Clicks per second"))
        cps_row.addStretch()
        rate_vbox.addLayout(cps_row)

        chk_rate_row = QHBoxLayout()
        self.chk_speed_unlimited = QCheckBox("unlimited")
        self.chk_speed_random = QCheckBox("random")
        for chk in (self.chk_speed_unlimited, self.chk_speed_random):
            chk.setStyleSheet(f"color: {self.colores['fg_principal']}; font-size: 11px;")
            chk_rate_row.addWidget(chk)
        self.chk_speed_unlimited.toggled.connect(self._on_speed_unlimited_toggled)
        chk_rate_row.addStretch()
        rate_vbox.addLayout(chk_rate_row)

        duty_row = QHBoxLayout()
        duty_row.addWidget(self._crear_label("Click duty cycle:"))
        self.spin_speed_duty = QDoubleSpinBox()
        self.spin_speed_duty.setRange(1.00, 99.00)
        self.spin_speed_duty.setDecimals(2)
        self.spin_speed_duty.setValue(50.00)
        self.spin_speed_duty.setMinimumWidth(85)
        self.spin_speed_duty.setStyleSheet(self._estilo_input())
        self.spin_speed_duty.valueChanged.connect(self._actualizar_label_click_wait)
        duty_row.addWidget(self.spin_speed_duty)
        duty_row.addWidget(self._crear_label("%"))
        duty_row.addStretch()
        rate_vbox.addLayout(duty_row)

        rate_limit_grid.addWidget(card_rate, 0, 0)

        # Columna Derecha: Click limit
        card_limit, limit_vbox = self._crear_card("Click limit")

        self.chk_speed_limit = QCheckBox("Enable Click Limit")
        self.chk_speed_limit.setChecked(False)
        self.chk_speed_limit.setStyleSheet(f"color: {self.colores['fg_principal']}; font-size: 11px;")
        limit_vbox.addWidget(self.chk_speed_limit)

        max_row = QHBoxLayout()
        max_row.addWidget(self._crear_label("Maximum"))
        self.spin_speed_max_clicks = self._crear_subspin(1, 10000000, "", val=1000, width=100)
        self.spin_speed_max_clicks.setEnabled(False)
        self.chk_speed_limit.toggled.connect(self.spin_speed_max_clicks.setEnabled)
        max_row.addWidget(self.spin_speed_max_clicks)
        max_row.addWidget(self._crear_label("Clicks"))
        max_row.addStretch()
        limit_vbox.addLayout(max_row)

        limit_vbox.addSpacing(6)

        self.lbl_click_wait = QLabel("Click / Wait: 50.0 ms / 50.0 ms")
        self.lbl_click_wait.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_click_wait.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_click_wait.setStyleSheet(f"color: {self.colores['fg_principal']};")
        limit_vbox.addWidget(self.lbl_click_wait)

        rate_limit_grid.addWidget(card_limit, 0, 1)
        sp_layout.addLayout(rate_limit_grid)

        # ── 4. MISC & BOTONES DE CONTROL (START / STOP / RESET SETTINGS) ─────
        card_misc, misc_vbox = self._crear_card("Misc & Controls")
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)

        self.btn_speed_start = QPushButton(f"▶ Start ({self.speed_hotkey})")
        self.btn_speed_start.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_speed_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_speed_start.setFixedHeight(42)
        self.btn_speed_start.setStyleSheet(self._estilo_btn_start(activo=True))
        self.btn_speed_start.clicked.connect(self.start_clicker)
        ctrl_row.addWidget(self.btn_speed_start, 1)

        self.btn_speed_stop = QPushButton(f"⏹ Stop ({self.speed_hotkey})")
        self.btn_speed_stop.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_speed_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_speed_stop.setFixedHeight(42)
        self.btn_speed_stop.setEnabled(False)
        self.btn_speed_stop.setStyleSheet(self._estilo_btn_stop(activo=False))
        self.btn_speed_stop.clicked.connect(self.stop_clicker)
        ctrl_row.addWidget(self.btn_speed_stop, 1)

        self.btn_speed_reset = QPushButton("RESET SETTINGS")
        self.btn_speed_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_speed_reset.setFixedHeight(42)
        self.btn_speed_reset.setMinimumWidth(155)
        self.btn_speed_reset.setStyleSheet(self._estilo_btn_speed_azul())
        self.btn_speed_reset.clicked.connect(self._reset_speed_settings)
        ctrl_row.addWidget(self.btn_speed_reset)

        misc_vbox.addLayout(ctrl_row)
        sp_layout.addWidget(card_misc)

        return page

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
            QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 11px;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
                border: 1px solid {self.colores['acento']};
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: #FFFFFF;
                selection-background-color: {self.colores['acento']};
                selection-color: #FFFFFF;
                border: 1px solid {self.colores['bg_terciario']};
                outline: none;
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                background-color: {self.colores['bg_secundario']};
                color: #FFFFFF;
                padding: 6px 10px;
                min-height: 22px;
            }}
            QComboBox QAbstractItemView::item:selected,
            QComboBox QAbstractItemView::item:hover {{
                background-color: {self.colores['acento']};
                color: #FFFFFF;
            }}
        """

    def _estilo_btn_speed_azul(self) -> str:
        return """
            QPushButton {
                background-color: #0284C7;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
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
            return """
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.04);
                    color: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                    padding: 8px;
                }
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
            return """
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.04);
                    color: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                    padding: 8px;
                }
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

    # ── CAMBIO DE MODO (EXCLUSIÓN MUTUA ENTRE OP Y SPEED) ────────────────────
    def _on_clicker_mode_changed(self, index: int):
        """
        Al cambiar entre OP Auto Clicker 4.0 (0) y Speed AutoClicker (1):
        1. Detiene inmediatamente cualquier ejecución activa.
        2. Desactiva el listener de atajos del otro modo para que no se dupliquen.
        3. Muestra únicamente la interfaz del autoclicker seleccionado.
        """
        if self.worker.running:
            self.worker.stop()

        if index == 0:
            # Activar OP Auto Clicker 4.0 y desactivar Speed AutoClicker
            self.speed_hotkey_listener.cancel_capturing()
            self.speed_hotkey_listener.enabled = False
            self.op_hotkey_listener.enabled = True
            self.stacked_modes.setCurrentIndex(0)
        else:
            # Activar Speed AutoClicker y desactivar OP Auto Clicker 4.0
            self.op_hotkey_listener.cancel_capturing()
            self.op_hotkey_listener.enabled = False
            self.speed_hotkey_listener.enabled = True
            self.stacked_modes.setCurrentIndex(1)

    # ── LÓGICA DE SPEED AUTOCLICKER ──────────────────────────────────────────
    def _on_mouse_graphic_clicked(self, btn: str):
        if btn == "left":
            self.rb_speed_lbutton.setChecked(True)
        elif btn == "middle":
            self.rb_speed_mbutton.setChecked(True)
        elif btn == "right":
            self.rb_speed_rbutton.setChecked(True)

    def _on_speed_unlimited_toggled(self, checked: bool):
        self.spin_speed_cps.setEnabled(not checked)
        self.spin_speed_duty.setEnabled(not checked)
        self._actualizar_label_click_wait()

    def _actualizar_label_click_wait(self):
        if self.chk_speed_unlimited.isChecked():
            self.lbl_click_wait.setText("Click / Wait: 0.5 ms / 0.5 ms (Unlimited)")
            return
        cps = max(0.1, self.spin_speed_cps.value())
        period_ms = 1000.0 / cps
        duty = self.spin_speed_duty.value() / 100.0
        click_ms = period_ms * duty
        wait_ms = period_ms * (1.0 - duty)
        self.lbl_click_wait.setText(f"Click / Wait: {click_ms:.1f} ms / {wait_ms:.1f} ms")

    def _toggle_speed_key_select(self):
        # Si acaba de terminar una captura con clic izquierdo (LButton) hace menos de 350ms,
        # ignorar el evento clicked de soltar el botón sobre 'SELECT...' para no reabrir la captura.
        if time.perf_counter() - self._last_speed_capture_ts < 0.35:
            return
        if not self.speed_is_capturing_key:
            self.speed_is_capturing_key = True
            self.btn_speed_select_key.setText("ESC = CANCEL")
            self.lbl_speed_key_box.setText("Press key, mouse or pad...")
            self.speed_hotkey_listener.start_capturing()

    def _cancel_speed_key_select(self):
        self.speed_is_capturing_key = False
        self._last_speed_capture_ts = time.perf_counter()
        self.speed_hotkey_listener.cancel_capturing()
        self.btn_speed_select_key.setText("SELECT...")
        self.lbl_speed_key_box.setText(self.speed_hotkey)

    def _on_speed_key_captured(self, vk: int, key_name: str):
        if not self.speed_is_capturing_key:
            return
        self.speed_is_capturing_key = False
        self._last_speed_capture_ts = time.perf_counter()
        self.btn_speed_select_key.setText("SELECT...")
        self._registrar_speed_hotkey(key_name)

    def _registrar_speed_hotkey(self, hotkey_name: str):
        if self.speed_hotkey:
            self.speed_hotkey_listener.unregister_hotkey(self.speed_hotkey)
        self.speed_hotkey = hotkey_name
        self.lbl_speed_key_box.setText(hotkey_name)
        self.btn_speed_start.setText(f"▶ Start ({hotkey_name})")
        self.btn_speed_stop.setText(f"⏹ Stop ({hotkey_name})")
        self.speed_hotkey_listener.register_hotkey(
            hotkey_name,
            on_down=self._on_speed_hotkey_down,
            on_up=self._on_speed_hotkey_up
        )

    def _on_speed_hotkey_down(self):
        if self.stacked_modes.currentIndex() != 1:
            return
        if self.rb_speed_hold.isChecked():
            if not self.worker.running:
                self.start_clicker()
        else:
            if self.worker.running:
                self.stop_clicker()
            else:
                self.start_clicker()

    def _on_speed_hotkey_up(self):
        if self.stacked_modes.currentIndex() != 1:
            return
        if self.rb_speed_hold.isChecked() and self.worker.running:
            self.stop_clicker()

    def _abrir_choose_apps(self):
        dlg = ChooseAppsDialog(self.speed_allowed_apps, self.colores, self)
        if dlg.exec():
            self.speed_allowed_apps = dlg.selected_apps
            if self.speed_allowed_apps:
                self.btn_choose_apps.setText(f"APPS ({len(self.speed_allowed_apps)})")
            else:
                self.btn_choose_apps.setText("CHOOSE APPS")

    def _reset_speed_settings(self):
        self.stop_clicker()
        self._registrar_speed_hotkey("MButton")
        self.rb_speed_hold.setChecked(True)
        self.rb_speed_lbutton.setChecked(True)
        self.mouse_visual.set_selected_button("left")
        self.spin_speed_cps.setValue(10.00)
        self.chk_speed_unlimited.setChecked(False)
        self.chk_speed_random.setChecked(False)
        self.spin_speed_duty.setValue(50.00)
        self.chk_speed_limit.setChecked(False)
        self.spin_speed_max_clicks.setValue(1000)
        self.speed_allowed_apps = []
        self.btn_choose_apps.setText("CHOOSE APPS")
        self._actualizar_label_click_wait()

    # ── LÓGICA DE OP AUTO CLICKER 4.0 ────────────────────────────────────────
    def _registrar_op_hotkey(self, hotkey_name: str):
        if self.op_hotkey:
            self.op_hotkey_listener.unregister_hotkey(self.op_hotkey)
        self.op_hotkey = hotkey_name
        self.btn_op_start.setText(f"Start ({hotkey_name})")
        self.btn_op_stop.setText(f"Stop ({hotkey_name})")
        self.op_hotkey_listener.register_hotkey(hotkey_name, on_down=self._on_op_hotkey_toggle, on_up=None)

    def _on_op_hotkey_toggle(self):
        if self.stacked_modes.currentIndex() != 0:
            return
        if self.worker.running:
            self.stop_clicker()
        else:
            self.start_clicker()

    def _abrir_dialogo_hotkey(self):
        dlg = HotkeySettingDialog(
            current_key=self.op_hotkey,
            listener=self.op_hotkey_listener,
            colores=self.colores,
            parent=self
        )
        if dlg.exec():
            self._registrar_op_hotkey(dlg.selected_key)

    def _abrir_record_playback(self):
        p = self.parentWidget()
        while p:
            if hasattr(p, "tabs"):
                p.tabs.setCurrentIndex(2)
                break
            p = p.parentWidget()

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

    def _aplicar_preset(self, index: int):
        if index == 0:
            return
        if index == 1:  # Minecraft PvP 16 CPS
            self.spin_hours.setValue(0)
            self.spin_mins.setValue(0)
            self.spin_secs.setValue(0)
            self.spin_ms.setValue(62)
            self.chk_random_offset.setChecked(True)
            self.spin_random_offset.setValue(10)
            self.combo_btn.setCurrentText("Left")
            self.combo_type.setCurrentText("Single")
            self.spin_speed_cps.setValue(16.00)
            self.chk_speed_random.setChecked(True)
        elif index == 2:  # Roblox AFK 100 ms
            self.spin_hours.setValue(0)
            self.spin_mins.setValue(0)
            self.spin_secs.setValue(0)
            self.spin_ms.setValue(100)
            self.chk_random_offset.setChecked(False)
            self.spin_speed_cps.setValue(10.00)
            self.chk_speed_random.setChecked(False)
        elif index == 3:  # Ultra Speed 100 CPS
            self.spin_ms.setValue(10)
            self.spin_speed_cps.setValue(100.00)
        elif index == 4:  # Doble Clic
            self.spin_ms.setValue(80)
            self.combo_type.setCurrentText("Double")
        elif index == 5:  # Clic Derecho Spammer
            self.spin_ms.setValue(50)
            self.combo_btn.setCurrentText("Right")
            self.rb_speed_rbutton.setChecked(True)

    # ── ARRANQUE Y PARADA DEL MOTOR ACTIVO ───────────────────────────────────
    def start_clicker(self):
        if self.worker.running:
            return
        self._aplicar_configuracion()
        if self.chk_minimize.isChecked():
            win = self.window()
            if win:
                win.showMinimized()
        self.worker.start()

    def stop_clicker(self):
        if not self.worker.running:
            return
        self.worker.stop()

    def stop_all(self):
        self.stop_clicker()

    def _aplicar_configuracion(self):
        if self.stacked_modes.currentIndex() == 1:
            # Configurar Speed AutoClicker
            self.worker.engine_type = "speed"
            if self.rb_speed_lbutton.isChecked():
                self.worker.button = "left"
            elif self.rb_speed_mbutton.isChecked():
                self.worker.button = "middle"
            else:
                self.worker.button = "right"

            self.worker.speed_cps = self.spin_speed_cps.value()
            self.worker.speed_unlimited = self.chk_speed_unlimited.isChecked()
            self.worker.speed_random = self.chk_speed_random.isChecked()
            self.worker.speed_duty_cycle = self.spin_speed_duty.value()
            self.worker.speed_limit_enabled = self.chk_speed_limit.isChecked()
            self.worker.speed_max_clicks = self.spin_speed_max_clicks.value()
            self.worker.allowed_apps = list(self.speed_allowed_apps)
        else:
            # Configurar OP Auto Clicker 4.0
            self.worker.engine_type = "op"
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

            if self.rb_rep_count.isChecked():
                self.worker.repeat_mode = "count"
                self.worker.target_count = self.spin_target_count.value()
            else:
                self.worker.repeat_mode = "infinite"

            if self.rb_pos_fixed.isChecked():
                self.worker.location_mode = "fixed"
                self.worker.fixed_x = self.spin_x.value()
                self.worker.fixed_y = self.spin_y.value()
                self.worker.lock_cursor = self.chk_lock_cursor.isChecked()
            else:
                self.worker.location_mode = "dynamic"
                self.worker.lock_cursor = False

    def _on_worker_started(self):
        self.lbl_status.setText("● EN EJECUCIÓN")
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(16, 185, 129, 0.15);
            color: {self.colores['exito']};
            border: 1px solid {self.colores['exito']};
            border-radius: 6px;
            padding: 4px 12px;
        """)

        for btn_s, btn_p in ((self.btn_op_start, self.btn_op_stop), (self.btn_speed_start, self.btn_speed_stop)):
            btn_s.setEnabled(False)
            btn_s.setStyleSheet(self._estilo_btn_start(activo=False))
            btn_p.setEnabled(True)
            btn_p.setStyleSheet(self._estilo_btn_stop(activo=True))

        if self.chk_sound.isChecked():
            play_sound_feedback("start")

    def _on_worker_stopped(self):
        self.lbl_status.setText("● DETENIDO")
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(239, 68, 68, 0.15);
            color: {self.colores['error']};
            border: 1px solid {self.colores['error']};
            border-radius: 6px;
            padding: 4px 12px;
        """)

        for btn_s, btn_p in ((self.btn_op_start, self.btn_op_stop), (self.btn_speed_start, self.btn_speed_stop)):
            btn_s.setEnabled(True)
            btn_s.setStyleSheet(self._estilo_btn_start(activo=True))
            btn_p.setEnabled(False)
            btn_p.setStyleSheet(self._estilo_btn_stop(activo=False))

        if self.chk_sound.isChecked():
            play_sound_feedback("stop")

    def _on_click_update(self, total: int, cps: float):
        self.lbl_stats_clicks.setText(f"Clics: {total:,}")
        self.lbl_stats_cps.setText(f"CPS: {cps:.1f}")

    def _actualizar_mouse_pos_label(self):
        x, y = get_cursor_pos()
        self.lbl_stats_pos.setText(f"Ratón: X={x}, Y={y}")

    def _reset_stats(self):
        self.lbl_stats_clicks.setText("Clics: 0")
        self.lbl_stats_cps.setText("CPS: 0.0")

    def cleanup(self):
        self.mouse_pos_timer.stop()
        self.picker_timer.stop()
        if hasattr(self, "worker") and self.worker.running:
            self.worker.stop()
        if hasattr(self, "op_hotkey_listener"):
            self.op_hotkey_listener.stop()
        if hasattr(self, "speed_hotkey_listener"):
            self.speed_hotkey_listener.stop()
