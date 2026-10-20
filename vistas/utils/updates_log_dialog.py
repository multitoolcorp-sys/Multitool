"""
updates_log_dialog.py — Diálogo para visualizar el historial de parches y actualizaciones .mtu instalados.
"""
import json
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit
from controlador.utils.paths import get_data_path

class UpdatesLogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Historial de Actualizaciones")
        self.setMinimumSize(550, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #121218;
                color: #E2E2E2;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #AAB0B8;
                font-size: 13px;
                font-weight: bold;
            }
            QPlainTextEdit {
                background-color: #1E1E2E;
                color: #818CF8;
                border: 1px solid #2D2D3D;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
            QPushButton {
                background-color: #2D2D3D;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        layout.addWidget(QLabel("📋 Registro de Actualizaciones Instaladas (.mtu):"))

        self.text_area = QPlainTextEdit()
        self.text_area.setReadOnly(True)
        layout.addWidget(self.text_area)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        self.cargar_log()

    def cargar_log(self):
        log_path = get_data_path() / "actualizaciones.json"
        if not log_path.exists():
            self.text_area.setPlainText("No se ha registrado ninguna actualización instalada en este sistema todavía.")
            return

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                historial = json.load(f)

            if not historial:
                self.text_area.setPlainText("Historial de actualizaciones vacío.")
                return

            texto = ""
            for i, entrada in enumerate(reversed(historial), 1):
                texto += f"[{i}] FECHA: {entrada.get('fecha', 'N/A')}\n"
                texto += f"    Archivo: {entrada.get('archivo', 'N/A')}\n"
                texto += f"    Tipo:    {entrada.get('tipo', 'N/A')}\n"
                afectados = entrada.get('archivos_afectados', [])
                if afectados:
                    texto += "    Módulos / Archivos Extraídos:\n"
                    for a in afectados:
                        texto += f"      - {a}\n"
                texto += "-" * 55 + "\n\n"

            self.text_area.setPlainText(texto)
        except Exception as e:
            self.text_area.setPlainText(f"Error al leer el archivo de historial: {e}")
