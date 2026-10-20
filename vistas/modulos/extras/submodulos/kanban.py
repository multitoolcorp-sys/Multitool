import json
import os
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QListWidgetItem, QPushButton, QInputDialog, QMessageBox, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

class KanbanList(QListWidget):
    """Lista especializada para el tablero Kanban con soporte para Drag and Drop y scrollbars personalizados."""
    def __init__(self, title, parent_board, colores, column_color):
        super().__init__()
        self.title = title
        self.parent_board = parent_board
        self.colores = colores
        self.column_color = column_color
        
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setSpacing(8)
        self.setContentsMargins(5, 5, 5, 5)
        
        self.setStyleSheet(f"""
            QListWidget {{
                background: transparent; 
                border: none; 
                outline: none; 
                padding: 5px;
            }}
            QListWidget::item {{
                background: rgba(255, 255, 255, 0.03);
                border-radius: 12px; 
                padding: 16px; 
                margin-bottom: 5px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-left: 4px solid {self.column_color};
                color: {self.colores['fg_principal']};
                font-family: 'Outfit', 'Segoe UI';
            }}
            QListWidget::item:hover {{
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid {self.column_color}44;
                border-left: 4px solid {self.column_color};
            }}
            QListWidget::item:selected {{
                background: {self.column_color}22;
                border: 1.5px solid {self.column_color};
                color: white; 
                font-weight: bold;
            }}
            QScrollBar:vertical {{
                border: none;
                background: rgba(255, 255, 255, 0.02);
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.1);
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 0.2);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

    def dropEvent(self, event):
        super().dropEvent(event)
        QTimer.singleShot(100, self.parent_board.on_list_changed)

class KanbanGUI(QWidget):
    """Gestor visual de tareas estilo Kanban con diseño premium."""
    def __init__(self, parent, context, colores):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        
        # Asegurar directorio notas
        (self.ruta_usuario / "notas").mkdir(parents=True, exist_ok=True)
        self.ruta_kanban = self.ruta_usuario / "notas" / "kanban.json"
        
        self.inicializar_ui()
        self.load_kanban()

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(25)
        
        # --- HEADER ---
        header = QHBoxLayout()
        header.setSpacing(15)
        
        lbl_titulo = QLabel("PROYECTOS Y TAREAS")
        lbl_titulo.setFont(QFont("Outfit", 14, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet(f"color: {self.colores['acento']}; letter-spacing: 1px;")
        header.addWidget(lbl_titulo)
        
        header.addStretch()
        
        btn_nueva = QPushButton("+ NUEVA TAREA")
        btn_nueva.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        btn_nueva.setMinimumHeight(40)
        btn_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nueva.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']}; 
                color: white; 
                padding: 0 20px; 
                border-radius: 10px; 
                border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_nueva.clicked.connect(self.agregar_tarea)
        header.addWidget(btn_nueva)
        
        btn_eliminar = QPushButton("🗑️ ELIMINAR")
        btn_eliminar.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        btn_eliminar.setMinimumHeight(40)
        btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eliminar.setStyleSheet(f"""
            QPushButton {{
                background: rgba(248, 113, 113, 0.1); 
                color: #F87171; 
                border: 1px solid rgba(248, 113, 113, 0.2); 
                border-radius: 10px; 
                padding: 0 20px;
            }}
            QPushButton:hover {{ background: rgba(248, 113, 113, 0.2); }}
        """)
        btn_eliminar.clicked.connect(self.eliminar_tarea)
        header.addWidget(btn_eliminar)
        
        self.main_layout.addLayout(header)
        
        # --- COLUMNAS (Splitter) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(12)
        self.splitter.setStyleSheet("QSplitter::handle { background: transparent; }")
        
        self.list_todo, self.lbl_todo = self._crear_columna("Pendientes", "#F87171") # Rojo pastel
        self.list_doing, self.lbl_doing = self._crear_columna("En Progreso", "#FBBF24") # Ámbar
        self.list_done, self.lbl_done = self._crear_columna("Completadas", "#34D399") # Esmeralda
        
        self.main_layout.addWidget(self.splitter, 1)

    def _crear_columna(self, title, border_color):
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background: rgba(30, 30, 46, 0.45); 
                border-radius: 16px; 
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(15, 20, 15, 20)
        lay.setSpacing(15)
        
        lbl = QLabel(f"{title.upper()} (0)")
        lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {border_color}; background: transparent; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        
        lst = KanbanList(title, self, self.colores, border_color)
        lay.addWidget(lst, 1)
        
        self.splitter.addWidget(container)
        return lst, lbl

    def on_list_changed(self):
        self.save_kanban()
        self.actualizar_contadores()

    def actualizar_contadores(self):
        self.lbl_todo.setText(f"PENDIENTES ({self.list_todo.count()})")
        self.lbl_doing.setText(f"EN PROGRESO ({self.list_doing.count()})")
        self.lbl_done.setText(f"COMPLETADAS ({self.list_done.count()})")

    def agregar_tarea(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Nueva Tarea")
        dialog.setLabelText("Descripción de la tarea:")
        dialog.setStyleSheet(f"""
            QInputDialog {{
                background-color: {self.colores['bg_secundario']};
            }}
            QLabel {{
                color: white;
                font-family: 'Outfit';
                font-size: 12px;
            }}
            QLineEdit {{
                background: {self.colores['bg_terciario']};
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                color: white;
                padding: 6px;
                font-family: 'Outfit';
            }}
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                padding: 6px 15px;
                border-radius: 6px;
                border: none;
                font-family: 'Outfit';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {self.colores['acento_hover']};
            }}
        """)
        ok = dialog.exec()
        text = dialog.textValue()
        if ok and text.strip():
            it = QListWidgetItem(text.strip())
            it.setFont(QFont("Outfit", 10))
            self.list_todo.addItem(it)
            self.save_kanban()
            self.actualizar_contadores()

    def eliminar_tarea(self):
        for lst in [self.list_todo, self.list_doing, self.list_done]:
            items = lst.selectedItems()
            if items:
                msg = QMessageBox(self)
                msg.setWindowTitle("Eliminar Tarea")
                msg.setText(f"¿Deseas eliminar '{items[0].text()}'?")
                msg.setIcon(QMessageBox.Icon.Question)
                btn_yes = msg.addButton("Sí, eliminar", QMessageBox.ButtonRole.YesRole)
                msg.addButton("Cancelar", QMessageBox.ButtonRole.NoRole)
                msg.setStyleSheet(f"""
                    QMessageBox {{
                        background-color: {self.colores['bg_secundario']};
                    }}
                    QLabel {{
                        color: white;
                        font-family: 'Outfit';
                    }}
                    QPushButton {{
                        background: {self.colores['acento']};
                        color: white;
                        padding: 6px 15px;
                        border-radius: 6px;
                        border: none;
                        font-family: 'Outfit';
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background: {self.colores['acento_hover']};
                    }}
                """)
                msg.exec()
                
                if msg.clickedButton() == btn_yes:
                    lst.takeItem(lst.row(items[0]))
                    self.save_kanban()
                    self.actualizar_contadores()
                return

    def save_kanban(self):
        data = {
            "Pendiente": [self.list_todo.item(i).text() for i in range(self.list_todo.count())],
            "EnProgreso": [self.list_doing.item(i).text() for i in range(self.list_doing.count())],
            "Completado": [self.list_done.item(i).text() for i in range(self.list_done.count())]
        }
        try:
            with open(self.ruta_kanban, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except: pass

    def load_kanban(self):
        if not self.ruta_kanban.exists(): return
        try:
            with open(self.ruta_kanban, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for txt in data.get("Pendiente", []): 
                it = QListWidgetItem(txt)
                it.setFont(QFont("Outfit", 10))
                self.list_todo.addItem(it)
            for txt in data.get("EnProgreso", []): 
                it = QListWidgetItem(txt)
                it.setFont(QFont("Outfit", 10))
                self.list_doing.addItem(it)
            for txt in data.get("Completado", []): 
                it = QListWidgetItem(txt)
                it.setFont(QFont("Outfit", 10))
                self.list_done.addItem(it)
            self.actualizar_contadores()
        except: pass

