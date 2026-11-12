import os
import sys
import csv
import json
import time
import socket
import platform
import subprocess
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QFormLayout, QComboBox, QMessageBox, QFrame,
    QSpinBox, QHeaderView, QStackedWidget, QTabWidget, QTextEdit, QPlainTextEdit,
    QCheckBox, QFileDialog, QMenu, QTableWidget, QTableWidgetItem, QInputDialog,
    QAbstractItemView, QToolButton, QApplication
)
from PyQt6.QtGui import QGuiApplication, QFont, QColor, QAction, QTextCursor
from PyQt6.QtCore import Qt, QTimer, QProcess, pyqtSignal, QUrl

from controlador.utils.paths import get_data_path

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False


DEFAULT_PORTS = {
    "SSH": 22,
    "RDP": 3389,
    "Telnet": 23,
    "VNC": 5900,
    "HTTP": 80,
    "HTTPS": 443,
    "SFTP": 22,
    "FTP": 21,
    "WinRM": 5985,
    "Raw": 9000,
}

PROTO_ICONS = {
    "SSH": "🖧",
    "RDP": "🖥️",
    "Telnet": "📟",
    "VNC": "👁️",
    "HTTP": "🌐",
    "HTTPS": "🔒",
    "SFTP": "📂",
    "FTP": "📁",
    "WinRM": "⚡",
    "Raw": "🔌",
}

TERMINAL_THEMES = {
    "Matrix Green": {"bg": "#070B0E", "fg": "#10B981", "accent": "#059669", "cmd": "#34D399"},
    "Cyberpunk Cyan": {"bg": "#080B14", "fg": "#38BDF8", "accent": "#0284C7", "cmd": "#7DD3FC"},
    "Dracula": {"bg": "#1E1F29", "fg": "#F8F8F2", "accent": "#BD93F9", "cmd": "#50FA7B"},
    "Amber Retro": {"bg": "#120D05", "fg": "#F59E0B", "accent": "#D97706", "cmd": "#FBBF24"},
    "Classic White": {"bg": "#0C0C0C", "fg": "#E5E7EB", "accent": "#6366F1", "cmd": "#FFFFFF"},
}

SSH_MACROS = [
    ("⚡ Seleccionar Macro / Snippet...", ""),
    ("📊 Recursos en Vivo (top -b -n 1)", "top -b -n 1 | head -n 25"),
    ("💾 Espacio en Disco (df -h)", "df -h"),
    ("🧠 Uso de Memoria RAM (free -m)", "free -m"),
    ("🐳 Contenedores Docker (docker ps -a)", "docker ps -a"),
    ("⚙️ Servicios Fallidos (systemctl --failed)", "systemctl --failed"),
    ("🔌 Puertos Escuchando (ss -tulpn)", "ss -tulpn"),
    ("📜 Últimos Logs del Sistema (journalctl)", "journalctl -n 40 --no-pager"),
    ("🌐 Interfaces e IPs (ip -br a)", "ip -br a"),
    ("⏱️ Uptime y Usuarios Conectados (w)", "uptime && w"),
]


class MRemoteTerminalSession(QWidget):
    """Pestaña de consola interactiva estilo mRemoteNG / MobaXterm para SSH, Telnet, SFTP, FTP, WinRM y Raw."""

    def __init__(self, parent, conn_data: dict, colores: dict, open_native_cb=None):
        super().__init__(parent)
        self.conn_data = dict(conn_data)
        self.colores = colores
        self.open_native_cb = open_native_cb
        self.process = None
        self.raw_socket = None
        self.history = []
        self.history_idx = -1
        self.font_size = int(self.conn_data.get("font", 12))
        self.theme_name = self.conn_data.get("theme", "Matrix Green")
        self.connected_at = datetime.now()
        self._password_injected = False
        self._post_cmd_sent = False

        self._build_ui()
        self.iniciar_sesion()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # Barra de herramientas de la sesión activa
        bar = QFrame()
        bar.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.07);
            }}
        """)
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(10, 6, 10, 6)
        bar_lay.setSpacing(8)

        proto = self.conn_data.get("proto", "SSH")
        ip = self.conn_data.get("ip", "")
        port = self.conn_data.get("port", DEFAULT_PORTS.get(proto, 22))
        user = self.conn_data.get("user", "")
        target_str = f"{user}@{ip}:{port}" if user else f"{ip}:{port}"

        self.lbl_status = QLabel(f"🟢 [{proto}] {target_str}")
        self.lbl_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: #34D399; border: none; background: transparent;")
        bar_lay.addWidget(self.lbl_status)

        bar_lay.addStretch()

        # Selector de Macros / Snippets
        self.combo_macros = QComboBox()
        for label, cmd in SSH_MACROS:
            self.combo_macros.addItem(label, cmd)
        self.combo_macros.setFixedWidth(230)
        self.combo_macros.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 9pt;
            }}
            QComboBox QAbstractItemView {{
                background: {self.colores['bg_secundario']};
                color: white;
                selection-background-color: {self.colores['acento']};
            }}
        """)
        self.combo_macros.currentIndexChanged.connect(self._ejecutar_macro_seleccionada)
        bar_lay.addWidget(self.combo_macros)

        # Selector de tema visual en vivo
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(list(TERMINAL_THEMES.keys()))
        if self.theme_name in TERMINAL_THEMES:
            self.combo_theme.setCurrentText(self.theme_name)
        self.combo_theme.setFixedWidth(130)
        self.combo_theme.setStyleSheet(self.combo_macros.styleSheet())
        self.combo_theme.currentTextChanged.connect(self._aplicar_tema_consola)
        bar_lay.addWidget(self.combo_theme)

        btn_style = f"""
            QPushButton {{
                background: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 5px;
                padding: 4px 9px;
                font-size: 8.5pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {self.colores['acento']};
                color: white;
            }}
        """

        btn_inject = QPushButton("🔑 Clave")
        btn_inject.setToolTip("Inyectar contraseña guardada o copiarla al portapapeles")
        btn_inject.setStyleSheet(btn_style)
        btn_inject.clicked.connect(self.inyectar_password)
        bar_lay.addWidget(btn_inject)

        btn_ctrlc = QPushButton("🛑 Ctrl+C")
        btn_ctrlc.setToolTip("Enviar señal de interrupción SIGINT (Ctrl+C)")
        btn_ctrlc.setStyleSheet(btn_style)
        btn_ctrlc.clicked.connect(self.enviar_ctrl_c)
        bar_lay.addWidget(btn_ctrlc)

        btn_clear = QPushButton("🧹 Limpiar")
        btn_clear.setStyleSheet(btn_style)
        btn_clear.clicked.connect(lambda: self.console.clear())
        bar_lay.addWidget(btn_clear)

        btn_log = QPushButton("💾 Log")
        btn_log.setToolTip("Exportar historial de esta sesión a archivo .log")
        btn_log.setStyleSheet(btn_style)
        btn_log.clicked.connect(self.exportar_log)
        bar_lay.addWidget(btn_log)

        btn_reconnect = QPushButton("🔄 Reconectar")
        btn_reconnect.setStyleSheet(btn_style)
        btn_reconnect.clicked.connect(self.iniciar_sesion)
        bar_lay.addWidget(btn_reconnect)

        btn_native = QPushButton("🪟 Nativa")
        btn_native.setToolTip("Desacoplar y abrir en ventana de terminal nativa del SO (para nano/vim/htop interactivo)")
        btn_native.setStyleSheet(btn_style)
        btn_native.clicked.connect(self._abrir_nativa)
        bar_lay.addWidget(btn_native)

        lay.addWidget(bar)

        # Pantalla de salida de terminal
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(5000)
        lay.addWidget(self.console, 1)

        # Barra de entrada de comandos interactiva
        cmd_frame = QFrame()
        cmd_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 7px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
        """)
        cmd_lay = QHBoxLayout(cmd_frame)
        cmd_lay.setContentsMargins(10, 4, 6, 4)
        cmd_lay.setSpacing(8)

        lbl_prompt = QLabel("❯")
        lbl_prompt.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        lbl_prompt.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        cmd_lay.addWidget(lbl_prompt)

        self.txt_cmd = QLineEdit()
        self.txt_cmd.setPlaceholderText("Escribe un comando y presiona Enter (Usa ↑/↓ para historial, o escribe 'yes' / contraseña cuando lo solicite)...")
        self.txt_cmd.setFont(QFont("Consolas", 10))
        self.txt_cmd.setStyleSheet("background: transparent; color: white; border: none; padding: 4px;")
        self.txt_cmd.returnPressed.connect(self._on_enter_cmd)
        self.txt_cmd.installEventFilter(self)
        cmd_lay.addWidget(self.txt_cmd, 1)

        btn_send = QPushButton("Enviar ↵")
        btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                border-radius: 5px;
                padding: 5px 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_send.clicked.connect(self._on_enter_cmd)
        cmd_lay.addWidget(btn_send)

        lay.addWidget(cmd_frame)
        self._aplicar_tema_consola(self.theme_name)

    def eventFilter(self, obj, event):
        if obj == self.txt_cmd and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                if self.history and self.history_idx > 0:
                    self.history_idx -= 1
                    self.txt_cmd.setText(self.history[self.history_idx])
                return True
            elif event.key() == Qt.Key.Key_Down:
                if self.history and self.history_idx < len(self.history) - 1:
                    self.history_idx += 1
                    self.txt_cmd.setText(self.history[self.history_idx])
                else:
                    self.history_idx = len(self.history)
                    self.txt_cmd.clear()
                return True
        return super().eventFilter(obj, event)

    def _aplicar_tema_consola(self, theme_name: str):
        self.theme_name = theme_name
        t = TERMINAL_THEMES.get(theme_name, TERMINAL_THEMES["Matrix Green"])
        self.console.setFont(QFont("Consolas", self.font_size))
        self.console.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {t['bg']};
                color: {t['fg']};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
                padding: 10px;
                selection-background-color: {t['accent']};
            }}
        """)

    def append_output(self, text: str):
        if not text:
            return
        # Limpiar secuencias ANSI básicas para legibilidad limpia en QPlainTextEdit
        import re
        clean = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", text)
        self.console.moveCursor(QTextCursor.MoveOperation.End)
        self.console.insertPlainText(clean)
        self.console.moveCursor(QTextCursor.MoveOperation.End)

        low = clean.lower()
        if ("password:" in low or "contraseña:" in low) and not self._password_injected:
            pwd = self.conn_data.get("pass", "")
            if pwd:
                self._password_injected = True
                QTimer.singleShot(250, lambda: self.enviar_comando(pwd, ocultar_eco=True))

        if not self._post_cmd_sent and any(prompt in clean for prompt in ["$ ", "# ", "> "]):
            post_cmd = (self.conn_data.get("post_cmd") or "").strip()
            if post_cmd:
                self._post_cmd_sent = True
                QTimer.singleShot(400, lambda: self.enviar_comando(post_cmd))

    def iniciar_sesion(self):
        self.cerrar_sesion()
        self._password_injected = False
        self._post_cmd_sent = False

        proto = self.conn_data.get("proto", "SSH")
        ip = self.conn_data.get("ip", "").strip()
        port = int(self.conn_data.get("port", DEFAULT_PORTS.get(proto, 22)) or DEFAULT_PORTS.get(proto, 22))
        user = self.conn_data.get("user", "").strip()
        ssh_key = (self.conn_data.get("ssh_key") or "").strip()
        tunnel = (self.conn_data.get("ssh_tunnel") or "").strip()

        self.console.clear()
        self.append_output(f"═══ mRemoteNG Session [{proto}] → {ip}:{port} ({datetime.now().strftime('%H:%M:%S')}) ═══\n")

        if self.conn_data.get("pass"):
            QGuiApplication.clipboard().setText(self.conn_data.get("pass"))
            self.append_output("🔑 Contraseña cargada en portapapeles y lista para auto-inyección.\n")

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_ready_read)
        self.process.finished.connect(self._on_finished)

        if proto == "SSH":
            args = ["-tt", "-p", str(port), "-o", "StrictHostKeyChecking=accept-new"]
            if ssh_key and os.path.exists(ssh_key):
                args.extend(["-i", ssh_key])
            if tunnel:
                args.extend(tunnel.split())
            target = f"{user}@{ip}" if user else ip
            args.append(target)
            self.append_output(f"$ ssh {' '.join(args)}\n\n")
            self.process.start("ssh", args)
        elif proto == "SFTP":
            args = ["-P", str(port), "-o", "StrictHostKeyChecking=accept-new"]
            if ssh_key and os.path.exists(ssh_key):
                args.extend(["-i", ssh_key])
            target = f"{user}@{ip}" if user else ip
            args.append(target)
            self.append_output(f"$ sftp {' '.join(args)}\n\n")
            self.process.start("sftp", args)
        elif proto == "FTP":
            self.append_output(f"$ ftp {ip} {port}\n\n")
            self.process.start("ftp", [ip])
        elif proto == "Telnet":
            self.append_output(f"$ telnet {ip} {port}\n\n")
            self.process.start("telnet", [ip, str(port)])
        elif proto == "WinRM":
            ps_cmd = f"Enter-PSSession -ComputerName {ip} -Port {port}"
            if user:
                ps_cmd += f" -Credential {user}"
            self.append_output(f"PS> {ps_cmd}\n\n")
            self.process.start("powershell", ["-NoLogo", "-NoExit", "-Command", ps_cmd])
        else:
            # Raw TCP o fallback interactivo con PowerShell/Python socket bridge
            py_bridge = (
                f"import socket, sys, threading; "
                f"s = socket.create_connection(('{ip}', {port}), timeout=5); "
                f"print('Conectado a socket TCP {ip}:{port}'); "
                f"t = threading.Thread(target=lambda: [sys.stdout.write(s.recv(4096).decode('utf-8','replace')) or sys.stdout.flush() for _ in iter(int, 1)], daemon=True); "
                f"t.start(); "
                f"[s.sendall((line).encode('utf-8')) for line in sys.stdin]"
            )
            self.process.start(sys.executable, ["-u", "-c", py_bridge])

        self.lbl_status.setText(f"🟢 [{proto}] {user + '@' if user else ''}{ip}:{port}")
        self.lbl_status.setStyleSheet("color: #34D399; border: none; background: transparent;")
        self.txt_cmd.setFocus()

    def _on_ready_read(self):
        if not self.process:
            return
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.append_output(data)

    def _on_finished(self, code, status):
        self.append_output(f"\n─── Sesión finalizada (código: {code}) ───\n")
        self.lbl_status.setText(f"🔴 [{self.conn_data.get('proto', 'SSH')}] Desconectado ({ self.conn_data.get('ip', '') })")
        self.lbl_status.setStyleSheet("color: #F87171; border: none; background: transparent;")

    def _on_enter_cmd(self):
        cmd = self.txt_cmd.text()
        self.txt_cmd.clear()
        if cmd.strip():
            self.history.append(cmd)
            self.history_idx = len(self.history)
        self.enviar_comando(cmd)

    def enviar_comando(self, cmd: str, ocultar_eco: bool = False):
        if not ocultar_eco:
            self.append_output(f"{cmd}\n")
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            payload = (cmd + "\n").encode("utf-8")
            self.process.write(payload)
        else:
            self.append_output("⚠️ El proceso no está activo. Usa '🔄 Reconectar'.\n")

    def enviar_ctrl_c(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.write(b"\x03")
            self.append_output("^C\n")

    def inyectar_password(self):
        pwd = self.conn_data.get("pass", "")
        if not pwd:
            QMessageBox.information(self, "Sin Clave", "Esta conexión no tiene una contraseña guardada.")
            return
        QGuiApplication.clipboard().setText(pwd)
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.enviar_comando(pwd, ocultar_eco=True)
            self.append_output("🔐 [Contraseña inyectada en sesión y copiada al portapapeles]\n")
        else:
            self.append_output("📋 [Contraseña copiada al portapapeles]\n")

    def _ejecutar_macro_seleccionada(self, idx: int):
        if idx <= 0:
            return
        cmd = self.combo_macros.itemData(idx)
        if cmd:
            self.enviar_comando(cmd)
        self.combo_macros.setCurrentIndex(0)

    def exportar_log(self):
        nombre = self.conn_data.get("name", "sesion").replace(" ", "_")
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar Log de Sesión mRemoteNG", f"log_{nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", "Log Files (*.log *.txt)"
        )
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(self.console.toPlainText())
            QMessageBox.information(self, "Log Exportado", f"Historial guardado en:\n{ruta}")

    def _abrir_nativa(self):
        if callable(self.open_native_cb):
            self.open_native_cb(self.conn_data)

    def cerrar_sesion(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(500)


class MRemoteRDPSession(QWidget):
    """Pestaña de control y lanzamiento directo de sesiones RDP / VNC estilo mRemoteNG con SSO (cmdkey)."""

    def __init__(self, parent, conn_data: dict, colores: dict, launch_cb=None):
        super().__init__(parent)
        self.conn_data = dict(conn_data)
        self.colores = colores
        self.launch_cb = launch_cb
        self._build_ui()
        # Lanzar automáticamente al abrir la pestaña
        QTimer.singleShot(250, lambda: self.lanzar_cliente(fullscreen=False))
        self._iniciar_monitor_puerto()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
        """)
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(22, 18, 22, 18)
        c_lay.setSpacing(10)

        proto = self.conn_data.get("proto", "RDP")
        name = self.conn_data.get("name", "Servidor Remoto")
        ip = self.conn_data.get("ip", "")
        port = self.conn_data.get("port", DEFAULT_PORTS.get(proto, 3389))
        user = self.conn_data.get("user", "Administrador")
        domain = self.conn_data.get("domain", "")
        res = self.conn_data.get("resolution", "Smart Sizing (Ajustar)")

        lbl_title = QLabel(f"🖥️  Sesión {proto}: {name}")
        lbl_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none; background: transparent;")
        c_lay.addWidget(lbl_title)

        self.lbl_status = QLabel(f"📡 Verificando disponibilidad de {ip}:{port}...")
        self.lbl_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: #34D399; border: none; background: transparent;")
        c_lay.addWidget(self.lbl_status)

        resumen_html = (
            f"<b>Host / IP:</b> {ip}:{port} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Usuario:</b> {domain + '\\' if domain else ''}{user} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Resolución:</b> {res}<br>"
            f"<b>Redirecciones:</b> "
            f"{'📋 Portapapeles ' if self.conn_data.get('rdp_clipboard', True) else ''}"
            f"{'💾 Discos Locales ' if self.conn_data.get('rdp_drives', False) else ''}"
            f"{'🔊 Audio ' if self.conn_data.get('rdp_audio', True) else ''}"
            f"{'🛡️ Consola /admin ' if self.conn_data.get('rdp_admin', False) else ''}"
            f"{'🔑 Auto-Login SSO (cmdkey)' if self.conn_data.get('rdp_sso', True) else ''}"
        )
        lbl_info = QLabel(resumen_html)
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 9.5pt; border: none; background: transparent;")
        c_lay.addWidget(lbl_info)

        # Botonera de control RDP estilo mRemoteNG
        row_btns = QHBoxLayout()
        row_btns.setSpacing(10)

        def _mk_btn(txt, bg, fn):
            b = QPushButton(txt)
            b.setFixedHeight(38)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {bg};
                    color: white;
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 0 14px;
                    border: none;
                }}
                QPushButton:hover {{ opacity: 0.9; }}
            """)
            b.clicked.connect(fn)
            return b

        row_btns.addWidget(_mk_btn("🚀 Reconectar Ventana RDP", self.colores['acento'], lambda: self.lanzar_cliente(fullscreen=False)))
        row_btns.addWidget(_mk_btn("📺 Pantalla Completa (/f)", "#0284C7", lambda: self.lanzar_cliente(fullscreen=True)))
        row_btns.addWidget(_mk_btn("🛡️ Sesión Admin (/admin)", "#7C3AED", lambda: self.lanzar_cliente(admin=True)))
        row_btns.addWidget(_mk_btn("📄 Exportar .rdp", "#059669", self.exportar_archivo_rdp))
        if platform.system() == "Windows":
            row_btns.addWidget(_mk_btn("🧹 Limpiar Credencial SSO", "#DC2626", self.limpiar_credencial_sso))
        c_lay.addLayout(row_btns)

        lay.addWidget(card)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 8px;
                padding: 10px;
                font-family: Consolas;
                font-size: 9.5pt;
            }}
        """)
        lay.addWidget(self.log_box, 1)

    def _log(self, msg: str):
        self.log_box.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _generar_contenido_rdp(self, fullscreen: bool = False) -> str:
        ip = self.conn_data.get("ip", "")
        port = self.conn_data.get("port", 3389)
        user = self.conn_data.get("user", "")
        domain = self.conn_data.get("domain", "")
        res = self.conn_data.get("resolution", "Smart Sizing (Ajustar)")

        width, height = 1280, 720
        screen_mode = 2 if (fullscreen or "Completa" in res) else 1
        if "x" in res:
            try:
                parts = res.split("x")
                width, height = int(parts[0].strip()), int(parts[1].strip())
            except Exception:
                pass

        lines = [
            f"full address:s:{ip}:{port}",
            f"screen mode id:i:{screen_mode}",
            f"desktopwidth:i:{width}",
            f"desktopheight:i:{height}",
            "session bpp:i:32",
            "smart sizing:i:1",
            "compression:i:1",
            "authentication level:i:2",
            "prompt for credentials:i:0",
            f"redirectclipboard:i:{1 if self.conn_data.get('rdp_clipboard', True) else 0}",
            f"redirectdrives:i:{1 if self.conn_data.get('rdp_drives', False) else 0}",
            f"audiomode:i:{0 if self.conn_data.get('rdp_audio', True) else 2}",
        ]
        if user:
            lines.append(f"username:s:{user}")
        if domain:
            lines.append(f"domain:s:{domain}")
        return "\n".join(lines)

    def lanzar_cliente(self, fullscreen: bool = False, admin: bool = False):
        proto = self.conn_data.get("proto", "RDP")
        ip = self.conn_data.get("ip", "").strip()
        port = int(self.conn_data.get("port", DEFAULT_PORTS.get(proto, 3389)) or 3389)
        user = self.conn_data.get("user", "").strip()
        pwd = self.conn_data.get("pass", "")
        domain = self.conn_data.get("domain", "").strip()

        if pwd:
            QGuiApplication.clipboard().setText(pwd)

        if proto == "VNC":
            self._log(f"Iniciando cliente VNC hacia {ip}:{port}...")
            for client in ["tvnviewer", "vncviewer"]:
                try:
                    subprocess.Popen([client, f"{ip}:{port}"])
                    self._log(f"Cliente {client} lanzado correctamente.")
                    return
                except Exception:
                    continue
            self._log("⚠️ No se detectó visor VNC externo (tvnviewer/vncviewer) en PATH. Clave copiada al portapapeles.")
            return

        # RDP con Single Sign-On vía cmdkey en Windows
        if platform.system() == "Windows":
            if self.conn_data.get("rdp_sso", True) and user and pwd:
                full_user = f"{domain}\\{user}" if domain else user
                for target in (f"TERMSRV/{ip}", f"TERMSRV/{ip}:{port}"):
                    subprocess.run(
                        ["cmdkey", f"/generic:{target}", f"/user:{full_user}", f"/pass:{pwd}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=0x08000000
                    )
                self._log(f"🔑 Credencial SSO inyectada en Windows Vault (TERMSRV/{ip}) para usuario '{full_user}'.")

            rdp_dir = get_data_path() / "rdp_profiles"
            rdp_dir.mkdir(parents=True, exist_ok=True)
            safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in self.conn_data.get("name", ip))
            rdp_file = rdp_dir / f"{safe_name}.rdp"
            rdp_file.write_text(self._generar_contenido_rdp(fullscreen=fullscreen), encoding="utf-8")

            args = ["mstsc.exe", str(rdp_file)]
            if admin or self.conn_data.get("rdp_admin", False):
                args.append("/admin")
            if fullscreen:
                args.append("/f")
            subprocess.Popen(args)
            self._log(f"🚀 Ejecutado: {' '.join(args)}")
        else:
            if callable(self.launch_cb):
                self.launch_cb(None, f"{ip}:{port}", admin, fullscreen)

    def exportar_archivo_rdp(self):
        nombre = self.conn_data.get("name", "servidor").replace(" ", "_")
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar perfil .rdp", f"{nombre}.rdp", "Remote Desktop (*.rdp)")
        if ruta:
            Path(ruta).write_text(self._generar_contenido_rdp(), encoding="utf-8")
            self._log(f"✅ Perfil .rdp exportado a: {ruta}")

    def limpiar_credencial_sso(self):
        ip = self.conn_data.get("ip", "").strip()
        port = self.conn_data.get("port", 3389)
        if platform.system() == "Windows" and ip:
            for target in (f"TERMSRV/{ip}", f"TERMSRV/{ip}:{port}"):
                subprocess.run(["cmdkey", f"/delete:{target}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
            self._log(f"🧹 Credenciales SSO eliminadas de Windows Credential Manager para {ip}.")

    def _iniciar_monitor_puerto(self):
        self._timer_mon = QTimer(self)
        self._timer_mon.timeout.connect(self._chequear_puerto)
        self._timer_mon.start(5000)
        self._chequear_puerto()

    def _chequear_puerto(self):
        ip = self.conn_data.get("ip", "").strip()
        port = int(self.conn_data.get("port", 3389) or 3389)

        def _probe():
            t0 = time.perf_counter()
            try:
                with socket.create_connection((ip, port), timeout=1.0):
                    ms = max(1, int((time.perf_counter() - t0) * 1000))
                    QTimer.singleShot(0, lambda: self.lbl_status.setText(f"🟢 Puerto TCP {port} Abierto y Activo ({ms} ms)"))
            except Exception:
                QTimer.singleShot(0, lambda: self.lbl_status.setText(f"🔴 Puerto TCP {port} sin respuesta directa en {ip}"))

        threading.Thread(target=_probe, daemon=True).start()

    def cerrar_sesion(self):
        if hasattr(self, "_timer_mon"):
            self._timer_mon.stop()


class MRemoteWebSession(QWidget):
    """Pestaña de administración web embebida (HTTP/HTTPS para Proxmox, Routers, Portainer, Grafana, Webmin)."""

    def __init__(self, parent, conn_data: dict, colores: dict):
        super().__init__(parent)
        self.conn_data = dict(conn_data)
        self.colores = colores
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        proto = self.conn_data.get("proto", "HTTPS").lower()
        ip = self.conn_data.get("ip", "localhost").strip()
        port = self.conn_data.get("port", 443 if proto == "https" else 80)
        if ip.startswith("http://") or ip.startswith("https://"):
            url = ip
        else:
            default_p = 443 if proto == "https" else 80
            url = f"{proto}://{ip}" if int(port) == default_p else f"{proto}://{ip}:{port}"

        nav = QFrame()
        nav.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 7px;")
        nav_lay = QHBoxLayout(nav)
        nav_lay.setContentsMargins(8, 4, 8, 4)
        nav_lay.setSpacing(6)

        self.txt_url = QLineEdit(url)
        self.txt_url.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 5px; padding: 4px 8px;")
        nav_lay.addWidget(self.txt_url, 1)

        btn_go = QPushButton("Ir / Recargar 🔄")
        btn_go.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 5px; padding: 4px 10px; font-weight: bold;")
        nav_lay.addWidget(btn_go)

        btn_ext = QPushButton("🌐 Abrir en Navegador")
        btn_ext.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 5px; padding: 4px 10px;")
        btn_ext.clicked.connect(lambda: subprocess.Popen(["cmd", "/c", "start", self.txt_url.text()] if platform.system() == "Windows" else ["xdg-open", self.txt_url.text()]))
        nav_lay.addWidget(btn_ext)

        lay.addWidget(nav)

        if WEBENGINE_AVAILABLE:
            self.web = QWebEngineView(self)
            self.web.load(QUrl(url))
            btn_go.clicked.connect(lambda: self.web.load(QUrl(self.txt_url.text())))
            self.txt_url.returnPressed.connect(lambda: self.web.load(QUrl(self.txt_url.text())))
            lay.addWidget(self.web, 1)
        else:
            lbl = QLabel(f"Panel Web listo en: <a href='{url}' style='color:{self.colores['acento']};'>{url}</a>")
            lbl.setOpenExternalLinks(True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(lbl, 1)

    def cerrar_sesion(self):
        pass


class TabRemote(QWidget):
    """
    Submódulo avanzado de Conexiones Remotas estilo mRemoteNG:
    - Árbol jerárquico con carpetas anidadas, Drag & Drop y herencia de credenciales
    - Barra superior Quick Connect + Escáner de puertos + Ping masivo + Import/Export (JSON, CSV, XML mRemoteNG)
    - Inspector de propiedades multi-categoría (General, Auth & Herencia, Pantalla/RDP/SSH)
    - Workspace multi-pestaña en vivo (SSH, Telnet, RDP con SSO cmdkey, VNC, HTTP/HTTPS, SFTP, FTP, WinRM, Raw)
    - Barra inferior Multi-Execution / Broadcast para enviar comandos a todas las terminales abiertas a la vez
    """

    def __init__(self, parent, colores, callbacks, context=None):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks or {}
        self.context = context

        if self.context and hasattr(self.context, "ruta_usuario") and self.context.ruta_usuario:
            self.archivo_datos = Path(self.context.ruta_usuario) / "conexiones_remotas.json"
        else:
            self.archivo_datos = get_data_path() / "conexiones_remotas.json"

        self._status_cache = {}  # ip -> {"online": bool, "latency_ms": int}
        self._updating_form = False
        self.inicializar_ui()

    # ──────────────────────────────────────────────────────────────────────────
    #  CONSTRUCCIÓN DE LA INTERFAZ ESTILO mRemoteNG
    # ──────────────────────────────────────────────────────────────────────────
    def inicializar_ui(self):
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(12, 10, 12, 10)
        self.layout_principal.setSpacing(8)

        # 1. Barra Superior mRemoteNG (Quick Connect + Herramientas Globales)
        self._build_top_quick_bar()

        # 2. Splitter Central: Izquierda (Árbol + Inspector Config) | Derecha (Workspace Multi-Pestaña + Broadcast)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background: rgba(255,255,255,0.06);
                width: 2px;
            }
        """)

        self._build_left_panel()
        self._build_right_workspace()

        self.splitter.addWidget(self.panel_izq)
        self.splitter.addWidget(self.panel_der_container)
        self.splitter.setSizes([340, 760])

        self.layout_principal.addWidget(self.splitter, 1)

        # Cargar árbol y poblar matriz inicial
        self.cargar_conexiones()
        self.actualizar_matriz_hosts()

    def _build_top_quick_bar(self):
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        t_lay = QHBoxLayout(top_bar)
        t_lay.setContentsMargins(12, 7, 12, 7)
        t_lay.setSpacing(8)

        lbl_qc = QLabel("⚡ Quick Connect:")
        lbl_qc.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_qc.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        t_lay.addWidget(lbl_qc)

        self.txt_quick_host = QLineEdit()
        self.txt_quick_host.setPlaceholderText("usuario@host:puerto o IP (ej. root@192.168.1.10 o 10.0.0.5)")
        self.txt_quick_host.setMinimumWidth(220)
        self.txt_quick_host.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 5px 10px;
            }}
            QLineEdit:focus {{ border: 1px solid {self.colores['acento']}; }}
        """)
        self.txt_quick_host.returnPressed.connect(self.conectar_rapido)
        t_lay.addWidget(self.txt_quick_host, 1)

        self.combo_quick_proto = QComboBox()
        self.combo_quick_proto.addItems(list(DEFAULT_PORTS.keys()))
        self.combo_quick_proto.setFixedWidth(95)
        self.combo_quick_proto.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 4px 8px;
                font-weight: bold;
            }}
            QComboBox QAbstractItemView {{
                background: {self.colores['bg_terciario']};
                color: white;
                selection-background-color: {self.colores['acento']};
            }}
        """)
        self.combo_quick_proto.currentTextChanged.connect(
            lambda p: self.spin_quick_port.setValue(DEFAULT_PORTS.get(p, 22))
        )
        t_lay.addWidget(self.combo_quick_proto)

        self.spin_quick_port = QSpinBox()
        self.spin_quick_port.setRange(1, 65535)
        self.spin_quick_port.setValue(22)
        self.spin_quick_port.setPrefix(":")
        self.spin_quick_port.setFixedWidth(78)
        self.spin_quick_port.setStyleSheet(self.txt_quick_host.styleSheet())
        t_lay.addWidget(self.spin_quick_port)

        btn_qc_go = QPushButton("🚀 Conectar")
        btn_qc_go.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_qc_go.setFixedHeight(30)
        btn_qc_go.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 12px;
                border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_qc_go.clicked.connect(self.conectar_rapido)
        t_lay.addWidget(btn_qc_go)

        btn_tool_style = f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 0 10px;
                font-size: 8.5pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {self.colores['acento']}44;
                border: 1px solid {self.colores['acento']};
            }}
        """

        btn_ping_all = QPushButton("📡 Ping Todos")
        btn_ping_all.setFixedHeight(30)
        btn_ping_all.setToolTip("Comprobar estado Online/Offline y latencia de todos los servidores guardados")
        btn_ping_all.setStyleSheet(btn_tool_style)
        btn_ping_all.clicked.connect(self.ping_todos_los_hosts)
        t_lay.addWidget(btn_ping_all)

        btn_import = QPushButton("📥 Importar")
        btn_import.setFixedHeight(30)
        btn_import.setToolTip("Importar conexiones desde mRemoteNG XML (confCons.xml), JSON o CSV")
        btn_import.setStyleSheet(btn_tool_style)
        btn_import.clicked.connect(self.importar_conexiones_dialogo)
        t_lay.addWidget(btn_import)

        btn_export = QPushButton("📤 Exportar")
        btn_export.setFixedHeight(30)
        btn_export.setToolTip("Exportar árbol de conexiones a mRemoteNG XML, JSON o CSV")
        btn_export.setStyleSheet(btn_tool_style)
        btn_export.clicked.connect(self.exportar_conexiones_dialogo)
        t_lay.addWidget(btn_export)

        self.layout_principal.addWidget(top_bar)

    def _build_left_panel(self):
        self.panel_izq = QFrame()
        self.panel_izq.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        layout_izq = QVBoxLayout(self.panel_izq)
        layout_izq.setContentsMargins(10, 10, 10, 10)
        layout_izq.setSpacing(8)

        # Splitter vertical izquierdo: Arriba = Árbol de Conexiones | Abajo = Inspector Config mRemoteNG
        self.left_vsplitter = QSplitter(Qt.Orientation.Vertical)
        self.left_vsplitter.setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.08); height: 2px; }")

        # ── Parte Superior Izquierda: Explorador de Conexiones ──
        tree_container = QWidget()
        tree_lay = QVBoxLayout(tree_container)
        tree_lay.setContentsMargins(0, 0, 0, 4)
        tree_lay.setSpacing(6)

        hdr_lay = QHBoxLayout()
        lbl_titulo_izq = QLabel("🖧 CONEXIONES & CARPETAS")
        lbl_titulo_izq.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_titulo_izq.setStyleSheet(f"color: {self.colores['fg_secundario']}; letter-spacing: 1px; border: none;")
        hdr_lay.addWidget(lbl_titulo_izq)
        hdr_lay.addStretch()

        btn_mini_style = f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 5px;
                padding: 2px 7px;
                font-size: 8pt;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {self.colores['acento']}; }}
        """
        btn_add_folder = QPushButton("📂+ Carpeta")
        btn_add_folder.setToolTip("Crear nueva carpeta/contenedor (soporta herencia de credenciales)")
        btn_add_folder.setStyleSheet(btn_mini_style)
        btn_add_folder.clicked.connect(self.nueva_carpeta)
        hdr_lay.addWidget(btn_add_folder)

        btn_add_host = QPushButton("➕ Host")
        btn_add_host.setToolTip("Crear nueva conexión remota")
        btn_add_host.setStyleSheet(btn_mini_style)
        btn_add_host.clicked.connect(self.nueva_conexion)
        hdr_lay.addWidget(btn_add_host)

        btn_del_node = QPushButton("🗑️")
        btn_del_node.setToolTip("Eliminar conexión o carpeta seleccionada")
        btn_del_node.setStyleSheet(btn_mini_style.replace(self.colores['acento'], self.colores.get('error', '#E53935')))
        btn_del_node.clicked.connect(self.eliminar_conexion)
        hdr_lay.addWidget(btn_del_node)

        tree_lay.addLayout(hdr_lay)

        # Buscador / Filtro del árbol
        self.txt_filtro_arbol = QLineEdit()
        self.txt_filtro_arbol.setPlaceholderText("🔍 Filtrar por nombre, IP, protocolo o etiqueta...")
        self.txt_filtro_arbol.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 8.5pt;
            }}
        """)
        self.txt_filtro_arbol.textChanged.connect(self._filtrar_arbol)
        tree_lay.addWidget(self.txt_filtro_arbol)

        self.arbol_conexiones = QTreeWidget()
        self.arbol_conexiones.setHeaderHidden(True)
        self.arbol_conexiones.setDragEnabled(True)
        self.arbol_conexiones.setAcceptDrops(True)
        self.arbol_conexiones.setDropIndicatorShown(True)
        self.arbol_conexiones.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.arbol_conexiones.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.arbol_conexiones.customContextMenuRequested.connect(self._mostrar_menu_contextual_arbol)
        self.arbol_conexiones.itemClicked.connect(self.cargar_datos)
        self.arbol_conexiones.itemDoubleClicked.connect(self._on_tree_double_clicked)
        self.arbol_conexiones.setStyleSheet(f"""
            QTreeWidget {{
                background: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 7px;
                outline: none;
                padding: 4px;
                font-size: 9pt;
            }}
            QTreeWidget::item {{
                padding: 5px 8px;
                border-radius: 4px;
            }}
            QTreeWidget::item:hover {{
                background: rgba(255,255,255,0.06);
            }}
            QTreeWidget::item:selected {{
                background: {self.colores['acento']}33;
                color: white;
                border-left: 2px solid {self.colores['acento']};
            }}
        """)
        tree_lay.addWidget(self.arbol_conexiones, 1)
        self.left_vsplitter.addWidget(tree_container)

        # ── Parte Inferior Izquierda: Inspector Config mRemoteNG ──
        config_container = QWidget()
        cfg_lay = QVBoxLayout(config_container)
        cfg_lay.setContentsMargins(0, 4, 0, 0)
        cfg_lay.setSpacing(6)

        lbl_cfg = QLabel("⚙️ PROPIEDADES & CONFIGURACIÓN (mRemoteNG Inspector)")
        lbl_cfg.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_cfg.setStyleSheet(f"color: {self.colores['fg_secundario']}; letter-spacing: 0.8px; border: none;")
        cfg_lay.addWidget(lbl_cfg)

        self.tabs_inspector = QTabWidget()
        self.tabs_inspector.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {self.colores['bg_terciario']};
                border-radius: 7px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
            QTabBar::tab {{
                background: {self.colores['bg_principal']};
                color: {self.colores['fg_secundario']};
                padding: 5px 10px;
                font-size: 8pt;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['bg_terciario']};
                color: {self.colores['acento']};
                font-weight: bold;
            }}
        """)

        estilo_input = f"""
            QLineEdit, QComboBox, QSpinBox {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.09);
                border-radius: 5px;
                padding: 4px 8px;
                min-height: 22px;
                font-size: 8.5pt;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border: 1px solid {self.colores['acento']};
            }}
            QComboBox QAbstractItemView {{
                background: {self.colores['bg_secundario']};
                color: white;
                selection-background-color: {self.colores['acento']};
            }}
        """
        estilo_lbl = f"color: {self.colores['fg_secundario']}; font-size: 8.5pt; font-weight: bold; border: none;"

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet(estilo_lbl)
            return l

        # Tab 1: General & Destino
        tab_gen = QWidget()
        f_gen = QFormLayout(tab_gen)
        f_gen.setContentsMargins(10, 8, 10, 8)
        f_gen.setSpacing(6)

        self.txt_nombre = QLineEdit()
        self.txt_nombre.setStyleSheet(estilo_input)

        lay_ip = QHBoxLayout()
        lay_ip.setContentsMargins(0, 0, 0, 0)
        lay_ip.setSpacing(5)
        self.txt_ip = QLineEdit()
        self.txt_ip.setPlaceholderText("IP o dominio (ej. 192.168.1.50)")
        self.txt_ip.setStyleSheet(estilo_input)
        self.txt_ip.textChanged.connect(self._iniciar_chequeo_ping)
        self.lbl_estado = QLabel("⚫")
        self.lbl_estado.setToolTip("Indicador de respuesta Ping / Puerto TCP en tiempo real")
        self.lbl_estado.setStyleSheet("font-size: 13px; border: none; background: transparent;")
        lay_ip.addWidget(self.txt_ip, 1)
        lay_ip.addWidget(self.lbl_estado)

        lay_proto_port = QHBoxLayout()
        lay_proto_port.setContentsMargins(0, 0, 0, 0)
        lay_proto_port.setSpacing(6)
        self.combo_proto = QComboBox()
        self.combo_proto.addItems(list(DEFAULT_PORTS.keys()))
        self.combo_proto.setStyleSheet(estilo_input)
        self.combo_proto.currentTextChanged.connect(self._on_proto_changed)

        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(22)
        self.spin_port.setStyleSheet(estilo_input)
        lay_proto_port.addWidget(self.combo_proto, 1)
        lay_proto_port.addWidget(_lbl("Puerto:"))
        lay_proto_port.addWidget(self.spin_port)

        self.combo_tag = QComboBox()
        self.combo_tag.addItems(["Producción", "Desarrollo", "Staging", "Laboratorio", "Crítico", "General"])
        self.combo_tag.setStyleSheet(estilo_input)

        self.txt_notas = QLineEdit()
        self.txt_notas.setPlaceholderText("Descripción, SO o notas del servidor...")
        self.txt_notas.setStyleSheet(estilo_input)

        f_gen.addRow(_lbl("Nombre:"), self.txt_nombre)
        f_gen.addRow(_lbl("Host / IP:"), lay_ip)
        f_gen.addRow(_lbl("Protocolo:"), lay_proto_port)
        f_gen.addRow(_lbl("Entorno:"), self.combo_tag)
        f_gen.addRow(_lbl("Notas:"), self.txt_notas)
        self.tabs_inspector.addTab(tab_gen, "🌐 Conexión")

        # Tab 2: Autenticación & Herencia
        tab_auth = QWidget()
        f_auth = QFormLayout(tab_auth)
        f_auth.setContentsMargins(10, 8, 10, 8)
        f_auth.setSpacing(6)

        self.chk_heredar_auth = QCheckBox("🔗 Heredar credenciales de la carpeta padre")
        self.chk_heredar_auth.setStyleSheet("color: #60A5FA; font-size: 8.5pt; font-weight: bold;")
        f_auth.addRow(self.chk_heredar_auth)

        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("root / administrator / ubuntu")
        self.txt_usuario.setStyleSheet(estilo_input)

        lay_pass = QHBoxLayout()
        lay_pass.setContentsMargins(0, 0, 0, 0)
        lay_pass.setSpacing(4)
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("Auto-inyección SSH y SSO en RDP")
        self.txt_pass.setStyleSheet(estilo_input)

        btn_eye = QPushButton("👁️")
        btn_eye.setFixedSize(26, 26)
        btn_eye.setToolTip("Mostrar / Ocultar contraseña")
        btn_eye.setStyleSheet(btn_mini_style)
        btn_eye.clicked.connect(
            lambda: self.txt_pass.setEchoMode(
                QLineEdit.EchoMode.Normal if self.txt_pass.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password
            )
        )
        lay_pass.addWidget(self.txt_pass, 1)
        lay_pass.addWidget(btn_eye)

        self.txt_dominio = QLineEdit()
        self.txt_dominio.setPlaceholderText("Opcional (ej. WORKGROUP o CORP)")
        self.txt_dominio.setStyleSheet(estilo_input)

        lay_key = QHBoxLayout()
        lay_key.setContentsMargins(0, 0, 0, 0)
        lay_key.setSpacing(4)
        self.txt_ssh_key = QLineEdit()
        self.txt_ssh_key.setPlaceholderText("Ruta a clave privada (.pem / id_rsa)")
        self.txt_ssh_key.setStyleSheet(estilo_input)
        btn_key = QPushButton("📂")
        btn_key.setFixedSize(26, 26)
        btn_key.setStyleSheet(btn_mini_style)
        btn_key.clicked.connect(self._seleccionar_clave_ssh)
        lay_key.addWidget(self.txt_ssh_key, 1)
        lay_key.addWidget(btn_key)

        f_auth.addRow(_lbl("Usuario:"), self.txt_usuario)
        f_auth.addRow(_lbl("Clave:"), lay_pass)
        f_auth.addRow(_lbl("Dominio:"), self.txt_dominio)
        f_auth.addRow(_lbl("SSH Key:"), lay_key)
        self.tabs_inspector.addTab(tab_auth, "🔐 Auth")

        # Tab 3: Pantalla, Recursos RDP y Avanzado SSH
        tab_adv = QWidget()
        f_adv = QFormLayout(tab_adv)
        f_adv.setContentsMargins(10, 8, 10, 8)
        f_adv.setSpacing(5)

        self.combo_resolucion = QComboBox()
        self.combo_resolucion.addItems(["Smart Sizing (Ajustar)", "Pantalla Completa (/f)", "1920x1080", "1600x900", "1366x768", "1280x720"])
        self.combo_resolucion.setStyleSheet(estilo_input)

        lay_theme_font = QHBoxLayout()
        lay_theme_font.setContentsMargins(0, 0, 0, 0)
        lay_theme_font.setSpacing(5)
        self.combo_tema_term = QComboBox()
        self.combo_tema_term.addItems(list(TERMINAL_THEMES.keys()))
        self.combo_tema_term.setStyleSheet(estilo_input)

        self.spin_font = QSpinBox()
        self.spin_font.setRange(8, 36)
        self.spin_font.setValue(12)
        self.spin_font.setSuffix(" pt")
        self.spin_font.setStyleSheet(estilo_input)
        lay_theme_font.addWidget(self.combo_tema_term, 1)
        lay_theme_font.addWidget(self.spin_font)

        self.txt_ssh_tunnel = QLineEdit()
        self.txt_ssh_tunnel.setPlaceholderText("Ej: -L 8080:127.0.0.1:80")
        self.txt_ssh_tunnel.setStyleSheet(estilo_input)

        self.txt_post_cmd = QLineEdit()
        self.txt_post_cmd.setPlaceholderText("Comando auto-ejecutado al conectar (ej. htop)")
        self.txt_post_cmd.setStyleSheet(estilo_input)

        chk_row1 = QHBoxLayout()
        self.chk_rdp_sso = QCheckBox("🔑 SSO")
        self.chk_rdp_sso.setChecked(True)
        self.chk_rdp_sso.setToolTip("Inyectar credenciales automáticamente en Windows (cmdkey) para no pedir clave en RDP")
        self.chk_rdp_admin = QCheckBox("🛡️ /admin")
        self.chk_rdp_clipboard = QCheckBox("📋 Portapapeles")
        self.chk_rdp_clipboard.setChecked(True)
        self.chk_rdp_drives = QCheckBox("💾 Discos")
        self.chk_rdp_audio = QCheckBox("🔊 Audio")
        self.chk_rdp_audio.setChecked(True)
        for c in (self.chk_rdp_sso, self.chk_rdp_admin, self.chk_rdp_clipboard, self.chk_rdp_drives):
            c.setStyleSheet("color: #D1D5DB; font-size: 8pt;")
            chk_row1.addWidget(c)

        f_adv.addRow(_lbl("Resolución:"), self.combo_resolucion)
        f_adv.addRow(_lbl("Consola:"), lay_theme_font)
        f_adv.addRow(_lbl("Túnel SSH:"), self.txt_ssh_tunnel)
        f_adv.addRow(_lbl("Post-Cmd:"), self.txt_post_cmd)
        f_adv.addRow(_lbl("Opciones RDP:"), chk_row1)
        self.tabs_inspector.addTab(tab_adv, "🖥️ Recursos")

        cfg_lay.addWidget(self.tabs_inspector)

        # Botones de acción del Inspector
        btn_accion_layout = QHBoxLayout()
        btn_accion_layout.setSpacing(6)

        self.btn_guardar = QPushButton("💾 Guardar")
        self.btn_guardar.setFixedHeight(32)
        self.btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guardar.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('exito', '#22c55e')};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                border: none;
                font-size: 9pt;
            }}
            QPushButton:hover {{ background: #16a34a; }}
        """)
        self.btn_guardar.clicked.connect(self.guardar_perfil)

        self.btn_conectar = QPushButton("🚀 Conectar (Pestaña)")
        self.btn_conectar.setFixedHeight(32)
        self.btn_conectar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_conectar.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                border: none;
                font-size: 9pt;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        self.btn_conectar.clicked.connect(self.conectar)

        self.btn_conectar_ext = QPushButton("🪟 Nativa")
        self.btn_conectar_ext.setFixedHeight(32)
        self.btn_conectar_ext.setToolTip("Abrir en ventana externa nativa del sistema operativo")
        self.btn_conectar_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_conectar_ext.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.1);
                padding: 0 10px;
                font-size: 8.5pt;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.12); }}
        """)
        self.btn_conectar_ext.clicked.connect(lambda: self.conectar(forzar_externa=True))

        btn_accion_layout.addWidget(self.btn_guardar)
        btn_accion_layout.addWidget(self.btn_conectar, 1)
        btn_accion_layout.addWidget(self.btn_conectar_ext)
        cfg_lay.addLayout(btn_accion_layout)

        self.left_vsplitter.addWidget(config_container)
        self.left_vsplitter.setSizes([310, 270])
        layout_izq.addWidget(self.left_vsplitter)

    def _build_right_workspace(self):
        self.panel_der_container = QFrame()
        self.panel_der_container.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        r_lay = QVBoxLayout(self.panel_der_container)
        r_lay.setContentsMargins(10, 10, 10, 10)
        r_lay.setSpacing(8)

        # QTabWidget de sesiones en vivo (estilo mRemoteNG Connections Workspace)
        self.tabs_sesiones = QTabWidget()
        self.tabs_sesiones.setTabsClosable(True)
        self.tabs_sesiones.setMovable(True)
        self.tabs_sesiones.tabCloseRequested.connect(self._cerrar_pestana_sesion)
        self.tabs_sesiones.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {self.colores['bg_principal']};
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
            QTabBar::tab {{
                background: {self.colores['bg_terciario']};
                color: {self.colores['fg_secundario']};
                padding: 7px 14px;
                font-size: 9pt;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 3px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['bg_principal']};
                color: {self.colores['acento']};
                font-weight: bold;
                border-top: 2px solid {self.colores['acento']};
            }}
        """)

        # Pestaña Fija 0: Centro de Control mRemoteNG (Matriz de Hosts + Escáner de Puertos)
        self._build_dashboard_tab()
        self.tabs_sesiones.addTab(self.tab_dashboard_mremote, "📊 Centro mRemoteNG & Escáner")
        # Ocultar botón de cerrar en la pestaña fija 0
        self.tabs_sesiones.tabBar().setTabButton(0, self.tabs_sesiones.tabBar().ButtonPosition.RightSide, None)

        r_lay.addWidget(self.tabs_sesiones, 1)

        # Barra Inferior Multi-SSH Broadcast (Enviar comando a todas las terminales abiertas)
        bcast_frame = QFrame()
        bcast_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.07);
            }}
        """)
        b_lay = QHBoxLayout(bcast_frame)
        b_lay.setContentsMargins(10, 5, 10, 5)
        b_lay.setSpacing(8)

        lbl_bcast = QLabel("📡 Multi-SSH Broadcast:")
        lbl_bcast.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_bcast.setStyleSheet("color: #FBBF24; border: none; background: transparent;")
        b_lay.addWidget(lbl_bcast)

        self.txt_broadcast = QLineEdit()
        self.txt_broadcast.setPlaceholderText("Escribe un comando para enviarlo simultáneamente a TODAS las pestañas de terminal activas...")
        self.txt_broadcast.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 5px;
                padding: 4px 10px;
                font-family: Consolas;
                font-size: 9pt;
            }}
        """)
        self.txt_broadcast.returnPressed.connect(self.enviar_broadcast_terminales)
        b_lay.addWidget(self.txt_broadcast, 1)

        btn_bcast = QPushButton("⚡ Enviar a Todas")
        btn_bcast.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_bcast.setStyleSheet("""
            QPushButton {
                background: #D97706;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px 12px;
                border: none;
                font-size: 8.5pt;
            }
            QPushButton:hover { background: #B45309; }
        """)
        btn_bcast.clicked.connect(self.enviar_broadcast_terminales)
        b_lay.addWidget(btn_bcast)

        r_lay.addWidget(bcast_frame)

    def _build_dashboard_tab(self):
        self.tab_dashboard_mremote = QWidget()
        d_lay = QVBoxLayout(self.tab_dashboard_mremote)
        d_lay.setContentsMargins(14, 14, 14, 14)
        d_lay.setSpacing(12)

        # Fila de KPIs
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)

        def _mk_kpi(titulo, valor, color):
            f = QFrame()
            f.setStyleSheet(f"""
                QFrame {{
                    background: {self.colores['bg_secundario']};
                    border-radius: 8px;
                    border: 1px solid rgba(255,255,255,0.06);
                }}
            """)
            fl = QVBoxLayout(f)
            fl.setContentsMargins(12, 8, 12, 8)
            fl.setSpacing(2)
            lt = QLabel(titulo)
            lt.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 8pt; font-weight: bold; border: none;")
            lv = QLabel(valor)
            lv.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            lv.setStyleSheet(f"color: {color}; border: none;")
            fl.addWidget(lt)
            fl.addWidget(lv)
            return f, lv

        card1, self.lbl_kpi_total = _mk_kpi("🖥️ SERVIDORES GUARDADOS", "0", self.colores['acento'])
        card2, self.lbl_kpi_folders = _mk_kpi("📂 CARPETAS / GRUPOS", "0", "#60A5FA")
        card3, self.lbl_kpi_online = _mk_kpi("🟢 HOSTS EN LÍNEA", "0", "#34D399")
        card4, self.lbl_kpi_sessions = _mk_kpi("⚡ SESIONES ACTIVAS", "0", "#FBBF24")

        for c in (card1, card2, card3, card4):
            kpi_row.addWidget(c, 1)
        d_lay.addLayout(kpi_row)

        # Tabla de Matriz de Servidores Guardados
        lbl_m = QLabel("📋 MATRIZ DE CONEXIONES & MONITOREO RÁPIDO (Doble clic en cualquier fila para conectar)")
        lbl_m.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_m.setStyleSheet(f"color: {self.colores['fg_secundario']}; letter-spacing: 0.8px;")
        d_lay.addWidget(lbl_m)

        self.table_hosts = QTableWidget(0, 7)
        self.table_hosts.setHorizontalHeaderLabels(["Estado", "Nombre", "Carpeta", "Protocolo", "Host : Puerto", "Usuario", "Entorno / Notas"])
        self.table_hosts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_hosts.verticalHeader().setVisible(False)
        self.table_hosts.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_hosts.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_hosts.setStyleSheet(f"""
            QTableWidget {{
                background: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
                gridline-color: rgba(255,255,255,0.04);
                font-size: 9pt;
            }}
            QHeaderView::section {{
                background: {self.colores['bg_terciario']};
                color: {self.colores['fg_secundario']};
                padding: 6px;
                border: none;
                font-weight: bold;
                font-size: 8.5pt;
            }}
        """)
        self.table_hosts.cellDoubleClicked.connect(self._on_matrix_double_clicked)
        d_lay.addWidget(self.table_hosts, 1)

        # Escáner de Puertos y Descubrimiento de Servicios Remotos (Port Scanner mRemoteNG)
        scan_box = QFrame()
        scan_box.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        s_lay = QVBoxLayout(scan_box)
        s_lay.setContentsMargins(12, 10, 12, 10)
        s_lay.setSpacing(8)

        s_top = QHBoxLayout()
        lbl_sc = QLabel("🔍 ESCÁNER DE PUERTOS DE ADMINISTRACIÓN REMOTA (SSH, RDP, HTTP/S, VNC, WinRM, DB)")
        lbl_sc.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_sc.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        s_top.addWidget(lbl_sc)
        s_top.addStretch()

        self.txt_scan_host = QLineEdit()
        self.txt_scan_host.setPlaceholderText("IP o Host a escanear (ej. 127.0.0.1)")
        self.txt_scan_host.setFixedWidth(200)
        self.txt_scan_host.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 5px; padding: 4px 8px;")
        s_top.addWidget(self.txt_scan_host)

        self.btn_scan_ports = QPushButton("🔍 Escanear Puertos")
        self.btn_scan_ports.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan_ports.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px 12px;
                border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        self.btn_scan_ports.clicked.connect(self.ejecutar_escaneo_puertos_ui)
        s_top.addWidget(self.btn_scan_ports)
        s_lay.addLayout(s_top)

        self.lbl_scan_results = QLabel("Selecciona un servidor o escribe una IP y pulsa 'Escanear Puertos' para detectar servicios activos.")
        self.lbl_scan_results.setWordWrap(True)
        self.lbl_scan_results.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 9pt; border: none;")
        s_lay.addWidget(self.lbl_scan_results)

        d_lay.addWidget(scan_box)

    # ──────────────────────────────────────────────────────────────────────────
    #  GESTIÓN JERÁRQUICA DEL ÁRBOL, CARPETAS Y HERENCIA (mRemoteNG Tree)
    # ──────────────────────────────────────────────────────────────────────────
    def cargar_conexiones(self):
        self.arbol_conexiones.clear()
        self.raiz = QTreeWidgetItem(self.arbol_conexiones, ["🖧 Conexiones mRemoteNG"])
        self.raiz.setData(0, Qt.ItemDataRole.UserRole, {"type": "root", "name": "Conexiones mRemoteNG"})
        self.raiz.setExpanded(True)

        conexiones = []
        if self.archivo_datos.exists():
            try:
                with open(self.archivo_datos, "r", encoding="utf-8") as f:
                    conexiones = json.load(f)
            except Exception:
                conexiones = []

        if not conexiones:
            conexiones = [
                {
                    "type": "folder",
                    "name": "Servidores Producción",
                    "user": "root",
                    "pass": "",
                    "domain": "",
                    "children": [
                        {"type": "connection", "name": "Gateway SSH Local", "ip": "127.0.0.1", "port": 22, "user": "admin", "proto": "SSH", "tag": "Producción", "inherit_auth": False},
                        {"type": "connection", "name": "Escritorio RDP Local", "ip": "127.0.0.1", "port": 3389, "user": "Administrador", "proto": "RDP", "tag": "Producción", "inherit_auth": False},
                    ]
                },
                {
                    "type": "connection",
                    "name": "Localhost Test",
                    "ip": "127.0.0.1",
                    "port": 22,
                    "user": "admin",
                    "proto": "SSH",
                    "tag": "Desarrollo",
                }
            ]

        self._poblar_nodos_recursivo(self.raiz, conexiones)
        self.raiz.setExpanded(True)
        self.actualizar_vista_vacia()

    def _poblar_nodos_recursivo(self, parent_item: QTreeWidgetItem, lista_nodos: list):
        for data in lista_nodos:
            if not isinstance(data, dict):
                continue
            node_type = data.get("type", "folder" if "children" in data else "connection")
            if node_type == "folder":
                folder_data = {
                    "type": "folder",
                    "name": data.get("name", "Carpeta"),
                    "user": data.get("user", ""),
                    "pass": data.get("pass", ""),
                    "domain": data.get("domain", ""),
                    "ssh_key": data.get("ssh_key", ""),
                    "notes": data.get("notes", ""),
                }
                item = QTreeWidgetItem(parent_item, [f"📁 {folder_data['name']}"])
                item.setData(0, Qt.ItemDataRole.UserRole, folder_data)
                item.setExpanded(True)
                self._poblar_nodos_recursivo(item, data.get("children", []))
            else:
                proto = data.get("proto", "SSH")
                data.setdefault("type", "connection")
                data.setdefault("port", DEFAULT_PORTS.get(proto, 22))
                item = QTreeWidgetItem(parent_item)
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                self._actualizar_etiqueta_item_arbol(item)

    def _actualizar_etiqueta_item_arbol(self, item: QTreeWidgetItem):
        if not item or item == self.raiz:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if data.get("type") == "folder":
            item.setText(0, f"📁 {data.get('name', 'Carpeta')}")
            return

        proto = data.get("proto", "SSH")
        icon = PROTO_ICONS.get(proto, "🖧")
        name = data.get("name", "Host")
        ip = data.get("ip", "")
        st = self._status_cache.get(ip)
        if st is None:
            dot = "⚪"
            lat = ""
        elif st.get("online"):
            dot = "🟢"
            lat = f" ({st.get('latency_ms', 1)}ms)" if st.get("latency_ms") else ""
        else:
            dot = "🔴"
            lat = ""
        item.setText(0, f"{dot} {icon} [{proto}] {name}{lat}")

    def _serializar_nodos_recursivo(self, parent_item: QTreeWidgetItem) -> list:
        resultado = []
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            data = dict(child.data(0, Qt.ItemDataRole.UserRole) or {})
            if data.get("type") == "folder" or child.childCount() > 0 and not data.get("ip"):
                data["type"] = "folder"
                data["children"] = self._serializar_nodos_recursivo(child)
            else:
                data["type"] = "connection"
            resultado.append(data)
        return resultado

    def guardar_todas_las_conexiones(self):
        if not hasattr(self, "raiz"):
            return
        data = self._serializar_nodos_recursivo(self.raiz)
        try:
            self.archivo_datos.parent.mkdir(parents=True, exist_ok=True)
            with open(self.archivo_datos, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
        self.actualizar_matriz_hosts()

    def obtener_todas_las_conexiones_planas(self) -> list[tuple[QTreeWidgetItem, dict, str]]:
        """Retorna una lista de tuplas (QTreeWidgetItem, datos_resueltos, nombre_carpeta)."""
        lista = []
        if not hasattr(self, "raiz"):
            return lista

        def _walk(node: QTreeWidgetItem, folder_name: str):
            for i in range(node.childCount()):
                ch = node.child(i)
                d = ch.data(0, Qt.ItemDataRole.UserRole) or {}
                if d.get("type") == "folder":
                    _walk(ch, d.get("name", "Carpeta"))
                else:
                    eff = self.resolver_credenciales_efectivas(ch)
                    lista.append((ch, eff, folder_name))

        _walk(self.raiz, "Raíz")
        return lista

    def resolver_credenciales_efectivas(self, item: QTreeWidgetItem) -> dict:
        """Resuelve la herencia de credenciales estilo mRemoteNG desde las carpetas padre si inherit_auth está activo."""
        if not item:
            return {}
        data = dict(item.data(0, Qt.ItemDataRole.UserRole) or {})
        if not data.get("inherit_auth", False):
            return data

        curr = item.parent()
        while curr and curr != self.raiz:
            p_data = curr.data(0, Qt.ItemDataRole.UserRole) or {}
            if not data.get("user") and p_data.get("user"):
                data["user"] = p_data["user"]
            if not data.get("pass") and p_data.get("pass"):
                data["pass"] = p_data["pass"]
            if not data.get("domain") and p_data.get("domain"):
                data["domain"] = p_data["domain"]
            if not data.get("ssh_key") and p_data.get("ssh_key"):
                data["ssh_key"] = p_data["ssh_key"]
            curr = curr.parent()
        return data

    # ──────────────────────────────────────────────────────────────────────────
    #  OPERACIONES CRUD EN ÁRBOL E INSPECTOR
    # ──────────────────────────────────────────────────────────────────────────
    def _obtener_contenedor_destino(self) -> QTreeWidgetItem:
        sel = self.arbol_conexiones.currentItem()
        if not sel or sel == self.raiz:
            return self.raiz
        data = sel.data(0, Qt.ItemDataRole.UserRole) or {}
        if data.get("type") == "folder":
            return sel
        return sel.parent() or self.raiz

    def nueva_carpeta(self):
        parent_node = self._obtener_contenedor_destino()
        folder_data = {
            "type": "folder",
            "name": "Nueva Carpeta",
            "user": "",
            "pass": "",
            "domain": "",
            "ssh_key": "",
            "notes": "Contenedor con herencia de credenciales",
        }
        item = QTreeWidgetItem(parent_node, ["📁 Nueva Carpeta"])
        item.setData(0, Qt.ItemDataRole.UserRole, folder_data)
        parent_node.setExpanded(True)
        self.arbol_conexiones.setCurrentItem(item)
        self.cargar_datos(item)
        self.guardar_todas_las_conexiones()

    def nueva_conexion(self):
        parent_node = self._obtener_contenedor_destino()
        conn_data = {
            "type": "connection",
            "name": "Nueva Conexión",
            "ip": "",
            "port": 22,
            "user": "",
            "pass": "",
            "domain": "",
            "proto": "SSH",
            "font": 12,
            "theme": "Matrix Green",
            "tag": "Producción",
            "resolution": "Smart Sizing (Ajustar)",
            "inherit_auth": parent_node != self.raiz,
            "rdp_sso": True,
            "rdp_admin": False,
            "rdp_clipboard": True,
            "rdp_drives": False,
            "rdp_audio": True,
        }
        item = QTreeWidgetItem(parent_node)
        item.setData(0, Qt.ItemDataRole.UserRole, conn_data)
        self._actualizar_etiqueta_item_arbol(item)
        parent_node.setExpanded(True)
        self.arbol_conexiones.setCurrentItem(item)
        self.cargar_datos(item)
        self.guardar_todas_las_conexiones()
        self.txt_nombre.setFocus()
        self.txt_nombre.selectAll()

    def duplicar_conexion_seleccionada(self):
        item = self.arbol_conexiones.currentItem()
        if not item or item == self.raiz:
            return
        orig = dict(item.data(0, Qt.ItemDataRole.UserRole) or {})
        if orig.get("type") == "folder":
            return
        orig["name"] = f"{orig.get('name', 'Host')} (Copia)"
        parent = item.parent() or self.raiz
        nuevo = QTreeWidgetItem(parent)
        nuevo.setData(0, Qt.ItemDataRole.UserRole, orig)
        self._actualizar_etiqueta_item_arbol(nuevo)
        self.arbol_conexiones.setCurrentItem(nuevo)
        self.cargar_datos(nuevo)
        self.guardar_todas_las_conexiones()

    def eliminar_conexion(self):
        item = self.arbol_conexiones.currentItem()
        if item and item != self.raiz:
            parent = item.parent() or self.raiz
            parent.removeChild(item)
            self.guardar_todas_las_conexiones()
            self.txt_nombre.clear()
            self.txt_ip.clear()
            self.txt_usuario.clear()
            self.txt_pass.clear()
            self.actualizar_vista_vacia()

    def cargar_datos(self, item: QTreeWidgetItem):
        if not item or item == self.raiz:
            return
        self._updating_form = True
        try:
            data = item.data(0, Qt.ItemDataRole.UserRole) or {}
            is_folder = data.get("type") == "folder"
            self.txt_nombre.setText(data.get("name", ""))
            self.txt_ip.setText(data.get("ip", ""))
            self.txt_ip.setEnabled(not is_folder)
            self.txt_usuario.setText(data.get("user", ""))
            self.txt_pass.setText(data.get("pass", ""))
            self.txt_dominio.setText(data.get("domain", ""))
            self.txt_ssh_key.setText(data.get("ssh_key", ""))
            self.txt_notas.setText(data.get("notes", ""))

            proto = data.get("proto", "SSH")
            self.combo_proto.setCurrentText(proto)
            self.spin_port.setValue(int(data.get("port", DEFAULT_PORTS.get(proto, 22)) or 22))
            self.spin_font.setValue(int(data.get("font", 12) or 12))
            self.combo_tag.setCurrentText(data.get("tag", "Producción"))
            self.combo_resolucion.setCurrentText(data.get("resolution", "Smart Sizing (Ajustar)"))
            self.combo_tema_term.setCurrentText(data.get("theme", "Matrix Green"))
            self.txt_ssh_tunnel.setText(data.get("ssh_tunnel", ""))
            self.txt_post_cmd.setText(data.get("post_cmd", ""))

            self.chk_heredar_auth.setChecked(bool(data.get("inherit_auth", False)))
            self.chk_rdp_sso.setChecked(bool(data.get("rdp_sso", True)))
            self.chk_rdp_admin.setChecked(bool(data.get("rdp_admin", False)))
            self.chk_rdp_clipboard.setChecked(bool(data.get("rdp_clipboard", True)))
            self.chk_rdp_drives.setChecked(bool(data.get("rdp_drives", False)))
            self.chk_rdp_audio.setChecked(bool(data.get("rdp_audio", True)))

            if data.get("ip"):
                self.txt_scan_host.setText(data.get("ip"))
        finally:
            self._updating_form = False

    def guardar_perfil(self):
        item = self.arbol_conexiones.currentItem()
        if not item or item == self.raiz:
            return

        prev = item.data(0, Qt.ItemDataRole.UserRole) or {}
        is_folder = prev.get("type") == "folder"

        data = {
            "type": "folder" if is_folder else "connection",
            "name": self.txt_nombre.text().strip() or ("Carpeta" if is_folder else "Nuevo_Host"),
            "ip": "" if is_folder else self.txt_ip.text().strip(),
            "port": self.spin_port.value(),
            "user": self.txt_usuario.text().strip(),
            "pass": self.txt_pass.text(),
            "domain": self.txt_dominio.text().strip(),
            "ssh_key": self.txt_ssh_key.text().strip(),
            "proto": self.combo_proto.currentText(),
            "font": self.spin_font.value(),
            "theme": self.combo_tema_term.currentText(),
            "tag": self.combo_tag.currentText(),
            "notes": self.txt_notas.text().strip(),
            "resolution": self.combo_resolucion.currentText(),
            "ssh_tunnel": self.txt_ssh_tunnel.text().strip(),
            "post_cmd": self.txt_post_cmd.text().strip(),
            "inherit_auth": self.chk_heredar_auth.isChecked(),
            "rdp_sso": self.chk_rdp_sso.isChecked(),
            "rdp_admin": self.chk_rdp_admin.isChecked(),
            "rdp_clipboard": self.chk_rdp_clipboard.isChecked(),
            "rdp_drives": self.chk_rdp_drives.isChecked(),
            "rdp_audio": self.chk_rdp_audio.isChecked(),
        }
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        self._actualizar_etiqueta_item_arbol(item)
        self.guardar_todas_las_conexiones()

        texto_orig = self.btn_guardar.text()
        self.btn_guardar.setText("✅ Guardado")
        QTimer.singleShot(1400, lambda: self.btn_guardar.setText(texto_orig))

    def _on_proto_changed(self, proto: str):
        if not self._updating_form:
            self.spin_port.setValue(DEFAULT_PORTS.get(proto, 22))

    def _seleccionar_clave_ssh(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar Clave Privada SSH", str(Path.home()), "SSH Keys (*.pem *.ppk *.key *id_rsa* *);;All Files (*)")
        if ruta:
            self.txt_ssh_key.setText(ruta)

    # ──────────────────────────────────────────────────────────────────────────
    #  CONEXIÓN EN PESTAÑAS INTEGRADAS Y VENTANAS NATIVAS (mRemoteNG Connect)
    # ──────────────────────────────────────────────────────────────────────────
    def conectar_rapido(self):
        raw = self.txt_quick_host.text().strip()
        if not raw:
            QMessageBox.warning(self, "Quick Connect", "Ingresa un Host o IP (ej. root@192.168.1.10 o 10.0.0.5).")
            return

        proto = self.combo_quick_proto.currentText()
        port = self.spin_quick_port.value()
        user = ""
        host = raw

        if "@" in host:
            user, host = host.split("@", 1)
        if ":" in host and not host.startswith("http"):
            h_part, p_part = host.rsplit(":", 1)
            if p_part.isdigit():
                host = h_part
                port = int(p_part)

        conn_data = {
            "type": "connection",
            "name": f"Quick: {host}",
            "ip": host,
            "port": port,
            "user": user,
            "pass": "",
            "proto": proto,
            "font": 12,
            "theme": "Matrix Green",
            "rdp_sso": True,
            "rdp_clipboard": True,
            "rdp_audio": True,
        }
        self._abrir_sesion_mremote(conn_data, forzar_externa=False)

    def conectar(self, forzar_externa: bool = False):
        # Sincronizar el formulario actual antes de conectar
        item = self.arbol_conexiones.currentItem()
        if item and item != self.raiz:
            d_item = item.data(0, Qt.ItemDataRole.UserRole) or {}
            if d_item.get("type") == "folder":
                # En mRemoteNG, conectar una carpeta abre todas las conexiones dentro de ella
                for i in range(item.childCount()):
                    ch = item.child(i)
                    ch_d = ch.data(0, Qt.ItemDataRole.UserRole) or {}
                    if ch_d.get("type") != "folder":
                        eff = self.resolver_credenciales_efectivas(ch)
                        self._abrir_sesion_mremote(eff, forzar_externa=forzar_externa)
                return

        conn_data = {
            "name": self.txt_nombre.text().strip() or self.txt_ip.text().strip() or "Sesión",
            "ip": self.txt_ip.text().strip(),
            "port": self.spin_port.value(),
            "user": self.txt_usuario.text().strip(),
            "pass": self.txt_pass.text(),
            "domain": self.txt_dominio.text().strip(),
            "ssh_key": self.txt_ssh_key.text().strip(),
            "proto": self.combo_proto.currentText(),
            "font": self.spin_font.value(),
            "theme": self.combo_tema_term.currentText(),
            "resolution": self.combo_resolucion.currentText(),
            "ssh_tunnel": self.txt_ssh_tunnel.text().strip(),
            "post_cmd": self.txt_post_cmd.text().strip(),
            "inherit_auth": self.chk_heredar_auth.isChecked(),
            "rdp_sso": self.chk_rdp_sso.isChecked(),
            "rdp_admin": self.chk_rdp_admin.isChecked(),
            "rdp_clipboard": self.chk_rdp_clipboard.isChecked(),
            "rdp_drives": self.chk_rdp_drives.isChecked(),
            "rdp_audio": self.chk_rdp_audio.isChecked(),
        }

        if item and item != self.raiz and self.chk_heredar_auth.isChecked():
            eff = self.resolver_credenciales_efectivas(item)
            for k in ("user", "pass", "domain", "ssh_key"):
                if not conn_data.get(k) and eff.get(k):
                    conn_data[k] = eff[k]

        if not conn_data["ip"]:
            QMessageBox.warning(self, "Error", "Debe ingresar una IP/Host para conectar.")
            return

        self._abrir_sesion_mremote(conn_data, forzar_externa=forzar_externa)

    def _abrir_sesion_mremote(self, conn_data: dict, forzar_externa: bool = False):
        proto = conn_data.get("proto", "SSH")
        name = conn_data.get("name", conn_data.get("ip", "Host"))
        icon = PROTO_ICONS.get(proto, "🖧")

        if forzar_externa:
            self._lanzar_consola_nativa_externa(conn_data)
            return

        if proto in ("HTTP", "HTTPS"):
            tab = MRemoteWebSession(self.tabs_sesiones, conn_data, self.colores)
        elif proto in ("RDP", "VNC"):
            tab = MRemoteRDPSession(
                self.tabs_sesiones,
                conn_data,
                self.colores,
                launch_cb=self.callbacks.get("abrir_rdp_nativo"),
            )
        else:
            tab = MRemoteTerminalSession(
                self.tabs_sesiones,
                conn_data,
                self.colores,
                open_native_cb=self._lanzar_consola_nativa_externa,
            )

        idx = self.tabs_sesiones.addTab(tab, f"{icon} {name}")
        self.tabs_sesiones.setCurrentIndex(idx)
        self.actualizar_vista_vacia()

    def _lanzar_consola_nativa_externa(self, conn_data: dict):
        ip = conn_data.get("ip", "").strip()
        port = conn_data.get("port", 22)
        usr = conn_data.get("user", "").strip()
        pwd = conn_data.get("pass", "")
        proto = conn_data.get("proto", "SSH")
        ssh_key = conn_data.get("ssh_key", "").strip()

        if pwd:
            QGuiApplication.clipboard().setText(pwd)

        if proto == "RDP":
            tab_rdp = MRemoteRDPSession(self, conn_data, self.colores, launch_cb=self.callbacks.get("abrir_rdp_nativo"))
            tab_rdp.deleteLater()
            return

        if proto == "SSH":
            key_arg = f'-i "{ssh_key}" ' if (ssh_key and os.path.exists(ssh_key)) else ""
            cmd = f"ssh -p {port} {key_arg}{usr}@{ip}" if usr else f"ssh -p {port} {key_arg}{ip}"
        elif proto == "SFTP":
            cmd = f"sftp -P {port} {usr}@{ip}" if usr else f"sftp -P {port} {ip}"
        elif proto == "Telnet":
            cmd = f"telnet {ip} {port}"
        else:
            cmd = f"ssh {usr}@{ip}" if usr else f"ping {ip}"

        so = platform.system()
        try:
            if so == "Windows":
                if pwd and proto in ("SSH", "SFTP"):
                    ps_script = (
                        f"$wshell = New-Object -ComObject wscript.shell; "
                        f"$wshell.Run('cmd.exe /k {cmd}', 1, $false); "
                        f"Start-Sleep -Milliseconds 1500; "
                        f"$wshell.SendKeys('{pwd}'); "
                        f"$wshell.SendKeys('{{ENTER}}');"
                    )
                    subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script])
                else:
                    subprocess.Popen(f'start cmd /k "{cmd}"', shell=True)
            elif so == "Linux":
                for term in ["x-terminal-emulator", "gnome-terminal", "konsole"]:
                    try:
                        subprocess.Popen([term, "-e", cmd])
                        break
                    except Exception:
                        pass
            elif so == "Darwin":
                subprocess.Popen(["osascript", "-e", f'tell app "Terminal" to do script "{cmd}"'])
        except Exception as e:
            QMessageBox.critical(self, "Error de Ejecución", f"No se pudo iniciar la consola externa: {e}")

    def _cerrar_pestana_sesion(self, index: int):
        if index <= 0:
            return
        w = self.tabs_sesiones.widget(index)
        if w and hasattr(w, "cerrar_sesion"):
            w.cerrar_sesion()
        self.tabs_sesiones.removeTab(index)
        if w:
            w.deleteLater()
        self.actualizar_vista_vacia()

    def enviar_broadcast_terminales(self):
        cmd = self.txt_broadcast.text().strip()
        if not cmd:
            return
        enviados = 0
        for i in range(1, self.tabs_sesiones.count()):
            w = self.tabs_sesiones.widget(i)
            if isinstance(w, MRemoteTerminalSession):
                w.enviar_comando(cmd)
                enviados += 1
        self.txt_broadcast.clear()
        if enviados == 0:
            QMessageBox.information(self, "Broadcast Multi-SSH", "No hay ninguna pestaña de terminal (SSH/Telnet/WinRM) abierta actualmente.")

    # ──────────────────────────────────────────────────────────────────────────
    #  MENÚ CONTEXTUAL, FILTRO, MATRIZ Y ESCÁNER DE PUERTOS
    # ──────────────────────────────────────────────────────────────────────────
    def _mostrar_menu_contextual_arbol(self, pos):
        item = self.arbol_conexiones.itemAt(pos)
        if not item:
            return
        self.arbol_conexiones.setCurrentItem(item)
        self.cargar_datos(item)
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        is_folder = data.get("type") == "folder" or item == self.raiz

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{ padding: 6px 18px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {self.colores['acento']}; }}
        """)

        if not is_folder:
            act_tab = QAction("🚀 Conectar en Pestaña Integrada", self)
            act_tab.triggered.connect(lambda: self.conectar(forzar_externa=False))
            menu.addAction(act_tab)

            act_ext = QAction("🪟 Conectar en Ventana Externa (Nativa)", self)
            act_ext.triggered.connect(lambda: self.conectar(forzar_externa=True))
            menu.addAction(act_ext)

            act_as = QAction("👤 Conectar como... (Credenciales al vuelo)", self)
            act_as.triggered.connect(self._conectar_como_dialogo)
            menu.addAction(act_as)

            menu.addSeparator()

            act_ping = QAction("📡 Comprobar Ping y Puerto TCP", self)
            act_ping.triggered.connect(lambda: self._chequear_item_individual(item))
            menu.addAction(act_ping)

            act_scan = QAction("🔍 Escanear Puertos de este Host", self)
            act_scan.triggered.connect(lambda: [self.txt_scan_host.setText(data.get("ip", "")), self.tabs_sesiones.setCurrentIndex(0), self.ejecutar_escaneo_puertos_ui()])
            menu.addAction(act_scan)

            menu.addSeparator()

            act_dup = QAction("📋 Duplicar Conexión", self)
            act_dup.triggered.connect(self.duplicar_conexion_seleccionada)
            menu.addAction(act_dup)

            act_cp_ip = QAction("📋 Copiar IP / Host", self)
            act_cp_ip.triggered.connect(lambda: QGuiApplication.clipboard().setText(data.get("ip", "")))
            menu.addAction(act_cp_ip)

            if data.get("pass"):
                act_cp_pw = QAction("🔑 Copiar Contraseña", self)
                act_cp_pw.triggered.connect(lambda: QGuiApplication.clipboard().setText(data.get("pass", "")))
                menu.addAction(act_cp_pw)
        else:
            if item != self.raiz:
                act_all = QAction("🚀 Conectar todos los hosts de esta carpeta", self)
                act_all.triggered.connect(lambda: self.conectar(forzar_externa=False))
                menu.addAction(act_all)
                menu.addSeparator()

        act_new_conn = QAction("➕ Nueva Conexión aquí", self)
        act_new_conn.triggered.connect(self.nueva_conexion)
        menu.addAction(act_new_conn)

        act_new_fld = QAction("📂 Nueva Carpeta aquí", self)
        act_new_fld.triggered.connect(self.nueva_carpeta)
        menu.addAction(act_new_fld)

        if item != self.raiz:
            menu.addSeparator()
            act_del = QAction("🗑️ Eliminar", self)
            act_del.triggered.connect(self.eliminar_conexion)
            menu.addAction(act_del)

        menu.exec(self.arbol_conexiones.viewport().mapToGlobal(pos))

    def _conectar_como_dialogo(self):
        usr, ok1 = QInputDialog.getText(self, "Conectar como...", "Usuario para esta sesión:", QLineEdit.EchoMode.Normal, self.txt_usuario.text())
        if not ok1:
            return
        pwd, ok2 = QInputDialog.getText(self, "Conectar como...", "Contraseña (opcional):", QLineEdit.EchoMode.Password)
        if not ok2:
            return
        self.txt_usuario.setText(usr)
        if pwd:
            self.txt_pass.setText(pwd)
        self.conectar(forzar_externa=False)

    def _on_tree_double_clicked(self, item: QTreeWidgetItem, col: int):
        if not item or item == self.raiz:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if data.get("type") != "folder":
            self.cargar_datos(item)
            self.conectar(forzar_externa=False)

    def _on_matrix_double_clicked(self, row: int, col: int):
        conns = self.obtener_todas_las_conexiones_planas()
        if 0 <= row < len(conns):
            item, eff, _ = conns[row]
            self.arbol_conexiones.setCurrentItem(item)
            self.cargar_datos(item)
            self._abrir_sesion_mremote(eff, forzar_externa=False)

    def _filtrar_arbol(self, texto: str):
        q = texto.strip().lower()
        if not hasattr(self, "raiz"):
            return

        def _filter_node(node: QTreeWidgetItem) -> bool:
            data = node.data(0, Qt.ItemDataRole.UserRole) or {}
            searchable = f"{data.get('name','')} {data.get('ip','')} {data.get('proto','')} {data.get('tag','')} {data.get('notes','')}".lower()
            own_match = (not q) or (q in searchable)
            child_match = False
            for i in range(node.childCount()):
                if _filter_node(node.child(i)):
                    child_match = True
            visible = own_match or child_match
            if node != self.raiz:
                node.setHidden(not visible)
            if child_match and q:
                node.setExpanded(True)
            return visible

        _filter_node(self.raiz)

    def actualizar_matriz_hosts(self):
        if not hasattr(self, "table_hosts"):
            return
        conns = self.obtener_todas_las_conexiones_planas()
        self.table_hosts.setRowCount(len(conns))

        online_count = 0
        for row, (item, data, folder_name) in enumerate(conns):
            ip = data.get("ip", "")
            proto = data.get("proto", "SSH")
            port = data.get("port", DEFAULT_PORTS.get(proto, 22))
            st = self._status_cache.get(ip)
            if st and st.get("online"):
                online_count += 1
                st_txt = f"🟢 Online ({st.get('latency_ms', 1)} ms)"
            elif st is not None:
                st_txt = "🔴 Offline"
            else:
                st_txt = "⚪ Sin probar"

            vals = [
                st_txt,
                data.get("name", "Host"),
                f"📁 {folder_name}",
                f"{PROTO_ICONS.get(proto, '🖧')} {proto}",
                f"{ip}:{port}",
                data.get("user", "-"),
                f"[{data.get('tag', 'General')}] {data.get('notes', '')}",
            ]
            for col, val in enumerate(vals):
                tw = QTableWidgetItem(str(val))
                self.table_hosts.setItem(row, col, tw)

        self.actualizar_vista_vacia(online_count=online_count)

    def actualizar_vista_vacia(self, online_count: int = None):
        conns = self.obtener_todas_las_conexiones_planas()
        total_hosts = len(conns)

        # Contar carpetas
        folders = 0
        if hasattr(self, "raiz"):
            def _cnt_f(n):
                nonlocal folders
                for i in range(n.childCount()):
                    ch = n.child(i)
                    if (ch.data(0, Qt.ItemDataRole.UserRole) or {}).get("type") == "folder":
                        folders += 1
                        _cnt_f(ch)
            _cnt_f(self.raiz)

        if online_count is None:
            online_count = sum(1 for _, d, _ in conns if self._status_cache.get(d.get("ip", ""), {}).get("online"))

        if hasattr(self, "lbl_kpi_total"):
            self.lbl_kpi_total.setText(str(total_hosts))
            self.lbl_kpi_folders.setText(str(folders))
            self.lbl_kpi_online.setText(str(online_count))
            active_tabs = max(0, self.tabs_sesiones.count() - 1) if hasattr(self, "tabs_sesiones") else 0
            self.lbl_kpi_sessions.setText(str(active_tabs))

    def _chequear_item_individual(self, item: QTreeWidgetItem):
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        ip = data.get("ip", "").strip()
        port = int(data.get("port", 22) or 22)
        if not ip:
            return

        def _work():
            fn = self.callbacks.get("verificar_host_remoto")
            if callable(fn):
                res = fn(ip, port)
            else:
                res = {"online": False, "latency_ms": None}
            self._status_cache[ip] = res
            QTimer.singleShot(0, lambda: [self._actualizar_etiqueta_item_arbol(item), self.actualizar_matriz_hosts()])

        threading.Thread(target=_work, daemon=True).start()

    def ping_todos_los_hosts(self):
        conns = self.obtener_todas_las_conexiones_planas()
        if not conns:
            return

        def _worker():
            fn = self.callbacks.get("verificar_host_remoto")
            for item, data, _ in conns:
                ip = data.get("ip", "").strip()
                port = int(data.get("port", 22) or 22)
                if not ip:
                    continue
                if callable(fn):
                    res = fn(ip, port, timeout=0.6)
                else:
                    t0 = time.perf_counter()
                    try:
                        with socket.create_connection((ip, port), timeout=0.6):
                            res = {"online": True, "latency_ms": max(1, int((time.perf_counter() - t0) * 1000))}
                    except Exception:
                        res = {"online": False, "latency_ms": None}
                self._status_cache[ip] = res
                QTimer.singleShot(0, lambda it=item: self._actualizar_etiqueta_item_arbol(it))
            QTimer.singleShot(0, self.actualizar_matriz_hosts)

        threading.Thread(target=_worker, daemon=True).start()

    def ejecutar_escaneo_puertos_ui(self):
        host = self.txt_scan_host.text().strip() or self.txt_ip.text().strip()
        if not host:
            QMessageBox.warning(self, "Escáner de Puertos", "Ingresa una IP o selecciona un servidor primero.")
            return

        self.lbl_scan_results.setText(f"⏳ Escaneando puertos comunes de administración remota en <b>{host}</b>...")
        self.btn_scan_ports.setEnabled(False)

        def _scan():
            fn = self.callbacks.get("escanear_puertos_remotos")
            if callable(fn):
                resultados = fn(host)
            else:
                resultados = []
            QTimer.singleShot(0, lambda: self._mostrar_resultados_escaneo(host, resultados))

        threading.Thread(target=_scan, daemon=True).start()

    def _mostrar_resultados_escaneo(self, host: str, resultados: list):
        self.btn_scan_ports.setEnabled(True)
        abiertos = [r for r in resultados if r.get("open")]
        if not abiertos:
            self.lbl_scan_results.setText(f"🔴 No se detectaron puertos estándar abiertos en <b>{host}</b> (o el firewall los filtra).")
            return

        badges = []
        for r in abiertos:
            badges.append(
                f"<span style='background:#065F46; color:#34D399; padding:3px 8px; border-radius:4px; font-weight:bold;'>"
                f"🟢 {r['port']} ({r['service']}) · {r['latency_ms']}ms</span>"
            )
        self.lbl_scan_results.setText(f"<b>Puertos abiertos en {host}:</b> &nbsp; " + " &nbsp; ".join(badges))

    # ──────────────────────────────────────────────────────────────────────────
    #  IMPORTACIÓN Y EXPORTACIÓN COMPATIBLE CON mRemoteNG XML (confCons.xml), JSON Y CSV
    # ──────────────────────────────────────────────────────────────────────────
    def exportar_conexiones_dialogo(self):
        ruta, filtro = QFileDialog.getSaveFileName(
            self,
            "Exportar Conexiones mRemoteNG",
            "confCons.xml",
            "mRemoteNG XML (*.xml);;Multitool JSON (*.json);;Tabla CSV (*.csv)"
        )
        if not ruta:
            return

        if ruta.endswith(".xml") or "XML" in filtro:
            self._exportar_mremoteng_xml(ruta)
        elif ruta.endswith(".csv") or "CSV" in filtro:
            self._exportar_csv(ruta)
        else:
            data = self._serializar_nodos_recursivo(self.raiz)
            Path(ruta).write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
        QMessageBox.information(self, "Exportación Exitosa", f"Conexiones exportadas correctamente a:\n{ruta}")

    def _exportar_mremoteng_xml(self, ruta: str):
        root_el = ET.Element("mrng:Connections", {" xmlns:mrng": "http://mremoteng.org", "Export": "Multitool-mRemoteNG"})

        def _append_xml(parent_item: QTreeWidgetItem, xml_parent: ET.Element):
            for i in range(parent_item.childCount()):
                ch = parent_item.child(i)
                d = ch.data(0, Qt.ItemDataRole.UserRole) or {}
                is_fld = d.get("type") == "folder"
                node_el = ET.SubElement(
                    xml_parent,
                    "Node",
                    {
                        "Name": str(d.get("name", "Node")),
                        "Type": "Container" if is_fld else "Connection",
                        "Hostname": str(d.get("ip", "")),
                        "Port": str(d.get("port", 22)),
                        "Protocol": str(d.get("proto", "SSH")),
                        "Username": str(d.get("user", "")),
                        "Domain": str(d.get("domain", "")),
                        "Descr": str(d.get("notes", "")),
                    },
                )
                if is_fld:
                    _append_xml(ch, node_el)

        _append_xml(self.raiz, root_el)
        tree = ET.ElementTree(root_el)
        tree.write(ruta, encoding="utf-8", xml_declaration=True)

    def _exportar_csv(self, ruta: str):
        conns = self.obtener_todas_las_conexiones_planas()
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Folder", "Protocol", "Host", "Port", "Username", "Domain", "Tag", "Notes"])
            for _, d, fld in conns:
                writer.writerow([
                    d.get("name", ""), fld, d.get("proto", "SSH"), d.get("ip", ""),
                    d.get("port", 22), d.get("user", ""), d.get("domain", ""),
                    d.get("tag", ""), d.get("notes", "")
                ])

    def importar_conexiones_dialogo(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Importar Conexiones (mRemoteNG XML, JSON, CSV)",
            "",
            "Archivos Soportados (*.xml *.json *.csv);;mRemoteNG XML (*.xml);;JSON (*.json);;CSV (*.csv)"
        )
        if not ruta:
            return

        try:
            if ruta.lower().endswith(".xml"):
                nodos = self._parsear_mremoteng_xml(ruta)
            elif ruta.lower().endswith(".csv"):
                nodos = self._parsear_csv(ruta)
            else:
                nodos = json.loads(Path(ruta).read_text(encoding="utf-8"))

            if nodos:
                self._poblar_nodos_recursivo(self.raiz, nodos)
                self.guardar_todas_las_conexiones()
                QMessageBox.information(self, "Importación Completada", f"Se importaron las conexiones desde:\n{Path(ruta).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Importar", f"No se pudo importar el archivo:\n{e}")

    def _parsear_mremoteng_xml(self, ruta: str) -> list:
        tree = ET.parse(ruta)
        root = tree.getroot()

        def _parse_el(el) -> list:
            out = []
            for child in el:
                if not child.tag.endswith("Node"):
                    continue
                ntype = child.attrib.get("Type", "Connection")
                proto_raw = child.attrib.get("Protocol", "SSH").upper()
                proto = "SSH"
                for k in DEFAULT_PORTS:
                    if k.upper() in proto_raw:
                        proto = k
                        break
                if ntype.lower() == "container":
                    out.append({
                        "type": "folder",
                        "name": child.attrib.get("Name", "Carpeta Importada"),
                        "user": child.attrib.get("Username", ""),
                        "domain": child.attrib.get("Domain", ""),
                        "notes": child.attrib.get("Descr", ""),
                        "children": _parse_el(child),
                    })
                else:
                    out.append({
                        "type": "connection",
                        "name": child.attrib.get("Name", "Host"),
                        "ip": child.attrib.get("Hostname", ""),
                        "port": int(child.attrib.get("Port", DEFAULT_PORTS.get(proto, 22)) or 22),
                        "proto": proto,
                        "user": child.attrib.get("Username", ""),
                        "domain": child.attrib.get("Domain", ""),
                        "notes": child.attrib.get("Descr", ""),
                        "tag": "Producción",
                    })
            return out

        return _parse_el(root)

    def _parsear_csv(self, ruta: str) -> list:
        out = []
        with open(ruta, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                proto = row.get("Protocol") or row.get("proto") or "SSH"
                out.append({
                    "type": "connection",
                    "name": row.get("Name") or row.get("name") or "Host CSV",
                    "ip": row.get("Host") or row.get("Hostname") or row.get("ip") or "",
                    "port": int(row.get("Port") or row.get("port") or DEFAULT_PORTS.get(proto, 22)),
                    "proto": proto,
                    "user": row.get("Username") or row.get("user") or "",
                    "domain": row.get("Domain") or row.get("domain") or "",
                    "tag": row.get("Tag") or "Producción",
                    "notes": row.get("Notes") or "",
                })
        return out

    # ──────────────────────────────────────────────────────────────────────────
    #  ESTADO INDICADOR EN TIEMPO REAL (PING / TCP CIRCLE)
    # ──────────────────────────────────────────────────────────────────────────
    def _iniciar_chequeo_ping(self, txt: str):
        if not txt.strip():
            self.lbl_estado.setText("⚫")
            return

        if hasattr(self, "_timer_ping"):
            self._timer_ping.stop()
        else:
            self._timer_ping = QTimer(self)
            self._timer_ping.setSingleShot(True)
            self._timer_ping.timeout.connect(lambda: threading.Thread(target=self._validar_ip, daemon=True).start())

        self._timer_ping.start(800)

    def _validar_ip(self):
        ip = self.txt_ip.text().strip()
        port = self.spin_port.value() if hasattr(self, "spin_port") else 22
        if not ip:
            return

        fn = self.callbacks.get("verificar_host_remoto")
        if callable(fn):
            res = fn(ip, port, timeout=0.8)
            exito = res.get("online", False)
            self._status_cache[ip] = res
        else:
            cmd_args = ["ping", "-n", "1", "-w", "1000", ip] if platform.system() == "Windows" else ["ping", "-c", "1", "-W", "1", ip]
            kwargs = {"creationflags": 0x08000000} if platform.system() == "Windows" else {}
            try:
                r = subprocess.run(cmd_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
                exito = (r.returncode == 0)
            except Exception:
                exito = False
            self._status_cache[ip] = {"online": exito, "latency_ms": 10 if exito else None}

        QTimer.singleShot(0, lambda: self.lbl_estado.setText("🟢" if exito else "🔴"))
