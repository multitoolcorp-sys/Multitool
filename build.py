import os
import sys
import shutil
import zipfile
import subprocess
import traceback
import platform
from pathlib import Path

# Configuración General
APP_NAME    = "Multitool"
MAIN_APP    = "main.py"
DOWNLOADER  = "downloader.py"
OUTPUT_DIR  = "build_out"

def banner(texto):
    linea = "=" * (len(texto) + 4)
    print(f"\n{linea}")
    print(f"  {texto}")
    print(f"{linea}")

def verificar_archivos(base_path: Path):
    for f in [MAIN_APP, DOWNLOADER]:
        if not (base_path / f).exists():
            raise FileNotFoundError(f"Falta archivo esencial: {f}")
    print("[OK] Archivos base verificados.")

def limpiar_entorno(base_path: Path, full=False):
    """
    Limpia carpetas de salida y archivos temporales de desarrollo. 
    """
    carpetas = ["dist", OUTPUT_DIR, "DISTRIBUCION", "__pycache__", ".temp_preview", ".papelera"]
    if full:
        carpetas.append("build")
        
    for c in carpetas:
        ruta = base_path / c
        if ruta.exists():
            print(f"[limpiando] {ruta}")
            shutil.rmtree(ruta, ignore_errors=True)

    # Limpiar logs residuales de desarrollo
    logs_a_limpiar = [
        "multitool.log", "log_actualizaciones.txt", "nuitka-crash-report.xml",
        "nuitka_error.txt", "startup_hack.log"
    ]
    for log_name in logs_a_limpiar:
        log_file = base_path / log_name
        if log_file.exists():
            try:
                log_file.unlink()
                print(f"[limpiando archivo] {log_name}")
            except Exception: pass
    
    # Crear carpeta de distribución única
    dist_path = base_path / "DISTRIBUCION"
    dist_path.mkdir(parents=True, exist_ok=True)

def compilar_app_principal(base_path: Path):
    """
    Pasa la App principal a Standalone (Motor Núcleo).
    Excluye vistas.modulos para que permanezca 100% físico en disco.
    """
    banner("1. COMPILANDO APP PRINCIPAL (NÚCLEO STANDALONE)")
    sys_os = platform.system()
    app_ext = ".exe" if sys_os == "Windows" else ""
    
    lto_flag = "--lto=no" if sys_os == "Windows" else "--lto=yes"
    jobs_count = min(6, os.cpu_count() or 4)
    
    cmd = [
        sys.executable, "-m", "nuitka",
        "--assume-yes-for-downloads",
        "--standalone",
        f"--output-dir={base_path / OUTPUT_DIR}",
        f"--output-filename={APP_NAME}{app_ext}",
        f"--jobs={jobs_count}", 
        
        # Plugins y dependencias
        "--enable-plugin=pyqt6",
        "--follow-imports",
        lto_flag,
        
        # Exclusiones de paquetes pesados y módulos dinámicos
        "--nofollow-import-to=fitz",
        "--nofollow-import-to=pymupdf",
        "--nofollow-import-to=sympy",
        "--nofollow-import-to=torch",
        "--nofollow-import-to=ctranslate2",
        "--nofollow-import-to=argostranslate",
        "--nofollow-import-to=compilar_actualizacion",
        "--nofollow-import-to=vistas.modulos",
        "--nofollow-import-to=webview",
        "--nofollow-import-to=yt_dlp",
        "--nofollow-import-to=PyQt6.QtWebEngineWidgets",
        "--nofollow-import-to=PyQt6.QtWebEngineCore",
        
        # Módulos del núcleo del sistema (Core de MultiTool)
        "--include-module=ssl",
        "--include-module=uuid",
        "--include-module=smtplib",
        "--include-module=winsound",
        "--include-module=sqlite3",
        "--include-module=_sqlite3",
        "--include-package=email",
        "--include-package=requests",
        "--include-package=urllib",
        "--include-package=asyncio",
        "--include-package=zoneinfo",
        "--include-package=wsgiref",
        "--include-package=http",
        "--include-package=html",
        "--include-package=mimetypes",
        "--include-package=configparser",
        "--include-package=socketserver",
        "--include-package=ctypes",
        "--include-package=dataclasses",
        "--include-package=pickle",
        "--include-package=PyQt6.QtMultimedia",
        "--include-package=PyQt6.QtMultimediaWidgets",
        "--include-package=cryptography",
        "--include-package=vistas",
        "--include-package=controlador",
        
        # Entrada principal
        str(base_path / MAIN_APP)
    ]
    
    if sys_os == "Windows":
        cmd.insert(4, "--windows-console-mode=disable")
        ico_path = base_path / "vistas" / "utils" / "icono.ico"
        if ico_path.exists():
            cmd.append(f"--windows-icon-from-ico={ico_path}")
    
    try:
        subprocess.run(cmd, check=True)
        print("[OK] Núcleo compilado con éxito.")
    except subprocess.CalledProcessError:
        print("\n[!] ERROR DE NUITKA (App Principal): Revisar el log superior.")
        raise

def copiar_modulos_fisicos(base_path: Path):
    """Copia la carpeta vistas/modulos/ completa como código fuente físico en main.dist."""
    banner("COPIANDO MÓDULOS FÍSICOS")
    origen = base_path / "vistas" / "modulos"
    destino = base_path / OUTPUT_DIR / "main.dist" / "vistas" / "modulos"

    if not origen.exists():
        print(f"[!] No existe la carpeta de módulos: {origen}")
        return

    if destino.exists():
        shutil.rmtree(destino, ignore_errors=True)

    shutil.copytree(origen, destino, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.pyc", "__pycache__", ".extracted_plugins", ".git*"))
    cantidad = sum(1 for _ in destino.rglob("*") if _.is_file())
    print(f"[OK] Módulos físicos copiados: {cantidad} archivos en vistas/modulos/")

def copiar_plugins_fisicos(base_path: Path):
    """Copia la carpeta plugins/ si existe."""
    banner("COPIANDO PLUGINS FÍSICOS")
    origen = base_path / "plugins"
    destino = base_path / OUTPUT_DIR / "main.dist" / "plugins"

    if not origen.exists():
        print("[!] No existe carpeta plugins/ (omitiendo).")
        return

    if destino.exists():
        shutil.rmtree(destino, ignore_errors=True)

    shutil.copytree(origen, destino, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
    print("[OK] Plugins físicos copiados.")

def copiar_recursos_fisicos(base_path: Path):
    """Copia vistas, controlador, navegador.py y recursos manteniendo la estructura física."""
    banner("COPIANDO ESTRUCTURA DE RECURSOS Y CÓDIGO FÍSICO")
    dest_dist = base_path / OUTPUT_DIR / "main.dist"
    
    # Copiar scripts auxiliares de raíz (navegador.py y puente console.py)
    for sc in ["navegador.py", "console.py"]:
        src_sc = base_path / sc
        if src_sc.exists():
            shutil.copy2(src_sc, dest_dist / sc)
            print(f"[OK] {sc} copiado a main.dist")

    # Copiar controladores y drivers de bases de datos
    db_drv = base_path / "db_drivers"
    if db_drv.exists():
        shutil.copytree(db_drv, dest_dist / "db_drivers", dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
        print("[OK] db_drivers copiado a main.dist")

    for folder in ["vistas", "controlador", "recursos"]:
        origen = base_path / folder
        if not origen.exists():
            continue
        
        destino = dest_dist / folder
        if folder == "vistas":
            for root, dirs, files in os.walk(origen):
                rel_path = Path(root).relative_to(origen)
                # Omitir vistas/modulos porque ya se copió explícitamente por copiar_modulos_fisicos
                if rel_path.parts and rel_path.parts[0] == "modulos":
                    continue
                dest_sub = destino / rel_path
                dest_sub.mkdir(parents=True, exist_ok=True)
                for file in files:
                    if file.endswith(".pyc") or "__pycache__" in root:
                        continue
                    shutil.copy2(Path(root) / file, dest_sub / file)
        else:
            shutil.copytree(origen, destino, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
            
        print(f"[OK] Estructura física copiada: {folder}")

def copiar_paquetes_excluidos(base_path: Path):
    banner("COPIANDO PAQUETES EXCLUIDOS (FITZ/PYMUPDF/WEBVIEW/CLR/CFFI/WIN32/YT_DLP)")
    import site
    
    dest_dist = base_path / OUTPUT_DIR / "main.dist"
    if not dest_dist.exists():
        print(f"[!] No se encontró el directorio de destino: {dest_dist}")
        return
        
    site_packages_dirs = site.getsitepackages()
    
    # 1. Carpetas de paquetes
    paquetes = ["fitz", "pymupdf", "webview", "clr_loader", "pythonnet", "cffi", "pycparser", "win32", "win32com", "win32comext", "yt_dlp", "proxy_tools", "bottle"]
    for pkg in paquetes:
        pkg_source = None
        for sp_dir in site_packages_dirs:
            candidate = Path(sp_dir) / pkg
            if candidate.exists():
                pkg_source = candidate
                break
        
        if not pkg_source:
            import importlib.util
            try:
                spec = importlib.util.find_spec(pkg)
                if spec and spec.submodule_search_locations:
                    pkg_source = Path(spec.submodule_search_locations[0])
            except Exception: pass
                
        if pkg_source:
            pkg_dest = dest_dist / pkg
            if pkg_dest.exists():
                shutil.rmtree(pkg_dest, ignore_errors=True)
            try:
                if pkg_source.is_dir():
                    shutil.copytree(pkg_source, pkg_dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(pkg_source, pkg_dest)
                print(f"[OK] {pkg} copiado con éxito.")
            except Exception as e:
                print(f"[!] Error copiando {pkg}: {e}")
        else:
            print(f"[!] ADVERTENCIA: No se pudo encontrar el paquete '{pkg}' en site-packages para copiarlo.")

    # 2. Archivos individuales críticos (clr.py, pythoncom.py, pywintypes.py, proxy_tools.py, bottle.py, typing_extensions.py)
    archivos_sueltos = ["clr.py", "pythoncom.py", "pywintypes.py", "proxy_tools.py", "bottle.py", "typing_extensions.py"]
    for arc in archivos_sueltos:
        for sp_dir in site_packages_dirs:
            cand = Path(sp_dir) / arc
            if cand.exists():
                shutil.copy2(cand, dest_dist / arc)
                print(f"[OK] {arc} copiado con éxito a main.dist.")
                break

    # 3. Módulos binarios CFFI (_cffi_backend*.pyd)
    for sp_dir in site_packages_dirs:
        for pyd in Path(sp_dir).glob("_cffi_backend*.pyd"):
            shutil.copy2(pyd, dest_dist / pyd.name)
            print(f"[OK] CFFI Backend {pyd.name} copiado a main.dist.")

    # 4. DLLs del sistema pywin32 (pythoncom*.dll, pywintypes*.dll)
    for sp_dir in site_packages_dirs:
        pywin_sys = Path(sp_dir) / "pywin32_system32"
        if pywin_sys.exists():
            for dll_file in pywin_sys.glob("*.dll"):
                shutil.copy2(dll_file, dest_dist / dll_file.name)
                print(f"[OK] DLL {dll_file.name} copiada a main.dist.")

def compilar_updater(base_path: Path):
    """
    Compila updater.py como ejecutable independiente Updater.exe en build_out/main.dist.
    """
    banner("COMPILANDO ACTUALIZADOR EXTERNO (UPDATER.EXE)")
    updater_script = base_path / "updater.py"
    if not updater_script.exists():
        print("[!] Advertencia: updater.py no existe, omitiendo compilación de Updater.exe.")
        return

    sys_os = platform.system()
    app_ext = ".exe" if sys_os == "Windows" else ""
    dest_dist = base_path / OUTPUT_DIR / "main.dist"

    lto_flag = "--lto=no" if sys_os == "Windows" else "--lto=yes"
    jobs_count = min(6, os.cpu_count() or 4)

    cmd = [
        sys.executable, "-m", "nuitka",
        "--assume-yes-for-downloads",
        "--onefile",
        f"--output-dir={dest_dist}",
        f"--output-filename=Updater{app_ext}",
        f"--jobs={jobs_count}",
        lto_flag,
        str(updater_script)
    ]

    if sys_os == "Windows":
        cmd.insert(4, "--windows-console-mode=disable")

    try:
        print(f"Compilando Updater{app_ext}...")
        subprocess.run(cmd, check=True)
        print(f"[OK] Updater{app_ext} generado exitosamente en {dest_dist}")
    except subprocess.CalledProcessError:
        print("[!] Advertencia: Nuitka falló al compilar updater.py en binario. Se usará updater.py directo como fallback.")

def comprimir_distribucion(base_path: Path):
    """
    Comprime el resultado completo de main.dist en data.zip
    """
    banner("COMPRIMIENDO APP (data.zip)")
    dist_path = base_path / OUTPUT_DIR / "main.dist"
    if not dist_path.exists():
        raise FileNotFoundError("No se encontró la carpeta .dist de la app principal.")
    
    zip_path = base_path / "data.zip"
    if zip_path.exists(): zip_path.unlink()

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_path):
            for file in files:
                abs_path = Path(root) / file
                rel_path = abs_path.relative_to(dist_path)
                zipf.write(abs_path, rel_path)
    
    print(f"[OK] {zip_path.name} creado exitosamente con todos los módulos y binarios.")

def compilar_instalador(base_path: Path):
    """
    Compila el downloader.py como ejecutable independiente para el sistema actual.
    """
    banner(f"COMPILANDO INSTALADOR (DOWNLOADER) PARA {platform.system().upper()}")
    
    sys_os = platform.system()
    inst_ext = ".exe" if sys_os == "Windows" else ".bin"
    if sys_os == "Darwin": inst_ext = ".app"
    
    dest_dir = base_path / 'DISTRIBUCION'
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    lto_flag = "--lto=no" if sys_os == "Windows" else "--lto=yes"
    jobs_count = min(6, os.cpu_count() or 4)
    
    cmd = [
        sys.executable, "-m", "nuitka",
        "--assume-yes-for-downloads",
        "--onefile", 
        f"--output-dir={dest_dir}",
        f"--output-filename={APP_NAME}_Installer{inst_ext}",
        
        f"--jobs={jobs_count}",
        "--enable-plugin=pyqt6",
        "--follow-imports",
        lto_flag,
        
        str(base_path / DOWNLOADER)
    ]

    if sys_os == "Windows":
        cmd.insert(4, "--windows-console-mode=disable")
        cmd.append("--windows-uac-admin")
        ico_path = base_path / "vistas" / "utils" / "icono.ico"
        if ico_path.exists():
            cmd.append(f"--windows-icon-from-ico={ico_path}")
    
    try:
        print(f"Compilando instalador para {sys_os}...")
        subprocess.run(cmd, check=True)
        
        # Copiar data.zip junto al instalador
        zip_source = base_path / "data.zip"
        if zip_source.exists():
            shutil.copy2(zip_source, dest_dir / "data.zip")
            print(f"[OK] data.zip colocado junto al instalador en {dest_dir}")
    except subprocess.CalledProcessError:
        print(f"\n[!] ERROR DE NUITKA (Instalador): Revisar el log superior.")
        raise

def generar_instaladores_cross(base_path: Path):
    """
    Genera instaladores auto-extraíbles para Linux (.sh) y MacOS (.command)
    utilizando data.zip y downloader.py.
    """
    banner("GENERANDO INSTALADORES MULTIPLATAFORMA (LINUX Y MACOS)")
    try:
        from generar_instaladores_cross import generate_linux_installer, generate_macos_installer
        generate_linux_installer()
        generate_macos_installer()
        print("[OK] Paquetes de instalación para Linux y MacOS generados con éxito.")
    except Exception as e:
        print(f"[!] Nota: No se pudieron generar instaladores cross-platform: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Utilidad de Compilación y Distribución de Multitool")
    parser.add_argument("--only-app", action="store_true", help="Compila solo la aplicación standalone sin empaquetar")
    parser.add_argument("--only-installer", action="store_true", help="Genera el instalador final usando el data.zip existente (omite compilar la app principal)")
    parser.add_argument("--cross", action="store_true", help="Genera también los scripts de instalación para Linux y MacOS")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    try:
        verificar_archivos(base)
        
        if args.only_installer:
            banner("COMPILANDO UNICAMENTE EL INSTALADOR (downloader.py)")
            zip_path = base / "data.zip"
            if not zip_path.exists():
                raise FileNotFoundError("Error: No se encontró 'data.zip'. Es necesario compilar la app principal primero para generarlo.")
            
            compilar_instalador(base)
            generar_instaladores_cross(base)
            banner("PROCESO DE INSTALADOR COMPLETADO - OK")
            print(f"Resultado en: {base / 'DISTRIBUCION'}")
            return
            
        # Limpieza
        limpiar_entorno(base)
        
        # 1. Compilar App Núcleo
        compilar_app_principal(base)
        
        # 2. Copiar archivos y estructura física (Módulos, Plugins, Recursos, Controlador)
        copiar_modulos_fisicos(base)
        copiar_plugins_fisicos(base)
        copiar_recursos_fisicos(base)
        
        # 3. Copiar paquetes excluidos (fitz / pymupdf)
        copiar_paquetes_excluidos(base)
        
        # 4. Compilar actualizador externo (Updater.exe)
        compilar_updater(base)
        
        if args.only_app:
            banner("COMPILACION DE APP (STANDALONE) COMPLETADA - OK")
            print(f"Resultado en: {base / OUTPUT_DIR / 'main.dist'}")
            return
            
        # 5. Comprimir resultado completo en data.zip
        comprimir_distribucion(base)
        
        # 6. Compilar instalador con data.zip embebido
        compilar_instalador(base)

        # 7. Generar instaladores multiplataforma (Linux / MacOS)
        generar_instaladores_cross(base)

        banner("PROCESO DE DISTRIBUCION COMPLETADO - OK")
        print(f"Resultado en: {base / 'DISTRIBUCION'}")

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    main()