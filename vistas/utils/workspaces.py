# -*- coding: utf-8 -*-
"""
Gestor de Perfiles / Espacios de Trabajo (Workspaces).
Permite filtrar dinámicamente qué módulos son visibles según el flujo de trabajo
(Programador, Productividad, Mantenimiento, Multimedia o Todos) sin reiniciar.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

DEFAULT_WORKSPACES = {
    "Todos": [],  # lista vacía = mostrar todos los módulos
    "Programador": ["general", "terminal", "proyectos", "basedatos", "navegador", "clipboard", "archivos", "automatizacion"],
    "Productividad": ["general", "notas", "calendario", "tiempo", "cuaderno", "traductor", "clipboard"],
    "Mantenimiento PC": ["general", "sistema", "seguridad", "archivos", "automatizacion", "terminal"],
    "Multimedia": ["general", "reproductor", "grabadora", "minigames", "widgets"],
}


def aplicar_workspace_a_app(app, workspace_name: str):
    """Aplica el filtro del workspace sobre `app.modulos_cargados` y refresca la barra/sidebar."""
    if not app or not hasattr(app, "modulos_cargados"):
        return
    custom = {}
    if hasattr(app, "config") and isinstance(app.config, dict):
        custom = app.config.get("workspaces", {})
    all_ws = {**DEFAULT_WORKSPACES, **custom}
    allowed = [m.lower() for m in all_ws.get(workspace_name, [])]

    for mod in app.modulos_cargados:
        m_name = mod.get("name", "").lower()
        m_folder = mod.get("folder", m_name).lower()
        if not allowed:
            mod["visible"] = True
        else:
            mod["visible"] = (m_name in allowed) or (m_folder in allowed) or (m_name == "general")

    if hasattr(app, "config") and isinstance(app.config, dict):
        app.config["active_workspace"] = workspace_name
        if hasattr(app, "guardar_configuracion"):
            try:
                app.guardar_configuracion()
            except Exception:
                pass

    if hasattr(app, "actualizar_menu_ver"):
        app.actualizar_menu_ver(app.modulos_cargados)
    if hasattr(app, "sidebar") and app.sidebar:
        app.sidebar.renderizar_arbol()


class WorkspaceManagerDialog(QDialog):
    """Interfaz para cambiar o crear Perfiles / Espacios de Trabajo."""

    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.setWindowTitle("🗂️ Espacios de Trabajo (Workspaces)")
        self.setMinimumSize(440, 420)
        self.setStyleSheet("""
            QDialog, QWidget { background-color: #131520; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QLabel, QCheckBox { color: #f8fafc; }
            QComboBox, QListWidget { background-color: #0f111a; color: #f8fafc; border: 1px solid #2e344d; border-radius: 6px; padding: 5px; }
            QPushButton { background-color: #252a3d; color: #f8fafc; border: 1px solid #38405e; border-radius: 6px; padding: 6px 12px; font-weight: 600; }
            QPushButton#Primary { background-color: #4f46e5; border-color: #6366f1; }
        """)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.addWidget(QLabel("Selecciona un perfil para mostrar solo los módulos que necesitas:"))

        row = QHBoxLayout()
        self.cmb_ws = QComboBox()
        self.cmb_ws.currentTextChanged.connect(self._on_ws_changed)
        row.addWidget(self.cmb_ws, 1)
        btn_new = QPushButton("➕ Nuevo Perfil")
        btn_new.clicked.connect(self._crear_perfil)
        row.addWidget(btn_new)
        lay.addLayout(row)

        self.list_mods = QListWidget()
        lay.addWidget(self.list_mods, 1)

        footer = QHBoxLayout()
        btn_apply = QPushButton("✅ Aplicar Workspace")
        btn_apply.setObjectName("Primary")
        btn_apply.clicked.connect(self._aplicar)
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)
        footer.addStretch(1)
        footer.addWidget(btn_apply)
        footer.addWidget(btn_close)
        lay.addLayout(footer)

    def _all_workspaces(self) -> dict[str, list[str]]:
        custom = self.app_ref.config.get("workspaces", {}) if hasattr(self.app_ref, "config") else {}
        return {**DEFAULT_WORKSPACES, **custom}

    def _load_data(self):
        self.cmb_ws.blockSignals(True)
        self.cmb_ws.clear()
        ws_dict = self._all_workspaces()
        self.cmb_ws.addItems(list(ws_dict.keys()))
        active = self.app_ref.config.get("active_workspace", "Todos") if hasattr(self.app_ref, "config") else "Todos"
        if self.cmb_ws.findText(active) >= 0:
            self.cmb_ws.setCurrentText(active)
        self.cmb_ws.blockSignals(False)
        self._on_ws_changed(self.cmb_ws.currentText())

    def _on_ws_changed(self, ws_name: str):
        self.list_mods.clear()
        allowed = [m.lower() for m in self._all_workspaces().get(ws_name, [])]
        for mod in getattr(self.app_ref, "modulos_cargados", []):
            name = mod.get("name", "")
            folder = mod.get("folder", name).lower()
            it = QListWidgetItem(f"🧩 {name}")
            it.setData(Qt.ItemDataRole.UserRole, folder)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            checked = True if not allowed else (name.lower() in allowed or folder in allowed)
            it.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.list_mods.addItem(it)

    def _crear_perfil(self):
        nombre, ok = QInputDialog.getText(self, "Nuevo Workspace", "Nombre del perfil:")
        if not ok or not nombre.strip():
            return
        nombre = nombre.strip()
        if hasattr(self.app_ref, "config"):
            ws = self.app_ref.config.setdefault("workspaces", {})
            ws[nombre] = ["general"]
            if hasattr(self.app_ref, "guardar_configuracion"):
                self.app_ref.guardar_configuracion()
        self._load_data()
        self.cmb_ws.setCurrentText(nombre)

    def _aplicar(self):
        ws_name = self.cmb_ws.currentText()
        if ws_name != "Todos" and hasattr(self.app_ref, "config"):
            selected = []
            for i in range(self.list_mods.count()):
                it = self.list_mods.item(i)
                if it.checkState() == Qt.CheckState.Checked:
                    selected.append(it.data(Qt.ItemDataRole.UserRole))
            ws = self.app_ref.config.setdefault("workspaces", {})
            ws[ws_name] = selected
        aplicar_workspace_a_app(self.app_ref, ws_name)
        self.accept()
