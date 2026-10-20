import os
import sys
import subprocess
import platform
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class TabPacmanGame(QWidget):
    """Submódulo Pacman Arcade (Lanzador Pygame embebido)"""
    def __init__(self, parent, context, colores, ruta_usuario):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.ruta_usuario = ruta_usuario
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        lbl_tit = QLabel("🕹️ PACMAN ARCADE CLASSIC (MOTOR PYGAME)")
        lbl_tit.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tit)

        card = QFrame()
        card.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 25px;")
        c_lay = QVBoxLayout(card)
        c_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_lay.setSpacing(15)

        lbl_ico = QLabel("🟡 👻 👻 👻")
        lbl_ico.setFont(QFont("Segoe UI Emoji", 32))
        lbl_ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_lay.addWidget(lbl_ico)

        lbl_desc = QLabel("Juego completo de Pacman con laberinto clásico, bolitas de poder y los 4 fantasmas (Blinky, Inky, Pinky, Clyde).\nPresiona el botón inferior para lanzar la ventana de juego.")
        lbl_desc.setFont(QFont(self.font_family, 10))
        lbl_desc.setStyleSheet("color: rgba(255,255,255,0.7);")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_lay.addWidget(lbl_desc)

        self.lbl_pts_pacman = QLabel(f"🏆 Puntos en Pacman: {self._obtener_puntos_pacman()} pts")
        self.lbl_pts_pacman.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_pts_pacman.setStyleSheet("color: #FBBF24;")
        c_lay.addWidget(self.lbl_pts_pacman)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_run = QPushButton("▶ EJECUTAR PACMAN ARCADE")
        btn_run.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_run.setStyleSheet(f"background: {exito}; color: white; border-radius: 8px; padding: 12px 32px; border: none;")
        btn_run.clicked.connect(self._lanzar_pacman)
        btn_row.addWidget(btn_run)

        c_lay.addLayout(btn_row)
        layout.addWidget(card, 1)

    def _obtener_puntos_pacman(self):
        from ..utils.score_manager import ScoreManager
        return ScoreManager(self.ruta_usuario).get_puntos("pacman")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(f"background-color: {colores.get('bg_principal', '#121218')}; color: white;")
        if hasattr(self, 'lbl_pts_pacman'):
            self.lbl_pts_pacman.setText(f"🏆 Puntos en Pacman: {self._obtener_puntos_pacman()} pts")

    def cleanup(self):
        pass

    def _lanzar_pacman(self):
        import shutil
        import subprocess
        from controlador.utils.paths import get_resource_path
        
        script_path = None
        bases = [
            Path(__file__).parent,
            get_resource_path(),
            Path(sys.executable).parent,
            Path.cwd()
        ]
        for base in bases:
            candidatos = [
                base / "vistas/modulos/minigames/submodulos/PACMAN/main.py",
                base / "vistas" / "modulos" / "minigames" / "submodulos" / "PACMAN" / "main.py",
                base / "minigames" / "PACMAN" / "main.py",
                base / "submodulos" / "PACMAN" / "main.py"
            ]
            for c in candidatos:
                if c.exists():
                    script_path = c
                    break
            if script_path:
                break

        if not script_path:
            try:
                for base in [Path(sys.executable).parent, get_resource_path()]:
                    found = list(base.rglob("PACMAN/main.py"))
                    if found:
                        script_path = found[0]
                        break
            except Exception:
                pass

        if not script_path:
            QMessageBox.critical(self, "Error", f"No se encontró la carpeta del juego de Pacman en la aplicación instalada.\nRuta base: {get_resource_path()}")
            return

        try:
            python_exe = sys.executable
            if getattr(sys, "frozen", False):
                py_sys = shutil.which("pythonw") or shutil.which("python") or shutil.which("py")
                if py_sys:
                    python_exe = py_sys
                else:
                    try:
                        from vistas.modulos.basedatos.submodulos.db_manager import DriverManager
                        cand = DriverManager._find_python()
                        if cand:
                            python_exe = cand
                    except Exception:
                        cand = None

                if not python_exe or python_exe.lower().endswith("multitool.exe"):
                    QMessageBox.warning(
                        self, "Python Requerido",
                        "Para ejecutar el minijuego de Pacman se requiere un intérprete de Python (con pygame) en el sistema."
                    )
                    return

            my_env = os.environ.copy()
            user_dir_str = str(Path(self.ruta_usuario).resolve()) if self.ruta_usuario else ""
            if user_dir_str:
                my_env["MULTITOOL_USER_DIR"] = user_dir_str

            args = [python_exe, str(script_path.resolve())]
            if user_dir_str:
                args.append(user_dir_str)

            subprocess.Popen(args, cwd=str(script_path.parent), env=my_env)

        except Exception as e:
            QMessageBox.critical(self, "Error de Ejecución", f"No se pudo iniciar el juego de Pacman:\n{e}")

    def showEvent(self, event):
        super().showEvent(event)
        self._refrescar_puntos_ui()

    def _refrescar_puntos_ui(self):
        if hasattr(self, 'lbl_pts_pacman'):
            self.lbl_pts_pacman.setText(f"🏆 Puntos en Pacman: {self._obtener_puntos_pacman()} pts")
