# -*- coding: utf-8 -*-
"""Ventana principal del Estudio Modo Creador de Módulos (mode MT)."""

import importlib
import json
import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from vistas.utils.compilar_modulo import abrir_compilador_modulos, obtener_raiz_proyecto
from vistas.utils.creator.ast_sync import generate_pyqt_from_design, parse_pyqt_to_design
from vistas.utils.creator.config_panel import ModuleConfigPanel
from vistas.utils.creator.dialogs import MODULE_TEMPLATES, NewModuleTemplateDialog
from vistas.utils.creator.file_manager import CreatorFileManagerMixin
from vistas.utils.creator.file_tab import FileEditorTab
from vistas.utils.creator.helpers import CREATOR_QSS, a_pascal_case, normalizar_id_modulo


class ModuleCreatorDialog(CreatorFileManagerMixin, QDialog):
    """Estudio compacto estilo IntelliJ IDEA con pestañas por archivo, sync bidireccional y consola."""

    def __init__(self, parent=None, app_ref=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.raiz = obtener_raiz_proyecto()
        self.modulos_dir = self.raiz / "vistas" / "modulos"
        self.modulo_actual: str | None = None
        self._bloqueando_signals = False
        self._open_tabs: dict[str, FileEditorTab] = {}

        self.setWindowTitle("🎨 Modo Creador de Módulos (mode MT)")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(740, 500)
        self.resize(1020, 650)

        self.setStyleSheet(CREATOR_QSS)
        self._construir_ui()
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._guardar_pestana_actual)
        self._restaurar_ultimo_modulo()

    def _construir_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(5)

        # Barra superior compacta
        top_bar = QFrame()
        top_bar.setObjectName("IdeBar")
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(8, 5, 8, 5)
        tb_lay.setSpacing(6)

        lbl_brand = QLabel("🎨 Modo Creador (mode MT)")
        lbl_brand.setObjectName("HeaderTitle")
        tb_lay.addWidget(lbl_brand)
        tb_lay.addStretch(1)

        btn_home = QPushButton("🏠 Inicio")
        btn_home.clicked.connect(self._mostrar_salvapantallas)
        tb_lay.addWidget(btn_home)

        btn_nuevo = QPushButton("➕ Nuevo")
        btn_nuevo.setObjectName("Accent")
        btn_nuevo.clicked.connect(self._crear_nuevo_modulo_dialog)
        tb_lay.addWidget(btn_nuevo)

        self.btn_config = QPushButton("⚙️ Config & Reqs")
        self.btn_config.clicked.connect(self._abrir_pestana_config)
        tb_lay.addWidget(self.btn_config)

        self.btn_guardar = QPushButton("💾 Guardar Todo")
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

        # Splitter principal + panel inferior de Output/Errores
        v_split = QSplitter(Qt.Orientation.Vertical)
        v_split.setChildrenCollapsible(False)

        h_split = QSplitter(Qt.Orientation.Horizontal)
        h_split.setChildrenCollapsible(False)

        # Panel izquierdo: Proyecto + Gestor de Archivos
        left_panel = QFrame()
        left_panel.setObjectName("Panel")
        left_panel.setMinimumWidth(190)
        left_panel.setMaximumWidth(265)
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(6, 6, 6, 6)
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
        h_split.addWidget(left_panel)

        # Panel derecho: 0 = Salvapantallas, 1 = Pestañas de archivos abiertas
        self.right_stack = QStackedWidget()
        self.right_stack.addWidget(self._crear_salvapantallas())

        self.open_tabs_widget = QTabWidget()
        self.open_tabs_widget.setTabsClosable(True)
        self.open_tabs_widget.tabCloseRequested.connect(self._on_cerrar_pestana_idx)
        self.config_panel = ModuleConfigPanel()
        self.config_panel.log_output.connect(self._append_output)
        self.config_panel.config_saved.connect(self._poblar_arbol_archivos)

        self.right_stack.addWidget(self.open_tabs_widget)
        h_split.addWidget(self.right_stack)
        h_split.setStretchFactor(0, 1)
        h_split.setStretchFactor(1, 4)
        v_split.addWidget(h_split)

        # Panel inferior: Consola Output / Traceback
        out_frame = QFrame()
        out_frame.setObjectName("Panel")
        out_lay = QVBoxLayout(out_frame)
        out_lay.setContentsMargins(6, 4, 6, 4)
        out_lay.setSpacing(2)
        out_hdr = QHBoxLayout()
        lbl_out = QLabel("📟 Output / Errores de Hot-Reload & Pip")
        lbl_out.setObjectName("Section")
        out_hdr.addWidget(lbl_out)
        out_hdr.addStretch(1)
        btn_clr = QPushButton("Limpiar")
        btn_clr.clicked.connect(lambda: self.txt_output.clear())
        out_hdr.addWidget(btn_clr)
        out_lay.addLayout(out_hdr)

        self.txt_output = QPlainTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setMaximumHeight(95)
        out_lay.addWidget(self.txt_output)
        v_split.addWidget(out_frame)
        v_split.setStretchFactor(0, 5)
        v_split.setStretchFactor(1, 1)
        root.addWidget(v_split, 1)

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

        lbl_s = QLabel("No hay ningún módulo abierto.\nCrea uno con plantilla o selecciona uno existente.")
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

    def _append_output(self, text: str, is_error: bool = False):
        prefix = "❌ " if is_error else ""
        self.txt_output.appendPlainText(f"{prefix}{text}")
        self.lbl_estado.setText(text.splitlines()[0][:120])

    # ── Persistencia y Navegación de Módulos ──────────────────────────────

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
        for b in [self.btn_config, self.btn_guardar, self.btn_recargar, self.btn_compilar, *self.tree_action_btns]:
            b.setEnabled(habilitado)

    def _confirmar_cambios_pendientes(self) -> bool:
        """Pregunta si desea guardar antes de cambiar/cerrar cuando hay archivos con `*`."""
        sucios = [t for t in self._open_tabs.values() if t.dirty]
        if not sucios:
            return True
        nombres = ", ".join(t.file_path.name for t in sucios)
        resp = QMessageBox.question(
            self,
            "Cambios sin guardar",
            f"Hay cambios sin guardar en: {nombres}.\n¿Deseas guardarlos antes de continuar?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
        )
        if resp == QMessageBox.StandardButton.Cancel:
            return False
        if resp == QMessageBox.StandardButton.Save:
            for t in sucios:
                t.save_to_disk()
        return True

    def closeEvent(self, event):
        if not self._confirmar_cambios_pendientes():
            event.ignore()
            return
        super().closeEvent(event)

    def _mostrar_salvapantallas(self):
        if not self._confirmar_cambios_pendientes():
            return
        self._cerrar_todas_las_pestanas()
        self.modulo_actual = None
        self._bloqueando_signals = True
        self.cmb_modulos.setCurrentIndex(0)
        self._bloqueando_signals = False
        self.tree_archivos.clear()
        self.right_stack.setCurrentIndex(0)
        self._set_acciones_habilitadas(False)
        self._guardar_ultimo_modulo_config(None)
        self.lbl_estado.setText("Sin módulo activo.")

    def _on_combo_modulo_cambiado(self, texto: str):
        if self._bloqueando_signals:
            return
        if not texto or texto.startswith("—"):
            self._mostrar_salvapantallas()
        elif texto != self.modulo_actual:
            if not self._confirmar_cambios_pendientes():
                self._bloqueando_signals = True
                self.cmb_modulos.setCurrentText(self.modulo_actual or "— Ninguno (Inicio) —")
                self._bloqueando_signals = False
                return
            self._abrir_modulo(texto)

    def _abrir_modulo(self, nombre_mod: str):
        if not nombre_mod or not (self.modulos_dir / nombre_mod).exists():
            self._mostrar_salvapantallas()
            return
        self._cerrar_todas_las_pestanas()
        self.modulo_actual = nombre_mod
        self._bloqueando_signals = True
        self.cmb_modulos.setCurrentText(nombre_mod)
        self._bloqueando_signals = False
        self.right_stack.setCurrentIndex(1)
        self._set_acciones_habilitadas(True)
        self._poblar_arbol_archivos()
        self.config_panel.load_module(self.modulos_dir / nombre_mod)
        self._guardar_ultimo_modulo_config(nombre_mod)
        self._abrir_archivo_principal_modulo()
        self.lbl_estado.setText(f"Editando: vistas/modulos/{nombre_mod}")

    # ── Pestañas Independientes por Archivo ───────────────────────────────

    def _es_archivo_visual(self, ruta: Path) -> bool:
        if not self.modulo_actual or ruta.suffix != ".py":
            return False
        mod_dir = self.modulos_dir / self.modulo_actual
        if "utils" in ruta.relative_to(mod_dir).parts:
            return False
        cfg_path = mod_dir / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                rel = ruta.relative_to(mod_dir).as_posix()
                for s in cfg.get("submodulos") or []:
                    if s.get("file_name") == rel:
                        return True
            except Exception:
                pass
        items, _ = parse_pyqt_to_design(ruta.read_text(encoding="utf-8", errors="ignore"))
        return len(items) > 0

    def _abrir_archivo_principal_modulo(self):
        if not self.modulo_actual:
            return
        mod_dir = self.modulos_dir / self.modulo_actual
        cfg_path = mod_dir / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                subs = cfg.get("submodulos") or []
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

    def _abrir_archivo_en_editor(self, ruta: Path, force_visual: bool | None = None):
        if not self.modulo_actual or not ruta.exists() or not ruta.is_file():
            return
        key = str(ruta.resolve())
        if key in self._open_tabs:
            self.open_tabs_widget.setCurrentWidget(self._open_tabs[key])
            return
        is_vis = self._es_archivo_visual(ruta) if force_visual is None else force_visual
        tab = FileEditorTab(ruta, self.modulos_dir / self.modulo_actual, is_vis, self)
        tab.dirtyChanged.connect(self._on_tab_dirty_changed)
        tab.statusMessage.connect(self.lbl_estado.setText)
        self._open_tabs[key] = tab
        idx = self.open_tabs_widget.addTab(tab, f"{'🎨' if is_vis else '💻'} {ruta.name}")
        self.open_tabs_widget.setCurrentIndex(idx)

    def _abrir_pestana_config(self):
        if not self.modulo_actual:
            return
        self.config_panel.load_module(self.modulos_dir / self.modulo_actual)
        idx = self.open_tabs_widget.indexOf(self.config_panel)
        if idx < 0:
            idx = self.open_tabs_widget.addTab(self.config_panel, "⚙️ Config & Reqs")
        self.open_tabs_widget.setCurrentIndex(idx)

    def _on_tab_dirty_changed(self, tab: FileEditorTab, dirty: bool):
        idx = self.open_tabs_widget.indexOf(tab)
        if idx >= 0:
            ico = "🎨" if tab.is_visual else "💻"
            self.open_tabs_widget.setTabText(idx, f"{ico} {tab.file_path.name}{'*' if dirty else ''}")

    def _on_cerrar_pestana_idx(self, idx: int):
        w = self.open_tabs_widget.widget(idx)
        if isinstance(w, FileEditorTab) and w.dirty:
            resp = QMessageBox.question(
                self, "Guardar", f"¿Guardar cambios en '{w.file_path.name}' antes de cerrar?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            if resp == QMessageBox.StandardButton.Cancel:
                return
            if resp == QMessageBox.StandardButton.Save:
                w.save_to_disk()
        self.open_tabs_widget.removeTab(idx)
        if isinstance(w, FileEditorTab):
            self._open_tabs.pop(str(w.file_path.resolve()), None)
            w.deleteLater()

    def _cerrar_todas_las_pestanas(self):
        while self.open_tabs_widget.count() > 0:
            w = self.open_tabs_widget.widget(0)
            self.open_tabs_widget.removeTab(0)
            if isinstance(w, FileEditorTab):
                w.deleteLater()
        self._open_tabs.clear()

    def _actualizar_ruta_pestana_abierta(self, vieja: Path, nueva: Path):
        k_old = str(vieja.resolve())
        tab = self._open_tabs.pop(k_old, None)
        if tab:
            tab.file_path = nueva
            self._open_tabs[str(nueva.resolve())] = tab
            self._on_tab_dirty_changed(tab, tab.dirty)

    def _cerrar_pestana_por_ruta(self, ruta: Path):
        k = str(ruta.resolve())
        tab = self._open_tabs.pop(k, None)
        if tab:
            idx = self.open_tabs_widget.indexOf(tab)
            if idx >= 0:
                self.open_tabs_widget.removeTab(idx)
            tab.deleteLater()

    def _guardar_pestana_actual(self):
        w = self.open_tabs_widget.currentWidget()
        if isinstance(w, FileEditorTab):
            w.save_to_disk()
        elif w is self.config_panel:
            self.config_panel.save_all()

    def _guardar_todo(self):
        for tab in self._open_tabs.values():
            if tab.dirty:
                tab.save_to_disk()
        if self.modulo_actual:
            self.config_panel.save_all()

    # ── Creación de Nuevo Módulo con Plantillas ───────────────────────────

    def _crear_nuevo_modulo_dialog(self):
        dlg = NewModuleTemplateDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.ent_nombre.text().strip():
            return
        nombre = dlg.ent_nombre.text().strip()
        icono = dlg.ent_icono.text().strip() or "🧩"
        tpl_key = dlg.cmb_tpl.currentData() or "basico"
        tpl = MODULE_TEMPLATES[tpl_key]

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
            f'"""Backend del módulo {nombre}."""\n\n\n'
            f"class {a_pascal_case(mod_id)}Backend:\n"
            "    def procesar(self, texto: str) -> str:\n"
            '        return f"Procesado: {texto}" if texto else "Listo."\n',
            encoding="utf-8",
        )
        (mod_dir / f"{mod_id}.py").write_text(
            "# -*- coding: utf-8 -*-\n"
            f'"""Archivo raíz del módulo {nombre}."""\n\n'
            f"from .submodulos.tab_{mod_id} import {clase_tab}\n"
            f"from .utils.backend import {a_pascal_case(mod_id)}Backend\n\n\n"
            f"class {clase_root}({clase_tab}):\n"
            "    pass\n",
            encoding="utf-8",
        )
        config_data = {
            "name": nombre, "icon": icono, "version": "1.0.0", "position": 25, "visible": True,
            "submodulos": [{
                "name": "Principal", "file_name": f"submodulos/tab_{mod_id}.py",
                "class_name": clase_tab, "visible": True, "icon": icono, "alias": mod_id, "position": 1,
            }],
        }
        (mod_dir / "config.json").write_text(json.dumps(config_data, indent=4, ensure_ascii=False), encoding="utf-8")
        (mod_dir / "commands.json").write_text("{}", encoding="utf-8")
        (mod_dir / "requirements.txt").write_text("# Dependencias pip\n", encoding="utf-8")

        items = []
        for it in tpl["items"]:
            cp = dict(it)
            cp["texto"] = cp["texto"].replace("{titulo}", nombre)
            items.append(cp)
        (sub_dir / f"tab_{mod_id}.py").write_text(
            generate_pyqt_from_design(items, clase_tab, nombre, tpl["layout"]), encoding="utf-8"
        )

        self._cargar_lista_modulos(seleccionar=mod_id)
        self._append_output(f"✅ Módulo '{mod_id}' creado con plantilla '{tpl['label']}'.")

    # ── Hot-Reload con Captura de Traceback & Compilador ──────────────────

    def _recargar_en_app(self):
        self._guardar_todo()
        app = self.app_ref or self.parent()
        if not app:
            return
        if self.modulo_actual:
            # Validar sintaxis de todos los .py del módulo antes de recargar
            for py in (self.modulos_dir / self.modulo_actual).rglob("*.py"):
                try:
                    compile(py.read_text(encoding="utf-8"), str(py), "exec")
                except SyntaxError as se:
                    self._append_output(f"Error de sintaxis en {py.name} línea {se.lineno}: {se.msg}", True)
                    return

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
                    self._append_output(f"🔥 Hot-Reload aplicado en '{self.modulo_actual}'.")
                    return
            if hasattr(app, "cargar_modulos"):
                app.cargar_modulos()
                self._append_output(f"🔄 Módulo '{self.modulo_actual}' recargado en Multitool.")
        except Exception:
            self._append_output(traceback.format_exc(), True)

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
