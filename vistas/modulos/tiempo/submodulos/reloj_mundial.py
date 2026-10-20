import datetime
import platform
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGridLayout, QScrollArea, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Diccionario de offsets UTC estáticos de respaldo para cuando tzdata no está en Windows
TIMEZONE_OFFSETS = {
    "America/New_York": -4,
    "Europe/London": 1,
    "Europe/Madrid": 2,
    "Europe/Paris": 2,
    "Asia/Tokyo": 9,
    "Australia/Sydney": 10,
    "America/Mexico_City": -6,
    "America/Buenos_Aires": -3,
    "America/Lima": -5,
    "America/Santiago": -4,
    "America/Bogota": -5,
    "Asia/Dubai": 4,
    "Asia/Hong_Kong": 8
}

def resolver_timezone(tz_str):
    """Resuelve un timezone devolviendo un objeto tzinfo compatible sin depender de tzdata"""
    if not tz_str:
        return datetime.timezone.utc

    # 1. Intentar ZoneInfo nativo
    try:
        return ZoneInfo(tz_str)
    except Exception:
        pass

    # 2. Buscar en diccionario precalculado
    if tz_str in TIMEZONE_OFFSETS:
        offset_hrs = TIMEZONE_OFFSETS[tz_str]
        return datetime.timezone(datetime.timedelta(hours=offset_hrs))

    # 3. Intentar parsear cadenas como UTC+9, UTC-4, GMT+2, -5, +8
    match = re.search(r'(?:UTC|GMT)?\s*([+-]?\d{1,2})', tz_str, re.IGNORECASE)
    if match:
        try:
            offset_hrs = int(match.group(1))
            return datetime.timezone(datetime.timedelta(hours=offset_hrs))
        except Exception:
            pass

    return datetime.timezone.utc


class CityClockCard(QFrame):
    """Tarjeta individual de reloj de ciudad internacional"""
    def __init__(self, ciudad_dict, colores, parent=None):
        super().__init__(parent)
        self.ciudad = ciudad_dict
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }}
            QFrame:hover {{
                border: 1px solid {colores['acento']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(6)

        # Header con bandera y nombre
        hdr = QHBoxLayout()
        lbl_name = QLabel(f"{ciudad_dict.get('bandera', '🌐')} {ciudad_dict.get('nombre', 'Ciudad')}")
        lbl_name.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_name.setStyleSheet("color: white;")
        hdr.addWidget(lbl_name)
        hdr.addStretch()

        self.lbl_daynight = QLabel("☀️")
        self.lbl_daynight.setFont(QFont(self.font_family, 12))
        hdr.addWidget(self.lbl_daynight)

        layout.addLayout(hdr)

        # Horario Digital
        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setFont(QFont(self.mono_font, 20, QFont.Weight.Bold))
        self.lbl_time.setStyleSheet(f"color: {colores['acento']};")
        layout.addWidget(self.lbl_time)

        # Fecha y Diferencia de Horas
        self.lbl_diff = QLabel("Diferencia: --")
        self.lbl_diff.setFont(QFont(self.font_family, 8))
        self.lbl_diff.setStyleSheet("color: rgba(255,255,255,0.7);")
        layout.addWidget(self.lbl_diff)

        self.actualizar_hora()

    def actualizar_hora(self):
        tz_str = self.ciudad.get("timezone", "UTC")
        try:
            tz = resolver_timezone(tz_str)
            now_tz = datetime.datetime.now(tz)
            now_local = datetime.datetime.now()
            
            # Formato de Hora
            self.lbl_time.setText(now_tz.strftime("%H:%M:%S"))

            # Indicador Día / Noche
            hora = now_tz.hour
            if 6 <= hora < 19:
                self.lbl_daynight.setText("☀️")
            else:
                self.lbl_daynight.setText("🌙")

            # Cálculo de diferencia de horas respecto al sistema local
            offset_local = now_local.astimezone().utcoffset() or datetime.timedelta(0)
            offset_tz = now_tz.utcoffset() or datetime.timedelta(0)
            diff_hours = int((offset_tz - offset_local).total_seconds() / 3600)

            if diff_hours == 0:
                diff_str = "Misma hora que tú"
            elif diff_hours > 0:
                diff_str = f"+{diff_hours} hrs respecto a ti"
            else:
                diff_str = f"{diff_hours} hrs respecto a ti"

            dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
            d_str = f"{dias_semana[now_tz.weekday()]}, {now_tz.day} {meses[now_tz.month-1]}"

            self.lbl_diff.setText(f"{d_str} • {diff_str}")
        except Exception as e:
            print(f"Error actualizando reloj de ciudad {self.ciudad}: {e}")
            self.lbl_time.setText("--:--:--")
            self.lbl_diff.setText("Zona Horaria No Válida")


class RelojMundialSubmodule(QWidget):
    """Submódulo 3: Reloj Mundial & Comparador de Zonas Horarias Internacionales"""
    def __init__(self, parent, context, manager, colores):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        self.cards = []
        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("🌐 RELOJ MUNDIAL & ZONAS HORARIAS")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        btn_add_city = QPushButton("➕ Añadir Ciudad")
        btn_add_city.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_city.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_add_city.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 6px 14px; border-radius: 6px; border: none;")
        btn_add_city.clicked.connect(self._abrir_dialogo_ciudad)
        hdr.addWidget(btn_add_city)

        layout.addLayout(hdr)

        # Marco Reloj Local Principal
        local_frame = QFrame()
        local_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }}
        """)
        loc_lay = QVBoxLayout(local_frame)
        loc_lay.setContentsMargins(20, 15, 20, 15)
        loc_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_local_title = QLabel("📍 HORA LOCAL DEL SISTEMA")
        self.lbl_local_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_local_title.setStyleSheet("color: rgba(255,255,255,0.6);")
        self.lbl_local_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loc_lay.addWidget(self.lbl_local_title)

        self.lbl_local_time = QLabel("00:00:00")
        self.lbl_local_time.setFont(QFont(self.mono_font, 38, QFont.Weight.Bold))
        self.lbl_local_time.setStyleSheet(f"color: {self.colores['acento']};")
        self.lbl_local_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loc_lay.addWidget(self.lbl_local_time)

        self.lbl_local_date = QLabel("Cargando fecha...")
        self.lbl_local_date.setFont(QFont(self.font_family, 10))
        self.lbl_local_date.setStyleSheet("color: white;")
        self.lbl_local_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loc_lay.addWidget(self.lbl_local_date)

        layout.addWidget(local_frame)

        # Cuadrícula Scroll de Ciudades Internacionales
        scroll_cities = QScrollArea()
        scroll_cities.setWidgetResizable(True)
        scroll_cities.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container_cities = QWidget()
        self.container_cities.setStyleSheet("background: transparent;")
        self.grid_cities = QGridLayout(self.container_cities)
        self.grid_cities.setContentsMargins(0, 0, 0, 0)
        self.grid_cities.setSpacing(12)

        scroll_cities.setWidget(self.container_cities)
        layout.addWidget(scroll_cities, 1)

        self.refrescar_ciudades()

    def actualizar_relojes(self):
        # Actualizar Reloj Local
        now = datetime.datetime.now()
        self.lbl_local_time.setText(now.strftime("%H:%M:%S"))
        
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        d_name = dias_semana[now.weekday()]
        m_name = meses[now.month - 1]
        self.lbl_local_date.setText(f"{d_name}, {now.day} de {m_name} de {now.year}")

        # Actualizar tarjetas internacionales
        for card in self.cards:
            card.actualizar_hora()

    def refrescar_ciudades(self):
        while self.grid_cities.count() > 0:
            item = self.grid_cities.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.cards.clear()

        ciudades = self.manager.ciudades
        for idx, c_dict in enumerate(ciudades):
            row = idx // 3
            col = idx % 3
            card = CityClockCard(c_dict, self.colores)
            self.grid_cities.addWidget(card, row, col)
            self.cards.append(card)

    def _abrir_dialogo_ciudad(self):
        nombre, ok = QInputDialog.getText(self, "Añadir Ciudad", "Nombre de la Ciudad (ej. Tokio, Paris, UTC+3):")
        if ok and nombre.strip():
            tz_str, ok2 = QInputDialog.getText(self, "Zona Horaria", "Identificador o diferencia (ej. Asia/Tokyo, UTC+9, -5):")
            if ok2 and tz_str.strip():
                self.manager.añadir_ciudad(nombre.strip(), tz_str.strip())
                self.refrescar_ciudades()

    def actualizar_tema(self, colores):
        self.colores = colores
        self.lbl_local_time.setStyleSheet(f"color: {self.colores['acento']};")
        self.refrescar_ciudades()
