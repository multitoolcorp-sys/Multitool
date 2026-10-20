import shutil
import zipfile
import sys
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QApplication

def reiniciar_app():
    """Reinicia la aplicación MultiTool de forma segura"""
    from controlador.utils.paths import reiniciar_aplicacion
    reiniciar_aplicacion()

def instalar_complemento_dialog(parent):
    """Permite seleccionar un archivo .zip/.mtp de complemento e instalarlo en la carpeta plugins/"""
    from controlador.utils.paths import get_resource_path
    
    ruta_zip, _ = QFileDialog.getOpenFileName(
        parent, "Seleccionar Complemento", "", "Complementos de Multitool (*.zip *.mtp)"
    )
    if not ruta_zip:
        return
        
    ruta_zip = Path(ruta_zip)
    base_dir = get_resource_path()
    plugins_dir = base_dir / "plugins"
    
    if not plugins_dir.exists():
        plugins_dir.mkdir(parents=True, exist_ok=True)
        
    dest_path = plugins_dir / ruta_zip.name
    
    try:
        shutil.copy(str(ruta_zip), str(dest_path))
        
        if zipfile.is_zipfile(dest_path):
            with zipfile.ZipFile(dest_path, 'r') as z:
                names = z.namelist()
                has_config = any(name.endswith("config.json") for name in names)
                
            if not has_config:
                dest_path.unlink()
                QMessageBox.warning(
                    parent, "Instalación fallida", 
                    "El archivo comprimido no parece ser un plugin válido de Multitool (falta config.json)."
                )
                return
        else:
            dest_path.unlink()
            QMessageBox.warning(parent, "Instalación fallida", "El archivo seleccionado no es un archivo zip válido.")
            return
            
        QMessageBox.information(
            parent, "Instalación exitosa",
            f"El complemento '{ruta_zip.stem}' se ha instalado correctamente.\n\n"
            "Para activarlo e integrarlo en el menú, es necesario reiniciar la aplicación."
        )
        
        confirm = QMessageBox.question(
            parent, "Reiniciar ahora",
            "¿Deseas reiniciar la aplicación de inmediato para activar el complemento?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            reiniciar_app()
            
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink()
        QMessageBox.critical(parent, "Error de instalación", f"Ocurrió un error al instalar el complemento:\n{e}")
