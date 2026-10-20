"""
basedatos.py - Módulo Gestor de Bases de Datos estilo DBeaver para MultiTool
Orquestador principal con soporte multibase (SQLite, PostgreSQL, MySQL),
pestañas dinámicas cerrables, terminal integrada sin bloqueos, diagramas ER y menús contextuales.
"""
import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QLabel, QFileDialog, QMessageBox, 
    QTabWidget, QFrame, QInputDialog, QDialog, QMenu, QApplication,
    QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QFont, QKeySequence, QShortcut

from .submodulos.db_manager import (
    BaseConnection, RelationalConnection, DatabaseConnection, PostgreSQLConnection, MySQLConnection,
    MongoDBConnection, RedisConnection, LocalDocumentConnection
)
from .submodulos.connection_dialog import NewConnectionDialog
from .submodulos.sql_editor import SqlEditorWidget
from .submodulos.data_grid import DataGridWidget
from .submodulos.schema_designer import SchemaDesignerWidget
from .submodulos.er_diagram import ERDiagramWidget
from .submodulos.data_importer import DataImporterDialog
from .submodulos.query_history import QueryHistoryWidget
from .submodulos.document_viewer import DocumentViewerWidget, JsonDocumentEditDialog
from .submodulos.redis_viewer import RedisExplorerWidget

from .utils.storage_utils import (
    asegurar_directorio_estatico,
    sanitizar_nombre_db,
    ruta_db_estatica,
    listar_archivos_dbs_estaticas,
    listar_nombres_dbs_estaticas
)
from .utils.sample_db_generator import crear_base_datos_inicial_demo
from .utils.sql_parser import split_sql_statements, parse_special_command


class QueryExecutionWorker(QThread):
    """Hilo secundario para ejecutar sentencias SQL de forma asíncrona sin congelar la interfaz de usuario"""
    finished = pyqtSignal(object, object, float, int, str)

    def __init__(self, db_conn, sql: str, params: tuple = ()):
        super().__init__()
        self.db_conn = db_conn
        self.sql = sql
        self.params = params

    def run(self):
        try:
            rows, columns, duration_ms, affected, err = self.db_conn.execute_query(self.sql, self.params)
            self.finished.emit(rows, columns, duration_ms, affected, err)
        except Exception as e:
            self.finished.emit(None, None, 0.0, 0, str(e))


class TabBasedatos(QWidget):
    """
    Controlador principal de la suite Gestor de Bases de Datos estilo DBeaver.
    Compatible con la app principal y con el módulo de widgets flotantes.
    """
    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.context = context
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }) if context and hasattr(context, "app") else {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }

        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.databases_dir = self.ruta_usuario / "databases"
        self.config_path = self.ruta_usuario / "basedatos_connections.json"
        self.history_path = self.ruta_usuario / "basedatos_history.json"
        self.tabs_state_path = self.ruta_usuario / "basedatos_tabs_state.json"

        self._asegurar_directorio_estatico()
        self.active_db = None
        self._sql_counter = 0
        self._active_query_workers = []

        self.history_widget = QueryHistoryWidget(self.colores, self.history_path)
        self.history_widget.query_selected.connect(self._cargar_query_en_consola)

        self.init_ui()
        self._cargar_o_crear_conexion_inicial()

    # ── Gestión de Almacenamiento Estático y Seguridad ─────────────────

    def _asegurar_directorio_estatico(self) -> Path:
        return asegurar_directorio_estatico(self.databases_dir)

    def _sanitizar_nombre_db(self, name: str) -> str:
        return sanitizar_nombre_db(name)

    def _ruta_db_estatica(self, name: str) -> Optional[Path]:
        return ruta_db_estatica(self.databases_dir, name)

    def _listar_archivos_dbs_estaticas(self) -> List[Path]:
        return listar_archivos_dbs_estaticas(self.databases_dir)

    def _listar_nombres_dbs_estaticas(self) -> List[str]:
        return listar_nombres_dbs_estaticas(self.databases_dir)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header superior
        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.colores.get('bg_secundario', '#1E1E2E')},
                    stop:1 {self.colores.get('bg_principal', '#121218')});
                border-bottom: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
            }}
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 16, 0)
        h_layout.setSpacing(8)

        lbl_logo = QLabel("🗄️  Gestor de Bases de Datos")
        lbl_logo.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background: transparent;")
        h_layout.addWidget(lbl_logo)

        self.lbl_active_conn = QLabel("Sin conexión")
        self.lbl_active_conn.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
        h_layout.addWidget(self.lbl_active_conn)

        # Botón para abrir la carpeta de la base de datos en el Explorador de Windows
        self.btn_open_db_folder = QPushButton("📁")
        self.btn_open_db_folder.setFixedSize(28, 28)
        self.btn_open_db_folder.setToolTip("Abrir la carpeta del archivo de base de datos en el Explorador de Windows")
        self.btn_open_db_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_db_folder.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 13px;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.btn_open_db_folder.clicked.connect(self._abrir_carpeta_db_activa)
        h_layout.addWidget(self.btn_open_db_folder)

        # Selector rápido de base de datos / catálogo
        self.cb_database_selector = QComboBox()
        self.cb_database_selector.setFixedHeight(28)
        self.cb_database_selector.setMinimumWidth(110)
        self.cb_database_selector.setToolTip("Selector rápido de base de datos / catálogo activo")
        self.cb_database_selector.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: bold;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #F8FAFC;
                selection-background-color: {self.colores.get('acento', '#6366F1')};
                selection-color: white;
            }}
        """)
        self.cb_database_selector.currentIndexChanged.connect(self._on_database_selector_changed)
        h_layout.addWidget(self.cb_database_selector)

        # Controles Transaccionales (Autocommit ON/OFF, Commit, Rollback)
        self.btn_autocommit = QPushButton("⚡ Autocommit: ON")
        self.btn_autocommit.setCheckable(True)
        self.btn_autocommit.setChecked(True)
        self.btn_autocommit.setFixedHeight(28)
        self.btn_autocommit.setToolTip("Alternar modo Autocommit continuo o Transacciones Manuales")
        self.btn_autocommit.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #34D399;
                font-size: 11px;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 10px;
                border: 1px solid rgba(255,255,255,0.08);
                outline: none;
            }}
            QPushButton:hover {{
                border-color: #34D399;
            }}
        """)
        self.btn_autocommit.toggled.connect(self._toggle_autocommit)
        h_layout.addWidget(self.btn_autocommit)

        self.btn_commit = QPushButton("💾 Commit")
        self.btn_commit.setEnabled(False)
        self.btn_commit.setFixedHeight(28)
        self.btn_commit.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #CBD5E1;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 10px;
                border: 1px solid rgba(255,255,255,0.08);
                outline: none;
            }}
            QPushButton:enabled:hover {{
                background-color: rgba(52, 211, 153, 0.2);
                border-color: #34D399;
                color: #34D399;
            }}
            QPushButton:disabled {{
                color: #64748B;
            }}
        """)
        self.btn_commit.clicked.connect(self._do_commit)
        h_layout.addWidget(self.btn_commit)

        self.btn_rollback = QPushButton("↩️ Rollback")
        self.btn_rollback.setEnabled(False)
        self.btn_rollback.setFixedHeight(28)
        self.btn_rollback.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #CBD5E1;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 10px;
                border: 1px solid rgba(255,255,255,0.08);
                outline: none;
            }}
            QPushButton:enabled:hover {{
                background-color: rgba(248, 113, 113, 0.2);
                border-color: #F87171;
                color: #F87171;
            }}
            QPushButton:disabled {{
                color: #64748B;
            }}
        """)
        self.btn_rollback.clicked.connect(self._do_rollback)
        h_layout.addWidget(self.btn_rollback)

        # Botón Importar Datos
        btn_import = QPushButton("📥 Importar...")
        btn_import.setFixedHeight(28)
        btn_import.setToolTip("Importar archivo CSV o JSON a una tabla")
        btn_import.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #CBD5E1;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 10px;
                border: 1px solid rgba(255,255,255,0.08);
                outline: none;
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
        """)
        btn_import.clicked.connect(lambda: self.abrir_asistente_importacion())
        h_layout.addWidget(btn_import)

        # Botón Historial
        btn_history = QPushButton("📜 Historial")
        btn_history.setFixedHeight(28)
        btn_history.setToolTip("Ver y buscar en el historial de consultas ejecutadas")
        btn_history.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #CBD5E1;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 10px;
                border: 1px solid rgba(255,255,255,0.08);
                outline: none;
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
        """)
        btn_history.clicked.connect(self.abrir_historial_consultas)
        h_layout.addWidget(btn_history)

        h_layout.addStretch()

        # Botón Asistente Nueva Conexión Multibase
        btn_new_conn = QPushButton("🔌 Nueva Conexión...")
        btn_new_conn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_conn.setFixedHeight(28)
        btn_new_conn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 12px;
                border: none;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
            QPushButton:pressed {{
                background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn_new_conn.clicked.connect(self._abrir_dialogo_nueva_conexion)
        h_layout.addWidget(btn_new_conn)

        btn_open = QPushButton("📂 Abrir SQLite")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedHeight(28)
        btn_open.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #FFFFFF;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 10px;
                border: 1px solid rgba(255,255,255,0.08);
                outline: none;
            }}
            QPushButton:hover {{
                background-color: rgba(99, 102, 241, 0.2);
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
            QPushButton:pressed {{
                background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn_open.clicked.connect(self._dialogo_abrir_archivo)
        h_layout.addWidget(btn_open)

        btn_new_db = QPushButton("✨ Nueva DB")
        btn_new_db.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_db.setFixedHeight(28)
        btn_new_db.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #FFFFFF;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 10px;
                border: 1px solid rgba(255,255,255,0.08);
                outline: none;
            }}
            QPushButton:hover {{
                background-color: rgba(99, 102, 241, 0.2);
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn_new_db.clicked.connect(self._crear_nueva_db)
        h_layout.addWidget(btn_new_db)

        btn_demo = QPushButton("⚡ Memoria")
        btn_demo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_demo.setFixedHeight(28)
        btn_demo.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #FFFFFF;
                font-size: 11px;
                border-radius: 6px;
                padding: 0 10px;
                border: 1px solid rgba(255,255,255,0.08);
                outline: none;
            }}
            QPushButton:hover {{
                background-color: rgba(99, 102, 241, 0.2);
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn_demo.clicked.connect(self._conectar_memoria)
        h_layout.addWidget(btn_demo)

        main_layout.addWidget(header)

        # Splitter principal (Sidebar Izquierdo vs Pestañas Dinámicas Derecha)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                width: 2px;
            }}
        """)

        # ── Sidebar: Árbol de Objetos estilo DBeaver ──
        sidebar = QWidget()
        sidebar.setMinimumWidth(230)
        sidebar.setMaximumWidth(380)
        sidebar.setStyleSheet(f"background-color: {self.colores.get('bg_principal', '#121218')};")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(8, 8, 8, 8)
        sb_layout.setSpacing(6)

        sb_header = QHBoxLayout()
        lbl_sb = QLabel("OBJETOS DE BASE DE DATOS")
        lbl_sb.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 10px; letter-spacing: 0.5px;")
        sb_header.addWidget(lbl_sb)
        sb_header.addStretch()

        btn_tree_refresh = QPushButton("🔄")
        btn_tree_refresh.setToolTip("Refrescar esquema")
        btn_tree_refresh.setFixedSize(22, 22)
        btn_tree_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_tree_refresh.setStyleSheet("background: transparent; border: none; color: #AAB0B8; outline: none;")
        btn_tree_refresh.clicked.connect(self.refrescar_arbol)
        sb_header.addWidget(btn_tree_refresh)
        sb_layout.addLayout(sb_header)

        self.txt_tree_filter = QLineEdit()
        self.txt_tree_filter.setPlaceholderText("🔍 Filtrar tablas y columnas...")
        self.txt_tree_filter.setFixedHeight(26)
        self.txt_tree_filter.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 8px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.txt_tree_filter.textChanged.connect(self._filtrar_arbol)
        sb_layout.addWidget(self.txt_tree_filter)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #F1F5F9;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
                padding: 4px;
                font-size: 11px;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 4px 6px;
                border-radius: 4px;
            }}
            QTreeWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.04);
            }}
            QTreeWidget::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
                font-weight: bold;
            }}
        """)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._mostrar_menu_arbol)
        sb_layout.addWidget(self.tree)

        splitter.addWidget(sidebar)

        # ── Área Central: Pestañas Dinámicas de Trabajo ──
        work_area = QWidget()
        work_layout = QVBoxLayout(work_area)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(0)

        # Barra de herramientas de acciones de pestañas
        tabs_toolbar = QFrame()
        tabs_toolbar.setFixedHeight(38)
        tabs_toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border-bottom: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
            }}
        """)
        tb_layout = QHBoxLayout(tabs_toolbar)
        tb_layout.setContentsMargins(10, 0, 10, 0)
        tb_layout.setSpacing(8)

        btn_add_sql = QPushButton("⚡ + Nueva Consulta")
        btn_add_sql.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_sql.setFixedHeight(26)
        btn_add_sql.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                font-size: 10px;
                border-radius: 4px;
                padding: 0 10px;
                border: none;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        btn_add_sql.clicked.connect(lambda: self.abrir_nueva_consola_sql())
        tb_layout.addWidget(btn_add_sql)

        btn_show_er = QPushButton("📊 Diagrama ER")
        btn_show_er.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_show_er.setFixedHeight(26)
        btn_show_er.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
                font-size: 10px;
                border-radius: 4px;
                padding: 0 10px;
                border: 1px solid rgba(255,255,255,0.06);
                outline: none;
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn_show_er.clicked.connect(self.abrir_diagrama_er)
        tb_layout.addWidget(btn_show_er)

        btn_show_ddl = QPushButton("📐 + Diseñar Tabla (DDL)")
        btn_show_ddl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_show_ddl.setFixedHeight(26)
        btn_show_ddl.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
                font-size: 10px;
                border-radius: 4px;
                padding: 0 10px;
                border: 1px solid rgba(255,255,255,0.06);
                outline: none;
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn_show_ddl.clicked.connect(self.abrir_disenador_ddl)
        tb_layout.addWidget(btn_show_ddl)

        tb_layout.addStretch()

        work_layout.addWidget(tabs_toolbar)

        # Contenedor dinámico de pestañas cerrables
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._cerrar_pestana)
        self.tabs.currentChanged.connect(lambda _: self.guardar_estado_pestanas())
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores.get('bg_principal', '#121218')};
            }}
            QTabBar {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                border-bottom: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
            }}
            QTabBar::tab {{
                background: transparent;
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                padding: 8px 18px;
                font-size: 11px;
                font-weight: bold;
                outline: none;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                color: #FFFFFF;
                border-bottom: 2px solid {self.colores.get('acento', '#6366F1')};
                background: rgba(99, 102, 241, 0.12);
            }}
            QTabBar::tab:hover:!selected {{
                color: #FFFFFF;
                background: rgba(255, 255, 255, 0.03);
            }}
            QTabBar::close-button {{
                margin-left: 6px;
                padding: 2px;
                border-radius: 4px;
            }}
            QTabBar::close-button:hover {{
                background-color: rgba(248, 113, 113, 0.3);
                color: #F87171;
            }}
        """)

        work_layout.addWidget(self.tabs)
        splitter.addWidget(work_area)
        splitter.setSizes([260, 740])

        main_layout.addWidget(splitter)

        # Atajo global Ctrl+W para cerrar la pestaña activa actual
        self.shortcut_close = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_close.activated.connect(self._cerrar_pestana_actual)

    # ── Pestañas Dinámicas (Estilo DBeaver) ─────────────────────────────

    def _cerrar_pestana_actual(self):
        idx = self.tabs.currentIndex()
        if idx >= 0:
            self._cerrar_pestana(idx)

    def _agregar_pestana(self, widget: QWidget, title: str) -> int:
        idx = self.tabs.addTab(widget, title)
        self._configurar_boton_cierre_pestana(idx)
        self.guardar_estado_pestanas()
        return idx

    def _configurar_boton_cierre_pestana(self, index: int):
        widget = self.tabs.widget(index)
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(18, 18)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setToolTip("Cerrar pestaña (Ctrl+W)")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #CBD5E1;
                font-size: 11px;
                font-weight: bold;
                border: none;
                border-radius: 9px;
                padding: 0;
                margin: 0;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.45);
                color: #FFFFFF;
            }
        """)
        btn_close.clicked.connect(lambda _, w=widget: self._cerrar_pestana_de_widget(w))
        self.tabs.tabBar().setTabButton(index, self.tabs.tabBar().ButtonPosition.RightSide, btn_close)

    def _cerrar_pestana_de_widget(self, target_widget: QWidget):
        """Cierra la pestaña que contiene el widget objetivo de forma instantánea y segura"""
        if not target_widget:
            return
        idx = self.tabs.indexOf(target_widget)
        if idx >= 0:
            self._cerrar_pestana(idx)

    def _cerrar_pestana(self, index: int):
        """Cierra la pestaña especificada liberando recursos de forma segura"""
        if index < 0 or index >= self.tabs.count():
            return
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)

        # Proteger widgets permanentes (ej: historial) de ser eliminados
        if widget and widget is not getattr(self, "history_widget", None):
            widget.deleteLater()

        # Reasignar los botones de cierre a las pestañas restantes
        for i in range(self.tabs.count()):
            self._configurar_boton_cierre_pestana(i)

        # Guardar estado actualizado de pestañas
        self.guardar_estado_pestanas()

        # Si no quedan pestañas, abrir una consola SQL por defecto
        if self.tabs.count() == 0:
            self.abrir_nueva_consola_sql()

    def abrir_tabla_datos(self, table_name: str):
        """Abre o enfoca una pestaña interactiva para ver y editar los datos de una tabla"""
        # Buscar si ya está abierta
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, DataGridWidget) and widget.property("table_name") == table_name:
                self.tabs.setCurrentIndex(idx)
                self._cargar_datos_en_grid(table_name, widget)
                return widget

        grid = DataGridWidget(self.colores)
        grid.setProperty("table_name", table_name)
        grid.data_changed.connect(self._on_cell_edited)
        grid.delete_row_requested.connect(self._on_row_deleted)
        grid.refresh_requested.connect(lambda: self._cargar_datos_en_grid(table_name, grid))

        self._agregar_pestana(grid, f"📄 {table_name}")
        self.tabs.setCurrentWidget(grid)
        self._cargar_datos_en_grid(table_name, grid)
        return grid

    def abrir_coleccion_documentos(self, database_name: str, collection_name: str) -> Optional[DocumentViewerWidget]:
        """Abre o enfoca una pestaña interactiva para explorar documentos NoSQL (MongoDB / Local JSON)"""
        if not self.active_db or not self.active_db.is_connected:
            return None
        
        # Buscar si ya está abierta
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, DocumentViewerWidget) and widget.property("collection_name") == collection_name:
                self.tabs.setCurrentIndex(idx)
                widget.cargar_datos()
                return widget

        doc_viewer = DocumentViewerWidget(self.colores)
        doc_viewer.setProperty("collection_name", collection_name)
        doc_viewer.setProperty("database_name", database_name)
        doc_viewer.set_collection(self.active_db, database_name, collection_name)
        self._agregar_pestana(doc_viewer, f"🍃 {collection_name}")
        self.tabs.setCurrentWidget(doc_viewer)
        return doc_viewer

    def abrir_explorador_redis(self, db_index: int = 0) -> Optional[RedisExplorerWidget]:
        """Abre o enfoca una pestaña interactiva para explorar claves y terminal CLI de Redis"""
        if not self.active_db or not self.active_db.is_connected:
            return None

        # Buscar si ya está abierta
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, RedisExplorerWidget) and widget.property("db_index") == db_index:
                self.tabs.setCurrentIndex(idx)
                widget.cargar_claves()
                return widget

        redis_viewer = RedisExplorerWidget(self.colores)
        redis_viewer.setProperty("db_index", db_index)
        redis_viewer.set_connection(self.active_db, db_index)
        self._agregar_pestana(redis_viewer, f"🔴 Redis db{db_index}")
        self.tabs.setCurrentWidget(redis_viewer)
        return redis_viewer

    def abrir_nueva_consola_sql(self, initial_sql: str = "") -> SqlEditorWidget:
        """Abre una nueva pestaña de consola SQL con su terminal integrada"""
        self._sql_counter += 1
        editor = SqlEditorWidget(self.colores)
        editor.query_executed.connect(lambda sql, ed=editor: self.ejecutar_sql_desde_editor(sql, ed))
        editor.explain_requested.connect(lambda sql, ed=editor: self.analizar_plan_sql(sql, ed))
        
        tab_name = f"⚡ Consulta {self._sql_counter}"
        self._agregar_pestana(editor, tab_name)
        self.tabs.setCurrentWidget(editor)

        if initial_sql:
            editor.set_sql(initial_sql)
        if self.active_db and self.active_db.is_connected:
            p_str = getattr(self.active_db, "db_path", "") or str(getattr(self.active_db, "file_path", ""))
            editor.set_target_db(self.active_db.name, p_str)
        self._actualizar_autocompletado_en_consolas()
        return editor

    def abrir_asistente_importacion(self, target_table=""):
        """Abre el asistente para importar CSV o JSON a tabla nueva o existente"""
        if not self.active_db or not self.active_db.is_connected:
            QMessageBox.warning(self, "Importar", "Primero debes conectar una base de datos.")
            return
        dlg = DataImporterDialog(self.active_db, self.colores, self, default_table=target_table)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refrescar_arbol()
            self._recargar_todas_las_tablas_abiertas()

    def abrir_historial_consultas(self) -> QueryHistoryWidget:
        """Abre o enfoca la pestaña de historial persistente de consultas y snippets"""
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, QueryHistoryWidget):
                self.tabs.setCurrentIndex(idx)
                widget.load_history()
                return widget

        self._agregar_pestana(self.history_widget, "📜 Historial SQL")
        self.tabs.setCurrentWidget(self.history_widget)
        self.history_widget.load_history()
        return self.history_widget

    def _cargar_query_en_consola(self, sql: str):
        """Inyecta una consulta del historial en una consola SQL activa o nueva"""
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, SqlEditorWidget):
            current_widget.set_sql(sql)
            self.tabs.setCurrentWidget(current_widget)
        else:
            self.abrir_nueva_consola_sql(sql)

    def analizar_plan_sql(self, sql: str, editor: SqlEditorWidget):
        """Ejecuta EXPLAIN QUERY PLAN y devuelve el reporte de índices al editor"""
        if not self.active_db or not self.active_db.is_connected:
            editor.set_status("⚠️ No hay base de datos conectada.", is_error=True)
            return
        rows, cols, err = self.active_db.get_explain_plan(sql)
        editor.show_explain_results(sql, rows, cols, err)

    def _toggle_autocommit(self, checked: bool):
        """Alterna entre Autocommit continuo y control manual de transacciones"""
        if checked:
            self.btn_autocommit.setText("⚡ Autocommit: ON")
            self.btn_autocommit.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; color: #34D399; font-size: 11px; font-weight: bold; border-radius: 6px; padding: 0 10px; border: 1px solid rgba(255,255,255,0.08); outline: none;")
            self.btn_commit.setEnabled(False)
            self.btn_rollback.setEnabled(False)
            if self.active_db:
                self.active_db.set_autocommit(True)
        else:
            self.btn_autocommit.setText("🔒 Manual: OFF")
            self.btn_autocommit.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; color: #FBBF24; font-size: 11px; font-weight: bold; border-radius: 6px; padding: 0 10px; border: 1px solid rgba(255,255,255,0.08); outline: none;")
            self.btn_commit.setEnabled(True)
            self.btn_rollback.setEnabled(True)
            if self.active_db:
                self.active_db.set_autocommit(False)

    def _log_transaccion_terminal(self, accion: str, ok: bool, msg: str):
        """Registra la sentencia de transacción en la terminal del editor activo sin bloquear con popups"""
        editor = self.tabs.currentWidget()
        if not isinstance(editor, SqlEditorWidget):
            for i in range(self.tabs.count()):
                w = self.tabs.widget(i)
                if isinstance(w, SqlEditorWidget):
                    editor = w
                    break
        if isinstance(editor, SqlEditorWidget):
            if ok:
                editor.log_query(accion, 0.5, 0, False)
                editor.set_status(f"✅ {msg}")
            else:
                editor.log_error(accion, msg, 0.5)
                editor.set_status(f"❌ {msg}", is_error=True)

    def _do_commit(self):
        """Ejecuta COMMIT en la conexión activa sin popups bloqueantes"""
        if self.active_db:
            ok, msg = self.active_db.commit()
            self._log_transaccion_terminal("COMMIT;", ok, msg)
            if ok:
                self.refrescar_arbol()
                self._recargar_todas_las_tablas_abiertas()

    def _do_rollback(self):
        """Ejecuta ROLLBACK en la conexión activa sin popups bloqueantes"""
        if self.active_db:
            ok, msg = self.active_db.rollback()
            self._log_transaccion_terminal("ROLLBACK;", ok, msg)
            if ok:
                self.refrescar_arbol()
                self._recargar_todas_las_tablas_abiertas()

    def _on_database_selector_changed(self, idx: int):
        """Manejador para el selector rápido de base de datos/catálogo"""
        if idx < 0 or not self.active_db:
            return
        new_db = self.cb_database_selector.currentText().strip()
        if not new_db:
            return
        eng = getattr(self.active_db, "engine", "sqlite")
        if eng == "mysql":
            if getattr(self.active_db, "database", "") != new_db:
                self.active_db.execute_query(f"USE `{new_db}`;")
                self.active_db.database = new_db
                self.active_db.name = f"MySQL: {new_db}@{self.active_db.host}"
                self._actualizar_estado_conexion()
                self.refrescar_arbol()
        elif eng == "mongodb":
            if getattr(self.active_db, "database_name", "") != new_db:
                self.active_db.database_name = new_db
                self.active_db.name = f"MongoDB: {new_db}@{self.active_db.host}:{self.active_db.port}"
                self._guardar_conexion_activa(self.active_db)
                self._actualizar_estado_conexion()
                self.refrescar_arbol()
        elif eng == "postgresql":
            if getattr(self.active_db, "database", "") != new_db:
                new_conn = PostgreSQLConnection(
                    host=self.active_db.host,
                    port=self.active_db.port,
                    database=new_db,
                    user=self.active_db.user,
                    password=self.active_db.password,
                    name=f"PostgreSQL: {new_db}@{self.active_db.host}"
                )
                if new_conn.connect():
                    self.active_db.close()
                    self.active_db = new_conn
                    self._guardar_conexion_activa(self.active_db)
                    self._actualizar_estado_conexion()
                    self.refrescar_arbol()
        elif eng == "sqlite":
            clean_name = self._sanitizar_nombre_db(new_db)
            target = self._ruta_db_estatica(clean_name)
            if target and target.exists():
                curr_path = getattr(self.active_db, "db_path", "")
                if not curr_path or Path(curr_path).resolve() != target.resolve():
                    self.conectar_base_datos(str(target))
                    current_ed = self._obtener_consola_activa()
                    if current_ed:
                        current_ed.log_info(f"Conectado a base de datos estática '{target.name}'")


    def _actualizar_selector_databases(self):
        """Rellena el combo desplegable con las bases de datos disponibles"""
        if not self.active_db or not self.active_db.is_connected:
            self.cb_database_selector.blockSignals(True)
            self.cb_database_selector.clear()
            self.cb_database_selector.setEnabled(False)
            self.cb_database_selector.blockSignals(False)
            return

        self.cb_database_selector.blockSignals(True)
        self.cb_database_selector.clear()
        try:
            eng = getattr(self.active_db, "engine", "sqlite")
            if eng == "sqlite":
                # Listar todas las bases de datos estáticas en el almacenamiento seguro
                dbs = self._listar_nombres_dbs_estaticas()
                for db in dbs:
                    self.cb_database_selector.addItem(db)
                
                curr_path = getattr(self.active_db, "db_path", "")
                curr_stem = Path(curr_path).stem if curr_path and curr_path != ":memory:" else ""
                idx = self.cb_database_selector.findText(curr_stem)
                if idx >= 0:
                    self.cb_database_selector.setCurrentIndex(idx)
                self.cb_database_selector.setEnabled(len(dbs) > 0)
            else:
                dbs = self.active_db.get_databases()
                for db in dbs:
                    self.cb_database_selector.addItem(db)
                current_db = getattr(self.active_db, "database", "") or getattr(self.active_db, "name", "")
                idx = self.cb_database_selector.findText(current_db)
                if idx >= 0:
                    self.cb_database_selector.setCurrentIndex(idx)
                self.cb_database_selector.setEnabled(len(dbs) > 0)
        except Exception:
            pass
        self.cb_database_selector.blockSignals(False)

    def _filtrar_arbol(self, text: str):
        """Filtra en tiempo real los nodos del árbol de tablas y columnas"""
        query = text.strip().lower()
        root_count = self.tree.topLevelItemCount()
        for i in range(root_count):
            root_item = self.tree.topLevelItem(i)
            self._filtrar_nodo_arbol(root_item, query)

    def _filtrar_nodo_arbol(self, item: QTreeWidgetItem, query: str) -> bool:
        """Función recursiva para mostrar u ocultar nodos según la coincidencia de texto"""
        if not query:
            item.setHidden(False)
            for i in range(item.childCount()):
                self._filtrar_nodo_arbol(item.child(i), query)
            return True

        matches = query in item.text(0).lower()
        child_matches = False
        for i in range(item.childCount()):
            child = item.child(i)
            if self._filtrar_nodo_arbol(child, query):
                child_matches = True

        visible = matches or child_matches
        item.setHidden(not visible)
        if child_matches:
            item.setExpanded(True)
        return visible

    def abrir_diagrama_er(self) -> ERDiagramWidget:
        """Abre o enfoca el diagrama Entidad-Relación de la base de datos"""
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, ERDiagramWidget):
                self.tabs.setCurrentIndex(idx)
                widget.load_schema(self.active_db)
                return widget

        er = ERDiagramWidget(self.colores)
        er.btn_refresh.clicked.connect(lambda: er.load_schema(self.active_db))
        er.load_schema(self.active_db)
        self._agregar_pestana(er, "📊 Diagrama ER")
        self.tabs.setCurrentWidget(er)
        return er

    def abrir_disenador_ddl(self, table_name: str = "") -> SchemaDesignerWidget:
        """Abre o enfoca el asistente de creación de tablas y visor DDL"""
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, SchemaDesignerWidget):
                self.tabs.setCurrentIndex(idx)
                if table_name and self.active_db:
                    schema = self.active_db.get_table_schema(table_name)
                    widget.show_ddl(schema.get("ddl", ""))
                return widget

        designer = SchemaDesignerWidget(self.colores)
        designer.create_table_requested.connect(lambda sql: self.ejecutar_sql_desde_editor(sql))
        if table_name and self.active_db:
            schema = self.active_db.get_table_schema(table_name)
            designer.show_ddl(schema.get("ddl", ""))

        self._agregar_pestana(designer, "📐 Diseñador DDL")
        self.tabs.setCurrentWidget(designer)
        return designer

    def _cargar_datos_en_grid(self, table_name: str, grid: DataGridWidget):
        if not self.active_db:
            return
        schema = self.active_db.get_table_schema(table_name)
        pk_col = ""
        for c in schema.get("columns", []):
            if c.get("pk"):
                pk_col = c.get("name")
                break
        if not pk_col and schema.get("columns"):
            pk_col = schema["columns"][0]["name"]

        engine = getattr(self.active_db, "engine", "sqlite")
        quote = '`' if engine == "mysql" else '"'
        sql = f'SELECT * FROM {quote}{table_name}{quote} LIMIT 200;'
        rows, columns, duration_ms, _, err = self.active_db.execute_query(sql)
        if not err and columns is not None and rows is not None:
            grid.load_data(columns, rows, table_name, pk_col, duration_ms)

    # ── Gestión de Conexiones ──────────────────────────────────────────

    def _cargar_conexiones_guardadas(self) -> dict:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_connection": None, "saved_connections": []}

    def _guardar_conexion_activa(self, conn):
        saved = self._cargar_conexiones_guardadas()
        engine = getattr(conn, "engine", "sqlite")
        conn_dict = {
            "engine": engine,
            "name": conn.name
        }
        if engine == "sqlite":
            conn_dict["path"] = getattr(conn, "db_path", ":memory:")
        elif engine == "localdoc":
            conn_dict["path"] = str(getattr(conn, "file_path", ""))
        elif engine == "mongodb":
            conn_dict["uri"] = getattr(conn, "uri", "")
            conn_dict["host"] = getattr(conn, "host", "localhost")
            conn_dict["port"] = getattr(conn, "port", 27017)
            conn_dict["database"] = getattr(conn, "database_name", "test")
            conn_dict["user"] = getattr(conn, "user", "")
            conn_dict["password"] = getattr(conn, "password", "")
            conn_dict["auth_source"] = getattr(conn, "auth_source", "admin")
        elif engine == "redis":
            conn_dict["host"] = getattr(conn, "host", "localhost")
            conn_dict["port"] = getattr(conn, "port", 6379)
            conn_dict["db_index"] = getattr(conn, "db_index", 0)
            conn_dict["password"] = getattr(conn, "password", "")
        else:
            conn_dict["host"] = getattr(conn, "host", "localhost")
            conn_dict["port"] = getattr(conn, "port", 5432)
            conn_dict["database"] = getattr(conn, "database", "")
            conn_dict["user"] = getattr(conn, "user", "")
            conn_dict["password"] = getattr(conn, "password", "")

        saved["last_connection"] = conn_dict
        
        conns_list = saved.get("saved_connections", [])
        if not any(c.get("name") == conn.name for c in conns_list):
            conns_list.append(conn_dict)
        saved["saved_connections"] = conns_list

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(saved, f, indent=4)
        except Exception:
            pass

    def _reconstruir_conexion(self, data: dict):
        if not data or not isinstance(data, dict):
            return None
        engine = data.get("engine", "sqlite")
        name = data.get("name", "")
        if engine == "sqlite":
            return DatabaseConnection(data.get("path", ":memory:"), name=name)
        elif engine == "postgresql":
            return PostgreSQLConnection(
                host=data.get("host", "localhost"),
                port=data.get("port", 5432),
                database=data.get("database", "postgres"),
                user=data.get("user", "postgres"),
                password=data.get("password", ""),
                name=name
            )
        elif engine == "mysql":
            return MySQLConnection(
                host=data.get("host", "localhost"),
                port=data.get("port", 3306),
                database=data.get("database", ""),
                user=data.get("user", "root"),
                password=data.get("password", ""),
                name=name
            )
        elif engine == "mongodb":
            return MongoDBConnection(
                uri=data.get("uri", ""),
                host=data.get("host", "localhost"),
                port=data.get("port", 27017),
                database=data.get("database", "test"),
                user=data.get("user", ""),
                password=data.get("password", ""),
                auth_source=data.get("auth_source", "admin"),
                name=name
            )
        elif engine == "redis":
            return RedisConnection(
                host=data.get("host", "localhost"),
                port=data.get("port", 6379),
                db_index=data.get("db_index", 0),
                password=data.get("password", ""),
                name=name
            )
        elif engine == "localdoc":
            return LocalDocumentConnection(
                file_path=data.get("path", "databases/local_store.nosql.json"),
                name=name
            )
        return None

    def _cargar_o_crear_conexion_inicial(self):
        """Carga la última conexión o inicializa la base de datos de muestra en la ruta estática segura"""
        self._asegurar_directorio_estatico()
        sample_db = self.databases_dir / "multitool_sample.db"

        # Migración automática si existía en la raíz de usuario
        old_sample = self.ruta_usuario / "multitool_sample.db"
        if old_sample.exists() and not sample_db.exists():
            try:
                import shutil
                shutil.move(str(old_sample), str(sample_db))
            except Exception:
                pass

        # Verificar si la base de datos de muestra existe y tiene el esquema relacional completo
        necesita_crear = not sample_db.exists()
        if not necesita_crear:
            try:
                test_conn = DatabaseConnection(str(sample_db))
                if test_conn.connect():
                    tbl_names = [t.get("name") for t in test_conn.get_tables()]
                    if "departamentos" not in tbl_names or "proyectos" not in tbl_names or "comentarios" not in tbl_names:
                        necesita_crear = True
                    test_conn.close()
            except Exception:
                necesita_crear = True

        if necesita_crear:
            self._crear_base_datos_inicial(str(sample_db))

        saved = self._cargar_conexiones_guardadas()
        last_conn = saved.get("last_connection")
        conectado = False
        if last_conn and isinstance(last_conn, dict):
            conn = self._reconstruir_conexion(last_conn)
            if conn and conn.connect():
                self.active_db = conn
                self._actualizar_estado_conexion()
                conectado = True

        if not conectado:
            self.conectar_base_datos(str(sample_db))

        self.refrescar_arbol()

        # Restaurar estado persistente de pestañas abiertas o abrir consola por defecto
        if not self._restaurar_estado_pestanas():
            self.abrir_nueva_consola_sql()

    def _crear_base_datos_inicial(self, path_db: str):
        """Crea la base de datos inicial multitool_sample.db con un esquema relacional rico y llaves foráneas"""
        crear_base_datos_inicial_demo(path_db, DatabaseConnection)

    def _actualizar_estado_conexion(self):
        if not self.active_db or not self.active_db.is_connected:
            self.lbl_active_conn.setText("🔴 Sin conexión")
            self.lbl_active_conn.setStyleSheet("color: #F87171; font-size: 11px; background: transparent;")
            self.lbl_active_conn.setToolTip("No hay base de datos conectada.")
            self._actualizar_selector_databases()
            self._actualizar_destino_db_en_consolas("", "")
            return

        engine = getattr(self.active_db, "engine", "sqlite")
        icons = {
            "sqlite": "🗄️", "postgresql": "🐘", "mysql": "🐬",
            "mongodb": "🍃", "redis": "🔴", "localdoc": "📁"
        }
        icon = icons.get(engine, "🗄️")
        db_path = getattr(self.active_db, "db_path", "") or str(getattr(self.active_db, "file_path", ""))
        
        if db_path and db_path != ":memory:":
            file_name = Path(db_path).name
            self.lbl_active_conn.setText(f"🟢 Conectado: {icon} {self.active_db.name}  📁 ({file_name})")
            tip = (
                f"Base de datos activa: {self.active_db.name}\n"
                f"Motor: {engine.upper()}\n"
                f"Ubicación en disco: {db_path}\n\n"
                f"💡 Todas las tablas, datos y modificaciones SQL se guardan físicamente en este archivo."
            )
        elif db_path == ":memory:":
            self.lbl_active_conn.setText(f"🟢 Conectado: {icon} {self.active_db.name} [Memoria]")
            tip = "Base de datos volátil en memoria (:memory:)\n⚠️ Los datos no se guardan en disco y se perderán al cerrar la sesión."
        else:
            host_info = getattr(self.active_db, "host", "")
            self.lbl_active_conn.setText(f"🟢 Conectado: {icon} {self.active_db.name}")
            tip = f"Conexión remota: {self.active_db.name}\nMotor: {engine.upper()}\nHost: {host_info}"

        self.lbl_active_conn.setToolTip(tip)
        self.lbl_active_conn.setStyleSheet("color: #34D399; font-size: 11px; font-weight: bold; background: transparent;")
        self._actualizar_selector_databases()
        self._actualizar_destino_db_en_consolas(self.active_db.name, db_path)

    def _abrir_carpeta_db_activa(self):
        """Abre la ubicación en disco de la base de datos activa en el Explorador de Windows"""
        target_path = None
        if self.active_db:
            p_str = getattr(self.active_db, "db_path", "") or str(getattr(self.active_db, "file_path", ""))
            if p_str and p_str != ":memory:":
                p = Path(p_str)
                if p.exists():
                    target_path = p.resolve()

        import subprocess
        if target_path:
            subprocess.Popen(f'explorer /select,"{target_path}"')
        else:
            self._asegurar_directorio_estatico()
            subprocess.Popen(f'explorer "{self.databases_dir.resolve()}"')

    def _actualizar_destino_db_en_consolas(self, name: str, path: str):
        """Actualiza el indicador visual de base de datos destino en todas las consolas SQL abiertas"""
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, SqlEditorWidget):
                widget.set_target_db(name, path)

    def _abrir_dialogo_nueva_conexion(self):
        dlg = NewConnectionDialog(self.colores, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_connection:
            if self.active_db:
                self.active_db.close()
            self.active_db = dlg.result_connection
            self._guardar_conexion_activa(self.active_db)
            self._actualizar_estado_conexion()
            self.refrescar_arbol()

    def conectar_base_datos(self, path: str) -> bool:
        if self.active_db:
            self.active_db.close()

        if str(path).lower().endswith(".json"):
            self.active_db = LocalDocumentConnection(path)
        else:
            self.active_db = DatabaseConnection(path)

        if self.active_db.connect():
            self._guardar_conexion_activa(self.active_db)
            self._actualizar_estado_conexion()
            self.refrescar_arbol()
            return True
        else:
            self.lbl_active_conn.setText(f"🔴 Error: {self.active_db.last_error}")
            self.lbl_active_conn.setStyleSheet("color: #F87171; font-size: 11px; background: transparent;")
            return False

    def conectar_desde_config(self, conn_data: dict, show_dialog: bool = True) -> bool:
        if not conn_data or not isinstance(conn_data, dict):
            return False

        engine = conn_data.get("engine", "sqlite")
        path_str = conn_data.get("path", "")

        # Si es una base de datos basada en archivo (SQLite o LocalDoc), verificar existencia física
        if engine in ("sqlite", "localdoc") and path_str and path_str != ":memory:":
            p = Path(path_str)
            if not p.exists():
                if show_dialog:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("Archivo de Base de Datos No Encontrado")
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    msg_box.setText(
                        f"El archivo de base de datos '{conn_data.get('name')}' no existe en el disco:\n\n"
                        f"📁 {path_str}\n\n"
                        f"Es posible que haya sido eliminado anteriormente."
                    )
                    msg_box.setInformativeText("¿Qué deseas hacer con esta conexión guardada?")
                    btn_delete = msg_box.addButton("🗑️ Eliminar Conexión Guardada", QMessageBox.ButtonRole.DestructiveRole)
                    btn_recreate = msg_box.addButton("🆕 Crear Base Vacía en esta Ruta", QMessageBox.ButtonRole.ActionRole)
                    btn_cancel = msg_box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
                    msg_box.setDefaultButton(btn_delete)
                    msg_box.exec()

                    clicked = msg_box.clickedButton()
                    if clicked == btn_delete:
                        self._eliminar_conexion_guardada(conn_data.get("name"))
                        return False
                    elif clicked == btn_cancel or clicked is None:
                        return False
                    elif clicked == btn_recreate:
                        current_ed = self._obtener_consola_activa()
                        if current_ed:
                            current_ed.log_info(f"🆕 Se ha inicializado una nueva base de datos vacía en: {path_str}")
                else:
                    return False

        conn = self._reconstruir_conexion(conn_data)
        if not conn:
            return False
        if self.active_db:
            self.active_db.close()
        self.active_db = conn
        if self.active_db.connect():
            self._guardar_conexion_activa(self.active_db)
            self._actualizar_estado_conexion()
            self.refrescar_arbol()
            return True
        else:
            if show_dialog:
                QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a '{conn.name}':\n\n{conn.last_error}")
            self._actualizar_estado_conexion()
            return False


    def _eliminar_archivo_db_y_limpiar_conexiones(self, target_path: Path, db_name: str = "") -> bool:
        """
        Elimina físicamente el archivo de base de datos del disco y purga
        todas las conexiones guardadas asociadas en db_connections.json para evitar
        conexiones huérfanas o bases fantasmas.
        """
        try:
            resolved_target = target_path.resolve()
        except Exception:
            resolved_target = target_path

        # 1. Si es la conexión activa actual, desconectar y conmutar a sample o memoria
        if self.active_db:
            curr_path = getattr(self.active_db, "db_path", "") or str(getattr(self.active_db, "file_path", ""))
            if curr_path and curr_path != ":memory:":
                try:
                    if Path(curr_path).resolve() == resolved_target:
                        self.active_db.close()
                        sample = self.databases_dir / "multitool_sample.db"
                        if sample.exists() and sample.resolve() != resolved_target:
                            self.conectar_base_datos(str(sample))
                        else:
                            self.conectar_base_datos(":memory:")
                except Exception:
                    pass

        # 2. Eliminar el archivo físico
        if target_path.exists():
            try:
                os.remove(str(target_path))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el archivo:\n{e}")
                return False

        # 3. Purgar conexiones guardadas asociadas a este archivo o nombre
        saved = self._cargar_conexiones_guardadas()
        conns_list = saved.get("saved_connections", [])
        nuevas_conns = []
        for c in conns_list:
            c_path = c.get("path")
            coincide_path = False
            if c_path and c_path != ":memory:":
                try:
                    if Path(c_path).resolve() == resolved_target:
                        coincide_path = True
                except Exception:
                    pass
            coincide_nombre = bool(db_name and c.get("name") in (db_name, f"{db_name}.db", f"{db_name}.json", target_path.name, target_path.stem))
            if not coincide_path and not coincide_nombre:
                nuevas_conns.append(c)

        saved["saved_connections"] = nuevas_conns

        # Limpiar last_connection si apuntaba a este archivo
        last_c = saved.get("last_connection")
        if last_c and isinstance(last_c, dict):
            last_p = last_c.get("path")
            coincide_last = False
            if last_p and last_p != ":memory:":
                try:
                    if Path(last_p).resolve() == resolved_target:
                        coincide_last = True
                except Exception:
                    pass
            if coincide_last or (db_name and last_c.get("name") in (db_name, f"{db_name}.db", f"{db_name}.json", target_path.name, target_path.stem)):
                saved["last_connection"] = None

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(saved, f, indent=4)
        except Exception:
            pass

        self.refrescar_arbol()
        self._actualizar_selector_databases()
        return True

    def _dialogo_abrir_archivo(self):
        self._asegurar_directorio_estatico()
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Base de Datos SQLite", 
            str(self.databases_dir), 
            "Bases de Datos SQLite (*.db *.sqlite *.sqlite3 *.db3);;Todos los archivos (*.*)"
        )
        if path:
            self.conectar_base_datos(path)

    def _crear_nueva_db(self):
        """Crea una nueva base de datos estática en el directorio seguro a sugerencia de ingeniería"""
        self._asegurar_directorio_estatico()
        name, ok = QInputDialog.getText(
            self, "Nueva Base de Datos Estática", 
            f"Nombre de la nueva base de datos:",
            QLineEdit.EchoMode.Normal, "mi_base_datos"
        )
        if not ok or not name.strip():
            return

        clean_name = self._sanitizar_nombre_db(name)
        if not clean_name:
            QMessageBox.warning(self, "Nombre Inválido", "El nombre contiene caracteres no válidos. Use únicamente letras, números y guiones.")
            return

        target_path = self._ruta_db_estatica(clean_name)
        if not target_path:
            QMessageBox.critical(self, "Error de Seguridad", "Nombre o ruta no permitida por seguridad.")
            return

        if target_path.exists():
            confirm = QMessageBox.question(
                self, "Base Existente",
                f"La base de datos '{clean_name}.db' ya existe.\n¿Deseas conectarte a ella?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.conectar_base_datos(str(target_path))
            return

        try:
            init_conn = DatabaseConnection(str(target_path), name=f"{clean_name}.db")
            if init_conn.connect():
                init_conn.execute_query("PRAGMA foreign_keys = ON;")
                init_conn.close()
            self.conectar_base_datos(str(target_path))
            current_ed = self._obtener_consola_activa()
            if current_ed:
                current_ed.log_info(f"Base de datos estática '{clean_name}.db' creada y conectada en {self.databases_dir}")
                current_ed.set_status(f"✅ Base de datos '{clean_name}.db' creada con éxito.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear la base de datos:\n{e}")

    def _conectar_memoria(self):
        self.conectar_base_datos(":memory:")

    # ── Explorador de Esquemas & Menús Contextuales ───────────────────

    def refrescar_arbol(self):
        self.tree.clear()

        # 1. Conexiones Guardadas
        saved = self._cargar_conexiones_guardadas()
        conns_list = saved.get("saved_connections", [])
        if conns_list:
            node_saved = QTreeWidgetItem(self.tree)
            node_saved.setText(0, f"⭐ Conexiones Guardadas ({len(conns_list)})")
            node_saved.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
            node_saved.setExpanded(True)
            for c_data in conns_list:
                c_item = QTreeWidgetItem(node_saved)
                eng = c_data.get("engine", "sqlite")
                c_path = c_data.get("path")
                c_name = c_data.get("name", "Conexión")
                exists = True
                if eng in ("sqlite", "localdoc") and c_path and c_path != ":memory:":
                    try:
                        exists = Path(c_path).exists()
                    except Exception:
                        exists = False

                icons = {
                    "sqlite": "🗄️", "postgresql": "🐘", "mysql": "🐬",
                    "mongodb": "🍃", "redis": "🔴", "localdoc": "📁"
                }
                icon = icons.get(eng, "🗄️")
                if not exists:
                    c_item.setText(0, f"⚠️ {c_name} [No existe en disco]")
                    c_item.setToolTip(0, f"⚠️ El archivo de base de datos fue eliminado del disco:\n{c_path}\n\n(Doble clic o clic derecho para eliminar esta conexión guardada)")
                    c_item.setForeground(0, QColor("#F87171"))
                else:
                    c_item.setText(0, f"{icon} {c_name}")
                    if c_path and c_path != ":memory:":
                        c_item.setToolTip(0, f"Ruta en disco: {c_path}\nMotor: {eng.upper()}")
                c_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "saved_conn", "data": c_data, "file_exists": exists})

        # 2. Bases de Datos Estáticas Seguras (directorio local databases/)
        static_dbs = self._listar_archivos_dbs_estaticas()
        if static_dbs:
            node_static = QTreeWidgetItem(self.tree)
            node_static.setText(0, f"📁 Bases de Datos Estáticas ({len(static_dbs)})")
            node_static.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
            node_static.setExpanded(True)
            curr_active_path = getattr(self.active_db, "db_path", "") or str(getattr(self.active_db, "file_path", "")) if self.active_db else ""
            for db_file in static_dbs:
                item_db = QTreeWidgetItem(node_static)
                is_active = False
                try:
                    if curr_active_path and curr_active_path != ":memory:":
                        is_active = (Path(curr_active_path).resolve() == db_file.resolve())
                except Exception:
                    pass
                is_json = db_file.suffix.lower() == ".json"
                if is_active:
                    status_icon = "🟢"
                else:
                    status_icon = "📁" if is_json else "💾"
                item_db.setText(0, f"{status_icon} {db_file.name}")
                if is_active:
                    item_db.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
                item_db.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "static_db",
                    "path": str(db_file),
                    "name": db_file.name
                })

        # 3. Conexión Activa y Esquema
        if not self.active_db or not self.active_db.is_connected:
            return

        eng = getattr(self.active_db, "engine", "sqlite")
        eng_type = getattr(self.active_db, "engine_type", "relational")
        icons = {
            "sqlite": "🗄️", "postgresql": "🐘", "mysql": "🐬",
            "mongodb": "🍃", "redis": "🔴", "localdoc": "📁"
        }
        icon = icons.get(eng, "🗄️")
        root = QTreeWidgetItem(self.tree)
        root.setText(0, f"{icon} {self.active_db.name}")
        root.setFont(0, QFont("Segoe UI", 10, QFont.Weight.Bold))
        root.setExpanded(True)

        if eng_type == "document":
            cols = self.active_db.get_collections()
            node_cols = QTreeWidgetItem(root)
            node_cols.setText(0, f"📁 Colecciones ({len(cols)})")
            node_cols.setExpanded(True)

            target_db = getattr(self.active_db, "database_name", "")
            for col_info in cols:
                col_name = col_info.get("name", "")
                doc_cnt = col_info.get("doc_count", 0)
                col_item = QTreeWidgetItem(node_cols)
                col_item.setText(0, f"📄 {col_name} ({doc_cnt} docs)")
                col_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "collection",
                    "db": target_db,
                    "name": col_name
                })
                if hasattr(self.active_db, "get_collection_indexes"):
                    indexes = self.active_db.get_collection_indexes(target_db, col_name)
                    for idx in indexes:
                        idx_item = QTreeWidgetItem(col_item)
                        idx_item.setText(0, f"⚡ {idx.get('name')}")

        elif eng_type == "kv":
            node_dbs = QTreeWidgetItem(root)
            node_dbs.setText(0, "📁 Keyspaces (16)")
            node_dbs.setExpanded(True)

            curr_idx = getattr(self.active_db, "db_index", 0)
            for i in range(16):
                db_item = QTreeWidgetItem(node_dbs)
                is_active_db = (curr_idx == i)
                prefix = "🟢" if is_active_db else "🔴"
                db_item.setText(0, f"{prefix} db{i}")
                if is_active_db:
                    db_item.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
                db_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "redis_db", "db_index": i})

        else:
            tables = self.active_db.get_tables()
            tbls_only = [t for t in tables if t.get("type") == "table"]
            views_only = [t for t in tables if t.get("type") == "view"]

            node_tables = QTreeWidgetItem(root)
            node_tables.setText(0, f"📁 Tablas ({len(tbls_only)})")
            node_tables.setExpanded(True)

            node_views = QTreeWidgetItem(root)
            node_views.setText(0, f"👁️ Vistas ({len(views_only)})")

            for t in tables:
                parent_node = node_tables if t.get("type") == "table" else node_views
                t_item = QTreeWidgetItem(parent_node)
                cnt = f" ({t.get('row_count', 0)})" if t.get("type") == "table" else ""
                t_item.setText(0, f"📄 {t['name']}{cnt}")
                t_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "table", "name": t["name"]})

                # Sub-elementos: Columnas
                schema = self.active_db.get_table_schema(t["name"])
                for c in schema.get("columns", []):
                    col_item = QTreeWidgetItem(t_item)
                    c_icon = "🔑" if c.get("pk") else "📋"
                    col_item.setText(0, f"{c_icon} {c['name']} : {c.get('type', '')}")
                    col_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "column", "table": t["name"], "name": c["name"]})

                # Sub-elementos: Índices
                for idx in schema.get("indexes", []):
                    idx_item = QTreeWidgetItem(t_item)
                    idx_item.setText(0, f"⚡ {idx.get('name', '')}")

        # Sincronizar autocompletado en todas las consolas abiertas
        self._actualizar_autocompletado_en_consolas()

    def _actualizar_autocompletado_en_consolas(self):
        """Alimenta los editores SQL con los nombres de tablas, colecciones y columnas/campos"""
        if not self.active_db or not self.active_db.is_connected:
            return
        tables = []
        columns = []
        table_columns_map = {}
        try:
            eng_type = getattr(self.active_db, "engine_type", "relational")
            if eng_type == "relational":
                for t in self.active_db.get_tables():
                    t_name = t.get("name", "")
                    if t_name:
                        tables.append(t_name)
                        schema = self.active_db.get_table_schema(t_name)
                        col_list = []
                        for col in schema.get("columns", []):
                            c_name = col.get("name", "")
                            if c_name:
                                col_list.append(c_name)
                                if c_name not in columns:
                                    columns.append(c_name)
                        table_columns_map[t_name] = col_list
            elif eng_type == "document":
                cols = self.active_db.get_collections()
                for c in cols:
                    c_name = c.get("name", "")
                    if c_name:
                        tables.append(c_name)
                        sample_docs, _, _, _ = self.active_db.find_documents(
                            getattr(self.active_db, "database_name", ""), c_name, limit=5
                        )
                        doc_keys = []
                        for doc in sample_docs:
                            for k in doc.keys():
                                if k not in doc_keys:
                                    doc_keys.append(k)
                                if k not in columns:
                                    columns.append(k)
                        table_columns_map[c_name] = doc_keys

            for idx in range(self.tabs.count()):
                w = self.tabs.widget(idx)
                if isinstance(w, SqlEditorWidget):
                    w.update_autocomplete_words(tables, columns, table_columns_map)
        except Exception:
            pass

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, col: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data.get("type") == "table":
            table_name = data.get("name")
            self.abrir_tabla_datos(table_name)
        elif data.get("type") == "collection":
            self.abrir_coleccion_documentos(data.get("db", ""), data.get("name"))
        elif data.get("type") == "redis_db":
            self.abrir_explorador_redis(data.get("db_index", 0))

    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem, col: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data.get("type") == "saved_conn":
            self.conectar_desde_config(data.get("data", {}))
        elif data.get("type") == "static_db":
            self.conectar_base_datos(data.get("path"))
        elif data.get("type") == "table":
            table_name = data.get("name")
            engine = getattr(self.active_db, "engine", "sqlite")
            quote = '`' if engine == "mysql" else '"'
            self.abrir_nueva_consola_sql(f'SELECT * FROM {quote}{table_name}{quote} LIMIT 100;\n')
        elif data.get("type") == "collection":
            self.abrir_coleccion_documentos(data.get("db", ""), data.get("name"))
        elif data.get("type") == "redis_db":
            self.abrir_explorador_redis(data.get("db_index", 0))

    def _mostrar_menu_arbol(self, pos):
        """Menú contextual de clic derecho para los elementos del árbol lateral"""
        item = self.tree.itemAt(pos)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF !important;
            }}
        """)

        item_type = data.get("type")

        if item_type == "static_db":
            db_path = data.get("path")
            db_name = data.get("name")
            a_connect = menu.addAction("🔌 Conectar")
            a_sql = menu.addAction("⚡ Abrir en Editor SQL")
            a_er = menu.addAction("📊 Ver Diagrama ER")
            a_copy_path = menu.addAction("📋 Copiar Ruta de Archivo")
            menu.addSeparator()
            a_delete = menu.addAction("❌ Eliminar Base de Datos")

            action = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if not action:
                return

            if action == a_connect:
                self.conectar_base_datos(db_path)
            elif action == a_sql:
                self.conectar_base_datos(db_path)
                self.abrir_nueva_consola_sql()
            elif action == a_er:
                self.conectar_base_datos(db_path)
                self.abrir_diagrama_er()
            elif action == a_copy_path:
                QApplication.clipboard().setText(db_path)
            elif action == a_delete:
                confirm = QMessageBox.question(
                    self, "Eliminar Base de Datos",
                    f"¿Estás seguro de eliminar permanentemente la base de datos estática '{db_name}'?\n\n"
                    f"Ruta: {db_path}\n\n"
                    f"💡 Esta acción eliminará el archivo del disco y purgará todas las conexiones guardadas asociadas.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirm == QMessageBox.StandardButton.Yes:
                    self._eliminar_archivo_db_y_limpiar_conexiones(Path(db_path), db_name)

        elif item_type == "table":
            tbl = data.get("name")
            a_data = menu.addAction("🔍 Ver Datos (SELECT *)")
            a_sql = menu.addAction("⚡ Abrir en Editor SQL")
            a_er = menu.addAction("📊 Ver en Diagrama ER")
            a_ddl = menu.addAction("📐 Ver Estructura / DDL")
            menu.addSeparator()
            a_import = menu.addAction("📥 Importar Datos (CSV / JSON)...")
            a_copy = menu.addAction("📋 Copiar Nombre de Tabla")
            menu.addSeparator()
            a_truncate = menu.addAction("🗑️ Vaciar Tabla (DELETE FROM)")
            a_drop = menu.addAction("❌ Eliminar Tabla (DROP TABLE)")

            action = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if not action:
                return

            engine = getattr(self.active_db, "engine", "sqlite")
            quote = '`' if engine == "mysql" else '"'

            if action == a_data:
                self.abrir_tabla_datos(tbl)
            elif action == a_sql:
                self.abrir_nueva_consola_sql(f'SELECT * FROM {quote}{tbl}{quote} LIMIT 100;\n')
            elif action == a_er:
                self.abrir_diagrama_er()
            elif action == a_ddl:
                self.abrir_disenador_ddl(tbl)
            elif action == a_import:
                self.abrir_asistente_importacion(tbl)
            elif action == a_copy:
                QApplication.clipboard().setText(tbl)
            elif action == a_truncate:
                confirm = QMessageBox.question(
                    self, "Vaciar Tabla", f"¿Estás seguro de eliminar todos los registros de '{tbl}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirm == QMessageBox.StandardButton.Yes:
                    self.ejecutar_sql_desde_editor(f'DELETE FROM {quote}{tbl}{quote};')
            elif action == a_drop:
                confirm = QMessageBox.question(
                    self, "Eliminar Tabla", f"¿Estás seguro de eliminar PERMANENTEMENTE la tabla '{tbl}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirm == QMessageBox.StandardButton.Yes:
                    self.ejecutar_sql_desde_editor(f'DROP TABLE {quote}{tbl}{quote};')

        elif item_type == "column":
            col_name = data.get("name")
            tbl_name = data.get("table")
            a_copy = menu.addAction("📋 Copiar Nombre de Columna")
            a_query = menu.addAction(f"🔍 Consultar Columna '{col_name}'")

            action = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if not action:
                return

            if action == a_copy:
                QApplication.clipboard().setText(col_name)
            elif action == a_query:
                engine = getattr(self.active_db, "engine", "sqlite")
                quote = '`' if engine == "mysql" else '"'
                self.abrir_nueva_consola_sql(f'SELECT {quote}{col_name}{quote} FROM {quote}{tbl_name}{quote} LIMIT 100;\n')

        elif item_type == "saved_conn":
            conn_data = data.get("data", {})
            c_path = conn_data.get("path")
            c_exists = data.get("file_exists", True)

            a_connect = menu.addAction("🔌 Conectar")
            a_copy_path = menu.addAction("📋 Copiar Ruta / Parámetros")
            a_open_folder = None
            if c_path and c_path != ":memory:" and c_exists:
                a_open_folder = menu.addAction("📂 Mostrar en Explorador de Archivos")
            menu.addSeparator()
            a_remove = menu.addAction("🗑️ Eliminar Conexión Guardada")

            action = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if not action:
                return

            if action == a_connect:
                self.conectar_desde_config(conn_data)
            elif action == a_copy_path:
                info_text = c_path or str(conn_data)
                QApplication.clipboard().setText(info_text)
            elif a_open_folder and action == a_open_folder:
                import subprocess
                p = Path(c_path).resolve()
                subprocess.Popen(f'explorer /select,"{p}"')
            elif action == a_remove:
                self._eliminar_conexion_guardada(conn_data.get("name"))

        elif item_type == "collection":
            col_name = data.get("name")
            db_name = data.get("db", "")
            a_view = menu.addAction("🔍 Ver Documentos")
            a_insert = menu.addAction("➕ Insertar Documento...")
            a_copy = menu.addAction("📋 Copiar Nombre de Colección")
            menu.addSeparator()
            a_empty = menu.addAction("🗑️ Vaciar Colección")
            a_drop = menu.addAction("❌ Eliminar Colección")

            action = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if not action:
                return

            if action == a_view:
                self.abrir_coleccion_documentos(db_name, col_name)
            elif action == a_insert:
                doc_viewer = self.abrir_coleccion_documentos(db_name, col_name)
                if doc_viewer:
                    doc_viewer.insertar_documento_dialogo()
            elif action == a_copy:
                QApplication.clipboard().setText(col_name)
            elif action == a_empty:
                confirm = QMessageBox.question(
                    self, "Vaciar Colección", f"¿Estás seguro de eliminar todos los documentos de '{col_name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirm == QMessageBox.StandardButton.Yes:
                    if hasattr(self.active_db, "delete_document"):
                        self.active_db.delete_document(db_name, col_name, {})
                        self.refrescar_arbol()
                        self._recargar_todas_las_tablas_abiertas()
            elif action == a_drop:
                confirm = QMessageBox.question(
                    self, "Eliminar Colección", f"¿Estás seguro de eliminar permanentemente la colección '{col_name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirm == QMessageBox.StandardButton.Yes:
                    if hasattr(self.active_db, "drop_collection"):
                        self.active_db.drop_collection(db_name, col_name)
                        self.refrescar_arbol()
                        self._recargar_todas_las_tablas_abiertas()

        elif item_type == "redis_db":
            db_index = data.get("db_index", 0)
            a_explore = menu.addAction(f"🔍 Explorar Claves en db{db_index}")
            a_flush = menu.addAction(f"⚠️ Vaciar DB (FLUSHDB db{db_index})")

            action = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if not action:
                return

            if action == a_explore:
                self.abrir_explorador_redis(db_index)
            elif action == a_flush:
                confirm = QMessageBox.question(
                    self, "Vaciar Redis DB", f"¿Estás seguro de ejecutar FLUSHDB en db{db_index}? Se eliminarán todas sus claves.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirm == QMessageBox.StandardButton.Yes:
                    if hasattr(self.active_db, "execute_command"):
                        self.active_db.execute_command(f"SELECT {db_index}")
                        self.active_db.execute_command("FLUSHDB")
                        self.refrescar_arbol()
                        self._recargar_todas_las_tablas_abiertas()

    def _eliminar_conexion_guardada(self, name: str):
        saved = self._cargar_conexiones_guardadas()
        conns_list = saved.get("saved_connections", [])
        saved["saved_connections"] = [c for c in conns_list if c.get("name") != name]
        last_c = saved.get("last_connection")
        if last_c and isinstance(last_c, dict) and last_c.get("name") == name:
            saved["last_connection"] = None
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(saved, f, indent=4)
        except Exception:
            pass
        self.refrescar_arbol()

    # ── Ejecución de Consultas sin MessageBox (Terminal Integrada) ────

    def ejecutar_sql_desde_editor(self, sql: str, editor_widget: Optional[SqlEditorWidget] = None):
        """
        Ejecuta SQL con soporte multi-sentencia secuencial (split por ';'),
        intercepción de USE DATABASE / USE TABLE y ejecución asíncrona sin bloqueos.
        """
        stripped_sql = sql.strip()
        if not stripped_sql:
            return

        statements = split_sql_statements(stripped_sql)
        if not statements:
            return

        if len(statements) == 1:
            # Sentencia única
            self._ejecutar_sentencia_sql(statements[0], editor_widget, is_multi=False)
        else:
            # Multi-sentencia: ejecutar secuencialmente
            if editor_widget:
                editor_widget.log_info(f"⚡ Iniciando ejecución de script ({len(statements)} sentencias)...")
                editor_widget.set_status(f"⏳ Ejecutando sentencia 1 de {len(statements)}...", is_error=False)

            for idx, stmt in enumerate(statements, 1):
                ok = self._ejecutar_sentencia_sql(stmt, editor_widget, is_multi=True, stmt_idx=idx, total_stmts=len(statements))
                if not ok:
                    if editor_widget:
                        editor_widget.log_error(stmt, f"Ejecución del script interrumpida en sentencia {idx}/{len(statements)} por error.")
                        editor_widget.set_status(f"❌ Error en sentencia {idx} de {len(statements)}.", is_error=True)
                    return

            if editor_widget:
                editor_widget.set_status(f"✅ Script completado con éxito ({len(statements)} sentencias).", is_error=False)

    def _ejecutar_sentencia_sql(self, stmt: str, editor_widget: Optional[SqlEditorWidget] = None,
                                is_multi: bool = False, stmt_idx: int = 1, total_stmts: int = 1) -> bool:
        """Ejecuta una sentencia individual analizando comandos especiales o SQL relacional/NoSQL"""
        clean_stmt = stmt.strip()
        if not clean_stmt:
            return True

        engine = getattr(self.active_db, "engine", "sqlite") if self.active_db else "sqlite"
        special_cmd = parse_special_command(clean_stmt)

        if special_cmd:
            cmd_type = special_cmd["type"]

            # ── A. USE TABLE <nombre> ──────────────────────────────
            if cmd_type == "USE_TABLE":
                tbl_name = special_cmd["target"]
                self.abrir_tabla_datos(tbl_name)
                if editor_widget:
                    editor_widget.log_query(clean_stmt, 0.5, 0, is_select=False)
                    editor_widget.set_status(f"✅ Enfocada tabla '{tbl_name}'.")
                if hasattr(self, "history_widget"):
                    self.history_widget.add_entry(clean_stmt, 0.5, success=True, rows=0)
                return True

            # ── B. USE DATABASE / USE AUTO ────────────────────────
            if cmd_type in ("USE_DATABASE", "USE_AUTO"):
                target = special_cmd["target"]
                # Si fue 'USE <nombre>' sin especificar DATABASE/TABLE, comprobar si es una tabla existente
                is_table = False
                if cmd_type == "USE_AUTO" and self.active_db and self.active_db.is_connected:
                    eng_type = getattr(self.active_db, "engine_type", "relational")
                    if eng_type == "relational":
                        tbl_names = [t.get("name", "").lower() for t in self.active_db.get_tables()]
                        if target.lower() in tbl_names:
                            is_table = True
                    elif eng_type == "document":
                        col_names = [c.get("name", "").lower() for c in self.active_db.get_collections()]
                        if target.lower() in col_names:
                            is_table = True

                if is_table:
                    if getattr(self.active_db, "engine_type", "relational") == "document":
                        self.abrir_coleccion_documentos(getattr(self.active_db, "database_name", ""), target)
                    else:
                        self.abrir_tabla_datos(target)
                    if editor_widget:
                        editor_widget.log_query(clean_stmt, 0.5, 0, is_select=False)
                        editor_widget.set_status(f"✅ Enfocada tabla/colección '{target}'.")
                    if hasattr(self, "history_widget"):
                        self.history_widget.add_entry(clean_stmt, 0.5, success=True, rows=0)
                    return True

                # ── Tratar como base de datos o cambio de conexión ─────────
                clean_target = target.strip()
                if (clean_target.startswith("`") and clean_target.endswith("`")) or \
                   (clean_target.startswith('"') and clean_target.endswith('"')) or \
                   (clean_target.startswith("'") and clean_target.endswith("'")) or \
                   (clean_target.startswith("[") and clean_target.endswith("]")):
                    clean_target = clean_target[1:-1].strip()

                target_lower = clean_target.lower()
                clean_target_no_ext = re.sub(r"\.(db|sqlite|sqlite3|json)$", "", clean_target, flags=re.IGNORECASE)
                target_no_ext_lower = clean_target_no_ext.lower()

                # 1. Prioridad: Buscar en Conexiones Guardadas (MongoDB, PostgreSQL, MySQL, SQLite, etc.)
                saved_config = self._cargar_conexiones_guardadas()
                saved_conns = saved_config.get("saved_connections", [])
                matched_conn = None

                for sc in saved_conns:
                    sc_name = sc.get("name", "").strip().lower()
                    sc_db = sc.get("database", "").strip().lower()
                    sc_path = sc.get("path", "")
                    sc_stem = Path(sc_path).stem.lower() if sc_path and sc_path != ":memory:" else ""
                    sc_file = Path(sc_path).name.lower() if sc_path and sc_path != ":memory:" else ""

                    if target_lower in (sc_name, sc_db, sc_stem, sc_file) or \
                       target_no_ext_lower in (sc_name, sc_db, sc_stem, sc_file):
                        matched_conn = sc
                        break

                if matched_conn:
                    ok = self.conectar_desde_config(matched_conn, show_dialog=False)
                    if ok and self.active_db and self.active_db.is_connected:
                        if editor_widget:
                            editor_widget.log_query(clean_stmt, 0.5, 0, is_select=False)
                            editor_widget.set_status(f"✅ Conectado a conexión guardada '{matched_conn.get('name', clean_target)}'.")
                        if hasattr(self, "history_widget"):
                            self.history_widget.add_entry(clean_stmt, 0.5, success=True, rows=0)
                        return True
                    else:
                        err_msg = getattr(self.active_db, "last_error", "Error al conectar con la base de datos remota/archivo.")
                        if editor_widget:
                            editor_widget.log_error(clean_stmt, f"No se pudo conectar a la conexión guardada '{matched_conn.get('name')}': {err_msg}")
                            editor_widget.set_status(f"❌ Error al conectar a '{matched_conn.get('name')}': {err_msg}", is_error=True)
                        return False

                # 2. Si estamos conectados a un servidor multi-base (MySQL, MongoDB, PostgreSQL, Redis), cambiar contexto
                if self.active_db and self.active_db.is_connected:
                    if engine == "mysql":
                        rows, cols, dur, aff, err = self.active_db.execute_query(f"USE `{clean_target}`;")
                        if err:
                            if editor_widget:
                                editor_widget.log_error(clean_stmt, err, dur)
                                editor_widget.set_status(f"❌ Error al usar base de datos: {err}", is_error=True)
                            return False
                        self.active_db.database = clean_target
                        self.active_db.name = f"MySQL: {clean_target}@{self.active_db.host}"
                        self._actualizar_estado_conexion()
                        self.refrescar_arbol()
                        if editor_widget:
                            editor_widget.log_query(clean_stmt, dur, 0, is_select=False)
                            editor_widget.set_status(f"✅ Conectado a base de datos MySQL '{clean_target}'.")
                        if hasattr(self, "history_widget"):
                            self.history_widget.add_entry(clean_stmt, dur, success=True, rows=0)
                        return True

                    elif engine == "mongodb":
                        self.active_db.database_name = clean_target
                        self.active_db.name = f"MongoDB: {clean_target}@{self.active_db.host}:{self.active_db.port}"
                        self._guardar_conexion_activa(self.active_db)
                        self._actualizar_estado_conexion()
                        self.refrescar_arbol()
                        if editor_widget:
                            editor_widget.log_query(clean_stmt, 0.5, 0, is_select=False)
                            editor_widget.set_status(f"✅ Conectado a base de datos MongoDB '{clean_target}'.")
                        if hasattr(self, "history_widget"):
                            self.history_widget.add_entry(clean_stmt, 0.5, success=True, rows=0)
                        return True

                    elif engine == "postgresql":
                        new_conn = PostgreSQLConnection(
                            host=self.active_db.host,
                            port=self.active_db.port,
                            database=clean_target,
                            user=self.active_db.user,
                            password=self.active_db.password,
                            name=f"PostgreSQL: {clean_target}@{self.active_db.host}"
                        )
                        if new_conn.connect():
                            self.active_db.close()
                            self.active_db = new_conn
                            self._guardar_conexion_activa(self.active_db)
                            self._actualizar_estado_conexion()
                            self.refrescar_arbol()
                            if editor_widget:
                                editor_widget.log_query(clean_stmt, 0.5, 0, is_select=False)
                                editor_widget.set_status(f"✅ Conectado a base de datos PostgreSQL '{clean_target}'.")
                            if hasattr(self, "history_widget"):
                                self.history_widget.add_entry(clean_stmt, 0.5, success=True, rows=0)
                            return True
                        else:
                            err_msg = new_conn.last_error
                            if editor_widget:
                                editor_widget.log_error(clean_stmt, f"No se pudo conectar a PostgreSQL '{clean_target}': {err_msg}")
                                editor_widget.set_status(f"❌ Error al conectar a PostgreSQL '{clean_target}'", is_error=True)
                            return False

                    elif engine == "redis":
                        idx_num = None
                        if clean_target.isdigit():
                            idx_num = int(clean_target)
                        elif clean_target.lower().startswith("db") and clean_target[2:].isdigit():
                            idx_num = int(clean_target[2:])
                        if idx_num is not None and hasattr(self.active_db, "execute_command"):
                            _, _, dur, _, err = self.active_db.execute_command(f"SELECT {idx_num}")
                            if not err:
                                self.active_db.db_index = idx_num
                                self.active_db.name = f"Redis: db{idx_num}@{self.active_db.host}:{self.active_db.port}"
                                self._guardar_conexion_activa(self.active_db)
                                self._actualizar_estado_conexion()
                                self.refrescar_arbol()
                                if editor_widget:
                                    editor_widget.log_query(clean_stmt, dur, 0, is_select=False)
                                    editor_widget.set_status(f"✅ Conectado a Redis db{idx_num}.")
                                return True

                # 3. Buscar archivo en el almacenamiento seguro local (databases/)
                clean_name = self._sanitizar_nombre_db(clean_target)
                target_path = None

                if self.databases_dir.exists():
                    p_estatica = self._ruta_db_estatica(clean_name)
                    if p_estatica and p_estatica.exists():
                        target_path = p_estatica
                    else:
                        try:
                            for cand in self.databases_dir.iterdir():
                                if not cand.is_file():
                                    continue
                                c_stem = cand.stem.lower()
                                c_name = cand.name.lower()
                                if target_lower in (c_stem, c_name) or \
                                   target_no_ext_lower in (c_stem, c_name) or \
                                   clean_name.lower() in (c_stem, c_name):
                                    target_path = cand
                                    break
                        except Exception:
                            pass

                if target_path and target_path.exists():
                    ok = self.conectar_base_datos(str(target_path))
                    if ok and self.active_db and self.active_db.is_connected:
                        if editor_widget:
                            editor_widget.log_query(clean_stmt, 0.5, 0, is_select=False)
                            editor_widget.set_status(f"✅ Conectado a base de datos estática '{target_path.name}'.")
                        if hasattr(self, "history_widget"):
                            self.history_widget.add_entry(clean_stmt, 0.5, success=True, rows=0)
                        return True
                    else:
                        err_msg = getattr(self.active_db, "last_error", "Error desconocido.")
                        if editor_widget:
                            editor_widget.log_error(clean_stmt, f"Error al conectar a '{target_path.name}': {err_msg}")
                            editor_widget.set_status(f"❌ Error al conectar a '{target_path.name}'", is_error=True)
                        return False

                # 4. No se encontró en ninguna parte
                if editor_widget:
                    editor_widget.log_error(
                        clean_stmt,
                        f"La base de datos o conexión '{clean_target}' no existe en conexiones guardadas ni en {self.databases_dir.name}/.\n"
                        f"💡 Para crear una nueva base SQLite local, ejecuta: CREATE DATABASE {clean_name}; o añade una conexión en '+ Nueva Conexión'."
                    )
                    editor_widget.set_status(f"❌ La base de datos o conexión '{clean_target}' no existe.", is_error=True)
                return False

            # ── C. CREATE DATABASE ─────────────────────────────────
            if cmd_type == "CREATE_DATABASE":
                name = special_cmd["name"]
                clean_name = self._sanitizar_nombre_db(name)
                if not clean_name:
                    if editor_widget:
                        editor_widget.log_error(clean_stmt, f"Nombre de base de datos no válido: '{name}'.")
                    return False
                target_path = self._ruta_db_estatica(clean_name)
                if not target_path:
                    if editor_widget:
                        editor_widget.log_error(clean_stmt, "Ruta no permitida por seguridad.")
                    return False
                if target_path.exists() and not special_cmd.get("if_not_exists"):
                    if editor_widget:
                        editor_widget.log_error(clean_stmt, f"La base de datos '{clean_name}.db' ya existe.")
                    return False

                try:
                    init_conn = DatabaseConnection(str(target_path), name=f"{clean_name}.db")
                    if init_conn.connect():
                        init_conn.execute_query("PRAGMA foreign_keys = ON;")
                        init_conn.close()
                    self.refrescar_arbol()
                    self._actualizar_selector_databases()
                    if editor_widget:
                        editor_widget.log_query(clean_stmt, 1.0, 0, is_select=False)
                        editor_widget.set_status(f"✅ Base de datos estática '{clean_name}.db' creada correctamente.")
                    if hasattr(self, "history_widget"):
                        self.history_widget.add_entry(clean_stmt, 1.0, success=True, rows=0)
                    return True
                except Exception as e:
                    if editor_widget:
                        editor_widget.log_error(clean_stmt, str(e), 1.0)
                    return False

            # ── D. DROP DATABASE ───────────────────────────────────
            if cmd_type == "DROP_DATABASE":
                name = special_cmd["name"]
                clean_name = self._sanitizar_nombre_db(name)
                target_path = self._ruta_db_estatica(clean_name)
                if not target_path or not target_path.exists():
                    if special_cmd.get("if_exists"):
                        if editor_widget:
                            editor_widget.log_query(clean_stmt, 0.5, 0, is_select=False, db_name=getattr(self.active_db, "name", ""))
                            editor_widget.set_status(f"⚠️ Base de datos '{name}' no existe (ignorado por IF EXISTS).")
                        return True
                    else:
                        if editor_widget:
                            editor_widget.log_error(clean_stmt, f"La base de datos '{name}' no existe.", db_name=getattr(self.active_db, "name", ""))
                        return False

                ok = self._eliminar_archivo_db_y_limpiar_conexiones(target_path, clean_name)
                if ok:
                    if editor_widget:
                        editor_widget.log_query(clean_stmt, 1.0, 0, is_select=False, db_name=getattr(self.active_db, "name", ""))
                        editor_widget.set_status(f"✅ Base de datos '{clean_name}' y sus conexiones eliminadas correctamente.")
                    if hasattr(self, "history_widget"):
                        self.history_widget.add_entry(clean_stmt, 1.0, success=True, rows=0)
                    return True
                else:
                    if editor_widget:
                        editor_widget.log_error(clean_stmt, f"Error al eliminar base de datos '{clean_name}'.", 1.0, db_name=getattr(self.active_db, "name", ""))
                    return False

            # ── E. SHOW DATABASES ──────────────────────────────────
            if cmd_type == "SHOW_DATABASES":
                rows = []
                cols = []
                # Si estamos conectados a un servidor multi-base (MySQL, MongoDB, PostgreSQL)
                if self.active_db and getattr(self.active_db, "engine", "sqlite") in ("mysql", "mongodb", "postgresql"):
                    try:
                        dbs = self.active_db.get_databases()
                        current_db = getattr(self.active_db, "database", "") or getattr(self.active_db, "database_name", "")
                        for db in dbs:
                            rows.append({
                                "Database": db,
                                "Motor": getattr(self.active_db, "engine", "").upper(),
                                "Activa": "✓" if db.lower() == str(current_db).lower() else ""
                            })
                        cols = ["Database", "Motor", "Activa"]
                    except Exception:
                        pass

                if not rows:
                    cols = ["Nombre", "Motor", "Ubicación / Destino", "Activa"]
                    curr_name = getattr(self.active_db, "name", "") if self.active_db else ""
                    curr_path = getattr(self.active_db, "db_path", "") or str(getattr(self.active_db, "file_path", "")) if self.active_db else ""

                    # Conexiones guardadas
                    saved = self._cargar_conexiones_guardadas()
                    for sc in saved.get("saved_connections", []):
                        sc_name = sc.get("name", "")
                        sc_eng = sc.get("engine", "sqlite").upper()
                        sc_loc = sc.get("path") or sc.get("uri") or f"{sc.get('database', '')}@{sc.get('host', '')}"
                        is_act = (curr_name == sc_name)
                        rows.append({
                            "Nombre": sc_name,
                            "Motor": sc_eng,
                            "Ubicación / Destino": str(sc_loc),
                            "Activa": "✓" if is_act else ""
                        })

                    # Bases de datos en databases/
                    for f in self._listar_archivos_dbs_estaticas():
                        is_act = False
                        try:
                            if curr_path and curr_path != ":memory:":
                                is_act = (Path(curr_path).resolve() == f.resolve())
                        except Exception:
                            pass
                        if not any(r["Nombre"] in (f.stem, f.name) for r in rows):
                            rows.append({
                                "Nombre": f.stem,
                                "Motor": "SQLITE" if f.suffix != ".json" else "LOCALDOC",
                                "Ubicación / Destino": f.name,
                                "Activa": "✓" if is_act else ""
                            })

                if editor_widget:
                    editor_widget.log_query(clean_stmt, 0.8, len(rows), is_select=True)
                    editor_widget.set_status(f"✅ {len(rows)} base(s) de datos / conexiones encontradas.")
                self._mostrar_resultados_query(cols, rows, 0.8)
                if hasattr(self, "history_widget"):
                    self.history_widget.add_entry(clean_stmt, 0.8, success=True, rows=len(rows))
                return True


            # ── F. SHOW TABLES ────────────────────────────────────
            if cmd_type == "SHOW_TABLES":
                if self.active_db and self.active_db.is_connected:
                    tables = self.active_db.get_tables()
                    rows = [{"Table": t.get("name"), "Type": t.get("type"), "Rows": t.get("row_count", 0)} for t in tables]
                    cols = ["Table", "Type", "Rows"]
                    if editor_widget:
                        editor_widget.log_query(clean_stmt, 0.5, len(rows), is_select=True)
                        editor_widget.set_status(f"✅ {len(rows)} tabla(s) encontradas.")
                    self._mostrar_resultados_query(cols, rows, 0.5)
                return True

        if not self.active_db or not self.active_db.is_connected:
            if editor_widget:
                editor_widget.log_error(clean_stmt, "No hay conexión activa a ninguna base de datos.")
                editor_widget.set_status("⚠️ No hay base de datos conectada.", is_error=True)
            return False

        if not hasattr(self.active_db, "execute_query"):
            err_msg = f"El motor '{getattr(self.active_db, 'engine', 'desconocido')}' no admite ejecución de consultas directas."
            if editor_widget:
                editor_widget.log_error(clean_stmt, err_msg)
                editor_widget.set_status(f"❌ {err_msg}", is_error=True)
            return False

        rows, columns, duration_ms, affected, err = self.active_db.execute_query(clean_stmt)
        if err:
            if editor_widget:
                editor_widget.log_error(clean_stmt, err, duration_ms)
                editor_widget.set_status(f"❌ Error: {err}", is_error=True)
            if hasattr(self, "history_widget"):
                self.history_widget.add_entry(clean_stmt, duration_ms, success=False, rows=0)
            return False

        db_tag = getattr(self.active_db, "name", "")
        if columns or (rows is not None and len(rows) > 0):
            cols = columns or (list(rows[0].keys()) if rows else [])
            self._mostrar_resultados_query(cols, rows, duration_ms)
            if editor_widget:
                editor_widget.log_query(clean_stmt, duration_ms, len(rows), is_select=True, db_name=db_tag)
                editor_widget.set_status(f"✅ {len(rows)} fila(s) obtenidas de [{db_tag}] ({duration_ms:.1f} ms).")
        else:
            # DDL / DML (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER)
            self.refrescar_arbol()
            self._recargar_todas_las_tablas_abiertas()
            if editor_widget:
                editor_widget.log_query(clean_stmt, duration_ms, affected, is_select=False, db_name=db_tag)
                editor_widget.set_status(f"✅ Ejecutado en [{db_tag}] ({affected} filas afectadas, {duration_ms:.1f} ms).")

        # Registrar en el historial de consultas persistente
        row_cnt = len(rows) if rows else affected
        if hasattr(self, "history_widget"):
            self.history_widget.add_entry(clean_stmt, duration_ms, success=True, rows=row_cnt)

        return True

    def _mostrar_resultados_query(self, columns: List[str], rows: List[Dict[str, Any]], duration_ms: float):
        """Muestra los resultados de una consulta SELECT en una pestaña de cuadrícula"""
        # Buscar pestaña de resultados existente
        res_grid = None
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, DataGridWidget) and widget.property("is_query_results"):
                res_grid = widget
                self.tabs.setCurrentIndex(idx)
                break

        if not res_grid:
            res_grid = DataGridWidget(self.colores)
            res_grid.setProperty("is_query_results", True)
            self._agregar_pestana(res_grid, "📋 Resultados")
            self.tabs.setCurrentWidget(res_grid)

        res_grid.load_data(columns, rows, "", "", duration_ms)

    def _recargar_todas_las_tablas_abiertas(self):
        """Refresca los datos de cualquier pestaña de tabla abierta tras una modificación"""
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, DataGridWidget) and widget.property("table_name"):
                tbl = widget.property("table_name")
                self._cargar_datos_en_grid(tbl, widget)
            elif isinstance(widget, ERDiagramWidget):
                widget.load_schema(self.active_db)
            elif isinstance(widget, DocumentViewerWidget):
                widget.cargar_datos()
            elif isinstance(widget, RedisExplorerWidget):
                widget.cargar_claves()

    def _on_cell_edited(self, table_name: str, pk_col: str, pk_val: any, col_name: str, new_val: any):
        if not self.active_db:
            return
        ok, msg = self.active_db.update_cell(table_name, pk_col, pk_val, col_name, new_val)
        current_ed = self._obtener_consola_activa()
        if current_ed:
            if ok:
                current_ed.log_info(f"Fila actualizada en '{table_name}': {col_name} = '{new_val}' (PK {pk_col}={pk_val})")
            else:
                current_ed.log_error(f"UPDATE {table_name}", msg)

    def _on_row_deleted(self, table_name: str, pk_col: str, pk_val: any):
        if not self.active_db:
            return
        confirm = QMessageBox.question(
            self, "Eliminar Fila",
            f"¿Deseas eliminar la fila donde {pk_col} = '{pk_val}' de la tabla '{table_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.active_db.delete_row(table_name, pk_col, pk_val)
        current_ed = self._obtener_consola_activa()
        if ok:
            if current_ed:
                current_ed.log_info(f"Fila eliminada de '{table_name}' ({pk_col}={pk_val})")
            self._recargar_todas_las_tablas_abiertas()
            self.refrescar_arbol()
        else:
            if current_ed:
                current_ed.log_error(f"DELETE FROM {table_name}", msg)

    def _obtener_consola_activa(self) -> Optional[SqlEditorWidget]:
        curr = self.tabs.currentWidget()
        if isinstance(curr, SqlEditorWidget):
            return curr
        for idx in range(self.tabs.count()):
            w = self.tabs.widget(idx)
            if isinstance(w, SqlEditorWidget):
                return w
        return None

    # ── Persistencia del Estado de Pestañas ─────────────────────────────

    def guardar_estado_pestanas(self):
        """Guarda el estado de todas las pestañas abiertas para persistencia entre sesiones"""
        try:
            tabs_data = []
            active_idx = self.tabs.currentIndex()
            for idx in range(self.tabs.count()):
                widget = self.tabs.widget(idx)
                tab_title = self.tabs.tabText(idx)
                if isinstance(widget, SqlEditorWidget):
                    tabs_data.append({
                        "type": "sql_editor",
                        "title": tab_title,
                        "sql": widget.get_sql()
                    })
                elif isinstance(widget, DataGridWidget):
                    if widget.property("is_query_results"):
                        continue
                    tbl = widget.property("table_name")
                    if tbl:
                        tabs_data.append({
                            "type": "table_data",
                            "title": tab_title,
                            "table_name": tbl
                        })
                elif isinstance(widget, ERDiagramWidget):
                    tabs_data.append({
                        "type": "er_diagram",
                        "title": tab_title
                    })
                elif isinstance(widget, SchemaDesignerWidget):
                    tabs_data.append({
                        "type": "schema_designer",
                        "title": tab_title
                    })
                elif isinstance(widget, QueryHistoryWidget):
                    tabs_data.append({
                        "type": "history",
                        "title": tab_title
                    })
                elif isinstance(widget, DocumentViewerWidget):
                    tabs_data.append({
                        "type": "document_viewer",
                        "title": tab_title,
                        "collection_name": widget.property("collection_name"),
                        "database_name": widget.property("database_name")
                    })
                elif isinstance(widget, RedisExplorerWidget):
                    tabs_data.append({
                        "type": "redis_viewer",
                        "title": tab_title,
                        "db_index": widget.property("db_index")
                    })

            state = {
                "active_index": active_idx,
                "sql_counter": self._sql_counter,
                "tabs": tabs_data
            }
            with open(self.tabs_state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[MultiTool DB] Error al guardar estado de pestañas: {e}")

    def _restaurar_estado_pestanas(self) -> bool:
        """Restaura las pestañas previas desde el archivo de estado persistente"""
        if not self.tabs_state_path.exists():
            return False
        try:
            with open(self.tabs_state_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            tabs_list = state.get("tabs", [])
            if not tabs_list:
                return False

            self._sql_counter = state.get("sql_counter", 0)

            self.tabs.blockSignals(True)
            for item in tabs_list:
                t_type = item.get("type")
                t_title = item.get("title", "")
                if t_type == "sql_editor":
                    ed = SqlEditorWidget(self.colores)
                    ed.query_executed.connect(lambda sql, w=ed: self.ejecutar_sql_desde_editor(sql, w))
                    ed.explain_requested.connect(lambda sql, w=ed: self.analizar_plan_sql(sql, w))
                    self._agregar_pestana(ed, t_title or "⚡ Consulta")
                    if item.get("sql"):
                        ed.set_sql(item.get("sql"))
                elif t_type == "table_data":
                    tbl = item.get("table_name")
                    if tbl:
                        grid = DataGridWidget(self.colores)
                        grid.setProperty("table_name", tbl)
                        grid.data_changed.connect(self._on_cell_edited)
                        grid.delete_row_requested.connect(self._on_row_deleted)
                        grid.refresh_requested.connect(lambda t=tbl, g=grid: self._cargar_datos_en_grid(t, g))
                        self._agregar_pestana(grid, t_title or f"📄 {tbl}")
                        self._cargar_datos_en_grid(tbl, grid)
                elif t_type == "er_diagram":
                    er = ERDiagramWidget(self.colores)
                    er.btn_refresh.clicked.connect(lambda w=er: w.load_schema(self.active_db))
                    self._agregar_pestana(er, t_title or "📊 Diagrama ER")
                    if self.active_db and self.active_db.is_connected:
                        er.load_schema(self.active_db)
                elif t_type == "schema_designer":
                    designer = SchemaDesignerWidget(self.colores)
                    designer.create_table_requested.connect(lambda sql: self.ejecutar_sql_desde_editor(sql))
                    self._agregar_pestana(designer, t_title or "📐 Diseñador DDL")
                elif t_type == "history":
                    self._agregar_pestana(self.history_widget, t_title or "📜 Historial SQL")
                    self.history_widget.load_history()
                elif t_type == "document_viewer":
                    col_n = item.get("collection_name")
                    db_n = item.get("database_name", "")
                    if col_n and self.active_db and self.active_db.is_connected:
                        self.abrir_coleccion_documentos(db_n, col_n)
                elif t_type == "redis_viewer":
                    db_idx = item.get("db_index", 0)
                    if self.active_db and self.active_db.is_connected:
                        self.abrir_explorador_redis(db_idx)

            self.tabs.blockSignals(False)

            active_idx = state.get("active_index", 0)
            if 0 <= active_idx < self.tabs.count():
                self.tabs.setCurrentIndex(active_idx)

            self._actualizar_autocompletado_en_consolas()
            return self.tabs.count() > 0
        except Exception as e:
            print(f"[MultiTool DB] Error restaurando pestañas: {e}")
            self.tabs.blockSignals(False)
            return False

    def hideEvent(self, event):
        super().hideEvent(event)
        self.guardar_estado_pestanas()

    def closeEvent(self, event):
        self.guardar_estado_pestanas()
        super().closeEvent(event)

