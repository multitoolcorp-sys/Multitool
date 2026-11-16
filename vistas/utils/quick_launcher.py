# -*- coding: utf-8 -*-
"""
Mini Launcher Rápido Flotante (Ctrl+Shift+Space / System Tray).
Permite saltar a cualquier módulo, ejecutar comandos del EventBus o cambiar de Workspace
al instante sin navegar por menús.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from controlador.utils.event_bus import get_event_bus
from controlador.utils.paths import get_resource_path


class QuickLauncherDialog(QDialog):
    """Spotlight flotante para módulos, comandos del EventBus y workspaces."""

    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.setWindowTitle("🚀 Launcher Rápido — Multitool")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(520, 360)
        self.setStyleSheet("""
            QDialog {
                background-color: #131520;
                border: 2px solid #6366f1;
                border-radius: 10px;
                color: #f8fafc;
            }
            QLabel { color: #94a3b8; font-size: 11px; }
            QLineEdit {
                background-color: #0f111a;
                color: #ffffff;
                border: 1px solid #38405e;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 13px;
            }
            QListWidget {
                background-color: #0f111a;
                color: #f8fafc;
                border: 1px solid #2a2f45;
                border-radius: 6px;
                font-size: 12px;
            }
            QListWidget::item { padding: 7px 10px; }
            QListWidget::item:selected { background-color: #4f46e5; color: #ffffff; }
        """)
        self._items_data: list[dict] = []
        self._build_ui()
        self._collect_items()
        self._filter_items("")

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        self.ent_search = QLineEdit()
        self.ent_search.setPlaceholderText("🚀 Ir a módulo, ejecutar comando o cambiar workspace...")
        self.ent_search.textChanged.connect(self._filter_items)
        self.ent_search.returnPressed.connect(self._execute_selected)
        lay.addWidget(self.ent_search)

        self.lista = QListWidget()
        self.lista.itemDoubleClicked.connect(self._execute_selected)
        lay.addWidget(self.lista, 1)

        lay.addWidget(QLabel("Enter: ejecutar  |  Esc: cerrar  |  Atajo: Ctrl+Shift+Space"))

    def _collect_items(self):
        self._items_data.clear()
        for idx, mod in enumerate(getattr(self.app_ref, "modulos_cargados", [])):
            self._items_data.append({
                "kind": "module",
                "label": f"🧩 Módulo: {mod.get('name', '').capitalize()}",
                "search": mod.get("name", "").lower(),
                "target": mod.get("name", ""),
                "index": idx,
            })

        bus = get_event_bus()
        for act in bus.list_actions():
            self._items_data.append({
                "kind": "action",
                "label": f"⚡ Acción: {act['id']} — {act['description']}",
                "search": f"{act['id']} {act['description']}".lower(),
                "target": act["id"],
            })

        modulos_dir = get_resource_path() / "vistas" / "modulos"
        for cmd in bus.discover_module_commands(modulos_dir):
            self._items_data.append({
                "kind": "command",
                "label": f"⌘ Comando: {cmd['id']} — {cmd['description']}",
                "search": f"{cmd['id']} {cmd['description']}".lower(),
                "target": cmd["module"],
            })

    def _filter_items(self, query: str):
        q = query.strip().lower()
        self.lista.clear()
        for item in self._items_data:
            if not q or q in item["search"]:
                it = QListWidgetItem(item["label"])
                it.setData(Qt.ItemDataRole.UserRole, item)
                self.lista.addItem(it)
        if self.lista.count() > 0:
            self.lista.setCurrentRow(0)

    def _execute_selected(self):
        it = self.lista.currentItem()
        if not it:
            return
        data = it.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind = data["kind"]
        if kind in {"module", "command"} and hasattr(self.app_ref, "notebook"):
            visibles = [m for m in getattr(self.app_ref, "modulos_cargados", []) if m.get("visible", True)]
            for idx, m in enumerate(visibles):
                if m.get("name", "").lower() == data["target"].lower() or m.get("folder", "").lower() == data["target"].lower():
                    self.app_ref.notebook.setCurrentIndex(idx)
                    break
        elif kind == "action":
            get_event_bus().execute_action(data["target"])
        self.accept()
