import os
import cv2
import platform

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QImage, QPixmap

class GrabadoraWebcamSubmodule(QWidget):
    """Submódulo 3: Grabadora de Cámara Web & Captura de Fotos Instantáneas (Snapshots)"""
    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.timer_webcam = QTimer(self)
        self.timer_webcam.timeout.connect(self._update_webcam_frame)
        self.cap = None

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#1E1E1E')
        bg_sec = self.colores.get('bg_secundario', '#2D2D2D')
        bg_terc = self.colores.get('bg_terciario', '#3D3D3D')
        acento = self.colores.get('acento', '#4A86E8')
        exito = self.colores.get('exito', '#43A047')
        error = self.colores.get('error', '#E53935')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Título
        lbl_tit = QLabel("🎥 CÁMARA WEB & FOTOS INSTANTÁNEAS")
        lbl_tit.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tit)

        # Canvas de Previsualización de Cámara
        self.cam_frame = QFrame()
        self.cam_frame.setMinimumHeight(260)
        self.cam_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #08080C;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        c_lay = QVBoxLayout(self.cam_frame)
        c_lay.setContentsMargins(0, 0, 0, 0)

        self.lbl_cam_preview = QLabel()
        self.lbl_cam_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cam_preview.setStyleSheet("background: transparent;")
        c_lay.addWidget(self.lbl_cam_preview)

        self.lbl_no_cam = QLabel(f"""
            <div style='text-align: center;'>
                <span style='font-size: 32px;'>📷</span><br><br>
                <span style='font-size: 14px; font-weight: bold; color: {acento};'>CÁMARA WEB</span><br><br>
                <span style='font-size: 11px; color: rgba(255,255,255,0.6);'>Enciende la cámara para ver la transmisión en directo</span>
            </div>
        """)
        self.lbl_no_cam.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_lay.addWidget(self.lbl_no_cam)

        layout.addWidget(self.cam_frame, 1)

        # Panel de Controles
        # Panel de Controles
        self.ctrl_frame = QFrame()
        self.ctrl_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 10px;")
        ctrl_lay = QHBoxLayout(self.ctrl_frame)
        ctrl_lay.setContentsMargins(12, 8, 12, 8)
        ctrl_lay.setSpacing(12)

        lbl_c = QLabel("📷 Cámara:")
        lbl_c.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        ctrl_lay.addWidget(lbl_c)

        self.combo_webcam = QComboBox()
        self.combo_webcam.setFont(QFont(self.font_family, 9))
        self.combo_webcam.setStyleSheet(f"""
            QComboBox {{ background: {bg_terc}; color: white; border-radius: 6px; padding: 5px 10px; border: none; }}
            QComboBox QAbstractItemView {{ background: {bg_sec}; color: white; selection-background-color: {acento}; }}
        """)
        self.combo_webcam.addItems(self.manager.obtener_camaras_web())
        ctrl_lay.addWidget(self.combo_webcam)

        self.btn_toggle_cam = QPushButton("🔌 Encender Cámara")
        self.btn_toggle_cam.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_toggle_cam.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_cam.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 8px 14px; border: none;")
        self.btn_toggle_cam.clicked.connect(self._toggle_camara)
        ctrl_lay.addWidget(self.btn_toggle_cam)

        self.btn_foto = QPushButton("📸 Tomar Foto")
        self.btn_foto.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_foto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_foto.setStyleSheet(f"background: {exito}; color: white; border-radius: 6px; padding: 8px 14px; border: none;")
        self.btn_foto.clicked.connect(self._tomar_foto)
        ctrl_lay.addWidget(self.btn_foto)

        self.btn_rec_webcam = QPushButton("🔴 Grabar Video")
        self.btn_rec_webcam.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_rec_webcam.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rec_webcam.setStyleSheet(f"background: {error}; color: white; border-radius: 6px; padding: 8px 14px; border: none;")
        self.btn_rec_webcam.clicked.connect(self._toggle_rec_webcam)
        ctrl_lay.addWidget(self.btn_rec_webcam)

        layout.addWidget(self.ctrl_frame)

    def _toggle_camara(self):
        if self.cap is None or not self.cap.isOpened():
            idx = self.combo_webcam.currentIndex()
            self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.lbl_no_cam.hide()
                self.lbl_cam_preview.show()
                self.timer_webcam.start(40) # ~25 FPS
                self.btn_toggle_cam.setText("🔌 Apagar Cámara")
                self.btn_toggle_cam.setStyleSheet(f"background: {self.colores.get('error', '#E53935')}; color: white; border-radius: 6px; padding: 8px 14px; border: none;")
            else:
                QMessageBox.warning(self, "Cámara no disponible", "No se pudo acceder a la cámara web seleccionada.")
        else:
            self.timer_webcam.stop()
            self.cap.release()
            self.cap = None
            self.lbl_cam_preview.hide()
            self.lbl_no_cam.show()
            self.btn_toggle_cam.setText("🔌 Encender Cámara")
            self.btn_toggle_cam.setStyleSheet(f"background: {self.colores.get('acento', '#4A86E8')}; color: white; border-radius: 6px; padding: 8px 14px; border: none;")

    def _update_webcam_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
                pix = QPixmap.fromImage(qimg).scaled(self.lbl_cam_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.lbl_cam_preview.setPixmap(pix)

    def _tomar_foto(self):
        idx = self.combo_webcam.currentIndex()
        nombre = self.manager.tomar_foto_webcam(idx)
        if nombre:
            QMessageBox.information(self, "Foto Tomada", f"¡Fotografía guardada con éxito como:\n📷 {nombre}")
            if "cargar_audios" in self.callbacks:
                self.callbacks["cargar_audios"]()
        else:
            QMessageBox.warning(self, "Error", "No se pudo tomar la fotografía. Asegúrate de tener la cámara activa.")

    def _toggle_rec_webcam(self):
        if not self.manager.grabando_webcam:
            idx = self.combo_webcam.currentIndex()
            self.manager.iniciar_webcam_video(idx, 25, lambda f: None)
            self.btn_rec_webcam.setText("⏹️ Detener Grabación")
        else:
            res = self.manager.detener_webcam_video()
            self.btn_rec_webcam.setText("🔴 Grabar Video")
            QMessageBox.information(self, "Grabación Finalizada", res)
            if "cargar_audios" in self.callbacks:
                self.callbacks["cargar_audios"]()

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#1E1E1E')
        bg_sec = colores.get('bg_secundario', '#2D2D2D')
        bg_terc = colores.get('bg_terciario', '#3D3D3D')
        acento = colores.get('acento', '#4A86E8')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        if hasattr(self, 'ctrl_frame'):
            self.ctrl_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 10px;")

        self.combo_webcam.setStyleSheet(f"""
            QComboBox {{ background: {bg_terc}; color: white; border-radius: 6px; padding: 5px 10px; border: none; }}
            QComboBox QAbstractItemView {{ background: {bg_sec}; color: white; selection-background-color: {acento}; }}
        """)

    def cleanup(self):
        try:
            if hasattr(self, 'timer_webcam'):
                self.timer_webcam.stop()
            if self.cap and self.cap.isOpened():
                self.cap.release()
                self.cap = None
        except Exception:
            pass

