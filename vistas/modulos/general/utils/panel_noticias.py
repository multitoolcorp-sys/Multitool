import importlib.util
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QPushButton, QInputDialog, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont

# Registro global para evitar GC de hilos activos
_active_news_threads = []

class NoticiasThread(QThread):
    """Hilo para fetching de noticias sin bloquear la UI principal"""
    noticias_listas = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key

    def _fetch_rss(self):
        import requests
        import xml.etree.ElementTree as ET

        rss_urls = [
            ("Google Noticias", "https://news.google.com/rss?hl=es-419&gl=US&ceid=US:es-419"),
            ("BBC Mundo", "https://feeds.bbci.co.uk/mundo/rss.xml"),
            ("El País", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada")
        ]

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        for feed_name, url in rss_urls:
            try:
                resp = requests.get(url, headers=headers, timeout=7)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    items = root.findall(".//item")
                    if items:
                        html = ""
                        for item in items[:10]:
                            title = item.findtext("title", "Titular no disponible")
                            source_elem = item.find("source")
                            source = source_elem.text if source_elem is not None and source_elem.text else feed_name
                            pub_date = item.findtext("pubDate", "")
                            date_str = pub_date[:16] if pub_date else ""
                            html += f"<div style='margin-bottom: 12px;'>"
                            html += f"<b style='color: white; font-size: 11px;'>🔹 {title}</b><br>"
                            html += f"<span style='color: #888; font-size: 10px;'><i>{source}</i> {f'• {date_str}' if date_str else ''}</span>"
                            html += f"</div>"
                        return html
            except Exception:
                continue
        return None

    def run(self):
        try:
            import requests
            # Si hay API key configurada, intentar NewsAPI primero
            if self.api_key and self.api_key != "TU_API_KEY":
                paises = ["us", "mx", "ar", "es", "co"]
                for pais in paises:
                    url = f"https://newsapi.org/v2/top-headlines?country={pais}&apiKey={self.api_key}"
                    try:
                        respuesta = requests.get(url, timeout=7)
                        datos = respuesta.json()
                        if respuesta.status_code == 200 and datos.get("status") == "ok":
                            noticias = datos.get("articles", [])
                            if noticias:
                                html = ""
                                for n in noticias[:10]:
                                    title = n.get('title','Sin título')
                                    source = n.get('source',{}).get('name','')
                                    html += f"<div style='margin-bottom: 12px;'>"
                                    html += f"<b style='color: white; font-size: 11px;'>🔹 {title}</b><br>"
                                    html += f"<span style='color: #888; font-size: 10px;'><i>{source}</i></span>"
                                    html += f"</div>"
                                self.noticias_listas.emit(html)
                                return
                    except Exception:
                        continue

            # Fallback a RSS feeds si no hay API key o falló NewsAPI
            rss_html = self._fetch_rss()
            if rss_html:
                self.noticias_listas.emit(rss_html)
                return

            self.error.emit("No se encontraron noticias disponibles.")
        except Exception as e:
            self.error.emit(str(e))

class PanelNoticias(QFrame):
    """Componente visual de noticias con scroll y auto-fetch"""
    def __init__(self, parent, config, colores, save_callback):
        super().__init__(parent)
        self.config = config
        self.colores = colores
        self.save_callback = save_callback
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(45, 45, 45, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }}
            QFrame:hover {{
                background-color: rgba(45, 45, 45, 0.65);
                border: 1px solid rgba(99, 102, 241, 0.4);
            }}
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(10)
        
        # --- HEADER ---
        header = QHBoxLayout()
        self.lbl_titulo = QLabel("📰 NOTICIAS")
        self.lbl_titulo.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_titulo.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        header.addWidget(self.lbl_titulo)
        header.addStretch()
        
        self.btn_refresh = self._crear_btn("🔄", self.iniciar_actualizacion)
        self.btn_config = self._crear_btn("⚙️", self.cambiar_api)
        header.addWidget(self.btn_refresh)
        header.addWidget(self.btn_config)
        self.layout.addLayout(header)
        
        # --- CONTENIDO ---
        self.txt_noticias = QTextEdit()
        self.txt_noticias.setReadOnly(True)
        self.txt_noticias.setFrameShape(QFrame.Shape.NoFrame)
        self.txt_noticias.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colores['bg_terciario']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.02);
                border-radius: 8px;
                padding: 12px;
                font-family: '{self.font_family}';
            }}
            QScrollBar:vertical {{ width: 8px; background: transparent; }}
            QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.1); border-radius: 4px; }}
        """)
        self.layout.addWidget(self.txt_noticias)
        
        self.iniciar_actualizacion()

    def _crear_btn(self, text, callback):
        btn = QPushButton(text)
        btn.setFixedSize(26, 26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255,255,255,0.03); 
                border: none; 
                border-radius: 13px; 
                color: #888; 
                font-size: 11px;
            }}
            QPushButton:hover {{ 
                background: {self.colores['bg_terciario']}; 
                color: white; 
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def iniciar_actualizacion(self):
        if importlib.util.find_spec("requests") is None:
            self.txt_noticias.setHtml("<p style='color: #F87171;'>Instala 'requests' con pip</p>")
            return
            
        if hasattr(self, "_thread") and self._thread.isRunning():
            return

        self.txt_noticias.setHtml("<p style='color: #888; font-style: italic;'>Actualizando titulares...</p>")
        
        self._thread = NoticiasThread(self.config.get("api_key_noticias", "ee2d3485d38a4764918a6ff14e6ff82a"))
        _active_news_threads.append(self._thread)
        
        def set_noticias_safe(html_content):
            try:
                if hasattr(self, "txt_noticias") and self.txt_noticias:
                    self.txt_noticias.setHtml(html_content)
            except RuntimeError:
                pass

        def set_error_safe(msg):
            try:
                if hasattr(self, "txt_noticias") and self.txt_noticias:
                    self.txt_noticias.setHtml(f"<p style='color: #F87171;'>Error: {msg}</p>")
            except RuntimeError:
                pass

        self._thread.noticias_listas.connect(set_noticias_safe)
        self._thread.error.connect(set_error_safe)
        
        def cleanup():
            if hasattr(self, "_thread") and self._thread in _active_news_threads:
                _active_news_threads.remove(self._thread)
            if hasattr(self, "_thread") and self._thread:
                self._thread.deleteLater()
            
        self._thread.finished.connect(cleanup)
        self._thread.start()

    def cambiar_api(self):
        key, ok = QInputDialog.getText(self, "Configurar Noticias", "API Key (NewsAPI.org):", text=self.config.get("api_key_noticias", ""))
        if ok and key:
            self.config["api_key_noticias"] = key
            self.save_callback()
            self.iniciar_actualizacion()

