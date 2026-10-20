import json
import datetime
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QComboBox, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class FinanceTrackerWindow(QWidget):
    """Submódulo premium para el seguimiento de flujos de efectivo personales"""
    def __init__(self, parent, context, colores):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.ruta_tracker = self.ruta_usuario / "finance_tracker.json"
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.setWindowTitle("🎯 Multitool Finance Tracker")
        self.setMinimumSize(850, 600)
        self.setStyleSheet(f"background: {self.colores['bg_principal']}; color: {self.colores['fg_principal']};")
        
        self.init_ui()
        self.cargar_datos()

    def init_ui(self):
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(15, 15, 15, 15)
        self.lay.setSpacing(12)
        
        # --- CABECERA Y BALANCE ---
        header_lay = QHBoxLayout()
        
        title_v = QVBoxLayout()
        lbl_head = QLabel("FINANCE TRACKER")
        lbl_head.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_head.setStyleSheet(f"color: {self.colores['acento']}; ")
        title_v.addWidget(lbl_head)
        
        self.lbl_balance = QLabel("Balance Total: $0.00")
        self.lbl_balance.setFont(QFont(self.font_family, 22, QFont.Weight.Bold))
        title_v.addWidget(self.lbl_balance)
        header_lay.addLayout(title_v)
        
        header_lay.addStretch()
        self.lay.addLayout(header_lay)
        
        # --- FORMULARIO DE ENTRADA ---
        form_card = QFrame()
        form_card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        form_lay = QHBoxLayout(form_card)
        form_lay.setContentsMargins(10, 10, 10, 10)
        form_lay.setSpacing(10)
        
        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItems(["Ingreso", "Gasto"])
        self.cmb_tipo.setMinimumHeight(32)
        self.cmb_tipo.setStyleSheet(self._get_input_style())
        form_lay.addWidget(self.cmb_tipo, 1)
        
        self.txt_monto = QLineEdit()
        self.txt_monto.setPlaceholderText("Monto ($)")
        self.txt_monto.setFont(QFont(self.mono_font, 11))
        self.txt_monto.setMinimumHeight(32)
        self.txt_monto.setStyleSheet(self._get_input_style())
        self.txt_monto.returnPressed.connect(self.agregar_registro)
        form_lay.addWidget(self.txt_monto, 1)
        
        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Descripción o Categoría...")
        self.txt_desc.setMinimumHeight(32)
        self.txt_desc.setStyleSheet(self._get_input_style())
        self.txt_desc.returnPressed.connect(self.agregar_registro)
        form_lay.addWidget(self.txt_desc, 2)
        
        btn_add = QPushButton("REGISTRAR")
        btn_add.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_add.setMinimumHeight(32)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white; border-radius: 8px; padding: 0 20px;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        btn_add.clicked.connect(self.agregar_registro)
        form_lay.addWidget(btn_add, 1)
        
        self.lay.addWidget(form_card)
        
        # --- TABLA DE REGISTROS ---
        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Fecha", "Tipo", "Concepto", "Monto"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setShowGrid(False)
        self.tabla.setFont(QFont(self.font_family, 10))
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 12px;
                padding: 10px;
            }}
            QHeaderView::section {{
                background-color: transparent;
                color: {self.colores['fg_secundario']};
                font-weight: bold;
                border: none;
                padding: 6px;
                text-align: left;
                border-bottom: 2px solid {self.colores['bg_terciario']};
            }}
            QTableWidget::item {{
                padding: 6px;
                border-bottom: 1px solid rgba(255,255,255,0.02);
            }}
            QTableWidget::item:selected {{
                background-color: {self.colores['acento']}22;
                color: white;
            }}
        """)
        self.tabla.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla.customContextMenuRequested.connect(self._mostrar_menu_tabla)
        self.lay.addWidget(self.tabla, 1)
        
        # --- PIE DE PÁGINA ---
        footer_lay = QHBoxLayout()
        btn_del = QPushButton("🗑️ ELIMINAR REGISTRO SELECCIONADO")
        btn_del.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setMinimumHeight(30)
        btn_del.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['error']}22;
                color: {self.colores['error']};
                border: 1px solid {self.colores['error']}44;
                border-radius: 8px; padding: 0 15px;
            }}
            QPushButton:hover {{ background-color: {self.colores['error']}; color: white; }}
        """)
        btn_del.clicked.connect(self.eliminar_registro)
        footer_lay.addStretch()
        footer_lay.addWidget(btn_del)
        self.lay.addLayout(footer_lay)

    def _get_input_style(self):
        return f"""
            QWidget {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: none; border-radius: 8px;
                padding-left: 10px;
            }}
            QComboBox::drop-down {{ border: none; width: 25px; }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
            }}
        """

    def calcular_balance(self):
        balance = 0.0
        for i in range(self.tabla.rowCount()):
            tipo = self.tabla.item(i, 1).text()
            monto_str = self.tabla.item(i, 3).text().replace("$", "").replace(",", "")
            try:
                monto = float(monto_str)
                balance += monto if tipo == "Ingreso" else -monto
            except: continue
        
        self.lbl_balance.setText(f"Balance Total: ${balance:,.2f}")
        color = self.colores['exito'] if balance >= 0 else self.colores['error']
        self.lbl_balance.setStyleSheet(f"color: {color}; font-size: 28px;")

    def agregar_registro(self):
        tipo = self.cmb_tipo.currentText()
        monto_str = self.txt_monto.text().replace(',', '.')
        desc = self.txt_desc.text().strip()
        
        if not monto_str or not desc:
            return QMessageBox.warning(self, "Campos Requeridos", "Debes completar el monto y la descripción.")
            
        try:
            monto = float(monto_str)
        except:
            return QMessageBox.warning(self, "Formato Inválido", "El monto debe ser un número válido.")
            
        row = self.tabla.rowCount()
        self.tabla.insertRow(row)
        
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.tabla.setItem(row, 0, QTableWidgetItem(fecha))
        
        it_tipo = QTableWidgetItem(tipo)
        it_tipo.setForeground(QColor(self.colores['exito'] if tipo == "Ingreso" else self.colores['error']))
        self.tabla.setItem(row, 1, it_tipo)
        self.tabla.setItem(row, 2, QTableWidgetItem(desc))
        self.tabla.setItem(row, 3, QTableWidgetItem(f"${monto:,.2f}"))
        
        self.txt_monto.clear()
        self.txt_desc.clear()
        self.calcular_balance()
        self.guardar_datos()

    def _mostrar_menu_tabla(self, pos):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        action_del = menu.addAction("🗑️ Eliminar Registro Seleccionado")
        action_del.triggered.connect(self.eliminar_registro)
        menu.exec(self.tabla.viewport().mapToGlobal(pos))

    def eliminar_registro(self):
        row = self.tabla.currentRow()
        if row >= 0:
            if QMessageBox.question(self, "Confirmar", "¿Eliminar registro seleccionado?") == QMessageBox.StandardButton.Yes:
                self.tabla.removeRow(row)
                self.calcular_balance()
                self.guardar_datos()

    def guardar_datos(self):
        data = []
        for i in range(self.tabla.rowCount()):
            data.append({
                "fecha": self.tabla.item(i, 0).text(),
                "tipo": self.tabla.item(i, 1).text(),
                "desc": self.tabla.item(i, 2).text(),
                "monto": self.tabla.item(i, 3).text()
            })
        try:
            self.ruta_tracker.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ruta_tracker, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except: pass

    def cargar_datos(self):
        if not self.ruta_tracker.exists(): return
        try:
            with open(self.ruta_tracker, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.tabla.setRowCount(len(data))
            for i, reg in enumerate(data):
                self.tabla.setItem(i, 0, QTableWidgetItem(reg["fecha"]))
                it_tipo = QTableWidgetItem(reg["tipo"])
                it_tipo.setForeground(QColor(self.colores['exito'] if reg["tipo"] == "Ingreso" else self.colores['error']))
                self.tabla.setItem(i, 1, it_tipo)
                self.tabla.setItem(i, 2, QTableWidgetItem(reg["desc"]))
                self.tabla.setItem(i, 3, QTableWidgetItem(reg["monto"]))
            
            self.calcular_balance()
        except: pass

class TabCalculadoraFinanzas(QWidget):
    """Submódulo de pestañas para seguimiento financiero personal integrado"""
    def __init__(self, parent=None, colores=None, add_historial_callback=None, context=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.context = context
        
        # Envolver FinanceTrackerWindow como layout interno
        self.dlg = FinanceTrackerWindow(self, context if context else parent, self.colores)
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.addWidget(self.dlg)

