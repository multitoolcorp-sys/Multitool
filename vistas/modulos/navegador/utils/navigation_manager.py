import webbrowser
import json
import datetime
import threading
from pathlib import Path
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QMessageBox
from PyQt6.QtCore import QUrl, Qt

PYQT_WEBENGINE_AVAILABLE = True

class NavigationManager:
    def __init__(self, ruta_usuario, url_callback=None, url_integrado_callback=None, 
                 hist_reciente_callback=None, hist_callback=None):
        self.ruta_usuario = Path(ruta_usuario)
        self.url_callback = url_callback
        self.url_integrado_callback = url_integrado_callback
        self.hist_reciente_callback = hist_reciente_callback
        self.hist_callback = hist_callback
        
        self.historial = self.cargar_historial()
        self.ventanas_navegador = []

    def cargar_historial(self):
        try:
            ruta = self.ruta_usuario / "historial.json"
            if ruta.exists():
                with open(ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except: return []

    def guardar_historial(self):
        try:
            ruta = self.ruta_usuario / "historial.json"
            self.ruta_usuario.mkdir(parents=True, exist_ok=True)
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(self.historial, f, ensure_ascii=False, indent=4)
        except: pass

    def añadir_historial(self, url, titulo=None):
        if not url or not isinstance(url, str):
            return
        url = url.strip()
        if not url or url.startswith(("about:", "data:", "chrome:", "edge:")):
            return

        fecha_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not titulo or titulo in ("Página Web", "Cargando...", "Nueva Pestaña"):
            try:
                titulo = url.split('//')[1].split('/')[0].replace('www.', '')
            except Exception:
                titulo = url

        # Evitar duplicados idénticos consecutivos pero actualizar título si llegó uno mejor
        if not self.historial or self.historial[0]["url"] != url:
            self.historial.insert(0, {"url": url, "titulo": str(titulo), "fecha": fecha_hora})
            self.historial = self.historial[:500]
            self.guardar_historial()
            
            if self.hist_callback: 
                try: self.hist_callback()
                except Exception: pass
            if self.hist_reciente_callback: 
                try: self.hist_reciente_callback()
                except Exception: pass
        elif self.historial and self.historial[0]["url"] == url and titulo and titulo not in ("Página Web", "Cargando...", "Nueva Pestaña"):
            if self.historial[0].get("titulo") != str(titulo):
                self.historial[0]["titulo"] = str(titulo)
                self.guardar_historial()
                if self.hist_callback: 
                    try: self.hist_callback()
                    except Exception: pass

    def navegador_ir(self, url):
        try:
            if not url.startswith(('http://', 'https://')): 
                url = 'https://' + url
            webbrowser.open(url)
            if self.url_callback: self.url_callback(url)
            self.añadir_historial(url)
        except Exception as e:
            print(f"Error opening external browser: {e}")

    def abrir_url_integrada(self, url):
        if not PYQT_WEBENGINE_AVAILABLE:
            QMessageBox.information(None, "Navegador", "El motor de navegación integrado (PyQt6-WebEngine) no está instalado.\nUsando navegador externo.")
            self.navegador_ir(url)
            return

        try:
            if not url.startswith(('http://', 'https://')): 
                url = 'https://' + url
            
            if self.url_integrado_callback: 
                self.url_integrado_callback(url)
            self.añadir_historial(url)
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error al abrir navegador integrado: {e}")

    def limpiar_historial(self):
        self.historial = []
        self.guardar_historial()
        if self.hist_callback: self.hist_callback()
        if self.hist_reciente_callback: self.hist_reciente_callback()

# NavegadorWindow eliminado ya que usamos la pestaña integrada del sistema

