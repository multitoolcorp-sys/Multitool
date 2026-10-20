import os
import sys
import time
import json
import shutil
import zipfile
import argparse
import subprocess
import datetime
from pathlib import Path

def log_msg(msg, is_error=False):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{'ERROR' if is_error else 'INFO'}] {msg}"
    print(formatted)
    try:
        log_file = Path(__file__).resolve().parent / "updater.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def esperar_cierre_proceso(pid, max_wait_sec=15):
    """Espera a que el proceso de Multitool.exe termine para liberar archivos."""
    if not pid or pid <= 0:
        return True
    
    log_msg(f"Esperando a que el proceso Multitool (PID {pid}) finalice...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait_sec:
        try:
            if sys.platform == "win32":
                cmd = f'tasklist /FI "PID eq {pid}"'
                out = subprocess.check_output(cmd, shell=True, text=True)
                if str(pid) not in out:
                    log_msg("El proceso principal ha finalizado correctamente.")
                    return True
            else:
                os.kill(pid, 0)
        except (OSError, subprocess.CalledProcessError):
            log_msg("Proceso finalizado libremente.")
            return True
        time.sleep(1)
        
    log_msg("El tiempo de espera expiró. Intentando forzar el cierre...", is_error=True)
    try:
        if sys.platform == "win32":
            subprocess.run(f"taskkill /F /PID {pid}", shell=True)
        else:
            os.kill(pid, 9)
    except Exception as e:
        log_msg(f"Error al forzar cierre de proceso: {e}", is_error=True)
    time.sleep(1)
    return True

def es_ruta_segura(base_dir: Path, target_path: Path) -> bool:
    """Evita ataques de Path Traversal (ej. ../../archivo.exe)."""
    try:
        resolved_base = base_dir.resolve()
        resolved_target = target_path.resolve()
        return str(resolved_target).startswith(str(resolved_base))
    except Exception:
        return False

def registrar_historial_actualizacion(base_dir: Path, registro: dict):
    """Guarda el log detallado de actualización en actualizaciones.json."""
    try:
        log_path = base_dir / "data" / "actualizaciones.json"
        if not log_path.parent.exists():
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
        historial = []
        if log_path.exists():
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    historial = json.load(f)
            except Exception:
                historial = []
                
        historial.append(registro)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(historial, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log_msg(f"No se pudo registrar historial en JSON: {e}", is_error=True)

def ejecutar_actualizacion(mtu_path: Path, app_dir: Path, pid: int = 0):
    log_msg(f"=== INICIANDO PROCESO DE ACTUALIZACIÓN EXTERNO ===")
    log_msg(f"Archivo .mtu: {mtu_path}")
    log_msg(f"Directorio App: {app_dir}")
    
    if not mtu_path.exists():
        log_msg(f"El archivo de actualización no existe: {mtu_path}", is_error=True)
        return False
        
    if not app_dir.exists():
        log_msg(f"El directorio de destino no existe: {app_dir}", is_error=True)
        return False

    # 1. Esperar cierre de Multitool
    esperar_cierre_proceso(pid)
    
    # Directorios de trabajo
    updates_dir = app_dir / "updates"
    temp_extract = updates_dir / "temp_extract"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = updates_dir / "backup" / f"backup_{timestamp}"
    
    if temp_extract.exists():
        shutil.rmtree(temp_extract, ignore_errors=True)
    temp_extract.mkdir(parents=True, exist_ok=True)
    
    manifest_data = {}
    archivos_respaldados = []
    
    try:
        # 2. Abrir y Validar ZIP en carpeta temporal
        log_msg("Abriendo paquete .mtu...")
        with zipfile.ZipFile(mtu_path, 'r') as zip_ref:
            lista_archivos = zip_ref.namelist()
            log_msg(f"Total de archivos en el paquete: {len(lista_archivos)}")
            
            # Extraer manifest si existe
            if "manifest.json" in lista_archivos:
                zip_ref.extract("manifest.json", temp_extract)
                with open(temp_extract / "manifest.json", "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                log_msg(f"Manifest detectado: Versión {manifest_data.get('version')} Tipo: {manifest_data.get('type')}")
            
            # Validar Path Traversal y extraer todo a temp_extract
            for member in zip_ref.infolist():
                target = temp_extract / member.filename
                if not es_ruta_segura(temp_extract, target):
                    raise ValueError(f"Intento de Path Traversal detectado en: {member.filename}")
                zip_ref.extract(member, temp_extract)
                
        log_msg("Validación previa y extracción a carpeta temporal completadas.")
        
        # 3. Crear Backup de archivos afectados antes de sobrescribir
        log_msg("Creando copia de seguridad (backup)...")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for root, dirs, files in os.walk(temp_extract):
            for file in files:
                if file == "manifest.json" or file == "descripcion.txt":
                    continue
                rel_path = Path(root).relative_to(temp_extract) / file
                existing_file = app_dir / rel_path
                
                if existing_file.exists():
                    dest_backup = backup_dir / rel_path
                    dest_backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(existing_file, dest_backup)
                    archivos_respaldados.append(rel_path)
                    
        log_msg(f"Backup creado exitosamente. Archivos respaldados: {len(archivos_respaldados)}")
        
        # 4. Copiar archivos actualizados a la instalación principal
        log_msg("Instalando actualización...")
        for root, dirs, files in os.walk(temp_extract):
            for file in files:
                if file == "manifest.json" or file == "descripcion.txt":
                    continue
                rel_path = Path(root).relative_to(temp_extract) / file
                src_file = Path(root) / file
                target_file = app_dir / rel_path
                
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, target_file)
                
        log_msg("¡Actualización aplicada en disco con éxito!")
        
        # 5. Registrar Historial Éxito
        registro_log = {
            "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "archivo": mtu_path.name,
            "tipo": manifest_data.get("type", "desconocido"),
            "version": manifest_data.get("version", "N/A"),
            "estado": "exito",
            "rollback": False,
            "archivos_afectados": [str(a) for a in archivos_respaldados[:10]]
        }
        registrar_historial_actualizacion(app_dir, registro_log)
        
        # Limpieza de temporales
        shutil.rmtree(temp_extract, ignore_errors=True)
        return True

    except Exception as e:
        log_msg(f"CRÍTICO: Error durante la instalación: {e}", is_error=True)
        log_msg("Iniciando ROLLBACK automático...", is_error=True)
        
        # Restaurar desde backup si existe
        if backup_dir.exists() and archivos_respaldados:
            try:
                for rel_path in archivos_respaldados:
                    b_file = backup_dir / rel_path
                    t_file = app_dir / rel_path
                    if b_file.exists():
                        shutil.copy2(b_file, t_file)
                log_msg("Rollback completado. La versión previa ha sido restaurada.")
            except Exception as re:
                log_msg(f"Falló la restauración del Rollback: {re}", is_error=True)
                
        registro_log = {
            "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "archivo": mtu_path.name,
            "tipo": manifest_data.get("type", "desconocido"),
            "version": manifest_data.get("version", "N/A"),
            "estado": "error",
            "error": str(e),
            "rollback": True
        }
        registrar_historial_actualizacion(app_dir, registro_log)
        shutil.rmtree(temp_extract, ignore_errors=True)
        return False

def reiniciar_multitool(app_dir: Path):
    """Reinicia la aplicación Multitool principal tras actualizar."""
    exe_path = app_dir / "Multitool.exe"
    py_path = app_dir / "main.py"
    
    log_msg("Reiniciando Multitool...")
    try:
        if exe_path.exists():
            subprocess.Popen([str(exe_path)], cwd=str(app_dir))
        elif py_path.exists():
            subprocess.Popen([sys.executable, str(py_path)], cwd=str(app_dir))
        else:
            log_msg("No se encontró ejecutable ni main.py para reiniciar.", is_error=True)
    except Exception as e:
        log_msg(f"Error al reiniciar Multitool: {e}", is_error=True)

def main():
    parser = argparse.ArgumentParser(description="Updater externo para Multitool Corp.")
    parser.add_argument("--mtu", required=True, help="Ruta al archivo .mtu")
    parser.add_argument("--app-dir", required=True, help="Ruta del directorio de la aplicación")
    parser.add_argument("--pid", type=int, default=0, help="PID del proceso Multitool a esperar")
    
    args = parser.parse_args()
    mtu_path = Path(args.mtu).resolve()
    app_dir = Path(args.app_dir).resolve()
    
    exito = ejecutar_actualizacion(mtu_path, app_dir, args.pid)
    
    if exito:
        reiniciar_multitool(app_dir)

if __name__ == "__main__":
    main()
