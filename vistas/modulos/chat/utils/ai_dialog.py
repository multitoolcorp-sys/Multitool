import sys
import os
import re
import html
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QLineEdit, QDialog, QGroupBox, 
    QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QFont, QDesktopServices

from .ai_provider import AIConfigManager


def find_ollama_binary() -> Path | None:
    candidates = [
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Ollama' / 'ollama.exe',
        Path(os.environ.get('ProgramFiles', '')) / 'Ollama' / 'ollama.exe',
        Path(os.environ.get('ProgramFiles(x86)', '')) / 'Ollama' / 'ollama.exe',
        Path.home() / 'AppData' / 'Local' / 'Programs' / 'Ollama' / 'ollama.exe',
    ]
    which_bin = shutil.which("ollama")
    if which_bin:
        candidates.insert(0, Path(which_bin))

    for c in candidates:
        if c and c.exists():
            return c
    return None


def format_ai_response_to_html(text: str) -> str:
    # 1. Bloques de código con ```
    pattern_block = r'```([a-zA-Z0-9_+-]*)\n?(.*?)```'
    blocks = []
    def save_block(match):
        lang = match.group(1) or ""
        code_content = html.escape(match.group(2).strip())
        header = f"<div style='font-size:10px; color:#818CF8; font-weight:bold; margin-bottom:4px;'>{lang.upper() if lang else 'CÓDIGO'}</div>"
        block_html = f"<div style='margin: 8px 0; background: #12121E; border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 10px;'>{header}<pre style='margin:0; font-family: Consolas, monospace; font-size: 11.5px; color: #E2E8F0; white-space: pre-wrap;'><code>{code_content}</code></pre></div>"
        blocks.append(block_html)
        return f"__CODE_BLOCK_{len(blocks)-1}__"

    text_no_blocks = re.sub(pattern_block, save_block, text, flags=re.DOTALL)

    # 2. Escapar texto fuera de bloques de código
    escaped = html.escape(text_no_blocks)

    # 3. Enlaces Markdown [Texto](url) y URLs directas
    escaped = re.sub(
        r'\[(.*?)\]\((https?://[^\s\)]+)\)',
        r"<a href='\2' style='color: #60A5FA; text-decoration: underline; font-weight: bold;'>\1</a>",
        escaped
    )
    escaped = re.sub(
        r'(?<!href=\')(https?://[^\s<]+)',
        r"<a href='\1' style='color: #60A5FA; text-decoration: underline;'>\1</a>",
        escaped
    )

    # 4. Formateo en línea (Títulos, Negritas, Cursivas, Viñetas, Código inline)
    escaped = re.sub(r'(?m)^###\s+(.*)$', r"<div style='font-size:13px; font-weight:bold; color:#34D399; margin:8px 0 4px 0;'>\1</div>", escaped)
    escaped = re.sub(r'(?m)^##\s+(.*)$', r"<div style='font-size:14px; font-weight:bold; color:#60A5FA; margin:10px 0 5px 0;'>\1</div>", escaped)
    escaped = re.sub(r'(?m)^#\s+(.*)$', r"<div style='font-size:15px; font-weight:bold; color:#A78BFA; margin:12px 0 6px 0;'>\1</div>", escaped)
    escaped = re.sub(r'(?m)^[\*\-]\s+(.*)$', r"<div style='margin-left: 14px;'>• \1</div>", escaped)

    escaped = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', escaped)
    escaped = re.sub(r'\*(.*?)\*', r'<i>\1</i>', escaped)
    escaped = re.sub(r'`(.*?)`', r"<code style='background:rgba(255,255,255,0.1); padding:2px 5px; border-radius:4px; font-family:Consolas,monospace; color:#93C5FD;'>\1</code>", escaped)
    escaped = escaped.replace("\n", "<br>")

    # 5. Restaurar bloques de código
    for i, b in enumerate(blocks):
        escaped = escaped.replace(f"__CODE_BLOCK_{i}__", b)

    return escaped


class AIChatInputEdit(QTextEdit):
    """QTextEdit con soporte para Drag & Drop y autocompletado de menciones @archivo estilo VSCode"""
    returnPressed = pyqtSignal()

    def __init__(self, workspace_root: Path, colores: dict, parent=None):
        super().__init__(parent)
        self.workspace_root = workspace_root
        self.colores = colores or {}
        self.setAcceptDrops(True)
        self._popup_list = None
        self._project_files = []
        self._index_workspace_files()

    def _index_workspace_files(self):
        try:
            files_found = []
            root = Path(__file__).resolve().parent.parent.parent.parent.parent
            for r, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "venv", ".venv", "node_modules", ".gemini")]
                for f in files:
                    full_p = Path(r) / f
                    rel_p = os.path.relpath(full_p, root)
                    files_found.append((f, rel_p, str(full_p)))
                if len(files_found) > 800:
                    break
            self._project_files = sorted(files_found, key=lambda x: x[0].lower())
        except Exception:
            self._project_files = []

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths_to_insert = []
            for u in urls:
                local_p = u.toLocalFile()
                if local_p:
                    paths_to_insert.append(f'@{local_p}')
            if paths_to_insert:
                cursor = self.textCursor()
                cursor.insertText(" " + " ".join(paths_to_insert) + " ")
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            if self._popup_list and self._popup_list.isVisible() and self._popup_list.count() > 0:
                self._insert_selected_mention()
                return
            self.returnPressed.emit()
            return

        if self._popup_list and self._popup_list.isVisible():
            if event.key() == Qt.Key.Key_Up:
                row = max(0, self._popup_list.currentRow() - 1)
                self._popup_list.setCurrentRow(row)
                return
            elif event.key() == Qt.Key.Key_Down:
                row = min(self._popup_list.count() - 1, self._popup_list.currentRow() + 1)
                self._popup_list.setCurrentRow(row)
                return
            elif event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                self._insert_selected_mention()
                return
            elif event.key() == Qt.Key.Key_Escape:
                self._popup_list.hide()
                return

        super().keyPressEvent(event)
        self._check_mention_trigger()

    def _check_mention_trigger(self):
        text = self.toPlainText()
        cursor_pos = self.textCursor().position()
        text_before = text[:cursor_pos]

        at_idx = text_before.rfind("@")
        if at_idx != -1:
            query = text_before[at_idx + 1:]
            if " " not in query and "\n" not in query:
                self._show_mention_popup(query)
                return
        if self._popup_list:
            self._popup_list.hide()

    def _show_mention_popup(self, query: str):
        if not self._popup_list:
            self._popup_list = QListWidget(self.window())
            self._popup_list.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
            self._popup_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                    color: white;
                    border: 1px solid {self.colores.get('acento', '#6366F1')};
                    border-radius: 8px;
                    padding: 4px;
                    font-size: 11px;
                }}
                QListWidget::item {{
                    padding: 5px 8px;
                    border-radius: 4px;
                }}
                QListWidget::item:selected {{
                    background-color: {self.colores.get('acento', '#6366F1')};
                    color: white;
                }}
            """)
            self._popup_list.itemClicked.connect(lambda it: self._insert_selected_mention())

        self._popup_list.clear()
        q_lower = query.lower()
        matches = [f for f in self._project_files if q_lower in f[0].lower() or q_lower in f[1].lower()]

        for fname, relpath, fullpath in matches[:15]:
            item = QListWidgetItem(f"📄 {fname}  ({relpath})")
            item.setData(Qt.ItemDataRole.UserRole, fullpath)
            self._popup_list.addItem(item)

        if self._popup_list.count() == 0:
            self._popup_list.hide()
            return

        self._popup_list.setCurrentRow(0)
        cursor_rect = self.cursorRect()
        global_pos = self.mapToGlobal(cursor_rect.bottomLeft())
        self._popup_list.resize(380, min(200, self._popup_list.count() * 28 + 12))
        self._popup_list.move(global_pos.x(), global_pos.y() - self._popup_list.height() - 25)
        self._popup_list.show()
        self._popup_list.raise_()

    def _insert_selected_mention(self):
        if not self._popup_list or not self._popup_list.currentItem():
            return
        fullpath = self._popup_list.currentItem().data(Qt.ItemDataRole.UserRole)
        self._popup_list.hide()

        text = self.toPlainText()
        cursor = self.textCursor()
        pos = cursor.position()
        text_before = text[:pos]
        at_idx = text_before.rfind("@")
        if at_idx != -1:
            cursor.setPosition(at_idx)
            cursor.setPosition(pos, cursor.MoveMode.KeepAnchor)
            cursor.insertText(f"@{fullpath} ")


class AIConfigDialog(QDialog):
    """Diálogo para configurar API Keys y servidor Ollama sin alterar el código fuente"""
    def __init__(self, config_mgr: AIConfigManager, colores: dict, parent=None):
        super().__init__(parent)
        self.config_mgr = config_mgr
        self.cfg = config_mgr.config
        self.colores = colores or {}

        self.setWindowTitle("⚙️ Configuración de Asistente IA (Privacidad & Keys)")
        self.setFixedWidth(520)

        bg = self.colores.get('bg_principal', '#1E1E1E')
        fg = self.colores.get('fg_principal', '#E0E0E0')
        acento = self.colores.get('acento', '#6366F1')
        sec = self.colores.get('bg_secundario', '#2D2D2D')

        self.setStyleSheet(f"background: {bg}; color: {fg}; font-family: 'Segoe UI';")

        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        lbl_head = QLabel("🔒 Configuración Segura de Inteligencia Artificial")
        lbl_head.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lay.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Las API Keys ingresadas se guardan de forma privada en tu equipo local (~/.multitool/ai_config.json) "
            "y jamás se compilan ni se comparten en el código abierto."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        lay.addWidget(lbl_desc)

        # Configuración Ollama Local
        g_ollama = QGroupBox("🦙 Servidor Local Ollama (100% Offline)")
        g_ollama.setStyleSheet(f"color: {fg}; font-weight: bold; border: 1px solid rgba(255,255,255,0.1); margin-top: 5px;")
        o_lay = QVBoxLayout(g_ollama)
        o_lay.addWidget(QLabel("URL del Servidor Ollama:"))
        self.txt_ollama_url = QLineEdit(self.cfg.get("ollama_url", "http://127.0.0.1:11434"))
        self.txt_ollama_url.setStyleSheet(f"background: {sec}; color: white; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 6px;")
        o_lay.addWidget(self.txt_ollama_url)
        lay.addWidget(g_ollama)

        # Configuración Cloud BYOK
        g_keys = QGroupBox("☁️ Claves API Personales (BYOK)")
        g_keys.setStyleSheet(f"color: {fg}; font-weight: bold; border: 1px solid rgba(255,255,255,0.1); margin-top: 5px;")
        k_lay = QVBoxLayout(g_keys)

        api_keys = self.cfg.get("api_keys", {})

        def create_key_row(label_text, key_val, url_get):
            h_lay = QHBoxLayout()
            h_lay.addWidget(QLabel(label_text), 1)
            btn_get = QPushButton("🔗 Obtener Clave")
            btn_get.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_get.setStyleSheet("background: rgba(255,255,255,0.08); color: #818CF8; border: none; font-size: 10px; padding: 2px 6px; border-radius: 4px;")
            btn_get.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url_get)))
            h_lay.addWidget(btn_get)
            txt = QLineEdit(key_val)
            txt.setEchoMode(QLineEdit.EchoMode.Password)
            txt.setStyleSheet(f"background: {sec}; color: white; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 5px;")
            v_wrap = QVBoxLayout()
            v_wrap.addLayout(h_lay)
            v_wrap.addWidget(txt)
            return v_wrap, txt

        r1, self.txt_openai = create_key_row("OpenAI API Key (sk-...):", api_keys.get("openai", ""), "https://platform.openai.com/api-keys")
        k_lay.addLayout(r1)

        r2, self.txt_groq = create_key_row("Groq API Key (gsk_...):", api_keys.get("groq", ""), "https://console.groq.com/keys")
        k_lay.addLayout(r2)

        r3, self.txt_deepseek = create_key_row("DeepSeek API Key (sk-...):", api_keys.get("deepseek", ""), "https://platform.deepseek.com/api_keys")
        k_lay.addLayout(r3)

        r4, self.txt_gemini = create_key_row("Google Gemini API Key:", api_keys.get("gemini", ""), "https://aistudio.google.com/app/apikey")
        k_lay.addLayout(r4)

        lay.addWidget(g_keys)

        # Botones
        b_lay = QHBoxLayout()
        btn_save = QPushButton("Guardar Configuración")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"background: {acento}; color: white; font-weight: bold; border: none; padding: 8px 16px; border-radius: 6px;")
        btn_save.clicked.connect(self.save_and_close)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#3D3D3D')}; color: white; border: none; padding: 8px 16px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)

        b_lay.addStretch()
        b_lay.addWidget(btn_cancel)
        b_lay.addWidget(btn_save)
        lay.addLayout(b_lay)

    def save_and_close(self):
        new_cfg = {
            "ollama_url": self.txt_ollama_url.text().strip(),
            "api_keys": {
                "openai": self.txt_openai.text().strip(),
                "groq": self.txt_groq.text().strip(),
                "deepseek": self.txt_deepseek.text().strip(),
                "gemini": self.txt_gemini.text().strip(),
                "custom": ""
            }
        }
        self.config_mgr.save_config(new_cfg)
        self.accept()
