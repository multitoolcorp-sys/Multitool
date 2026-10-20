import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QProgressBar, QSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class PomodoroSubmodule(QWidget):
    """Submódulo 4: Temporizador Pomodoro & Enfoque de Trabajo/Estudio"""
    def __init__(self, parent, context, manager, colores):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        # Tiempos por defecto (en minutos y convertidos a segundos)
        self.MODOS = {
            "trabajo": {"nombre": "🍅 Enfoque", "tiempo": 25 * 60, "color": "#F87171", "minutos": 25},
            "descanso_corto": {"nombre": "☕ Descanso Corto", "tiempo": 5 * 60, "color": "#34D399", "minutos": 5},
            "descanso_largo": {"nombre": "🌴 Descanso Largo", "tiempo": 15 * 60, "color": "#60A5FA", "minutos": 15}
        }
        self.modo_actual = "trabajo"
        self.tiempo_restante = self.MODOS["trabajo"]["tiempo"]
        self.running = False

        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("🍅 TEMPORIZADOR POMODORO & ENFOQUE")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        layout.addLayout(hdr)

        # Botones de Selección de Modo (Enfoque / Descanso Corto / Descanso Largo)
        modes_lay = QHBoxLayout()
        modes_lay.setSpacing(10)

        self.btn_m_trabajo = QPushButton(f"🍅 Enfoque ({self.MODOS['trabajo']['minutos']} min)")
        self.btn_m_trabajo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_m_trabajo.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_m_trabajo.clicked.connect(lambda: self._cambiar_modo("trabajo"))
        modes_lay.addWidget(self.btn_m_trabajo)

        self.btn_m_corto = QPushButton(f"☕ Descanso Corto ({self.MODOS['descanso_corto']['minutos']} min)")
        self.btn_m_corto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_m_corto.setFont(QFont(self.font_family, 9))
        self.btn_m_corto.clicked.connect(lambda: self._cambiar_modo("descanso_corto"))
        modes_lay.addWidget(self.btn_m_corto)

        self.btn_m_largo = QPushButton(f"🌴 Descanso Largo ({self.MODOS['descanso_largo']['minutos']} min)")
        self.btn_m_largo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_m_largo.setFont(QFont(self.font_family, 9))
        self.btn_m_largo.clicked.connect(lambda: self._cambiar_modo("descanso_largo"))
        modes_lay.addWidget(self.btn_m_largo)

        layout.addLayout(modes_lay)

        # Display Digital Central
        self.pomo_frame = QFrame()
        self.pomo_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }}
        """)
        disp_lay = QVBoxLayout(self.pomo_frame)
        disp_lay.setContentsMargins(20, 20, 20, 20)
        disp_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_modo_status = QLabel("🍅 Enfoque")
        self.lbl_modo_status.setFont(QFont(self.font_family, 14, QFont.Weight.Bold))
        self.lbl_modo_status.setStyleSheet("color: #F87171;")
        self.lbl_modo_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disp_lay.addWidget(self.lbl_modo_status)

        self.lbl_pomo_digits = QLabel("25:00")
        self.lbl_pomo_digits.setFont(QFont(self.mono_font, 52, QFont.Weight.Bold))
        self.lbl_pomo_digits.setStyleSheet("color: white; border: none; background: transparent;")
        self.lbl_pomo_digits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disp_lay.addWidget(self.lbl_pomo_digits)

        # Barra de progreso
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(8)
        self.pbar.setFixedWidth(300)
        self.pbar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.colores['bg_terciario']};
                border-radius: 4px; text-align: center; color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: #F87171; border-radius: 4px;
            }}
        """)
        disp_lay.addWidget(self.pbar)

        # Botones de Control
        ctrl_lay = QHBoxLayout()
        ctrl_lay.setSpacing(12)

        self.btn_pomo_start = QPushButton("▶ Iniciar Sesión")
        self.btn_pomo_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pomo_start.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_pomo_start.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 10px 24px; border-radius: 8px; border: none;")
        self.btn_pomo_start.clicked.connect(self._toggle_start_pause)
        ctrl_lay.addWidget(self.btn_pomo_start)

        self.btn_pomo_reset = QPushButton("🔄 Reiniciar")
        self.btn_pomo_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pomo_reset.setFont(QFont(self.font_family, 10))
        self.btn_pomo_reset.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; padding: 10px 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);")
        self.btn_pomo_reset.clicked.connect(self._reset_pomo)
        ctrl_lay.addWidget(self.btn_pomo_reset)

        disp_lay.addLayout(ctrl_lay)
        layout.addWidget(self.pomo_frame)

        # Sección de Configuración de Duraciones Personalizadas
        config_frame = QFrame()
        config_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        cfg_lay = QHBoxLayout(config_frame)
        cfg_lay.setContentsMargins(15, 8, 15, 8)
        cfg_lay.setSpacing(10)

        lbl_cfg_title = QLabel("⚙️ Configurar Minutos:")
        lbl_cfg_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_cfg_title.setStyleSheet("color: white;")
        cfg_lay.addWidget(lbl_cfg_title)

        spin_style = f"""
            QSpinBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 2px 6px; font-weight: bold;
            }}
        """

        lbl_w = QLabel("Enfoque:")
        lbl_w.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 9px;")
        self.spin_work = QSpinBox()
        self.spin_work.setRange(1, 120)
        self.spin_work.setValue(25)
        self.spin_work.setStyleSheet(spin_style)

        lbl_sb = QLabel("Descanso Corto:")
        lbl_sb.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 9px;")
        self.spin_short = QSpinBox()
        self.spin_short.setRange(1, 60)
        self.spin_short.setValue(5)
        self.spin_short.setStyleSheet(spin_style)

        lbl_lb = QLabel("Descanso Largo:")
        lbl_lb.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 9px;")
        self.spin_long = QSpinBox()
        self.spin_long.setRange(1, 90)
        self.spin_long.setValue(15)
        self.spin_long.setStyleSheet(spin_style)

        btn_apply = QPushButton("💾 Guardar Tiempos")
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_apply.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 4px 10px; border-radius: 4px; border: none;")
        btn_apply.clicked.connect(self._aplicar_duraciones_personalizadas)

        cfg_lay.addWidget(lbl_w)
        cfg_lay.addWidget(self.spin_work)
        cfg_lay.addWidget(lbl_sb)
        cfg_lay.addWidget(self.spin_short)
        cfg_lay.addWidget(lbl_lb)
        cfg_lay.addWidget(self.spin_long)
        cfg_lay.addWidget(btn_apply)

        layout.addWidget(config_frame)

        # Cuadro de Métricas Diarias
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        st_lay = QHBoxLayout(stats_frame)
        st_lay.setContentsMargins(15, 10, 15, 10)

        self.lbl_stats_txt = QLabel("🍅 Sesiones completadas hoy: 0 | ⏱️ Enfoque acumulado: 0 min")
        self.lbl_stats_txt.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_stats_txt.setStyleSheet("color: white;")
        st_lay.addWidget(self.lbl_stats_txt)

        layout.addWidget(stats_frame)

        self._actualizar_estilos_modos()
        self.refrescar_stats()

    def _aplicar_duraciones_personalizadas(self):
        w_min = self.spin_work.value()
        sb_min = self.spin_short.value()
        lb_min = self.spin_long.value()

        self.MODOS["trabajo"]["minutos"] = w_min
        self.MODOS["trabajo"]["tiempo"] = w_min * 60

        self.MODOS["descanso_corto"]["minutos"] = sb_min
        self.MODOS["descanso_corto"]["tiempo"] = sb_min * 60

        self.MODOS["descanso_largo"]["minutos"] = lb_min
        self.MODOS["descanso_largo"]["tiempo"] = lb_min * 60

        self.btn_m_trabajo.setText(f"🍅 Enfoque ({w_min} min)")
        self.btn_m_corto.setText(f"☕ Descanso Corto ({sb_min} min)")
        self.btn_m_largo.setText(f"🌴 Descanso Largo ({lb_min} min)")

        self._reset_pomo()

    def tick_100ms(self):
        if self.running and self.tiempo_restante > 0:
            self.tiempo_restante -= 0.1
            if self.tiempo_restante <= 0:
                self.tiempo_restante = 0
                self.running = False
                self.btn_pomo_start.setText("▶ Iniciar Sesión")
                if self.modo_actual == "trabajo":
                    self.manager.registrar_sesion_pomodoro(self.MODOS["trabajo"]["minutos"])
                    self._cambiar_modo("descanso_corto")
                else:
                    self._cambiar_modo("trabajo")
                self.refrescar_stats()
            self._update_display()

    def _update_display(self):
        m = int(self.tiempo_restante // 60)
        s = int(self.tiempo_restante % 60)
        self.lbl_pomo_digits.setText(f"{m:02d}:{s:02d}")
        
        tot = self.MODOS[self.modo_actual]["tiempo"]
        pct = int(((tot - self.tiempo_restante) / tot) * 100) if tot > 0 else 0
        self.pbar.setValue(pct)

    def _cambiar_modo(self, modo_key):
        if modo_key not in self.MODOS: return
        self.modo_actual = modo_key
        self.running = False
        self.btn_pomo_start.setText("▶ Iniciar Sesión")
        self.tiempo_restante = self.MODOS[modo_key]["tiempo"]
        
        info = self.MODOS[modo_key]
        self.lbl_modo_status.setText(info["nombre"])
        self.lbl_modo_status.setStyleSheet(f"color: {info['color']};")
        self.pbar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.colores['bg_terciario']};
                border-radius: 4px; text-align: center; color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {info['color']}; border-radius: 4px;
            }}
        """)
        self._actualizar_estilos_modos()
        self._update_display()

    def _actualizar_estilos_modos(self):
        active_style = f"background-color: {self.colores['acento']}; color: white; border-radius: 6px; padding: 6px 12px;"
        inactive_style = f"background-color: {self.colores['bg_secundario']}; color: rgba(255,255,255,0.7); border-radius: 6px; padding: 6px 12px; border: 1px solid rgba(255,255,255,0.06);"
        
        self.btn_m_trabajo.setStyleSheet(active_style if self.modo_actual == "trabajo" else inactive_style)
        self.btn_m_corto.setStyleSheet(active_style if self.modo_actual == "descanso_corto" else inactive_style)
        self.btn_m_largo.setStyleSheet(active_style if self.modo_actual == "descanso_largo" else inactive_style)

    def _toggle_start_pause(self):
        self.running = not self.running
        self.btn_pomo_start.setText("⏸️ Pausar" if self.running else "▶ Reanudar")

    def _reset_pomo(self):
        self.running = False
        self.btn_pomo_start.setText("▶ Iniciar Sesión")
        self.tiempo_restante = self.MODOS[self.modo_actual]["tiempo"]
        self._update_display()

    def refrescar_stats(self):
        st = self.manager.pomodoro_stats
        self.lbl_stats_txt.setText(f"🍅 Sesiones completadas hoy: {st.get('sesiones_hoy', 0)} | ⏱️ Enfoque acumulado: {st.get('minutos_enfoque', 0)} min")

    def actualizar_tema(self, colores):
        self.colores = colores
        self._actualizar_estilos_modos()
        self._cambiar_modo(self.modo_actual)
