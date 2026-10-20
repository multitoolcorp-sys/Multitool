"""
redis_viewer.py - Explorador visual y consola interactiva para bases de datos NoSQL Redis
Permite explorar claves con SCAN, editar valores según su estructura de datos y ejecutar comandos CLI nativos.
"""
import json
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QTableWidget, QTableWidgetItem, QSplitter,
    QPlainTextEdit, QMessageBox, QHeaderView, QMenu, QApplication,
    QFrame, QComboBox, QDialog, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class NewRedisKeyDialog(QDialog):
    """Diálogo modal para crear una nueva clave en Redis con su tipo y valor inicial"""
    def __init__(self, colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.result_data = None
        self.setWindowTitle("➕ Nueva Clave Redis")
        self.setFixedSize(440, 360)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores.get('bg_principal', '#121218')};
                color: white;
            }}
            QLabel {{
                color: #CBD5E1;
                font-size: 11px;
            }}
            QLineEdit, QComboBox, QSpinBox {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
            QPlainTextEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                font-family: Consolas;
                font-size: 11px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Nombre de la clave (Key):"))
        self.txt_key = QLineEdit()
        self.txt_key.setPlaceholderText("ej: usuario:1001:perfil, sesion:activo")
        layout.addWidget(self.txt_key)

        h_tb = QHBoxLayout()
        v_t = QVBoxLayout()
        v_t.addWidget(QLabel("Tipo de dato:"))
        self.cb_type = QComboBox()
        self.cb_type.addItems(["String", "Hash (JSON)", "List", "Set"])
        v_t.addWidget(self.cb_type)
        h_tb.addLayout(v_t, 2)

        v_ttl = QVBoxLayout()
        v_ttl.addWidget(QLabel("TTL (segundos, -1 = persistente):"))
        self.sp_ttl = QSpinBox()
        self.sp_ttl.setRange(-1, 86400000)
        self.sp_ttl.setValue(-1)
        v_ttl.addWidget(self.sp_ttl)
        h_tb.addLayout(v_ttl, 1)
        layout.addLayout(h_tb)

        layout.addWidget(QLabel("Valor inicial:"))
        self.txt_val = QPlainTextEdit()
        self.txt_val.setPlaceholderText("Ingresa el valor de la clave...")
        layout.addWidget(self.txt_val)

        bot = QHBoxLayout()
        bot.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("background: transparent; color: #AAB0B8; border: none; padding: 0 10px;")
        btn_cancel.clicked.connect(self.reject)
        bot.addWidget(btn_cancel)

        btn_save = QPushButton("Crear Clave")
        btn_save.setFixedHeight(30)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 16px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        btn_save.clicked.connect(self._guardar)
        bot.addWidget(btn_save)

        layout.addLayout(bot)

    def _guardar(self):
        k = self.txt_key.text().strip()
        if not k:
            QMessageBox.warning(self, "Campo Requerido", "Debes ingresar un nombre para la clave.")
            return
        t = self.cb_type.currentText().split()[0].lower()
        v_raw = self.txt_val.toPlainText()
        ttl = self.sp_ttl.value()

        val = v_raw
        if t == "hash":
            try:
                val = json.loads(v_raw) if v_raw.strip() else {}
                if not isinstance(val, dict):
                    val = {"valor": v_raw}
            except Exception:
                val = {"valor": v_raw}
        elif t in ("list", "set"):
            val = [line.strip() for line in v_raw.splitlines() if line.strip()]

        self.result_data = (k, t, val, ttl)
        self.accept()


class RedisExplorerWidget(QWidget):
    """Explorador completo de claves y consola interactiva de comandos para Redis"""
    data_changed = pyqtSignal()

    def __init__(self, colores: dict, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.active_db = None
        self.db_index = 0
        self.current_keys: List[Dict[str, Any]] = []
        self.selected_key = ""
        self.selected_type = ""
        self.history_cmd = []
        self.history_idx = -1

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ── Barra Superior de Base de Datos Redis ─────────────────────
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.lbl_title = QLabel("🔴 Redis Explorer [db0]")
        self.lbl_title.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        top_bar.addWidget(self.lbl_title)

        top_bar.addSpacing(10)
        top_bar.addWidget(QLabel("Keyspace:"))
        self.cb_db = QComboBox()
        self.cb_db.addItems([f"db{i}" for i in range(16)])
        self.cb_db.setFixedHeight(28)
        self.cb_db.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 8px;
                font-size: 11px;
                font-weight: bold;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                selection-background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.cb_db.currentIndexChanged.connect(self._on_keyspace_changed)
        top_bar.addWidget(self.cb_db)

        self.lbl_keys_count = QLabel("(0 claves encontradas)")
        self.lbl_keys_count.setStyleSheet("color: #94A3B8; font-size: 11px;")
        top_bar.addWidget(self.lbl_keys_count)

        top_bar.addStretch()

        self.btn_flush = QPushButton("🧹 Vaciar DB (FLUSHDB)")
        self.btn_flush.setFixedHeight(28)
        self.btn_flush.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #F87171;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(248, 113, 113, 0.2);
                border-color: #F87171;
            }}
        """)
        self.btn_flush.clicked.connect(self._flush_db)
        top_bar.addWidget(self.btn_flush)

        layout.addLayout(top_bar)

        # ── Splitter Horizontal: Izquierda (Claves) / Derecha (Editor + Consola)
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                width: 3px;
            }}
        """)

        # ── Panel Izquierdo: Lista de Claves y Filtro ─────────────────
        left_panel = QWidget()
        l_lay = QVBoxLayout(left_panel)
        l_lay.setContentsMargins(0, 0, 0, 0)
        l_lay.setSpacing(6)

        search_box = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Filtrar claves (ej: * o usuario:*)")
        self.txt_search.setText("*")
        self.txt_search.setFixedHeight(28)
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 0 8px;
                font-family: Consolas;
                font-size: 11px;
            }}
        """)
        self.txt_search.returnPressed.connect(self.cargar_claves)
        search_box.addWidget(self.txt_search)

        btn_find = QPushButton("🔍")
        btn_find.setFixedSize(28, 28)
        btn_find.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border: none; border-radius: 6px;")
        btn_find.clicked.connect(self.cargar_claves)
        search_box.addWidget(btn_find)
        l_lay.addLayout(search_box)

        self.table_keys = QTableWidget()
        self.table_keys.setColumnCount(3)
        self.table_keys.setHorizontalHeaderLabels(["Clave (Key)", "Tipo", "TTL (s)"])
        self.table_keys.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_keys.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_keys.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_keys.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_keys.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_keys.itemSelectionChanged.connect(self._on_key_selected)
        self.table_keys.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #F8FAFC;
                gridline-color: rgba(255,255,255,0.06);
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
                font-size: 11px;
            }}
            QTableWidget::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #CBD5E1;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 6px;
                border: none;
            }}
        """)
        l_lay.addWidget(self.table_keys)

        l_actions = QHBoxLayout()
        btn_add = QPushButton("➕ Clave")
        btn_add.setFixedHeight(28)
        btn_add.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: #34D399; font-weight: bold; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')}; border-radius: 6px; font-size: 11px;")
        btn_add.clicked.connect(self._nueva_clave)
        l_actions.addWidget(btn_add)

        btn_del = QPushButton("🗑️ Borrar")
        btn_del.setFixedHeight(28)
        btn_del.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: #F87171; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')}; border-radius: 6px; font-size: 11px;")
        btn_del.clicked.connect(self._eliminar_clave)
        l_actions.addWidget(btn_del)

        btn_ref = QPushButton("🔄")
        btn_ref.setFixedSize(28, 28)
        btn_ref.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')}; border-radius: 6px;")
        btn_ref.clicked.connect(self.cargar_claves)
        l_actions.addWidget(btn_ref)
        l_lay.addLayout(l_actions)

        h_splitter.addWidget(left_panel)

        # ── Panel Derecho: Inspector de Valor y Consola CLI ───────────
        right_panel = QWidget()
        r_lay = QVBoxLayout(right_panel)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(6)

        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                height: 3px;
            }}
        """)

        # 1. Editor de Valor
        val_box = QWidget()
        v_val_lay = QVBoxLayout(val_box)
        v_val_lay.setContentsMargins(0, 0, 0, 0)
        v_val_lay.setSpacing(6)

        val_head = QHBoxLayout()
        self.lbl_selected_info = QLabel("Selecciona una clave para inspeccionar su valor")
        self.lbl_selected_info.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        val_head.addWidget(self.lbl_selected_info)

        val_head.addStretch()

        self.btn_save_val = QPushButton("💾 Guardar Valor")
        self.btn_save_val.setEnabled(False)
        self.btn_save_val.setFixedHeight(26)
        self.btn_save_val.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 0 12px;
                font-size: 11px;
                border: none;
            }}
            QPushButton:disabled {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #64748B;
            }}
        """)
        self.btn_save_val.clicked.connect(self._guardar_valor_editado)
        val_head.addWidget(self.btn_save_val)
        v_val_lay.addLayout(val_head)

        # Subpanel de TTL
        ttl_box = QHBoxLayout()
        ttl_box.addWidget(QLabel("TTL (segundos):"))
        self.sp_edit_ttl = QSpinBox()
        self.sp_edit_ttl.setRange(-1, 86400000)
        self.sp_edit_ttl.setValue(-1)
        self.sp_edit_ttl.setFixedHeight(24)
        ttl_box.addWidget(self.sp_edit_ttl)

        btn_apply_ttl = QPushButton("Aplicar TTL")
        btn_apply_ttl.setFixedHeight(24)
        btn_apply_ttl.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border-radius: 4px; padding: 0 8px; font-size: 10px;")
        btn_apply_ttl.clicked.connect(self._aplicar_ttl)
        ttl_box.addWidget(btn_apply_ttl)
        ttl_box.addStretch()
        v_val_lay.addLayout(ttl_box)

        self.txt_editor_val = QPlainTextEdit()
        self.txt_editor_val.setPlaceholderText("El contenido de la clave se mostrará aquí...")
        self.txt_editor_val.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #F8FAFC;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 6px;
                font-family: Consolas;
                font-size: 11px;
            }}
        """)
        v_val_lay.addWidget(self.txt_editor_val)
        v_splitter.addWidget(val_box)

        # 2. Terminal CLI Redis
        cli_box = QWidget()
        v_cli_lay = QVBoxLayout(cli_box)
        v_cli_lay.setContentsMargins(0, 0, 0, 0)
        v_cli_lay.setSpacing(6)

        cli_head = QHBoxLayout()
        lbl_cli = QLabel("⚡ Consola CLI Redis (Comandos nativos)")
        lbl_cli.setStyleSheet("color: #CBD5E1; font-weight: bold; font-size: 11px;")
        cli_head.addWidget(lbl_cli)

        cli_head.addStretch()

        for q_cmd in ["INFO", "DBSIZE", "PING", "KEYS *"]:
            btn_q = QPushButton(q_cmd)
            btn_q.setFixedHeight(22)
            btn_q.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: #94A3B8; border-radius: 3px; font-size: 9px; padding: 0 6px;")
            btn_q.clicked.connect(lambda _, c=q_cmd: self._ejecutar_comando_cli(c))
            cli_head.addWidget(btn_q)

        v_cli_lay.addLayout(cli_head)

        self.txt_cli_out = QPlainTextEdit()
        self.txt_cli_out.setReadOnly(True)
        self.txt_cli_out.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: #0D0D12;
                color: #34D399;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 6px;
                font-family: Consolas;
                font-size: 10px;
            }}
        """)
        v_cli_lay.addWidget(self.txt_cli_out)

        cli_input_lay = QHBoxLayout()
        lbl_prompt = QLabel("redis>")
        lbl_prompt.setStyleSheet("color: #F87171; font-family: Consolas; font-weight: bold;")
        cli_input_lay.addWidget(lbl_prompt)

        self.txt_cli_in = QLineEdit()
        self.txt_cli_in.setPlaceholderText("Escribe un comando de Redis (ej: GET mi_clave, HGETALL usuario:1)...")
        self.txt_cli_in.setFixedHeight(28)
        self.txt_cli_in.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 4px;
                padding: 0 8px;
                font-family: Consolas;
                font-size: 11px;
            }}
        """)
        self.txt_cli_in.returnPressed.connect(lambda: self._ejecutar_comando_cli())
        cli_input_lay.addWidget(self.txt_cli_in)

        btn_run_cmd = QPushButton("Enviar")
        btn_run_cmd.setFixedHeight(28)
        btn_run_cmd.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border: none; border-radius: 4px; padding: 0 12px; font-size: 11px;")
        btn_run_cmd.clicked.connect(lambda: self._ejecutar_comando_cli())
        cli_input_lay.addWidget(btn_run_cmd)

        v_cli_lay.addLayout(cli_input_lay)
        v_splitter.addWidget(cli_box)

        v_splitter.setSizes([260, 200])
        r_lay.addWidget(v_splitter)

        h_splitter.addWidget(right_panel)
        h_splitter.setSizes([340, 560])

        layout.addWidget(h_splitter)

    def set_connection(self, db_conn, db_index: int = 0):
        self.active_db = db_conn
        self.db_index = db_index
        self.cb_db.blockSignals(True)
        self.cb_db.setCurrentIndex(db_index)
        self.cb_db.blockSignals(False)
        self.lbl_title.setText(f"🔴 Redis Explorer [db{db_index}]")
        self.cargar_claves()

    def _on_keyspace_changed(self, idx: int):
        self.db_index = idx
        if self.active_db:
            self.active_db.select_db(idx)
        self.lbl_title.setText(f"🔴 Redis Explorer [db{idx}]")
        self.cargar_claves()

    def cargar_claves(self):
        if not self.active_db:
            return
        pattern = self.txt_search.text().strip() or "*"
        keys_info, duration_ms, err = self.active_db.scan_keys(pattern=pattern, limit=250)
        if err:
            self.txt_cli_out.appendPlainText(f"[ERROR SCAN] {err}")
            return

        self.current_keys = keys_info
        self.lbl_keys_count.setText(f"({len(keys_info)} claves en db{self.db_index}) - {duration_ms} ms")

        self.table_keys.setRowCount(len(keys_info))
        for row_idx, k_item in enumerate(keys_info):
            k_name = k_item["key"]
            k_type = k_item["type"]
            k_ttl = k_item["ttl"]

            it_name = QTableWidgetItem(k_name)
            it_name.setForeground(QColor("#F8FAFC"))

            it_type = QTableWidgetItem(k_type)
            color_map = {
                "STRING": "#34D399", "HASH": "#60A5FA", "LIST": "#F59E0B",
                "SET": "#A855F7", "ZSET": "#EC4899"
            }
            it_type.setForeground(QColor(color_map.get(k_type, "#94A3B8")))

            ttl_str = "Persistente" if k_ttl == -1 else (f"{k_ttl}s" if k_ttl >= 0 else "Expirado")
            it_ttl = QTableWidgetItem(ttl_str)
            it_ttl.setForeground(QColor("#64748B" if k_ttl == -1 else "#FBBF24"))

            self.table_keys.setItem(row_idx, 0, it_name)
            self.table_keys.setItem(row_idx, 1, it_type)
            self.table_keys.setItem(row_idx, 2, it_ttl)

    def _on_key_selected(self):
        selected_rows = self.table_keys.selectedItems()
        if not selected_rows:
            return
        row = self.table_keys.currentRow()
        if 0 <= row < len(self.current_keys):
            k_item = self.current_keys[row]
            self.selected_key = k_item["key"]
            self._cargar_detalle_clave(self.selected_key)

    def _cargar_detalle_clave(self, key: str):
        if not self.active_db:
            return
        val, k_type, ttl, err = self.active_db.get_key_value(key)
        if err:
            self.lbl_selected_info.setText(f"❌ Error: {err}")
            return

        self.selected_type = k_type
        self.lbl_selected_info.setText(f"🔑 {key}  [{k_type}]")
        self.sp_edit_ttl.setValue(ttl)
        self.btn_save_val.setEnabled(True)

        # Formatear el valor
        if isinstance(val, (dict, list)):
            try:
                self.txt_editor_val.setPlainText(json.dumps(val, indent=2, ensure_ascii=False))
            except Exception:
                self.txt_editor_val.setPlainText(str(val))
        elif val is None:
            self.txt_editor_val.setPlainText("(null)")
        else:
            # Si el string es un JSON válido, formatearlo legible
            raw_str = str(val)
            try:
                parsed = json.loads(raw_str)
                self.txt_editor_val.setPlainText(json.dumps(parsed, indent=2, ensure_ascii=False))
            except Exception:
                self.txt_editor_val.setPlainText(raw_str)

    def _guardar_valor_editado(self):
        if not self.active_db or not self.selected_key:
            return

        raw = self.txt_editor_val.toPlainText()
        val = raw
        if self.selected_type.lower() == "hash":
            try:
                val = json.loads(raw)
            except Exception as e:
                QMessageBox.warning(self, "Error de Formato", f"El valor para Hash debe ser un objeto JSON válido:\n{e}")
                return
        elif self.selected_type.lower() in ("list", "set"):
            try:
                val = json.loads(raw)
                if not isinstance(val, list):
                    val = [str(val)]
            except Exception:
                val = [line.strip() for line in raw.splitlines() if line.strip()]

        ok, msg = self.active_db.set_key_value(self.selected_key, self.selected_type, val, ttl=self.sp_edit_ttl.value())
        if ok:
            QMessageBox.information(self, "Guardado", f"Clave '{self.selected_key}' actualizada con éxito.")
            self.cargar_claves()
        else:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la clave:\n{msg}")

    def _aplicar_ttl(self):
        if not self.active_db or not self.selected_key:
            return
        ttl = self.sp_edit_ttl.value()
        ok, msg = self.active_db.set_ttl(self.selected_key, ttl)
        if ok:
            self.txt_cli_out.appendPlainText(f"[TTL] {self.selected_key} -> {msg}")
            self.cargar_claves()
        else:
            QMessageBox.critical(self, "Error TTL", msg)

    def _nueva_clave(self):
        if not self.active_db:
            return
        dlg = NewRedisKeyDialog(self.colores, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_data:
            k, t, val, ttl = dlg.result_data
            ok, msg = self.active_db.set_key_value(k, t, val, ttl=ttl)
            if ok:
                self.txt_cli_out.appendPlainText(f"[NUEVA CLAVE] Creada '{k}' ({t.upper()})")
                self.cargar_claves()
                self._cargar_detalle_clave(k)
            else:
                QMessageBox.critical(self, "Error al crear", f"No se pudo crear la clave:\n{msg}")

    def _eliminar_clave(self):
        if not self.active_db or not self.selected_key:
            QMessageBox.information(self, "Seleccionar", "Selecciona una clave para eliminar.")
            return

        confirm = QMessageBox.question(
            self, "Eliminar Clave",
            f"¿Estás seguro de eliminar permanentemente la clave '{self.selected_key}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            ok, msg = self.active_db.delete_key(self.selected_key)
            if ok:
                self.txt_cli_out.appendPlainText(f"[DELETE] Clave '{self.selected_key}' eliminada.")
                self.selected_key = ""
                self.txt_editor_val.clear()
                self.btn_save_val.setEnabled(False)
                self.cargar_claves()
            else:
                QMessageBox.critical(self, "Error", msg)

    def _flush_db(self):
        if not self.active_db:
            return
        confirm = QMessageBox.question(
            self, "Vaciar Base de Datos (FLUSHDB)",
            f"⚠️ ¡ADVERTENCIA! ¿Estás COMPLETAMENTE SEGURO de eliminar TODAS las claves en db{self.db_index}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            ok, msg = self.active_db.flush_current_db()
            self.txt_cli_out.appendPlainText(f"[FLUSHDB] {msg}")
            self.cargar_claves()
            self.txt_editor_val.clear()

    def _ejecutar_comando_cli(self, command_str: str = ""):
        if not self.active_db:
            return
        cmd = command_str or self.txt_cli_in.text().strip()
        if not cmd:
            return

        self.txt_cli_out.appendPlainText(f"> {cmd}")
        res, duration_ms, err = self.active_db.execute_command(cmd)

        if err:
            self.txt_cli_out.appendPlainText(f"(error) {err}")
        else:
            if isinstance(res, (dict, list)):
                out = json.dumps(res, indent=2, ensure_ascii=False)
            else:
                out = str(res)
            self.txt_cli_out.appendPlainText(f"{out}\n({duration_ms} ms)")

        if not command_str:
            self.txt_cli_in.clear()
            self.cargar_claves()
