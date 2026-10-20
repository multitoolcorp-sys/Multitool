import platform
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, 
    QPushButton, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class HistorySearchDialog(QDialog):
    """Diálogo de Búsqueda Inversa del Historial de Comandos (Estilo Ctrl+R)"""
    def __init__(self, parent, history_list, colores):
        super().__init__(parent)
        self.history_list = history_list
        self.colores = colores
        self.selected_command = None
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.setWindowTitle("📜 Búsqueda en Historial (Ctrl+R)")
        self.resize(500, 350)
        self.inicializar_ui()

    def inicializar_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores['bg_secundario']};
                color: white;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header
        lbl = QLabel("🔍 Buscar en Comandos Pasados:")
        lbl.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl.setStyleSheet("color: white;")
        layout.addWidget(lbl)

        # Campo de entrada
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Escribe para filtrar el historial...")
        self.txt_search.setFont(QFont("Consolas" if platform.system() == "Windows" else "Monospace", 10))
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores['bg_terciario']};
                color: white; padding: 6px 10px;
                border: 1px solid {self.colores['acento']};
                border-radius: 6px;
            }}
        """)
        self.txt_search.textChanged.connect(self._filtrar_historial)
        layout.addWidget(self.txt_search)

        # Lista de resultados
        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont("Consolas" if platform.system() == "Windows" else "Monospace", 9))
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.colores['bg_principal']};
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 6px;
            }}
            QListWidget::item {{
                color: #FFFFFF;
                padding: 6px 8px;
                border-bottom: 1px solid rgba(255,255,255,0.02);
            }}
            QListWidget::item:selected {{
                background-color: {self.colores['acento']};
                color: #FFFFFF;
            }}
        """)
        self.list_widget.itemDoubleClicked.connect(self._on_item_selected)
        layout.addWidget(self.list_widget)

        # Botones inferiores
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFont(QFont(self.font_family, 9))
        btn_cancel.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; padding: 6px 15px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        btn_lay.addWidget(btn_cancel)

        btn_ok = QPushButton("⚡ Ejecutar Comando")
        btn_ok.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_ok.setStyleSheet(f"background: {self.colores['acento']}; color: white; padding: 6px 15px; border-radius: 6px;")
        btn_ok.clicked.connect(self._aceptar_seleccion)
        btn_lay.addWidget(btn_ok)

        layout.addLayout(btn_lay)

        # Cargar lista inicial (en orden inverso, más recientes primero)
        self._cargar_lista(list(reversed(self.history_list)))
        self.txt_search.setFocus()

    def _cargar_lista(self, items):
        self.list_widget.clear()
        vistos = set()
        for cmd in items:
            cmd_clean = cmd.strip()
            if cmd_clean and cmd_clean not in vistos:
                vistos.add(cmd_clean)
                self.list_widget.addItem(cmd_clean)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _filtrar_historial(self, text):
        query = text.strip().lower()
        if not query:
            self._cargar_lista(list(reversed(self.history_list)))
            return
        
        filtrados = [cmd for cmd in reversed(self.history_list) if query in cmd.lower()]
        self._cargar_lista(filtrados)

    def _aceptar_seleccion(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_command = item.text()
            self.accept()
        else:
            self.reject()

    def _on_item_selected(self, item):
        self.selected_command = item.text()
        self.accept()
