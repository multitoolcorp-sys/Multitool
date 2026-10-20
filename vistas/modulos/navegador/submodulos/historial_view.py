import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QTreeWidget, QTreeWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication

class TabNavegadorHistorial(QWidget):
    """Submódulo visual para explorar, buscar y gestionar el historial de navegación"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Header y Buscador
        top_bar = QHBoxLayout()
        lbl_title = QLabel("📜 HISTORIAL DE NAVEGACIÓN")
        lbl_title.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        acento = self.colores.get('acento', '#6366F1')
        lbl_title.setStyleSheet(f"color: {acento};")
        top_bar.addWidget(lbl_title)

        top_bar.addStretch()

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar en el historial...")
        self.txt_buscar.setFixedWidth(250)
        self.txt_buscar.setFixedHeight(32)
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        self.txt_buscar.setStyleSheet(f"""
            QLineEdit {{
                background: {bg_sec};
                color: white; border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px; padding: 4px 10px; font-size: 11px;
            }}
            QLineEdit:focus {{ border: 1px solid {acento}; }}
        """)
        self.txt_buscar.textChanged.connect(self._filtrar_historial)
        top_bar.addWidget(self.txt_buscar)

        layout.addLayout(top_bar)

        # Árbol/Lista de Historial
        self.tree_historial = QTreeWidget()
        self.tree_historial.setColumnCount(3)
        self.tree_historial.setHeaderLabels(["Sitio / Título", "Dirección URL", "Fecha / Hora"])
        self.tree_historial.setIndentation(15)
        self.tree_historial.setAnimated(True)
        self.tree_historial.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tree_historial.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree_historial.header().resizeSection(0, 200)
        self.tree_historial.header().resizeSection(2, 140)

        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')
        fg_sec = self.colores.get('fg_secundario', '#AAB0B8')
        self.tree_historial.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {bg_sec};
                color: {fg_sec};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 8px;
                border-bottom: 1px solid rgba(255,255,255,0.02);
            }}
            QTreeWidget::item:hover {{
                background-color: rgba(255,255,255,0.03);
                color: white;
            }}
            QTreeWidget::item:selected {{
                background-color: {acento}22;
                color: {acento};
            }}
            QHeaderView::section {{
                background-color: {bg_ter};
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }}
        """)

        self.tree_historial.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree_historial, 1)

        # Botones de Acción inferiores (Compactos)
        actions_lay = QHBoxLayout()
        actions_lay.setSpacing(8)

        btn_abrir = QPushButton("🚀 Abrir")
        btn_copiar = QPushButton("📋 Copiar URL")
        btn_limpiar = QPushButton("🗑️ Limpiar Historial")

        btns_config = [
            (btn_abrir, acento, self._abrir_seleccionado),
            (btn_copiar, bg_ter, self._copiar_url),
            (btn_limpiar, self.colores.get('error', '#EF4444'), self._limpiar_todo)
        ]

        for b, col, handler in btns_config:
            b.setFont(QFont("Inter", 8, QFont.Weight.Bold))
            b.setFixedHeight(32)
            b.setMinimumWidth(110)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{ background: {col}; color: white; border-radius: 8px; padding: 4px 12px; }}
                QPushButton:hover {{ background-color: {col}CC; }}
            """)
            b.clicked.connect(handler)
            actions_lay.addWidget(b)

        actions_lay.addStretch()
        layout.addLayout(actions_lay)

    def _filtrar_historial(self, texto):
        texto = texto.lower().strip()
        for i in range(self.tree_historial.topLevelItemCount()):
            item = self.tree_historial.topLevelItem(i)
            match = texto in item.text(0).lower() or texto in item.text(1).lower()
            item.setHidden(not match)

    def _on_item_double_clicked(self, item, column):
        self._abrir_seleccionado()

    def _abrir_seleccionado(self):
        item = self.tree_historial.currentItem()
        if not item: return
        url = item.text(1)
        if url and hasattr(self.callbacks, '__getitem__') and "abrir_url_integrada" in self.callbacks:
            self.callbacks["abrir_url_integrada"](url)

    def _copiar_url(self):
        item = self.tree_historial.currentItem()
        if not item: return
        url = item.text(1)
        if url:
            QGuiApplication.clipboard().setText(url)
            if "mostrar_notificacion" in self.callbacks:
                self.callbacks["mostrar_notificacion"]("URL copiada al portapapeles")

    def _limpiar_todo(self):
        if QMessageBox.question(self, "Limpiar Historial", "¿Deseas borrar todo el historial de navegación?") == QMessageBox.StandardButton.Yes:
            if "limpiar_historial" in self.callbacks:
                self.callbacks["limpiar_historial"]()
            self.tree_historial.clear()
