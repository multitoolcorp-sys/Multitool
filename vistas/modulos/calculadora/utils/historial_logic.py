import json
from pathlib import Path

class HistorialLogic:
    def __init__(self, ruta_usuario):
        self.ruta_usuario = Path(ruta_usuario) if ruta_usuario else None
        self.historial = []
        self.cargar_historial()

    def guardar_historial(self):
        """Guarda el historial en un archivo"""
        if not self.ruta_usuario:
            return
            
        try:
            historial_dir = self.ruta_usuario / "historial"
            historial_dir.mkdir(exist_ok=True)
            
            with open(historial_dir / "calculadora_historial.json", "w") as f:
                json.dump(self.historial, f)
        except Exception as e:
            print(f"Error al guardar historial: {e}")

    def cargar_historial(self):
        """Carga el historial desde un archivo"""
        if not self.ruta_usuario:
            return
            
        try:
            historial_path = self.ruta_usuario / "historial" / "calculadora_historial.json"
            if historial_path.exists():
                with open(historial_path, "r") as f:
                    self.historial = json.load(f)
        except Exception as e:
            print(f"Error al cargar historial: {e}")

    def agregar(self, expresion, resultado):
        """Agrega un cálculo al historial y guarda"""
        entrada = f"{expresion} = {resultado}"
        self.historial.insert(0, entrada)
        
        if len(self.historial) > 50:
            self.historial.pop()
            
        self.guardar_historial()

    def limpiar(self):
        """Limpia el historial"""
        self.historial = []
        self.guardar_historial()
        
    def obtener_lista(self):
        """Retorna la lista actual"""
        return self.historial

