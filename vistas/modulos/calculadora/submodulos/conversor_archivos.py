import platform
import os
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QMessageBox, QFrame, QFileDialog, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor

try:
    from vistas.modulos.calculadora.utils.file_conversion_worker import ConversionThread
except ImportError:
    from ..utils.file_conversion_worker import ConversionThread


class TabCalculadoraConversorArchivos(QWidget):
    """Interfaz moderna al estilo Convertio para convertir tipos de archivos"""
    def __init__(self, parent, colores, agregar_al_historial_callback):
        super().__init__(parent)
        self.colores = colores
        self.agregar_al_historial = agregar_al_historial_callback
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.archivo_actual = None
        self.temp_out_path = None
        self.inicializar_ui()

    def inicializar_ui(self):
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(12, 12, 12, 12)
        self.layout_principal.setSpacing(12)
        
        # --- HEADER / DROPZONE ---
        self.drop_card = QFrame()
        self.drop_card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 2px dashed {self.colores['acento']}66;")
        drop_lay = QVBoxLayout(self.drop_card)
        drop_lay.setContentsMargins(15, 15, 15, 15)
        drop_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_drop_icon = QLabel("📁")
        self.lbl_drop_icon.setFont(QFont("Segoe UI Emoji", 32))
        self.lbl_drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_drop_icon.setStyleSheet("background: transparent; border: none;")
        drop_lay.addWidget(self.lbl_drop_icon)
        
        self.lbl_file = QLabel("Selecciona un archivo para convertir")
        self.lbl_file.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.lbl_file.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_file.setStyleSheet("background: transparent; border: none; color: white;")
        drop_lay.addWidget(self.lbl_file)

        self.btn_seleccionar = QPushButton("📁 Seleccionar archivo")
        self.btn_seleccionar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_seleccionar.setFixedHeight(32)
        self.btn_seleccionar.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_seleccionar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white; border-radius: 12px; border: none; padding: 0 15px;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        self.btn_seleccionar.clicked.connect(self.seleccionar_archivo)
        
        btn_ly = QHBoxLayout()
        btn_ly.setSpacing(10)
        btn_ly.addWidget(self.btn_seleccionar)
        btn_ly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_lay.addLayout(btn_ly)
        
        self.layout_principal.addWidget(self.drop_card)
        
        # --- PANEL DE SELECCION FORMATO ---
        form_card = QFrame()
        form_card.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 12px;")
        form_lay = QHBoxLayout(form_card)
        form_lay.setContentsMargins(12, 12, 12, 12)
        
        lbl_to = QLabel("CONVERTIR A:")
        lbl_to.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_to.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        form_lay.addWidget(lbl_to)
        
        self.combo_formatos = QComboBox()
        self.combo_formatos.setMinimumHeight(32)
        self.combo_formatos.setFont(QFont(self.font_family, 10))
        self.combo_formatos.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_secundario']}; color: white; border: none; border-radius: 8px; padding-left: 15px; min-width: 150px;
            }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid white; }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']}; color: white; selection-background-color: {self.colores['acento']};
                border: 1px solid rgba(255,255,255,0.1); outline: none; padding: 5px;
            }}
        """)
        self.combo_formatos.addItems([".pdf", ".docx", ".png", ".jpg", ".ico", ".webp", ".txt", ".md"])
        form_lay.addWidget(self.combo_formatos, 1)
        
        self.btn_convertir = QPushButton("⚡ CONVERTIR AHORA")
        self.btn_convertir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_convertir.setMinimumHeight(32)
        self.btn_convertir.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_convertir.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('exito', '#34D399')}; color: #121218; border-radius: 8px; border: none; padding: 0 20px;
            }}
            QPushButton:hover {{ background-color: #10B981; }}
            QPushButton:disabled {{ background-color: {self.colores['bg_secundario']}; color: {self.colores['fg_secundario']}; }}
        """)
        self.btn_convertir.setEnabled(False)
        self.btn_convertir.clicked.connect(self.iniciar_conversion)
        form_lay.addWidget(self.btn_convertir)
        
        self.btn_descargar = QPushButton("📥 DESCARGAR")
        self.btn_descargar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_descargar.setMinimumHeight(32)
        self.btn_descargar.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_descargar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']}; color: white; border-radius: 8px; border: none; padding: 0 20px;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
            QPushButton:disabled {{ background-color: {self.colores['bg_secundario']}; color: {self.colores['fg_secundario']}; }}
        """)
        self.btn_descargar.clicked.connect(self.descargar_archivo)
        self.btn_descargar.setVisible(False)
        form_lay.addWidget(self.btn_descargar)
        
        self.layout_principal.addWidget(form_card)
        
        # --- PROGRESO Y RESULTADO ---
        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ background-color: {self.colores['bg_secundario']}; border-radius: 4px; border: none; }}
            QProgressBar::chunk {{ background-color: {self.colores['acento']}; border-radius: 4px; }}
        """)
        self.layout_principal.addWidget(self.progress)
        
        self.lbl_resultado = QLabel()
        self.lbl_resultado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_resultado.setFont(QFont(self.font_family, 10))
        self.lbl_resultado.setStyleSheet("color: white; border: none;")
        self.layout_principal.addWidget(self.lbl_resultado)
        
        self.layout_principal.addStretch()

    def seleccionar_archivo(self):
        file, _ = QFileDialog.getOpenFileName(self, "Seleccionar el archivo a convertir", "", "Todos los Archivos (*.*)")
        if file:
            self.archivo_actual = file
            fname = Path(self.archivo_actual).name
            self.lbl_file.setText(fname)
            self.lbl_drop_icon.setText("✅")
            self.btn_convertir.setEnabled(True)
            self.btn_descargar.setVisible(False)
            self.progress.setValue(0)
            self.lbl_resultado.clear()
            
            # Limpiar archivo temporal previo
            if hasattr(self, 'temp_out_path') and self.temp_out_path and self.temp_out_path.exists():
                try:
                    self.temp_out_path.unlink()
                except:
                    pass
            self.temp_out_path = None
            
            # Auto-sugerir extensiones filtradas estilo Convertio
            ext = Path(self.archivo_actual).suffix.lower()
            self.combo_formatos.clear()

            mapa_convertio = {
                # Audio
                '.mp3': [".wav", ".aac", ".flac", ".ogg", ".m4a"],
                '.wav': [".mp3", ".aac", ".flac", ".ogg", ".m4a"],
                '.aac': [".mp3", ".wav", ".flac", ".ogg"],
                '.flac': [".mp3", ".wav", ".aac", ".ogg"],
                '.ogg': [".mp3", ".wav", ".flac", ".m4a"],
                '.m4a': [".mp3", ".wav", ".aac", ".flac"],

                # Imágenes
                '.jpg': [".png", ".webp", ".ico", ".bmp", ".pdf", ".tiff"],
                '.jpeg': [".png", ".webp", ".ico", ".bmp", ".pdf", ".tiff"],
                '.png': [".jpg", ".webp", ".ico", ".bmp", ".pdf", ".tiff"],
                '.webp': [".png", ".jpg", ".ico", ".bmp", ".pdf"],
                '.bmp': [".png", ".jpg", ".webp", ".ico", ".pdf"],
                '.ico': [".png", ".jpg", ".webp", ".bmp"],

                # Documentos / PDF / Texto
                '.pdf': [".docx", ".txt", ".png", ".jpg", ".html"],
                '.docx': [".pdf", ".txt", ".html", ".png"],
                '.txt': [".pdf", ".html", ".md", ".docx"],
                '.md': [".pdf", ".html", ".txt", ".docx"],
                '.html': [".pdf", ".txt", ".md"],

                # Video
                '.mp4': [".avi", ".mkv", ".webm", ".gif", ".mp3"],
                '.avi': [".mp4", ".mkv", ".webm", ".gif", ".mp3"],
                '.mkv': [".mp4", ".avi", ".webm", ".gif", ".mp3"],
                '.webm': [".mp4", ".avi", ".gif", ".mp3"],
                '.gif': [".mp4", ".png", ".webp"],

                # Datos / Hojas de cálculo
                '.xlsx': [".csv", ".pdf", ".json", ".html", ".txt"],
                '.xls': [".xlsx", ".csv", ".pdf", ".json", ".txt"],
                '.csv': [".xlsx", ".json", ".txt", ".pdf"],
                '.json': [".csv", ".xlsx", ".txt"]
            }

            formatos_sugeridos = mapa_convertio.get(ext, [".pdf", ".docx", ".png", ".jpg", ".txt", ".mp3"])
            self.combo_formatos.addItems(formatos_sugeridos)

    def iniciar_conversion(self):
        if not self.archivo_actual: return
        target_ext = self.combo_formatos.currentText()
        
        # Limpiar archivo temporal previo
        if hasattr(self, 'temp_out_path') and self.temp_out_path and self.temp_out_path.exists():
            try:
                self.temp_out_path.unlink()
            except:
                pass
        
        # Generar ruta temporal de salida
        import tempfile
        import uuid
        temp_dir = Path(tempfile.gettempdir())
        self.temp_out_path = temp_dir / f"multitool_conv_{uuid.uuid4().hex}{target_ext}"

        self.progress.setValue(10)
        self.btn_convertir.setEnabled(False)
        self.btn_seleccionar.setEnabled(False)
        self.btn_descargar.setVisible(False)
        self.lbl_resultado.setText("Procesando conversión, por favor espere...")
        self.lbl_resultado.setStyleSheet(f"color: {self.colores['advertencia']};")
        
        self.thread = ConversionThread(self.archivo_actual, self.temp_out_path)
        self.thread.progress.connect(self.progress.setValue)
        self.thread.finished.connect(self.conversion_terminada)
        self.thread.start()

    def conversion_terminada(self, msj, exito):
        self.btn_convertir.setEnabled(True)
        self.btn_seleccionar.setEnabled(True)
        
        if exito:
            self.temp_out_path = Path(msj)
            self.progress.setValue(100)
            self.lbl_resultado.setStyleSheet(f"color: {self.colores['exito']}; font-weight: bold;")
            self.lbl_resultado.setText("¡Conversión exitosa! Haz clic en Descargar para guardar el archivo.")
            self.btn_descargar.setVisible(True)
            self.btn_descargar.setEnabled(True)
        else:
            self.temp_out_path = None
            self.progress.setValue(0)
            self.lbl_resultado.setStyleSheet(f"color: {self.colores['error']}; font-weight: bold;")
            self.lbl_resultado.setText(f"Error:\n{msj}")
            self.btn_descargar.setVisible(False)

    def descargar_archivo(self):
        if not hasattr(self, 'temp_out_path') or not self.temp_out_path or not self.temp_out_path.exists():
            QMessageBox.warning(self, "Error", "No hay ningún archivo convertido listo para descargar.")
            return
        
        # Nombre sugerido original con la nueva extensión
        sug_name = Path(self.archivo_actual).add_suffix(self.temp_out_path.suffix).name if hasattr(Path(self.archivo_actual), 'add_suffix') else Path(self.archivo_actual).stem + self.temp_out_path.suffix
        ext_filter = f"Archivos (*{self.temp_out_path.suffix})"
        
        # Sugerir la carpeta del archivo original
        sug_path = str(Path(self.archivo_actual).parent / sug_name)
        
        dest_file, _ = QFileDialog.getSaveFileName(self, "Guardar archivo convertido", sug_path, ext_filter)
        if dest_file:
            try:
                import shutil
                shutil.copy(str(self.temp_out_path), dest_file)
                self.lbl_resultado.setText(f"¡Guardado con éxito en:\n{Path(dest_file).name}!")
                self.lbl_resultado.setStyleSheet(f"color: {self.colores['exito']}; font-weight: bold;")
                self.agregar_al_historial("Conversor Archivos", f"{Path(self.archivo_actual).name} ➔ {Path(dest_file).name}")
                self.btn_descargar.setEnabled(False)
            except Exception as e:
                QMessageBox.critical(self, "Error al guardar", f"No se pudo guardar el archivo: {str(e)}")
