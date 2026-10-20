"""
tab_markdown.py - Editor Markdown Split-Screen con Vista Previa en Tiempo Real
"""
import re
import json
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QPlainTextEdit, QTextBrowser, QSplitter, QComboBox, QMessageBox,
    QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class TabMarkdownGUI(QWidget):
    """Editor Markdown a pantalla dividida (Código Markdown a la izquierda + Preview HTML a la derecha)"""
    def __init__(self, parent=None, context=None, colores=None, **kwargs):
        super().__init__(parent)
        self.context = context
        self.colores = colores or (getattr(context, "colores", {}) if context else {})
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.ruta_notas = self.ruta_usuario / "notas"
        self.ruta_notas.mkdir(parents=True, exist_ok=True)

        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(150)
        self.debounce_timer.timeout.connect(self._render_markdown)

        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_p}; color: white;")
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(12, 12, 12, 12)
        main_lay.setSpacing(10)

        # Toolbar Superior
        toolbar = QFrame()
        toolbar.setStyleSheet(f"background: {bg_sec}; border-radius: 8px; padding: 4px;")
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(8, 4, 8, 4)
        tb_lay.setSpacing(5)

        lbl_tit = QLabel("📑 MARKDOWN SPLIT")
        lbl_tit.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; margin-right: 6px;")
        tb_lay.addWidget(lbl_tit)

        # Acciones de Markdown rápido
        acciones_md = [
            ("H1", "# ", "Título 1"),
            ("H2", "## ", "Título 2"),
            ("H3", "### ", "Título 3"),
            ("B", "**", "Negrita"),
            ("I", "*", "Cursiva"),
            ("S", "~~", "Tachado"),
            ("❝", "> ", "Cita / Blockquote"),
            ("`", "`", "Código inline"),
            ("```", "```\n", "Bloque de código"),
            ("☑", "- [ ] ", "Checklist"),
            ("•", "- ", "Viñeta"),
            ("🔗", "[texto](url)", "Enlace")
        ]

        for text, snippet, tooltip in acciones_md:
            btn = QPushButton(text)
            btn.setFixedSize(28, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(0,0,0,0.25); color: white; border-radius: 4px;
                    border: 1px solid rgba(255,255,255,0.06); font-weight: bold; font-size: 10px;
                }}
                QPushButton:hover {{ background: rgba(255,255,255,0.1); border-color: {acento}; }}
            """)
            btn.clicked.connect(lambda ch, s=snippet, t=text: self._insertar_markdown(s, t))
            tb_lay.addWidget(btn)

        tb_lay.addStretch()

        # Selector para cargar nota existente
        self.combo_cargar = QComboBox()
        self.combo_cargar.setMinimumWidth(130)
        self.combo_cargar.setStyleSheet("""
            QComboBox { background: rgba(0,0,0,0.25); color: white; border-radius: 6px; padding: 3px 8px; font-size: 10px; }
            QComboBox::drop-down { border: none; }
        """)
        self._actualizar_combo_notas()
        tb_lay.addWidget(self.combo_cargar)

        btn_cargar = QPushButton("📥 Cargar")
        btn_cargar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cargar.setStyleSheet("background: rgba(255,255,255,0.06); color: white; border-radius: 6px; padding: 4px 10px; font-size: 10px;")
        btn_cargar.clicked.connect(self._cargar_nota_seleccionada)
        tb_lay.addWidget(btn_cargar)

        btn_copy = QPushButton("📋 Copiar MD")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet("background: rgba(255,255,255,0.06); color: white; border-radius: 6px; padding: 4px 10px; font-size: 10px;")
        btn_copy.clicked.connect(self._copiar_markdown)
        tb_lay.addWidget(btn_copy)

        btn_save = QPushButton("💾 Guardar en Biblioteca")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {acento}; color: white; border-radius: 6px;
                padding: 4px 12px; font-weight: bold; font-size: 10px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_save.clicked.connect(self._guardar_como_nota)
        tb_lay.addWidget(btn_save)

        main_lay.addWidget(toolbar)

        # Splitter Central
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle { background-color: rgba(255,255,255,0.06); width: 2px; }
        """)

        # Panel Izquierdo: Editor Markdown Puro
        frame_editor = QFrame()
        frame_editor.setStyleSheet(f"background: {bg_sec}; border-radius: 8px;")
        fed_lay = QVBoxLayout(frame_editor)
        fed_lay.setContentsMargins(10, 8, 10, 8)
        fed_lay.setSpacing(6)

        lbl_fed = QLabel("✏️ Sintaxis Markdown")
        lbl_fed.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_fed.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')};")
        fed_lay.addWidget(lbl_fed)

        self.editor_md = QPlainTextEdit()
        self.editor_md.setFont(QFont("Consolas", 11))
        self.editor_md.setStyleSheet("""
            QPlainTextEdit {
                background: rgba(0,0,0,0.2); color: #E2E8F0;
                border: none; border-radius: 6px; padding: 10px; line-height: 1.4;
            }
        """)
        self.editor_md.textChanged.connect(self.debounce_timer.start)
        fed_lay.addWidget(self.editor_md)

        splitter.addWidget(frame_editor)

        # Panel Derecho: Vista Previa Renderizada
        frame_prev = QFrame()
        frame_prev.setStyleSheet(f"background: {bg_sec}; border-radius: 8px;")
        fprev_lay = QVBoxLayout(frame_prev)
        fprev_lay.setContentsMargins(10, 8, 10, 8)
        fprev_lay.setSpacing(6)

        lbl_fprev = QLabel("👁️ Vista Previa en Vivo (HTML)")
        lbl_fprev.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_fprev.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')};")
        fprev_lay.addWidget(lbl_fprev)

        self.preview_browser = QTextBrowser()
        self.preview_browser.setOpenExternalLinks(True)
        self.preview_browser.setStyleSheet("""
            QTextBrowser {
                background: rgba(0,0,0,0.2); color: #F1F5F9;
                border: none; border-radius: 6px; padding: 12px;
            }
        """)
        fprev_lay.addWidget(self.preview_browser)

        splitter.addWidget(frame_prev)
        splitter.setSizes([450, 450])
        main_lay.addWidget(splitter, 1)

        # Footer con estadísticas de texto
        footer = QHBoxLayout()
        self.lbl_md_stats = QLabel("Líneas: 0 | Palabras: 0 | Caracteres: 0")
        self.lbl_md_stats.setFont(QFont("Segoe UI", 8))
        self.lbl_md_stats.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')};")
        footer.addWidget(self.lbl_md_stats)
        footer.addStretch()
        main_lay.addLayout(footer)

        # Contenido inicial de ejemplo
        ejemplo_md = (
            "# 🚀 Bienvenido al Editor Markdown\n\n"
            "Este submódulo te permite redactar en **Markdown puro** con visualización instantánea.\n\n"
            "### ✨ Funcionalidades Clave:\n"
            "- [x] Renderizado en tiempo real con debounce\n"
            "- [x] Soporte para listas de tareas (Checklists)\n"
            "- [x] Bloques de código monospace y tablas\n"
            "- [ ] Exportación directa a la biblioteca de Notas\n\n"
            "> \"La simplicidad es la máxima sofisticación.\" — Leonardo da Vinci\n\n"
            "```python\n"
            "# Código de ejemplo\n"
            "def saludar(nombre):\n"
            "    return f'Hola {nombre} desde Markdown!'\n"
            "```\n"
        )
        self.editor_md.setPlainText(ejemplo_md)
        self._render_markdown()

    def _actualizar_combo_notas(self):
        self.combo_cargar.clear()
        self.combo_cargar.addItem("Seleccionar nota...", "")
        for f in self.ruta_notas.glob("*.txt"):
            self.combo_cargar.addItem(f.stem, str(f))

    def _cargar_nota_seleccionada(self):
        ruta = self.combo_cargar.currentData()
        if not ruta or not Path(ruta).exists():
            return
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                raw = f.read()
            html = ""
            try:
                data = json.loads(raw)
                html = data.get("html", "") if isinstance(data, dict) else raw
            except Exception:
                html = raw

            # Convertir HTML básico a Markdown para edición
            md_text = self._html_a_markdown(html)
            self.editor_md.setPlainText(md_text)
            self._render_markdown()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo cargar la nota: {e}")

    def _html_a_markdown(self, html):
        text = html
        text = re.sub(r'<h1>(.*?)</h1>', r'# \1\n', text, flags=re.I)
        text = re.sub(r'<h2>(.*?)</h2>', r'## \1\n', text, flags=re.I)
        text = re.sub(r'<h3>(.*?)</h3>', r'### \1\n', text, flags=re.I)
        text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.I)
        text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text, flags=re.I)
        text = re.sub(r'<i>(.*?)</i>', r'*\1*', text, flags=re.I)
        text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.I)
        text = re.sub(r'<s>(.*?)</s>', r'~~\1~~', text, flags=re.I)
        text = re.sub(r'<li>(.*?)</li>', r'- \1\n', text, flags=re.I)
        text = re.sub(r'<p>(.*?)</p>', r'\1\n\n', text, flags=re.I)
        text = re.sub(r'<br\s*/?>', r'\n', text, flags=re.I)
        text = re.sub(r'<hr\s*/?>', r'\n---\n', text, flags=re.I)
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()

    def _insertar_markdown(self, snippet, token):
        cursor = self.editor_md.textCursor()
        sel = cursor.selectedText()
        if token in ["B", "I", "S", "`"]:
            if sel:
                cursor.insertText(f"{snippet}{sel}{snippet}")
            else:
                cursor.insertText(f"{snippet}{snippet}")
                cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor, len(snippet))
                self.editor_md.setTextCursor(cursor)
        elif token == "```":
            if sel:
                cursor.insertText(f"```\n{sel}\n```\n")
            else:
                cursor.insertText("```\n\n```\n")
                cursor.movePosition(cursor.MoveOperation.Up, cursor.MoveMode.MoveAnchor, 2)
                self.editor_md.setTextCursor(cursor)
        else:
            cursor.insertText(snippet)
        self.editor_md.setFocus()

    def _render_markdown(self):
        md_text = self.editor_md.toPlainText()
        
        # Stats
        lineas = len(md_text.splitlines())
        palabras = len([w for w in md_text.split() if w.strip()])
        caracteres = len(md_text)
        self.lbl_md_stats.setText(f"Líneas: {lineas} | Palabras: {palabras} | Caracteres: {caracteres}")

        # Simple pero robusto convertidor Markdown a HTML estilizado
        html = self._convertir_markdown_a_html(md_text)
        self.preview_browser.setHtml(html)

    def _convertir_markdown_a_html(self, md):
        css = """
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 14px; line-height: 1.6; color: #E2E8F0; }
            h1 { color: #818CF8; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px; font-size: 22px; }
            h2 { color: #93C5FD; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 4px; font-size: 18px; }
            h3 { color: #A78BFA; font-size: 15px; }
            p { margin: 8px 0; }
            blockquote { border-left: 4px solid #6366F1; margin: 10px 0; padding: 8px 14px; background: rgba(99,102,241,0.08); color: #CBD5E1; }
            code { background: rgba(255,255,255,0.08); color: #F472B6; padding: 2px 5px; border-radius: 4px; font-family: Consolas, monospace; }
            pre { background: #0F172A; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 12px; font-family: Consolas, monospace; overflow-x: auto; color: #38BDF8; }
            ul, ol { padding-left: 20px; }
            li { margin: 4px 0; }
            hr { border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 14px 0; }
            a { color: #60A5FA; text-decoration: none; }
            .chk-done { color: #10B981; }
            .chk-todo { color: #94A3B8; }
        </style>
        """

        lines = md.splitlines()
        out = []
        in_code_block = False
        code_buf = []

        for line in lines:
            if line.startswith("```"):
                if in_code_block:
                    in_code_block = False
                    code_content = "\n".join(code_buf).replace("<", "&lt;").replace(">", "&gt;")
                    out.append(f"<pre><code>{code_content}</code></pre>")
                    code_buf = []
                else:
                    in_code_block = True
                    code_buf = []
                continue

            if in_code_block:
                code_buf.append(line)
                continue

            # Encabezados
            if line.startswith("### "):
                out.append(f"<h3>{self._format_inline(line[4:])}</h3>")
            elif line.startswith("## "):
                out.append(f"<h2>{self._format_inline(line[3:])}</h2>")
            elif line.startswith("# "):
                out.append(f"<h1>{self._format_inline(line[2:])}</h1>")
            elif line.startswith("> "):
                out.append(f"<blockquote>{self._format_inline(line[2:])}</blockquote>")
            elif line.startswith("- [x] ") or line.startswith("- [X] "):
                out.append(f"<p class='chk-done'>☑ <s>{self._format_inline(line[6:])}</s></p>")
            elif line.startswith("- [ ] "):
                out.append(f"<p class='chk-todo'>☐ {self._format_inline(line[6:])}</p>")
            elif line.startswith("- ") or line.startswith("* "):
                out.append(f"<ul><li>{self._format_inline(line[2:])}</li></ul>")
            elif line.strip() == "---":
                out.append("<hr>")
            elif line.strip():
                out.append(f"<p>{self._format_inline(line)}</p>")
            else:
                out.append("<br>")

        if in_code_block and code_buf:
            code_content = "\n".join(code_buf).replace("<", "&lt;").replace(">", "&gt;")
            out.append(f"<pre><code>{code_content}</code></pre>")

        return f"{css}<body>{''.join(out)}</body>"

    def _format_inline(self, text):
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        text = re.sub(r'~~(.*?)~~', r'<s>\1</s>', text)
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
        return text

    def _copiar_markdown(self):
        txt = self.editor_md.toPlainText()
        QApplication.clipboard().setText(txt)
        QMessageBox.information(self, "Copiado", "¡Código Markdown copiado al portapapeles!")

    def _guardar_como_nota(self):
        md = self.editor_md.toPlainText().strip()
        if not md:
            QMessageBox.information(self, "Guardar", "El editor está vacío.")
            return

        primer_linea = md.splitlines()[0].lstrip("#").strip()
        fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_base = re.sub(r'[\\/*?:"<>|]', "", primer_linea).replace(" ", "_")[:30] or f"Nota_MD_{fecha}"
        nombre = f"{nombre_base}_{fecha}"

        html_render = self._convertir_markdown_a_html(md)
        datos = {
            "html": html_render,
            "imagenes_metadata": {},
            "favorita": False,
            "background_color": "default"
        }
        ruta_nota = self.ruta_notas / f"{nombre}.txt"
        try:
            with open(ruta_nota, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=4)
            self._actualizar_combo_notas()
            QMessageBox.information(self, "Guardado", f"¡Nota '{nombre}' guardada en la biblioteca!")

            # Notificar al módulo principal
            parent_tab = self.parent()
            while parent_tab and not hasattr(parent_tab, "cargar_lista_notas"):
                parent_tab = parent_tab.parent()
            if parent_tab and hasattr(parent_tab, "cargar_lista_notas"):
                parent_tab.cargar_lista_notas()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la nota: {e}")
