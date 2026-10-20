import platform
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QHeaderView
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath

from ..utils.controlador_procesos import actualizar_procesos, finalizar_proceso

class NeonRealtimeChart(QWidget):
    """Lienzo personalizado pintado con QPainter para mostrar el uso de CPU/RAM en tiempo real"""
    def __init__(self, parent=None, colores=None):
        super().__init__(parent)
        if isinstance(colores, dict):
            self.colores = colores
        elif hasattr(colores, "app") and hasattr(colores.app, "COLORES"):
            self.colores = colores.app.COLORES
        else:
            self.colores = {
                "acento": "#6366F1", "exito": "#34D399", "bg_secundario": "#1E1E2E",
                "fg_secundario": "#AAB0B8"
            }
        self.setFixedHeight(110)
        self.cpu_history = [0.0] * 60
        self.ram_history = [0.0] * 60

    def add_points(self, cpu, ram):
        self.cpu_history.append(float(cpu))
        self.cpu_history.pop(0)
        self.ram_history.append(float(ram))
        self.ram_history.pop(0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Fondo con efecto vidrio (glassmorphic)
        painter.setPen(Qt.PenStyle.NoPen)
        bg = QColor(self.colores.get("bg_secundario", "#1E1E2E"))
        bg.setAlpha(120)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(0, 0, w, h, 12, 12)

        # Borde sutil
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 12, 12)

        # Rejilla (Grid lines)
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1, Qt.PenStyle.DashLine))
        for i in range(1, 4):
            y = int(h * i / 4)
            painter.drawLine(15, y, w - 15, y)

        # Dibujar líneas del historial
        self._dibujar_curva(painter, self.cpu_history, self.colores.get("acento", "#6366F1"))
        self._dibujar_curva(painter, self.ram_history, self.colores.get("exito", "#34D399"))

        # Pintar Leyenda con tipografía limpia
        font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        painter.setFont(QFont(font_family, 8, QFont.Weight.Bold))
        
        # Leyenda CPU
        painter.setPen(QColor(self.colores.get("acento", "#6366F1")))
        painter.drawText(20, 22, f"● CPU: {self.cpu_history[-1]:.1f}%")
        
        # Leyenda RAM
        painter.setPen(QColor(self.colores.get("exito", "#34D399")))
        painter.drawText(120, 22, f"● RAM: {self.ram_history[-1]:.1f}%")

    def _dibujar_curva(self, painter, history, color_hex):
        w = self.width()
        h = self.height()
        puntos = len(history)
        if puntos < 2: return

        step = (w - 30) / (puntos - 1)
        color = QColor(color_hex)

        path = QPainterPath()

        def map_y(val):
            # Mapear 0-100 a la altura con margen superior/inferior de 15px
            return h - 15 - (val / 100.0) * (h - 30)

        path.moveTo(15, map_y(history[0]))
        for i in range(1, puntos):
            x = 15 + i * step
            y = map_y(history[i])
            path.lineTo(x, y)

        # 1. Dibujar destello inferior (glow grueso de baja opacidad)
        glow_color = QColor(color)
        glow_color.setAlpha(25)
        painter.setPen(QPen(glow_color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)

        # 2. Dibujar línea principal (fina y brillante)
        painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)

        # 3. Dibujar relleno translúcido en gradiente hacia abajo
        fill_path = QPainterPath(path)
        fill_path.lineTo(15 + (puntos - 1) * step, h - 15)
        fill_path.lineTo(15, h - 15)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, 15, 0, h - 15)
        c_start = QColor(color)
        c_start.setAlpha(35)
        c_end = QColor(color)
        c_end.setAlpha(0)
        grad.setColorAt(0.0, c_start)
        grad.setColorAt(1.0, c_end)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(fill_path)


class TabProcesos(QWidget):
    """Pestaña de Gestión de Procesos en Tiempo Real (Task Manager)"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.inicializar_ui()

    def inicializar_ui(self):
        self.setStyleSheet("color: white;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # ── Gráfico en Tiempo Real ──
        self.chart = NeonRealtimeChart(self, self.colores)
        layout.addWidget(self.chart)
        
        # ── Barra superior de acciones ──
        h_lay = QHBoxLayout()
        h_lay.setSpacing(10)

        self.txt_proc_search = QLineEdit()
        self.txt_proc_search.setPlaceholderText("🔍  Filtrar por nombre o PID…")
        self.txt_proc_search.setFont(QFont(self.font_family, 10))
        self.txt_proc_search.setFixedHeight(42)
        self.txt_proc_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                padding: 0px 16px;
                selection-background-color: {self.colores['acento']}66;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {self.colores['acento']};
                background-color: {self.colores['bg_terciario']};
            }}
        """)
        self.txt_proc_search.textChanged.connect(lambda: actualizar_procesos(self))
        h_lay.addWidget(self.txt_proc_search, 1)

        btn_act = QPushButton("🔄  Actualizar")
        btn_act.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_act.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_act.setFixedHeight(42)
        btn_act.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: rgba(255,255,255,0.85);
                border-radius: 10px;
                padding: 0px 22px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
            QPushButton:hover {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid {self.colores['acento']}88;
                color: white;
            }}
            QPushButton:pressed {{ background-color: {self.colores['acento']}33; }}
        """)
        btn_act.clicked.connect(lambda: actualizar_procesos(self))
        h_lay.addWidget(btn_act)

        btn_kill = QPushButton("☠  Terminar")
        btn_kill.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_kill.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_kill.setFixedHeight(42)
        btn_kill.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.colores['error']};
                border: 1.5px solid {self.colores['error']}88;
                border-radius: 10px;
                padding: 0px 22px;
            }}
            QPushButton:hover {{
                background-color: {self.colores['error']}22;
                border-color: {self.colores['error']};
                color: #FF6B6B;
            }}
            QPushButton:pressed {{ background-color: {self.colores['error']}44; }}
        """)
        btn_kill.clicked.connect(lambda: finalizar_proceso(self))
        h_lay.addWidget(btn_kill)

        layout.addLayout(h_lay)

        # ── Tabla de Procesos ──
        self.table_procs = QTableWidget()
        self.table_procs.setColumnCount(6)
        self.table_procs.setHorizontalHeaderLabels(["PID", "Nombre", "Usuario", "CPU %", "Memoria", "Estado"])
        self.table_procs.setFont(QFont(self.font_family, 9))
        self.table_procs.setAlternatingRowColors(True)
        self.table_procs.setShowGrid(False)
        self.table_procs.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_procs.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_procs.verticalHeader().setVisible(False)
        self.table_procs.verticalHeader().setDefaultSectionSize(36)
        self.table_procs.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.table_procs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_procs.horizontalHeader().setStretchLastSection(True)
        self.table_procs.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table_procs.horizontalHeader().setHighlightSections(False)

        self.table_procs.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                alternate-background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 10px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 0px 14px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background: {self.colores['acento']}33;
                color: white;
                border-left: 2px solid {self.colores['acento']};
            }}
            QHeaderView::section {{
                background-color: {self.colores['bg_terciario']};
                color: {self.colores['fg_secundario']};
                padding: 10px 14px;
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.06);
                font-weight: 600;
                font-size: 9px;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
            QHeaderView::section:first {{
                border-top-left-radius: 10px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.15);
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        layout.addWidget(self.table_procs)
