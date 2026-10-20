import platform
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtGui import QFont

from .pizarra import PizarraGUI

class KanbanPizarraSubmodule(QWidget):
    """Submódulo de Productividad: Pizarra Interactiva (Kanban eliminado por redundancia)"""
    def __init__(self, parent, context, colores):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Solo Pizarra Interactiva
        self.pizarra = PizarraGUI(self, self.context, self.colores)
        layout.addWidget(self.pizarra)
