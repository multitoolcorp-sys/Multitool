import os
import json
import subprocess
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QFrame, QMessageBox, 
    QLineEdit, QInputDialog, QFileIconProvider, QScrollArea,
    QGridLayout
)
from PyQt6.QtCore import Qt, QSize, QFileInfo
from PyQt6.QtGui import QFont, QIcon, QPixmap

class AppCard(QFrame):
    """Tarjeta individual de aplicación en el lanzador con diseño glassmorphic y efectos hover."""
    def __init__(self, parent, app_data, colores, on_launch, on_delete):
        super().__init__(parent)
        self.app_data = app_data
        self.colores = colores
        self.on_launch = on_launch
        self.on_delete = on_delete
        
        self.setFixedSize(140, 150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        ruta = self.app_data.get('ruta', '')
        self.exists = os.path.exists(ruta)
        
        color_text = self.colores['fg_principal'] if self.exists else self.colores['fg_secundario']
        border_color_hover = self.colores['acento'] if self.exists else self.colores['error']
        
        self.normal_style = f"""
            QFrame {{
                background: rgba(255, 255, 255, {0.02 if self.exists else 0.01});
                border: 1px solid rgba(255, 255, 255, {0.05 if self.exists else 0.02});
                border-radius: 16px;
            }}
        """
        self.hover_style = f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.06);
                border: 1.5px solid {border_color_hover};
                border-radius: 16px;
            }}
        """
        self.setStyleSheet(self.normal_style)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        
        # Header bar in card (Delete button)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addStretch()
        
        self.btn_del = QPushButton("×")
        self.btn_del.setFixedSize(20, 20)
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.setToolTip("Eliminar acceso directo")
        self.btn_del.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores['fg_secundario']};
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                color: white;
                background: {self.colores['error']};
            }}
        """)
        self.btn_del.clicked.connect(self.delete_clicked)
        self.btn_del.hide()
        header.addWidget(self.btn_del)
        layout.addLayout(header)
        
        # Icon
        self.lbl_icon = QLabel()
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        self.lbl_icon.setFixedSize(56, 56)
        
        provider = QFileIconProvider()
        if self.exists:
            info = QFileInfo(ruta)
            icon = provider.icon(info)
            pixmap = icon.pixmap(48, 48)
            self.lbl_icon.setPixmap(pixmap)
        else:
            self.lbl_icon.setText("❓")
            self.lbl_icon.setStyleSheet(f"color: {self.colores['error']}; background: transparent; border: none; font-size: 32px; font-weight: bold;")
            self.setToolTip(f"Ruta no encontrada:\n{ruta}")
            
        layout.addWidget(self.lbl_icon, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Name
        self.lbl_name = QLabel(self.app_data.get('nombre', 'Sin Nombre'))
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setWordWrap(True)
        self.lbl_name.setFont(QFont("Outfit", 9, QFont.Weight.Medium))
        self.lbl_name.setStyleSheet(f"color: {color_text}; background: transparent; border: none;")
        if self.exists:
            self.lbl_name.setToolTip(ruta)
        layout.addWidget(self.lbl_name)
        
        layout.addStretch()
        
    def enterEvent(self, event):
        self.setStyleSheet(self.hover_style)
        self.btn_del.show()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.setStyleSheet(self.normal_style)
        self.btn_del.hide()
        super().leaveEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_launch(self.app_data)
        super().mouseDoubleClickEvent(event)

    def delete_clicked(self):
        self.on_delete(self.app_data)


class LauncherGUI(QWidget):
    """Submódulo de Lanzador de Aplicaciones Personalizado con diseño moderno y responsivo."""
    def __init__(self, parent, colores, ruta_usuario):
        super().__init__(parent)
        self.colores = colores
        self.ruta_data = Path(ruta_usuario) / "launcher_apps.json"
        self.apps = self.cargar_datos()
        
        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 30, 30, 30)
        lay.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        lbl_tit = QLabel("🚀 Lanzador de Aplicaciones")
        lbl_tit.setFont(QFont("Outfit", 16, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['fg_principal']};")
        header.addWidget(lbl_tit)
        
        btn_add = QPushButton("+ Agregar App")
        btn_add.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background: {self.colores['acento_hover']};
            }}
        """)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self.agregar_app)
        header.addWidget(btn_add)
        lay.addLayout(header)
        
        # Filtro de búsqueda
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar aplicación por nombre...")
        self.search_input.setFont(QFont("Outfit", 10))
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colores['acento']};
            }}
        """)
        self.search_input.textChanged.connect(self._refresh_list)
        lay.addWidget(self.search_input)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
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
        
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(0, 10, 0, 10)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll.setWidget(self.grid_container)
        lay.addWidget(self.scroll, 1)
        
        # Panel inferior de Ayuda
        footer = QLabel("Haz doble clic en una aplicación para lanzarla. Pasa el cursor por encima para ver la ruta o eliminarla.")
        footer.setFont(QFont("Outfit", 9))
        footer.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-style: italic;")
        lay.addWidget(footer)
        
        self.cards = []
        self._refresh_list()

    def cargar_datos(self):
        if self.ruta_data.exists():
            try:
                with open(self.ruta_data, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def guardar_datos(self):
        try:
            with open(self.ruta_data, "w", encoding="utf-8") as f:
                json.dump(self.apps, f, indent=4)
        except:
            pass

    def _refresh_list(self):
        # Limpiar grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.cards = []
        filtro = self.search_input.text().lower().strip() if hasattr(self, 'search_input') else ""
        
        for app in self.apps:
            if filtro and filtro not in app.get('nombre', '').lower():
                continue
            card = AppCard(
                self, 
                app, 
                self.colores, 
                on_launch=self.abrir_app, 
                on_delete=self.eliminar_app
            )
            self.cards.append(card)
            
        self.reorganizar_grid()

    def reorganizar_grid(self):
        if not hasattr(self, 'grid_layout') or not hasattr(self, 'cards'):
            return
            
        ancho_disponible = self.grid_container.width()
        if ancho_disponible < 200:
            ancho_disponible = self.width() - 80
            if ancho_disponible < 200:
                ancho_disponible = 600
                
        card_w = 140
        spacing = 20
        columnas = max(1, (ancho_disponible + spacing) // (card_w + spacing))
        
        # Remover del grid sin destruir
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.takeAt(i)
            
        # Volver a agregar
        for idx, card in enumerate(self.cards):
            row = idx // columnas
            col = idx % columnas
            self.grid_layout.addWidget(card, row, col)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reorganizar_grid()

    def eliminar_app(self, app):
        msg = QMessageBox(self)
        msg.setWindowTitle("Eliminar Acceso Directo")
        msg.setText(f"¿Estás seguro de que deseas eliminar '{app.get('nombre', '')}' del lanzador?")
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
            if app in self.apps:
                self.apps.remove(app)
                self.guardar_datos()
                self._refresh_list()

    def agregar_app(self):
        p, _ = QFileDialog.getOpenFileName(self, "Seleccionar Ejecutable", "", "Executables (*.exe *.app *.bin *.sh);;All Files (*)")
        if p:
            nombre_sugerido = os.path.splitext(os.path.basename(p))[0]
            dialog = QInputDialog(self)
            dialog.setWindowTitle("Nombre de la App")
            dialog.setLabelText("Ingresa una etiqueta para el acceso directo:")
            dialog.setTextValue(nombre_sugerido)
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
            nombre = dialog.textValue()
            if ok and nombre.strip():
                self.apps.append({"nombre": nombre.strip(), "ruta": p})
                self.guardar_datos()
                self._refresh_list()

    def abrir_app(self, app):
        try:
            if platform.system() == "Windows":
                 os.startfile(app['ruta'])
            else:
                 subprocess.Popen(["open" if platform.system() == "Darwin" else "xdg-open", app['ruta']])
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText(f"No se pudo iniciar:\n{e}")
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setStyleSheet(f"""
                QMessageBox {{ background-color: {self.colores['bg_secundario']}; }}
                QLabel {{ color: white; font-family: 'Outfit'; }}
                QPushButton {{
                    background: {self.colores['acento']}; color: white; padding: 6px 15px; border-radius: 6px; border: none; font-family: 'Outfit'; font-weight: bold;
                }}
                QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
            """)
            msg.exec()
