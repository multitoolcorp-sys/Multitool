"""
herramientas_texto.py - Submódulo de Herramientas de Texto, JSON, Base64, Hashes y Formateo
"""
import re
import json
import base64
import hashlib
import urllib.parse

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QPlainTextEdit, QMessageBox, QApplication, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor


class TabHerramientasTextoClipboard(QWidget):
    """Submódulo con herramientas avanzadas para desarrolladores y usuarios de portapapeles."""
    def __init__(self, parent=None, colores=None):
        super().__init__(parent)
        self.colores = colores or {}

        self.init_ui()

    def _hex_to_rgb(self, hex_str):
        hex_str = str(hex_str).lstrip('#')
        if len(hex_str) == 3:
            hex_str = ''.join(c*2 for c in hex_str)
        try:
            return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"
        except Exception:
            return "99, 102, 241"

    def init_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(16, 16, 16, 16)
        main_lay.setSpacing(10)

        # ── Header ──
        hdr = QHBoxLayout()
        lbl_t = QLabel("⚙️ HERRAMIENTAS DE FORMATEO Y CONVERSIÓN DE TEXTO")
        lbl_t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        hdr.addWidget(lbl_t)
        hdr.addStretch()

        btn_limpiar = QPushButton("🧹 Limpiar Editor")
        btn_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_limpiar.setStyleSheet("background: rgba(248,113,113,0.15); color: #F87171; border: 1px solid rgba(248,113,113,0.3); border-radius: 6px; padding: 4px 10px; font-weight: bold; font-size: 10px;")
        btn_limpiar.clicked.connect(lambda: self.txt_editor.clear())
        hdr.addWidget(btn_limpiar)
        main_lay.addLayout(hdr)

        # ── Barra de herramientas agrupadas ──
        tb = QHBoxLayout()
        tb.setSpacing(8)

        # 1. Menú JSON
        btn_json = QPushButton("✨ JSON ▾")
        btn_json.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_json.setStyleSheet(self._btn_style())
        m_json = QMenu(self)
        m_json.setStyleSheet(self._menu_style())
        m_json.addAction("✨ Formatear (Pretty Print)", self._formatear_json)
        m_json.addAction("📦 Minificar (Compactar)", self._minificar_json)
        btn_json.setMenu(m_json)
        tb.addWidget(btn_json)

        # 2. Menú Codificación (Base64 & URL)
        btn_code = QPushButton("🔒 Codificación ▾")
        btn_code.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_code.setStyleSheet(self._btn_style())
        m_code = QMenu(self)
        m_code.setStyleSheet(self._menu_style())
        m_code.addAction("🔒 Codificar a Base64", self._encode_base64)
        m_code.addAction("🔓 Decodificar de Base64", self._decode_base64)
        m_code.addSeparator()
        m_code.addAction("🌐 Codificar URL (URL Encode)", self._encode_url)
        m_code.addAction("🌐 Decodificar URL (URL Decode)", self._decode_url)
        btn_code.setMenu(m_code)
        tb.addWidget(btn_code)

        # 3. Menú Casos y Mayúsculas
        btn_case = QPushButton("🔤 Capitalización ▾")
        btn_case.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_case.setStyleSheet(self._btn_style())
        m_case = QMenu(self)
        m_case.setStyleSheet(self._menu_style())
        m_case.addAction("MAYÚSCULAS", self._to_upper)
        m_case.addAction("minúsculas", self._to_lower)
        m_case.addAction("Tipo Título (Title Case)", self._to_title)
        m_case.addAction("Capitalizar Primera Letra", self._to_capitalize)
        m_case.addSeparator()
        m_case.addAction("camelCase", self._to_camel_case)
        m_case.addAction("snake_case", self._to_snake_case)
        m_case.addAction("kebab-case", self._to_kebab_case)
        btn_case.setMenu(m_case)
        tb.addWidget(btn_case)

        # 4. Menú Líneas y Listas
        btn_lines = QPushButton("📝 Líneas ▾")
        btn_lines.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_lines.setStyleSheet(self._btn_style())
        m_lines = QMenu(self)
        m_lines.setStyleSheet(self._menu_style())
        m_lines.addAction("🧹 Sanitizar espacios en blanco", self._sanitizar_texto)
        m_lines.addAction("🔀 Eliminar líneas duplicadas", self._eliminar_duplicados)
        m_lines.addAction("⬆️ Ordenar líneas (A-Z)", lambda: self._ordenar_lineas(reverse=False))
        m_lines.addAction("⬇️ Ordenar líneas (Z-A)", lambda: self._ordenar_lineas(reverse=True))
        m_lines.addAction("🔃 Invertir orden de líneas", self._invertir_lineas)
        m_lines.addAction("🗑️ Eliminar líneas vacías", self._eliminar_lineas_vacias)
        btn_lines.setMenu(m_lines)
        tb.addWidget(btn_lines)

        # 5. Menú Hashes Criptográficos
        btn_hash = QPushButton("#️⃣ Hashes ▾")
        btn_hash.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_hash.setStyleSheet(self._btn_style())
        m_hash = QMenu(self)
        m_hash.setStyleSheet(self._menu_style())
        m_hash.addAction("#️⃣ Generar MD5", lambda: self._generar_hash("md5"))
        m_hash.addAction("#️⃣ Generar SHA-256", lambda: self._generar_hash("sha256"))
        m_hash.addAction("#️⃣ Generar SHA-1", lambda: self._generar_hash("sha1"))
        btn_hash.setMenu(m_hash)
        tb.addWidget(btn_hash)

        tb.addStretch()
        main_lay.addLayout(tb)

        # ── Editor de Texto Principal ──
        self.txt_editor = QPlainTextEdit()
        self.txt_editor.setFont(QFont("Consolas", 10))
        self.txt_editor.setPlaceholderText("Escribe, pega texto del portapapeles o genera contenido aquí...")
        self.txt_editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: {self.colores.get('fg_principal', '#E2E2E2')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px; padding: 10px;
                line-height: 1.4;
            }}
            QPlainTextEdit:focus {{
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.txt_editor.textChanged.connect(self._actualizar_estadisticas_texto)
        main_lay.addWidget(self.txt_editor, 1)

        # ── Footer con estadísticas y botones ──
        ft = QHBoxLayout()
        self.lbl_stats = QLabel("Caracteres: 0 | Palabras: 0 | Líneas: 0 | Espacios: 0 | Lectura: ~0 min")
        self.lbl_stats.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px;")
        ft.addWidget(self.lbl_stats)

        ft.addStretch()

        btn_load_clip = QPushButton("📥 Pegar de Portapapeles")
        btn_load_clip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_load_clip.setStyleSheet("background: rgba(255,255,255,0.06); color: white; border-radius: 6px; padding: 6px 12px; font-size: 10px; font-weight: bold;")
        btn_load_clip.clicked.connect(self._pegar_portapapeles)
        ft.addWidget(btn_load_clip)

        btn_copy = QPushButton("📋 Copiar Resultado")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')}; color: white;
                border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 10px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_copy.clicked.connect(self._copiar_resultado)
        ft.addWidget(btn_copy)

        main_lay.addLayout(ft)

    def _btn_style(self):
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        return f"""
            QPushButton {{
                background: {bg_sec};
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {self.colores.get('acento', '#6366F1')};
                background: rgba(255,255,255,0.06);
            }}
            QPushButton::menu-indicator {{ image: none; }}
        """

    def _menu_style(self):
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        return f"""
            QMenu {{
                background-color: {bg_terc};
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 11px;
            }}
            QMenu::item:selected {{
                background-color: {acento};
                color: #FFFFFF;
            }}
            QMenu::separator {{
                height: 1px;
                background: rgba(255,255,255,0.1);
                margin: 4px 6px;
            }}
        """

    def cargar_texto(self, texto: str):
        """Permite cargar texto desde otros submódulos (como Historial o Snippets)."""
        if texto:
            self.txt_editor.setPlainText(texto)

    def _actualizar_estadisticas_texto(self):
        txt = self.txt_editor.toPlainText()
        chars = len(txt)
        words = len(txt.split())
        lines = len(txt.splitlines()) if txt else 0
        spaces = txt.count(' ') + txt.count('\t')
        reading_time = max(1, round(words / 200)) if words > 100 else 0
        self.lbl_stats.setText(f"Caracteres: {chars} | Palabras: {words} | Líneas: {lines} | Espacios: {spaces} | Lectura: ~{reading_time} min")

    def _pegar_portapapeles(self):
        txt = QApplication.clipboard().text()
        self.txt_editor.setPlainText(txt)

    def _copiar_resultado(self):
        txt = self.txt_editor.toPlainText()
        if not txt:
            return
        QApplication.clipboard().setText(txt)
        QMessageBox.information(self, "Copiado", "Texto copiado al portapapeles exitosamente.")

    # ── MÉTODOS DE CONVERSIÓN ──
    def _formatear_json(self):
        txt = self.txt_editor.toPlainText().strip()
        if not txt: return
        try:
            parsed = json.loads(txt)
            formatted = json.dumps(parsed, indent=4, ensure_ascii=False)
            self.txt_editor.setPlainText(formatted)
        except Exception as e:
            QMessageBox.warning(self, "Error JSON", f"Formato JSON inválido:\n{e}")

    def _minificar_json(self):
        txt = self.txt_editor.toPlainText().strip()
        if not txt: return
        try:
            parsed = json.loads(txt)
            compact = json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
            self.txt_editor.setPlainText(compact)
        except Exception as e:
            QMessageBox.warning(self, "Error JSON", f"Formato JSON inválido:\n{e}")

    def _encode_base64(self):
        txt = self.txt_editor.toPlainText()
        if not txt: return
        try:
            encoded = base64.b64encode(txt.encode('utf-8')).decode('utf-8')
            self.txt_editor.setPlainText(encoded)
        except Exception as e:
            QMessageBox.warning(self, "Error Base64", f"Error al codificar:\n{e}")

    def _decode_base64(self):
        txt = self.txt_editor.toPlainText().strip()
        if not txt: return
        try:
            decoded = base64.b64decode(txt.encode('utf-8')).decode('utf-8')
            self.txt_editor.setPlainText(decoded)
        except Exception as e:
            QMessageBox.warning(self, "Error Base64", f"Cadena Base64 inválida:\n{e}")

    def _encode_url(self):
        txt = self.txt_editor.toPlainText()
        if not txt: return
        self.txt_editor.setPlainText(urllib.parse.quote(txt))

    def _decode_url(self):
        txt = self.txt_editor.toPlainText()
        if not txt: return
        self.txt_editor.setPlainText(urllib.parse.unquote(txt))

    def _to_upper(self):
        self.txt_editor.setPlainText(self.txt_editor.toPlainText().upper())

    def _to_lower(self):
        self.txt_editor.setPlainText(self.txt_editor.toPlainText().lower())

    def _to_title(self):
        self.txt_editor.setPlainText(self.txt_editor.toPlainText().title())

    def _to_capitalize(self):
        txt = self.txt_editor.toPlainText()
        self.txt_editor.setPlainText(txt.capitalize() if txt else "")

    def _extract_words(self, txt: str):
        # Separa transiciones camelCase/PascalCase antes de extraer palabras
        s = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', txt)
        return re.findall(r'[a-zA-Z0-9]+', s)

    def _to_camel_case(self):
        txt = self.txt_editor.toPlainText()
        words = self._extract_words(txt)
        if words:
            camel = words[0].lower() + "".join(w.capitalize() for w in words[1:])
            self.txt_editor.setPlainText(camel)

    def _to_snake_case(self):
        txt = self.txt_editor.toPlainText()
        words = self._extract_words(txt)
        if words:
            self.txt_editor.setPlainText("_".join(w.lower() for w in words))

    def _to_kebab_case(self):
        txt = self.txt_editor.toPlainText()
        words = self._extract_words(txt)
        if words:
            self.txt_editor.setPlainText("-".join(w.lower() for w in words))

    def _sanitizar_texto(self):
        txt = self.txt_editor.toPlainText()
        if not txt: return
        cleaned = "\n".join([line.strip() for line in txt.splitlines() if line.strip()])
        self.txt_editor.setPlainText(cleaned)

    def _eliminar_duplicados(self):
        txt = self.txt_editor.toPlainText()
        if not txt: return
        vistos = set()
        resultado = []
        for line in txt.splitlines():
            if line not in vistos:
                vistos.add(line)
                resultado.append(line)
        self.txt_editor.setPlainText("\n".join(resultado))

    def _ordenar_lineas(self, reverse=False):
        txt = self.txt_editor.toPlainText()
        if not txt: return
        lineas = txt.splitlines()
        lineas.sort(reverse=reverse)
        self.txt_editor.setPlainText("\n".join(lineas))

    def _invertir_lineas(self):
        txt = self.txt_editor.toPlainText()
        if not txt: return
        lineas = txt.splitlines()
        lineas.reverse()
        self.txt_editor.setPlainText("\n".join(lineas))

    def _eliminar_lineas_vacias(self):
        txt = self.txt_editor.toPlainText()
        if not txt: return
        lineas = [l for l in txt.splitlines() if l.strip()]
        self.txt_editor.setPlainText("\n".join(lineas))

    def _generar_hash(self, algoritmo="sha256"):
        txt = self.txt_editor.toPlainText()
        if not txt: return
        h = hashlib.new(algoritmo, txt.encode('utf-8')).hexdigest()
        self.txt_editor.setPlainText(h)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.txt_editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: {self.colores.get('fg_principal', '#E2E2E2')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px; padding: 10px;
            }}
            QPlainTextEdit:focus {{
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
