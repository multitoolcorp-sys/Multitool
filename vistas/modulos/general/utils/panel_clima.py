import importlib.util
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QPushButton, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread
from PyQt6.QtGui import QFont

# Registro global para evitar GC de hilos activos
_active_weather_threads = []

class ClimaThread(QThread):
    """Hilo para fetching de datos de clima sin bloquear la UI"""
    clima_listo = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, ciudad, pais, api_key):
        super().__init__()
        self.ciudad = ciudad
        self.pais = pais
        self.api_key = api_key

    def _fetch_open_meteo(self):
        import requests
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={self.ciudad}&count=1&language=es&format=json"
        geo_res = requests.get(geo_url, timeout=8).json()
        if not geo_res.get("results"):
            raise ValueError(f"Ubicación no encontrada: {self.ciudad}")
        res0 = geo_res["results"][0]
        lat, lon = res0["latitude"], res0["longitude"]
        city_name = res0.get("name", self.ciudad)
        country_code = res0.get("country_code", self.pais)

        f_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        f_res = requests.get(f_url, timeout=8).json()
        current = f_res.get("current", {})
        temp = current.get("temperature_2m", 0)
        humedad = current.get("relative_humidity_2m", 0)
        viento = current.get("wind_speed_10m", 0)
        code = current.get("weather_code", 0)

        wmo = {
            0: ("Despejado", "☀️"), 1: ("Mayormente despejado", "🌤️"), 2: ("Parcialmente nublado", "⛅"),
            3: ("Nublado", "☁️"), 45: ("Niebla", "🌫️"), 48: ("Niebla con escarcha", "🌫️"),
            51: ("Llovizna ligera", "🌦️"), 53: ("Llovizna moderada", "🌦️"), 55: ("Llovizna densa", "🌧️"),
            61: ("Lluvia ligera", "🌧️"), 63: ("Lluvia moderada", "🌧️"), 65: ("Lluvia fuerte", "🌧️"),
            71: ("Nieve ligera", "❄️"), 73: ("Nieve moderada", "❄️"), 75: ("Nieve fuerte", "❄️"),
            80: ("Chubascos", "🌦️"), 81: ("Chubascos intensos", "🌧️"), 82: ("Chubascos violentos", "⛈️"),
            95: ("Tormenta", "⛈️"), 96: ("Tormenta con granizo", "⛈️"), 99: ("Tormenta severa", "⛈️")
        }
        desc, icono = wmo.get(code, ("Despejado", "🌤️"))
        return {
            "temp": f"{temp:.0f}°",
            "desc": desc,
            "icono": icono,
            "ciudad": f"{city_name}, {country_code.upper()}",
            "humedad": f"Humedad: {humedad}%",
            "viento": f"Viento: {viento}km/h"
        }

    def run(self):
        try:
            import requests
            # Intentar OpenWeatherMap primero
            if self.api_key and self.api_key != "TU_API_KEY":
                try:
                    url = f"https://api.openweathermap.org/data/2.5/weather?q={self.ciudad},{self.pais}&appid={self.api_key}&units=metric&lang=es"
                    respuesta = requests.get(url, timeout=7)
                    if respuesta.status_code == 200:
                        datos = respuesta.json()
                        temp = datos["main"]["temp"]
                        desc = datos["weather"][0]["description"]
                        humedad = datos["main"]["humidity"]
                        viento = datos["wind"]["speed"]
                        icono_id = datos["weather"][0]["icon"]
                        
                        iconos = {
                            "01d": "☀️", "01n": "🌙", "02d": "⛅", "02n": "☁️", "03d": "☁️", "03n": "☁️",
                            "04d": "☁️", "04n": "☁️", "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌧️",
                            "11d": "⛈️", "11n": "⛈️", "13d": "❄️", "13n": "❄️", "50d": "🌫️", "50n": "🌫️"
                        }
                        icono = iconos.get(icono_id, "🌤️")
                        
                        self.clima_listo.emit({
                            "temp": f"{temp:.0f}°",
                            "desc": desc.capitalize(),
                            "icono": icono,
                            "ciudad": f"{self.ciudad}, {self.pais}",
                            "humedad": f"Humedad: {humedad}%",
                            "viento": f"Viento: {viento}m/s"
                        })
                        return
                except Exception:
                    pass

            # Fallback transparente a Open-Meteo (sin API key requerida)
            datos_om = self._fetch_open_meteo()
            self.clima_listo.emit(datos_om)
        except Exception as e:
            self.error.emit(str(e))

class PanelClima(QFrame):
    """Componente visual del clima con auto-actualización"""
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
        self.lbl_titulo = QLabel("🌤️ CLIMA")
        self.lbl_titulo.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_titulo.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        header.addWidget(self.lbl_titulo)
        header.addStretch()
        
        self.btn_refresh = self._crear_btn("🔄", self.iniciar_actualizacion)
        self.btn_config = self._crear_btn("⚙️", self.cambiar_ubicacion)
        header.addWidget(self.btn_refresh)
        header.addWidget(self.btn_config)
        self.layout.addLayout(header)
        
        # --- CUERPO ---
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(15)
        self.lbl_icono = QLabel("🌤️")
        self.lbl_icono.setFont(QFont(self.font_family, 42))
        self.lbl_icono.setStyleSheet("border: none; background: transparent;")
        cuerpo.addWidget(self.lbl_icono)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        self.lbl_temp = QLabel("--°")
        self.lbl_temp.setFont(QFont(self.font_family, 32, QFont.Weight.Bold))
        self.lbl_temp.setStyleSheet("color: white; border: none; background: transparent;")
        info_layout.addWidget(self.lbl_temp)
        
        self.lbl_desc = QLabel("Cargando...")
        self.lbl_desc.setFont(QFont(self.font_family, 10))
        self.lbl_desc.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        info_layout.addWidget(self.lbl_desc)
        cuerpo.addLayout(info_layout)
        
        cuerpo.addStretch()
        self.layout.addLayout(cuerpo)
        
        # --- FOOTER ---
        footer = QHBoxLayout()
        self.lbl_detalles = QLabel(f"📍 {self.config.get('ciudad_clima', 'S/D')}")
        self.lbl_detalles.setFont(QFont(self.font_family, 9))
        self.lbl_detalles.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        footer.addWidget(self.lbl_detalles)
        
        footer.addStretch()
        
        self.lbl_extra = QLabel("")
        self.lbl_extra.setFont(QFont(self.font_family, 8))
        self.lbl_extra.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        footer.addWidget(self.lbl_extra)
        self.layout.addLayout(footer)
        
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

    def set_clima_estilo(self, icono):
        gradient = ""
        border_color = "rgba(255, 255, 255, 0.08)"
        
        if icono in ["☀️"]:
            gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(251, 146, 60, 0.12), stop:1 rgba(45, 45, 45, 0.65))"
            border_color = "rgba(251, 146, 60, 0.25)"
        elif icono in ["🌧️", "⛈️", "🌦️"]:
            gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(59, 130, 246, 0.12), stop:1 rgba(45, 45, 45, 0.65))"
            border_color = "rgba(59, 130, 246, 0.25)"
        elif icono in ["❄️"]:
            gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(103, 232, 249, 0.12), stop:1 rgba(45, 45, 45, 0.65))"
            border_color = "rgba(103, 232, 249, 0.25)"
        elif icono in ["🌙"]:
            gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(99, 102, 241, 0.12), stop:1 rgba(45, 45, 45, 0.65))"
            border_color = "rgba(99, 102, 241, 0.25)"
        else:
            gradient = "rgba(45, 45, 45, 0.45)"
            border_color = "rgba(255, 255, 255, 0.08)"
            
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {gradient};
                border: 1px solid {border_color};
                border-radius: 16px;
            }}
            QFrame:hover {{
                background-color: rgba(45, 45, 45, 0.65);
                border: 1px solid rgba(99, 102, 241, 0.4);
            }}
        """)

    def iniciar_actualizacion(self):
        if importlib.util.find_spec("requests") is None:
            self.lbl_desc.setText("Instala 'requests'")
            return
            
        if hasattr(self, "_thread") and self._thread.isRunning():
            return

        self.lbl_desc.setText("Actualizando...")
        
        self._thread = ClimaThread(
            self.config.get("ciudad_clima", "Madrid"),
            self.config.get("pais_clima", "ES"),
            self.config.get("api_key_clima", "ce067c6c189a5688e2f145a39b65641a")
        )
        _active_weather_threads.append(self._thread)
        
        def on_finished(datos):
            try:
                if not hasattr(self, "lbl_temp"):
                    return
                self.lbl_temp.setText(datos["temp"])
                self.lbl_desc.setText(datos["desc"])
                self.lbl_icono.setText(datos["icono"])
                self.lbl_detalles.setText(f"📍 {datos['ciudad']}")
                self.lbl_extra.setText(f"{datos['humedad']} | {datos['viento']}")
                self.set_clima_estilo(datos["icono"])
            except (RuntimeError, Exception):
                pass
            
        def on_error(msg):
            try:
                if hasattr(self, "lbl_desc"):
                    self.lbl_desc.setText("Error API")
            except (RuntimeError, Exception):
                pass

        self._thread.clima_listo.connect(on_finished)
        self._thread.error.connect(on_error)
        
        def cleanup():
            if self._thread in _active_weather_threads:
                _active_weather_threads.remove(self._thread)
            self._thread.deleteLater()
            
        self._thread.finished.connect(cleanup)
        self._thread.start()

    def cambiar_ubicacion(self):
        ciudad, ok1 = QInputDialog.getText(self, "Configurar Clima", "Introduce la ciudad:", text=self.config.get("ciudad_clima", ""))
        if ok1 and ciudad:
            pais, ok2 = QInputDialog.getText(self, "Configurar Clima", "Introduce Código País (ES, US, MX, etc):", text=self.config.get("pais_clima", ""))
            if ok2 and pais:
                self.config["ciudad_clima"] = ciudad
                self.config["pais_clima"] = pais
                self.save_callback()
                self.iniciar_actualizacion()

