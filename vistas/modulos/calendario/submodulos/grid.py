import platform
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from .cards import DayCard

class CalendarGrid(QWidget):
    """Cuadrícula interactiva del calendario mensual"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.matriz_dias_widgets = []
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.inicializar_ui()

    def inicializar_ui(self):
        layout_central = QVBoxLayout(self)
        layout_central.setContentsMargins(20, 20, 20, 20)
        layout_central.setSpacing(12)
        
        # --- CABECERA DE NAVEGACIÓN ---
        layout_nav = QHBoxLayout()
        layout_nav.setSpacing(10)
        
        btn_nav_style = f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: none; border-radius: 8px;
                padding: 6px 12px; font-size: 14px;
            }}
            QPushButton:hover {{ 
                background-color: {self.colores['bg_secundario']}; 
                border: 1px solid rgba(255,255,255,0.1); 
            }}
        """
        
        self.btn_prev = QPushButton("❮")
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.setToolTip("Mes anterior")
        self.btn_prev.setStyleSheet(btn_nav_style)
        self.btn_prev.clicked.connect(self.callbacks["mes_anterior"])
        layout_nav.addWidget(self.btn_prev)
 
        self.btn_hoy = QPushButton("HOY")
        self.btn_hoy.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self.btn_hoy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hoy.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.colores['acento']};
                border: 1.5px solid {self.colores['acento']}44;
                border-radius: 8px; padding: 6px 12px; 
            }}
            QPushButton:hover {{ background-color: {self.colores['acento']}22; }}
        """)
        self.btn_hoy.clicked.connect(self.callbacks["ir_a_hoy"])
        layout_nav.addWidget(self.btn_hoy)

        self.btn_goto = QPushButton("IR A...")
        self.btn_goto.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self.btn_goto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_goto.setStyleSheet(self.btn_hoy.styleSheet().replace(self.colores['acento'], self.colores['fg_secundario']))
        self.btn_goto.clicked.connect(self._abrir_goto_dialog)
        layout_nav.addWidget(self.btn_goto)
        
        self.lbl_mes_año = QLabel("ENERO 2024")
        self.lbl_mes_año.setFont(QFont(self.font_family, 18, QFont.Weight.Bold))
        self.lbl_mes_año.setStyleSheet("color: white; ")
        self.lbl_mes_año.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_nav.addWidget(self.lbl_mes_año, 1)
        
        self.btn_next = QPushButton("❯")
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setToolTip("Mes siguiente")
        self.btn_next.setStyleSheet(btn_nav_style)
        self.btn_next.clicked.connect(self.callbacks["mes_siguiente"])
        layout_nav.addWidget(self.btn_next)
        
        layout_central.addLayout(layout_nav)
        
        # --- GRID DEL CALENDARIO ---
        self.grid_container = QFrame()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(8)
        layout_central.addWidget(self.grid_container, 1)
        
        # Headers de días (LUN - DOM)
        dias_nombres = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
        for col, dia in enumerate(dias_nombres):
            lbl_dia = QLabel(dia)
            lbl_dia.setFont(QFont(self.font_family, 7, QFont.Weight.Bold))
            lbl_dia.setStyleSheet(f"color: {self.colores['fg_secundario']}; padding-bottom: 6px; ")
            lbl_dia.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(lbl_dia, 0, col)
            
        # Crear los 42 cuadros (6 semanas x 7 días)
        for fila in range(6):
            fila_widgets = []
            for col in range(7):
                card = DayCard(self.colores, self.callbacks["ver_detalle"], parent_grid=self)
                self.grid_layout.addWidget(card, fila + 1, col)
                fila_widgets.append(card)
            self.matriz_dias_widgets.append(fila_widgets)

    def actualizar_calendario(self, mes_nombre, año, dias_info):
        self.lbl_mes_año.setText(f"{mes_nombre.upper()} {año}")
        
        today_card = None
        first_enabled_card = None

        for r in range(6):
            for c in range(7):
                info = dias_info[r][c]
                widget = self.matriz_dias_widgets[r][c]
                widget.set_data(info, self.callbacks["get_cat_color"])
                
                if widget.isEnabled():
                    if not first_enabled_card:
                        first_enabled_card = widget
                    if info.get("is_today", False):
                        today_card = widget
        
        # Establecer la celda enfocable inicial
        target_focus = today_card if today_card else first_enabled_card
        if target_focus:
            self.set_active_focus_card(target_focus)

    def _abrir_goto_dialog(self):
        from .dialogs import GoToDateDialog
        dialog = GoToDateDialog(self, self.colores, self.callbacks["ir_a_fecha"])
        dialog.exec()

    # --- NAVEGACIÓN POR TECLADO ---
    
    def get_first_enabled_card(self):
        for row in self.matriz_dias_widgets:
            for w in row:
                if w.isEnabled() and w.fecha:
                    return w
        return None

    def get_last_enabled_card(self):
        for row in reversed(self.matriz_dias_widgets):
            for w in reversed(row):
                if w.isEnabled() and w.fecha:
                    return w
        return None

    def set_active_focus_card(self, target):
        for row in self.matriz_dias_widgets:
            for card in row:
                if card == target:
                    card.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                else:
                    card.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def manejar_tecla_grid(self, card, key):
        r, c = -1, -1
        for row_idx, row in enumerate(self.matriz_dias_widgets):
            if card in row:
                r = row_idx
                c = row.index(card)
                break
        if r == -1:
            return

        # Navegación inter-mensual
        if key == Qt.Key.Key_Left and card == self.get_first_enabled_card():
            self.callbacks["mes_anterior"]()
            last_card = self.get_last_enabled_card()
            if last_card:
                last_card.setFocus()
            return
        elif key == Qt.Key.Key_Right and card == self.get_last_enabled_card():
            self.callbacks["mes_siguiente"]()
            first_card = self.get_first_enabled_card()
            if first_card:
                first_card.setFocus()
            return

        new_r, new_c = r, c
        if key == Qt.Key.Key_Left:
            new_c -= 1
            if new_c < 0:
                new_c = 6
                new_r -= 1
        elif key == Qt.Key.Key_Right:
            new_c += 1
            if new_c > 6:
                new_c = 0
                new_r += 1
        elif key == Qt.Key.Key_Up:
            new_r -= 1
        elif key == Qt.Key.Key_Down:
            new_r += 1

        if 0 <= new_r < 6 and 0 <= new_c < 7:
            target = self.matriz_dias_widgets[new_r][new_c]
            if not target.isEnabled():
                if key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
                    target = self.get_first_enabled_card()
                else:
                    target = self.get_last_enabled_card()
            
            if target and target.isEnabled():
                target.setFocus()
