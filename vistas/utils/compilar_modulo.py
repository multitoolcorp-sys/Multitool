# -*- coding: utf-8 -*-
"""
Empaquetador de Módulos para Usuarios (.mtu)
Permite exportar cualquier módulo de `vistas/modulos/` en un paquete `.mtu`
listo para compartir con otros usuarios de Multitool, sin dependencias web.
"""

import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

EXCLUDED_DIRS = {"__pycache__", ".git", ".pytest_cache", "node_modules", ".venv", "venv"}
EXCLUDED_EXTS = {".pyc", ".pyo", ".old", ".tmp", ".log"}


def obtener_raiz_proyecto() -> Path:
    """Devuelve la raíz del proyecto Multitool (contiene `vistas/modulos`)."""
    try:
        from controlador.utils.paths import get_resource_path
        ruta = Path(get_resource_path())
        if (ruta / "vistas" / "modulos").exists():
            return ruta
    except Exception:
        pass
    return Path(__file__).resolve().parents[2]


def escanear_modulos_disponibles(raiz: Path | None = None) -> list[dict]:
    """Descubre dinámicamente los módulos instalados en `vistas/modulos/`."""
    raiz = raiz or obtener_raiz_proyecto()
    modulos_dir = raiz / "vistas" / "modulos"
    if not modulos_dir.exists():
        return []

    encontrados = []
    for item in sorted(modulos_dir.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_dir() or item.name.startswith("__") or item.name.startswith("."):
            continue

        cfg_path = item / "config.json"
        cfg = {}
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}

        archivos = []
        total_bytes = 0
        for root, dirs, files in os.walk(item):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
            for fn in sorted(files):
                fp = Path(root) / fn
                if fp.suffix.lower() in EXCLUDED_EXTS:
                    continue
                rel_mod = fp.relative_to(item).as_posix()
                try:
                    size = fp.stat().st_size
                except OSError:
                    size = 0
                archivos.append((fp, rel_mod, size))
                total_bytes += size

        req_path = item / "requirements.txt"
        reqs = []
        if req_path.exists():
            try:
                reqs = [
                    line.strip()
                    for line in req_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip() and not line.strip().startswith("#")
                ]
            except Exception:
                reqs = []

        encontrados.append({
            "id": item.name,
            "nombre": cfg.get("name") or cfg.get("nombre") or item.name.capitalize(),
            "icono": cfg.get("icon") or cfg.get("icono") or "📦",
            "version": str(cfg.get("version") or "1.0.0"),
            "ruta": item,
            "config": cfg,
            "archivos": archivos,
            "total_bytes": total_bytes,
            "requirements": reqs,
        })
    return encontrados


def sugerir_siguiente_version(version_actual: str) -> str:
    """Incrementa el último dígito numérico de una versión semántica simple."""
    partes = [p for p in str(version_actual or "1.0.0").strip().split(".") if p]
    nums = []
    for p in partes:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    nums[-1] += 1
    return ".".join(str(n) for n in nums[:3])


class ModuleCompileWorker(QThread):
    """Hilo en segundo plano para empaquetar uno o más módulos en formato `.mtu`."""

    progreso = pyqtSignal(int, str)
    log_msg = pyqtSignal(str)
    terminado = pyqtSignal(bool, str, list)

    def __init__(
        self,
        raiz: Path,
        modulos: list[dict],
        version_nueva: str,
        notas: str,
        carpeta_salida: Path,
        actualizar_config_version: bool = True,
    ):
        super().__init__()
        self.raiz = raiz
        self.modulos = modulos
        self.version_nueva = version_nueva.strip() or "1.0.0"
        self.notas = notas.strip()
        self.carpeta_salida = carpeta_salida
        self.actualizar_config_version = actualizar_config_version

    def run(self):
        generados = []
        try:
            self.carpeta_salida.mkdir(parents=True, exist_ok=True)
            total_mods = max(len(self.modulos), 1)

            for idx, mod in enumerate(self.modulos):
                mod_id = mod["id"]
                mod_dir: Path = mod["ruta"]
                ver = self.version_nueva if total_mods == 1 else sugerir_siguiente_version(mod["version"])
                self.log_msg.emit(f"📦 Empaquetando módulo '{mod['nombre']}' (v{ver})...")

                # Actualizar versión en config.json local si el usuario lo activó
                cfg_path = mod_dir / "config.json"
                if self.actualizar_config_version and cfg_path.exists():
                    try:
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            cfg_data = json.load(f)
                        cfg_data["version"] = ver
                        with open(cfg_path, "w", encoding="utf-8") as f:
                            json.dump(cfg_data, f, indent=4, ensure_ascii=False)
                        self.log_msg.emit(f"   ✓ Versión actualizada en config.json -> {ver}")
                    except Exception as e:
                        self.log_msg.emit(f"   ⚠ No se pudo actualizar config.json: {e}")

                nombre_zip = f"{mod_id}_v{ver}.mtu"
                destino_mtu = self.carpeta_salida / nombre_zip

                archivos = mod["archivos"]
                total_files = max(len(archivos), 1)

                manifest = {
                    "format": "multitool-module-mtu",
                    "type": "module",
                    "module_id": mod_id,
                    "name": mod["nombre"],
                    "version": ver,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "notes": self.notas or f"Módulo {mod['nombre']} empaquetado localmente.",
                    "requirements": mod.get("requirements", []),
                    "files_count": len(archivos),
                }

                with zipfile.ZipFile(destino_mtu, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("manifest.json", json.dumps(manifest, indent=4, ensure_ascii=False))
                    for f_idx, (fp, _rel_mod, _size) in enumerate(archivos):
                        if not fp.exists():
                            continue
                        arcname = fp.relative_to(self.raiz).as_posix()
                        zf.write(fp, arcname)
                        pct_mod = ((idx + ((f_idx + 1) / total_files)) / total_mods) * 100
                        self.progreso.emit(int(pct_mod), f"Comprimiendo {mod_id}/{_rel_mod}...")

                size_kb = max(1, destino_mtu.stat().st_size // 1024)
                self.log_msg.emit(f"   ✅ Generado: {destino_mtu.name} ({size_kb} KB)")
                generados.append(str(destino_mtu))

            self.progreso.emit(100, "¡Empaquetado completado!")
            self.terminado.emit(
                True,
                f"Se empaquetaron {len(generados)} módulo(s) en:\n{self.carpeta_salida}",
                generados,
            )
        except Exception as exc:
            self.log_msg.emit(f"❌ Error al compilar módulo: {exc}")
            self.terminado.emit(False, str(exc), generados)


class ModuleCompilerDialog(QDialog):
    """Interfaz responsiva y amigable para que cualquier usuario compile y comparta módulos (.mtu)."""

    def __init__(self, parent=None, modulo_preseleccionado: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("📦 Compilador y Empaquetador de Módulos (.mtu)")
        self.setMinimumSize(640, 480)
        self.resize(920, 620)

        self.raiz = obtener_raiz_proyecto()
        self.modulos = escanear_modulos_disponibles(self.raiz)
        self.modulo_preseleccionado = modulo_preseleccionado
        self._worker = None
        self._ultimos_generados = []

        default_out = Path.home() / "Documents" / "Multitool_Modulos_Exportados"
        self.carpeta_salida = default_out

        self._aplicar_estilo()
        self._construir_ui()
        self._poblar_lista()

    def _aplicar_estilo(self):
        self.setStyleSheet("""
            QDialog, QWidget {
                background-color: #13141c;
                color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel, QCheckBox {
                color: #f8fafc;
                background: transparent;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QFrame#Card {
                background-color: #1b1d29;
                border: 1px solid #2d3144;
                border-radius: 10px;
            }
            QLabel#Title {
                font-size: 16px;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel#Subtitle {
                font-size: 12px;
                color: #9ca3af;
            }
            QLabel#Section {
                font-size: 12px;
                font-weight: 700;
                color: #a5b4fc;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QListWidget, QTextEdit, QLineEdit {
                background-color: #11131b;
                color: #e4e6f0;
                border: 1px solid #2e3348;
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-radius: 5px;
                margin-bottom: 2px;
            }
            QListWidget::item:selected {
                background-color: #4f46e5;
                color: #ffffff;
            }
            QPushButton {
                background-color: #26293a;
                color: #e4e6f0;
                border: 1px solid #383d56;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #32364d;
            }
            QPushButton#Primary {
                background-color: #4f46e5;
                border-color: #6366f1;
                color: #ffffff;
            }
            QPushButton#Primary:hover {
                background-color: #6366f1;
            }
            QPushButton#Primary:disabled {
                background-color: #2d3144;
                color: #7c8299;
                border-color: #2d3144;
            }
            QProgressBar {
                background-color: #11131b;
                border: 1px solid #2e3348;
                border-radius: 6px;
                text-align: center;
                height: 18px;
                color: #ffffff;
                font-size: 11px;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 5px;
            }
        """)

    def _construir_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(14, 14, 14, 14)
        root_lay.setSpacing(10)

        # Cabecera compacta
        header = QFrame()
        header.setObjectName("Card")
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(14, 10, 14, 10)
        h_lay.setSpacing(2)

        lbl_title = QLabel("📦 Exportar y Compartir Módulos (.mtu)")
        lbl_title.setObjectName("Title")
        lbl_sub = QLabel(
            "Empaqueta tus módulos locales en un archivo portátil .mtu para enviarlos por Discord, Drive, USB o correo. "
            "No sube ni modifica nada en la web."
        )
        lbl_sub.setObjectName("Subtitle")
        lbl_sub.setWordWrap(True)
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_sub)
        root_lay.addWidget(header)

        # Splitter principal responsivo
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Panel izquierdo: lista de módulos
        left_card = QFrame()
        left_card.setObjectName("Card")
        left_lay = QVBoxLayout(left_card)
        left_lay.setContentsMargins(12, 12, 12, 12)
        left_lay.setSpacing(8)

        lbl_mods = QLabel("1. Elige un módulo")
        lbl_mods.setObjectName("Section")
        left_lay.addWidget(lbl_mods)

        self.ent_filtro = QLineEdit()
        self.ent_filtro.setPlaceholderText("🔍 Filtrar módulo por nombre...")
        self.ent_filtro.textChanged.connect(self._filtrar_lista)
        left_lay.addWidget(self.ent_filtro)

        self.lista_modulos = QListWidget()
        self.lista_modulos.currentItemChanged.connect(self._on_modulo_seleccionado)
        left_lay.addWidget(self.lista_modulos, 1)

        btn_refrescar = QPushButton("🔄 Refrescar Módulos")
        btn_refrescar.clicked.connect(self._recargar_modulos)
        left_lay.addWidget(btn_refrescar)

        splitter.addWidget(left_card)

        # Panel derecho con ScrollArea para máxima responsividad en ventanas pequeñas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        right_container = QWidget()
        right_lay = QVBoxLayout(right_container)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(10)

        # Tarjeta de configuración del paquete
        cfg_card = QFrame()
        cfg_card.setObjectName("Card")
        cfg_lay = QVBoxLayout(cfg_card)
        cfg_lay.setContentsMargins(12, 12, 12, 12)
        cfg_lay.setSpacing(8)

        lbl_cfg = QLabel("2. Detalles del paquete .mtu")
        lbl_cfg.setObjectName("Section")
        cfg_lay.addWidget(lbl_cfg)

        self.lbl_info_modulo = QLabel("Selecciona un módulo de la lista izquierda.")
        self.lbl_info_modulo.setWordWrap(True)
        self.lbl_info_modulo.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        cfg_lay.addWidget(self.lbl_info_modulo)

        row_ver = QHBoxLayout()
        row_ver.setSpacing(8)
        row_ver.addWidget(QLabel("Versión del paquete:"))
        self.ent_version = QLineEdit("1.0.0")
        self.ent_version.setMaximumWidth(140)
        row_ver.addWidget(self.ent_version)
        self.chk_actualizar_cfg = QCheckBox("Guardar versión en config.json")
        self.chk_actualizar_cfg.setChecked(True)
        row_ver.addWidget(self.chk_actualizar_cfg, 1)
        cfg_lay.addLayout(row_ver)

        cfg_lay.addWidget(QLabel("Descripción / Notas para quien lo instale:"))
        self.txt_notas = QTextEdit()
        self.txt_notas.setPlaceholderText("Ej: Módulo creado en Modo Creador. Incluye utilidades...")
        self.txt_notas.setFixedHeight(64)
        cfg_lay.addWidget(self.txt_notas)

        cfg_lay.addWidget(QLabel("Carpeta donde guardar el archivo .mtu:"))
        row_out = QHBoxLayout()
        row_out.setSpacing(6)
        self.ent_salida = QLineEdit(str(self.carpeta_salida))
        self.ent_salida.setReadOnly(True)
        row_out.addWidget(self.ent_salida, 1)
        btn_carpeta = QPushButton("📁 Elegir...")
        btn_carpeta.clicked.connect(self._elegir_carpeta_salida)
        row_out.addWidget(btn_carpeta)
        cfg_lay.addLayout(row_out)

        right_lay.addWidget(cfg_card)

        # Tarjeta de contenido incluido + log
        files_card = QFrame()
        files_card.setObjectName("Card")
        files_lay = QVBoxLayout(files_card)
        files_lay.setContentsMargins(12, 12, 12, 12)
        files_lay.setSpacing(6)

        lbl_files = QLabel("3. Archivos incluidos y progreso")
        lbl_files.setObjectName("Section")
        files_lay.addWidget(lbl_files)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 9))
        self.txt_log.setMinimumHeight(130)
        files_lay.addWidget(self.txt_log, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        files_lay.addWidget(self.progress_bar)

        right_lay.addWidget(files_card, 1)
        scroll.setWidget(right_container)
        splitter.addWidget(scroll)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        root_lay.addWidget(splitter, 1)

        # Barra inferior de acciones
        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.btn_abrir_carpeta = QPushButton("📂 Abrir Carpeta de Salida")
        self.btn_abrir_carpeta.clicked.connect(self._abrir_carpeta_salida)
        footer.addWidget(self.btn_abrir_carpeta)

        footer.addStretch(1)

        self.btn_compilar = QPushButton("📦 Compilar Módulo (.mtu)")
        self.btn_compilar.setObjectName("Primary")
        self.btn_compilar.clicked.connect(self._iniciar_compilacion)
        footer.addWidget(self.btn_compilar)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.close)
        footer.addWidget(btn_cerrar)

        root_lay.addLayout(footer)

    def _poblar_lista(self):
        self.lista_modulos.clear()
        filtro = self.ent_filtro.text().strip().lower() if hasattr(self, "ent_filtro") else ""
        item_pre = None

        for mod in self.modulos:
            texto = f"{mod['icono']}  {mod['nombre']}  ({mod['id']})  — v{mod['version']}"
            if filtro and filtro not in texto.lower():
                continue
            it = QListWidgetItem(texto)
            it.setData(Qt.ItemDataRole.UserRole, mod)
            self.lista_modulos.addItem(it)
            if self.modulo_preseleccionado and mod["id"].lower() == self.modulo_preseleccionado.lower():
                item_pre = it

        if item_pre:
            self.lista_modulos.setCurrentItem(item_pre)
        elif self.lista_modulos.count() > 0:
            self.lista_modulos.setCurrentRow(0)

    def _filtrar_lista(self):
        self._poblar_lista()

    def _recargar_modulos(self):
        self.modulos = escanear_modulos_disponibles(self.raiz)
        self._poblar_lista()

    def _on_modulo_seleccionado(self, current: QListWidgetItem | None, _prev=None):
        if not current:
            self.btn_compilar.setEnabled(False)
            return
        mod = current.data(Qt.ItemDataRole.UserRole)
        self.btn_compilar.setEnabled(True)
        size_kb = max(1, mod["total_bytes"] // 1024)
        reqs_txt = ", ".join(mod["requirements"]) if mod["requirements"] else "Ninguna declarada"
        self.lbl_info_modulo.setText(
            f"<b>Módulo:</b> {mod['icono']} {mod['nombre']} (<code>vistas/modulos/{mod['id']}</code>)<br>"
            f"<b>Archivos:</b> {len(mod['archivos'])} archivo(s) (~{size_kb} KB) &nbsp;|&nbsp; "
            f"<b>Versión actual:</b> {mod['version']}<br>"
            f"<b>Dependencias:</b> {reqs_txt}"
        )
        self.ent_version.setText(sugerir_siguiente_version(mod["version"]))

        preview_lines = [f"Archivos que se empaquetarán en {mod['id']}_v{self.ent_version.text()}.mtu:"]
        for _fp, rel, sz in mod["archivos"][:40]:
            preview_lines.append(f"  • {rel} ({max(1, sz // 1024)} KB)")
        if len(mod["archivos"]) > 40:
            preview_lines.append(f"  ... y {len(mod['archivos']) - 40} archivo(s) más.")
        self.txt_log.setPlainText("\n".join(preview_lines))
        self.progress_bar.setValue(0)

    def _elegir_carpeta_salida(self):
        carpeta = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta para guardar el módulo .mtu", str(self.carpeta_salida)
        )
        if carpeta:
            self.carpeta_salida = Path(carpeta)
            self.ent_salida.setText(str(self.carpeta_salida))

    def _abrir_carpeta_salida(self):
        self.carpeta_salida.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(str(self.carpeta_salida))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(self.carpeta_salida)])
        else:
            subprocess.Popen(["xdg-open", str(self.carpeta_salida)])

    def _iniciar_compilacion(self):
        item = self.lista_modulos.currentItem()
        if not item:
            QMessageBox.warning(self, "Sin selección", "Selecciona un módulo para empaquetar.")
            return
        mod = item.data(Qt.ItemDataRole.UserRole)

        self.btn_compilar.setEnabled(False)
        self.txt_log.clear()
        self.progress_bar.setValue(0)

        self._worker = ModuleCompileWorker(
            raiz=self.raiz,
            modulos=[mod],
            version_nueva=self.ent_version.text(),
            notas=self.txt_notas.toPlainText(),
            carpeta_salida=self.carpeta_salida,
            actualizar_config_version=self.chk_actualizar_cfg.isChecked(),
        )
        self._worker.progreso.connect(self._on_progreso)
        self._worker.log_msg.connect(self.txt_log.append)
        self._worker.terminado.connect(self._on_terminado)
        self._worker.start()

    def _on_progreso(self, pct: int, texto: str):
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(f"{pct}% — {texto}")

    def _on_terminado(self, ok: bool, mensaje: str, generados: list):
        self.btn_compilar.setEnabled(True)
        self._ultimos_generados = generados
        if ok:
            self._recargar_modulos()
            QMessageBox.information(
                self,
                "¡Módulo Empaquetado!",
                f"{mensaje}\n\nYa puedes compartir el archivo .mtu con otros usuarios de Multitool.",
            )
        else:
            QMessageBox.critical(self, "Error al empaquetar", mensaje)


def abrir_compilador_modulos(parent=None, modulo_preseleccionado: str | None = None):
    """Abre el diálogo del compilador de módulos para usuarios."""
    dlg = ModuleCompilerDialog(parent=parent, modulo_preseleccionado=modulo_preseleccionado)
    dlg.exec()
    return dlg
