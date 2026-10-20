import os
import sys
import json
import shutil
import zipfile
import platform
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QMessageBox, QFrame, QFileDialog, QCheckBox,
    QRadioButton, QButtonGroup, QScrollArea, QDialog, QTextEdit, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QProcess, QPoint
from PyQt6.QtGui import QFont, QIcon


class TerminosCondicionesDialog(QDialog):
    """Diálogo modal para visualizar los Términos y Condiciones de MultiTool"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Términos y Condiciones de Uso - MultiTool")
        self.resize(520, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #121218;
                color: #E2E8F0;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 22, 22, 22)
        lay.setSpacing(14)

        lbl = QLabel("📜 TÉRMINOS Y CONDICIONES DE USO")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #6366F1;")
        lay.addWidget(lbl)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E2E;
                color: #E2E8F0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px;
                font-family: 'Segoe UI';
                font-size: 9.5pt;
                line-height: 1.4;
            }
        """)
        txt.setHtml("""
            <h3 style="color:#818CF8;">1. Licencia y Uso del Software</h3>
            <p>MultiTool es una suite digital integral de utilidades de productividad, administración de archivos, monitoreo de sistema y herramientas digitales integradas.</p>
            
            <h3 style="color:#818CF8;">2. Privacidad y Almacenamiento Local</h3>
            <p>MultiTool opera de manera <b>100% local</b> en su equipo. Sus datos de cuentas, notas, credenciales, historial y configuraciones se almacenan cifrados o en bases de datos locales sin telemetría invasiva ni envío encubierto de datos a servidores externos.</p>
            
            <h3 style="color:#818CF8;">3. Uso Responsable de Herramientas de Sistema</h3>
            <p>La aplicación contiene utilidades avanzadas (Terminal integrada, administrador de procesos, control de aplicaciones de inicio de Windows y navegación web). El usuario asume la responsabilidad sobre las órdenes, modificaciones o tareas que ejecute en su sistema anfitrión.</p>
            
            <h3 style="color:#818CF8;">4. Modularidad y Actualizaciones</h3>
            <p>El usuario tiene plena libertad de seleccionar qué módulos instalar, actualizar o eliminar en cualquier momento, ya sea desde este instalador o mediante el gestor interno de la aplicación.</p>

            <h3 style="color:#818CF8;">5. Exención de Responsabilidad</h3>
            <p>El software se entrega 'TAL CUAL' (AS IS) sin garantías expresas o implícitas de ningún tipo. Los desarrolladores no serán responsables de daños directos o indirectos derivados del uso o mal uso del software.</p>
        """)
        lay.addWidget(txt)

        btn_ok = QPushButton("Entendido y Aceptar")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setFixedHeight(36)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                font-weight: bold;
                border-radius: 8px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #818CF8;
            }
        """)
        btn_ok.clicked.connect(self.accept)
        lay.addWidget(btn_ok)


class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, zip_path, dest_path, mode="installer", modulos_seleccionados=None):
        super().__init__()
        self.zip_path = zip_path
        self.dest_path = Path(dest_path)
        self.mode = mode  # "installer" o "updater"
        self.modulos_seleccionados = set(m.lower() for m in (modulos_seleccionados or []))
        # Siempre asegurar módulos obligatorios
        self.modulos_seleccionados.add("general")
        self.modulos_seleccionados.add("cuenta")
        self.modulos_seleccionados.add("cuentas")

    def _debe_instalar_archivo(self, rel_path_str):
        """Determina si un archivo debe instalarse según el modo y los módulos seleccionados"""
        norm = rel_path_str.replace("\\", "/").lower()

        # Si el archivo forma parte de algún módulo
        if "vistas/modulos/" in norm:
            try:
                partes = norm.split("vistas/modulos/")[1].split("/")
                if partes and partes[0]:
                    mod_name = partes[0]
                    return mod_name in self.modulos_seleccionados
            except Exception:
                pass
            return True

        # Para archivos base / core (fuera de vistas/modulos/):
        if self.mode == "updater":
            # En modo actualizador de módulos, no se sobreescribe el core
            return False

        return True

    def run(self):
        self.security_warning = None
        try:
            # 0. Verificar espacio libre en disco (mínimo 300 MB)
            parent_dir = self.dest_path.parent
            parent_dir.mkdir(parents=True, exist_ok=True)
            total, used, free = shutil.disk_usage(parent_dir)
            free_mb = free / (1024 * 1024)
            if free_mb < 300:
                self.finished.emit(False, f"Espacio en disco insuficiente ({free_mb:.1f} MB libres). Se requieren al menos 300 MB.")
                return

            self.dest_path.mkdir(parents=True, exist_ok=True)
            self.progress.emit(10, "Preparando directorios y archivos...")

            # 1. Extraer o copiar archivos
            if os.path.exists(self.zip_path):
                self._extraer_desde_zip()
            else:
                self._copiar_desde_directorio_local()

            # 2. Guardar registro dinámico de instalación
            exe_name = "Multitool.exe" if platform.system() == "Windows" else "Multitool"
            path_exe = self.dest_path / exe_name
            install_info = {
                "install_path": str(self.dest_path),
                "exe_path": str(path_exe),
                "mode": self.mode,
                "installed_modules": list(self.modulos_seleccionados),
                "installed_at": datetime.now().isoformat()
            }
            manifest_path = Path.home() / ".multitool_install.json"
            try:
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(install_info, f, indent=4, ensure_ascii=False)
            except Exception:
                pass

            # 3. Registrar exclusión en Windows Defender si es Windows
            if platform.system() == "Windows":
                self.progress.emit(85, "Configurando exclusión en Windows Defender...")
                self.agregar_exclusion_antivirus(self.dest_path)

            # 4. Crear Acceso Directo (solo en instalación completa)
            status_shortcut = True
            if self.mode == "installer":
                self.progress.emit(90, "Creando acceso directo en el Escritorio...")
                status_shortcut = self.crear_acceso_directo()

            self.progress.emit(100, "¡Operación completada con éxito!")

            msg = "Instalación completada correctamente." if self.mode == "installer" else "Módulos actualizados con éxito."
            if not status_shortcut:
                msg += "\n\nNota: No se pudo crear el acceso directo automático en el escritorio."

            self.finished.emit(True, msg)
        except Exception as e:
            self.finished.emit(False, str(e))

    def _extraer_desde_zip(self):
        with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
            files = zip_ref.namelist()
            total = len(files)
            for i, file in enumerate(files):
                if self._debe_instalar_archivo(file):
                    zip_ref.extract(file, self.dest_path)
                p = 20 + int((i / total) * 60)
                self.progress.emit(p, f"Procesando: {file}")

    def _copiar_desde_directorio_local(self):
        origen = Path(__file__).resolve().parent
        all_files = []
        for root, dirs, files in os.walk(origen):
            if any(ign in root for ign in [".git", "__pycache__", ".vscode", "DISTRIBUCION"]):
                continue
            for f in files:
                all_files.append(Path(root) / f)

        total = len(all_files)
        for i, fpath in enumerate(all_files):
            rel = fpath.relative_to(origen)
            if self._debe_instalar_archivo(str(rel)):
                dest_file = self.dest_path / rel
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(fpath, dest_file)
                except Exception:
                    pass
            p = 20 + int((i / total) * 60)
            self.progress.emit(p, f"Instalando: {rel.name}")

    def crear_acceso_directo(self):
        system = platform.system()
        try:
            exe_name = "Multitool.exe" if system == "Windows" else "Multitool"
            path_exe = self.dest_path / exe_name
            path_icon = self.dest_path / "vistas" / "utils" / "icono.ico"
            desktop = Path(os.path.join(os.path.expanduser("~"), "Desktop"))

            if system == "Windows":
                import tempfile
                vbs_script = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{str(desktop / 'Multitool.lnk')}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{str(path_exe)}"
oLink.WorkingDirectory = "{str(path_exe.parent)}"
oLink.IconLocation = "{str(path_icon)}"
oLink.Save
"""
                vbs_path = Path(tempfile.gettempdir()) / "create_shortcut.vbs"
                vbs_path.write_text(vbs_script, encoding="utf-8")
                subprocess.run(["cscript.exe", "//Nologo", str(vbs_path)], creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    vbs_path.unlink()
                except Exception:
                    pass
                return True

            elif system == "Linux":
                desktop_file = f"""[Desktop Entry]
Type=Application
Name=Multitool
Exec={path_exe}
Icon={path_icon}
Path={path_exe.parent}
Terminal=false
Categories=Utility;
"""
                with open(desktop / "Multitool.desktop", "w", encoding="utf-8") as f:
                    f.write(desktop_file)
                os.chmod(desktop / "Multitool.desktop", 0o755)
                return True

            elif system == "Darwin":
                target_alias = desktop / "Multitool"
                if target_alias.exists():
                    target_alias.unlink()
                os.symlink(path_exe, target_alias)
                return True

        except Exception as e:
            print(f"Error shortcut: {e}")
            return False
        return False

    def agregar_exclusion_antivirus(self, path):
        try:
            cmd = f'powershell -Command "Add-MpPreference -ExclusionPath \'{str(path)}\'"'
            subprocess.run(
                cmd,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception:
            return False


class DownloaderGUI(QWidget):
    # Catálogo de los 22 módulos reales de MultiTool (vistas/modulos/)
    CATALOGO_MODULOS = [
        ("general", "General (Dashboard, Productividad, Clima & Hábitos)", True, True),
        ("cuenta", "Cuenta (Perfil, Auditoría, Bóveda & 2FA)", True, True),
        ("archivos", "Archivos (Explorador de Archivos)", True, False),
        ("basedatos", "Base de Datos (Gestor SQL & SQLite estilo DBeaver)", True, False),
        ("calculadora", "Calculadora (Científica, Gráficas, Finanzas)", True, False),
        ("calendario", "Calendario (Agenda & Eventos)", True, False),
        ("chat", "Chat (Sala LAN & Asistente IA Privado)", True, False),
        ("clipboard", "Clipboard (Historial de Portapapeles & Snippets)", True, False),
        ("cuaderno", "Cuaderno (Editor Markdown, Grid & Notas)", True, False),
        ("emulador", "Emulador (Consola Arcade & ROMs)", True, False),
        ("extras", "Extras (Espejo Celular, Recortes & OCR, Ruleta)", True, False),
        ("grabadora", "Grabadora (Audio, Pantalla & Cámara)", True, False),
        ("minigames", "MiniGames (Juegos Arcade & Roguelike)", True, False),
        ("navegador", "Navegador (Navegador Web, Gmail, Descargas)", True, False),
        ("notas", "Notas (Mis Notas, Editor & Post-its)", True, False),
        ("proyectos", "Proyectos (Tablero Kanban & Estadísticas)", True, False),
        ("reproductor", "Reproductor (Multimedia ARK & Radio Online)", True, False),
        ("seguridad", "Seguridad (Bóveda de Seguridad & Protección)", True, False),
        ("sistema", "Sistema (Monitoreo, Procesos & Inicio Windows)", True, False),
        ("terminal", "Terminal (Terminal PowerShell & Consola)", True, False),
        ("tiempo", "Tiempo (Reloj Mundial, Alarmas, Temporizador, Pomodoro)", True, False),
        ("traductor", "Traductor (Texto, Voz & Documentos)", True, False),
        ("widgets", "Widgets (Widgets Flotantes de Escritorio)", True, False),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multitool - Instalador y Actualizador Multiplataforma")
        self.setFixedSize(580, 680)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.colores = {
            "bg": "#121218", "sec": "#1E1E2E", "ter": "#2A2A3C",
            "accent": "#6366F1", "accent_hover": "#818CF8",
            "exito": "#34D399", "fg": "#E2E8F0", "fg_muted": "#94A3B8"
        }
        
        sys_os = platform.system()
        if sys_os == "Windows":
            self.custom_dest_root = Path(os.path.expanduser("~")) / "Documents" / "Multitool"
        elif sys_os == "Darwin":
            self.custom_dest_root = Path("/Applications/Multitool.app")
        else:
            self.custom_dest_root = Path(os.path.expanduser("~")) / ".local" / "share" / "Multitool"

        self.checkboxes_modulos = {}
        self.drag_position = QPoint()
        self.init_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame#MainContainer {{
                background-color: {self.colores['bg']};
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
        """)
        container.setObjectName("MainContainer")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(28, 22, 28, 22)
        c_lay.setSpacing(10)
        
        # ── Barra Superior (Título y Botón Cerrar) ──
        top_bar = QHBoxLayout()
        self.lbl_title = QLabel("MULTITOOL SUITE")
        self.lbl_title.setFont(QFont("Segoe UI" if platform.system() == "Windows" else "Inter", 15, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet(f"color: {self.colores['accent']}; border: none;")
        top_bar.addWidget(self.lbl_title)
        top_bar.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent; color: #94A3B8; border: none; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover {
                color: #F87171; background: rgba(248, 113, 113, 0.15); border-radius: 13px;
            }
        """)
        btn_close.clicked.connect(self.close)
        top_bar.addWidget(btn_close)
        c_lay.addLayout(top_bar)

        lbl_sub = QLabel("Instalador y Actualizador Modular")
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setStyleSheet("color: #64748B; border: none; margin-top: -6px;")
        c_lay.addWidget(lbl_sub)

        # ── Selector de Modo: Instalación vs Actualización ──
        mode_box = QFrame()
        mode_box.setStyleSheet(f"background: {self.colores['sec']}; border-radius: 10px; padding: 6px;")
        mode_lay = QHBoxLayout(mode_box)
        mode_lay.setContentsMargins(10, 6, 10, 6)

        self.btn_group_mode = QButtonGroup(self)
        self.rad_installer = QRadioButton("🛠️ Instalador Completo (Core + Módulos)")
        self.rad_installer.setChecked(True)
        self.rad_installer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rad_installer.setStyleSheet(f"""
            QRadioButton {{ color: white; font-weight: bold; font-size: 9.5pt; }}
            QRadioButton::indicator:checked {{ background-color: {self.colores['accent']}; border: 2px solid #818CF8; border-radius: 6px; }}
        """)

        self.rad_updater = QRadioButton("⚡ Actualizador / Solo Módulos")
        self.rad_updater.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rad_updater.setStyleSheet(f"""
            QRadioButton {{ color: white; font-weight: bold; font-size: 9.5pt; }}
            QRadioButton::indicator:checked {{ background-color: {self.colores['accent']}; border: 2px solid #818CF8; border-radius: 6px; }}
        """)

        self.btn_group_mode.addButton(self.rad_installer)
        self.btn_group_mode.addButton(self.rad_updater)
        self.rad_installer.toggled.connect(self._on_mode_changed)

        mode_lay.addWidget(self.rad_installer)
        mode_lay.addSpacing(15)
        mode_lay.addWidget(self.rad_updater)
        c_lay.addWidget(mode_box)

        # ── Ruta de Instalación ──
        path_box = QHBoxLayout()
        self.lbl_desc = QLabel(f"📂 Ruta: {self.custom_dest_root}")
        self.lbl_desc.setFont(QFont("Segoe UI", 9))
        self.lbl_desc.setStyleSheet("color: #94A3B8; border: none;")
        path_box.addWidget(self.lbl_desc, stretch=1)

        btn_change_path = QPushButton("Cambiar Ruta...")
        btn_change_path.setFixedHeight(26)
        btn_change_path.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_path.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['sec']}; color: #CBD5E1; 
                border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; 
                font-size: 8.5pt; padding: 0 10px;
            }}
            QPushButton:hover {{ background: {self.colores['ter']}; color: white; }}
        """)
        btn_change_path.clicked.connect(self._seleccionar_ruta_personalizada)
        path_box.addWidget(btn_change_path)
        c_lay.addLayout(path_box)

        # ── Selector de Módulos (Scrollable) ──
        mod_header = QHBoxLayout()
        lbl_mod_title = QLabel("📦 SELECCIÓN DE MÓDULOS:")
        lbl_mod_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_mod_title.setStyleSheet(f"color: {self.colores['accent']};")
        mod_header.addWidget(lbl_mod_title)
        mod_header.addStretch()

        btn_all = QPushButton("☑ Todos")
        btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_all.setStyleSheet("background: transparent; color: #818CF8; border: none; font-size: 8pt; font-weight: bold;")
        btn_all.clicked.connect(lambda: self._set_all_modules(True))
        mod_header.addWidget(btn_all)

        btn_none = QPushButton("☐ Mínimo")
        btn_none.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_none.setStyleSheet("background: transparent; color: #94A3B8; border: none; font-size: 8pt; font-weight: bold;")
        btn_none.clicked.connect(lambda: self._set_all_modules(False))
        mod_header.addWidget(btn_none)
        c_lay.addLayout(mod_header)

        # Contenedor con Scroll para Módulos
        scroll_mod = QScrollArea()
        scroll_mod.setFixedHeight(180)
        scroll_mod.setWidgetResizable(True)
        scroll_mod.setFrameShape(QFrame.Shape.NoFrame)
        scroll_mod.setStyleSheet(f"""
            QScrollArea {{
                background-color: {self.colores['sec']};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
            }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.colores['accent']}; border-radius: 3px; min-height: 20px;
            }}
        """)

        scroll_mod_widget = QWidget()
        scroll_mod_widget.setStyleSheet("background: transparent;")
        grid_mod = QGridLayout(scroll_mod_widget)
        grid_mod.setContentsMargins(10, 8, 10, 8)
        grid_mod.setHorizontalSpacing(14)
        grid_mod.setVerticalSpacing(6)

        for idx, (mod_id, display_name, def_checked, is_locked) in enumerate(self.CATALOGO_MODULOS):
            row = idx // 2
            col = idx % 2

            chk = QCheckBox(f"{display_name}" + (" 🔒" if is_locked else ""))
            chk.setChecked(def_checked)
            if is_locked:
                chk.setEnabled(False)
                chk.setToolTip("Módulo central obligatorio del sistema")
                chk.setStyleSheet(f"""
                    QCheckBox {{ color: {self.colores['exito']}; font-size: 8.5pt; font-weight: bold; }}
                    QCheckBox::indicator {{ width: 15px; height: 15px; border-radius: 3px; border: 1px solid {self.colores['exito']}; background: {self.colores['exito']}; }}
                """)
            else:
                chk.setCursor(Qt.CursorShape.PointingHandCursor)
                chk.setStyleSheet(f"""
                    QCheckBox {{ color: #E2E8F0; font-size: 8.5pt; }}
                    QCheckBox::indicator {{ width: 15px; height: 15px; border-radius: 3px; border: 1px solid rgba(255,255,255,0.25); background: #121218; }}
                    QCheckBox::indicator:checked {{ background-color: {self.colores['accent']}; border-color: {self.colores['accent']}; }}
                """)
            self.checkboxes_modulos[mod_id] = (chk, is_locked)
            grid_mod.addWidget(chk, row, col)

        scroll_mod.setWidget(scroll_mod_widget)
        c_lay.addWidget(scroll_mod)

        # ── Términos y Condiciones ──
        terms_box = QHBoxLayout()
        self.chk_terms = QCheckBox("Acepto los Términos y Condiciones de Uso")
        self.chk_terms.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_terms.setStyleSheet(f"""
            QCheckBox {{ color: #CBD5E1; font-size: 9pt; font-weight: bold; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; border: 1px solid rgba(255,255,255,0.3); background: #121218; }}
            QCheckBox::indicator:checked {{ background-color: {self.colores['accent']}; border-color: {self.colores['accent']}; }}
        """)
        self.chk_terms.stateChanged.connect(self._on_terms_changed)
        terms_box.addWidget(self.chk_terms)
        terms_box.addStretch()

        btn_view_terms = QPushButton("📄 Leer Términos")
        btn_view_terms.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view_terms.setStyleSheet("background: transparent; color: #818CF8; border: none; font-size: 8.5pt; text-decoration: underline;")
        btn_view_terms.clicked.connect(self._mostrar_terminos)
        terms_box.addWidget(btn_view_terms)
        c_lay.addLayout(terms_box)

        # ── Barra de Progreso ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ background: {self.colores['sec']}; border-radius: 4px; border: none; }}
            QProgressBar::chunk {{ background: {self.colores['accent']}; border-radius: 4px; }}
        """)
        c_lay.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Listo para comenzar...")
        self.lbl_status.setFont(QFont("Segoe UI", 8))
        self.lbl_status.setStyleSheet("color: #64748B; border: none;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_lay.addWidget(self.lbl_status)

        # Iniciar al terminar
        self.chk_launch = QCheckBox("Iniciar MultiTool al finalizar")
        self.chk_launch.setChecked(True)
        self.chk_launch.setStyleSheet("color: #94A3B8; font-size: 8.5pt; border: none;")
        c_lay.addWidget(self.chk_launch)

        # ── Botón Principal de Instalación / Actualización ──
        self.btn_install = QPushButton("INSTALAR AHORA")
        self.btn_install.setFixedHeight(44)
        self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install.setEnabled(False)  # Deshabilitado hasta aceptar términos
        self.btn_install.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['accent']};
                color: white; border-radius: 10px;
                font-weight: bold; font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: {self.colores['accent_hover']};
            }}
            QPushButton:disabled {{
                background-color: #2A2A3C;
                color: #64748B;
            }}
        """)
        self.btn_install.clicked.connect(self.start_installation)
        c_lay.addWidget(self.btn_install)

        main_layout.addWidget(container)

    def _on_mode_changed(self):
        if self.rad_installer.isChecked():
            self.btn_install.setText("INSTALAR AHORA")
        else:
            self.btn_install.setText("ACTUALIZAR MÓDULOS AHORA")

    def _on_terms_changed(self):
        self.btn_install.setEnabled(self.chk_terms.isChecked())

    def _mostrar_terminos(self):
        dlg = TerminosCondicionesDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.chk_terms.setChecked(True)

    def _set_all_modules(self, state):
        for mod_id, (chk, is_locked) in self.checkboxes_modulos.items():
            if not is_locked:
                chk.setChecked(state)

    def _seleccionar_ruta_personalizada(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Instalación", str(self.custom_dest_root.parent))
        if folder:
            self.custom_dest_root = Path(folder) / "Multitool"
            self.lbl_desc.setText(f"📂 Ruta: {self.custom_dest_root}")

    def start_installation(self):
        self.btn_install.setEnabled(False)
        self.rad_installer.setEnabled(False)
        self.rad_updater.setEnabled(False)

        # Obtener módulos seleccionados
        seleccionados = []
        for mod_id, (chk, is_locked) in self.checkboxes_modulos.items():
            if is_locked or chk.isChecked():
                seleccionados.append(mod_id)

        mode = "installer" if self.rad_installer.isChecked() else "updater"

        # Buscar paquete data.zip o directorio origen
        zip_path = None
        if hasattr(sys, '_MEIPASS'):
            candidate = Path(sys._MEIPASS).resolve() / "data.zip"
            if candidate.exists():
                zip_path = candidate

        if not zip_path or not zip_path.exists():
            exe_dir = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
            if (exe_dir / "data.zip").exists():
                zip_path = exe_dir / "data.zip"
            elif (Path.cwd() / "data.zip").exists():
                zip_path = Path.cwd() / "data.zip"
            else:
                zip_path = Path(__file__).resolve().parent / "data.zip"

        self.worker = InstallWorker(zip_path, self.custom_dest_root, mode=mode, modulos_seleccionados=seleccionados)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.installation_finished)
        self.worker.start()

    def update_progress(self, val, msg):
        self.progress_bar.setValue(val)
        self.lbl_status.setText(msg)

    def installation_finished(self, success, msg):
        if success:
            self.lbl_status.setText("¡Operación completada exitosamente!")
            self.btn_install.setText("FINALIZAR")
            self.btn_install.setEnabled(True)
            self.btn_install.clicked.disconnect()

            def finalizar():
                if self.chk_launch.isChecked():
                    exe_name = "Multitool.exe" if platform.system() == "Windows" else "Multitool"
                    path_exe = self.custom_dest_root / exe_name
                    if path_exe.exists():
                        QProcess.startDetached(str(path_exe))
                sys.exit(0)

            self.btn_install.clicked.connect(finalizar)
            QMessageBox.information(self, "Multitool", msg)
        else:
            QMessageBox.critical(self, "Error", f"Fallo en la operación:\n{msg}")
            self.btn_install.setEnabled(True)
            self.rad_installer.setEnabled(True)
            self.rad_updater.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    window = DownloaderGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
