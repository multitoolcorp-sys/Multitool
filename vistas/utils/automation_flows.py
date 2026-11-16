# -*- coding: utf-8 -*-
"""
Motor de Flujos Automáticos entre Módulos (EventBus -> Acciones).
Permite crear reglas del tipo:
  Cuando ocurra `<evento>` -> Ejecutar `<accion>` o mostrar notificación en Multitool.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from controlador.utils.event_bus import get_event_bus


class FlowRuleEngine:
    """Conecta reglas guardadas en `app.config['event_flows']` al EventBus en vivo."""

    def __init__(self, app_ref):
        self.app_ref = app_ref
        self.bus = get_event_bus()
        self._active_listeners: list[tuple[str, callable]] = []

    def reload_rules(self):
        for ev, cb in self._active_listeners:
            self.bus.unsubscribe(ev, cb)
        self._active_listeners.clear()

        rules = []
        if self.app_ref and hasattr(self.app_ref, "config") and isinstance(self.app_ref.config, dict):
            rules = self.app_ref.config.get("event_flows", [])

        for r in rules:
            if not r.get("enabled", True):
                continue
            ev_name = r.get("event", "").strip()
            action_id = r.get("action", "").strip()
            msg = r.get("message", "").strip()
            if not ev_name:
                continue

            def _make_cb(act=action_id, note=msg, ev=ev_name):
                def _cb(payload):
                    if act == "notificacion":
                        if hasattr(self.app_ref, "mostrar_notificacion"):
                            self.app_ref.mostrar_notificacion(f"Flujo: {ev}", note or str(payload), tipo="info")
                    elif act:
                        self.bus.execute_action(act)
                return _cb

            cb = _make_cb()
            self.bus.subscribe(ev_name, cb)
            self._active_listeners.append((ev_name, cb))


class AutomationFlowsDialog(QDialog):
    """Interfaz para crear, probar y gestionar flujos entre módulos."""

    def __init__(self, app_ref, engine: FlowRuleEngine, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.engine = engine
        self.setWindowTitle("⚡ Flujos Automáticos entre Módulos")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("""
            QDialog, QWidget { background-color: #131520; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #f8fafc; }
            QLineEdit, QComboBox, QListWidget {
                background-color: #0f111a; color: #f8fafc; border: 1px solid #2e344d; border-radius: 5px; padding: 5px;
            }
            QPushButton { background-color: #252a3d; color: #f8fafc; border: 1px solid #38405e; border-radius: 6px; padding: 6px 12px; font-weight: 600; }
            QPushButton#Primary { background-color: #4f46e5; border-color: #6366f1; }
        """)
        self._build_ui()
        self._render_list()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.addWidget(QLabel("Conecta eventos de cualquier módulo con acciones automáticas:"))

        form = QFormLayout()
        self.ent_event = QLineEdit()
        self.ent_event.setPlaceholderText("Ej: pomodoro_finished, backup_done, cpu_alert")
        self.cmb_action = QComboBox()
        self.cmb_action.addItem("notificacion")
        for act in get_event_bus().list_actions():
            self.cmb_action.addItem(act["id"])
        self.ent_msg = QLineEdit()
        self.ent_msg.setPlaceholderText("Mensaje de notificación (opcional)")

        form.addRow("Cuando ocurra evento:", self.ent_event)
        form.addRow("Ejecutar acción:", self.cmb_action)
        form.addRow("Mensaje:", self.ent_msg)
        lay.addLayout(form)

        row_add = QHBoxLayout()
        btn_add = QPushButton("➕ Agregar Flujo")
        btn_add.setObjectName("Primary")
        btn_add.clicked.connect(self._add_rule)
        btn_test = QPushButton("▶ Probar Evento")
        btn_test.clicked.connect(self._test_rule)
        btn_del = QPushButton("🗑 Eliminar")
        btn_del.clicked.connect(self._del_rule)
        row_add.addWidget(btn_add)
        row_add.addWidget(btn_test)
        row_add.addWidget(btn_del)
        lay.addLayout(row_add)

        self.lista = QListWidget()
        lay.addWidget(self.lista, 1)

    def _get_rules(self) -> list[dict]:
        if hasattr(self.app_ref, "config") and isinstance(self.app_ref.config, dict):
            return self.app_ref.config.setdefault("event_flows", [])
        return []

    def _save_and_reload(self):
        if hasattr(self.app_ref, "guardar_configuracion"):
            self.app_ref.guardar_configuracion()
        self.engine.reload_rules()
        self._render_list()

    def _render_list(self):
        self.lista.clear()
        for r in self._get_rules():
            st = "✅" if r.get("enabled", True) else "⏸"
            self.lista.addItem(f"{st} Cuando [{r.get('event')}]  →  {r.get('action')} ({r.get('message', '')})")

    def _add_rule(self):
        ev = self.ent_event.text().strip()
        if not ev:
            return
        self._get_rules().append({
            "event": ev,
            "action": self.cmb_action.currentText(),
            "message": self.ent_msg.text().strip(),
            "enabled": True,
        })
        self.ent_event.clear()
        self._save_and_reload()

    def _test_rule(self):
        row = self.lista.currentRow()
        rules = self._get_rules()
        if 0 <= row < len(rules):
            get_event_bus().publish(rules[row]["event"], {"source": "manual_test"})

    def _del_rule(self):
        row = self.lista.currentRow()
        rules = self._get_rules()
        if 0 <= row < len(rules):
            rules.pop(row)
            self._save_and_reload()
