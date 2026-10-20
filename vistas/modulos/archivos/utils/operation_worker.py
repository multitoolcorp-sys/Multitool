import os
import shutil
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

class FileOperationWorker(QThread):
    """Hilo para operaciones de archivos (copiar/mover) con progreso"""
    progress = pyqtSignal(int, str)  # porcentaje, mensaje
    finished = pyqtSignal(bool, str) # exito, mensaje final

    def __init__(self, source, destination, action):
        super().__init__()
        self.source = Path(source)
        self.destination = Path(destination)
        self.action = action

    def run(self):
        try:
            if self.action == "cortar":
                self.progress.emit(50, f"Moviendo {self.source.name}...")
                shutil.move(str(self.source), str(self.destination))
                self.finished.emit(True, f"'{self.source.name}' movido con éxito.")
            else:
                # Copiar con detección de progreso (vía tamaño si es posible)
                if self.source.is_dir():
                    # Para directorios, usamos copytree (más complejo medir progreso real por archivos)
                    self.progress.emit(10, f"Calculando copia de carpeta {self.source.name}...")
                    shutil.copytree(str(self.source), str(self.destination))
                else:
                    # Para archivos grandes, usamos copia por chunks para dar progreso
                    total_size = self.source.stat().st_size
                    copied = 0
                    chunk_size = 1024 * 1024 # 1MB
                    
                    with open(self.source, 'rb') as fsrc:
                        with open(self.destination, 'wb') as fdst:
                            while True:
                                chunk = fsrc.read(chunk_size)
                                if not chunk:
                                    break
                                fdst.write(chunk)
                                copied += len(chunk)
                                percent = int((copied / total_size) * 100)
                                self.progress.emit(percent, f"Copiando... {percent}%")
                                
                    shutil.copystat(str(self.source), str(self.destination))
                
                self.finished.emit(True, f"'{self.source.name}' copiado con éxito.")
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")

