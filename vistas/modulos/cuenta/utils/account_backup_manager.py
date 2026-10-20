import json
from pathlib import Path
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor

def generar_carnet_hd(parent, config, usuario, colores, font_family="Segoe UI"):
    """Genera y exporta un carnet de credencial HD en formato PNG"""
    pix = QPixmap(520, 320)
    pix.fill(QColor(colores.get("bg_principal", "#121218")))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Header banner gradient
    painter.fillRect(0, 0, 520, 75, QColor(colores.get("acento", "#6366F1")))
    
    painter.setPen(QColor("white"))
    painter.setFont(QFont(font_family, 13, QFont.Weight.Bold))
    painter.drawText(20, 45, "MULTITOOL SUITE — CARNET DE CREDENCIAL")

    painter.setFont(QFont(font_family, 16, QFont.Weight.Bold))
    painter.drawText(20, 125, f"👤 {config.get('usuario', usuario)}")

    painter.setFont(QFont(font_family, 10))
    painter.setPen(QColor("#AAB0B8"))
    painter.drawText(20, 160, f"📧 Correo: {config.get('correo', 'Sin especificar')}")
    painter.drawText(20, 190, f"🎂 Cumpleaños: {config.get('cumpleaños', 'N/A')}")
    painter.drawText(20, 220, f"📅 Registro: {config.get('fecha_registro', 'N/A')}")
    painter.setPen(QColor("#10B981"))
    painter.drawText(20, 255, "🏅 Rango: Power User (Nivel 5 • Identidad Verificada)")

    painter.end()

    file_path, _ = QFileDialog.getSaveFileName(parent, "Guardar Carnet HD", f"Carnet_{usuario}.png", "Imágenes PNG (*.png)")
    if file_path:
        pix.save(file_path, "PNG")
        QMessageBox.information(parent, "Carnet HD Guardado", f"¡Carnet HD guardado exitosamente en:\n{file_path}!")

def exportar_respaldo_cuenta(parent, config):
    """Exporta la configuración del perfil a un archivo .mtbackup cifrado/json"""
    filename, _ = QFileDialog.getSaveFileName(parent, "Exportar Respaldo de Cuenta", "mi_cuenta.mtbackup", "Archivos de Respaldo (*.mtbackup *.json)")
    if filename:
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            QMessageBox.information(parent, "Respaldo Completo", "¡Respaldo (.mtbackup) de tu cuenta generado con éxito!")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"No se pudo exportar el respaldo:\n{e}")

def importar_respaldo_cuenta(parent, ruta_usuario, on_success_callback=None):
    """Importa un archivo .mtbackup y actualiza config.json de la cuenta"""
    filename, _ = QFileDialog.getOpenFileName(parent, "Importar Respaldo de Cuenta", "", "Archivos de Respaldo (*.mtbackup *.json)")
    if filename:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                from controlador.auth.crypto_utils import process_config_for_save
                with open(Path(ruta_usuario) / "config.json", "w", encoding="utf-8") as f:
                    json.dump(process_config_for_save(data), f, indent=4)
                QMessageBox.information(parent, "Respaldo Restaurado", "¡Respaldo importado correctamente! La información se ha actualizado.")
                if callable(on_success_callback):
                    on_success_callback(data)
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"No se pudo importar el respaldo:\n{e}")
