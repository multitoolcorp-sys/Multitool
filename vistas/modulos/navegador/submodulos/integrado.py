"""
integrado.py - Fachada modular del Navegador Multipestaña con Microsoft Edge WebView2
Reorganizado y modularizado en vistas/modulos/navegador/submodulos/integrado/
"""

from .integrado.browser import MultiTabBrowser
from .integrado.container import (
    BrowserContainer, BrowserTabBar, generar_icono_por_defecto,
    obtener_o_generar_icono, guardar_icono_en_cache
)
from .integrado.dialogs import DialogoPermisos, DialogoProxy, BrowserPopupWindow
from .integrado.toolbar import BrowserToolbar, ZoomFloatingWidget
from .integrado.extensions_dialog import ExtensionsDialog

# Aliases de compatibilidad hacia atrás
TabNavegadorIntegrado = MultiTabBrowser
CustomTabBar = BrowserTabBar
PermisosDialog = DialogoPermisos
ProxyDialog = DialogoProxy

__all__ = [
    "MultiTabBrowser",
    "TabNavegadorIntegrado",
    "CustomTabBar",
    "BrowserTabBar",
    "BrowserContainer",
    "generar_icono_por_defecto",
    "obtener_o_generar_icono",
    "guardar_icono_en_cache",
    "DialogoPermisos",
    "DialogoProxy",
    "PermisosDialog",
    "ProxyDialog",
    "BrowserPopupWindow",
    "BrowserToolbar",
    "ZoomFloatingWidget",
    "ExtensionsDialog"
]
