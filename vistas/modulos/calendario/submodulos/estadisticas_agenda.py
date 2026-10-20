import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGridLayout, QProgressBar, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class StatMetricCard(QFrame):
    """Tarjeta de métrica estadística"""
    def __init__(self, titulo, valor, icono, color_acento, colores, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        
        hdr = QHBoxLayout()
        lbl_ico = QLabel(icono)
        lbl_ico.setFont(QFont("Segoe UI" if platform.system() == "Windows" else "Inter", 16))
        hdr.addWidget(lbl_ico)

        lbl_val = QLabel(str(valor))
        lbl_val.setFont(QFont("Segoe UI" if platform.system() == "Windows" else "Inter", 18, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {color_acento};")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        hdr.addWidget(lbl_val)
        layout.addLayout(hdr)

        lbl_t = QLabel(titulo)
        lbl_t.setFont(QFont("Segoe UI" if platform.system() == "Windows" else "Inter", 9))
        lbl_t.setStyleSheet("color: rgba(255,255,255,0.7);")
        layout.addWidget(lbl_t)


class EstadisticasAgenda(QWidget):
    """Submódulo 3: Análisis & Estadísticas de Productividad y Agenda"""
    def __init__(self, parent, context, manager, colores):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("📊 ANÁLISIS & ESTADÍSTICAS DE AGENDA")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        btn_export_ics = QPushButton("📅 Exportar iCalendar (.ics)")
        btn_export_ics.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export_ics.setStyleSheet(f"background-color: {self.colores['acento']}; color: white; padding: 6px 14px; border-radius: 6px; font-weight: bold;")
        btn_export_ics.clicked.connect(self._exportar_ics)
        hdr.addWidget(btn_export_ics)

        btn_export_csv = QPushButton("📊 Exportar CSV (.csv)")
        btn_export_csv.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export_csv.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white; padding: 6px 14px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        btn_export_csv.clicked.connect(self._exportar_csv)
        hdr.addWidget(btn_export_csv)

        layout.addLayout(hdr)

        # Grid de Tarjetas de Métricas (2x2)
        grid_lay = QGridLayout()
        grid_lay.setSpacing(12)

        stats = self.manager.get_estadisticas_agenda()

        self.card_total = StatMetricCard("Total de Eventos Registrados", stats['total_eventos'], "📌", self.colores['acento'], self.colores)
        self.card_anuales = StatMetricCard("Eventos Anuales / Cumpleaños", stats['eventos_anuales'], "🎉", "#34D399", self.colores)
        self.card_objs = StatMetricCard("Objetivos Cumplidos del Año", f"{stats['objetivos_cumplidos']}/{stats['total_objetivos']}", "🎯", "#FBBF24", self.colores)
        self.card_pct = StatMetricCard("Tasa de Cumplimiento de Objetivos", f"{stats['porcentaje_objetivos']}%", "📈", "#60A5FA", self.colores)

        grid_lay.addWidget(self.card_total, 0, 0)
        grid_lay.addWidget(self.card_anuales, 0, 1)
        grid_lay.addWidget(self.card_objs, 1, 0)
        grid_lay.addWidget(self.card_pct, 1, 1)

        layout.addLayout(grid_lay)

        # Marco de Desglose por Categorías
        cat_frame = QFrame()
        cat_frame.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06);")
        cat_lay = QVBoxLayout(cat_frame)
        cat_lay.setContentsMargins(15, 15, 15, 15)
        cat_lay.setSpacing(10)

        lbl_cat_t = QLabel("🏷️ DISTRIBUCIÓN POR CATEGORÍAS")
        lbl_cat_t.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_cat_t.setStyleSheet("color: white;")
        cat_lay.addWidget(lbl_cat_t)

        self.cat_bars_container = QVBoxLayout()
        self.cat_bars_container.setSpacing(8)
        cat_lay.addLayout(self.cat_bars_container)

        layout.addWidget(cat_frame, 1)

        self.refrescar()

    def refrescar(self):
        stats = self.manager.get_estadisticas_agenda()
        
        # Actualizar valores de las tarjetas
        self.card_total.findChildren(QLabel)[1].setText(str(stats['total_eventos']))
        self.card_anuales.findChildren(QLabel)[1].setText(str(stats['eventos_anuales']))
        self.card_objs.findChildren(QLabel)[1].setText(f"{stats['objetivos_cumplidos']}/{stats['total_objetivos']}")
        self.card_pct.findChildren(QLabel)[1].setText(f"{stats['porcentaje_objetivos']}%")

        # Limpiar barras anteriores
        while self.cat_bars_container.count() > 0:
            item = self.cat_bars_container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget(): child.widget().deleteLater()

        tot = stats['total_eventos'] or 1
        for cat, cant in stats['por_categoria'].items():
            color = self.manager.categorias.get(cat, "#AAB0B8")
            pct = int((cant / tot * 100))

            row = QHBoxLayout()
            lbl_cat_name = QLabel(f"{cat} ({cant})")
            lbl_cat_name.setFont(QFont(self.font_family, 9))
            lbl_cat_name.setFixedWidth(120)
            lbl_cat_name.setStyleSheet("color: white;")
            row.addWidget(lbl_cat_name)

            pbar = QProgressBar()
            pbar.setFixedHeight(10)
            pbar.setValue(pct)
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {self.colores['bg_terciario']};
                    border-radius: 5px; text-align: center; color: transparent;
                }}
                QProgressBar::chunk {{
                    background-color: {color}; border-radius: 5px;
                }}
            """)
            row.addWidget(pbar, 1)

            lbl_pct_txt = QLabel(f"{pct}%")
            lbl_pct_txt.setFont(QFont(self.font_family, 9))
            lbl_pct_txt.setFixedWidth(40)
            lbl_pct_txt.setStyleSheet("color: rgba(255,255,255,0.7); text-align: right;")
            row.addWidget(lbl_pct_txt)

            self.cat_bars_container.addLayout(row)

    def _exportar_ics(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Agenda iCalendar", "agenda.ics", "iCalendar (*.ics)")
        if path:
            try:
                self.manager.exportar_ical(path)
                QMessageBox.information(self, "Exportación Exitosa", "Agenda exportada correctamente en formato iCalendar (.ics).")
            except Exception as e:
                QMessageBox.critical(self, "Error Exportando", f"No se pudo exportar: {e}")

    def _exportar_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Agenda CSV", "agenda.csv", "Archivos CSV (*.csv)")
        if path:
            try:
                self.manager.exportar_csv(path)
                QMessageBox.information(self, "Exportación Exitosa", "Agenda exportada correctamente en formato CSV (.csv).")
            except Exception as e:
                QMessageBox.critical(self, "Error Exportando", f"No se pudo exportar: {e}")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.refrescar()
