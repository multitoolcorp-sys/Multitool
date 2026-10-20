"""
connection_dialog.py - Asistente y diálogo de nueva conexión multibase estilo DBeaver
Soporta SQLite, PostgreSQL, MySQL, MongoDB, Redis y NoSQL Local con verificación y descarga autorizada de drivers.
"""
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QStackedWidget, QWidget, 
    QFileDialog, QMessageBox, QFrame, QApplication, QSpinBox,
    QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from .db_manager import (
    DriverManager, DatabaseConnection, PostgreSQLConnection, MySQLConnection,
    MongoDBConnection, RedisConnection, LocalDocumentConnection
)


class DriverInstallerThread(QThread):
    """Hilo secundario para instalar el driver pip sin congelar la interfaz de usuario"""
    finished = pyqtSignal(bool, str)

    def __init__(self, package_name: str):
        super().__init__()
        self.package_name = package_name

    def run(self):
        try:
            ok, msg = DriverManager.install_driver(self.package_name)
            self.finished.emit(ok, msg)
        except Exception as e:
            self.finished.emit(False, f"Excepción durante la instalación: {e}")


class NewConnectionDialog(QDialog):
    """Diálogo estilo DBeaver para configurar conexiones a SQL y NoSQL"""
    def __init__(self, colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.result_connection = None
        self.setWindowTitle("🔌 Nueva Conexión a Base de Datos (SQL & NoSQL)")
        self.setFixedSize(510, 560)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores.get('bg_principal', '#121218')};
                color: white;
            }}
            QLabel {{
                color: #CBD5E1;
                font-size: 11px;
            }}
            QLineEdit, QSpinBox {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
            QComboBox {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                selection-background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Título
        lbl_title = QLabel("Configuración de Conexión (Multibase)")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        layout.addWidget(lbl_title)

        # Selector de motor
        lbl_engine = QLabel("Tipo de Base de Datos / Motor:")
        layout.addWidget(lbl_engine)

        self.cb_engine = QComboBox()
        self.cb_engine.addItem("🗄️ SQLite (Archivo local o :memory:)", "sqlite")
        self.cb_engine.addItem("🐘 PostgreSQL (SQL Relacional)", "postgresql")
        self.cb_engine.addItem("🐬 MySQL / MariaDB (SQL Relacional)", "mysql")
        self.cb_engine.addItem("🍃 MongoDB (NoSQL Documentos)", "mongodb")
        self.cb_engine.addItem("🔴 Redis (NoSQL Clave-Valor)", "redis")
        self.cb_engine.addItem("📁 NoSQL Local (.json Documentos)", "localdoc")
        self.cb_engine.currentIndexChanged.connect(self._on_engine_changed)
        layout.addWidget(self.cb_engine)

        # Nombre de conexión
        lbl_name = QLabel("Nombre de la conexión (etiqueta personalizada):")
        layout.addWidget(lbl_name)
        self.txt_conn_name = QLineEdit()
        self.txt_conn_name.setPlaceholderText("ej: Mi Servidor Producción, Base de Datos Local")
        layout.addWidget(self.txt_conn_name)

        # Banner de estado del driver
        self.driver_banner = QFrame()
        self.driver_banner.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        d_lay = QHBoxLayout(self.driver_banner)
        d_lay.setContentsMargins(10, 8, 10, 8)
        self.lbl_driver_info = QLabel("Driver disponible.")
        self.lbl_driver_info.setStyleSheet("color: #34D399; font-size: 11px;")
        d_lay.addWidget(self.lbl_driver_info)
        d_lay.addStretch()

        self.btn_install_driver = QPushButton("⬇️ Descargar Driver")
        self.btn_install_driver.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install_driver.setFixedHeight(26)
        self.btn_install_driver.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 10px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        self.btn_install_driver.clicked.connect(self._autorizar_y_descargar_driver)
        self.btn_install_driver.hide()
        d_lay.addWidget(self.btn_install_driver)
        layout.addWidget(self.driver_banner)

        # Stack de formularios según el motor
        self.stack = QStackedWidget()

        # ── Página 0: SQLite ──────────────────────────────────────────
        page_sqlite = QWidget()
        lay_sq = QVBoxLayout(page_sqlite)
        lay_sq.setContentsMargins(0, 4, 0, 4)
        lay_sq.setSpacing(6)

        lay_sq.addWidget(QLabel("Ruta del archivo SQLite:"))
        path_box = QHBoxLayout()
        self.txt_sqlite_path = QLineEdit()
        self.txt_sqlite_path.setPlaceholderText("C:/ruta/a/mi_base_de_datos.db o :memory:")
        path_box.addWidget(self.txt_sqlite_path)

        btn_browse = QPushButton("Examinar...")
        btn_browse.setFixedHeight(28)
        btn_browse.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border-radius: 4px; padding: 0 8px;")
        btn_browse.clicked.connect(self._examinar_sqlite)
        path_box.addWidget(btn_browse)
        lay_sq.addLayout(path_box)
        lay_sq.addStretch()
        self.stack.addWidget(page_sqlite)

        # ── Página 1: PostgreSQL / MySQL ───────────────────────────────
        page_remote = QWidget()
        lay_rem = QVBoxLayout(page_remote)
        lay_rem.setContentsMargins(0, 4, 0, 4)
        lay_rem.setSpacing(6)

        h_hp = QHBoxLayout()
        v_h = QVBoxLayout()
        v_h.addWidget(QLabel("Servidor / Host:"))
        self.txt_host = QLineEdit("localhost")
        v_h.addWidget(self.txt_host)
        h_hp.addLayout(v_h, 3)

        v_p = QVBoxLayout()
        v_p.addWidget(QLabel("Puerto:"))
        self.txt_port = QLineEdit("5432")
        v_p.addWidget(self.txt_port)
        h_hp.addLayout(v_p, 1)
        lay_rem.addLayout(h_hp)

        lay_rem.addWidget(QLabel("Nombre de la Base de Datos:"))
        self.txt_db_name = QLineEdit("postgres")
        lay_rem.addWidget(self.txt_db_name)

        h_up = QHBoxLayout()
        v_u = QVBoxLayout()
        v_u.addWidget(QLabel("Usuario:"))
        self.txt_user = QLineEdit("postgres")
        v_u.addWidget(self.txt_user)
        h_up.addLayout(v_u)

        v_pw = QVBoxLayout()
        v_pw.addWidget(QLabel("Contraseña:"))
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        v_pw.addWidget(self.txt_password)
        h_up.addLayout(v_pw)
        lay_rem.addLayout(h_up)
        lay_rem.addStretch()
        self.stack.addWidget(page_remote)

        # ── Página 2: MongoDB (NoSQL) ──────────────────────────────────
        page_mongo = QWidget()
        lay_mg = QVBoxLayout(page_mongo)
        lay_mg.setContentsMargins(0, 4, 0, 4)
        lay_mg.setSpacing(6)

        lay_mg.addWidget(QLabel("Cadena de Conexión URI (opcional):"))
        self.txt_mongo_uri = QLineEdit()
        self.txt_mongo_uri.setPlaceholderText("mongodb://usuario:pass@localhost:27017/test?authSource=admin")
        lay_mg.addWidget(self.txt_mongo_uri)

        h_mhp = QHBoxLayout()
        v_mh = QVBoxLayout()
        v_mh.addWidget(QLabel("Servidor / Host:"))
        self.txt_mongo_host = QLineEdit("localhost")
        v_mh.addWidget(self.txt_mongo_host)
        h_mhp.addLayout(v_mh, 3)

        v_mp = QVBoxLayout()
        v_mp.addWidget(QLabel("Puerto:"))
        self.txt_mongo_port = QLineEdit("27017")
        v_mp.addWidget(self.txt_mongo_port)
        h_mhp.addLayout(v_mp, 1)
        lay_mg.addLayout(h_mhp)

        h_mdb = QHBoxLayout()
        v_mdb = QVBoxLayout()
        v_mdb.addWidget(QLabel("Base de Datos:"))
        self.txt_mongo_db = QLineEdit("test")
        v_mdb.addWidget(self.txt_mongo_db)
        h_mdb.addLayout(v_mdb)

        v_mauth = QVBoxLayout()
        v_mauth.addWidget(QLabel("Auth Source:"))
        self.txt_mongo_auth = QLineEdit("admin")
        v_mauth.addWidget(self.txt_mongo_auth)
        h_mdb.addLayout(v_mauth)
        lay_mg.addLayout(h_mdb)

        h_mup = QHBoxLayout()
        v_mu = QVBoxLayout()
        v_mu.addWidget(QLabel("Usuario:"))
        self.txt_mongo_user = QLineEdit()
        v_mu.addWidget(self.txt_mongo_user)
        h_mup.addLayout(v_mu)

        v_mpw = QVBoxLayout()
        v_mpw.addWidget(QLabel("Contraseña:"))
        self.txt_mongo_pass = QLineEdit()
        self.txt_mongo_pass.setEchoMode(QLineEdit.EchoMode.Password)
        v_mpw.addWidget(self.txt_mongo_pass)
        h_mup.addLayout(v_mpw)
        lay_mg.addLayout(h_mup)
        lay_mg.addStretch()
        self.stack.addWidget(page_mongo)

        # ── Página 3: Redis (NoSQL) ────────────────────────────────────
        page_redis = QWidget()
        lay_rd = QVBoxLayout(page_redis)
        lay_rd.setContentsMargins(0, 4, 0, 4)
        lay_rd.setSpacing(6)

        h_rhp = QHBoxLayout()
        v_rh = QVBoxLayout()
        v_rh.addWidget(QLabel("Servidor / Host:"))
        self.txt_redis_host = QLineEdit("localhost")
        v_rh.addWidget(self.txt_redis_host)
        h_rhp.addLayout(v_rh, 3)

        v_rp = QVBoxLayout()
        v_rp.addWidget(QLabel("Puerto:"))
        self.txt_redis_port = QLineEdit("6379")
        v_rp.addWidget(self.txt_redis_port)
        h_rhp.addLayout(v_rp, 1)
        lay_rd.addLayout(h_rhp)

        h_rdb = QHBoxLayout()
        v_rdb = QVBoxLayout()
        v_rdb.addWidget(QLabel("Índice de Base de Datos (db0 a db15):"))
        self.sp_redis_db = QSpinBox()
        self.sp_redis_db.setRange(0, 15)
        self.sp_redis_db.setValue(0)
        v_rdb.addWidget(self.sp_redis_db)
        h_rdb.addLayout(v_rdb)

        v_rpw = QVBoxLayout()
        v_rpw.addWidget(QLabel("Contraseña (opcional):"))
        self.txt_redis_pass = QLineEdit()
        self.txt_redis_pass.setEchoMode(QLineEdit.EchoMode.Password)
        v_rpw.addWidget(self.txt_redis_pass)
        h_rdb.addLayout(v_rpw)
        lay_rd.addLayout(h_rdb)
        lay_rd.addStretch()
        self.stack.addWidget(page_redis)

        # ── Página 4: NoSQL Local (JSON) ───────────────────────────────
        page_localdoc = QWidget()
        lay_ld = QVBoxLayout(page_localdoc)
        lay_ld.setContentsMargins(0, 4, 0, 4)
        lay_ld.setSpacing(6)

        lay_ld.addWidget(QLabel("Ruta del archivo NoSQL (.nosql.json):"))
        path_ld_box = QHBoxLayout()
        self.txt_localdoc_path = QLineEdit()
        self.txt_localdoc_path.setPlaceholderText("C:/ruta/a/mi_coleccion.nosql.json")
        path_ld_box.addWidget(self.txt_localdoc_path)

        btn_browse_ld = QPushButton("Examinar...")
        btn_browse_ld.setFixedHeight(28)
        btn_browse_ld.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border-radius: 4px; padding: 0 8px;")
        btn_browse_ld.clicked.connect(self._examinar_localdoc)
        path_ld_box.addWidget(btn_browse_ld)
        lay_ld.addLayout(path_ld_box)

        lbl_ld_info = QLabel("ℹ️ Almacén de documentos NoSQL local autónomo. No requiere servidor externo ni internet.")
        lbl_ld_info.setStyleSheet("color: #94A3B8; font-size: 10px;")
        lbl_ld_info.setWordWrap(True)
        lay_ld.addWidget(lbl_ld_info)
        lay_ld.addStretch()
        self.stack.addWidget(page_localdoc)

        layout.addWidget(self.stack)

        # Mensaje de estado de prueba
        self.lbl_test_result = QLabel("")
        self.lbl_test_result.setWordWrap(True)
        layout.addWidget(self.lbl_test_result)

        # Botones inferiores
        bot_bar = QHBoxLayout()
        self.btn_test = QPushButton("🧪 Probar Conexión")
        self.btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test.setFixedHeight(32)
        self.btn_test.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 14px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.btn_test.clicked.connect(self._probar_conexion)
        bot_bar.addWidget(self.btn_test)

        bot_bar.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedHeight(32)
        btn_cancel.setStyleSheet("background: transparent; color: #AAB0B8; border: none; padding: 0 10px;")
        btn_cancel.clicked.connect(self.reject)
        bot_bar.addWidget(btn_cancel)

        self.btn_connect = QPushButton("Guardar y Conectar")
        self.btn_connect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect.setFixedHeight(32)
        self.btn_connect.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 18px;
                border: none;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        self.btn_connect.clicked.connect(self._guardar_y_conectar)
        bot_bar.addWidget(self.btn_connect)

        layout.addLayout(bot_bar)

        self._on_engine_changed(0)

    def _on_engine_changed(self, idx: int):
        engine = self.cb_engine.currentData()
        self.lbl_test_result.setText("")

        if engine == "sqlite":
            self.stack.setCurrentIndex(0)
            self.lbl_driver_info.setText("🟢 Driver SQLite nativo integrado en Python.")
            self.lbl_driver_info.setStyleSheet("color: #34D399; font-size: 11px;")
            self.btn_install_driver.hide()
        elif engine in ("postgresql", "mysql"):
            self.stack.setCurrentIndex(1)
            if engine == "postgresql":
                self.txt_port.setText("5432")
                self.txt_db_name.setText("postgres")
                self.txt_user.setText("postgres")
            elif engine == "mysql":
                self.txt_port.setText("3306")
                self.txt_db_name.setText("")
                self.txt_user.setText("root")

            installed, pkg = DriverManager.is_installed(engine)
            self._actualizar_banner_driver(engine, installed, pkg)
        elif engine == "mongodb":
            self.stack.setCurrentIndex(2)
            installed, pkg = DriverManager.is_installed(engine)
            self._actualizar_banner_driver(engine, installed, pkg)
        elif engine == "redis":
            self.stack.setCurrentIndex(3)
            installed, pkg = DriverManager.is_installed(engine)
            self._actualizar_banner_driver(engine, installed, pkg)
        elif engine == "localdoc":
            self.stack.setCurrentIndex(4)
            self.lbl_driver_info.setText("🟢 Motor NoSQL Local integrado (cero dependencias).")
            self.lbl_driver_info.setStyleSheet("color: #34D399; font-size: 11px;")
            self.btn_install_driver.hide()

    def _actualizar_banner_driver(self, engine: str, installed: bool, pkg: Optional[str]):
        if installed:
            self.lbl_driver_info.setText(f"🟢 Driver para {engine.capitalize()} disponible.")
            self.lbl_driver_info.setStyleSheet("color: #34D399; font-size: 11px;")
            self.btn_install_driver.hide()
        else:
            self.lbl_driver_info.setText(f"⚠️ Falta el driver oficial '{pkg}' para {engine.capitalize()}.")
            self.lbl_driver_info.setStyleSheet("color: #FBBF24; font-size: 11px;")
            self.btn_install_driver.show()

    def _examinar_sqlite(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Base de Datos SQLite", "",
            "Bases de Datos SQLite (*.db *.sqlite *.sqlite3 *.db3);;Todos los archivos (*.*)"
        )
        if path:
            self.txt_sqlite_path.setText(path)
            if not self.txt_conn_name.text().strip():
                self.txt_conn_name.setText(os.path.basename(path))

    def _examinar_localdoc(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Seleccionar o Crear Almacén NoSQL Local", "",
            "Almacenes NoSQL (*.nosql.json *.json);;Todos los archivos (*.*)"
        )
        if path:
            self.txt_localdoc_path.setText(path)
            if not self.txt_conn_name.text().strip():
                self.txt_conn_name.setText(os.path.basename(path))

    def _autorizar_y_descargar_driver(self):
        engine = self.cb_engine.currentData()
        installed, pkg = DriverManager.is_installed(engine)
        if installed:
            return

        resp = QMessageBox.question(
            self,
            "📥 Autorización de Descarga de Driver",
            f"El gestor de bases de datos requiere el driver oficial '{pkg}' para conectar con {engine.capitalize()}.\n\n"
            f"¿Autorizas a MultiTool a descargar e instalar automáticamente este driver mediante pip?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        self.btn_install_driver.setEnabled(False)
        self.btn_install_driver.setText("⏳ Instalando...")
        self.lbl_driver_info.setText(f"Instalando {pkg} mediante pip... por favor espera.")
        self.lbl_driver_info.setStyleSheet("color: #60A5FA; font-size: 11px;")
        QApplication.processEvents()

        self.thread = DriverInstallerThread(pkg)
        self.thread.finished.connect(self._on_driver_installed)
        self.thread.start()

    def _on_driver_installed(self, success: bool, msg: str):
        self.btn_install_driver.setEnabled(True)
        self.btn_install_driver.setText("⬇️ Descargar Driver")
        if success:
            QMessageBox.information(self, "Driver Instalado", f"El driver se instaló con éxito:\n\n{msg}")
            self._on_engine_changed(self.cb_engine.currentIndex())
        else:
            QMessageBox.critical(self, "Error de Instalación", f"No se pudo instalar el driver:\n\n{msg}")
            self.lbl_driver_info.setText(f"❌ Error al instalar driver: {msg}")
            self.lbl_driver_info.setStyleSheet("color: #F87171; font-size: 11px;")

    def _construir_objeto_conexion(self):
        engine = self.cb_engine.currentData()
        name = self.txt_conn_name.text().strip()

        if engine == "sqlite":
            path = self.txt_sqlite_path.text().strip() or ":memory:"
            return DatabaseConnection(path, name=name)
        elif engine == "postgresql":
            return PostgreSQLConnection(
                host=self.txt_host.text().strip() or "localhost",
                port=int(self.txt_port.text().strip() or 5432),
                database=self.txt_db_name.text().strip() or "postgres",
                user=self.txt_user.text().strip() or "postgres",
                password=self.txt_password.text(),
                name=name
            )
        elif engine == "mysql":
            return MySQLConnection(
                host=self.txt_host.text().strip() or "localhost",
                port=int(self.txt_port.text().strip() or 3306),
                database=self.txt_db_name.text().strip(),
                user=self.txt_user.text().strip() or "root",
                password=self.txt_password.text(),
                name=name
            )
        elif engine == "mongodb":
            return MongoDBConnection(
                uri=self.txt_mongo_uri.text().strip(),
                host=self.txt_mongo_host.text().strip() or "localhost",
                port=int(self.txt_mongo_port.text().strip() or 27017),
                database=self.txt_mongo_db.text().strip() or "test",
                user=self.txt_mongo_user.text().strip(),
                password=self.txt_mongo_pass.text(),
                auth_source=self.txt_mongo_auth.text().strip() or "admin",
                name=name
            )
        elif engine == "redis":
            return RedisConnection(
                host=self.txt_redis_host.text().strip() or "localhost",
                port=int(self.txt_redis_port.text().strip() or 6379),
                db_index=self.sp_redis_db.value(),
                password=self.txt_redis_pass.text(),
                name=name
            )
        elif engine == "localdoc":
            path = self.txt_localdoc_path.text().strip()
            if not path:
                path = "databases/local_store.nosql.json"
            return LocalDocumentConnection(path, name=name)
        return None

    def _probar_conexion(self):
        engine = self.cb_engine.currentData()
        installed, pkg = DriverManager.is_installed(engine)
        if not installed:
            self._autorizar_y_descargar_driver()
            return

        conn = self._construir_objeto_conexion()
        if not conn:
            return

        self.btn_test.setEnabled(False)
        self.btn_test.setText("Conectando...")
        QApplication.processEvents()

        ok = conn.connect()
        self.btn_test.setEnabled(True)
        self.btn_test.setText("🧪 Probar Conexión")

        if ok:
            self.lbl_test_result.setText("✅ ¡Conexión exitosa al servidor de base de datos!")
            self.lbl_test_result.setStyleSheet("color: #34D399; font-weight: bold; font-size: 11px;")
            conn.close()
        else:
            self.lbl_test_result.setText(f"❌ Falló la conexión: {conn.last_error}")
            self.lbl_test_result.setStyleSheet("color: #F87171; font-size: 11px;")

    def _guardar_y_conectar(self):
        engine = self.cb_engine.currentData()
        installed, pkg = DriverManager.is_installed(engine)
        if not installed:
            self._autorizar_y_descargar_driver()
            return

        conn = self._construir_objeto_conexion()
        if not conn:
            return

        if not conn.connect():
            QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a la base de datos:\n\n{conn.last_error}")
            return

        self.result_connection = conn
        self.accept()
