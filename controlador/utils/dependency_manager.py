"""
dependency_manager.py - Gestor universal de dependencias modulares para MultiTool.
Permite que cualquier módulo declare sus librerías requeridas en requirements.txt,
detecta dependencias faltantes e instala los paquetes en un directorio local aislado (.libs/)
utilizando 'pip --target', manteniendo la integración 100% nativa con PyQt6 sin contaminar
el sistema ni requerir entornos virtuales pesados.
"""

import os
import sys
import re
import shutil
import subprocess
import importlib.util
from pathlib import Path
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QTextEdit, QFrame
)
from PyQt6.QtGui import QFont


class DependencyInstallerThread(QThread):
    """
    Hilo asíncrono para descargar e instalar dependencias con pip sin bloquear la UI de PyQt6.
    """
    progreso_linea = pyqtSignal(str)
    progreso_porcentaje = pyqtSignal(int)
    finalizado = pyqtSignal(bool, str)

    def __init__(self, python_exe: Path, requirements_file: Path, target_dir: Path):
        super().__init__()
        self.python_exe = Path(python_exe)
        self.requirements_file = Path(requirements_file)
        self.target_dir = Path(target_dir)

    def run(self):
        try:
            self.target_dir.mkdir(parents=True, exist_ok=True)
            self.progreso_linea.emit(f"Preparando instalación en: {self.target_dir.name}")
            self.progreso_porcentaje.emit(10)

            cmd = [
                str(self.python_exe),
                "-m", "pip",
                "install",
                "-r", str(self.requirements_file),
                "--target", str(self.target_dir),
                "--no-user",
                "--upgrade",
                "--no-warn-script-location"
            ]

            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW

            self.progreso_linea.emit(f"Ejecutando pip install...")
            self.progreso_porcentaje.emit(25)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                creationflags=creationflags
            )

            current_pct = 25
            if process.stdout:
                for line in process.stdout:
                    cleaned = line.strip()
                    if cleaned:
                        self.progreso_linea.emit(cleaned)
                        if "Downloading" in cleaned:
                            current_pct = min(current_pct + 8, 75)
                            self.progreso_porcentaje.emit(current_pct)
                        elif "Installing" in cleaned:
                            current_pct = min(current_pct + 10, 90)
                            self.progreso_porcentaje.emit(current_pct)

            process.wait()

            if process.returncode == 0:
                self.progreso_porcentaje.emit(100)
                self.progreso_linea.emit("¡Instalación completada exitosamente!")
                self.finalizado.emit(True, "Dependencias instaladas con éxito.")
            else:
                self.progreso_porcentaje.emit(100)
                self.finalizado.emit(False, f"pip finalizó con código de error {process.returncode}")

        except Exception as e:
            self.finalizado.emit(False, f"Error durante la instalación: {e}")


class DependencyManager:
    """
    Controlador central de análisis, aislamiento y gestión de dependencias por módulo.
    """

    @staticmethod
    def normalizar_nombre_paquete(req_line: str) -> tuple[str, str]:
        """
        Extrae el nombre del paquete y su especificación de versión a partir de una línea de requirements.txt.
        Ejemplo: 'pypdf>=4.0.0' -> ('pypdf', '>=4.0.0')
        """
        line = req_line.split("#")[0].strip()
        if not line or line.startswith("-"):
            return "", ""

        # Manejar extras: 'requests[security]>=2.20'
        match = re.match(r"^([a-zA-Z0-9_\-\.]+)(?:\[[^\]]+\])?(.*)$", line)
        if match:
            pkg_name = match.group(1).strip().replace("-", "_").lower()
            spec = match.group(2).strip()
            return pkg_name, spec
        return line.lower(), ""

    @classmethod
    def leer_requirements(cls, requirements_file: Path) -> list[tuple[str, str, str]]:
        """
        Lee el archivo requirements.txt y devuelve [(nombre_normalizado, especificacion, linea_original)].
        """
        reqs = []
        if not requirements_file.exists():
            return reqs

        try:
            with open(requirements_file, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    pkg, spec = cls.normalizar_nombre_paquete(line)
                    if pkg:
                        reqs.append((pkg, spec, line))
        except Exception as e:
            print(f"[DependencyManager] Error leyendo {requirements_file}: {e}")

        return reqs

    @classmethod
    def activar_entorno_modulo(cls, module_dir: Path) -> Path | None:
        """
        Inyecta la carpeta .libs/ del módulo al inicio de sys.path si existe.
        Garantiza que el módulo pueda importar sus dependencias locales prioritariamente.
        """
        libs_dir = (Path(module_dir) / ".libs").resolve()
        if libs_dir.exists():
            str_path = str(libs_dir)
            if str_path not in sys.path:
                sys.path.insert(0, str_path)
            return libs_dir
        return None

    PIP_TO_IMPORT_MAP = {
        "pillow": "PIL",
        "opencv_python": "cv2",
        "opencv_contrib_python": "cv2",
        "beautifulsoup4": "bs4",
        "scikit_learn": "sklearn",
        "pyyaml": "yaml",
        "python_dateutil": "dateutil",
        "pypdf2": "PyPDF2",
        "pyqt6": "PyQt6",
        "pyqt5": "PyQt5",
        "pyside6": "PySide6",
        "pyside2": "PySide2",
    }

    @classmethod
    def paquete_esta_disponible(cls, pkg_name: str, module_dir: Path = None) -> bool:
        """
        Comprueba si un paquete o módulo de Python está disponible para ser importado,
        revisando metadatos de pip, importlib y la carpeta .libs/ del módulo.
        """
        if module_dir:
            cls.activar_entorno_modulo(module_dir)

        norm_name = pkg_name.strip().replace("-", "_").lower()

        # 1. Comprobar mediante importlib.metadata (distribución instalada vía pip)
        try:
            import importlib.metadata
            for cand_dist in [norm_name, norm_name.replace("_", "-"), pkg_name]:
                try:
                    importlib.metadata.version(cand_dist)
                    return True
                except Exception:
                    pass
        except Exception:
            pass

        # 2. Comprobar nombres de importación canónicos y alternativos
        candidatos_import = [pkg_name, norm_name]
        if norm_name in cls.PIP_TO_IMPORT_MAP:
            candidatos_import.insert(0, cls.PIP_TO_IMPORT_MAP[norm_name])

        for cand in candidatos_import:
            try:
                spec = importlib.util.find_spec(cand)
                if spec is not None:
                    return True
            except (ImportError, ValueError, AttributeError):
                pass

        # 3. Comprobar físicamente en la carpeta .libs del módulo
        if module_dir:
            libs_dir = Path(module_dir) / ".libs"
            if libs_dir.exists():
                for item in libs_dir.iterdir():
                    clean_item = item.name.lower().split("-")[0].split(".")[0].replace("-", "_")
                    if clean_item in [norm_name, norm_name.replace("_", "-")]:
                        return True

        return False

    @classmethod
    def analizar_dependencias_faltantes(cls, module_dir: Path) -> list[str]:
        """
        Comprueba requirements.txt en module_dir y devuelve una lista con las líneas
        de requerimiento que aún no están disponibles en el sistema.
        """
        req_file = Path(module_dir) / "requirements.txt"
        if not req_file.exists():
            return []

        faltantes = []
        reqs = cls.leer_requirements(req_file)

        for pkg_name, spec, raw_line in reqs:
            if not cls.paquete_esta_disponible(pkg_name, module_dir):
                faltantes.append(raw_line)

        return faltantes

    @classmethod
    def buscar_interprete_python(cls, base_app_dir: Path = None) -> Path | None:
        """
        Localiza un intérprete de Python válido para ejecutar pip.
        Estrategia de resolución:
        1. Directorio runtime/ de MultiTool (entorno portable).
        2. sys.executable si no es una app congelada (desarrollo).
        3. Instalaciones en PATH (python, py, python3).
        4. Rutas comunes en Windows (%LOCALAPPDATA%/Programs/Python).
        """
        base = base_app_dir or Path(__file__).resolve().parents[2]

        # 1. runtime/ de MultiTool
        candidatos_runtime = [
            base / "runtime" / "python.exe",
            base / "runtime" / "bin" / "python",
            base / "runtime" / "python" / "python.exe",
        ]
        for c in candidatos_runtime:
            if c.exists():
                return c

        # 2. sys.executable en desarrollo
        if not getattr(sys, "frozen", False):
            exe = Path(sys.executable)
            if exe.exists() and "python" in exe.name.lower():
                return exe

        # 3. PATH del sistema operativo
        for bin_name in ["python", "py", "python3"]:
            which_res = shutil.which(bin_name)
            if which_res:
                p = Path(which_res)
                if p.exists():
                    return p

        # 4. Windows rutas estándar en LocalAppData
        if sys.platform == "win32":
            local_app = os.environ.get("LOCALAPPDATA", "")
            if local_app:
                base_py = Path(local_app) / "Programs" / "Python"
                if base_py.exists():
                    for version_dir in sorted(base_py.glob("Python3*"), reverse=True):
                        cand = version_dir / "python.exe"
                        if cand.exists():
                            return cand

        return None


class MissingDependenciesWidget(QFrame):
    """
    Panel visual moderno que se muestra cuando un módulo requiere librerías adicionales.
    Permite instalarlas con un solo clic con barra de progreso y recarga en caliente.
    """
    def __init__(self, module_dir: Path, sub_name: str, dependencias_faltantes: list[str], 
                 on_success_callback=None, colores: dict = None, parent=None):
        super().__init__(parent)
        self.module_dir = Path(module_dir)
        self.sub_name = sub_name
        self.dependencias = dependencias_faltantes
        self.on_success_callback = on_success_callback
        self.colores = colores or {
            "bg_principal": "#121218",
            "bg_secundario": "#1E1E2E",
            "bg_terciario": "#262638",
            "fg_principal": "#FFFFFF",
            "fg_secundario": "#9CA3AF",
            "acento": "#6366F1",
            "acento_hover": "#4F46E5",
            "exito": "#10B981",
            "error": "#EF4444"
        }
        self.installer_thread = None
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(36, 32, 36, 32)
        lay.setSpacing(18)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icono y encabezado
        lbl_icon = QLabel("📦")
        lbl_icon.setFont(QFont("Segoe UI Emoji", 36))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("border: none; background: transparent;")
        lay.addWidget(lbl_icon)

        lbl_titulo = QLabel(f"Dependencias Requeridas: {self.sub_name}")
        lbl_titulo.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_titulo.setStyleSheet(f"color: {self.colores['fg_principal']}; border: none; background: transparent;")
        lay.addWidget(lbl_titulo)

        lbl_desc = QLabel(
            "Este módulo incluye funciones externas que requieren paquetes adicionales de Python.\n"
            "Puedes instalarlos automáticamente en el entorno aislado del módulo sin alterar tu sistema."
        )
        lbl_desc.setFont(QFont("Segoe UI", 10))
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; background: transparent;")
        lay.addWidget(lbl_desc)

        # Lista de dependencias en tarjeta
        card_deps = QFrame()
        card_deps.setStyleSheet(f"""
            background-color: {self.colores['bg_terciario']};
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 10px;
        """)
        card_lay = QVBoxLayout(card_deps)
        card_lay.setSpacing(6)

        lbl_deps_title = QLabel("Librerías a descargar:")
        lbl_deps_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_deps_title.setStyleSheet("color: #818CF8; border: none; background: transparent;")
        card_lay.addWidget(lbl_deps_title)

        for dep in self.dependencias[:8]:
            lbl_item = QLabel(f"  •  {dep}")
            lbl_item.setFont(QFont("Consolas", 9))
            lbl_item.setStyleSheet(f"color: {self.colores['fg_principal']}; border: none; background: transparent;")
            card_lay.addWidget(lbl_item)

        if len(self.dependencias) > 8:
            lbl_more = QLabel(f"  ... y {len(self.dependencias) - 8} paquetes más")
            lbl_more.setStyleSheet("color: #9CA3AF; font-style: italic; border: none; background: transparent;")
            card_lay.addWidget(lbl_more)

        lay.addWidget(card_deps)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.colores['bg_principal']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                height: 12px;
                text-align: center;
                color: white;
                font-size: 8.5pt;
            }}
            QProgressBar::chunk {{
                background-color: {self.colores['acento']};
                border-radius: 5px;
            }}
        """)
        lay.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setFont(QFont("Segoe UI", 9))
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #9CA3AF; border: none; background: transparent;")
        self.lbl_status.setVisible(False)
        lay.addWidget(self.lbl_status)

        # Botón de acción
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_install = QPushButton("⬇️ Instalar Dependencias del Módulo")
        self.btn_install.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
            }}
            QPushButton:hover {{
                background-color: {self.colores['acento_hover']};
            }}
            QPushButton:disabled {{
                background-color: #374151;
                color: #9CA3AF;
            }}
        """)
        self.btn_install.clicked.connect(self._iniciar_instalacion)
        btn_box.addWidget(self.btn_install)

        lay.addLayout(btn_box)

    def _iniciar_instalacion(self):
        python_exe = DependencyManager.buscar_interprete_python()
        if not python_exe:
            self.lbl_status.setText("❌ No se encontró intérprete de Python para ejecutar pip.")
            self.lbl_status.setStyleSheet("color: #EF4444; border: none; background: transparent;")
            self.lbl_status.setVisible(True)
            return

        req_file = self.module_dir / "requirements.txt"
        target_dir = self.module_dir / ".libs"

        self.btn_install.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.lbl_status.setVisible(True)
        self.lbl_status.setText("Iniciando descarga de dependencias...")
        self.lbl_status.setStyleSheet("color: #818CF8; border: none; background: transparent;")

        self.installer_thread = DependencyInstallerThread(python_exe, req_file, target_dir)
        self.installer_thread.progreso_porcentaje.connect(self.progress_bar.setValue)
        self.installer_thread.progreso_linea.connect(self._actualizar_estado)
        self.installer_thread.finalizado.connect(self._on_instalacion_terminada)
        self.installer_thread.start()

    def _actualizar_estado(self, linea):
        corta = linea if len(linea) < 70 else linea[:67] + "..."
        self.lbl_status.setText(corta)

    def _on_instalacion_terminada(self, exito, mensaje):
        if exito:
            DependencyManager.activar_entorno_modulo(self.module_dir)
            self.lbl_status.setText("✅ " + mensaje)
            self.lbl_status.setStyleSheet("color: #10B981; border: none; background: transparent;")
            if callable(self.on_success_callback):
                self.on_success_callback()
        else:
            self.btn_install.setEnabled(True)
            self.lbl_status.setText("❌ " + mensaje)
            self.lbl_status.setStyleSheet("color: #EF4444; border: none; background: transparent;")
