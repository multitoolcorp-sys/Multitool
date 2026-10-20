from PyQt6.QtWidgets import QWidget, QHBoxLayout
from .sidebar import CalendarSidebar
from .grid import CalendarGrid
from .dialogs import DetailDialog, FormDialog

class CalendarioGUI(QWidget):
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.inicializar_ui()

    def inicializar_ui(self):
        self.layout_principal = QHBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(0)
        
        # Componentes
        self.sidebar = CalendarSidebar(self, self.colores, self.callbacks)
        self.grid = CalendarGrid(self, self.colores, self.callbacks)
        
        # Ensamblar
        self.layout_principal.addWidget(self.sidebar)
        self.layout_principal.addWidget(self.grid)

    def actualizar_calendario(self, mes_nombre, año, dias_info):
        self.grid.actualizar_calendario(mes_nombre, año, dias_info)

    def actualizar_proximos(self, proximos):
        self.sidebar.actualizar_proximos(proximos)

    def ventana_detalle(self, fecha, recs):
        dialog = DetailDialog(self, fecha, recs, self.colores, self.callbacks)
        dialog.exec()

    def ventana_formulario(self, modo, fecha, r_obj=None):
        dialog = FormDialog(self, modo, fecha, r_obj, self.colores, self.callbacks)
        dialog.exec()

    def actualizar_tema(self, colores):
        self.colores = colores
        if hasattr(self.sidebar, "colores"):
            self.sidebar.colores = colores
        if hasattr(self.grid, "colores"):
            self.grid.colores = colores

