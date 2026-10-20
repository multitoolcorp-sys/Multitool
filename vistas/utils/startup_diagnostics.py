"""
startup_diagnostics.py - Diagnosticador Pre-Flight e Integridad al Inicio de MultiTool
"""
import os
import sys
import json
import shutil
import logging
from pathlib import Path

class StartupDiagnostics:
    """Ejecuta chequeos rápidos de salud de sistema y archivos antes de iniciar la GUI"""

    @staticmethod
    def run_checks():
        warnings = []
        is_ok = True

        # 1. Verificar Espacio en Disco
        try:
            total, used, free = shutil.disk_usage(".")
            free_mb = free / (1024 * 1024)
            if free_mb < 200:
                warnings.append(f"Espacio libre en disco bajo: {free_mb:.1f} MB disponibles.")
        except Exception as e:
            warnings.append(f"No se pudo verificar el disco: {e}")

        # 2. Verificar estructura de carpetas esenciales
        base_dir = Path(".")
        cuentas_dir = base_dir / "cuentas"
        if not cuentas_dir.exists():
            try:
                cuentas_dir.mkdir(parents=True, exist_ok=True)
                logging.info("[Diagnostics] Creada carpeta de cuentas por defecto.")
            except Exception as e:
                is_ok = False
                warnings.append(f"No se pudo crear carpeta 'cuentas': {e}")

        # 3. Verificar JSON de Temas
        temas_file = base_dir / "vistas" / "utils" / "temas.json"
        if temas_file.exists():
            try:
                with open(temas_file, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception:
                warnings.append("Archivo 'temas.json' corrupto. Se usarán temas por defecto.")

        # 4. Verificar módulos clave de Python
        mods_requeridos = ["PyQt6", "psutil"]
        for mod in mods_requeridos:
            try:
                __import__(mod)
            except ImportError:
                is_ok = False
                warnings.append(f"Librería requerida no encontrada: '{mod}'")

        return is_ok, warnings
