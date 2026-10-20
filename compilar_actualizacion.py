import os
import sys
import shutil
import zipfile
import subprocess
import json
import platform
import time
from pathlib import Path
import datetime

# Intentar importar componentes de PyQt6 para la interfaz gráfica
try:
    from PyQt6.QtWidgets import (
        QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton,
        QPlainTextEdit, QLabel, QProgressBar, QMessageBox, QFrame, QScrollArea, QLineEdit
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QIcon, QTextCursor
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

def banner(texto):
    linea = "=" * (len(texto) + 4)
    print(f"\n{linea}")
    print(f"  {texto}")
    print(f"{linea}")

def resolver_nombre_archivo(directorio, base_defecto, custom_name=None):
    if custom_name:
        nombre = custom_name.strip()
        if nombre:
            if not nombre.lower().endswith(".mtu"):
                nombre += ".mtu"
            return directorio / nombre
            
    base_name = base_defecto
    if base_name.lower().endswith(".mtu"):
        base_name = base_name[:-4]
        
    path = directorio / f"{base_name}.mtu"
    if not path.exists():
        return path
        
    i = 1
    while True:
        candidate = directorio / f"{base_name}_v{i}.mtu"
        if not candidate.exists():
            return candidate
        i += 1

def obtener_ruta_destino(directorio, base_defecto, custom_name, num_outputs, sufijo):
    if num_outputs > 1 and custom_name:
        c_name = custom_name.strip()
        if c_name:
            if c_name.lower().endswith(".mtu"):
                c_name = c_name[:-4]
            nombre_base = f"{c_name}_{sufijo}"
            return resolver_nombre_archivo(directorio, nombre_base, None)
    return resolver_nombre_archivo(directorio, base_defecto, custom_name)

def generar_manifest_json(tipo, target_name="sistema", descripcion=""):
    """
    Genera el diccionario del manifest estandarizado para archivos .mtu.
    """
    return {
        "app": "Multitool",
        "version": "4.0.0",
        "type": tipo,
        "target": target_name,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": descripcion or "Actualización de Multitool Corp."
    }

def agregar_core_al_zip(zipf, dist_dir, descripcion=""):
    """
    Agrega el Core al ZIP de actualización.

    IMPORTANTE:
    El Core NO debe contener vistas/modulos,
    ya que los módulos tienen su propio sistema de actualización.
    """
    manifest = generar_manifest_json("core", "sistema", descripcion)
    zipf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

    if descripcion:
        zipf.writestr("descripcion.txt", descripcion.encode("utf-8"))

    for root, dirs, files in os.walk(dist_dir):
        rel_dir = Path(root).relative_to(dist_dir)

        # Si ya estamos dentro de vistas/modulos, no procesar nada.
        if rel_dir.parts[:2] == ("vistas", "modulos"):
            dirs[:] = []
            continue

        # Cuando estamos exactamente en vistas/, impedir que os.walk() entre en modulos/.
        if rel_dir.parts == ("vistas",):
            dirs[:] = [d for d in dirs if d != "modulos"]

        for file in files:
            abs_path = Path(root) / file
            rel_path = abs_path.relative_to(dist_dir)

            # Protección adicional
            if rel_path.parts[:2] == ("vistas", "modulos"):
                continue

            zipf.write(abs_path, rel_path)

def verificar_core_zip(zip_path):
    """
    Comprueba automáticamente que update_sistema.mtu no contenga elementos de vistas/modulos/.
    """
    with zipfile.ZipFile(zip_path, "r") as zipf:
        archivos = zipf.namelist()

    prohibido = []
    for archivo in archivos:
        partes = Path(archivo).parts
        if partes[:2] == ("vistas", "modulos"):
            prohibido.append(archivo)

    if prohibido:
        raise RuntimeError(
            "ERROR: update_sistema.mtu contiene módulos:\n"
            + "\n".join(prohibido[:20])
        )

    print("[OK] Verificación Core: no contiene vistas/modulos/")

def limpiar_versiones_inexistentes_web(web_base, log_signal=None):
    """
    Recorre data.json y elimina automáticamente aquellas versiones cuyos archivos .mtu
    hayan sido borrados de la carpeta public/actualizaciones_multitool/ para evitar enlaces rotos.
    """
    try:
        data_json_path = web_base / "api" / "data.json"
        if not data_json_path.exists():
            return
            
        with open(data_json_path, "r", encoding="utf-8") as f:
            apps_data = json.load(f)

        item = next((a for a in apps_data if a.get("id") == "update-principal"), None)
        if not item or "versions" not in item:
            return

        versions_originales = item.get("versions", [])
        versions_validas = []
        removidos = 0

        for v in versions_originales:
            url = v.get("url", "")
            if url.startswith("/actualizaciones_multitool/"):
                rel_path = url.lstrip("/")
                file_on_disk = web_base / "public" / rel_path
                if not file_on_disk.exists():
                    removidos += 1
                    msg = f"[WEB CLEANUP] Eliminando referencia antigua a .mtu borrado: {url}"
                    if log_signal:
                        log_signal.emit(msg)
                    else:
                        print(msg)

                    # Eliminar acompañantes .txt/.json si existieran
                    try:
                        txt_stem = file_on_disk.with_suffix(".txt")
                        if txt_stem.exists(): txt_stem.unlink()
                        json_stem = file_on_disk.with_suffix(".json")
                        if json_stem.exists(): json_stem.unlink()
                    except Exception:
                        pass
                    continue
            versions_validas.append(v)

        if removidos > 0:
            item["versions"] = versions_validas
            with open(data_json_path, "w", encoding="utf-8") as f:
                json.dump(apps_data, f, indent=2, ensure_ascii=False)
            msg_clean = f"[WEB CLEANUP] Se eliminaron {removidos} versión(es) obsoleta(s) de data.json"
            if log_signal:
                log_signal.emit(msg_clean)
            else:
                print(msg_clean)
    except Exception as e:
        err = f"[WEB CLEANUP WARN] Error limpiando catálogo: {e}"
        if log_signal:
            log_signal.emit(err)
        else:
            print(err)


def incrementar_version_semver(version_str, tiene_novedad=False, tiene_arreglo=False):
    clean_v = str(version_str).strip().lstrip("v")
    parts = clean_v.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        major, minor, patch = 21, 0, 0

    if tiene_novedad:
        minor += 1
        patch = 0
    elif tiene_arreglo:
        patch += 1
    else:
        patch += 1

    return f"{major}.{minor}.{patch}"

def obtener_o_actualizar_version_modulo(base_dir, mod_name, descripcion=""):
    """
    Lee 'vistas/modulos/<mod_name>/utils/version.json', calcula la nueva versión SemVer
    según la descripción (+ = MINOR bump 21.1.0, - = PATCH bump 21.0.1) y la guarda de nuevo.
    """
    mod_dir = Path(base_dir) / "vistas" / "modulos" / mod_name
    utils_dir = mod_dir / "utils"
    utils_dir.mkdir(parents=True, exist_ok=True)
    vfile = utils_dir / "version.json"
    
    current_ver = "21.0.0"
    vdata = {}
    if vfile.exists():
        try:
            with open(vfile, "r", encoding="utf-8") as f:
                vdata = json.load(f)
                current_ver = vdata.get("version", "21.0.0")
        except Exception:
            pass

    tiene_novedad = False
    tiene_arreglo = False
    
    if descripcion:
        lines = [l.strip() for l in descripcion.splitlines() if l.strip()]
        for line in lines:
            if line.startswith("+") or any(k in line.lower() for k in ["añadido", "novedad", "nueva", "feature", "agregado"]):
                tiene_novedad = True
            if line.startswith("-") or any(k in line.lower() for k in ["solucionado", "corregido", "fix", "bug", "error", "parche"]):
                tiene_arreglo = True

    nueva_ver = incrementar_version_semver(current_ver, tiene_novedad, tiene_arreglo)

    vdata["modulo"] = mod_name
    vdata["version"] = nueva_ver
    vdata["ultima_actualizacion"] = time.strftime("%Y-%m-%d")
    vdata["descripcion"] = descripcion or f"Actualización del módulo {mod_name.capitalize()} v{nueva_ver}"
    
    historial = vdata.get("historial", [])
    historial.insert(0, {
        "version": nueva_ver,
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "descripcion": descripcion or "Actualización de módulo."
    })
    vdata["historial"] = historial

    with open(vfile, "w", encoding="utf-8") as f:
        json.dump(vdata, f, indent=2, ensure_ascii=False)

    try:
        doc_utils = Path.home() / "Documents" / "Multitool" / "vistas" / "modulos" / mod_name / "utils"
        doc_utils.mkdir(parents=True, exist_ok=True)
        shutil.copy2(vfile, doc_utils / "version.json")
    except Exception:
        pass

    return nueva_ver

ALL_23_MODULES = [
    "archivos", "calculadora", "calendario", "chat", "clipboard",
    "cuaderno", "cuenta", "emulador", "extras", "general",
    "grabadora", "minigames", "navegador", "notas", "proyectos",
    "reproductor", "seguridad", "sistema", "terminal", "tiempo",
    "traductor", "widgets", "basedatos"
]

def copiar_y_registrar_actualizacion_web(base_dir, tipo, zip_filename, log_signal=None, descripcion="", mod_name=None, num_items=1, mod_version="21.0.0"):
    """
    Copia el archivo .mtu a la subcarpeta correspondiente en la página web:
      - 'core': pagina/public/updates/core/
      - 'auth': pagina/public/updates/auth/
      - 'modulo' (1 solo módulo): pagina/public/updates/modulos/<modulo>/
      - 'generales' / 'multimodulo' / num_items > 1: pagina/public/updates/generales/
    """
    try:
        web_base = Path(base_dir).parent / "pagina"
        public_updates = web_base / "public" / "updates"
        
        (public_updates / "core").mkdir(parents=True, exist_ok=True)
        (public_updates / "auth").mkdir(parents=True, exist_ok=True)
        (public_updates / "generales").mkdir(parents=True, exist_ok=True)
        for mod in ALL_23_MODULES:
            (public_updates / "modulos" / mod).mkdir(parents=True, exist_ok=True)

        if num_items > 1 or tipo in ["multimodulo", "general", "generales"]:
            sub_path = Path("generales")
            tipo_label = "Actualización General (Multimódulo)"
        elif tipo == "core" or zip_filename.name == "update_sistema.mtu":
            sub_path = Path("core")
            tipo_label = "Sistema Base (Core)"
        elif tipo in ["auth", "oaut", "oauth", "autenticacion"]:
            sub_path = Path("auth")
            tipo_label = "Sistema de Autenticación (Auth)"
        elif tipo == "modulo" and mod_name:
            sub_path = Path("modulos") / mod_name.lower().strip()
            tipo_label = f"Módulo: {mod_name.title()}"
        else:
            sub_path = Path("generales")
            tipo_label = "Actualización General"

        target_dir = public_updates / sub_path
        target_dir.mkdir(parents=True, exist_ok=True)
        
        dest_file = target_dir / zip_filename.name
        shutil.copy2(zip_filename, dest_file)

        desc_text = descripcion.strip() if (descripcion and descripcion.strip()) else f"Parche {zip_filename.name}"
        size_mb = f"{max(0.1, round(zip_filename.stat().st_size / (1024*1024), 2))} MB"

        desc_json = target_dir / f"{zip_filename.stem}.json"
        metadata = {
            "archivo": zip_filename.name,
            "tipo": tipo,
            "categoria": tipo_label,
            "modulo": mod_name if mod_name else "",
            "version": mod_version,
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
            "size": size_mb,
            "descripcion": desc_text
        }
        with open(desc_json, "w", encoding="utf-8") as f_meta:
            json.dump(metadata, f_meta, indent=2, ensure_ascii=False)

        msg_log = f"[WEB] Copiado .mtu y generado .json metadata (v{mod_version}) en: {dest_file.relative_to(web_base)}"
        if log_signal:
            log_signal.emit(msg_log)
        else:
            print(msg_log)

        data_json_path = web_base / "api" / "data.json"
        if data_json_path.exists():
            with open(data_json_path, "r", encoding="utf-8") as f:
                apps_data = json.load(f)
                
            relative_url = f"/updates/{sub_path.as_posix()}/{zip_filename.name}"
            clean_name = zip_filename.stem.replace("update_", "").replace("_", " ").title()
            badge_name = f"{tipo_label}"

            item = next((a for a in apps_data if a.get("id") == "update-principal"), None)
            if not item:
                item = {
                    "id": "update-principal",
                    "name": "Actualizaciones de Módulos",
                    "category": "Actualizaciones",
                    "tags": ["Actualización", "Módulos", "Sistema"],
                    "status": "official",
                    "icon": "🔄",
                    "image": "",
                    "description": "Lista de actualizaciones y parches .mtu para Multitool Suite.",
                    "longDesc": "Canal oficial unificado de actualizaciones. Lista completa de parches de módulos y del sistema.",
                    "developer": "MultiToolCorp",
                    "platform": ["Windows"],
                    "featured": False,
                    "versions": []
                }
                apps_data.append(item)

            versions = item.get("versions", [])
            versions = [v for v in versions if v.get("url") != relative_url]
            
            nueva_version = {
                "version": f"v{mod_version} ({clean_name})",
                "releaseDate": time.strftime("%Y-%m-%d"),
                "size": size_mb,
                "url": relative_url,
                "platforms": ["Windows"],
                "badge": badge_name,
                "changelog": desc_text
            }
            versions.insert(0, nueva_version)
            item["versions"] = versions
            
            with open(data_json_path, "w", encoding="utf-8") as f:
                json.dump(apps_data, f, indent=2, ensure_ascii=False)
                
            msg_catalog = f"[WEB] Catálogo data.json actualizado con versión {nueva_version['version']} ({relative_url})"
            if log_signal:
                log_signal.emit(msg_catalog)
            else:
                print(msg_catalog)

        limpiar_versiones_inexistentes_web(web_base, log_signal)
    except Exception as e:
        err_msg = f"[WEB WARN] No se pudo copiar a carpeta web: {e}"
        if log_signal:
            log_signal.emit(err_msg)
        else:
            print(err_msg)

# Hilo de compilación para ejecutar Nuitka sin congelar la GUI
if HAS_PYQT:
    class CompileWorker(QThread):
        log_signal = pyqtSignal(str)
        progress_signal = pyqtSignal(int, str)
        finished_signal = pyqtSignal(bool, str)

        def __init__(self, base_dir, modulos_a_compilar, compilar_sistema, compilar_autenticacion=False, unificar_modulos=False, nombre_personalizado="", descripcion="", copiar_a_web=True):
            super().__init__()
            self.base_dir = base_dir
            self.modulos = modulos_a_compilar
            self.compilar_sistema = compilar_sistema
            self.compilar_autenticacion = compilar_autenticacion
            self.unificar = unificar_modulos
            self.nombre_personalizado = nombre_personalizado.strip()
            self.descripcion = descripcion.strip()
            self.copiar_a_web = copiar_a_web

        def read_process_output(self, process):
            buffer = bytearray()
            pending_cr = False
            overwrite_next = False
            
            while True:
                b = process.stdout.read(1)
                if b == b'':
                    break
                
                if b == b'\r':
                    if pending_cr:
                        if overwrite_next:
                            self.log_signal.emit("\r" + buffer.decode('utf-8', errors='replace').rstrip('\r\n'))
                        else:
                            self.log_signal.emit(buffer.decode('utf-8', errors='replace').rstrip('\r\n'))
                        buffer.clear()
                        overwrite_next = True
                    else:
                        pending_cr = True
                elif b == b'\n':
                    if pending_cr:
                        if overwrite_next:
                            self.log_signal.emit("\r" + buffer.decode('utf-8', errors='replace').rstrip('\r\n'))
                        else:
                            self.log_signal.emit(buffer.decode('utf-8', errors='replace').rstrip('\r\n'))
                        buffer.clear()
                        overwrite_next = False
                        pending_cr = False
                    else:
                        if overwrite_next:
                            self.log_signal.emit("\r" + buffer.decode('utf-8', errors='replace').rstrip('\r\n'))
                        else:
                            self.log_signal.emit(buffer.decode('utf-8', errors='replace').rstrip('\r\n'))
                        buffer.clear()
                        overwrite_next = False
                else:
                    if pending_cr:
                        if overwrite_next:
                            self.log_signal.emit("\r" + buffer.decode('utf-8', errors='replace').rstrip('\r\n'))
                        else:
                            self.log_signal.emit(buffer.decode('utf-8', errors='replace').rstrip('\r\n'))
                        buffer.clear()
                        overwrite_next = True
                        pending_cr = False
                    buffer.extend(b)
                    
            if pending_cr or buffer:
                if overwrite_next:
                    self.log_signal.emit("\r" + buffer.decode('utf-8', errors='replace').rstrip('\r\n'))
                else:
                    self.log_signal.emit(buffer.decode('utf-8', errors='replace').rstrip('\r\n'))

        def run(self):
            sys_os = platform.system()
            ext_bin = ".pyd" if sys_os == "Windows" else ".so"
            updates_out = self.base_dir / "DISTRIBUCION" / "UPDATES"
            updates_out.mkdir(parents=True, exist_ok=True)
            
            num_outputs = (1 if self.compilar_sistema else 0) + (1 if self.compilar_autenticacion else 0) + (1 if (self.modulos and self.unificar) else len(self.modulos))
            
            # Limpiar directorio temporal antes de empezar
            temp_dir = self.base_dir / "updates_temp"
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 1. COMPILAR SISTEMA (CORE) si está solicitado
            if self.compilar_sistema:
                self.progress_signal.emit(5, "Compilando Sistema (Core)...")
                self.log_signal.emit("\n=== INICIANDO COMPILACIÓN DEL SISTEMA (CORE) ===")
                
                temp_sys_dir = temp_dir / "sistema_build"
                temp_sys_dir.mkdir(parents=True, exist_ok=True)
                
                # Comando Nuitka similar a build.py para crear la app core standalone
                cmd = [
                    sys.executable, "-m", "nuitka",
                    "--assume-yes-for-downloads",
                    "--standalone",
                    "--show-progress",
                    f"--output-dir={temp_sys_dir}",
                    "--output-filename=Multitool.exe" if sys_os == "Windows" else "Multitool",
                    "--jobs=8",
                    "--enable-plugin=pyqt6",
                    "--follow-imports",
                    "--lto=no",
                    "--nofollow-import-to=fitz",
                    "--nofollow-import-to=pymupdf",
                    "--nofollow-import-to=sympy",
                    "--nofollow-import-to=torch",
                    "--nofollow-import-to=ctranslate2",
                    "--nofollow-import-to=argostranslate",
                    "--nofollow-import-to=compilar_actualizacion",
                    "--include-module=ssl",
                    "--include-package=urllib",
                    "--include-package=vistas",
                    "--include-package=controlador",
                    "--include-data-dir=vistas=vistas",
                    "--include-data-dir=controlador=controlador",
                    str(self.base_dir / "main.py")
                ]
                if sys_os == "Windows":
                    cmd.insert(4, "--windows-console-mode=disable")
                
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        bufsize=0,
                        shell=True if sys_os == "Windows" else False
                    )
                    self.read_process_output(process)
                    rc = process.wait()
                    if rc != 0:
                        self.log_signal.emit(f"[!] Nuitka finalizó con código de error {rc}")
                        self.finished_signal.emit(False, "Error compilando el sistema principal.")
                        return
                except Exception as e:
                    self.log_signal.emit(f"[!] Falló la ejecución de Nuitka de Sistema: {e}")
                    self.finished_signal.emit(False, f"Excepción en compilación de sistema: {e}")
                    return
                
                # Copiar fitz y pymupdf excluidos si existen en site-packages
                dist_dir = temp_sys_dir / "main.dist"
                if dist_dir.exists():
                    self.log_signal.emit("Copiando dependencias externas excluidas (fitz/pymupdf)...")
                    import site
                    site_packages_dirs = site.getsitepackages()
                    for pkg in ["fitz", "pymupdf"]:
                        pkg_source = None
                        for sp_dir in site_packages_dirs:
                            candidate = Path(sp_dir) / pkg
                            if candidate.exists():
                                pkg_source = candidate
                                break
                        if pkg_source:
                            shutil.copytree(pkg_source, dist_dir / pkg, dirs_exist_ok=True)
                            self.log_signal.emit(f"[OK] Paquete {pkg} copiado al Core de distribución.")
                    
                    # Comprimir core en update_sistema.mtu OMITIENDO vistas/modulos
                    zip_filename = obtener_ruta_destino(updates_out, "update_sistema", self.nombre_personalizado, num_outputs, "sistema")
                    if zip_filename.exists():
                        zip_filename.unlink()
                        
                    self.log_signal.emit(f"Empaquetando {zip_filename.name} (excluyendo vistas/modulos/)...")
                    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        agregar_core_al_zip(zipf, dist_dir, self.descripcion)

                    try:
                        verificar_core_zip(zip_filename)
                        self.log_signal.emit("[OK] Verificación Core: update_sistema.mtu no contiene vistas/modulos/.")
                    except Exception as ve:
                        self.log_signal.emit(f"[!] ERROR DE VERIFICACIÓN: {ve}")
                        raise ve

                    self.log_signal.emit(f"[ÉXITO] Actualización de Sistema empaquetada en:\n -> {zip_filename.name}")
                    if self.copiar_a_web:
                        copiar_y_registrar_actualizacion_web(self.base_dir, "core", zip_filename, self.log_signal, self.descripcion)
                    else:
                        self.log_signal.emit(f"[WEB OMITIDO] No se copió a la web (guardado únicamente en UPDATES/{zip_filename.name}).")
            
            # 1.5. COMPILAR / EMPAQUETAR SISTEMA DE AUTENTICACIÓN si está solicitado
            if self.compilar_autenticacion:
                self.progress_signal.emit(20, "Empaquetando Sistema de Autenticación...")
                self.log_signal.emit("\n=== INICIANDO COMPILACIÓN DEL SISTEMA DE AUTENTICACIÓN (OAUTH & CUENTAS) ===")
                
                temp_auth_dir = temp_dir / "autenticacion_build"
                if temp_auth_dir.exists():
                    shutil.rmtree(temp_auth_dir, ignore_errors=True)
                temp_auth_dir.mkdir(parents=True, exist_ok=True)
                
                # Copiar controlador/auth
                ctrl_auth_src = self.base_dir / "controlador" / "auth"
                if ctrl_auth_src.exists():
                    dest = temp_auth_dir / "controlador" / "auth"
                    shutil.copytree(ctrl_auth_src, dest, dirs_exist_ok=True)
                    self.log_signal.emit("[OK] Controlador de Autenticación copiado.")
                
                # Copiar módulo cuenta
                cuenta_src = self.base_dir / "vistas" / "modulos" / "cuenta"
                if cuenta_src.exists():
                    dest = temp_auth_dir / "vistas" / "modulos" / "cuenta"
                    shutil.copytree(cuenta_src, dest, dirs_exist_ok=True)
                    self.log_signal.emit("[OK] Módulo Vista Cuenta copiado.")
                
                # Copiar oauth_manager si existe
                oauth_src = self.base_dir / "vistas" / "modulos" / "navegador" / "utils" / "oauth_manager.py"
                if oauth_src.exists():
                    dest = temp_auth_dir / "vistas" / "modulos" / "navegador" / "utils" / "oauth_manager.py"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(oauth_src, dest)
                    self.log_signal.emit("[OK] Gestor Google OAuth copiado.")
                
                # Empaquetar en update_autenticacion.mtu
                zip_filename = obtener_ruta_destino(updates_out, "update_autenticacion", self.nombre_personalizado, num_outputs, "autenticacion")
                if zip_filename.exists():
                    zip_filename.unlink()
                    
                self.log_signal.emit(f"Empaquetando {zip_filename.name}...")
                with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    manifest = generar_manifest_json("auth", "autenticacion", self.descripcion)
                    zipf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
                    if self.descripcion:
                        zipf.writestr("descripcion.txt", self.descripcion.encode("utf-8"))
                    for root, dirs, files in os.walk(temp_auth_dir):
                        for file in files:
                            abs_path = Path(root) / file
                            rel_path = abs_path.relative_to(temp_auth_dir)
                            zipf.write(abs_path, rel_path)
                            
                self.log_signal.emit(f"[ÉXITO] Actualización de Autenticación empaquetada en:\n -> {zip_filename.name}")
                if self.copiar_a_web:
                    copiar_y_registrar_actualizacion_web(self.base_dir, "oaut", zip_filename, self.log_signal, self.descripcion)
                else:
                    self.log_signal.emit(f"[WEB OMITIDO] No se copió a la web (guardado únicamente en UPDATES/{zip_filename.name}).")

            # 2. COMPILAR MÓDULOS si hay solicitados
            if self.modulos:
                total_mods = len(self.modulos)
                unified_temp_dir = temp_dir / "unified"
                if self.unificar:
                    unified_temp_dir.mkdir(parents=True, exist_ok=True)

                for index, mod_name in enumerate(self.modulos):
                    pct = 35 + int((index / total_mods) * 55)
                    self.progress_signal.emit(pct, f"Compilando módulo: {mod_name}...")
                    self.log_signal.emit(f"\n=== COMPILANDO MÓDULO: {mod_name.upper()} ===")
                    
                    mod_dir = self.base_dir / "vistas" / "modulos" / mod_name
                    if not mod_dir.exists():
                        self.log_signal.emit(f"[!] Error: El módulo '{mod_name}' no existe en {mod_dir}")
                        continue
                    
                    config_path = mod_dir / "config.json"
                    main_file = None
                    if config_path.exists():
                        try:
                            with open(config_path, "r", encoding="utf-8") as f:
                                cfg = json.load(f)
                                main_file = cfg.get("file_name")
                                if not main_file:
                                    for alt in [f"{mod_name}.py", f"{mod_name}_main.py", "widgets_main.py", "main.py"]:
                                        if (mod_dir / alt).exists():
                                            main_file = alt
                                            break
                                if not main_file and "submodulos" in cfg and isinstance(cfg["submodulos"], list) and len(cfg["submodulos"]) > 0:
                                    main_file = cfg["submodulos"][0].get("file_name")
                        except Exception as e:
                            self.log_signal.emit(f"[!] Advertencia leyendo config.json: {e}")
                    
                    if not main_file:
                        main_file = "main.py"

                    target_py = mod_dir / main_file
                    if not target_py.exists():
                        encontrado = False
                        for alt in [f"{mod_name}.py", f"{mod_name}_main.py", "widgets_main.py", "main.py"]:
                            alt_path = mod_dir / alt
                            if alt_path.exists():
                                target_py = alt_path
                                encontrado = True
                                break
                        if not encontrado:
                            self.log_signal.emit(f"[!] Error: No se encontró el script de entrada {target_py}")
                            continue
                    
                    # Carpeta temporal del módulo
                    temp_update_dir = temp_dir / "modules_temp" / mod_name
                    if temp_update_dir.exists():
                        shutil.rmtree(temp_update_dir, ignore_errors=True)
                    temp_update_dir.mkdir(parents=True, exist_ok=True)
                    
                    self.log_signal.emit(f"Compilando script de entrada: {target_py.name}...")
                    
                    cmd = [
                        sys.executable, "-m", "nuitka",
                        "--assume-yes-for-downloads",
                        "--module",
                        "--show-progress",
                        f"--output-dir={temp_dir}",
                        "--jobs=8",
                        "--lto=no",
                        str(target_py)
                    ]
                    
                    try:
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            bufsize=0,
                            shell=True if sys_os == "Windows" else False
                        )
                        self.read_process_output(process)
                        rc = process.wait()
                        if rc != 0:
                            self.log_signal.emit(f"[!] Nuitka finalizó con código de error {rc}")
                            continue
                    except Exception as e:
                        self.log_signal.emit(f"[!] Falló la ejecución de Nuitka: {e}")
                        continue
                    
                    # Buscar binario compilado generado
                    file_base_name = target_py.stem
                    compiled_file = None
                    for item in temp_dir.iterdir():
                        if item.is_file() and item.name.startswith(file_base_name) and item.name.endswith(ext_bin):
                            compiled_file = item
                            break
                            
                    if not compiled_file:
                        self.log_signal.emit(f"[!] Error: No se generó el archivo compilado {file_base_name}{ext_bin}")
                        continue
                        
                    self.log_signal.emit(f"[OK] Módulo compilado con éxito: {compiled_file.name}")
                    
                    # Mover archivo a la estructura temporal con reintentos
                    moved = False
                    for attempt in range(5):
                        try:
                            if (temp_update_dir / f"{file_base_name}{ext_bin}").exists():
                                (temp_update_dir / f"{file_base_name}{ext_bin}").unlink()
                            shutil.move(str(compiled_file), str(temp_update_dir / f"{file_base_name}{ext_bin}"))
                            moved = True
                            break
                        except Exception as e:
                            self.log_signal.emit(f"[!] Intento {attempt + 1}: No se pudo mover el archivo. Reintentando en 1s... ({e})")
                            time.sleep(1)
                    
                    if not moved:
                        self.log_signal.emit("[!] Advertencia: Falló el movimiento directo. Intentando copia + eliminación diferida...")
                        try:
                            shutil.copy2(str(compiled_file), str(temp_update_dir / f"{file_base_name}{ext_bin}"))
                            try:
                                os.unlink(compiled_file)
                            except: pass
                        except Exception as e:
                            self.log_signal.emit(f"[!] Error crítico al copiar el módulo: {e}")
                            continue
                    
                    # Copiar recursos adicionales
                    for root, dirs, files in os.walk(mod_dir):
                        rel_path = Path(root).relative_to(mod_dir)
                        if "__pycache__" in root or "browser_data" in root:
                            continue
                        dest_subdir = temp_update_dir / rel_path
                        dest_subdir.mkdir(parents=True, exist_ok=True)
                        
                        for file in files:
                            src_file = Path(root) / file
                            dest_file = dest_subdir / file
                            shutil.copy2(src_file, dest_file)
                            
                    self.log_signal.emit("Recursos copiados correctamente.")
                    
                    # Actualizar versión SemVer del módulo según la descripción (+/-)
                    mod_ver = obtener_o_actualizar_version_modulo(self.base_dir, mod_name, self.descripcion)
                    self.log_signal.emit(f"Versión calculada del módulo '{mod_name}': v{mod_ver}")
                    
                    # Empaquetamiento
                    if self.unificar:
                        # Copiar todo a la carpeta unificada
                        dest_unified = unified_temp_dir / "vistas" / "modulos" / mod_name
                        dest_unified.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(temp_update_dir, dest_unified, dirs_exist_ok=True)
                        self.log_signal.emit("Módulo copiado para empaquetado unificado.")
                    else:
                        # ZIP Individual (.mtu)
                        zip_filename = obtener_ruta_destino(updates_out, f"update_{mod_name}", self.nombre_personalizado, num_outputs, mod_name)
                        if zip_filename.exists():
                            zip_filename.unlink()
                            
                        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            manifest = generar_manifest_json("module", mod_name, self.descripcion)
                            manifest["version"] = mod_ver
                            zipf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
                            if self.descripcion:
                                zipf.writestr("descripcion.txt", self.descripcion.encode("utf-8"))
                            for root, dirs, files in os.walk(temp_update_dir):
                                for file in files:
                                    abs_path = Path(root) / file
                                    rel_path = abs_path.relative_to(temp_update_dir)
                                    zip_path_in_archive = Path("vistas") / "modulos" / mod_name / rel_path
                                    zipf.write(abs_path, zip_path_in_archive)
                                    
                        self.log_signal.emit(f"[ÉXITO] Actualización empaquetada en:\n -> {zip_filename.name} (v{mod_ver})")
                        if self.copiar_a_web:
                            copiar_y_registrar_actualizacion_web(self.base_dir, "modulo", zip_filename, self.log_signal, self.descripcion, mod_name=mod_name, num_items=1, mod_version=mod_ver)
                        else:
                            self.log_signal.emit(f"[WEB OMITIDO] No se copió a la web (guardado únicamente en UPDATES/{zip_filename.name}).")
                
                # Crear ZIP de actualización unificada si aplica
                if self.unificar and unified_temp_dir.exists():
                    zip_filename = obtener_ruta_destino(updates_out, "update_multimodulo", self.nombre_personalizado, num_outputs, "multimodulo")
                    if zip_filename.exists():
                        zip_filename.unlink()
                        
                    self.log_signal.emit(f"\nCreando archivo de actualización unificada ({zip_filename.name})...")
                    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        manifest = generar_manifest_json("multimodulo", "varios_modulos", self.descripcion)
                        zipf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
                        if self.descripcion:
                            zipf.writestr("descripcion.txt", self.descripcion.encode("utf-8"))
                        for root, dirs, files in os.walk(unified_temp_dir):
                            for file in files:
                                abs_path = Path(root) / file
                                rel_path = abs_path.relative_to(unified_temp_dir)
                                zipf.write(abs_path, rel_path)
                                
                    self.log_signal.emit(f"[ÉXITO] Actualización unificada empaquetada en:\n -> {zip_filename.name}")
                    if self.copiar_a_web:
                        copiar_y_registrar_actualizacion_web(self.base_dir, "multimodulo", zip_filename, self.log_signal, self.descripcion, num_items=len(self.modulos))
                    else:
                        self.log_signal.emit(f"[WEB OMITIDO] No se copió a la web (guardado únicamente en UPDATES/{zip_filename.name}).")
            
            # Limpieza final
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
                
            self.progress_signal.emit(100, "¡Finalizado!")
            self.finished_signal.emit(True, f"Actualizaciones guardadas en:\n{updates_out}")

    class CompilerGUIDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.base_dir = Path(__file__).resolve().parent
            self.setWindowTitle("Compilador de Actualizaciones - Multitool")
            self.setMinimumSize(850, 580)
            self.setStyleSheet("""
                QDialog {
                    background-color: #121218;
                    color: #E2E2E2;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QLabel {
                    color: #E2E2E2;
                }
                QPushButton {
                    background-color: #6366F1;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #818CF8;
                }
                QPushButton:disabled {
                    background-color: #4B5563;
                    color: #9CA3AF;
                }
                QPlainTextEdit {
                    background-color: #0B0B0F;
                    color: #34D399;
                    border: 1px solid #2D2D3D;
                    border-radius: 5px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 11px;
                }
                QScrollArea {
                    border: 1px solid #2D2D3D;
                    background-color: #1E1E2E;
                    border-radius: 5px;
                }
                QCheckBox {
                    color: #AAB0B8;
                    font-weight: bold;
                    padding: 4px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 1px solid #4B5563;
                    background-color: #121218;
                }
                QCheckBox::indicator:checked {
                    background-color: #6366F1;
                    border: 1px solid #818CF8;
                }
                QProgressBar {
                    border: 1px solid #2D2D3D;
                    background-color: #1E1E2E;
                    border-radius: 4px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background-color: #6366F1;
                    border-radius: 3px;
                }
            """)
            self.init_ui()

        def init_ui(self):
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(15, 15, 15, 15)
            main_layout.setSpacing(12)

            # Título principal
            lbl_title = QLabel("🛠️ Compilador de Actualizaciones y Sistema")
            lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #6366F1;")
            main_layout.addWidget(lbl_title)

            lbl_desc = QLabel("Seleccione el sistema y/o los módulos para compilar y empaquetar en archivos ZIP de actualización:")
            lbl_desc.setStyleSheet("color: #AAB0B8; font-size: 12px;")
            main_layout.addWidget(lbl_desc)

            # Contenedor central dividido
            content_layout = QHBoxLayout()
            content_layout.setSpacing(12)

            # Panel Izquierdo: Elementos Disponibles
            left_layout = QVBoxLayout()
            left_layout.addWidget(QLabel("Elementos para Actualizar:"))

            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            scroll_widget = QWidget()
            scroll_widget.setStyleSheet("background-color: #1E1E2E;")
            self.scroll_layout = QVBoxLayout(scroll_widget)
            self.scroll_layout.setContentsMargins(10, 10, 10, 10)
            self.scroll_layout.setSpacing(8)

            # Checkbox especial de Sistema (Core)
            self.cb_sistema = QCheckBox("✨ Sistema (Núcleo de Multitool)")
            self.cb_sistema.setStyleSheet("color: #6366F1; font-weight: bold; font-size: 13px; padding-bottom: 3px;")
            self.scroll_layout.addWidget(self.cb_sistema)

            # Checkbox especial de Sistema de Autenticación
            self.cb_autenticacion = QCheckBox("🔑 Sistema de Autenticación (OAuth & Cuentas)")
            self.cb_autenticacion.setStyleSheet("color: #10B981; font-weight: bold; font-size: 13px; padding-bottom: 5px;")
            self.scroll_layout.addWidget(self.cb_autenticacion)

            # Separador visual
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            line.setStyleSheet("background-color: #2D2D3D; max-height: 1px; margin-bottom: 5px;")
            self.scroll_layout.addWidget(line)

            # Rellenar lista de módulos
            self.checkboxes = {}
            modulos_dir = self.base_dir / "vistas" / "modulos"
            if modulos_dir.exists():
                for item in modulos_dir.iterdir():
                    if item.is_dir() and not item.name.startswith("__"):
                        config_path = item / "config.json"
                        if config_path.exists():
                            cb = QCheckBox(item.name.capitalize())
                            self.checkboxes[item.name] = cb
                            self.scroll_layout.addWidget(cb)

            self.scroll_layout.addStretch()
            self.scroll_area.setWidget(scroll_widget)
            left_layout.addWidget(self.scroll_area)

            # Botones de selección rápida
            sel_btn_layout = QHBoxLayout()
            self.btn_select_all = QPushButton("Todos")
            self.btn_select_all.clicked.connect(self.select_all)
            self.btn_select_all.setStyleSheet("background-color: #2D2D3D; color: #E2E2E2;")
            
            self.btn_deselect_all = QPushButton("Ninguno")
            self.btn_deselect_all.clicked.connect(self.deselect_all)
            self.btn_deselect_all.setStyleSheet("background-color: #2D2D3D; color: #E2E2E2;")
            
            sel_btn_layout.addWidget(self.btn_select_all)
            sel_btn_layout.addWidget(self.btn_deselect_all)
            left_layout.addLayout(sel_btn_layout)

            content_layout.addLayout(left_layout, 1)

            # Panel Derecho: Terminal de compilación
            right_layout = QVBoxLayout()
            right_layout.addWidget(QLabel("Terminal de Compilación (Nuitka Logs):"))
            
            self.console = QPlainTextEdit()
            self.console.setReadOnly(True)
            right_layout.addWidget(self.console)

            content_layout.addLayout(right_layout, 2)
            main_layout.addLayout(content_layout)

            # Fila de Opciones
            options_layout = QVBoxLayout()
            options_layout.setSpacing(6)
            
            self.cb_unificar = QCheckBox("📦 Unificar módulos seleccionados en un archivo único de actualización (.mtu)")
            self.cb_unificar.setChecked(True)
            self.cb_unificar.setStyleSheet("color: #AAB0B8; font-size: 11px; font-weight: normal;")
            options_layout.addWidget(self.cb_unificar)

            self.cb_copiar_web = QCheckBox("🌐 Registrar y copiar automáticamente la actualización a la página web (pagina/public/ y data.json)")
            self.cb_copiar_web.setChecked(True)
            self.cb_copiar_web.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: bold;")
            options_layout.addWidget(self.cb_copiar_web)

            main_layout.addLayout(options_layout)

            # Nombre personalizado del archivo
            name_layout = QHBoxLayout()
            name_layout.setSpacing(8)
            lbl_name = QLabel("📝 Nombre del archivo (opcional):")
            lbl_name.setStyleSheet("color: #AAB0B8; font-size: 12px; font-weight: bold;")
            self.txt_custom_name = QLineEdit()
            self.txt_custom_name.setPlaceholderText("Ej: mi_parche (se guardará como .mtu, incremental por defecto)")
            self.txt_custom_name.setStyleSheet("""
                QLineEdit {
                    background-color: #0B0B0F;
                    color: #E2E2E2;
                    border: 1px solid #2D2D3D;
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-size: 12px;
                }
                QLineEdit:focus {
                    border: 1px solid #6366F1;
                }
            """)
            name_layout.addWidget(lbl_name)
            name_layout.addWidget(self.txt_custom_name)
            main_layout.addLayout(name_layout)

            # Descripción / Novedades de la actualización
            desc_input_layout = QVBoxLayout()
            desc_input_layout.setSpacing(4)
            lbl_desc_input = QLabel("📋 Descripción / Novedades de la actualización (se guardará en .txt, .json y web):")
            lbl_desc_input.setStyleSheet("color: #AAB0B8; font-size: 12px; font-weight: bold;")
            self.txt_descripcion = QPlainTextEdit()
            self.txt_descripcion.setPlaceholderText("Escriba los detalles o notas del parche (ej: Corrección de errores en traductor y nuevas funciones)...")
            self.txt_descripcion.setMaximumHeight(65)
            self.txt_descripcion.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #0B0B0F;
                    color: #E2E2E2;
                    border: 1px solid #2D2D3D;
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 11px;
                }
                QPlainTextEdit:focus {
                    border: 1px solid #6366F1;
                }
            """)
            desc_input_layout.addWidget(lbl_desc_input)
            desc_input_layout.addWidget(self.txt_descripcion)
            main_layout.addLayout(desc_input_layout)

            # Panel Inferior: Progreso y Botón de Inicio
            bottom_layout = QHBoxLayout()
            bottom_layout.setSpacing(12)

            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(True)
            bottom_layout.addWidget(self.progress_bar, 2)

            self.btn_compile = QPushButton("⚡ Iniciar Compilación")
            self.btn_compile.clicked.connect(self.start_compilation)
            self.btn_compile.setMinimumHeight(38)
            bottom_layout.addWidget(self.btn_compile, 1)

            main_layout.addLayout(bottom_layout)

        def select_all(self):
            for cb in self.checkboxes.values():
                cb.setChecked(True)

        def deselect_all(self):
            for cb in self.checkboxes.values():
                cb.setChecked(False)

        def start_compilation(self):
            modulos_seleccionados = [name for name, cb in self.checkboxes.items() if cb.isChecked()]
            compilar_sistema = self.cb_sistema.isChecked()
            compilar_autenticacion = self.cb_autenticacion.isChecked()
            
            if not modulos_seleccionados and not compilar_sistema and not compilar_autenticacion:
                QMessageBox.warning(self, "Advertencia", "Por favor, seleccione al menos un módulo, el Sistema o el Sistema de Autenticación.")
                return

            self.btn_compile.setEnabled(False)
            self.btn_select_all.setEnabled(False)
            self.btn_deselect_all.setEnabled(False)
            self.cb_sistema.setEnabled(False)
            self.cb_autenticacion.setEnabled(False)
            self.cb_unificar.setEnabled(False)
            self.cb_copiar_web.setEnabled(False)
            self.txt_custom_name.setEnabled(False)
            self.txt_descripcion.setEnabled(False)
            for cb in self.checkboxes.values():
                cb.setEnabled(False)

            self.console.clear()
            self.progress_bar.setValue(0)

            # Iniciar hilo de compilación
            self.worker = CompileWorker(
                self.base_dir,
                modulos_seleccionados,
                compilar_sistema,
                compilar_autenticacion,
                self.cb_unificar.isChecked(),
                self.txt_custom_name.text(),
                self.txt_descripcion.toPlainText(),
                self.cb_copiar_web.isChecked()
            )
            self.worker.log_signal.connect(self.append_log)
            self.worker.progress_signal.connect(self.update_progress)
            self.worker.finished_signal.connect(self.compilation_finished)
            self.worker.start()

        def append_log(self, text):
            if text.startswith('\r'):
                cursor = self.console.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                cursor.removeSelectedText()
                cursor.insertText(text[1:])
                self.console.setTextCursor(cursor)
            else:
                self.console.appendPlainText(text)
            self.console.ensureCursorVisible()

        def update_progress(self, val, msg):
            self.progress_bar.setValue(val)
            self.progress_bar.setFormat(f"{msg} ({val}%)")

        def compilation_finished(self, success, message):
            self.btn_compile.setEnabled(True)
            self.btn_select_all.setEnabled(True)
            self.btn_deselect_all.setEnabled(True)
            self.cb_sistema.setEnabled(True)
            self.cb_autenticacion.setEnabled(True)
            self.cb_unificar.setEnabled(True)
            self.cb_copiar_web.setEnabled(True)
            self.txt_custom_name.setEnabled(True)
            self.txt_descripcion.setEnabled(True)
            for cb in self.checkboxes.values():
                cb.setEnabled(True)

            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("Finalizado")

            if success:
                QMessageBox.information(self, "Compilación Exitosa", message)
            else:
                QMessageBox.critical(self, "Error de Compilación", message)

def run_gui():
    if not HAS_PYQT:
        print("[!] Error: No se puede abrir la interfaz gráfica porque PyQt6 no está instalado.")
        sys.exit(1)
    app = QApplication.instance()
    standalone = False
    if not app:
        app = QApplication(sys.argv)
        standalone = True
    
    dialog = CompilerGUIDialog()
    dialog.exec()
    
    if standalone:
        sys.exit(0)

def main():
    base_dir = Path(__file__).resolve().parent
    
    # Si no hay argumentos o se pide explícitamente el GUI
    if len(sys.argv) < 2 or sys.argv[1] == "--gui":
        if HAS_PYQT:
            run_gui()
        else:
            print("\n[!] PyQt6 no está instalado en este entorno.")
            print("[Uso CLI] python compilar_actualizacion.py <modulo1> [modulo2] ... [--sistema] [--autenticacion] [--unificar]")
        return

    # Parsear CLI
    args = sys.argv[1:]
    compilar_sistema = False
    compilar_autenticacion = False
    unificar_modulos = False
    nombre_personalizado = ""
    descripcion_personalizada = ""
    modulos_solicitados = []
    
    copiar_a_web = True
    
    skip = False
    for i, arg in enumerate(args):
        if skip:
            skip = False
            continue
        if arg in ("--name", "-n"):
            if i + 1 < len(args):
                nombre_personalizado = args[i + 1].strip()
                skip = True
            continue
        elif arg in ("--desc", "-d", "--descripcion"):
            if i + 1 < len(args):
                descripcion_personalizada = args[i + 1].strip()
                skip = True
            continue
        elif arg == "--no-web":
            copiar_a_web = False
        elif arg == "--copiar-web":
            copiar_a_web = True
        elif arg == "--sistema":
            compilar_sistema = True
        elif arg == "--autenticacion":
            compilar_autenticacion = True
        elif arg == "--unificar":
            unificar_modulos = True
        else:
            modulos_solicitados.append(arg)
            
    updates_out = base_dir / "DISTRIBUCION" / "UPDATES"
    num_outputs = (1 if compilar_sistema else 0) + (1 if compilar_autenticacion else 0) + (1 if (modulos_solicitados and unificar_modulos) else len(modulos_solicitados))
    updates_out.mkdir(parents=True, exist_ok=True)
    sys_os = platform.system()
    ext_bin = ".pyd" if sys_os == "Windows" else ".so"
    
    # Lógica CLI de compilación de Sistema
    if compilar_sistema:
        banner("COMPILANDO ACTUALIZACIÓN DE SISTEMA (CORE)")
        # Lógica abreviada para consola
        temp_sys_dir = base_dir / "updates_temp" / "sistema_build"
        if temp_sys_dir.exists():
            shutil.rmtree(temp_sys_dir, ignore_errors=True)
        temp_sys_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            sys.executable, "-m", "nuitka",
            "--standalone",
            "--show-progress",
            f"--output-dir={temp_sys_dir}",
            "--output-filename=Multitool.exe" if sys_os == "Windows" else "Multitool",
            "--jobs=8",
            "--enable-plugin=pyqt6",
            "--follow-imports",
            "--lto=no",
            "--nofollow-import-to=fitz",
            "--nofollow-import-to=pymupdf",
            "--nofollow-import-to=sympy",
            "--nofollow-import-to=torch",
            "--nofollow-import-to=ctranslate2",
            "--nofollow-import-to=argostranslate",
            "--nofollow-import-to=compilar_actualizacion",
            "--include-module=ssl",
            "--include-package=urllib",
            "--include-package=vistas",
            "--include-package=controlador",
            "--include-data-dir=vistas=vistas",
            "--include-data-dir=controlador=controlador",
            str(base_dir / "main.py")
        ]
        if sys_os == "Windows":
            cmd.insert(4, "--windows-console-mode=disable")
            
        try:
            subprocess.run(cmd, check=True)
            dist_dir = temp_sys_dir / "main.dist"
            if dist_dir.exists():
                # Copiar fitz/pymupdf
                import site
                site_packages_dirs = site.getsitepackages()
                for pkg in ["fitz", "pymupdf"]:
                    pkg_source = None
                    for sp_dir in site_packages_dirs:
                        candidate = Path(sp_dir) / pkg
                        if candidate.exists():
                            pkg_source = candidate
                            break
                    if pkg_source:
                        shutil.copytree(pkg_source, dist_dir / pkg, dirs_exist_ok=True)

                zip_filename = obtener_ruta_destino(updates_out, "update_sistema", nombre_personalizado, num_outputs, "sistema")
                with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    agregar_core_al_zip(zipf, dist_dir, descripcion_personalizada)

                verificar_core_zip(zip_filename)
                print(f"[ÉXITO] Sistema compilado y empaquetado en: {zip_filename}")
                if copiar_a_web:
                    copiar_y_registrar_actualizacion_web(base_dir, "core", zip_filename, descripcion=descripcion_personalizada)
        except Exception as e:
            print(f"[!] Error compilando sistema CLI: {e}")

    # Lógica CLI de compilación de Sistema de Autenticación
    if compilar_autenticacion:
        banner("COMPILANDO ACTUALIZACIÓN DE SISTEMA DE AUTENTICACIÓN (OAUTH & CUENTAS)")
        try:
            temp_auth_dir = base_dir / "updates_temp" / "autenticacion_build"
            if temp_auth_dir.exists():
                shutil.rmtree(temp_auth_dir, ignore_errors=True)
            temp_auth_dir.mkdir(parents=True, exist_ok=True)
            
            ctrl_auth_src = base_dir / "controlador" / "auth"
            if ctrl_auth_src.exists():
                shutil.copytree(ctrl_auth_src, temp_auth_dir / "controlador" / "auth", dirs_exist_ok=True)
                
            cuenta_src = base_dir / "vistas" / "modulos" / "cuenta"
            if cuenta_src.exists():
                shutil.copytree(cuenta_src, temp_auth_dir / "vistas" / "modulos" / "cuenta", dirs_exist_ok=True)
                
            oauth_src = base_dir / "vistas" / "modulos" / "navegador" / "utils" / "oauth_manager.py"
            if oauth_src.exists():
                dest = temp_auth_dir / "vistas" / "modulos" / "navegador" / "utils" / "oauth_manager.py"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(oauth_src, dest)
                
            zip_filename = obtener_ruta_destino(updates_out, "update_autenticacion", nombre_personalizado, num_outputs, "autenticacion")
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                manifest = generar_manifest_json("auth", "autenticacion", descripcion_personalizada)
                zipf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
                for root, dirs, files in os.walk(temp_auth_dir):
                    for file in files:
                        abs_path = Path(root) / file
                        rel_path = abs_path.relative_to(temp_auth_dir)
                        zipf.write(abs_path, rel_path)
            print(f"[ÉXITO] Sistema de Autenticación empaquetada en: {zip_filename}")
            if copiar_a_web:
                copiar_y_registrar_actualizacion_web(base_dir, "oaut", zip_filename, descripcion=descripcion_personalizada)
        except Exception as e:
            print(f"[!] Error empaquetando sistema de autenticación CLI: {e}")

    # Lógica CLI de compilación de Módulos
    if modulos_solicitados:
        unified_temp_dir = base_dir / "updates_temp" / "unified"
        if unificar_modulos:
            if unified_temp_dir.exists():
                shutil.rmtree(unified_temp_dir, ignore_errors=True)
            unified_temp_dir.mkdir(parents=True, exist_ok=True)
            
        for mod_name in modulos_solicitados:
            mod_name = mod_name.lower().strip()
            mod_dir = base_dir / "vistas" / "modulos" / mod_name
            if not mod_dir.exists():
                print(f"[!] El módulo '{mod_name}' no existe.")
                continue
                
            banner(f"COMPILANDO MÓDULO: {mod_name.upper()}")
            
            config_path = mod_dir / "config.json"
            main_file = "main.py"
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        main_file = cfg.get("file_name", "main.py")
                except: pass
            
            target_py = mod_dir / main_file
            if not target_py.exists():
                alternative = mod_dir / f"{mod_name}.py"
                if alternative.exists():
                    target_py = alternative
                else:
                    print(f"[!] No se encontró el script de entrada {target_py}")
                    continue

            temp_update_dir = base_dir / "updates_temp" / mod_name
            if temp_update_dir.exists():
                shutil.rmtree(temp_update_dir, ignore_errors=True)
            temp_update_dir.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                sys.executable, "-m", "nuitka",
                "--module",
                "--show-progress",
                f"--output-dir={base_dir / 'updates_temp'}",
                "--jobs=8",
                "--lto=no",
                str(target_py)
            ]
            
            try:
                subprocess.run(cmd, check=True)
                file_base_name = target_py.stem
                compiled_file = None
                for item in (base_dir / 'updates_temp').iterdir():
                    if item.is_file() and item.name.startswith(file_base_name) and item.name.endswith(ext_bin):
                        compiled_file = item
                        break
                if compiled_file:
                    shutil.move(str(compiled_file), str(temp_update_dir / f"{file_base_name}{ext_bin}"))
                    
                    # Copiar recursos
                    for root, dirs, files in os.walk(mod_dir):
                        rel_path = Path(root).relative_to(mod_dir)
                        if "__pycache__" in root or "browser_data" in root:
                            continue
                        dest_subdir = temp_update_dir / rel_path
                        dest_subdir.mkdir(parents=True, exist_ok=True)

                        mod_ver = obtener_o_actualizar_version_modulo(base_dir, mod_name, descripcion_personalizada)
                        if unificar_modulos:
                            shutil.copytree(temp_update_dir, unified_temp_dir / "vistas" / "modulos" / mod_name, dirs_exist_ok=True)
                        else:
                            # Zip individual (.mtu)
                            zip_filename = obtener_ruta_destino(updates_out, f"update_{mod_name}", nombre_personalizado, num_outputs, mod_name)
                            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                manifest = generar_manifest_json("module", mod_name, descripcion_personalizada)
                                manifest["version"] = mod_ver
                                zipf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
                                for root, dirs, files in os.walk(temp_update_dir):
                                    for file in files:
                                        abs_path = Path(root) / file
                                        rel_path = abs_path.relative_to(temp_update_dir)
                                        zipf.write(abs_path, Path("vistas") / "modulos" / mod_name / rel_path)
                            print(f"[ÉXITO] Actualización empaquetada: {zip_filename.name} (v{mod_ver})")
                            if copiar_a_web:
                                copiar_y_registrar_actualizacion_web(base_dir, "modulo", zip_filename, descripcion=descripcion_personalizada, mod_name=mod_name, num_items=1, mod_version=mod_ver)
            except Exception as e:
                print(f"[!] Error compilando modulo {mod_name}: {e}")
                
        if unificar_modulos and unified_temp_dir.exists():
            zip_filename = obtener_ruta_destino(updates_out, "update_multimodulo", nombre_personalizado, num_outputs, "multimodulo")
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                manifest = generar_manifest_json("multimodulo", "varios_modulos", descripcion_personalizada)
                zipf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
                for root, dirs, files in os.walk(unified_temp_dir):
                    for file in files:
                        abs_path = Path(root) / file
                        rel_path = abs_path.relative_to(unified_temp_dir)
                        zipf.write(abs_path, rel_path)
            print(f"[ÉXITO] Actualización unificada empaquetada: {zip_filename.name}")
            if copiar_a_web:
                copiar_y_registrar_actualizacion_web(base_dir, "multimodulo", zip_filename, descripcion=descripcion_personalizada, num_items=len(modulos_solicitados))

    # Limpiar
    temp_dir = base_dir / "updates_temp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    print("\nProceso de generación de actualizaciones finalizado.")

if __name__ == "__main__":
    main()
