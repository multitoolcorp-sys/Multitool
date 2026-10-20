import datetime
import calendar
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QPushButton, QGridLayout
)
from PyQt6.QtCore import Qt, QSize, QPointF, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QRadialGradient, QPainterPath

class SolarLunarArcWidget(QWidget):
    """Widget que dibuja la trayectoria del sol/luna usando QPainter"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(110)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(15000) # Actualizar cada 15 segundos
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        y_horizon = h - 25
        
        # 1. Dibujar línea de horizonte
        pen_horizon = QPen(QColor(255, 255, 255, 40), 1, Qt.PenStyle.SolidLine)
        painter.setPen(pen_horizon)
        painter.drawLine(10, y_horizon, w - 10, y_horizon)
        
        # Calcular t (0 a 1) y si es de día/noche
        now = datetime.datetime.now()
        m = now.hour * 60 + now.minute
        if 360 <= m < 1080:
            is_day = True
            t = (m - 360) / 720.0
        else:
            is_day = False
            if m >= 1080:
                t = (m - 1080) / 720.0
            else:
                t = (m + 360) / 720.0
                
        # Definir puntos de control para la curva bezier (parábola)
        p0_x, p0_y = 20, y_horizon
        p2_x, p2_y = w - 20, y_horizon
        p1_x, p1_y = w / 2, 20
        
        # 2. Dibujar la trayectoria (curva bezier)
        path = QPainterPath()
        path.moveTo(p0_x, p0_y)
        path.quadTo(p1_x, p1_y, p2_x, p2_y)
        
        if is_day:
            arc_color = QColor(251, 191, 36, 120) # Amber con transparencia
        else:
            arc_color = QColor(99, 102, 241, 100) # Indigo/blue con transparencia
            
        pen_arc = QPen(arc_color, 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen_arc)
        painter.drawPath(path)
        
        # 3. Calcular la posición actual en la curva
        cx = (1 - t)**2 * p0_x + 2 * (1 - t) * t * p1_x + t**2 * p2_x
        cy = (1 - t)**2 * p0_y + 2 * (1 - t) * t * p1_y + t**2 * p2_y
        
        # 4. Dibujar el resplandor (glow)
        glow_radius = 24 if is_day else 18
        glow_grad = QRadialGradient(cx, cy, glow_radius)
        if is_day:
            glow_grad.setColorAt(0.0, QColor(251, 191, 36, 90))
            glow_grad.setColorAt(0.5, QColor(251, 191, 36, 30))
            glow_grad.setColorAt(1.0, QColor(251, 191, 36, 0))
        else:
            glow_grad.setColorAt(0.0, QColor(147, 197, 253, 80))
            glow_grad.setColorAt(0.6, QColor(147, 197, 253, 20))
            glow_grad.setColorAt(1.0, QColor(147, 197, 253, 0))
            
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), glow_radius, glow_radius)
        
        # 5. Dibujar el cuerpo celeste
        if is_day:
            # Sol
            painter.setBrush(QColor(251, 191, 36))
            painter.setPen(QPen(QColor(255, 255, 255, 220), 1))
            painter.drawEllipse(QPointF(cx, cy), 7, 7)
        else:
            # Luna creciente
            painter.setBrush(QColor(229, 231, 235))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), 6, 6)
            
            # Círculo de sombra para hacer la luna creciente
            painter.setBrush(QColor(35, 35, 35, 230))
            painter.drawEllipse(QPointF(cx - 3, cy - 2), 5, 5)
            
        # 6. Etiquetas de texto debajo de la línea del horizonte
        painter.setPen(QColor(255, 255, 255, 120))
        font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        painter.setFont(QFont(font_family, 7))
        
        if is_day:
            painter.drawText(10, y_horizon + 15, "06:00")
            painter.drawText(w - 35, y_horizon + 15, "18:00")
        else:
            painter.drawText(10, y_horizon + 15, "18:00")
            painter.drawText(w - 35, y_horizon + 15, "06:00")
            
        # Dibujar hora actual sobre el cuerpo celeste
        painter.setPen(QColor(255, 255, 255, 180))
        painter.setFont(QFont(font_family, 7, QFont.Weight.Bold))
        time_str = now.strftime("%H:%M")
        painter.drawText(int(cx - 13), int(cy - 12), time_str)

class PanelHorario(QFrame):
    """Panel de Calendario interactivo y datos astronómicos básicos"""
    def __init__(self, parent, config, colores):
        super().__init__(parent)
        self.config = config
        self.colores = colores
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        # Estado del calendario
        hoy = datetime.datetime.now()
        self.cal_anio = hoy.year
        self.cal_mes = hoy.month
        
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
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(15)
        
        # Título
        lbl_titulo = QLabel("📅 CALENDARIO Y ENTORNO")
        lbl_titulo.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        self.main_layout.addWidget(lbl_titulo)
        
        # Grid para contenido
        self.grid_layout = QHBoxLayout()
        self.grid_layout.setSpacing(30)
        self.main_layout.addLayout(self.grid_layout)
        
        # --- BLOQUE CALENDARIO ---
        self.cal_container = QVBoxLayout()
        self.grid_layout.addLayout(self.cal_container, 2)
        
        # Navegación del mes
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(5)
        self.btn_ant = self._crear_btn("<", self.mes_anterior)
        self.btn_hoy = self._crear_btn("HOY", self.ir_a_hoy)
        self.btn_sig = self._crear_btn(">", self.mes_siguiente)
        
        self.lbl_mes_anio = QLabel("")
        self.lbl_mes_anio.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        self.lbl_mes_anio.setStyleSheet("color: white; border: none; background: transparent;")
        self.lbl_mes_anio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        nav_layout.addWidget(self.btn_ant)
        nav_layout.addWidget(self.lbl_mes_anio, 1)
        nav_layout.addWidget(self.btn_hoy)
        nav_layout.addWidget(self.btn_sig)
        self.cal_container.addLayout(nav_layout)
        
        # Grid de días
        self.cal_grid = QGridLayout()
        self.cal_grid.setSpacing(4)
        self.cal_container.addLayout(self.cal_grid)
        
        # --- BLOQUE ASTROS ---
        self.astros_container = QVBoxLayout()
        self.astros_container.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.astros_container.setSpacing(10)
        self.grid_layout.addLayout(self.astros_container, 1)
        
        # Fase Lunar
        lbl_fase_titulo = QLabel("FASE LUNAR")
        lbl_fase_titulo.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_fase_titulo.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        self.astros_container.addWidget(lbl_fase_titulo)
        
        self.lbl_fase = QLabel(self.obtener_fase_lunar())
        self.lbl_fase.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        self.lbl_fase.setStyleSheet("color: white; border: none; padding-bottom: 10px; background: transparent;")
        self.astros_container.addWidget(self.lbl_fase)
        
        # Estado del Sol
        lbl_sol_titulo = QLabel("CICLO SOLAR")
        lbl_sol_titulo.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_sol_titulo.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        self.astros_container.addWidget(lbl_sol_titulo)
        
        hora = datetime.datetime.now().hour
        is_day = 6 <= hora < 18
        sol_texto = "☀️ Día" if is_day else "🌙 Noche"
        self.lbl_sol = QLabel(sol_texto)
        self.lbl_sol.setFont(QFont(self.font_family, 11))
        self.lbl_sol.setStyleSheet("color: white; border: none; background: transparent; padding-bottom: 5px;")
        self.astros_container.addWidget(self.lbl_sol)
        
        # Widget interactivo del Arco Solar/Lunar
        self.arc_widget = SolarLunarArcWidget(self)
        self.astros_container.addWidget(self.arc_widget)
        
        self.actualizar_mini_calendario()

    def _crear_btn(self, text, callback):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05);
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {self.colores['acento']};
                color: white;
                border: 1px solid {self.colores['acento']};
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def obtener_fase_lunar(self):
        now = datetime.datetime.now()
        known_new_moon = datetime.datetime(2000, 1, 6, 18, 14)
        lunar_cycle = 29.53058867
        diff = now - known_new_moon
        days = diff.total_seconds() / 86400
        phase = (days % lunar_cycle) / lunar_cycle
        
        if phase < 0.03 or phase > 0.97: return "🌑 Luna Nueva"
        elif phase < 0.22: return "🌒 Creciente"
        elif phase < 0.28: return "🌓 Cuarto Creciente"
        elif phase < 0.47: return "🌔 Gibada Creciente"
        elif phase < 0.53: return "🌕 Luna Llena"
        elif phase < 0.72: return "🌖 Gibada Menguante"
        elif phase < 0.78: return "🌗 Cuarto Menguante"
        else: return "🌘 Menguante"

    def actualizar_mini_calendario(self):
        # Limpiar grid
        for i in reversed(range(self.cal_grid.count())):
            widget = self.cal_grid.itemAt(i).widget()
            if widget: widget.setParent(None)
            
        mes_nombre = calendar.month_name[self.cal_mes].upper()
        self.lbl_mes_anio.setText(f"{mes_nombre} {self.cal_anio}")
        
        # Encabezados
        dias = ["LU", "MA", "MI", "JU", "VI", "SA", "DO"]
        for i, d in enumerate(dias):
            lbl = QLabel(d)
            lbl.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cal_grid.addWidget(lbl, 0, i)
            
        primer_dia = datetime.date(self.cal_anio, self.cal_mes, 1)
        # calendar usa Monday=0, Sunday=6
        dias_en_mes = calendar.monthrange(self.cal_anio, self.cal_mes)[1]
        dia_semana_inicio = primer_dia.weekday()
        
        hoy = datetime.datetime.now()
        dia = 1
        
        # Llenar grid
        for fila in range(1, 7):
            for col in range(7):
                if (fila == 1 and col < dia_semana_inicio) or dia > dias_en_mes:
                    continue
                
                es_hoy = (dia == hoy.day and self.cal_mes == hoy.month and self.cal_anio == hoy.year)
                
                lbl = QLabel(str(dia))
                lbl.setFixedSize(30, 30)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setFont(QFont(self.font_family, 10))
                
                if es_hoy:
                    lbl.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; border-radius: 15px; font-weight: bold; border: none;")
                else:
                    lbl.setStyleSheet(f"color: white; border: none; background: transparent;")
                
                self.cal_grid.addWidget(lbl, fila, col)
                dia += 1

    def mes_anterior(self):
        self.cal_mes -= 1
        if self.cal_mes < 1:
            self.cal_mes = 12
            self.cal_anio -= 1
        self.actualizar_mini_calendario()

    def mes_siguiente(self):
        self.cal_mes += 1
        if self.cal_mes > 12:
            self.cal_mes = 1
            self.cal_anio += 1
        self.actualizar_mini_calendario()

    def ir_a_hoy(self):
        hoy = datetime.datetime.now()
        self.cal_anio = hoy.year
        self.cal_mes = hoy.month
        self.actualizar_mini_calendario()

    def crear(self): return self


