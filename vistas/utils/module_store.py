# -*- coding: utf-8 -*-
"""
Tienda y Gestor Comunitario de Módulos (.mtu).
- Permite instalar paquetes `.mtu` locales o desde un catálogo JSON con verificación
  de seguridad (manifest.json, prevención de path traversal y escaneo básico de código).
- Lista módulos instalados y permite abrirlos o empaquetarlos.
"""

import json
import zipfile
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from vistas.utils.compilar_modulo import (
    abrir_compilador_modulos,
    escanear_modulos_disponibles,
    obtener_raiz_proyecto,
)
from vistas.utils.creator.helpers import normalizar_id_modulo

SUSPICIOUS_PATTERNS = ("os.system(", "eval(", "exec(", "ctypes.windll", "winreg.DeleteKey")


def verificar_paquete_mtu(ruta_mtu: Path) -> tuple[bool, dict, list[str]]:
    """Valida integridad y seguridad básica de un paquete `.mtu` antes de instalarlo."""
    advertencias = []
    if not ruta_mtu.exists():
        return False, {}, ["El archivo .mtu no existe."]
    try:
        with zipfile.ZipFile(ruta_mtu, "r") as zf:
            names = zf.namelist()
            if "manifest.json" not in names:
                return False, {}, ["Paquete inválido: falta manifest.json."]
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            for member in names:
                p = Path(member)
                if p.is_absolute() or ".." in p.parts:
                    return False, manifest, [f"Ruta insegura detectada en el paquete: {member}"]
                if member.endswith(".py"):
                    src = zf.read(member).decode("utf-8", errors="ignore")
                    for pat in SUSPICIOUS_PATTERNS:
                        if pat in src:
                            advertencias.append(f"Uso sensible '{pat}' en {member}")
            return True, manifest, advertencias
    except Exception as exc:
        return False, {}, [f"No se pudo leer el archivo .mtu: {exc}"]


def instalar_paquete_mtu(ruta_mtu: Path, raiz: Path | None = None) -> tuple[bool, str]:
    """Instala un paquete `.mtu` verificado dentro de `vistas/modulos/`."""
    raiz = raiz or obtener_raiz_proyecto()
    ok, manifest, warns = verificar_paquete_mtu(ruta_mtu)
    if not ok:
        return False, "\n".join(warns)

    mod_id = normalizar_id_modulo(manifest.get("module_id") or ruta_mtu.stem)
    dest_dir = raiz / "vistas" / "modulos" / mod_id

    with zipfile.ZipFile(ruta_mtu, "r") as zf:
        for member in zf.namelist():
            if member == "manifest.json" or member.endswith("/"):
                continue
            rel = Path(member)
            if ".." in rel.parts:
                continue
            out = (raiz / rel) if rel.parts[:2] == ("vistas", "modulos") else (dest_dir / rel)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(zf.read(member))

    return True, mod_id


class ModuleStoreDialog(QDialog):
    """Interfaz para explorar módulos instalados, instalar `.mtu` verificados y compartir."""

    def __init__(self, app_ref=None, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.raiz = obtener_raiz_proyecto()
        self.setWindowTitle("🛒 Tienda y Gestor de Módulos (.mtu)")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(680, 460)
        self.resize(840, 540)
        self.setStyleSheet("""
            QDialog, QWidget { background-color: #13141c; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #f8fafc; }
            QFrame#Card { background-color: #1b1d29; border: 1px solid #2d3144; border-radius: 8px; }
            QListWidget, QTextEdit, QLineEdit {
                background-color: #0f111a; color: #f8fafc; border: 1px solid #2e3348; border-radius: 6px; padding: 6px;
            }
            QListWidget::item:selected { background-color: #4f46e5; color: #ffffff; }
            QPushButton { background-color: #252a3d; color: #f8fafc; border: 1px solid #38405e; border-radius: 6px; padding: 6px 12px; font-weight: 600; }
            QPushButton#Primary { background-color: #4f46e5; border-color: #6366f1; }
            QPushButton#Success { background-color: #059669; border-color: #10b981; }
        """)
        self._build_ui()
        self._reload_list()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)

        top = QHBoxLayout()
        lbl = QLabel("🛒 Módulos Instalados e Instalador Seguro (.mtu)")
        lbl.setStyleSheet("font-size: 15px; font-weight: 700;")
        top.addWidget(lbl)
        top.addStretch(1)

        btn_install = QPushButton("📥 Instalar .mtu desde PC...")
        btn_install.setObjectName("Primary")
        btn_install.clicked.connect(self._instalar_desde_archivo)
        top.addWidget(btn_install)

        btn_export = QPushButton("📦 Exportar / Compartir (.mtu)")
        btn_export.setObjectName("Success")
        btn_export.clicked.connect(lambda: abrir_compilador_modulos(self))
        top.addWidget(btn_export)
        root.addLayout(top)

        self.ent_filter = QLineEdit()
        self.ent_filter.setPlaceholderText("🔍 Buscar módulo instalado...")
        self.ent_filter.textChanged.connect(self._reload_list)
        root.addWidget(self.ent_filter)

        mid = QHBoxLayout()
        self.lista = QListWidget()
        self.lista.currentItemChanged.connect(self._on_select)
        mid.addWidget(self.lista, 2)

        detail = QFrame()
        detail.setObjectName("Card")
        d_lay = QVBoxLayout(detail)
        self.txt_detail = QTextEdit()
        self.txt_detail.setReadOnly(True)
        d_lay.addWidget(self.txt_detail)
        mid.addWidget(detail, 3)
        root.addLayout(mid, 1)

    def _reload_list(self):
        q = self.ent_filter.text().strip().lower()
        self.lista.clear()
        for m in escanear_modulos_disponibles(self.raiz):
            txt = f"{m['icono']}  {m['nombre']}  (v{m['version']})"
            if q and q not in txt.lower() and q not in m["id"].lower():
                continue
            it = QListWidgetItem(txt)
            it.setData(Qt.ItemDataRole.UserRole, m)
            self.lista.addItem(it)

    def _on_select(self, cur: QListWidgetItem | None, _prev=None):
        if not cur:
            return
        m = cur.data(Qt.ItemDataRole.UserRole)
        reqs = ", ".join(m["requirements"]) if m["requirements"] else "Ninguna"
        self.txt_detail.setHtml(
            f"<h3>{m['icono']} {m['nombre']}</h3>"
            f"<p><b>ID:</b> {m['id']}<br>"
            f"<b>Versión:</b> {m['version']}<br>"
            f"<b>Archivos:</b> {len(m['archivos'])}<br>"
            f"<b>Dependencias:</b> {reqs}</p>"
        )

    def _instalar_desde_archivo(self):
        ruta_str, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar paquete .mtu", str(Path.home()), "Paquetes Multitool (*.mtu *.zip)"
        )
        if not ruta_str:
            return
        ruta = Path(ruta_str)
        ok, manifest, warns = verificar_paquete_mtu(ruta)
        if not ok:
            QMessageBox.critical(self, "Paquete rechazado", "\n".join(warns))
            return
        if warns:
            resp = QMessageBox.warning(
                self, "Advertencia de seguridad",
                "Se detectaron patrones sensibles:\n• " + "\n• ".join(warns) + "\n\n¿Deseas instalarlo de todos modos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if resp != QMessageBox.StandardButton.Yes:
                return
        ok_inst, res = instalar_paquete_mtu(ruta, self.raiz)
        if ok_inst:
            self._reload_list()
            if self.app_ref and hasattr(self.app_ref, "cargar_modulos"):
                self.app_ref.cargar_modulos()
            QMessageBox.information(self, "Instalado", f"Módulo '{res}' instalado y cargado correctamente.")
        else:
            QMessageBox.critical(self, "Error", res)
