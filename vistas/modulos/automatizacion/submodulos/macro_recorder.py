"""
macro_recorder.py - Submódulo de Grabación y Reproducción de Macros para Ratón y Teclado.
Permite grabar secuencias de acciones en tiempo real, editarlas, guardarlas en archivos .mtmacro,
y reproducirlas con aceleradores de velocidad y bucles con atajos interactivos configurables.
"""

import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QFrame, QFileDialog,
    QProgressBar, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor

from ..utils.macro_engine import (
    MacroRecorder, MacroPlayer, MacroEvent,
    save_macro_file, load_macro_file
)
from ..utils.input_simulator import GlobalHotkeyListener
from ..utils.hotkey_widget import HotkeyCaptureButton

class MacroSignals(QObject):
    event_recorded = pyqtSignal(object)
    playback_progress = pyqtSignal(int, int)
    playback_finished = pyqtSignal()


class TabMacroRecorder(QWidget):
    """Interfaz gráfica responsiva para el Grabador y Reproductor de Macros."""
    def __init__(self, parent=None, colores=None, context=None, **kwargs):
        super().__init__(parent)
        self.context = context
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171",
        }
        self.font_family = "Segoe UI"

        self.signals = MacroSignals(self)
        self.recorder = MacroRecorder()
        self.player = MacroPlayer()

        self.recorded_events: list[MacroEvent] = []

        # Conectar señales con QueuedConnection estricto para evitar problemas de hilos cruzados
        self.signals.event_recorded.connect(self._on_event_recorded_ui, Qt.ConnectionType.QueuedConnection)
        self.signals.playback_progress.connect(self._on_playback_progress_ui, Qt.ConnectionType.QueuedConnection)
        self.signals.playback_finished.connect(self._on_playback_finished_ui, Qt.ConnectionType.QueuedConnection)

        self.recorder.on_event_recorded = lambda evt: self.signals.event_recorded.emit(evt)
        self.player.on_progress = lambda curr, total: self.signals.playback_progress.emit(curr, total)
        self.player.on_finished = lambda: self.signals.playback_finished.emit()

        # Hotkeys globales interactivos
        self.hotkey_listener = GlobalHotkeyListener()
        self.hotkey_record = "F8"
        self.hotkey_play = "F9"

        self._init_ui()
        self._registrar_hotkeys()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # ── 1. HEADER CARD ───────────────────────────────────────────────────
        header_card = QFrame()
        header_card.setObjectName("MacroHeader")
        header_card.setStyleSheet(f"""
            QFrame#MacroHeader {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 10px;
            }}
            QLabel {{ border: none; background: transparent; padding: 0px; }}
        """)
        h_lay = QHBoxLayout(header_card)
        h_lay.setContentsMargins(10, 6, 10, 6)

        lbl_title = QLabel("🎬 Grabador y Reproductor de Macros")
        lbl_title.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none;")
        h_lay.addWidget(lbl_title)

        h_lay.addStretch()

        self.lbl_status = QLabel("● INACTIVO")
        self.lbl_status.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, 0.06);
            color: {self.colores['fg_secundario']};
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 4px 12px;
        """)
        h_lay.addWidget(self.lbl_status)
        main_layout.addWidget(header_card)

        # ── 2. BARRA PRINCIPAL DE CONTROLES ──────────────────────────────────
        ctrl_bar = QFrame()
        ctrl_bar.setObjectName("MacroCtrlBar")
        ctrl_bar.setStyleSheet(f"""
            QFrame#MacroCtrlBar {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 8px;
            }}
            QLabel {{ border: none; background: transparent; padding: 0px; }}
        """)
        cb_lay = QHBoxLayout(ctrl_bar)
        cb_lay.setSpacing(8)

        # Botón Grabar
        self.btn_record = QPushButton(f"🔴 Grabar ({self.hotkey_record})")
        self.btn_record.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_record.setStyleSheet(self._estilo_btn_record(activo=False))
        self.btn_record.clicked.connect(self.toggle_record)
        cb_lay.addWidget(self.btn_record)

        # Botón Atajo de Grabación
        self.btn_hk_record = HotkeyCaptureButton(
            default_key="F8",
            listener=self.hotkey_listener,
            colores=self.colores,
            parent=self
        )
        self.btn_hk_record.hotkey_changed.connect(self._on_record_hk_changed)
        cb_lay.addWidget(self.btn_hk_record)

        cb_lay.addSpacing(6)

        # Botón Reproducir
        self.btn_play = QPushButton(f"▶ Reproducir ({self.hotkey_play})")
        self.btn_play.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_play.setStyleSheet(self._estilo_btn_play(activo=False))
        self.btn_play.clicked.connect(self.toggle_playback)
        cb_lay.addWidget(self.btn_play)

        # Botón Atajo de Reproducción
        self.btn_hk_play = HotkeyCaptureButton(
            default_key="F9",
            listener=self.hotkey_listener,
            colores=self.colores,
            parent=self
        )
        self.btn_hk_play.hotkey_changed.connect(self._on_play_hk_changed)
        cb_lay.addWidget(self.btn_hk_play)

        cb_lay.addStretch()

        # Opciones de Grabación
        self.chk_record_clicks = QCheckBox("Clics")
        self.chk_record_clicks.setChecked(True)
        self.chk_record_keys = QCheckBox("Teclas")
        self.chk_record_keys.setChecked(True)
        self.chk_record_moves = QCheckBox("Movimientos")
        self.chk_record_moves.setChecked(False)

        for chk in (self.chk_record_clicks, self.chk_record_keys, self.chk_record_moves):
            chk.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
            cb_lay.addWidget(chk)

        cb_lay.addSpacing(8)

        # Botones de Archivo
        btn_save = QPushButton("💾 Guardar")
        btn_save.setStyleSheet(self._estilo_btn_secundario())
        btn_save.clicked.connect(self._guardar_macro)
        cb_lay.addWidget(btn_save)

        btn_load = QPushButton("📂 Cargar")
        btn_load.setStyleSheet(self._estilo_btn_secundario())
        btn_load.clicked.connect(self._cargar_macro)
        cb_lay.addWidget(btn_load)

        btn_clear = QPushButton("🗑 Limpiar")
        btn_clear.setStyleSheet(self._estilo_btn_secundario())
        btn_clear.clicked.connect(self._limpiar_macro)
        cb_lay.addWidget(btn_clear)

        main_layout.addWidget(ctrl_bar)

        # ── 3. AJUSTES DE REPRODUCCIÓN (VELOCIDAD & BUCLES) ────────────────────
        play_cfg_frame = QFrame()
        play_cfg_frame.setObjectName("MacroPlayCfg")
        play_cfg_frame.setStyleSheet(f"""
            QFrame#MacroPlayCfg {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 6px 12px;
            }}
            QLabel {{ border: none; background: transparent; padding: 0px; }}
        """)
        pc_lay = QHBoxLayout(play_cfg_frame)
        pc_lay.setSpacing(12)

        pc_lay.addWidget(QLabel("Velocidad:"))
        self.combo_speed = QComboBox()
        self.combo_speed.addItems(["0.25x", "0.5x", "1.0x (Normal)", "1.5x", "2.0x", "3.0x", "5.0x", "10.0x"])
        self.combo_speed.setCurrentText("1.0x (Normal)")
        self.combo_speed.setStyleSheet(self._estilo_combo())
        pc_lay.addWidget(self.combo_speed)

        pc_lay.addWidget(QLabel("Bucle:"))
        self.spin_loops = QSpinBox()
        self.spin_loops.setRange(1, 10000)
        self.spin_loops.setValue(1)
        self.spin_loops.setSuffix(" veces")
        self.spin_loops.setStyleSheet(self._estilo_combo())
        pc_lay.addWidget(self.spin_loops)

        pc_lay.addWidget(QLabel("Espera:"))
        self.spin_loop_delay = QDoubleSpinBox()
        self.spin_loop_delay.setRange(0.0, 60.0)
        self.spin_loop_delay.setValue(0.5)
        self.spin_loop_delay.setSuffix(" s")
        self.spin_loop_delay.setStyleSheet(self._estilo_combo())
        pc_lay.addWidget(self.spin_loop_delay)

        pc_lay.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(140)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.colores['bg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 4px;
                text-align: center;
                color: white;
                font-size: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {self.colores['acento']};
                border-radius: 3px;
            }}
        """)
        pc_lay.addWidget(self.progress_bar)

        main_layout.addWidget(play_cfg_frame)

        # ── 4. TABLA DE EVENTOS ───────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["#", "Tiempo (s)", "Acción", "Detalle / Parámetros", "Coordenadas (X, Y)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                gridline-color: rgba(255, 255, 255, 0.05);
            }}
            QHeaderView::section {{
                background-color: {self.colores['bg_terciario']};
                color: {self.colores['fg_secundario']};
                font-weight: bold;
                border: none;
                padding: 6px;
            }}
            QTableWidget::item:selected {{
                background-color: {self.colores['acento']};
                color: white;
            }}
        """)
        main_layout.addWidget(self.table, 1)

    # ── ESTILOS ───────────────────────────────────────────────────────────────
    def _estilo_combo(self) -> str:
        return f"""
            QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }}
        """

    def _estilo_btn_record(self, activo: bool) -> str:
        if activo:
            return f"""
                QPushButton {{
                    background-color: #EF4444;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 14px;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: rgba(239, 68, 68, 0.15);
                    color: #F87171;
                    border: 1px solid rgba(239, 68, 68, 0.4);
                    border-radius: 6px;
                    padding: 6px 14px;
                }}
                QPushButton:hover {{
                    background-color: rgba(239, 68, 68, 0.25);
                }}
            """

    def _estilo_btn_play(self, activo: bool) -> str:
        if activo:
            return f"""
                QPushButton {{
                    background-color: {self.colores['error']};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 14px;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: rgba(52, 211, 153, 0.15);
                    color: #34D399;
                    border: 1px solid rgba(52, 211, 153, 0.4);
                    border-radius: 6px;
                    padding: 6px 14px;
                }}
                QPushButton:hover {{
                    background-color: rgba(52, 211, 153, 0.25);
                }}
            """

    def _estilo_btn_secundario(self) -> str:
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

    # ── ACCIONES ─────────────────────────────────────────────────────────────
    def _registrar_hotkeys(self):
        self.hotkey_listener.unregister_all()
        if self.hotkey_record:
            self.hotkey_listener.register_hotkey(self.hotkey_record, self.toggle_record)
        if self.hotkey_play:
            self.hotkey_listener.register_hotkey(self.hotkey_play, self.toggle_playback)

    def _on_record_hk_changed(self, new_key: str, vk: int):
        self.hotkey_record = new_key
        self.btn_record.setText(f"🔴 Grabar ({new_key})" if not self.recorder.is_recording() else f"⏹ Detener ({new_key})")
        self._registrar_hotkeys()

    def _on_play_hk_changed(self, new_key: str, vk: int):
        self.hotkey_play = new_key
        self.btn_play.setText(f"▶ Reproducir ({new_key})" if not self.player.is_playing() else f"⏹ Detener ({new_key})")
        self._registrar_hotkeys()

    def toggle_record(self):
        if self.recorder.is_recording():
            self._detener_grabacion()
        else:
            self._iniciar_grabacion()

    def _iniciar_grabacion(self):
        if self.player.is_playing():
            self.player.stop()

        self._limpiar_macro()
        self.btn_record.setText(f"⏹ Detener ({self.hotkey_record})")
        self.btn_record.setStyleSheet(self._estilo_btn_record(activo=True))
        self.btn_play.setEnabled(False)

        self.lbl_status.setText("● GRABANDO...")
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(239, 68, 68, 0.2);
            color: #F87171;
            border: 1px solid #F87171;
            border-radius: 6px;
            padding: 4px 12px;
        """)

        self.recorder.start_recording(
            record_clicks=self.chk_record_clicks.isChecked(),
            record_moves=self.chk_record_moves.isChecked(),
            record_keys=self.chk_record_keys.isChecked()
        )

    def _detener_grabacion(self):
        self.recorded_events = self.recorder.stop_recording()
        self.btn_record.setText(f"🔴 Grabar ({self.hotkey_record})")
        self.btn_record.setStyleSheet(self._estilo_btn_record(activo=False))
        self.btn_play.setEnabled(True)

        self.lbl_status.setText(f"● GRABADO ({len(self.recorded_events)} acciones)")
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(99, 102, 241, 0.15);
            color: {self.colores['acento']};
            border: 1px solid {self.colores['acento']};
            border-radius: 6px;
            padding: 4px 12px;
        """)

    def toggle_playback(self):
        if self.player.is_playing():
            self._detener_reproduccion()
        else:
            self._iniciar_reproduccion()

    def _iniciar_reproduccion(self):
        if not self.recorded_events:
            QMessageBox.information(self, "Aviso", "No hay ninguna macro grabada para reproducir.")
            return

        if self.recorder.is_recording():
            self._detener_grabacion()

        spd_text = self.combo_speed.currentText().split()[0].replace("x", "")
        try:
            speed = float(spd_text)
        except Exception:
            speed = 1.0

        loops = self.spin_loops.value()
        delay = self.spin_loop_delay.value()

        self.btn_play.setText(f"⏹ Detener ({self.hotkey_play})")
        self.btn_play.setStyleSheet(self._estilo_btn_play(activo=True))
        self.btn_record.setEnabled(False)

        self.lbl_status.setText("● REPRODUCIENDO...")
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(52, 211, 153, 0.2);
            color: #34D399;
            border: 1px solid #34D399;
            border-radius: 6px;
            padding: 4px 12px;
        """)

        self.progress_bar.setValue(0)
        self.player.play(self.recorded_events, speed=speed, repeat_count=loops, delay_between_loops=delay)

    def _detener_reproduccion(self):
        self.player.stop()
        self._on_playback_finished_ui()

    def _on_playback_progress_ui(self, current: int, total: int):
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
            if current - 1 < self.table.rowCount():
                self.table.selectRow(current - 1)

    def _on_playback_finished_ui(self):
        self.btn_play.setText(f"▶ Reproducir ({self.hotkey_play})")
        self.btn_play.setStyleSheet(self._estilo_btn_play(activo=False))
        self.btn_record.setEnabled(True)
        self.progress_bar.setValue(100)

        self.lbl_status.setText("● LISTO")
        self.lbl_status.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, 0.06);
            color: {self.colores['fg_secundario']};
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 4px 12px;
        """)

    def _on_event_recorded_ui(self, evt: MacroEvent):
        """Se ejecuta con total seguridad en el hilo principal de Qt gracias a QueuedConnection."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        item_num = QTableWidgetItem(str(row + 1))
        item_time = QTableWidgetItem(f"+{evt.time_offset:.2f}s")
        item_action = QTableWidgetItem(evt.action)

        coords_str = "-"
        if evt.action == "click":
            detail = f"Botón {evt.params.get('button', 'left')} ({evt.params.get('click_type', 'single')})"
            coords_str = f"X: {evt.params.get('x', 0)}, Y: {evt.params.get('y', 0)}"
        elif evt.action == "move":
            detail = "Movimiento del cursor"
            coords_str = f"X: {evt.params.get('x', 0)}, Y: {evt.params.get('y', 0)}"
        elif evt.action == "key_press":
            detail = f"Tecla '{evt.params.get('key', '')}'"
        else:
            detail = str(evt.params)

        item_detail = QTableWidgetItem(detail)
        item_coords = QTableWidgetItem(coords_str)

        for col, itm in enumerate([item_num, item_time, item_action, item_detail, item_coords]):
            itm.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, col, itm)

        self.table.scrollToBottom()

    def _guardar_macro(self):
        if not self.recorded_events:
            QMessageBox.warning(self, "Aviso", "No hay eventos grabados para guardar.")
            return

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar Macro Multitool", "", "Archivos de Macro (*.mtmacro);;Todos (*.*)"
        )
        if ruta:
            p = Path(ruta)
            if not p.suffix:
                p = p.with_suffix(".mtmacro")
            if save_macro_file(p, self.recorded_events, name=p.stem):
                QMessageBox.information(self, "Éxito", f"Macro guardada correctamente en:\n{p}")

    def _cargar_macro(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Cargar Macro Multitool", "", "Archivos de Macro (*.mtmacro);;Todos (*.*)"
        )
        if ruta:
            p = Path(ruta)
            name, events = load_macro_file(p)
            if events:
                self._limpiar_macro()
                self.recorded_events = events
                for evt in events:
                    self._on_event_recorded_ui(evt)
                self.lbl_status.setText(f"● CARGADO: {name} ({len(events)} pasos)")
                QMessageBox.information(self, "Éxito", f"Macro '{name}' cargada con {len(events)} pasos.")

    def _limpiar_macro(self):
        self.recorded_events = []
        self.table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("● INACTIVO")

    def cleanup(self):
        if hasattr(self, "recorder") and self.recorder.is_recording():
            self.recorder.stop_recording()
        if hasattr(self, "player") and self.player.is_playing():
            self.player.stop()
        if hasattr(self, "hotkey_listener"):
            self.hotkey_listener.stop()
