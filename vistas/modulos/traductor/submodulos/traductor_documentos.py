import os
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QTextEdit, QFrame, QFileDialog, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class TraductorDocumentosSubmodule(QWidget):
    """Submódulo 2: Traducción de Archivos de Texto, Documentos y Subtítulos (.txt, .srt)"""
    def __init__(self, parent, context, manager, colores):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        self.archivo_cargado = None
        self.inicializar_ui()

        # Conectar señales del manager
        self.manager.doc_traduccion_progreso.connect(self._on_progreso)
        self.manager.doc_traduccion_fin.connect(self._on_traduccion_fin)

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("📄 TRADUCCIÓN DE DOCUMENTOS & SUBTÍTULOS (.TXT, .SRT)")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        layout.addLayout(hdr)

        # Panel de Selección de Archivo
        self.file_frame = QFrame()
        self.file_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px dashed rgba(255, 255, 255, 0.15);
                border-radius: 10px;
            }}
        """)
        f_lay = QHBoxLayout(self.file_frame)
        f_lay.setContentsMargins(15, 12, 15, 12)
        f_lay.setSpacing(12)

        self.lbl_file_path = QLabel("📁 Ningún archivo seleccionado (Soporta .txt, .srt, .md)")
        self.lbl_file_path.setFont(QFont(self.font_family, 9))
        self.lbl_file_path.setStyleSheet("color: rgba(255,255,255,0.7);")
        f_lay.addWidget(self.lbl_file_path, 1)

        btn_select_file = QPushButton("📂 Seleccionar Archivo")
        btn_select_file.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select_file.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_select_file.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 8px 16px; border-radius: 6px; border: none;")
        btn_select_file.clicked.connect(self._seleccionar_archivo)
        f_lay.addWidget(btn_select_file)

        layout.addWidget(self.file_frame)

        # Configuración de Traducción
        cfg_bar = QHBoxLayout()
        cfg_bar.setSpacing(10)

        lbl_target = QLabel("Traducir a:")
        lbl_target.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_target.setStyleSheet("color: white;")
        cfg_bar.addWidget(lbl_target)

        self.combo_target_lang = QComboBox()
        self.combo_target_lang.setFont(QFont(self.font_family, 9))
        self.combo_target_lang.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 6px 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
            }}
        """)
        self.combo_target_lang.addItems(self.manager.obtener_lista_formatada(incluir_auto=False))
        cfg_bar.addWidget(self.combo_target_lang, 1)

        self.btn_start_doc_trad = QPushButton("⚡ Traducir Documento")
        self.btn_start_doc_trad.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start_doc_trad.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_start_doc_trad.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 8px 20px; border-radius: 6px; border: none;")
        self.btn_start_doc_trad.clicked.connect(self._iniciar_traduccion_documento)
        cfg_bar.addWidget(self.btn_start_doc_trad)

        layout.addLayout(cfg_bar)

        # Barra de Progreso
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(8)
        self.pbar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.colores['bg_terciario']};
                border-radius: 4px; text-align: center; color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {self.colores['acento']}; border-radius: 4px;
            }}
        """)
        self.pbar.setValue(0)
        layout.addWidget(self.pbar)

        self.lbl_status = QLabel("Listo.")
        self.lbl_status.setFont(QFont(self.font_family, 8))
        self.lbl_status.setStyleSheet("color: rgba(255,255,255,0.6);")
        layout.addWidget(self.lbl_status)

        # Vista Previa del Documento
        lbl_preview = QLabel("📄 Vista previa de la traducción:")
        lbl_preview.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_preview.setStyleSheet("color: white;")
        layout.addWidget(lbl_preview)

        self.txt_preview = QTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setPlaceholderText("La vista previa del archivo traducido aparecerá aquí...")
        self.txt_preview.setFont(QFont(self.mono_font, 10))
        self.txt_preview.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px; padding: 12px;
            }}
        """)
        layout.addWidget(self.txt_preview, 1)

    def _seleccionar_archivo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Documento para Traducir", "", "Archivos de Texto (*.txt *.srt *.md *.csv);;Todos los Archivos (*.*)")
        if file_path:
            self.archivo_cargado = file_path
            self.lbl_file_path.setText(f"📄 {Path(file_path).name} ({os.path.getsize(file_path)} bytes)")

    def _iniciar_traduccion_documento(self):
        if not self.archivo_cargado:
            QMessageBox.warning(self, "Sin Archivo", "Por favor selecciona un archivo primero.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Guardar Archivo Traducido", f"traducido_{Path(self.archivo_cargado).name}", "Archivos del Mismo Tipo (*.*)")
        if not out_path:
            return

        dest_text = self.combo_target_lang.currentText()
        dest_code = dest_text.rsplit("(", 1)[1].rstrip(")") if "(" in dest_text else "es"

        self.pbar.setValue(0)
        self.lbl_status.setText("Iniciando traducción...")
        self.manager.traducir_documento(self.archivo_cargado, "auto", dest_code, out_path)

    def _on_progreso(self, pct, status_msg):
        self.pbar.setValue(pct)
        self.lbl_status.setText(status_msg)

    def _on_traduccion_fin(self, out_path, preview_text):
        self.pbar.setValue(100)
        self.lbl_status.setText(f"✅ ¡Guardado en {out_path}!")
        self.txt_preview.setPlainText(preview_text)
        QMessageBox.information(self, "Éxito", f"Documento traducido y guardado en:\n{out_path}")

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#121218')
        bg_sec = colores.get('bg_secundario', '#1E1E2E')
        bg_terc = colores.get('bg_terciario', '#2D2D3D')
        acento = colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        if hasattr(self, 'file_frame'):
            self.file_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_sec};
                    border: 1px dashed rgba(255, 255, 255, 0.15);
                    border-radius: 10px;
                }}
            """)
        self.combo_target_lang.setStyleSheet(f"""
            QComboBox {{
                background-color: {bg_terc};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 6px 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg_sec};
                color: white; selection-background-color: {acento};
            }}
        """)
        self.txt_preview.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_sec};
                color: white; border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px; padding: 12px;
            }}
        """)
        self.btn_start_doc_trad.setStyleSheet(f"background-color: {acento}; color: white; padding: 8px 20px; border-radius: 6px; border: none;")

    def cleanup(self):
        pass

