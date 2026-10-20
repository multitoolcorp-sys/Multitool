import platform
import urllib.request
import urllib.parse
import json
import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QFrame, QScrollArea, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

try:
    from ..utils.reproductor_logger import ReproductorLogger
except Exception:
    class ReproductorLogger:
        @staticmethod
        def log(n, m): pass
        @staticmethod
        def info(m): pass
        @staticmethod
        def warning(m): pass
        @staticmethod
        def error(m): pass

class RadioStreamingSubmodule(QWidget):
    """Submódulo 4: Radio Online en Vivo con Integración a Radio Browser API (30,000+ Emisoras 100% Gratuitas y Verificadas)"""
    radio_busqueda_fin = pyqtSignal(list)

    STATIONS_DEFAULT = [
        {"name": "Arrow Classic Rock", "genre": "Classic Rock", "country": "Holanda", "url": "http://stream.gal.io/arrow", "icon": "🎸"},
        {"name": "ROCKANTENNE Alternative", "genre": "Alternative Rock", "country": "Alemania", "url": "https://s2-webradio.rockantenne.de/alternative/stream/mp3", "icon": "⚡"},
        {"name": "181.FM The Eagle", "genre": "Classic Hits & Rock", "country": "EE. UU.", "url": "https://listen.181fm.com/181-eagle_128k.mp3", "icon": "🦅"},
        {"name": "Power 181 Top 40", "genre": "Pop & Top 40 Hits", "country": "EE. UU.", "url": "https://listen.181fm.com/181-power_128k.mp3", "icon": "🔥"},
        {"name": "Dance Wave FM", "genre": "EDM & Club", "country": "Internacional", "url": "https://stream1.dancewave.online:8082/dance.mp3", "icon": "🎧"},
        {"name": "SomaFM Groove Salad", "genre": "Ambient & Chillout", "country": "EE. UU.", "url": "https://ice1.somafm.com/groovesalad-128-mp3", "icon": "☕"}
    ]

    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.radio_busqueda_fin.connect(self._on_radio_busqueda_fin)
        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("📻 RADIO ONLINE EN VIVO (30,000+ EMISORAS VERIFICADAS)")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; background: transparent;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        layout.addLayout(hdr)

        # Barra de Búsqueda de Radio
        search_f = QFrame()
        search_f.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }}
        """)
        s_lay = QHBoxLayout(search_f)
        s_lay.setContentsMargins(10, 8, 10, 8)
        s_lay.setSpacing(10)

        self.inp_radio_search = QLineEdit()
        self.inp_radio_search.setPlaceholderText("Busca emisoras verificadas (ej: Rock, Jazz, Metal, Pop, Mexico, Spain, Lofi)...")
        self.inp_radio_search.setFont(QFont(self.font_family, 10))
        self.inp_radio_search.setStyleSheet(f"background: {bg_terc}; border-radius: 8px; padding: 8px 12px; color: white; border: none;")
        self.inp_radio_search.returnPressed.connect(self._buscar_radios)
        s_lay.addWidget(self.inp_radio_search, 1)

        btn_search = QPushButton("🔍 Buscar Emisoras")
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_search.setStyleSheet(f"background: {acento}; border-radius: 8px; color: white; padding: 8px 18px; border: none;")
        btn_search.clicked.connect(self._buscar_radios)
        s_lay.addWidget(btn_search)

        layout.addWidget(search_f)

        # Label de estado de búsqueda
        self.lbl_radio_status = QLabel("⭐ Mostrando emisoras destacadas en vivo 100% verificadas:")
        self.lbl_radio_status.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_radio_status.setStyleSheet("color: rgba(255,255,255,0.7); background: transparent;")
        layout.addWidget(self.lbl_radio_status)

        # Scroll Area con Rejilla de Estaciones
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(f"QScrollArea {{ background-color: {bg_main}; border: none; }}")

        self.content = QWidget()
        self.content.setStyleSheet(f"background-color: {bg_main}; color: white;")
        self.grid = QGridLayout(self.content)
        self.grid.setSpacing(15)
        self.scroll.setWidget(self.content)

        layout.addWidget(self.scroll, 1)

        # Cargar emisoras destacadas al inicio
        self._renderizar_estaciones(self.STATIONS_DEFAULT)

    def _buscar_radios(self):
        query = self.inp_radio_search.text().strip()
        if not query:
            self.lbl_radio_status.setText("⭐ Mostrando emisoras destacadas en vivo 100% verificadas:")
            self._renderizar_estaciones(self.STATIONS_DEFAULT)
            return

        self.lbl_radio_status.setText(f"🔍 Buscando emisoras verificadas con el término '{query}'...")

        def run():
            try:
                # Filtrar solo emisoras verificadas (lastcheckok=1, hidebroken=true)
                url = f"https://de1.api.radio-browser.info/json/stations/search?name=" + urllib.parse.quote(query) + "&hidebroken=true&order=clickcount&reverse=true&limit=12"
                req = urllib.request.Request(url, headers={'User-Agent': 'MultiToolApp/1.0'})
                with urllib.request.urlopen(req, timeout=6) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    stations = []
                    for st in data:
                        name = st.get("name", "").strip()
                        stream_url = st.get("url_resolved") or st.get("url")
                        country = st.get("country", "Global")
                        tags = st.get("tags", "Radio")
                        if name and stream_url and stream_url.startswith("http"):
                            stations.append({
                                "name": name,
                                "url": stream_url,
                                "country": country,
                                "genre": tags[:30] if tags else "General",
                                "icon": "📻"
                            })
                    self.radio_busqueda_fin.emit(stations)
            except Exception:
                self.radio_busqueda_fin.emit([])

        threading.Thread(target=run, daemon=True).start()

    def _on_radio_busqueda_fin(self, stations):
        if not stations:
            self.lbl_radio_status.setText("⚠️ No se encontraron emisoras activas con ese término. Intenta con otra búsqueda (ej: Rock, Pop, Mexico):")
            stations = self.STATIONS_DEFAULT
        else:
            self.lbl_radio_status.setText(f"✅ Se encontraron {len(stations)} emisoras en vivo 100% verificadas:")
        self._renderizar_estaciones(stations)

    def _renderizar_estaciones(self, stations):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')

        for idx, station in enumerate(stations):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_sec};
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 12px;
                    padding: 10px;
                }}
                QFrame:hover {{
                    border: 1px solid {acento};
                }}
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setSpacing(8)

            top_row = QHBoxLayout()
            lbl_icon = QLabel(station.get("icon", "📻"))
            lbl_icon.setFont(QFont(self.font_family, 22))
            top_row.addWidget(lbl_icon)

            info_lay = QVBoxLayout()
            lbl_name = QLabel(station.get("name", "Radio Station"))
            lbl_name.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
            lbl_name.setStyleSheet("color: white; background: transparent;")
            info_lay.addWidget(lbl_name)

            lbl_sub = QLabel(f"🎵 {station.get('genre', 'General')}  •  📍 {station.get('country', 'Global')}")
            lbl_sub.setFont(QFont(self.font_family, 8))
            lbl_sub.setStyleSheet("color: rgba(255,255,255,0.6); background: transparent;")
            info_lay.addWidget(lbl_sub)

            top_row.addLayout(info_lay, 1)
            c_lay.addLayout(top_row)

            btn_play = QPushButton("▶ Sintonizar En Vivo")
            btn_play.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_play.setStyleSheet(f"background-color: {acento}; color: white; border: none; border-radius: 6px; padding: 8px;")
            btn_play.clicked.connect(lambda _, st=station: self._sintonizar_radio(st))
            c_lay.addWidget(btn_play)

            row = idx // 2
            col = idx % 2
            self.grid.addWidget(card, row, col)

    def _sintonizar_radio(self, station):
        name = station.get("name", "Desconocido")
        url = station.get("url", "")
        genre = station.get("genre", "General")
        country = station.get("country", "Global")
        ReproductorLogger.info(f"Radio Online: Sintonizando '{name}' | {genre} | {country} | {url}")

        if "reproducir_directo" in self.callbacks:
            self.callbacks["reproducir_directo"](url, titulo_radio=name)

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#12121C')
        bg_sec = colores.get('bg_secundario', '#1E1E2E')
        bg_terc = colores.get('bg_terciario', '#2D2D3D')
        acento = colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main};")
        self.scroll.setStyleSheet(f"QScrollArea {{ background-color: {bg_main}; border: none; }}")
        self.content.setStyleSheet(f"background-color: {bg_main};")
        self.inp_busqueda.setStyleSheet(f"background: {bg_terc}; border-radius: 8px; padding: 8px 12px; color: white; border: none;")
        self.btn_buscar.setStyleSheet(f"background: {acento}; border-radius: 8px; color: white; padding: 8px 14px; border: none;")
        self._renderizar_estaciones(getattr(self, 'estaciones_actuales', self.STATIONS_DEFAULT))
