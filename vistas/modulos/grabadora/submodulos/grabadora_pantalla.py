import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class GrabadoraPantallaSubmodule(QWidget):
    """Submódulo 2: Grabadora de Pantalla & Selección de Región"""
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

        # Título
        lbl_tit = QLabel("🎬 GRABADORA DE PANTALLA Y REGIÓN")
        lbl_tit.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tit)

        # ── Área de Preview de Pantalla ──
        self.preview_f = QFrame()
        self.preview_f.setMinimumHeight(240)
        self.preview_f.setStyleSheet(f"""
            QFrame {{
                background-color: #0A0A0E;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        p_layout = QVBoxLayout(self.preview_f)
        p_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet("background: transparent;")
        self.lbl_preview.hide()
        p_layout.addWidget(self.lbl_preview)

        self.lbl_no_preview = QLabel(f"""
            <div style='text-align: center;'>
                <span style='font-size: 32px;'>🖥️</span><br><br>
                <span style='font-size: 14px; font-weight: bold; color: {acento};'>VISTA PREVIA DE PANTALLA</span><br><br>
                <span style='font-size: 11px; color: rgba(255,255,255,0.6);'>Configura las opciones y haz clic en Iniciar Grabación</span>
            </div>
        """)
        self.lbl_no_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_layout.addWidget(self.lbl_no_preview)

        layout.addWidget(self.preview_f, 1)

        # ── Opciones de Selección de Pantalla, FPS y Audio ──
        self.opts_frame = QFrame()
        self.opts_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 10px;")
        o_lay = QHBoxLayout(self.opts_frame)
        o_lay.setContentsMargins(12, 8, 12, 8)
        o_lay.setSpacing(12)

        lbl_p = QLabel("🖥️ Pantalla:")
        lbl_p.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        o_lay.addWidget(lbl_p)

        self.combo_pantalla = QComboBox()
        self.combo_pantalla.setFont(QFont(self.font_family, 9))
        self.combo_pantalla.setStyleSheet(f"""
            QComboBox {{ background: {bg_terc}; color: white; border-radius: 6px; padding: 5px 10px; border: none; }}
            QComboBox QAbstractItemView {{ background: {bg_sec}; color: white; selection-background-color: {acento}; }}
        """)
        o_lay.addWidget(self.combo_pantalla)

        lbl_fps = QLabel("⚡ FPS:")
        lbl_fps.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        o_lay.addWidget(lbl_fps)

        self.combo_fps = QComboBox()
        self.combo_fps.addItems(["15 FPS", "30 FPS", "60 FPS"])
        self.combo_fps.setCurrentIndex(1)
        self.combo_fps.setStyleSheet(self.combo_pantalla.styleSheet())
        o_lay.addWidget(self.combo_fps)

        self.chk_completa = QCheckBox("Pantalla Completa")
        self.chk_completa.setChecked(True)
        self.chk_completa.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.chk_completa.setStyleSheet("QCheckBox { color: white; background: transparent; }")
        self.chk_completa.toggled.connect(self.callbacks.get("toggle_completa"))
        o_lay.addWidget(self.chk_completa)

        self.chk_incluir_audio = QCheckBox("Audio de Micrófono")
        self.chk_incluir_audio.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.chk_incluir_audio.setStyleSheet("QCheckBox { color: white; background: transparent; }")
        o_lay.addWidget(self.chk_incluir_audio)

        self.btn_seleccionar_area = QPushButton("✂️ Elegir Región")
        self.btn_seleccionar_area.setFont(QFont(self.font_family, 9))
        self.btn_seleccionar_area.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_seleccionar_area.setStyleSheet(f"background: {bg_terc}; color: white; border-radius: 6px; padding: 6px 12px; border: none;")
        self.btn_seleccionar_area.clicked.connect(self.callbacks.get("seleccionar_area"))
        o_lay.addWidget(self.btn_seleccionar_area)

        layout.addWidget(self.opts_frame)

        # ── Controles de Grabación ──
        self.ctrl_frame = QFrame()
        self.ctrl_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 10px;")
        c_lay = QHBoxLayout(self.ctrl_frame)
        c_lay.setContentsMargins(12, 8, 12, 8)
        c_lay.setSpacing(12)

        self.btn_grabar_video = QPushButton("🎥 Iniciar Grabación de Pantalla")
        self.btn_grabar_video.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_grabar_video.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_grabar_video.setStyleSheet(f"""
            QPushButton {{
                background: {exito}; color: white; padding: 10px 20px; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background: {exito}dd; }}
        """)
        self.btn_grabar_video.clicked.connect(self.callbacks.get("toggle_video"))
        c_lay.addWidget(self.btn_grabar_video)

        self.btn_pausar_video = QPushButton("⏸️ Pausar")
        self.btn_pausar_video.setFont(QFont(self.font_family, 9))
        self.btn_pausar_video.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pausar_video.setEnabled(False)
        self.btn_pausar_video.setStyleSheet(f"""
            QPushButton {{
                background: {bg_terc}; color: white; padding: 10px 16px; border-radius: 8px; border: none;
            }}
            QPushButton:disabled {{ background: {bg_terc}66; color: #777; }}
        """)
        self.btn_pausar_video.clicked.connect(self.callbacks.get("pause_video"))
        c_lay.addWidget(self.btn_pausar_video)

        c_lay.addStretch()

        self.lbl_status_video = QLabel("Listo")
        self.lbl_status_video.setFont(QFont(self.font_family, 9))
        self.lbl_status_video.setStyleSheet("color: rgba(255,255,255,0.7);")
        c_lay.addWidget(self.lbl_status_video)

        self.lbl_tiempo_video = QLabel("00:00:00")
        self.lbl_tiempo_video.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        self.lbl_tiempo_video.setStyleSheet(f"color: {acento};")
        c_lay.addWidget(self.lbl_tiempo_video)

        layout.addWidget(self.ctrl_frame)

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#1E1E1E')
        bg_sec = colores.get('bg_secundario', '#2D2D2D')
        bg_terc = colores.get('bg_terciario', '#3D3D3D')
        acento = colores.get('acento', '#4A86E8')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        if hasattr(self, 'opts_frame'):
            self.opts_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 10px;")
        if hasattr(self, 'ctrl_frame'):
            self.ctrl_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 10px;")

        self.combo_pantalla.setStyleSheet(f"""
            QComboBox {{ background: {bg_terc}; color: white; border-radius: 6px; padding: 5px 10px; border: none; }}
            QComboBox QAbstractItemView {{ background: {bg_sec}; color: white; selection-background-color: {acento}; }}
        """)
        self.combo_fps.setStyleSheet(self.combo_pantalla.styleSheet())
        self.btn_seleccionar_area.setStyleSheet(f"background: {bg_terc}; color: white; border-radius: 6px; padding: 6px 12px; border: none;")
        self.lbl_tiempo_video.setStyleSheet(f"color: {acento};")

