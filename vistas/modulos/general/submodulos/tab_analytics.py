import os
import json
import datetime
import platform
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QGridLayout
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QPainterPath

class NeonProgressBarChart(QWidget):
    """Widget de dibujo personalizado para mostrar un gráfico de barras neon de tiempo de actividad por módulo"""
    def __init__(self, colores, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.data = [] # Lista de tuplas (modulo, segundos, porcentaje)
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.setMinimumHeight(220)

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Limpiar fondo
        painter.fillRect(self.rect(), QColor(self.colores["bg_secundario"]))
        
        if not self.data:
            painter.setPen(QColor(self.colores["fg_secundario"]))
            painter.setFont(QFont(self.font_family, 10))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sin datos de módulos para graficar")
            return

        margin_left = 110
        margin_right = 60
        margin_top = 20
        row_height = 36
        bar_height = 12
        
        font_label = QFont(self.font_family, 8, QFont.Weight.Bold)
        font_value = QFont(self.font_family, 8)
        
        max_width = self.width() - margin_left - margin_right
        
        palette = [
            self.colores.get("acento", "#6366F1"),
            self.colores.get("exito", "#34D399"),
            self.colores.get("advertencia", "#FBBF24"),
            self.colores.get("error", "#F87171"),
            "#10B981", "#3B82F6", "#EC4899", "#8B5CF6"
        ]

        for i, (modulo, segs, pct) in enumerate(self.data[:5]): # Top 5 módulos
            y = margin_top + i * row_height
            color = palette[i % len(palette)]
            
            # Dibujar etiqueta de módulo
            painter.setPen(QColor(self.colores["fg_principal"]))
            painter.setFont(font_label)
            painter.drawText(QRectF(10, y, margin_left - 20, row_height), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, modulo)
            
            # Fondo de la barra
            bar_rect_bg = QRectF(margin_left, y + (row_height - bar_height) / 2, max_width, bar_height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
            painter.drawRoundedRect(bar_rect_bg, bar_height/2, bar_height/2)
            
            # Relleno de la barra (Neon)
            fill_w = max_width * (pct / 100.0)
            if fill_w > 0:
                bar_rect_fill = QRectF(margin_left, y + (row_height - bar_height) / 2, fill_w, bar_height)
                
                # Crear gradiente neon
                gradient = QLinearGradient(bar_rect_fill.left(), bar_rect_fill.top(), bar_rect_fill.right(), bar_rect_fill.top())
                c_start = QColor(color)
                c_end = QColor(color)
                c_end.setAlpha(120)
                gradient.setColorAt(0, c_start)
                gradient.setColorAt(1, c_end)
                
                painter.setBrush(QBrush(gradient))
                painter.drawRoundedRect(bar_rect_fill, bar_height/2, bar_height/2)
                
                # Efecto de brillo sutil en el borde de la barra
                painter.setBrush(Qt.BrushStyle.NoBrush)
                glow_pen = QPen(c_start, 1)
                painter.setPen(glow_pen)
                painter.drawRoundedRect(bar_rect_fill, bar_height/2, bar_height/2)
            
            # Dibujar valor del porcentaje / tiempo
            hrs = int(segs // 3600)
            mins = int((segs % 3600) // 60)
            text_val = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"
            if segs < 60:
                text_val = f"{int(segs)}s"
                
            painter.setPen(QColor(self.colores["fg_secundario"]))
            painter.setFont(font_value)
            painter.drawText(QRectF(margin_left + max_width + 10, y, margin_right - 10, row_height), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{text_val} ({pct:.1f}%)")


class NeonLineChart(QWidget):
    """Widget de dibujo personalizado para mostrar un gráfico de ondas neon de actividad horaria (24 horas)"""
    def __init__(self, colores, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.hourly_data = [0] * 24
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.setMinimumHeight(220)

    def set_data(self, data):
        self.hourly_data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Limpiar fondo
        painter.fillRect(self.rect(), QColor(self.colores["bg_secundario"]))
        
        margin_left = 35
        margin_right = 20
        margin_top = 20
        margin_bottom = 30
        
        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom
        
        max_val = max(self.hourly_data) if any(self.hourly_data) else 1
        
        # Dibujar cuadrícula de fondo horizontal
        grid_pen = QPen(QColor(255, 255, 255, 10), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        grid_levels = 4
        for gl in range(grid_levels + 1):
            y_level = margin_top + h * (gl / grid_levels)
            painter.drawLine(int(margin_left), int(y_level), int(margin_left + w), int(y_level))
            
            # Dibujar etiquetas del eje Y
            val = int(max_val * (1.0 - gl / grid_levels))
            painter.setPen(QColor(self.colores["fg_secundario"]))
            painter.setFont(QFont(self.font_family, 7))
            painter.drawText(QRectF(5, y_level - 6, margin_left - 10, 12), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, str(val))
            painter.setPen(grid_pen)
            
        # Puntos del gráfico
        points = []
        step_x = w / 23.0
        for hour in range(24):
            x = margin_left + hour * step_x
            val = self.hourly_data[hour]
            y = margin_top + h * (1.0 - val / max_val)
            points.append(QPointF(x, y))
            
        # Dibujar área de onda rellena con gradiente
        if points:
            path = QPainterPath()
            path.moveTo(points[0])
            for i in range(1, len(points)):
                # Curva suave
                p_prev = points[i-1]
                p_curr = points[i]
                c1 = QPointF(p_prev.x() + step_x/2.0, p_prev.y())
                c2 = QPointF(p_curr.x() - step_x/2.0, p_curr.y())
                path.cubicTo(c1, c2, p_curr)
                
            # Cerrar el área para el relleno
            fill_path = QPainterPath(path)
            fill_path.lineTo(margin_left + w, margin_top + h)
            fill_path.lineTo(margin_left, margin_top + h)
            fill_path.closeSubpath()
            
            area_gradient = QLinearGradient(0, margin_top, 0, margin_top + h)
            c_accent = QColor(self.colores["acento"])
            c_top = QColor(c_accent)
            c_top.setAlpha(60)
            c_bottom = QColor(c_accent)
            c_bottom.setAlpha(5)
            area_gradient.setColorAt(0, c_top)
            area_gradient.setColorAt(1, c_bottom)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(area_gradient))
            painter.drawPath(fill_path)
            
            # Dibujar la línea principal (Neon Line)
            line_pen = QPen(c_accent, 2)
            painter.setPen(line_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            
            # Dibujar puntos de datos para horas clave
            painter.setPen(Qt.PenStyle.NoPen)
            for i, p in enumerate(points):
                if self.hourly_data[i] > 0:
                    painter.setBrush(QBrush(QColor(self.colores["exito"])))
                    painter.drawEllipse(p, 3.5, 3.5)
                    painter.setBrush(QBrush(QColor(self.colores["acento"])))
                    painter.drawEllipse(p, 1.5, 1.5)

        # Dibujar etiquetas del eje X (cada 4 horas)
        painter.setPen(QColor(self.colores["fg_secundario"]))
        painter.setFont(QFont(self.font_family, 7, QFont.Weight.Bold))
        for hour in range(0, 25, 4):
            h_val = hour % 24
            x = margin_left + h_val * step_x
            text_x = f"{h_val:02d}:00"
            painter.drawText(QRectF(x - 20, margin_top + h + 8, 40, 15), Qt.AlignmentFlag.AlignCenter, text_x)


class TabAnalyticsGUI(QWidget):
    """Pestaña de analíticas de productividad del usuario integrada en Inicio"""
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
        
        self.inicializar_ui()
        self.refresh_logs()

    def inicializar_ui(self):
        self.setStyleSheet(f"background-color: {self.colores['bg_principal']}; border: none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Encabezado con Botón Refrescar
        header_lay = QHBoxLayout()
        header_title = QLabel("📊 ANALÍTICAS DE PRODUCTIVIDAD")
        header_title.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        header_title.setStyleSheet(f"color: white; font-weight: bold;")
        header_lay.addWidget(header_title)
        
        header_lay.addStretch()

        self.btn_refresh = QPushButton("🔄 Actualizar")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_refresh.setFixedSize(120, 32)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#4F46E5')};
            }}
        """)
        self.btn_refresh.clicked.connect(self.refresh_logs)
        header_lay.addWidget(self.btn_refresh)
        
        layout.addLayout(header_lay)

        # Panel de Tarjetas de Resumen
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet("background: transparent; border: none;")
        self.summary_layout = QHBoxLayout(self.summary_frame)
        self.summary_layout.setContentsMargins(0, 0, 0, 0)
        self.summary_layout.setSpacing(15)
        
        self.card_events = self._crear_resumen_card("EVENTOS DE ACTIVIDAD", "0", "Total de acciones logueadas")
        self.card_time = self._crear_resumen_card("TIEMPO ACTIVO TOTAL", "0m", "Tiempo acumulado en pantalla")
        self.card_favorite = self._crear_resumen_card("MÓDULO PREFERIDO", "Ninguno", "Módulo con mayor interacción")
        
        self.summary_layout.addWidget(self.card_events)
        self.summary_layout.addWidget(self.card_time)
        self.summary_layout.addWidget(self.card_favorite)
        layout.addWidget(self.summary_frame)

        # Sección de Gráficos (Split horizontal)
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(20)

        # Gráfico Izquierdo (Módulos)
        self.box_modules = QFrame()
        self.box_modules.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;")
        box_mod_lay = QVBoxLayout(self.box_modules)
        box_mod_lay.setContentsMargins(15, 15, 15, 15)
        box_mod_lbl = QLabel("🕒 DISTRIBUCIÓN DE TIEMPO POR MÓDULO")
        box_mod_lbl.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        box_mod_lbl.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        box_mod_lay.addWidget(box_mod_lbl)
        
        self.chart_modules = NeonProgressBarChart(self.colores)
        box_mod_lay.addWidget(self.chart_modules)
        charts_layout.addWidget(self.box_modules, 1)

        # Gráfico Derecho (Horas de actividad)
        self.box_hours = QFrame()
        self.box_hours.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;")
        box_hrs_lay = QVBoxLayout(self.box_hours)
        box_hrs_lay.setContentsMargins(15, 15, 15, 15)
        box_hrs_lbl = QLabel("📈 ACTIVIDAD POR HORA DEL DÍA")
        box_hrs_lbl.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        box_hrs_lbl.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        box_hrs_lay.addWidget(box_hrs_lbl)
        
        self.chart_hours = NeonLineChart(self.colores)
        box_hrs_lay.addWidget(self.chart_hours)
        charts_layout.addWidget(self.box_hours, 1)

        layout.addLayout(charts_layout, 1)

    def _crear_resumen_card(self, titulo, valor, descripcion):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
            }}
            QFrame:hover {{
                border: 1px solid rgba(99, 102, 241, 0.4);
            }}
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(15, 15, 15, 15)
        card_lay.setSpacing(6)

        lbl_t = QLabel(titulo)
        lbl_t.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_t.setStyleSheet("color: rgba(255,255,255,0.4); border: none;")
        card_lay.addWidget(lbl_t)

        lbl_val = QLabel(valor)
        lbl_val.setFont(QFont(self.font_family, 15, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {self.colores['acento']}; border: none;")
        card_lay.addWidget(lbl_val)

        lbl_d = QLabel(descripcion)
        lbl_d.setFont(QFont(self.font_family, 8))
        lbl_d.setStyleSheet("color: rgba(255,255,255,0.5); border: none;")
        card_lay.addWidget(lbl_d)

        # Almacenar referencias para actualizar valores más adelante
        if not hasattr(self, "_labels_dinamicos"):
            self._labels_dinamicos = {}
        self._labels_dinamicos[titulo] = lbl_val
        
        return card

    def refresh_logs(self):
        ruta_logs = Path(self.context.ruta_usuario) / "logs"
        if not ruta_logs.exists():
            self.show_no_data()
            return

        module_events = {}
        module_time = {}
        hourly_activity = [0] * 24
        
        log_files = sorted(list(ruta_logs.glob("*.json")))
        
        total_logs = 0
        last_timestamp = None
        last_module = None
        
        for file_path in log_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                if not isinstance(logs, list):
                    continue
                
                for entry in logs:
                    timestamp_str = entry.get("timestamp")
                    modulo = entry.get("modulo", "Sistema")
                    
                    if not timestamp_str:
                        continue
                        
                    try:
                        dt = datetime.datetime.fromisoformat(timestamp_str[:19])
                    except ValueError:
                        continue
                    
                    total_logs += 1
                    module_events[modulo] = module_events.get(modulo, 0) + 1
                    
                    # Track hourly activity
                    hour = dt.hour
                    hourly_activity[hour] += 1
                    
                    # Compute duration in module
                    if last_timestamp is not None and last_module == modulo:
                        delta = (dt - last_timestamp).total_seconds()
                        if delta < 900: # < 15 mins
                            module_time[modulo] = module_time.get(modulo, 0.0) + delta
                    
                    last_timestamp = dt
                    last_module = modulo
            except Exception as e:
                print(f"[!] Error parsing log file {file_path}: {e}")

        # Update labels
        if hasattr(self, "_labels_dinamicos"):
            # 1. Eventos
            self._labels_dinamicos["EVENTOS DE ACTIVIDAD"].setText(f"{total_logs}")
            
            # 2. Tiempo activo total
            total_active_seconds = sum(module_time.values())
            hrs = int(total_active_seconds // 3600)
            mins = int((total_active_seconds % 3600) // 60)
            if hrs > 0:
                self._labels_dinamicos["TIEMPO ACTIVO TOTAL"].setText(f"{hrs}h {mins}m")
            else:
                self._labels_dinamicos["TIEMPO ACTIVO TOTAL"].setText(f"{mins}m")
                
            # 3. Módulo preferido
            if module_events:
                pref_module = max(module_events, key=module_events.get)
                pref_pct = (module_events[pref_module] / total_logs) * 100
                self._labels_dinamicos["MÓDULO PREFERIDO"].setText(f"{pref_module[:12]} ({int(pref_pct)}%)")
            else:
                self._labels_dinamicos["MÓDULO PREFERIDO"].setText("Ninguno")

        # Preparar datos para el gráfico de barras
        bar_data = []
        total_time_calc = sum(module_time.values())
        if total_time_calc > 0:
            for mod, secs in module_time.items():
                pct = (secs / total_time_calc) * 100
                bar_data.append((mod, secs, pct))
        else:
            # Fallback a conteo de eventos si no hay diferencias de tiempo acumuladas
            total_ev = sum(module_events.values())
            if total_ev > 0:
                for mod, evs in module_events.items():
                    pct = (evs / total_ev) * 100
                    # Simular 10 segundos por evento
                    bar_data.append((mod, evs * 10.0, pct))
                    
        # Ordenar por tiempo descendente
        bar_data.sort(key=lambda x: x[1], reverse=True)
        
        self.chart_modules.set_data(bar_data)
        self.chart_hours.set_data(hourly_activity)

    def show_no_data(self):
        if hasattr(self, "_labels_dinamicos"):
            self._labels_dinamicos["EVENTOS DE ACTIVIDAD"].setText("0")
            self._labels_dinamicos["TIEMPO ACTIVO TOTAL"].setText("0m")
            self._labels_dinamicos["MÓDULO PREFERIDO"].setText("Ninguno")
        self.chart_modules.set_data([])
        self.chart_hours.set_data([0] * 24)

# Compatibilidad hacia atrás
ProductividadGUI = TabAnalyticsGUI
