import os
import sys
import platform
import re
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLineEdit, QPushButton, QLabel, QFrame, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, QProcess, QTimer, QProcessEnvironment
from PyQt6.QtGui import QFont, QColor, QTextCursor, QKeySequence, QShortcut

from ..utils.ansi_parser import AnsiParser

class InteractiveTerminalScreen(QTextEdit):
    """
    Consola interactiva directa estilo Windows Terminal / VS Code.
    El usuario escribe, autocompleta con Tab y ejecuta directamente en la pantalla de la terminal.
    """
    def __init__(self, session=None):
        super().__init__(session)
        self.session = session
        self._prompt_pos = 0
        self.setAcceptRichText(True)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def get_current_input(self) -> str:
        text = self.toPlainText()
        if self._prompt_pos <= len(text):
            return text[self._prompt_pos:]
        return ""

    def set_current_input(self, new_text: str):
        cursor = self.textCursor()
        cursor.setPosition(self._prompt_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(new_text)
        self.setTextCursor(cursor)

    def _pegar_en_prompt(self):
        cb = QApplication.clipboard()
        if cb and cb.text():
            cursor = self.textCursor()
            if cursor.position() < self._prompt_pos:
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.setTextCursor(cursor)
            cursor.insertText(cb.text())

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        # Atajos de Zoom y Control
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                if self.session: self.session.ajustar_zoom(1)
                event.accept()
                return
            elif key == Qt.Key.Key_Minus:
                if self.session: self.session.ajustar_zoom(-1)
                event.accept()
                return
            elif key == Qt.Key.Key_0:
                if self.session: self.session.reset_zoom()
                event.accept()
                return
            elif key == Qt.Key.Key_L:
                if self.session: self.session.limpiar_consola()
                event.accept()
                return
            elif key == Qt.Key.Key_C:
                if self.textCursor().hasSelection():
                    self.copy()
                else:
                    if self.session: self.session.enviar_interrupcion()
                event.accept()
                return
            elif key == Qt.Key.Key_V:
                self._pegar_en_prompt()
                event.accept()
                return

        # Ctrl+Shift+C / Ctrl+Shift+V
        if modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
            if key == Qt.Key.Key_C:
                self.copy()
                event.accept()
                return
            elif key == Qt.Key.Key_V:
                self._pegar_en_prompt()
                event.accept()
                return

        cursor = self.textCursor()

        # Enter / Return: Enviar comando
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cmd = self.get_current_input()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText("\n")
            self.setTextCursor(cursor)
            self._prompt_pos = self.textCursor().position()
            
            if self.session:
                self.session.enviar_comando(cmd, desde_teclado=True)
            event.accept()
            return

        # Backspace: Borrar carácter en el input actual
        elif key == Qt.Key.Key_Backspace:
            if cursor.position() > self._prompt_pos:
                super().keyPressEvent(event)
            else:
                event.accept()
            return

        # Delete: Borrar carácter hacia adelante
        elif key == Qt.Key.Key_Delete:
            if cursor.position() >= self._prompt_pos:
                super().keyPressEvent(event)
            else:
                event.accept()
            return

        # Tab: Autocompletado de rutas
        elif key == Qt.Key.Key_Tab:
            if self.session:
                self.session.auto_completar_tab()
            event.accept()
            return

        # Flecha Arriba: Historial anterior
        elif key == Qt.Key.Key_Up:
            if self.session:
                self.session.history_up()
            event.accept()
            return

        # Flecha Abajo: Historial posterior
        elif key == Qt.Key.Key_Down:
            if self.session:
                self.session.history_down()
            event.accept()
            return

        # Flecha Izquierda: Navegar dentro de la línea actual
        elif key == Qt.Key.Key_Left:
            if cursor.position() > self._prompt_pos:
                super().keyPressEvent(event)
            else:
                event.accept()
            return

        # Home / Inicio: Ir al inicio de la línea de comandos
        elif key == Qt.Key.Key_Home:
            cursor.setPosition(self._prompt_pos)
            self.setTextCursor(cursor)
            event.accept()
            return

        # End / Fin: Ir al final de la línea de comandos
        elif key == Qt.Key.Key_End:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            event.accept()
            return

        # Si el usuario presiona una tecla imprimible mientras el cursor está más arriba,
        # saltar automáticamente al prompt al final para escribir ahí
        text = event.text()
        if text and text.isprintable():
            if cursor.position() < self._prompt_pos:
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.setTextCursor(cursor)

        super().keyPressEvent(event)


class SingleTerminalSession(QWidget):
    """Módulo de sesión de terminal interactiva unificada con soporte Git y detección dinámica de CWD"""
    def __init__(self, parent, context, shell_cmd=None, shell_args=None, cwd=None, tema_dict=None):
        super().__init__(parent)
        self.context = context
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1"
        })
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.shell_cmd = shell_cmd
        self.shell_args = shell_args or []
        self.cwd = str(Path(cwd).resolve()) if cwd and os.path.exists(cwd) else str(Path.home().resolve())
        self.tema_dict = tema_dict or {"bg": "#07090e", "fg": "#10B981", "accent": "#059669"}

        self.ansi_parser = AnsiParser(default_fg=self.tema_dict['fg'], default_bg=self.tema_dict['bg'])
        
        self.history = []
        self.history_index = -1
        self.process = None
        self._pending_echo = None
        self._pending_empty_enter = False

        self.inicializar_ui()
        self.iniciar_proceso()
        self.actualizar_info_git()

    def inicializar_ui(self):
        self.setStyleSheet("background-color: transparent; border: none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Barra de Búsqueda Desplegable (Hidden por defecto)
        self.search_frame = QFrame()
        self.search_frame.setFixedHeight(34)
        self.search_frame.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; border-radius: 6px;")
        search_lay = QHBoxLayout(self.search_frame)
        search_lay.setContentsMargins(8, 2, 8, 2)
        search_lay.setSpacing(6)

        self.lbl_search_info = QLabel("🔍 Buscar:")
        self.lbl_search_info.setStyleSheet("color: white; font-size: 10px;")
        search_lay.addWidget(self.lbl_search_info)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Escribe para buscar en consola...")
        self.txt_search.setFont(QFont(self.font_family, 9))
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_terciario']}; color: white;
                border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 2px 8px;
            }}
        """)
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        search_lay.addWidget(self.txt_search, 1)

        btn_prev = QPushButton("▲")
        btn_prev.setFixedSize(22, 22)
        btn_prev.setToolTip("Buscar Anterior")
        btn_prev.setStyleSheet("QPushButton { background: transparent; color: white; border: none; } QPushButton:hover { background: rgba(255,255,255,0.1); }")
        btn_prev.clicked.connect(lambda: self._buscar_consola(forward=False))
        search_lay.addWidget(btn_prev)

        btn_next = QPushButton("▼")
        btn_next.setFixedSize(22, 22)
        btn_next.setToolTip("Buscar Siguiente")
        btn_next.setStyleSheet("QPushButton { background: transparent; color: white; border: none; } QPushButton:hover { background: rgba(255,255,255,0.1); }")
        btn_next.clicked.connect(lambda: self._buscar_consola(forward=True))
        search_lay.addWidget(btn_next)

        btn_close_search = QPushButton("✖")
        btn_close_search.setFixedSize(22, 22)
        btn_close_search.setStyleSheet("QPushButton { background: transparent; color: #888; border: none; } QPushButton:hover { color: white; }")
        btn_close_search.clicked.connect(lambda: self.search_frame.hide())
        search_lay.addWidget(btn_close_search)

        self.search_frame.hide()
        layout.addWidget(self.search_frame)

        # Marco de la Consola Interactiva
        self.console_frame = QFrame()
        self.console_frame.setStyleSheet(f"background-color: {self.tema_dict['bg']}; border: 1px solid rgba(255,255,255,0.05); border-radius: 8px;")
        console_lay = QVBoxLayout(self.console_frame)
        console_lay.setContentsMargins(10, 10, 10, 10)
        console_lay.setSpacing(0)

        # Consola Interactiva Unificada (Se escribe directamente aquí)
        self.terminal = InteractiveTerminalScreen(self)
        self.terminal.setFont(QFont(self.mono_font, 11))
        self.terminal.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {self.tema_dict['fg']};
                selection-background-color: {self.tema_dict['accent']}44;
            }}
        """)
        console_lay.addWidget(self.terminal, 1)

        layout.addWidget(self.console_frame, 1)

        # Mini Barra de Estado Inferior
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(26)
        self.status_bar.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; border-top: 1px solid rgba(255,255,255,0.03);")
        st_lay = QHBoxLayout(self.status_bar)
        st_lay.setContentsMargins(10, 0, 10, 0)
        st_lay.setSpacing(8)
        
        self.lbl_status = QLabel("🟢 En Ejecución")
        self.lbl_status.setFont(QFont(self.font_family, 8))
        self.lbl_status.setStyleSheet("color: #10B981;")
        st_lay.addWidget(self.lbl_status)

        # Botón / Badge de Git interactivo
        self.btn_git_badge = QPushButton("🌿 Git")
        self.btn_git_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_git_badge.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self.btn_git_badge.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(99, 102, 241, 0.15);
                color: {self.colores['acento']};
                border: 1px solid {self.colores['acento']}44;
                border-radius: 4px;
                padding: 1px 8px;
            }}
            QPushButton:hover {{
                background-color: {self.colores['acento']};
                color: #FFFFFF;
            }}
        """)
        self.btn_git_badge.clicked.connect(self.abrir_dialogo_git)
        st_lay.addWidget(self.btn_git_badge)

        st_lay.addStretch()

        self.lbl_cwd = QLabel(f"📁 {self.cwd}")
        self.lbl_cwd.setFont(QFont(self.font_family, 8))
        self.lbl_cwd.setStyleSheet("color: rgba(255,255,255,0.6);")
        st_lay.addWidget(self.lbl_cwd)

        layout.addWidget(self.status_bar)

        self._configurar_atajos()

    def _configurar_atajos(self):
        s_find = QShortcut(QKeySequence("Ctrl+F"), self)
        s_find.activated.connect(self.toggle_buscador)

    def wheelEvent(self, event):
        """Permite zoom con Ctrl + Rueda del ratón"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.ajustar_zoom(1)
            elif delta < 0:
                self.ajustar_zoom(-1)
            event.accept()
            return
        super().wheelEvent(event)

    def ajustar_zoom(self, delta):
        f = self.terminal.font()
        nuevo_size = max(8, min(26, f.pointSize() + delta))
        f.setPointSize(nuevo_size)
        self.terminal.setFont(f)

    def reset_zoom(self):
        f = self.terminal.font()
        f.setPointSize(11)
        self.terminal.setFont(f)

    def abrir_dialogo_git(self):
        from .git_dialog import GitViewerDialog
        dlg = GitViewerDialog(self, self.cwd, self.colores, on_execute_cmd_callback=self.enviar_comando)
        dlg.exec()
        self.actualizar_info_git()

    def actualizar_cwd(self, nueva_ruta):
        """Actualiza el directorio actual de la sesión y sincroniza Git"""
        if not nueva_ruta or not os.path.exists(nueva_ruta):
            return
        self.cwd = str(Path(nueva_ruta).resolve())
        self.lbl_cwd.setText(f"📁 {self.cwd}")
        self.actualizar_info_git()

    def actualizar_info_git(self):
        """Actualiza el badge de Git en la barra inferior según el CWD actual"""
        try:
            from ..utils.git_utils import es_repositorio_git, obtener_estado_git
            if es_repositorio_git(self.cwd):
                st = obtener_estado_git(self.cwd)
                rama = st["rama"] or "git"
                if st["es_limpio"]:
                    txt = f"🌿 {rama} (✓)"
                    c_bg = "rgba(16, 185, 129, 0.15)"
                    c_bdr = "rgba(16, 185, 129, 0.4)"
                    c_fg = "#10B981"
                else:
                    total_mod = st["modificados"] + st["staged"] + st["untracked"]
                    txt = f"🌿 {rama} (±{total_mod})"
                    c_bg = "rgba(245, 158, 11, 0.15)"
                    c_bdr = "rgba(245, 158, 11, 0.4)"
                    c_fg = "#F59E0B"
                
                self.btn_git_badge.setText(txt)
                self.btn_git_badge.setToolTip(f"Rama activa: {rama}\nDirectorio: {self.cwd}\nClic para abrir el visor gráfico de Git")
                self.btn_git_badge.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c_bg}; color: {c_fg};
                        border: 1px solid {c_bdr}; border-radius: 4px; padding: 1px 8px;
                    }}
                    QPushButton:hover {{ background-color: {c_fg}; color: #FFFFFF; }}
                """)
            else:
                self.btn_git_badge.setText("🌿 Sin Git")
                self.btn_git_badge.setToolTip(f"El directorio actual no es un repositorio Git:\n{self.cwd}")
                self.btn_git_badge.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.04);
                        color: rgba(255, 255, 255, 0.4);
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 4px; padding: 1px 8px;
                    }
                    QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); color: white; }
                """)
        except Exception:
            pass

    def iniciar_proceso(self):
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.leer_salida)
        self.process.finished.connect(self.on_process_finished)

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "UTF-8")
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
        self.lbl_status.setText("🟢 En Ejecución")
        self.lbl_status.setStyleSheet("color: #10B981;")

    def leer_salida(self):
        """Lectura con decodificación robusta, soporte para cls y detección automática de CWD"""
        data = self.process.readAllStandardOutput()
        data_bytes = data.data()
        try:
            text = data_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                codec = 'cp1252' if platform.system() == "Windows" else 'latin-1'
                text = data_bytes.decode(codec, errors='replace')
            except Exception:
                text = data_bytes.decode('cp850', errors='replace')

        # Detección y eliminación del eco local del comando enviado por el subshell (PowerShell / CMD)
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

        # Soporte para secuencias ANSI de limpieza de pantalla (cls / clear / Clear-Host)
        if "\x1b[2J" in text or "\x1b[3J" in text or "\x1b[H\x1b[2J" in text:
            self.terminal.clear()
            self.terminal._prompt_pos = 0
            text = text.replace("\x1b[2J", "").replace("\x1b[3J", "").replace("\x1b[H", "")

        # Renderizar texto formateado en la terminal interactiva
        self.ansi_parser.append_ansi_text(self.terminal, text, default_fg=self.tema_dict['fg'])
        self.terminal._prompt_pos = self.terminal.textCursor().position()

        # Detección dinámica de CWD en el prompt (PowerShell 'PS C:\path> ' o CMD 'C:\path> ')
        m_ps = re.findall(r'(?:PS\s+)?([A-Za-z]:\\[^>\r\n]+)>', text)
        if m_ps:
            detected_dir = m_ps[-1].strip()
            if os.path.exists(detected_dir) and detected_dir.lower() != self.cwd.lower():
                self.actualizar_cwd(detected_dir)
        elif platform.system() != "Windows":
            m_unix = re.findall(r'(\/[^\s$#>]+)[$#>]', text)
            if m_unix:
                detected_dir = m_unix[-1].strip()
                if os.path.exists(detected_dir) and detected_dir != self.cwd:
                    self.actualizar_cwd(detected_dir)

        # Auto-scroll hacia el final
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)

    def enviar_comando(self, cmd_text=None, desde_teclado=False):
        cmd = cmd_text if cmd_text is not None else self.terminal.get_current_input()
        cmd_clean = cmd.strip()
        if not cmd_clean:
            # Enviar enter vacío si se requiere
            if self.process and self.process.state() == QProcess.ProcessState.Running:
                self._pending_empty_enter = True
                self.process.write(b"\r\n" if platform.system() == "Windows" else b"\n")
            return

        self.history.append(cmd_clean)
        self.history_index = len(self.history)
        
        # Si fue invocado programáticamente (snippets, diálogo git), escribir en terminal
        if not desde_teclado and cmd_clean:
            cursor = self.terminal.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(cmd_clean + "\n")
            self.terminal.setTextCursor(cursor)
            self.terminal._prompt_pos = self.terminal.textCursor().position()

        # Soporte nativo instantáneo para 'cls' / 'clear'
        if cmd_clean.lower() in ("cls", "clear", "clear-host"):
            self.limpiar_consola()
            line_ending = "\r\n" if platform.system() == "Windows" else "\n"
            if self.process and self.process.state() == QProcess.ProcessState.Running:
                self._pending_echo = cmd_clean
                self.process.write((cmd_clean + line_ending).encode('utf-8'))
            return

        # Detección proactiva de comandos 'cd' para sincronizar CWD y Git al instante
        if cmd_clean.lower().startswith("cd ") or cmd_clean.lower().startswith("chdir "):
            partes = cmd_clean.split(maxsplit=1)
            if len(partes) > 1:
                arg_path = partes[1].strip().strip('"').strip("'")
                target = os.path.expanduser(arg_path)
                if not os.path.isabs(target):
                    target = os.path.normpath(os.path.join(self.cwd, target))
                if os.path.exists(target) and os.path.isdir(target):
                    self.actualizar_cwd(target)
        elif re.match(r'^[a-zA-Z]:$', cmd_clean):
            target = f"{cmd_clean.upper()}:\\"
            if os.path.exists(target):
                self.actualizar_cwd(target)
        elif cmd_clean == "..":
            target = str(Path(self.cwd).parent)
            if os.path.exists(target):
                self.actualizar_cwd(target)

        # Enviar el comando al proceso con supresión de duplicación de eco
        line_ending = "\r\n" if platform.system() == "Windows" else "\n"
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self._pending_echo = cmd_clean
            try:
                self.process.write((cmd_clean + line_ending).encode('utf-8'))
            except Exception:
                self.process.write((cmd_clean + line_ending).encode('cp850', errors='replace'))

        QTimer.singleShot(500, self.actualizar_info_git)

    def auto_completar_tab(self):
        """Autocompleta rutas de archivos y carpetas directamente en la terminal interactiva"""
        current_input = self.terminal.get_current_input()
        if not current_input:
            return
        
        parts = current_input.split()
        if not parts:
            return
        
        last_part = parts[-1].strip('"').strip("'")
        dirname = os.path.dirname(last_part)
        base_dir = os.path.join(self.cwd, dirname) if dirname else self.cwd
        prefix = os.path.basename(last_part).lower()

        try:
            if os.path.exists(base_dir):
                candidates = [
                    entry.name for entry in os.scandir(base_dir)
                    if entry.name.lower().startswith(prefix)
                ]
                if len(candidates) == 1:
                    matched = candidates[0]
                    completed = os.path.join(dirname, matched) if dirname else matched
                    if os.path.isdir(os.path.join(base_dir, matched)):
                        completed += os.sep
                    if " " in completed:
                        completed = f'"{completed}"'
                    parts[-1] = completed
                    self.terminal.set_current_input(" ".join(parts))
        except Exception:
            pass

    def history_up(self):
        if self.history and self.history_index > 0:
            self.history_index -= 1
            self.terminal.set_current_input(self.history[self.history_index])

    def history_down(self):
        if self.history:
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.terminal.set_current_input(self.history[self.history_index])
            else:
                self.history_index = len(self.history)
                self.terminal.set_current_input("")

    def enviar_interrupcion(self):
        """Envía señal Ctrl+C (SIGINT) al proceso"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.write(b"\x03")
            cursor = self.terminal.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText("^C\n")
            self.terminal.setTextCursor(cursor)
            self.terminal._prompt_pos = self.terminal.textCursor().position()

    def aplicar_tema(self, t):
        self.tema_dict = t
        self.console_frame.setStyleSheet(f"background-color: {t['bg']}; border: 1px solid rgba(255,255,255,0.05); border-radius: 8px;")
        self.terminal.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {t['fg']};
                selection-background-color: {t['accent']}44;
            }}
        """)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.search_frame.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; border-radius: 6px;")
        self.status_bar.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; border-top: 1px solid rgba(255,255,255,0.03);")
        self.actualizar_info_git()

    def toggle_buscador(self):
        if self.search_frame.isVisible():
            self.search_frame.hide()
        else:
            self.search_frame.show()
            self.txt_search.setFocus()

    def _on_search_text_changed(self, text):
        if text:
            self._buscar_consola(forward=True)

    def _buscar_consola(self, forward=True):
        query = self.txt_search.text()
        if not query:
            return
        if forward:
            self.terminal.find(query)
        else:
            from PyQt6.QtGui import QTextDocument
            self.terminal.find(query, QTextDocument.FindFlag.FindBackward)

    def limpiar_consola(self):
        """Limpia la pantalla de la consola y resetea el prompt"""
        self.terminal.clear()
        self.terminal._prompt_pos = 0

    def exportar_log(self):
        text = self.terminal.toPlainText()
        if not text.strip():
            return
        suggested = os.path.join(self.cwd, "terminal_output.log")
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Registro de Consola", suggested, "Archivos de Log (*.log *.txt)")
        if path:
            try:
                Path(path).write_text(text, encoding="utf-8")
                self.lbl_status.setText(f"💾 Guardado: {os.path.basename(path)}")
            except Exception as e:
                print(f"Error exportando log: {e}")

    def reiniciar_proceso(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process.waitForFinished(1000)
        self._pending_echo = None
        self._pending_empty_enter = False
        self.terminal.append("\n*** SESIÓN DE CONSOLA REINICIADA ***\n\n")
        self.iniciar_proceso()

    def on_process_finished(self, exit_code, exit_status):
        self.lbl_status.setText(f"🔴 Detenido (Código: {exit_code})")
        self.lbl_status.setStyleSheet("color: #EF4444;")
        try:
            self.terminal.append(f"\n*** El proceso ha finalizado con código de salida: {exit_code} ***\n")
        except RuntimeError:
            pass
        self.actualizar_info_git()

    def cleanup(self):
        self._pending_echo = None
        self._pending_empty_enter = False
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            try:
                self.process.kill()
                self.process.waitForFinished(400)
            except Exception:
                pass

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
