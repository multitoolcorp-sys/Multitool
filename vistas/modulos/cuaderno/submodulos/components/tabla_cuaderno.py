from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMenu, QColorDialog, QApplication, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QKeySequence, QAction, QFont

from vistas.modulos.cuaderno.utils.formula_engine import (
    FormulaEngine, index_to_col_name, col_name_to_index
)

class TablaCuaderno(QTableWidget):
    """Hoja de cálculo estilo Excel con soporte para celdas dinámicas, fórmulas y formato."""
    
    cambio_datos = pyqtSignal()

    def __init__(self, colores, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.undo_stack = []
        self.redo_stack = []
        self._ignorar_cambios = False
        self._configurar_basico()

    def _hex_to_rgb(self, hex_str):
        hex_str = hex_str.lstrip('#')
        if len(hex_str) == 3:
            hex_str = ''.join(c*2 for c in hex_str)
        return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"

    def _configurar_basico(self):
        # 20 filas y 10 columnas por defecto (estilo Cuaderno)
        self.setRowCount(20)
        self.setColumnCount(12)
        self.setHorizontalHeaderLabels([chr(65+i) if i < 26 else f"Col {i}" for i in range(12)])
        
        # Configurar paleta para asegurar letras blancas en edición y celdas
        palette = self.palette()
        palette.setColor(palette.ColorGroup.Active, palette.ColorRole.Text, QColor("#ffffff"))
        palette.setColor(palette.ColorGroup.Inactive, palette.ColorRole.Text, QColor("#ffffff"))
        palette.setColor(palette.ColorGroup.Active, palette.ColorRole.WindowText, QColor("#ffffff"))
        palette.setColor(palette.ColorGroup.Inactive, palette.ColorRole.WindowText, QColor("#ffffff"))
        palette.setColor(palette.ColorGroup.Active, palette.ColorRole.Base, QColor("#1e1e2e"))
        palette.setColor(palette.ColorGroup.Inactive, palette.ColorRole.Base, QColor("#1e1e2e"))
        self.setPalette(palette)
        
        # Configurar prototipo de ítem con texto blanco por defecto
        proto = QTableWidgetItem()
        proto.setForeground(QBrush(QColor("#ffffff")))
        self.setItemPrototype(proto)
        
        self.setStyleSheet(self._obtener_hoja_estilos("cuadricula"))

        self._actualizar_modos_redimensionado()
        
        hdr_v = self.verticalHeader()
        hdr_v.setVisible(True)
        hdr_v.setMinimumSectionSize(30)
        hdr_v.setDefaultSectionSize(40)

        self.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item):
        if self._ignorar_cambios:
            return
        
        self.redo_stack.clear()
        raw_text = item.text().strip()
        
        # Evaluar fórmula si el texto empieza con '='
        if FormulaEngine.is_formula(raw_text):
            item.setData(Qt.ItemDataRole.UserRole, raw_text)
            item.setToolTip(f"Fórmula: {raw_text}")
            evaluated = FormulaEngine.evaluate(raw_text, self, current_cell=(item.row(), item.column()))
            self._ignorar_cambios = True
            item.setText(evaluated)
            self._ignorar_cambios = False
        elif not raw_text.startswith("="):
            # Si se sobrescribió con texto normal y no es fórmula, limpiar fórmula previa
            item.setData(Qt.ItemDataRole.UserRole, None)
            item.setToolTip("")

        # Recalcular otras fórmulas dependientes en la tabla
        self.recalcular_formulas(exclude=item)
        self.cambio_datos.emit()

    def recalcular_formulas(self, exclude=None):
        """Recalcula todas las celdas que contienen fórmulas."""
        if self._ignorar_cambios:
            return
        self._ignorar_cambios = True
        try:
            for r in range(self.rowCount()):
                for c in range(self.columnCount()):
                    it = self.item(r, c)
                    if it and it != exclude:
                        formula = it.data(Qt.ItemDataRole.UserRole)
                        if formula and str(formula).startswith("="):
                            res = FormulaEngine.evaluate(str(formula), self, current_cell=(r, c))
                            if it.text() != res:
                                it.setText(res)
        finally:
            self._ignorar_cambios = False

    def obtener_formula_celda(self, r, c):
        """Retorna la fórmula de la celda o su texto visible."""
        it = self.item(r, c)
        if not it:
            return ""
        formula = it.data(Qt.ItemDataRole.UserRole)
        return str(formula) if formula else it.text()

    def asignar_formula_celda(self, r, c, val):
        """Asigna una fórmula o texto a la celda indicada y ejecuta el cálculo."""
        if r < 0 or c < 0:
            return
        self._guardar_snapshot()
        it = self.item(r, c)
        if not it:
            it = QTableWidgetItem("")
            it.setForeground(QBrush(QColor("#ffffff")))
            self.setItem(r, c, it)
        it.setText(val)

    def sumar_columna_actual(self):
        """Inserta automáticamente la fórmula de autosuma =SUMA(...) en la celda activa."""
        r = self.currentRow()
        c = self.currentColumn()
        if r < 0 or c < 0:
            return
        col_letter = index_to_col_name(c)
        if r == 0:
            formula = f"=SUMA({col_letter}2:{col_letter}10)"
        else:
            formula = f"=SUMA({col_letter}1:{col_letter}{r})"
        self.asignar_formula_celda(r, c, formula)

    def _guardar_snapshot(self):
        snapshot = self._crear_snapshot()
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > 50: self.undo_stack.pop(0)

    def _crear_snapshot(self):
        estado = {
            "rows": self.rowCount(),
            "cols": self.columnCount(),
            "headers": [self.horizontalHeaderItem(i).text() if self.horizontalHeaderItem(i) else f"Col {i}" for i in range(self.columnCount())],
            "items": []
        }
        for r in range(self.rowCount()):
            row_data = []
            for c in range(self.columnCount()):
                it = self.item(r, c)
                if it:
                    bg = None
                    if it.background().style() != Qt.BrushStyle.NoBrush:
                        bg_color = it.background().color()
                        if bg_color.isValid() and bg_color.alpha() > 0: bg = bg_color.name()
                    
                    fg = it.foreground().color().name() if it.foreground().color().isValid() else None
                    align_val = int(it.textAlignment().value) if hasattr(it.textAlignment(), 'value') else int(it.textAlignment())
                    formula = it.data(Qt.ItemDataRole.UserRole)
                    row_data.append({
                        "text": it.text(),
                        "formula": str(formula) if formula else None,
                        "bg": bg, "fg": fg,
                        "font_size": it.font().pointSize(), "bold": it.font().bold(),
                        "italic": it.font().italic(), "align": align_val
                    })
                else: row_data.append(None)
            estado["items"].append(row_data)
        return estado

    def _restaurar_snapshot(self, snapshot):
        self._ignorar_cambios = True
        self.blockSignals(True)
        self.clear() 
        self.setColumnCount(snapshot["cols"])
        self.setRowCount(snapshot["rows"])
        self.setHorizontalHeaderLabels(snapshot["headers"])
        self._actualizar_modos_redimensionado()

        for r, row_data in enumerate(snapshot["items"]):
            for c, it_data in enumerate(row_data):
                if it_data:
                    it = QTableWidgetItem(it_data["text"])
                    if it_data.get("formula"):
                        it.setData(Qt.ItemDataRole.UserRole, it_data["formula"])
                        it.setToolTip(f"Fórmula: {it_data['formula']}")
                    if it_data["bg"]: it.setBackground(QBrush(QColor(it_data["bg"])))
                    if it_data["fg"]: 
                        it.setForeground(QBrush(QColor(it_data["fg"])))
                    else:
                        it.setForeground(QBrush(QColor("#ffffff")))
                    font = it.font()
                    font.setPointSize(it_data["font_size"])
                    font.setBold(it_data["bold"])
                    font.setItalic(it_data["italic"])
                    font.setItalic(it_data["italic"])
                    it.setFont(font)
                    it.setTextAlignment(Qt.AlignmentFlag(it_data["align"]))
                    self.setItem(r, c, it)
                else:
                    it = QTableWidgetItem("")
                    it.setForeground(QBrush(QColor("#ffffff")))
                    self.setItem(r, c, it)
        
        self.blockSignals(False)
        self._ignorar_cambios = False
        self.recalcular_formulas()
        self.cambio_datos.emit()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self._crear_snapshot())
            self._restaurar_snapshot(self.undo_stack.pop())

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self._crear_snapshot())
            self._restaurar_snapshot(self.redo_stack.pop())

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste): self._pegar_portapapeles()
        elif event.matches(QKeySequence.StandardKey.Undo): self.undo()
        elif event.matches(QKeySequence.StandardKey.Redo): self.redo()
        elif event.key() == Qt.Key.Key_Delete: self._limpiar_seleccion()
        else: super().keyPressEvent(event)

    def _pegar_portapapeles(self):
        import re
        mime = QApplication.clipboard().mimeData()
        self._guardar_snapshot()
        row_start = max(0, self.currentRow())
        col_start = max(0, self.currentColumn())
        self.blockSignals(True)
        if mime.hasHtml():
            # Pegar con formato
            self._pegar_texto_plano(mime.text(), row_start, col_start) # Simplificado por ahora
        else:
            self._pegar_texto_plano(mime.text(), row_start, col_start)
        self.blockSignals(False)
        self.cambio_datos.emit()

    def _pegar_texto_plano(self, text, row_start, col_start):
        if not text: return
        lines = text.strip().split("\n")
        if row_start + len(lines) > self.rowCount(): self.setRowCount(row_start + len(lines))
        for r_offset, line in enumerate(lines):
            cells = line.split("\t")
            if col_start + len(cells) > self.columnCount(): self.setColumnCount(col_start + len(cells))
            for c_offset, content in enumerate(cells):
                r = row_start + r_offset
                c = col_start + c_offset
                it = QTableWidgetItem(content.strip())
                it.setForeground(QBrush(QColor("#ffffff")))
                self.setItem(r, c, it)
        self.cambio_datos.emit()

    def aplicar_formateo(self, t="bold", val=None):
        self._guardar_snapshot()
        ranges = self.selectedRanges()
        if not ranges: return
        for r_range in ranges:
            for r in range(r_range.topRow(), r_range.bottomRow() + 1):
                for c in range(r_range.leftColumn(), r_range.rightColumn() + 1):
                    it = self.item(r, c)
                    if not it:
                        it = QTableWidgetItem("")
                        it.setForeground(QBrush(QColor("#ffffff")))
                        self.setItem(r, c, it)
                    font = it.font()
                    if t == "bold": font.setBold(not font.bold() if val is None else val)
                    elif t == "italic": font.setItalic(not font.italic() if val is None else val)
                    elif t == "size": font.setPointSize(int(val))
                    elif t == "fg": it.setForeground(QBrush(QColor(val)))
                    elif t == "bg": it.setBackground(QBrush(QColor(val)))
                    elif t == "align":
                        if val == "left":
                            it.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                        elif val == "center":
                            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        elif val == "right":
                            it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    elif t == "currency":
                        txt = it.text().strip().replace('$', '').replace(',', '')
                        try:
                            val_num = float(txt)
                            it.setText(f"${val_num:,.2f}")
                        except ValueError:
                            pass
                    elif t == "percent":
                        txt = it.text().strip().replace('%', '')
                        try:
                            val_num = float(txt)
                            it.setText(f"{val_num:.1f}%")
                        except ValueError:
                            pass
                    it.setFont(font)
        self.cambio_datos.emit()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("➕ Insertar fila", self._insertar_fila)
        menu.addAction("🗑 Eliminar fila", self._eliminar_fila)
        menu.addSeparator()
        menu.addAction("➕ Insertar columna", self._insertar_columna)
        menu.addAction("🗑 Eliminar columna", self._eliminar_columna)
        menu.exec(event.globalPos())

    def _insertar_fila(self):
        self._guardar_snapshot()
        idx = self.currentRow()
        row = idx + 1 if idx >= 0 else self.rowCount()
        self.insertRow(row)
        for c in range(self.columnCount()):
            it = QTableWidgetItem("")
            it.setForeground(QBrush(QColor("#ffffff")))
            self.setItem(row, c, it)
        self.cambio_datos.emit()

    def _eliminar_fila(self):
        row = self.currentRow()
        if row >= 0:
            self._guardar_snapshot()
            self.removeRow(row)
            self.cambio_datos.emit()

    def _insertar_columna(self):
        self._guardar_snapshot()
        idx = self.currentColumn()
        col = idx + 1 if idx >= 0 else self.columnCount()
        self.insertColumn(col)
        self.setHorizontalHeaderItem(col, QTableWidgetItem(f"Col {col}"))
        self._actualizar_modos_redimensionado()
        for r in range(self.rowCount()):
            it = QTableWidgetItem("")
            it.setForeground(QBrush(QColor("#ffffff")))
            self.setItem(r, col, it)
        self.cambio_datos.emit()

    def _eliminar_columna(self):
        col = self.currentColumn()
        if col >= 0 and self.columnCount() > 1:
            self._guardar_snapshot()
            self.removeColumn(col)
            self._actualizar_modos_redimensionado()
            self.cambio_datos.emit()

    def _actualizar_modos_redimensionado(self):
        hdr = self.horizontalHeader()
        for i in range(self.columnCount()): hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

    def _limpiar_seleccion(self):
        self._guardar_snapshot()
        for it in self.selectedItems():
            it.setText("")
            it.setBackground(QBrush(Qt.GlobalColor.transparent))
        self.cambio_datos.emit()

    def cargar_datos_tabla(self, actividades, horas=None, headers=None):
        self._ignorar_cambios = True
        self.blockSignals(True)
        self.clear()
        if headers:
            self.setColumnCount(len(headers))
            self.setHorizontalHeaderLabels(headers)
        self.setRowCount(20)
        self.blockSignals(False)
        self._ignorar_cambios = False

    def _obtener_hoja_estilos(self, modo_rejilla=None):
        if modo_rejilla is None:
            modo_rejilla = getattr(self, "_modo_rejilla_actual", "cuadricula")
        self._modo_rejilla_actual = modo_rejilla

        acento = self.colores.get('acento', '#6366F1')
        rgb_acento = self._hex_to_rgb(acento)
        fg_sec = self.colores.get('fg_secundario', '#AAB0B8')
        bg_header = "rgba(40, 40, 56, 0.98)"

        if modo_rejilla == "lineas":
            gridline_color = f"rgba({rgb_acento}, 0.35)"
        elif modo_rejilla == "sin_rejilla":
            gridline_color = "transparent"
        else:
            gridline_color = "rgba(255, 255, 255, 0.08)"

        return f"""
            QTableWidget {{
                background: rgba(30, 30, 46, 0.35);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                gridline-color: {gridline_color};
                color: #ffffff;
                selection-background-color: rgba({rgb_acento}, 0.2);
                selection-color: white;
            }}
            QTableWidget QLineEdit {{
                color: #ffffff;
                background-color: #2d2d3d;
                border: 1px solid rgba(255,255,255,0.2);
            }}
            QHeaderView::section {{
                background-color: {bg_header};
                color: {fg_sec};
                padding: 6px 8px;
                font-weight: bold;
                font-size: 11px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.12);
                border-right: 1px solid rgba(255, 255, 255, 0.12);
            }}
            QHeaderView::section:vertical {{
                background-color: {bg_header};
                color: {fg_sec};
                padding: 4px;
                font-weight: bold;
                font-size: 10px;
                border: none;
                border-right: 1px solid rgba(255, 255, 255, 0.12);
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }}
            QScrollBar:vertical {{
                border: none;
                background: rgba(30, 30, 46, 0.2);
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.15);
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {acento};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar:horizontal {{
                border: none;
                background: rgba(30, 30, 46, 0.2);
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: rgba(255, 255, 255, 0.15);
                min-width: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {acento};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
            }}
        """

    def cambiar_estilo_rejilla(self, modo):
        """
        Cambia el estilo visual de las líneas de cuadrícula de la tabla.
        modo: 'cuadricula' | 'lineas' | 'sin_rejilla'
        """
        self.setShowGrid(modo != "sin_rejilla")
        self.setStyleSheet(self._obtener_hoja_estilos(modo))

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(self._obtener_hoja_estilos())
