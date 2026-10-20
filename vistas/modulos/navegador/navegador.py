import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QMessageBox, QInputDialog, 
    QTabWidget, QDialog, QGridLayout, QLabel, QLineEdit, 
    QComboBox, QDialogButtonBox, QPushButton, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont

from .submodulos.externo import TabNavegadorExterno
from .submodulos.integrado import TabNavegadorIntegrado
from .submodulos.favoritos import TabNavegadorFavoritos
from .submodulos.explorar import TabNavegadorExplorar
from .submodulos.gui_email import EmailGUI
from .submodulos.historial_view import TabNavegadorHistorial
from .submodulos.descargas import TabNavegadorDescargas
from .utils.navigation_manager import NavigationManager, PYQT_WEBENGINE_AVAILABLE
from .utils.favorites_manager import FavoritesManager

class TabNavegador(QWidget):
    def __init__(self, parent, context=None):
        super().__init__(parent)
        self.context = context
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        
        # Paleta de colores - Intentar obtener del contexto, del app o usar default completo
        app = getattr(context, "app", None)
        self.colores = getattr(app, "COLORES", {
            "bg_principal": "#1E1E1E", "bg_secundario": "#2D2D2D", "bg_terciario": "#3D3D3D",
            "fg_principal": "#E0E0E0", "fg_secundario": "#A0A0A0", "acento": "#6366F1", 
            "acento_hover": "#818CF8", "exito": "#43A047", "error": "#E53935", "advertencia": "#FDD835"
        }) if app else {
            "bg_principal": "#1E1E1E", "bg_secundario": "#2D2D2D", "bg_terciario": "#3D3D3D",
            "fg_principal": "#E0E0E0", "fg_secundario": "#A0A0A0", "acento": "#6366F1", 
            "acento_hover": "#818CF8", "exito": "#43A047", "error": "#E53935", "advertencia": "#FDD835"
        }
        
        # Callbacks para la GUI
        self.callbacks = {
            "navegador_comando": self.navegador_comando,
            "navegador_ir": self.navegador_ir,
            "abrir_url_integrada": self.abrir_url_integrada,
            "abrir_nueva_pestana_integrada": self.abrir_nueva_pestana_integrada,
            "guardar_link": self.guardar_link,
            "guardar_link_integrado": self.guardar_link_integrado,
            "mostrar_aclaraciones": self.mostrar_aclaraciones,
            "filtrar_historial": self.filtrar_historial,
            "limpiar_historial": self.limpiar_historial,
            "abrir_desde_historial": self.abrir_desde_historial,
            "abrir_desde_historial_reciente": self.abrir_desde_historial_reciente,
            "mostrar_detalles_favorito": self.mostrar_detalles_favorito,
            "nueva_categoria": self.nueva_categoria,
            "eliminar_categoria": self.eliminar_categoria,
            "abrir_favorito_seleccionado": self.abrir_favorito_seleccionado,
            "editar_favorito": self.editar_favorito,
            "eliminar_favorito": self.eliminar_favorito,
            "abrir_desde_favoritos": self.abrir_desde_favoritos,
            "filtrar_favoritos": self.filtrar_favoritos,
            "cambiar_tab": self.cambiar_tab,
            "actualizar_explorar": self.actualizar_explorar
        }
        
        # Callback para notificaciones
        if app and hasattr(app, "mostrar_notificacion"):
            self.callbacks["mostrar_notificacion"] = lambda msg: app.mostrar_notificacion("Navegador", msg)
        else:
            self.callbacks["mostrar_notificacion"] = lambda msg: print(f"[NAV-NOTIF] {msg}")

        # Inicializar Navigation Manager y callbacks de historial antes de la UI
        self.nav_manager = NavigationManager(self.ruta_usuario)
        self.nav_manager.hist_callback = self.actualizar_lista_historial
        self.callbacks["añadir_historial"] = self.nav_manager.añadir_historial
        self.callbacks["guardar_historial"] = self.nav_manager.añadir_historial

        # 1. Inicializar UI (Crea los submódulos con los callbacks activos)
        self.inicializar_ui()

        self.nav_manager.url_callback = lambda u: self.sub_externo.txt_url.setText(u) if hasattr(self, "sub_externo") and hasattr(self.sub_externo, "txt_url") else None
        self.nav_manager.url_integrado_callback = lambda u: self.sub_integrado.web_view.load(QUrl(u)) if hasattr(self, "sub_integrado") and self.sub_integrado and hasattr(self.sub_integrado, "web_view") else None
        
        self.fav_manager = FavoritesManager(self.ruta_usuario)
        self.fav_manager.listbox_callback = self.actualizar_datos_favoritos
        
        # 3. Carga inicial de datos
        self.actualizar_lista_historial()
        self.actualizar_datos_favoritos()
        self.actualizar_explorar()

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Main TabWidget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ 
                border: 0; 
                background: {self.colores['bg_principal']};
                margin-top: -1px;
            }}
            QTabBar::tab {{ 
                background: transparent; 
                color: {self.colores['fg_secundario']};
                padding: 8px 20px;
                font-family: 'Inter';
                font-weight: 600;
                font-size: 11px;
                border-bottom: 2px solid transparent;
                margin-right: 8px;
            }}
            QTabBar::tab:hover {{ 
                color: {self.colores['fg_principal']};
                background: {self.colores['bg_secundario']};
                border-top-left-radius: 8px; border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{ 
                background: rgba(99, 102, 241, 0.05);
                color: {self.colores['acento']}; 
                border-bottom: 2px solid {self.colores['acento']};
            }}
        """)
        
        # Crear Instancias de Submódulos
        self.sub_externo = TabNavegadorExterno(self, self.colores, self.callbacks)
        self.sub_integrado = TabNavegadorIntegrado(self, self.colores, self.callbacks, self.ruta_usuario)
        self.sub_favoritos = TabNavegadorFavoritos(self, self.colores, self.callbacks)
        self.sub_explorar = TabNavegadorExplorar(self, self.colores, self.callbacks)
        self.sub_historial = TabNavegadorHistorial(self, self.colores, self.callbacks)
        self.sub_email = EmailGUI(self, self.colores, self.context)
        self.sub_descargas = TabNavegadorDescargas(self, self.colores, self.callbacks, self.context)
        
        # Añadir Tabs
        self.tabs.addTab(self.sub_externo, "🌎 EXTERNO")
        self.tabs.addTab(self.sub_integrado, "🧩 INTEGRADO")
        self.tabs.addTab(self.sub_favoritos, "⭐ FAVORITOS")
        self.tabs.addTab(self.sub_explorar, "🧭 EXPLORAR")
        self.tabs.addTab(self.sub_historial, "📜 HISTORIAL")
        self.tabs.addTab(self.sub_email, "📧 CLIENTE GMAIL")
        self.tabs.addTab(self.sub_descargas, "⚡ DESCARGAS")
        
        # Botón Extender
        self.btn_extender = QPushButton("🚀 Extender")
        self.btn_extender.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_extender.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 15px;
                font-family: 'Inter';
                font-weight: bold;
                margin: 2px 8px;
            }}
            QPushButton:hover {{
                background: {self.colores['acento_hover']};
            }}
        """)
        self.btn_extender.clicked.connect(self.abrir_navegador_extendido)
        self.tabs.setCornerWidget(self.btn_extender, Qt.Corner.TopRightCorner)
        
        self.main_layout.addWidget(self.tabs)

        # Restaurar sub-pestaña activa
        self.nav_state_file = self.ruta_usuario / "browser_data" / "nav_state.json"
        self._restaurar_submodulo_activo()
        self.tabs.currentChanged.connect(self._guardar_submodulo_activo)

    def _guardar_submodulo_activo(self, index):
        if index != 1:
            self.desenfocar_web()
        try:
            self.nav_state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.nav_state_file, "w", encoding="utf-8") as f:
                json.dump({"active_subtab": index}, f)
        except Exception:
            pass

    def desenfocar_web(self):
        """Desenfoca las vistas web del navegador para que no capturen teclado."""
        try:
            if hasattr(self, "sub_integrado") and hasattr(self.sub_integrado, "desenfocar_todo"):
                self.sub_integrado.desenfocar_todo()
        except Exception:
            pass
        try:
            win = self.window()
            if win:
                win.setFocus()
        except Exception:
            pass

    def hideEvent(self, event):
        super().hideEvent(event)
        self.desenfocar_web()

    def _restaurar_submodulo_activo(self):
        try:
            if self.nav_state_file.exists():
                with open(self.nav_state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    idx = data.get("active_subtab", 0)
                    if 0 <= idx < self.tabs.count():
                        self.tabs.setCurrentIndex(idx)
        except Exception:
            pass

    def toggle_fullscreen_mode(self, is_fullscreen):
        """Oculta o muestra la barra de pestañas de submódulos y las pestañas web del navegador integrado."""
        if hasattr(self, "tabs") and hasattr(self.tabs, "tabBar"):
            self.tabs.tabBar().setVisible(not is_fullscreen)
        if hasattr(self, "btn_extender"):
            self.btn_extender.setVisible(not is_fullscreen)
        if hasattr(self, "sub_integrado") and self.sub_integrado:
            if hasattr(self.sub_integrado, "toggle_fullscreen_mode"):
                self.sub_integrado.toggle_fullscreen_mode(is_fullscreen)

    def abrir_navegador_extendido(self):
        url_actual = "https://www.google.com"
        if self.sub_externo and hasattr(self.sub_externo, "txt_url"):
            url_actual = self.sub_externo.txt_url.text() or url_actual
        elif self.sub_integrado and hasattr(self.sub_integrado, "txt_url"):
            url_actual = self.sub_integrado.txt_url.text() or url_actual
        from .utils.webview2_runner import lanzar_ventana_webview2
        lanzar_ventana_webview2(url_actual)

    def actualizar_tema(self, colores):
        """Actualiza la paleta de colores del módulo Navegador y de todos sus submódulos."""
        if not colores:
            return
        self.colores = colores
        if hasattr(self, "tabs"):
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane {{ 
                    border: 0; 
                    background: {self.colores['bg_principal']};
                    margin-top: -1px;
                }}
                QTabBar::tab {{ 
                    background: transparent; 
                    color: {self.colores['fg_secundario']};
                    padding: 8px 20px;
                    font-family: 'Inter';
                    font-weight: 600;
                    font-size: 11px;
                    border-bottom: 2px solid transparent;
                    margin-right: 8px;
                }}
                QTabBar::tab:hover {{ 
                    color: {self.colores['fg_principal']};
                    background: {self.colores['bg_secundario']};
                    border-top-left-radius: 8px; border-top-right-radius: 8px;
                }}
                QTabBar::tab:selected {{ 
                    background: rgba(99, 102, 241, 0.05);
                    color: {self.colores['acento']}; 
                    border-bottom: 2px solid {self.colores['acento']};
                }}
            """)

        submodulos = [
            getattr(self, "sub_externo", None),
            getattr(self, "sub_integrado", None),
            getattr(self, "sub_favoritos", None),
            getattr(self, "sub_explorar", None),
            getattr(self, "sub_historial", None),
            getattr(self, "sub_email", None),
            getattr(self, "sub_descargas", None),
        ]
        for sub in submodulos:
            if sub and hasattr(sub, "actualizar_tema"):
                try:
                    sub.actualizar_tema(colores)
                except Exception:
                    pass

    # --- IMPLEMENTACIÓN DE CALLBACKS ---
    def navegador_comando(self, comando):
        from .utils.webview2_runner import lanzar_ventana_webview2
        if comando in ("go_edge", "ir_integrado"):
            url = self.sub_externo.txt_url.text() if hasattr(self.sub_externo, "txt_url") else "https://www.google.com"
            lanzar_ventana_webview2(url)
            self.nav_manager.añadir_historial(url)
        elif comando == "go": 
            self.nav_manager.navegador_ir(self.sub_externo.txt_url.text())
        elif comando == "home": 
            self.nav_manager.navegador_ir("https://www.google.com")
        else: pass

    def navegador_ir(self, url): 
        self.nav_manager.navegador_ir(url)

    def abrir_url_integrada(self, url): 
        if self.sub_integrado and hasattr(self.sub_integrado, "add_new_tab"):
            self.tabs.setCurrentWidget(self.sub_integrado)
            self.sub_integrado.add_new_tab(QUrl(url), "Cargando...")
        else:
            from .utils.webview2_runner import lanzar_ventana_webview2
            lanzar_ventana_webview2(url)
        self.nav_manager.añadir_historial(url)
        
    def abrir_nueva_pestana_integrada(self, url, label="Nueva Pestaña"):
        if self.sub_integrado and hasattr(self.sub_integrado, "add_new_tab"):
            self.tabs.setCurrentWidget(self.sub_integrado)
            self.sub_integrado.add_new_tab(QUrl(url), label)
        else:
            from .utils.webview2_runner import lanzar_ventana_webview2
            lanzar_ventana_webview2(url)
        self.nav_manager.añadir_historial(url)

    def guardar_link(self):
        url = self.sub_externo.txt_url.text()
        if not url: return
        self.mostrar_dialogo_guardar_favorito(url, "Marcador Externo")

    def guardar_link_integrado(self, titulo=None, url=None):
        if not url:
            if hasattr(self.sub_integrado, "current_browser") and self.sub_integrado.current_browser():
                b = self.sub_integrado.current_browser()
                url = b.url().toString() if hasattr(b, "url") else ""
                titulo = b.title() if hasattr(b, "title") else "Marcador Web"
            elif hasattr(self.sub_integrado, "url_bar"):
                url = self.sub_integrado.url_bar.text()
        if not url: return
        self.mostrar_dialogo_guardar_favorito(url, titulo or "Nuevo Marcador")

    def mostrar_dialogo_guardar_favorito(self, url, titulo_defecto=""):
        # Diálogo Avanzado de Guardado unificado
        dialog = QDialog(self)
        dialog.setWindowTitle("Guardar en Favoritos")
        dialog.setFixedWidth(350)
        dialog.setStyleSheet(f"""
            QDialog {{ background: {self.colores['bg_principal']}; border-radius: 12px; }}
            QLabel {{ color: white; font-weight: bold; font-size: 9pt; }}
            QLineEdit, QComboBox {{ 
                background: {self.colores['bg_secundario']}; color: white; border: 1px solid rgba(255,255,255,0.1); 
                border-radius: 8px; padding: 10px; font-size: 9pt;
            }}
            QPushButton {{ 
                padding: 10px; border-radius: 8px; font-weight: bold; 
            }}
        """)
        
        lay = QVBoxLayout(dialog)
        lay.setSpacing(15)
        lay.setContentsMargins(20, 20, 20, 20)
        
        lay.addWidget(QLabel("Nombre del Marcador:"))
        txt_nombre = QLineEdit()
        txt_nombre.setText(titulo_defecto)
        lay.addWidget(txt_nombre)
        
        lay.addWidget(QLabel("Categoría / Carpeta:"))
        combo_cat = QComboBox()
        cats = self.fav_manager.obtener_categorias()
        combo_cat.addItems(cats)
        combo_cat.addItem("+ Nueva Categoría...")
        lay.addWidget(combo_cat)
        
        # Campo oculto para nueva categoría
        txt_nueva_cat = QLineEdit()
        txt_nueva_cat.setPlaceholderText("Nombre de la nueva carpeta...")
        txt_nueva_cat.setVisible(False)
        lay.addWidget(txt_nueva_cat)
        
        def toggle_new_cat(index):
            txt_nueva_cat.setVisible(combo_cat.currentText() == "+ Nueva Categoría...")
            
        combo_cat.currentIndexChanged.connect(toggle_new_cat)
        
        btns = QVBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white;")
        btn_cancel.clicked.connect(dialog.reject)
        
        btn_ok = QPushButton("Guardar ⭐")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(f"background: {self.colores['acento']}; color: white;")
        
        def save():
            nombre = txt_nombre.text().strip()
            if not nombre: return
            
            cat = combo_cat.currentText()
            if cat == "+ Nueva Categoría...":
                cat = txt_nueva_cat.text().strip() or "General"
                
            self.fav_manager.añadir_favorito(nombre, url, cat)
            self.actualizar_datos_favoritos()
            dialog.accept()
            
        btn_ok.clicked.connect(save)
        
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)
        lay.addLayout(btns)
        
        dialog.exec()

    def actualizar_lista_historial(self):
        self.sub_externo.tree_historial.clear()
        if hasattr(self, 'sub_historial') and self.sub_historial:
            self.sub_historial.tree_historial.clear()

        busq = self.sub_externo.txt_hist_search.text().lower()
        
        # Agrupar por fechas
        grupos_fecha = {}
        for e in self.nav_manager.historial:
            if hasattr(self, 'sub_historial') and self.sub_historial:
                item_h = QTreeWidgetItem([e.get("titulo", "Sin título"), e.get("url", ""), e.get("fecha", "")])
                self.sub_historial.tree_historial.addTopLevelItem(item_h)

            if not busq or busq in e["titulo"].lower() or busq in e["url"].lower():
                fecha_dia = e["fecha"].split(" ")[0] if " " in e["fecha"] else "Desconocido"
                if fecha_dia not in grupos_fecha:
                    grupos_fecha[fecha_dia] = []
                grupos_fecha[fecha_dia].append(e)
                
        # Construir el árbol
        for fecha, items in grupos_fecha.items():
            nodo_fecha = QTreeWidgetItem([f"📅 {fecha}"])
            nodo_fecha.setFont(0, QFont("Inter", 11, QFont.Weight.Bold))
            nodo_fecha.setFlags(nodo_fecha.flags() & ~Qt.ItemFlag.ItemIsSelectable) # No seleccionable para abrir
            
            for item in items:
                hora = item["fecha"].split(" ")[1] if " " in item["fecha"] else ""
                nodo_link = QTreeWidgetItem([f"[{hora}] {item['titulo']}"])
                nodo_link.setData(0, Qt.ItemDataRole.UserRole, item["url"]) # Guardamos la URL de forma segura
                nodo_fecha.addChild(nodo_link)
                
            self.sub_externo.tree_historial.addTopLevelItem(nodo_fecha)
            nodo_fecha.setExpanded(True)

    def filtrar_historial(self): self.actualizar_lista_historial()
    
    def limpiar_historial(self):
        btn = QMessageBox.question(self, "Confirmar", "¿Desea borrar todo el historial?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if btn == QMessageBox.StandardButton.Yes:
            self.nav_manager.limpiar_historial()
            self.actualizar_lista_historial()
    
    def abrir_desde_historial(self):
        item = self.sub_externo.tree_historial.currentItem()
        if not item or item.childCount() > 0: 
            return # Evitamos procesar si es un padre (carpeta de fecha)
            
        url = item.data(0, Qt.ItemDataRole.UserRole)
        if url:
            # Consistencia UX: Permitir elegir navegador al dar doble clic en el historial
            self._seleccionar_navegador_y_abrir(url)

    def abrir_desde_historial_reciente(self):
        pass # No implementado en esta versión modular

    def cambiar_tab(self, index):
        self.tabs.setCurrentIndex(index)

    def actualizar_datos_favoritos(self):
        """Poblar el QTreeWidget de favoritos jerárquicamente"""
        from PyQt6.QtWidgets import QTreeWidgetItem
        from PyQt6.QtCore import Qt
        
        self.sub_favoritos.tree_favoritos.clear()
        
        # Agrupar favoritos por categoría
        cats = {}
        for f in self.fav_manager.favoritos:
            c = f.get("categoria", "General")
            if c not in cats:
                cat_item = QTreeWidgetItem(self.sub_favoritos.tree_favoritos)
                cat_item.setText(0, f"📂 {c}")
                cat_item.setText(1, f"Carpeta")
                cat_item.setFont(0, QFont("Inter", 10, QFont.Weight.Bold))
                cat_item.setForeground(0, Qt.GlobalColor.white)
                cat_item.setExpanded(True)
                cats[c] = cat_item
            
            fav_item = QTreeWidgetItem(cats[c])
            fav_item.setText(0, f"⭐ {f['nombre']}")
            fav_item.setText(1, f['url'])
            fav_item.setText(2, f.get('fecha', '--'))
            fav_item.setData(0, Qt.ItemDataRole.UserRole, f) # Objeto completo
            
    def filtrar_favoritos(self):
        """Filtrado dinámico en tiempo real para el TreeView (Recorrido Jerárquico Eficiente)"""
        busq = self.sub_favoritos.txt_fav_search.text().lower()
        
        root = self.sub_favoritos.tree_favoritos.invisibleRootItem()
        for i in range(root.childCount()):
            cat_item = root.child(i)
            cat_visible = False
            for j in range(cat_item.childCount()):
                fav_item = cat_item.child(j)
                match = busq in fav_item.text(0).lower() or busq in fav_item.text(1).lower()
                fav_item.setHidden(not match)
                if match:
                    cat_visible = True
            cat_item.setHidden(not cat_visible)

    def abrir_desde_favoritos(self): self.abrir_favorito_seleccionado()

    def abrir_favorito_seleccionado(self):
        item = self.sub_favoritos.tree_favoritos.currentItem()
        if not item or item.parent() is None: return # No es un link o nada seleccionado
        
        fav = item.data(0, Qt.ItemDataRole.UserRole)
        if fav and "url" in fav:
            self._seleccionar_navegador_y_abrir(fav["url"])

    def actualizar_explorar(self):
        if hasattr(self, "sub_explorar"):
            self.sub_explorar.popular_cuadros()

    def _seleccionar_navegador_y_abrir(self, url):
        dialog = QDialog(self)
        dialog.setWindowTitle("Abrir Marcador")
        dialog.setFixedSize(320, 230)
        dialog.setStyleSheet(f"""
            QDialog {{ background: {self.colores['bg_principal']}; border: 1px solid {self.colores['bg_terciario']}; border-radius: 12px; }}
            QLabel {{ color: white; font-family: 'Inter'; }}
            QPushButton {{ 
                background: {self.colores['bg_secundario']}; 
                color: white; 
                border-radius: 10px; 
                padding: 10px; 
                font-family: 'Inter'; 
                font-weight: bold;
                font-size: 11px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            QPushButton:hover {{ background: {self.colores['acento']}; border: 1px solid {self.colores['acento']}; }}
        """)
        
        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        
        lbl = QLabel("¿Dónde deseas abrir este sitio?")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Inter", 10))
        lay.addWidget(lbl)
        
        btn_edge = QPushButton("⚡ EDGE (WEBVIEW2)")
        btn_edge.setCursor(Qt.CursorShape.PointingHandCursor)
        def abrir_edge():
            from .utils.webview2_runner import lanzar_ventana_webview2
            lanzar_ventana_webview2(url)
            self.nav_manager.añadir_historial(url)
            dialog.accept()
        btn_edge.clicked.connect(abrir_edge)
        lay.addWidget(btn_edge)

        btn_int = QPushButton("🧩 NAVEGADOR INTEGRADO")
        btn_int.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_int.clicked.connect(lambda: [self.abrir_url_integrada(url), dialog.accept()])
        lay.addWidget(btn_int)
        
        btn_ext = QPushButton("🌐 NAVEGADOR PREDETERMINADO")
        btn_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ext.clicked.connect(lambda: [self.nav_manager.navegador_ir(url), dialog.accept()])
        lay.addWidget(btn_ext)
        
        dialog.exec()

    def mostrar_detalles_favorito(self):
        """Actualiza el panel de detalles basado en el ítem seleccionado del árbol"""
        item = self.sub_favoritos.tree_favoritos.currentItem()
        if not item or item.parent() is None: return
        
        fav = item.data(0, Qt.ItemDataRole.UserRole)
        if fav:
            # En TabNavegadorFavoritos definimos estos labels para compatibilidad
            if hasattr(self.sub_favoritos, "lbl_det_nombre"):
                self.sub_favoritos.lbl_det_nombre.setText(fav["nombre"])
                self.sub_favoritos.lbl_det_url.setText(fav["url"])
                self.sub_favoritos.lbl_det_cat.setText(fav.get("categoria", "General"))
                self.sub_favoritos.lbl_det_fecha.setText(fav.get("fecha", "Desconocida"))

    def nueva_categoria(self):
        """Crear una nueva carpeta vacía en el sistema de favoritos con validaciones"""
        cat, ok = QInputDialog.getText(self, "Nueva Carpeta", "Nombre de la categoría:")
        if ok:
            cat = cat.strip()
            if not cat:
                QMessageBox.warning(self, "Error", "El nombre de la carpeta no puede estar vacío.")
                return
            if cat in self.fav_manager.obtener_categorias():
                QMessageBox.warning(self, "Error", f"La carpeta '{cat}' ya existe.")
                return
            # Añadimos un favorito dummy o simplemente registramos la categoría para el manager
            # El FavManager crea categorías dinámicamente si no existen
            self.fav_manager.añadir_favorito(f"Acceso a {cat}", "https://google.com", cat)
            self.actualizar_datos_favoritos()

    def eliminar_categoria(self):
        """Eliminar una categoría del árbol (nodo principal) limpiando marcadores dummy"""
        item = self.sub_favoritos.tree_favoritos.currentItem()
        if not item or item.parent() is not None: 
            QMessageBox.warning(self, "Selección", "Por favor, seleccione una carpeta para eliminar.")
            return
            
        cat = item.text(0).replace("📂 ", "")
        if cat == "General":
            QMessageBox.warning(self, "Protección", "La carpeta General no puede eliminarse.")
            return
            
        btn = QMessageBox.question(self, "Eliminar Carpeta", f"¿Eliminar carpeta '{cat}' y mover su contenido a General?", 
                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if btn == QMessageBox.StandardButton.Yes:
            # Eliminar marcador dummy si existe para que no contamine la carpeta General
            dummy_name = f"Acceso a {cat}"
            self.fav_manager.eliminar_favorito(dummy_name)
            self.fav_manager.reasignar_categoria(cat, "General")
            self.actualizar_datos_favoritos()

    def editar_favorito(self):
        """Editar el marcador seleccionado del árbol"""
        item = self.sub_favoritos.tree_favoritos.currentItem()
        if not item or item.parent() is None: return
        
        fav = item.data(0, Qt.ItemDataRole.UserRole)
        if fav:
            self.mostrar_ventana_edicion(fav, self.fav_manager.obtener_categorias(), self.guardar_edicion_favorito)

    def mostrar_ventana_edicion(self, favorito, categorias, save_callback):
        dialog = QDialog(self)
        dialog.setWindowTitle("Editar Favorito")
        dialog.setStyleSheet(f"background-color: {self.colores['bg_principal']}; color: white;")
        layout = QVBoxLayout(dialog)
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Nombre:"), 0, 0)
        txt_n = QLineEdit(favorito["nombre"])
        grid.addWidget(txt_n, 0, 1)
        
        grid.addWidget(QLabel("URL:"), 1, 0)
        txt_u = QLineEdit(favorito["url"])
        grid.addWidget(txt_u, 1, 1)
        
        grid.addWidget(QLabel("Categoría:"), 2, 0)
        combo = QComboBox()
        combo.addItems(categorias)
        combo.setCurrentText(favorito.get("categoria", "General"))
        grid.addWidget(combo, 2, 1)
        
        layout.addLayout(grid)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(lambda: save_callback(dialog, favorito["nombre"], txt_n.text(), txt_u.text(), combo.currentText()))
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)
        
        dialog.exec()

    def guardar_edicion_favorito(self, dialog, old_nombre, nombre, url, categoria):
        if not nombre or not url: return
        for f in self.fav_manager.favoritos:
            if f["nombre"] == old_nombre:
                f["nombre"] = nombre
                f["url"] = url
                f["categoria"] = categoria
                break
        self.fav_manager.guardar_favoritos()
        self.actualizar_datos_favoritos()
        dialog.accept()

    def eliminar_favorito(self):
        """Eliminar un marcador o una categoría mediante el ítem seleccionado del árbol"""
        item = self.sub_favoritos.tree_favoritos.currentItem()
        if not item: return
        
        # Caso: Nodo Hijo (Marcador)
        if item.parent():
            fav = item.data(0, Qt.ItemDataRole.UserRole)
            btn = QMessageBox.question(self, "Eliminar Marcador", f"¿Desea eliminar el marcador '{fav['nombre']}' permanentemente?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if btn == QMessageBox.StandardButton.Yes:
                self.fav_manager.eliminar_favorito(fav["nombre"])
                self.actualizar_datos_favoritos()
        # Caso: Nodo Padre (Categoría) -> Llamar a eliminar_categoria
        else:
            self.eliminar_categoria()

    def mostrar_aclaraciones(self):
        QMessageBox.information(self, "Aclaraciones", 
            "1. El navegador puede requerir instalar PyQt6-WebEngine.\n"
            "2. Puede tardar un poco en cargar URL pesadas.\n"
            "3. Se recomienda cerrar las ventanas del navegador integrado antes de salir de la app.")

    def toggle_fullscreen_mode(self, is_fullscreen):
        """Oculta o muestra la barra de submódulos y propaga al navegador integrado."""
        if hasattr(self, "tabs") and hasattr(self.tabs, "tabBar"):
            self.tabs.tabBar().setVisible(not is_fullscreen)
        if hasattr(self, "btn_extender"):
            self.btn_extender.setVisible(not is_fullscreen)
        if hasattr(self, "sub_integrado") and self.sub_integrado:
            if hasattr(self.sub_integrado, "toggle_fullscreen_mode"):
                self.sub_integrado.toggle_fullscreen_mode(is_fullscreen)


