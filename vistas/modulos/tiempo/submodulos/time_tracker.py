import os
import time
import platform
import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, 
    QLineEdit, QComboBox, QFileDialog, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

class TimeTrackerSubmodule(QWidget):
    """Submódulo 6: Registro de Tiempo y Horas Trabajadas por Proyecto (Time Tracker)"""
    def __init__(self, parent, context, manager, colores):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"

        self.inicializar_ui()
        self.refrescar_estadisticas()
        self.refrescar_tabla()

        # Si había una tarea activa guardada, reanudar visualización
        if getattr(self.manager, "tracker_activo", None):
            self._restaurar_tarea_activa()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Header y botón exportar
        hdr = QHBoxLayout()
        lbl_title = QLabel("📊 REGISTRO DE HORAS Y ACTIVIDADES (TIME TRACKER)")
        lbl_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        btn_export = QPushButton("💾 Exportar Reporte")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_secundario']};
                color: white; border-radius: 6px; padding: 6px 14px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.12); }}
        """)
        btn_export.clicked.connect(self._exportar_csv)
        hdr.addWidget(btn_export)

        layout.addLayout(hdr)

        # =========================================================================
        # PANEL CENTRAL DE CONTROL: INICIAR / DETENER TAREA
        # =========================================================================
        tracker_panel = QFrame()
        tracker_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }}
        """)
        t_lay = QVBoxLayout(tracker_panel)
        t_lay.setContentsMargins(15, 12, 15, 12)
        t_lay.setSpacing(10)

        # Fila de Inputs: Proyecto, Descripción y Botón
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        lbl_proj = QLabel("Proyecto:")
        lbl_proj.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_proj.setStyleSheet("color: rgba(255,255,255,0.7);")
        input_row.addWidget(lbl_proj)

        self.combo_proyecto = QComboBox()
        self.combo_proyecto.setEditable(True)
        self.combo_proyecto.setFont(QFont(self.font_family, 9))
        self.combo_proyecto.setFixedWidth(160)
        self.combo_proyecto.addItems(["Desarrollo", "Estudio", "Diseño", "Reunión", "Investigación", "General"])
        self.combo_proyecto.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 4px 8px;
            }}
        """)
        input_row.addWidget(self.combo_proyecto)

        lbl_desc = QLabel("Actividad:")
        lbl_desc.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_desc.setStyleSheet("color: rgba(255,255,255,0.7);")
        input_row.addWidget(lbl_desc)

        self.txt_descripcion = QLineEdit()
        self.txt_descripcion.setPlaceholderText("¿En qué estás trabajando ahora?")
        self.txt_descripcion.setFont(QFont(self.font_family, 9))
        self.txt_descripcion.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 4px 10px;
            }}
        """)
        input_row.addWidget(self.txt_descripcion, 1)

        # Display Digital en vivo
        self.lbl_live_time = QLabel("00:00:00")
        self.lbl_live_time.setFont(QFont(self.mono_font, 16, QFont.Weight.Bold))
        self.lbl_live_time.setStyleSheet(f"color: {self.colores['acento']}; padding: 0 8px;")
        input_row.addWidget(self.lbl_live_time)

        # Botón Iniciar / Detener
        self.btn_toggle_tracker = QPushButton("▶ Iniciar Tarea")
        self.btn_toggle_tracker.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_tracker.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_toggle_tracker.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white; border-radius: 6px; padding: 7px 18px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores.get('acento_hover', self.colores['acento'])}; }}
        """)
        self.btn_toggle_tracker.clicked.connect(self._toggle_tracker)
        input_row.addWidget(self.btn_toggle_tracker)

        t_lay.addLayout(input_row)

        layout.addWidget(tracker_panel)

        # =========================================================================
        # CARDS DE RESUMEN Y MÉTRICAS
        # =========================================================================
        stats_lay = QHBoxLayout()
        stats_lay.setSpacing(10)

        self.card_hoy = self._crear_stat_card("⏱️ Horas Hoy", "0h 0m", self.colores['acento'])
        self.card_total = self._crear_stat_card("📈 Horas Totales", "0h 0m", "#10B981")
        self.card_top_proj = self._crear_stat_card("🏷️ Proyecto Principal", "--", "#F59E0B")

        stats_lay.addWidget(self.card_hoy)
        stats_lay.addWidget(self.card_total)
        stats_lay.addWidget(self.card_top_proj)

        layout.addLayout(stats_lay)

        # =========================================================================
        # TABLA DE SESIONES REGISTRADAS
        # =========================================================================
        self.table_tracker = QTableWidget()
        self.table_tracker.setColumnCount(5)
        self.table_tracker.setHorizontalHeaderLabels(["Proyecto", "Actividad / Nota", "Inicio", "Fin", "Duración"])
        self.table_tracker.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tracker.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_tracker.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tracker.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tracker.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tracker.setFont(QFont(self.font_family, 9))
        self.table_tracker.setStyleSheet(f"""
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
        layout.addWidget(self.table_tracker, 1)

    def _crear_stat_card(self, titulo, valor_inicial, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-left: 3px solid {color};
                border-radius: 8px;
            }}
        """)
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(12, 8, 12, 8)
        c_lay.setSpacing(2)

        lbl_t = QLabel(titulo)
        lbl_t.setFont(QFont(self.font_family, 8))
        lbl_t.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        c_lay.addWidget(lbl_t)

        lbl_v = QLabel(valor_inicial)
        lbl_v.setObjectName("val")
        lbl_v.setFont(QFont(self.mono_font, 14, QFont.Weight.Bold))
        lbl_v.setStyleSheet(f"color: {color};")
        c_lay.addWidget(lbl_v)

        return card

    def _toggle_tracker(self):
        if getattr(self.manager, "tracker_activo", None):
            # Detener tarea activa
            rec = self.manager.detener_tarea_tracker()
            self.btn_toggle_tracker.setText("▶ Iniciar Tarea")
            self.btn_toggle_tracker.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colores['acento']};
                    color: white; border-radius: 6px; padding: 7px 18px; border: none;
                }}
            """)
            self.lbl_live_time.setText("00:00:00")
            self.txt_descripcion.clear()
            self.refrescar_tabla()
            self.refrescar_estadisticas()
        else:
            # Iniciar nueva tarea
            proj = self.combo_proyecto.currentText().strip() or "General"
            desc = self.txt_descripcion.text().strip()
            self.manager.iniciar_tarea_tracker(proj, desc)
            self._restaurar_tarea_activa()

    def _restaurar_tarea_activa(self):
        self.btn_toggle_tracker.setText("⏹ Detener Tarea")
        self.btn_toggle_tracker.setStyleSheet("""
            QPushButton {{
                background-color: #EF4444;
                color: white; border-radius: 6px; padding: 7px 18px; border: none;
            }}
            QPushButton:hover {{ background-color: #DC2626; }}
        """)
        act = getattr(self.manager, "tracker_activo", {})
        if act:
            idx = self.combo_proyecto.findText(act.get("proyecto", ""))
            if idx >= 0:
                self.combo_proyecto.setCurrentIndex(idx)
            else:
                self.combo_proyecto.setCurrentText(act.get("proyecto", "General"))
            self.txt_descripcion.setText(act.get("descripcion", ""))

    def tick_100ms(self):
        """Llamado desde el loop de 100ms de TabTiempo para actualizar el contador en vivo"""
        act = getattr(self.manager, "tracker_activo", None)
        if act:
            inicio_ts = act.get("inicio_ts", time.time())
            elapsed = max(0, int(time.time() - inicio_ts))
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60
            self.lbl_live_time.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def refrescar_estadisticas(self):
        stats = self.manager.obtener_estadisticas_tracker()
        
        # Horas Hoy
        hoy_s = stats.get("total_hoy_seg", 0)
        h_hoy, m_hoy = hoy_s // 3600, (hoy_s % 3600) // 60
        lbl_hoy = self.card_hoy.findChild(QLabel, "val")
        if lbl_hoy: lbl_hoy.setText(f"{h_hoy}h {m_hoy}m")

        # Horas Totales
        tot_s = stats.get("total_general_seg", 0)
        h_tot, m_tot = tot_s // 3600, (tot_s % 3600) // 60
        lbl_tot = self.card_total.findChild(QLabel, "val")
        if lbl_tot: lbl_tot.setText(f"{h_tot}h {m_tot}m")

        # Proyecto Principal
        por_proj = stats.get("por_proyecto", {})
        top_name = "--"
        if por_proj:
            top_name = max(por_proj.items(), key=lambda x: x[1])[0]
        lbl_top = self.card_top_proj.findChild(QLabel, "val")
        if lbl_top: lbl_top.setText(top_name)

    def refrescar_tabla(self):
        records = getattr(self.manager, "tracker_records", [])
        self.table_tracker.setRowCount(len(records))

        for i, r in enumerate(records):
            item_proj = QTableWidgetItem(f"📁 {r.get('proyecto', 'General')}")
            item_desc = QTableWidgetItem(r.get("descripcion", "--"))
            item_ini = QTableWidgetItem(r.get("inicio_str", ""))
            item_fin = QTableWidgetItem(r.get("fin_str", ""))
            
            d_seg = r.get("duracion_seg", 0)
            h = d_seg // 3600
            m = (d_seg % 3600) // 60
            s = d_seg % 60
            item_dur = QTableWidgetItem(f"{h:02d}:{m:02d}:{s:02d}")

            item_proj.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            item_dur.setFont(QFont(self.mono_font, 9, QFont.Weight.Bold))
            item_dur.setForeground(QColor(self.colores['acento']))

            self.table_tracker.setItem(i, 0, item_proj)
            self.table_tracker.setItem(i, 1, item_desc)
            self.table_tracker.setItem(i, 2, item_ini)
            self.table_tracker.setItem(i, 3, item_fin)
            self.table_tracker.setItem(i, 4, item_dur)

    def _exportar_csv(self):
        records = getattr(self.manager, "tracker_records", [])
        if not records:
            QMessageBox.information(self, "Sin Registros", "No hay registros de tiempo para exportar.")
            return

        suggested = str(Path.home() / "registro_tiempo.csv")
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Registro de Tiempo", suggested, "Archivos CSV (*.csv);;Archivos de Texto (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("Proyecto,Descripcion,Inicio,Fin,Duracion_Segundos,Duracion_Formateada\n")
                    for r in records:
                        d_seg = r.get("duracion_seg", 0)
                        h = d_seg // 3600
                        m = (d_seg % 3600) // 60
                        s = d_seg % 60
                        dur_fmt = f"{h:02d}:{m:02d}:{s:02d}"
                        f.write(f'"{r.get("proyecto","")}","{r.get("descripcion","")}","{r.get("inicio_str","")}","{r.get("fin_str","")}",{d_seg},"{dur_fmt}"\n')
                QMessageBox.information(self, "Exportación Exitosa", f"Se exportaron {len(records)} registros correctamente a:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error al Exportar", f"No se pudo guardar el archivo:\n{e}")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.refrescar_estadisticas()
        self.refrescar_tabla()
