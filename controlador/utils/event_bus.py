# -*- coding: utf-8 -*-
"""
Bus de Eventos y Acciones Cruzadas entre Módulos (EventBus).
Permite que cualquier módulo publique eventos, se suscriba a eventos de otros
módulos y descubra/ejecute acciones declaradas en `commands.json`.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Callable


class MultitoolEventBus:
    """Bus central ligero (Publish/Subscribe + Registro de Acciones)."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._actions: dict[str, dict] = {}

    def subscribe(self, event_name: str, callback: Callable):
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable):
        if callback in self._subscribers.get(event_name, []):
            self._subscribers[event_name].remove(callback)

    def publish(self, event_name: str, payload: dict | None = None):
        data = payload or {}
        for cb in list(self._subscribers.get(event_name, [])):
            try:
                cb(data)
            except Exception as exc:
                print(f"[EventBus] Error en listener de '{event_name}': {exc}")

    def register_action(self, action_id: str, handler: Callable, description: str = "", module_id: str = ""):
        self._actions[action_id] = {
            "id": action_id,
            "handler": handler,
            "description": description,
            "module": module_id,
        }

    def execute_action(self, action_id: str, **kwargs):
        info = self._actions.get(action_id)
        if not info:
            return False, f"Acción '{action_id}' no encontrada."
        try:
            res = info["handler"](**kwargs)
            self.publish("action_executed", {"action_id": action_id, "result": res})
            return True, res
        except Exception as exc:
            return False, str(exc)

    def list_actions(self) -> list[dict]:
        return [
            {"id": k, "description": v.get("description", ""), "module": v.get("module", "")}
            for k, v in sorted(self._actions.items())
        ]

    def discover_module_commands(self, modulos_dir: Path) -> list[dict]:
        """Lee todos los `commands.json` en `vistas/modulos/*/commands.json`."""
        discovered = []
        if not modulos_dir.exists():
            return discovered
        for mod in sorted(modulos_dir.iterdir(), key=lambda p: p.name.lower()):
            if not mod.is_dir():
                continue
            cmd_file = mod / "commands.json"
            if not cmd_file.exists():
                continue
            try:
                data = json.loads(cmd_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data, dict):
                for cmd_key, meta in data.items():
                    desc = meta.get("description", "") if isinstance(meta, dict) else str(meta)
                    discovered.append({
                        "id": f"{mod.name}.{cmd_key}",
                        "module": mod.name,
                        "command": cmd_key,
                        "description": desc,
                    })
        return discovered


_GLOBAL_BUS = MultitoolEventBus()


def get_event_bus() -> MultitoolEventBus:
    return _GLOBAL_BUS
