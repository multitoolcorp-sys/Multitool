# -*- coding: utf-8 -*-
"""
Fachada de compatibilidad para el Modo Creador (mode MT).
La implementación modular reside en `vistas/utils/creator/`.
"""

from vistas.utils.creator import (
    ModuleCreatorDialog,
    a_pascal_case,
    abrir_creador_modulos,
    normalizar_id_modulo,
)

__all__ = [
    "ModuleCreatorDialog",
    "abrir_creador_modulos",
    "normalizar_id_modulo",
    "a_pascal_case",
]
