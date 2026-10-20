"""
window_cards.py - Tarjeta estilo ventana con diseño Glassmorphism (ModuleWindowCard) para accesos de Quick Widgets
"""
import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt


class ModuleWindowCard(QFrame):
    """Tarjeta estilo ventana Glassmorphism para un módulo Quick Widget"""
    def __init__(self, key, display_name, emoji, description, colores, on_open, on_pin, parent=None):
        super().__init__(parent)
        self.key = key
        self.colores = colores
        self._hovered = False
        self.setMinimumHeight(135)
        self.setMaximumHeight(145)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName(f"ModuleCard_{key}")
        self.setStyleSheet(f"""
            QFrame#ModuleCard_{key} {{
                background-color: rgba(30, 30, 46, 0.85);
                border: 1.5px solid {colores.get('bg_terciario', '#2A2A3C')};
                border-radius: 12px;
            }}
            QFrame#ModuleCard_{key}:hover {{
                border: 1.5px solid {colores.get('acento', '#6366F1')};
                background-color: rgba(99, 102, 241, 0.12);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Barra decorativa estilo ventana OS
        title_bar = QWidget()
        title_bar.setFixedHeight(20)
        title_bar.setStyleSheet("background: transparent;")
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(4)
        for col in ["#F87171", "#FBBF24", "#34D399"]:
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background: {col}; border-radius: 4px;")
            tb_lay.addWidget(dot)

        tb_lay.addStretch()

        # Insignia de Estado En Vivo
        live_str = self._get_live_info()
        if live_str:
            lbl_live = QLabel(live_str)
            lbl_live.setStyleSheet(f"color: {colores.get('acento', '#6366F1')}; font-weight: bold; font-size: 9px; background: rgba(99,102,241,0.15); border-radius: 4px; padding: 1px 6px;")
            tb_lay.addWidget(lbl_live)

        layout.addWidget(title_bar)

        # Encabezado del módulo
        header = QHBoxLayout()
        lbl_icon = QLabel(emoji)
        lbl_icon.setStyleSheet("font-size: 22px; background: transparent;")
        header.addWidget(lbl_icon)
        lbl_name = QLabel(display_name)
        lbl_name.setStyleSheet("color: white; font-weight: bold; font-size: 13px; background: transparent;")
        header.addWidget(lbl_name)
        header.addStretch()
        layout.addLayout(header)

        # Descripción
        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet(f"color: {colores.get('fg_secundario', '#9CA3AF')}; font-size: 10px; background: transparent;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        layout.addStretch()

        # Botones de Acción: Abrir / Fijar
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_open = QPushButton("⬡ Abrir")
        btn_open.setFixedHeight(24)
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setStyleSheet(f"""
            QPushButton {{
                background-color: {colores.get('acento', '#6366F1')};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                padding: 0 10px;
            }}
            QPushButton:hover {{ background-color: {colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_open.clicked.connect(lambda checked=False: on_open())
        btn_row.addWidget(btn_open)

        btn_pin = QPushButton("📌 Fijar")
        btn_pin.setFixedHeight(24)
        btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pin.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {colores.get('fg_secundario', '#9CA3AF')};
                border: 1px solid {colores.get('bg_terciario', '#2A2A3C')};
                border-radius: 4px;
                font-size: 10px;
                padding: 0 10px;
            }}
            QPushButton:hover {{ color: white; border-color: {colores.get('acento', '#6366F1')}; }}
        """)
        btn_pin.clicked.connect(lambda checked=False: on_pin())
        btn_row.addWidget(btn_pin)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _get_live_info(self):
        try:
            if self.key == "sistema" or self.key == "syshud":
                ram = psutil.virtual_memory().percent
                return f"RAM {ram:.0f}%"
            elif self.key == "postits":
                return "Adhesivas"
            elif self.key == "launcher":
                return "Accesos"
            elif self.key == "tiempo":
                return "Reloj OS"
        except Exception: pass
        return ""
