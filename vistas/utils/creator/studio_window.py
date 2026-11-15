# -*- coding: utf-8 -*-
"""Ventana principal del Estudio Modo Creador de Módulos (mode MT)."""

import importlib
import json
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
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
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from vistas.utils.compilar_modulo import abrir_compilador_modulos, obtener_raiz_proyecto
from vistas.utils.creator.code_editor import CodeEditor
from vistas.utils.creator.designer_canvas import DesignCanvas, PaletteDragList
from vistas.utils.creator.dialogs import generar_codigo_pyqt
from vistas.utils.creator.file_manager import CreatorFileManagerMixin
from vistas.utils.creator.helpers import (
    CREATOR_QSS,
    MULTITOOL_SNIPPETS,
    a_pascal_case,
    normalizar_id_modulo,
)


class ModuleCreatorDialog(CreatorFileManagerMixin, QDialog):
    """Estudio compacto estilo IntelliJ IDEA para crear y editar módulos de Multitool."""

    def __init__(self, parent=None, app_ref=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.raiz = obtener_raiz_proyecto()
        self.modulos_dir = self.raiz / "vistas" / "modulos"
        self.modulo_actual: str | None = None
        self.archivo_actual: Path | None = None
        self._dirty_code = False
        self._bloqueando_signals = False
        self._selected_design_idx = 0
        self.design_items: list[dict] = [
            {"tipo": "QLabel_title", "var": "lbl_titulo", "texto": "Mi Módulo", "placeholder": "", "x": 16, "y": 16, "w": 280, "h": 32, "target_sub": ""},
            {"tipo": "QLabel", "var": "lbl_desc", "texto": "Arrastra o edita componentes en el lienzo.", "placeholder": "", "x": 16, "y": 56, "w": 320, "h": 24, "target_sub": ""},
            {"tipo": "QLineEdit", "var": "ent_entrada", "texto": "", "placeholder": "Escribe aquí...", "x": 16, "y": 88, "w": 240, "h": 32, "target_sub": ""},
            {"tipo": "QPushButton", "var": "btn_accion", "texto": "Ejecutar", "placeholder": "", "x": 16, "y": 132, "w": 150, "h": 34, "target_sub": ""},
        ]

        self.setWindowTitle("🎨 Modo Creador de Módulos (mode MT)")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(720, 480)
        self.resize(980, 620)

        self.setStyleSheet(CREATOR_QSS)
        self._construir_ui()
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._guardar_archivo_actual)
        self._restaurar_ultimo_modulo()

    def _construir_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        top_bar = QFrame()
        top_bar.setObjectName("IdeBar")
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(8, 5, 8, 5)
        tb_lay.setSpacing(6)

        lbl_brand = QLabel("🎨 Modo Creador (mode MT)")
        lbl_brand.setObjectName("HeaderTitle")
        tb_lay.addWidget(lbl_brand)

        self.lbl_sync_badge = QLabel("● Sync en vivo")
        self.lbl_sync_badge.setStyleSheet("color: #34d399; font-weight: 600; font-size: 10px;")
        tb_lay.addWidget(self.lbl_sync_badge)
        tb_lay.addStretch(1)

        btn_home = QPushButton("🏠 Inicio")
        btn_home.setToolTip("Cerrar módulo activo y volver al salvapantallas")
        btn_home.clicked.connect(self._mostrar_salvapantallas)
        tb_lay.addWidget(btn_home)

        btn_nuevo = QPushButton("➕ Nuevo")
        btn_nuevo.setObjectName("Accent")
        btn_nuevo.clicked.connect(self._crear_nuevo_modulo_dialog)
        tb_lay.addWidget(btn_nuevo)

        self.btn_guardar = QPushButton("💾 Guardar")
        self.btn_guardar.clicked.connect(self._guardar_todo)
        tb_lay.addWidget(self.btn_guardar)

        self.btn_recargar = QPushButton("🔄 Hot-Reload")
        self.btn_recargar.clicked.connect(self._recargar_en_app)
        tb_lay.addWidget(self.btn_recargar)

        self.btn_compilar = QPushButton("📦 .mtu")
        self.btn_compilar.setObjectName("Success")
        self.btn_compilar.clicked.connect(self._abrir_compilador)
        tb_lay.addWidget(self.btn_compilar)

        root.addWidget(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left_panel = QFrame()
        left_panel.setObjectName("Panel")
        left_panel.setMinimumWidth(190)
        left_panel.setMaximumWidth(270)
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(7, 7, 7, 7)
        left_lay.setSpacing(5)

        lbl_proj = QLabel("Proyecto / Módulo")
        lbl_proj.setObjectName("Section")
        left_lay.addWidget(lbl_proj)

        self.cmb_modulos = QComboBox()
        self.cmb_modulos.currentTextChanged.connect(self._on_combo_modulo_cambiado)
        left_lay.addWidget(self.cmb_modulos)

        self.tree_archivos = QTreeWidget()
        self.tree_archivos.setHeaderLabel("Archivos")
        self.tree_archivos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_archivos.customContextMenuRequested.connect(self._menu_contextual_arbol)
        self.tree_archivos.itemDoubleClicked.connect(self._abrir_item_arbol)
        self.tree_archivos.itemClicked.connect(self._abrir_item_arbol)
        left_lay.addWidget(self.tree_archivos, 1)

        row_tree_btns = QHBoxLayout()
        row_tree_btns.setSpacing(3)
        self.tree_action_btns: list[QPushButton] = []
        for txt, tip, fn in [
            ("📄+", "Nuevo archivo (Visual o Funcionalidad)", self._crear_archivo_en_modulo),
            ("📁+", "Nueva carpeta", self._crear_carpeta_en_modulo),
            ("✏️", "Renombrar", self._renombrar_item_arbol),
            ("📦", "Mover", self._mover_item_arbol),
            ("🗑️", "Eliminar", self._eliminar_item_arbol),
            ("↻", "Refrescar", self._poblar_arbol_archivos),
        ]:
            b = QPushButton(txt)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row_tree_btns.addWidget(b)
            self.tree_action_btns.append(b)
        left_lay.addLayout(row_tree_btns)
        splitter.addWidget(left_panel)

        self.right_stack = QStackedWidget()
        self.right_stack.addWidget(self._crear_salvapantallas())

        self.tabs_editor = QTabWidget()
        self.tabs_editor.addTab(self._crear_tab_diseño(), "🎨 Diseño Visual")
        self.tabs_editor.addTab(self._crear_tab_codigo(), "💻 Código")
        self.tabs_editor.addTab(self._crear_tab_config(), "⚙️ Config & Reqs")
        self.right_stack.addWidget(self.tabs_editor)

        splitter.addWidget(self.right_stack)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        root.addWidget(splitter, 1)

        self.lbl_estado = QLabel("Listo.")
        self.lbl_estado.setStyleSheet("color: #94a3b8; font-size: 10px;")
        root.addWidget(self.lbl_estado)

    def _crear_salvapantallas(self) -> QWidget:
        w = QFrame()
        w.setObjectName("Panel")
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(10)

        lbl_ico = QLabel("🎨")
        lbl_ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_ico.setStyleSheet("font-size: 42px;")
        lay.addWidget(lbl_ico)

        lbl_t = QLabel("Estudio Creador de Módulos (mode MT)")
        lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_t.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        lay.addWidget(lbl_t)

        lbl_s = QLabel(
            "No hay ningún módulo abierto.\n"
            "Crea un módulo nuevo o selecciona uno del panel izquierdo para diseñar y programar."
        )
        lbl_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_s.setStyleSheet("color: #94a3b8; font-size: 11px;")
        lay.addWidget(lbl_s)

        btn_new = QPushButton("➕ Crear Nuevo Módulo")
        btn_new.setObjectName("Accent")
        btn_new.clicked.connect(self._crear_nuevo_modulo_dialog)
        lay.addWidget(btn_new, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lista_recientes = QListWidget()
        self.lista_recientes.setMaximumWidth(340)
        self.lista_recientes.setMaximumHeight(160)
        self.lista_recientes.itemDoubleClicked.connect(
            lambda it: self._abrir_modulo(it.data(Qt.ItemDataRole.UserRole))
        )
        lay.addWidget(self.lista_recientes)
        return w

    def _crear_tab_diseño(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        pal_frame = QFrame()
        pal_frame.setObjectName("Panel")
        pal_frame.setMinimumWidth(145)
        pal_frame.setMaximumWidth(175)
        pal_lay = QVBoxLayout(pal_frame)
        pal_lay.setContentsMargins(6, 6, 6, 6)
        pal_lay.setSpacing(4)
        lbl_p = QLabel("Arrastra al Lienzo")
        lbl_p.setObjectName("Section")
        pal_lay.addWidget(lbl_p)

        self.palette_list = PaletteDragList()
        self.palette_list.itemActivatedCustom.connect(
            lambda t, l, pw, ph: self._agregar_widget_diseno(t, l, 16, 16 + len(self.design_items) * 38, pw, ph)
        )
        pal_lay.addWidget(self.palette_list, 1)
        lay.addWidget(pal_frame)

        center_frame = QFrame()
        center_frame.setObjectName("Panel")
        c_lay = QVBoxLayout(center_frame)
        c_lay.setContentsMargins(6, 6, 6, 6)
        c_lay.setSpacing(4)

        top_c = QHBoxLayout()
        top_c.addWidget(QLabel("Lienzo Interactivo (arrastra y redimensiona — Sync automático)"))
        top_c.addStretch(1)
        btn_del = QPushButton("🗑 Quitar")
        btn_del.clicked.connect(self._eliminar_widget_diseno)
        top_c.addWidget(btn_del)
        c_lay.addLayout(top_c)

        scroll_canvas = QScrollArea()
        scroll_canvas.setWidgetResizable(True)
        self.design_canvas = DesignCanvas()
        self.design_canvas.widgetDropped.connect(self._agregar_widget_diseno)
        self.design_canvas.widgetSelected.connect(self._on_widget_diseno_sel)
        self.design_canvas.widgetMovedResized.connect(self._on_widget_moved_resized)
        scroll_canvas.setWidget(self.design_canvas)
        c_lay.addWidget(scroll_canvas, 1)
        lay.addWidget(center_frame, 1)

        insp_frame = QFrame()
        insp_frame.setObjectName("Panel")
        insp_frame.setMinimumWidth(185)
        insp_frame.setMaximumWidth(230)
        insp = QFormLayout(insp_frame)
        insp.setContentsMargins(7, 7, 7, 7)
        insp.setSpacing(5)
        lbl_i = QLabel("Propiedades")
        lbl_i.setObjectName("Section")
        insp.addRow(lbl_i)

        self.ent_prop_var = QLineEdit()
        self.ent_prop_var.textEdited.connect(self._actualizar_prop_widget)
        insp.addRow("Var:", self.ent_prop_var)

        self.ent_prop_texto = QLineEdit()
        self.ent_prop_texto.textEdited.connect(self._actualizar_prop_widget)
        insp.addRow("Texto:", self.ent_prop_texto)

        self.ent_prop_placeholder = QLineEdit()
        self.ent_prop_placeholder.textEdited.connect(self._actualizar_prop_widget)
        insp.addRow("Hint:", self.ent_prop_placeholder)

        self.spn_x = QSpinBox(); self.spn_x.setRange(0, 2000); self.spn_x.valueChanged.connect(self._actualizar_geo_desde_insp)
        self.spn_y = QSpinBox(); self.spn_y.setRange(0, 2000); self.spn_y.valueChanged.connect(self._actualizar_geo_desde_insp)
        self.spn_w = QSpinBox(); self.spn_w.setRange(24, 2000); self.spn_w.valueChanged.connect(self._actualizar_geo_desde_insp)
        self.spn_h = QSpinBox(); self.spn_h.setRange(16, 2000); self.spn_h.valueChanged.connect(self._actualizar_geo_desde_insp)
        insp.addRow("X:", self.spn_x)
        insp.addRow("Y:", self.spn_y)
        insp.addRow("Ancho:", self.spn_w)
        insp.addRow("Alto:", self.spn_h)

        self.cmb_target_sub = QComboBox()
        self.cmb_target_sub.currentTextChanged.connect(self._actualizar_prop_widget)
        insp.addRow("Acción/Sub:", self.cmb_target_sub)

        lay.addWidget(insp_frame)
        self._refrescar_lienzo(sync_code=False)
        return w

    def _crear_tab_codigo(self) -> QWidget:
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        self.lbl_archivo_abierto = QLabel("Ningún archivo abierto")
        self.lbl_archivo_abierto.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        hdr.addWidget(self.lbl_archivo_abierto, 1)

        btn_save_code = QPushButton("💾 Guardar Archivo")
        btn_save_code.setObjectName("Accent")
        btn_save_code.clicked.connect(self._guardar_archivo_actual)
        hdr.addWidget(btn_save_code)
        lay.addLayout(hdr)

        snip_bar = QHBoxLayout()
        snip_bar.setSpacing(4)
        snip_lbl = QLabel("Snippets:")
        snip_lbl.setStyleSheet("color: #93c5fd; font-weight: 600;")
        snip_bar.addWidget(snip_lbl)
        for name, code_snip in MULTITOOL_SNIPPETS.items():
            b = QPushButton(name)
            b.clicked.connect(lambda _c=False, s=code_snip: self._insertar_snippet(s))
            snip_bar.addWidget(b)
        snip_bar.addStretch(1)
        lay.addLayout(snip_bar)

        self.code_editor = CodeEditor()
        self.code_editor.textChanged.connect(self._on_code_changed)
        lay.addWidget(self.code_editor, 1)
        return cont

    def _crear_tab_config(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        meta_w = QWidget()
        m_lay = QVBoxLayout(meta_w)
        m_lay.setContentsMargins(8, 8, 8, 8)
        m_lay.setSpacing(8)

        cfg_box = QFrame()
        cfg_box.setObjectName("Panel")
        form = QFormLayout(cfg_box)
        form.setContentsMargins(10, 10, 10, 10)
        form.setSpacing(6)

        self.ent_cfg_name = QLineEdit()
        self.ent_cfg_icon = QLineEdit("🧩")
        self.ent_cfg_version = QLineEdit("1.0.0")
        self.spn_cfg_pos = QSpinBox()
        self.spn_cfg_pos.setRange(1, 999)
        self.chk_cfg_visible = QCheckBox("Visible en la barra de módulos")
        self.chk_cfg_visible.setChecked(True)

        form.addRow("Nombre visible:", self.ent_cfg_name)
        form.addRow("Icono:", self.ent_cfg_icon)
        form.addRow("Versión:", self.ent_cfg_version)
        form.addRow("Posición:", self.spn_cfg_pos)
        form.addRow("", self.chk_cfg_visible)

        btn_save_cfg = QPushButton("💾 Guardar config.json y requirements.txt")
        btn_save_cfg.setObjectName("Success")
        btn_save_cfg.clicked.connect(self._guardar_meta_modulo)
        form.addRow("", btn_save_cfg)
        m_lay.addWidget(cfg_box)

        req_box = QFrame()
        req_box.setObjectName("Panel")
        req_lay = QVBoxLayout(req_box)
        req_lay.setContentsMargins(10, 10, 10, 10)
        req_lay.setSpacing(5)
        req_lay.addWidget(QLabel("Dependencias Python (requirements.txt):"))
        self.txt_requirements = QPlainTextEdit()
        self.txt_requirements.setPlaceholderText("requests>=2.31.0\npsutil")
        self.txt_requirements.setMinimumHeight(110)
        req_lay.addWidget(self.txt_requirements, 1)
        m_lay.addWidget(req_box, 1)

        scroll.setWidget(meta_w)
        return scroll

    def _cargar_lista_modulos(self, seleccionar: str | None = None):
        self._bloqueando_signals = True
        self.cmb_modulos.clear()
        self.cmb_modulos.addItem("— Ninguno (Inicio) —")
        self.lista_recientes.clear()
        if self.modulos_dir.exists():
            dirs = sorted(
                [d.name for d in self.modulos_dir.iterdir() if d.is_dir() and not d.name.startswith("__")],
                key=str.lower,
            )
            self.cmb_modulos.addItems(dirs)
            for d in dirs:
                it = QListWidgetItem(f"📁  {d}")
                it.setData(Qt.ItemDataRole.UserRole, d)
                self.lista_recientes.addItem(it)
        self._bloqueando_signals = False

        if seleccionar and self.cmb_modulos.findText(seleccionar) >= 0:
            self._abrir_modulo(seleccionar)
        else:
            self._mostrar_salvapantallas()

    def _restaurar_ultimo_modulo(self):
        ultimo = None
        if self.app_ref and hasattr(self.app_ref, "config") and isinstance(self.app_ref.config, dict):
            ultimo = self.app_ref.config.get("creator_last_module")
        self._cargar_lista_modulos(seleccionar=ultimo)

    def _guardar_ultimo_modulo_config(self, nombre_mod: str | None):
        if self.app_ref and hasattr(self.app_ref, "config") and isinstance(self.app_ref.config, dict):
            self.app_ref.config["creator_last_module"] = nombre_mod or ""
            if hasattr(self.app_ref, "guardar_configuracion"):
                try:
                    self.app_ref.guardar_configuracion()
                except Exception:
                    pass

    def _set_acciones_habilitadas(self, habilitado: bool):
        for b in [self.btn_guardar, self.btn_recargar, self.btn_compilar, *self.tree_action_btns]:
            b.setEnabled(habilitado)

    def _mostrar_salvapantallas(self):
        self.modulo_actual = None
        self.archivo_actual = None
        self._bloqueando_signals = True
        self.cmb_modulos.setCurrentIndex(0)
        self._bloqueando_signals = False
        self.tree_archivos.clear()
        self.right_stack.setCurrentIndex(0)
        self._set_acciones_habilitadas(False)
        self._guardar_ultimo_modulo_config(None)
        self.lbl_estado.setText("Sin módulo activo. Selecciona o crea uno para comenzar.")

    def _on_combo_modulo_cambiado(self, texto: str):
        if self._bloqueando_signals:
            return
        if not texto or texto.startswith("—"):
            self._mostrar_salvapantallas()
        else:
            self._abrir_modulo(texto)

    def _abrir_modulo(self, nombre_mod: str):
        if not nombre_mod or not (self.modulos_dir / nombre_mod).exists():
            self._mostrar_salvapantallas()
            return
        self.modulo_actual = nombre_mod
        self._bloqueando_signals = True
        self.cmb_modulos.setCurrentText(nombre_mod)
        self._bloqueando_signals = False
        self.right_stack.setCurrentIndex(1)
        self._set_acciones_habilitadas(True)
        self._poblar_arbol_archivos()
        self._cargar_meta_modulo()
        self._abrir_archivo_principal_modulo()
        self._guardar_ultimo_modulo_config(nombre_mod)
        self.lbl_estado.setText(f"Editando: vistas/modulos/{nombre_mod}")

    def _abrir_archivo_principal_modulo(self):
        if not self.modulo_actual:
            return
        mod_dir = self.modulos_dir / self.modulo_actual
        cfg_path = mod_dir / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                subs = cfg.get("submodulos") or cfg.get("submodules") or []
                if subs and subs[0].get("file_name"):
                    cand = mod_dir / subs[0]["file_name"]
                    if cand.exists():
                        self._abrir_archivo_en_editor(cand)
                        return
            except Exception:
                pass
        for py in sorted(mod_dir.rglob("*.py")):
            if py.name != "__init__.py":
                self._abrir_archivo_en_editor(py)
                return

    def _abrir_archivo_en_editor(self, ruta: Path):
        if not ruta.exists() or not ruta.is_file():
            return
        self.archivo_actual = ruta
        contenido = ruta.read_text(encoding="utf-8", errors="replace")
        self._bloqueando_signals = True
        self.code_editor.highlighter.set_mode("json" if ruta.suffix.lower() == ".json" else "python")
        self.code_editor.setPlainText(contenido)
        self._bloqueando_signals = False
        self._dirty_code = False
        self.lbl_archivo_abierto.setText(str(ruta.relative_to(self.raiz)))

    def _on_code_changed(self):
        if not self._bloqueando_signals and self.archivo_actual:
            self._dirty_code = True
            self.lbl_archivo_abierto.setText(f"{self.archivo_actual.relative_to(self.raiz)} *")

    def _insertar_snippet(self, snippet: str):
        self.code_editor.insertPlainText(snippet)
        self.code_editor.setFocus()

    def _guardar_archivo_actual(self):
        if not self.archivo_actual:
            return
        self.archivo_actual.write_text(self.code_editor.toPlainText(), encoding="utf-8")
        self._dirty_code = False
        rel = str(self.archivo_actual.relative_to(self.raiz))
        self.lbl_archivo_abierto.setText(rel)
        self.lbl_estado.setText(f"Guardado: {rel}")
        if self.archivo_actual.name in {"config.json", "requirements.txt"}:
            self._cargar_meta_modulo()

    def _cargar_meta_modulo(self):
        if not self.modulo_actual:
            return
        mod_dir = self.modulos_dir / self.modulo_actual
        cfg_path = mod_dir / "config.json"
        cfg = {}
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                cfg = {}

        self.ent_cfg_name.setText(str(cfg.get("name") or cfg.get("nombre") or self.modulo_actual.capitalize()))
        self.ent_cfg_icon.setText(str(cfg.get("icon") or cfg.get("icono") or "🧩"))
        self.ent_cfg_version.setText(str(cfg.get("version") or "1.0.0"))
        self.spn_cfg_pos.setValue(int(cfg.get("position", 10) or 10))
        self.chk_cfg_visible.setChecked(bool(cfg.get("visible", True)))

        self._bloqueando_signals = True
        self.cmb_target_sub.clear()
        self.cmb_target_sub.addItem("")
        self.cmb_target_sub.addItem("notificacion:info")
        for s in cfg.get("submodulos") or []:
            if s.get("name"):
                self.cmb_target_sub.addItem(f"submodulo:{s['name']}")
        self._bloqueando_signals = False

        req_path = mod_dir / "requirements.txt"
        self.txt_requirements.setPlainText(
            req_path.read_text(encoding="utf-8", errors="ignore") if req_path.exists() else ""
        )

    def _guardar_meta_modulo(self):
        if not self.modulo_actual:
            return
        mod_dir = self.modulos_dir / self.modulo_actual
        cfg_path = mod_dir / "config.json"
        cfg = {}
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                cfg = {}

        cfg["name"] = self.ent_cfg_name.text().strip() or self.modulo_actual.capitalize()
        cfg["icon"] = self.ent_cfg_icon.text().strip() or "🧩"
        cfg["version"] = self.ent_cfg_version.text().strip() or "1.0.0"
        cfg["position"] = self.spn_cfg_pos.value()
        cfg["visible"] = self.chk_cfg_visible.isChecked()
        if "submodulos" not in cfg:
            cfg["submodulos"] = []

        cfg_path.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")
        (mod_dir / "requirements.txt").write_text(self.txt_requirements.toPlainText().strip() + "\n", encoding="utf-8")
        self._poblar_arbol_archivos()
        if self.archivo_actual and self.archivo_actual.name in {"config.json", "requirements.txt"}:
            self._abrir_archivo_en_editor(self.archivo_actual)
        self.lbl_estado.setText(f"config.json y requirements.txt guardados en {self.modulo_actual}.")

    def _guardar_todo(self):
        self._guardar_archivo_actual()
        self._guardar_meta_modulo()

    def _crear_nuevo_modulo_dialog(self):
        nombre, ok = QInputDialog.getText(
            self, "Crear Nuevo Módulo", "Nombre del nuevo módulo (vistas/modulos/<nombre>):"
        )
        if not ok or not nombre.strip():
            return
        mod_id = normalizar_id_modulo(nombre)
        mod_dir = self.modulos_dir / mod_id
        if mod_dir.exists():
            QMessageBox.warning(self, "Ya existe", f"La carpeta '{mod_id}' ya existe.")
            return

        sub_dir = mod_dir / "submodulos"
        utils_dir = mod_dir / "utils"
        sub_dir.mkdir(parents=True, exist_ok=True)
        utils_dir.mkdir(parents=True, exist_ok=True)
        (mod_dir / "__init__.py").write_text("", encoding="utf-8")
        (sub_dir / "__init__.py").write_text("", encoding="utf-8")
        (utils_dir / "__init__.py").write_text("", encoding="utf-8")

        clase_tab = f"Tab{a_pascal_case(mod_id)}"
        clase_root = f"{a_pascal_case(mod_id)}App"

        (utils_dir / "backend.py").write_text(
            "# -*- coding: utf-8 -*-\n"
            f'"""Backend del módulo {nombre.strip()}."""\n\n\n'
            f"class {a_pascal_case(mod_id)}Backend:\n"
            "    def procesar(self, texto: str) -> str:\n"
            '        return f"Procesado: {texto}" if texto else "Listo."\n',
            encoding="utf-8",
        )
        (mod_dir / f"{mod_id}.py").write_text(
            "# -*- coding: utf-8 -*-\n"
            f'"""Archivo raíz del módulo {nombre.strip()}."""\n\n'
            f"from .submodulos.tab_{mod_id} import {clase_tab}\n"
            f"from .utils.backend import {a_pascal_case(mod_id)}Backend\n\n\n"
            f"class {clase_root}({clase_tab}):\n"
            "    pass\n",
            encoding="utf-8",
        )

        config_data = {
            "name": nombre.strip(),
            "icon": "🧩",
            "version": "1.0.0",
            "position": 25,
            "visible": True,
            "submodulos": [
                {
                    "name": "Principal",
                    "file_name": f"submodulos/tab_{mod_id}.py",
                    "class_name": clase_tab,
                    "visible": True,
                    "icon": "🧩",
                    "alias": mod_id,
                    "position": 1,
                }
            ],
        }
        (mod_dir / "config.json").write_text(json.dumps(config_data, indent=4, ensure_ascii=False), encoding="utf-8")
        (mod_dir / "commands.json").write_text("{}", encoding="utf-8")
        (mod_dir / "requirements.txt").write_text("# Dependencias pip\n", encoding="utf-8")
        (sub_dir / f"tab_{mod_id}.py").write_text(
            generar_codigo_pyqt(self.design_items, clase_tab, nombre.strip()), encoding="utf-8"
        )

        self._cargar_lista_modulos(seleccionar=mod_id)
        self.lbl_estado.setText(f"✅ Módulo '{mod_id}' creado con raíz, frontend y backend.")

    def _agregar_widget_diseno(self, tipo: str, label: str, x: int = 16, y: int = 16, w: int = 200, h: int = 32):
        idx = len(self.design_items) + 1
        var = f"{tipo.lower().replace('q', '')}_{idx}"
        self.design_items.append({
            "tipo": tipo, "var": var, "texto": f"{label} {idx}",
            "placeholder": "Escribe aquí..." if tipo == "QLineEdit" else "",
            "x": x, "y": y, "w": w, "h": h, "target_sub": "",
        })
        self._selected_design_idx = len(self.design_items) - 1
        self._refrescar_lienzo(sync_code=True)
        self._cargar_inspector(self._selected_design_idx)

    def _on_widget_diseno_sel(self, idx: int):
        self._selected_design_idx = idx
        self._refrescar_lienzo(sync_code=False)
        self._cargar_inspector(idx)

    def _on_widget_moved_resized(self, idx: int, x: int, y: int, w: int, h: int):
        if 0 <= idx < len(self.design_items):
            self.design_items[idx].update({"x": x, "y": y, "w": w, "h": h})
            self._cargar_inspector(idx)
            self._sincronizar_diseno_a_codigo()

    def _cargar_inspector(self, idx: int):
        if idx < 0 or idx >= len(self.design_items):
            return
        it = self.design_items[idx]
        self._bloqueando_signals = True
        self.ent_prop_var.setText(it["var"])
        self.ent_prop_texto.setText(it["texto"])
        self.ent_prop_placeholder.setText(it.get("placeholder", ""))
        self.spn_x.setValue(int(it.get("x", 16)))
        self.spn_y.setValue(int(it.get("y", 16)))
        self.spn_w.setValue(int(it.get("w", 180)))
        self.spn_h.setValue(int(it.get("h", 32)))
        self.cmb_target_sub.setCurrentText(it.get("target_sub", ""))
        self._bloqueando_signals = False

    def _actualizar_prop_widget(self):
        if self._bloqueando_signals:
            return
        idx = self._selected_design_idx
        if 0 <= idx < len(self.design_items):
            it = self.design_items[idx]
            it["var"] = normalizar_id_modulo(self.ent_prop_var.text() or it["var"])
            it["texto"] = self.ent_prop_texto.text()
            it["placeholder"] = self.ent_prop_placeholder.text()
            it["target_sub"] = self.cmb_target_sub.currentText()
            self._refrescar_lienzo(sync_code=True)

    def _actualizar_geo_desde_insp(self):
        if self._bloqueando_signals:
            return
        idx = self._selected_design_idx
        if 0 <= idx < len(self.design_items):
            self.design_items[idx].update({
                "x": self.spn_x.value(), "y": self.spn_y.value(),
                "w": self.spn_w.value(), "h": self.spn_h.value(),
            })
            self._refrescar_lienzo(sync_code=True)

    def _eliminar_widget_diseno(self):
        idx = self._selected_design_idx
        if 0 <= idx < len(self.design_items):
            self.design_items.pop(idx)
            self._selected_design_idx = max(0, idx - 1)
            self._refrescar_lienzo(sync_code=True)
            self._cargar_inspector(self._selected_design_idx)

    def _refrescar_lienzo(self, sync_code: bool = True):
        self.design_canvas.render_items(self.design_items, self._selected_design_idx)
        if sync_code:
            self._sincronizar_diseno_a_codigo()

    def _sincronizar_diseno_a_codigo(self):
        if not self.modulo_actual or not self.archivo_actual or self.archivo_actual.suffix != ".py":
            return
        clase = f"Tab{a_pascal_case(self.archivo_actual.stem)}"
        cfg_path = self.modulos_dir / self.modulo_actual / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                for s in cfg.get("submodulos") or []:
                    if s.get("file_name") and (self.modulos_dir / self.modulo_actual / s["file_name"]) == self.archivo_actual:
                        clase = s.get("class_name") or clase
                        break
            except Exception:
                pass

        codigo = generar_codigo_pyqt(self.design_items, clase, self.ent_cfg_name.text() or self.modulo_actual)
        self._bloqueando_signals = True
        self.code_editor.setPlainText(codigo)
        self._bloqueando_signals = False
        self._guardar_archivo_actual()
        self.lbl_estado.setText("● Sincronizado en tiempo real y guardado.")

    def _recargar_en_app(self):
        self._guardar_todo()
        app = self.app_ref or self.parent()
        if not app:
            return
        if self.modulo_actual:
            prefijo = f"vistas.modulos.{self.modulo_actual.lower()}"
            for k in list(sys.modules.keys()):
                if k == prefijo or k.startswith(prefijo + "."):
                    sys.modules.pop(k, None)
            importlib.invalidate_caches()
        try:
            ya_registrado = any(
                m.get("folder", "").lower() == (self.modulo_actual or "").lower()
                or m.get("name", "").lower() == (self.modulo_actual or "").lower()
                for m in getattr(app, "modulos_cargados", [])
            )
            if ya_registrado and self.modulo_actual and hasattr(app, "recargar_modulo_en_caliente"):
                if app.recargar_modulo_en_caliente(self.modulo_actual):
                    self.lbl_estado.setText(f"🔥 Hot-Reload aplicado en '{self.modulo_actual}'.")
                    return
            if hasattr(app, "cargar_modulos"):
                app.cargar_modulos()
                self.lbl_estado.setText(f"🔄 Módulo '{self.modulo_actual}' recargado en Multitool.")
        except Exception as e:
            QMessageBox.warning(self, "Aviso", f"No se pudo recargar:\n{e}")

    def _abrir_compilador(self):
        self._guardar_todo()
        abrir_compilador_modulos(parent=self, modulo_preseleccionado=self.modulo_actual)


def abrir_creador_modulos(parent=None, app_ref=None):
    """Abre el estudio Modo Creador de Módulos (mode MT) como ventana independiente no bloqueante."""
    holder = app_ref or parent
    existing = getattr(holder, "_creador_modulos_win", None) if holder is not None else None
    if existing is not None:
        try:
            if existing.isMinimized():
                existing.showNormal()
            existing.show()
            existing.raise_()
            existing.activateWindow()
            return existing
        except RuntimeError:
            pass

    win = ModuleCreatorDialog(parent=None, app_ref=app_ref or parent)
    if holder is not None:
        holder._creador_modulos_win = win
    win.show()
    win.raise_()
    win.activateWindow()
    return win
