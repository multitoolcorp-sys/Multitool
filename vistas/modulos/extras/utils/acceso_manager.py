import json
import os
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox

class AccesosManager:
    def __init__(self, ruta_usuario):
        self.ruta_usuario = Path(ruta_usuario)
        self.ruta_usuario.mkdir(parents=True, exist_ok=True)
        self.ruta_datos = self.ruta_usuario / "mis_accesos.json"
        
        # Aplicaciones recomendadas iniciales que se copian la primera vez (para Windows)
        self.apps_por_defecto = [
            {"nombre": "Calculadora", "ruta": "calc.exe", "icono": "🧮"},
            {"nombre": "Bloc de Notas", "ruta": "notepad.exe", "icono": "📝"},
            {"nombre": "Paint", "ruta": "mspaint.exe", "icono": "🎨"},
            {"nombre": "Explorador", "ruta": "explorer.exe", "icono": "📁"},
            {"nombre": "Terminal", "ruta": "cmd.exe", "icono": "🖥️"},
            {"nombre": "Configuración", "ruta": "ms-settings:", "icono": "⚙️"}
        ]
        
        self.mis_apps = self._cargar_datos()

    def _cargar_datos(self):
        if not self.ruta_datos.exists():
            # Crear base si no existe
            self._guardar_datos(self.apps_por_defecto)
            return self.apps_por_defecto
        
        try:
            with open(self.ruta_datos, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else self.apps_por_defecto
        except Exception as e:
            print(f"Error cargando accesos directos: {e}")
            return self.apps_por_defecto

    def _guardar_datos(self, datos):
        try:
            with open(self.ruta_datos, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=4)
        except Exception as e:
            print(f"Error guardando accesos directos: {e}")

    def añadir_acceso(self, nombre, ruta, icono="🚀"):
        nuevo = {"nombre": nombre, "ruta": ruta, "icono": icono}
        self.mis_apps.append(nuevo)
        self._guardar_datos(self.mis_apps)

    def eliminar_acceso(self, ruta):
        self.mis_apps = [a for a in self.mis_apps if a["ruta"] != ruta]
        self._guardar_datos(self.mis_apps)

    def lanzar_aplicacion(self, ruta, emisor_gui=None):
        try:
            # Ejecutar el proceso de forma limpia en Windows
            if os.name == 'nt':
                # startfile maneja tanto URIs como executables
                os.startfile(ruta)
            else:
                subprocess.Popen([ruta])
            
            return True
        except Exception as e:
            if emisor_gui:
                QMessageBox.warning(emisor_gui, "Error al lanzar", f"No se pudo ejecutar: '{ruta}'\n\nMotivo: {str(e)}")
            return False

