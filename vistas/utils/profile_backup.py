# -*- coding: utf-8 -*-
"""
Backup Portátil Cifrado de Perfil (.mtbackup).
Permite exportar e importar configuración, workspaces, notas y flujos entre equipos
Windows, Linux y macOS usando cifrado autenticado (PBKDF2-HMAC-SHA256).
"""

import hashlib
import hmac
import io
import json
import os
import zipfile
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

MAGIC_HEADER = b"MTBACKUP1"


def _derive_keys(password: str, salt: bytes) -> tuple[bytes, bytes]:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000, dklen=64)
    return dk[:32], dk[32:]


def _xor_stream(data: bytes, enc_key: bytes, nonce: bytes) -> bytes:
    out = bytearray(len(data))
    counter = 0
    pos = 0
    while pos < len(data):
        block = hashlib.sha256(enc_key + nonce + counter.to_bytes(8, "big")).digest()
        take = min(32, len(data) - pos)
        for i in range(take):
            out[pos + i] = data[pos + i] ^ block[i]
        pos += take
        counter += 1
    return bytes(out)


def exportar_backup_perfil(ruta_usuario: Path, destino_archivo: Path, password: str) -> tuple[bool, str]:
    """Empaqueta los archivos de configuración del usuario en un `.mtbackup` cifrado."""
    if not password:
        return False, "Debes indicar una contraseña para cifrar el backup."
    if not ruta_usuario.exists():
        return False, "La carpeta del usuario no existe."

    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in ruta_usuario.rglob("*"):
            if fp.is_file() and fp.suffix.lower() not in {".tmp", ".lock", ".old"}:
                rel = fp.relative_to(ruta_usuario).as_posix()
                zf.write(fp, rel)
                count += 1

    plain = buf.getvalue()
    salt = os.urandom(16)
    nonce = os.urandom(16)
    enc_key, mac_key = _derive_keys(password, salt)
    cipher = _xor_stream(plain, enc_key, nonce)
    tag = hmac.new(mac_key, MAGIC_HEADER + salt + nonce + cipher, hashlib.sha256).digest()

    destino_archivo.parent.mkdir(parents=True, exist_ok=True)
    destino_archivo.write_bytes(MAGIC_HEADER + salt + nonce + tag + cipher)
    return True, f"Backup cifrado exportado ({count} archivo(s)) en:\n{destino_archivo}"


def importar_backup_perfil(ruta_backup: Path, ruta_usuario: Path, password: str) -> tuple[bool, str]:
    """Verifica la contraseña/integridad y restaura un `.mtbackup` en `ruta_usuario`."""
    if not ruta_backup.exists():
        return False, "El archivo de backup no existe."
    raw = ruta_backup.read_bytes()
    min_len = len(MAGIC_HEADER) + 16 + 16 + 32
    if len(raw) < min_len or not raw.startswith(MAGIC_HEADER):
        return False, "Formato de backup inválido."

    off = len(MAGIC_HEADER)
    salt = raw[off : off + 16]
    nonce = raw[off + 16 : off + 32]
    tag = raw[off + 32 : off + 64]
    cipher = raw[off + 64 :]

    enc_key, mac_key = _derive_keys(password, salt)
    expected_tag = hmac.new(mac_key, MAGIC_HEADER + salt + nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        return False, "Contraseña incorrecta o archivo corrupto."

    plain = _xor_stream(cipher, enc_key, nonce)
    ruta_usuario.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(io.BytesIO(plain), "r") as zf:
        for member in zf.namelist():
            rel = Path(member)
            if rel.is_absolute() or ".." in rel.parts or member.endswith("/"):
                continue
            out = ruta_usuario / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(zf.read(member))
            count += 1
    return True, f"Backup restaurado correctamente ({count} archivo(s))."


class ProfileBackupDialog(QDialog):
    """Diálogo gráfico para exportar o restaurar un `.mtbackup` cifrado."""

    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.setWindowTitle("💾 Backup Portátil Cifrado (.mtbackup)")
        self.setMinimumWidth(440)
        self.setStyleSheet("""
            QDialog, QWidget { background-color: #131520; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #f8fafc; }
            QLineEdit { background-color: #0f111a; color: #f8fafc; border: 1px solid #2e344d; border-radius: 5px; padding: 6px; }
            QPushButton { background-color: #252a3d; color: #f8fafc; border: 1px solid #38405e; border-radius: 6px; padding: 7px 12px; font-weight: 600; }
            QPushButton#Primary { background-color: #4f46e5; border-color: #6366f1; }
            QPushButton#Success { background-color: #059669; border-color: #10b981; }
        """)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.addWidget(QLabel("Exporta o restaura tu perfil completo (config, workspaces, notas y flujos) entre PCs Windows, Linux o macOS:"))

        lay.addWidget(QLabel("Contraseña de cifrado:"))
        self.ent_pass = QLineEdit()
        self.ent_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ent_pass.setPlaceholderText("Contraseña segura...")
        lay.addWidget(self.ent_pass)

        row = QHBoxLayout()
        btn_exp = QPushButton("📤 Exportar .mtbackup")
        btn_exp.setObjectName("Success")
        btn_exp.clicked.connect(self._exportar)
        btn_imp = QPushButton("📥 Importar .mtbackup")
        btn_imp.setObjectName("Primary")
        btn_imp.clicked.connect(self._importar)
        row.addWidget(btn_exp)
        row.addWidget(btn_imp)
        lay.addLayout(row)

    def _exportar(self):
        pwd = self.ent_pass.text()
        if not pwd:
            QMessageBox.warning(self, "Contraseña requerida", "Escribe una contraseña para cifrar el backup.")
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Guardar Backup", str(Path.home() / "multitool_perfil.mtbackup"), "Multitool Backup (*.mtbackup)")
        if not dest:
            return
        if hasattr(self.app_ref, "guardar_configuracion"):
            self.app_ref.guardar_configuracion()
        ok, msg = exportar_backup_perfil(Path(self.app_ref.ruta_usuario), Path(dest), pwd)
        QMessageBox.information(self, "Exportar Backup", msg) if ok else QMessageBox.critical(self, "Error", msg)

    def _importar(self):
        pwd = self.ent_pass.text()
        if not pwd:
            QMessageBox.warning(self, "Contraseña requerida", "Escribe la contraseña del backup.")
            return
        src, _ = QFileDialog.getOpenFileName(self, "Abrir Backup", str(Path.home()), "Multitool Backup (*.mtbackup)")
        if not src:
            return
        ok, msg = importar_backup_perfil(Path(src), Path(self.app_ref.ruta_usuario), pwd)
        if ok:
            if hasattr(self.app_ref, "cargar_configuracion"):
                self.app_ref.cargar_configuracion()
            QMessageBox.information(self, "Restaurado", msg + "\nReinicia o recarga módulos para aplicar todo.")
        else:
            QMessageBox.critical(self, "Error", msg)
