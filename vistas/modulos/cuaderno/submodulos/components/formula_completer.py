"""
formula_completer.py — Popup de autocompletado flotante para fórmulas matemáticas de Cuaderno estilo Excel.
Muestra funciones disponibles filtradas en tiempo real mientras el usuario escribe '=' y permite completarlas con Enter, Tab o clic.
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QKeyEvent

from ...utils.formula_engine import CATALOGO_FORMULAS


class FormulaCompleterPopup(QFrame):
    """Ventana flotante de autocompletado de fórmulas estilo Excel."""
    
    funcion_seleccionada = pyqtSignal(str)

    def __init__(self, colores, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.colores = colores
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._build_ui()
        self._cargar_items()

    def _hex_to_rgb(self, hex_str):
        hex_str = str(hex_str).lstrip('#')
        if len(hex_str) == 3:
            hex_str = ''.join(c*2 for c in hex_str)
        try:
            return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"
        except Exception:
            return "99, 102, 241"

    def _build_ui(self):
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')
        rgb_acento = self._hex_to_rgb(acento)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid {acento};
                border-radius: 8px;
            }}
        """)
        self.setFixedWidth(280)
        self.setMaximumHeight(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Header sutil
        lbl_hint = QLabel("  ⚡ Fórmulas Disponibles (Tab / Enter)")
        lbl_hint.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_hint.setStyleSheet(f"color: {acento}; border: none; padding: 2px;")
        layout.addWidget(lbl_hint)

        self.list_widget = QListWidget()
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                color: #FFFFFF;
                font-family: Consolas, monospace;
                font-size: 11px;
            }}
            QListWidget::item {{
                padding: 5px 8px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: rgba({rgb_acento}, 0.35);
                color: #FFFFFF;
                font-weight: bold;
            }}
            QListWidget::item:hover:!selected {{
                background-color: rgba(255, 255, 255, 0.05);
            }}
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

    def _cargar_items(self):
        self._todos_los_items = []
        for fn in CATALOGO_FORMULAS:
            if fn["nombre"] != "ARITMÉTICA DIRECTA":
                nombre = fn["nombre"]
                desc = fn.get("descripcion", "")
                self._todos_los_items.append((nombre, desc))

    def filtrar(self, texto_busqueda: str, line_edit):
        """Filtra los items según el texto ingresado tras el '=' o separador."""
        txt = texto_busqueda.strip().upper()
        # Extraer el token de función en edición
        if txt.startswith("="):
            txt = txt[1:]
        
        # Obtener último token tras operadores (+, -, *, /, (, ,)
        for sep in ['+', '-', '*', '/', '(', ',', ';']:
            if sep in txt:
                txt = txt.split(sep)[-1]
        txt = txt.strip()

        self.list_widget.clear()
        if not txt:
            # Mostrar todas
            for nombre, desc in self._todos_los_items:
                item = QListWidgetItem(f"{nombre}  ({desc[:25]}...)")
                item.setData(Qt.ItemDataRole.UserRole, f"{nombre}(")
                self.list_widget.addItem(item)
        else:
            for nombre, desc in self._todos_los_items:
                if nombre.startswith(txt) or txt in nombre:
                    item = QListWidgetItem(f"{nombre}  ({desc[:25]}...)")
                    item.setData(Qt.ItemDataRole.UserRole, f"{nombre}(")
                    self.list_widget.addItem(item)

        if self.list_widget.count() == 0:
            self.hide()
            return False

        self.list_widget.setCurrentRow(0)
        self._posicionar_debajo_de(line_edit)
        self.show()
        line_edit.setFocus()
        return True

    def _posicionar_debajo_de(self, widget):
        pos_global = widget.mapToGlobal(QPoint(0, widget.height() + 2))
        self.move(pos_global)

    def seleccionar_actual(self):
        it = self.list_widget.currentItem()
        if it:
            fn_call = it.data(Qt.ItemDataRole.UserRole)
            self.funcion_seleccionada.emit(fn_call)
            self.hide()
            return True
        return False

    def navegar(self, direccion):
        """Permite mover la selección hacia arriba (-1) o abajo (1)."""
        cur = self.list_widget.currentRow()
        count = self.list_widget.count()
        if count == 0:
            return
        nuevo = max(0, min(count - 1, cur + direccion))
        self.list_widget.setCurrentRow(nuevo)

    def _on_item_clicked(self, item):
        fn_call = item.data(Qt.ItemDataRole.UserRole)
        self.funcion_seleccionada.emit(fn_call)
        self.hide()
