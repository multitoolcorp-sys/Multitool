"""
Submódulo Isaac Roguelike: Rendimiento HTML5/JS embebido en PyQt6 con acumulación automática de puntos.
Carga el motor HTML5/Canvas desde 'isaac_game.html' y sincroniza el score con ScoreManager.
"""
import os
import sys
import platform
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QFont

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False
    from PyQt6.QtWidgets import QTextBrowser

from ..utils.score_manager import ScoreManager

class TabIsaacGame(QWidget):
    """Submódulo Isaac Roguelike: Rendimiento Canvas JS en PyQt6 con sistema de puntos y récords."""
    def __init__(self, parent, context, colores, ruta_usuario):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.ruta_usuario = ruta_usuario
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.score_mgr = ScoreManager(self.ruta_usuario)
        self.run_score = 0
        self.last_sync_score = 0

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Barra Superior de Control y Puntuación
        bar = QHBoxLayout()
        bar.setSpacing(12)

        lbl_tit = QLabel("🗡️ THE BINDING OF ISAAC - ROGUELIKE")
        lbl_tit.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 0.5px;")
        bar.addWidget(lbl_tit)

        bar.addStretch()

        self.lbl_run = QLabel("🎮 Partida Actual: 0 pts")
        self.lbl_run.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_run.setStyleSheet("color: #38BDF8; background: rgba(56, 189, 248, 0.12); padding: 4px 10px; border-radius: 6px;")
        bar.addWidget(self.lbl_run)

        self.lbl_cuenta = QLabel(f"🏆 Puntos en Cuenta: {self.score_mgr.get_puntos('isaac')} pts")
        self.lbl_cuenta.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.lbl_cuenta.setStyleSheet("color: #FBBF24; background: rgba(251, 191, 36, 0.12); padding: 4px 10px; border-radius: 6px;")
        bar.addWidget(self.lbl_cuenta)


        btn_reload = QPushButton("🔄 Reiniciar")
        btn_reload.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reload.setStyleSheet("background: rgba(255,255,255,0.1); color: white; border-radius: 6px; padding: 5px 10px; border: none;")
        btn_reload.clicked.connect(self._reiniciar_juego)
        bar.addWidget(btn_reload)

        layout.addLayout(bar)

        # Preparar archivo HTML
        html_file = Path(__file__).parent / "isaac_game.html"
        if not html_file.exists():
            html_content = "<h2>Falta isaac_game.html</h2>"
        else:
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()

        self.temp_dir = tempfile.gettempdir()
        self.temp_html_path = os.path.join(self.temp_dir, "isaac_game_render.html")
        with open(self.temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Embeber WebView2 o WebEngine
        self.web_view = None
        try:
            from vistas.modulos.navegador.utils.webview2_widget import WebView2Widget, WEBVIEW2_AVAILABLE
            if WEBVIEW2_AVAILABLE:
                self.web_view = WebView2Widget(self, initial_url=QUrl.fromLocalFile(self.temp_html_path).toString())
                self.web_view.titleChanged.connect(self._on_title_changed)
                layout.addWidget(self.web_view, 1)
                return
        except Exception as e:
            print(f"[Isaac] WebView2 no disponible: {e}")

        if HAS_WEBENGINE:
            self.web_view = QWebEngineView()
            self.web_view.setUrl(QUrl.fromLocalFile(self.temp_html_path))
            self.web_view.titleChanged.connect(self._on_title_changed)
            layout.addWidget(self.web_view, 1)
        else:
            self.browser = QTextBrowser()
            self.browser.setOpenExternalLinks(True)
            self.browser.setHtml(html_content)
            layout.addWidget(self.browser, 1)

    def _on_title_changed(self, title):
        """Captura los eventos de puntuación disparados por el motor HTML5 Canvas."""
        if not title or not title.startswith("ISAAC_SCORE:"):
            return

        partes = title.split(":")
        try:
            score_val = int(partes[1])
            self.run_score = score_val
            self.lbl_run.setText(f"🎮 Partida Actual: {score_val} pts")

            # Acumular delta a la cuenta
            delta = score_val - self.last_sync_score
            if delta > 0:
                pts_ganados = max(1, delta // 10)
                self.score_mgr.sumar_puntos("isaac", pts_ganados)
                self.score_mgr.actualizar_highscore("isaac", score_val)
                self.last_sync_score = score_val
                self.lbl_cuenta.setText(f"🏆 Puntos en Cuenta: {self.score_mgr.get_puntos('isaac')} pts")

            if len(partes) > 2 and partes[2] in ["restart", "dead"]:
                self.last_sync_score = 0
        except Exception as e:
            print(f"[Isaac] Error al sincronizar puntuación: {e}")


    def _reiniciar_juego(self):
        if self.web_view:
            if hasattr(self.web_view, "load_url"):
                self.web_view.load_url(QUrl.fromLocalFile(self.temp_html_path).toString())
            elif hasattr(self.web_view, "setUrl"):
                self.web_view.setUrl(QUrl.fromLocalFile(self.temp_html_path))
        self.run_score = 0
        self.last_sync_score = 0
        self.lbl_run.setText("🎮 Partida Actual: 0 pts")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(f"background-color: {colores.get('bg_principal', '#121218')}; color: white;")
        if hasattr(self, 'lbl_cuenta'):
            self.lbl_cuenta.setText(f"🏆 Puntos en Cuenta: {self.score_mgr.get_puntos('isaac')} pts")

    def cleanup(self):
        if self.run_score > self.last_sync_score:
            delta = self.run_score - self.last_sync_score
            pts = max(1, delta // 10)
            self.score_mgr.sumar_puntos("isaac", pts)
            self.score_mgr.actualizar_highscore("isaac", self.run_score)