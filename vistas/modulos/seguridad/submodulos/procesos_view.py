"""
procesos_view.py - Monitor de procesos del sistema para el módulo de Seguridad
Permite listar, buscar, filtrar y finalizar procesos del sistema operativo
con visualización de uso de CPU y memoria RAM.
"""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class ProcesosView(QWidget):
    """Panel de monitoreo de tareas y procesos del sistema operativo."""

    volver_solicitado = pyqtSignal()

    def __init__(self, parent=None, colores: Optional[Dict[str, str]] = None, font_family: str = "Segoe UI"):
        super().__init__(parent)
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "error": "#F87171", "exito": "#34D399", "advertencia": "#FBBF24"
        }
        self.font_family = font_family
        self._procesos_data: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        # Encabezado
        hdr = QHBoxLayout()
        lbl_t = QLabel("🖥️ PROCESOS DEL SISTEMA")
        lbl_t.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_t.setStyleSheet("color: white; border: none; background: transparent;")
        hdr.addWidget(lbl_t)
        hdr.addStretch()

        self.btn_volver = QPushButton("← Volver a la Bóveda")
        self.btn_volver.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_volver.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_volver.setStyleSheet(f"background: {self.colores['acento']}; color: white; padding: 6px 14px; border-radius: 6px; border: none;")
        self.btn_volver.clicked.connect(self.volver_solicitado.emit)
        hdr.addWidget(self.btn_volver)

        self.btn_refrescar = QPushButton("🔄 Refrescar")
        self.btn_refrescar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refrescar.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_refrescar.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; padding: 6px 14px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);")
        self.btn_refrescar.clicked.connect(self.cargar_procesos)
        hdr.addWidget(self.btn_refrescar)
        lay.addLayout(hdr)

        # Barra de estadísticas rápidas
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        s_lay = QHBoxLayout(self.stats_frame)
        s_lay.setContentsMargins(14, 8, 14, 8)

        self.lbl_total_proc = QLabel("Total Procesos: 0")
        self.lbl_total_proc.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_total_proc.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        s_lay.addWidget(self.lbl_total_proc)

        self.lbl_mem_total = QLabel("RAM Monitoreada: 0 MB")
        self.lbl_mem_total.setFont(QFont(self.font_family, 9))
        self.lbl_mem_total.setStyleSheet("color: white; border: none; background: transparent;")
        s_lay.addWidget(self.lbl_mem_total)
        s_lay.addStretch()
        lay.addWidget(self.stats_frame)

        # Buscador de procesos
        self.txt_buscar_proc = QLineEdit()
        self.txt_buscar_proc.setPlaceholderText("🔍 Buscar proceso por nombre o PID...")
        self.txt_buscar_proc.setFont(QFont(self.font_family, 9))
        self.txt_buscar_proc.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_secundario']};
                color: white;
                border-radius: 6px;
                padding: 8px 12px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            QLineEdit:focus {{
                border-color: {self.colores['acento']};
            }}
        """)
        self.txt_buscar_proc.textChanged.connect(self.filtrar_procesos)
        lay.addWidget(self.txt_buscar_proc)

        # Tabla de procesos
        self.tabla_procesos = QTableWidget(0, 4)
        self.tabla_procesos.setHorizontalHeaderLabels(["PID", "Nombre del Proceso", "CPU %", "Memoria (MB)"])
        self.tabla_procesos.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_procesos.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_procesos.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_procesos.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_procesos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_procesos.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_procesos.setAlternatingRowColors(True)
        self.tabla_procesos.verticalHeader().setVisible(False)
        self.aplicar_estilos_tabla()
        lay.addWidget(self.tabla_procesos, 1)

        # Botón de acción
        self.btn_terminar = QPushButton("🛑 Terminar Proceso Seleccionado")
        self.btn_terminar.setFixedHeight(36)
        self.btn_terminar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_terminar.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_terminar.setStyleSheet(f"background: rgba(248,113,113,0.15); color: {self.colores['error']}; border: 1px solid rgba(248,113,113,0.3); border-radius: 6px; padding: 6px;")
        self.btn_terminar.clicked.connect(self.terminar_proceso)
        lay.addWidget(self.btn_terminar)

    def aplicar_estilos_tabla(self):
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        self.tabla_procesos.setStyleSheet(f"""
            QTableWidget {{
                background-color: {bg_sec};
                alternate-background-color: {bg_ter};
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.08);
                gridline-color: rgba(255,255,255,0.06);
                border-radius: 8px;
            }}
            QHeaderView::section {{
                background-color: {bg_ter};
                color: {acento};
                padding: 8px 10px;
                border: none;
                border-bottom: 2px solid {acento};
                font-weight: bold;
            }}
            QTableWidget::item {{
                color: #FFFFFF;
                padding: 6px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: rgba(99,102,241,0.35);
                color: #FFFFFF;
            }}
        """)

    def cargar_procesos(self):
        """Lee los procesos activos del sistema usando psutil y actualiza la tabla."""
        try:
            import psutil
            procesos = []
            mem_acumulada = 0.0
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
                try:
                    info = p.info
                    mem_mb = round(info["memory_info"].rss / 1024 / 1024, 1) if info.get("memory_info") else 0.0
                    mem_acumulada += mem_mb
                    procesos.append({
                        "pid": info["pid"],
                        "nombre": info["name"] or "",
                        "cpu": info["cpu_percent"] or 0.0,
                        "mem": mem_mb
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            procesos.sort(key=lambda x: x["mem"], reverse=True)
            self._procesos_data = procesos
            self.lbl_total_proc.setText(f"Total Procesos: {len(procesos)}")
            self.lbl_mem_total.setText(f"RAM Procesos: {round(mem_acumulada, 1)} MB")
            self.filtrar_procesos(self.txt_buscar_proc.text())
        except ImportError:
            QMessageBox.warning(
                self, "psutil requerido",
                "El monitor de procesos requiere la librería 'psutil'.\nPuedes instalarla ejecutando:\npip install psutil"
            )

    def filtrar_procesos(self, query: str = ""):
        """Filtra la lista de procesos por nombre o PID en tiempo real."""
        query = query.lower().strip()
        if query:
            filtrados = [
                p for p in self._procesos_data
                if query in p["nombre"].lower() or query in str(p["pid"])
            ]
        else:
            filtrados = self._procesos_data

        self.tabla_procesos.setRowCount(len(filtrados))
        for row, p in enumerate(filtrados):
            pid_item = QTableWidgetItem(str(p["pid"]))
            pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pid_item.setForeground(QColor("#AAB0B8"))
            self.tabla_procesos.setItem(row, 0, pid_item)

            name_item = QTableWidgetItem(p["nombre"])
            name_item.setForeground(QColor("#FFFFFF"))
            self.tabla_procesos.setItem(row, 1, name_item)

            cpu_val = p.get("cpu", 0.0)
            cpu_item = QTableWidgetItem(f"{cpu_val:.1f}%")
            cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if cpu_val > 50:
                cpu_item.setForeground(QColor("#F87171"))
            elif cpu_val > 15:
                cpu_item.setForeground(QColor("#FBBF24"))
            else:
                cpu_item.setForeground(QColor("#34D399"))
            self.tabla_procesos.setItem(row, 2, cpu_item)

            mem_item = QTableWidgetItem(f"{p['mem']:.1f} MB")
            mem_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            mem_item.setForeground(QColor("#60A5FA"))
            self.tabla_procesos.setItem(row, 3, mem_item)

    def terminar_proceso(self):
        """Solicita confirmación y termina el proceso seleccionado."""
        row = self.tabla_procesos.currentRow()
        if row < 0:
            QMessageBox.information(self, "Seleccionar", "Por favor selecciona un proceso de la tabla para terminar.")
            return

        pid_item = self.tabla_procesos.item(row, 0)
        name_item = self.tabla_procesos.item(row, 1)
        if not pid_item:
            return

        pid = int(pid_item.text())
        name = name_item.text() if name_item else str(pid)

        resp = QMessageBox.question(
            self, "Terminar Proceso",
            f"¿Estás seguro de que deseas terminar el proceso '{name}' (PID: {pid})?\n"
            "⚠️ Esta acción forzará el cierre inmediato del proceso.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            try:
                import psutil
                psutil.Process(pid).terminate()
                self.cargar_procesos()
            except Exception as e:
                QMessageBox.critical(self, "Error al Terminar", f"No se pudo terminar el proceso:\n{e}")

    def actualizar_tema(self, colores: Dict[str, str]):
        """Actualiza los estilos con los nuevos colores de la aplicación."""
        self.colores = colores
        self.btn_volver.setStyleSheet(f"background: {colores['acento']}; color: white; padding: 6px 14px; border-radius: 6px; border: none;")
        self.btn_refrescar.setStyleSheet(f"background: {colores['bg_secundario']}; color: white; padding: 6px 14px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);")
        self.stats_frame.setStyleSheet(f"background: {colores['bg_secundario']}; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        self.lbl_total_proc.setStyleSheet(f"color: {colores['acento']}; border: none; background: transparent;")
        self.aplicar_estilos_tabla()
