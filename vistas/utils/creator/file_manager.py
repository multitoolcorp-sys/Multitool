# -*- coding: utf-8 -*-
"""Mixin de gestor completo de archivos y carpetas para el Modo Creador."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialog, QInputDialog, QMenu, QMessageBox, QTreeWidgetItem

from vistas.utils.creator.dialogs import NewFileTypeDialog, generar_codigo_pyqt
from vistas.utils.creator.helpers import a_pascal_case, normalizar_id_modulo


class CreatorFileManagerMixin:
    """Agrupa las operaciones de árbol, creación, renombrado, movimiento y borrado de archivos."""

    def _poblar_arbol_archivos(self):
        self.tree_archivos.clear()
        if not self.modulo_actual:
            return
        mod_dir = self.modulos_dir / self.modulo_actual
        if not mod_dir.exists():
            return

        root_item = QTreeWidgetItem([f"📁 {self.modulo_actual}"])
        root_item.setData(0, Qt.ItemDataRole.UserRole, str(mod_dir))
        self.tree_archivos.addTopLevelItem(root_item)

        def _add_dir(parent_item: QTreeWidgetItem, current_dir: Path):
            entries = sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for entry in entries:
                if entry.name in {"__pycache__", ".git"} or entry.suffix in {".pyc", ".old"}:
                    continue
                if entry.is_dir():
                    dir_it = QTreeWidgetItem([f"📂 {entry.name}"])
                    dir_it.setData(0, Qt.ItemDataRole.UserRole, str(entry))
                    parent_item.addChild(dir_it)
                    _add_dir(dir_it, entry)
                else:
                    icon = "⚙️" if entry.name == "config.json" else ("📋" if entry.name == "requirements.txt" else "🐍")
                    file_it = QTreeWidgetItem([f"{icon} {entry.name}"])
                    file_it.setData(0, Qt.ItemDataRole.UserRole, str(entry))
                    parent_item.addChild(file_it)

        _add_dir(root_item, mod_dir)
        self.tree_archivos.expandAll()

    def _abrir_item_arbol(self, item: QTreeWidgetItem, _col: int = 0):
        ruta_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not ruta_str:
            return
        ruta = Path(ruta_str)
        if ruta.is_file():
            self._abrir_archivo_en_editor(ruta)

    def _obtener_ruta_item_seleccionado(self) -> Path | None:
        item = self.tree_archivos.currentItem()
        if not item:
            return (self.modulos_dir / self.modulo_actual) if self.modulo_actual else None
        ruta_str = item.data(0, Qt.ItemDataRole.UserRole)
        return Path(ruta_str) if ruta_str else None

    def _obtener_directorio_destino_actual(self) -> Path | None:
        if not self.modulo_actual:
            return None
        ruta = self._obtener_ruta_item_seleccionado()
        if ruta is None:
            return self.modulos_dir / self.modulo_actual
        return ruta if ruta.is_dir() else ruta.parent

    def _menu_contextual_arbol(self, pos):
        if not self.modulo_actual:
            return
        menu = QMenu(self)
        for label, fn in [
            ("📄 Nuevo archivo (Visual / Funcionalidad)...", self._crear_archivo_en_modulo),
            ("📁 Nueva carpeta...", self._crear_carpeta_en_modulo),
            ("✏️ Renombrar...", self._renombrar_item_arbol),
            ("📦 Mover a otra carpeta...", self._mover_item_arbol),
            ("🗑️ Eliminar", self._eliminar_item_arbol),
            ("📂 Abrir en Explorador", self._abrir_en_explorador),
        ]:
            act = QAction(label, self)
            act.triggered.connect(fn)
            menu.addAction(act)
        menu.exec(self.tree_archivos.viewport().mapToGlobal(pos))

    def _crear_archivo_en_modulo(self):
        if not self.modulo_actual:
            return
        mod_dir = self.modulos_dir / self.modulo_actual
        base_dir = self._obtener_directorio_destino_actual() or mod_dir
        dlg = NewFileTypeDialog(base_dir.name, self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.ent_nombre.text().strip():
            return

        nombre = dlg.ent_nombre.text().strip().lstrip("/\\")
        if dlg.rb_visual.isChecked():
            if not nombre.endswith(".py"):
                nombre += ".py"
            destino = (mod_dir / "submodulos" / nombre) if base_dir == mod_dir else (base_dir / nombre)
        else:
            if "." not in Path(nombre).name:
                nombre += ".py"
            destino = (mod_dir / "utils" / nombre) if base_dir == mod_dir else (base_dir / nombre)

        if destino.exists():
            QMessageBox.warning(self, "Ya existe", f"'{destino.name}' ya existe.")
            return
        destino.parent.mkdir(parents=True, exist_ok=True)

        if dlg.rb_visual.isChecked():
            clase = a_pascal_case(destino.stem)
            destino.write_text(
                generar_codigo_pyqt(self.design_items, clase, dlg.ent_sub_name.text().strip()),
                encoding="utf-8",
            )
            cfg_path = mod_dir / "config.json"
            if cfg_path.exists():
                try:
                    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                    subs = cfg.setdefault("submodulos", [])
                    rel_fn = destino.relative_to(mod_dir).as_posix()
                    subs.append({
                        "name": dlg.ent_sub_name.text().strip() or destino.stem,
                        "file_name": rel_fn,
                        "class_name": clase,
                        "visible": True,
                        "icon": dlg.ent_sub_icon.text().strip() or "🧩",
                        "alias": normalizar_id_modulo(destino.stem),
                        "position": len(subs) + 1,
                    })
                    cfg_path.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")
                    self._cargar_meta_modulo()
                except Exception:
                    pass
            self._poblar_arbol_archivos()
            self._abrir_archivo_en_editor(destino)
            self.tabs_editor.setCurrentIndex(0)
        else:
            destino.write_text(
                "# -*- coding: utf-8 -*-\n"
                f'"""Módulo de funcionalidad: {destino.stem}."""\n\n\n'
                f"def ejecutar(context=None, **kwargs):\n"
                '    app = getattr(context, "app", None) if context else None\n'
                '    if app and hasattr(app, "mostrar_notificacion"):\n'
                '        app.mostrar_notificacion("Módulo", "Función ejecutada", tipo="info")\n'
                "    return True\n",
                encoding="utf-8",
            )
            self._poblar_arbol_archivos()
            self._abrir_archivo_en_editor(destino)
            self.tabs_editor.setCurrentIndex(1)

    def _crear_carpeta_en_modulo(self):
        base_dir = self._obtener_directorio_destino_actual()
        if not base_dir:
            return
        nombre, ok = QInputDialog.getText(self, "Nueva Carpeta", f"Nombre dentro de {base_dir.name}/:")
        if not ok or not nombre.strip():
            return
        nueva = base_dir / nombre.strip().strip("/\\")
        if nueva.exists():
            QMessageBox.warning(self, "Ya existe", f"'{nueva.name}' ya existe.")
            return
        nueva.mkdir(parents=True, exist_ok=True)
        self._poblar_arbol_archivos()

    def _renombrar_item_arbol(self):
        ruta = self._obtener_ruta_item_seleccionado()
        mod_root = self.modulos_dir / self.modulo_actual if self.modulo_actual else None
        if not ruta or not mod_root or ruta == mod_root:
            return
        nuevo, ok = QInputDialog.getText(self, "Renombrar", "Nuevo nombre:", text=ruta.name)
        if not ok or not nuevo.strip() or nuevo.strip() == ruta.name:
            return
        destino = ruta.parent / nuevo.strip()
        if destino.exists():
            QMessageBox.warning(self, "Error", f"Ya existe '{destino.name}'.")
            return
        ruta.rename(destino)
        if self.archivo_actual == ruta:
            self.archivo_actual = destino
        self._poblar_arbol_archivos()

    def _mover_item_arbol(self):
        ruta = self._obtener_ruta_item_seleccionado()
        mod_root = self.modulos_dir / self.modulo_actual if self.modulo_actual else None
        if not ruta or not mod_root or ruta == mod_root:
            return
        carpetas = [mod_root] + [
            p for p in sorted(mod_root.rglob("*"))
            if p.is_dir() and p.name not in {"__pycache__", ".git"} and p != ruta and ruta not in p.parents
        ]
        opciones = [("." if c == mod_root else c.relative_to(mod_root).as_posix()) for c in carpetas]
        elegida, ok = QInputDialog.getItem(self, "Mover", f"Mover '{ruta.name}' a:", opciones, 0, False)
        if not ok or not elegida:
            return
        dest_dir = mod_root if elegida == "." else (mod_root / elegida)
        destino = dest_dir / ruta.name
        if destino.exists():
            QMessageBox.warning(self, "Conflicto", f"Ya existe '{ruta.name}' en '{elegida}'.")
            return
        shutil.move(str(ruta), str(destino))
        if self.archivo_actual == ruta:
            self.archivo_actual = destino
        self._poblar_arbol_archivos()

    def _eliminar_item_arbol(self):
        ruta = self._obtener_ruta_item_seleccionado()
        mod_root = self.modulos_dir / self.modulo_actual if self.modulo_actual else None
        if not ruta or not mod_root or ruta == mod_root:
            return
        resp = QMessageBox.question(self, "Confirmar", f"¿Eliminar '{ruta.name}'?")
        if resp != QMessageBox.StandardButton.Yes:
            return
        if ruta.is_dir():
            shutil.rmtree(ruta)
        else:
            ruta.unlink(missing_ok=True)
        if self.archivo_actual == ruta:
            self.archivo_actual = None
            self.code_editor.clear()
        self._poblar_arbol_archivos()

    def _abrir_en_explorador(self):
        if not self.modulo_actual:
            return
        mod_root = self.modulos_dir / self.modulo_actual
        if sys.platform.startswith("win"):
            os.startfile(str(mod_root))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(mod_root)])
        else:
            subprocess.Popen(["xdg-open", str(mod_root)])
