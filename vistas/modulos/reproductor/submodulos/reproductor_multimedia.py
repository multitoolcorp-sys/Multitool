import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QSlider, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class ReproductorMultimediaSubmodule(QWidget):
    """Submódulo 1: Reproductor Multimedia ARK (Audio & Video) con Controles Flotantes"""
    play_requested = pyqtSignal(str)
    toggle_requested = pyqtSignal()
    vol_changed = pyqtSignal(int)
    seek_requested = pyqtSignal(int)
    skip_requested = pyqtSignal(int)
    device_changed = pyqtSignal(str)
    cinema_requested = pyqtSignal()

    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.video_widget = None

        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # ── Área Central de Visualización / Lienzo ──
        self.canvas_frame = QFrame()
        self.canvas_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #08080C;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }}
        """)
        self.v_lay = QVBoxLayout(self.canvas_frame)
        self.v_lay.setContentsMargins(0, 0, 0, 0)
        self.v_lay.setSpacing(0)

        # Cartel de Espera / Reproducción de Audio (Clickable para abrir archivo)
        self.lbl_no_media = QLabel(f"""
            <div style='text-align: center;'>
                <span style='font-size: 36px;'>🎬</span><br><br>
                <span style='font-size: 17px; font-weight: bold; color: {self.colores.get('acento', '#6366F1')}; letter-spacing: 1px;'>REPRODUCTOR MULTIMEDIA ARK</span><br><br>
                <span style='font-size: 13px; color: rgba(255,255,255,0.85); font-weight: 500;'>Haz clic aquí o pulsa <b>📂 Abrir Archivo</b> para reproducir audio o vídeo</span><br><br>
                <span style='font-size: 11px; color: rgba(255,255,255,0.5);'>Soporta MP3, WAV, OGG, FLAC, MP4, AVI, MKV, MOV</span>
            </div>
        """)
        self.lbl_no_media.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_media.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_no_media.setStyleSheet("background: transparent; color: white;")
        self.lbl_no_media.mousePressEvent = lambda e: self.callbacks.get("reproducir_archivo", lambda: None)()
        self.v_lay.addWidget(self.lbl_no_media)

        layout.addWidget(self.canvas_frame, 1)

        # ── Barra Cápsula de Controles Flotantes ──
        controls_frame = QFrame()
        controls_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 6px;
            }}
        """)
        c_lay = QVBoxLayout(controls_frame)
        c_lay.setContentsMargins(15, 10, 15, 10)
        c_lay.setSpacing(8)

        # Fila 1: Título actual y Slider de progreso
        title_row = QHBoxLayout()
        self.lbl_current_title = QLabel("Sin archivo seleccionado")
        self.lbl_current_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_current_title.setStyleSheet("color: white;")
        title_row.addWidget(self.lbl_current_title)
        title_row.addStretch()

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setFont(QFont("Consolas", 9))
        self.lbl_time.setStyleSheet("color: rgba(255,255,255,0.7);")
        title_row.addWidget(self.lbl_time)
        c_lay.addLayout(title_row)

        self.slider_seek = QSlider(Qt.Orientation.Horizontal)
        self.slider_seek.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: 6px; background: {self.colores.get('bg_terciario', '#2D2D3D')}; border-radius: 3px; }}
            QSlider::sub-page:horizontal {{ background: {self.colores.get('acento', '#6366F1')}; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: white; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; }}
        """)
        self.is_seeking = False

        def _on_slider_moved(v):
            self.is_seeking = True
            dur = self.slider_seek.maximum()
            s = v // 1000
            m = s // 60
            s = s % 60
            h = m // 60
            m = m % 60
            t_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            
            s2 = dur // 1000
            m2 = s2 // 60
            s2 = s2 % 60
            h2 = m2 // 60
            m2 = m2 % 60
            dur_str = f"{h2:02d}:{m2:02d}:{s2:02d}" if h2 > 0 else f"{m2:02d}:{s2:02d}"
            self.lbl_time.setText(f"{t_str} / {dur_str}")

        def _on_slider_released():
            self.is_seeking = False
            self.callbacks.get("seek_tiempo", lambda x: None)(self.slider_seek.value())

        self.slider_seek.sliderMoved.connect(_on_slider_moved)
        self.slider_seek.sliderReleased.connect(_on_slider_released)
        c_lay.addWidget(self.slider_seek)

        # Fila 2: Botones de reproducción, volumen, parlantes y cine
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_open = QPushButton("📂 Abrir Archivo")
        btn_open.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.4); border-radius: 6px; padding: 7px 14px;")
        btn_open.clicked.connect(lambda: self.callbacks.get("reproducir_archivo", lambda: None)())
        btn_row.addWidget(btn_open)

        btn_prev = QPushButton("⏪ -5s")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border: none; border-radius: 6px; padding: 6px 12px;")
        btn_prev.clicked.connect(lambda: self.callbacks.get("skip_tiempo", lambda x: None)(-5000))
        btn_row.addWidget(btn_prev)

        self.btn_play = QPushButton("▶ REPRODUCIR")
        self.btn_play.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setStyleSheet(f"background-color: {self.colores.get('acento', '#6366F1')}; color: white; border: none; border-radius: 6px; padding: 8px 20px;")
        self.btn_play.clicked.connect(self.callbacks["toggle_play"])
        btn_row.addWidget(self.btn_play)

        btn_next = QPushButton("+5s ⏩")
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border: none; border-radius: 6px; padding: 6px 12px;")
        btn_next.clicked.connect(lambda: self.callbacks.get("skip_tiempo", lambda x: None)(5000))
        btn_row.addWidget(btn_next)

        btn_row.addStretch()

        # Selector de Salida de Audio
        lbl_spk = QLabel("🔊 Salida:")
        lbl_spk.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_spk.setStyleSheet("color: rgba(255,255,255,0.7);")
        btn_row.addWidget(lbl_spk)

        self.cb_audio = QComboBox()
        self.cb_audio.setFont(QFont(self.font_family, 8))
        self.cb_audio.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 4px 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white; selection-background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.cb_audio.currentTextChanged.connect(lambda name: self.callbacks.get("cambiar_dispositivo", lambda x: None)(name))
        btn_row.addWidget(self.cb_audio)

        # Slider de Volumen
        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setFixedWidth(90)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(80)
        self.slider_vol.setStyleSheet(self.slider_seek.styleSheet())
        self.slider_vol.valueChanged.connect(lambda v: self.callbacks.get("cambiar_volumen", lambda x: None)(v))
        btn_row.addWidget(self.slider_vol)

        # Botón Pantalla Completa / Modo Cine
        btn_cinema = QPushButton("🎬 Modo Cine")
        btn_cinema.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cinema.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border: none; border-radius: 6px; padding: 6px 12px;")
        btn_cinema.clicked.connect(self.callbacks["modo_cine"])
        btn_row.addWidget(btn_cinema)

        c_lay.addLayout(btn_row)
        layout.addWidget(controls_frame)

    def actualizar_tema(self, colores):
        self.colores = colores
        if hasattr(self, "btn_play"):
            self.btn_play.setStyleSheet(f"background-color: {self.colores.get('acento', '#6366F1')}; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
