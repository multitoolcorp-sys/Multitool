import os
import sys
import time
import json
import shutil
import hashlib
import zipfile
import psutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QCheckBox,
    QFrame, QTextEdit, QScrollArea, QTabWidget, QMessageBox, QListWidget,
    QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from ..utils.antivirus_scanner import ScanThread


class TabAntivirus(QWidget):
    def __init__(self, parent, colores, callbacks, context=None):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.context = context

        # Rutas de base de datos y carpeta de cuarentena basadas en la cuenta
        if self.context and hasattr(self.context, 'ruta_usuario') and self.context.ruta_usuario:
            self.user_dir = Path(self.context.ruta_usuario)
        else:
            self.user_dir = Path(os.getcwd()) / "cuentas" / "default"
        
        self.quarantine_dir = self.user_dir / "quarantine_files"
        self.quarantine_db = self.user_dir / "antivirus_quarantine.json"
        self.config_path = self.user_dir / "antivirus_config.json"
        
        # Crear directorios si no existen
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        self.exclusiones = []
        self.amenazas_detectadas = []
        self.scan_thread = None

        # Configuración por defecto
        self.real_time_protection = False
        self.heuristic_enabled = True
        self.scan_zip_enabled = True

        self.cargar_configuraciones()
        self.setup_ui()
        self.cargar_cuarentena_ui()

    def cargar_configuraciones(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.real_time_protection = cfg.get("real_time", False)
                    self.heuristic_enabled = cfg.get("heuristic", True)
                    self.scan_zip_enabled = cfg.get("scan_zip", True)
                    self.exclusiones = cfg.get("exclusions", [])
        except Exception:
            pass

    def guardar_configuraciones(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "real_time": self.real_time_protection,
                    "heuristic": self.heuristic_enabled,
                    "scan_zip": self.scan_zip_enabled,
                    "exclusions": self.exclusiones
                }, f, indent=4)
        except Exception:
            pass

    def setup_ui(self):
        # Layout principal
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(15, 15, 15, 15)
        self.layout_principal.setSpacing(10)

        # Tabs internos: Dashboard, Cuarentena, Configuración
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid rgba(255,255,255,0.05);
                background: {self.colores['bg_principal']};
                border-radius: 10px;
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: {self.colores['fg_secundario']};
                padding: 10px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:hover {{
                background: {self.colores['bg_terciario']};
            }}
            QTabBar::tab:selected {{
                background: {self.colores['bg_principal']};
                color: {self.colores['acento']};
                border-bottom: 2px solid {self.colores['acento']};
                font-weight: bold;
            }}
        """)

        # ── 1. Tab de Dashboard y Escaneo ──
        self.tab_scan = QWidget()
        layout_scan = QVBoxLayout(self.tab_scan)
        layout_scan.setContentsMargins(15, 15, 15, 15)
        layout_scan.setSpacing(15)

        # Banner de Estado
        self.frame_estado = QFrame()
        self.frame_estado.setFixedHeight(90)
        self.frame_estado.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.colores['bg_secundario']}, stop:1 rgba(34, 197, 94, 0.08));
                border: 1px solid rgba(34, 197, 94, 0.2);
                border-radius: 10px;
            }}
        """)
        layout_estado = QHBoxLayout(self.frame_estado)
        layout_estado.setContentsMargins(20, 10, 20, 10)

        self.lbl_escudo = QLabel("🛡️")
        self.lbl_escudo.setFont(QFont("Segoe UI", 32))
        layout_estado.addWidget(self.lbl_escudo)

        layout_estado_texto = QVBoxLayout()
        layout_estado_texto.setSpacing(2)
        self.lbl_estado_titulo = QLabel("SISTEMA PROTEGIDO")
        self.lbl_estado_titulo.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_estado_titulo.setStyleSheet(f"color: {self.colores.get('exito', '#22c55e')}; letter-spacing: 1px;")

        self.lbl_estado_desc = QLabel("La protección está activa. No se han detectado amenazas.")
        self.lbl_estado_desc.setFont(QFont("Segoe UI", 9))
        self.lbl_estado_desc.setStyleSheet(f"color: {self.colores['fg_secundario']};")

        layout_estado_texto.addWidget(self.lbl_estado_titulo)
        layout_estado_texto.addWidget(self.lbl_estado_desc)
        layout_estado.addLayout(layout_estado_texto)
        layout_estado.addStretch()
        layout_scan.addWidget(self.frame_estado)

        # Botones de Acción de Escaneo
        layout_botones = QHBoxLayout()
        layout_botones.setSpacing(10)

        self.btn_quick = QPushButton("⚡  Análisis Rápido")
        self.btn_full = QPushButton("🌀  Análisis Completo")
        self.btn_custom = QPushButton("📂  Analizar Carpeta")
        self.btn_cancel = QPushButton("🛑  Cancelar")
        self.btn_cancel.setEnabled(False)

        estilo_btn = f"""
            QPushButton {{
                background: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
                padding: 12px 18px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {self.colores['acento']}22;
                border: 1px solid {self.colores['acento']};
            }}
            QPushButton:pressed {{
                background: {self.colores['acento']}44;
            }}
            QPushButton:disabled {{
                background: rgba(255,255,255,0.02);
                color: {self.colores['fg_secundario']}55;
                border: 1px solid rgba(255,255,255,0.02);
            }}
        """
        for btn in [self.btn_quick, self.btn_full, self.btn_custom, self.btn_cancel]:
            btn.setStyleSheet(estilo_btn)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout_botones.addWidget(btn)

        self.btn_cancel.setStyleSheet(self.btn_cancel.styleSheet().replace(
            f"QPushButton:hover {{ background: {self.colores['acento']}22; border: 1px solid {self.colores['acento']}; }}",
            f"QPushButton:hover {{ background: {self.colores['error']}22; border: 1px solid {self.colores['error']}; }}"
        ))

        self.btn_quick.clicked.connect(lambda: self.iniciar_escaneo("quick"))
        self.btn_full.clicked.connect(lambda: self.iniciar_escaneo("full"))
        self.btn_custom.clicked.connect(lambda: self.iniciar_escaneo("custom"))
        self.btn_cancel.clicked.connect(self.cancelar_escaneo)

        layout_scan.addLayout(layout_botones)

        # Panel de Progreso
        self.frame_progreso = QFrame()
        self.frame_progreso.setVisible(False)
        self.frame_progreso.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        layout_progreso_int = QVBoxLayout(self.frame_progreso)
        layout_progreso_int.setSpacing(8)

        self.lbl_progreso_status = QLabel("Analizando sistema...")
        self.lbl_progreso_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_progreso_status.setStyleSheet("color: white;")
        layout_progreso_int.addWidget(self.lbl_progreso_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {self.colores['bg_principal']};
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.colores['acento']}, stop:1 {self.colores.get('acento_hover', '#6366F1')});
                border-radius: 4px;
            }}
        """)
        layout_progreso_int.addWidget(self.progress_bar)

        # Stats
        layout_stats = QHBoxLayout()
        self.lbl_stat_files = QLabel("Archivos: 0")
        self.lbl_stat_threats = QLabel("Amenazas: 0")
        self.lbl_stat_speed = QLabel("Velocidad: 0 arch/s")
        self.lbl_stat_time = QLabel("Tiempo: 0s")

        estilo_stat = f"color: {self.colores['fg_secundario']}; font-size: 8.5pt;"
        for lbl in [self.lbl_stat_files, self.lbl_stat_threats, self.lbl_stat_speed, self.lbl_stat_time]:
            lbl.setStyleSheet(estilo_stat)
            layout_stats.addWidget(lbl)
        
        layout_progreso_int.addLayout(layout_stats)

        self.lbl_current_file = QLabel("Iniciando...")
        self.lbl_current_file.setFont(QFont("Consolas", 8))
        self.lbl_current_file.setStyleSheet(f"color: {self.colores['fg_secundario']}88;")
        self.lbl_current_file.setWordWrap(False)
        layout_progreso_int.addWidget(self.lbl_current_file)

        layout_scan.addWidget(self.frame_progreso)

        # Consola de Registros y Tabla de Amenazas (Splitter)
        self.splitter_analisis = QSplitter(Qt.Orientation.Vertical)
        self.splitter_analisis.setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.03); height: 1px; }")

        # Registro en tiempo real
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setPlaceholderText("Logs detallados del análisis aparecerán aquí...")
        self.log_console.setStyleSheet(f"""
            QTextEdit {{
                background: {self.colores['bg_principal']};
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 8px;
                color: #A0A0A0;
                font-family: Consolas, Monaco, monospace;
                font-size: 9pt;
                padding: 10px;
            }}
        """)
        self.splitter_analisis.addWidget(self.log_console)

        # Tabla de amenazas
        self.threat_table = QTableWidget(0, 5)
        self.threat_table.setHorizontalHeaderLabels(["Nombre", "Ruta del Archivo", "Tipo", "Riesgo", "Acción"])
        self.threat_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.threat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.threat_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.threat_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.threat_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.threat_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.threat_table.verticalHeader().setVisible(False)
        self.threat_table.verticalHeader().setDefaultSectionSize(65)
        self.threat_table.setShowGrid(False)
        self.threat_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.threat_table.setStyleSheet(f"""
            QTableWidget {{
                background: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 8px;
                outline: none;
            }}
            QHeaderView::section {{
                background: {self.colores['bg_principal']};
                color: {self.colores['fg_secundario']};
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.06);
                padding: 8px;
                font-weight: bold;
                font-size: 8.5pt;
            }}
            QTableWidget::item {{
                padding: 5px;
                border: none;
            }}
        """)
        self.splitter_analisis.addWidget(self.threat_table)
        self.splitter_analisis.setSizes([120, 150])

        layout_scan.addWidget(self.splitter_analisis)
        self.sub_tabs.addTab(self.tab_scan, "🛡️ Escáner")

        # ── 2. Tab de Cuarentena ──
        self.tab_quarantine = QWidget()
        layout_quar = QVBoxLayout(self.tab_quarantine)
        layout_quar.setContentsMargins(15, 15, 15, 15)
        layout_quar.setSpacing(10)

        lbl_quar_info = QLabel("Los archivos en cuarentena se guardan de forma encriptada y segura. No representan peligro para el sistema.")
        lbl_quar_info.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 9pt;")
        lbl_quar_info.setWordWrap(True)
        layout_quar.addWidget(lbl_quar_info)

        self.quarantine_table = QTableWidget(0, 5)
        self.quarantine_table.setHorizontalHeaderLabels(["Nombre", "Ruta Original", "Fecha", "Tamaño", "Acciones"])
        self.quarantine_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.quarantine_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.quarantine_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.quarantine_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.quarantine_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.quarantine_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.quarantine_table.verticalHeader().setVisible(False)
        self.quarantine_table.verticalHeader().setDefaultSectionSize(65)
        self.quarantine_table.setShowGrid(False)
        self.quarantine_table.setStyleSheet(self.threat_table.styleSheet())
        layout_quar.addWidget(self.quarantine_table)

        self.sub_tabs.addTab(self.tab_quarantine, "📦 Cuarentena")

        # ── 3. Tab de Configuración ──
        self.tab_config = QWidget()
        layout_cfg = QVBoxLayout(self.tab_config)
        layout_cfg.setContentsMargins(15, 15, 15, 15)
        layout_cfg.setSpacing(15)

        # Opciones Generales
        group_gen = QGroupBox("Opciones de Protección")
        group_gen.setStyleSheet(f"""
            QGroupBox {{
                color: {self.colores['acento']};
                font-weight: bold;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        layout_group_gen = QVBoxLayout(group_gen)
        layout_group_gen.setSpacing(10)

        self.chk_real_time = QCheckBox("Habilitar Protección en Tiempo Real (Simulación de agente)")
        self.chk_heuristic = QCheckBox("Activar Análisis Heurístico (Detectar amenazas desconocidas)")
        self.chk_scan_zip = QCheckBox("Escanear archivos comprimidos (.zip)")

        estilo_chk = f"""
            QCheckBox {{
                color: white;
                font-size: 9.5pt;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                background: {self.colores['bg_principal']};
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background: {self.colores['acento']};
                border: 1px solid {self.colores['acento']};
            }}
        """
        for chk in [self.chk_real_time, self.chk_heuristic, self.chk_scan_zip]:
            chk.setStyleSheet(estilo_chk)
            layout_group_gen.addWidget(chk)

        self.chk_real_time.setChecked(self.real_time_protection)
        self.chk_heuristic.setChecked(self.heuristic_enabled)
        self.chk_scan_zip.setChecked(self.scan_zip_enabled)

        self.chk_real_time.stateChanged.connect(self._toggle_real_time)
        self.chk_heuristic.stateChanged.connect(self._toggle_heuristic)
        self.chk_scan_zip.stateChanged.connect(self._toggle_scan_zip)

        layout_cfg.addWidget(group_gen)

        # Exclusiones
        group_ex = QGroupBox("Exclusiones de Análisis")
        group_ex.setStyleSheet(group_gen.styleSheet())
        layout_group_ex = QVBoxLayout(group_ex)
        layout_group_ex.setSpacing(10)

        lbl_ex_desc = QLabel("Las carpetas agregadas a esta lista no serán analizadas durante los escaneos.")
        lbl_ex_desc.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 8.5pt;")
        layout_group_ex.addWidget(lbl_ex_desc)

        self.list_exclusions = QListWidget()
        self.list_exclusions.setStyleSheet(f"""
            QListWidget {{
                background: {self.colores['bg_principal']};
                color: white;
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 6px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 4px;
            }}
        """)
        layout_group_ex.addWidget(self.list_exclusions)
        self._actualizar_lista_exclusiones_ui()

        layout_ex_btns = QHBoxLayout()
        self.btn_add_ex = QPushButton("➕  Agregar Carpeta")
        self.btn_del_ex = QPushButton("🗑️  Eliminar Seleccionada")
        
        estilo_ex_btn = f"""
            QPushButton {{
                background: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 9pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {self.colores['acento']}11;
                border: 1px solid {self.colores['acento']};
            }}
        """
        for btn in [self.btn_add_ex, self.btn_del_ex]:
            btn.setStyleSheet(estilo_ex_btn)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout_ex_btns.addWidget(btn)

        self.btn_add_ex.clicked.connect(self._agregar_exclusion)
        self.btn_del_ex.clicked.connect(self._eliminar_exclusion)
        layout_group_ex.addLayout(layout_ex_btns)

        layout_cfg.addWidget(group_ex)
        layout_cfg.addStretch()

        self.sub_tabs.addTab(self.tab_config, "⚙️ Configuración")

        self.layout_principal.addWidget(self.sub_tabs)

    # ── Métodos de Escaneo ──

    def iniciar_escaneo(self, scan_type):
        path_to_scan = None
        
        if scan_type == "custom":
            dir_selected = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Analizar")
            if not dir_selected:
                return
            path_to_scan = dir_selected

        # Restablecer UI
        self.threat_table.setRowCount(0)
        self.amenazas_detectadas = []
        self.log_console.clear()
        self.frame_progreso.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Desactivar botones de escaneo
        self.btn_quick.setEnabled(False)
        self.btn_full.setEnabled(False)
        self.btn_custom.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        # Actualizar banner de estado
        self.lbl_escudo.setText("🌀")
        self.lbl_estado_titulo.setText("ANALIZANDO SISTEMA...")
        self.lbl_estado_titulo.setStyleSheet(f"color: {self.colores['acento']};")
        self.lbl_estado_desc.setText("El escáner está analizando archivos en busca de amenazas...")
        self.frame_estado.setStyleSheet(self.frame_estado.styleSheet().replace(
            f"stop:1 rgba(34, 197, 94, 0.08)", f"stop:1 {self.colores['acento']}11"
        ).replace(
            f"border: 1px solid rgba(34, 197, 94, 0.2)", f"border: 1px solid {self.colores['acento']}33"
        ))

        # Crear y arrancar Thread
        self.scan_thread = ScanThread(
            scan_type=scan_type,
            initial_path=path_to_scan,
            exclusions=self.exclusiones,
            use_heuristics=self.heuristic_enabled,
            scan_zip=self.scan_zip_enabled
        )
        self.scan_thread.progress_updated.connect(self._on_scan_progress)
        self.scan_thread.threat_detected.connect(self._on_threat_detected)
        self.scan_thread.scan_finished.connect(self._on_scan_finished)
        self.scan_thread.start()

        self.log_console.append(f">> Iniciando análisis ({scan_type.upper()}) en {time.strftime('%Y-%m-%d %H:%M:%S')}...")

    def cancelar_escaneo(self):
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.cancel()
            self.log_console.append(">> Solicitando cancelación del análisis...")
            self.btn_cancel.setEnabled(False)

    def _on_scan_progress(self, percent, current_file, scanned, threats, speed):
        self.progress_bar.setValue(percent)
        
        # Truncar nombre del archivo
        max_len = 70
        truncated_file = current_file
        if len(current_file) > max_len:
            truncated_file = "..." + current_file[-(max_len-3):]
            
        self.lbl_current_file.setText(truncated_file)
        
        self.lbl_stat_files.setText(f"Archivos: {scanned}")
        self.lbl_stat_threats.setText(f"Amenazas: {threats}")
        self.lbl_stat_speed.setText(f"Velocidad: {int(speed)} arch/s")
        
        # Logs periódicos en la consola
        if scanned % 100 == 0 or threats > 0:
            self.log_console.append(f"Analizados: {scanned} | Amenazas: {threats} | {truncated_file}")

    def _on_threat_detected(self, threat):
        self.amenazas_detectadas.append(threat)
        self.log_console.append(f"<font color='{self.colores['error']}'><b>[AMENAZA DETECTADA]</b> {threat['name']} ({threat['type']}) -> {threat['path']}</font>")

        # Añadir a la tabla de amenazas
        row = self.threat_table.rowCount()
        self.threat_table.insertRow(row)

        item_name = QTableWidgetItem(threat['name'])
        item_path = QTableWidgetItem(threat['path'])
        item_type = QTableWidgetItem(threat['type'])
        item_severity = QTableWidgetItem(threat['severity'])

        # Colorear según severidad
        color_sev = self.colores['error'] if threat['severity'] in ['CRITICAL', 'ALTO'] else self.colores['advertencia']
        item_severity.setForeground(QColor(color_sev))

        self.threat_table.setItem(row, 0, item_name)
        self.threat_table.setItem(row, 1, item_path)
        self.threat_table.setItem(row, 2, item_type)
        self.threat_table.setItem(row, 3, item_severity)

        # Botones de Acción
        action_layout = QVBoxLayout()
        action_layout.setContentsMargins(4, 4, 4, 4)
        action_layout.setSpacing(4)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_quar = QPushButton("Quarentena")
        btn_del = QPushButton("Eliminar")

        estilo_act = """
            QPushButton {
                background: transparent;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 8.5pt;
                font-weight: bold;
            }
        """
        btn_quar.setStyleSheet(estilo_act + f"QPushButton {{ border: 1px solid {self.colores['acento']}; color: {self.colores['acento']}; }} QPushButton:hover {{ background: {self.colores['acento']}22; }}")
        btn_del.setStyleSheet(estilo_act + f"QPushButton {{ border: 1px solid {self.colores['error']}; color: {self.colores['error']}; }} QPushButton:hover {{ background: {self.colores['error']}22; }}")

        btn_quar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_quar.clicked.connect(lambda: self.quarentenar_amenaza(threat, row))
        btn_del.clicked.connect(lambda: self.eliminar_amenaza(threat, row))

        action_layout.addWidget(btn_quar)
        action_layout.addWidget(btn_del)
        
        container = QWidget()
        container.setLayout(action_layout)
        self.threat_table.setCellWidget(row, 4, container)

        # Parpadear banner en rojo
        self.lbl_escudo.setText("⚠️")
        self.lbl_estado_titulo.setText("AMENAZAS DETECTADAS")
        self.lbl_estado_titulo.setStyleSheet(f"color: {self.colores['error']};")
        self.lbl_estado_desc.setText(f"¡Atención! Se han encontrado {len(self.amenazas_detectadas)} amenazas activas en el equipo.")
        self.frame_estado.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.colores['bg_secundario']}, stop:1 rgba(229, 57, 53, 0.08));
                border: 1px solid rgba(229, 57, 53, 0.2);
                border-radius: 10px;
            }}
        """)

    def _on_scan_finished(self, success, stats):
        # Habilitar botones de escaneo
        self.btn_quick.setEnabled(True)
        self.btn_full.setEnabled(True)
        self.btn_custom.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if not success:
            self.log_console.append(f">> Análisis abortado por el usuario o finalizado con error: {stats.get('error', 'Cancelado')}")
            # Restablecer escudo
            if len(self.amenazas_detectadas) == 0:
                self.lbl_escudo.setText("🛡️")
                self.lbl_estado_titulo.setText("SISTEMA PROTEGIDO")
                self.lbl_estado_titulo.setStyleSheet(f"color: {self.colores.get('exito', '#22c55e')};")
                self.lbl_estado_desc.setText("El análisis fue cancelado. No hay amenazas activas registradas.")
                self.frame_estado.setStyleSheet(f"""
                    QFrame {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.colores['bg_secundario']}, stop:1 rgba(34, 197, 94, 0.08));
                        border: 1px solid rgba(34, 197, 94, 0.2);
                        border-radius: 10px;
                    }}
                """)
            return

        self.log_console.append(f">> Análisis finalizado exitosamente en {time.strftime('%Y-%m-%d %H:%M:%S')}.")
        self.log_console.append(f">> Total Escaneado: {stats['scanned']} archivos | Amenazas Encontradas: {stats['threats']} | Duración: {stats['elapsed']:.2f}s")
        self.progress_bar.setValue(100)
        self.lbl_current_file.setText("Análisis Finalizado.")

        if len(self.amenazas_detectadas) == 0:
            self.lbl_escudo.setText("🛡️")
            self.lbl_estado_titulo.setText("SISTEMA PROTEGIDO")
            self.lbl_estado_titulo.setStyleSheet(f"color: {self.colores.get('exito', '#22c55e')};")
            self.lbl_estado_desc.setText(f"Análisis terminado. Se analizaron {stats['scanned']} archivos y no se encontraron amenazas.")
            self.frame_estado.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.colores['bg_secundario']}, stop:1 rgba(34, 197, 94, 0.08));
                    border: 1px solid rgba(34, 197, 94, 0.2);
                    border-radius: 10px;
                }}
            """)
            QMessageBox.information(self, "Antivirus", f"Análisis finalizado.\nNo se detectaron amenazas en {stats['scanned']} archivos.")
        else:
            QMessageBox.warning(self, "Antivirus", f"Análisis finalizado.\n¡Atención! Se detectaron {stats['threats']} amenazas potenciales. Revise la tabla de resultados.")

    # ── Acciones de Amenazas (Cuarentena y Eliminación) ──

    def quarentenar_amenaza(self, threat, row_index):
        orig_path = threat["path"]
        if not os.path.exists(orig_path):
            QMessageBox.warning(self, "Error", "El archivo ya no existe en la ruta original.")
            return

        try:
            # Generar hash para nombre en cuarentena
            file_hash = hashlib.sha256(orig_path.encode('utf-8') + str(time.time()).encode('utf-8')).hexdigest()
            quar_file_path = self.quarantine_dir / f"{file_hash}.bin"

            # Mover y encriptar (XOR simple de 0xFF para dejar el ejecutable/script totalmente inerte)
            with open(orig_path, 'rb') as f_orig:
                data = f_orig.read()
            
            # Ofuscar bytes
            obfuscated_data = bytearray(b ^ 0xFF for b in data)

            with open(quar_file_path, 'wb') as f_quar:
                f_quar.write(obfuscated_data)

            # Eliminar original
            os.remove(orig_path)

            # Guardar en base de datos JSON
            db_entries = []
            if self.quarantine_db.exists():
                try:
                    with open(self.quarantine_db, "r", encoding="utf-8") as f:
                        db_entries = json.load(f)
                except Exception:
                    pass

            db_entries.append({
                "hash": file_hash,
                "name": threat["name"],
                "original_path": orig_path,
                "quarantine_path": str(quar_file_path),
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "size": len(data)
            })

            with open(self.quarantine_db, "w", encoding="utf-8") as f:
                json.dump(db_entries, f, indent=4)

            self.log_console.append(f">> Archivo en cuarentena: {threat['name']} -> Mantenido seguro en almacén.")
            
            # Remover de la lista de amenazas detectadas y UI
            self.threat_table.removeRow(row_index)
            # Reindexar botones de la tabla si es necesario
            self.cargar_cuarentena_ui()
            
            # Comprobar si quedan más amenazas
            self.amenazas_detectadas = [t for t in self.amenazas_detectadas if t["path"] != orig_path]
            if not self.amenazas_detectadas:
                self._restablecer_escudo_seguro()

            QMessageBox.information(self, "Antivirus", f"El archivo '{threat['name']}' ha sido movido a cuarentena de forma segura.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo mover el archivo a cuarentena: {e}")

    def eliminar_amenaza(self, threat, row_index):
        orig_path = threat["path"]
        if not os.path.exists(orig_path):
            QMessageBox.warning(self, "Error", "El archivo ya no existe.")
            return

        confirm = QMessageBox.question(
            self, "Confirmar Eliminación", 
            f"¿Está seguro de que desea eliminar permanentemente el archivo:\n{orig_path}?\n\nEsta acción es irreversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            try:
                os.remove(orig_path)
                self.log_console.append(f">> Archivo eliminado permanentemente: {threat['name']}")
                self.threat_table.removeRow(row_index)
                
                self.amenazas_detectadas = [t for t in self.amenazas_detectadas if t["path"] != orig_path]
                if not self.amenazas_detectadas:
                    self._restablecer_escudo_seguro()

                QMessageBox.information(self, "Antivirus", f"El archivo '{threat['name']}' ha sido eliminado permanentemente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el archivo: {e}")

    def _restablecer_escudo_seguro(self):
        self.lbl_escudo.setText("🛡️")
        self.lbl_estado_titulo.setText("SISTEMA PROTEGIDO")
        self.lbl_estado_titulo.setStyleSheet(f"color: {self.colores.get('exito', '#22c55e')};")
        self.lbl_estado_desc.setText("La protección está activa. No se han detectado amenazas.")
        self.frame_estado.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.colores['bg_secundario']}, stop:1 rgba(34, 197, 94, 0.08));
                border: 1px solid rgba(34, 197, 94, 0.2);
                border-radius: 10px;
            }}
        """)

    # ── UI y Gestión de Cuarentena ──

    def cargar_cuarentena_ui(self):
        self.quarantine_table.setRowCount(0)
        if not self.quarantine_db.exists():
            return

        try:
            with open(self.quarantine_db, "r", encoding="utf-8") as f:
                entries = json.load(f)

            for i, entry in enumerate(entries):
                row = self.quarantine_table.rowCount()
                self.quarantine_table.insertRow(row)

                sz_kb = f"{entry.get('size', 0) / 1024:.2f} KB"
                self.quarantine_table.setItem(row, 0, QTableWidgetItem(entry["name"]))
                self.quarantine_table.setItem(row, 1, QTableWidgetItem(entry["original_path"]))
                self.quarantine_table.setItem(row, 2, QTableWidgetItem(entry["date"]))
                self.quarantine_table.setItem(row, 3, QTableWidgetItem(sz_kb))

                # Botones
                act_layout = QVBoxLayout()
                act_layout.setContentsMargins(4, 4, 4, 4)
                act_layout.setSpacing(4)
                act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                btn_restore = QPushButton("Restaurar")
                btn_delete = QPushButton("Eliminar Def.")

                estilo_act = """
                    QPushButton {
                        background: transparent;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 8.5pt;
                        font-weight: bold;
                    }
                """
                btn_restore.setStyleSheet(estilo_act + f"QPushButton {{ border: 1px solid {self.colores.get('exito', '#22c55e')}; color: {self.colores.get('exito', '#22c55e')}; }} QPushButton:hover {{ background: {self.colores.get('exito', '#22c55e')}22; }}")
                btn_delete.setStyleSheet(estilo_act + f"QPushButton {{ border: 1px solid {self.colores['error']}; color: {self.colores['error']}; }} QPushButton:hover {{ background: {self.colores['error']}22; }}")

                btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)

                # Pasamos la entrada completa
                btn_restore.clicked.connect(lambda checked, ent=entry: self.restaurar_quarentena(ent))
                btn_delete.clicked.connect(lambda checked, ent=entry: self.eliminar_permanente_quarentena(ent))

                act_layout.addWidget(btn_restore)
                act_layout.addWidget(btn_delete)

                container = QWidget()
                container.setLayout(act_layout)
                self.quarantine_table.setCellWidget(row, 4, container)
        except Exception:
            pass

    def restaurar_quarentena(self, entry):
        quar_path = Path(entry["quarantine_path"])
        orig_path = Path(entry["original_path"])

        if not quar_path.exists():
            QMessageBox.warning(self, "Error", "El archivo de cuarentena física ya no existe.")
            return

        try:
            # Recrear carpeta contenedora si no existe
            orig_path.parent.mkdir(parents=True, exist_ok=True)

            # Leer y desencriptar (XOR simple)
            with open(quar_path, 'rb') as f_quar:
                obfuscated_data = f_quar.read()

            original_data = bytearray(b ^ 0xFF for b in obfuscated_data)

            with open(orig_path, 'wb') as f_orig:
                f_orig.write(original_data)

            # Eliminar binario de cuarentena
            os.remove(quar_path)

            # Remover de la BD
            with open(self.quarantine_db, "r", encoding="utf-8") as f:
                entries = json.load(f)
            
            entries = [e for e in entries if e["hash"] != entry["hash"]]

            with open(self.quarantine_db, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=4)

            self.cargar_cuarentena_ui()
            QMessageBox.information(self, "Antivirus", f"El archivo '{entry['name']}' ha sido restaurado exitosamente a su ubicación original:\n{orig_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo restaurar el archivo: {e}")

    def eliminar_permanente_quarentena(self, entry):
        quar_path = Path(entry["quarantine_path"])

        confirm = QMessageBox.question(
            self, "Confirmar Eliminación", 
            f"¿Está seguro de que desea eliminar permanentemente de la cuarentena el archivo:\n{entry['name']}?\n\nEsta acción es definitiva.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            try:
                if quar_path.exists():
                    os.remove(quar_path)

                with open(self.quarantine_db, "r", encoding="utf-8") as f:
                    entries = json.load(f)

                entries = [e for e in entries if e["hash"] != entry["hash"]]

                with open(self.quarantine_db, "w", encoding="utf-8") as f:
                    json.dump(entries, f, indent=4)

                self.cargar_cuarentena_ui()
                QMessageBox.information(self, "Antivirus", f"Archivo '{entry['name']}' eliminado de la cuarentena.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el archivo de la cuarentena: {e}")

    # ── Configuración y Exclusiones ──

    def _toggle_real_time(self, state):
        self.real_time_protection = (state == Qt.CheckState.Checked.value)
        self.guardar_configuraciones()
        status_str = "habilitada (simulado)" if self.real_time_protection else "deshabilitada"
        self.log_console.append(f">> Configuración cambiada: Protección en tiempo real {status_str}.")

    def _toggle_heuristic(self, state):
        self.heuristic_enabled = (state == Qt.CheckState.Checked.value)
        self.guardar_configuraciones()
        status_str = "habilitado" if self.heuristic_enabled else "deshabilitado"
        self.log_console.append(f">> Configuración cambiada: Análisis heurístico {status_str}.")

    def _toggle_scan_zip(self, state):
        self.scan_zip_enabled = (state == Qt.CheckState.Checked.value)
        self.guardar_configuraciones()
        status_str = "habilitado" if self.scan_zip_enabled else "deshabilitado"
        self.log_console.append(f">> Configuración cambiada: Escaneo de comprimidos .zip {status_str}.")

    def _actualizar_lista_exclusiones_ui(self):
        self.list_exclusions.clear()
        for exc in self.exclusiones:
            self.list_exclusions.addItem(exc)

    def _agregar_exclusion(self):
        dir_selected = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Excluir")
        if dir_selected:
            norm_dir = os.path.abspath(dir_selected)
            if norm_dir not in self.exclusiones:
                self.exclusiones.append(norm_dir)
                self.guardar_configuraciones()
                self._actualizar_lista_exclusiones_ui()
                self.log_console.append(f">> Exclusión agregada: {norm_dir}")

    def _eliminar_exclusion(self):
        item = self.list_exclusions.currentItem()
        if item:
            path_exc = item.text()
            if path_exc in self.exclusiones:
                self.exclusiones.remove(path_exc)
                self.guardar_configuraciones()
                self._actualizar_lista_exclusiones_ui()
                self.log_console.append(f">> Exclusión eliminada: {path_exc}")
