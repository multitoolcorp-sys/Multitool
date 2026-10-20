"""
snippets_clip.py - Submódulo de Snippets, Plantillas y Textos Frecuentes con Variables Dinámicas
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QLineEdit, QPlainTextEdit, QComboBox, QDialog, QMessageBox, 
    QApplication, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


CATEGORIAS_SNIPPETS = ["✍️ Firmas", "💻 Código", "📧 Correos", "📝 General", "⚡ Respuestas Rápidas"]

DEFAULT_SNIPPETS = [
    {
        "titulo": "Saludos Atentos",
        "categoria": "✍️ Firmas",
        "texto": "Quedo atento a cualquier duda o comentario.\nSaludos cordiales,\n{USUARIO} ({FECHA})"
    },
    {
        "titulo": "Función Main Python",
        "categoria": "💻 Código",
        "texto": "def main():\n    print('Iniciando script...')\n\nif __name__ == '__main__':\n    main()"
    },
    {
        "titulo": "Plantilla Respuesta Correo",
        "categoria": "📧 Correos",
        "texto": "Hola,\n\nGracias por comunicarte. He recibido tu mensaje el día {FECHA} a las {HORA} y me pondré en contacto en breve.\n\nAtentamente,\n{USUARIO}"
    },
    {
        "titulo": "Envoltorio Portapapeles",
        "categoria": "📝 General",
        "texto": "/* INICIO BLOQUE [{FECHA}] */\n{PORTAPAPELES}\n/* FIN BLOQUE */"
    }
]


def interpolar_snippet(texto, usuario="Usuario"):
    """Reemplaza placeholders dinámicos con datos en tiempo real."""
    ahora = datetime.now()
    clip_txt = ""
    try:
        clip_txt = QApplication.clipboard().text() or ""
    except Exception:
        pass

    resultado = str(texto)
    resultado = resultado.replace("{FECHA}", ahora.strftime("%d/%m/%Y"))
    resultado = resultado.replace("{HORA}", ahora.strftime("%H:%M"))
    resultado = resultado.replace("{FECHA_HORA}", ahora.strftime("%d/%m/%Y %H:%M"))
    resultado = resultado.replace("{USUARIO}", str(usuario))
    resultado = resultado.replace("{PORTAPAPELES}", clip_txt)
    resultado = resultado.replace("{UUID}", uuid.uuid4().hex[:8])
    return resultado


class TabSnippetsClipboard(QWidget):
    """Submódulo de Armario de Snippets, Plantillas y Textos Frecuentes"""
    def __init__(self, parent=None, colores=None, ruta_usuario=None):
        super().__init__(parent)
        self.colores = colores or {}
        ruta = Path(ruta_usuario or ".")
        self.ruta_json = ruta / "snippets_data.json"
        self.snippets = []

        self.cargar_snippets()
        self.init_ui()

    def init_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(16, 16, 16, 16)
        main_lay.setSpacing(10)

        # ── Header ──
        hdr = QHBoxLayout()
        lbl_t = QLabel("📌 ARMARIO DE SNIPPETS & PLANTILLAS")
        lbl_t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        hdr.addWidget(lbl_t)
        hdr.addStretch()

        self.lbl_count = QLabel(f"{len(self.snippets)} plantillas")
        self.lbl_count.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 11px;")
        hdr.addWidget(self.lbl_count)

        btn_exp = QPushButton("📤 Exportar")
        btn_exp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exp.setStyleSheet(self._subtle_btn_style())
        btn_exp.clicked.connect(self._exportar_snippets)
        hdr.addWidget(btn_exp)

        btn_imp = QPushButton("📥 Importar")
        btn_imp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_imp.setStyleSheet(self._subtle_btn_style())
        btn_imp.clicked.connect(self._importar_snippets)
        hdr.addWidget(btn_imp)

        btn_new = QPushButton("➕ Nuevo Snippet")
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')}; color: white;
                border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 11px;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_new.clicked.connect(lambda: self._dialog_snippet())
        hdr.addWidget(btn_new)
        main_lay.addLayout(hdr)

        # ── Barra de Búsqueda y Filtro de Categoría ──
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar por título o contenido...")
        self.txt_buscar.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white;
                border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); padding: 6px 10px;
                font-size: 11px;
            }}
            QLineEdit:focus {{ border-color: {self.colores.get('acento', '#6366F1')}; }}
        """)
        self.txt_buscar.textChanged.connect(self.refrescar_lista)
        bar.addWidget(self.txt_buscar, 1)

        self.combo_cat = QComboBox()
        self.combo_cat.addItems(["Todas las Categorías"] + CATEGORIAS_SNIPPETS)
        self.combo_cat.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white;
                border-radius: 6px; padding: 5px 10px; border: 1px solid rgba(255,255,255,0.1);
                font-size: 11px;
            }}
        """)
        self.combo_cat.currentIndexChanged.connect(self.refrescar_lista)
        bar.addWidget(self.combo_cat)

        main_lay.addLayout(bar)

        # ── Scroll Area de Snippets ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container = QWidget()
        self.lay_snip = QVBoxLayout(self.container)
        self.lay_snip.setSpacing(8)
        self.lay_snip.addStretch()
        scroll.setWidget(self.container)
        main_lay.addWidget(scroll, 1)

        self.refrescar_lista()

    def _subtle_btn_style(self):
        return f"""
            QPushButton {{
                background: rgba(255,255,255,0.06); color: white;
                border: 1px solid rgba(255,255,255,0.1); border-radius: 6px;
                padding: 5px 10px; font-size: 10px; font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.12);
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """

    def cargar_snippets(self):
        if self.ruta_json.exists():
            try:
                with open(self.ruta_json, "r", encoding="utf-8") as f:
                    self.snippets = json.load(f)
            except Exception:
                self.snippets = []

        if not self.snippets:
            self.snippets = list(DEFAULT_SNIPPETS)
            self.guardar_snippets()

    def guardar_snippets(self):
        try:
            with open(self.ruta_json, "w", encoding="utf-8") as f:
                json.dump(self.snippets, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def _guardar_snippets(self):
        self.guardar_snippets()

    def refrescar_lista(self):
        while self.lay_snip.count() > 1:
            item = self.lay_snip.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cat_sel = self.combo_cat.currentText()
        query = self.txt_buscar.text().strip().lower()

        visibles = 0
        for idx, snip in enumerate(self.snippets):
            categoria = snip.get("categoria", "📝 General")
            if cat_sel != "Todas las Categorías" and categoria != cat_sel:
                continue

            titulo = snip.get("titulo", "")
            texto = snip.get("texto", "")

            if query and (query not in titulo.lower() and query not in texto.lower()):
                continue

            card = self._crear_card_snippet(idx, snip)
            self.lay_snip.insertWidget(self.lay_snip.count() - 1, card)
            visibles += 1

        if visibles == 0:
            empty_card = QFrame()
            empty_card.setStyleSheet(f"""
                QFrame {{
                    background: rgba(30, 30, 46, 0.4);
                    border: 1px dashed rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    padding: 30px;
                }}
            """)
            e_lay = QVBoxLayout(empty_card)
            e_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            e_lbl = QLabel("📌 No se encontraron plantillas o snippets")
            e_lbl.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 12px; font-weight: bold;")
            e_lay.addWidget(e_lbl)

            btn_crear = QPushButton("➕ Crear Primer Snippet")
            btn_crear.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_crear.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores.get('acento', '#6366F1')}; color: white;
                    border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 11px;
                }}
            """)
            btn_crear.clicked.connect(lambda: self._dialog_snippet())
            e_lay.addWidget(btn_crear)
            self.lay_snip.insertWidget(0, empty_card)

        self.lbl_count.setText(f"{len(self.snippets)} plantillas ({visibles} visibles)")

    def _crear_card_snippet(self, idx, snip):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px;
            }}
            QFrame:hover {{ border-color: {self.colores.get('acento', '#6366F1')}; }}
        """)
        c_lay = QVBoxLayout(card)
        c_lay.setSpacing(6)

        top = QHBoxLayout()
        lbl_title = QLabel(f"{snip.get('categoria', '📝')}  {snip.get('titulo', 'Snippet')}")
        lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        top.addWidget(lbl_title)
        top.addStretch()

        # Botón Editar
        btn_edit = QPushButton("✏️")
        btn_edit.setFixedSize(24, 24)
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setToolTip("Editar plantilla")
        btn_edit.setStyleSheet("background: rgba(255,255,255,0.06); border: none; border-radius: 4px; font-size: 11px;")
        btn_edit.clicked.connect(lambda ch, i=idx: self._dialog_snippet(i))
        top.addWidget(btn_edit)

        # Botón Eliminar
        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(24, 24)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setToolTip("Eliminar plantilla")
        btn_del.setStyleSheet("background: rgba(248,113,113,0.15); color: #F87171; border: none; border-radius: 4px; font-size: 11px;")
        btn_del.clicked.connect(lambda ch, i=idx: self._borrar_snippet(i))
        top.addWidget(btn_del)

        c_lay.addLayout(top)

        # Vista previa del texto
        texto_raw = snip.get("texto", "")
        preview = texto_raw[:160] + ("…" if len(texto_raw) > 160 else "")
        lbl_body = QLabel(preview)
        lbl_body.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px; font-family: Consolas, monospace;")
        lbl_body.setWordWrap(True)
        lbl_body.setMaximumHeight(50)
        c_lay.addWidget(lbl_body)

        # Barra inferior de acción
        b_lay = QHBoxLayout()
        if "{" in texto_raw and "}" in texto_raw:
            lbl_dyn = QLabel("⚡ Contiene variables dinámicas")
            lbl_dyn.setStyleSheet("color: #FBBF24; font-size: 9px; font-weight: bold;")
            b_lay.addWidget(lbl_dyn)
        b_lay.addStretch()

        btn_copy = QPushButton("📋 Copiar al Portapapeles")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')}; color: white;
                border: none; border-radius: 5px; padding: 5px 12px; font-size: 10px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_copy.clicked.connect(lambda ch, s=snip: self._copiar_snippet(s))
        b_lay.addWidget(btn_copy)

        c_lay.addLayout(b_lay)
        return card

    def _obtener_usuario(self):
        p = self.parent()
        while p:
            if hasattr(p, "context") and hasattr(p.context, "usuario"):
                return p.context.usuario
            if hasattr(p, "usuario"):
                return p.usuario
            p = p.parent()
        return "Usuario"

    def _interpolar_variables(self, texto):
        """Interpola variables dinámicas ({FECHA}, {HORA}, {USUARIO}, etc.)."""
        return interpolar_snippet(texto, usuario=self._obtener_usuario())

    def _copiar_snippet(self, snip):
        raw = snip.get("texto", "")
        procesado = self._interpolar_variables(raw)
        QApplication.clipboard().setText(procesado)
        QMessageBox.information(self, "Copiado", f"Plantilla '{snip.get('titulo')}' copiada al portapapeles con sus variables actualizadas.")

    def _borrar_snippet(self, idx):
        if 0 <= idx < len(self.snippets):
            tit = self.snippets[idx].get("titulo", "")
            resp = QMessageBox.question(self, "Eliminar", f"¿Eliminar la plantilla '{tit}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if resp == QMessageBox.StandardButton.Yes:
                self.snippets.pop(idx)
                self.guardar_snippets()
                self.refrescar_lista()

    def agregar_desde_historial(self, texto: str, titulo: str = "", auto_guardar: bool = False):
        """Abre el diálogo de plantilla pre-rellenado desde una copia guardada del historial."""
        sugerido = titulo or (texto.splitlines()[0][:30].strip() if texto.strip() else "Copia Guardada")
        if auto_guardar:
            snip = {"titulo": sugerido, "categoria": "📝 General", "texto": texto}
            self.snippets.insert(0, snip)
            self.guardar_snippets()
            self.refrescar_lista()
            return
        self._dialog_snippet(None, texto_inicial=texto, titulo_inicial=sugerido)

    def _dialog_snippet(self, snip_idx=None, texto_inicial="", titulo_inicial=""):
        es_edicion = snip_idx is not None and 0 <= snip_idx < len(self.snippets)
        if es_edicion:
            snip = self.snippets[snip_idx]
        else:
            snip = {
                "titulo": titulo_inicial,
                "categoria": "📝 General",
                "texto": texto_inicial
            }

        dlg = QDialog(self)
        dlg.setWindowTitle("Editar Plantilla" if es_edicion else "Guardar Copia como Snippet / Plantilla")
        dlg.setMinimumWidth(440)
        dlg.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; color: white;")

        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Título de la Copia / Plantilla:"))
        txt_t = QLineEdit(snip.get("titulo", ""))
        txt_t.setPlaceholderText("Ej: Copia Importante, Saludo, Clave de Acceso...")
        txt_t.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 6px; border: 1px solid rgba(255,255,255,0.1);")
        lay.addWidget(txt_t)

        lay.addWidget(QLabel("Categoría:"))
        combo_c = QComboBox()
        combo_c.addItems(CATEGORIAS_SNIPPETS)
        if snip.get("categoria") in CATEGORIAS_SNIPPETS:
            combo_c.setCurrentText(snip.get("categoria"))
        combo_c.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 6px; border: 1px solid rgba(255,255,255,0.1);")
        lay.addWidget(combo_c)

        lay.addWidget(QLabel("Contenido de Texto:"))
        txt_b = QPlainTextEdit(snip.get("texto", ""))
        txt_b.setPlaceholderText("Escribe aquí el texto o código...")
        txt_b.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 8px; border: 1px solid rgba(255,255,255,0.1); font-family: Consolas, monospace;")
        lay.addWidget(txt_b)

        # Barra de inserción de variables
        lbl_vars = QLabel("⚡ Insertar variable dinámica:")
        lbl_vars.setStyleSheet("color: #FBBF24; font-size: 10px; font-weight: bold;")
        lay.addWidget(lbl_vars)

        v_lay = QHBoxLayout()
        for v_name, tag in [
            ("📅 Fecha", "{FECHA}"),
            ("⏰ Hora", "{HORA}"),
            ("👤 Usuario", "{USUARIO}"),
            ("📋 Portapapeles", "{PORTAPAPELES}"),
            ("🔑 UUID", "{UUID}")
        ]:
            b_var = QPushButton(v_name)
            b_var.setCursor(Qt.CursorShape.PointingHandCursor)
            b_var.setStyleSheet("background: rgba(255,255,255,0.06); color: #E2E2E2; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 2px 6px; font-size: 9px;")
            b_var.clicked.connect(lambda ch, t=tag: txt_b.insertPlainText(t))
            v_lay.addWidget(b_var)
        v_lay.addStretch()
        lay.addLayout(v_lay)

        btn_save = QPushButton("💾 Guardar Cambios" if es_edicion else "💾 Crear Plantilla")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; font-weight: bold; border-radius: 6px; padding: 8px; border: none;")

        def save():
            tit = txt_t.text().strip()
            cont = txt_b.toPlainText().strip()
            if not tit or not cont:
                QMessageBox.warning(dlg, "Campos Vacíos", "Por favor completa el título y el contenido.")
                return

            data = {
                "titulo": tit,
                "categoria": combo_c.currentText(),
                "texto": txt_b.toPlainText()
            }
            if es_edicion:
                self.snippets[snip_idx] = data
            else:
                self.snippets.insert(0, data)

            self.guardar_snippets()
            self.refrescar_lista()
            dlg.accept()

        btn_save.clicked.connect(save)
        lay.addWidget(btn_save)

        dlg.exec()

    def _exportar_snippets(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Snippets", "snippets_backup.json", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.snippets, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Éxito", f"Se exportaron {len(self.snippets)} plantillas correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar: {e}")

    def _importar_snippets(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Snippets", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                nuevos = json.load(f)
            if isinstance(nuevos, list):
                agregados = 0
                for n in nuevos:
                    if isinstance(n, dict) and "titulo" in n and "texto" in n:
                        self.snippets.append(n)
                        agregados += 1
                self.guardar_snippets()
                self.refrescar_lista()
                QMessageBox.information(self, "Éxito", f"Se importaron {agregados} plantillas correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo importar: {e}")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.refrescar_lista()
