import platform
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class GrabadoraAudioSubmodule(QWidget):
    """Submódulo 1: Grabadora de Audio & Micrófono con Visualizador de Onda"""
    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#1E1E1E')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        bg_terc = self.colores.get('bg_terciario', '#3D3D3D')
        acento = self.colores.get('acento', '#4A86E8')
        exito = self.colores.get('exito', '#43A047')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        lbl_tit = QLabel("🎙️ GRABADORA DE AUDIO Y MICRÓFONO")
        lbl_tit.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tit)

        # ── Visualización Matplotlib (waveform) ──
        self.visual_frame = QFrame()
        self.visual_frame.setFixedHeight(200)
        self.visual_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        v_layout = QVBoxLayout(self.visual_frame)
        v_layout.setContentsMargins(8, 8, 8, 8)

        self.fig_audio = plt.Figure(figsize=(5, 2), dpi=100)
        self.fig_audio.patch.set_facecolor(bg_sec)
        self.ax_audio = self.fig_audio.add_subplot(111)
        self.ax_audio.set_facecolor(bg_sec)
        self.ax_audio.set_ylim(-1, 1)
        self.ax_audio.set_xlim(0, 100)
        
        self.ax_audio.spines['top'].set_visible(False)
        self.ax_audio.spines['right'].set_visible(False)
        self.ax_audio.spines['bottom'].set_visible(False)
        self.ax_audio.spines['left'].set_visible(False)
        self.ax_audio.get_xaxis().set_visible(False)
        self.ax_audio.get_yaxis().set_visible(False)
        
        self.line_audio, = self.ax_audio.plot([], [], lw=2, color=acento)

        self.canvas_plot = FigureCanvas(self.fig_audio)
        self.canvas_plot.setStyleSheet("background: transparent; border: none;")
        v_layout.addWidget(self.canvas_plot)
        layout.addWidget(self.visual_frame)

        # ── Controles de Grabación ──
        controles = QFrame()
        controles.setStyleSheet(f"""
            QFrame {{
                background: {bg_sec}; 
                border-radius: 12px; 
                border: 1px solid rgba(255,255,255,0.05);
                padding: 12px;
            }}
        """)
        c_layout = QHBoxLayout(controles)
        c_layout.setContentsMargins(15, 10, 15, 10)
        c_layout.setSpacing(12)

        self.btn_grabar_audio = QPushButton("🎙️ Iniciar Grabación")
        self.btn_grabar_audio.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_grabar_audio.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_grabar_audio.setStyleSheet(f"""
            QPushButton {{
                background: {exito}; 
                color: white; 
                padding: 10px 20px; 
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{ background: {exito}dd; }}
        """)
        self.btn_grabar_audio.clicked.connect(self.callbacks.get("toggle_audio"))
        c_layout.addWidget(self.btn_grabar_audio)

        self.btn_pausar_audio = QPushButton("⏸️ Pausar")
        self.btn_pausar_audio.setFont(QFont(self.font_family, 9))
        self.btn_pausar_audio.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pausar_audio.setEnabled(False)
        self.btn_pausar_audio.setStyleSheet(f"""
            QPushButton {{
                background: {bg_terc}; 
                color: white; 
                padding: 10px 16px; 
                border-radius: 8px;
                border: none;
            }}
            QPushButton:disabled {{ background: {bg_terc}66; color: #777; }}
        """)
        self.btn_pausar_audio.clicked.connect(self.callbacks.get("pause_audio"))
        c_layout.addWidget(self.btn_pausar_audio)

        c_layout.addStretch()

        lbl_mic = QLabel("🎤 Micrófono:")
        lbl_mic.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        c_layout.addWidget(lbl_mic)

        self.combo_dispositivo = QComboBox()
        self.combo_dispositivo.setFont(QFont(self.font_family, 9))
        self.combo_dispositivo.setStyleSheet(f"""
            QComboBox {{
                background: {bg_terc}; color: white; border-radius: 6px; padding: 6px 12px; border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {bg_sec}; color: white; selection-background-color: {acento};
            }}
        """)
        c_layout.addWidget(self.combo_dispositivo)
        layout.addWidget(controles)

        # Barra de Estado y Cronómetro
        status_frame = QFrame()
        status_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 8px 15px;")
        st_lay = QHBoxLayout(status_frame)
        st_lay.setContentsMargins(10, 5, 10, 5)

        self.lbl_status_audio = QLabel("Listo para grabar")
        self.lbl_status_audio.setFont(QFont(self.font_family, 9))
        self.lbl_status_audio.setStyleSheet("color: rgba(255,255,255,0.7);")
        st_lay.addWidget(self.lbl_status_audio)

        st_lay.addStretch()

        self.lbl_tiempo_audio = QLabel("00:00:00")
        self.lbl_tiempo_audio.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.lbl_tiempo_audio.setStyleSheet(f"color: {acento};")
        st_lay.addWidget(self.lbl_tiempo_audio)

        layout.addWidget(status_frame)

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#1E1E1E')
        bg_sec = colores.get('bg_secundario', '#2D2D2D')
        bg_terc = colores.get('bg_terciario', '#3D3D3D')
        acento = colores.get('acento', '#4A86E8')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        if hasattr(self, 'visual_frame'):
            self.visual_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_sec};
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }}
            """)
        try:
            self.fig_audio.patch.set_facecolor(bg_sec)
            self.ax_audio.set_facecolor(bg_sec)
            self.line_audio.set_color(acento)
            self.canvas_plot.draw_idle()
        except Exception:
            pass

        self.lbl_tiempo_audio.setStyleSheet(f"color: {acento};")
        self.combo_dispositivo.setStyleSheet(f"""
            QComboBox {{
                background: {bg_terc}; color: white; border-radius: 6px; padding: 6px 12px; border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {bg_sec}; color: white; selection-background-color: {acento};
            }}
        """)

    def cleanup(self):
        try:
            plt.close(self.fig_audio)
        except Exception:
            pass

