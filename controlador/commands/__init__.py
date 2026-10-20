"""
Módulo de automatización y gestión de comandos de MultiTool.
Proporciona el motor de comandos, parser de placeholders y ejecutor de acciones modulares.
"""
from .command_engine import CommandEngine, ModuleCommandRegistry, PlaceholderParser

__all__ = ["CommandEngine", "ModuleCommandRegistry", "PlaceholderParser"]
