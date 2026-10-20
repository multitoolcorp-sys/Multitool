import os
import json
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTreeWidget, QTreeWidgetItem, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

class SnippetsPanel(QFrame):
    """Panel lateral de Snippets y Comandos Rápidos preseteados con soporte Git y persistencia"""
    snippet_selected = pyqtSignal(str)

    def __init__(self, parent, colores, ruta_usuario=None):
        super().__init__(parent)
        self.colores = colores
        self.ruta_usuario = Path(ruta_usuario) if ruta_usuario else None
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        
        self.presets = {
            "🌿 Git": [
                ("Status de Repositorio", "git status"),
                ("Log de Commits (Compacto)", "git log --oneline -n 10"),
                ("Árbol Gráfico de Ramas", "git log --graph --oneline --decorate --all"),
                ("Ramas Locales y Remotas", "git branch -a"),
                ("Diferencias no guardadas", "git diff"),
                ("Pull de Cambios", "git pull"),
                ("Push al Repositorio", "git push"),
                ("Guardar en Stash temporal", "git stash"),
                ("Recuperar Stash", "git stash pop"),
                ("Fetch de todo", "git fetch --all"),
            ],
            "🌐 Red & Conectividad": [
                ("Configuración de Red", "ipconfig /all" if platform.system() == "Windows" else "ifconfig"),
                ("Prueba de Conexión Ping", "ping -n 4 8.8.8.8" if platform.system() == "Windows" else "ping -c 4 8.8.8.8"),
                ("Conexiones Activas", "netstat -ano"),
                ("Consulta DNS Google", "nslookup google.com"),
            ],
            "🖥️ Sistema & Procesos": [
                ("Lista de Procesos", "tasklist" if platform.system() == "Windows" else "ps aux"),
                ("Información del Sistema", "systeminfo" if platform.system() == "Windows" else "uname -a"),
                ("Listar Archivos (Detalle)", "dir /w" if platform.system() == "Windows" else "ls -la"),
                ("Usuario Actual", "whoami"),
            ],
            "🐍 Python & Node": [
                ("Versión de Python", "python --version"),
                ("Paquetes Pip Instalados", "pip list"),
                ("Versión de Node.js", "node -v"),
            ]
        }
        
        self.ruta_snippets_json = self._obtener_ruta_snippets_json()
        self._cargar_snippets_guardados()
        
        self.inicializar_ui()

    def _obtener_ruta_snippets_json(self):
        if self.ruta_usuario and self.ruta_usuario.exists():
            return self.ruta_usuario / "terminal_snippets.json"
        return Path(__file__).resolve().parent.parent / "terminal_snippets.json"

    def _cargar_snippets_guardados(self):
        try:
            if self.ruta_snippets_json.exists():
                data = json.loads(self.ruta_snippets_json.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for cat, items in data.items():
                        if cat not in self.presets:
                            self.presets[cat] = []
                        # Añadir ítems evitando duplicados
                        existentes = {cmd for _, cmd in self.presets[cat]}
                        for label, cmd in items:
                            if cmd not in existentes:
                                self.presets[cat].append((label, cmd))
        except Exception:
            pass

    def _guardar_snippets(self):
        try:
            custom_data = {}
            if "⭐ Personalizados" in self.presets:
                custom_data["⭐ Personalizados"] = self.presets["⭐ Personalizados"]
            self.ruta_snippets_json.write_text(json.dumps(custom_data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def inicializar_ui(self):
        self.setFixedWidth(240)
        self.setStyleSheet(f"""
            QFrame {{ 
                background: {self.colores['bg_secundario']}; 
                border-left: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(8)

        # Header del panel
        hdr_lay = QHBoxLayout()
        self.lbl_title = QLabel("⚡ SNIPPETS RÁPIDOS")
        self.lbl_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet(f"color: {self.colores['acento']}; border: none;")
        hdr_lay.addWidget(self.lbl_title)
        hdr_lay.addStretch()

        btn_add = QPushButton("➕")
        btn_add.setFixedSize(22, 22)
        btn_add.setToolTip("Añadir comando personalizado")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 11px; color: white; }
            QPushButton:hover { background: rgba(255,255,255,0.1); border-radius: 4px; }
        """)
        btn_add.clicked.connect(self._agregar_snippet_personalizado)
        hdr_lay.addWidget(btn_add)
        layout.addLayout(hdr_lay)

        # Árbol de snippets por categoría
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setFont(QFont(self.font_family, 9))
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: transparent;
                color: {self.colores['fg_principal']};
                border: none; outline: none;
            }}
            QTreeWidget::item {{
                padding: 4px 6px; border-radius: 4px;
            }}
            QTreeWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.05);
                color: {self.colores['acento']};
            }}
            QTreeWidget::item:selected {{
                background-color: {self.colores['acento']}22;
                color: {self.colores['acento']};
            }}
        """)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)

        self._cargar_tree()

        # Botón de ayuda/instrucción al pie
        lbl_info = QLabel("💡 Doble clic para ejecutar")
        lbl_info.setFont(QFont(self.font_family, 8))
        lbl_info.setStyleSheet("color: rgba(255,255,255,0.4);")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_info)

    def _cargar_tree(self):
        self.tree.clear()
        for cat_name, items in self.presets.items():
            cat_item = QTreeWidgetItem(self.tree)
            cat_item.setText(0, cat_name)
            cat_item.setFont(0, QFont(self.font_family, 9, QFont.Weight.Bold))
            cat_item.setForeground(0, QColor(self.colores['acento']))
            cat_item.setExpanded(True)

            for label, cmd in items:
                child = QTreeWidgetItem(cat_item)
                child.setText(0, f"▶ {label}")
                child.setForeground(0, QColor("#FFFFFF"))
                child.setData(0, Qt.ItemDataRole.UserRole, cmd)
                child.setToolTip(0, f"Ejecutar: {cmd}")

    def _on_item_double_clicked(self, item, col):
        cmd = item.data(0, Qt.ItemDataRole.UserRole)
        if cmd:
            self.snippet_selected.emit(cmd)

    def _agregar_snippet_personalizado(self):
        cmd, ok = QInputDialog.getText(self, "Nuevo Snippet", "Introduce el comando a guardar:")
        if ok and cmd.strip():
            cmd = cmd.strip()
            cat = "⭐ Personalizados"
            if cat not in self.presets:
                self.presets[cat] = []
            nombre_label = cmd[:25] + ("..." if len(cmd) > 25 else "")
            self.presets[cat].append((nombre_label, cmd))
            self._guardar_snippets()
            self._cargar_tree()

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(f"""
            QFrame {{ 
                background: {self.colores['bg_secundario']}; 
                border-left: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        if hasattr(self, 'lbl_title'):
            self.lbl_title.setStyleSheet(f"color: {self.colores['acento']}; border: none;")
        self._cargar_tree()
