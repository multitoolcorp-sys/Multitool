"""
tab_session_manager.py - Gestor de persistencia de sesión, historial de pestañas y reposo
Permite guardar y restaurar el estado de cada pestaña individual incluyendo su pila de navegación (Back/Forward).
"""
import json
import time
from pathlib import Path
from PyQt6.QtCore import QUrl


class TabSessionManager:
    """Gestiona la persistencia de pestañas, historial propio por pestaña y suspensión de RAM."""
    def __init__(self, browser):
        self.b = browser

    def guardar_estado_pestanas(self):
        try:
            tabs_data = []
            for i in range(self.b.tabs.count()):
                container = self.b.tabs.widget(i)
                if container:
                    u = container.saved_url if getattr(container, "is_sleeping", False) else (container.url().toString() if hasattr(container, "url") else "")
                    if u and not u.startswith("about:"):
                        is_pinned = getattr(container, "is_pinned", False)
                        title = getattr(container, "full_title", container.title()).replace("💤 ", "").strip()
                        zoom = getattr(container, "zoom_level", self.b.zoom_level)
                        nav_stack = getattr(container, "nav_history_stack", [u])
                        nav_index = getattr(container, "nav_history_index", len(nav_stack) - 1)

                        tabs_data.append({
                            "url": u,
                            "pinned": is_pinned,
                            "title": title,
                            "zoom": float(zoom),
                            "nav_stack": nav_stack,
                            "nav_index": nav_index
                        })

            with open(self.b.state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "tabs": tabs_data,
                    "active_index": self.b.tabs.currentIndex(),
                    "default_zoom": self.b.zoom_level
                }, f, indent=2)
        except Exception as e:
            print(f"[TabSessionManager] Error guardando estado de pestañas: {e}")

    def restaurar_estado_pestanas(self):
        try:
            if self.b.state_file.exists():
                with open(self.b.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                tabs_data = data.get("tabs", [])
                if tabs_data:
                    self.b.zoom_level = float(data.get("default_zoom", 1.0))
                    if hasattr(self.b, "toolbar"):
                        self.b.toolbar.actualizar_badge_zoom(self.b.zoom_level)

                    active_idx = min(len(tabs_data) - 1, max(0, data.get("active_index", 0)))
                    self.b.tabs.blockSignals(True)
                    try:
                        for idx_tab, t in enumerate(tabs_data):
                            u = t.get("url")
                            is_pin = t.get("pinned", False)
                            title = t.get("title", "Cargando...")
                            tab_zoom = float(t.get("zoom", self.b.zoom_level))
                            nav_stack = t.get("nav_stack", [u] if u else [])
                            nav_index = t.get("nav_index", len(nav_stack) - 1 if nav_stack else 0)

                            if u:
                                # Las pestañas en segundo plano se restauran en reposo para acelerar el inicio
                                should_sleep = (idx_tab != active_idx)
                                self.b.add_new_tab(
                                    QUrl(u), title,
                                    is_pinned=is_pin,
                                    zoom=tab_zoom,
                                    start_sleeping=should_sleep,
                                    nav_history=nav_stack,
                                    nav_index=nav_index
                                )
                    finally:
                        self.b.tabs.blockSignals(False)

                    if 0 <= active_idx < self.b.tabs.count():
                        self.b.tabs.setCurrentIndex(active_idx)
                    self.b.current_tab_changed(self.b.tabs.currentIndex())
                    self.b.pestanas_restauradas = True
                    return
        except Exception as e:
            print(f"[TabSessionManager] Error restaurando estado de pestañas: {e}")

        self.b.add_new_tab(QUrl("https://www.google.com"), "Google")
        self.b.pestanas_restauradas = True

    def verificar_pestanas_para_reposo(self):
        """Comprueba periódicamente las pestañas inactivas y las suspende si superan el tiempo configurado."""
        if not self.b.sleep_enabled:
            return

        ahora = time.time()
        timeout_sec = self.b.sleep_timeout_minutes * 60
        curr_idx = self.b.tabs.currentIndex()

        for i in range(self.b.tabs.count()):
            if i == curr_idx:
                container = self.b.tabs.widget(i)
                if container:
                    container.last_active_time = ahora
                continue

            container = self.b.tabs.widget(i)
            if not container or getattr(container, "is_sleeping", False):
                continue

            if getattr(container, "is_pip_active", False):
                container.last_active_time = ahora
                continue

            inactividad = ahora - getattr(container, "last_active_time", ahora)
            if inactividad >= timeout_sec:
                self.b.dormir_pestana(i)

    def guardar_config_reposo(self):
        try:
            with open(self.b.sleep_config_file, "w", encoding="utf-8") as f:
                json.dump({
                    "sleep_enabled": self.b.sleep_enabled,
                    "sleep_timeout_minutes": self.b.sleep_timeout_minutes
                }, f, indent=2)
        except Exception:
            pass

    def cargar_config_reposo(self):
        try:
            if self.b.sleep_config_file.exists():
                with open(self.b.sleep_config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.b.sleep_enabled = cfg.get("sleep_enabled", True)
                    self.b.sleep_timeout_minutes = cfg.get("sleep_timeout_minutes", 15)
        except Exception:
            pass
