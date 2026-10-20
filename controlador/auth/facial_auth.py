import sys
import os
import cv2
import json
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QFrame,
    QScrollArea, QWidget
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QFont
from ..utils.paths import get_cuentas_path, get_user_path
from .crypto_utils import process_config_for_load

def get_face_cascade():
    """Carga el CascadeClassifier buscando en múltiples rutas posibles."""
    if not hasattr(cv2, 'CascadeClassifier'):
        return None

    local_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(local_dir, 'haarcascade_frontalface_default.xml'),
    ]
    if hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, 'controlador', 'auth', 'haarcascade_frontalface_default.xml'))
        candidates.append(os.path.join(sys._MEIPASS, 'cv2', 'data', 'haarcascade_frontalface_default.xml'))
    if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
        candidates.append(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml'))
    if hasattr(cv2, '__file__') and cv2.__file__:
        candidates.append(os.path.join(os.path.dirname(cv2.__file__), 'data', 'haarcascade_frontalface_default.xml'))

    for path in candidates:
        if path and os.path.isfile(path):
            try:
                cascade = cv2.CascadeClassifier(path)
                if not cascade.empty():
                    return cascade
            except Exception:
                pass

    try:
        return cv2.CascadeClassifier()
    except Exception:
        return None




class FacialAuthManager:
    """Gestor principal de autenticación facial con OpenCV"""

    @staticmethod
    def get_facial_path(ruta_usuario: Path) -> Path:
        return Path(ruta_usuario) / "facial_data.npy"

    @staticmethod
    def is_facial_enabled(ruta_usuario: Path) -> bool:
        return FacialAuthManager.get_facial_path(ruta_usuario).exists()

    @staticmethod
    def save_face_template(ruta_usuario: Path, face_gray: np.ndarray):
        """Procesa y guarda la plantilla del rostro"""
        face_resized = cv2.resize(face_gray, (150, 150))
        face_eq = cv2.equalizeHist(face_resized)
        path = FacialAuthManager.get_facial_path(ruta_usuario)
        np.save(str(path), face_eq)

    @staticmethod
    def remove_face_template(ruta_usuario: Path):
        """Elimina los datos faciales del usuario"""
        path = FacialAuthManager.get_facial_path(ruta_usuario)
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass

    @staticmethod
    def compare_faces(template: np.ndarray, face_gray: np.ndarray) -> float:
        """Retorna una puntuación de similitud entre 0.0 y 1.0"""
        try:
            face_resized = cv2.resize(face_gray, (150, 150))
            face_eq = cv2.equalizeHist(face_resized)

            # 1. Comparación por plantilla (Template Matching)
            res = cv2.matchTemplate(face_eq, template, cv2.TM_CCOEFF_NORMED)
            score_template = max(0.0, float(res[0][0]))

            # 2. Comparación por Histograma de Intensidad
            hist1 = cv2.calcHist([template], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([face_eq], [0], None, [256], [0, 256])
            cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
            score_hist = max(0.0, float(cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)))

            similitud = (score_template * 0.65) + (score_hist * 0.35)
            return similitud
        except Exception:
            return 0.0


class FacialRegisterDialog(QDialog):
    """Diálogo para registrar el rostro del usuario desde el módulo Cuenta"""

    def __init__(self, parent, ruta_usuario: Path, colores: dict):
        super().__init__(parent)
        self.ruta_usuario = Path(ruta_usuario)
        self.colores = colores
        self.setWindowTitle("Configurar Reconocimiento Facial")
        self.setFixedSize(540, 520)
        self.setStyleSheet(f"background: {colores.get('bg_secundario', '#1e1e2e')}; color: white; border-radius: 12px;")

        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.current_face = None

        self.face_cascade = get_face_cascade()

        self._init_ui()
        self._start_camera()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        lbl_title = QLabel("📷 REGISTRO DE RECONOCIMIENTO FACIAL")
        lbl_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Ubícate de frente a la cámara en un lugar iluminado.")
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet("color: #aaa;")
        layout.addWidget(lbl_sub)

        # Feed de video
        self.lbl_video = QLabel("Iniciando cámara...")
        self.lbl_video.setFixedSize(480, 320)
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setStyleSheet("background: #0b0b0f; border-radius: 8px; border: 2px solid #2d2d3d;")
        layout.addWidget(self.lbl_video, 0, Qt.AlignmentFlag.AlignCenter)

        # Indicador de estado
        self.lbl_status = QLabel("Buscando rostro...")
        self.lbl_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #EAB308;")
        layout.addWidget(self.lbl_status)

        # Botón de captura
        self.btn_capture = QPushButton("📸 CAPTURAR Y GUARDAR ROSTRO")
        self.btn_capture.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_capture.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_capture.setEnabled(False)
        self.btn_capture.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')}; color: white;
                padding: 12px; border-radius: 8px; border: none;
            }}
            QPushButton:disabled {{
                background: #444; color: #888;
            }}
        """)
        self.btn_capture.clicked.connect(self._capturar)
        layout.addWidget(self.btn_capture)

    def _start_camera(self):
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.lbl_status.setText("❌ No se detectó ninguna cámara disponible")
                self.lbl_status.setStyleSheet("color: #EF4444;")
                return
            self.timer.start(30)
        except Exception as e:
            self.lbl_status.setText(f"Error cámara: {e}")

    def _update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self.face_cascade is None or self.face_cascade.empty():
            self.lbl_status.setText("❌ Error al cargar modelo de detección (haarcascade missing)")
            self.lbl_status.setStyleSheet("color: #EF4444;")
            faces = []
        else:
            try:
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))
            except Exception as e:
                faces = []

        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            self.current_face = gray[y:y+h, x:x+w]
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, "Rostro Detectado", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            self.lbl_status.setText("✅ Rostro detectado - ¡Listo para capturar!")
            self.lbl_status.setStyleSheet("color: #10B981;")
            self.btn_capture.setEnabled(True)
        else:
            self.current_face = None
            self.lbl_status.setText("🔍 Buscando rostro...")
            self.lbl_status.setStyleSheet("color: #EAB308;")
            self.btn_capture.setEnabled(False)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img).scaled(480, 320, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.lbl_video.setPixmap(pix)

    def _capturar(self):
        if self.current_face is not None:
            FacialAuthManager.save_face_template(self.ruta_usuario, self.current_face)
            self._close_camera()
            QMessageBox.information(self, "Reconocimiento Facial", "✅ ¡Rostro registrado exitosamente!")
            self.accept()

    def _close_camera(self):
        if self.timer.isActive():
            self.timer.stop()
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None

    def closeEvent(self, event):
        self._close_camera()
        super().closeEvent(event)


class MultipleAccountFacialSelectorDialog(QDialog):
    """Diálogo modal para elegir la cuenta cuando múltiples cuentas coinciden con el mismo rostro"""

    def __init__(self, parent, matching_accounts: list, colores: dict):
        super().__init__(parent)
        self.matching_accounts = matching_accounts
        self.colores = colores
        self.selected_account = None
        self.setWindowTitle("Coincidencia Múltiple de Rostro")
        self.setFixedSize(460, 360)
        self.setStyleSheet(f"background: {colores.get('bg_secundario', '#1e1e2e')}; color: white; border-radius: 12px;")

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        lbl_title = QLabel("⚠️ MÚLTIPLES CUENTAS DETECTADAS")
        lbl_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("color: #EAB308;")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel(
            f"Se detectó que este rostro coincide con {len(self.matching_accounts)} cuentas registradas.\n"
            "Por favor, selecciona la cuenta a la cual deseas acceder:"
        )
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setWordWrap(True)
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet("color: #aaa;")
        layout.addWidget(lbl_sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(10)

        for acc in self.matching_accounts:
            btn = QPushButton(f"👤  {acc['usuario']}  ({acc['persona']})")
            btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores.get('bg_terciario', '#2d2d3d')};
                    color: white;
                    padding: 12px 16px;
                    border-radius: 8px;
                    border: 1px solid rgba(255,255,255,0.05);
                    text-align: left;
                }}
                QPushButton:hover {{
                    border-color: {self.colores.get('acento', '#6366F1')};
                    background: #38384d;
                }}
            """)
            btn.clicked.connect(lambda _, a=acc: self._select(a))
            c_layout.addWidget(btn)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("background: #333; color: white; padding: 10px; border-radius: 6px; border: none;")
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel)

    def _select(self, account):
        self.selected_account = account
        self.accept()


class FacialLoginDialog(QDialog):
    """Diálogo interactivo para iniciar sesión escaneando el rostro"""

    def __init__(self, parent, colores: dict, on_success_callback):
        super().__init__(parent)
        self.colores = colores
        self.on_success_callback = on_success_callback
        self.setWindowTitle("Iniciar Sesión con Rostro")
        self.setFixedSize(500, 460)
        self.setStyleSheet(f"background: {colores.get('bg_secundario', '#1e1e2e')}; color: white; border-radius: 12px;")

        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)

        self.face_cascade = get_face_cascade()

        self.templates = self._load_all_registered_faces()

        self._init_ui()
        self._start_camera()

    def _load_all_registered_faces(self) -> list:
        """Carga todas las plantillas faciales registradas"""
        registered = []
        cuentas_dir = get_cuentas_path()
        if cuentas_dir.exists():
            for folder in cuentas_dir.iterdir():
                if folder.is_dir():
                    facial_file = FacialAuthManager.get_facial_path(folder)
                    config_file = folder / "config.json"
                    if facial_file.exists() and config_file.exists():
                        try:
                            with open(config_file, "r", encoding="utf-8") as f:
                                cfg = process_config_for_load(json.load(f))
                            template = np.load(str(facial_file))
                            registered.append({
                                "persona": folder.name,
                                "usuario": cfg.get("usuario", folder.name),
                                "config": cfg,
                                "template": template,
                                "avatar": cfg.get("avatar", "")
                            })
                        except Exception as e:
                            print(f"[FacialAuth] Error cargando facial para {folder.name}: {e}")
        return registered

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl_title = QLabel("👤 INICIO DE SESIÓN FACIAL")
        lbl_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Por favor, mira hacia la cámara...")
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet("color: #aaa;")
        layout.addWidget(lbl_sub)

        # Feed de video
        self.lbl_video = QLabel("Iniciando cámara...")
        self.lbl_video.setFixedSize(440, 290)
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setStyleSheet("background: #0b0b0f; border-radius: 8px; border: 2px solid #2d2d3d;")
        layout.addWidget(self.lbl_video, 0, Qt.AlignmentFlag.AlignCenter)

        self.lbl_status = QLabel("Escaneando..." if self.templates else "❌ No hay cuentas con reconocimiento facial activo")
        self.lbl_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #EAB308;" if self.templates else "color: #EF4444;")
        layout.addWidget(self.lbl_status)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("background: #333; color: white; padding: 8px; border-radius: 6px; border: none;")
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel)

    def _start_camera(self):
        if not self.templates:
            return
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.lbl_status.setText("❌ No se detectó ninguna cámara")
                self.lbl_status.setStyleSheet("color: #EF4444;")
                return
            self.timer.start(30)
        except Exception as e:
            self.lbl_status.setText(f"Error cámara: {e}")

    def _update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self.face_cascade is None or self.face_cascade.empty():
            self.lbl_status.setText("❌ Error al cargar modelo de detección (haarcascade missing)")
            self.lbl_status.setStyleSheet("color: #EF4444;")
            faces = []
        else:
            try:
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))
            except Exception as e:
                faces = []

        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            current_face = gray[y:y+h, x:x+w]

            # Comparar con todas las plantillas registradas
            matching_accounts = []
            for user_data in self.templates:
                score = FacialAuthManager.compare_faces(user_data["template"], current_face)
                if score >= 0.55:
                    matching_accounts.append((score, user_data))

            if len(matching_accounts) > 1:
                # ⚠️ Se detectaron 2 o más cuentas con el mismo rostro -> Preguntar a cuál acceder
                self._close_camera()
                self.lbl_status.setText("⚠️ Múltiples cuentas coinciden. Elige una cuenta...")
                self.lbl_status.setStyleSheet("color: #EAB308;")
                
                matching_accounts.sort(key=lambda item: item[0], reverse=True)
                accounts_list = [item[1] for item in matching_accounts]
                
                dlg = MultipleAccountFacialSelectorDialog(self, accounts_list, self.colores)
                if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_account:
                    selected = dlg.selected_account
                    if self.on_success_callback:
                        self.on_success_callback(selected)
                    self.accept()
                else:
                    self.reject()
                return

            elif len(matching_accounts) == 1:
                match_found = matching_accounts[0][1]
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f"Hola, {match_found['usuario']}!", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                self.lbl_status.setText(f"✅ ¡Rostro reconocido! Hola {match_found['usuario']}")
                self.lbl_status.setStyleSheet("color: #10B981;")

                self._close_camera()
                if self.on_success_callback:
                    self.on_success_callback(match_found)
                self.accept()
                return
            else:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 165, 255), 2)
                self.lbl_status.setText("🔍 Verificando identidad...")
                self.lbl_status.setStyleSheet("color: #EAB308;")
        else:
            self.lbl_status.setText("🔍 Esperando rostro...")
            self.lbl_status.setStyleSheet("color: #EAB308;")

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img).scaled(440, 290, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.lbl_video.setPixmap(pix)

    def _close_camera(self):
        if self.timer.isActive():
            self.timer.stop()
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None

    def reject(self):
        self._close_camera()
        super().reject()

    def closeEvent(self, event):
        self._close_camera()
        super().closeEvent(event)

