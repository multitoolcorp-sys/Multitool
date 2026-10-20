import subprocess
import os
import shutil

def es_git_disponible() -> bool:
    """Verifica si el binario git está instalado y accesible en el PATH del sistema."""
    return shutil.which("git") is not None

def es_repositorio_git(cwd: str) -> bool:
    """Comprueba de forma rápida si el directorio especificado pertenece a un repositorio Git."""
    if not cwd or not os.path.exists(cwd) or not es_git_disponible():
        return False
    try:
        res = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=1.5
        )
        return res.returncode == 0 and "true" in res.stdout.strip().lower()
    except Exception:
        return False

def obtener_estado_git(cwd: str) -> dict:
    """
    Obtiene el estado completo y resumido de Git para el directorio indicado:
    - nombre de la rama activa
    - cantidad de archivos modificados, agregados y no rastreados
    - commits adelantados/atrasados respecto al origen
    - último commit (hash y mensaje)
    """
    info = {
        "es_repo": False,
        "rama": "",
        "modificados": 0,
        "staged": 0,
        "untracked": 0,
        "adelante": 0,
        "atras": 0,
        "es_limpio": True,
        "ultimo_commit": ""
    }
    
    if not es_repositorio_git(cwd):
        return info

    info["es_repo"] = True

    # 1. Rama activa
    try:
        res_branch = subprocess.run(
            ["git", "-C", cwd, "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=1.5
        )
        rama = res_branch.stdout.strip()
        if not rama:
            # HEAD desasociada o commit específico
            res_head = subprocess.run(
                ["git", "-C", cwd, "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=1.5
            )
            rama = f"HEAD ({res_head.stdout.strip()})" if res_head.returncode == 0 else "HEAD"
        info["rama"] = rama
    except Exception:
        info["rama"] = "desconocida"

    # 2. Archivos modificados (git status --porcelain)
    try:
        res_status = subprocess.run(
            ["git", "-C", cwd, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if res_status.returncode == 0:
            lines = [l for l in res_status.stdout.splitlines() if l.strip()]
            for l in lines:
                x = l[0] if len(l) > 0 else " "
                y = l[1] if len(l) > 1 else " "
                if x in ("M", "A", "D", "R", "C"):
                    info["staged"] += 1
                if y in ("M", "D"):
                    info["modificados"] += 1
                elif x == "?" and y == "?":
                    info["untracked"] += 1
            info["es_limpio"] = len(lines) == 0
    except Exception:
        pass

    # 3. Ahead / Behind (si tiene upstream configurado)
    try:
        res_sync = subprocess.run(
            ["git", "-C", cwd, "rev-list", "--left-right", "--count", "HEAD...@{u}"],
            capture_output=True,
            text=True,
            timeout=1.5
        )
        if res_sync.returncode == 0:
            parts = res_sync.stdout.strip().split()
            if len(parts) == 2:
                info["adelante"] = int(parts[0])
                info["atras"] = int(parts[1])
    except Exception:
        pass

    # 4. Último commit
    try:
        res_log = subprocess.run(
            ["git", "-C", cwd, "log", "-1", "--format=%h - %s (%cr)"],
            capture_output=True,
            text=True,
            timeout=1.5
        )
        if res_log.returncode == 0:
            info["ultimo_commit"] = res_log.stdout.strip()
    except Exception:
        pass

    return info

def obtener_grafo_git(cwd: str, max_commits: int = 40) -> str:
    """
    Retorna el árbol visual de commits con colores ANSI formateados:
    'git log --graph --color=always ...'
    """
    if not es_repositorio_git(cwd):
        return ""
    try:
        fmt = "%C(yellow)%h%Creset%C(auto)%d%Creset %C(white)%s%Creset %C(dim green)(%cr)%Creset %C(cyan)<%an>%Creset"
        cmd = [
            "git", "-C", cwd, "log",
            "--graph",
            "--color=always",
            f"--pretty=format:{fmt}",
            "--all",
            "-n", str(max_commits)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
        return res.stdout if res.returncode == 0 else ""
    except Exception as e:
        return f"Error obteniendo grafo de git: {e}"

def obtener_ramas_git(cwd: str) -> list:
    """Lista todas las ramas locales y remotas del repositorio."""
    if not es_repositorio_git(cwd):
        return []
    ramas = []
    try:
        res = subprocess.run(
            ["git", "-C", cwd, "branch", "-a"],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                line_s = line.strip()
                if not line_s:
                    continue
                es_actual = line_s.startswith("*")
                nombre = line_s.lstrip("* ").strip()
                es_remota = nombre.startswith("remotes/")
                ramas.append({
                    "nombre": nombre,
                    "actual": es_actual,
                    "remota": es_remota
                })
    except Exception:
        pass
    return ramas

def obtener_status_archivos(cwd: str) -> list:
    """Retorna la lista de archivos con cambios pendientes: [(codigo, ruta)]."""
    if not es_repositorio_git(cwd):
        return []
    items = []
    try:
        res = subprocess.run(
            ["git", "-C", cwd, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if len(line) >= 3:
                    estado = line[:2].strip()
                    ruta = line[3:].strip()
                    items.append((estado, ruta))
    except Exception:
        pass
    return items

def ejecutar_comando_git(cwd: str, args: list) -> tuple:
    """Ejecuta un comando git y retorna (exito: bool, salida: str)."""
    if not es_git_disponible():
        return False, "Git no está instalado o no se encuentra en el PATH."
    try:
        cmd = ["git", "-C", cwd] + args
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10.0)
        salida = res.stdout if res.returncode == 0 else res.stderr
        return res.returncode == 0, salida.strip()
    except Exception as e:
        return False, str(e)
