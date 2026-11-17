import datetime
import os
import platform
import stat
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from controlador.utils.platform_compat import open_path_native


class UnixPropertiesDialog(QDialog):
    """Diálogo interactivo de propiedades y permisos chmod para Linux y macOS."""

    def __init__(self, ruta_archivo, parent=None):
        super().__init__(parent)
        self.ruta = Path(ruta_archivo)
        st = self.ruta.stat()
        self._mode = st.st_mode
        self.setWindowTitle(f"Propiedades — {self.ruta.name}")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog, QWidget { background-color: #151824; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QLabel, QCheckBox { color: #f8fafc; }
            QPushButton { background-color: #252a3d; color: #f8fafc; border: 1px solid #38405e; border-radius: 5px; padding: 5px 10px; font-weight: 600; }
            QPushButton#Primary { background-color: #4f46e5; border-color: #6366f1; }
        """)
        lay = QVBoxLayout(self)
        tipo = "Carpeta" if self.ruta.is_dir() else "Archivo"
        mod_t = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        tam = f"{st.st_size:,} bytes ({max(1, st.st_size // 1024):,} KB)" if self.ruta.is_file() else "Directorio"
        lay.addWidget(QLabel(
            f"<b>Nombre:</b> {self.ruta.name}<br>"
            f"<b>Tipo:</b> {tipo}<br>"
            f"<b>Ruta:</b> <code>{self.ruta.resolve()}</code><br>"
            f"<b>Tamaño:</b> {tam}<br>"
            f"<b>Modificado:</b> {mod_t}<br>"
            f"<b>Modo actual:</b> <code>{stat.filemode(st.st_mode)} ({oct(stat.S_IMODE(st.st_mode))})</code>"
        ))

        grid = QGridLayout()
        self._checks: dict[int, QCheckBox] = {}
        bits = [
            ("Propietario", [(stat.S_IRUSR, "Lectura"), (stat.S_IWUSR, "Escritura"), (stat.S_IXUSR, "Ejecución")]),
            ("Grupo", [(stat.S_IRGRP, "Lectura"), (stat.S_IWGRP, "Escritura"), (stat.S_IXGRP, "Ejecución")]),
            ("Otros", [(stat.S_IROTH, "Lectura"), (stat.S_IWOTH, "Escritura"), (stat.S_IXOTH, "Ejecución")]),
        ]
        for r, (grp_lbl, perms) in enumerate(bits):
            grid.addWidget(QLabel(f"<b>{grp_lbl}:</b>"), r, 0)
            for c, (bit, plbl) in enumerate(perms, start=1):
                chk = QCheckBox(plbl)
                chk.setChecked(bool(st.st_mode & bit))
                self._checks[bit] = chk
                grid.addWidget(chk, r, c)
        lay.addLayout(grid)

        row_b = QHBoxLayout()
        btn_exec = QPushButton("⚡ Hacer Ejecutable (+x)")
        btn_exec.clicked.connect(self._hacer_ejecutable)
        btn_apply = QPushButton("💾 Aplicar Permisos")
        btn_apply.setObjectName("Primary")
        btn_apply.clicked.connect(self._aplicar_permisos)
        row_b.addWidget(btn_exec)
        row_b.addWidget(btn_apply)
        lay.addLayout(row_b)

    def _hacer_ejecutable(self):
        for bit in (stat.S_IXUSR, stat.S_IXGRP, stat.S_IXOTH):
            self._checks[bit].setChecked(True)
        self._aplicar_permisos()

    def _aplicar_permisos(self):
        new_mode = 0
        for bit, chk in self._checks.items():
            if chk.isChecked():
                new_mode |= bit
        try:
            os.chmod(self.ruta, new_mode)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error chmod", f"No se pudieron cambiar los permisos: {e}")


def mostrar_propiedades_multiplataforma(ruta_archivo, parent_widget=None):
    """Muestra propiedades nativas en Windows y un editor interactivo chmod en Linux/macOS."""
    if platform.system() == "Windows":
        return mostrar_propiedades_windows(ruta_archivo)
    try:
        dlg = UnixPropertiesDialog(ruta_archivo, parent=parent_widget)
        dlg.exec()
        return True
    except Exception:
        return False

def mostrar_propiedades_windows(ruta_archivo):
    """Invoca la ventana de propiedades nativa de Windows usando ShellExecuteExW"""
    if platform.system() != "Windows":
        return False
    import ctypes
    from ctypes import wintypes
    
    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", ctypes.c_ulong),
            ("hwnd", wintypes.HWND),
            ("lpVerb", ctypes.c_wchar_p),
            ("lpFile", ctypes.c_wchar_p),
            ("lpParameters", ctypes.c_wchar_p),
            ("lpDirectory", ctypes.c_wchar_p),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", ctypes.c_wchar_p),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIconOrMonitor", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]
        
    SEE_MASK_INVOKEIDLIST = 0x0000000C
    SEE_MASK_NOCLOSEPROCESS = 0x00000040
    
    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
    sei.fMask = SEE_MASK_INVOKEIDLIST | SEE_MASK_NOCLOSEPROCESS
    sei.lpVerb = "properties"
    sei.lpFile = str(Path(ruta_archivo).resolve())
    sei.nShow = 5 # SW_SHOW
    
    ret = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))
    return bool(ret)


def abrir_dispositivo_adb(dev_id, parent_widget=None):
    """Gestiona la interacción con un dispositivo móvil Android detectado por ADB"""
    try:
        msg = QMessageBox(parent_widget)
        msg.setWindowTitle("Dispositivo Android Conectado")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"<h3 style='color: #6366F1;'>📲 Dispositivo Móvil Detectado</h3>"
                    f"<p><b>Identificador / Serie:</b> <code>{dev_id}</code></p>"
                    f"<p>El teléfono está conectado y disponible mediante <b>ADB (Depuración USB)</b>.</p>"
                    f"<p>¿Qué acción deseas realizar?</p>")
        btn_espejo = msg.addButton("📱 Abrir en Espejo Celular", QMessageBox.ButtonRole.ActionRole)
        btn_explorar = msg.addButton("📂 Abrir Almacenamiento (Este equipo)", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        
        if msg.clickedButton() == btn_espejo:
            app = getattr(parent_widget, "main_window", None) or parent_widget
            while app and not hasattr(app, "notebook") and hasattr(app, "parent") and app.parent():
                app = app.parent()
            if hasattr(app, "notebook"):
                for i in range(app.notebook.count()):
                    txt = app.notebook.tabText(i).lower()
                    if "extra" in txt or "espejo" in txt:
                        app.notebook.setCurrentIndex(i)
                        if hasattr(app, "nav_bar"):
                            if hasattr(app.nav_bar, "select_tab"):
                                app.nav_bar.select_tab(i)
                            elif hasattr(app.nav_bar, "seleccionar_tab"):
                                app.nav_bar.seleccionar_tab(i)
                        break
        elif msg.clickedButton() == btn_explorar:
            sys_os = platform.system()
            if sys_os == "Windows":
                subprocess.Popen(["explorer.exe", "shell:MyComputerFolder"])
            elif sys_os == "Darwin":
                open_path_native("/Volumes")
            else:
                gvfs = Path(f"/run/user/{os.getuid()}/gvfs") if hasattr(os, "getuid") else Path("/media")
                open_path_native(gvfs if gvfs.exists() else Path("/media"))
    except Exception as e:
        print(f"[ShellUtils] Error al interactuar con dispositivo ADB: {e}")
