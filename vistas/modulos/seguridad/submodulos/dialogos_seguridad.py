"""
dialogos_seguridad.py - Diálogos auxiliares del módulo de Seguridad
Incluye:
- Generador avanzado de contraseñas con medidor de entropía y opciones personalizables.
- Calculadora de hashes criptográficos (MD5, SHA-1, SHA-256, SHA-512) para textos y archivos.
- Auditoría de salud y vulnerabilidades de la bóveda (contraseñas débiles o duplicadas).
- Diálogo de exportación e importación segura con cifrado de respaldo.
"""

import string
import secrets
from pathlib import Path
from typing import List, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSlider, QCheckBox, QFrame, QTextEdit, QMessageBox, QFileDialog, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..utils.crypto import calcular_hashes_texto, calcular_hashes_archivo, encrypt_vault, decrypt_vault


class PasswordGeneratorDialog(QDialog):
    """Diálogo interactivo para generar contraseñas criptográficamente seguras."""

    def __init__(self, parent, colores, font_family):
        super().__init__(parent)
        self.colores = colores
        self.font_family = font_family
        self.setWindowTitle("⚡ Generador de Contraseñas Seguras")
        self.setMinimumWidth(420)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
            }}
            QLabel {{
                color: #FFFFFF;
            }}
            QCheckBox {{
                color: #FFFFFF;
            }}
        """)
        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 22, 22, 22)
        lay.setSpacing(14)

        lbl_title = QLabel("⚡ GENERADOR DE CONTRASEÑAS")
        lbl_title.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        acento = self.colores.get('acento', '#6366F1')
        lbl_title.setStyleSheet(f"color: {acento}; border: none; background: transparent;")
        lay.addWidget(lbl_title)

        self.txt_result = QLineEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')
        exito = self.colores.get('exito', '#34D399')
        self.txt_result.setStyleSheet(f"""
            background-color: {bg_ter};
            color: {exito};
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 8px;
            padding: 10px;
        """)
        lay.addWidget(self.txt_result)

        self.lbl_strength = QLabel("Fortaleza: Media")
        self.lbl_strength.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_strength.setStyleSheet("border: none; background: transparent;")
        lay.addWidget(self.lbl_strength)

        self.strength_bar = QFrame()
        self.strength_bar.setFixedHeight(6)
        self.strength_bar.setStyleSheet("background-color: #FBBF24; border-radius: 3px;")
        lay.addWidget(self.strength_bar)

        h_len = QHBoxLayout()
        lbl_len = QLabel("Longitud:")
        lbl_len.setFont(QFont(self.font_family, 9))
        lbl_len.setStyleSheet("border: none; background: transparent;")
        self.lbl_len_val = QLabel("16")
        self.lbl_len_val.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_len_val.setStyleSheet("border: none; background: transparent; color: white;")
        h_len.addWidget(lbl_len)
        h_len.addWidget(self.lbl_len_val)
        h_len.addStretch()
        lay.addLayout(h_len)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(8, 64)
        self.slider.setValue(16)
        self.slider.valueChanged.connect(self.update_length_label)
        lay.addWidget(self.slider)

        self.cb_upper = QCheckBox("Mayúsculas (A-Z)")
        self.cb_lower = QCheckBox("Minúsculas (a-z)")
        self.cb_nums = QCheckBox("Números (0-9)")
        self.cb_syms = QCheckBox("Símbolos (!@#$...)")

        self.cb_upper.setChecked(True)
        self.cb_lower.setChecked(True)
        self.cb_nums.setChecked(True)
        self.cb_syms.setChecked(True)

        for cb in [self.cb_upper, self.cb_lower, self.cb_nums, self.cb_syms]:
            cb.stateChanged.connect(self.generate)
            cb.setStyleSheet("color: white; border: none; background: transparent;")
            lay.addWidget(cb)

        h_btn = QHBoxLayout()
        btn_gen = QPushButton("⚡ Generar")
        btn_gen.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gen.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_gen.setStyleSheet(f"background-color: {acento}; color: white; padding: 8px 16px; border-radius: 6px; border: none;")
        btn_gen.clicked.connect(self.generate)

        btn_acc = QPushButton("✓ Usar Contraseña")
        btn_acc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_acc.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_acc.setStyleSheet(f"background-color: {exito}; color: white; padding: 8px 16px; border-radius: 6px; border: none;")
        btn_acc.clicked.connect(self.accept)

        h_btn.addWidget(btn_gen)
        h_btn.addWidget(btn_acc)
        lay.addLayout(h_btn)

        self.generate()

    def update_length_label(self, val):
        self.lbl_len_val.setText(str(val))
        self.generate()

    def generate(self):
        chars = ""
        if self.cb_upper.isChecked(): chars += string.ascii_uppercase
        if self.cb_lower.isChecked(): chars += string.ascii_lowercase
        if self.cb_nums.isChecked(): chars += string.digits
        if self.cb_syms.isChecked(): chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if not chars:
            self.txt_result.setText("")
            self.lbl_strength.setText("Fortaleza: Muy Débil 🔴")
            self.strength_bar.setStyleSheet("background-color: #EF4444; border-radius: 3px;")
            return

        length = self.slider.value()
        password = "".join(secrets.choice(chars) for _ in range(length))
        self.txt_result.setText(password)

        cats = sum([self.cb_upper.isChecked(), self.cb_lower.isChecked(), self.cb_nums.isChecked(), self.cb_syms.isChecked()])
        score = length * cats

        if score < 24:
            self.lbl_strength.setText("Fortaleza: Débil 🔴")
            self.strength_bar.setStyleSheet("background-color: #EF4444; border-radius: 3px;")
        elif score < 45:
            self.lbl_strength.setText("Fortaleza: Media 🟡")
            self.strength_bar.setStyleSheet("background-color: #FBBF24; border-radius: 3px;")
        else:
            self.lbl_strength.setText("Fortaleza: Fuerte 🟢")
            self.strength_bar.setStyleSheet("background-color: #10B981; border-radius: 3px;")

    def get_password(self):
        return self.txt_result.text()


class HashCalculatorDialog(QDialog):
    """Diálogo para calcular hashes criptográficos MD5, SHA-1, SHA-256, SHA-512 de textos o archivos."""

    def __init__(self, parent, colores, font_family):
        super().__init__(parent)
        self.colores = colores
        self.font_family = font_family
        self.setWindowTitle("🔑 Calculadora de Hashes Criptográficos")
        self.setMinimumSize(520, 420)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
            }}
            QLabel {{
                color: #FFFFFF;
            }}
        """)
        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        lbl_title = QLabel("🔑 CALCULADORA DE HASHES")
        lbl_title.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        acento = self.colores.get('acento', '#6366F1')
        lbl_title.setStyleSheet(f"color: {acento}; border: none; background: transparent;")
        lay.addWidget(lbl_title)

        lbl_in = QLabel("Texto de Entrada / Archivo:")
        lbl_in.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lay.addWidget(lbl_in)

        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("Escribe el texto para calcular sus hashes...")
        self.txt_input.setFont(QFont(self.font_family, 9))
        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')
        self.txt_input.setStyleSheet(f"background: {bg_ter}; color: white; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 8px;")
        self.txt_input.textChanged.connect(self._calcular_hashes_texto)
        lay.addWidget(self.txt_input)

        btn_file = QPushButton("📁 Examinar Archivo para Hash...")
        btn_file.setFixedHeight(34)
        btn_file.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_file.setStyleSheet(f"background: {bg_ter}; color: white; border-radius: 6px; padding: 4px 12px; font-weight: bold;")
        btn_file.clicked.connect(self._examinar_archivo)
        lay.addWidget(btn_file)

        # Displays de Hashes
        self.txt_md5 = self._crear_hash_display(lay, "MD5")
        self.txt_sha1 = self._crear_hash_display(lay, "SHA-1")
        self.txt_sha256 = self._crear_hash_display(lay, "SHA-256")
        self.txt_sha512 = self._crear_hash_display(lay, "SHA-512")

    def _crear_hash_display(self, parent_lay, label_text):
        h_lay = QHBoxLayout()
        lbl = QLabel(f"{label_text}:")
        lbl.setFixedWidth(75)
        lbl.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")

        txt = QLineEdit()
        txt.setReadOnly(True)
        txt.setFont(QFont("Consolas", 8))
        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')
        txt.setStyleSheet(f"background: {bg_ter}; color: #34D399; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 5px 8px;")

        btn_copy = QPushButton("📋")
        btn_copy.setToolTip(f"Copiar hash {label_text}")
        btn_copy.setFixedSize(30, 30)
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(f"background: {bg_ter}; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; color: white;")
        from PyQt6.QtWidgets import QApplication
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(txt.text()))

        h_lay.addWidget(lbl)
        h_lay.addWidget(txt, 1)
        h_lay.addWidget(btn_copy)
        parent_lay.addLayout(h_lay)
        return txt

    def _calcular_hashes_texto(self, text):
        hashes = calcular_hashes_texto(text)
        self.txt_md5.setText(hashes["md5"])
        self.txt_sha1.setText(hashes["sha1"])
        self.txt_sha256.setText(hashes["sha256"])
        self.txt_sha512.setText(hashes["sha512"])

    def _examinar_archivo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo para Hash")
        if not path:
            return
        try:
            hashes = calcular_hashes_archivo(path)
            self.txt_input.setText(f"Archivo: {Path(path).name}")
            self.txt_md5.setText(hashes["md5"])
            self.txt_sha1.setText(hashes["sha1"])
            self.txt_sha256.setText(hashes["sha256"])
            self.txt_sha512.setText(hashes["sha512"])
        except Exception as e:
            QMessageBox.warning(self, "Error Hash", f"No se pudo leer el archivo: {e}")


class VaultAuditDialog(QDialog):
    """Diálogo de auditoría de seguridad y vulnerabilidades de la bóveda de contraseñas."""

    def __init__(self, parent, colores, font_family, secretos: List[Dict[str, Any]]):
        super().__init__(parent)
        self.colores = colores
        self.font_family = font_family
        self.secretos = secretos
        self.setWindowTitle("🛡️ Auditoría de Salud de la Bóveda")
        self.setMinimumSize(480, 440)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
            }}
            QLabel {{
                color: #FFFFFF;
            }}
        """)
        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 22, 22, 22)
        lay.setSpacing(14)

        lbl_title = QLabel("🛡️ INFORME DE AUDITORÍA DE SEGURIDAD")
        lbl_title.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        acento = self.colores.get('acento', '#6366F1')
        lbl_title.setStyleSheet(f"color: {acento}; border: none; background: transparent;")
        lay.addWidget(lbl_title)

        total = len(self.secretos)
        reusadas = 0
        debiles = 0
        pass_map = {}

        for s in self.secretos:
            p = s.get('password', '') or s.get('pass', '')
            if p in pass_map:
                reusadas += 1
            else:
                pass_map[p] = 1

            if len(p) < 10 or p.isalpha() or p.isdigit():
                debiles += 1

        salud = 100
        if total > 0:
            salud = max(0, 100 - int((reusadas * 30 + debiles * 20) / total))

        lbl_score = QLabel(f"Salud de la Bóveda: {salud}%")
        lbl_score.setFont(QFont(self.font_family, 16, QFont.Weight.Bold))
        color_salud = "#34D399" if salud >= 80 else ("#FBBF24" if salud >= 50 else "#F87171")
        lbl_score.setStyleSheet(f"color: {color_salud}; border: none; background: transparent;")
        lay.addWidget(lbl_score)

        txt_info = QTextEdit()
        txt_info.setReadOnly(True)
        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')
        txt_info.setStyleSheet(f"background: {bg_ter}; color: white; border-radius: 8px; padding: 10px; font-size: 11px;")

        reporte = [
            "📊 Resumen Criptográfico:",
            f"  • Total de contraseñas guardadas: {total}",
            f"  • Contraseñas reutilizadas/duplicadas: {reusadas} ⚠️",
            f"  • Contraseñas débiles (< 10 caracteres): {debiles} 🔴",
            "",
            "💡 Recomendaciones de Seguridad:",
            "  1. Reemplaza contraseñas duplicadas entre servicios web.",
            "  2. Utiliza el Generador Integrado para crear claves de 16+ caracteres.",
            "  3. Asegúrate de activar la verificación en dos pasos (2FA) en tus servicios críticos.",
            "  4. Realiza respaldos regulares exportando tu bóveda cifrada."
        ]
        txt_info.setText("\n".join(reporte))
        lay.addWidget(txt_info, 1)

        btn_ok = QPushButton("✓ Entendido")
        btn_ok.setFixedHeight(34)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; font-weight: bold;")
        btn_ok.clicked.connect(self.accept)
        lay.addWidget(btn_ok)


class ExportImportDialog(QDialog):
    """Diálogo para exportar e importar respaldos de la bóveda cifrados o en JSON."""

    def __init__(self, parent, colores, font_family, secretos: List[Dict[str, Any]], master_pwd: str):
        super().__init__(parent)
        self.colores = colores
        self.font_family = font_family
        self.secretos = secretos
        self.master_pwd = master_pwd
        self.imported_secretos = None
        self.setWindowTitle("📦 Respaldo y Exportación / Importación")
        self.setMinimumSize(440, 320)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
            }}
            QLabel {{
                color: #FFFFFF;
            }}
        """)
        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        lbl_title = QLabel("📦 RESPALDOS DE LA BÓVEDA")
        lbl_title.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        acento = self.colores.get('acento', '#6366F1')
        lbl_title.setStyleSheet(f"color: {acento}; border: none; background: transparent;")
        lay.addWidget(lbl_title)

        lbl_desc = QLabel("Exporta tus secretos a un respaldo cifrado con AES-256 o restaura desde un respaldo previo.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; border: none;")
        lay.addWidget(lbl_desc)

        btn_export = QPushButton("📤 Exportar Respaldo Cifrado (.enc)...")
        btn_export.setFixedHeight(36)
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet(f"background: {acento}; color: white; border-radius: 8px; font-weight: bold;")
        btn_export.clicked.connect(self._exportar_cifrado)
        lay.addWidget(btn_export)

        btn_import = QPushButton("📥 Importar Respaldo (.enc / .json)...")
        btn_import.setFixedHeight(36)
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')
        btn_import.setStyleSheet(f"background: {bg_ter}; color: white; border-radius: 8px; font-weight: bold; border: 1px solid rgba(255,255,255,0.1);")
        btn_import.clicked.connect(self._importar_respaldo)
        lay.addWidget(btn_import)

        lay.addStretch()

        btn_close = QPushButton("Cerrar")
        btn_close.setFixedHeight(32)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("background: transparent; color: white; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px;")
        btn_close.clicked.connect(self.reject)
        lay.addWidget(btn_close)

    def _exportar_cifrado(self):
        import json
        fpath, _ = QFileDialog.getSaveFileName(self, "Exportar Respaldo Cifrado", "boveda_respaldo.enc", "Archivo Cifrado (*.enc)")
        if not fpath:
            return
        try:
            raw_str = json.dumps(self.secretos, indent=4)
            enc_dict = encrypt_vault(raw_str, self.master_pwd)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(enc_dict, f, indent=4)
            QMessageBox.information(self, "Exportación Exitosa", f"Se exportaron {len(self.secretos)} registros cifrados correctamente a:\n{fpath}")
        except Exception as e:
            QMessageBox.critical(self, "Error Exportando", f"No se pudo exportar el respaldo:\n{e}")

    def _importar_respaldo(self):
        import json
        from PyQt6.QtWidgets import QInputDialog
        fpath, _ = QFileDialog.getOpenFileName(self, "Seleccionar Respaldo", "", "Archivos de Respaldo (*.enc *.json);;Todos los archivos (*.*)")
        if not fpath:
            return
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = json.load(f)

            if isinstance(content, dict) and "ciphertext" in content:
                pwd, ok = QInputDialog.getText(self, "Contraseña de Respaldo", "Introduce la contraseña con la que se cifró el archivo:", QLineEdit.EchoMode.Password)
                if not ok or not pwd:
                    return
                dec_str = decrypt_vault(content, pwd)
                nuevos = json.loads(dec_str)
            elif isinstance(content, list):
                nuevos = content
            else:
                QMessageBox.warning(self, "Formato no compatible", "El archivo seleccionado no tiene un formato de respaldo válido.")
                return

            if isinstance(nuevos, list):
                self.imported_secretos = nuevos
                QMessageBox.information(self, "Importación Lista", f"Se leyeron {len(nuevos)} registros del respaldo.")
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error Importando", f"No se pudo descifrar o importar el respaldo:\n{e}")
