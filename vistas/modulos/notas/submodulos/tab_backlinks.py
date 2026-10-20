"""
tab_backlinks.py - Submódulo de Enlaces Bidireccionales (Backlinks) y Red de Conexiones de Notas
Detecta enlaces estilo [[Nombre de Nota]] entre notas y muestra el mapa de conexiones e interconexión del conocimiento.
"""
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QListWidget, QListWidgetItem, QSplitter, QTextEdit,
    QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class TabBacklinksGUI(QWidget):
    """Submódulo para explorar la red de notas interconectadas y enlaces bidireccionales"""
    nota_solicitada = pyqtSignal(str)

    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent if isinstance(parent, QWidget) else None)
        self.context = context
        self.colores = colores or (getattr(context.app, "COLORES", {}) if context and hasattr(context, "app") else {})

        self.ruta_usuario = Path(getattr(self.context, "ruta_usuario", ".")) if self.context else Path(".")
        self.ruta_notas = self.ruta_usuario / "notas"

        # Grafos en memoria: outgoing_links[nota] = set(destinos), incoming_links[nota] = set(origenes)
        self.outgoing_links = {}
        self.incoming_links = {}
        self.todas_las_notas = []

        self.init_ui()
        self.escanear_red()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(18, 18, 18, 18)
        main_lay.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        info_col = QVBoxLayout()
        lbl_titulo = QLabel("🔗 Red de Conexiones & Backlinks")
        lbl_titulo.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')};")

        lbl_sub = QLabel("Descubre cómo se relacionan tus notas usando enlaces [[Nombre de Nota]].")
        lbl_sub.setFont(QFont("Segoe UI", 10))
        lbl_sub.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#A0A0A0')};")
        info_col.addWidget(lbl_titulo)
        info_col.addWidget(lbl_sub)

        btn_refrescar = QPushButton("🔄 Actualizar Red")
        btn_refrescar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refrescar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: {self.colores.get('fg_principal', '#FFFFFF')};
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn_refrescar.clicked.connect(self.escanear_red)

        top_bar.addLayout(info_col)
        top_bar.addStretch()
        top_bar.addWidget(btn_refrescar)
        main_lay.addLayout(top_bar)

        # Tarjetas de estadísticas de la red
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(12)
        main_lay.addLayout(self.stats_row)

        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.06); width: 2px; }")

        # Panel izquierdo: Lista de notas
        panel_izq = QFrame()
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        panel_izq.setStyleSheet(f"background-color: {bg_sec}; border-radius: 10px; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};")
        izq_lay = QVBoxLayout(panel_izq)
        izq_lay.setContentsMargins(12, 12, 12, 12)
        izq_lay.setSpacing(10)

        lbl_col1 = QLabel("Notas Registradas")
        lbl_col1.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_col1.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')}; border: none;")
        izq_lay.addWidget(lbl_col1)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Filtrar nota...")
        self.txt_buscar.setStyleSheet(f"background-color: {bg_p}; color: white; border-radius: 6px; padding: 6px 10px; border: none;")
        self.txt_buscar.textChanged.connect(self._filtrar_lista)
        izq_lay.addWidget(self.txt_buscar)

        self.lista_notas = QListWidget()
        self.lista_notas.setStyleSheet(f"background-color: {bg_p}; color: white; border-radius: 8px; border: none; padding: 4px;")
        self.lista_notas.currentRowChanged.connect(self._nota_seleccionada)
        izq_lay.addWidget(self.lista_notas)

        splitter.addWidget(panel_izq)

        # Panel derecho: Detalle de conexiones de la nota activa
        panel_der = QFrame()
        panel_der.setStyleSheet(f"background-color: {bg_sec}; border-radius: 10px; border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};")
        der_lay = QVBoxLayout(panel_der)
        der_lay.setContentsMargins(16, 16, 16, 16)
        der_lay.setSpacing(12)

        self.lbl_nota_activa = QLabel("Selecciona una nota para ver sus conexiones")
        self.lbl_nota_activa.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_nota_activa.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; border: none;")
        der_lay.addWidget(self.lbl_nota_activa)

        # Backlinks entrantes (Notas que citan a esta nota)
        lbl_in = QLabel("⬅️ Mencionada en (Backlinks Entrantes):")
        lbl_in.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_in.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')}; border: none;")
        der_lay.addWidget(lbl_in)

        self.lista_incoming = QListWidget()
        self.lista_incoming.setStyleSheet(f"background-color: {bg_p}; color: white; border-radius: 6px; border: none; max-height: 140px;")
        der_lay.addWidget(self.lista_incoming)

        # Links salientes (Notas que esta nota cita)
        lbl_out = QLabel("➡️ Enlaces Salientes (Esta nota cita a):")
        lbl_out.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_out.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')}; border: none;")
        der_lay.addWidget(lbl_out)

        self.lista_outgoing = QListWidget()
        self.lista_outgoing.setStyleSheet(f"background-color: {bg_p}; color: white; border-radius: 6px; border: none; max-height: 140px;")
        der_lay.addWidget(self.lista_outgoing)

        der_lay.addStretch()
        splitter.addWidget(panel_der)
        splitter.setSizes([300, 500])

        main_lay.addWidget(splitter, 1)

    def escanear_red(self):
        """Escanea todos los archivos .txt y extrae referencias de [[Nota]]"""
        self.outgoing_links.clear()
        self.incoming_links.clear()
        self.todas_las_notas.clear()

        if not self.ruta_notas.exists():
            return

        regex_wiki = re.compile(r'\[\[(.*?)\]\]')

        archivos = list(self.ruta_notas.glob("*.txt"))
        nombres = [f.stem for f in archivos if not f.stem.startswith(".")]
        self.todas_las_notas = sorted(nombres)

        for n in self.todas_las_notas:
            self.outgoing_links[n] = set()
            if n not in self.incoming_links:
                self.incoming_links[n] = set()

        for f in archivos:
            origen = f.stem
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    contenido = fp.read()
                matches = regex_wiki.findall(contenido)
                for destino in matches:
                    dest_limpio = destino.strip()
                    if dest_limpio:
                        self.outgoing_links[origen].add(dest_limpio)
                        if dest_limpio not in self.incoming_links:
                            self.incoming_links[dest_limpio] = set()
                        self.incoming_links[dest_limpio].add(origen)
            except Exception:
                pass

        self._actualizar_estadisticas_cards()
        self._filtrar_lista()

    def _actualizar_estadisticas_cards(self):
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        total_notas = len(self.todas_las_notas)
        total_conexiones = sum(len(v) for v in self.outgoing_links.values())
        huerfanas = sum(1 for n in self.todas_las_notas if len(self.outgoing_links.get(n, set())) == 0 and len(self.incoming_links.get(n, set())) == 0)

        metricas = [
            ("📄 Total Notas", str(total_notas), self.colores.get('acento', '#6366F1')),
            ("🔗 Conexiones [[ ]]", str(total_conexiones), self.colores.get('exito', '#10B981')),
            ("🏝️ Notas Huérfanas", str(huerfanas), self.colores.get('advertencia', '#F59E0B')),
        ]

        bg_card = self.colores.get('bg_secundario', '#1E1E2E')
        for titulo, valor, color in metricas:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_card};
                    border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                    border-radius: 8px;
                    padding: 8px 14px;
                }}
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(4, 4, 4, 4)
            c_lay.setSpacing(2)
            lbl_v = QLabel(valor)
            lbl_v.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            lbl_v.setStyleSheet(f"color: {color}; border: none;")
            lbl_t = QLabel(titulo)
            lbl_t.setFont(QFont("Segoe UI", 9))
            lbl_t.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#A0A0A0')}; border: none;")
            c_lay.addWidget(lbl_v)
            c_lay.addWidget(lbl_t)
            self.stats_row.addWidget(card)

    def _filtrar_lista(self):
        query = self.txt_buscar.text().strip().lower()
        self.lista_notas.clear()
        for n in self.todas_las_notas:
            if not query or query in n.lower():
                conex = len(self.outgoing_links.get(n, set())) + len(self.incoming_links.get(n, set()))
                item = QListWidgetItem(f"📄 {n} ({conex} 🔗)")
                item.setData(Qt.ItemDataRole.UserRole, n)
                self.lista_notas.addItem(item)

        if self.lista_notas.count() > 0:
            self.lista_notas.setCurrentRow(0)

    def _nota_seleccionada(self, row):
        if row < 0:
            return
        item = self.lista_notas.item(row)
        if not item:
            return
        nombre_nota = item.data(Qt.ItemDataRole.UserRole)
        self.lbl_nota_activa.setText(f"📄 {nombre_nota}")

        # Cargar incoming
        self.lista_incoming.clear()
        incomings = sorted(list(self.incoming_links.get(nombre_nota, set())))
        if incomings:
            for inc in incomings:
                it = QListWidgetItem(f"⬅️ {inc}")
                self.lista_incoming.addItem(it)
        else:
            self.lista_incoming.addItem(QListWidgetItem("Ninguna nota enlaza a esta."))

        # Cargar outgoing
        self.lista_outgoing.clear()
        outgoings = sorted(list(self.outgoing_links.get(nombre_nota, set())))
        if outgoings:
            for outg in outgoings:
                it = QListWidgetItem(f"➡️ {outg}")
                self.lista_outgoing.addItem(it)
        else:
            self.lista_outgoing.addItem(QListWidgetItem("Esta nota no incluye enlaces [[ ]]."))

    def actualizar_tema(self, colores):
        if isinstance(colores, dict):
            self.colores = colores
            bg_p = self.colores.get('bg_principal', '#121218')
            self.setStyleSheet(f"background-color: {bg_p}; color: white;")
            self._actualizar_estadisticas_cards()
