import platform
import datetime
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QTabWidget, QFrame, QPushButton,
    QDialog, QCheckBox, QGridLayout, QApplication,
    QLineEdit, QTextEdit, QInputDialog, QFileDialog, QMenu,
    QProgressBar
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QColor
from pathlib import Path

from vistas.modulos.general.utils.panel_reloj import PanelReloj
from vistas.modulos.general.utils.panel_horario import PanelHorario
from vistas.modulos.general.utils.panel_clima import PanelClima
from vistas.modulos.general.utils.panel_noticias import PanelNoticias
try:
    from vistas.modulos.cuenta.submodulos.gui_user import GuiUser
except Exception:
    GuiUser = None

from vistas.modulos.general.utils.dashboard_dialogs import DialogoConfigurarIconos


class TabInicioGUI(QWidget):
    """Interfaz gráfica del módulo de Inicio con sistema de Felicitaciones"""
    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent)
        if isinstance(context, dict):
            self.colores = context
            self.context = colores
        elif isinstance(colores, dict):
            self.colores = colores
            self.context = context
        else:
            self.context = context
            self.colores = getattr(context, "colores", {}) if context else {}

        if not self.colores and self.context and hasattr(self.context, "app") and hasattr(self.context.app, "COLORES"):
            self.colores = self.context.app.COLORES

        if not isinstance(self.colores, dict):
            self.colores = {}
        self.config_personalizada = {}
        self.panels = {}
        self.tareas = []
        self.status_timer = None
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.inicializar_ui_base()
        self.inicializar_ui()

    def inicializar_ui_base(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

    def inicializar_ui(self):
        # Limpiar dashboard anterior si existe
        if hasattr(self, "dashboard_widget") and self.dashboard_widget:
            self.main_layout.removeWidget(self.dashboard_widget)
            self.dashboard_widget.deleteLater()
            self.dashboard_widget = None

        # Asegurar de obtener los módulos disponibles del app context
        self.modulos_disponibles = getattr(self.context.app, 'modulos_cargados', [])
        if not self.modulos_disponibles and hasattr(self.context.app, 'obtener_todos_los_modulos'):
            self.modulos_disponibles = self.context.app.obtener_todos_los_modulos()

        self.dashboard_widget = self._crear_tab_dashboard()
        self.main_layout.addWidget(self.dashboard_widget, 1)

    def cambiar_tab(self, nombre_tab):
        """Busca el tab por su nombre en el QTabWidget de la aplicación principal y lo selecciona"""
        app = getattr(self.context, "app", None)
        if not app:
            return
            
        # Buscar en el notebook de la app principal
        notebook = getattr(app, "notebook", None)
        if not notebook:
            return
            
        # Iterar por los tabs reales en el notebook
        for i in range(notebook.count()):
            tab_title = notebook.tabText(i)
            if tab_title.lower() == nombre_tab.lower():
                notebook.setCurrentIndex(i)
                return

    def aplicar_icono_boton(self, btn, mod):
        from PyQt6.QtGui import QIcon, QPixmap
        m_name = mod["name"]

        # Cargar personalización guardada en la cuenta del usuario si existe
        icon_val = None
        try:
            cfg_file = Path(self.context.ruta_usuario) / "iconos_modulos.json"
            if cfg_file.exists():
                with open(cfg_file, "r", encoding="utf-8") as f:
                    iconos_custom = json.load(f)
                    icon_val = iconos_custom.get(m_name.lower())
        except Exception:
            pass

        if icon_val is None:
            icon_val = mod.get("icon")
        
        EMOJI_MAP = {
            "archivos": "📁",
            "calculadora": "🧮",
            "calendario": "📅",
            "chat": "💬",
            "cuaderno": "📓",
            "extras": "🌟",
            "grabadora": "🎙️",
            "navegador": "🌐",
            "notas": "📝",
            "reproductor": "🎵",
            "sistema": "⚙️",
            "tiempo": "⏱️",
            "traductor": "🗣️",
            "default": "🧩"
        }
        
        emoji_fallback = EMOJI_MAP.get(m_name.lower(), EMOJI_MAP["default"])
        
        if not icon_val:
            btn.setText(emoji_fallback)
            return
            
        icon_str = str(icon_val).strip()
        
        # 1. Caso: URL web
        if icon_str.startswith("http://") or icon_str.startswith("https://"):
            import hashlib
            from pathlib import Path
            
            cache_dir = Path(self.context.ruta_usuario) / ".icon_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            url_hash = hashlib.md5(icon_str.encode('utf-8')).hexdigest()
            local_path = cache_dir / f"{url_hash}.png"
            
            if local_path.exists():
                pix = QPixmap(str(local_path))
                if not pix.isNull():
                    btn.setIcon(QIcon(pix))
                    btn.setIconSize(QSize(28, 28))
                    btn.setText("")
                else:
                    btn.setText(emoji_fallback)
            else:
                from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
                from PyQt6.QtCore import QUrl
                
                if not hasattr(self, "_net_managers"):
                    self._net_managers = []
                manager = QNetworkAccessManager(self)
                self._net_managers.append(manager)
                
                def on_finished(reply):
                    if reply.error() == reply.NetworkError.NoError:
                        data = reply.readAll()
                        pix = QPixmap()
                        pix.loadFromData(data)
                        if not pix.isNull():
                            try:
                                with open(local_path, "wb") as f:
                                    f.write(data)
                            except: pass
                            btn.setIcon(QIcon(pix))
                            btn.setIconSize(QSize(28, 28))
                            btn.setText("")
                        else:
                            btn.setText(emoji_fallback)
                    else:
                        btn.setText(emoji_fallback)
                    reply.deleteLater()
                    if manager in self._net_managers:
                        self._net_managers.remove(manager)
                
                manager.finished.connect(on_finished)
                manager.get(QNetworkRequest(QUrl(icon_str)))
                btn.setText(emoji_fallback)
                
        # 2. Caso: Dirección local (archivo de imagen)
        elif icon_str.lower().endswith((".png", ".jpg", ".jpeg", ".ico", ".svg", ".bmp")):
            from pathlib import Path
            from controlador.utils.paths import get_resource_path
            
            base_dir = get_resource_path()
            path_local = Path(icon_str)
            if not path_local.is_absolute():
                folder = mod.get("folder")
                # Buscar en plugins/<folder>/<icon>
                path_local = base_dir / "plugins" / folder / icon_str
                if not path_local.exists():
                    # Fallback a vistas/<folder>/<icon>
                    path_local = base_dir / "vistas" / folder / icon_str
            
            if path_local.exists():
                pix = QPixmap(str(path_local))
                if not pix.isNull():
                    btn.setIcon(QIcon(pix))
                    btn.setIconSize(QSize(28, 28))
                    btn.setText("")
                else:
                    btn.setText(emoji_fallback)
            else:
                btn.setText(emoji_fallback)
                
        # 3. Caso: Letra, número, texto corto o emoji directo
        else:
            btn.setText(icon_str)

    def ir_a_caja_fuerte(self):
        self.cambiar_tab("Seguridad")

    def actualizar_recursos_sistema(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            if hasattr(self, "lbl_cpu_text"):
                self.lbl_cpu_text.setText(f"CPU: {cpu:.1f}%")
                self.bar_cpu.setValue(int(cpu))
            if hasattr(self, "lbl_ram_text"):
                self.lbl_ram_text.setText(f"RAM: {ram:.1f}%")
                self.bar_ram.setValue(int(ram))
        except Exception:
            pass

    def _ejecutar_busqueda_spotlight(self):
        if not hasattr(self, "ent_search"):
            return
        query = self.ent_search.text().strip().lower()
        if not query:
            return
        mods = getattr(self, 'modulos_disponibles', [])
        for mod in mods:
            m_name = mod.get("name", "").lower()
            if query in m_name:
                self.ent_search.clear()
                self.cambiar_tab(mod.get("name", "").capitalize())
                return
        app = getattr(self.context, "app", None)
        if app and hasattr(app, "notebook"):
            for i in range(app.notebook.count()):
                t = app.notebook.tabText(i).lower()
                if query in t:
                    self.ent_search.clear()
                    app.notebook.setCurrentIndex(i)
                    return

    def actualizar_estado_boveda(self):
        self.actualizar_recursos_sistema()
        if not hasattr(self, 'lbl_vault_status') or not self.lbl_vault_status:
            return
            
        seguridad_mod = getattr(self.context.app, "clases_modulos", {}).get("Seguridad")
        if not seguridad_mod:
            self.lbl_vault_status.setText("Desactivada")
            self.lbl_vault_status.setStyleSheet("color: #9CA3AF; border: none; background: transparent;")
            self.btn_vault_action.setText("BÓVEDA NO DISPONIBLE")
            self.btn_vault_action.setEnabled(False)
            return
            
        if getattr(seguridad_mod, "desbloqueada", False):
            self.lbl_vault_status.setText("Desbloqueada 🟢")
            self.lbl_vault_status.setStyleSheet("color: #10B981; border: none; background: transparent;")
            self.btn_vault_action.setText("GESTIONAR SECRETOS")
            self.btn_vault_action.setEnabled(True)
        else:
            self.lbl_vault_status.setText("Bloqueada 🔴")
            self.lbl_vault_status.setStyleSheet("color: #EF4444; border: none; background: transparent;")
            self.btn_vault_action.setText("DESBLOQUEAR BÓVEDA")
            self.btn_vault_action.setEnabled(True)

    def cargar_tareas(self):
        from pathlib import Path
        ruta_todo = Path(self.context.ruta_usuario) / "tareas_dashboard.json"
        if ruta_todo.exists():
            try:
                with open(ruta_todo, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []
        
    def guardar_tareas(self):
        from pathlib import Path
        ruta_todo = Path(self.context.ruta_usuario) / "tareas_dashboard.json"
        try:
            with open(ruta_todo, "w", encoding="utf-8") as f:
                json.dump(self.tareas, f, indent=4)
        except Exception as e:
            print(f"Error guardando tareas: {e}")
            
    def renderizar_tareas(self):
        # Limpiar contenedor de tareas
        for i in reversed(range(self.todo_list_container.count())):
            widget = self.todo_list_container.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                
        for idx, tarea in enumerate(self.tareas):
            item_widget = QFrame()
            item_widget.setStyleSheet("background: transparent; border: none;")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(8)
            
            cb = QCheckBox()
            cb.setChecked(tarea.get("completed", False))
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            
            lbl_text = QLabel(tarea.get("text", ""))
            lbl_text.setFont(QFont(self.font_family, 10))
            
            if tarea.get("completed", False):
                lbl_text.setStyleSheet("color: rgba(255, 255, 255, 0.4); text-decoration: line-through; border: none; background: transparent;")
            else:
                lbl_text.setStyleSheet("color: white; border: none; background: transparent;")
                
            cb.stateChanged.connect(lambda state, i=idx: self.toggle_tarea(i, state))
            
            item_layout.addWidget(cb)
            item_layout.addWidget(lbl_text, 1)
            
            btn_del = QPushButton("❌")
            btn_del.setFixedSize(24, 24)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: rgba(239, 68, 68, 0.6);
                    border: none;
                    font-size: 10px;
                }
                QPushButton:hover {
                    color: rgba(239, 68, 68, 1);
                }
            """)
            btn_del.clicked.connect(lambda checked, i=idx: self.eliminar_tarea(i))
            item_layout.addWidget(btn_del)
            
            self.todo_list_container.addWidget(item_widget)
            
    def agregar_tarea(self):
        texto = self.ent_tarea.text().strip()
        if not texto:
            return
        self.tareas.append({"text": texto, "completed": False})
        self.ent_tarea.clear()
        self.guardar_tareas()
        self.renderizar_tareas()
        
    def toggle_tarea(self, idx, state):
        if 0 <= idx < len(self.tareas):
            self.tareas[idx]["completed"] = (state == 2 or state == Qt.CheckState.Checked)
            self.guardar_tareas()
            self.renderizar_tareas()
            
    def eliminar_tarea(self, idx):
        if 0 <= idx < len(self.tareas):
            self.tareas.pop(idx)
            self.guardar_tareas()
            self.renderizar_tareas()

    def cargar_postit(self):
        from pathlib import Path
        ruta_pi = Path(self.context.ruta_usuario) / "postit_dashboard.json"
        if ruta_pi.exists():
            try:
                with open(ruta_pi, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("text", "")
            except:
                return ""
        return ""
        
    def guardar_postit(self):
        from pathlib import Path
        ruta_pi = Path(self.context.ruta_usuario) / "postit_dashboard.json"
        texto = self.txt_postit.toPlainText()
        try:
            with open(ruta_pi, "w", encoding="utf-8") as f:
                json.dump({"text": texto}, f, indent=4)
        except Exception as e:
            print(f"Error guardando postit: {e}")

    def _crear_tab_dashboard(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {self.colores['bg_principal']}; }}")
        
        container = QWidget()
        container.setStyleSheet(f"background: {self.colores['bg_principal']};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)
        
        # --- Lógica de CUMPLEAÑOS ---
        self._verificar_cumpleaños(layout)
        
        # Header Bienvenida
        header_layout = QVBoxLayout()
        lbl_welcome = QLabel(f"¡Hola de nuevo, {self.context.usuario}!")
        lbl_welcome.setFont(QFont(self.font_family, 26, QFont.Weight.Bold))
        lbl_welcome.setStyleSheet("color: white; border: none; background: transparent;")
        header_layout.addWidget(lbl_welcome)
        
        lbl_desc = QLabel("Tu resumen diario y herramientas rápidas.")
        lbl_desc.setFont(QFont(self.font_family, 11))
        lbl_desc.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        header_layout.addWidget(lbl_desc)
        layout.addLayout(header_layout)

        # Barra de Búsqueda Rápida / Command Spotlight
        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }}
            QFrame:focus-within {{
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
        sf_lay = QHBoxLayout(search_frame)
        sf_lay.setContentsMargins(16, 8, 16, 8)
        sf_lay.setSpacing(12)
        
        lbl_search_ico = QLabel("🔍")
        lbl_search_ico.setFont(QFont(self.font_family, 12))
        lbl_search_ico.setStyleSheet("border: none; background: transparent;")
        sf_lay.addWidget(lbl_search_ico)
        
        self.ent_search = QLineEdit()
        self.ent_search.setPlaceholderText("Comando rápido o buscar módulo (ej: archivos, notas, seguridad, traductor)...")
        self.ent_search.setFont(QFont(self.font_family, 10))
        self.ent_search.setStyleSheet("QLineEdit { background: transparent; border: none; color: white; }")
        self.ent_search.returnPressed.connect(self._ejecutar_busqueda_spotlight)
        sf_lay.addWidget(self.ent_search, 1)
        
        btn_search_go = QPushButton("Abrir ↵")
        btn_search_go.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search_go.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_search_go.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: #4F46E5;
            }}
        """)
        btn_search_go.clicked.connect(self._ejecutar_busqueda_spotlight)
        sf_lay.addWidget(btn_search_go)
        layout.addWidget(search_frame)
        
        # Columnas principal (Izquierda y Derecha)
        cols_layout = QHBoxLayout()
        cols_layout.setSpacing(25)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        
        col_izq = QVBoxLayout()
        col_izq.setSpacing(25)
        
        col_der = QVBoxLayout()
        col_der.setSpacing(25)
        
        # --- COLUMNA IZQUIERDA (Info y Reloj) ---
        if self.config_personalizada.get("mostrar_reloj", True):
            p = PanelReloj(container, self.config_personalizada, self.colores)
            col_izq.addWidget(p)
            self.panels['reloj'] = p
            
        if self.config_personalizada.get("mostrar_mini_calendario", True):
            p = PanelHorario(container, self.config_personalizada, self.colores)
            col_izq.addWidget(p)
            self.panels['horario'] = p
            
        grid_info = QHBoxLayout()
        grid_info.setSpacing(20)
        mostrar_c = self.config_personalizada.get("mostrar_clima", True)
        mostrar_n = self.config_personalizada.get("mostrar_noticias", True)
        
        if mostrar_c:
            p = PanelClima(container, self.config_personalizada, self.colores, self.guardar_configuracion_personalizada)
            grid_info.addWidget(p, 1)
            self.panels['clima'] = p
            
        if mostrar_n:
            p = PanelNoticias(container, self.config_personalizada, self.colores, self.guardar_configuracion_personalizada)
            grid_info.addWidget(p, 1)
            self.panels['noticias'] = p
            
        if mostrar_c or mostrar_n:
            col_izq.addLayout(grid_info)
            
        col_izq.addStretch()
        
        # --- COLUMNA DERECHA (Lanzador, Bóveda, Tareas, Post-it) ---
        
        # 1. Module Launchpad
        lp_frame = QFrame()
        lp_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(45, 45, 45, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }}
            QFrame:hover {{
                background-color: rgba(45, 45, 45, 0.65);
                border: 1px solid rgba(99, 102, 241, 0.4);
            }}
        """)
        lp_layout = QVBoxLayout(lp_frame)
        lp_layout.setContentsMargins(20, 20, 20, 20)
        lp_layout.setSpacing(12)
        
        lp_title = QLabel("🚀 LANZADOR DE MÓDULOS")
        lp_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lp_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        lp_layout.addWidget(lp_title)
        
        lp_grid = QGridLayout()
        lp_grid.setSpacing(10)
        
        EMOJI_MAP = {
            "archivos": "📁",
            "calculadora": "🧮",
            "calendario": "📅",
            "chat": "💬",
            "cuaderno": "📓",
            "extras": "🌟",
            "grabadora": "🎙️",
            "navegador": "🌐",
            "notas": "📝",
            "reproductor": "🎵",
            "sistema": "⚙️",
            "tiempo": "⏱️",
            "traductor": "🗣️",
            "default": "🧩"
        }
        
        mods = getattr(self, 'modulos_disponibles', [])
        col_count = 0
        row_count = 0
        max_cols = 5
        self._lp_botones = []

        lp_frame.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        lp_frame.customContextMenuRequested.connect(self._mostrar_menu_config_iconos)
        
        for mod in mods:
            if not mod.get("visible", True) or mod["name"].lower() == "inicio":
                continue
            
            m_name = mod["name"]
            
            btn = QPushButton()
            btn.setFixedSize(45, 45)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont(self.font_family, 14))
            btn.setToolTip(f"Abrir {m_name.capitalize()} (Clic derecho para configurar iconos)")
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(self._mostrar_menu_config_iconos)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background-color: {self.colores['acento']};
                    border: 1px solid {self.colores['acento']};
                }}
            """)
            self.aplicar_icono_boton(btn, mod)
            btn.clicked.connect(lambda checked, n=m_name.capitalize(): self.cambiar_tab(n))
            self._lp_botones.append((btn, mod))
            
            lp_grid.addWidget(btn, row_count, col_count)
            col_count += 1
            if col_count >= max_cols:
                col_count = 0
                row_count += 1
                
        lp_layout.addLayout(lp_grid)
        col_der.addWidget(lp_frame)
        
        # 2. Safe Box Status Card
        vault_frame = QFrame()
        vault_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(45, 45, 45, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }}
            QFrame:hover {{
                background-color: rgba(45, 45, 45, 0.65);
                border: 1px solid rgba(99, 102, 241, 0.4);
            }}
        """)
        v_layout = QVBoxLayout(vault_frame)
        v_layout.setContentsMargins(20, 20, 20, 20)
        v_layout.setSpacing(10)
        
        v_title = QLabel("🔐 ESTADO DE BÓVEDA")
        v_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        v_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        v_layout.addWidget(v_title)
        
        h_status = QHBoxLayout()
        h_status.setSpacing(8)
        lbl_v_status_label = QLabel("Estado:")
        lbl_v_status_label.setFont(QFont(self.font_family, 10))
        lbl_v_status_label.setStyleSheet("color: white; border: none; background: transparent;")
        h_status.addWidget(lbl_v_status_label)
        
        self.lbl_vault_status = QLabel("Consultando...")
        self.lbl_vault_status.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_vault_status.setStyleSheet("color: white; border: none; background: transparent;")
        h_status.addWidget(self.lbl_vault_status)
        h_status.addStretch()
        v_layout.addLayout(h_status)
        
        self.btn_vault_action = QPushButton("IR A BÓVEDA")
        self.btn_vault_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_vault_action.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_vault_action.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.colores['acento']};
                border: 1px solid {self.colores['acento']};
            }}
        """)
        self.btn_vault_action.clicked.connect(self.ir_a_caja_fuerte)
        v_layout.addWidget(self.btn_vault_action)
        col_der.addWidget(vault_frame)

        # Hardware Resource Mini-Monitor
        res_frame = QFrame()
        res_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(45, 45, 45, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }}
            QFrame:hover {{
                background-color: rgba(45, 45, 45, 0.65);
                border: 1px solid rgba(99, 102, 241, 0.4);
            }}
        """)
        res_layout = QVBoxLayout(res_frame)
        res_layout.setContentsMargins(20, 16, 20, 16)
        res_layout.setSpacing(10)
        
        lbl_res_title = QLabel("⚡ RECURSOS DEL SISTEMA")
        lbl_res_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_res_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        res_layout.addWidget(lbl_res_title)
        
        cpu_row = QHBoxLayout()
        self.lbl_cpu_text = QLabel("CPU: 0%")
        self.lbl_cpu_text.setFont(QFont(self.font_family, 9))
        self.lbl_cpu_text.setStyleSheet("color: white; border: none; background: transparent;")
        self.bar_cpu = QProgressBar()
        self.bar_cpu.setRange(0, 100)
        self.bar_cpu.setValue(0)
        self.bar_cpu.setTextVisible(False)
        self.bar_cpu.setFixedHeight(7)
        self.bar_cpu.setStyleSheet(f"QProgressBar {{ background-color: rgba(255,255,255,0.06); border-radius: 3px; border: none; }} QProgressBar::chunk {{ background-color: {self.colores.get('acento', '#6366F1')}; border-radius: 3px; }}")
        cpu_row.addWidget(self.lbl_cpu_text, 1)
        cpu_row.addWidget(self.bar_cpu, 2)
        res_layout.addLayout(cpu_row)
        
        ram_row = QHBoxLayout()
        self.lbl_ram_text = QLabel("RAM: 0%")
        self.lbl_ram_text.setFont(QFont(self.font_family, 9))
        self.lbl_ram_text.setStyleSheet("color: white; border: none; background: transparent;")
        self.bar_ram = QProgressBar()
        self.bar_ram.setRange(0, 100)
        self.bar_ram.setValue(0)
        self.bar_ram.setTextVisible(False)
        self.bar_ram.setFixedHeight(7)
        self.bar_ram.setStyleSheet(f"QProgressBar {{ background-color: rgba(255,255,255,0.06); border-radius: 3px; border: none; }} QProgressBar::chunk {{ background-color: #10B981; border-radius: 3px; }}")
        ram_row.addWidget(self.lbl_ram_text, 1)
        ram_row.addWidget(self.bar_ram, 2)
        res_layout.addLayout(ram_row)
        
        col_der.addWidget(res_frame)
        self.actualizar_recursos_sistema()
        
        # 3. To-Do List (Pendientes)
        todo_frame = QFrame()
        todo_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(45, 45, 45, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }}
            QFrame:hover {{
                background-color: rgba(45, 45, 45, 0.65);
                border: 1px solid rgba(99, 102, 241, 0.4);
            }}
        """)
        todo_layout = QVBoxLayout(todo_frame)
        todo_layout.setContentsMargins(20, 20, 20, 20)
        todo_layout.setSpacing(12)
        
        todo_title = QLabel("📋 LISTA DE PENDIENTES")
        todo_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        todo_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        todo_layout.addWidget(todo_title)
        
        # Add Input Row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        self.ent_tarea = QLineEdit()
        self.ent_tarea.setPlaceholderText("Nueva tarea...")
        self.ent_tarea.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(255, 255, 255, 0.05);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 8px 12px;
                font-family: '{self.font_family}';
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colores['acento']};
            }}
        """)
        self.ent_tarea.returnPressed.connect(self.agregar_tarea)
        input_layout.addWidget(self.ent_tarea, 1)
        
        btn_add_tarea = QPushButton("➕")
        btn_add_tarea.setFixedSize(32, 32)
        btn_add_tarea.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_tarea.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {self.colores['acento']};
                border: 1px solid {self.colores['acento']};
            }}
        """)
        btn_add_tarea.clicked.connect(self.agregar_tarea)
        input_layout.addWidget(btn_add_tarea)
        todo_layout.addLayout(input_layout)
        
        self.todo_list_container = QVBoxLayout()
        self.todo_list_container.setSpacing(6)
        todo_layout.addLayout(self.todo_list_container)
        
        self.tareas = self.cargar_tareas()
        self.renderizar_tareas()
        col_der.addWidget(todo_frame)
        
        # 4. Quick Post-it
        postit_frame = QFrame()
        postit_frame.setMinimumHeight(150)
        postit_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(253, 224, 71, 0.12);
                border: 1px solid rgba(253, 224, 71, 0.25);
                border-radius: 16px;
            }}
            QFrame:hover {{
                background-color: rgba(253, 224, 71, 0.18);
                border: 1px solid rgba(253, 224, 71, 0.4);
            }}
        """)
        pi_layout = QVBoxLayout(postit_frame)
        pi_layout.setContentsMargins(20, 20, 20, 20)
        pi_layout.setSpacing(10)
        
        pi_title = QLabel("📌 NOTA RÁPIDA")
        pi_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        pi_title.setStyleSheet("color: #FEF08A; border: none; background: transparent;")
        pi_layout.addWidget(pi_title)
        
        self.txt_postit = QTextEdit()
        self.txt_postit.setPlaceholderText("Escribe un recordatorio rápido aquí...")
        self.txt_postit.setFont(QFont(self.font_family, 10))
        self.txt_postit.setStyleSheet("""
            QTextEdit {
                background: transparent;
                color: #FEF08A;
                border: none;
            }
        """)
        pi_layout.addWidget(self.txt_postit)
        
        postit_text = self.cargar_postit()
        self.txt_postit.setPlainText(postit_text)
        self.txt_postit.textChanged.connect(self.guardar_postit)
        col_der.addWidget(postit_frame)
        
        col_der.addStretch()
        
        # Add columns to main layout
        cols_layout.addLayout(col_izq, 3)
        cols_layout.addLayout(col_der, 2)
        layout.addLayout(cols_layout)
        
        # Botón Personalizar debajo
        btn_pers = QPushButton("🎨 Personalizar Dashboard")
        btn_pers.setFixedSize(220, 45)
        btn_pers.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pers.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 8px; border: none;")
        btn_pers.clicked.connect(self.mostrar_personalizar)
        layout.addWidget(btn_pers, 0, Qt.AlignmentFlag.AlignRight)
        
        # Iniciar actualizaciones de estado de la bóveda
        self.actualizar_estado_boveda()
        if not hasattr(self, 'status_timer') or not self.status_timer or not self.status_timer.isActive():
            self.status_timer = QTimer(self)
            self.status_timer.timeout.connect(self.actualizar_estado_boveda)
            self.status_timer.start(1000)
            
        scroll.setWidget(container)
        return scroll

    def _mostrar_menu_config_iconos(self, pos=None):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white; border: 1px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 8px; padding: 4px;
            }}
            QMenu::item {{ padding: 6px 14px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {self.colores.get('acento', '#6366F1')}; }}
        """)
        act_cfg = menu.addAction("⚙️ Configurar Iconos de Accesos Rápidos...")
        chosen = menu.exec(self.cursor().pos())
        if chosen == act_cfg:
            mods = getattr(self, 'modulos_disponibles', [])
            dlg = DialogoConfigurarIconos(
                self, mods, self.context.ruta_usuario, self.colores,
                on_guardado=self._recargar_iconos_lanzador
            )
            dlg.exec()

    def _recargar_iconos_lanzador(self):
        from PyQt6.QtGui import QIcon
        if hasattr(self, "_lp_botones"):
            for btn, mod in self._lp_botones:
                btn.setIcon(QIcon())
                btn.setText("")
                self.aplicar_icono_boton(btn, mod)

    def _verificar_cumpleaños(self, layout):
        """Muestra una felicitación si hoy es el cumpleaños del usuario"""
        try:
            from pathlib import Path
            config_path = Path(self.context.ruta_usuario) / "config.json"
            if not config_path.exists(): return
            
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            cumple = data.get("cumpleaños", "")
            if not cumple: return
            
            hoy = datetime.datetime.now().strftime("%d/%m")
            if hoy == cumple:
                celebrado = data.get("celebrado_fecha", "")
                if celebrado == hoy: return

                banner = QFrame()
                banner.setStyleSheet(f"""
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {self.colores['acento']}, stop:1 #818CF8);
                    border-radius: 15px; border: none;
                """)
                b_lay = QHBoxLayout(banner)
                b_lay.setContentsMargins(30, 25, 30, 25)
                
                txt_lay = QVBoxLayout()
                lbl_h1 = QLabel(f"🎂 ¡FELIZ CUMPLEAÑOS, {self.context.usuario.upper()}! 🥳")
                lbl_h1.setFont(QFont(self.font_family, 18, QFont.Weight.Bold))
                lbl_h1.setStyleSheet("color: white; border: none; background: transparent;")
                txt_lay.addWidget(lbl_h1)
                
                lbl_h2 = QLabel("Todo el equipo de Multitool te desea un excelente día lleno de éxitos.")
                lbl_h2.setFont(QFont(self.font_family, 10))
                lbl_h2.setStyleSheet("color: rgba(255,255,255,0.8); border: none; background: transparent;")
                txt_lay.addWidget(lbl_h2)
                b_lay.addLayout(txt_lay, 1)
                
                self.btn_gracias = QPushButton("¡GRACIAS! ❤️")
                self.btn_gracias.setFixedSize(120, 45)
                self.btn_gracias.setCursor(Qt.CursorShape.PointingHandCursor)
                self.btn_gracias.setStyleSheet("background: white; color: #6366F1; border-radius: 10px; font-weight: bold; border: none;")
                self.btn_gracias.clicked.connect(lambda: self._ocultar_felicitacion(data, hoy, banner))
                b_lay.addWidget(self.btn_gracias)
                
                layout.addWidget(banner)
        except Exception as e:
            print(f"Error en verificación cumple: {e}")

    def _ocultar_felicitacion(self, data, fecha, banner):
        """Marca como celebrado y oculta el banner"""
        try:
            from pathlib import Path
            config_path = Path(self.context.ruta_usuario) / "config.json"
            data["celebrado_fecha"] = fecha
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            banner.hide()
        except: pass

    def mostrar_personalizar(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Personalización")
        dialog.setFixedWidth(400)
        dialog.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border: 1px solid {self.colores['bg_terciario']};")
        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(30,30,30,30)
        
        lbl = QLabel("Dashboard")
        lbl.setFont(QFont(self.font_family, 14, QFont.Weight.Bold))
        lay.addWidget(lbl)
        
        checks = {}
        for k, name in {"mostrar_reloj": "Reloj", "mostrar_clima": "Clima", "mostrar_noticias": "Noticias"}.items():
            cb = QCheckBox(name)
            cb.setChecked(self.config_personalizada.get(k, True))
            lay.addWidget(cb)
            checks[k] = cb
        
        btn = QPushButton("GUARDAR")
        btn.setMinimumHeight(45)
        btn.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 10px;")
        btn.clicked.connect(lambda: [self.config_personalizada.update({k: c.isChecked() for k, c in checks.items()}), self.guardar_configuracion_personalizada(), dialog.accept(), self.inicializar_ui()])
        lay.addSpacing(20)
        lay.addWidget(btn)
        dialog.exec()

    def guardar_configuracion_personalizada(self): pass

    def _ejecutar_busqueda_spotlight(self):
        query = self.ent_search.text().strip()
        if not query:
            return

        # Comando secreto: 'mode dev' activa el modo desarrollador
        if query.lower() == "mode dev":
            self.ent_search.clear()
            app = getattr(self.context, "app", None) or self.window()
            if hasattr(app, "activar_modo_dev"):
                app.activar_modo_dev(True)
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "Modo Programador Activado",
                    "⛏️ ¡MODO PROGRAMADOR ACTIVADO CON ÉXITO!\n\n"
                    "Se ha añadido el botón '⛏️ CONSOLA DEV' en la barra de herramientas superior.\n"
                    "Haz clic en él o presiona F1 / F12 para abrir la consola con logs y comandos de minijuegos."
                )
            return

        app = getattr(self.context, "app", None) or self.window()
        notebook = getattr(app, "notebook", None)
        if notebook:
            q_clean = "".join(c for c in query.lower() if c.isalnum())
            for i in range(notebook.count()):
                clean_t = "".join(c for c in notebook.tabText(i).lower() if c.isalnum())
                if q_clean and (q_clean in clean_t or clean_t in q_clean):
                    notebook.setCurrentIndex(i)
                    self.ent_search.clear()
                    return
