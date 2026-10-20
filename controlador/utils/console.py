"""
console.py — Terminal y Línea de Comandos para MultiTool.
Permite gestionar la aplicación, navegar entre módulos y ejecutar comandos modulares
con soporte para manifiestos de comandos personalizados (commands.json) y placeholders.
"""
import sys
import os
import re
import collections
import threading
from pathlib import Path

# --- GESTOR GLOBAL DE TRAMPAS Y VENTAJAS (CHEAT MANAGER) ---
class CheatManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = CheatManager()
        return cls._instance

    def __init__(self):
        self.cheats_enabled = False
        self.godmode = False
        self.extra_lives = 0
        self.damage_multiplier = 1.0
        self.casino_luck = False
        self.force_jackpot = False

    def is_godmode(self):
        return self.cheats_enabled and self.godmode

    def get_lives_override(self):
        if self.cheats_enabled and self.extra_lives > 0:
            return self.extra_lives
        return None

    def get_damage_multiplier(self):
        if self.cheats_enabled:
            return max(1.0, float(self.damage_multiplier))
        return 1.0

    def has_casino_luck(self):
        return self.cheats_enabled and self.casino_luck

    def consume_jackpot(self):
        if self.cheats_enabled and self.force_jackpot:
            self.force_jackpot = False
            return True
        return False

    def reset_cheats(self):
        self.cheats_enabled = False
        self.godmode = False
        self.extra_lives = 0
        self.damage_multiplier = 1.0
        self.casino_luck = False
        self.force_jackpot = False

    def get_status_dict(self):
        return {
            "cheats_activos": self.cheats_enabled,
            "godmode_invencible": self.godmode,
            "vidas_fijadas": self.extra_lives if self.extra_lives > 0 else "Normal",
            "multiplicador_danio": f"x{self.damage_multiplier}",
            "suerte_casino": self.casino_luck,
            "jackpot_pendiente": self.force_jackpot
        }


# Importar el motor modular de comandos y placeholders
from controlador.commands.command_engine import CommandEngine, ModuleCommandRegistry, PlaceholderParser

# Alias de compatibilidad
MinecraftCommandEngine = CommandEngine


# --- WIDGET PYQT6: TERMINAL FLOTANTE NO BLOQUEANTE ---
try:
    from PyQt6.QtWidgets import (
        QDialog, QFrame, QVBoxLayout, QHBoxLayout, QTextEdit, 
        QLineEdit, QLabel, QPushButton, QApplication
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QPoint
    from PyQt6.QtGui import QFont, QTextCursor

    # Paleta de colores para formato de texto (§ codes)
    CLI_COLORS = {
        "0": "#000000", "1": "#0000AA", "2": "#00AA00", "3": "#00AAAA",
        "4": "#AA0000", "5": "#AA00AA", "6": "#FFAA00", "7": "#AAAAAA",
        "8": "#555555", "9": "#5555FF", "a": "#55FF55", "b": "#55FFFF",
        "c": "#FF5555", "d": "#FF55FF", "e": "#FFFF55", "f": "#FFFFFF",
        "r": "#FFFFFF"
    }

    def format_to_html(text: str) -> str:
        """Convierte códigos de formato (§a, §c, etc.) a HTML enriquecido."""
        parts = re.split(r'(§[0-9a-fr])', text)
        cur_color = "#FFFFFF"
        html = ""
        for p in parts:
            if p.startswith("§") and len(p) == 2:
                c_code = p[1].lower()
                cur_color = CLI_COLORS.get(c_code, "#FFFFFF")
            else:
                if p:
                    safe_p = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    html += f'<span style="color: {cur_color};">{safe_p}</span>'
        return html

    # Alias de compatibilidad
    mc_to_html = format_to_html

    # --- SISTEMA DE CAPTURA Y STREAMING DE LOGS DE TERMINAL ---
    from PyQt6.QtCore import QObject
    class LogSignalEmitter(QObject):
        log_received = pyqtSignal(str)

    _local_tee = threading.local()

    class TeeStream:
        """Duplica stdout/stderr hacia la consola de la app y la terminal nativa."""
        def __init__(self, original_stream, log_manager, is_stderr=False):
            self.original_stream = original_stream
            self.log_manager = log_manager
            self.is_stderr = is_stderr
            self.buffer = ""
            self._lock = threading.Lock()

        def write(self, text):
            if getattr(_local_tee, "in_write", False):
                return self.original_stream.write(text)
            _local_tee.in_write = True
            try:
                self.original_stream.write(text)
                with self._lock:
                    self.buffer += text
                    while "\n" in self.buffer:
                        line, self.buffer = self.buffer.split("\n", 1)
                        if line.strip():
                            self.log_manager.record_log(line, self.is_stderr)
            except Exception:
                pass
            finally:
                _local_tee.in_write = False

        def flush(self):
            try:
                if self.original_stream:
                    self.original_stream.flush()
            except Exception:
                pass

        def isatty(self):
            return getattr(self.original_stream, "isatty", lambda: False)()

        def fileno(self):
            return self.original_stream.fileno()

    class TerminalLogManager:
        _instance = None

        @classmethod
        def get_instance(cls):
            if cls._instance is None:
                cls._instance = TerminalLogManager()
            return cls._instance

        def __init__(self):
            self.emitter = LogSignalEmitter()
            self.history = collections.deque(maxlen=1000)
            self.installed = False

        def install(self):
            if self.installed:
                return
            try:
                self.orig_stdout = sys.stdout
                self.orig_stderr = sys.stderr
                sys.stdout = TeeStream(self.orig_stdout, self, is_stderr=False)
                sys.stderr = TeeStream(self.orig_stderr, self, is_stderr=True)
                self.installed = True
            except Exception:
                pass

        def record_log(self, raw_line, is_stderr=False):
            formatted = self.format_terminal_line(raw_line, is_stderr)
            self.history.append(formatted)
            if self.emitter:
                try:
                    self.emitter.log_received.emit(formatted)
                except Exception:
                    pass

        @staticmethod
        def format_terminal_line(line, is_stderr=False):
            line = line.rstrip("\r\n")
            if not line:
                return ""
            if "§" in line:
                return line
            if is_stderr:
                return f"§c[STDERR] {line}§r"
            u = line.upper()
            if "ERROR" in u or "CRITICAL" in u or "TRACEBACK" in u or "EXCEPTION" in u:
                return f"§c{line}§r"
            elif "WARNING" in u or "WARN" in u:
                return f"§e{line}§r"
            elif "INFO" in u:
                return f"§b{line}§r"
            elif "DEBUG" in u:
                return f"§8{line}§r"
            return f"§7{line}§r"


    class ConsoleDialog(QDialog):
        """
        Terminal interactiva NO BLOQUEANTE (Non-Modal).
        Permite al usuario interactuar libremente con la ventana principal mientras está abierta.
        """
        def __init__(self, parent=None, engine=None):
            # parent=None para no heredar bloqueo modal del MainWindow
            super().__init__(None)
            self.main_window = parent
            self.engine = engine or CommandEngine(main_window=parent)
            self.historial_comandos = []
            self.hist_idx = 0
            self._drag_position = None

            self.setWindowTitle("Terminal de Comandos — MultiTool")
            self.setMinimumSize(700, 440)
            self.resize(780, 480)

            # Ventana independiente, no modal, flotante sin bordes de sistema
            self.setModal(False)
            self.setWindowModality(Qt.WindowModality.NonModal)
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

            self._init_ui()

        def _init_ui(self):
            main_lay = QVBoxLayout(self)
            main_lay.setContentsMargins(10, 10, 10, 10)

            container = QFrame()
            container.setStyleSheet("""
                background-color: rgba(14, 16, 24, 0.96);
                border: 2px solid #34D399;
                border-radius: 12px;
            """)
            c_lay = QVBoxLayout(container)
            c_lay.setContentsMargins(14, 12, 14, 12)
            c_lay.setSpacing(10)

            # Barra de título superior arrastrable
            self.top_bar = QFrame()
            self.top_bar.setStyleSheet("border: none; background: transparent;")
            tb_lay = QHBoxLayout(self.top_bar)
            tb_lay.setContentsMargins(0, 0, 0, 0)

            lbl_icon = QLabel("⚡")
            lbl_icon.setStyleSheet("font-size: 15px; border: none; background: transparent;")
            tb_lay.addWidget(lbl_icon)

            lbl_title = QLabel("TERMINAL DE COMANDOS — MULTITOOL")
            lbl_title.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            lbl_title.setStyleSheet("color: #34D399; border: none; background: transparent;")
            tb_lay.addWidget(lbl_title)

            self.lbl_module_badge = QLabel("[GLOBAL]")
            self.lbl_module_badge.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            self.lbl_module_badge.setStyleSheet("""
                background-color: rgba(52, 211, 153, 0.15);
                color: #34D399;
                border: 1px solid rgba(52, 211, 153, 0.4);
                border-radius: 4px;
                padding: 2px 6px;
            """)
            tb_lay.addWidget(self.lbl_module_badge)

            tb_lay.addStretch()

            btn_close = QPushButton("✕")
            btn_close.setAutoDefault(False)
            btn_close.setDefault(False)
            btn_close.setFixedSize(28, 28)
            btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_close.setStyleSheet("""
                QPushButton {
                    background: rgba(248, 113, 113, 0.2); color: #F87171;
                    font-weight: bold; border-radius: 6px; border: 1px solid rgba(248, 113, 113, 0.4);
                }
                QPushButton:hover { background: #F87171; color: black; }
            """)
            btn_close.clicked.connect(self.hide)
            tb_lay.addWidget(btn_close)
            c_lay.addWidget(self.top_bar)

            # Área de salida de texto
            self.output_area = QTextEdit()
            self.output_area.setReadOnly(True)
            self.output_area.setFont(QFont("Consolas", 10))
            self.output_area.document().setMaximumBlockCount(3000)
            self.output_area.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(6, 8, 12, 0.90);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    padding: 8px;
                    color: #E2E8F0;
                }
            """)
            c_lay.addWidget(self.output_area, 1)

            # Entrada de comando interactiva
            input_box = QHBoxLayout()
            self.lbl_prompt = QLabel("> ")
            self.lbl_prompt.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            self.lbl_prompt.setStyleSheet("color: #34D399; border: none; background: transparent;")
            input_box.addWidget(self.lbl_prompt)

            self.input_edit = QLineEdit()
            self.input_edit.setFont(QFont("Consolas", 10))
            self.input_edit.setPlaceholderText("Escribe un comando... (ej: help, use module minigames, goto extras, points add 500)")
            self.input_edit.setStyleSheet("""
                QLineEdit {
                    background-color: rgba(18, 22, 32, 0.95);
                    border: 1px solid #34D399;
                    border-radius: 6px;
                    padding: 7px 12px;
                    color: #FFFFFF;
                }
                QLineEdit:focus { border: 2px solid #55FF55; }
            """)
            self.input_edit.returnPressed.connect(self._on_enter_pressed)
            input_box.addWidget(self.input_edit, 1)

            btn_send = QPushButton("Ejecutar")
            btn_send.setAutoDefault(False)
            btn_send.setDefault(False)
            btn_send.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_send.setStyleSheet("""
                QPushButton {
                    background: #34D399; color: #0A0A0F;
                    border-radius: 6px; padding: 7px 16px; border: none;
                }
                QPushButton:hover { background: #55FF55; }
            """)
            btn_send.clicked.connect(self._on_enter_pressed)
            input_box.addWidget(btn_send)

            c_lay.addLayout(input_box)
            main_lay.addWidget(container)

            # Conectar streaming en vivo de logs de terminal
            log_mgr = TerminalLogManager.get_instance()
            log_mgr.install()
            if log_mgr.emitter:
                log_mgr.emitter.log_received.connect(self.append_formatted_text)

            # Mensajes iniciales de bienvenida
            self.append_formatted_text("§6[MultiTool CLI] §aTerminal interactiva y motor de automatización inicializados.§r")
            self.append_formatted_text("§7Escribe §ehelp §7para consultar comandos o §euse module <nombre> §7para activar un módulo específico.§r")

            # Cargar buffer reciente si hay logs previos
            if log_mgr.history:
                self.append_formatted_text("§8--- [Logs Recientes de Terminal] ---§r")
                for item in list(log_mgr.history)[-30:]:
                    self.append_formatted_text(item)
                self.append_formatted_text("§8--- [Fin de Logs Previos] ---§r")

        def append_formatted_text(self, text: str):
            html = format_to_html(text)
            self.output_area.append(html)
            self.output_area.moveCursor(QTextCursor.MoveOperation.End)

        def append_mc_text(self, text: str):
            """Alias de compatibilidad"""
            self.append_formatted_text(text)

        def _actualizar_badges(self):
            """Actualiza la insignia de módulo activo y el prompt."""
            if self.engine.active_module:
                mod_str = self.engine.active_module.upper()
                self.lbl_module_badge.setText(f"[{mod_str}]")
                self.lbl_module_badge.setStyleSheet("""
                    background-color: rgba(251, 191, 36, 0.2);
                    color: #FBBF24;
                    border: 1px solid rgba(251, 191, 36, 0.4);
                    border-radius: 4px;
                    padding: 2px 6px;
                """)
                self.lbl_prompt.setText(f"[{self.engine.active_module}] > ")
            else:
                self.lbl_module_badge.setText("[GLOBAL]")
                self.lbl_module_badge.setStyleSheet("""
                    background-color: rgba(52, 211, 153, 0.15);
                    color: #34D399;
                    border: 1px solid rgba(52, 211, 153, 0.4);
                    border-radius: 4px;
                    padding: 2px 6px;
                """)
                self.lbl_prompt.setText("> ")

        def _on_enter_pressed(self):
            cmd = self.input_edit.text().strip()
            if not cmd:
                return

            self.historial_comandos.append(cmd)
            self.hist_idx = len(self.historial_comandos)
            self.input_edit.clear()

            # Mostrar comando ingresado
            prompt_str = self.lbl_prompt.text()
            self.append_formatted_text(f"§8{prompt_str}§f{cmd}")

            res = self.engine.execute(cmd)
            self._actualizar_badges()

            if res == ["__CLEAR__"]:
                self.output_area.clear()
                self.input_edit.setFocus()
                return

            for linea in res:
                self.append_formatted_text(linea)

            self.input_edit.setFocus()

        def accept(self):
            pass

        def reject(self):
            self.hide()

        # Permitir arrastrar la ventana mediante clic en la barra superior
        def mousePressEvent(self, event):
            if event.button() == Qt.MouseButton.LeftButton and event.pos().y() < 60:
                self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
            else:
                super().mousePressEvent(event)

        def mouseMoveEvent(self, event):
            if self._drag_position is not None and event.buttons() == Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_position)
                event.accept()
            else:
                super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event):
            self._drag_position = None
            super().mouseReleaseEvent(event)

        def keyPressEvent(self, event):
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._on_enter_pressed()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Escape:
                self.hide()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Up:
                if self.historial_comandos and self.hist_idx > 0:
                    self.hist_idx -= 1
                    self.input_edit.setText(self.historial_comandos[self.hist_idx])
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Down:
                if self.historial_comandos and self.hist_idx < len(self.historial_comandos) - 1:
                    self.hist_idx += 1
                    self.input_edit.setText(self.historial_comandos[self.hist_idx])
                else:
                    self.hist_idx = len(self.historial_comandos)
                    self.input_edit.clear()
                event.accept()
                return
            else:
                super().keyPressEvent(event)

    # Alias de retrocompatibilidad
    MinecraftConsoleDialog = ConsoleDialog

except ImportError:
    ConsoleDialog = None
    MinecraftConsoleDialog = None

# Auto-instalar captura de logs si PyQt está disponible
try:
    if 'TerminalLogManager' in globals():
        TerminalLogManager.get_instance().install()
except Exception:
    pass

# Modo CLI standalone para ejecución directa en terminal
def run_cli_interactive():
    engine = CommandEngine()
    print("=====================================================")
    print("   MULTITOOL COMMAND INTERFACE")
    print("=====================================================")
    print("Escribe help para lista de comandos, exit para salir.\n")

    while True:
        try:
            prompt = engine.get_prompt_label()
            line = input(prompt)
            if line.strip().lower() in ["exit", "quit", ":q"]:
                print("Saliendo de la consola.")
                break
            resp = engine.execute(line)
            for r in resp:
                clean_r = re.sub(r'§[0-9a-fr]', '', r)
                print(clean_r)
        except (KeyboardInterrupt, EOFError):
            print("\nConsola cerrada.")
            break

if __name__ == "__main__":
    run_cli_interactive()
