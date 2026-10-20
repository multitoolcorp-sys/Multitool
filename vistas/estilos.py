import json
from pathlib import Path
from controlador.utils.paths import get_resource_path

def obtener_todos_los_temas():
    """
    Retorna el diccionario de todos los temas registrados en temas.json.
    """
    base_dir = get_resource_path()
    temas_file = base_dir / "vistas" / "utils" / "temas.json"
    if temas_file.exists():
        try:
            with open(temas_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ThemeEngine] Error leyendo temas.json: {e}")
    return {}

def obtener_colores_tema(tema_nombre, config_usuario=None):
    """
    Retorna los valores cromáticos del tema solicitado. 
    Si el tema es 'personalizado' y existe 'colores_personalizados' en config_usuario, los fusiona con los valores por defecto.
    """
    temas = obtener_todos_los_temas()
    default_base = temas.get("azul_oscuro", {
        "nombre": "Azul Espacial",
        "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
        "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
        "acento_hover": "#818CF8", "error": "#F87171", "exito": "#34D399", "advertencia": "#FBBF24"
    })

    if tema_nombre == "personalizado" and config_usuario and isinstance(config_usuario, dict):
        base = dict(default_base)
        custom_colors = config_usuario.get("colores_personalizados", {})
        base.update(custom_colors)
        base["nombre"] = "Personalizado"
        return base

    if tema_nombre in temas:
        return temas[tema_nombre]

    return default_base
