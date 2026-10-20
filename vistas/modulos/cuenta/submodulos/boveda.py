"""
boveda.py - Submódulo de Bóveda de Claves API, Generador de 2FA TOTP y Contraseñas Fuertes
"""
import json
import time
import hmac
import hashlib
import base64
import struct
import random
import string
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QCheckBox, QSpinBox, QMessageBox, QScrollArea, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

def generar_totp_code(secret_b32):
    """Genera código de 6 dígitos TOTP según RFC 6238"""
    try:
        secret_clean = secret_b32.strip().replace(" ", "").upper()
        if not secret_clean: return "------"
        missing_padding = len(secret_clean) % 8
        if missing_padding:
            secret_clean += '=' * (8 - missing_padding)
        key = base64.b32decode(secret_clean, casefold=True)
        t = int(time.time()) // 30
        msg = struct.pack(">Q", t)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[19] & 0x0f
        code = (struct.unpack(">I", h[offset:offset+4])[0] & 0x7fffffff) % 1000000
        return f"{code:06d}"
    except Exception:
        return "INVÁLIDO"

class TabBoveda(QWidget):
    """Submódulo de Bóveda de Claves API y Generador de Contraseñas Fuertes con Auto-Borrado"""
    def __init__(self, parent, context, colores):
        super().__init__(parent)
        self.context = context
        self.colores = colores or {}
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.persona = getattr(context, "persona", "Usuario")
        self.font_family = "Segoe UI"

        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        self.init_ui()

    def cargar_config(self):
        cfg_path = self.ruta_usuario / "config.json"
        if cfg_path.exists():
            try:
                from controlador.auth.crypto_utils import process_config_for_load
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return process_config_for_load(json.load(f))
            except Exception:
                pass
        return {}

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 8, 10, 8)
        main_lay.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {bg_p}; }}")

        content = QWidget()
        content.setStyleSheet(f"background-color: {bg_p};")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        lbl_head = QLabel("🔑 BÓVEDA DE CREDENCIALES, GENERADOR Y 2FA TOTP")
        lbl_head.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_head.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; margin-bottom: 2px;")
        lay.addWidget(lbl_head)

        config = self.cargar_config()
        boveda = config.get("boveda_api_keys", {})

        # ── 1. BÓVEDA DE CLAVES API Y CREDENCIALES ──────────────────
        api_card = QFrame()
        api_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }}
        """)
        api_lay = QVBoxLayout(api_card)
        api_lay.setContentsMargins(14, 12, 14, 12)
        api_lay.setSpacing(8)

        lbl_api_t = QLabel("🛡️ Almacenamiento Seguro de Claves API")
        lbl_api_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_api_t.setStyleSheet("color: white;")
        api_lay.addWidget(lbl_api_t)

        self.api_inputs = {}
        servicios = [
            ("openai", "🤖 OpenAI API Key:"),
            ("gemini", "✨ Google Gemini API Key:"),
            ("weather", "🌤️ Weather / Clima API Key:"),
            ("custom", "🔐 Clave Secreta Personal:")
        ]

        for key, label in servicios:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFont(QFont(self.font_family, 9))
            lbl.setFixedWidth(190)

            ent = QLineEdit(boveda.get(key, ""))
            ent.setEchoMode(QLineEdit.EchoMode.Password)
            ent.setPlaceholderText("sk-...")
            ent.setStyleSheet(f"""
                QLineEdit {{
                    background: {self.colores.get('bg_terciario', '#2D2D3D')};
                    color: white;
                    padding: 6px;
                    border-radius: 6px;
                    border: 1px solid rgba(255,255,255,0.1);
                }}
            """)
            self.api_inputs[key] = ent

            btn_toggle = QPushButton("👁️")
            btn_toggle.setFixedSize(28, 28)
            btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_toggle.setStyleSheet("background: transparent; color: white; border: none; font-size: 13px;")
            
            def _toggle_mode(checked, field=ent, btn=btn_toggle):
                if field.echoMode() == QLineEdit.EchoMode.Password:
                    field.setEchoMode(QLineEdit.EchoMode.Normal)
                    btn.setText("🙈")
                else:
                    field.setEchoMode(QLineEdit.EchoMode.Password)
                    btn.setText("👁️")
            
            btn_toggle.clicked.connect(_toggle_mode)

            row.addWidget(lbl)
            row.addWidget(ent, 1)
            row.addWidget(btn_toggle)
            api_lay.addLayout(row)

        btn_save_keys = QPushButton("💾 GUARDAR BÓVEDA DE CLAVES")
        btn_save_keys.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_keys.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; padding: 7px 14px; font-weight: bold; border-radius: 6px; border: none;")
        btn_save_keys.clicked.connect(self._guardar_boveda)
        api_lay.addWidget(btn_save_keys, 0, Qt.AlignmentFlag.AlignRight)

        lay.addWidget(api_card)

        # ── 2. GENERADOR 2FA TOTP (6 DÍGITOS) ──────────────────────────
        totp_card = QFrame()
        totp_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px; padding: 12px;
            }}
        """)
        totp_lay = QVBoxLayout(totp_card)
        totp_lay.setSpacing(8)

        lbl_totp_t = QLabel("🔐 Generador de Autenticación 2FA / TOTP")
        lbl_totp_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_totp_t.setStyleSheet("color: white;")
        totp_lay.addWidget(lbl_totp_t)

        row_t = QHBoxLayout()
        self.txt_totp_secret = QLineEdit(boveda.get("totp_secret", ""))
        self.txt_totp_secret.setPlaceholderText("Clave Secreta Base32 (ej: JBSWY3DPEHPK3PXP)")
        self.txt_totp_secret.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; padding: 6px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        row_t.addWidget(self.txt_totp_secret, 1)

        self.lbl_totp_val = QLabel("------")
        self.lbl_totp_val.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.lbl_totp_val.setStyleSheet("color: #34D399; padding: 0 10px;")
        row_t.addWidget(self.lbl_totp_val)

        btn_gen_totp = QPushButton("⚡ Obtener Código 2FA")
        btn_gen_totp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gen_totp.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; padding: 6px 12px; font-weight: bold; border-radius: 6px; border: none;")
        btn_gen_totp.clicked.connect(self._actualizar_totp)
        row_t.addWidget(btn_gen_totp)

        totp_lay.addLayout(row_t)
        lay.addWidget(totp_card)

        # ── 3. GENERADOR DE CONTRASEÑAS FUERTES CON AUTO-BORRADO ───────
        gen_card = QFrame()
        gen_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px; padding: 12px;
            }}
        """)
        gen_lay = QVBoxLayout(gen_card)
        gen_lay.setSpacing(8)

        lbl_gen_t = QLabel("⚡ Generador de Contraseñas Fuertes (Auto-borrado 30s)")
        lbl_gen_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_gen_t.setStyleSheet("color: white;")
        gen_lay.addWidget(lbl_gen_t)

        row_gen_out = QHBoxLayout()
        self.ent_pwd = QLineEdit()
        self.ent_pwd.setReadOnly(True)
        self.ent_pwd.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.ent_pwd.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #10B981;
                padding: 7px;
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.15);
            }}
        """)
        row_gen_out.addWidget(self.ent_pwd, 1)

        btn_copy = QPushButton("📋 Copiar (Auto-limpieza 30s)")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; padding: 7px 12px; font-weight: bold; border-radius: 6px; border: none;")
        btn_copy.clicked.connect(self._copiar_pwd)
        row_gen_out.addWidget(btn_copy)
        gen_lay.addLayout(row_gen_out)

        row_opts = QHBoxLayout()
        row_opts.addWidget(QLabel("Longitud:"))
        
        self.spin_len = QSpinBox()
        self.spin_len.setRange(8, 64)
        self.spin_len.setValue(16)
        self.spin_len.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; padding: 4px; border-radius: 4px;")
        row_opts.addWidget(self.spin_len)

        self.chk_upper = QCheckBox("Mayúsculas (A-Z)")
        self.chk_upper.setChecked(True)
        self.chk_upper.setStyleSheet("color: white;")
        row_opts.addWidget(self.chk_upper)

        self.chk_nums = QCheckBox("Números (0-9)")
        self.chk_nums.setChecked(True)
        self.chk_nums.setStyleSheet("color: white;")
        row_opts.addWidget(self.chk_nums)

        self.chk_syms = QCheckBox("Símbolos (!@#$)")
        self.chk_syms.setChecked(True)
        self.chk_syms.setStyleSheet("color: white;")
        row_opts.addWidget(self.chk_syms)

        gen_lay.addLayout(row_opts)

        btn_gen = QPushButton("🎲 Generar Nueva Contraseña")
        btn_gen.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gen.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; padding: 7px 12px; font-weight: bold; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        btn_gen.clicked.connect(self.generar_password)
        gen_lay.addWidget(btn_gen)

        lay.addWidget(gen_card)

        self.generar_password()

        scroll.setWidget(content)
        main_lay.addWidget(scroll)

    def _actualizar_totp(self):
        sec = self.txt_totp_secret.text().strip()
        code = generar_totp_code(sec)
        self.lbl_totp_val.setText(code)

    def _guardar_boveda(self):
        cfg = self.cargar_config()
        boveda_data = {key: ent.text().strip() for key, ent in self.api_inputs.items()}
        boveda_data["totp_secret"] = self.txt_totp_secret.text().strip()
        cfg["boveda_api_keys"] = boveda_data

        from controlador.auth.crypto_utils import process_config_for_save
        with open(self.ruta_usuario / "config.json", "w", encoding="utf-8") as f:
            json.dump(process_config_for_save(cfg), f, indent=4)

        QMessageBox.information(self, "Bóveda Guardada", "¡Las claves y secretos de la Bóveda se han guardado con éxito!")

    def generar_password(self):
        length = self.spin_len.value()
        chars = string.ascii_lowercase
        if self.chk_upper.isChecked():
            chars += string.ascii_uppercase
        if self.chk_nums.isChecked():
            chars += string.digits
        if self.chk_syms.isChecked():
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if not chars:
            chars = string.ascii_lowercase

        pwd = "".join(random.choice(chars) for _ in range(length))
        self.ent_pwd.setText(pwd)

    def _copiar_pwd(self):
        pwd = self.ent_pwd.text()
        if pwd:
            app = QApplication.clipboard()
            if app:
                app.setText(pwd)
                QMessageBox.information(self, "Portapapeles", "Contraseña copiada. Se borrará automáticamente del portapapeles en 30 segundos.")
                QTimer.singleShot(30000, lambda: self._limpiar_portapapeles_si_coincide(pwd))

    def _limpiar_portapapeles_si_coincide(self, pwd_target):
        app = QApplication.clipboard()
        if app and app.text() == pwd_target:
            app.clear()
