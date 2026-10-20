import os
import platform
from pathlib import Path
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QWidget, QScrollArea
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class FileSidebar(QFrame):
    """Panel lateral con bibliotecas, recientes, Este equipo, unidades y acciones"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.drives_buttons = []
        self.historial_recientes = []
        self.botones_recientes = []
        self.inicializar_ui()
        
        # Timer para detección de unidades (USB, etc) en segundo plano sin lag
        self.timer_drives = QTimer(self)
        self.timer_drives.timeout.connect(self.refrescar_unidades)
        self.timer_drives.start(10000)

    def inicializar_ui(self):
        self.setFixedWidth(200)
        self.setStyleSheet(f"background: {self.colores['bg_principal']}; border-right: 1px solid rgba(255,255,255,0.03);")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area para permitir que se vea todo cómodamente
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.main_layout = QVBoxLayout(self.content)
        self.main_layout.setContentsMargins(10, 12, 10, 12)
        self.main_layout.setSpacing(4)
        
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)
 
        self.side_btn_style = f"""
            QPushButton {{
                background: transparent; color: #E2E2E2; border: none;
                text-align: left; padding: 6px 10px; border-radius: 6px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: rgba(255, 255, 255, 0.05); color: {self.colores['acento']}; }}
        """

        # ── 1. SECCIÓN BIBLIOTECAS ──
        lbl_side = QLabel("BIBLIOTECAS")
        lbl_side.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_side.setStyleSheet(f"color: {self.colores['fg_secundario']}; margin-bottom: 3px; letter-spacing: 1px;")
        self.main_layout.addWidget(lbl_side)
        
        home = str(Path.home())
        accesos = [
            ("💻 Este Equipo", "shell:MyComputerFolder"),
            ("🏠 Home", home),
            ("🖥️ Escritorio", str(Path.home() / "Desktop")),
            ("📂 Documentos", str(Path.home() / "Documents")),
            ("⬇️ Descargas", str(Path.home() / "Downloads")),
            ("🖼️ Imágenes", str(Path.home() / "Pictures")),
            ("🗑️ Papelera", "trash"),
        ]
        
        for text, path in accesos:
            if path in ("trash", "shell:MyComputerFolder") or os.path.exists(path):
                btn = QPushButton(text)
                btn.setFont(QFont(self.font_family, 9))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(self.side_btn_style)
                if path == "trash":
                    btn.clicked.connect(self.callbacks.get("mostrar_papelera"))
                else:
                    btn.clicked.connect(lambda checked, p=path: self.callbacks.get("ir_a_ruta_manual")(p))
                self.main_layout.addWidget(btn)

        # ── 2. SECCIÓN CARPETAS RECIENTES (Últimas 4) ──
        lbl_rec = QLabel("ÚLTIMAS 4 CARPETAS")
        lbl_rec.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_rec.setStyleSheet(f"color: {self.colores['fg_secundario']}; margin-top: 10px; margin-bottom: 3px; letter-spacing: 1px;")
        self.main_layout.addWidget(lbl_rec)

        self.container_recientes = QWidget()
        self.lay_recientes = QVBoxLayout(self.container_recientes)
        self.lay_recientes.setContentsMargins(0, 0, 0, 0)
        self.lay_recientes.setSpacing(2)
        self.main_layout.addWidget(self.container_recientes)
        self._render_carpetas_recientes()

        # ── 3. SECCIÓN UNIDADES (Dinámica) ──
        self.lbl_unidades = QLabel("UNIDADES")
        self.lbl_unidades.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self.lbl_unidades.setStyleSheet(f"color: {self.colores['fg_secundario']}; margin-top: 10px; margin-bottom: 3px; letter-spacing: 1px;")
        self.main_layout.addWidget(self.lbl_unidades)
        
        self.container_unidades = QWidget()
        self.lay_unidades = QVBoxLayout(self.container_unidades)
        self.lay_unidades.setContentsMargins(0, 0, 0, 0)
        self.lay_unidades.setSpacing(2)
        self.main_layout.addWidget(self.container_unidades)
        
        self.refrescar_unidades()

        self.main_layout.addStretch()
        
        # ── 4. ACCIONES ──
        lbl_acc = QLabel("ACCIONES")
        lbl_acc.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_acc.setStyleSheet(f"color: {self.colores['fg_secundario']}; margin: 12px 0 6px 0; letter-spacing: 1px;")
        self.main_layout.addWidget(lbl_acc)
        
        action_btn_style = f"""
            QPushButton {{
                background: {self.colores['bg_terciario']}; color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 8px 10px;
                font-size: 10px; font-weight: bold; text-align: left;
            }}
            QPushButton:hover {{ background: {self.colores['acento']}; color: white; border: none; }}
        """
        
        acciones = [
            ("🌳 EXPLORAR ÁRBOL", self.callbacks.get("mostrar_arbol_carpetas")),
            ("📄 NUEVO ARCHIVO", self.callbacks.get("nuevo_archivo")),
            ("📁 NUEVA CARPETA", self.callbacks.get("nueva_carpeta")),
        ]
        
        for name, callback in acciones:
            btn = QPushButton(name)
            btn.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
            btn.setStyleSheet(action_btn_style)
            btn.clicked.connect(callback)
            self.main_layout.addWidget(btn)

    def registrar_carpeta_reciente(self, ruta):
        """Añade una ruta al historial de las últimas 4 carpetas abiertas."""
        if not ruta or str(ruta) in ("trash", "PAPELERA_RECICLAJE") or str(ruta).startswith("shell:"):
            return
        try:
            p_str = str(Path(ruta).resolve())
            if not os.path.exists(p_str) or not os.path.isdir(p_str):
                return
            if p_str in self.historial_recientes:
                self.historial_recientes.remove(p_str)
            self.historial_recientes.insert(0, p_str)
            self.historial_recientes = self.historial_recientes[:4]
            self._render_carpetas_recientes()
        except Exception:
            pass

    def _render_carpetas_recientes(self):
        """Renderiza los botones de las últimas 4 carpetas abiertas"""
        while self.lay_recientes.count():
            item = self.lay_recientes.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not self.historial_recientes:
            lbl_vacio = QLabel("(Sin recientes)")
            lbl_vacio.setFont(QFont(self.font_family, 8))
            lbl_vacio.setStyleSheet(f"color: {self.colores['fg_secundario']}; padding: 2px 10px; font-style: italic;")
            self.lay_recientes.addWidget(lbl_vacio)
            return

        for p_str in self.historial_recientes:
            p = Path(p_str)
            nombre = p.name or p_str
            btn = QPushButton(f"📁 {nombre}")
            btn.setToolTip(p_str)
            btn.setFont(QFont(self.font_family, 8))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: #D1D5DB; border: none;
                    text-align: left; padding: 4px 8px; border-radius: 4px;
                    font-size: 11px;
                }}
                QPushButton:hover {{ background: rgba(255, 255, 255, 0.05); color: {self.colores['acento']}; }}
            """)
            btn.clicked.connect(lambda checked, path=p_str: self.callbacks.get("ir_a_ruta_manual")(path))
            self.lay_recientes.addWidget(btn)

    def _crear_boton_acceso(self, text, path):
        btn = QPushButton(text)
        btn.setFont(QFont(self.font_family, 9))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(self.side_btn_style)
        btn.clicked.connect(lambda checked, p=path: self.callbacks.get("ir_a_ruta_manual")(p))
        return btn

    def _on_mtp_actualizado(self):
        QTimer.singleShot(0, self.refrescar_unidades)

    def refrescar_unidades(self):
        """Detecta unidades montadas (USB, Celulares, Discos) y dispositivos móviles MTP sin bloquear la UI"""
        try:
            from ..utils.drive_detector import obtener_todas_las_unidades, iniciar_escaneo_mtp_asincrono
            unidades = obtener_todas_las_unidades(incluir_mtp_cache=True)
            actuales = [(texto, ruta) for texto, ruta, _ in unidades]
            # Lanzar escaneo MTP en segundo plano sin congelar la app
            iniciar_escaneo_mtp_asincrono(on_finished=self._on_mtp_actualizado)
        except Exception as e:
            print(f"Error al obtener unidades en sidebar: {e}")
            actuales = []
            
        if actuales != getattr(self, "_ultimas_unidades", None):
            self._ultimas_unidades = actuales
            while self.lay_unidades.count():
                item = self.lay_unidades.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            self.drives_buttons = []
            
            for text, path in actuales:
                btn = self._crear_boton_acceso(text, path)
                self.lay_unidades.addWidget(btn)
                self.drives_buttons.append(btn)
