import platform
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class TabMonitoreo(QWidget):
    """Pestaña de Monitoreo de Recursos en Tiempo Real"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "monospace"

        self.inicializar_ui()

    def inicializar_ui(self):
        self.setStyleSheet(f"color: white;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # -----------------------------
        # Panel izquierdo (Stats)
        # -----------------------------
        stats_f = QFrame()
        stats_f.setMinimumWidth(320)
        stats_f.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)

        s_lay = QVBoxLayout(stats_f)
        s_lay.setContentsMargins(20, 20, 20, 20)
        s_lay.setSpacing(12)

        lbl_title = QLabel("RECURSOS EN VIVO")
        lbl_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        s_lay.addWidget(lbl_title)

        cpu_style = f"""
            QProgressBar {{
                border: none;
                background-color: {self.colores['bg_principal']};
                border-radius: 5px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.colores['acento']}, stop:1 {self.colores['acento_hover']});
                border-radius: 5px;
            }}
        """
        
        ram_style = f"""
            QProgressBar {{
                border: none;
                background-color: {self.colores['bg_principal']};
                border-radius: 5px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #059669);
                border-radius: 5px;
            }}
        """
        
        disk_style = f"""
            QProgressBar {{
                border: none;
                background-color: {self.colores['bg_principal']};
                border-radius: 5px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F59E0B, stop:1 #D97706);
                border-radius: 5px;
            }}
        """

        # CPU
        s_lay.addWidget(self._create_stat_row("CPU:", "bar_cpu", "lbl_cpu_val", cpu_style))
        # RAM
        s_lay.addWidget(self._create_stat_row("RAM:", "bar_mem", "lbl_mem_val", ram_style))
        # DISCO
        s_lay.addWidget(self._create_stat_row("DISCO:", "bar_disk", "lbl_disk_val", disk_style))

        # RED
        s_lay.addSpacing(15)
        lbl_net = QLabel("ACTIVIDAD DE RED")
        lbl_net.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_net.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        s_lay.addWidget(lbl_net)

        self.lbl_net_up = QLabel("Subida: 0.0 KB/s")
        self.lbl_net_down = QLabel("Bajada: 0.0 KB/s")
        for lbl in [self.lbl_net_up, self.lbl_net_down]:
            lbl.setFont(QFont(self.font_family, 9))
            lbl.setStyleSheet("color: #E2E2E2;")
            s_lay.addWidget(lbl)

        s_lay.addStretch()

        self.lbl_uptime = QLabel("Activo: ---")
        self.lbl_uptime.setFont(QFont(self.font_family, 8))
        self.lbl_uptime.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        s_lay.addWidget(self.lbl_uptime)

        # Botones
        self.btn_iniciar = QPushButton("▶ INICIAR MONITOREO")
        self.btn_iniciar.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_iniciar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_iniciar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white;
                border-radius: 8px;
                padding: 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores['acento_hover']};
            }}
            QPushButton:pressed {{
                background-color: #3b82f6;
            }}
        """)
        self.btn_iniciar.clicked.connect(self.callbacks["iniciar_monitoreo"])
        s_lay.addWidget(self.btn_iniciar)

        self.btn_detener = QPushButton("⏹ DETENER")
        self.btn_detener.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_detener.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_detener.setEnabled(False)
        self.btn_detener.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: {self.colores['fg_secundario']};
                border-radius: 8px;
                padding: 10px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            QPushButton:enabled {{
                background-color: {self.colores['error']};
                color: white;
                border: none;
            }}
            QPushButton:enabled:hover {{
                background-color: #ef4444;
            }}
            QPushButton:enabled:pressed {{
                background-color: #dc2626;
            }}
        """)
        self.btn_detener.clicked.connect(self.callbacks["detener_monitoreo"])
        s_lay.addWidget(self.btn_detener)

        layout.addWidget(stats_f)

        # Panel derecho (Gráfico + Top)
        der_f = QFrame()
        d_lay = QVBoxLayout(der_f)
        d_lay.setContentsMargins(0, 0, 0, 0)
        d_lay.setSpacing(15)

        self.graf_f = QFrame()
        self.graf_f.setStyleSheet(f"background: {self.colores['bg_principal']}; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05);")
        self.layout_grafico = QVBoxLayout(self.graf_f)
        d_lay.addWidget(self.graf_f, 1)

        # TOP PROCESOS
        top_f = QFrame()
        top_f.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        t_lay = QVBoxLayout(top_f)
        t_lay.setContentsMargins(20, 20, 20, 20)

        lbl_top = QLabel("⚡ TOP 5 PROCESOS (CPU)")
        lbl_top.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_top.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        t_lay.addWidget(lbl_top)

        self.txt_top_procs = QLabel("Esperando datos...")
        self.txt_top_procs.setFont(QFont(self.mono_font, 10))
        self.txt_top_procs.setStyleSheet(f"""
            QLabel {{
                color: {self.colores['fg_principal']};
                background: {self.colores['bg_principal']};
                padding: 10px;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.03);
            }}
        """)
        self.txt_top_procs.setWordWrap(True)
        self.txt_top_procs.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        t_lay.addWidget(self.txt_top_procs, 1)

        d_lay.addWidget(top_f)
        layout.addWidget(der_f, 1)

    def _create_stat_row(self, text, bar_attr, lbl_attr, style):
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)
        
        lbl_name = QLabel(text)
        lbl_name.setFont(QFont(self.font_family, 9))
        lay.addWidget(lbl_name)
        
        h = QHBoxLayout()
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setFixedHeight(10)
        bar.setStyleSheet(style)
        setattr(self, bar_attr, bar)
        h.addWidget(bar)
        
        val = QLabel("0%")
        val.setFixedWidth(45)
        val.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        val.setAlignment(Qt.AlignmentFlag.AlignRight)
        setattr(self, lbl_attr, val)
        h.addWidget(val)
        
        lay.addLayout(h)
        return container
