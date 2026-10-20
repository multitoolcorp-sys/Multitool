import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QGridLayout, QFrame, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class TabResumen(QWidget):
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.inicializar_ui()

    def inicializar_ui(self):
        self.setStyleSheet("color: white;")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)
        
        # --- ENCABEZADO ---
        header_lay = QHBoxLayout()
        lbl_tit = QLabel("RESUMEN DEL SISTEMA")
        lbl_tit.setFont(QFont(self.font_family, 18, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']};")
        header_lay.addWidget(lbl_tit)
        header_lay.addStretch()
        self.main_layout.addLayout(header_lay)

        # --- SECCIÓN: DASHBOARD EN TIEMPO REAL ---
        dash_frame = QFrame()
        dash_frame.setFixedHeight(120)  # Altura fija para evitar que empuje hacia abajo
        dash_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 12px;
                padding: 5px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        dash_lay = QHBoxLayout(dash_frame)
        dash_lay.setContentsMargins(10, 5, 10, 5)
        dash_lay.setSpacing(10)

        # CPU Card
        self.card_cpu = self._crear_indicador("CPU", "0%")
        dash_lay.addWidget(self.card_cpu)
        
        # RAM Card
        self.card_ram = self._crear_indicador("RAM", "0%")
        dash_lay.addWidget(self.card_ram)
        
        # GPU Card
        self.card_gpu = self._crear_indicador("GPU", "0%")
        dash_lay.addWidget(self.card_gpu)
        
        # DISK Card
        self.card_disk = self._crear_indicador("DISCO", "0%")
        dash_lay.addWidget(self.card_disk)

        # NET Card
        self.card_net = self._crear_indicador_red("RED (SUB/BAJ)", "0/0")
        dash_lay.addWidget(self.card_net)

        self.main_layout.addWidget(dash_frame)

        # --- SECCIÓN: INFORMACIÓN DETALLADA (SCROLLABLE) ---
        self.scroll_info = QScrollArea()
        self.scroll_info.setWidgetResizable(True)
        self.scroll_info.setStyleSheet("background: transparent; border: none;")
        
        self.info_widget = QWidget()
        self.info_grid = QGridLayout(self.info_widget)
        self.info_grid.setContentsMargins(0, 0, 0, 0)
        self.info_grid.setSpacing(12)
        self.scroll_info.setWidget(self.info_widget)
        
        self.main_layout.addWidget(self.scroll_info, 1)

        # --- SECCIÓN: ACCIONES RÁPIDAS ---
        actions_frame = QFrame()
        actions_frame.setFixedHeight(80) # Altura limitada
        actions_frame.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; padding: 5px;")
        actions_lay = QVBoxLayout(actions_frame)
        actions_lay.setContentsMargins(10, 5, 10, 5)
        
        btns_lay = QHBoxLayout()
        tools = [
            ("📁 Proyecto", "abrir_carpeta"),
            ("🛠️ Tareas", "abrir_admin"),
            ("💻 CMD", "abrir_cmd"),
            ("💾 Discos", "abrir_discos"),
            ("🌐 Red", "abrir_redes"),
            ("🧩 Regedit", "abrir_regedit")
        ]
        for t, c in tools:
            btn = QPushButton(t)
            btn.setMinimumHeight(45)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores['bg_terciario']};
                    color: {self.colores['fg_principal']};
                    border-radius: 8px;
                    padding: 5px 15px;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }}
                QPushButton:hover {{
                    background: {self.colores['acento']};
                    color: white;
                    border: 1px solid {self.colores['acento']};
                }}
                QPushButton:pressed {{
                    background: {self.colores['acento_hover']};
                }}
            """)
            if c in self.callbacks: btn.clicked.connect(self.callbacks[c])
            btns_lay.addWidget(btn)
        actions_lay.addLayout(btns_lay)
        
        self.main_layout.addWidget(actions_frame)

    def _crear_indicador(self, titulo, valor_inicial):
        container = QFrame()
        
        # Mapa de colores para cada indicador para consistencia visual
        col_map = {
            "CPU": self.colores['acento'],
            "RAM": self.colores['exito'],
            "GPU": "#8B5CF6", # Violeta
            "DISCO": self.colores['advertencia']
        }
        accent = col_map.get(titulo, self.colores['acento'])
        
        container.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.02);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.03);
            }}
            QFrame:hover {{
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid {accent}44;
            }}
        """)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(10, 10, 10, 10)
        
        title = QLabel(titulo)
        title.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        
        val = QLabel(valor_inicial)
        val.setFont(QFont(self.font_family, 14, QFont.Weight.Bold))
        val.setStyleSheet(f"color: {accent};")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(val)
        
        bar = QProgressBar()
        bar.setFixedHeight(4)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background: rgba(0,0,0,0.3); border: none; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}
        """)
        lay.addWidget(bar)
        
        # Guardar referencias
        container.lbl_val = val
        container.bar = bar
        return container

    def _crear_indicador_red(self, titulo, valor_inicial):
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.02);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.03);
            }}
            QFrame:hover {{
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid {self.colores['exito']}44;
            }}
        """)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(10, 10, 10, 10)
        
        title = QLabel(titulo)
        title.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        
        self.lbl_net_val = QLabel(valor_inicial)
        self.lbl_net_val.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_net_val.setStyleSheet(f"color: {self.colores['exito']};")
        self.lbl_net_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_net_val)
        
        return container

    def actualizar_dashboard(self, data):
        """Actualiza los indicadores en tiempo real"""
        try:
            self.card_cpu.lbl_val.setText(f"{data['cpu']:.1f}%")
            self.card_cpu.bar.setValue(int(data['cpu']))
            
            self.card_ram.lbl_val.setText(f"{data['mem_p']:.1f}%")
            self.card_ram.bar.setValue(int(data['mem_p']))
            
            self.card_disk.lbl_val.setText(f"{data['disk_p']:.1f}%")
            self.card_disk.bar.setValue(int(data['disk_p']))
            
            gpu = data.get('gpu', {})
            uso_gpu = gpu.get('uso', 0)
            self.card_gpu.lbl_val.setText(f"{uso_gpu:.1f}%")
            self.card_gpu.bar.setValue(int(uso_gpu))
            
            self.lbl_net_val.setText(f"▲ {data['net_up']} | ▼ {data['net_down']}")
        except: pass

    def rellenar_grid_info(self, info):
        # Limpiar
        for i in reversed(range(self.info_grid.count())): 
            widget = self.info_grid.itemAt(i).widget()
            if widget: widget.setParent(None)
            
        label_map = {
            "so": "Sistema Operativo:", "version": "Versión:", "arch": "Arquitectura:",
            "nodo": "Nombre del Equipo:", "usuario": "Usuario Actual:", "cpu_modelo": "Procesador:",
            "cpu_hilos": "Núcleos/Hilos:", "ram_total": "Total RAM:", "ram_disp": "RAM Disponible:",
            "ip_local": "IP Privada:", "uptime": "Tiempo Encendido:"
        }
        
        row, col = 0, 0
        for k, v in info.items():
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {self.colores['bg_secundario']};
                    border-radius: 8px;
                    padding: 10px 14px;
                    border: 1px solid rgba(255, 255, 255, 0.03);
                }}
                QFrame:hover {{
                    background: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                }}
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(12, 10, 12, 10)
            c_lay.setSpacing(4)
            
            lbl_k = QLabel(label_map.get(k, k))
            lbl_k.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
            lbl_k.setStyleSheet(f"color: {self.colores['fg_secundario']}; text-transform: uppercase; letter-spacing: 0.5px;")
            c_lay.addWidget(lbl_k)
            
            lbl_v = QLabel(str(v))
            lbl_v.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
            lbl_v.setStyleSheet(f"color: white;")
            lbl_v.setWordWrap(True)
            c_lay.addWidget(lbl_v)
            
            self.info_grid.addWidget(card, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
