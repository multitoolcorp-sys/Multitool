import platform
import json
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QFrame, QScrollArea, QGridLayout, QMessageBox, QComboBox
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

class TelevisionOnlineSubmodule(QWidget):
    """
    Submódulo 5: Televisión Online en Vivo con Canales Abiertos y Legales (IPTV HLS/M3U8).
    Permite sintonizar canales de Noticias, Deportes, Música, Ciencia, Documentales y Cine,
    además de cargar cualquier enlace M3U8 personalizado.
    """
    CHANNELS_DEFAULT = [
        {
            "name": "DW Español",
            "category": "Noticias",
            "country": "Alemania / Latam",
            "icon": "📰",
            "quality": "HD 1080p",
            "url": "https://dwamdstream104.akamaized.net/hls/live/2015530/dwstream104/index.m3u8"
        },
        {
            "name": "RTVE Canal 24 Horas",
            "category": "Noticias",
            "country": "España",
            "icon": "🇪🇸",
            "quality": "HD 1080p",
            "url": "https://rtvelivestream.akamaized.net/rtvesec/24h/24h_main.m3u8"
        },
        {
            "name": "Euronews Español",
            "category": "Noticias",
            "country": "Europa / Global",
            "icon": "🌍",
            "quality": "HD 720p",
            "url": "https://euronews-euronews-spanish-1-es.samsung.wurl.tv/playlist.m3u8"
        },
        {
            "name": "France 24 Español",
            "category": "Noticias",
            "country": "Francia / Latam",
            "icon": "🇫🇷",
            "quality": "HD 1080p",
            "url": "https://stream.france24.com/hls/es/live.m3u8"
        },
        {
            "name": "TeleSUR Noticias",
            "category": "Noticias",
            "country": "Latinoamérica",
            "icon": "📡",
            "quality": "HD 1080p",
            "url": "https://cdnh5.iblups.com/hls/TVEPG_1080p.m3u8"
        },
        {
            "name": "Bloomberg TV+",
            "category": "Noticias",
            "country": "EE. UU. / Global",
            "icon": "📈",
            "quality": "HD 1080p",
            "url": "https://bloomberg.com/media-manifest/streams/us.m3u8"
        },
        {
            "name": "NASA TV Public HD",
            "category": "Ciencia",
            "country": "EE. UU. / Espacio",
            "icon": "🚀",
            "quality": "HD 1080p",
            "url": "https://ntv1.akamaized.net/hls/live/2014075/NASA-NTV1-HLS/master.m3u8"
        },
        {
            "name": "NASA TV Media HD",
            "category": "Ciencia",
            "country": "EE. UU. / Espacio",
            "icon": "🛸",
            "quality": "HD 1080p",
            "url": "https://ntv2.akamaized.net/hls/live/2014076/NASA-NTV2-HLS/master.m3u8"
        },
        {
            "name": "Red Bull TV",
            "category": "Deportes",
            "country": "Internacional",
            "icon": "⚡",
            "quality": "HD 1080p",
            "url": "https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8"
        },
        {
            "name": "Real Madrid TV Español",
            "category": "Deportes",
            "country": "España",
            "icon": "⚽",
            "quality": "HD 1080p",
            "url": "https://rmtv.akamaized.net/hls/live/2043153/rmtv-es/master.m3u8"
        },
        {
            "name": "Runtime Cine y Series",
            "category": "Cine",
            "country": "España / Latam",
            "icon": "🎬",
            "quality": "HD 720p",
            "url": "https://runtime-runtime-es-rakuten.amagi.tv/playlist.m3u8"
        },
        {
            "name": "Anime & Pop TV",
            "category": "Entretenimiento",
            "country": "Internacional",
            "icon": "🍿",
            "quality": "HD 720p",
            "url": "https://playplus-animes-br.rakuten.wurl.tv/playlist.m3u8"
        }
    ]

    CATEGORIES = ["Todos", "Noticias", "Deportes", "Ciencia", "Cine", "Entretenimiento"]

    def __init__(self, parent, context, manager, colores, callbacks=None):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks or {}
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.selected_category = "Todos"
        self.canales_actuales = list(self.CHANNELS_DEFAULT)

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("📺 TELEVISIÓN ONLINE EN VIVO (CANALES ABIERTOS & LEGALES)")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; background: transparent;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()
        layout.addLayout(hdr)

        # Barra de Búsqueda y Filtros
        bar_f = QFrame()
        bar_f.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }}
        """)
        b_lay = QHBoxLayout(bar_f)
        b_lay.setContentsMargins(12, 10, 12, 10)
        b_lay.setSpacing(10)

        self.inp_tv_search = QLineEdit()
        self.inp_tv_search.setPlaceholderText("Buscar canal por nombre o país (ej: DW, RTVE, NASA, Deportes, España, Francia)...")
        self.inp_tv_search.setFont(QFont(self.font_family, 10))
        self.inp_tv_search.setStyleSheet(f"background: {bg_terc}; border-radius: 8px; padding: 8px 12px; color: white; border: none;")
        self.inp_tv_search.textChanged.connect(self._filtrar_canales)
        b_lay.addWidget(self.inp_tv_search, 1)

        # Barra para URL M3U8 manual
        self.inp_custom_m3u8 = QLineEdit()
        self.inp_custom_m3u8.setPlaceholderText("📡 O pega aquí un enlace de transmisión (.m3u8)...")
        self.inp_custom_m3u8.setFont(QFont(self.font_family, 9))
        self.inp_custom_m3u8.setStyleSheet(f"background: {bg_terc}; border-radius: 8px; padding: 8px 12px; color: #AAB0B8; border: none;")
        b_lay.addWidget(self.inp_custom_m3u8, 1)

        btn_abrir_m3u8 = QPushButton("▶ Sintonizar M3U8")
        btn_abrir_m3u8.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_abrir_m3u8.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_abrir_m3u8.setStyleSheet(f"background: {acento}; border-radius: 8px; color: white; padding: 8px 14px; border: none;")
        btn_abrir_m3u8.clicked.connect(self._sintonizar_m3u8_manual)
        b_lay.addWidget(btn_abrir_m3u8)

        layout.addWidget(bar_f)

        # Fila de Categorías (Botones estilo píldora)
        cat_layout = QHBoxLayout()
        cat_layout.setSpacing(8)
        self.cat_buttons = {}

        for cat in self.CATEGORIES:
            btn_cat = QPushButton(cat)
            btn_cat.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cat.setFont(QFont(self.font_family, 9, QFont.Weight.Bold if cat == "Todos" else QFont.Weight.Medium))
            self._estilar_boton_categoria(btn_cat, cat == "Todos")
            btn_cat.clicked.connect(lambda checked, c=cat: self._seleccionar_categoria(c))
            cat_layout.addWidget(btn_cat)
            self.cat_buttons[cat] = btn_cat

        cat_layout.addStretch()
        layout.addLayout(cat_layout)

        # Estado
        self.lbl_status = QLabel("⭐ Selecciona un canal para sintonizar en vivo con audio y vídeo completo:")
        self.lbl_status.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: rgba(255,255,255,0.7); background: transparent;")
        layout.addWidget(self.lbl_status)

        # Scroll Area para Tarjetas de Canales
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(f"QScrollArea {{ background-color: {bg_main}; border: none; }}")

        self.content = QWidget()
        self.content.setStyleSheet(f"background-color: {bg_main}; color: white;")
        self.grid = QGridLayout(self.content)
        self.grid.setSpacing(14)
        self.scroll.setWidget(self.content)

        layout.addWidget(self.scroll, 1)

        self._renderizar_canales(self.canales_actuales)

    def _estilar_boton_categoria(self, btn, activo):
        acento = self.colores.get('acento', '#6366F1')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        if activo:
            btn.setStyleSheet(f"background-color: {acento}; color: white; border: none; border-radius: 14px; padding: 6px 16px; font-weight: bold;")
        else:
            btn.setStyleSheet(f"background-color: {bg_terc}; color: rgba(255,255,255,0.7); border: none; border-radius: 14px; padding: 6px 16px;")

    def _seleccionar_categoria(self, cat):
        self.selected_category = cat
        for c_name, btn in self.cat_buttons.items():
            self._estilar_boton_categoria(btn, c_name == cat)
        self._filtrar_canales()

    def _filtrar_canales(self):
        query = self.inp_tv_search.text().strip().lower()
        filtrados = []
        for ch in self.CHANNELS_DEFAULT:
            coincide_cat = (self.selected_category == "Todos") or (ch.get("category", "") == self.selected_category)
            coincide_txt = (not query) or (query in ch.get("name", "").lower()) or (query in ch.get("country", "").lower())
            if coincide_cat and coincide_txt:
                filtrados.append(ch)
        self.canales_actuales = filtrados
        self._renderizar_canales(filtrados)

    def _renderizar_canales(self, canales):
        # Limpiar grid anterior
        while self.grid.count() > 0:
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not canales:
            lbl_vacio = QLabel("No se encontraron canales que coincidan con la búsqueda.")
            lbl_vacio.setStyleSheet("color: rgba(255,255,255,0.5); font-style: italic; padding: 20px;")
            self.grid.addWidget(lbl_vacio, 0, 0)
            return

        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')

        cols = 3
        for idx, ch in enumerate(canales):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_sec};
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 10px;
                }}
                QFrame:hover {{
                    border: 1px solid {acento};
                    background-color: {bg_terc};
                }}
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(14, 14, 14, 14)
            c_lay.setSpacing(10)

            # Fila Superior: Icono, Nombre y Calidad
            top_row = QHBoxLayout()
            lbl_icon = QLabel(ch.get("icon", "📺"))
            lbl_icon.setFont(QFont(self.font_family, 18))
            top_row.addWidget(lbl_icon)

            lbl_name = QLabel(ch.get("name", "Canal TV"))
            lbl_name.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
            lbl_name.setStyleSheet("color: white;")
            lbl_name.setWordWrap(True)
            top_row.addWidget(lbl_name, 1)

            lbl_qual = QLabel(ch.get("quality", "HD"))
            lbl_qual.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
            lbl_qual.setStyleSheet(f"background: rgba(52, 211, 153, 0.15); color: {exito}; border-radius: 4px; padding: 3px 7px; border: 1px solid rgba(52, 211, 153, 0.3);")
            top_row.addWidget(lbl_qual)

            c_lay.addLayout(top_row)

            # Fila Info: Categoría y País
            info_txt = f"📂 {ch.get('category', 'General')}   •   📍 {ch.get('country', 'Internacional')}"
            lbl_info = QLabel(info_txt)
            lbl_info.setFont(QFont(self.font_family, 8))
            lbl_info.setStyleSheet("color: rgba(255,255,255,0.6);")
            c_lay.addWidget(lbl_info)

            # Botón Sintonizar
            btn_play = QPushButton("▶ Sintonizar Canal")
            btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_play.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            btn_play.setStyleSheet(f"""
                QPushButton {{
                    background-color: {acento};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 14px;
                }}
                QPushButton:hover {{
                    background-color: #818CF8;
                }}
            """)
            btn_play.clicked.connect(lambda checked, c=ch: self._sintonizar_canal(c))
            c_lay.addWidget(btn_play)

            row = idx // cols
            col = idx % cols
            self.grid.addWidget(card, row, col)

    def _sintonizar_canal(self, ch):
        name = ch.get("name", "Canal de Televisión")
        url = ch.get("url", "")
        if not url:
            return
        ReproductorLogger.info(f"Televisión Online: Sintonizando '{name}' | URL: {url}")
        if "reproducir_directo" in self.callbacks:
            self.callbacks["reproducir_directo"](url, titulo_radio=name, es_video=True)

    def _sintonizar_m3u8_manual(self):
        url = self.inp_custom_m3u8.text().strip()
        if not url:
            QMessageBox.warning(self, "Enlace M3U8 Vacío", "Por favor ingresa una URL válida con protocolo http:// o https://")
            return
        ReproductorLogger.info(f"Televisión Online: Sintonizando M3U8 manual: {url}")
        if "reproducir_directo" in self.callbacks:
            self.callbacks["reproducir_directo"](url, titulo_radio="Emisión IPTV en Vivo", es_video=True)

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#12121C')
        bg_terc = colores.get('bg_terciario', '#2D2D3D')

        self.setStyleSheet(f"background-color: {bg_main};")
        self.scroll.setStyleSheet(f"QScrollArea {{ background-color: {bg_main}; border: none; }}")
        self.content.setStyleSheet(f"background-color: {bg_main};")
        self.inp_tv_search.setStyleSheet(f"background: {bg_terc}; border-radius: 8px; padding: 8px 12px; color: white; border: none;")
        self.inp_custom_m3u8.setStyleSheet(f"background: {bg_terc}; border-radius: 8px; padding: 8px 12px; color: #AAB0B8; border: none;")
        for cat, btn in self.cat_buttons.items():
            self._estilar_boton_categoria(btn, cat == self.selected_category)
        self._renderizar_canales(self.canales_actuales)
