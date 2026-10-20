import os
import zipfile
import platform
from PyQt6.QtWidgets import QDialog, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QProgressBar, QMessageBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

class ZipCompressThread(QThread):
    """Hilo asíncrono para comprimir archivos/carpetas"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, source_path, dest_zip_path):
        super().__init__()
        self.source_path = source_path
        self.dest_zip_path = dest_zip_path

    def run(self):
        try:
            files_to_zip = []
            if os.path.isdir(self.source_path):
                for root, dirs, files in os.walk(self.source_path):
                    for file in files:
                        files_to_zip.append(os.path.join(root, file))
            else:
                files_to_zip.append(self.source_path)

            total_files = len(files_to_zip)
            if total_files == 0:
                self.finished.emit(False, "No hay archivos en la ruta de origen.")
                return

            base_dir = os.path.dirname(self.source_path)
            
            with zipfile.ZipFile(self.dest_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for idx, file_path in enumerate(files_to_zip):
                    arcname = os.path.relpath(file_path, base_dir)
                    zipf.write(file_path, arcname)
                    pct = int(((idx + 1) / total_files) * 100)
                    self.progress.emit(pct, f"Comprimiendo {os.path.basename(file_path)}...")

            self.finished.emit(True, f"Archivo comprimido con éxito en:\n{self.dest_zip_path}")
        except Exception as e:
            self.finished.emit(False, str(e))


class ZipExtractThread(QThread):
    """Hilo asíncrono para extraer archivos ZIP con soporte de contraseña opcional"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, zip_path, dest_dir, password=None):
        super().__init__()
        self.zip_path = zip_path
        self.dest_dir = dest_dir
        self.password = password

    def run(self):
        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zipf:
                namelist = zipf.namelist()
                total_files = len(namelist)
                if total_files == 0:
                    self.finished.emit(False, "El archivo ZIP está vacío.")
                    return

                pwd_bytes = self.password.encode('utf-8') if self.password else None

                for idx, name in enumerate(namelist):
                    zipf.extract(name, self.dest_dir, pwd=pwd_bytes)
                    pct = int(((idx + 1) / total_files) * 100)
                    self.progress.emit(pct, f"Extrayendo {os.path.basename(name)}...")

            self.finished.emit(True, f"Extracción exitosa en:\n{self.dest_dir}")
        except RuntimeError as re:
            if "encrypted" in str(re).lower() or "password" in str(re).lower():
                self.finished.emit(False, "Cifrado detectado: Contraseña incorrecta o ausente.")
            else:
                self.finished.emit(False, str(re))
        except Exception as e:
            self.finished.emit(False, str(e))


class ZipProgressDialog(QDialog):
    """Diálogo de progreso premium para operaciones ZIP"""
    def __init__(self, parent, title, colores):
        super().__init__(parent)
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.setWindowTitle(title)
        self.setFixedWidth(400)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white;")
        
        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        self.lbl_status = QLabel("Preparando operación...")
        self.lbl_status.setFont(QFont(self.font_family, 10))
        self.lbl_status.setStyleSheet("color: white; border: none;")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(16)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 8px;
                color: white;
                text-align: center;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {self.colores['acento']};
                border-radius: 8px;
            }}
        """)
        layout.addWidget(self.progress)
        
        self.thread = None

    def start_compress(self, source, dest):
        self.thread = ZipCompressThread(source, dest)
        self.thread.progress.connect(self._on_progress)
        self.thread.finished.connect(self._on_finished)
        self.thread.start()

    def start_extract(self, zip_path, dest_dir, password=None):
        self.thread = ZipExtractThread(zip_path, dest_dir, password)
        self.thread.progress.connect(self._on_progress)
        self.thread.finished.connect(self._on_finished)
        self.thread.start()

    def _on_progress(self, val, msg):
        self.progress.setValue(val)
        self.lbl_status.setText(msg)

    def _on_finished(self, success, message):
        if success:
            QMessageBox.information(self, "ZIP Operación", message)
            self.accept()
        else:
            QMessageBox.critical(self, "ZIP Error", f"Ocurrió un error en la operación:\n\n{message}")
            self.reject()


class TabZipManager(QWidget):
    """Submódulo inline para compresión y extracción rápida de archivos ZIP"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        lbl_title = QLabel("📦 COMPRESOR Y EXTRACTOR ZIP")
        lbl_title.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores['acento']};")
        layout.addWidget(lbl_title)

        # Sección Comprimir
        box_comp = QFrame()
        box_comp.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06);")
        c_lay = QVBoxLayout(box_comp)
        c_lay.setSpacing(10)

        lbl_c = QLabel("1. Comprimir Archivo o Carpeta")
        lbl_c.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_c.setStyleSheet("color: white;")
        c_lay.addWidget(lbl_c)

        h_c = QHBoxLayout()
        self.txt_source = QLineEdit()
        self.txt_source.setPlaceholderText("Ruta del archivo o carpeta a comprimir...")
        self.txt_source.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 6px;")
        btn_browse_c = QPushButton("📂 Seleccionar")
        btn_browse_c.setFixedHeight(32)
        btn_browse_c.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 4px 10px;")
        btn_browse_c.clicked.connect(self._browse_source)
        h_c.addWidget(self.txt_source, 1)
        h_c.addWidget(btn_browse_c)
        c_lay.addLayout(h_c)

        btn_do_comp = QPushButton("⚡ Comprimir a ZIP")
        btn_do_comp.setFixedHeight(32)
        btn_do_comp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_do_comp.setStyleSheet(f"background: {self.colores['acento']}; color: white; font-weight: bold; border-radius: 6px;")
        btn_do_comp.clicked.connect(self._comprimir)
        c_lay.addWidget(btn_do_comp)

        layout.addWidget(box_comp)

        # Sección Extraer
        box_ext = QFrame()
        box_ext.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06);")
        e_lay = QVBoxLayout(box_ext)
        e_lay.setSpacing(10)

        lbl_e = QLabel("2. Extraer Archivo ZIP")
        lbl_e.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_e.setStyleSheet("color: white;")
        e_lay.addWidget(lbl_e)

        h_e = QHBoxLayout()
        self.txt_zip = QLineEdit()
        self.txt_zip.setPlaceholderText("Ruta del archivo .zip a extraer...")
        self.txt_zip.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 6px;")
        btn_browse_e = QPushButton("📂 Seleccionar ZIP")
        btn_browse_e.setFixedHeight(32)
        btn_browse_e.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 4px 10px;")
        btn_browse_e.clicked.connect(self._browse_zip)
        h_e.addWidget(self.txt_zip, 1)
        h_e.addWidget(btn_browse_e)
        e_lay.addLayout(h_e)

        btn_do_ext = QPushButton("🔓 Extraer ZIP")
        btn_do_ext.setFixedHeight(32)
        btn_do_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_do_ext.setStyleSheet(f"background: {self.colores['exito']}; color: white; font-weight: bold; border-radius: 6px;")
        btn_do_ext.clicked.connect(self._extraer)
        e_lay.addWidget(btn_do_ext)

        layout.addWidget(box_ext)
        layout.addStretch()

    def _browse_source(self):
        from PyQt6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Comprimir")
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo para Comprimir")
        if path:
            self.txt_source.setText(path)

    def _browse_zip(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo ZIP", filter="Archivos ZIP (*.zip)")
        if path:
            self.txt_zip.setText(path)

    def _comprimir(self):
        src = self.txt_source.text().strip()
        if not src or not os.path.exists(src): return
        from PyQt6.QtWidgets import QFileDialog
        dest, _ = QFileDialog.getSaveFileName(self, "Guardar como ZIP", os.path.dirname(src), "Archivo ZIP (*.zip)")
        if dest:
            if not dest.endswith(".zip"): dest += ".zip"
            dlg = ZipProgressDialog(self, f"Comprimiendo {os.path.basename(src)}", self.colores)
            dlg.start_compress(src, dest)
            dlg.exec()

    def _extraer(self):
        zip_path = self.txt_zip.text().strip()
        if not zip_path or not os.path.exists(zip_path): return
        from PyQt6.QtWidgets import QFileDialog
        dest_dir = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de destino")
        if dest_dir:
            dlg = ZipProgressDialog(self, f"Extrayendo {os.path.basename(zip_path)}", self.colores)
            dlg.start_extract(zip_path, dest_dir)
            dlg.exec()
