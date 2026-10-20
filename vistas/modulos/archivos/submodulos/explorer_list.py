import os
import platform
from pathlib import Path
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu
from PyQt6.QtCore import Qt, QMimeData, QUrl
from PyQt6.QtGui import QColor, QFont, QDrag

class FileTreeWidget(QTreeWidget):
    """QTreeWidget personalizado para capturar eventos de teclado del explorador"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.callbacks = {}

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if not item:
            self.clearSelection()
            if "limpiar_vista_previa" in self.callbacks:
                self.callbacks["limpiar_vista_previa"]()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.clearSelection()
            if "limpiar_vista_previa" in self.callbacks:
                self.callbacks["limpiar_vista_previa"]()
            event.accept()
            return
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if "abrir_seleccionado" in self.callbacks:
                self.callbacks["abrir_seleccionado"]()
                event.accept()
                return
        elif key == Qt.Key.Key_Backspace:
            if "subir_nivel" in self.callbacks:
                self.callbacks["subir_nivel"]()
                event.accept()
                return
        elif key == Qt.Key.Key_F5:
            if "refrescar" in self.callbacks:
                self.callbacks["refrescar"]()
                event.accept()
                return
        elif key == Qt.Key.Key_F2:
            if "renombrar_item" in self.callbacks:
                self.callbacks["renombrar_item"]()
                event.accept()
                return
        elif key == Qt.Key.Key_Delete:
            if "eliminar" in self.callbacks:
                self.callbacks["eliminar"]()
                event.accept()
                return
        super().keyPressEvent(event)


class FileExplorerList(QFrame):
    """Lista de archivos con soporte para Drag & Drop y menús contextuales"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        from PyQt6.QtWidgets import QFileIconProvider
        self.icon_provider = QFileIconProvider()
        self._icon_cache = {}
        self._folder_icon = None

        self.inicializar_ui()
        
        # 🛡️ INSTALAR FILTRO PARA SCROLL DURANTE DRAG
        self.tree.viewport().installEventFilter(self)
        self.tree.setMouseTracking(True)

    def inicializar_ui(self):
        self.setStyleSheet(f"background: {self.colores['bg_principal']}; border: none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Mini Toolbar de Archivos
        self.file_toolbar = QFrame()
        self.file_toolbar.setFixedHeight(32)
        self.file_toolbar.setStyleSheet(f"background: {self.colores['bg_principal']}; border-bottom: 1px solid rgba(255,255,255,0.03);")
        ft_lay = QHBoxLayout(self.file_toolbar)
        ft_lay.setContentsMargins(10, 0, 10, 0)
        ft_lay.setSpacing(5)
        
        ft_btn_style = f"""
            QPushButton {{ 
                font-size: 13px; 
                background: transparent; 
                border: none; 
                padding: 3px; 
                color: #FFFFFF;
                border-radius: 6px;
            }}
            QPushButton:hover {{ 
                background: rgba(255, 255, 255, 0.05); 
                color: {self.colores['acento']};
            }}
            QPushButton:disabled {{
                color: rgba(255, 255, 255, 0.25);
            }}
        """
        
        mini_acciones = [
            ("✂️", "cortar", "Cortar"), 
            ("📋", "copiar", "Copiar"), 
            ("📌", "pegar", "Pegar"), 
            ("🗑️", "eliminar", "Eliminar")
        ]
        
        self.toolbar_buttons = {}
        for icon, act, tool in mini_acciones:
            btn = QPushButton(icon)
            btn.setFixedSize(26, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tool)
            btn.setStyleSheet(ft_btn_style)
            
            if act == "pegar":
                btn.clicked.connect(self.callbacks.get("pegar"))
            elif act == "eliminar":
                btn.clicked.connect(self.callbacks.get("eliminar"))
            else:
                btn.clicked.connect(lambda checked, a=act: self.callbacks.get("operacion_archivo")(a))
            ft_lay.addWidget(btn)
            self.toolbar_buttons[act] = btn
            
        ft_lay.addStretch()
        layout.addWidget(self.file_toolbar)

        # La Lista de Archivos
        self.tree = FileTreeWidget()
        self.tree.callbacks = self.callbacks
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Nombre", "Fecha de modificación", "Tipo", "Tamaño"])
        self.tree.setFont(QFont(self.font_family, 9))
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIndentation(20)
        
        # Drag and Drop
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QTreeWidget.DragDropMode.DragDrop)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        
        # Eventos personalizados
        self.tree.mouseMoveEvent = self._on_mouse_move
        self.tree.dragEnterEvent = self._on_drag_enter
        self.tree.dragMoveEvent = self._on_drag_move
        self.tree.dropEvent = self._on_drop
        
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                alternate-background-color: rgba(255, 255, 255, 0.015);
                border: none;
                outline: none;
            }}
            QTreeWidget::item {{ 
                padding: 5px 8px; 
                border-bottom: 1px solid rgba(255,255,255,0.01);
                color: rgba(255, 255, 255, 0.85);
            }}
            QTreeWidget::item:hover {{ 
                background: rgba(255, 255, 255, 0.03); 
            }}
            QTreeWidget::item:selected {{ 
                background: {self.colores['acento']}15; 
                color: {self.colores['acento']}; 
                border-left: 2px solid {self.colores['acento']};
            }}
            QHeaderView::section {{
                background: {self.colores['bg_secundario']};
                color: {self.colores['fg_secundario']};
                padding: 6px 10px;
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.05);
                font-weight: bold;
                font-size: 10px;
            }}
        """)
        
        hdr = self.tree.header()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setStretchLastSection(False)
        hdr.resizeSection(0, 240)
        hdr.resizeSection(1, 140)
        hdr.resizeSection(2, 90)
        hdr.resizeSection(3, 90)
        self.tree.itemDoubleClicked.connect(lambda: self.callbacks.get("abrir_seleccionado")())
        self.tree.itemSelectionChanged.connect(self.callbacks.get("al_seleccionar_item"))
        self.tree.header().sectionClicked.connect(self._on_header_clicked)
        
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        
        layout.addWidget(self.tree)

    def _on_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        is_inside_archive = False
        if "is_inside_archive" in self.callbacks:
            try:
                is_inside_archive = self.callbacks["is_inside_archive"]()
            except Exception as e:
                print(f"Error checking is_inside_archive: {e}")

        menu = QMenu(self)
        menu.setFont(QFont(self.font_family, 9))
        menu.setStyleSheet(f"""
            QMenu {{ 
                background-color: {self.colores['bg_secundario']}; 
                color: white; 
                border: 1px solid rgba(255,255,255,0.1); 
                padding: 5px; 
                border-radius: 8px;
            }}
            QMenu::item {{ padding: 8px 25px 8px 25px; border-radius: 4px; margin: 2px; }}
            QMenu::item:selected {{ background-color: {self.colores['acento']}; color: white; }}
        """)
        
        if self.header_ruta_actual == "PAPELERA_RECICLAJE":
            if item is None:
                menu.addAction("🧹 Vaciar Papelera", self.callbacks.get("vaciar_papelera"))
                menu.addAction("🔄 Refrescar", self.callbacks.get("mostrar_papelera"))
            else:
                self.tree.setCurrentItem(item)
                menu.addAction("♻️ Restaurar elemento", self.callbacks.get("restaurar_elemento"))
                menu.addSeparator()
                menu.addAction("🗑️ Eliminar permanentemente", self.callbacks.get("eliminar_definitivo"))
                menu.addSeparator()
                menu.addAction("🧹 Vaciar Papelera", self.callbacks.get("vaciar_papelera"))
            global_pos = self.tree.viewport().mapToGlobal(pos)
            menu.exec(global_pos)
            return

        if is_inside_archive:
            if not item:
                menu.addAction("📋 Copiar ruta de acceso virtual", self.callbacks.get("copiar_ruta_acceso"))
                menu.addAction("👁️ Mostrar archivo comprimido en Explorador", self.callbacks.get("mostrar_en_explorador"))
                menu.addAction("ℹ️ Propiedades del archivo comprimido", self.callbacks.get("mostrar_propiedades"))
            else:
                self.tree.setCurrentItem(item)
                menu.addAction("📂 Abrir", self.callbacks.get("abrir_seleccionado"))
                menu.addSeparator()
                menu.addAction("📋 Copiar ruta de acceso virtual", self.callbacks.get("copiar_ruta_acceso"))
                menu.addAction("👁️ Mostrar archivo comprimido en Explorador", self.callbacks.get("mostrar_en_explorador"))
                menu.addAction("ℹ️ Propiedades del archivo comprimido", self.callbacks.get("mostrar_propiedades"))
        else:
            if not item:
                menu.addAction("🔄 Refrescar", self.callbacks.get("refrescar"))
                menu.addSeparator()
                menu.addAction("📁 Nueva Carpeta", self.callbacks.get("nueva_carpeta"))
                menu.addAction("📄 Nuevo Archivo", self.callbacks.get("nuevo_archivo"))
                menu.addSeparator()
                menu.addAction("📌 Pegar", self.callbacks.get("pegar"))
                menu.addSeparator()
                menu.addAction("🖥️ Mostrar en Explorador", self.callbacks.get("mostrar_en_explorador"))
                menu.addAction("📋 Copiar ruta de acceso", self.callbacks.get("copiar_ruta_acceso"))
                menu.addAction("ℹ️ Propiedades de Windows", self.callbacks.get("mostrar_propiedades"))
            else:
                self.tree.setCurrentItem(item)
                selected_items = self.tree.selectedItems()
                
                if len(selected_items) == 2:
                    name1 = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
                    name2 = selected_items[1].data(0, Qt.ItemDataRole.UserRole)
                    path1 = os.path.join(self.header_ruta_actual, name1)
                    path2 = os.path.join(self.header_ruta_actual, name2)
                    if os.path.isfile(path1) and os.path.isfile(path2):
                        menu.addAction("🔍 Comparar Diferencias (Diff)", lambda: self.mostrar_comparador(path1, path2))
                        menu.addSeparator()
                
                menu.addAction("📂 Abrir", self.callbacks.get("abrir_seleccionado"))
                menu.addAction("⚙️ Abrir con...", self.callbacks.get("abrir_con_seleccionado"))
                menu.addSeparator()
                
                menu.addAction("📦 Comprimir en ZIP", self.comprimir_seleccionado)
                first_name = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
                if first_name.lower().endswith(".zip"):
                    menu.addAction("📂 Extraer aquí (ZIP)", self.extraer_seleccionado)
                menu.addSeparator()

                menu.addAction("✏️ Renombrar", self.callbacks.get("renombrar_item"))
                menu.addAction("✂️ Cortar", lambda: self.callbacks.get("operacion_archivo")("cortar"))
                menu.addAction("📋 Copiar", lambda: self.callbacks.get("operacion_archivo")("copiar"))
                menu.addSeparator()
                menu.addAction("🗑️ Eliminar", self.callbacks.get("eliminar"))
                menu.addSeparator()
                menu.addAction("🖥️ Mostrar en Explorador", self.callbacks.get("mostrar_en_explorador"))
                menu.addAction("📋 Copiar ruta de acceso", self.callbacks.get("copiar_ruta_acceso"))
                menu.addAction("ℹ️ Propiedades de Windows", self.callbacks.get("mostrar_propiedades"))
        
        global_pos = self.tree.viewport().mapToGlobal(pos)
        menu.exec(global_pos)

    def _on_header_clicked(self, index):
        cols = ["nombre", "fecha", "tipo", "tamaño"]
        if index < len(cols):
            self.callbacks.get("ordenar")(cols[index])

    def cambiar_modo_vista(self, modo):
        """Cambia el tamaño de los iconos y la visibilidad de las columnas según el modo de vista seleccionado"""
        self.modo_vista = modo
        from PyQt6.QtCore import QSize
        
        t = self.tree
        if modo == "iconos_muy_grandes":
            t.setIconSize(QSize(96, 96))
            t.setColumnHidden(1, False)
            t.setColumnHidden(2, False)
            t.setColumnHidden(3, False)
        elif modo == "iconos_grandes":
            t.setIconSize(QSize(64, 64))
            t.setColumnHidden(1, False)
            t.setColumnHidden(2, False)
            t.setColumnHidden(3, False)
        elif modo == "iconos_medianos":
            t.setIconSize(QSize(48, 48))
            t.setColumnHidden(1, False)
            t.setColumnHidden(2, False)
            t.setColumnHidden(3, False)
        elif modo == "iconos_pequeños":
            t.setIconSize(QSize(24, 24))
            t.setColumnHidden(1, False)
            t.setColumnHidden(2, False)
            t.setColumnHidden(3, False)
        elif modo == "lista":
            t.setIconSize(QSize(16, 16))
            t.setColumnHidden(1, True)
            t.setColumnHidden(2, True)
            t.setColumnHidden(3, True)
        elif modo == "detalles":
            t.setIconSize(QSize(16, 16))
            t.setColumnHidden(1, False)
            t.setColumnHidden(2, False)
            t.setColumnHidden(3, False)

    def ajustar_columnas(self):
        """Auto-ajusta el ancho de todas las columnas al contenido"""
        hdr = self.tree.header()
        for i in range(self.tree.columnCount()):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

    def _obtener_icono(self, path_abs, is_dir=False, is_inside=False):
        if is_dir or is_inside:
            if self._folder_icon is None:
                from PyQt6.QtWidgets import QFileIconProvider
                self._folder_icon = self.icon_provider.icon(QFileIconProvider.IconType.Folder)
            return self._folder_icon

        suffix = Path(path_abs).suffix.lower()
        if suffix and suffix not in ('.exe', '.lnk', '.ico'):
            if suffix in self._icon_cache:
                return self._icon_cache[suffix]
            from PyQt6.QtCore import QFileInfo
            icon = self.icon_provider.icon(QFileInfo(str(path_abs)))
            self._icon_cache[suffix] = icon
            return icon
        
        from PyQt6.QtCore import QFileInfo
        return self.icon_provider.icon(QFileInfo(str(path_abs)))

    def actualizar_lista(self, carpetas, archivos, ruta_actual=""):
        self.header_ruta_actual = str(ruta_actual)
        
        is_inside = False
        if "is_inside_archive" in self.callbacks:
            try:
                is_inside = self.callbacks["is_inside_archive"]()
            except:
                pass
                
        if hasattr(self, "toolbar_buttons"):
            for act, btn in self.toolbar_buttons.items():
                btn.setEnabled(not is_inside)

        # 1. Filtro estricto de elementos ocultos de Windows y sistema
        def _es_oculto(nombre, is_hidden_flag):
            n = nombre.lower()
            if n.startswith('.') or n.startswith('$') or n in ('desktop.ini', 'thumbs.db', 'ntuser.dat', 'swapfile.sys', 'pagefile.sys', 'hiberfil.sys'):
                return True
            return is_hidden_flag

        mostrar_ocultos = getattr(self, "mostrar_ocultos", False)
        if not mostrar_ocultos:
            carpetas = [c for c in carpetas if not _es_oculto(c['name'], c.get('is_hidden', False))]
            archivos = [a for a in archivos if not _es_oculto(a['name'], a.get('is_hidden', False))]

        mostrar_extensiones = getattr(self, "mostrar_extensiones", False)
        mostrar_casillas = getattr(self, "mostrar_casillas", False)
        grupo_actual = getattr(self, "grupo_actual", "none")

        self.tree.clear()

        # Helper para añadir item con casillas y formateo de nombre
        def _build_item(parent_widget, text0, text1, text2, text3, icon, raw_name, is_dir):
            item = QTreeWidgetItem(parent_widget)
            item.setIcon(0, icon)
            item.setText(0, text0)
            item.setText(1, text1)
            item.setText(2, text2)
            item.setText(3, text3)
            item.setData(0, Qt.ItemDataRole.UserRole, raw_name)
            if is_dir:
                item.setForeground(0, QColor("#FACC15"))
            if mostrar_casillas:
                item.setCheckState(0, Qt.CheckState.Unchecked)
            return item

        # Si no hay agrupación
        if grupo_actual == "none":
            for c in carpetas:
                path_abs = Path(self.header_ruta_actual) / c['name']
                icon = self._obtener_icono(str(path_abs), is_dir=True, is_inside=is_inside)
                _build_item(self.tree, c['name'], c['date'], c['type'], c['size'], icon, c['name'], True)

            for a in archivos:
                path_abs = Path(self.header_ruta_actual) / a['name']
                icon = self._obtener_icono(str(path_abs), is_dir=False, is_inside=False)
                display_name = a['name'] if mostrar_extensiones else Path(a['name']).stem
                if not display_name: display_name = a['name']
                _build_item(self.tree, display_name, a['date'], a['type'], a['size'], icon, a['name'], False)
        else:
            # Agrupar por Tipo o Fecha
            grupos = {}
            for c in carpetas:
                gkey = "📁 Carpetas de archivos" if grupo_actual == "tipo" else "Carpetas"
                grupos.setdefault(gkey, []).append((c, True))
            for a in archivos:
                if grupo_actual == "tipo":
                    gkey = f"📄 Archivos {a['type'].upper()}" if a['type'] else "📄 Archivos"
                elif grupo_actual == "fecha":
                    gkey = f"📅 {a['date'].split()[0]}" if a['date'] else "📅 Desconocido"
                else:
                    gkey = f"📊 Tamaño: {a['size']}"
                grupos.setdefault(gkey, []).append((a, False))

            for gname, items in grupos.items():
                gitem = QTreeWidgetItem(self.tree)
                gitem.setText(0, gname)
                gitem.setFont(0, QFont(self.font_family, 9, QFont.Weight.Bold))
                gitem.setForeground(0, QColor(self.colores['acento']))
                gitem.setExpanded(True)
                for el, is_dir in items:
                    path_abs = Path(self.header_ruta_actual) / el['name']
                    icon = self._obtener_icono(str(path_abs), is_dir=is_dir, is_inside=is_inside)
                    display_name = el['name'] if (is_dir or mostrar_extensiones) else Path(el['name']).stem
                    if not display_name: display_name = el['name']
                    _build_item(gitem, display_name, el['date'], el['type'], el['size'], icon, el['name'], is_dir)

    def agregar_resultado_busqueda(self, data):
        """Inserta un resultado de búsqueda global con iconos nativos del sistema"""
        item = QTreeWidgetItem(self.tree)
        path_abs = data.get('path')
        
        # Obtener el icono real del sistema para este archivo/carpeta
        if path_abs and os.path.exists(path_abs):
            icon = self._obtener_icono(str(path_abs), is_dir=os.path.isdir(path_abs))
            item.setIcon(0, icon)
        
        item.setText(0, data['name'])
        item.setText(1, "En: " + os.path.dirname(data['path']))
        item.setText(2, data['type'])
        item.setText(3, data.get('size', '--'))
        item.setForeground(0, QColor(self.colores['acento']))
        item.setData(0, Qt.ItemDataRole.UserRole, data['name'])
    def get_selected_names(self):
        """Retorna la lista de todos los nombres seleccionados o marcados con casillas"""
        names = []
        checked_names = []
        
        from PyQt6.QtWidgets import QTreeWidgetItemIterator
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if item.checkState(0) == Qt.CheckState.Checked:
                name = item.data(0, Qt.ItemDataRole.UserRole)
                if name and name not in checked_names:
                    checked_names.append(name)
            iterator += 1

        if checked_names:
            return checked_names

        for item in self.tree.selectedItems():
            name = item.data(0, Qt.ItemDataRole.UserRole)
            if name and name not in names:
                names.append(name)
        return names

    def get_selected_name(self):
        names = self.get_selected_names()
        return names[0] if names else None
    
    def get_selected_full_path(self):
        sel = self.tree.selectedItems()
        if not sel: return None
        return sel[0].data(1, Qt.ItemDataRole.UserRole)

    def mostrar_comparador(self, path1, path2):
        from .diff_viewer import DiffViewerDialog
        dialog = DiffViewerDialog(self, path1, path2, self.colores)
        dialog.exec()

    def comprimir_seleccionado(self):
        selected_items = self.tree.selectedItems()
        if not selected_items: return
        from PyQt6.QtWidgets import QFileDialog
        first_name = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        suggested_zip = os.path.join(self.header_ruta_actual, first_name + ".zip")
        dest_zip, ok = QFileDialog.getSaveFileName(self, "Guardar Archivo ZIP", suggested_zip, "ZIP Archivos (*.zip)")
        if ok and dest_zip:
            from .zip_manager import ZipProgressDialog
            source_path = os.path.join(self.header_ruta_actual, first_name)
            dialog = ZipProgressDialog(self, "Comprimiendo...", self.colores)
            dialog.start_compress(source_path, dest_zip)
            dialog.exec()
            if "refrescar" in self.callbacks:
                self.callbacks["refrescar"]()

    def extraer_seleccionado(self):
        selected_items = self.tree.selectedItems()
        if not selected_items: return
        name = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        zip_path = os.path.join(self.header_ruta_actual, name)
        if not zip_path.lower().endswith(".zip"): return
        from PyQt6.QtWidgets import QFileDialog, QInputDialog, QLineEdit
        dest_dir = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Destino", self.header_ruta_actual)
        if dest_dir:
            password, ok = QInputDialog.getText(self, "Contraseña ZIP", "Contraseña (dejar vacío si no está cifrado):", QLineEdit.EchoMode.Password)
            if ok:
                from .zip_manager import ZipProgressDialog
                dialog = ZipProgressDialog(self, "Extrayendo...", self.colores)
                dialog.start_extract(zip_path, dest_dir, password if password else None)
                dialog.exec()
                if "refrescar" in self.callbacks:
                    self.callbacks["refrescar"]()

    # --- Lógica de Drag and Drop ---
    def _on_mouse_move(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton): return
        item = self.tree.itemAt(event.position().toPoint())
        if not item: return

        nombre = item.data(0, Qt.ItemDataRole.UserRole)
        ruta_abs = Path(getattr(self, "header_ruta_actual", ".")) / nombre
        
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(ruta_abs.resolve()))])
        mime.setText(nombre)

        drag = QDrag(self.tree)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)

    def _on_drag_enter(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def _on_drag_move(self, event):
        item = self.tree.itemAt(event.position().toPoint())
        if item:
            item_type = item.text(2)
            if "Carpeta" in item_type:
                self.tree.setCurrentItem(item)
        event.acceptProposedAction()

    def _on_drop(self, event):
        target_item = self.tree.itemAt(event.position().toPoint())
        nombre_origen = event.mimeData().text()
        
        if target_item:
            nombre_destino = target_item.data(0, Qt.ItemDataRole.UserRole)
            item_type = target_item.text(2)
            
            if "Carpeta" in item_type:
                if "mover_archivo" in self.callbacks:
                    self.callbacks["mover_archivo"](nombre_origen, nombre_destino)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def eventFilter(self, source, event):
        """Permite que la rueda del mouse haga scroll incluso durante un arrastre (Drag)"""
        if event.type() == event.Type.Wheel and source is self.tree.viewport():
            # Obtener el valor del scroll
            delta = event.angleDelta().y()
            v_bar = self.tree.verticalScrollBar()
            # Ajuste de velocidad de scroll: angleDelta.y() suele ser múltiplo de 120
            # singleStep es lo que se mueve por "clic" de la rueda
            pasos = delta / 120.0
            nuevo_valor = v_bar.value() - (pasos * v_bar.singleStep() * 3)
            v_bar.setValue(int(nuevo_valor))
            return True
        return super().eventFilter(source, event)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(f"background: {self.colores['bg_principal']}; border: none;")
        self.file_toolbar.setStyleSheet(f"background: {self.colores['bg_principal']}; border-bottom: 1px solid rgba(255,255,255,0.03);")
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                alternate-background-color: rgba(255, 255, 255, 0.015);
                border: none;
                outline: none;
            }}
            QTreeWidget::item {{ 
                padding: 5px 8px; 
                border-bottom: 1px solid rgba(255,255,255,0.01);
                color: rgba(255, 255, 255, 0.85);
            }}
            QTreeWidget::item:hover {{ 
                background: rgba(255, 255, 255, 0.03); 
            }}
            QTreeWidget::item:selected {{ 
                background: {self.colores['acento']}15; 
                color: {self.colores['acento']}; 
                border-left: 2px solid {self.colores['acento']};
            }}
            QHeaderView::section {{
                background: {self.colores['bg_secundario']};
                color: {self.colores['fg_secundario']};
                padding: 6px 10px;
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.05);
                font-weight: bold;
                font-size: 10px;
            }}
        """)
