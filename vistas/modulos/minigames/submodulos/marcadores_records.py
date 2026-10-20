import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..utils.score_manager import ScoreManager

class MarcadoresRecordsSubmodule(QWidget):
    """Submódulo 6: Salón de la Fama, Marcadores & Récords Locales vinculados a la Cuenta del Usuario"""
    def __init__(self, parent, context, colores, ruta_usuario):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.ruta_usuario = Path(ruta_usuario)
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.score_mgr = ScoreManager(self.ruta_usuario)

        self.inicializar_ui()
        self.cargar_records()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_tit = QLabel("🏆 SALÓN DE LA FAMA & RÉCORDS DE LA CUENTA")
        lbl_tit.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        hdr.addWidget(lbl_tit)

        hdr.addStretch()

        self.lbl_total_banner = QLabel("💰 TOTAL CUENTA: 0 PTS")
        self.lbl_total_banner.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_total_banner.setStyleSheet("color: #FBBF24; background: rgba(251,191,36,0.12); padding: 6px 14px; border-radius: 6px;")
        hdr.addWidget(self.lbl_total_banner)

        btn_refresh = QPushButton("🔄 Sincronizar Récords")
        btn_refresh.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 6px 14px; border: none;")
        btn_refresh.clicked.connect(self.cargar_records)
        hdr.addWidget(btn_refresh)

        layout.addLayout(hdr)

        # Tabla de Marcadores
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["Juego", "Puntos Acumulados", "Récord / Victorias", "Estado Registrado"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setFont(QFont(self.font_family, 9))
        self.tabla.setStyleSheet(f"""
            QTableWidget {{
                background-color: {bg_sec};
                color: white; border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px; gridline-color: rgba(255,255,255,0.05);
            }}
            QHeaderView::section {{
                background-color: {bg_terc}; color: {acento}; font-weight: bold; padding: 8px; border: none;
            }}
        """)
        layout.addWidget(self.tabla, 1)

    def cargar_records(self):
        self.tabla.setRowCount(0)
        self.score_mgr.sincronizar_archivos()

        total = self.score_mgr.get_total_puntos()
        self.lbl_total_banner.setText(f"💰 TOTAL CUENTA: {total} PTS")

        extras_data = self.score_mgr.data_extras
        minigames_data = self.score_mgr.data_minigames

        juegos_info = [
            ("👾 Space Invaders Arcade", self.score_mgr.get_puntos("space_invaders"), f"Récord: {extras_data.get('space_invaders_highscore', 0)} pts", "✅ Sincronizado en Cuenta"),
            ("🚀 Galaga Arcade", self.score_mgr.get_puntos("galaga"), f"Récord: {extras_data.get('galaga_highscore', 0)} pts", "✅ Sincronizado en Cuenta"),
            ("☄️ Asteroids Arcade", self.score_mgr.get_puntos("asteroids"), f"Récord: {extras_data.get('asteroids_highscore', 0)} pts", "✅ Sincronizado en Cuenta"),
            ("🧱 Tetris", self.score_mgr.get_puntos("tetris"), f"Récord: {extras_data.get('tetris_highscore', 0)} pts", "✅ Sincronizado en Cuenta"),
            ("🕹️ Pacman Arcade", self.score_mgr.get_puntos("pacman"), f"Récord: {extras_data.get('pacman_highscore', 0)} pts", "✅ Sincronizado en Cuenta"),
            ("🗡️ Isaac Roguelike", self.score_mgr.get_puntos("isaac"), f"Récord: {extras_data.get('isaac_highscore', 0)} pts", "✅ Sincronizado en Cuenta"),
            ("🐍 Snake Arcade", self.score_mgr.get_puntos("snake"), f"Récord: {extras_data.get('snake_highscore_facil', 0)} pts", "✅ Sincronizado en Cuenta"),
            ("💣 Buscaminas Classic", self.score_mgr.get_puntos("buscaminas"), f"Mejor Tiempo: {extras_data.get('buscaminas_highscore_facil', 0)}s", "✅ Sincronizado en Cuenta"),
            ("🎴 Memory / Parejas", self.score_mgr.get_puntos("memory"), "Puntos de Memoria", "✅ Sincronizado en Cuenta"),
            ("🔴 Damas Tradicionales 1v1", self.score_mgr.get_puntos("damas"), f"Victorias IA: {minigames_data.get('damas', {}).get('vs_ia_ganadas', 0)}", "✅ Sincronizado en Cuenta"),
            ("♟️ Ajedrez Clásico 1v1", self.score_mgr.get_puntos("ajedrez"), "Victorias 1v1", "✅ Sincronizado en Cuenta"),
            ("❌ Tres en Raya 1v1", self.score_mgr.get_puntos("tres_en_raya"), "Victorias 1v1", "✅ Sincronizado en Cuenta"),
            ("🚢 Battleship (Hundir la Flota)", self.score_mgr.get_puntos("battleship"), "Victorias 1v1", "✅ Sincronizado en Cuenta"),
            ("❓ Adivina Quién 1v1", self.score_mgr.get_puntos("adivina_quien"), "Partidas Ganadas", "✅ Sincronizado en Cuenta"),
            ("🔤 Juego del Ahorcado", self.score_mgr.get_puntos("ahorcado"), "Palabras Acertadas", "✅ Sincronizado en Cuenta"),
            ("🎰 Casino Royal", self.score_mgr.get_puntos("casino"), f"Récord: {extras_data.get('casino_highscore', 0)} pts", "✅ Slots / Ruleta / BJ")
        ]

        for r, (juego, pts, record, estado) in enumerate(juegos_info):
            self.tabla.insertRow(r)
            self.tabla.setItem(r, 0, QTableWidgetItem(juego))
            self.tabla.setItem(r, 1, QTableWidgetItem(f"{pts} pts"))
            self.tabla.setItem(r, 2, QTableWidgetItem(record))
            self.tabla.setItem(r, 3, QTableWidgetItem(estado))

    def actualizar_tema(self, colores):
        self.colores = colores
        bg_main = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        self.cargar_records()

    def cleanup(self):
        pass
