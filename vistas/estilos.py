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


def generar_qss_global(colores=None):
    """Genera la hoja de estilos QSS global para diálogos, tooltips y menús usando la paleta activa."""
    c = colores or {}
    bg_sec = c.get("bg_secundario", "#1E1E2E")
    bg_ter = c.get("bg_terciario", "#2D2D3D")
    fg_pri = c.get("fg_principal", "#E2E8F0")
    acento = c.get("acento", "#6366F1")
    acento_hover = c.get("acento_hover", "#4F46E5")

    return f"""
        QMessageBox {{
            background-color: {bg_sec};
            color: {fg_pri};
        }}
        QMessageBox QLabel {{
            color: {fg_pri};
            background-color: transparent;
            font-size: 9.5pt;
        }}
        QMessageBox QPushButton {{
            background-color: {acento};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 6px 16px;
            font-weight: bold;
            min-width: 75px;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {acento_hover};
        }}
        QToolTip {{
            background-color: {bg_ter};
            color: {fg_pri};
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 5px 8px;
            border-radius: 4px;
            font-size: 9pt;
        }}
        QMenu {{
            background-color: {bg_sec};
            color: {fg_pri};
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            padding: 6px;
        }}
        QMenu::item {{
            background-color: transparent;
            color: {fg_pri};
            padding: 8px 24px 8px 14px;
            border-radius: 6px;
            font-size: 9.5pt;
        }}
        QMenu::item:selected {{
            background-color: {acento};
            color: #FFFFFF !important;
            font-weight: bold;
        }}
        QMenu::item:disabled {{
            background-color: transparent;
            color: #64748B !important;
        }}
        QMenu::separator {{
            height: 1px;
            background-color: rgba(255, 255, 255, 0.08);
            margin: 4px 6px;
        }}
        QMenu::indicator {{
            width: 16px;
            height: 16px;
            margin-left: 6px;
        }}
        QMenu::indicator:checked {{
            background-color: {acento};
            border: 1px solid {acento_hover};
            border-radius: 3px;
        }}
        QMenu::indicator:unchecked {{
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 3px;
        }}
    """
