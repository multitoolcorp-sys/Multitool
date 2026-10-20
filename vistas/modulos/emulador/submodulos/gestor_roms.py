import os
import platform
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QFrame, QGroupBox, QMessageBox, QFileDialog,
    QListWidget, QListWidgetItem, QStackedWidget, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

class GestorRomsSubmodule(QWidget):
    """Submódulo 3: Biblioteca de ROMs de la Comunidad con Vista Sin Selección & Lanzador N64"""
    def __init__(self, parent, context, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.rom_files = []
        self.selected_rom_path = None

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')
        error = self.colores.get('error', '#F87171')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ── PANEL IZQUIERDO: Explorador de ROMs & Filtros (330px) ──
        left_panel = QFrame()
        left_panel.setFixedWidth(330)
        left_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
            }}
        """)
        l_lay = QVBoxLayout(left_panel)
        l_lay.setContentsMargins(12, 14, 12, 14)
        l_lay.setSpacing(10)

        # Header de la biblioteca
        lbl_biblio = QLabel("📁 BIBLIOTECA DE ROMS")
        lbl_biblio.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_biblio.setStyleSheet(f"color: {acento}; border: none;")
        l_lay.addWidget(lbl_biblio)

        # Barra de Búsqueda
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Filtrar juegos por nombre...")
        self.txt_buscar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg_terc};
                color: white; border-radius: 8px; padding: 6px 10px;
                border: 1px solid rgba(255,255,255,0.1); font-size: 11px;
            }}
            QLineEdit:focus {{ border: 1px solid {acento}; }}
        """)
        self.txt_buscar.textChanged.connect(self._filtrar_lista)
        l_lay.addWidget(self.txt_buscar)

        # Filtro de Formato
        self.cb_filtro = QComboBox()
        self.cb_filtro.addItems(["Todos los Formatos", "CHIP-8 (.ch8 / .rom)", "Nintendo 64 (.n64 / .z64)"])
        self.cb_filtro.setStyleSheet(f"""
            QComboBox {{
                background-color: {bg_terc}; color: white; border-radius: 6px;
                padding: 6px; border: 1px solid rgba(255,255,255,0.08); font-size: 10px;
            }}
        """)
        self.cb_filtro.currentIndexChanged.connect(self._filtrar_lista)
        l_lay.addWidget(self.cb_filtro)

        # Lista de ROMs
        self.list_roms = QListWidget()
        self.list_roms.setFont(QFont(self.font_family, 9))
        self.list_roms.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_main};
                color: white; border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
            }}
            QListWidget::item {{
                padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.04);
            }}
            QListWidget::item:selected {{
                background-color: {acento}; color: white; border-radius: 4px;
            }}
        """)
        self.list_roms.itemSelectionChanged.connect(self._on_rom_selected)
        self.list_roms.itemDoubleClicked.connect(lambda item: self._jugar_rom_actual())
        l_lay.addWidget(self.list_roms, 1)

        # Botones de Acción de Lista
        row_actions = QHBoxLayout()
        row_actions.setSpacing(6)

        btn_examinar = QPushButton("📂 Cargar")
        btn_examinar.setToolTip("Cargar archivo de ROM manualmente")
        btn_examinar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_examinar.setStyleSheet(f"""
            QPushButton {{
                background: {bg_terc}; color: white; padding: 6px 10px;
                border-radius: 6px; font-size: 10px; font-weight: bold; border: none;
            }}
            QPushButton:hover {{ background: {acento}; }}
        """)
        btn_examinar.clicked.connect(self.callbacks.get("cargar_archivo_manual", lambda: None))
        row_actions.addWidget(btn_examinar)

        btn_carpeta = QPushButton("📁 Carpeta")
        btn_carpeta.setToolTip("Abrir carpeta de ROMs en el Explorador")
        btn_carpeta.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_carpeta.setStyleSheet(btn_examinar.styleSheet())
        btn_carpeta.clicked.connect(self.callbacks.get("abrir_carpeta_roms", lambda: None))
        row_actions.addWidget(btn_carpeta)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setToolTip("Actualizar lista de ROMs")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setFixedWidth(32)
        btn_refresh.setStyleSheet(btn_examinar.styleSheet())
        btn_refresh.clicked.connect(self.callbacks.get("escanear_roms", lambda: None))
        row_actions.addWidget(btn_refresh)

        l_lay.addLayout(row_actions)

        # Compatibilidad con callbacks antiguos (ComboBox oculto y botón proxy)
        self.cb_comunidad = QComboBox()
        self.cb_comunidad.hide()
        l_lay.addWidget(self.cb_comunidad)

        self.btn_play_comunidad = QPushButton("▶ JUGAR SELECCIONADO")
        self.btn_play_comunidad.hide()
        l_lay.addWidget(self.btn_play_comunidad)

        main_layout.addWidget(left_panel)

        # ── PANEL DERECHO: QStackedWidget (Página 0: Sin Selección / Página 1: Detalle) ──
        self.stack_roms = QStackedWidget()
        self.stack_roms.setStyleSheet("background: transparent;")

        # ── PÁGINA 0: VISTA VACÍA SIN SELECCIÓN (Estilo Notas) ──
        self.widget_vacio = self._build_widget_vacio()
        self.stack_roms.addWidget(self.widget_vacio)

        # ── PÁGINA 1: DETALLE DE ROM SELECCIONADA ──
        self.widget_detalle = self._build_widget_detalle()
        self.stack_roms.addWidget(self.widget_detalle)

        main_layout.addWidget(self.stack_roms, 1)

        # Iniciar en vista sin selección por defecto
        self.stack_roms.setCurrentWidget(self.widget_vacio)

    def _build_widget_vacio(self):
        """Construye la vista vacía informativa (sin selección activa)"""
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')

        w = QFrame()
        w.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
            }}
        """)
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(14)

        ico_empty = QLabel("🕹️")
        ico_empty.setFont(QFont("Segoe UI Emoji", 48))
        ico_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico_empty.setStyleSheet("background: transparent; color: #6366F1;")
        lay.addWidget(ico_empty)

        lbl_tit = QLabel("Biblioteca de Juegos Retro")
        lbl_tit.setFont(QFont(self.font_family, 18, QFont.Weight.Bold))
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_tit.setStyleSheet("color: #E2E2E2; border: none;")
        lay.addWidget(lbl_tit)

        lbl_sub = QLabel(
            "Selecciona una ROM de la lista izquierda para consultar sus detalles técnicos y jugarla, "
            "o arrastra archivos .ch8 / .rom / .n64 a la carpeta de ROMs para que aparezcan automáticamente."
        )
        lbl_sub.setFont(QFont(self.font_family, 10))
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("color: #AAB0B8; max-width: 480px; border: none; line-height: 1.4;")
        lay.addWidget(lbl_sub)

        lay.addSpacing(8)

        # Botones de Acción Rápida
        row_quick = QHBoxLayout()
        row_quick.setSpacing(10)
        row_quick.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_q_examinar = QPushButton("📂 Cargar ROM Externa")
        btn_q_examinar.setFixedHeight(36)
        btn_q_examinar.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_q_examinar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_examinar.setStyleSheet(f"""
            QPushButton {{
                background: {acento}; color: white; border-radius: 18px; padding: 0 18px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_q_examinar.clicked.connect(self.callbacks.get("cargar_archivo_manual", lambda: None))
        row_quick.addWidget(btn_q_examinar)

        btn_q_carpeta = QPushButton("📁 Abrir Carpeta de ROMs")
        btn_q_carpeta.setFixedHeight(36)
        btn_q_carpeta.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_q_carpeta.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_carpeta.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.06); color: white; border-radius: 18px; padding: 0 16px; border: 1px solid rgba(255,255,255,0.1);
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.12); }}
        """)
        btn_q_carpeta.clicked.connect(self.callbacks.get("abrir_carpeta_roms", lambda: None))
        row_quick.addWidget(btn_q_carpeta)

        btn_q_n64 = QPushButton("⚙ Configurar N64")
        btn_q_n64.setFixedHeight(36)
        btn_q_n64.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_q_n64.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_n64.setStyleSheet(f"""
            QPushButton {{
                background: rgba(251,191,36,0.15); color: #FBBF24; border-radius: 18px; padding: 0 16px; border: 1px solid rgba(251,191,36,0.3);
            }}
            QPushButton:hover {{ background: rgba(251,191,36,0.25); }}
        """)
        btn_q_n64.clicked.connect(self.callbacks.get("configurar_emulador_n64", lambda: None))
        row_quick.addWidget(btn_q_n64)

        lay.addLayout(row_quick)

        lay.addSpacing(10)

        # Estado del Emulador N64
        self.lbl_n64_status = QLabel("🎮 Emulador N64: Sin configurar (usa Configurar N64 para asociar Project64/RetroArch)")
        self.lbl_n64_status.setFont(QFont(self.font_family, 9))
        self.lbl_n64_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_n64_status.setStyleSheet("color: rgba(255,255,255,0.4); border: none;")
        lay.addWidget(self.lbl_n64_status)

        lbl_esc_hint = QLabel("💡 Presiona la tecla Esc para volver a esta pantalla sin selección")
        lbl_esc_hint.setFont(QFont(self.font_family, 8))
        lbl_esc_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_esc_hint.setStyleSheet("color: rgba(255,255,255,0.25); border: none;")
        lay.addWidget(lbl_esc_hint)

        return w

    def _build_widget_detalle(self):
        """Construye la tarjeta de detalles cuando hay una ROM seleccionada"""
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')
        error = self.colores.get('error', '#F87171')

        w = QFrame()
        w.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
            }}
        """)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(30, 30, 30, 30)
        lay.setSpacing(16)

        # Badge de Formato
        self.lbl_badge_formato = QLabel("👾 CHIP-8 ARCADE")
        self.lbl_badge_formato.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_badge_formato.setStyleSheet(f"""
            background: rgba(99,102,241,0.2); color: {acento};
            padding: 4px 12px; border-radius: 6px; border: 1px solid {acento};
        """)
        self.lbl_badge_formato.setFixedHeight(26)
        lay.addWidget(self.lbl_badge_formato)

        # Nombre del Juego
        self.lbl_det_nombre = QLabel("Nombre_Juego.ch8")
        self.lbl_det_nombre.setFont(QFont(self.font_family, 16, QFont.Weight.Bold))
        self.lbl_det_nombre.setStyleSheet("color: #FFFFFF; border: none;")
        self.lbl_det_nombre.setWordWrap(True)
        lay.addWidget(self.lbl_det_nombre)

        # Tarjeta de Propiedades
        card_info = QFrame()
        card_info.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_terc};
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 8px; padding: 12px;
            }}
            QLabel {{ border: none; font-size: 11px; }}
        """)
        c_lay = QVBoxLayout(card_info)
        c_lay.setSpacing(8)

        self.lbl_det_tipo = QLabel("Formato: CHIP-8 ROM nativa")
        c_lay.addWidget(self.lbl_det_tipo)

        self.lbl_det_size = QLabel("Tamaño: 0 KB")
        c_lay.addWidget(self.lbl_det_size)

        self.lbl_det_ruta = QLabel("Ruta: -")
        self.lbl_det_ruta.setWordWrap(True)
        self.lbl_det_ruta.setStyleSheet("color: rgba(255,255,255,0.5);")
        c_lay.addWidget(self.lbl_det_ruta)

        lay.addWidget(card_info)

        lay.addStretch()

        # Botón Principal: JUGAR ESTE JUEGO
        self.btn_det_jugar = QPushButton("▶ JUGAR ESTE JUEGO")
        self.btn_det_jugar.setFixedHeight(44)
        self.btn_det_jugar.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.btn_det_jugar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_det_jugar.setStyleSheet(f"""
            QPushButton {{
                background: {exito}; color: white; border-radius: 8px; border: none; font-weight: bold;
            }}
            QPushButton:hover {{ background: #10B981; }}
        """)
        self.btn_det_jugar.clicked.connect(self._jugar_rom_actual)
        lay.addWidget(self.btn_det_jugar)

        # Fila de Acciones Secundarias (Eliminar, Abrir ubicación, Volver)
        row_sub = QHBoxLayout()
        row_sub.setSpacing(10)

        btn_det_del = QPushButton("🗑️ Eliminar ROM")
        btn_det_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_det_del.setFixedHeight(34)
        btn_det_del.setStyleSheet(f"""
            QPushButton {{
                background: rgba(248,113,113,0.15); color: {error}; border: 1px solid rgba(248,113,113,0.3); border-radius: 6px; padding: 0 14px; font-weight: bold; font-size: 10px;
            }}
            QPushButton:hover {{ background: rgba(248,113,113,0.25); }}
        """)
        btn_det_del.clicked.connect(self._eliminar_rom_actual)
        row_sub.addWidget(btn_det_del)

        btn_det_reveal = QPushButton("📂 Ver en Carpeta")
        btn_det_reveal.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_det_reveal.setFixedHeight(34)
        btn_det_reveal.setStyleSheet(f"""
            QPushButton {{
                background: {bg_terc}; color: white; border-radius: 6px; padding: 0 14px; font-size: 10px; border: none;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.15); }}
        """)
        btn_det_reveal.clicked.connect(self._abrir_ubicacion_actual)
        row_sub.addWidget(btn_det_reveal)

        row_sub.addStretch()

        btn_det_esc = QPushButton("🔙 Volver (Esc)")
        btn_det_esc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_det_esc.setFixedHeight(34)
        btn_det_esc.setStyleSheet(btn_det_reveal.styleSheet())
        btn_det_esc.clicked.connect(self.deseleccionar)
        row_sub.addWidget(btn_det_esc)

        lay.addLayout(row_sub)

        return w

    def actualizar_lista_roms(self, rom_files=None):
        """Alimenta la lista de ROMs y sincroniza con el selector"""
        if rom_files is not None:
            self.rom_files = rom_files
        self._filtrar_lista()

        # Sincronizar combobox proxy para compatibilidad
        self.cb_comunidad.clear()
        for f in self.rom_files:
            self.cb_comunidad.addItem(f.name)
        if not self.rom_files:
            self.cb_comunidad.addItem("Sin juegos")
            self.deseleccionar()

        self._actualizar_estado_n64()

    def _filtrar_lista(self):
        """Filtra los juegos en pantalla según el texto y formato"""
        query = self.txt_buscar.text().strip().lower()
        filtro_idx = self.cb_filtro.currentIndex()

        self.list_roms.clear()
        for p in self.rom_files:
            name_lower = p.name.lower()
            if query and query not in name_lower:
                continue

            suffix = p.suffix.lower()
            if filtro_idx == 1 and suffix not in [".ch8", ".rom", ".bin"]:
                continue
            elif filtro_idx == 2 and suffix not in [".n64", ".z64"]:
                continue

            ico_str = "🎮" if suffix in [".n64", ".z64"] else "👾"
            size_kb = max(1, p.stat().st_size // 1024) if p.exists() else 0
            size_str = f"{size_kb} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"

            item = QListWidgetItem(f"{ico_str} {p.name}  ({size_str})")
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.list_roms.addItem(item)

        if self.list_roms.count() == 0 or not self.list_roms.currentItem():
            self.deseleccionar()

    def _on_rom_selected(self):
        item = self.list_roms.currentItem()
        if not item:
            self.deseleccionar()
            return

        path_str = item.data(Qt.ItemDataRole.UserRole)
        if not path_str:
            self.deseleccionar()
            return

        p = Path(path_str)
        self.selected_rom_path = p
        suffix = p.suffix.lower()

        is_n64 = suffix in [".n64", ".z64"]
        if is_n64:
            self.lbl_badge_formato.setText("🎮 NINTENDO 64 (3D EXTERNO)")
            self.lbl_badge_formato.setStyleSheet("background: rgba(251,191,36,0.15); color: #FBBF24; padding: 4px 12px; border-radius: 6px; border: 1px solid #FBBF24;")
            self.lbl_det_tipo.setText("Formato: ROM Nintendo 64 (.n64 / .z64)")
        else:
            self.lbl_badge_formato.setText("👾 CHIP-8 ARCADE (NATIVO)")
            self.lbl_badge_formato.setStyleSheet(f"background: rgba(99,102,241,0.2); color: {self.colores.get('acento', '#6366F1')}; padding: 4px 12px; border-radius: 6px; border: 1px solid {self.colores.get('acento', '#6366F1')};")
            self.lbl_det_tipo.setText("Formato: ROM CHIP-8 nativa (.ch8 / .rom / .bin)")

        self.lbl_det_nombre.setText(p.name)

        if p.exists():
            size_bytes = p.stat().st_size
            size_str = f"{size_bytes} bytes ({size_bytes / 1024:.1f} KB)" if size_bytes < 1048576 else f"{size_bytes / (1024 * 1024):.2f} MB"
            self.lbl_det_size.setText(f"Tamaño: {size_str}")
        else:
            self.lbl_det_size.setText("Tamaño: Desconocido")

        self.lbl_det_ruta.setText(f"Ubicación: {p.parent}")

        # Sincronizar cb_comunidad
        idx = self.cb_comunidad.findText(p.name)
        if idx >= 0:
            self.cb_comunidad.setCurrentIndex(idx)

        self.stack_roms.setCurrentWidget(self.widget_detalle)

    def _jugar_rom_actual(self):
        if self.selected_rom_path and self.selected_rom_path.exists():
            if "play_comunidad_game" in self.callbacks:
                idx = self.cb_comunidad.findText(self.selected_rom_path.name)
                if idx >= 0:
                    self.cb_comunidad.setCurrentIndex(idx)
                self.callbacks["play_comunidad_game"]()

    def _eliminar_rom_actual(self):
        if not self.selected_rom_path or not self.selected_rom_path.exists():
            return

        res = QMessageBox.question(
            self, "Eliminar ROM",
            f"¿Estás seguro de que deseas eliminar permanentemente la ROM '{self.selected_rom_path.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            try:
                self.selected_rom_path.unlink()
                QMessageBox.information(self, "ROM Eliminada", f"Se eliminó '{self.selected_rom_path.name}' correctamente.")
                self.deseleccionar()
                if "escanear_roms" in self.callbacks:
                    self.callbacks["escanear_roms"]()
            except Exception as e:
                QMessageBox.critical(self, "Error al eliminar", f"No se pudo eliminar el archivo:\n{e}")

    def _abrir_ubicacion_actual(self):
        if self.selected_rom_path and self.selected_rom_path.parent.exists():
            path_str = str(self.selected_rom_path.parent.resolve())
            if platform.system() == "Windows": os.startfile(path_str)
            else: subprocess.Popen(["xdg-open", path_str])

    def _actualizar_estado_n64(self):
        config = getattr(self.context, "config", {})
        n64_path = config.get("ruta_emulador_n64", "")
        if n64_path and os.path.exists(n64_path):
            self.lbl_n64_status.setText(f"🎮 Emulador N64 Asociado: <b>{Path(n64_path).name}</b> ({n64_path})")
            self.lbl_n64_status.setStyleSheet("color: #34D399; border: none;")
        else:
            self.lbl_n64_status.setText("🎮 Emulador N64: Sin configurar (usa Configurar N64 para asociar Project64/RetroArch)")
            self.lbl_n64_status.setStyleSheet("color: rgba(255,255,255,0.4); border: none;")

    def deseleccionar(self):
        """Deselecciona la ROM activa y retorna a la vista vacía por defecto"""
        self.list_roms.clearSelection()
        self.selected_rom_path = None
        self.stack_roms.setCurrentWidget(self.widget_vacio)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.deseleccionar()
            event.accept()
            return
        super().keyPressEvent(event)

    def actualizar_tema(self, colores: dict = None):
        if colores:
            self.colores = colores
            self.setStyleSheet(f"background-color: {colores.get('bg_principal', '#121218')}; color: white;")

    def cleanup(self):
        pass
