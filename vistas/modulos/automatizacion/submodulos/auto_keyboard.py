"""
auto_keyboard.py - Submódulo Pro de Automatización de Teclado (Auto Key Presser & Spammer).
Permite automatizar pulsaciones de teclas individuales, secuencias de texto,
modo mantener tecla (Hold Key para juegos/AFK) con 2 botones separados para iniciar y detener.
"""

import time
import random
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QRadioButton, QSpinBox, QTextEdit, QScrollArea,
    QLineEdit, QFrame, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont

from ..utils.input_simulator import (
    key_press, key_down, key_up, type_text, play_sound_feedback,
    GlobalHotkeyListener, VK_MAP, VK_TO_NAME
)
from ..utils.hotkey_widget import HotkeyCaptureButton

class KeyboardSignals(QObject):
    pressed = pyqtSignal(int)  # total_presses
    started = pyqtSignal()
    stopped = pyqtSignal()


class AutoKeyboardWorker:
    """Motor de automatización de teclado en hilo separado."""
    def __init__(self, signals: KeyboardSignals):
        self.signals = signals
        self.running = False
        self.thread = None

        self.mode = "single"  # "single", "text", "hold"
        self.vk_code = VK_MAP.get("ESPACIO", 0x20)
        self.text_to_type = ""
        self.press_enter_after_line = True
        self.interval_ms = 50
        self.hold_ms = 10
        self.humanize = False
        self.repeat_mode = "infinite"
        self.target_count = 100

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
        total = 0
        try:
            if self.mode == "hold":
                key_down(self.vk_code)
                while self.running:
                    time.sleep(0.05)
                key_up(self.vk_code)
                return

            delay = max(0.002, self.interval_ms / 1000.0)
            hold = max(0.001, self.hold_ms / 1000.0)

            while self.running:
                t0 = time.perf_counter()

                if self.mode == "single":
                    key_press(self.vk_code, hold_duration=hold)
                    total += 1
                    self.signals.pressed.emit(total)
                elif self.mode == "text":
                    lines = self.text_to_type.splitlines() or [""]
                    for line in lines:
                        if not self.running:
                            break
                        char_delay = 0.015 if not self.humanize else random.uniform(0.01, 0.03)
                        type_text(line, delay=char_delay)
                        if self.press_enter_after_line:
                            key_press(VK_MAP.get("ENTER", 0x0D), hold_duration=0.01)
                        total += 1
                        self.signals.pressed.emit(total)

                if self.repeat_mode == "count" and total >= self.target_count:
                    break

                actual_delay = delay
                if self.humanize:
                    actual_delay *= random.uniform(0.85, 1.25)

                elapsed = time.perf_counter() - t0
                sleep_needed = actual_delay - elapsed
                if sleep_needed > 0.002:
                    time.sleep(sleep_needed - 0.001)
                while (time.perf_counter() - t0) < actual_delay:
                    pass

        finally:
            if self.mode == "hold":
                key_up(self.vk_code)
            self.running = False
            self.signals.stopped.emit()


class TabAutoKeyboard(QWidget):
    """Interfaz gráfica responsiva para el Auto Teclado con 2 botones de acción independientes."""
    def __init__(self, parent=None, colores=None, context=None, **kwargs):
        super().__init__(parent)
        self.context = context
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#10B981", "error": "#EF4444",
        }
        self.font_family = "Segoe UI"

        self.signals = KeyboardSignals()
        self.worker = AutoKeyboardWorker(self.signals)

        self.signals.pressed.connect(self._on_press_update)
        self.signals.started.connect(self._on_worker_started)
        self.signals.stopped.connect(self._on_worker_stopped)

        # Hotkey listener global
        self.hotkey_listener = GlobalHotkeyListener()
        self.current_hotkey = "F7"
        self.target_key_name = "ESPACIO"
        self.target_vk = 0x20

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

        lbl_title = QLabel("⌨️ Auto Teclado & Spammer Pro")
        lbl_title.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none;")
        h_lay.addWidget(lbl_title)

        h_lay.addStretch()

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

        # ── 2. SELECCIÓN DE MODO ─────────────────────────────────────────────
        card_mode = self._crear_card("⚙️ Modo de Operación")
        m_lay = QHBoxLayout(card_mode)
        self.rb_mode_single = QRadioButton("Tecla Individual (Spammer)")
        self.rb_mode_text = QRadioButton("Secuencia de Texto / Frases")
        self.rb_mode_hold = QRadioButton("Mantener Tecla (Key Hold / AFK)")
        self.rb_mode_single.setChecked(True)

        for rb in (self.rb_mode_single, self.rb_mode_text, self.rb_mode_hold):
            rb.setStyleSheet(f"color: {self.colores['fg_principal']}; font-weight: 500;")
            rb.toggled.connect(self._on_mode_changed)
            m_lay.addWidget(rb)
        main_layout.addWidget(card_mode)

        # ── 3. PARÁMETROS EN GRID ─────────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(12)

        # CARD A: Tecla Objetivo con Capturador Interactivo
        self.card_input = self._crear_card("🎯 Tecla Objetivo")
        in_lay = QVBoxLayout(self.card_input)

        self.frame_single_key = QFrame()
        sk_lay = QHBoxLayout(self.frame_single_key)
        sk_lay.setContentsMargins(0, 0, 0, 0)
        sk_lay.addWidget(QLabel("Tecla a pulsar:"))

        self.btn_pick_key = HotkeyCaptureButton(
            default_key="ESPACIO",
            listener=self.hotkey_listener,
            colores=self.colores,
            parent=self
        )
        self.btn_pick_key.hotkey_changed.connect(self._on_target_key_changed)
        sk_lay.addWidget(self.btn_pick_key, 1)
        in_lay.addWidget(self.frame_single_key)

        # Frame para Texto
        self.frame_text = QFrame()
        self.frame_text.setVisible(False)
        tx_lay = QVBoxLayout(self.frame_text)
        tx_lay.setContentsMargins(0, 0, 0, 0)
        self.edit_text = QTextEdit()
        self.edit_text.setPlaceholderText("Escribe el texto a enviar repetidamente...")
        self.edit_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        self.edit_text.setFixedHeight(75)
        tx_lay.addWidget(self.edit_text)
        self.chk_enter_line = QCheckBox("Enviar 'Enter' al final de cada frase")
        self.chk_enter_line.setChecked(True)
        self.chk_enter_line.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        tx_lay.addWidget(self.chk_enter_line)
        in_lay.addWidget(self.frame_text)

        grid.addWidget(self.card_input, 0, 0)

        # CARD B: Intervalo y Velocidad
        card_timing = self._crear_card("⏱️ Temporización y Retardo")
        t_lay = QGridLayout(card_timing)
        t_lay.setSpacing(8)

        t_lay.addWidget(QLabel("Intervalo:"), 0, 0)
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(2, 60000)
        self.spin_interval.setValue(50)
        self.spin_interval.setSuffix(" ms")
        self.spin_interval.setStyleSheet(self._estilo_input())
        t_lay.addWidget(self.spin_interval, 0, 1)

        t_lay.addWidget(QLabel("Sostenimiento (Hold):"), 1, 0)
        self.spin_hold = QSpinBox()
        self.spin_hold.setRange(1, 5000)
        self.spin_hold.setValue(10)
        self.spin_hold.setSuffix(" ms")
        self.spin_hold.setStyleSheet(self._estilo_input())
        t_lay.addWidget(self.spin_hold, 1, 1)

        self.chk_humanize = QCheckBox("Factor humano (±15% jitter anti-bot)")
        self.chk_humanize.setChecked(False)
        self.chk_humanize.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        t_lay.addWidget(self.chk_humanize, 2, 0, 1, 2)

        grid.addWidget(card_timing, 0, 1)

        # CARD C: Repetición
        card_rep = self._crear_card("🔁 Límite de Repetición")
        rep_lay = QVBoxLayout(card_rep)

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
        self.spin_target_count = QSpinBox()
        self.spin_target_count.setRange(1, 1000000)
        self.spin_target_count.setValue(50)
        self.spin_target_count.setSuffix(" veces")
        self.spin_target_count.setStyleSheet(self._estilo_input())
        rc_lay.addWidget(self.spin_target_count)
        rep_lay.addWidget(self.frame_rep_count)

        grid.addWidget(card_rep, 1, 0, 1, 2)
        main_layout.addLayout(grid)

        # ── 4. CONTROLES DE ACCIÓN CON 2 BOTONES INDEPENDIENTES ───────────────
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

        hk_box = QVBoxLayout()
        lbl_hk = QLabel("Atajo Teclado:")
        lbl_hk.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        hk_box.addWidget(lbl_hk)

        self.btn_hotkey = HotkeyCaptureButton(
            default_key="F7",
            listener=self.hotkey_listener,
            colores=self.colores,
            parent=self
        )
        self.btn_hotkey.hotkey_changed.connect(self._on_hotkey_captured)
        hk_box.addWidget(self.btn_hotkey)
        c_lay.addLayout(hk_box)

        c_lay.addSpacing(6)

        # BOTÓN 1: INICIAR (Habilitado inicialmente, se apaga al hacer clic)
        self.btn_start = QPushButton(f"▶ INICIAR ({self.current_hotkey})")
        self.btn_start.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setFixedHeight(48)
        self.btn_start.setStyleSheet(self._estilo_btn_iniciar(habilitado=True))
        self.btn_start.clicked.connect(self.start_keyboard)
        c_lay.addWidget(self.btn_start, 1)

        # BOTÓN 2: DETENER (Deshabilitado inicialmente, se enciende al iniciar)
        self.btn_stop = QPushButton(f"⏹ DETENER ({self.current_hotkey})")
        self.btn_stop.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setFixedHeight(48)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(self._estilo_btn_detener(habilitado=False))
        self.btn_stop.clicked.connect(self.stop_keyboard)
        c_lay.addWidget(self.btn_stop, 1)

        main_layout.addWidget(ctrl_card)

        # ── 5. ESTADÍSTICAS ───────────────────────────────────────────────────
        stats_frame = QFrame()
        stats_lay = QHBoxLayout(stats_frame)
        self.lbl_stats_count = QLabel("Pulsaciones enviadas: 0")
        self.lbl_stats_count.setFont(QFont(self.font_family, 9))
        self.lbl_stats_count.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        stats_lay.addWidget(self.lbl_stats_count)

        btn_reset = QPushButton("🔄 Reiniciar Contador")
        btn_reset.setStyleSheet(self._estilo_boton_secundario())
        btn_reset.clicked.connect(lambda: self.lbl_stats_count.setText("Pulsaciones enviadas: 0"))
        stats_lay.addWidget(btn_reset)
        main_layout.addWidget(stats_frame)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    # ── HELPERS ──────────────────────────────────────────────────────────────
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

    def _estilo_input(self) -> str:
        return f"""
            QSpinBox {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QSpinBox:focus {{
                border: 1px solid {self.colores['acento']};
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
                QPushButton:hover {{ background-color: #059669; }}
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
                QPushButton:hover {{ background-color: #DC2626; }}
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
            QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.15); }}
        """

    def _on_mode_changed(self):
        is_text = self.rb_mode_text.isChecked()
        self.frame_single_key.setVisible(not is_text)
        self.frame_text.setVisible(is_text)

    def _on_repeat_mode_toggled(self, checked: bool):
        self.frame_rep_count.setVisible(self.rb_rep_count.isChecked())

    def _on_target_key_changed(self, key_name: str, vk: int):
        self.target_key_name = key_name
        self.target_vk = vk if vk else VK_MAP.get(key_name.upper(), 0x20)

    def _on_hotkey_captured(self, new_hk: str, vk: int):
        self._registrar_hotkey(new_hk)

    def _registrar_hotkey(self, hotkey_name: str):
        if self.current_hotkey:
            self.hotkey_listener.unregister_hotkey(self.current_hotkey)
        self.current_hotkey = hotkey_name
        self.btn_start.setText(f"▶ INICIAR ({hotkey_name})")
        self.btn_stop.setText(f"⏹ DETENER ({hotkey_name})")
        self.hotkey_listener.register_hotkey(hotkey_name, on_down=self._on_hotkey_toggle, on_up=None)

    def _on_hotkey_toggle(self):
        if self.worker.running:
            self.stop_keyboard()
        else:
            self.start_keyboard()

    def start_keyboard(self):
        """Inicia el auto teclado: apaga el botón Iniciar y enciende Detener."""
        if self.worker.running:
            return
        self._aplicar_configuracion()
        self.worker.start()

    def stop_keyboard(self):
        """Detiene el auto teclado: apaga el botón Detener y enciende Iniciar."""
        if not self.worker.running:
            return
        self.worker.stop()

    def _aplicar_configuracion(self):
        if self.rb_mode_single.isChecked():
            self.worker.mode = "single"
        elif self.rb_mode_text.isChecked():
            self.worker.mode = "text"
        else:
            self.worker.mode = "hold"

        self.worker.vk_code = self.target_vk
        self.worker.text_to_type = self.edit_text.toPlainText()
        self.worker.press_enter_after_line = self.chk_enter_line.isChecked()
        self.worker.interval_ms = self.spin_interval.value()
        self.worker.hold_ms = self.spin_hold.value()
        self.worker.humanize = self.chk_humanize.isChecked()

        if self.rb_rep_count.isChecked():
            self.worker.repeat_mode = "count"
            self.worker.target_count = self.spin_target_count.value()
        else:
            self.worker.repeat_mode = "infinite"

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

        # Separación clara de 2 botones: encender Iniciar y apagar Detener
        self.btn_start.setEnabled(True)
        self.btn_start.setStyleSheet(self._estilo_btn_iniciar(habilitado=True))

        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(self._estilo_btn_detener(habilitado=False))

        play_sound_feedback("stop")

    def _on_press_update(self, total: int):
        self.lbl_stats_count.setText(f"Pulsaciones enviadas: {total:,}")

    def cleanup(self):
        if hasattr(self, "worker") and self.worker.running:
            self.worker.stop()
        if hasattr(self, "hotkey_listener"):
            self.hotkey_listener.stop()
