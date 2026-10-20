from PyQt6.QtGui import QTextTableFormat, QTextLength, QTextCursor, QColor, QFont
import platform
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QGridLayout, QFrame, QHBoxLayout, QPushButton, QMessageBox, QWidget, QInputDialog
from PyQt6.QtCore import Qt, pyqtSignal, QSize

class GridCell(QFrame):
    """Celda individual para el selector de cuadrícula con feedback visual premium"""
    hovered = pyqtSignal(int, int)
    clicked = pyqtSignal(int, int)

    def __init__(self, r, c, colores):
        super().__init__()
        self.r, self.c = r, c
        self.colores = colores
        self.setFixedSize(24, 24)
        self.setMouseTracking(True)
        self.set_active(False)

    def set_active(self, active):
        if active:
            bg = self.colores.get('acento', "#4A86E8")
            border = "none"
        else:
            bg = "rgba(255, 255, 255, 0.05)"
            border = "1px solid rgba(255, 255, 255, 0.08)"
        self.setStyleSheet(f"background: {bg}; border: {border}; border-radius: 4px;")

    def enterEvent(self, event):
        self.hovered.emit(self.r, self.c)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.r, self.c)

class TableGridDialog(QDialog):
    """Diálogo selector de tabla con estética Glassmorphism"""
    def __init__(self, parent=None, colores=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.result = None
        self.cells = []
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        
        self.container = QFrame(self)
        self.container.setStyleSheet(f"""
            QFrame {{
                background: {self.colores.get('bg_secundario', '#1E1E1E')};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 15px;
            }}
        """)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        self.lbl_dim = QLabel("Tamaño: 0 x 0")
        self.lbl_dim.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_dim.setStyleSheet(f"color: {self.colores.get('acento', '#4A86E8')};")
        self.lbl_dim.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_dim)
        
        grid_widget = QWidget()
        self.grid_lay = QGridLayout(grid_widget)
        self.grid_lay.setSpacing(4)
        self.grid_lay.setContentsMargins(0, 0, 0, 0)
        
        for r in range(10):
            row_cells = []
            for c in range(10):
                cell = GridCell(r + 1, c + 1, self.colores)
                cell.hovered.connect(self._on_hover)
                cell.clicked.connect(self._on_click)
                self.grid_lay.addWidget(cell, r, c)
                row_cells.append(cell)
            self.cells.append(row_cells)
        
        layout.addWidget(grid_widget)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)
        
    def _on_hover(self, r, c):
        self.lbl_dim.setText(f"Tamaño: {r} x {c}")
        for row_idx, row in enumerate(self.cells):
            for col_idx, cell in enumerate(row):
                cell.set_active(row_idx < r and col_idx < c)

    def _on_click(self, r, c):
        self.result = (r, c)
        self.accept()

class TableManager:
    def __init__(self, editor, colores=None):
        self.editor = editor
        if isinstance(colores, dict):
            self.colores = colores
        else:
            self.colores = {
                "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
                "fg_principal": "#FFFFFF", "acento": "#6366F1"
            }

    def insertar_tabla(self):
        """Abre el selector de cuadrícula estilo Word"""
        dialog = TableGridDialog(self.editor, self.colores)
        from PyQt6.QtGui import QCursor
        dialog.move(QCursor.pos())
        
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result:
            rows, cols = dialog.result
            self._crear_tabla(rows, cols)

    def _crear_tabla(self, rows, cols):
        """Crea e inserta la tabla con configuraciones de estabilidad profesional"""
        cursor = self.editor.textCursor()
        
        table_format = QTextTableFormat()
        table_format.setCellPadding(10)
        table_format.setCellSpacing(0)
        table_format.setBorder(1)
        table_format.setBorderStyle(QTextTableFormat.BorderStyle.BorderStyle_Solid)
        
        border_color = self.colores.get('bg_terciario', "#3D3D4D") if isinstance(self.colores, dict) else "#3D3D4D"
        table_format.setBorderBrush(QColor(border_color))
        
        table_format.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
        
        constraints = []
        col_width = 100.0 / cols
        for _ in range(cols):
            constraints.append(QTextLength(QTextLength.Type.PercentageLength, col_width))
        table_format.setColumnWidthConstraints(constraints)
        
        cursor.insertTable(rows, cols, table_format)
        self.editor.setFocus()

    def agregar_fila(self):
        cursor = self.editor.textCursor()
        table = cursor.currentTable()
        if table:
            cell = table.cellAt(cursor)
            table.insertRows(cell.row() + 1, 1)

    def agregar_columna(self):
        cursor = self.editor.textCursor()
        table = cursor.currentTable()
        if table:
            cell = table.cellAt(cursor)
            table.insertColumns(cell.column() + 1, 1)

    def eliminar_fila(self):
        cursor = self.editor.textCursor()
        table = cursor.currentTable()
        if table:
            cell = table.cellAt(cursor)
            table.removeRows(cell.row(), 1)

    def eliminar_columna(self):
        cursor = self.editor.textCursor()
        table = cursor.currentTable()
        if table:
            cell = table.cellAt(cursor)
            table.removeColumns(cell.column(), 1)
