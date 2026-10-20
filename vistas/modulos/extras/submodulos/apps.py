import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QGridLayout, QMessageBox, QFileDialog, QInputDialog, QLineEdit
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

from ..utils.acceso_manager import AccesosManager

class CardApp(QFrame):
    def __init__(self, nombre, ruta, icono, manager, colores, parent=None):
        super().__init__(parent)
        self.nombre = nombre
        self.ruta = ruta
        self.icono = icono
        self.manager = manager
        self.colores = colores
        self.btn_del = None
        self.inicializar_ui()

    def inicializar_ui(self):
        self.setFixedSize(180, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"QFrame {{ background: {self.colores['bg_secundario']}; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; }}")
        
        lay = QVBoxLayout(self)
        
        top = QHBoxLayout()
        top.addStretch()
        self.btn_del = QPushButton("×")
        self.btn_del.setFixedSize(20, 20)
        self.btn_del.setStyleSheet(f"color: {self.colores['error']}; background: transparent; font-weight: bold;")
        top.addWidget(self.btn_del)
        lay.addLayout(top)
        
        ic = QLabel(self.icono)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setStyleSheet("font-size: 30px;")
        lay.addWidget(ic)
        
        nm = QLabel(self.nombre)
        nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nm.setStyleSheet("color: white; font-weight: bold;")
        nm.setWordWrap(True)
        lay.addWidget(nm)
        lay.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if child != self.btn_del:
                self.manager.lanzar_aplicacion(self.ruta, emisor_gui=self)
        super().mousePressEvent(event)

class TabExtrasApps(QWidget):
    def __init__(self, parent, colores, callbacks, ruta_usuario):
        print(f"[*] Cargando TabExtrasApps en: {ruta_usuario}")
        super().__init__(parent)
        self.colores = colores
        self.ruta_usuario = ruta_usuario
        self.manager = AccesosManager(self.ruta_usuario)
        self.inicializar_ui()

    def inicializar_ui(self):
        print("[*] Iniciando construccion de UI segura...")
        self.layout_principal = QVBoxLayout(self)
        
        # 1. Header Simple
        header = QHBoxLayout()
        lbl = QLabel("🚀 ACCESOS DIRECTOS")
        lbl.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        header.addWidget(lbl)
        header.addStretch()
        
        # 2. Boton Añadir (Sin efectos complejos al inicio para evitar crash)
        self.btn_add = QPushButton("+ Añadir")
        self.btn_add.setFixedSize(100, 35)
        self.btn_add.setStyleSheet(f"background: {self.colores['exito']}; color: white; border-radius: 5px;")
        
        # Conexión Segura
        self.btn_add.clicked.connect(self._seguro_abrir_dialogo)
        
        header.addWidget(self.btn_add)
        self.layout_principal.addLayout(header)
        print("[*] Header y Boton añadidos con exito")

        # 3. Area de Apps
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.contenedor = QWidget()
        self.grid = QGridLayout(self.contenedor)
        self.refrescar_tarjetas()
        
        self.scroll.setWidget(self.contenedor)
        self.layout_principal.addWidget(self.scroll)
        print("[*] Todo el modulo cargado correctamente")

    def _seguro_abrir_dialogo(self):
        """Metodo de interfaz para evitar colisiones de hilos"""
        self.dialogo_añadir_app()

    def refrescar_tarjetas(self):
        # Limpiar
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        col, row = 0, 0
        for app in self.manager.mis_apps:
            card = CardApp(app["nombre"], app["ruta"], app.get("icono", "💻"), self.manager, self.colores)
            card.btn_del.clicked.connect(lambda ch, r=app["ruta"]: self.eliminar_app(r))
            self.grid.addWidget(card, row, col)
            col += 1
            if col > 3: col, row = 0, row + 1

    def dialogo_añadir_app(self):
        rutas, _ = QFileDialog.getOpenFileNames(self, "Seleccionar Aplicación", "C:\\", "Ejecutables (*.exe *.lnk);;Todos (*.*)")
        if rutas:
            for r in rutas:
                nombre = os.path.splitext(os.path.basename(r))[0].capitalize()
                self.manager.añadir_acceso(nombre, r)
            self.refrescar_tarjetas()

    def eliminar_app(self, ruta):
        self.manager.eliminar_acceso(ruta)
        self.refrescar_tarjetas()

