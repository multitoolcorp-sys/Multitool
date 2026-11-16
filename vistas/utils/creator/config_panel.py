# -*- coding: utf-8 -*-
"""
Panel de Configuración Visual del Módulo:
- Metadatos (`config.json`)
- Editor visual de `submodulos` (reordenar, activar/desactivar, editar alias/icono/clase)
- Editor visual de `commands.json`
- Editor e instalador de `requirements.txt` (`pip install -r`) en segundo plano
"""

import json
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class PipInstallWorker(QThread):
    """Ejecuta `pip install -r requirements.txt` sin bloquear la interfaz."""

    output_line = pyqtSignal(str)
    finished_ok = pyqtSignal(bool)

    def __init__(self, req_path: Path):
        super().__init__()
        self.req_path = req_path

    def run(self):
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-r", str(self.req_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if proc.stdout:
                for line in proc.stdout:
                    self.output_line.emit(line.rstrip())
            rc = proc.wait()
            self.finished_ok.emit(rc == 0)
        except Exception as exc:
            self.output_line.emit(f"Error ejecutando pip: {exc}")
            self.finished_ok.emit(False)


class ModuleConfigPanel(QScrollArea):
    """Panel visual completo para config.json, submodulos, commands.json y requirements.txt."""

    log_output = pyqtSignal(str, bool)  # (texto, es_error)
    config_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.mod_dir: Path | None = None
        self._cfg_data: dict = {}
        self._cmds_data: dict = {}
        self._pip_worker: PipInstallWorker | None = None
        self._build_ui()

    def _build_ui(self):
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # 1. Metadatos principales
        cfg_box = QFrame()
        cfg_box.setObjectName("Panel")
        form = QFormLayout(cfg_box)
        form.setContentsMargins(10, 10, 10, 10)
        form.setSpacing(5)
        lbl_m = QLabel("Configuración General (config.json)")
        lbl_m.setObjectName("Section")
        form.addRow(lbl_m)

        self.ent_name = QLineEdit()
        self.ent_icon = QLineEdit("🧩")
        self.ent_version = QLineEdit("1.0.0")
        self.spn_pos = QSpinBox()
        self.spn_pos.setRange(1, 999)
        self.cmb_os = QComboBox()
        self.cmb_os.addItem("Todos (Windows, Linux, macOS)", ["all"])
        self.cmb_os.addItem("Solo Windows", ["windows"])
        self.cmb_os.addItem("Solo Linux", ["linux"])
        self.cmb_os.addItem("Solo macOS", ["macos"])
        self.cmb_os.addItem("Windows + Linux", ["windows", "linux"])
        self.chk_visible = QCheckBox("Visible en la barra de módulos")
        self.chk_visible.setChecked(True)

        form.addRow("Nombre:", self.ent_name)
        form.addRow("Icono:", self.ent_icon)
        form.addRow("Versión:", self.ent_version)
        form.addRow("Posición:", self.spn_pos)
        form.addRow("Sistemas (os):", self.cmb_os)
        form.addRow("", self.chk_visible)
        lay.addWidget(cfg_box)

        # 2. Editor visual de Submódulos
        sub_box = QFrame()
        sub_box.setObjectName("Panel")
        s_lay = QVBoxLayout(sub_box)
        s_lay.setContentsMargins(10, 10, 10, 10)
        s_lay.setSpacing(5)
        lbl_s = QLabel("Submódulos (Pestañas del Módulo)")
        lbl_s.setObjectName("Section")
        s_lay.addWidget(lbl_s)

        self.list_subs = QListWidget()
        self.list_subs.setMaximumHeight(120)
        s_lay.addWidget(self.list_subs)

        r_sub = QHBoxLayout()
        for txt, fn in [
            ("⬆ Subir", lambda: self._mover_sub(-1)),
            ("⬇ Bajar", lambda: self._mover_sub(1)),
            ("👁️ Activar/Ocultar", self._toggle_sub_visible),
            ("✏️ Editar", self._editar_sub),
            ("🗑 Quitar", self._quitar_sub),
        ]:
            b = QPushButton(txt)
            b.clicked.connect(fn)
            r_sub.addWidget(b)
        r_sub.addStretch(1)
        s_lay.addLayout(r_sub)
        lay.addWidget(sub_box)

        # 3. Editor visual de commands.json
        cmd_box = QFrame()
        cmd_box.setObjectName("Panel")
        c_lay = QVBoxLayout(cmd_box)
        c_lay.setContentsMargins(10, 10, 10, 10)
        c_lay.setSpacing(5)
        lbl_c = QLabel("Comandos Rápidos (commands.json)")
        lbl_c.setObjectName("Section")
        c_lay.addWidget(lbl_c)

        self.list_cmds = QListWidget()
        self.list_cmds.setMaximumHeight(95)
        c_lay.addWidget(self.list_cmds)

        r_cmd = QHBoxLayout()
        btn_add_cmd = QPushButton("➕ Comando")
        btn_add_cmd.clicked.connect(self._agregar_comando)
        btn_del_cmd = QPushButton("🗑 Quitar")
        btn_del_cmd.clicked.connect(self._quitar_comando)
        r_cmd.addWidget(btn_add_cmd)
        r_cmd.addWidget(btn_del_cmd)
        r_cmd.addStretch(1)
        c_lay.addLayout(r_cmd)
        lay.addWidget(cmd_box)

        # 4. Dependencias (requirements.txt + pip install)
        req_box = QFrame()
        req_box.setObjectName("Panel")
        q_lay = QVBoxLayout(req_box)
        q_lay.setContentsMargins(10, 10, 10, 10)
        q_lay.setSpacing(5)
        lbl_r = QLabel("Dependencias Python (requirements.txt)")
        lbl_r.setObjectName("Section")
        q_lay.addWidget(lbl_r)

        self.txt_reqs = QPlainTextEdit()
        self.txt_reqs.setPlaceholderText("requests>=2.31.0\npsutil")
        self.txt_reqs.setMaximumHeight(90)
        q_lay.addWidget(self.txt_reqs)

        r_btns = QHBoxLayout()
        self.btn_pip = QPushButton("📥 Instalar Dependencias (pip)")
        self.btn_pip.clicked.connect(self._instalar_deps)
        btn_save = QPushButton("💾 Guardar Config, Comandos y Reqs")
        btn_save.setObjectName("Success")
        btn_save.clicked.connect(self.save_all)
        r_btns.addWidget(self.btn_pip)
        r_btns.addStretch(1)
        r_btns.addWidget(btn_save)
        q_lay.addLayout(r_btns)
        lay.addWidget(req_box)

        self.setWidget(cont)

    def load_module(self, mod_dir: Path):
        self.mod_dir = mod_dir
        cfg_path = mod_dir / "config.json"
        self._cfg_data = {}
        if cfg_path.exists():
            try:
                self._cfg_data = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                self._cfg_data = {}

        self.ent_name.setText(str(self._cfg_data.get("name") or self._cfg_data.get("nombre") or mod_dir.name.capitalize()))
        self.ent_icon.setText(str(self._cfg_data.get("icon") or self._cfg_data.get("icono") or "🧩"))
        self.ent_version.setText(str(self._cfg_data.get("version") or "1.0.0"))
        self.spn_pos.setValue(int(self._cfg_data.get("position", 10) or 10))
        os_val = self._cfg_data.get("os") or ["all"]
        idx_os = self.cmb_os.findData(os_val)
        self.cmb_os.setCurrentIndex(idx_os if idx_os >= 0 else 0)
        self.chk_visible.setChecked(bool(self._cfg_data.get("visible", True)))
        self._render_subs()

        cmd_path = mod_dir / "commands.json"
        self._cmds_data = {}
        if cmd_path.exists():
            try:
                loaded = json.loads(cmd_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self._cmds_data = loaded
            except Exception:
                self._cmds_data = {}
        self._render_cmds()

        req_path = mod_dir / "requirements.txt"
        self.txt_reqs.setPlainText(req_path.read_text(encoding="utf-8", errors="ignore") if req_path.exists() else "")

    def _render_subs(self):
        self.list_subs.clear()
        for s in self._cfg_data.get("submodulos") or []:
            vis = "👁️" if s.get("visible", True) else "🚫"
            txt = f"{vis} {s.get('icon', '🧩')} {s.get('name', '?')}  —  {s.get('file_name', '')} ({s.get('class_name', '')}) [alias: {s.get('alias', '')}]"
            self.list_subs.addItem(txt)

    def _mover_sub(self, delta: int):
        subs = self._cfg_data.get("submodulos") or []
        row = self.list_subs.currentRow()
        nuevo = row + delta
        if 0 <= row < len(subs) and 0 <= nuevo < len(subs):
            subs[row], subs[nuevo] = subs[nuevo], subs[row]
            for i, s in enumerate(subs):
                s["position"] = i + 1
            self._render_subs()
            self.list_subs.setCurrentRow(nuevo)

    def _toggle_sub_visible(self):
        subs = self._cfg_data.get("submodulos") or []
        row = self.list_subs.currentRow()
        if 0 <= row < len(subs):
            subs[row]["visible"] = not subs[row].get("visible", True)
            self._render_subs()
            self.list_subs.setCurrentRow(row)

    def _editar_sub(self):
        subs = self._cfg_data.get("submodulos") or []
        row = self.list_subs.currentRow()
        if not (0 <= row < len(subs)):
            return
        s = subs[row]
        dlg = QDialog(self)
        dlg.setWindowTitle("Editar Submódulo")
        dlg.setStyleSheet("QDialog, QWidget { background: #151824; color: #f8fafc; } QLineEdit { background: #0f111a; color: #f8fafc; border: 1px solid #38405e; padding: 4px; }")
        f = QFormLayout(dlg)
        e_name = QLineEdit(s.get("name", ""))
        e_icon = QLineEdit(s.get("icon", "🧩"))
        e_alias = QLineEdit(s.get("alias", ""))
        e_file = QLineEdit(s.get("file_name", ""))
        e_cls = QLineEdit(s.get("class_name", ""))
        f.addRow("Nombre:", e_name)
        f.addRow("Icono:", e_icon)
        f.addRow("Alias:", e_alias)
        f.addRow("Archivo:", e_file)
        f.addRow("Clase:", e_cls)
        btn_ok = QPushButton("Aceptar")
        btn_ok.clicked.connect(dlg.accept)
        f.addRow(btn_ok)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            s["name"] = e_name.text().strip() or s.get("name", "")
            s["icon"] = e_icon.text().strip() or "🧩"
            s["alias"] = e_alias.text().strip()
            s["file_name"] = e_file.text().strip()
            s["class_name"] = e_cls.text().strip()
            self._render_subs()
            self.list_subs.setCurrentRow(row)

    def _quitar_sub(self):
        subs = self._cfg_data.get("submodulos") or []
        row = self.list_subs.currentRow()
        if 0 <= row < len(subs):
            subs.pop(row)
            self._render_subs()

    def _render_cmds(self):
        self.list_cmds.clear()
        for k, v in self._cmds_data.items():
            desc = v.get("description", v) if isinstance(v, dict) else str(v)
            it = QListWidgetItem(f"⚡ {k}  —  {desc}")
            it.setData(Qt.ItemDataRole.UserRole, k)
            self.list_cmds.addItem(it)

    def _agregar_comando(self):
        cmd, ok = QInputDialog.getText(self, "Nuevo Comando", "Nombre del comando (ej: abrir_panel):")
        if not ok or not cmd.strip():
            return
        desc, ok2 = QInputDialog.getText(self, "Descripción", "Descripción breve:")
        if not ok2:
            return
        self._cmds_data[cmd.strip()] = {"description": desc.strip(), "action": cmd.strip()}
        self._render_cmds()

    def _quitar_comando(self):
        it = self.list_cmds.currentItem()
        if not it:
            return
        k = it.data(Qt.ItemDataRole.UserRole)
        self._cmds_data.pop(k, None)
        self._render_cmds()

    def save_all(self):
        if not self.mod_dir:
            return
        self._cfg_data["name"] = self.ent_name.text().strip() or self.mod_dir.name.capitalize()
        self._cfg_data["icon"] = self.ent_icon.text().strip() or "🧩"
        self._cfg_data["version"] = self.ent_version.text().strip() or "1.0.0"
        self._cfg_data["position"] = self.spn_pos.value()
        self._cfg_data["os"] = self.cmb_os.currentData() or ["all"]
        self._cfg_data["visible"] = self.chk_visible.isChecked()
        self._cfg_data.setdefault("submodulos", [])

        (self.mod_dir / "config.json").write_text(
            json.dumps(self._cfg_data, indent=4, ensure_ascii=False), encoding="utf-8"
        )
        (self.mod_dir / "commands.json").write_text(
            json.dumps(self._cmds_data, indent=4, ensure_ascii=False), encoding="utf-8"
        )
        (self.mod_dir / "requirements.txt").write_text(
            self.txt_reqs.toPlainText().strip() + "\n", encoding="utf-8"
        )
        self.log_output.emit(f"✔ Guardado config.json, commands.json y requirements.txt en {self.mod_dir.name}", False)
        self.config_saved.emit()

    def _instalar_deps(self):
        if not self.mod_dir:
            return
        self.save_all()
        req_path = self.mod_dir / "requirements.txt"
        self.btn_pip.setEnabled(False)
        self.log_output.emit(f"⏳ Ejecutando pip install -r {req_path.name}...", False)
        self._pip_worker = PipInstallWorker(req_path)
        self._pip_worker.output_line.connect(lambda ln: self.log_output.emit(ln, False))
        self._pip_worker.finished_ok.connect(self._on_pip_done)
        self._pip_worker.start()

    def _on_pip_done(self, ok: bool):
        self.btn_pip.setEnabled(True)
        self.log_output.emit(
            "✅ Dependencias instaladas correctamente." if ok else "❌ pip finalizó con errores.",
            not ok,
        )

