from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QListWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class SidebarCuaderno(QFrame):
    def __init__(self, colores, callbacks, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self._build_sidebar()

    def _hex_to_rgb(self, hex_str):
        hex_str = hex_str.lstrip('#')
        if len(hex_str) == 3:
            hex_str = ''.join(c*2 for c in hex_str)
        return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"

    def _build_sidebar(self):
        self.setFixedWidth(240)
        self.setStyleSheet(
            f"QFrame {{ background:{self.colores['bg_secundario']}; border-right:1px solid rgba(255, 255, 255, 0.08); }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 18, 14, 18)
        lay.setSpacing(12)

        # Header
        lbl = QLabel("📚  MIS CUADERNOS")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color:{self.colores['acento']}; margin-top: 5px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)

        # Botones nuevo / eliminar
        row = QHBoxLayout()
        for label, key, color in [
            (" Nuevo",    "nuevo",    self.colores.get("acento", "#6366F1")),
            (" Eliminar", "eliminar", self.colores.get("error", "#F87171")),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{ 
                    background:{color}; 
                    color:white; 
                    padding:8px 12px; 
                    border-radius:8px; 
                    font-weight:bold; 
                    font-size:11px; 
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }}
                QPushButton:hover {{ 
                    background:{color}cc; 
                }}
                QPushButton:pressed {{ 
                    background:{color}aa; 
                }}
            """)
            if key in self.callbacks and self.callbacks[key]:
                btn.clicked.connect(self.callbacks[key])
            row.addWidget(btn)
        lay.addLayout(row)

        # Lista
        self.list_horarios = QListWidget()
        self.list_horarios.setStyleSheet(f"""
            QListWidget {{
                background: rgba(30, 30, 46, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding: 6px;
                color: {self.colores['fg_principal']};
            }}
            QListWidget::item {{
                padding: 10px 12px;
                margin-bottom: 4px;
                border-radius: 8px;
                color: {self.colores['fg_principal']};
            }}
            QListWidget::item:selected {{
                background: rgba({self._hex_to_rgb(self.colores['acento'])}, 0.25);
                color: white;
                border: 1px solid {self.colores['acento']};
            }}
            QListWidget::item:hover:!selected {{
                background: rgba(255, 255, 255, 0.05);
                color: white;
            }}
        """)
        if "cargar" in self.callbacks and self.callbacks["cargar"]:
            self.list_horarios.itemSelectionChanged.connect(self.callbacks["cargar"])
        lay.addWidget(self.list_horarios)

        # Tip
        tip = QLabel("💡 TIP: Puedes pegar tablas desde Excel directamente con Ctrl+V")
        tip.setStyleSheet(f"color:{self.colores['fg_secundario']}; font-size:10px; margin-top:10px;")
        tip.setWordWrap(True)
        lay.addWidget(tip)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(
            f"QFrame {{ background:{self.colores.get('bg_secundario', '#1E1E2E')}; border-right:1px solid rgba(255, 255, 255, 0.08); }}"
        )
