import os
import sys
import platform
import psutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox,
    QMenu, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QAction

# Intentar importación de winreg en Windows
if platform.system() == "Windows":
    import winreg
else:
    winreg = None

class TabStartup(QWidget):
    """Submódulo 4: Gestor de Aplicaciones de Inicio Automático del Sistema & Servicios"""
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

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("🚀 PROGRAMAS DE INICIO & SERVICIOS DEL SISTEMA")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores['acento']};")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        btn_refresh = QPushButton("🔄 Actualizar Lista")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white; padding: 6px 14px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        btn_refresh.clicked.connect(self.cargar_startup_items)
        hdr.addWidget(btn_refresh)

        layout.addLayout(hdr)

        # Tabla de Aplicaciones de Inicio
        lbl_sub = QLabel("📌 Aplicaciones que inician automáticamente con el Sistema Operativo:")
        lbl_sub.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_sub.setStyleSheet("color: white;")
        layout.addWidget(lbl_sub)

        self.table_startup = QTableWidget()
        self.table_startup.setColumnCount(5)
        self.table_startup.setHorizontalHeaderLabels(["Nombre", "Comando / Ruta", "Ubicación", "Estado", "Acción"])
        self.table_startup.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_startup.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_startup.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_startup.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_startup.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table_startup.setColumnWidth(4, 130)
        self.table_startup.setFont(QFont(self.font_family, 9))
        self.table_startup.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px; gridline-color: rgba(255,255,255,0.05);
            }}
            QHeaderView::section {{
                background-color: {self.colores['bg_terciario']};
                color: white; font-weight: bold; border: none; padding: 6px;
            }}
        """)
        self.table_startup.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_startup.customContextMenuRequested.connect(self._mostrar_context_menu_startup)
        layout.addWidget(self.table_startup, 1)

        self.cargar_startup_items()

    def cargar_startup_items(self):
        items = []

        # 1. Leer Claves de Registro (Windows) - Claves Activas y Desactivadas (Run / Run-)
        if winreg and platform.system() == "Windows":
            key_paths = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Registro Usuario (HKCU)", True),
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run-", "Registro Usuario (HKCU)", False),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "Registro Sistema (HKLM)", True),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run-", "Registro Sistema (HKLM)", False)
            ]
            for hkey, path_str, ubi, activo in key_paths:
                try:
                    with winreg.OpenKey(hkey, path_str, 0, winreg.KEY_READ) as key:
                        idx = 0
                        while True:
                            try:
                                name, val, _ = winreg.EnumValue(key, idx)
                                est = "Activo" if activo else "Desactivado"
                                items.append((name, str(val), ubi, est, {"tipo": "reg", "hkey": hkey, "path": path_str, "name": name, "val": val, "activo": activo}))
                                idx += 1
                            except OSError:
                                break
                except Exception:
                    pass

        # 2. Carpeta de Inicio de Usuario
        try:
            if platform.system() == "Windows":
                startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
                if startup_dir.exists():
                    for f in startup_dir.glob("*"):
                        if f.name.lower() != "desktop.ini":
                            desactivado = f.name.endswith(".disabled")
                            nombre_limpio = f.name[:-9] if desactivado else f.name
                            est = "Desactivado" if desactivado else "Activo"
                            items.append((nombre_limpio, str(f), "Carpeta Inicio (Startup)", est, {"tipo": "file", "path": f, "activo": not desactivado}))
        except Exception:
            pass

        # Poblar Tabla
        self._startup_items_meta = []
        self.table_startup.setRowCount(len(items))
        for row, (nombre, cmd, ubi, est, meta) in enumerate(items):
            self._startup_items_meta.append(meta)
            item_n = QTableWidgetItem(nombre)
            item_c = QTableWidgetItem(cmd)
            item_u = QTableWidgetItem(ubi)
            
            # Texto y color de estado con alto contraste
            item_e = QTableWidgetItem("🟢 Activo" if meta["activo"] else "⚪ Desactivado")
            item_n.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            item_c.setFont(QFont(self.mono_font, 8))

            item_n.setForeground(QColor("#FFFFFF"))
            item_c.setForeground(QColor("#CBD5E1"))
            item_u.setForeground(QColor("#94A3B8"))
            item_e.setForeground(QColor("#34D399") if meta["activo"] else QColor("#94A3B8"))

            self.table_startup.setItem(row, 0, item_n)
            self.table_startup.setItem(row, 1, item_c)
            self.table_startup.setItem(row, 2, item_u)
            self.table_startup.setItem(row, 3, item_e)

            # Botón de Acción con diseño moderno y colores intuitivos
            if meta["activo"]:
                btn_toggle = QPushButton("⛔ Desactivar")
                btn_toggle.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(239, 68, 68, 0.15);
                        color: #FCA5A5;
                        border: 1px solid rgba(239, 68, 68, 0.4);
                        border-radius: 6px;
                        padding: 3px 10px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: rgba(239, 68, 68, 0.35);
                        color: #FFFFFF;
                        border-color: #EF4444;
                    }
                """)
            else:
                btn_toggle = QPushButton("✅ Activar")
                btn_toggle.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(52, 211, 153, 0.15);
                        color: #6EE7B7;
                        border: 1px solid rgba(52, 211, 153, 0.4);
                        border-radius: 6px;
                        padding: 3px 10px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: rgba(52, 211, 153, 0.35);
                        color: #FFFFFF;
                        border-color: #10B981;
                    }
                """)
            btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_toggle.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
            btn_toggle.clicked.connect(lambda _, m=meta: self._toggle_inicio_item(m))
            self.table_startup.setCellWidget(row, 4, btn_toggle)

    def _toggle_inicio_item(self, meta):
        """Activa o desactiva un elemento de inicio de Windows."""
        try:
            if meta["tipo"] == "file":
                f = meta["path"]
                if meta["activo"]:
                    new_f = f.with_name(f.name + ".disabled")
                    f.rename(new_f)
                else:
                    if f.name.endswith(".disabled"):
                        new_f = f.with_name(f.name[:-9])
                        f.rename(new_f)
            elif meta["tipo"] == "reg" and winreg:
                hkey = meta["hkey"]
                old_path = meta["path"]
                name = meta["name"]
                val = meta["val"]
                activo = meta["activo"]
                
                new_path = old_path[:-1] if not activo else old_path + "-"
                
                # Crear clave destino si no existe
                with winreg.CreateKey(hkey, new_path) as k_dest:
                    winreg.SetValueEx(k_dest, name, 0, winreg.REG_SZ, val)
                
                # Eliminar de clave origen
                try:
                    with winreg.OpenKey(hkey, old_path, 0, winreg.KEY_SET_VALUE) as k_orig:
                        winreg.DeleteValue(k_orig, name)
                except Exception:
                    pass

            self.cargar_startup_items()
        except Exception as e:
            QMessageBox.critical(self, "Error de Permisos", f"No se pudo modificar el elemento de inicio:\n{e}\n\nPuede que requiera ejecutar como Administrador.")

    def _mostrar_context_menu_startup(self, pos):
        """Muestra el menú contextual al hacer clic derecho en un elemento de inicio."""
        item = self.table_startup.itemAt(pos)
        if not item:
            return
        row = item.row()
        if not hasattr(self, "_startup_items_meta") or row >= len(self._startup_items_meta):
            return
        meta = self._startup_items_meta[row]
        cmd_text = self.table_startup.item(row, 1).text() if self.table_startup.item(row, 1) else ""

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #E2E8F0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: #E2E8F0;
                padding: 8px 22px 8px 14px;
                border-radius: 5px;
                font-size: 9.5pt;
            }}
            QMenu::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF !important;
                font-weight: bold;
            }}
            QMenu::item:disabled {{
                color: #64748B !important;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: rgba(255, 255, 255, 0.08);
                margin: 4px 6px;
            }}
        """)

        if meta.get("activo"):
            act_toggle = QAction("⛔ Desactivar del inicio de Windows", self)
        else:
            act_toggle = QAction("✅ Activar para iniciar con Windows", self)
        act_toggle.triggered.connect(lambda: self._toggle_inicio_item(meta))
        menu.addAction(act_toggle)

        menu.addSeparator()

        act_copy = QAction("📋 Copiar comando / ruta", self)
        act_copy.triggered.connect(lambda: QApplication.clipboard().setText(cmd_text))
        menu.addAction(act_copy)

        # Ubicación física si es un archivo o ejecutable
        target_path = None
        if meta.get("tipo") == "file":
            target_path = str(meta.get("path"))
        elif cmd_text:
            cleaned = cmd_text.strip().strip('"')
            if os.path.exists(cleaned):
                target_path = cleaned

        if target_path:
            act_loc = QAction("📂 Abrir ubicación en Explorador de Windows", self)
            act_loc.triggered.connect(lambda: self._abrir_en_explorer(target_path))
            menu.addAction(act_loc)

        menu.exec(self.table_startup.viewport().mapToGlobal(pos))

    def _abrir_en_explorer(self, target_path):
        import subprocess
        try:
            if os.path.exists(target_path):
                if os.path.isfile(target_path):
                    subprocess.run(f'explorer /select,"{target_path}"', shell=True)
                else:
                    subprocess.run(f'explorer "{target_path}"', shell=True)
        except Exception:
            pass
