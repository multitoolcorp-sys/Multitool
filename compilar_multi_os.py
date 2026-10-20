import os
import sys
import platform
import subprocess
from pathlib import Path

def banner(message):
    print("\n" + "=" * 50)
    print(f"  {message}")
    print("=" * 50)

def compilar_downloader():
    base_path = Path(__file__).resolve().parent
    downloader_script = base_path / "downloader.py"
    dist_dir = base_path / "DISTRIBUCION"
    
    if not downloader_script.exists():
        print(f"[!] Error: No se encontró '{downloader_script.name}'")
        return

    # Determinar sistema operativo actual
    sys_os = platform.system()
    
    if sys_os == "Windows":
        ext = ".exe"
        folder = "Windows"
    elif sys_os == "Darwin":
        ext = ".app"
        folder = "MacOS"
    else: # Linux
        ext = ".bin"
        folder = "Linux"

    target_dir = dist_dir / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    
    banner(f"COMPILANDO INSTALADOR PARA {sys_os.upper()}")
    
    # Comando de Nuitka optimizado para el instalador
    cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        f"--output-dir={target_dir}",
        f"--output-filename=Multitool_Installer{ext}",
        "--enable-plugin=pyqt6",
        "--follow-imports",
        "--lto=yes",
        "--jobs=4", # Ajustar según procesador
        # Incluir el paquete data.zip si existe
        f"--include-data-file={base_path / 'data.zip'}=data.zip" if (base_path / "data.zip").exists() else "",
        str(downloader_script)
    ]

    # Quitar elementos vacíos si data.zip no existe
    cmd = [c for c in cmd if c]

    if sys_os == "Windows":
        cmd.insert(4, "--windows-console-mode=disable")

    try:
        print(f"[*] Ejecutando compilación en {folder}...")
        subprocess.run(cmd, check=True)
        print(f"\n[OK] ¡Éxito! El ejecutable se encuentra en: {target_dir}")
    except subprocess.CalledProcessError:
        print("\n[!] Error: Nuitka falló durante la compilación.")
    except Exception as e:
        print(f"\n[!] Error inesperado: {e}")

if __name__ == "__main__":
    # Verificar si Nuitka está instalado
    try:
        import nuitka
    except ImportError:
        print("[!] Nuitka no está instalado. Instalando con pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "nuitka", "zstandard"], check=True)
        
    compilar_downloader()
