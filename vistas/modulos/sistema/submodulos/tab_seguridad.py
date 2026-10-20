import os
import threading
import platform
import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, 
    QTextEdit, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QAction, QColor

class TabSeguridad(QWidget):
    """Refactorizado: Gestor de Hardware y Puertos (Seguridad Física)"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(20, 20, 20, 20)
        self.layout_principal.setSpacing(15)
        
        self.setup_ui()
        
        # Timer para refrescar dispositivos automáticamente
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refrescar_dispositivos)
        self.timer.start(3000)
        
        self.refrescar_dispositivos()

    def setup_ui(self):
        # ── Encabezado ──
        header = QHBoxLayout()
        header.setSpacing(12)
        lbl_tit = QLabel("🔌 Gestor de Hardware")
        lbl_tit.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['fg_principal']};")
        header.addWidget(lbl_tit)
        header.addStretch()

        self.btn_refresh = QPushButton("🔄  Actualizar")
        self.btn_refresh.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_refresh.setFixedHeight(36)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                padding: 0px 18px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
            QPushButton:pressed {{ background: {self.colores['acento']}cc; }}
        """)
        self.btn_refresh.clicked.connect(self.refrescar_dispositivos)
        header.addWidget(self.btn_refresh)
        self.layout_principal.addLayout(header)

        # Separador decorativo
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.07);")
        self.layout_principal.addWidget(sep)

        # ── Etiqueta de sección ──
        lbl_res = QLabel("  DISPOSITIVOS DETECTADOS")
        lbl_res.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_res.setStyleSheet(f"color: {self.colores['fg_secundario']}; letter-spacing: 1.5px;")
        self.layout_principal.addWidget(lbl_res)

        # ── Tabla de Dispositivos ──
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Unidad", "Punto de Montaje", "Tipo", "Uso", "Acción"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {self.colores['bg_secundario']};
                alternate-background-color: {self.colores['bg_terciario']};
                border: none;
                color: white;
                border-radius: 10px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 0px 12px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background: {self.colores['acento']}33;
                color: white;
            }}
            QHeaderView::section {{
                background: {self.colores['bg_principal']};
                color: {self.colores['fg_secundario']};
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.06);
                padding: 10px 12px;
                font-weight: 600;
                font-size: 9px;
                letter-spacing: 1px;
            }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.15);
                border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._mostrar_context_menu)
        self.layout_principal.addWidget(self.table)

        # ── Monitor en tiempo real (Log) ──
        lbl_log = QLabel("  REGISTRO DE HARDWARE")
        lbl_log.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_log.setStyleSheet(f"color: {self.colores['fg_secundario']}; letter-spacing: 1.5px;")
        self.layout_principal.addWidget(lbl_log)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(90)
        self.txt_log.setStyleSheet(f"""
            QTextEdit {{
                background: {self.colores['bg_principal']};
                color: {self.colores['exito']};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
                font-family: Consolas;
                font-size: 10px;
                padding: 8px;
            }}
        """)
        self.txt_log.append(f">> Monitor de Hardware iniciado en {platform.system()}.")
        self.layout_principal.addWidget(self.txt_log)

    def refrescar_dispositivos(self):
        """Detecta unidades flash, discos y DVDs"""
        try:
            prev_rows = self.table.rowCount()
            self.table.setRowCount(0)
            
            partitions = psutil.disk_partitions(all=True)
            for p in partitions:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Icono según tipo
                icono = "💽"
                tipo_str = "Desconocido"
                
                if 'cdrom' in p.opts.lower() or p.fstype == "":
                    icono = "💿"
                    tipo_str = "DVD/CD-ROM"
                elif 'removable' in p.opts.lower() or (platform.system() == "Windows" and p.device.startswith(('E:', 'F:', 'G:', 'H:', 'I:'))):
                    icono = "🔌"
                    tipo_str = "Unidad Flash / Extraíble"
                else:
                    icono = "💻"
                    tipo_str = "Disco Local"

                it_dev = QTableWidgetItem(f"{icono} {p.device}")
                it_dev.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                it_dev.setForeground(QColor("#FFFFFF"))
                self.table.setItem(row, 0, it_dev)

                it_mnt = QTableWidgetItem(p.mountpoint)
                it_mnt.setFont(QFont("Consolas", 9))
                it_mnt.setForeground(QColor("#60A5FA"))
                self.table.setItem(row, 1, it_mnt)

                it_type = QTableWidgetItem(tipo_str)
                it_type.setFont(QFont("Segoe UI", 9))
                it_type.setForeground(QColor("#FBBF24") if tipo_str != "Disco Local" else QColor("#AAB0B8"))
                self.table.setItem(row, 2, it_type)
                
                # Estado (Ocupado/Libre)
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    estado = f"{usage.percent}% usado"
                except:
                    estado = "No montado / Protegido"
                
                it_use = QTableWidgetItem(estado)
                it_use.setFont(QFont("Segoe UI", 9))
                it_use.setForeground(QColor("#34D399") if "%" in estado else QColor("#9CA3AF"))
                self.table.setItem(row, 3, it_use)
                
                # Botón de Expulsar si es extraíble
                if tipo_str != "Disco Local":
                    btn_eject = QPushButton("⏏️  Eyectar")
                    btn_eject.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    btn_eject.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_eject.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            color: {self.colores['error']};
                            border: 1px solid {self.colores['error']}88;
                            border-radius: 5px;
                            padding: 4px 8px;
                        }}
                        QPushButton:hover {{
                            background: {self.colores['error']}22;
                            color: #FF6B6B;
                        }}
                    """)
                    btn_eject.clicked.connect(lambda ch, d=p.device: self.expulsar_unidad(d))
                    self.table.setCellWidget(row, 4, btn_eject)
                else:
                    it_dash = QTableWidgetItem("---")
                    it_dash.setForeground(QColor("#6B7280"))
                    self.table.setItem(row, 4, it_dash)

            # Log de cambios si varía el número de unidades
            if self.table.rowCount() != prev_rows and prev_rows > 0:
                self.txt_log.append(">> Cambio en configuración de hardware detectado.")
                
        except Exception as e:
            self.txt_log.append(f">> Error al refrescar: {e}")

    def expulsar_unidad(self, device):
        """Expulsa la unidad de forma segura e instantánea en segundo plano sin abrir consolas ni bloquear la interfaz."""
        def _hacer_eject():
            try:
                if platform.system() == "Windows":
                    import subprocess
                    letra = device.rstrip('\\/').rstrip(':') + ":"
                    # Ejecutar en segundo plano con CREATE_NO_WINDOW
                    ps_cmd = f"$d = New-Object -ComObject Shell.Application; $item = $d.NameSpace(17).ParseName('{letra}\\'); if ($item) {{ $item.InvokeVerb('Eject') }}"
                    subprocess.run(
                        ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=4,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    import subprocess
                    subprocess.run(["umount", device], timeout=4, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as ex:
                print(f"[Hardware] Error expulsando unidad {device}: {ex}")
            finally:
                QTimer.singleShot(500, self.refrescar_dispositivos)

        threading.Thread(target=_hacer_eject, daemon=True).start()
        QMessageBox.information(
            self, "Hardware", 
            f"Se ha enviado la señal de expulsión a {device}.\n\nPuedes retirar el dispositivo de forma segura."
        )

    def _mostrar_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        
        menu = QMenu(self)
        menu.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white;")
        
        act_open = QAction("📂 Abrir en Navegador de Archivos", self)
        act_open.triggered.connect(lambda: self._abrir_en_explorer(self.table.item(item.row(), 1).text()))
        menu.addAction(act_open)
        
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _abrir_en_explorer(self, path):
        if os.path.exists(path):
             os.startfile(path) if platform.system() == "Windows" else os.system(f"xdg-open {path}")

    def showEvent(self, event):
        super().showEvent(event)
        self.refrescar_dispositivos()
        if hasattr(self, "timer") and not self.timer.isActive():
            self.timer.start(3000)

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()
