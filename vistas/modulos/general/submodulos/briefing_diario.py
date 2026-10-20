import json
import datetime
import random
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

CITAS_INSPIRADORAS = [
    ("El éxito no es definitivo, el fracaso no es fatal: lo que cuenta es el valor para continuar.", "Winston Churchill"),
    ("La mejor manera de predecir el futuro es creándolo.", "Peter Drucker"),
    ("La disciplina es el puente entre las metas y los logros.", "Jim Rohn"),
    ("Pequeños avances diarios conducen a resultados extraordinarios a lo largo del tiempo.", "Robin Sharma"),
    ("Haz de cada día tu obra maestra.", "John Wooden"),
    ("La simplicidad es la máxima sofisticación.", "Leonardo da Vinci"),
    ("Lo que haces hoy puede mejorar todos tus mañanas.", "Ralph Marston"),
    ("La concentración y la simplicidad son las claves del verdadero éxito.", "Steve Jobs")
]

class BriefingDiarioGUI(QWidget):
    """Submódulo Briefing Diario: Resumen ejecutivo matutino/diario personalizado"""
    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent)
        if isinstance(context, dict):
            self.colores = context
            self.context = colores
        elif isinstance(colores, dict):
            self.colores = colores
            self.context = context
        else:
            self.context = context
            self.colores = getattr(context, "colores", {}) if context else {}

        if not self.colores and self.context and hasattr(self.context, "app") and hasattr(self.context.app, "COLORES"):
            self.colores = self.context.app.COLORES

        if not isinstance(self.colores, dict):
            self.colores = {}

        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.init_ui()

    def _obtener_saludo(self):
        hora = datetime.datetime.now().hour
        if 5 <= hora < 12:
            return "🌅 ¡Buenos días"
        elif 12 <= hora < 19:
            return "☀️ ¡Buenas tardes"
        else:
            return "🌙 ¡Buenas noches"

    def _obtener_fecha_formateada(self):
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        ahora = datetime.datetime.now()
        dia_sem = dias[ahora.weekday()]
        mes = meses[ahora.month - 1]
        return f"{dia_sem}, {ahora.day} de {mes} de {ahora.year}"

    def _obtener_cita_del_dia(self):
        # Selección consistente por día del año
        dia_año = datetime.datetime.now().timetuple().tm_yday
        idx = dia_año % len(CITAS_INSPIRADORAS)
        return CITAS_INSPIRADORAS[idx]

    def _contar_tareas_pendientes(self):
        if not self.context or not hasattr(self.context, "ruta_usuario") or not self.context.ruta_usuario:
            return 0, 0
        try:
            ruta_todo = Path(self.context.ruta_usuario) / "tareas_dashboard.json"
            if ruta_todo.exists():
                with open(ruta_todo, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    total = len(data)
                    pendientes = sum(1 for t in data if not t.get("completed", False))
                    return pendientes, total
        except Exception:
            pass
        return 0, 0

    def _contar_habitos_activos(self):
        if not self.context or not hasattr(self.context, "ruta_usuario") or not self.context.ruta_usuario:
            return 0
        try:
            ruta_hab = Path(self.context.ruta_usuario) / "habitos.json"
            if ruta_hab.exists():
                with open(ruta_hab, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return len(data) if isinstance(data, list) else 0
        except Exception:
            pass
        return 0

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {self.colores.get('bg_principal', '#121218')}; }}")

        container = QWidget()
        container.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')};")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(40, 35, 40, 35)
        lay.setSpacing(25)

        # Saludo Principal
        usuario = getattr(self.context, "usuario", "Usuario")
        saludo = f"{self._obtener_saludo()}, {usuario}!"
        
        lbl_saludo = QLabel(saludo)
        lbl_saludo.setFont(QFont(self.font_family, 24, QFont.Weight.Bold))
        lbl_saludo.setStyleSheet("color: white; border: none; background: transparent;")
        lay.addWidget(lbl_saludo)

        lbl_fecha = QLabel(f"📅 {self._obtener_fecha_formateada()}")
        lbl_fecha.setFont(QFont(self.font_family, 11))
        lbl_fecha.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; border: none; background: transparent; font-weight: bold;")
        lay.addWidget(lbl_fecha)

        # Banner Cita del Día
        cita, autor = self._obtener_cita_del_dia()
        banner_cita = QFrame()
        banner_cita.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border-left: 4px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 12px;
                padding: 18px 24px;
            }}
        """)
        bc_lay = QVBoxLayout(banner_cita)
        bc_lay.setSpacing(6)
        
        lbl_c_tit = QLabel("💡 CITA DEL DÍA")
        lbl_c_tit.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_c_tit.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; border: none; background: transparent;")
        bc_lay.addWidget(lbl_c_tit)

        lbl_c_texto = QLabel(f'"{cita}"')
        lbl_c_texto.setFont(QFont(self.font_family, 12, QFont.Weight.DemiBold))
        lbl_c_texto.setWordWrap(True)
        lbl_c_texto.setStyleSheet("color: white; border: none; background: transparent;")
        bc_lay.addWidget(lbl_c_texto)

        lbl_c_autor = QLabel(f"— {autor}")
        lbl_c_autor.setFont(QFont(self.font_family, 9))
        lbl_c_autor.setStyleSheet("color: #9CA3AF; border: none; background: transparent;")
        bc_lay.addWidget(lbl_c_autor)

        lay.addWidget(banner_cita)

        # Grid de Tarjetas de Estado Diario (3 Columnas)
        grid = QGridLayout()
        grid.setSpacing(20)

        pend, tot = self._contar_tareas_pendientes()
        hab_count = self._contar_habitos_activos()

        # 1. Tarjeta Tareas
        c_tar = self._crear_tarjeta_kpi(
            "📋 TAREAS DE HOY",
            f"{pend} pendientes",
            f"De {tot} tareas registradas",
            "#F59E0B"
        )
        grid.addWidget(c_tar, 0, 0)

        # 2. Tarjeta Hábitos
        c_hab = self._crear_tarjeta_kpi(
            "🔥 HÁBITOS ACTIVOS",
            f"{hab_count} en curso",
            "Mantén la consistencia hoy",
            "#10B981"
        )
        grid.addWidget(c_hab, 0, 1)

        # 3. Tarjeta Sistema
        try:
            import psutil
            ram_free = 100 - psutil.virtual_memory().percent
            sys_desc = f"{ram_free:.0f}% disponible"
        except Exception:
            sys_desc = "Óptimo"

        c_sys = self._crear_tarjeta_kpi(
            "⚡ ESTADO DEL SISTEMA",
            sys_desc,
            "Rendimiento optimizado",
            self.colores.get("acento", "#6366F1")
        )
        grid.addWidget(c_sys, 0, 2)

        lay.addLayout(grid)

        # Sección de Acción Rápida: Botones para saltar a la acción
        acciones_frame = QFrame()
        acciones_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
                padding: 20px;
            }}
        """)
        af_lay = QVBoxLayout(acciones_frame)
        af_lay.setSpacing(14)

        lbl_af_tit = QLabel("🚀 ¿CÓMO DESEAS COMENZAR?")
        lbl_af_tit.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_af_tit.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; border: none; background: transparent;")
        af_lay.addWidget(lbl_af_tit)

        botones_row = QHBoxLayout()
        botones_row.setSpacing(12)

        btn_pomodoro = QPushButton("⏱️ Iniciar Sesión de Enfoque")
        btn_pomodoro.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pomodoro.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_pomodoro.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white; border-radius: 8px; padding: 10px 18px; border: none;
            }}
            QPushButton:hover {{ background-color: #4F46E5; }}
        """)
        btn_pomodoro.clicked.connect(lambda: self._navegar_a("Productividad"))
        botones_row.addWidget(btn_pomodoro)

        btn_habitos = QPushButton("✅ Registrar Hábitos")
        btn_habitos.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_habitos.setFont(QFont(self.font_family, 9))
        btn_habitos.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255,255,255,0.05);
                color: white; border-radius: 8px; padding: 10px 18px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.1); }}
        """)
        btn_habitos.clicked.connect(lambda: self._navegar_a("Hábitos"))
        botones_row.addWidget(btn_habitos)

        btn_reposo = QPushButton("🌙 Gestión de Inicio y Reposo")
        btn_reposo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reposo.setFont(QFont(self.font_family, 9))
        btn_reposo.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255,255,255,0.05);
                color: white; border-radius: 8px; padding: 10px 18px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.1); }}
        """)
        btn_reposo.clicked.connect(lambda: self._navegar_a("Modo Reposo"))
        botones_row.addWidget(btn_reposo)

        botones_row.addStretch()
        af_lay.addLayout(botones_row)
        lay.addWidget(acciones_frame)

        lay.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _crear_tarjeta_kpi(self, titulo, valor, subtitulo, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
                padding: 16px;
            }}
            QFrame:hover {{
                border: 1px solid {color}88;
            }}
        """)
        c_lay = QVBoxLayout(card)
        c_lay.setSpacing(6)

        lbl_t = QLabel(titulo)
        lbl_t.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        c_lay.addWidget(lbl_t)

        lbl_v = QLabel(valor)
        lbl_v.setFont(QFont(self.font_family, 16, QFont.Weight.Bold))
        lbl_v.setStyleSheet("color: white; border: none; background: transparent;")
        c_lay.addWidget(lbl_v)

        lbl_s = QLabel(subtitulo)
        lbl_s.setFont(QFont(self.font_family, 8))
        lbl_s.setStyleSheet("color: #9CA3AF; border: none; background: transparent;")
        c_lay.addWidget(lbl_s)

        return card

    def _navegar_a(self, nombre_submodulo):
        # Buscar el QTabWidget contenedor más cercano
        w = self.parent()
        while w:
            if isinstance(w, QTabWidget):
                for i in range(w.count()):
                    tab_name = w.tabText(i).strip().lower()
                    target = nombre_submodulo.strip().lower()
                    if target in tab_name or tab_name in target:
                        w.setCurrentIndex(i)
                        return
            w = w.parent()

        # Fallback: buscar en el notebook de la aplicación principal
        app = getattr(self.context, "app", None) if self.context else None
        if app and hasattr(app, "notebook") and isinstance(app.notebook, QTabWidget):
            for i in range(app.notebook.count()):
                tab_name = app.notebook.tabText(i).strip().lower()
                target = nombre_submodulo.strip().lower()
                if target in tab_name or tab_name in target:
                    app.notebook.setCurrentIndex(i)
                    return
