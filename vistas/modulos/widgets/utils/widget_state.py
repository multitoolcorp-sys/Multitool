"""
widget_state.py - Gestor de estado y configuración persistente del sistema de Quick Widgets
"""
import json
from pathlib import Path

DEFAULT_WIDGET_CONFIG = {
    "flotante_activo": True,
    "siempre_visible_top": True,  # Opción para mantener visible en 2º plano sobre otras ventanas de Windows
    "modo_acople": "borde",       # borde, libre
    "posicion_x": -1,
    "posicion_y": -1,
    "pinned_widgets": [],
    "widgets": {
        "calculadora": True,
        "archivos": True,
        "notas": True,
        "reproductor": True,
        "grabadora": True,
        "cuaderno": True,
        "chat": True,
        "extras": True,
        "minigames": True,
        "tiempo": True,
        "traductor": True
    }
}

class QuickWidgetState:
    """Gestiona la carga, modificación y guardado de la configuración de widgets"""
    def __init__(self, ruta_usuario=None):
        self.ruta_usuario = Path(ruta_usuario) if ruta_usuario else Path(".")
        self.config_file = self.ruta_usuario / "config_widgets.json"
        self.config = self.cargar_configuracion()

    def cargar_configuracion(self):
        config = dict(DEFAULT_WIDGET_CONFIG)
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        config.update(data)
            except Exception as e:
                print(f"[QuickWidgetState Error]: {e}")
        return config

    def guardar_configuracion(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"[QuickWidgetState Guardar Error]: {e}")
            return False

    def is_always_on_top(self) -> bool:
        return self.config.get("siempre_visible_top", True)

    def set_always_on_top(self, enabled: bool):
        self.config["siempre_visible_top"] = enabled
        self.guardar_configuracion()
