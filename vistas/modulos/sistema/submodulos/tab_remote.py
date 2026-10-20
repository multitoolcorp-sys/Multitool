import sys
import json
import platform
import subprocess
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QFormLayout, QComboBox, QMessageBox, QFrame,
    QSpinBox, QHeaderView, QStackedWidget
)
from PyQt6.QtGui import QGuiApplication,QFont
from PyQt6.QtCore import Qt, QTimer
from controlador.utils.paths import get_data_path

class TabRemote(QWidget):
    """Submódulo para manejar conexiones remotas tipo mRemoteNG"""
    def __init__(self, parent, colores, callbacks, context=None):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.context = context
        
        # Orientar la base de datos a la carpeta de la cuenta si existe el contexto
        if self.context and hasattr(self.context, 'ruta_usuario'):
            self.archivo_datos = Path(self.context.ruta_usuario) / "conexiones_remotas.json"
        else:
            self.archivo_datos = get_data_path() / "conexiones_remotas.json"
            
        self.inicializar_ui()

    def inicializar_ui(self):
        self.layout_principal = QHBoxLayout(self)
        self.layout_principal.setContentsMargins(15, 15, 15, 15)
        self.layout_principal.setSpacing(0)

        # Splitter principal
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: rgba(255,255,255,0.06);
                width: 1px;
            }}
        """)

        # ── Panel izquierdo (Conexiones guardadas) ──
        self.panel_izq = QFrame()
        self.panel_izq.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        layout_izq = QVBoxLayout(self.panel_izq)
        layout_izq.setContentsMargins(14, 14, 14, 14)
        layout_izq.setSpacing(10)

        lbl_titulo_izq = QLabel("🖧 CONEXIONES REMOTAS")
        lbl_titulo_izq.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_titulo_izq.setStyleSheet(f"color: {self.colores['fg_secundario']}; letter-spacing: 1.5px;")
        layout_izq.addWidget(lbl_titulo_izq)

        self.arbol_conexiones = QTreeWidget()
        self.arbol_conexiones.setHeaderHidden(True)
        self.arbol_conexiones.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.arbol_conexiones.setStyleSheet(f"""
            QTreeWidget {{
                background: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 8px;
                outline: none;
                padding: 4px;
            }}
            QTreeWidget::item {{
                padding: 7px 10px;
                border-radius: 4px;
            }}
            QTreeWidget::item:hover {{
                background: rgba(255,255,255,0.05);
            }}
            QTreeWidget::item:selected {{
                background: {self.colores['acento']}33;
                color: white;
                border-left: 2px solid {self.colores['acento']};
            }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.15);
                border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        layout_izq.addWidget(self.arbol_conexiones)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self.btn_nuevo = QPushButton("➕ Nueva")
        self.btn_nuevo.setFixedHeight(34)
        self.btn_nuevo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nuevo.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                border-radius: 7px;
                font-weight: bold;
                font-size: 10px;
                border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        self.btn_nuevo.clicked.connect(self.nueva_conexion)

        self.btn_eliminar = QPushButton("🗑️ Borrar")
        self.btn_eliminar.setFixedHeight(34)
        self.btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eliminar.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores['error']};
                border: 1px solid {self.colores['error']}88;
                border-radius: 7px;
                font-weight: bold;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background: {self.colores['error']}22;
                color: #FF6B6B;
            }}
        """)
        self.btn_eliminar.clicked.connect(self.eliminar_conexion)

        btn_layout.addWidget(self.btn_nuevo)
        btn_layout.addWidget(self.btn_eliminar)
        layout_izq.addLayout(btn_layout)

        # ── Panel derecho (Detalles + consola) ──
        self.panel_der = QFrame()
        self.panel_der.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        layout_der = QVBoxLayout(self.panel_der)
        layout_der.setContentsMargins(18, 14, 18, 14)
        layout_der.setSpacing(12)

        lbl_titulo_der = QLabel("⚙️ CONFIGURACIÓN DE CONEXIÓN")
        lbl_titulo_der.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_titulo_der.setStyleSheet(f"color: {self.colores['fg_secundario']}; letter-spacing: 1.5px;")
        layout_der.addWidget(lbl_titulo_der)

        # Formulario de configuración
        form_frame = QFrame()
        form_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(16, 14, 16, 14)
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.txt_nombre = QLineEdit()

        lay_ip = QHBoxLayout()
        lay_ip.setContentsMargins(0, 0, 0, 0)
        lay_ip.setSpacing(8)
        self.txt_ip = QLineEdit()
        self.lbl_estado = QLabel("⚫")
        self.lbl_estado.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        self.txt_ip.textChanged.connect(self._iniciar_chequeo_ping)
        lay_ip.addWidget(self.txt_ip)
        lay_ip.addWidget(self.lbl_estado)

        self.txt_usuario = QLineEdit()

        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("Autocopia al conectar (Win/Mac)")

        self.combo_proto = QComboBox()
        self.combo_proto.addItems(["SSH", "Telnet", "RDP"])

        self.spin_font = QSpinBox()
        self.spin_font.setRange(8, 72)
        self.spin_font.setValue(14)
        self.spin_font.setSuffix(" pt")

        estilo_input = f"""
            QLineEdit, QComboBox, QSpinBox {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 28px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border: 1.5px solid {self.colores['acento']};
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {self.colores['bg_terciario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                selection-background-color: {self.colores['acento']}44;
            }}
        """
        estilo_label = f"color: {self.colores['fg_secundario']}; font-size: 9pt; font-weight: bold;"

        for w in [self.txt_nombre, self.txt_ip, self.txt_usuario, self.txt_pass, self.combo_proto, self.spin_font]:
            w.setStyleSheet(estilo_input)

        def _lbl(txt):
            l = QLabel(txt)
            l.setStyleSheet(estilo_label)
            return l

        form_layout.addRow(_lbl("Nombre:"), self.txt_nombre)
        form_layout.addRow(_lbl("IP/Host:"), lay_ip)
        form_layout.addRow(_lbl("Usuario:"), self.txt_usuario)
        form_layout.addRow(_lbl("Clave:"), self.txt_pass)
        form_layout.addRow(_lbl("Protocolo:"), self.combo_proto)
        form_layout.addRow(_lbl("Tamaño CMD:"), self.spin_font)

        layout_der.addWidget(form_frame)

        btn_accion_layout = QHBoxLayout()
        btn_accion_layout.setSpacing(10)

        self.btn_guardar = QPushButton("💾  Guardar")
        self.btn_guardar.setFixedHeight(40)
        self.btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guardar.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('exito', '#22c55e')};
                color: white;
                font-weight: bold;
                border-radius: 9px;
                border: none;
            }}
            QPushButton:hover {{ background: #16a34a; }}
        """)
        self.btn_guardar.clicked.connect(self.guardar_perfil)

        self.btn_conectar = QPushButton("🚀  Conectar")
        self.btn_conectar.setFixedHeight(40)
        self.btn_conectar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_conectar.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                font-weight: bold;
                border-radius: 9px;
                border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        self.btn_conectar.clicked.connect(self.conectar)

        btn_accion_layout.addWidget(self.btn_guardar)
        btn_accion_layout.addWidget(self.btn_conectar)
        layout_der.addLayout(btn_accion_layout)

        # Placeholder / info terminal
        self.terminal_log = QLabel("Las sesiones de consola verdaderas\n(que soportan Curses/Top/Nano) se abrirán\nnativamente aprovechando el Terminal del SO.")
        self.terminal_log.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.terminal_log.setStyleSheet(f"""
            QLabel {{
                color: {self.colores['fg_secundario']};
                font-style: italic;
                font-size: 10pt;
                background: {self.colores['bg_principal']};
                border-radius: 8px;
                padding: 16px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        layout_der.addWidget(self.terminal_log)
        layout_der.addStretch()

        # ── Stack Derecho: 0 = Vista por defecto / Estado vacío, 1 = Configuración ──
        self._setup_widget_vacio()
        self.stack_der = QStackedWidget(self.splitter)
        self.stack_der.addWidget(self.widget_vacio)
        self.stack_der.addWidget(self.panel_der)

        self.splitter.addWidget(self.panel_izq)
        self.splitter.addWidget(self.stack_der)
        self.splitter.setSizes([250, 560])

        self.layout_principal.addWidget(self.splitter)

        self.cargar_conexiones()
        self.actualizar_vista_vacia()
        self.stack_der.setCurrentWidget(self.widget_vacio)

    def _setup_widget_vacio(self):
        """Construye la vista por defecto cuando no hay ninguna conexión seleccionada."""
        self.widget_vacio = QFrame()
        self.widget_vacio.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        v_lay = QVBoxLayout(self.widget_vacio)
        v_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_lay.setContentsMargins(30, 30, 30, 30)
        v_lay.setSpacing(14)

        lbl_icon = QLabel("🌐")
        lbl_icon.setFont(QFont("Segoe UI", 48))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("border: none; background: transparent;")
        v_lay.addWidget(lbl_icon)

        lbl_tit = QLabel("CONTROL REMOTO & TERMINAL")
        lbl_tit.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_tit.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")
        v_lay.addWidget(lbl_tit)

        lbl_desc = QLabel(
            "Selecciona una conexión del panel izquierdo para configurar o iniciar sesión,\n"
            "o añade un nuevo host para conectarte mediante SSH, Telnet o RDP."
        )
        lbl_desc.setFont(QFont("Segoe UI", 9))
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        v_lay.addWidget(lbl_desc)

        # Tarjeta de estado
        self.card_stats_remote = QFrame()
        self.card_stats_remote.setStyleSheet(f"""
            background-color: {self.colores['bg_terciario']};
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.06);
        """)
        cs_lay = QHBoxLayout(self.card_stats_remote)
        cs_lay.setContentsMargins(16, 8, 16, 8)

        self.lbl_vacio_stats = QLabel("📊 Dispositivos Guardados: 0")
        self.lbl_vacio_stats.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_vacio_stats.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        cs_lay.addWidget(self.lbl_vacio_stats)
        cs_lay.addStretch()

        lbl_proto = QLabel("🔒 Protocolos: SSH | Telnet | RDP")
        lbl_proto.setFont(QFont("Segoe UI", 9))
        lbl_proto.setStyleSheet(f"color: {self.colores.get('exito', '#34D399')}; border: none; background: transparent;")
        cs_lay.addWidget(lbl_proto)
        v_lay.addWidget(self.card_stats_remote)

        # Acciones rápidas
        row_quick = QHBoxLayout()
        row_quick.setSpacing(10)

        btn_q_nuevo = QPushButton("➕ Nueva Conexión")
        btn_q_nuevo.setFixedHeight(34)
        btn_q_nuevo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_nuevo.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn_q_nuevo.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 7px; padding: 0 16px; border: none;")
        btn_q_nuevo.clicked.connect(self.nueva_conexion)
        row_quick.addWidget(btn_q_nuevo)
        v_lay.addLayout(row_quick)

        lbl_esc = QLabel("💡 Presiona la tecla Esc para deseleccionar y volver a esta pantalla")
        lbl_esc.setFont(QFont("Segoe UI", 8))
        lbl_esc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_esc.setStyleSheet("color: rgba(255,255,255,0.35); margin-top: 8px; border: none; background: transparent;")
        v_lay.addWidget(lbl_esc)

    def actualizar_vista_vacia(self):
        """Actualiza el contador numérico de conexiones guardadas en la vista vacía."""
        total = self.raiz.childCount() if hasattr(self, "raiz") else 0
        if hasattr(self, "lbl_vacio_stats"):
            self.lbl_vacio_stats.setText(f"📊 Dispositivos Guardados: {total}")

    def keyPressEvent(self, event):
        """Deselecciona y regresa a la vista vacía con Escape."""
        if event.key() == Qt.Key.Key_Escape:
            self.arbol_conexiones.clearSelection()
            self.actualizar_vista_vacia()
            if hasattr(self, "stack_der"):
                self.stack_der.setCurrentWidget(self.widget_vacio)
        super().keyPressEvent(event)

    def cargar_conexiones(self):
        self.arbol_conexiones.clear()
        self.raiz = QTreeWidgetItem(self.arbol_conexiones, ["Dispositivos Guardados"])
        self.raiz.setExpanded(True)
        
        conexiones = []
        if self.archivo_datos.exists():
            try:
                with open(self.archivo_datos, "r", encoding="utf-8") as f:
                    conexiones = json.load(f)
            except Exception: pass
            
        if not conexiones:
            conexiones = [{"name": "Localhost Test", "ip": "127.0.0.1", "user": "admin", "proto": "SSH"}]
            
        for data in conexiones:
            hijo = QTreeWidgetItem(self.raiz, [data.get("name", "Host")])
            hijo.setData(0, Qt.ItemDataRole.UserRole, data)
            
        self.arbol_conexiones.itemClicked.connect(self.cargar_datos)

    def guardar_todas_las_conexiones(self):
        data = []
        for i in range(self.raiz.childCount()):
            item = self.raiz.child(i)
            obj = item.data(0, Qt.ItemDataRole.UserRole)
            if obj: data.append(obj)
        try:
            with open(self.archivo_datos, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception: pass

    def guardar_perfil(self):
        item = self.arbol_conexiones.currentItem()
        if not item or item == self.raiz: return
            
        data = {
            "name": self.txt_nombre.text().strip() or "Nuevo_Host",
            "ip": self.txt_ip.text().strip(),
            "user": self.txt_usuario.text().strip(),
            "pass": self.txt_pass.text(),
            "proto": self.combo_proto.currentText(),
            "font": self.spin_font.value()
        }
        item.setText(0, data["name"])
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        self.guardar_todas_las_conexiones()
        
        # Feedback visual discreto sin alertas intrusivas
        texto_orig = self.btn_guardar.text()
        self.btn_guardar.setText("✅ Guardado")
        self.btn_guardar.setStyleSheet(self.btn_guardar.styleSheet().replace(self.colores.get('exito', '#43A047'), '#2E7D32'))
        QTimer.singleShot(1500, lambda: [self.btn_guardar.setText(texto_orig), self.btn_guardar.setStyleSheet(self.btn_guardar.styleSheet().replace('#2E7D32', self.colores.get('exito', '#43A047')))])

    def nueva_conexion(self):
        item = QTreeWidgetItem(self.raiz, ["Nueva Conexión"])
        item.setData(0, Qt.ItemDataRole.UserRole, {"name": "Nueva Conexión", "ip": "", "user": "", "pass": "", "proto": "SSH", "font": 14})
        self.arbol_conexiones.setCurrentItem(item)
        self.cargar_datos(item)
        self.guardar_todas_las_conexiones()
        self.actualizar_vista_vacia()
        if hasattr(self, "stack_der"):
            self.stack_der.setCurrentWidget(self.panel_der)

    def eliminar_conexion(self):
        item = self.arbol_conexiones.currentItem()
        if item and item != self.raiz:
            self.raiz.removeChild(item)
            self.guardar_todas_las_conexiones()
            self.txt_nombre.clear()
            self.txt_ip.clear()
            self.txt_usuario.clear()
            self.txt_pass.clear()
            self.actualizar_vista_vacia()
            if hasattr(self, "stack_der"):
                self.stack_der.setCurrentWidget(self.widget_vacio)

    def cargar_datos(self, item):
        if item == self.raiz:
            if hasattr(self, "stack_der"):
                self.stack_der.setCurrentWidget(self.widget_vacio)
            self.actualizar_vista_vacia()
            return
        if hasattr(self, "stack_der"):
            self.stack_der.setCurrentWidget(self.panel_der)
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.txt_nombre.setText(data.get("name", item.text(0)))
            self.txt_ip.setText(data.get("ip", ""))
            self.txt_usuario.setText(data.get("user", ""))
            self.txt_pass.setText(data.get("pass", ""))
            self.combo_proto.setCurrentText(data.get("proto", "SSH"))
            self.spin_font.setValue(data.get("font", 14))

    def conectar(self):
        ip = self.txt_ip.text().strip()
        usr = self.txt_usuario.text().strip()
        pwd = self.txt_pass.text()
        proto = self.combo_proto.currentText()
        f_size = self.spin_font.value()
        
        if not ip:
            QMessageBox.warning(self, "Error", "Debe ingresar una IP/Host para conectar.")
            return

        if pwd:
            if platform.system() == "Windows":
                self.terminal_log.setText("✅ Clave detectada. Iniciando sesión e inyectando credencial mágica.\n(Si pide 'yes/no' la primera vez, ignora el error y usa portapapeles).")
                QGuiApplication.clipboard().setText(pwd)  # Respaldo por si acaso
            else:
                QGuiApplication.clipboard().setText(pwd)
                self.terminal_log.setText("✅ ¡Clave copiada automáticamente!\nHaz clic derecho en la ventanita negra para pegarla.")
        else:
            self.terminal_log.setText("Iniciando sesión nativa SSH sin clave adjunta...")
            
        if proto == "SSH":
            cmd = f"ssh {usr}@{ip}" if usr else f"ssh {ip}"
            so = platform.system()
            try:
                # Disparar shell independiente verdadera
                if so == "Windows":
                    if pwd:
                        # Usamos wshell.Run con cmd /k para garantizar que la pantalla negra SEA VISIBLE (1) y persista
                        ps_script = f"$wshell = New-Object -ComObject wscript.shell; $wshell.Run('cmd.exe /k {cmd}', 1, $false); Start-Sleep -Milliseconds 1500; $wshell.SendKeys('{pwd}'); $wshell.SendKeys('{{ENTER}}');"
                        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script])
                    else:
                        subprocess.Popen(f'start cmd /k "{cmd}"', shell=True)
                elif so == "Linux":
                    # Intentar emuladores estándar
                    for term in ["x-terminal-emulator", "gnome-terminal", "konsole"]:
                        try:
                            subprocess.Popen([term, "-e", cmd])
                            break
                        except: pass
                elif so == "Darwin":
                    subprocess.Popen(['osascript', '-e', f'tell app "Terminal" to do script "{cmd}"'])
            except Exception as e:
                QMessageBox.critical(self, "Error de Ejecución", f"No se pudo iniciar la consola: {e}")
        elif proto == "Telnet":
            # Comando genérico en windows/linux
            QMessageBox.information(self, "Info", "Ejecutando Telnet... (Asegúrate de tener el cliente instalado).")
            if platform.system() == "Windows":
                subprocess.Popen(f'start cmd /k "telnet {ip}"', shell=True)
            else:
                try: subprocess.Popen(["x-terminal-emulator", "-e", f"telnet {ip}"])
                except: pass
        else:
            QMessageBox.information(self, "Protocolo Incompleto", f"El soporte para {proto} se añadirá posteriormente.")

    # ──────────────────────────────────────────────────
    #  ESTADO INDICADOR EN TIEMPO REAL (PING CIRCULO)
    # ──────────────────────────────────────────────────
    def _iniciar_chequeo_ping(self, txt):
        if not txt.strip():
            self.lbl_estado.setText("⚫")
            return
            
        if hasattr(self, "_timer_ping"):
            self._timer_ping.stop()
        else:
            self._timer_ping = QTimer()
            self._timer_ping.setSingleShot(True)
            self._timer_ping.timeout.connect(lambda: threading.Thread(target=self._validar_ip, daemon=True).start())
            
        self._timer_ping.start(1000)

    def _validar_ip(self):
        ip = self.txt_ip.text().strip()
        if not ip: return
            
        cmd_args = ["ping", "-n", "1", "-w", "1000", ip] if platform.system() == "Windows" else ["ping", "-c", "1", "-W", "1", ip]
        kwargs = {}
        if platform.system() == "Windows":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            
        try:
            res = subprocess.run(cmd_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
            exito = (res.returncode == 0)
        except Exception:
            exito = False
        
        QTimer.singleShot(0, lambda: self.lbl_estado.setText("🟢" if exito else "🔴"))
