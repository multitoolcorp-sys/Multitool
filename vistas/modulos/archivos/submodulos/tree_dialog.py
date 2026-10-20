import os
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class FolderTreeDialog(QDialog):
    """Diálogo interactivo para navegar por la estructura de carpetas del sistema"""
    def __init__(self, parent, colores, current_path):
        super().__init__(parent)
        self.colores = colores
        self.current_path = Path(current_path)
        self.selected_path = None
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.setWindowTitle("Navegador de Directorios")
        self.setFixedSize(400, 520)
        self.setStyleSheet(f"background: {colores['bg_principal']}; border: none;")
        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        title = QLabel("📂 SELECCIONAR CARPETA")
        title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colores['acento']}; ")
        layout.addWidget(title)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setFont(QFont(self.font_family, 10))
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
                border-radius: 8px;
                padding: 4px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            QTreeWidget::item {{ padding: 4px; border-radius: 4px; }}
            QTreeWidget::item:selected {{ background: {self.colores['acento']}33; color: {self.colores['acento']}; }}
        """)
        
        self.popular_unidades()
        
        self.tree.itemExpanded.connect(self.al_expandir)
        layout.addWidget(self.tree)

        # Botones de acción
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch()
        
        btn_cancel = QPushButton("CANCELAR")
        btn_cancel.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(f"color: {self.colores['fg_secundario']}; background: transparent; padding: 8px 15px;")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        btn_go = QPushButton("SELECCIONAR ESTA CARPETA")
        btn_go.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_go.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_go.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']}; 
                color: white; 
                padding: 8px 18px; 
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_go.clicked.connect(self.ir_a_seleccionado)
        btn_box.addWidget(btn_go)
        
        layout.addLayout(btn_box)

    def popular_unidades(self):
        """Detecta automáticamente unidades en Windows o raíces en Unix"""
        if platform.system() == "Windows":
            try:
                import ctypes
                bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                for i in range(26):
                    if bitmask & (1 << i):
                        drive = f"{chr(65 + i)}:\\"
                        if os.path.exists(drive):
                            root = self.crear_item(self.tree, f"💻 Disco Local ({drive})", drive)
                            self.crear_item(root, "Cargando...", "")
            except:
                # Fallback a C: si falla la API
                root = self.crear_item(self.tree, "💻 Disco Local (C:)", "C:\\")
                self.crear_item(root, "Cargando...", "")
        else:
            # Unix/Linux/Mac
            root = self.crear_item(self.tree, "💻 Raíz (System)", "/")
            self.crear_item(root, "Cargando...", "")
            
            # También añadir Home directamente por comodidad
            home = str(Path.home())
            h_node = self.crear_item(self.tree, "🏠 Carpeta Personal (Home)", home)
            self.crear_item(h_node, "Cargando...", "")

    def crear_item(self, parent, texto, ruta):
        item = QTreeWidgetItem(parent)
        item.setText(0, texto)
        item.setData(0, Qt.ItemDataRole.UserRole, ruta)
        return item

    def al_expandir(self, item):
        ruta = item.data(0, Qt.ItemDataRole.UserRole)
        if not ruta: return
        
        item.takeChildren()
        
        try:
            path = Path(ruta)
            # Solo iterar directorios
            dirs = [e for e in path.iterdir() if e.is_dir() and not e.name.startswith('.')]
            dirs.sort(key=lambda x: x.name.lower())
            
            for entry in dirs:
                node = self.crear_item(item, f"📁 {entry.name}", str(entry))
                # Intentar ver si tiene subdirectorios para añadir la flecha de expansión
                try:
                    if any(e.is_dir() for e in entry.iterdir()):
                        self.crear_item(node, "Cargando...", "")
                except:
                    pass
        except PermissionError:
            self.crear_item(item, "🚫 Sin acceso", "")
        except Exception:
            pass

    def ir_a_seleccionado(self):
        sel = self.tree.selectedItems()
        if sel:
            path = sel[0].data(0, Qt.ItemDataRole.UserRole)
            if path:
                self.selected_path = path
                self.accept()

