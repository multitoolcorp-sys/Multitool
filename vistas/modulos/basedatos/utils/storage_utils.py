"""
storage_utils.py - Utilidades de almacenamiento seguro, sanitización de rutas
y prevención de ataques de path traversal para bases de datos SQLite y NoSQL.
"""
import os
import re
from pathlib import Path
from typing import Optional, List

RESERVED_DEVICE_NAMES = {
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
    "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
    "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

VALID_DB_EXTENSIONS = {".db", ".sqlite", ".sqlite3", ".db3", ".json"}


def asegurar_directorio_estatico(databases_dir: Path) -> Path:
    """Asegura la existencia del directorio estático para bases de datos con permisos seguros"""
    try:
        databases_dir.mkdir(parents=True, exist_ok=True)
        if os.name != 'nt':
            try:
                os.chmod(databases_dir, 0o700)
            except Exception:
                pass
    except Exception as e:
        print(f"[StorageUtils] Error asegurando directorio estático: {e}")
    return databases_dir


def sanitizar_nombre_db(name: str) -> str:
    """
    Sanitiza el nombre de la base de datos previniendo inyecciones y Directory Traversal.
    Solo permite caracteres alfanuméricos, guiones y guiones bajos.
    """
    if not name:
        return ""
    clean = name.strip().strip("'\"`")
    if clean.endswith(".db"):
        clean = clean[:-3]
    elif clean.endswith(".sqlite") or clean.endswith(".sqlite3") or clean.endswith(".db3"):
        clean = clean.rsplit(".", 1)[0]
    elif clean.endswith(".nosql.json"):
        clean = clean[:-11]
    elif clean.endswith(".json"):
        clean = clean[:-5]

    # Eliminar caracteres peligrosos o separadores de ruta
    clean = re.sub(r'[^a-zA-Z0-9_\-]', '', clean)

    # Prevenir nombres de dispositivos reservados en Windows
    if clean.upper() in RESERVED_DEVICE_NAMES:
        clean = f"db_{clean}"
    return clean


def ruta_db_estatica(databases_dir: Path, name: str) -> Optional[Path]:
    """
    Obtiene la ruta absoluta dentro del directorio estático validando estrictamente
    que la ruta final no escape del directorio base mediante canonicalización (resolve).
    """
    clean_name = sanitizar_nombre_db(name)
    if not clean_name:
        return None
    asegurar_directorio_estatico(databases_dir)
    base_dir = databases_dir.resolve()
    target_path = (databases_dir / f"{clean_name}.db").resolve()
    try:
        if base_dir not in target_path.parents and target_path.parent != base_dir:
            return None
    except Exception:
        return None
    return target_path


def listar_archivos_dbs_estaticas(databases_dir: Path) -> List[Path]:
    """Retorna la lista ordenada de archivos de base de datos en el directorio estático seguro"""
    asegurar_directorio_estatico(databases_dir)
    try:
        archivos = [
            p for p in databases_dir.iterdir()
            if p.is_file() and p.suffix.lower() in VALID_DB_EXTENSIONS
        ]
        return sorted(archivos, key=lambda p: p.name.lower())
    except Exception:
        return []


def listar_nombres_dbs_estaticas(databases_dir: Path) -> List[str]:
    """Retorna la lista de identificadores limpios de las bases de datos estáticas"""
    return [p.stem for p in listar_archivos_dbs_estaticas(databases_dir)]
