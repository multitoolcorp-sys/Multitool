"""
tab_tablero_notas.py - Tablero de Notas Rápidas y Vista Mosaico (Sticky Notes)
"""
import os
import json
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QScrollArea, QGridLayout, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextDocument


PASTEL_COLORS = [
    {"bg": "#FEF9C3", "fg": "#1E293B", "border": "#FDE047", "name": "Amarillo"},
    {"bg": "#DBEAFE", "fg": "#1E293B", "border": "#93C5FD", "name": "Azul"},
    {"bg": "#DCFCE7", "fg": "#1E293B", "border": "#86EFAC", "name": "Verde"},
    {"bg": "#F3E8FF", "fg": "#1E293B", "border": "#D8B4FE", "name": "Lavanda"},
    {"bg": "#FEE2E2", "fg": "#1E293B", "border": "#FCA5A5", "name": "Rosa"},
    {"bg": "#FFEDD5", "fg": "#1E293B", "border": "#FDBA74", "name": "Melocotón"}
]


class TableroNotasGUI(QWidget):
    """Lienzo visual estilo Post-It / Google Keep para notas rápidas y navegación en mosaico"""
    def __init__(self, parent=None, context=None, colores=None, callbacks=None, **kwargs):
        super().__init__(parent)
        self.context = context
        self.colores = colores or (getattr(context, "colores", {}) if context else {})
        self.callbacks = callbacks or {}
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.ruta_notas = self.ruta_usuario / "notas"
        self.ruta_notas.mkdir(parents=True, exist_ok=True)
        self.filtro_busqueda = ""
        self.filtro_tag = None

        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_p}; color: white;")
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(18, 18, 18, 18)
        main_lay.setSpacing(14)

        # Header con barra de creación rápida y controles
        top_bar = QFrame()
        top_bar.setStyleSheet(f"background: {bg_sec}; border-radius: 10px; padding: 6px;")
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(12, 6, 12, 6)
        top_lay.setSpacing(10)

        lbl_tit = QLabel("📌 TABLERO MOSAICO")
        lbl_tit.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento};")
        top_lay.addWidget(lbl_tit)

        # Input Nota Rápida
        self.txt_rapida = QLineEdit()
        self.txt_rapida.setPlaceholderText("💡 Escribe una nota rápida y pulsa Enter o Agregar...")
        self.txt_rapida.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(0,0,0,0.25); color: white; border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px; padding: 6px 12px; font-size: 11px;
            }}
            QLineEdit:focus {{ border-color: {acento}; }}
        """)
        self.txt_rapida.returnPressed.connect(self._crear_nota_rapida)
        top_lay.addWidget(self.txt_rapida, 1)

        self.combo_color = QComboBox()
        for idx, col in enumerate(PASTEL_COLORS):
            self.combo_color.addItem(f"● {col['name']}", idx)
        self.combo_color.setStyleSheet("""
            QComboBox { background: rgba(0,0,0,0.25); color: white; border-radius: 6px; padding: 4px 8px; font-size: 10px; }
            QComboBox::drop-down { border: none; }
        """)
        top_lay.addWidget(self.combo_color)

        btn_add = QPushButton("➕ Crear")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background: {acento}; color: white; border-radius: 6px; font-weight: bold;
                padding: 6px 14px; font-size: 11px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_add.clicked.connect(self._crear_nota_rapida)
        top_lay.addWidget(btn_add)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setFixedSize(30, 30)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setToolTip("Refrescar tablero")
        btn_refresh.setStyleSheet("background: rgba(255,255,255,0.06); color: white; border-radius: 6px; border: none;")
        btn_refresh.clicked.connect(self.recargar_tablero)
        top_lay.addWidget(btn_refresh)

        main_lay.addWidget(top_bar)

        # Barra de Búsqueda y Filtros
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Filtrar tarjetas por título o palabra clave...")
        self.txt_buscar.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.04); color: white; border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px; padding: 5px 10px; font-size: 11px;
            }
        """)
        self.txt_buscar.textChanged.connect(self._on_search_changed)
        filter_bar.addWidget(self.txt_buscar, 1)

        self.lbl_contador = QLabel("0 notas")
        self.lbl_contador.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px;")
        filter_bar.addWidget(self.lbl_contador)

        main_lay.addLayout(filter_bar)

        # Área de Scroll con rejilla de tarjetas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.grid_cards = QGridLayout(self.cards_container)
        self.grid_cards.setSpacing(14)
        self.grid_cards.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self.cards_container)
        main_lay.addWidget(scroll, 1)

        self.recargar_tablero()

    def _on_search_changed(self, text):
        self.filtro_busqueda = text.strip().lower()
        self.recargar_tablero()

    def _crear_nota_rapida(self):
        txt = self.txt_rapida.text().strip()
        if not txt:
            return
        
        fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"Nota_{fecha}"
        color_idx = self.combo_color.currentData()
        pastel = PASTEL_COLORS[color_idx] if 0 <= color_idx < len(PASTEL_COLORS) else PASTEL_COLORS[0]
        
        # Color mapping to storage pastel theme ids
        tema_map = ["yellow", "blue", "green", "purple", "pink", "orange"]
        tema_id = tema_map[color_idx] if color_idx < len(tema_map) else "yellow"

        datos = {
            "html": f"<p>{txt}</p>",
            "imagenes_metadata": {},
            "favorita": False,
            "background_color": tema_id,
            "tablero_color": pastel["bg"]
        }
        ruta_nota = self.ruta_notas / f"{nombre}.txt"
        try:
            with open(ruta_nota, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=4)
            self.txt_rapida.clear()
            self.recargar_tablero()

            # Notificar al módulo principal si existe
            parent_tab = self.parent()
            while parent_tab and not hasattr(parent_tab, "cargar_lista_notas"):
                parent_tab = parent_tab.parent()
            if parent_tab and hasattr(parent_tab, "cargar_lista_notas"):
                parent_tab.cargar_lista_notas()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear la nota rápida: {e}")

    def recargar_tablero(self):
        # Limpiar rejilla
        while self.grid_cards.count():
            item = self.grid_cards.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        archivos = list(self.ruta_notas.glob("*.txt"))
        archivos.sort(key=lambda x: -os.path.getmtime(x))

        # Cargar etiquetas
        tags_map = {}
        ruta_tags = self.ruta_usuario / "notas_tags.json"
        if ruta_tags.exists():
            try:
                with open(ruta_tags, "r", encoding="utf-8") as f:
                    tags_map = json.load(f)
            except Exception:
                pass

        tarjetas_mostradas = 0
        columnas = 3

        for archivo in archivos:
            nombre = archivo.stem
            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    raw = f.read()
                
                html = ""
                bg_custom = None
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        html = data.get("html", "")
                        bg_custom = data.get("tablero_color")
                except Exception:
                    html = raw

                doc = QTextDocument()
                doc.setHtml(html)
                texto_plano = doc.toPlainText().strip()

                # Filtro de búsqueda
                if self.filtro_busqueda:
                    if self.filtro_busqueda not in nombre.lower() and self.filtro_busqueda not in texto_plano.lower():
                        continue

                # Determinar color pastel
                color_obj = PASTEL_COLORS[tarjetas_mostradas % len(PASTEL_COLORS)]
                bg_card = bg_custom or color_obj["bg"]
                fg_card = "#1E293B"
                border_card = color_obj["border"]

                card = QFrame()
                card.setFixedWidth(260)
                card.setMinimumHeight(170)
                card.setMaximumHeight(240)
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {bg_card};
                        border: 1px solid {border_card};
                        border-radius: 12px;
                        padding: 12px;
                    }}
                """)
                card_lay = QVBoxLayout(card)
                card_lay.setContentsMargins(10, 10, 10, 10)
                card_lay.setSpacing(6)

                # Header tarjeta (Título y fecha)
                row_th = QHBoxLayout()
                lbl_t = QLabel(nombre)
                lbl_t.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                lbl_t.setStyleSheet(f"color: {fg_card};")
                lbl_t.setWordWrap(True)
                row_th.addWidget(lbl_t, 1)

                card_lay.addLayout(row_th)

                # Tags si tiene
                tags = tags_map.get(nombre, [])
                if tags:
                    tags_str = " ".join([f"#{t}" for t in tags[:3]])
                    lbl_tag = QLabel(tags_str)
                    lbl_tag.setStyleSheet("color: #4F46E5; font-size: 8px; font-weight: bold;")
                    card_lay.addWidget(lbl_tag)

                # Preview de texto
                snippet = (texto_plano[:140] + "...") if len(texto_plano) > 140 else (texto_plano or "(Nota sin texto)")
                lbl_snip = QLabel(snippet)
                lbl_snip.setFont(QFont("Segoe UI", 9))
                lbl_snip.setStyleSheet(f"color: {fg_card};")
                lbl_snip.setWordWrap(True)
                card_lay.addWidget(lbl_snip, 1)

                # Botones de Acción
                row_act = QHBoxLayout()
                row_act.setSpacing(4)

                mtime = os.path.getmtime(archivo)
                fecha_str = datetime.datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
                lbl_fecha = QLabel(fecha_str)
                lbl_fecha.setStyleSheet("color: #64748B; font-size: 8px;")
                row_act.addWidget(lbl_fecha)
                row_act.addStretch()

                btn_edit = QPushButton("✏️ Abrir")
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setStyleSheet(f"""
                    QPushButton {{
                        background: rgba(0,0,0,0.1); color: {fg_card}; border-radius: 4px;
                        padding: 3px 8px; font-size: 9px; font-weight: bold; border: 1px solid rgba(0,0,0,0.1);
                    }}
                    QPushButton:hover {{ background: rgba(0,0,0,0.2); }}
                """)
                btn_edit.clicked.connect(lambda ch, n=nombre: self._abrir_en_editor(n))
                row_act.addWidget(btn_edit)

                card_lay.addLayout(row_act)

                row = tarjetas_mostradas // columnas
                col = tarjetas_mostradas % columnas
                self.grid_cards.addWidget(card, row, col)
                tarjetas_mostradas += 1

            except Exception:
                continue

        self.lbl_contador.setText(f"{tarjetas_mostradas} notas visualizadas")

    def _abrir_en_editor(self, nombre):
        parent_tab = self.parent()
        while parent_tab and not hasattr(parent_tab, "tabs"):
            parent_tab = parent_tab.parent()
        
        if parent_tab and hasattr(parent_tab, "tabs"):
            if hasattr(parent_tab, "seleccionar_nota_por_nombre"):
                parent_tab.seleccionar_nota_por_nombre(nombre)
            parent_tab.tabs.setCurrentIndex(0)
