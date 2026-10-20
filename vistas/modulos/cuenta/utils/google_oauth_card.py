import threading
import urllib.request
from pathlib import Path
import sys
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

class GoogleOAuthCardWidget(QFrame):
    """Card reutilizable para vincular y gestionar la sesión de Google OAuth 2.0"""
    def __init__(self, ruta_usuario, colores, font_family="Segoe UI", parent=None):
        super().__init__(parent)
        self.ruta_usuario = Path(ruta_usuario)
        self.colores = colores or {}
        self.font_family = font_family
        self.oauth_manager = None
        self._avatar_google = None

        self.setStyleSheet(
            f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; "
            f"border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);"
        )

        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(22, 18, 22, 18)
        card_layout.setSpacing(12)

        lbl_title = QLabel("CUENTAS VINCULADAS")
        lbl_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; border: none;")
        card_layout.addWidget(lbl_title)

        self._google_body = QVBoxLayout()
        self._google_body.setSpacing(12)
        card_layout.addLayout(self._google_body)

        self._inicializar_oauth()
        self.actualizar_card()

    def _inicializar_oauth(self):
        try:
            GoogleOAuthManager = None
            try:
                from vistas.modulos.navegador.utils.oauth_pkce import GoogleOAuthManager
            except Exception:
                pass

            if not GoogleOAuthManager:
                candidatos = [
                    Path(__file__).resolve().parents[2] / "navegador" / "utils",
                    Path(__file__).resolve().parents[3] / "navegador" / "utils",
                    Path(sys.executable).resolve().parent / "vistas" / "modulos" / "navegador" / "utils"
                ]
                for p in candidatos:
                    if p.exists() and str(p) not in sys.path:
                        sys.path.insert(0, str(p))
                try:
                    from oauth_pkce import GoogleOAuthManager
                except Exception:
                    try:
                        from oauth_manager import GoogleOAuthManager
                    except Exception:
                        GoogleOAuthManager = None

            if GoogleOAuthManager:
                self.oauth_manager = GoogleOAuthManager(self.ruta_usuario)
                self.oauth_manager.login_completed.connect(self._on_google_login_ok)
                self.oauth_manager.login_failed.connect(self._on_google_login_fail)
                self.oauth_manager.logout_completed.connect(self._on_google_logout)
            else:
                self.oauth_manager = None
        except Exception as e:
            print(f"[OAuth/Cuenta] No se pudo inicializar GoogleOAuthManager: {e}")
            self.oauth_manager = None

    def actualizar_card(self):
        while self._google_body.count():
            item = self._google_body.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.oauth_manager and self.oauth_manager.is_logged_in():
            self._dibujar_conectado(self.oauth_manager.get_user_info())
        else:
            self._dibujar_desconectado()

    def _dibujar_desconectado(self):
        lbl_name = QLabel("Google — Sin vincular")
        lbl_name.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_name.setStyleSheet("color: white; border: none; margin-bottom: 4px;")
        self._google_body.addWidget(lbl_name)

        lbl_desc = QLabel(
            "Vincula tu cuenta de Google para acceder\n"
            "a servicios integrados. El login se abre\n"
            "en tu navegador seguro del sistema."
        )
        lbl_desc.setFont(QFont(self.font_family, 9))
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; border: none; margin-bottom: 8px;")
        self._google_body.addWidget(lbl_desc)

        btn_conectar = QPushButton("  Conectar con Google")
        btn_conectar.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_conectar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_conectar.setObjectName("btn_google_connect")
        btn_conectar.setStyleSheet("""
            QPushButton#btn_google_connect {
                background: #4285F4;
                color: white;
                padding: 11px 20px;
                border-radius: 8px;
                border: none;
                text-align: left;
            }
            QPushButton#btn_google_connect:hover {
                background: #357abd;
            }
            QPushButton#btn_google_connect:disabled {
                background: #555;
                color: #999;
            }
        """)
        btn_conectar.clicked.connect(self.conectar_google)
        self._google_body.addWidget(btn_conectar)
        self._google_body.addStretch()

    def _dibujar_conectado(self, info: dict):
        nombre = info.get("name", "Usuario de Google")
        email = info.get("email", "")
        picture_url = info.get("picture", "")

        self._avatar_google = QLabel()
        self._avatar_google.setFixedSize(80, 80)
        self._avatar_google.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_google.setStyleSheet("background: transparent; border: none;")
        self._google_body.addWidget(self._avatar_google, 0, Qt.AlignmentFlag.AlignLeft)

        if picture_url:
            self._cargar_foto_google(picture_url)

        lbl_name = QLabel(f"✅  {nombre}")
        lbl_name.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_name.setStyleSheet("color: white; border: none;")
        self._google_body.addWidget(lbl_name)

        if email:
            lbl_email = QLabel(f"📧  {email}")
            lbl_email.setFont(QFont(self.font_family, 9))
            lbl_email.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; border: none;")
            self._google_body.addWidget(lbl_email)

        lbl_srv = QLabel("Cuenta de Google vinculada")
        lbl_srv.setFont(QFont(self.font_family, 8))
        lbl_srv.setStyleSheet(f"color: {self.colores.get('exito', '#10B981')}; border: none; margin-bottom: 6px;")
        self._google_body.addWidget(lbl_srv)

        btn_desconectar = QPushButton("🔌 Desconectar")
        btn_desconectar.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_desconectar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_desconectar.setObjectName("btn_google_disconnect")
        btn_desconectar.setStyleSheet(f"""
            QPushButton#btn_google_disconnect {{
                background: transparent;
                color: {self.colores.get('error', '#EF4444')};
                border: 1px solid {self.colores.get('error', '#EF4444')};
                padding: 8px 18px;
                border-radius: 8px;
            }}
            QPushButton#btn_google_disconnect:hover {{
                background: {self.colores.get('error', '#EF4444')};
                color: white;
            }}
        """)
        btn_desconectar.clicked.connect(self.desconectar_google)
        self._google_body.addWidget(btn_desconectar, 0, Qt.AlignmentFlag.AlignLeft)
        self._google_body.addStretch()

    def _cargar_foto_google(self, url: str):
        def _fetch():
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = resp.read()
                pix = QPixmap()
                pix.loadFromData(data)
                if not pix.isNull():
                    pix = pix.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                     Qt.TransformationMode.SmoothTransformation)
                    try:
                        self._avatar_google.setPixmap(pix)
                    except RuntimeError:
                        pass
            except Exception:
                pass
        threading.Thread(target=_fetch, daemon=True).start()

    def conectar_google(self):
        if not self.oauth_manager:
            self._inicializar_oauth()
        if not self.oauth_manager:
            QMessageBox.warning(self, "Error", "El módulo OAuth no está disponible.")
            return

        btn = self.findChild(QPushButton, "btn_google_connect")
        if btn:
            btn.setEnabled(False)
            btn.setText("⏳ Esperando en el navegador...")

        QMessageBox.information(
            self,
            "Iniciar sesión con Google",
            "🌐 Se abrirá tu navegador predeterminado para iniciar sesión con Google.\n\n"
            "Después de completar el login, vuelve a la aplicación — "
            "la vinculación se realizará automáticamente.",
            QMessageBox.StandardButton.Ok
        )
        self.oauth_manager.login()

    def desconectar_google(self):
        if not self.oauth_manager:
            return
        confirm = QMessageBox.question(
            self, "Desconectar Google",
            "¿Deseas desconectar tu cuenta de Google?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.oauth_manager.logout()

    def _on_google_login_ok(self, user_info: dict):
        self.actualizar_card()
        nombre = user_info.get("name", "tu cuenta de Google")
        QMessageBox.information(
            self, "Google vinculado",
            f"✅ ¡Cuenta vinculada exitosamente!\n\nBienvenido/a, {nombre}."
        )

    def _on_google_login_fail(self, error: str):
        btn = self.findChild(QPushButton, "btn_google_connect")
        if btn:
            btn.setEnabled(True)
            btn.setText("  Conectar con Google")
        QMessageBox.critical(
            self, "Error de autenticación",
            f"No se pudo completar el inicio de sesión con Google.\n\nDetalle: {error}"
        )

    def _on_google_logout(self):
        self.actualizar_card()
