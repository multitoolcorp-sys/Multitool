import os
import platform
import subprocess
import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from ..utils.drive_detector import (
    obtener_letras_unidades_libres,
    obtener_conexiones_red,
    escanear_dispositivos_red_arp
)

class NetworkConnectionDialog(QDialog):
    """
    Diálogo para conectar unidades de red (SMB/UNC) y gestionar
    unidades compartidas mapeadas estilo Explorador de Windows.
    """
    def __init__(self, parent=None, colores=None, on_connected=None):
        super().__init__(parent)
        self.colores = colores or {
            'bg_principal': '#121218',
            'bg_secundario': '#1E1E2E',
            'bg_terciario': '#2D2D3D',
            'fg_principal': '#FFFFFF',
            'fg_secundario': '#AAB0B8',
            'acento': '#6366F1',
            'acento_hover': '#4F46E5',
            'peligro': '#EF4444'
        }
        self.on_connected = on_connected
        self.font_family = "Segoe UI"
        
        self.setWindowTitle("🌐 Conectar a Unidad de Red")
        self.setMinimumWidth(620)
        self.setMinimumHeight(540)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
                font-family: '{self.font_family}';
            }}
            QLabel {{
                color: {self.colores['fg_principal']};
                font-family: '{self.font_family}';
            }}
            QLineEdit {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colores['acento']};
            }}
            QComboBox {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QCheckBox {{
                color: {self.colores['fg_principal']};
                font-size: 11px;
                spacing: 6px;
            }}
        """)

        self.init_ui()
        self.refrescar_conexiones_existentes()
        
        # Iniciar escaneo ARP en segundo plano para sugerir servidores
        QTimer.singleShot(100, self._iniciar_escaneo_red_bg)

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        # Header con Título
        header_lay = QVBoxLayout()
        header_lay.setSpacing(2)
        lbl_titulo = QLabel("🌐 Conectar a Unidad o Recurso de Red")
        lbl_titulo.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet(f"color: {self.colores['acento']};")
        header_lay.addWidget(lbl_titulo)

        lbl_desc = QLabel("Asigna una letra de unidad a una carpeta compartida o conéctate directamente vía SMB/UNC.")
        lbl_desc.setFont(QFont(self.font_family, 9))
        lbl_desc.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        header_lay.addWidget(lbl_desc)
        lay.addLayout(header_lay)

        # Separador
        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet(f"background-color: {self.colores['bg_terciario']};")
        lay.addWidget(sep1)

        # Fila 1: Letra de unidad
        row_letra = QHBoxLayout()
        lbl_l = QLabel("Letra de unidad:")
        lbl_l.setFixedWidth(130)
        lbl_l.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        row_letra.addWidget(lbl_l)

        self.cmb_letra = QComboBox()
        letras_libres = obtener_letras_unidades_libres()
        if letras_libres:
            for l in letras_libres:
                self.cmb_letra.addItem(f"{l} (Disponible)", l)
        else:
            self.cmb_letra.addItem("Z: (Sugerida)", "Z:")
        self.cmb_letra.addItem("🌐 (Sin letra - Solo navegar ruta UNC)", "")
        row_letra.addWidget(self.cmb_letra, 1)
        lay.addLayout(row_letra)

        # Fila 2: Ruta UNC
        row_ruta = QHBoxLayout()
        lbl_r = QLabel("Carpeta o Servidor:")
        lbl_r.setFixedWidth(130)
        lbl_r.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        row_ruta.addWidget(lbl_r)

        self.txt_ruta = QLineEdit()
        self.txt_ruta.setPlaceholderText(r"Ejemplo: \\servidor\compartido o \\192.168.0.15\servers")
        row_ruta.addWidget(self.txt_ruta, 1)

        self.btn_scan = QPushButton("🔍 Escanear")
        self.btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colores['acento']};
                color: white;
            }}
        """)
        self.btn_scan.clicked.connect(self._iniciar_escaneo_red_bg)
        row_ruta.addWidget(self.btn_scan)
        lay.addLayout(row_ruta)

        # Fila 3: Checkboxes de opciones
        row_opts = QHBoxLayout()
        row_opts.setContentsMargins(130, 0, 0, 0)
        self.chk_reconnect = QCheckBox("Reconectar al iniciar sesión")
        self.chk_reconnect.setChecked(True)
        row_opts.addWidget(self.chk_reconnect)

        self.chk_credenciales = QCheckBox("Conectar con credenciales diferentes")
        self.chk_credenciales.toggled.connect(self._toggle_credenciales)
        row_opts.addWidget(self.chk_credenciales)
        row_opts.addStretch()
        lay.addLayout(row_opts)

        # Sección desplegable de Credenciales
        self.container_credenciales = QWidget()
        lay_cred = QVBoxLayout(self.container_credenciales)
        lay_cred.setContentsMargins(130, 4, 0, 4)
        lay_cred.setSpacing(6)

        row_user = QHBoxLayout()
        lbl_u = QLabel("Usuario:")
        lbl_u.setFixedWidth(70)
        lbl_u.setFont(QFont(self.font_family, 9))
        row_user.addWidget(lbl_u)
        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("Ej: DOMINIO\\usuario o usuario")
        row_user.addWidget(self.txt_usuario, 1)
        lay_cred.addLayout(row_user)

        row_pass = QHBoxLayout()
        lbl_p = QLabel("Contraseña:")
        lbl_p.setFixedWidth(70)
        lbl_p.setFont(QFont(self.font_family, 9))
        row_pass.addWidget(lbl_p)
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("••••••••")
        row_pass.addWidget(self.txt_password, 1)
        lay_cred.addLayout(row_pass)

        self.container_credenciales.hide()
        lay.addWidget(self.container_credenciales)

        # Sugerencias / Equipos detectados
        self.lbl_sug = QLabel("Equipos y servidores detectados en tu red local (clic para autocompletar):")
        self.lbl_sug.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self.lbl_sug.setStyleSheet(f"color: {self.colores['fg_secundario']}; margin-top: 6px;")
        lay.addWidget(self.lbl_sug)

        self.lay_chips = QHBoxLayout()
        self.lay_chips.setSpacing(6)
        self.container_chips = QWidget()
        self.container_chips.setLayout(self.lay_chips)
        lay.addWidget(self.container_chips)

        # Tabla de conexiones de red existentes
        lbl_exist = QLabel("Conexiones y Unidades de Red Actuales:")
        lbl_exist.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_exist.setStyleSheet(f"color: {self.colores['fg_principal']}; margin-top: 6px;")
        lay.addWidget(lbl_exist)

        self.table_conns = QTableWidget(0, 4)
        self.table_conns.setHorizontalHeaderLabels(["Estado", "Unidad", "Ruta Remota UNC", "Acciones"])
        self.table_conns.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_conns.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_conns.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_conns.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_conns.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_conns.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_conns.setFixedHeight(140)
        self.table_conns.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                gridline-color: {self.colores['bg_terciario']};
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {self.colores['bg_terciario']};
                color: {self.colores['fg_secundario']};
                padding: 4px 8px;
                border: none;
                font-weight: bold;
                font-size: 10px;
            }}
        """)
        lay.addWidget(self.table_conns)

        # Botones de Acción abajo
        row_btns = QHBoxLayout()
        row_btns.setSpacing(10)
        row_btns.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancelar.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.colores['fg_secundario']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colores['bg_terciario']};
                color: white;
            }}
        """)
        self.btn_cancelar.clicked.connect(self.reject)
        row_btns.addWidget(self.btn_cancelar)

        self.btn_conectar = QPushButton("🚀 Conectar y Abrir")
        self.btn_conectar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_conectar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 7px 20px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#4F46E5')};
            }}
        """)
        self.btn_conectar.clicked.connect(self._ejecutar_conexion)
        row_btns.addWidget(self.btn_conectar)

        lay.addLayout(row_btns)

    def _toggle_credenciales(self, checked):
        self.container_credenciales.setVisible(checked)

    def _iniciar_escaneo_red_bg(self):
        """Escanea la red de forma asíncrona para no congelar la ventana."""
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("⏳ Escaneando...")

        def _worker():
            ips = escanear_dispositivos_red_arp()
            conns = obtener_conexiones_red()
            QTimer.singleShot(0, lambda: self._on_escaneo_finalizado(ips, conns))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _on_escaneo_finalizado(self, ips, conns):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("🔍 Escanear")

        # Limpiar chips
        while self.lay_chips.count():
            item = self.lay_chips.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sugerencias = []
        for c in conns:
            unc = c.get("unc")
            if unc and unc not in sugerencias:
                sugerencias.append(unc)

        for ip in ips:
            unc_ip = f"\\\\{ip}"
            if unc_ip not in sugerencias:
                sugerencias.append(unc_ip)

        if not sugerencias:
            lbl = QLabel("(No se detectaron servidores adicionales en la red local)")
            lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-style: italic; font-size: 10px;")
            self.lay_chips.addWidget(lbl)
        else:
            for s in sugerencias[:5]:
                btn_chip = QPushButton(f"💻 {s}")
                btn_chip.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_chip.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(99, 102, 241, 0.12);
                        color: {self.colores['acento']};
                        border: 1px solid rgba(99, 102, 241, 0.3);
                        border-radius: 12px;
                        padding: 3px 10px;
                        font-size: 10px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: {self.colores['acento']};
                        color: white;
                    }}
                """)
                btn_chip.clicked.connect(lambda ch, ruta=s: self.txt_ruta.setText(ruta))
                self.lay_chips.addWidget(btn_chip)
            self.lay_chips.addStretch()

        self.refrescar_conexiones_existentes()

    def refrescar_conexiones_existentes(self):
        """Actualiza la tabla con las conexiones net use."""
        conns = obtener_conexiones_red()
        self.table_conns.setRowCount(len(conns))

        for row, c in enumerate(conns):
            status = c.get("status", "")
            letter = c.get("letter", "")
            unc = c.get("unc", "")

            it_status = QTableWidgetItem(status)
            it_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "ok" in status.lower() or "conectado" in status.lower():
                it_status.setForeground(QColor("#34D399"))
            else:
                it_status.setForeground(QColor("#FBBF24"))

            it_letter = QTableWidgetItem(letter or "(UNC)")
            it_letter.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            it_unc = QTableWidgetItem(unc)

            self.table_conns.setItem(row, 0, it_status)
            self.table_conns.setItem(row, 1, it_letter)
            self.table_conns.setItem(row, 2, it_unc)

            # Botones de acción en celda
            w_act = QWidget()
            l_act = QHBoxLayout(w_act)
            l_act.setContentsMargins(4, 2, 4, 2)
            l_act.setSpacing(4)

            target_path = f"{letter}\\" if letter else unc
            btn_ir = QPushButton("📂 Abrir")
            btn_ir.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_ir.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores['bg_terciario']};
                    color: white; border: none; border-radius: 4px;
                    padding: 2px 8px; font-size: 10px;
                }}
                QPushButton:hover {{ background: {self.colores['acento']}; }}
            """)
            btn_ir.clicked.connect(lambda ch, tp=target_path: self._abrir_conexion_existente(tp))
            l_act.addWidget(btn_ir)

            btn_del = QPushButton("✕")
            btn_del.setToolTip("Desconectar recurso de red")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {self.colores['peligro']};
                    border: 1px solid rgba(239, 68, 68, 0.4);
                    border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;
                }}
                QPushButton:hover {{ background: {self.colores['peligro']}; color: white; }}
            """)
            target_disc = letter if letter else unc
            btn_del.clicked.connect(lambda ch, td=target_disc: self._desconectar_recurso(td))
            l_act.addWidget(btn_del)

            self.table_conns.setCellWidget(row, 3, w_act)

    def _abrir_conexion_existente(self, target_path):
        if self.on_connected:
            self.on_connected(target_path)
        self.accept()

    def _desconectar_recurso(self, target):
        resp = QMessageBox.question(
            self,
            "Confirmar desconexión",
            f"¿Deseas desconectar el recurso de red '{target}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            try:
                subprocess.run(
                    ["net", "use", target, "/delete", "/y"],
                    capture_output=True,
                    errors="replace",
                    timeout=4,
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                )
            except Exception as e:
                QMessageBox.warning(self, "Error al desconectar", str(e))
            self.refrescar_conexiones_existentes()

    def _ejecutar_conexion(self):
        ruta_raw = self.txt_ruta.text().strip().strip('"').strip("'")
        if not ruta_raw:
            QMessageBox.warning(self, "Ruta requerida", "Por favor ingresa una ruta UNC válida (ej. \\\\servidor\\compartido).")
            return

        # Normalizar barras a formato Windows UNC
        if ruta_raw.startswith("//") or ruta_raw.startswith("\\\\"):
            unc_path = "\\\\" + ruta_raw.lstrip("/\\").replace("/", "\\")
        else:
            unc_path = "\\\\" + ruta_raw.replace("/", "\\")

        letra = self.cmb_letra.currentData()
        reconnect = self.chk_reconnect.isChecked()
        use_creds = self.chk_credenciales.isChecked()
        usuario = self.txt_usuario.text().strip() if use_creds else ""
        password = self.txt_password.text().strip() if use_creds else ""

        self.btn_conectar.setEnabled(False)
        self.btn_conectar.setText("⏳ Conectando...")

        def _do_connect():
            error_msg = None
            try:
                cmd = ["net", "use"]
                if letra:
                    cmd.append(letra)
                cmd.append(unc_path)

                if password:
                    cmd.append(password)
                elif use_creds and not password:
                    # Sin contraseña
                    cmd.append('""')

                if usuario:
                    cmd.append(f"/user:{usuario}")

                if reconnect:
                    cmd.append("/persistent:yes")
                else:
                    cmd.append("/persistent:no")

                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    errors="replace",
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                )
                if res.returncode != 0:
                    out = res.stderr or res.stdout
                    # Si el código es distinto de 0 pero ya está conectado
                    if "ya existe" in out.lower() or "already exists" in out.lower():
                        pass
                    else:
                        error_msg = out.strip() or "No se pudo establecer la conexión de red."
            except subprocess.TimeoutExpired:
                error_msg = "Tiempo de espera agotado al conectar al servidor de red."
            except Exception as e:
                error_msg = str(e)

            QTimer.singleShot(0, lambda: self._on_conexion_completada(error_msg, letra, unc_path))

        t = threading.Thread(target=_do_connect, daemon=True)
        t.start()

    def _on_conexion_completada(self, error_msg, letra, unc_path):
        self.btn_conectar.setEnabled(True)
        self.btn_conectar.setText("🚀 Conectar y Abrir")

        if error_msg:
            QMessageBox.critical(self, "Fallo al conectar", f"Error de red:\n\n{error_msg}")
            return

        target_nav = f"{letra}\\" if letra else unc_path
        if self.on_connected:
            self.on_connected(target_nav)

        self.accept()

