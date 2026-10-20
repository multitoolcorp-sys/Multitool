import platform
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame, QLabel
from PyQt6.QtGui import QFont, QShortcut, QKeySequence
from PyQt6.QtCore import Qt

from .header import FileHeader
from .sidebar import FileSidebar
from .explorer_list import FileExplorerList
from .preview import FilePreview

class ArchivosGUI(QWidget):
    """Interfaz principal del explorador de archivos con diseño Premium"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        
        # Estado
        self.busqueda_var = ""
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        # Inyectar callback para filtrado de texto desde el header
        self.callbacks["filtrar_por_texto"] = self._on_filtrar_por_texto
        
        self.inicializar_ui()

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Componentes
        self.header = FileHeader(self, self.colores, self.callbacks)
        self.sidebar = FileSidebar(self, self.colores, self.callbacks)
        self.explorer = FileExplorerList(self, self.colores, self.callbacks)
        self.preview = FilePreview(self, self.colores, self.callbacks)
        
        # Ensamblar
        self.main_layout.addWidget(self.header)
        
        self.body_splitter = QSplitter()
        self.body_splitter.setStyleSheet(f"""
            QSplitter::handle {{ 
                background: {self.colores['bg_terciario']}; 
                width: 1px;
                border-left: 1px solid rgba(255,255,255,0.02);
            }}
        """)
        
        self.body_splitter.addWidget(self.sidebar)
        self.body_splitter.addWidget(self.explorer)
        self.body_splitter.addWidget(self.preview)
        
        self.body_splitter.setStretchFactor(0, 0) # Sidebar fijo (220px aprox)
        self.body_splitter.setStretchFactor(1, 4) # Explorer crece
        self.body_splitter.setStretchFactor(2, 2) # Preview intermedio
        
        # Inyectar callbacks para alternar visibilidad de paneles
        self.callbacks["toggle_sidebar"] = self.toggle_sidebar
        self.callbacks["toggle_preview"] = self.toggle_preview

        # Permitir colapsar a 0 los paneles lateral y de vista previa
        self.sidebar.setMinimumWidth(0)
        self.preview.setMinimumWidth(0)

        self.body_splitter.setCollapsible(0, True)
        self.body_splitter.setCollapsible(1, False)
        self.body_splitter.setCollapsible(2, True)
        
        # Tamaños iniciales explícitos
        self.body_splitter.setSizes([200, 550, 300])
        
        self.main_layout.addWidget(self.body_splitter)

        # Barra de estado inferior premium
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(32)
        self.status_bar.setStyleSheet(f"""
            QFrame {{ 
                background: {self.colores['bg_secundario']}; 
                border-top: 1px solid rgba(255,255,255,0.03);
            }}
        """)
        status_lay = QHBoxLayout(self.status_bar)
        status_lay.setContentsMargins(12, 0, 12, 0)
        
        self._lbl_status = QLabel("Explorador de Archivos activo".upper())
        self._lbl_status.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self._lbl_status.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        status_lay.addWidget(self._lbl_status)
        status_lay.addStretch()
        
        self.main_layout.addWidget(self.status_bar)
        self._configurar_accesos_rapidos()

    def toggle_sidebar(self, estado=None):
        if estado is None:
            estado = not self.sidebar.isVisible()
        self.sidebar.setVisible(estado)

    def toggle_preview(self, estado=None):
        if estado is None:
            estado = not self.preview.isVisible()
        self.preview.setVisible(estado)
        
        self.main_layout.addWidget(self.status_bar)
        self._configurar_accesos_rapidos()

    def _configurar_accesos_rapidos(self):
        for key, callback in [
            ("Ctrl+N", self._on_shortcut_nueva_carpeta),
            ("Ctrl+Shift+N", self._on_shortcut_nuevo_archivo),
            ("Ctrl+F", self._on_shortcut_buscar),
            ("Ctrl+L", self._on_shortcut_ruta),
            ("Alt+D", self._on_shortcut_ruta),
            ("F5", lambda: self.callbacks.get("refrescar", lambda: None)()),
            ("Ctrl+C", lambda: self.callbacks.get("operacion_archivo", lambda x: None)("copiar")),
            ("Ctrl+X", lambda: self.callbacks.get("operacion_archivo", lambda x: None)("cortar")),
            ("Ctrl+V", lambda: self.callbacks.get("pegar", lambda: None)()),
            ("F2", lambda: self.callbacks.get("renombrar_item", lambda: None)()),
            ("Delete", lambda: self.callbacks.get("eliminar", lambda: None)()),
        ]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)

    def _on_shortcut_nueva_carpeta(self):
        cb = self.callbacks.get("nueva_carpeta")
        if cb:
            cb()

    def _on_shortcut_nuevo_archivo(self):
        cb = self.callbacks.get("nuevo_archivo")
        if cb:
            cb()

    def _on_shortcut_buscar(self):
        self.header.search_field.setFocus()
        self.header.search_field.selectAll()

    def _on_shortcut_ruta(self):
        self.header.ent_ruta.setFocus()
        self.header.ent_ruta.selectAll()

    def _on_filtrar_por_texto(self, texto):
        # Puente entre header y la lógica central
        # La lógica central tiene el valor en gui.busqueda_var
        self.busqueda_var = texto
        if "filtrar" in self.callbacks:
            self.callbacks["filtrar"]()

    def actualizar_lista(self, carpetas, archivos, ruta):
        self.explorer.actualizar_lista(carpetas, archivos, ruta)
        self.header.set_ruta(str(ruta))
        self._lbl_status.setText(f"{len(carpetas)} Carpetas  •  {len(archivos)} Archivos")

    def mostrar_vista_imagen(self, image_path):
        self.preview.mostrar_imagen(image_path)

    def mostrar_vista_texto(self, content, nombre_archivo=None, editable=False):
        name = nombre_archivo or self.get_selected_name() or "Archivo"
        self.preview.mostrar_texto(content, name, editable)

    def mostrar_info_general(self, title, message):
        self.preview.mostrar_texto(message, title, False)

    def limpiar_vista_previa(self):
        self.preview.limpiar()

    def get_selected_name(self):
        return self.explorer.get_selected_name()

    def get_selected_names(self):
        return self.explorer.get_selected_names()

    @property
    def barra_estado(self):
        """Proxy para compatibilidad con la lógica que espera un QStatusBar"""
        return self

    def showMessage(self, message, timeout=0):
        """Muestra un mensaje temporal en la barra de estado personalizada"""
        if hasattr(self, "_lbl_status"):
            original = self._lbl_status.text()
            self._lbl_status.setText(message.upper())
            if timeout > 0:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(timeout, lambda: self._lbl_status.setText(original))

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(f"background-color: {self.colores['bg_principal']};")
        if hasattr(self.status_bar, "setStyleSheet"):
            self.status_bar.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-top: 1px solid rgba(255,255,255,0.05);")
        if hasattr(self, "_lbl_status"):
            self._lbl_status.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        if hasattr(self.sidebar, "actualizar_tema"):
            self.sidebar.actualizar_tema(colores)
        if hasattr(self.header, "actualizar_tema"):
            self.header.actualizar_tema(colores)
        if hasattr(self.explorer, "actualizar_tema"):
            self.explorer.actualizar_tema(colores)
        if hasattr(self.preview, "actualizar_tema"):
            self.preview.actualizar_tema(colores)



