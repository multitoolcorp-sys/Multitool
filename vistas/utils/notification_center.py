"""
notification_center.py - Centro de Notificaciones y Registro de Auditoría de MultiTool
"""
import json
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


class NotificationCenterDialog(QDialog):
    """Panel flotante del Centro de Notificaciones y Registro de Eventos."""
    def __init__(self, parent=None, colores=None, ruta_usuario=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.ruta_usuario = ruta_usuario
        self.setWindowTitle("🔔 Centro de Notificaciones y Auditoría")
        self.resize(520, 500)
        self.init_ui()
        self.cargar_eventos()

    def init_ui(self):
        bg = self.colores.get("bg_principal", "#121218")
        bg_s = self.colores.get("bg_secundario", "#1E1E2E")
        bg_t = self.colores.get("bg_terciario", "#2D2D3D")
        acento = self.colores.get("acento", "#6366F1")
        fg_p = self.colores.get("fg_principal", "#FFFFFF")
        fg_s = self.colores.get("fg_secundario", "#AAB0B8")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_s};
                color: {fg_p};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header
        h_box = QHBoxLayout()
        lbl_title = QLabel("🔔 Centro de Actividades & Notificaciones")
        lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: white;")
        h_box.addWidget(lbl_title)
        h_box.addStretch()

        btn_refresh = QPushButton("🔄")
        btn_refresh.setFixedSize(26, 26)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setToolTip("Refrescar registros")
        btn_refresh.setStyleSheet(f"background: {bg_t}; color: white; border: none; border-radius: 4px;")
        btn_refresh.clicked.connect(self.cargar_eventos)
        h_box.addWidget(btn_refresh)
        layout.addLayout(h_box)

        # Filtros
        f_box = QHBoxLayout()
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍 Filtrar eventos o módulos...")
        self.txt_filter.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg};
                color: {fg_p};
                border: 1px solid {bg_t};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
        """)
        self.txt_filter.textChanged.connect(self.filtrar_eventos)
        f_box.addWidget(self.txt_filter, 1)

        self.cb_nivel = QComboBox()
        self.cb_nivel.addItems(["Todos los niveles", "INFO", "WARNING", "ERROR"])
        self.cb_nivel.setStyleSheet(f"""
            QComboBox {{
                background-color: {bg};
                color: {fg_p};
                border: 1px solid {bg_t};
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 10px;
            }}
        """)
        self.cb_nivel.currentIndexChanged.connect(self.filtrar_eventos)
        f_box.addWidget(self.cb_nivel)
        layout.addLayout(f_box)

        # Lista de Notificaciones
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg};
                border: 1px solid {bg_t};
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid rgba(255,255,255,0.04);
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: rgba(255,255,255,0.05);
            }}
        """)
        layout.addWidget(self.list_widget, 1)

        # Footer con botón Cerrar
        b_box = QHBoxLayout()
        self.lbl_count = QLabel("0 eventos registrados")
        self.lbl_count.setStyleSheet(f"color: {fg_s}; font-size: 10px;")
        b_box.addWidget(self.lbl_count)
        b_box.addStretch()

        btn_close = QPushButton("Cerrar")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_t};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 16px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {acento};
            }}
        """)
        btn_close.clicked.connect(self.accept)
        b_box.addWidget(btn_close)
        layout.addLayout(b_box)

        self.todos_los_eventos = []

    def cargar_eventos(self):
        self.todos_los_eventos = []
        # Buscar en archivo de log de hoy
        if self.ruta_usuario:
            hoy = datetime.date.today().isoformat()
            log_file = Path(self.ruta_usuario) / "logs" / f"{hoy}.json"
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    item = json.loads(line)
                                    self.todos_los_eventos.append(item)
                                except Exception:
                                    pass
                except Exception:
                    pass

        # Invertir para mostrar lo más reciente arriba
        self.todos_los_eventos.reverse()
        self.filtrar_eventos()

    def filtrar_eventos(self):
        self.list_widget.clear()
        query = self.txt_filter.text().strip().lower()
        nivel = self.cb_nivel.currentText()

        mostrados = 0
        for ev in self.todos_los_eventos:
            ev_nivel = ev.get("nivel", "INFO").upper()
            ev_mod = ev.get("modulo", "Sistema")
            ev_msg = ev.get("mensaje", "")
            ev_time = ev.get("timestamp", "")
            if "T" in ev_time:
                ev_time = ev_time.split("T")[-1].split(".")[0]

            if nivel != "Todos los niveles" and ev_nivel != nivel:
                continue

            if query and (query not in ev_msg.lower() and query not in ev_mod.lower()):
                continue

            color_tag = "#34D399" if ev_nivel == "INFO" else ("#FBBF24" if ev_nivel == "WARNING" else "#F87171")
            icon_tag = "ℹ️" if ev_nivel == "INFO" else ("⚠️" if ev_nivel == "WARNING" else "❌")

            txt_item = f"[{ev_time}]  {icon_tag} [{ev_mod}]  {ev_msg}"
            item = QListWidgetItem(txt_item)
            item.setForeground(QColor(self.colores.get("fg_principal", "#FFFFFF")))
            self.list_widget.addItem(item)
            mostrados += 1

        self.lbl_count.setText(f"{mostrados} eventos mostrados de {len(self.todos_los_eventos)}")

