"""
terminal_console.py - Terminal y consola de salida SQL integrada estilo DBeaver / VS Code
Elimina por completo el uso de QMessageBox intrusivos al ejecutar consultas.
"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QPlainTextEdit, QFrame, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCharFormat, QColor


class SqlTerminalWidget(QWidget):
    """Terminal interactiva de ejecución SQL con registro de consultas, tiempos y errores"""
    def __init__(self, colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Barra superior de la terminal
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        lbl_term = QLabel("💻  Terminal de Salida & Registro de Ejecución")
        lbl_term.setStyleSheet("color: #CBD5E1; font-weight: bold; font-size: 11px;")
        top_bar.addWidget(lbl_term)

        top_bar.addStretch()

        self.btn_copy = QPushButton("📋 Copiar")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setFixedHeight(24)
        self.btn_copy.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #FFFFFF;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 4px;
                padding: 0 8px;
                font-size: 10px;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.btn_copy.clicked.connect(self._copiar_salida)
        top_bar.addWidget(self.btn_copy)

        self.btn_clear = QPushButton("🧹 Limpiar")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setFixedHeight(24)
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #AAB0B8;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 0 8px;
                font-size: 10px;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #FFFFFF;
            }}
        """)
        self.btn_clear.clicked.connect(self.clear)
        top_bar.addWidget(self.btn_clear)

        layout.addLayout(top_bar)

        # Consola de texto estilo terminal
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.output.setFont(font)
        self.output.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: #0D0E15;
                color: #F8FAFC;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 8px;
            }}
            QScrollBar:vertical {{
                background: #0D0E15;
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.output)

        self.log_info("Terminal SQL iniciada. Las consultas ejecutadas se registrarán aquí.")

    def log_query(self, sql: str, duration_ms: float, rows_count: int, is_select: bool, db_name: str = ""):
        """Registra una consulta exitosa indicando la base de datos de destino"""
        now = datetime.now().strftime("%H:%M:%S")
        tipo = f"{rows_count} fila(s) obtenida(s)" if is_select else f"{rows_count} fila(s) afectada(s)"
        target_info = f" [en {db_name}]" if db_name else ""
        msg = (
            f"[{now}] ▶ SQL{target_info}: {sql.strip()}\n"
            f"       ✅ Éxito ({duration_ms} ms) — {tipo}\n"
        )
        self.output.appendPlainText(msg)
        self._scroll_to_bottom()

    def log_error(self, sql: str, error_msg: str, duration_ms: float = 0.0, db_name: str = ""):
        """Registra un error de ejecución sin abrir MessageBox indicando la base de datos"""
        now = datetime.now().strftime("%H:%M:%S")
        target_info = f" [en {db_name}]" if db_name else ""
        msg = (
            f"[{now}] ▶ SQL{target_info}: {sql.strip()}\n"
            f"       ❌ ERROR ({duration_ms} ms): {error_msg}\n"
        )
        self.output.appendPlainText(msg)
        self._scroll_to_bottom()

    def log_info(self, text: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.output.appendPlainText(f"[{now}] ℹ️  {text}\n")
        self._scroll_to_bottom()

    def clear(self):
        self.output.clear()

    def _copiar_salida(self):
        QApplication.clipboard().setText(self.output.toPlainText())

    def _scroll_to_bottom(self):
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())
