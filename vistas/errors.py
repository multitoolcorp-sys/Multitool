"""
errors.py - Manejador Global de Excepciones No Controladas y Diálogo de Recuperación
"""
import sys
import logging
import traceback
from PyQt6.QtWidgets import (
    QApplication, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QPlainTextEdit
)
from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtGui import QFont


class CrashRecoveryDialog(QDialog):
    """Diálogo modal para recuperación de caídas y reporte limpio de errores"""
    def __init__(self, error_msg, parent=None):
        super().__init__(parent)
        self.error_msg = error_msg
        self.setWindowTitle("⚠️ Error Crítico de Aplicación")
        self.setMinimumSize(540, 360)
        self.setStyleSheet("""
            QDialog { background-color: #121218; color: white; }
            QLabel { color: white; }
            QPlainTextEdit { background-color: #1E1E2E; color: #F87171; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; font-family: Consolas; }
            QPushButton { background-color: #6366F1; color: white; border-radius: 6px; padding: 8px 16px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #818CF8; }
        """)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        lbl_head = QLabel("⚠️ MultiTool ha experimentado un error inesperado")
        lbl_head.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_head.setStyleSheet("color: #F87171;")
        lay.addWidget(lbl_head)

        lbl_desc = QLabel("El error ha sido registrado en 'multitool.log'. Puedes copiar el informe o reiniciar la aplicación:")
        lbl_desc.setStyleSheet("color: #AAB0B8; font-size: 11px;")
        lay.addWidget(lbl_desc)

        txt_trace = QPlainTextEdit(self.error_msg)
        txt_trace.setReadOnly(True)
        lay.addWidget(txt_trace, 1)

        btm = QHBoxLayout()

        btn_copy = QPushButton("📋 Copiar Informe")
        btn_copy.clicked.connect(self._copiar_informe)
        btm.addWidget(btn_copy)

        btm.addStretch()

        btn_restart = QPushButton("🔄 Reiniciar App")
        btn_restart.setStyleSheet("background-color: #34D399; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        btn_restart.clicked.connect(self._reiniciar_app)
        btm.addWidget(btn_restart)

        btn_close = QPushButton("✕ Cerrar")
        btn_close.setStyleSheet("background-color: rgba(255,255,255,0.1); color: white; padding: 8px 16px; border-radius: 6px;")
        btn_close.clicked.connect(self.reject)
        btm.addWidget(btn_close)

        lay.addLayout(btm)

    def _copiar_informe(self):
        QApplication.clipboard().setText(self.error_msg)
        QMessageBox.information(self, "Copiado", "Informe de error copiado al portapapeles.")

    def _reiniciar_app(self):
        from controlador.utils.paths import reiniciar_aplicacion
        reiniciar_aplicacion(self)


def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    """Manejador global de excepciones no controladas"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.critical("Excepción no controlada:\n" + error_msg)

    if QApplication.instance():
        try:
            dlg = CrashRecoveryDialog(error_msg)
            dlg.exec()
        except Exception:
            print(error_msg)
    else:
        print(error_msg)

def setup_error_handler():
    """Asigna el manejador global de excepciones"""
    sys.excepthook = handle_unhandled_exception
