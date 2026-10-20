import os
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QFileDialog, QListWidget, QListWidgetItem, QFrame, QComboBox, 
                             QSlider, QGridLayout, QScrollArea)
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QFont, QIcon
from vistas.utils.hardware_manager import get_hardware_manager

class SoundboardGUI(QWidget):
    def __init__(self, parent, colores, ruta_usuario):
        super().__init__(parent)
        self.colores = colores
        self.ruta_usuario = Path(ruta_usuario)
        self.ruta_sounds = self.ruta_usuario / "soundboard"
        self.ruta_sounds.mkdir(exist_ok=True)
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        self.hw_manager = get_hardware_manager()
        self.hw_manager.devices_changed.connect(self._update_devices)
        
        self._build_ui()
        self.load_sounds()
        self._update_devices()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)
        
        header = QHBoxLayout()
        lbl_tit = QLabel("🔊 TOCADOR DE SONIDOS (SOUNDBOARD)")
        lbl_tit.setStyleSheet(f"color: white; font-size: 18px; font-weight: 800; letter-spacing: 0.5px;")
        header.addWidget(lbl_tit)
        header.addStretch()
        
        btn_add = QPushButton("+ Añadir Sonido")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['exito']}; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            QPushButton:hover {{
                background: #34D399; /* verde vibrante */
            }}
        """)
        btn_add.clicked.connect(self.add_sound)
        header.addWidget(btn_add)
        
        self.layout.addLayout(header)
        
        # Panel de Controles de Audio
        out_f = QFrame()
        out_f.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            QLabel {{
                color: {self.colores['fg_secundario']};
                font-weight: bold;
                border: none;
                background: transparent;
            }}
        """)
        out_lay = QHBoxLayout(out_f)
        out_lay.setContentsMargins(20, 15, 20, 15)
        
        out_lay.addWidget(QLabel("🔈 Salida de Audio:"))
        self.cb_output = QComboBox()
        self.cb_output.setMinimumWidth(250)
        self.cb_output.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_terciario']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 6px 12px;
                color: white;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white;
                selection-background-color: {self.colores['acento']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                outline: none;
            }}
        """)
        self.cb_output.currentIndexChanged.connect(self.change_device)
        out_lay.addWidget(self.cb_output)
        
        out_lay.addSpacing(30)
        out_lay.addWidget(QLabel("🔊 Volumen:"))
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.setFixedWidth(130)
        self.vol_slider.setStyleSheet(f"""
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
                background: white;
                width: 14px;
                height: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
                border: 1px solid rgba(0,0,0,0.2);
            }}
            QSlider::handle:horizontal:hover {{
                background: {self.colores['acento_hover']};
            }}
        """)
        self.vol_slider.valueChanged.connect(lambda v: self.audio_output.setVolume(v / 100))
        out_lay.addWidget(self.vol_slider)
        
        self.layout.addWidget(out_f)
        
        # Rejilla de sonidos con ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(0, 10, 0, 10)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self.grid_container)
        self.layout.addWidget(scroll)
        
    def _update_devices(self):
        self.cb_output.blockSignals(True)
        prev = self.cb_output.currentText()
        self.cb_output.clear()
        
        outputs = self.hw_manager.get_audio_outputs()
        for d in outputs:
            self.cb_output.addItem(d["name"], d["obj"])
            
        idx = self.cb_output.findText(prev)
        if idx >= 0: self.cb_output.setCurrentIndex(idx)
        self.cb_output.blockSignals(False)
            
    def change_device(self, index):
        device = self.cb_output.currentData()
        if device:
            self.audio_output.setDevice(device)

    def add_sound(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Añadir Sonidos", "", "Audio (*.wav *.mp3 *.ogg *.m4a)")
        if files:
            import shutil
            for f in files:
                dest = self.ruta_sounds / Path(f).name
                if not dest.exists():
                    shutil.copy(f, dest)
            self.load_sounds()

    def load_sounds(self):
        # Limpiar grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        sounds = list(self.ruta_sounds.glob("*.*"))
        for i, s in enumerate(sounds):
            btn_f = QFrame()
            btn_f.setFixedSize(160, 125)
            btn_f.setStyleSheet(f"""
                QFrame {{
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 12px;
                }}
                QFrame:hover {{
                    background: rgba(255, 255, 255, 0.07);
                    border: 1px solid {self.colores['acento']};
                }}
            """)
            btn_lay = QVBoxLayout(btn_f)
            btn_lay.setContentsMargins(12, 10, 12, 10)
            btn_lay.setSpacing(6)
            
            # Fila Superior (Icono + Eliminar)
            top_bar = QHBoxLayout()
            top_bar.setContentsMargins(0, 0, 0, 0)
            
            lbl_icon = QLabel("🎵")
            lbl_icon.setStyleSheet("background: transparent; border: none; font-size: 12px;")
            top_bar.addWidget(lbl_icon)
            
            top_bar.addStretch()
            
            btn_del = QPushButton("×")
            btn_del.setFixedSize(18, 18)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setToolTip("Eliminar Sonido")
            btn_del.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {self.colores['fg_secundario']}; font-weight: bold; font-size: 14px; border: none; border-radius: 9px;
                }}
                QPushButton:hover {{
                    color: white; background: {self.colores['error']};
                }}
            """)
            btn_del.clicked.connect(lambda _, path=s: self.delete_sound(path))
            top_bar.addWidget(btn_del)
            btn_lay.addLayout(top_bar)
            
            # Nombre del Sonido (truncado elegante)
            name = s.stem if len(s.stem) < 18 else s.stem[:15] + "..."
            lbl_name = QLabel(name)
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_name.setStyleSheet("color: white; font-size: 11px; font-weight: bold; background: transparent; border: none;")
            btn_lay.addWidget(lbl_name)
            
            btn_lay.addStretch()
            
            # Botón de Reproducción
            btn_play = QPushButton("▶️ ESCUCHAR")
            btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_play.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores['acento']}; color: white; font-weight: 800; font-size: 9px; padding: 6px; border-radius: 6px; border: none;
                }}
                QPushButton:hover {{
                    background: {self.colores['acento_hover']};
                }}
            """)
            btn_play.clicked.connect(lambda _, path=s: self.play_sound(path))
            btn_lay.addWidget(btn_play)
            
            self.grid_layout.addWidget(btn_f, i // 4, i % 4)

    def play_sound(self, path):
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()

    def delete_sound(self, path):
        try:
            path.unlink()
            self.load_sounds()
        except: pass
