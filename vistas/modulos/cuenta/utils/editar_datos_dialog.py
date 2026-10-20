import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QGridLayout, QMessageBox, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

class EditarDatosDialog(QDialog):
    """Diálogo modal para modificar datos personales (Usuario, Correo, Cumpleaños) y vincular Google"""
    def __init__(self, parent, config, colores, font_family, ruta_usuario, usuario_actual, oauth_manager=None, on_google_connect=None):
        super().__init__(parent)
        self.config = config or {}
        self.colores = colores or {}
        self.font_family = font_family or "Segoe UI"
        self.ruta_usuario = Path(ruta_usuario)
        self.usuario_actual = usuario_actual
        self.oauth_manager = oauth_manager
        self.on_google_connect = on_google_connect
        self.nuevos_datos = {}

        self.setWindowTitle("✏️ Modificar Datos Personales")
        self.setFixedSize(440, 420)
        self.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 10px;")

        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 22, 22, 22)
        lay.setSpacing(12)

        lbl_t = QLabel("EDITAR DATOS DE PERFIL")
        lbl_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        lay.addWidget(lbl_t)

        form_grid = QGridLayout()
        form_grid.setSpacing(10)

        # Nombre de usuario
        form_grid.addWidget(QLabel("Nombre de Usuario:"), 0, 0)
        self.ent_nick = QLineEdit(self.config.get("usuario", self.usuario_actual))
        self.ent_nick.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; padding: 8px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        form_grid.addWidget(self.ent_nick, 0, 1)

        # Correo electrónico
        form_grid.addWidget(QLabel("Correo Electrónico:"), 1, 0)
        self.ent_email = QLineEdit(self.config.get("correo", ""))
        self.ent_email.setPlaceholderText("ejemplo@correo.com")
        self.ent_email.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; padding: 8px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        form_grid.addWidget(self.ent_email, 1, 1)

        # Selector de Cumpleaños Moderno
        form_grid.addWidget(QLabel("Cumpleaños (Día/Mes):"), 2, 0)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM")
        self.date_edit.setStyleSheet(f"""
            QDateEdit {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
                padding: 8px;
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            QCalendarWidget QWidget {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
            }}
        """)
        c_str = self.config.get("cumpleaños", "")
        if c_str and "/" in c_str:
            try:
                d, m = map(int, c_str.split("/")[:2])
                self.date_edit.setDate(QDate(2026, m, d))
            except Exception:
                self.date_edit.setDate(QDate.currentDate())
        else:
            self.date_edit.setDate(QDate.currentDate())
        form_grid.addWidget(self.date_edit, 2, 1)

        lay.addLayout(form_grid)

        # SECCIÓN VINCULACIÓN CUENTA GOOGLE (OAuth 2.0)
        google_box = QFrame()
        google_box.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; border-radius: 8px;")
        g_lay = QVBoxLayout(google_box)
        g_lay.setContentsMargins(12, 10, 12, 10)
        g_lay.setSpacing(6)

        if self.oauth_manager and self.oauth_manager.is_logged_in():
            u_info = self.oauth_manager.get_user_info()
            g_email = u_info.get("email", "Cuenta vinculada")
            lbl_g = QLabel(f"🌐 Google OAuth: ✅ Conectado (<b>{g_email}</b>)")
            lbl_g.setStyleSheet("color: #34D399; font-size: 11px;")
            g_lay.addWidget(lbl_g)

            btn_g_disc = QPushButton("🔌 Desconectar cuenta de Google")
            btn_g_disc.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_g_disc.setStyleSheet("background: transparent; color: #F87171; border: none; font-size: 11px; text-decoration: underline;")
            
            def _disc():
                self.oauth_manager.logout()
                self.reject()
            btn_g_disc.clicked.connect(_disc)
            g_lay.addWidget(btn_g_disc)
        else:
            lbl_g = QLabel("🌐 Cuenta Google: Sin vincular")
            lbl_g.setStyleSheet("color: #AAB0B8; font-size: 11px;")
            g_lay.addWidget(lbl_g)

            btn_g_conn = QPushButton("🔗 Vincular cuenta de Google")
            btn_g_conn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_g_conn.setStyleSheet("background: #4285F4; color: white; border-radius: 6px; padding: 7px 14px; font-weight: bold; border: none;")
            
            def _conn():
                self.reject()
                if callable(self.on_google_connect):
                    self.on_google_connect()
            btn_g_conn.clicked.connect(_conn)
            g_lay.addWidget(btn_g_conn)

        lay.addWidget(google_box)
        lay.addStretch()

        btns = QHBoxLayout()
        btns.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("background: transparent; color: #AAA; padding: 8px 16px; border: none;")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Guardar")
        btn_save.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; padding: 8px 20px; border-radius: 6px; border: none;")
        btn_save.clicked.connect(self._guardar_datos)
        btns.addWidget(btn_save)

        lay.addLayout(btns)

    def _guardar_datos(self):
        new_nick = self.ent_nick.text().strip()
        new_mail = self.ent_email.text().strip()
        new_cumple = self.date_edit.date().toString("dd/MM")

        if not new_nick:
            QMessageBox.warning(self, "Error", "El nombre de usuario no puede estar vacío.")
            return

        cfg = dict(self.config)
        cfg["usuario"] = new_nick
        cfg["correo"] = new_mail
        cfg["cumpleaños"] = new_cumple

        try:
            from controlador.auth.crypto_utils import process_config_for_save
            cfg_to_save = process_config_for_save(cfg)
        except Exception:
            cfg_to_save = cfg

        with open(self.ruta_usuario / "config.json", "w", encoding="utf-8") as f:
            json.dump(cfg_to_save, f, indent=4)

        self.nuevos_datos = {
            "usuario": new_nick,
            "correo": new_mail,
            "cumpleaños": new_cumple
        }

        QMessageBox.information(self, "Perfil Actualizado", "¡Tus datos personales se han guardado correctamente!")
        self.accept()
