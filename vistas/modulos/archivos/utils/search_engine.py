import os
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

class GlobalSearchWorker(QThread):
    """Buscador global recursivo en segundo plano"""
    match_found = pyqtSignal(dict) # Metadata del archivo encontrado
    finished = pyqtSignal(int)    # Total de coincidencias
    
    def __init__(self, start_path, query):
        super().__init__()
        self.start_path = Path(start_path)
        self.query = query.lower()
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        count = 0
        try:
            for root, dirs, files in os.walk(str(self.start_path)):
                if not self._is_running: break
                
                # Buscar en archivos
                for f in files:
                    if self.query in f.lower():
                        path = Path(root) / f
                        try:
                            stats = path.stat()
                            self.match_found.emit({
                                "name": f,
                                "path": str(path),
                                "size": f"{stats.st_size / 1024:.1f} KB",
                                "type": path.suffix.upper() if path.suffix else "Archivo"
                            })
                            count += 1
                        except: continue
                
                # Buscar en carpetas
                for d in dirs:
                    if self.query in d.lower():
                        path = Path(root) / d
                        self.match_found.emit({
                            "name": d,
                            "path": str(path),
                            "size": "--",
                            "type": "Carpeta"
                        })
                        count += 1

        except Exception as e:
            print(f"Error búsqueda: {e}")
            
        self.finished.emit(count)
