"""
Paquete modular del Navegador Integrado WebView2 para MultiTool
"""

from .browser import MultiTabBrowser
from .container import (
    BrowserContainer, BrowserTabBar, generar_icono_por_defecto,
    obtener_o_generar_icono, guardar_icono_en_cache
)
from .dialogs import DialogoPermisosSitio, DialogoProxy, BrowserPopupWindow

from .toolbar import BrowserToolbar, ZoomFloatingWidget
from .extensions_dialog import ExtensionsDialog

TabNavegadorIntegrado = MultiTabBrowser

__all__ = [
    "MultiTabBrowser",
    "TabNavegadorIntegrado",
    "BrowserContainer",
    "BrowserTabBar",
    "generar_icono_por_defecto",
    "obtener_o_generar_icono",
    "guardar_icono_en_cache",
    "DialogoPermisos",
    "DialogoProxy",
    "BrowserPopupWindow",
    "BrowserToolbar",
    "ZoomFloatingWidget",
    "ExtensionsDialog"
]
