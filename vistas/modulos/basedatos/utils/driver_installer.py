"""
driver_installer.py - Gestor autónomo de controladores de bases de datos para Python.
Permite verificar paquetes instalados y descargar ruedas (.whl) de PyPI sin requerir pip.
"""
import sys
import os
import io
import json
import zipfile
import urllib.request
import subprocess
import importlib
import importlib.util
from pathlib import Path
from typing import Tuple, Optional


class DriverManager:
    """Gestor de drivers de base de datos para Python (verificación y descarga autorizada)"""
    DRIVERS = {
        "sqlite": {
            "name": "SQLite",
            "package": None,
            "module": "sqlite3"
        },
        "postgresql": {
            "name": "PostgreSQL",
            "package": "psycopg2-binary",
            "fallback_package": "pg8000",
            "module": "psycopg2"
        },
        "mysql": {
            "name": "MySQL / MariaDB",
            "package": "pymysql",
            "fallback_package": "mysql-connector-python",
            "module": "pymysql"
        },
        "mongodb": {
            "name": "MongoDB (NoSQL)",
            "package": "pymongo",
            "fallback_package": None,
            "module": "pymongo"
        },
        "redis": {
            "name": "Redis (NoSQL Key-Value)",
            "package": "redis",
            "fallback_package": None,
            "module": "redis"
        }
    }

    @classmethod
    def get_drivers_dir(cls) -> Path:
        try:
            from controlador.utils.paths import get_data_path
            d = Path(get_data_path()) / "db_drivers"
        except Exception:
            d = Path.cwd() / "db_drivers"
        d.mkdir(parents=True, exist_ok=True)
        if str(d) not in sys.path:
            sys.path.insert(0, str(d))
        return d

    @classmethod
    def _find_python(cls) -> Optional[str]:
        import shutil
        if not getattr(sys, "frozen", False):
            if sys.executable and os.path.exists(sys.executable):
                return sys.executable

        for name in ["python", "python3", "py", "pythonw"]:
            p = shutil.which(name)
            if p and os.path.exists(p):
                return p

        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            if local_appdata:
                py_base = Path(local_appdata) / "Programs" / "Python"
                if py_base.exists():
                    for py_dir in sorted(py_base.glob("Python3*"), reverse=True):
                        cand = py_dir / "python.exe"
                        if cand.exists():
                            return str(cand)
            for pf in [os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")]:
                if pf:
                    for p_dir in Path(pf).glob("Python3*"):
                        cand = p_dir / "python.exe"
                        if cand.exists():
                            return str(cand)
        return None

    @classmethod
    def _install_from_pypi(cls, pkg_name: str, drivers_dir: Path) -> Tuple[bool, str]:
        """Descarga e instala paquetes puros de Python (.whl) directamente desde PyPI sin requerir pip"""
        target_pkg = pkg_name
        if "psycopg2" in pkg_name.lower():
            target_pkg = "pg8000"  # Fallback 100% Python puro sin binarios C
        elif "mysql" in pkg_name.lower() and "connector" in pkg_name.lower():
            target_pkg = "pymysql"

        try:
            url_api = f"https://pypi.org/pypi/{target_pkg}/json"
            req = urllib.request.Request(url_api, headers={'User-Agent': 'MultiTool/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            urls = data.get("urls", [])
            wheel_url = None
            for u in urls:
                fn = u.get("filename", "").lower()
                if fn.endswith("-none-any.whl") or ("py3" in fn and fn.endswith(".whl")):
                    wheel_url = u.get("url")
                    break
            if not wheel_url and urls:
                for u in urls:
                    if u.get("filename", "").endswith(".whl"):
                        wheel_url = u.get("url")
                        break

            if not wheel_url:
                return False, f"No se encontró un paquete precompilado compatible para {target_pkg} en PyPI."

            req_whl = urllib.request.Request(wheel_url, headers={'User-Agent': 'MultiTool/1.0'})
            with urllib.request.urlopen(req_whl, timeout=30) as resp:
                whl_bytes = resp.read()

            with zipfile.ZipFile(io.BytesIO(whl_bytes)) as z:
                z.extractall(str(drivers_dir))

            # Para pg8000, descargar también scramp y dependencias puras si es necesario
            if target_pkg == "pg8000":
                try:
                    for dep in ["scramp", "asn1crypto"]:
                        dep_api = f"https://pypi.org/pypi/{dep}/json"
                        with urllib.request.urlopen(urllib.request.Request(dep_api, headers={'User-Agent': 'MultiTool/1.0'}), timeout=10) as r:
                            d_data = json.loads(r.read().decode())
                            for u in d_data.get("urls", []):
                                if u.get("filename", "").endswith("-none-any.whl"):
                                    with urllib.request.urlopen(urllib.request.Request(u.get("url"), headers={'User-Agent': 'MultiTool/1.0'}), timeout=15) as dw:
                                        with zipfile.ZipFile(io.BytesIO(dw.read())) as dz:
                                            dz.extractall(str(drivers_dir))
                                    break
                except Exception:
                    pass

            if str(drivers_dir) not in sys.path:
                sys.path.insert(0, str(drivers_dir))
            importlib.invalidate_caches()
            return True, f"Driver '{target_pkg}' descargado e instalado con éxito en la app."

        except Exception as e:
            return False, f"Error descargando desde PyPI: {e}"

    @classmethod
    def is_installed(cls, engine: str) -> Tuple[bool, Optional[str]]:
        cls.get_drivers_dir()
        engine = engine.lower()
        info = cls.DRIVERS.get(engine)
        if not info or not info.get("package"):
            return True, None
        
        mod_name = info["module"]
        if importlib.util.find_spec(mod_name) is not None:
            return True, info["package"]
        if info.get("fallback_package") and importlib.util.find_spec(info["fallback_package"]) is not None:
            return True, info["fallback_package"]
        return False, info["package"]

    @classmethod
    def install_driver(cls, package_name: str) -> Tuple[bool, str]:
        """Descarga e instala el driver en la carpeta local de la aplicación"""
        drivers_dir = cls.get_drivers_dir()
        py_exe = cls._find_python()

        # Intentar con pip si hay un Python disponible
        if py_exe:
            try:
                cmd = [py_exe, "-m", "pip", "install", "--target", str(drivers_dir), package_name]
                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                res = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    creationflags=creation_flags, timeout=120
                )
                if res.returncode == 0:
                    if str(drivers_dir) not in sys.path:
                        sys.path.insert(0, str(drivers_dir))
                    importlib.invalidate_caches()
                    return True, f"Driver '{package_name}' instalado con éxito."
            except Exception as e:
                print(f"[DriverManager] pip falló, intentando PyPI directo: {e}")

        # Fallback autónomo: Descargar directamente desde PyPI
        return cls._install_from_pypi(package_name, drivers_dir)
