# -*- coding: utf-8 -*-
"""
Pestaña independiente por archivo abierto en el IDE (como IntelliJ / VS Code).
- Si el archivo es Visual (submódulo UI / clase PyQt6): ofrece conmutador 🎨 Visual | 💻 Código
  con sincronización bidireccional en tiempo real (AST <-> Lienzo) y selector de Layout responsivo.
- Si es Funcionalidad / JSON / TXT: muestra únicamente 💻 Código (+ snippets Multitool si es .py).
"""

import json
from pathlib import Path

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from vistas.utils.creator.ast_sync import LAYOUT_MODES, generate_pyqt_from_design, parse_pyqt_to_design
from vistas.utils.creator.code_editor import CodeEditor
from vistas.utils.creator.designer_canvas import DesignCanvas, PaletteDragList
from vistas.utils.creator.helpers import MULTITOOL_SNIPPETS, a_pascal_case, normalizar_id_modulo


class FileEditorTab(QWidget):
    """Pestaña individual para un archivo abierto del módulo."""

    dirtyChanged = pyqtSignal(object, bool)
    statusMessage = pyqtSignal(str)

    def __init__(self, file_path: Path, mod_dir: Path, is_visual: bool, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.mod_dir = mod_dir
        self.is_visual = is_visual
        self.dirty = False
        self._blocking = False
        self._selected_idx = 0
        self.layout_mode = "free"
        self.design_items: list[dict] = []

        self._code_sync_timer = QTimer(self)
        self._code_sync_timer.setSingleShot(True)
        self._code_sync_timer.setInterval(450)
        self._code_sync_timer.timeout.connect(self._sync_code_to_visual)

        self._build_ui()
        self.load_from_disk()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Barra superior de la pestaña
        bar = QHBoxLayout()
        bar.setSpacing(6)

        if self.is_visual:
            self.btn_mode_visual = QPushButton("🎨 Visual")
            self.btn_mode_code = QPushButton("💻 Código")
            self.btn_mode_visual.setCheckable(True)
            self.btn_mode_code.setCheckable(True)
            self.btn_mode_visual.setChecked(True)
            self.btn_mode_visual.clicked.connect(lambda: self._switch_mode(0))
            self.btn_mode_code.clicked.connect(lambda: self._switch_mode(1))
            bar.addWidget(self.btn_mode_visual)
            bar.addWidget(self.btn_mode_code)

            bar.addWidget(QLabel("Layout:"))
            self.cmb_layout = QComboBox()
            for lbl, val in LAYOUT_MODES:
                self.cmb_layout.addItem(lbl, val)
            self.cmb_layout.currentIndexChanged.connect(self._on_layout_mode_changed)
            bar.addWidget(self.cmb_layout)
        else:
            lbl_ro = QLabel("💻 Modo Código (Archivo de Funcionalidad / Datos)")
            lbl_ro.setStyleSheet("color: #93c5fd; font-weight: 600;")
            bar.addWidget(lbl_ro)

        bar.addStretch(1)
        btn_save = QPushButton("💾 Guardar")
        btn_save.setObjectName("Accent")
        btn_save.clicked.connect(self.save_to_disk)
        bar.addWidget(btn_save)
        root.addLayout(bar)

        self.stack = QStackedWidget()
        if self.is_visual:
            self.stack.addWidget(self._build_visual_view())
        self.stack.addWidget(self._build_code_view())
        root.addWidget(self.stack, 1)

    def _build_visual_view(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        pal_frame = QFrame()
        pal_frame.setObjectName("Panel")
        pal_frame.setMinimumWidth(140)
        pal_frame.setMaximumWidth(168)
        p_lay = QVBoxLayout(pal_frame)
        p_lay.setContentsMargins(5, 5, 5, 5)
        p_lay.setSpacing(4)
        lbl_p = QLabel("Arrastra al Lienzo")
        lbl_p.setObjectName("Section")
        p_lay.addWidget(lbl_p)
        self.palette_list = PaletteDragList()
        self.palette_list.itemActivatedCustom.connect(
            lambda t, l, pw, ph: self._add_widget(t, l, 16, 16 + len(self.design_items) * 38, pw, ph)
        )
        p_lay.addWidget(self.palette_list, 1)
        lay.addWidget(pal_frame)

        center = QFrame()
        center.setObjectName("Panel")
        c_lay = QVBoxLayout(center)
        c_lay.setContentsMargins(5, 5, 5, 5)
        c_lay.setSpacing(4)

        top_c = QHBoxLayout()
        top_c.addWidget(QLabel("Lienzo (arrastra, redimensiona y edita — Sync bidireccional)"))
        top_c.addStretch(1)
        btn_del = QPushButton("🗑 Quitar")
        btn_del.clicked.connect(self._remove_selected_widget)
        top_c.addWidget(btn_del)
        c_lay.addLayout(top_c)

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        self.canvas = DesignCanvas()
        self.canvas.widgetDropped.connect(self._add_widget)
        self.canvas.widgetSelected.connect(self._on_widget_selected)
        self.canvas.widgetMovedResized.connect(self._on_widget_moved_resized)
        sc.setWidget(self.canvas)
        c_lay.addWidget(sc, 1)
        lay.addWidget(center, 1)

        insp_frame = QFrame()
        insp_frame.setObjectName("Panel")
        insp_frame.setMinimumWidth(175)
        insp_frame.setMaximumWidth(215)
        insp = QFormLayout(insp_frame)
        insp.setContentsMargins(6, 6, 6, 6)
        insp.setSpacing(4)
        lbl_i = QLabel("Propiedades")
        lbl_i.setObjectName("Section")
        insp.addRow(lbl_i)

        self.ent_var = QLineEdit(); self.ent_var.textEdited.connect(self._on_prop_edited)
        self.ent_texto = QLineEdit(); self.ent_texto.textEdited.connect(self._on_prop_edited)
        self.ent_hint = QLineEdit(); self.ent_hint.textEdited.connect(self._on_prop_edited)
        self.spn_x = QSpinBox(); self.spn_x.setRange(0, 2000); self.spn_x.valueChanged.connect(self._on_geo_spin)
        self.spn_y = QSpinBox(); self.spn_y.setRange(0, 2000); self.spn_y.valueChanged.connect(self._on_geo_spin)
        self.spn_w = QSpinBox(); self.spn_w.setRange(24, 2000); self.spn_w.valueChanged.connect(self._on_geo_spin)
        self.spn_h = QSpinBox(); self.spn_h.setRange(16, 2000); self.spn_h.valueChanged.connect(self._on_geo_spin)
        self.cmb_action = QComboBox(); self.cmb_action.currentTextChanged.connect(self._on_prop_edited)

        insp.addRow("Var:", self.ent_var)
        insp.addRow("Texto:", self.ent_texto)
        insp.addRow("Hint:", self.ent_hint)
        insp.addRow("X:", self.spn_x)
        insp.addRow("Y:", self.spn_y)
        insp.addRow("Ancho:", self.spn_w)
        insp.addRow("Alto:", self.spn_h)
        insp.addRow("Acción:", self.cmb_action)
        lay.addWidget(insp_frame)
        return w

    def _build_code_view(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        if self.file_path.suffix == ".py":
            sb = QHBoxLayout()
            sb.setSpacing(4)
            lbl = QLabel("Snippets:")
            lbl.setStyleSheet("color: #93c5fd; font-weight: 600;")
            sb.addWidget(lbl)
            for name, code_snip in MULTITOOL_SNIPPETS.items():
                b = QPushButton(name)
                b.clicked.connect(lambda _c=False, s=code_snip: self._insert_snippet(s))
                sb.addWidget(b)
            sb.addStretch(1)
            lay.addLayout(sb)

        self.code_editor = CodeEditor()
        self.code_editor.highlighter.set_mode("json" if self.file_path.suffix.lower() == ".json" else "python")
        self.code_editor.textChanged.connect(self._on_code_text_changed)
        lay.addWidget(self.code_editor, 1)
        return w

    def _switch_mode(self, idx: int):
        if not self.is_visual:
            return
        self.btn_mode_visual.setChecked(idx == 0)
        self.btn_mode_code.setChecked(idx == 1)
        if idx == 0:
            self._sync_code_to_visual()
        self.stack.setCurrentIndex(idx)

    def load_from_disk(self):
        if not self.file_path.exists():
            return
        text = self.file_path.read_text(encoding="utf-8", errors="replace")
        self._blocking = True
        self.code_editor.setPlainText(text)
        if self.is_visual:
            self._refresh_action_combo()
            items, lmode = parse_pyqt_to_design(text)
            self.design_items = items
            self.layout_mode = lmode
            idx_l = max(0, self.cmb_layout.findData(lmode))
            self.cmb_layout.setCurrentIndex(idx_l)
            self._selected_idx = 0 if items else -1
            self.canvas.render_items(self.design_items, self._selected_idx)
            self._load_inspector(self._selected_idx)
        self._blocking = False
        self._set_dirty(False)

    def save_to_disk(self) -> bool:
        try:
            self.file_path.write_text(self.code_editor.toPlainText(), encoding="utf-8")
            self._set_dirty(False)
            self.statusMessage.emit(f"Guardado: {self.file_path.name}")
            return True
        except Exception as exc:
            self.statusMessage.emit(f"Error al guardar: {exc}")
            return False

    def _set_dirty(self, state: bool):
        if self.dirty != state:
            self.dirty = state
            self.dirtyChanged.emit(self, state)

    def _refresh_action_combo(self):
        self.cmb_action.clear()
        self.cmb_action.addItem("")
        self.cmb_action.addItem("notificacion:info")
        cfg_path = self.mod_dir / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                for s in cfg.get("submodulos") or []:
                    if s.get("name"):
                        self.cmb_action.addItem(f"submodulo:{s['name']}")
            except Exception:
                pass

    def _on_code_text_changed(self):
        if self._blocking:
            return
        self._set_dirty(True)
        if self.is_visual:
            self._code_sync_timer.start()

    def _sync_code_to_visual(self):
        if not self.is_visual or self._blocking:
            return
        items, lmode = parse_pyqt_to_design(self.code_editor.toPlainText())
        if not items and self.code_editor.toPlainText().strip():
            return
        self._blocking = True
        self.design_items = items
        self.layout_mode = lmode
        idx_l = max(0, self.cmb_layout.findData(lmode))
        self.cmb_layout.setCurrentIndex(idx_l)
        if self._selected_idx >= len(items):
            self._selected_idx = len(items) - 1
        self.canvas.render_items(self.design_items, self._selected_idx)
        self._load_inspector(self._selected_idx)
        self._blocking = False

    def _sync_visual_to_code(self):
        if not self.is_visual or self._blocking:
            return
        clase = f"Tab{a_pascal_case(self.file_path.stem)}"
        cfg_path = self.mod_dir / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                for s in cfg.get("submodulos") or []:
                    if s.get("file_name") and (self.mod_dir / s["file_name"]) == self.file_path:
                        clase = s.get("class_name") or clase
                        break
            except Exception:
                pass
        code = generate_pyqt_from_design(self.design_items, clase, self.mod_dir.name, self.layout_mode)
        self._blocking = True
        self.code_editor.setPlainText(code)
        self._blocking = False
        self._set_dirty(True)
        self.statusMessage.emit("● Visual -> Código sincronizado")

    def _add_widget(self, tipo: str, label: str, x: int = 16, y: int = 16, w: int = 180, h: int = 32):
        idx = len(self.design_items) + 1
        var = f"{tipo.lower().replace('q', '')}_{idx}"
        self.design_items.append({
            "tipo": tipo, "var": var, "texto": f"{label} {idx}",
            "placeholder": "Escribe aquí..." if tipo == "QLineEdit" else "",
            "x": x, "y": y, "w": w, "h": h, "target_sub": "",
        })
        self._selected_idx = len(self.design_items) - 1
        self.canvas.render_items(self.design_items, self._selected_idx)
        self._load_inspector(self._selected_idx)
        self._sync_visual_to_code()

    def _on_widget_selected(self, idx: int):
        self._selected_idx = idx
        self.canvas.update_selection_only(idx)
        self._load_inspector(idx)

    def _on_widget_moved_resized(self, idx: int, x: int, y: int, w: int, h: int):
        if 0 <= idx < len(self.design_items):
            self.design_items[idx].update({"x": x, "y": y, "w": w, "h": h})
            self._load_inspector(idx)
            self._sync_visual_to_code()

    def _load_inspector(self, idx: int):
        if idx < 0 or idx >= len(self.design_items):
            return
        it = self.design_items[idx]
        self._blocking = True
        self.ent_var.setText(it["var"])
        self.ent_texto.setText(it.get("texto", ""))
        self.ent_hint.setText(it.get("placeholder", ""))
        self.spn_x.setValue(int(it.get("x", 16)))
        self.spn_y.setValue(int(it.get("y", 16)))
        self.spn_w.setValue(int(it.get("w", 180)))
        self.spn_h.setValue(int(it.get("h", 32)))
        self.cmb_action.setCurrentText(it.get("target_sub", ""))
        self._blocking = False

    def _on_prop_edited(self):
        if self._blocking or not (0 <= self._selected_idx < len(self.design_items)):
            return
        it = self.design_items[self._selected_idx]
        it["var"] = normalizar_id_modulo(self.ent_var.text() or it["var"])
        it["texto"] = self.ent_texto.text()
        it["placeholder"] = self.ent_hint.text()
        it["target_sub"] = self.cmb_action.currentText()
        self.canvas.render_items(self.design_items, self._selected_idx)
        self._sync_visual_to_code()

    def _on_geo_spin(self):
        if self._blocking or not (0 <= self._selected_idx < len(self.design_items)):
            return
        self.design_items[self._selected_idx].update({
            "x": self.spn_x.value(), "y": self.spn_y.value(),
            "w": self.spn_w.value(), "h": self.spn_h.value(),
        })
        self.canvas.render_items(self.design_items, self._selected_idx)
        self._sync_visual_to_code()

    def _on_layout_mode_changed(self):
        if self._blocking:
            return
        self.layout_mode = self.cmb_layout.currentData() or "free"
        self._sync_visual_to_code()

    def _remove_selected_widget(self):
        if 0 <= self._selected_idx < len(self.design_items):
            self.design_items.pop(self._selected_idx)
            self._selected_idx = max(-1, min(self._selected_idx, len(self.design_items) - 1))
            self.canvas.render_items(self.design_items, self._selected_idx)
            self._load_inspector(self._selected_idx)
            self._sync_visual_to_code()

    def _insert_snippet(self, snippet: str):
        self.code_editor.insertPlainText(snippet)
        self.code_editor.setFocus()
