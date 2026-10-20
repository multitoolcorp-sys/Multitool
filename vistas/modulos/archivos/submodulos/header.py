import os
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QWidget, QMenu, QScrollArea, QWidgetAction
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QAction

class PathLineEdit(QLineEdit):
    """Campo de texto de ruta que selecciona todo el contenido al recibir el foco"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._just_focused = False

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._just_focused = True
        self.selectAll()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self._just_focused:
            self._just_focused = False
            QTimer.singleShot(0, self.selectAll)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            header = self.parent()
            while header and not hasattr(header, "cancelar_edicion") and hasattr(header, "parent"):
                header = header.parent()
            if header and hasattr(header, "cancelar_edicion"):
                header.cancelar_edicion()
                return
        super().keyPressEvent(event)

class ClickablePathContainer(QFrame):
    """Contenedor de ruta que activa la edición al hacer clic en cualquier área vacía"""
    def __init__(self, on_empty_click, parent=None):
        super().__init__(parent)
        self.on_empty_click = on_empty_click

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.on_empty_click:
            self.on_empty_click()
        super().mousePressEvent(event)

class ClickableWidget(QWidget):
    """Widget contenedor que propaga clics en zonas vacías al callback de edición"""
    def __init__(self, on_empty_click, parent=None):
        super().__init__(parent)
        self.on_empty_click = on_empty_click

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.on_empty_click:
            self.on_empty_click()
        super().mousePressEvent(event)

class FileHeader(QFrame):
    """Cabecera con navegación, breadcrumbs y cinta de vista estilo Explorador de Windows"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.ruta_actual = ""
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "monospace"

        self.modo_edicion = False
        self.inicializar_ui()

    def inicializar_ui(self):
        self.setFixedHeight(72)
        self.setStyleSheet(f"""
            QFrame {{ 
                background: {self.colores['bg_secundario']}; 
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)
        
        # Fila 1: Ribbon de Opciones (Estilo Explorador de Windows)
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        title_lbl = QLabel("EXPLORADOR")
        title_lbl.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {self.colores['acento']};")
        row1.addWidget(title_lbl)

        # Botón desplegable unificado "👁️ Vista ▾" estilo Explorador de Windows
        self.btn_vista = QPushButton("👁️ Vista ▾")
        self.btn_vista.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white; border: none; border-radius: 6px;
                padding: 4px 12px; font-weight: bold; font-size: 11px;
                font-family: '{self.font_family}';
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', self.colores['acento'])}; }}
        """)

        menu_vista = QMenu(self)
        menu_vista.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px; padding: 6px; font-family: '{self.font_family}';
            }}
            QMenu::item {{ padding: 6px 20px; border-radius: 4px; font-size: 11px; }}
            QMenu::item:selected {{ background-color: {self.colores['acento']}; color: white; }}
            QMenu::separator {{ height: 1px; background: rgba(255,255,255,0.1); margin: 4px 0; }}
        """)

        # 1. Paneles
        m_paneles = menu_vista.addMenu("🖼️ Paneles")
        m_paneles.setStyleSheet(menu_vista.styleSheet())
        m_paneles.addAction("📂 Panel de accesos rápidos", lambda: self.callbacks.get("toggle_sidebar")())
        m_paneles.addAction("🖼️ Panel de vista previa", lambda: self.callbacks.get("toggle_preview")())

        menu_vista.addSeparator()

        # 2. Diseño
        m_diseno = menu_vista.addMenu("🎨 Diseño")
        m_diseno.setStyleSheet(menu_vista.styleSheet())
        m_diseno.addAction("🖼️ Iconos muy grandes", lambda: self.callbacks.get("cambiar_modo_vista")("iconos_muy_grandes"))
        m_diseno.addAction("🖼️ Iconos grandes", lambda: self.callbacks.get("cambiar_modo_vista")("iconos_grandes"))
        m_diseno.addAction("🖼️ Iconos medianos", lambda: self.callbacks.get("cambiar_modo_vista")("iconos_medianos"))
        m_diseno.addAction("🖼️ Iconos pequeños", lambda: self.callbacks.get("cambiar_modo_vista")("iconos_pequeños"))
        m_diseno.addAction("📜 Lista", lambda: self.callbacks.get("cambiar_modo_vista")("lista"))
        m_diseno.addAction("📋 Detalles", lambda: self.callbacks.get("cambiar_modo_vista")("detalles"))

        menu_vista.addSeparator()

        # 3. Vista actual
        m_actual = menu_vista.addMenu("📊 Vista actual")
        m_actual.setStyleSheet(menu_vista.styleSheet())

        m_sort = m_actual.addMenu("📊 Ordenar por")
        m_sort.setStyleSheet(menu_vista.styleSheet())
        for col_name in ["nombre", "fecha", "tipo", "tamaño"]:
            m_sort.addAction(col_name.capitalize(), lambda c=col_name: self.callbacks.get("ordenar")(c))

        m_group = m_actual.addMenu("📑 Agrupar por")
        m_group.setStyleSheet(menu_vista.styleSheet())
        for gkey, glabel in [("none", "(Ninguno)"), ("tipo", "Tipo"), ("fecha", "Fecha"), ("tamaño", "Tamaño")]:
            m_group.addAction(glabel, lambda g=gkey: self.callbacks.get("agrupar_por")(g))

        m_cols = m_actual.addMenu("📋 Agregar columnas")
        m_cols.setStyleSheet(menu_vista.styleSheet())
        for idx_c, name_c in enumerate(["Nombre", "Fecha de modificación", "Tipo", "Tamaño"]):
            m_cols.addAction(f"✓ {name_c}", lambda idx=idx_c: self.callbacks.get("toggle_columna")(idx))
        m_cols.addAction("⚙️ Elegir columnas...", lambda: self.callbacks.get("elegir_columnas_dialog")())

        m_actual.addAction("↔️ Ajustar todas las columnas", lambda: self.callbacks.get("ajustar_columnas")())

        menu_vista.addSeparator()

        # 4. Mostrar u Ocultar (Checkable Actions)
        self.act_boxes = menu_vista.addAction("☐ Casillas de elemento")
        self.act_boxes.setCheckable(True)
        self.act_boxes.setChecked(False)
        self.act_boxes.toggled.connect(lambda st: self.callbacks.get("toggle_casillas")(st))

        self.act_ext = menu_vista.addAction("☐ Extensiones de nombre de archivo")
        self.act_ext.setCheckable(True)
        self.act_ext.setChecked(False)
        self.act_ext.toggled.connect(lambda st: self.callbacks.get("toggle_extensiones")(st))

        self.act_hid = menu_vista.addAction("☐ Elementos ocultos")
        self.act_hid.setCheckable(True)
        self.act_hid.setChecked(False)
        self.act_hid.toggled.connect(lambda st: self.callbacks.get("toggle_ocultos")(st))

        self.btn_vista.setMenu(menu_vista)
        row1.addWidget(self.btn_vista)

        row1.addStretch()

        # Campo de búsqueda rápida
        search_lay = QHBoxLayout()
        search_lay.setSpacing(4)
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("🔍 Filtrar...")
        self.search_field.setFixedWidth(180)
        self.search_field.setFixedHeight(26)
        self.search_field.setFont(QFont(self.font_family, 8))
        self.search_field.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 13px; padding: 0 10px;
            }}
            QLineEdit:focus {{ border: 1px solid {self.colores['acento']}; }}
        """)
        self.search_field.textChanged.connect(self._on_search_changed)
        search_lay.addWidget(self.search_field)
        
        self.btn_global_search = QPushButton("🌍")
        self.btn_global_search.setFixedSize(26, 26)
        self.btn_global_search.setToolTip("Búsqueda Global Recursiva")
        self.btn_global_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_global_search.setStyleSheet(f"""
            QPushButton {{ 
                background: {self.colores['bg_terciario']}; border: 1px solid rgba(255,255,255,0.1); 
                border-radius: 13px; color: white; font-size: 10px;
            }}
            QPushButton:hover {{ background: {self.colores['acento']}; border: none; }}
        """)
        self.btn_global_search.clicked.connect(lambda: self.callbacks.get("busqueda_global")(self.search_field.text()))
        search_lay.addWidget(self.btn_global_search)
        
        row1.addLayout(search_lay)
        layout.addLayout(row1)

        # Fila 2: Ruta Interactiva (Breadcrumbs) y Navegación
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        
        btn_nav_style = f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: white; border: none; border-radius: 6px;
                padding: 3px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {self.colores['acento']}; }}
        """
        
        self.btn_back = QPushButton("⬅")
        self.btn_back.setFixedSize(28, 28)
        self.btn_back.setStyleSheet(btn_nav_style)
        self.btn_back.clicked.connect(self.callbacks.get("subir_nivel"))
        row2.addWidget(self.btn_back)
        
        self.btn_home = QPushButton("🏠")
        self.btn_home.setFixedSize(28, 28)
        self.btn_home.setStyleSheet(btn_nav_style)
        self.btn_home.clicked.connect(self.callbacks.get("ir_inicio"))
        row2.addWidget(self.btn_home)
        
        # Barra de Ruta con Breadcrumbs Interactivos (Clic en espacio vacío activa edición)
        self.path_container = ClickablePathContainer(self.activar_modo_edicion)
        self.path_container.setFixedHeight(28)
        self.path_container.setCursor(Qt.CursorShape.IBeamCursor)
        self.path_container.setStyleSheet(f"""
            QFrame {{ 
                background: {self.colores['bg_terciario']}; 
                border-radius: 6px; 
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        self.path_lay = QHBoxLayout(self.path_container)
        self.path_lay.setContentsMargins(6, 0, 6, 0)
        self.path_lay.setSpacing(2)
        
        btn_tree = QPushButton("🌲")
        btn_tree.setFixedSize(22, 22)
        btn_tree.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_tree.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(255,255,255,0.1); border-radius: 4px; }")
        btn_tree.clicked.connect(self.callbacks.get("mostrar_arbol_carpetas"))
        self.path_lay.addWidget(btn_tree)

        # Contenedor dinámico para botones de migas de pan (Breadcrumbs)
        self.breadcrumbs_widget = ClickableWidget(self.activar_modo_edicion)
        self.breadcrumbs_widget.setStyleSheet("background: transparent; border: none;")
        self.breadcrumbs_lay = QHBoxLayout(self.breadcrumbs_widget)
        self.breadcrumbs_lay.setContentsMargins(0, 0, 0, 0)
        self.breadcrumbs_lay.setSpacing(2)
        self.path_lay.addWidget(self.breadcrumbs_widget)

        self.ent_ruta = PathLineEdit()
        self.ent_ruta.setFont(QFont(self.mono_font, 9))
        self.ent_ruta.setStyleSheet("background: transparent; color: #E0E0E0; border: none; padding: 2px 5px;")
        self.ent_ruta.returnPressed.connect(self._on_path_return)
        self.ent_ruta.hide()  # Se muestra al hacer doble clic o editar
        self.path_lay.addWidget(self.ent_ruta)
        
        self.path_lay.addStretch()

        btn_edit_path = QPushButton("✏️")
        btn_edit_path.setFixedSize(22, 22)
        btn_edit_path.setToolTip("Editar ruta como texto")
        btn_edit_path.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit_path.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 11px; } QPushButton:hover { background: rgba(255,255,255,0.1); border-radius: 4px; }")
        btn_edit_path.clicked.connect(self.toggle_modo_edicion)
        self.path_lay.addWidget(btn_edit_path)

        btn_goto = QPushButton("📂")
        btn_goto.setFixedSize(22, 22)
        btn_goto.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_goto.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(255,255,255,0.1); border-radius: 4px; }")
        btn_goto.clicked.connect(self.callbacks.get("seleccionar_directorio"))
        self.path_lay.addWidget(btn_goto)
        
        row2.addWidget(self.path_container, 1)
        layout.addLayout(row2)

    def toggle_modo_edicion(self):
        if self.modo_edicion:
            self.cancelar_edicion()
        else:
            self.activar_modo_edicion()

    def activar_modo_edicion(self):
        if not self.modo_edicion:
            self.modo_edicion = True
            self.breadcrumbs_widget.hide()
            self.ent_ruta.show()
            self.ent_ruta.setFocus()
            self.ent_ruta.selectAll()

    def cancelar_edicion(self):
        if self.modo_edicion:
            self.modo_edicion = False
            self.ent_ruta.hide()
            self.breadcrumbs_widget.show()

    def _on_path_return(self):
        texto = self.ent_ruta.text().strip()
        self.modo_edicion = False
        self.ent_ruta.hide()
        self.breadcrumbs_widget.show()
        if texto.lower() == "cmd":
            self.callbacks.get("ejecutar_comando_ruta")("cmd")
            self.callbacks.get("refrescar")()
        else:
            self.callbacks.get("ir_a_ruta_manual")(texto)

    def _on_search_changed(self, text):
        if "filtrar_por_texto" in self.callbacks:
            self.callbacks["filtrar_por_texto"](text)

    def set_ruta(self, ruta_texto):
        self.ruta_actual = ruta_texto
        self.ent_ruta.setText(ruta_texto)
        self.ent_ruta.setCursorPosition(len(ruta_texto))
        self._actualizar_breadcrumbs(ruta_texto)

    def _mostrar_subcarpetas_menu(self, ruta_padre, btn_sender):
        """Muestra un menú desplegable con scrollbar vertical con las carpetas y archivos del segmento de ruta"""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores['bg_secundario']};
                color: #E2E8F0; 
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px; 
                padding: 4px; 
                font-family: '{self.font_family}';
            }}
        """)
        try:
            from PyQt6.QtWidgets import QFileIconProvider
            from PyQt6.QtCore import QFileInfo
            icon_provider = QFileIconProvider()
            
            subdirs = []
            files = []
            for entry in os.scandir(ruta_padre):
                if entry.name.startswith('.') or entry.name.startswith('$'):
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        subdirs.append(entry.name)
                    elif entry.is_file(follow_symlinks=False):
                        files.append(entry.name)
                except Exception:
                    continue
                    
            subdirs.sort(key=str.lower)
            files.sort(key=str.lower)
            
            total_items = len(subdirs) + len(files)
            if total_items == 0:
                act = menu.addAction("(Carpeta vacía)")
                act.setEnabled(False)
            else:
                scroll_container = QWidget()
                scroll_container.setStyleSheet("background: transparent; border: none;")
                scroll_lay = QVBoxLayout(scroll_container)
                scroll_lay.setContentsMargins(4, 4, 4, 4)
                scroll_lay.setSpacing(2)

                for sname in subdirs:
                    target = os.path.join(ruta_padre, sname)
                    icon = icon_provider.icon(QFileInfo(target))
                    btn = QPushButton(f" {sname}")
                    btn.setIcon(icon)
                    btn.setIconSize(QSize(16, 16))
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setFont(QFont(self.font_family, 9))
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            color: {self.colores.get('fg_principal', '#FFFFFF')};
                            border: none;
                            text-align: left;
                            padding: 6px 12px;
                            border-radius: 4px;
                        }}
                        QPushButton:hover {{
                            background-color: {self.colores['acento']};
                            color: #FFFFFF;
                            font-weight: bold;
                        }}
                    """)
                    btn.clicked.connect(lambda ch, t=target: (self.callbacks.get("ir_a_ruta_manual")(t), menu.close()))
                    scroll_lay.addWidget(btn)

                if subdirs and files:
                    div = QFrame()
                    div.setFixedHeight(1)
                    div.setStyleSheet("background: rgba(255,255,255,0.1); margin: 4px 6px;")
                    scroll_lay.addWidget(div)

                for fname in files:
                    target = os.path.join(ruta_padre, fname)
                    icon = icon_provider.icon(QFileInfo(target))
                    btn = QPushButton(f" {fname}")
                    btn.setIcon(icon)
                    btn.setIconSize(QSize(16, 16))
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setFont(QFont(self.font_family, 9))
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            color: {self.colores.get('fg_secundario', '#CBD5E1')};
                            border: none;
                            text-align: left;
                            padding: 6px 12px;
                            border-radius: 4px;
                        }}
                        QPushButton:hover {{
                            background-color: {self.colores['acento']};
                            color: #FFFFFF;
                            font-weight: bold;
                        }}
                    """)
                    btn.clicked.connect(lambda ch, t=target: (self._abrir_o_seleccionar_archivo(t), menu.close()))
                    scroll_lay.addWidget(btn)

                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QFrame.Shape.NoFrame)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                altura = min(380, max(120, total_items * 32 + 10))
                scroll.setFixedSize(260, altura)
                scroll.setStyleSheet(f"""
                    QScrollArea {{
                        background-color: {self.colores['bg_secundario']};
                        border: none;
                    }}
                    QScrollBar:vertical {{
                        background: rgba(0, 0, 0, 0.2);
                        width: 7px;
                        border-radius: 3px;
                        margin: 0px;
                    }}
                    QScrollBar::handle:vertical {{
                        background: {self.colores['acento']};
                        min-height: 25px;
                        border-radius: 3px;
                    }}
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                        height: 0px;
                    }}
                """)
                scroll.setWidget(scroll_container)

                action = QWidgetAction(menu)
                action.setDefaultWidget(scroll)
                menu.addAction(action)

        except Exception as e:
            print(f"Error cargando subcarpetas: {e}")
            act = menu.addAction("(Error leyendo carpeta)")
            act.setEnabled(False)

        pos = btn_sender.mapToGlobal(btn_sender.rect().bottomLeft())
        menu.exec(pos)

    def _abrir_o_seleccionar_archivo(self, ruta_archivo):
        """Abre un archivo directamente desde el menú de la ruta"""
        try:
            if platform.system() == "Windows":
                os.startfile(ruta_archivo)
            elif platform.system() == "Darwin":
                import subprocess
                subprocess.call(["open", ruta_archivo])
            else:
                import subprocess
                subprocess.call(["xdg-open", ruta_archivo])
        except Exception as e:
            print(f"Error al abrir archivo {ruta_archivo}: {e}")

    def _actualizar_breadcrumbs(self, ruta_texto):
        # Limpiar botones anteriores
        while self.breadcrumbs_lay.count():
            item = self.breadcrumbs_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not ruta_texto or ruta_texto == "trash":
            lbl = QLabel("🗑️ Papelera de Reciclaje" if ruta_texto == "trash" else "Inicio")
            lbl.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
            self.breadcrumbs_lay.addWidget(lbl)
            return
            
        # Construir botones intermedios
        p = Path(self.ruta_actual)
        partes = list(p.parts)
        
        for i, parte in enumerate(partes):
            sub_ruta = str(Path(*partes[:i+1]))
            texto_btn = parte
            if parte.endswith("\\") or parte.endswith("/"):
                texto_btn = parte.rstrip("\\/")
                
            btn = QPushButton(texto_btn)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #E0E0E0; border: none;
                    padding: 2px 6px; font-size: 11px; border-radius: 4px;
                }
                QPushButton:hover { background: rgba(255, 255, 255, 0.1); color: white; }
            """)
            btn.clicked.connect(lambda checked, r=sub_ruta: self.callbacks.get("ir_a_ruta_manual")(r))
            self.breadcrumbs_lay.addWidget(btn)
            
            # Botón de flecha '▸' para desplegar subcarpetas del nivel
            btn_arrow = QPushButton("▸")
            btn_arrow.setFixedSize(16, 16)
            btn_arrow.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_arrow.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #888; border: none;
                    font-size: 9px; border-radius: 3px;
                }
                QPushButton:hover { background: rgba(255, 255, 255, 0.15); color: #FFF; }
            """)
            btn_arrow.clicked.connect(lambda checked, r=sub_ruta, b=btn_arrow: self._mostrar_subcarpetas_menu(r, b))
            self.breadcrumbs_lay.addWidget(btn_arrow)
