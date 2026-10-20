import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class CronometroSubmodule(QWidget):
    """Submódulo 2: Cronómetro de Precisión & Registro de Vueltas (Laps)"""
    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("⏱️ CRONÓMETRO DE PRECISIÓN")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        btn_export = QPushButton("💾 Exportar Vueltas")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white; padding: 6px 14px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        btn_export.clicked.connect(self._exportar_vueltas)
        hdr.addWidget(btn_export)

        layout.addLayout(hdr)

        # Marco de Display Digital
        display_frame = QFrame()
        display_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }}
        """)
        disp_lay = QVBoxLayout(display_frame)
        disp_lay.setContentsMargins(20, 25, 20, 25)
        disp_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_crono_digits = QLabel("00:00:00.00")
        self.lbl_crono_digits.setFont(QFont(self.mono_font, 48, QFont.Weight.Bold))
        self.lbl_crono_digits.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        self.lbl_crono_digits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disp_lay.addWidget(self.lbl_crono_digits)

        # Botones de Control
        ctrl_lay = QHBoxLayout()
        ctrl_lay.setSpacing(12)

        self.btn_crono_start = QPushButton("▶ Iniciar")
        self.btn_crono_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_crono_start.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_crono_start.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 10px 24px; border-radius: 8px; border: none;")
        self.btn_crono_start.clicked.connect(self._on_start_pause_click)
        ctrl_lay.addWidget(self.btn_crono_start)

        self.btn_crono_lap = QPushButton("🚩 Vuelta")
        self.btn_crono_lap.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_crono_lap.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_crono_lap.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; padding: 10px 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);")
        self.btn_crono_lap.clicked.connect(self._on_lap_click)
        ctrl_lay.addWidget(self.btn_crono_lap)

        self.btn_crono_reset = QPushButton("🔄 Reiniciar")
        self.btn_crono_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_crono_reset.setFont(QFont(self.font_family, 10))
        self.btn_crono_reset.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; padding: 10px 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);")
        self.btn_crono_reset.clicked.connect(self._on_reset_click)
        ctrl_lay.addWidget(self.btn_crono_reset)

        disp_lay.addLayout(ctrl_lay)
        layout.addWidget(display_frame)

        # Tabla de Vueltas (Laps)
        self.table_laps = QTableWidget()
        self.table_laps.setColumnCount(3)
        self.table_laps.setHorizontalHeaderLabels(["Nº Vuelta", "Tiempo de Vuelta", "Tiempo Total"])
        self.table_laps.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_laps.setFont(QFont(self.mono_font, 9))
        self.table_laps.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colores['bg_secundario']};
                color: white; border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px; gridline-color: rgba(255,255,255,0.05);
            }}
            QHeaderView::section {{
                background-color: {self.colores['bg_terciario']};
                color: white; font-weight: bold; border: none; padding: 6px;
            }}
        """)
        layout.addWidget(self.table_laps, 1)

    def actualizar_crono_ui(self, t_seg):
        h = int(t_seg // 3600)
        m = int((t_seg % 3600) // 60)
        s = int(t_seg % 60)
        cs = int((t_seg * 100) % 100)
        self.lbl_crono_digits.setText(f"{h:02d}:{m:02d}:{s:02d}.{cs:02d}")

    def _on_start_pause_click(self):
        if self.manager.crono_running:
            self.callbacks["crono_pause"]()
            self.btn_crono_start.setText("▶ Reanudar")
        else:
            self.callbacks["crono_start"]()
            self.btn_crono_start.setText("⏸️ Pausar")

    def _on_lap_click(self):
        if self.callbacks["crono_lap"]:
            self.callbacks["crono_lap"]()
            self.refrescar_tabla_vueltas()

    def _on_reset_click(self):
        self.callbacks["crono_reset"]()
        self.btn_crono_start.setText("▶ Iniciar")
        self.lbl_crono_digits.setText("00:00:00.00")
        self.table_laps.setRowCount(0)

    def refrescar_tabla_vueltas(self):
        laps = self.manager.laps
        self.table_laps.setRowCount(len(laps))
        
        last_t = 0
        for i, total_t in enumerate(laps):
            lap_t = total_t - last_t
            last_t = total_t

            item_num = QTableWidgetItem(f"Vuelta #{i+1}")
            item_lap = QTableWidgetItem(self._format_time(lap_t))
            item_total = QTableWidgetItem(self._format_time(total_t))

            item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_lap.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_total.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table_laps.setItem(i, 0, item_num)
            self.table_laps.setItem(i, 1, item_lap)
            self.table_laps.setItem(i, 2, item_total)

    def _format_time(self, t_seg):
        h = int(t_seg // 3600)
        m = int((t_seg % 3600) // 60)
        s = int(t_seg % 60)
        cs = int((t_seg * 100) % 100)
        return f"{h:02d}:{m:02d}:{s:02d}.{cs:02d}"

    def _exportar_vueltas(self):
        if not self.manager.laps:
            QMessageBox.information(self, "Sin Datos", "No hay vueltas registradas para exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Exportar Registro de Vueltas", "vueltas_cronometro.csv", "Archivos CSV (*.csv);;Archivos de Texto (*.txt)")
        if path:
            try:
                lines = ["Nº Vuelta,Tiempo Vuelta,Tiempo Total\n"]
                last_t = 0
                for i, total_t in enumerate(self.manager.laps):
                    lap_t = total_t - last_t
                    last_t = total_t
                    lines.append(f"Vuelta #{i+1},{self._format_time(lap_t)},{self._format_time(total_t)}\n")
                Path(path).write_text("".join(lines), encoding="utf-8")
                QMessageBox.information(self, "Exportación Exitosa", "Tiempos exportados correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error Exportando", f"No se pudo exportar: {e}")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.lbl_crono_digits.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        self.btn_crono_start.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 10px 24px; border-radius: 8px; border: none;")
