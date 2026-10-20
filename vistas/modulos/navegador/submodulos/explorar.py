import json
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QTreeWidget, QTreeWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

class TabNavegadorExplorar(QWidget):
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        
        # Obtener ruta del perfil del usuario de manera segura
        self.ruta_usuario = getattr(parent, "ruta_usuario", None)
        if not self.ruta_usuario:
            try:
                from controlador.utils.paths import get_data_path
                self.ruta_usuario = get_data_path()
            except Exception:
                self.ruta_usuario = Path.cwd()
        else:
            self.ruta_usuario = Path(self.ruta_usuario)
            
        # Cargar los navegadores desde el archivo JSON (Speed Dial)
        self.navegadores = self._cargar_datos_navegadores()
        
        self.inicializar_ui()

    def _cargar_datos_navegadores(self):
        self.speed_dial_file = self.ruta_usuario / "browser_data" / "speed_dial.json"
        if self.speed_dial_file.exists():
            try:
                with open(self.speed_dial_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data: return data
            except Exception: pass
            
        # Fallback a defaults
        try:
            ruta_json = Path(__file__).parent.parent / "utils" / "browsers.json"
            if ruta_json.exists():
                with open(ruta_json, "r", encoding="utf-8") as f:
                    defaults = json.load(f)
                    self._guardar_datos_navegadores(defaults)
                    return defaults
        except Exception as e:
            print(f"[!] Error al cargar browsers.json: {e}")
            
        return []

    def _guardar_datos_navegadores(self, data):
        try:
            self.speed_dial_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.speed_dial_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[!] Error al guardar speed_dial.json: {e}")

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header
        header = QVBoxLayout()
        title = QLabel("🧭 EXPLORAR RED GLOBAL")
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: white;")
        header.addWidget(title)
        
        subtitle = QLabel("Navega de forma segura o explora redes alternativas categorizadas.")
        subtitle.setFont(QFont("Inter", 10))
        subtitle.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        header.addWidget(subtitle)
        layout.addLayout(header)
        
        # Scroll Area para las tarjetas
        from PyQt6.QtWidgets import QScrollArea, QGridLayout
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{ background: {self.colores['bg_secundario']}; width: 10px; }}
            QScrollBar::handle:vertical {{ background: {self.colores['bg_terciario']}; border-radius: 5px; }}
        """)
        
        self.container_widget = QWidget()
        self.container_widget.setStyleSheet("background: transparent;")
        self.grid_lay = QGridLayout(self.container_widget)
        self.grid_lay.setSpacing(15)
        
        self.scroll.setWidget(self.container_widget)
        layout.addWidget(self.scroll)
        
        self.popular_cuadros()

    def popular_cuadros(self):
        # Limpiar layout
        while self.grid_lay.count():
            child = self.grid_lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        row, col = 0, 0
        max_cols = 3
        
        for b in self.navegadores:
            # Crear Tarjeta (Frame)
            card = QFrame()
            card.setFixedSize(220, 160)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Estilos según criticidad
            border_color = "rgba(255,255,255,0.1)"
            if b.get("tipo") == "Peligroso": border_color = "rgba(239, 68, 68, 0.4)"
                
            card.setStyleSheet(f"""
                QFrame {{
                    background: {self.colores['bg_secundario']};
                    border: 1px solid {border_color};
                    border-radius: 12px;
                }}
                QFrame:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {self.colores['bg_terciario']}, stop:1 #2E2F4F);
                    border: 1px solid {self.colores['acento']};
                }}
            """)
            
            c_lay = QVBoxLayout(card)
            c_lay.setSpacing(10)
            
            lbl_icon = QLabel(b.get('icon', '🌐'))
            lbl_icon.setFont(QFont("Segoe UI Emoji", 24))
            lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_icon.setStyleSheet("border: none; background: transparent;")
            c_lay.addWidget(lbl_icon)
            
            lbl_n = QLabel(b.get('nombre', 'Desconocido'))
            lbl_n.setFont(QFont("Inter", 11, QFont.Weight.Bold))
            lbl_n.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_n.setStyleSheet("border: none; background: transparent; color: white;")
            c_lay.addWidget(lbl_n)
            
            lbl_dsc = QLabel(b.get('desc', ''))
            lbl_dsc.setFont(QFont("Inter", 8))
            lbl_dsc.setWordWrap(True)
            lbl_dsc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_dsc.setStyleSheet("border: none; background: transparent; color: #aaa;")
            c_lay.addWidget(lbl_dsc)
            
            # Controles de Acción: 2 botones (Pestaña Principal y Nueva Pestaña)
            btn_lay = QHBoxLayout()
            btn_lay.setSpacing(5)
            
            btn_main = QPushButton("Principal")
            btn_main.setFixedHeight(28)
            btn_main.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_main.setStyleSheet(f"""
                QPushButton {{ 
                    background: {self.colores['bg_terciario']}; 
                    color: {self.colores['fg_principal']}; 
                    border-radius: 6px; 
                    padding: 3px 6px; 
                    font-family: 'Inter'; 
                    font-size: 9px;
                    font-weight: bold;
                    border: 1px solid rgba(255,255,255,0.05);
                }}
                QPushButton:hover {{ background: {self.colores['acento']}; color: white; }}
            """)
            btn_main.clicked.connect(lambda _, bow=b: self.abrir_browser(bow, new_tab=False))
            
            btn_new = QPushButton("+ Nueva Tab")
            btn_new.setFixedHeight(28)
            btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_new.setStyleSheet(f"""
                QPushButton {{ 
                    background: {self.colores['bg_secundario']}; 
                    color: {self.colores['fg_principal']}; 
                    border-radius: 6px; 
                    padding: 3px 6px; 
                    font-family: 'Inter'; 
                    font-size: 9px;
                    font-weight: bold;
                    border: 1px solid rgba(255,255,255,0.05);
                }}
                QPushButton:hover {{ background: {self.colores['acento_hover']}; color: white; }}
            """)
            btn_new.clicked.connect(lambda _, bow=b: self.abrir_browser(bow, new_tab=True))
            
            btn_lay.addWidget(btn_main)
            btn_lay.addWidget(btn_new)
            c_lay.addLayout(btn_lay)
            
            self.grid_lay.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
                
        # Tarjeta "Añadir Sitio"
        add_card = QFrame()
        add_card.setFixedSize(220, 160)
        add_card.setCursor(Qt.CursorShape.PointingHandCursor)
        add_card.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border: 2px dashed rgba(255,255,255,0.15);
                border-radius: 12px;
            }}
            QFrame:hover {{
                background: {self.colores['bg_terciario']};
                border: 2px dashed {self.colores['acento']};
            }}
        """)
        add_lay = QVBoxLayout(add_card)
        add_lay.setSpacing(10)
        add_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_add_icon = QLabel("➕")
        lbl_add_icon.setFont(QFont("Segoe UI Emoji", 24))
        lbl_add_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_add_icon.setStyleSheet("border: none; background: transparent;")
        add_lay.addWidget(lbl_add_icon)
        
        lbl_add_title = QLabel("Añadir Sitio")
        lbl_add_title.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        lbl_add_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_add_title.setStyleSheet("border: none; background: transparent; color: white;")
        add_lay.addWidget(lbl_add_title)
        
        # Interceptar clic
        add_card.mousePressEvent = lambda event: self.mostrar_dialogo_nuevo_speed_dial() if event.button() == Qt.MouseButton.LeftButton else None
        
        self.grid_lay.addWidget(add_card, row, col)
        col += 1
        if col >= max_cols:
            col = 0
            row += 1
            
        # Empujar hacia arriba
        self.grid_lay.setRowStretch(row + 1, 1)

    def mostrar_dialogo_nuevo_speed_dial(self):
        from PyQt6.QtWidgets import QDialog, QLineEdit, QDialogButtonBox, QGridLayout
        dialog = QDialog(self)
        dialog.setWindowTitle("Añadir a Accesos Rápidos")
        dialog.setStyleSheet(f"""
            QDialog {{ background: {self.colores['bg_principal']}; border: 1px solid {self.colores['bg_terciario']}; border-radius: 10px; }}
            QLabel {{ font-family: 'Inter'; color: white; }}
            QLineEdit {{
                background: {self.colores['bg_terciario']}; 
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; 
                padding: 6px;
                color: white;
                font-family: 'Inter';
            }}
        """)
        dialog.setFixedSize(350, 250)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Nombre:"), 0, 0)
        txt_nombre = QLineEdit()
        grid.addWidget(txt_nombre, 0, 1)
        
        grid.addWidget(QLabel("URL:"), 1, 0)
        txt_url = QLineEdit("https://")
        grid.addWidget(txt_url, 1, 1)
        
        grid.addWidget(QLabel("Emoji / Icono:"), 2, 0)
        txt_emoji = QLineEdit("🌐")
        grid.addWidget(txt_emoji, 2, 1)
        
        grid.addWidget(QLabel("Descripción:"), 3, 0)
        txt_desc = QLineEdit()
        grid.addWidget(txt_desc, 3, 1)
        
        layout.addLayout(grid)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.setStyleSheet("""
            QPushButton {
                background: #2D3748;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #4A5568;
            }
        """)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            nombre = txt_nombre.text().strip()
            url = txt_url.text().strip()
            emoji = txt_emoji.text().strip() or "🌐"
            desc = txt_desc.text().strip()
            
            if not nombre or not url:
                QMessageBox.warning(self, "Error", "El nombre y la URL son obligatorios.")
                return
                
            nuevo_site = {
                "nombre": nombre,
                "url": url,
                "icon": emoji,
                "desc": desc,
                "tipo": "Seguro"
            }
            
            self.navegadores.append(nuevo_site)
            self._guardar_datos_navegadores(self.navegadores)
            self.popular_cuadros()

    def abrir_browser(self, browser, new_tab=False):
        if "warning" in browser:
            res = QMessageBox.warning(
                self, "Aviso de Seguridad", browser["warning"],
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.No:
                return
        
        url = browser["url"]
        if new_tab and "abrir_nueva_pestana_integrada" in self.callbacks:
            self.callbacks["abrir_nueva_pestana_integrada"](url, browser.get("nombre", "Nueva Pestaña"))
        elif "abrir_url_integrada" in self.callbacks:
            self.callbacks["abrir_url_integrada"](url)
        elif hasattr(self.parent(), "_seleccionar_navegador_y_abrir"):
            self.parent()._seleccionar_navegador_y_abrir(url)
