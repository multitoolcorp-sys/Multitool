import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSlider,
    QPushButton, QFrame, QSizePolicy, QButtonGroup
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class ConsolaArcadeSubmodule(QWidget):
    """Submódulo 1: Consola Arcade Retro con Monitor CRT, Controles Zoom/Scanlines, Play/Pausa & Selector de Juegos"""
    def __init__(self, parent, context, colores, callbacks, canvas=None, canvas_widget=None):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.canvas = canvas or canvas_widget or getattr(parent, "canvas", None)
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.scanlines_active = True

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # ── Panel Izquierdo: Monitor CRT, Barra de Herramientas CRT & HUD ──
        left_panel = QVBoxLayout()
        left_panel.setSpacing(8)

        # Barra superior de visualización CRT (Zoom & Scanlines)
        crt_toolbar = QFrame()
        crt_toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 4px;
            }}
            QPushButton {{
                background-color: {bg_terc};
                color: #C8CCD0;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {acento};
                color: white;
            }}
            QPushButton:checked {{
                background-color: {acento};
                color: white;
                border: 1px solid white;
            }}
        """)
        tb_layout = QHBoxLayout(crt_toolbar)
        tb_layout.setContentsMargins(6, 4, 6, 4)
        tb_layout.setSpacing(8)

        lbl_zoom = QLabel("🔍 ESCALADO:")
        lbl_zoom.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        lbl_zoom.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; border: none;")
        tb_layout.addWidget(lbl_zoom)

        self.zoom_group = QButtonGroup(self)
        self.btn_scale_fit = QPushButton("Ajustar")
        self.btn_scale_fit.setCheckable(True)
        self.btn_scale_fit.setChecked(True)
        self.btn_scale_fit.clicked.connect(lambda: self._on_scale_clicked("fit"))
        self.zoom_group.addButton(self.btn_scale_fit)
        tb_layout.addWidget(self.btn_scale_fit)

        self.btn_scale_1x = QPushButton("1x (Nativo)")
        self.btn_scale_1x.setCheckable(True)
        self.btn_scale_1x.clicked.connect(lambda: self._on_scale_clicked("1x"))
        self.zoom_group.addButton(self.btn_scale_1x)
        tb_layout.addWidget(self.btn_scale_1x)

        self.btn_scale_2x = QPushButton("2x (HD)")
        self.btn_scale_2x.setCheckable(True)
        self.btn_scale_2x.clicked.connect(lambda: self._on_scale_clicked("2x"))
        self.zoom_group.addButton(self.btn_scale_2x)
        tb_layout.addWidget(self.btn_scale_2x)

        tb_layout.addStretch()

        # Botón de Scanlines CRT
        self.btn_scanlines = QPushButton("📺 Scanlines: ON")
        self.btn_scanlines.setToolTip("Activar/Desactivar líneas de barrido de fósforo CRT")
        self.btn_scanlines.clicked.connect(self._toggle_scanlines)
        tb_layout.addWidget(self.btn_scanlines)

        left_panel.addWidget(crt_toolbar)

        # Marco del Monitor CRT
        self.monitor_frame = QFrame()
        self.monitor_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #07070A;
                border: 2px solid {acento};
                border-radius: 12px;
            }}
        """)
        mon_lay = QVBoxLayout(self.monitor_frame)
        mon_lay.setContentsMargins(8, 8, 8, 8)
        mon_lay.addWidget(self.canvas, 1)

        left_panel.addWidget(self.monitor_frame, 1)

        # Barra de Estado Retro HUD (Inferior)
        hud_frame = QFrame()
        hud_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }}
        """)
        hud_lay = QHBoxLayout(hud_frame)
        hud_lay.setContentsMargins(10, 6, 10, 6)
        hud_lay.setSpacing(15)

        self.status_bar = QLabel("Estado: Listo")
        self.status_bar.setFont(QFont("Consolas", 10))
        self.status_bar.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; border: none;")
        hud_lay.addWidget(self.status_bar, 1)

        self.fps_badge = QLabel("⚡ 60 FPS")
        self.fps_badge.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.fps_badge.setStyleSheet(f"color: {exito}; border: none;")
        hud_lay.addWidget(self.fps_badge)

        self.audio_badge = QLabel("🔊 Audio: ON")
        self.audio_badge.setFont(QFont("Consolas", 10))
        self.audio_badge.setStyleSheet(f"color: {acento}; border: none;")
        hud_lay.addWidget(self.audio_badge)

        left_panel.addWidget(hud_frame)
        layout.addLayout(left_panel, 1)

        # ── Panel Derecho: Mandos & Configuración Rápidas (290px) ──
        self.right_panel = QFrame()
        self.right_panel.setFixedWidth(290)
        self.right_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid {bg_terc};
                border-radius: 12px;
            }}
            QLabel {{ color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px; font-weight: bold; }}
            QComboBox {{
                background-color: {bg_terc}; color: white; border-radius: 6px; padding: 6px; border: 1px solid {bg_terc};
            }}
            QPushButton {{
                background-color: {bg_terc}; color: white; border-radius: 6px; padding: 8px 12px; font-weight: bold; border: none;
            }}
            QPushButton:hover {{ background-color: {acento}; }}
        """)

        r_lay = QVBoxLayout(self.right_panel)
        r_lay.setContentsMargins(15, 15, 15, 15)
        r_lay.setSpacing(12)

        # Título
        tit = QLabel("👾 ARCADE CONSOLE")
        tit.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        tit.setStyleSheet(f"color: {acento}; border: none;")
        tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r_lay.addWidget(tit)

        # Juegos Pre-instalados
        r_lay.addWidget(QLabel("JUEGOS PRE-INSTALADOS CHIP-8"))
        self.cb_juegos = QComboBox()
        self.cb_juegos.addItems(["Maze (Generador)", "Pong (Clásico)", "Brix (Ladrillos)", "Tetris", "Space Invaders"])
        self.cb_juegos.currentIndexChanged.connect(self.callbacks.get("on_game_changed", lambda i: None))
        r_lay.addWidget(self.cb_juegos)

        # Botones de Ejecución
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(8)

        self.btn_play = QPushButton("▶ INICIAR")
        self.btn_play.setStyleSheet(f"background: {exito}; color: white;")
        self.btn_play.clicked.connect(self.callbacks.get("toggle_play", lambda: None))
        btn_lay.addWidget(self.btn_play)

        self.btn_reset = QPushButton("🔄 RESET")
        self.btn_reset.clicked.connect(self.callbacks.get("reset_cpu", lambda: None))
        btn_lay.addWidget(self.btn_reset)
        r_lay.addLayout(btn_lay)

        # Slider de Velocidad CPU
        self.speed_label = QLabel("VELOCIDAD: 600 Hz")
        r_lay.addWidget(self.speed_label)

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setMinimum(1)
        self.slider_speed.setMaximum(25)
        self.slider_speed.setValue(10)
        self.slider_speed.setStyleSheet(f"""
            QSlider::groove:horizontal {{ border: 1px solid {bg_terc}; height: 6px; background: {bg_terc}; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {acento}; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; }}
        """)
        self.slider_speed.valueChanged.connect(self.callbacks.get("on_speed_changed", lambda v: None))
        r_lay.addWidget(self.slider_speed)

        # Botón de Sonido
        self.btn_sound = QPushButton("🔊 SONIDO: ACTIVO")
        self.btn_sound.clicked.connect(self._toggle_sound_wrapped)
        r_lay.addWidget(self.btn_sound)

        # Tip de Uso
        tip = QLabel("🎯 Tip: Haz clic en la pantalla CRT para activar el teclado físico PC (1-F). Pulsa Esc para volver al menú de ROMs.")
        tip.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 10px; font-weight: normal; margin-top: 10px; border: none;")
        tip.setWordWrap(True)
        r_lay.addWidget(tip)

        r_lay.addStretch()
        layout.addWidget(self.right_panel)

    def _on_scale_clicked(self, mode):
        if hasattr(self.canvas, "set_scale_mode"):
            self.canvas.set_scale_mode(mode)

    def _toggle_scanlines(self):
        if hasattr(self.canvas, "toggle_scanlines"):
            enabled = self.canvas.toggle_scanlines()
            self.scanlines_active = enabled
        else:
            self.scanlines_active = not self.scanlines_active
        self.btn_scanlines.setText(f"📺 Scanlines: {'ON' if self.scanlines_active else 'OFF'}")

    def _toggle_sound_wrapped(self):
        cb = self.callbacks.get("toggle_sound")
        if cb:
            cb()
        # Actualizar badge en HUD
        if "DESACTIVADO" in self.btn_sound.text():
            self.audio_badge.setText("🔇 Audio: OFF")
            self.audio_badge.setStyleSheet("color: #F87171; border: none;")
        else:
            self.audio_badge.setText("🔊 Audio: ON")
            self.audio_badge.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; border: none;")

    def actualizar_tema(self, colores):
        """Actualiza la paleta de colores dinámicamente sin reiniciar la aplicación."""
        self.colores = colores
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        if hasattr(self, 'monitor_frame'):
            self.monitor_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: #07070A;
                    border: 2px solid {acento};
                    border-radius: 12px;
                }}
            """)
        if hasattr(self, 'right_panel'):
            self.right_panel.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_sec};
                    border: 1px solid {bg_terc};
                    border-radius: 12px;
                }}
                QLabel {{ color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px; font-weight: bold; }}
                QComboBox {{
                    background-color: {bg_terc}; color: white; border-radius: 6px; padding: 6px; border: 1px solid {bg_terc};
                }}
                QPushButton {{
                    background-color: {bg_terc}; color: white; border-radius: 6px; padding: 8px 12px; font-weight: bold; border: none;
                }}
                QPushButton:hover {{ background-color: {acento}; }}
            """)

    def cleanup(self):
        """Libera recursos y desconecta eventos si es necesario."""
        pass
