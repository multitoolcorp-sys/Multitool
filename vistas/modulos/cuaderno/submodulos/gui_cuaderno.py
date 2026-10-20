from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QLineEdit, QStackedWidget, QPushButton, QTextEdit, QTextBrowser, QSplitter
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .components.sidebar_cuaderno import SidebarCuaderno
from .components.tabla_cuaderno import TablaCuaderno
from .components.action_bar_cuaderno import ActionBarCuaderno
from .components.toolbar_cuaderno import ToolbarCuaderno
from .components.chart_studio import ChartStudio

class CuadernoGUI(QWidget):
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.current_view_index = 0
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar (Libros guardados)
        self.sidebar = SidebarCuaderno(self.colores, self.callbacks, self)
        main_layout.addWidget(self.sidebar)

        # 2. Área Central del Editor
        editor_frame = QFrame()
        editor_frame.setStyleSheet(f"background:{self.colores['bg_principal']};")
        editor_lay = QVBoxLayout(editor_frame)
        editor_lay.setContentsMargins(15, 10, 15, 12)
        editor_lay.setSpacing(8)

        # Barra de Control de Vistas (Tabs Intercambiables)
        view_ctrl_lay = QHBoxLayout()
        view_ctrl_lay.setSpacing(5)
        
        self.btn_view_editor = self._create_view_btn("🧮 Edición Grid", 0)
        self.btn_view_text = self._create_view_btn("📝 Modo Texto/JSON", 1)
        self.btn_view_preview = self._create_view_btn("👁️ Vista Previa", 2)
        
        view_ctrl_lay.addWidget(self.btn_view_editor)
        view_ctrl_lay.addWidget(self.btn_view_text)
        view_ctrl_lay.addWidget(self.btn_view_preview)
        view_ctrl_lay.addStretch()
        
        # Título
        lbl_nombre = QLabel("Libro:")
        lbl_nombre.setStyleSheet(f"color:{self.colores['fg_secundario']}; font-weight:bold; font-size:11px;")
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre del Libro...")
        self.txt_nombre.setFixedWidth(200)
        self.txt_nombre.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(45, 45, 61, 0.45);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colores['acento']};
                background: rgba(45, 45, 61, 0.7);
            }}
        """)
        self.txt_nombre.textChanged.connect(self.callbacks["marcar_modificado"])
        
        view_ctrl_lay.addWidget(lbl_nombre)
        view_ctrl_lay.addWidget(self.txt_nombre)
        
        editor_lay.addLayout(view_ctrl_lay)

        # 3. Stacked Widget para Vistas Intercambiables
        self.stack_views = QStackedWidget()
        
        # Vista 0: Tabla (Grid Excel) - INICIALIZAR TABLA ANTES QUE TOOLBAR
        self.view_editor_widget = QWidget()
        tab_lay = QVBoxLayout(self.view_editor_widget)
        tab_lay.setContentsMargins(0, 0, 0, 0)
        
        # FIX: Primero se crea la tabla
        self.tabla = TablaCuaderno(self.colores, self)
        self.tabla.cambio_datos.connect(self.callbacks["marcar_modificado"])
        
        # Pasamos la tabla real a la barra de herramientas
        self.toolbar = ToolbarCuaderno(self.colores, self.tabla, self) 
        
        tab_lay.addWidget(self.toolbar, 0)
        
        # QSplitter horizontal para Tabla y ChartStudio
        self.editor_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor_splitter.setStyleSheet("QSplitter::handle { background: rgba(255, 255, 255, 0.05); width: 4px; }")
        self.editor_splitter.addWidget(self.tabla)
        
        # Añadir Chart Studio
        self.chart_studio = ChartStudio(self.tabla, self.colores)
        self.chart_studio.setVisible(False)
        self.editor_splitter.addWidget(self.chart_studio)
        
        tab_lay.addWidget(self.editor_splitter, 1)
        self.stack_views.addWidget(self.view_editor_widget)
        
        # Vista 1: Editor de Texto (JSON Raw)
        self.text_editor = QTextEdit()
        self.text_editor.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(30, 30, 46, 0.5);
                color: #A3E635;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 15px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }}
        """)
        self.text_editor.setReadOnly(True)
        self.stack_views.addWidget(self.text_editor)
        
        # Vista 2: Vista Previa (HTML WebView)
        self.preview_browser = QTextBrowser()
        self.preview_browser.setOpenExternalLinks(True)
        self.preview_browser.setStyleSheet(f"""
            QTextBrowser {{
                background: rgba(18, 18, 24, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 10px;
            }}
        """)
        self.stack_views.addWidget(self.preview_browser)
        
        editor_lay.addWidget(self.stack_views)

        # 4. Action Bar (Guardar / Exportar)
        self.action_bar = ActionBarCuaderno(self.colores, self.callbacks, self)
        editor_lay.addWidget(self.action_bar)

        # Footer Status
        self.lbl_status = QLabel("Listo.")
        self.lbl_status.setStyleSheet(f"color:{self.colores['fg_secundario']}; font-style:italic; font-size:10px;")
        editor_lay.addWidget(self.lbl_status)

        main_layout.addWidget(editor_frame, 1)

        # Aliases
        self.list_horarios = self.sidebar.list_horarios
        self.btn_guardar = self.action_bar.btn_guardar

    def _hex_to_rgb(self, hex_str):
        hex_str = hex_str.lstrip('#')
        if len(hex_str) == 3:
            hex_str = ''.join(c*2 for c in hex_str)
        return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"

    def _create_view_btn(self, text, index):
        btn = QPushButton(text)
        btn.setCheckable(True)
        if index == 0: btn.setChecked(True)
        btn.setMinimumHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255, 255, 255, 0.03); 
                color: {self.colores['fg_secundario']}; 
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px; 
                padding: 4px 14px; 
                font-weight: bold; 
                font-size: 11px;
            }}
            QPushButton:hover {{ 
                background: rgba(255, 255, 255, 0.08); 
                color: white; 
            }}
            QPushButton:checked {{ 
                background: rgba({{self._hex_to_rgb('{self.colores['acento']}')}}, 0.2); 
                color: white; 
                border: 1px solid {self.colores['acento']}; 
            }}
        """)
        btn.clicked.connect(lambda: self._on_view_clicked(index))
        return btn

    def _on_view_clicked(self, index):
        # Desmarcar los otros
        self.btn_view_editor.setChecked(index == 0)
        self.btn_view_text.setChecked(index == 1)
        self.btn_view_preview.setChecked(index == 2)
        
        # Llamar al callback
        self.callbacks["cambiar_vista"](index)

    def habilitar_botones(self, enabled):
        self.action_bar.set_enabled_all(enabled)

    def _style_btn_guardar(self, state):
        mapping = {True: "modified", False: "saved"}
        self.action_bar.apply_style_guardar(mapping.get(state, "disabled"))

    def limpiar_celdas(self):
        self.tabla.clearContents()
        self.tabla.setRowCount(0)

    def cargar_actividades(self, actividades, horas=None, headers=None):
        self.tabla.cargar_datos_tabla(actividades, horas, headers)

    def toggle_chart_studio(self):
        is_visible = self.chart_studio.isVisible()
        self.chart_studio.setVisible(not is_visible)
        if not is_visible:
            # Regenerar gráfico con los datos actuales seleccionados
            self.chart_studio.generar_grafico()
