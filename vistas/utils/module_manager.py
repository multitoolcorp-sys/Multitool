import sys
import os
import json
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem, QWidget, QCheckBox, 
    QFrame, QSizePolicy, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

class ModuleItemWidget(QFrame):
    """Widget personalizado para cada fila del gestor"""
    def __init__(self, mod, colores, font_family, on_delete_callback=None):
        super().__init__()
        self.mod = mod
        self.setStyleSheet(f"""
            QFrame {{ 
                background: {colores['bg_terciario']}; 
                border-radius: 6px; 
                border: 1px solid {colores['bg_secundario']};
            }}
            QFrame:hover {{ border-color: {colores['acento']}; }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(15, 8, 15, 8)
        
        self.cb = QCheckBox()
        self.cb.setFixedSize(24, 24)
        self.cb.setChecked(mod.get('visible', True))
        self.cb.setEnabled(mod['name'] != "inicio") # No se puede ocultar inicio
        self.cb.setStyleSheet(f"""
            QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 2px solid {colores['fg_secundario']}; }}
            QCheckBox::indicator:checked {{ background: {colores['acento']}; border-color: {colores['acento']}; }}
        """)
        lay.addWidget(self.cb)
        
        lbl_icon = QLabel("⠿") # Símbolo de drag
        lbl_icon.setStyleSheet(f"color: {colores['fg_secundario']}; font-size: 16px; margin: 0 10px;")
        lay.addWidget(lbl_icon)
        
        self.lbl_name = QLabel(mod['name'].capitalize())
        self.lbl_name.setFont(QFont(font_family, 10, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet(f"color: {colores['fg_principal']};")
        lay.addWidget(self.lbl_name)
        
        lay.addStretch()

        # Botón de eliminar módulo físico
        name_lower = mod.get('name', '').lower()
        is_protected = name_lower in ("general", "inicio", "cuenta", "cuentas")

        self.btn_del = QPushButton("🗑️")
        self.btn_del.setFixedSize(28, 28)
        if is_protected:
            self.btn_del.setEnabled(False)
            self.btn_del.setToolTip("Módulo central protegido del sistema (no se puede eliminar)")
            self.btn_del.setStyleSheet("QPushButton { background: transparent; color: #4B5563; border: none; font-size: 11px; }")
        else:
            self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_del.setToolTip(f"Eliminar permanentemente el módulo {mod['name']}")
            self.btn_del.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(248, 113, 113, 0.1);
                    color: #F87171;
                    border: 1px solid rgba(248, 113, 113, 0.25);
                    border-radius: 5px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: rgba(248, 113, 113, 0.25);
                    border-color: #EF4444;
                    color: white;
                }}
            """)
            if on_delete_callback:
                self.btn_del.clicked.connect(lambda: on_delete_callback(self.mod, self))

        lay.addWidget(self.btn_del)
        
    def get_config_actualizada(self):
        """Retorna la config con la visibilidad del checkbox"""
        self.mod['visible'] = self.cb.isChecked()
        return self.mod

class ModuleManagerGUI(QDialog):
    """Gestor de Módulos Premium con Rearrastre Nativo"""
    def __init__(self, parent, all_modules, colores, on_save_callback):
        super().__init__(parent)
        self.setWindowTitle("Gestor de Módulos")
        self.resize(450, 550)
        self.colores = colores
        self.on_save = on_save_callback
        self.ruta_usuario = getattr(parent, "ruta_usuario", None)
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        # Ordenar por posición actual
        self.modulos_data = sorted(all_modules, key=lambda x: x.get('position', 99))
        
        self.setStyleSheet(f"background: {colores['bg_principal']};")
        self.inicializar_ui()
        self.center_window()

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.left() + (screen.width() - self.width()) // 2
        y = screen.top() + (screen.height() - self.height()) // 2
        self.move(x, y)

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-bottom: 1px solid {self.colores['bg_terciario']};")
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(25, 20, 25, 20)
        
        title = QLabel("PERSONALIZAR MENÚ")
        title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colores['acento']}; ")
        h_lay.addWidget(title)
        
        desc = QLabel("Arrastra los módulos para cambiar el orden.")
        desc.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 10px;")
        h_lay.addWidget(desc)
        layout.addWidget(header)
        
        # Lista con DRAG AND DROP nativo
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.setSpacing(8)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; outline: none; padding: 15px; }}
            QListWidget::item {{ background: transparent; border: none; padding: 0px; }}
            QListWidget::item:selected {{ background: transparent; }}
        """)
        
        for mod in self.modulos_data:
            item = QListWidgetItem(self.list_widget)
            widget = ModuleItemWidget(mod, self.colores, self.font_family, self.eliminar_modulo)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            
        layout.addWidget(self.list_widget)
        
        # Footer
        footer = QFrame()
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(20, 20, 20, 20)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(f"color: {self.colores['fg_secundario']}; background: transparent; padding: 8px;")
        btn_cancel.clicked.connect(self.reject)
        f_lay.addWidget(btn_cancel)
        
        # Botón Reiniciar
        self.btn_reset = QPushButton("🧺 REINICIAR")
        self.btn_reset.setToolTip("Restaurar orden y visión predeterminada")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {self.colores['fg_secundario']}; border: 1px solid {self.colores['bg_terciario']}; border-radius: 6px; padding: 8px 15px; font-weight: bold; font-size: 10px; }}
            QPushButton:hover {{ background: rgba(255,255,255,0.05); color: white; }}
        """)
        self.btn_reset.clicked.connect(self.reiniciar_ajustes)
        f_lay.addWidget(self.btn_reset)
        
        f_lay.addStretch()
        
        btn_save = QPushButton("GUARDAR CAMBIOS")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{ 
                background: {self.colores['acento']}; color: white; border-radius: 6px; 
                padding: 10px 25px; font-weight: bold; font-size: 11px;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_save.clicked.connect(self.finalizar_edicion)
        f_lay.addWidget(btn_save)
        layout.addWidget(footer)

    def finalizar_edicion(self):
        """Recolecta el nuevo orden y visibilidad para guardarlos"""
        nuevos_modulos = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            mod_config = widget.get_config_actualizada()
            
            if mod_config['name'] == "inicio":
                mod_config['position'] = 0
            else:
                mod_config['position'] = i + 1
                
            nuevos_modulos.append(mod_config)
            
        if self.on_save:
            self.on_save(nuevos_modulos)
            
        # Reinicio para aplicar cambios
        if QMessageBox.question(self, "Reiniciar", "Los cambios requieren reiniciar la Multitool. ¿Hacerlo ahora?") == QMessageBox.StandardButton.Yes:
            self.reiniciar_app()
        else:
            self.accept()

    def reiniciar_app(self):
        """Reinicia la aplicación de forma segura multiplataforma"""
        from controlador.utils.paths import reiniciar_aplicacion
        reiniciar_aplicacion(self)

    def reiniciar_ajustes(self):
        """Elimina el archivo modulos.conf del usuario para volver a los defaults"""
        if not self.ruta_usuario: return
        
        confirm = QMessageBox.question(
            self, "Confirmar Reinicio", 
            "¿Deseas restablecer el orden y visibilidad de los módulos a los valores de fábrica?\nSe eliminarán tus preferencias personalizadas.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            conf_path = self.ruta_usuario / "modulos.conf"
            try:
                if conf_path.exists():
                    conf_path.unlink()
                
                QMessageBox.information(self, "Éxito", "Preferencias restablecidas. Reiniciando...")
                self.reiniciar_app()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar la configuración: {e}")

    def eliminar_modulo(self, mod, widget_item):
        """Elimina permanentemente la carpeta física del módulo con confirmación previa del usuario."""
        nombre_mod = mod.get("name", "").capitalize()
        resp = QMessageBox.warning(
            self, "Eliminar Módulo",
            f"⚠️ ¿Estás completamente seguro de que deseas eliminar el módulo '{nombre_mod}'?\n\n"
            f"Se borrará de forma permanente su carpeta física y todos sus submódulos.\n"
            f"Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        # Localizar la carpeta física del módulo
        from controlador.utils.paths import get_resource_path
        base_dir = get_resource_path()
        folder_clean = mod.get("folder", mod["name"].lower()).replace("modulos/", "")
        mod_folder = base_dir / "vistas" / "modulos" / folder_clean
        if not mod_folder.exists():
            mod_folder = Path(__file__).resolve().parent.parent / "modulos" / folder_clean

        if mod_folder.exists() and mod_folder.is_dir():
            import shutil
            try:
                shutil.rmtree(mod_folder)
            except Exception as e:
                QMessageBox.critical(self, "Error al Eliminar", f"No se pudo eliminar la carpeta del módulo:\n{e}")
                return
        else:
            QMessageBox.warning(self, "Carpeta no encontrada", f"No se encontró la carpeta física en:\n{mod_folder}")

        # Remover de la lista gráfica
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if self.list_widget.itemWidget(item) == widget_item:
                self.list_widget.takeItem(i)
                break

        if mod in self.modulos_data:
            self.modulos_data.remove(mod)

        # Eliminar también de modulos.conf si existe
        if self.ruta_usuario:
            conf_path = self.ruta_usuario / "modulos.conf"
            if conf_path.exists():
                try:
                    with open(conf_path, "r", encoding="utf-8") as f:
                        u_conf = json.load(f)
                    if mod["name"] in u_conf:
                        del u_conf[mod["name"]]
                        with open(conf_path, "w", encoding="utf-8") as f:
                            json.dump(u_conf, f, indent=4)
                except Exception:
                    pass

        QMessageBox.information(
            self, "Módulo Eliminado",
            f"El módulo '{nombre_mod}' ha sido eliminado exitosamente.\n\n"
            "Reinicia MultiTool para sincronizar los cambios en la interfaz."
        )

