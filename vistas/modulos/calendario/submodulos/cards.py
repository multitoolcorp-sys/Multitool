import platform
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class DayCard(QFrame):
    """Celda individual interactiva para cada día del mes"""
    def __init__(self, colores, click_callback, parent_grid=None):
        super().__init__()
        self.colores = colores
        self.click_callback = click_callback
        self.parent_grid = parent_grid
        self.fecha = None
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(60, 60)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
        self.layout_v = QVBoxLayout(self)
        self.layout_v.setContentsMargins(8, 8, 8, 8)
        self.layout_v.setSpacing(3)
        
        self.lbl_num = QLabel("")
        self.lbl_num.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.layout_v.addWidget(self.lbl_num, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.dots_container = QWidget()
        self.dots_layout = QHBoxLayout(self.dots_container)
        self.dots_layout.setContentsMargins(0, 0, 0, 0)
        self.dots_layout.setSpacing(3)
        self.dots_layout.addStretch()
        self.layout_v.addWidget(self.dots_container, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)

    def set_data(self, info, get_cat_color):
        self.fecha = info["fecha"]
        self.lbl_num.setText(info["num"])
        
        # Limpiar dots
        while self.dots_layout.count() > 1:
            item = self.dots_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        # Estilo de la fecha
        if not info["es_mes_actual"]:
            self.setStyleSheet("background-color: transparent; border: 1px solid rgba(255,255,255,0.01);")
            self.lbl_num.setStyleSheet(f"color: {self.colores['bg_terciario']};")
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            is_today = info.get("is_today", False)
            
            border_style = f"1.5px solid {self.colores['acento']}" if is_today else "1px solid rgba(255,255,255,0.05)"
            bg_style = f"{self.colores['acento']}18" if is_today else "rgba(255,255,255,0.02)"
            
            self.setStyleSheet(f"""
                DayCard {{
                    background-color: {bg_style};
                    border-radius: 8px;
                    border: {border_style};
                }}
                DayCard:hover {{
                    background-color: rgba(255, 255, 255, 0.06);
                    border: 1px solid {self.colores['acento']};
                }}
                DayCard:focus {{
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1.8px solid {self.colores['acento']};
                }}
            """)
            self.lbl_num.setStyleSheet(f"color: {info['fg']};")
            
            # Puntos de categorías
            if info["recs"]:
                for r in info["recs"][:3]: # Máximo 3 puntos
                    dot = QFrame()
                    dot.setFixedSize(5, 5)
                    color = get_cat_color(r.get("categoria", "General"))
                    dot.setStyleSheet(f"background-color: {color}; border-radius: 2.5px;")
                    self.dots_layout.insertWidget(self.dots_layout.count()-1, dot)
                
                if len(info["recs"]) > 3:
                    lbl_plus = QLabel("+")
                    lbl_plus.setFont(QFont(self.font_family, 7, QFont.Weight.Bold))
                    lbl_plus.setStyleSheet(f"color: {self.colores['fg_secundario']};")
                    self.dots_layout.insertWidget(self.dots_layout.count()-1, lbl_plus)

    def mousePressEvent(self, event):
        if self.fecha and event.button() == Qt.MouseButton.LeftButton:
            self.click_callback(self.fecha)
            self.setFocus()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            if self.parent_grid:
                self.parent_grid.manejar_tecla_grid(self, key)
                event.accept()
                return
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self.fecha and self.click_callback:
                self.click_callback(self.fecha)
                event.accept()
                return
        super().keyPressEvent(event)

    def focusInEvent(self, event):
        if self.parent_grid:
            self.parent_grid.set_active_focus_card(self)
        super().focusInEvent(event)

class UpcomingCard(QFrame):
    """Tarjeta compacta para vista previa de eventos futuros"""
    def __init__(self, rec, colores, get_cat_color, click_callback):
        super().__init__()
        self.colores = colores
        self.callback = click_callback
        self.clicked_fecha = rec["fecha_dt"]
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            UpcomingCard {{
                background-color: rgba(255, 255, 255, 0.02);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            UpcomingCard:hover {{
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid {self.colores['acento']}44;
            }}
        """)
        
        layout_h = QHBoxLayout(self)
        layout_h.setContentsMargins(10, 8, 10, 8)
        layout_h.setSpacing(10)
        
        # Indicador de categoría
        cat_color = get_cat_color(rec.get("categoria", "General"))
        indicador = QFrame()
        indicador.setFixedWidth(4)
        indicador.setStyleSheet(f"background-color: {cat_color}; border-radius: 2px;")
        layout_h.addWidget(indicador)
        
        # Información del evento
        info_v = QVBoxLayout()
        info_v.setContentsMargins(0, 0, 0, 0)
        info_v.setSpacing(1)
        
        fecha_str = rec["fecha_dt"].strftime("%d %b")
        hora = rec.get('hora', '00:00')
        lbl_meta = QLabel(f"{fecha_str.upper()} • {hora}")
        lbl_meta.setFont(QFont(self.font_family, 7, QFont.Weight.Bold))
        lbl_meta.setStyleSheet(f"color: {self.colores['acento']}; ")
        info_v.addWidget(lbl_meta)
        
        lbl_tit = QLabel(rec["titulo"])
        lbl_tit.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_tit.setStyleSheet("color: white;")
        lbl_tit.setWordWrap(True)
        info_v.addWidget(lbl_tit)
        
        layout_h.addLayout(info_v, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback(self.clicked_fecha)
