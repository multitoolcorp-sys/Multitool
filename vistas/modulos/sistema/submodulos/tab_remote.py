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
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QFormLayout, QComboBox, QMessageBox, QFrame,
    QSpinBox, QHeaderView, QTabWidget, QPlainTextEdit, QCheckBox, QFileDialog,
    QMenu, QTableWidget, QTableWidgetItem, QInputDialog, QAbstractItemView,
    QScrollArea, QSizePolicy, QApplication
)
from PyQt6.QtGui import QGuiApplication, QFont, QColor, QAction, QTextCursor, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QTimer, QProcess, QProcessEnvironment, pyqtSignal, QUrl

from controlador.utils.paths import get_data_path

# Reutilizar la consola interactiva real de terminal_main.py (SingleTerminalSession)
try:
    from vistas.modulos.terminal.submodulos.terminal_session import SingleTerminalSession
    TERMINAL_MODULE_AVAILABLE = True
except ImportError:
    SingleTerminalSession = QWidget
    TERMINAL_MODULE_AVAILABLE = False


def _asegurar_script_ssh_askpass() -> str:
    """
    Crea un script auxiliar SSH_ASKPASS para Windows/Linux/macOS de modo que OpenSSH (ssh.exe / sftp.exe)
    pueda autenticar dentro de QProcess sin requerir CONIN$ nativo:
    1) Si MULTITOOL_SSH_PASS está definida (campo Clave), la inyecta automáticamente sin diálogos.
    2) Si está vacía y el servidor pide contraseña o confirmación, abre un cuadro de entrada para el usuario.
    """
    helper_dir = get_data_path() / "ssh_helpers"
    helper_dir.mkdir(parents=True, exist_ok=True)

    if platform.system() == "Windows":
        bat_path = helper_dir / "multitool_askpass.bat"
        ps1_path = helper_dir / "multitool_askpass.ps1"
        ps1_code = (
            "param([string]$PromptText = 'SSH Password:')\r\n"
            "if ($env:MULTITOOL_SSH_PASS -and $env:MULTITOOL_SSH_PASS.Length -gt 0) {\r\n"
            "    [Console]::Out.WriteLine($env:MULTITOOL_SSH_PASS)\r\n"
            "    exit 0\r\n"
            "}\r\n"
            "Add-Type -AssemblyName Microsoft.VisualBasic\r\n"
            "$ans = [Microsoft.VisualBasic.Interaction]::InputBox($PromptText, 'Multitool mRemoteNG - Autenticacion SSH', '')\r\n"
            "[Console]::Out.WriteLine($ans)\r\n"
        )
        bat_code = f'@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "{ps1_path}" %*\r\n'
        try:
            ps1_path.write_text(ps1_code, encoding="utf-8")
            bat_path.write_text(bat_code, encoding="utf-8")
        except Exception:
            pass
        return str(bat_path)
    else:
        sh_path = helper_dir / "multitool_askpass.sh"
        sh_code = '#!/bin/sh\nif [ -n "$MULTITOOL_SSH_PASS" ]; then\n  echo "$MULTITOOL_SSH_PASS"\nfi\n'
        try:
            sh_path.write_text(sh_code, encoding="utf-8")
            os.chmod(sh_path, 0o755)
        except Exception:
            pass
        return str(sh_path)


if TERMINAL_MODULE_AVAILABLE:
    class RemoteSingleTerminalSession(SingleTerminalSession):
        """
        Extiende SingleTerminalSession (de terminal_main.py) para sesiones remotas SSH / SFTP / Telnet / WinRM:
        - Ejecuta ssh -tt directamente en QProcess con SSH_ASKPASS_REQUIRE=force (sin el error 'stdin is not a terminal')
        - Envía saltos de línea '\\n' puros en sesiones PTY remotas Linux para evitar doble eco de prompt
        """

        def __init__(self, parent, context, shell_cmd=None, shell_args=None, cwd=None, tema_dict=None, ssh_password="", is_remote_pty=False):
            self.ssh_password = ssh_password or ""
            self.is_remote_pty = bool(is_remote_pty)
            self._esc_tail_buffer = ""
            super().__init__(parent, context, shell_cmd=shell_cmd, shell_args=shell_args, cwd=cwd, tema_dict=tema_dict)

        def leer_salida(self):
            """Pre-limpia secuencias OSC/CSI fragmentadas entre paquetes TCP antes de pasarlas a AnsiParser."""
            data_bytes = self.process.readAllStandardOutput().data()
            if not data_bytes:
                return
            try:
                text = data_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = data_bytes.decode("latin-1", errors="replace")

            if self._esc_tail_buffer:
                text = self._esc_tail_buffer + text
                self._esc_tail_buffer = ""

            # Si el bloque termina con una secuencia ESC/OSC/CSI incompleta, retenerla hasta el siguiente chunk
            last_esc = text.rfind("\x1b")
            if last_esc != -1 and last_esc >= len(text) - 512:
                tail = text[last_esc:]
                if tail.startswith("\x1b]") and ("\x07" not in tail and "\x1b\\" not in tail):
                    self._esc_tail_buffer = tail
                    text = text[:last_esc]
                elif tail == "\x1b" or (tail.startswith("\x1b[") and not any(c.isalpha() or c == "~" for c in tail[2:])):
                    self._esc_tail_buffer = tail
                    text = text[:last_esc]

            if not text:
                return

            text = self.ansi_parser.limpiar_secuencias_control(text)
            if not text:
                return

            # Inyectar el texto limpio reutilizando el flujo de SingleTerminalSession sin volver a leer del QProcess
            if self._pending_echo:
                trimmed = text.lstrip("\r\n")
                if trimmed.startswith(self._pending_echo):
                    remainder = trimmed[len(self._pending_echo):]
                    if remainder.startswith("\r\n"):
                        remainder = remainder[2:]
                    elif remainder.startswith("\n") or remainder.startswith("\r"):
                        remainder = remainder[1:]
                    text = remainder
                    self._pending_echo = None
                elif self._pending_echo.startswith(trimmed) and trimmed:
                    self._pending_echo = self._pending_echo[len(trimmed):]
                    text = ""
                else:
                    self._pending_echo = None
            elif self._pending_empty_enter:
                if text.startswith("\r\n"):
                    text = text[2:]
                elif text.startswith("\n") or text.startswith("\r"):
                    text = text[1:]
                self._pending_empty_enter = False

            if not text:
                return

            if "\x1b[2J" in text or "\x1b[3J" in text or "\x1b[H\x1b[2J" in text:
                self.terminal.clear()
                self.terminal._prompt_pos = 0
                text = text.replace("\x1b[2J", "").replace("\x1b[3J", "").replace("\x1b[H", "")

            self.ansi_parser.append_ansi_text(self.terminal, text, default_fg=self.tema_dict["fg"])
            self.terminal._prompt_pos = self.terminal.textCursor().position()
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)

        def iniciar_proceso(self):
            self.process = QProcess(self)
            self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            self.process.readyReadStandardOutput.connect(self.leer_salida)
            self.process.finished.connect(self.on_process_finished)

            env = QProcessEnvironment.systemEnvironment()
            env.insert("PYTHONIOENCODING", "UTF-8")
            env.insert("TERM", "xterm-256color")

            if self.is_remote_pty:
                askpass_script = _asegurar_script_ssh_askpass()
                env.insert("SSH_ASKPASS", askpass_script)
                env.insert("SSH_ASKPASS_REQUIRE", "force")
                env.insert("DISPLAY", "1")
                if self.ssh_password:
                    env.insert("MULTITOOL_SSH_PASS", self.ssh_password)

            self.process.setProcessEnvironment(env)
            self.process.setWorkingDirectory(self.cwd)

            if not self.shell_cmd:
                if platform.system() == "Windows":
                    self.shell_cmd = "powershell.exe"
                    self.shell_args = ["-NoLogo", "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass"]
                else:
                    self.shell_cmd = "bash"
                    self.shell_args = ["-i"]

            self.process.start(self.shell_cmd, self.shell_args)
            self.lbl_status.setText("🟢 Conectado / En Ejecución" if self.is_remote_pty else "🟢 En Ejecución")
            self.lbl_status.setStyleSheet("color: #10B981;")

        def enviar_comando(self, cmd_text=None, desde_teclado=False):
            if not self.is_remote_pty:
                return super().enviar_comando(cmd_text=cmd_text, desde_teclado=desde_teclado)

            cmd = cmd_text if cmd_text is not None else self.terminal.get_current_input()
            cmd_clean = cmd.strip()
            if not cmd_clean:
                if self.process and self.process.state() == QProcess.ProcessState.Running:
                    self._pending_empty_enter = True
                    self.process.write(b"\n")
                return

            self.history.append(cmd_clean)
            self.history_index = len(self.history)

            if not desde_teclado and cmd_clean:
                cursor = self.terminal.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText(cmd_clean + "\n")
                self.terminal.setTextCursor(cursor)
                self.terminal._prompt_pos = self.terminal.textCursor().position()

            if cmd_clean.lower() in ("cls", "clear"):
                self.limpiar_consola()
                if self.process and self.process.state() == QProcess.ProcessState.Running:
                    self._pending_echo = cmd_clean
                    self.process.write((cmd_clean + "\n").encode("utf-8"))
                return

            if self.process and self.process.state() == QProcess.ProcessState.Running:
                self._pending_echo = cmd_clean
                self.process.write((cmd_clean + "\n").encode("utf-8", errors="replace"))

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
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

# Mismos temas que vistas/modulos/terminal/terminal_main.py
TERMINAL_THEMES = {
    "🟢 Hacker Esmeralda": {"bg": "#07090e", "fg": "#10B981", "accent": "#059669"},
    "🟦 Cyberpunk Neón": {"bg": "#090d16", "fg": "#06B6D4", "accent": "#0891B2"},
    "🟡 Matrix Ámbar": {"bg": "#0c0a07", "fg": "#F59E0B", "accent": "#D97706"},
    "🫥 Consola Clásica": {"bg": "#0f0f15", "fg": "#F3F4F6", "accent": "#9CA3AF"},
}

SSH_MACROS = [
    ("⚡ Snippets...", ""),
    ("📊 top (Recursos)", "top -b -n 1 | head -n 20"),
    ("💾 df -h (Disco)", "df -h"),
    ("🧠 free -m (RAM)", "free -m"),
    ("🐳 docker ps", "docker ps -a"),
    ("⚙️ systemctl --failed", "systemctl --failed"),
    ("🔌 ss -tulpn (Puertos)", "ss -tulpn"),
    ("📜 journalctl (Logs)", "journalctl -n 30 --no-pager"),
    ("🌐 ip -br a (Red)", "ip -br a"),
    ("⏱️ uptime & w", "uptime && w"),
]


class MRemoteTerminalSession(QWidget):
    """
    Sesión de terminal remota e interactiva basada exactamente en el motor de
    vistas/modulos/terminal/terminal_main.py (SingleTerminalSession / InteractiveTerminalScreen).
    Se escribe directamente en la pantalla de consola, soporta ANSI, Tab, historial ↑/↓, Zoom y Ctrl+F.
    """

    def __init__(self, parent, conn_data: dict, colores: dict, context=None, open_native_cb=None):
        super().__init__(parent)
        self.conn_data = dict(conn_data)
        self.colores = colores
        self.context = context
        self.open_native_cb = open_native_cb
        self.theme_name = self.conn_data.get("theme", "🟢 Hacker Esmeralda")
        if self.theme_name not in TERMINAL_THEMES:
            self.theme_name = "🟢 Hacker Esmeralda"

        self._build_ui()
        QTimer.singleShot(250, self._lanzar_comando_conexion_inicial)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)

        # Barra de Controles Compacta (idéntica en estilo a terminal_main.py)
        ctrl_bar = QFrame()
        ctrl_bar.setFixedHeight(32)
        ctrl_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        c_lay = QHBoxLayout(ctrl_bar)
        c_lay.setContentsMargins(8, 2, 8, 2)
        c_lay.setSpacing(5)

        proto = self.conn_data.get("proto", "SSH")
        ip = self.conn_data.get("ip", "127.0.0.1")
        port = self.conn_data.get("port", DEFAULT_PORTS.get(proto, 22))
        user = self.conn_data.get("user", "")
        target_str = f"{user}@{ip}:{port}" if user else f"{ip}:{port}"

        self.lbl_title = QLabel(f"📟 {proto} › {target_str}")
        self.lbl_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("color: #10B981; border: none; background: transparent;")
        c_lay.addWidget(self.lbl_title)

        c_lay.addStretch()

        combo_style = f"""
            QComboBox {{
                background-color: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 8pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white;
                selection-background-color: {self.colores['acento']};
            }}
        """

        # Selector de Snippets / Macros remotas
        self.combo_macros = QComboBox()
        for label, cmd in SSH_MACROS:
            self.combo_macros.addItem(label, cmd)
        self.combo_macros.setFixedWidth(125)
        self.combo_macros.setStyleSheet(combo_style)
        self.combo_macros.currentIndexChanged.connect(self._ejecutar_snippet_combo)
        c_lay.addWidget(self.combo_macros)

        # Selector de Tema igual a terminal_main.py
        self.combo_tema = QComboBox()
        self.combo_tema.addItems(list(TERMINAL_THEMES.keys()))
        self.combo_tema.setCurrentText(self.theme_name)
        self.combo_tema.setFixedWidth(135)
        self.combo_tema.setStyleSheet(combo_style)
        self.combo_tema.currentTextChanged.connect(self.cambiar_tema)
        c_lay.addWidget(self.combo_tema)

        btn_style = f"""
            QPushButton {{
                background-color: {self.colores['bg_principal']};
                color: white;
                padding: 2px 7px;
                border-radius: 4px;
                border: 1px solid rgba(255,255,255,0.08);
                font-size: 8pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colores['acento']};
                color: white;
            }}
        """

        btn_key = QPushButton("🔑 Clave")
        btn_key.setToolTip("Inyectar contraseña en la consola y copiar al portapapeles")
        btn_key.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_key.setStyleSheet(btn_style)
        btn_key.clicked.connect(self.inyectar_password)
        c_lay.addWidget(btn_key)

        btn_find = QPushButton("🔍")
        btn_find.setToolTip("Buscar en consola (Ctrl+F)")
        btn_find.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_find.setStyleSheet(btn_style)
        btn_find.clicked.connect(lambda: self.session.toggle_buscador() if hasattr(self, "session") else None)
        c_lay.addWidget(btn_find)

        btn_log = QPushButton("💾")
        btn_log.setToolTip("Exportar Log de consola")
        btn_log.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_log.setStyleSheet(btn_style)
        btn_log.clicked.connect(lambda: self.session.exportar_log() if hasattr(self, "session") else None)
        c_lay.addWidget(btn_log)

        btn_clear = QPushButton("🗑️")
        btn_clear.setToolTip("Limpiar consola (Ctrl+L)")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet(btn_style)
        btn_clear.clicked.connect(lambda: self.session.limpiar_consola() if hasattr(self, "session") else None)
        c_lay.addWidget(btn_clear)

        btn_restart = QPushButton("🔄")
        btn_restart.setToolTip("Reconectar / Reiniciar sesión")
        btn_restart.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restart.setStyleSheet(btn_style)
        btn_restart.clicked.connect(self.reconectar)
        c_lay.addWidget(btn_restart)

        btn_native = QPushButton("🪟")
        btn_native.setToolTip("Abrir en ventana de terminal nativa del SO")
        btn_native.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_native.setStyleSheet(btn_style)
        btn_native.clicked.connect(lambda: self.open_native_cb(self.conn_data) if callable(self.open_native_cb) else None)
        c_lay.addWidget(btn_native)

        lay.addWidget(ctrl_bar)

        # Instanciar RemoteSingleTerminalSession (basada en SingleTerminalSession de terminal_main.py)
        t_dict = TERMINAL_THEMES.get(self.theme_name, TERMINAL_THEMES["🟢 Hacker Esmeralda"])
        if TERMINAL_MODULE_AVAILABLE and SingleTerminalSession is not None:
            class _DummyCtx:
                app = None
            ctx = self.context or _DummyCtx()
            shell_cmd, shell_args, is_remote_pty = self._resolver_proceso_directo()
            self.session = RemoteSingleTerminalSession(
                parent=self,
                context=ctx,
                shell_cmd=shell_cmd,
                shell_args=shell_args,
                tema_dict=t_dict,
                ssh_password=self.conn_data.get("pass", ""),
                is_remote_pty=is_remote_pty,
            )
            f_size = int(self.conn_data.get("font", 11) or 11)
            f = self.session.terminal.font()
            f.setPointSize(f_size)
            self.session.terminal.setFont(f)
            lay.addWidget(self.session, 1)
        else:
            self.session = None
            self.fallback_box = QPlainTextEdit(self)
            lay.addWidget(self.fallback_box, 1)

    def _resolver_proceso_directo(self) -> tuple[str | None, list[str], bool]:
        """
        Determina el ejecutable y argumentos directos para iniciar dentro de QProcess
        evitando abrir una sub-shell intermedia cuando es SSH/SFTP/Telnet.
        """
        proto = self.conn_data.get("proto", "SSH")
        ip = self.conn_data.get("ip", "").strip()
        port = int(self.conn_data.get("port", DEFAULT_PORTS.get(proto, 22)) or 22)
        user = self.conn_data.get("user", "").strip()
        ssh_key = (self.conn_data.get("ssh_key") or "").strip()
        tunnel = (self.conn_data.get("ssh_tunnel") or "").strip()

        if not ip:
            return None, [], False

        if proto == "SSH":
            args = ["-tt", "-p", str(port), "-o", "StrictHostKeyChecking=accept-new"]
            if ssh_key and os.path.exists(ssh_key):
                args.extend(["-i", ssh_key])
            if tunnel:
                args.extend(tunnel.split())
            args.append(f"{user}@{ip}" if user else ip)
            return "ssh", args, True

        if proto == "SFTP":
            args = ["-P", str(port), "-o", "StrictHostKeyChecking=accept-new"]
            if ssh_key and os.path.exists(ssh_key):
                args.extend(["-i", ssh_key])
            args.append(f"{user}@{ip}" if user else ip)
            return "sftp", args, True

        if proto == "Telnet":
            return "telnet", [ip, str(port)], True

        if proto == "FTP":
            return "ftp", [ip], True

        return None, [], False

    def _lanzar_comando_conexion_inicial(self):
        pwd = self.conn_data.get("pass", "")
        if pwd:
            QGuiApplication.clipboard().setText(pwd)

        proto = self.conn_data.get("proto", "SSH")
        ip = self.conn_data.get("ip", "").strip()
        port = int(self.conn_data.get("port", DEFAULT_PORTS.get(proto, 22)) or 22)
        user = self.conn_data.get("user", "").strip()

        if ip and proto == "WinRM":
            cmd = f"Enter-PSSession -ComputerName {ip} -Port {port}" + (f" -Credential {user}" if user else "")
            self.enviar_comando(cmd)

        post_cmd = (self.conn_data.get("post_cmd") or "").strip()
        if post_cmd:
            QTimer.singleShot(1500, lambda: self.enviar_comando(post_cmd))

    def enviar_comando(self, cmd: str):
        if self.session and hasattr(self.session, "enviar_comando"):
            self.session.enviar_comando(cmd)
            self.session.terminal.setFocus()

    def inyectar_password(self):
        pwd = self.conn_data.get("pass", "")
        if not pwd:
            QMessageBox.information(self, "Sin Clave", "Esta conexión no tiene una contraseña guardada.")
            return
        QGuiApplication.clipboard().setText(pwd)
        if self.session and self.session.process and self.session.process.state() == QProcess.ProcessState.Running:
            line_end = "\r\n" if platform.system() == "Windows" else "\n"
            self.session.process.write((pwd + line_end).encode("utf-8"))
            self.session.lbl_status.setText("🔑 Clave inyectada y copiada")
            self.session.terminal.setFocus()

    def cambiar_tema(self, nombre_tema: str):
        if nombre_tema in TERMINAL_THEMES and self.session:
            self.theme_name = nombre_tema
            self.session.aplicar_tema(TERMINAL_THEMES[nombre_tema])

    def _ejecutar_snippet_combo(self, idx: int):
        if idx <= 0:
            return
        cmd = self.combo_macros.itemData(idx)
        if cmd:
            self.enviar_comando(cmd)
        self.combo_macros.setCurrentIndex(0)

    def reconectar(self):
        if self.session:
            self.session.reiniciar_proceso()
            QTimer.singleShot(400, self._lanzar_comando_conexion_inicial)

    def cerrar_sesion(self):
        if self.session and hasattr(self.session, "cleanup"):
            self.session.cleanup()


class MRemoteRDPSession(QWidget):
    """Pestaña compacta de control y lanzamiento directo de sesiones RDP / VNC con Single Sign-On (cmdkey)."""

    status_updated = pyqtSignal(str, str)

    def __init__(self, parent, conn_data: dict, colores: dict, launch_cb=None):
        super().__init__(parent)
        self.conn_data = dict(conn_data)
        self.colores = colores
        self.launch_cb = launch_cb
        self.status_updated.connect(self._on_status_ui)
        self._build_ui()
        QTimer.singleShot(200, lambda: self.lanzar_cliente(fullscreen=False))
        self._iniciar_monitor_puerto()

    def _on_status_ui(self, text: str, color: str):
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"color: {color}; border: none; background: transparent; font-weight: bold;")

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.07);
            }}
        """)
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(14, 10, 14, 10)
        c_lay.setSpacing(6)

        proto = self.conn_data.get("proto", "RDP")
        name = self.conn_data.get("name", "Servidor Remoto")
        ip = self.conn_data.get("ip", "")
        port = self.conn_data.get("port", DEFAULT_PORTS.get(proto, 3389))
        user = self.conn_data.get("user", "Administrador")
        domain = self.conn_data.get("domain", "")
        res = self.conn_data.get("resolution", "Smart Sizing (Ajustar)")

        top_r = QHBoxLayout()
        lbl_title = QLabel(f"🖥️ {proto}: {name} ({ip}:{port})")
        lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none; background: transparent;")
        top_r.addWidget(lbl_title)
        top_r.addStretch()

        self.lbl_status = QLabel("🟡 Verificando puerto...")
        self.lbl_status.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: #FBBF24; border: none; background: transparent;")
        top_r.addWidget(self.lbl_status)
        c_lay.addLayout(top_r)

        lbl_info = QLabel(
            f"Usuario: <b>{domain + '\\' if domain else ''}{user}</b> | Resolución: <b>{res}</b> | "
            f"{'🔑 SSO Activo ' if self.conn_data.get('rdp_sso', True) else ''}"
            f"{'📋 Portapapeles ' if self.conn_data.get('rdp_clipboard', True) else ''}"
            f"{'💾 Discos ' if self.conn_data.get('rdp_drives', False) else ''}"
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 8.5pt; border: none; background: transparent;")
        c_lay.addWidget(lbl_info)

        row_btns = QHBoxLayout()
        row_btns.setSpacing(6)

        def _mk_btn(txt, bg, fn):
            b = QPushButton(txt)
            b.setFixedHeight(28)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {bg};
                    color: white;
                    font-weight: bold;
                    border-radius: 5px;
                    padding: 0 10px;
                    font-size: 8pt;
                    border: none;
                }}
                QPushButton:hover {{ opacity: 0.9; }}
            """)
            b.clicked.connect(fn)
            return b

        row_btns.addWidget(_mk_btn("🚀 Reconectar RDP", self.colores['acento'], lambda: self.lanzar_cliente(fullscreen=False)))
        row_btns.addWidget(_mk_btn("📺 Pantalla Completa", "#0284C7", lambda: self.lanzar_cliente(fullscreen=True)))
        row_btns.addWidget(_mk_btn("🛡️ /admin", "#7C3AED", lambda: self.lanzar_cliente(admin=True)))
        row_btns.addWidget(_mk_btn("📄 Exportar .rdp", "#059669", self.exportar_archivo_rdp))
        if platform.system() == "Windows":
            row_btns.addWidget(_mk_btn("🧹 Limpiar SSO", "#DC2626", self.limpiar_credencial_sso))
        row_btns.addStretch()
        c_lay.addLayout(row_btns)

        lay.addWidget(card)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
                padding: 8px;
                font-family: Consolas;
                font-size: 8.5pt;
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
            self._log(f"Iniciando visor VNC hacia {ip}:{port}...")
            for client in ["tvnviewer", "vncviewer"]:
                try:
                    subprocess.Popen([client, f"{ip}:{port}"])
                    self._log(f"Cliente {client} lanzado.")
                    return
                except Exception:
                    continue
            self._log("⚠️ Visor VNC externo no detectado en PATH. Clave copiada al portapapeles.")
            return

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
                self._log(f"🔑 Credencial SSO registrada en Windows Vault (TERMSRV/{ip}).")

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
            self._log(f"✅ Exportado a: {ruta}")

    def limpiar_credencial_sso(self):
        ip = self.conn_data.get("ip", "").strip()
        port = self.conn_data.get("port", 3389)
        if platform.system() == "Windows" and ip:
            for target in (f"TERMSRV/{ip}", f"TERMSRV/{ip}:{port}"):
                subprocess.run(["cmdkey", f"/delete:{target}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
            self._log(f"🧹 Credencial SSO eliminada para {ip}.")

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
                    self.status_updated.emit(f"🟢 TCP {port} Activo ({ms} ms)", "#34D399")
            except Exception:
                self.status_updated.emit(f"🔴 TCP {port} Sin respuesta", "#F87171")

        threading.Thread(target=_probe, daemon=True).start()

    def cerrar_sesion(self):
        if hasattr(self, "_timer_mon"):
            self._timer_mon.stop()


class MRemoteWebSession(QWidget):
    """Pestaña de administración web embebida (HTTP/HTTPS)."""

    def __init__(self, parent, conn_data: dict, colores: dict):
        super().__init__(parent)
        self.conn_data = dict(conn_data)
        self.colores = colores
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)

        proto = self.conn_data.get("proto", "HTTPS").lower()
        ip = self.conn_data.get("ip", "localhost").strip()
        port = self.conn_data.get("port", 443 if proto == "https" else 80)
        if ip.startswith("http://") or ip.startswith("https://"):
            url = ip
        else:
            default_p = 443 if proto == "https" else 80
            url = f"{proto}://{ip}" if int(port) == default_p else f"{proto}://{ip}:{port}"

        nav = QFrame()
        nav.setFixedHeight(30)
        nav.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 5px;")
        nav_lay = QHBoxLayout(nav)
        nav_lay.setContentsMargins(6, 2, 6, 2)
        nav_lay.setSpacing(4)

        self.txt_url = QLineEdit(url)
        self.txt_url.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 4px; padding: 2px 6px; font-size: 8.5pt;")
        nav_lay.addWidget(self.txt_url, 1)

        btn_go = QPushButton("🔄 Ir")
        btn_go.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 4px; padding: 2px 8px; font-size: 8pt; font-weight: bold;")
        nav_lay.addWidget(btn_go)

        btn_ext = QPushButton("🌐 Externo")
        btn_ext.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 4px; padding: 2px 8px; font-size: 8pt;")
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
            lbl = QLabel(f"Panel Web: <a href='{url}' style='color:{self.colores['acento']};'>{url}</a>")
            lbl.setOpenExternalLinks(True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(lbl, 1)

    def cerrar_sesion(self):
        pass


class TabRemote(QWidget):
    """
    Submódulo compacto y 100% responsivo de Conexiones Remotas estilo mRemoteNG:
    - Señales Qt thread-safe (host_status_signal / port_scan_signal) para que el indicador 🟢/🔴 registre siempre al instante
    - Consola integrada usando exactamente SingleTerminalSession de terminal_main.py
    - Diseño compacto y scrollable que no colisiona al reducir el tamaño de la ventana
    """

    # Señales thread-safe hacia el hilo principal de Qt
    host_status_signal = pyqtSignal(str, bool, object, str)  # ip, online, latency_ms, method
    port_scan_signal = pyqtSignal(str, list)                  # host, lista_resultados

    def __init__(self, parent, colores, callbacks, context=None):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks or {}
        self.context = context

        if self.context and hasattr(self.context, "ruta_usuario") and self.context.ruta_usuario:
            self.archivo_datos = Path(self.context.ruta_usuario) / "conexiones_remotas.json"
        else:
            self.archivo_datos = get_data_path() / "conexiones_remotas.json"

        self._status_cache = {}
        self._updating_form = False

        # Conectar señales de hilos secundarios al hilo principal GUI
        self.host_status_signal.connect(self._on_host_status_received)
        self.port_scan_signal.connect(self._mostrar_resultados_escaneo)

        self.inicializar_ui()

    def inicializar_ui(self):
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(6, 6, 6, 6)
        self.layout_principal.setSpacing(5)

        # 1. Barra Superior Compacta Quick Connect (32px)
        self._build_top_quick_bar()

        # 2. Splitter Central Responsivo
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
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
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setSizes([270, 680])

        self.layout_principal.addWidget(self.splitter, 1)

        self.cargar_conexiones()
        self.actualizar_matriz_hosts()

    def _build_top_quick_bar(self):
        top_bar = QFrame()
        top_bar.setFixedHeight(34)
        top_bar.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 7px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        t_lay = QHBoxLayout(top_bar)
        t_lay.setContentsMargins(8, 3, 8, 3)
        t_lay.setSpacing(5)

        lbl_qc = QLabel("⚡ Quick:")
        lbl_qc.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_qc.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        t_lay.addWidget(lbl_qc)

        self.txt_quick_host = QLineEdit()
        self.txt_quick_host.setPlaceholderText("user@host:port o IP...")
        self.txt_quick_host.setMinimumWidth(80)
        self.txt_quick_host.setFixedHeight(24)
        self.txt_quick_host.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 8.5pt;
            }}
            QLineEdit:focus {{ border: 1px solid {self.colores['acento']}; }}
        """)
        self.txt_quick_host.returnPressed.connect(self.conectar_rapido)
        t_lay.addWidget(self.txt_quick_host, 1)

        self.combo_quick_proto = QComboBox()
        self.combo_quick_proto.addItems(list(DEFAULT_PORTS.keys()))
        self.combo_quick_proto.setFixedSize(76, 24)
        self.combo_quick_proto.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px;
                padding: 1px 5px;
                font-size: 8pt;
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
        self.spin_quick_port.setFixedSize(64, 24)
        self.spin_quick_port.setStyleSheet(self.txt_quick_host.styleSheet())
        t_lay.addWidget(self.spin_quick_port)

        btn_qc_go = QPushButton("🚀 Ir")
        btn_qc_go.setToolTip("Conectar inmediatamente en una pestaña")
        btn_qc_go.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_qc_go.setFixedHeight(24)
        btn_qc_go.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 0 9px;
                font-size: 8pt;
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
                border-radius: 4px;
                padding: 0 7px;
                font-size: 8pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {self.colores['acento']}44;
                border: 1px solid {self.colores['acento']};
            }}
        """

        btn_local_term = QPushButton("📟 Consola Local")
        btn_local_term.setFixedHeight(24)
        btn_local_term.setToolTip("Abrir pestaña de Terminal Interactiva Local (PowerShell/Bash)")
        btn_local_term.setStyleSheet(btn_tool_style)
        btn_local_term.clicked.connect(self.abrir_terminal_local)
        t_lay.addWidget(btn_local_term)

        btn_ping_all = QPushButton("📡 Ping")
        btn_ping_all.setFixedHeight(24)
        btn_ping_all.setToolTip("Comprobar estado Online/Offline de todos los hosts")
        btn_ping_all.setStyleSheet(btn_tool_style)
        btn_ping_all.clicked.connect(self.ping_todos_los_hosts)
        t_lay.addWidget(btn_ping_all)

        btn_import = QPushButton("📥")
        btn_import.setFixedSize(26, 24)
        btn_import.setToolTip("Importar conexiones (mRemoteNG XML, JSON, CSV)")
        btn_import.setStyleSheet(btn_tool_style)
        btn_import.clicked.connect(self.importar_conexiones_dialogo)
        t_lay.addWidget(btn_import)

        btn_export = QPushButton("📤")
        btn_export.setFixedSize(26, 24)
        btn_export.setToolTip("Exportar conexiones (mRemoteNG XML, JSON, CSV)")
        btn_export.setStyleSheet(btn_tool_style)
        btn_export.clicked.connect(self.exportar_conexiones_dialogo)
        t_lay.addWidget(btn_export)

        self.layout_principal.addWidget(top_bar)

    def _build_left_panel(self):
        self.panel_izq = QFrame()
        self.panel_izq.setMinimumWidth(215)
        self.panel_izq.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        layout_izq = QVBoxLayout(self.panel_izq)
        layout_izq.setContentsMargins(6, 6, 6, 6)
        layout_izq.setSpacing(4)

        self.left_vsplitter = QSplitter(Qt.Orientation.Vertical)
        self.left_vsplitter.setChildrenCollapsible(False)
        self.left_vsplitter.setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.08); height: 2px; }")

        # ── Parte Superior Izquierda: Árbol de Conexiones ──
        tree_container = QWidget()
        tree_lay = QVBoxLayout(tree_container)
        tree_lay.setContentsMargins(0, 0, 0, 2)
        tree_lay.setSpacing(4)

        hdr_lay = QHBoxLayout()
        hdr_lay.setSpacing(3)
        lbl_titulo_izq = QLabel("🖧 CONEXIONES")
        lbl_titulo_izq.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_titulo_izq.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        hdr_lay.addWidget(lbl_titulo_izq)
        hdr_lay.addStretch()

        btn_mini_style = f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px;
                padding: 1px 5px;
                font-size: 7.5pt;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {self.colores['acento']}; }}
        """
        btn_add_folder = QPushButton("📂+")
        btn_add_folder.setFixedHeight(22)
        btn_add_folder.setToolTip("Nueva carpeta/contenedor")
        btn_add_folder.setStyleSheet(btn_mini_style)
        btn_add_folder.clicked.connect(self.nueva_carpeta)
        hdr_lay.addWidget(btn_add_folder)

        btn_add_host = QPushButton("➕ Host")
        btn_add_host.setFixedHeight(22)
        btn_add_host.setToolTip("Nueva conexión remota")
        btn_add_host.setStyleSheet(btn_mini_style)
        btn_add_host.clicked.connect(self.nueva_conexion)
        hdr_lay.addWidget(btn_add_host)

        btn_dup = QPushButton("📋")
        btn_dup.setFixedHeight(22)
        btn_dup.setToolTip("Duplicar conexión seleccionada")
        btn_dup.setStyleSheet(btn_mini_style)
        btn_dup.clicked.connect(self.duplicar_conexion_seleccionada)
        hdr_lay.addWidget(btn_dup)

        btn_del_node = QPushButton("🗑️")
        btn_del_node.setFixedHeight(22)
        btn_del_node.setToolTip("Eliminar seleccionado")
        btn_del_node.setStyleSheet(btn_mini_style.replace(self.colores['acento'], self.colores.get('error', '#E53935')))
        btn_del_node.clicked.connect(self.eliminar_conexion)
        hdr_lay.addWidget(btn_del_node)

        tree_lay.addLayout(hdr_lay)

        self.txt_filtro_arbol = QLineEdit()
        self.txt_filtro_arbol.setPlaceholderText("🔍 Filtrar árbol...")
        self.txt_filtro_arbol.setFixedHeight(22)
        self.txt_filtro_arbol.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 8pt;
            }}
        """)
        self.txt_filtro_arbol.textChanged.connect(self._filtrar_arbol)
        tree_lay.addWidget(self.txt_filtro_arbol)

        self.arbol_conexiones = QTreeWidget()
        self.arbol_conexiones.setHeaderHidden(True)
        self.arbol_conexiones.setIndentation(14)
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
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 5px;
                outline: none;
                padding: 2px;
                font-size: 8.5pt;
            }}
            QTreeWidget::item {{
                padding: 3px 5px;
                border-radius: 3px;
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

        # ── Parte Inferior Izquierda: Inspector Config mRemoteNG Compacto y Scrollable ──
        config_container = QWidget()
        cfg_lay = QVBoxLayout(config_container)
        cfg_lay.setContentsMargins(0, 2, 0, 0)
        cfg_lay.setSpacing(4)

        self.tabs_inspector = QTabWidget()
        self.tabs_inspector.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {self.colores['bg_terciario']};
                border-radius: 5px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
            QTabBar::tab {{
                background: {self.colores['bg_principal']};
                color: {self.colores['fg_secundario']};
                padding: 3px 7px;
                font-size: 7.5pt;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 1px;
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
                border-radius: 4px;
                padding: 2px 5px;
                height: 20px;
                font-size: 8pt;
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
        estilo_lbl = f"color: {self.colores['fg_secundario']}; font-size: 7.8pt; font-weight: bold; border: none;"

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet(estilo_lbl)
            return l

        def _wrap_scroll(w: QWidget) -> QScrollArea:
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QFrame.Shape.NoFrame)
            sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            sa.setStyleSheet("QScrollArea { background: transparent; border: none; }")
            sa.setWidget(w)
            return sa

        # Tab 1: General
        tab_gen = QWidget()
        f_gen = QFormLayout(tab_gen)
        f_gen.setContentsMargins(6, 6, 6, 6)
        f_gen.setSpacing(4)

        self.txt_nombre = QLineEdit()
        self.txt_nombre.setStyleSheet(estilo_input)

        lay_ip = QHBoxLayout()
        lay_ip.setContentsMargins(0, 0, 0, 0)
        lay_ip.setSpacing(4)
        self.txt_ip = QLineEdit()
        self.txt_ip.setPlaceholderText("IP o Host (ej. 127.0.0.1)")
        self.txt_ip.setStyleSheet(estilo_input)
        self.txt_ip.textChanged.connect(self._iniciar_chequeo_ping)

        self.lbl_estado = QPushButton("⚫")
        self.lbl_estado.setFixedSize(22, 22)
        self.lbl_estado.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_estado.setToolTip("Clic para comprobar conectividad ahora mismo")
        self.lbl_estado.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        self.lbl_estado.clicked.connect(self._forzar_chequeo_ip_actual)
        lay_ip.addWidget(self.txt_ip, 1)
        lay_ip.addWidget(self.lbl_estado)

        lay_proto_port = QHBoxLayout()
        lay_proto_port.setContentsMargins(0, 0, 0, 0)
        lay_proto_port.setSpacing(4)
        self.combo_proto = QComboBox()
        self.combo_proto.addItems(list(DEFAULT_PORTS.keys()))
        self.combo_proto.setStyleSheet(estilo_input)
        self.combo_proto.currentTextChanged.connect(self._on_proto_changed)

        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(22)
        self.spin_port.setFixedWidth(58)
        self.spin_port.setStyleSheet(estilo_input)
        self.spin_port.valueChanged.connect(lambda _: self._iniciar_chequeo_ping(self.txt_ip.text()))
        lay_proto_port.addWidget(self.combo_proto, 1)
        lay_proto_port.addWidget(self.spin_port)

        self.combo_tag = QComboBox()
        self.combo_tag.addItems(["Producción", "Desarrollo", "Staging", "Laboratorio", "Crítico", "General"])
        self.combo_tag.setStyleSheet(estilo_input)

        self.txt_notas = QLineEdit()
        self.txt_notas.setPlaceholderText("Notas...")
        self.txt_notas.setStyleSheet(estilo_input)

        f_gen.addRow(_lbl("Nombre:"), self.txt_nombre)
        f_gen.addRow(_lbl("Host/IP:"), lay_ip)
        f_gen.addRow(_lbl("Proto/Pto:"), lay_proto_port)
        f_gen.addRow(_lbl("Entorno:"), self.combo_tag)
        f_gen.addRow(_lbl("Notas:"), self.txt_notas)
        self.tabs_inspector.addTab(_wrap_scroll(tab_gen), "🌐 General")

        # Tab 2: Auth & Herencia
        tab_auth = QWidget()
        f_auth = QFormLayout(tab_auth)
        f_auth.setContentsMargins(6, 6, 6, 6)
        f_auth.setSpacing(4)

        self.chk_heredar_auth = QCheckBox("🔗 Heredar de carpeta padre")
        self.chk_heredar_auth.setStyleSheet("color: #60A5FA; font-size: 7.8pt; font-weight: bold;")
        f_auth.addRow(self.chk_heredar_auth)

        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("root / admin")
        self.txt_usuario.setStyleSheet(estilo_input)

        lay_pass = QHBoxLayout()
        lay_pass.setContentsMargins(0, 0, 0, 0)
        lay_pass.setSpacing(3)
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("Clave SSH / RDP SSO")
        self.txt_pass.setStyleSheet(estilo_input)

        btn_eye = QPushButton("👁️")
        btn_eye.setFixedSize(22, 22)
        btn_eye.setStyleSheet(btn_mini_style)
        btn_eye.clicked.connect(
            lambda: self.txt_pass.setEchoMode(
                QLineEdit.EchoMode.Normal if self.txt_pass.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password
            )
        )
        lay_pass.addWidget(self.txt_pass, 1)
        lay_pass.addWidget(btn_eye)

        self.txt_dominio = QLineEdit()
        self.txt_dominio.setPlaceholderText("Dominio AD / WORKGROUP")
        self.txt_dominio.setStyleSheet(estilo_input)

        lay_key = QHBoxLayout()
        lay_key.setContentsMargins(0, 0, 0, 0)
        lay_key.setSpacing(3)
        self.txt_ssh_key = QLineEdit()
        self.txt_ssh_key.setPlaceholderText("Clave .pem / id_rsa")
        self.txt_ssh_key.setStyleSheet(estilo_input)
        btn_key = QPushButton("📂")
        btn_key.setFixedSize(22, 22)
        btn_key.setStyleSheet(btn_mini_style)
        btn_key.clicked.connect(self._seleccionar_clave_ssh)
        lay_key.addWidget(self.txt_ssh_key, 1)
        lay_key.addWidget(btn_key)

        f_auth.addRow(_lbl("Usuario:"), self.txt_usuario)
        f_auth.addRow(_lbl("Clave:"), lay_pass)
        f_auth.addRow(_lbl("Dominio:"), self.txt_dominio)
        f_auth.addRow(_lbl("SSH Key:"), lay_key)
        self.tabs_inspector.addTab(_wrap_scroll(tab_auth), "🔐 Auth")

        # Tab 3: Recursos RDP & Consola
        tab_adv = QWidget()
        f_adv = QFormLayout(tab_adv)
        f_adv.setContentsMargins(6, 6, 6, 6)
        f_adv.setSpacing(4)

        self.combo_resolucion = QComboBox()
        self.combo_resolucion.addItems(["Smart Sizing (Ajustar)", "Pantalla Completa (/f)", "1920x1080", "1600x900", "1366x768", "1280x720"])
        self.combo_resolucion.setStyleSheet(estilo_input)

        lay_theme_font = QHBoxLayout()
        lay_theme_font.setContentsMargins(0, 0, 0, 0)
        lay_theme_font.setSpacing(3)
        self.combo_tema_term = QComboBox()
        self.combo_tema_term.addItems(list(TERMINAL_THEMES.keys()))
        self.combo_tema_term.setStyleSheet(estilo_input)

        self.spin_font = QSpinBox()
        self.spin_font.setRange(8, 28)
        self.spin_font.setValue(11)
        self.spin_font.setFixedWidth(48)
        self.spin_font.setStyleSheet(estilo_input)
        lay_theme_font.addWidget(self.combo_tema_term, 1)
        lay_theme_font.addWidget(self.spin_font)

        self.txt_ssh_tunnel = QLineEdit()
        self.txt_ssh_tunnel.setPlaceholderText("-L 8080:127.0.0.1:80")
        self.txt_ssh_tunnel.setStyleSheet(estilo_input)

        self.txt_post_cmd = QLineEdit()
        self.txt_post_cmd.setPlaceholderText("Comando inicial (ej. htop)")
        self.txt_post_cmd.setStyleSheet(estilo_input)

        # Grid 2x2 para que las casillas nunca choquen en paneles estrechos
        chk_grid = QGridLayout()
        chk_grid.setContentsMargins(0, 0, 0, 0)
        chk_grid.setSpacing(3)
        self.chk_rdp_sso = QCheckBox("🔑 SSO")
        self.chk_rdp_sso.setChecked(True)
        self.chk_rdp_admin = QCheckBox("🛡️ /admin")
        self.chk_rdp_clipboard = QCheckBox("📋 Portapapeles")
        self.chk_rdp_clipboard.setChecked(True)
        self.chk_rdp_drives = QCheckBox("💾 Discos")
        self.chk_rdp_audio = QCheckBox("🔊 Audio")
        self.chk_rdp_audio.setChecked(True)
        for idx_c, c in enumerate((self.chk_rdp_sso, self.chk_rdp_admin, self.chk_rdp_clipboard, self.chk_rdp_drives)):
            c.setStyleSheet("color: #D1D5DB; font-size: 7.5pt;")
            chk_grid.addWidget(c, idx_c // 2, idx_c % 2)

        f_adv.addRow(_lbl("RDP Res:"), self.combo_resolucion)
        f_adv.addRow(_lbl("Consola:"), lay_theme_font)
        f_adv.addRow(_lbl("Túnel:"), self.txt_ssh_tunnel)
        f_adv.addRow(_lbl("PostCmd:"), self.txt_post_cmd)
        f_adv.addRow(_lbl("RDP Opt:"), chk_grid)
        self.tabs_inspector.addTab(_wrap_scroll(tab_adv), "🖥️ Avanzado")

        cfg_lay.addWidget(self.tabs_inspector, 1)

        # Botonera compacta del Inspector
        btn_accion_layout = QHBoxLayout()
        btn_accion_layout.setSpacing(4)

        self.btn_guardar = QPushButton("💾 Guardar")
        self.btn_guardar.setFixedHeight(26)
        self.btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guardar.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('exito', '#22c55e')};
                color: white;
                font-weight: bold;
                border-radius: 5px;
                border: none;
                font-size: 8pt;
                padding: 0 8px;
            }}
            QPushButton:hover {{ background: #16a34a; }}
        """)
        self.btn_guardar.clicked.connect(self.guardar_perfil)

        self.btn_conectar = QPushButton("🚀 Conectar")
        self.btn_conectar.setFixedHeight(26)
        self.btn_conectar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_conectar.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                font-weight: bold;
                border-radius: 5px;
                border: none;
                font-size: 8pt;
                padding: 0 8px;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        self.btn_conectar.clicked.connect(self.conectar)

        self.btn_conectar_ext = QPushButton("🪟")
        self.btn_conectar_ext.setFixedSize(28, 26)
        self.btn_conectar_ext.setToolTip("Abrir en ventana nativa externa del SO")
        self.btn_conectar_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_conectar_ext.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: white;
                font-weight: bold;
                border-radius: 5px;
                border: 1px solid rgba(255,255,255,0.1);
                font-size: 8pt;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.12); }}
        """)
        self.btn_conectar_ext.clicked.connect(lambda: self.conectar(forzar_externa=True))

        btn_accion_layout.addWidget(self.btn_guardar)
        btn_accion_layout.addWidget(self.btn_conectar, 1)
        btn_accion_layout.addWidget(self.btn_conectar_ext)
        cfg_lay.addLayout(btn_accion_layout)

        self.left_vsplitter.addWidget(config_container)
        self.left_vsplitter.setSizes([260, 220])
        layout_izq.addWidget(self.left_vsplitter)

    def _build_right_workspace(self):
        self.panel_der_container = QFrame()
        self.panel_der_container.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        r_lay = QVBoxLayout(self.panel_der_container)
        r_lay.setContentsMargins(6, 6, 6, 6)
        r_lay.setSpacing(5)

        self.tabs_sesiones = QTabWidget()
        self.tabs_sesiones.setTabsClosable(True)
        self.tabs_sesiones.setMovable(True)
        self.tabs_sesiones.tabCloseRequested.connect(self._cerrar_pestana_sesion)
        self.tabs_sesiones.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {self.colores['bg_principal']};
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            QTabBar::tab {{
                background: {self.colores['bg_terciario']};
                color: {self.colores['fg_secundario']};
                padding: 5px 11px;
                font-size: 8.5pt;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['bg_principal']};
                color: {self.colores['acento']};
                font-weight: bold;
                border-top: 2px solid {self.colores['acento']};
            }}
        """)

        self._build_dashboard_tab()
        self.tabs_sesiones.addTab(self.tab_dashboard_scroll, "📊 Panel & Escáner")
        self.tabs_sesiones.tabBar().setTabButton(0, self.tabs_sesiones.tabBar().ButtonPosition.RightSide, None)

        r_lay.addWidget(self.tabs_sesiones, 1)

        # Barra Inferior Compacta Multi-SSH Broadcast (28px)
        bcast_frame = QFrame()
        bcast_frame.setFixedHeight(28)
        bcast_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_terciario']};
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        b_lay = QHBoxLayout(bcast_frame)
        b_lay.setContentsMargins(8, 2, 6, 2)
        b_lay.setSpacing(6)

        lbl_bcast = QLabel("📡 Broadcast:")
        lbl_bcast.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_bcast.setStyleSheet("color: #FBBF24; border: none; background: transparent;")
        b_lay.addWidget(lbl_bcast)

        self.txt_broadcast = QLineEdit()
        self.txt_broadcast.setPlaceholderText("Enviar comando a todas las pestañas de terminal abiertas...")
        self.txt_broadcast.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px;
                padding: 1px 8px;
                font-family: Consolas;
                font-size: 8.5pt;
            }}
        """)
        self.txt_broadcast.returnPressed.connect(self.enviar_broadcast_terminales)
        b_lay.addWidget(self.txt_broadcast, 1)

        btn_bcast = QPushButton("⚡ Enviar")
        btn_bcast.setFixedHeight(22)
        btn_bcast.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_bcast.setStyleSheet("""
            QPushButton {
                background: #D97706;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 0 9px;
                border: none;
                font-size: 8pt;
            }
            QPushButton:hover { background: #B45309; }
        """)
        btn_bcast.clicked.connect(self.enviar_broadcast_terminales)
        b_lay.addWidget(btn_bcast)

        r_lay.addWidget(bcast_frame)

    def _build_dashboard_tab(self):
        self.tab_dashboard_mremote = QWidget()
        d_lay = QVBoxLayout(self.tab_dashboard_mremote)
        d_lay.setContentsMargins(8, 8, 8, 8)
        d_lay.setSpacing(8)

        # Fila de KPIs compactos en una sola línea (32px de alto)
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(6)

        def _mk_kpi_pill(titulo, valor, color):
            f = QFrame()
            f.setFixedHeight(32)
            f.setStyleSheet(f"""
                QFrame {{
                    background: {self.colores['bg_secundario']};
                    border-radius: 6px;
                    border: 1px solid rgba(255,255,255,0.06);
                }}
            """)
            fl = QHBoxLayout(f)
            fl.setContentsMargins(10, 2, 10, 2)
            fl.setSpacing(6)
            lt = QLabel(titulo)
            lt.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 8pt; font-weight: bold; border: none;")
            lv = QLabel(valor)
            lv.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lv.setStyleSheet(f"color: {color}; border: none;")
            fl.addWidget(lt)
            fl.addStretch()
            fl.addWidget(lv)
            return f, lv

        card1, self.lbl_kpi_total = _mk_kpi_pill("🖥️ Hosts:", "0", self.colores['acento'])
        card2, self.lbl_kpi_folders = _mk_kpi_pill("📂 Carpetas:", "0", "#60A5FA")
        card3, self.lbl_kpi_online = _mk_kpi_pill("🟢 Online:", "0", "#34D399")
        card4, self.lbl_kpi_sessions = _mk_kpi_pill("⚡ Sesiones:", "0", "#FBBF24")

        for c in (card1, card2, card3, card4):
            kpi_row.addWidget(c, 1)
        d_lay.addLayout(kpi_row)

        # Tabla compacta de Matriz de Servidores Guardados
        self.table_hosts = QTableWidget(0, 6)
        self.table_hosts.setMinimumHeight(140)
        self.table_hosts.setHorizontalHeaderLabels(["Estado", "Nombre", "Carpeta", "Proto", "Host:Puerto", "Usuario"])
        self.table_hosts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_hosts.verticalHeader().setVisible(False)
        self.table_hosts.verticalHeader().setDefaultSectionSize(24)
        self.table_hosts.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_hosts.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_hosts.setStyleSheet(f"""
            QTableWidget {{
                background: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
                gridline-color: rgba(255,255,255,0.04);
                font-size: 8.5pt;
            }}
            QHeaderView::section {{
                background: {self.colores['bg_terciario']};
                color: {self.colores['fg_secundario']};
                padding: 4px;
                border: none;
                font-weight: bold;
                font-size: 8pt;
            }}
        """)
        self.table_hosts.cellDoubleClicked.connect(self._on_matrix_double_clicked)
        d_lay.addWidget(self.table_hosts, 1)

        # Escáner de Puertos Compacto
        scan_box = QFrame()
        scan_box.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        s_lay = QVBoxLayout(scan_box)
        s_lay.setContentsMargins(8, 6, 8, 6)
        s_lay.setSpacing(5)

        s_top = QHBoxLayout()
        s_top.setSpacing(6)
        lbl_sc = QLabel("🔍 Escáner de Puertos:")
        lbl_sc.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_sc.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        s_top.addWidget(lbl_sc)

        self.txt_scan_host = QLineEdit()
        self.txt_scan_host.setPlaceholderText("IP o Host (ej. 127.0.0.1)")
        self.txt_scan_host.setFixedHeight(22)
        self.txt_scan_host.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white; border-radius: 4px; padding: 2px 6px; font-size: 8pt;")
        s_top.addWidget(self.txt_scan_host, 1)

        self.btn_scan_ports = QPushButton("🔍 Escanear")
        self.btn_scan_ports.setFixedHeight(22)
        self.btn_scan_ports.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan_ports.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 8pt;
                border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        self.btn_scan_ports.clicked.connect(self.ejecutar_escaneo_puertos_ui)
        s_top.addWidget(self.btn_scan_ports)
        s_lay.addLayout(s_top)

        self.lbl_scan_results = QLabel("Selecciona un host o ingresa una IP para detectar puertos activos (SSH, RDP, HTTP/S, VNC, WinRM, DB).")
        self.lbl_scan_results.setWordWrap(True)
        self.lbl_scan_results.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 8pt; border: none;")
        s_lay.addWidget(self.lbl_scan_results)

        d_lay.addWidget(scan_box)

        self.tab_dashboard_scroll = QScrollArea()
        self.tab_dashboard_scroll.setWidgetResizable(True)
        self.tab_dashboard_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.tab_dashboard_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.tab_dashboard_scroll.setWidget(self.tab_dashboard_mremote)

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
        # Verificar conectividad inicial de todos los hosts en segundo plano
        QTimer.singleShot(300, self.ping_todos_los_hosts)

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
        ip = (data.get("ip") or "").strip()
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
        item.setText(0, f"{dot} {icon} {name}{lat}")

    def _serializar_nodos_recursivo(self, parent_item: QTreeWidgetItem) -> list:
        resultado = []
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            data = dict(child.data(0, Qt.ItemDataRole.UserRole) or {})
            if data.get("type") == "folder" or (child.childCount() > 0 and not data.get("ip")):
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
            "notes": "",
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
            "font": 11,
            "theme": "🟢 Hacker Esmeralda",
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
            self.lbl_estado.setText("⚫")
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
            self.spin_font.setValue(int(data.get("font", 11) or 11))
            self.combo_tag.setCurrentText(data.get("tag", "Producción"))
            self.combo_resolucion.setCurrentText(data.get("resolution", "Smart Sizing (Ajustar)"))

            theme_saved = data.get("theme", "🟢 Hacker Esmeralda")
            if theme_saved not in TERMINAL_THEMES:
                theme_saved = "🟢 Hacker Esmeralda"
            self.combo_tema_term.setCurrentText(theme_saved)

            self.txt_ssh_tunnel.setText(data.get("ssh_tunnel", ""))
            self.txt_post_cmd.setText(data.get("post_cmd", ""))

            self.chk_heredar_auth.setChecked(bool(data.get("inherit_auth", False)))
            self.chk_rdp_sso.setChecked(bool(data.get("rdp_sso", True)))
            self.chk_rdp_admin.setChecked(bool(data.get("rdp_admin", False)))
            self.chk_rdp_clipboard.setChecked(bool(data.get("rdp_clipboard", True)))
            self.chk_rdp_drives.setChecked(bool(data.get("rdp_drives", False)))
            self.chk_rdp_audio.setChecked(bool(data.get("rdp_audio", True)))

            ip_val = (data.get("ip") or "").strip()
            if ip_val:
                self.txt_scan_host.setText(ip_val)
                # Mostrar caché inmediata si ya existe y lanzar verificación en vivo
                cached = self._status_cache.get(ip_val)
                if cached is not None:
                    self.lbl_estado.setText("🟢" if cached.get("online") else "🔴")
                else:
                    self.lbl_estado.setText("🟡")
                self._forzar_chequeo_ip_actual()
            else:
                self.lbl_estado.setText("⚫")
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
        if not is_folder and data["ip"]:
            self._forzar_chequeo_ip_actual()

        texto_orig = self.btn_guardar.text()
        self.btn_guardar.setText("✅ OK")
        QTimer.singleShot(1200, lambda: self.btn_guardar.setText(texto_orig))

    def _on_proto_changed(self, proto: str):
        if not self._updating_form:
            self.spin_port.setValue(DEFAULT_PORTS.get(proto, 22))

    def _seleccionar_clave_ssh(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar Clave Privada SSH", str(Path.home()), "SSH Keys (*.pem *.ppk *.key *id_rsa* *);;All Files (*)")
        if ruta:
            self.txt_ssh_key.setText(ruta)

    # ──────────────────────────────────────────────────────────────────────────
    #  CONEXIÓN EN PESTAÑAS INTEGRADAS Y VENTANAS NATIVAS
    # ──────────────────────────────────────────────────────────────────────────
    def abrir_terminal_local(self):
        """Abre una pestaña de Terminal Interactiva Local idéntica a terminal_main.py."""
        conn_data = {
            "type": "connection",
            "name": f"Shell Local #{self.tabs_sesiones.count()}",
            "ip": "",
            "port": 0,
            "user": "",
            "pass": "",
            "proto": "SSH",
            "font": 11,
            "theme": "🟢 Hacker Esmeralda",
        }
        tab = MRemoteTerminalSession(
            self.tabs_sesiones,
            conn_data,
            self.colores,
            context=self.context,
            open_native_cb=self._lanzar_consola_nativa_externa,
        )
        idx = self.tabs_sesiones.addTab(tab, f"📟 Shell #{self.tabs_sesiones.count()}")
        self.tabs_sesiones.setCurrentIndex(idx)
        self.actualizar_vista_vacia()

    def conectar_rapido(self):
        raw = self.txt_quick_host.text().strip()
        if not raw:
            self.abrir_terminal_local()
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
            "name": f"{host}",
            "ip": host,
            "port": port,
            "user": user,
            "pass": "",
            "proto": proto,
            "font": 11,
            "theme": "🟢 Hacker Esmeralda",
            "rdp_sso": True,
            "rdp_clipboard": True,
            "rdp_audio": True,
        }
        self._abrir_sesion_mremote(conn_data, forzar_externa=False)

    def conectar(self, forzar_externa: bool = False):
        item = self.arbol_conexiones.currentItem()
        if item and item != self.raiz:
            d_item = item.data(0, Qt.ItemDataRole.UserRole) or {}
            if d_item.get("type") == "folder":
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
                context=self.context,
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
            QMessageBox.information(self, "Broadcast Multi-SSH", "No hay ninguna pestaña de terminal abierta actualmente.")

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
                font-size: 8.5pt;
            }}
            QMenu::item {{ padding: 5px 14px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {self.colores['acento']}; }}
        """)

        if not is_folder:
            act_tab = QAction("🚀 Conectar en Pestaña Integrada", self)
            act_tab.triggered.connect(lambda: self.conectar(forzar_externa=False))
            menu.addAction(act_tab)

            act_ext = QAction("🪟 Conectar en Ventana Externa", self)
            act_ext.triggered.connect(lambda: self.conectar(forzar_externa=True))
            menu.addAction(act_ext)

            act_as = QAction("👤 Conectar como...", self)
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
        usr, ok1 = QInputDialog.getText(self, "Conectar como...", "Usuario:", QLineEdit.EchoMode.Normal, self.txt_usuario.text())
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
            ip = (data.get("ip") or "").strip()
            proto = data.get("proto", "SSH")
            port = data.get("port", DEFAULT_PORTS.get(proto, 22))
            st = self._status_cache.get(ip)
            if st and st.get("online"):
                online_count += 1
                st_txt = f"🟢 Online ({st.get('latency_ms', 1)}ms)"
            elif st is not None:
                st_txt = "🔴 Offline"
            else:
                st_txt = "⚪ Pendiente"

            vals = [
                st_txt,
                data.get("name", "Host"),
                f"📁 {folder_name}",
                f"{PROTO_ICONS.get(proto, '🖧')} {proto}",
                f"{ip}:{port}",
                data.get("user", "-"),
            ]
            for col, val in enumerate(vals):
                tw = QTableWidgetItem(str(val))
                self.table_hosts.setItem(row, col, tw)

        self.actualizar_vista_vacia(online_count=online_count)

    def actualizar_vista_vacia(self, online_count: int = None):
        conns = self.obtener_todas_las_conexiones_planas()
        total_hosts = len(conns)

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
            online_count = sum(1 for _, d, _ in conns if self._status_cache.get((d.get("ip") or "").strip(), {}).get("online"))

        if hasattr(self, "lbl_kpi_total"):
            self.lbl_kpi_total.setText(str(total_hosts))
            self.lbl_kpi_folders.setText(str(folders))
            self.lbl_kpi_online.setText(str(online_count))
            active_tabs = max(0, self.tabs_sesiones.count() - 1) if hasattr(self, "tabs_sesiones") else 0
            self.lbl_kpi_sessions.setText(str(active_tabs))

    # ──────────────────────────────────────────────────────────────────────────
    #  VERIFICACIÓN DE IP / PING / PUERTO TCP THREAD-SAFE CON SEÑALES QT
    # ──────────────────────────────────────────────────────────────────────────
    def _iniciar_chequeo_ping(self, txt: str):
        ip = (txt or "").strip()
        if not ip:
            self.lbl_estado.setText("⚫")
            self.lbl_estado.setToolTip("Sin dirección IP/Host")
            return

        self.lbl_estado.setText("🟡")
        self.lbl_estado.setToolTip(f"Comprobando conectividad con {ip}...")

        if hasattr(self, "_timer_ping"):
            self._timer_ping.stop()
        else:
            self._timer_ping = QTimer(self)
            self._timer_ping.setSingleShot(True)
            self._timer_ping.timeout.connect(self._forzar_chequeo_ip_actual)

        self._timer_ping.start(550)

    def _forzar_chequeo_ip_actual(self):
        ip = self.txt_ip.text().strip()
        if not ip:
            self.lbl_estado.setText("⚫")
            return
        port = self.spin_port.value() if hasattr(self, "spin_port") else 22
        self.lbl_estado.setText("🟡")
        threading.Thread(target=self._probe_host_worker, args=(ip, port), daemon=True).start()

    def _probe_host_worker(self, ip: str, port: int):
        """Ejecuta la prueba de red en hilo secundario y emite host_status_signal al hilo principal Qt."""
        res = self._medir_conectividad_host(ip, port, timeout=0.85)
        self.host_status_signal.emit(
            ip,
            bool(res.get("online", False)),
            res.get("latency_ms"),
            str(res.get("method", "ICMP"))
        )

    def _medir_conectividad_host(self, ip: str, port: int = 0, timeout: float = 0.85) -> dict:
        fn = self.callbacks.get("verificar_host_remoto")
        if callable(fn):
            try:
                return fn(ip, port, timeout=timeout)
            except Exception:
                pass

        # 1. Intentar conexión TCP directa al puerto
        if port and int(port) > 0:
            t0 = time.perf_counter()
            try:
                with socket.create_connection((ip, int(port)), timeout=timeout):
                    ms = max(1, int((time.perf_counter() - t0) * 1000))
                    return {"online": True, "latency_ms": ms, "method": f"TCP:{port}"}
            except Exception:
                pass

        # 2. Intentar ICMP Ping del sistema
        cmd_args = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip] if platform.system() == "Windows" else ["ping", "-c", "1", "-W", "1", ip]
        kwargs = {"creationflags": 0x08000000} if platform.system() == "Windows" else {}
        t0 = time.perf_counter()
        try:
            r = subprocess.run(cmd_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
            if r.returncode == 0:
                ms = max(1, int((time.perf_counter() - t0) * 1000))
                return {"online": True, "latency_ms": ms, "method": "ICMP Ping"}
        except Exception:
            pass

        return {"online": False, "latency_ms": None, "method": "Sin respuesta"}

    def _on_host_status_received(self, ip: str, online: bool, latency_ms, method: str):
        """Slot ejecutado garantizadamente en el hilo principal de la GUI."""
        self._status_cache[ip] = {"online": online, "latency_ms": latency_ms, "method": method}

        # Si el campo txt_ip actual coincide con la IP comprobada, actualizar el círculo inmediatamente
        if self.txt_ip.text().strip() == ip:
            if online:
                self.lbl_estado.setText("🟢")
                self.lbl_estado.setToolTip(f"🟢 ACTIVO ({ip}) — {latency_ms or 1} ms vía {method}")
            else:
                self.lbl_estado.setText("🔴")
                self.lbl_estado.setToolTip(f"🔴 INACTIVO ({ip}) — No responde Ping ni puerto TCP")

        # Actualizar todos los nodos del árbol que tengan esa IP
        for item, data, _ in self.obtener_todas_las_conexiones_planas():
            if (data.get("ip") or "").strip() == ip:
                self._actualizar_etiqueta_item_arbol(item)

        self.actualizar_matriz_hosts()

    def _chequear_item_individual(self, item: QTreeWidgetItem):
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        ip = (data.get("ip") or "").strip()
        port = int(data.get("port", 22) or 22)
        if ip:
            threading.Thread(target=self._probe_host_worker, args=(ip, port), daemon=True).start()

    def ping_todos_los_hosts(self):
        conns = self.obtener_todas_las_conexiones_planas()
        if not conns:
            return

        def _worker():
            vistos = set()
            for _, data, _ in conns:
                ip = (data.get("ip") or "").strip()
                port = int(data.get("port", 22) or 22)
                if not ip or (ip, port) in vistos:
                    continue
                vistos.add((ip, port))
                res = self._medir_conectividad_host(ip, port, timeout=0.65)
                self.host_status_signal.emit(
                    ip,
                    bool(res.get("online", False)),
                    res.get("latency_ms"),
                    str(res.get("method", "ICMP"))
                )

        threading.Thread(target=_worker, daemon=True).start()

    def ejecutar_escaneo_puertos_ui(self):
        host = self.txt_scan_host.text().strip() or self.txt_ip.text().strip()
        if not host:
            QMessageBox.warning(self, "Escáner de Puertos", "Ingresa una IP o selecciona un servidor primero.")
            return

        self.lbl_scan_results.setText(f"⏳ Escaneando puertos comunes en <b>{host}</b>...")
        self.btn_scan_ports.setEnabled(False)

        def _scan():
            fn = self.callbacks.get("escanear_puertos_remotos")
            if callable(fn):
                resultados = fn(host)
            else:
                resultados = []
            self.port_scan_signal.emit(host, resultados)

        threading.Thread(target=_scan, daemon=True).start()

    def _mostrar_resultados_escaneo(self, host: str, resultados: list):
        self.btn_scan_ports.setEnabled(True)
        abiertos = [r for r in resultados if r.get("open")]
        if not abiertos:
            self.lbl_scan_results.setText(f"🔴 Sin puertos estándar abiertos detectados en <b>{host}</b>.")
            return

        badges = [
            f"<span style='background:#065F46; color:#34D399; padding:2px 6px; border-radius:4px; font-weight:bold;'>"
            f"🟢 {r['port']} ({r['service']}) · {r['latency_ms']}ms</span>"
            for r in abiertos
        ]
        self.lbl_scan_results.setText(f"<b>Abiertos en {host}:</b> &nbsp; " + " &nbsp; ".join(badges))

    # ──────────────────────────────────────────────────────────────────────────
    #  IMPORTACIÓN Y EXPORTACIÓN (mRemoteNG XML, JSON, CSV)
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
        QMessageBox.information(self, "Exportación Exitosa", f"Conexiones exportadas a:\n{ruta}")

    def _exportar_mremoteng_xml(self, ruta: str):
        root_el = ET.Element("mrng:Connections", {"xmlns:mrng": "http://mremoteng.org", "Export": "Multitool-mRemoteNG"})

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
                self.ping_todos_los_hosts()
                QMessageBox.information(self, "Importación Completada", f"Conexiones importadas desde:\n{Path(ruta).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Importar", f"No se pudo importar:\n{e}")

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
