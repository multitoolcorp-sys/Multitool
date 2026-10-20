import os
import shutil
import datetime
from pathlib import Path
from .trash_manager import TrashManager

class FileManager:
    """Gestor de lógica de archivos con soporte para papelera indexada y archivos comprimidos"""
    def __init__(self, ruta_usuario):
        self.ruta_usuario = Path(ruta_usuario)
        self.ruta_actual = Path.home()  # Empezar en el directorio home del usuario real
        self.portapapeles = None
        self.accion_portapapeles = None
        
        # Inicializar papelera propia en la carpeta de usuario
        self.trash_manager = TrashManager(self.ruta_usuario)

        # Estado de archivos comprimidos
        self.is_inside_archive = False
        self.archive_path = None
        self.archive_internal_dir = ""
        self.archive_type = None
        self.archive_metadata = {}
        
        # Carpeta temporal para previsualización de archivos comprimidos
        self.temp_dir = self.ruta_usuario / ".temp_preview"
        if not self.temp_dir.exists():
            self.temp_dir.mkdir(parents=True, exist_ok=True)

    def limpiar_temporales(self):
        if self.temp_dir.exists():
            shutil.rmtree(str(self.temp_dir), ignore_errors=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def obtener_elementos(self):
        if self.is_inside_archive:
            return self._obtener_elementos_archivo()

        try:
            elementos = list(self.ruta_actual.iterdir())
            carpetas_data, archivos_data = [], []
            
            for item in elementos:
                if item.name.startswith(".papelera"): continue # Ocultar la propia papelera
                try:
                    stats = item.stat()
                    fecha_mod = datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M")
                    
                    data = {
                        "name": item.name,
                        "path": str(item),
                        "date": fecha_mod,
                        "type": "Carpeta" if item.is_dir() else self._get_file_type(item.suffix),
                    }
                    
                    if item.is_dir():
                        data["size_raw"], data["size"] = -1, "--"
                        carpetas_data.append(data)
                    else:
                        data["size_raw"] = stats.st_size
                        data["size"] = self._format_bytes(stats.st_size)
                        archivos_data.append(data)
                except: continue
                    
            carpetas_data.sort(key=lambda x: x["name"].lower())
            archivos_data.sort(key=lambda x: x["name"].lower())
            return carpetas_data, archivos_data
        except: return [], []

    def _obtener_elementos_archivo(self):
        carpetas_data, archivos_data = [], []
        d = self.archive_internal_dir
        subdirs = set()
        files = []
        
        for path_in_archive, meta in self.archive_metadata.items():
            # Limpiar barras iniciales por si acaso para comparación
            clean_path = path_in_archive.lstrip('/')
            
            if clean_path.startswith(d) and clean_path != d:
                rel = clean_path[len(d):]
                parts = rel.split('/')
                
                is_dir_entry = False
                if len(parts) > 1:
                    is_dir_entry = True
                    name = parts[0]
                elif rel.endswith('/'):
                    is_dir_entry = True
                    name = parts[0]
                else:
                    name = parts[0]
                
                if not name:
                    continue
                    
                if is_dir_entry:
                    subdirs.add(name)
                else:
                    files.append({
                        "name": name,
                        "path": str(self.archive_path),
                        "date": meta.get("date", "--"),
                        "type": self._get_file_type(Path(name).suffix),
                        "size_raw": meta.get("size_raw", 0),
                        "size": self._format_bytes(meta.get("size_raw", 0))
                    })
                    
        unique_files = {}
        for f in files:
            unique_files[f["name"]] = f
            
        for sd in sorted(subdirs, key=str.lower):
            carpetas_data.append({
                "name": sd,
                "path": str(self.archive_path / d / sd),
                "date": "--",
                "type": "Carpeta",
                "size_raw": -1,
                "size": "--"
            })
            
        for name in sorted(unique_files.keys(), key=str.lower):
            archivos_data.append(unique_files[name])
            
        return carpetas_data, archivos_data

    def _get_file_type(self, suffix):
        suffix = suffix.lower()
        types = {
            '.txt': 'Texto', '.py': 'Python', '.js': 'JavaScript', 
            '.pdf': 'PDF', '.docx': 'Word', '.zip': 'Archivo ZIP', 
            '.rar': 'Archivo RAR', '.tar': 'Archivo TAR', '.gz': 'Archivo GZIP',
            '.tgz': 'Archivo TAR GZIP'
        }
        return types.get(suffix, f"Archivo {suffix[1:].upper()}" if suffix else "Archivo")

    def _format_bytes(self, b):
        for u in ['B', 'KB', 'MB', 'GB']:
            if b < 1024: return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} TB"

    def subir_nivel(self):
        if self.is_inside_archive:
            if self.archive_internal_dir == "":
                # Salir del archivo y volver al directorio contenedor
                self.ruta_actual = self.archive_path.parent
                self.is_inside_archive = False
                self.archive_path = None
                self.archive_internal_dir = ""
                self.archive_type = None
                self.archive_metadata.clear()
                self.limpiar_temporales()
                return True
            else:
                # Subir un nivel en el path virtual interno
                parts = self.archive_internal_dir.rstrip('/').split('/')
                if len(parts) <= 1:
                    self.archive_internal_dir = ""
                else:
                    self.archive_internal_dir = "/".join(parts[:-1]) + "/"
                return True
        else:
            if self.ruta_actual.parent != self.ruta_actual:
                self.ruta_actual = self.ruta_actual.parent
                return True
            return False

    def ir_a_ruta(self, ruta):
        if self.is_inside_archive:
            return False # No se permite cambiar de ruta física directamente mientras se está dentro del archivo
        path = Path(ruta)
        if path.exists():
            self.ruta_actual = path
            return True
        return False

    def ir_inicio(self):
        if self.is_inside_archive:
            # Salir de la navegación de archivo comprimido e ir al inicio
            self.is_inside_archive = False
            self.archive_path = None
            self.archive_internal_dir = ""
            self.archive_type = None
            self.archive_metadata.clear()
            self.limpiar_temporales()
        self.ruta_actual = self.ruta_usuario

    def es_archivo_comprimido(self, ruta):
        path = Path(ruta)
        if not path.is_file():
            return False
        ext = path.suffix.lower()
        return ext in ['.zip', '.tar', '.gz', '.tgz', '.bz2', '.tbz2', '.xz', '.txz', '.rar']

    def entrar_a_archivo(self, ruta):
        ruta = Path(ruta)
        if not ruta.exists():
            return False
        ext = ruta.suffix.lower()
        if ext == '.zip':
            return self._cargar_zip(ruta)
        elif ext in ['.tar', '.gz', '.tgz', '.bz2', '.tbz2', '.xz', '.txz']:
            return self._cargar_tar(ruta)
        elif ext == '.rar':
            return self._cargar_rar(ruta)
        return False

    def _cargar_zip(self, path):
        import zipfile
        try:
            with zipfile.ZipFile(path, 'r') as z:
                self.archive_metadata.clear()
                for info in z.infolist():
                    dt = info.date_time
                    date_str = f"{dt[2]:02d}/{dt[1]:02d}/{dt[0]} {dt[3]:02d}:{dt[4]:02d}"
                    self.archive_metadata[info.filename] = {
                        "size_raw": info.file_size,
                        "date": date_str,
                        "is_dir": info.is_dir()
                    }
            self.archive_path = path
            self.archive_internal_dir = ""
            self.archive_type = 'zip'
            self.is_inside_archive = True
            self.limpiar_temporales()
            return True
        except Exception as e:
            print(f"Error cargando ZIP: {e}")
            return False

    def _cargar_tar(self, path):
        import tarfile
        try:
            with tarfile.open(path, 'r') as t:
                self.archive_metadata.clear()
                for member in t.getmembers():
                    date_str = datetime.datetime.fromtimestamp(member.mtime).strftime("%d/%m/%Y %H:%M")
                    self.archive_metadata[member.name] = {
                        "size_raw": member.size,
                        "date": date_str,
                        "is_dir": member.isdir()
                    }
            self.archive_path = path
            self.archive_internal_dir = ""
            self.archive_type = 'tar'
            self.is_inside_archive = True
            self.limpiar_temporales()
            return True
        except Exception as e:
            print(f"Error cargando TAR: {e}")
            return False

    def _cargar_rar(self, path):
        try:
            import rarfile
            # Comprobar la lectura del archivo RAR
            with rarfile.RarFile(path, 'r') as r:
                self.archive_metadata.clear()
                for info in r.infolist():
                    dt = info.date_time
                    if dt:
                        date_str = f"{dt[2]:02d}/{dt[1]:02d}/{dt[0]} {dt[3]:02d}:{dt[4]:02d}"
                    else:
                        date_str = "--"
                    self.archive_metadata[info.filename] = {
                        "size_raw": info.file_size,
                        "date": date_str,
                        "is_dir": info.isdir()
                    }
            self.archive_path = path
            self.archive_internal_dir = ""
            self.archive_type = 'rar'
            self.is_inside_archive = True
            self.limpiar_temporales()
            return True
        except ImportError:
            raise ImportError("El módulo 'rarfile' no está instalado. Ejecute 'pip install rarfile'.")
        except Exception as e:
            raise Exception(str(e))

    def es_directorio_interno(self, nombre):
        if not self.is_inside_archive:
            return False
        target = self.archive_internal_dir + nombre + "/"
        for path_in_archive in self.archive_metadata.keys():
            if path_in_archive.lstrip('/').startswith(target):
                return True
        return False

    def entrar_a_directorio_interno(self, nombre):
        if self.is_inside_archive:
            self.archive_internal_dir = self.archive_internal_dir + nombre + "/"

    def extraer_archivo_temporal(self, nombre):
        if not self.is_inside_archive:
            return None
            
        internal_path = self.archive_internal_dir + nombre
        dest_path = self.temp_dir / nombre
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if self.archive_type == 'zip':
                import zipfile
                with zipfile.ZipFile(self.archive_path, 'r') as z:
                    with z.open(internal_path) as source, open(dest_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                return dest_path
                
            elif self.archive_type == 'tar':
                import tarfile
                with tarfile.open(self.archive_path, 'r') as t:
                    member = t.getmember(internal_path)
                    source = t.extractfile(member)
                    if source:
                        with open(dest_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        source.close()
                return dest_path
                
            elif self.archive_type == 'rar':
                import rarfile
                with rarfile.RarFile(self.archive_path, 'r') as r:
                    with r.open(internal_path) as source, open(dest_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                return dest_path
        except Exception as e:
            print(f"Error al extraer archivo temporal {internal_path}: {e}")
            return None

    def crear_archivo(self, nombre):
        if self.is_inside_archive: return False
        ruta = self.ruta_actual / nombre
        if not ruta.exists():
            with open(ruta, "w") as f: pass
            return True
        return False

    def crear_carpeta(self, nombre):
        if self.is_inside_archive: return False
        ruta = self.ruta_actual / nombre
        if not ruta.exists():
            ruta.mkdir()
            return True
        return False

    def renombrar(self, nombre_viejo, nombre_nuevo):
        if self.is_inside_archive: return False, "Modo lectura activa en archivos comprimidos"
        origen = self.ruta_actual / nombre_viejo
        destino = self.ruta_actual / nombre_nuevo
        if origen.exists() and not destino.exists():
            try:
                origen.rename(destino)
                return True, "Éxito"
            except Exception as e:
                return False, str(e)
        return False, "El destino ya existe o el origen no."

    def eliminar(self, nombre):
        """Mueve a la papelera propia"""
        if self.is_inside_archive: return False
        return self.trash_manager.move_to_trash(self.ruta_actual / nombre)

    def preparar_operacion(self, nombres, accion):
        if self.is_inside_archive: return
        if isinstance(nombres, (str, Path)):
            nombres = [nombres]
        self.portapapeles = [self.ruta_actual / n if isinstance(n, str) else n for n in nombres]
        self.accion_portapapeles = accion

    def pegar(self):
        if self.is_inside_archive: return False, "Modo lectura"
        if not self.portapapeles: return False, "Vacío"
        
        exitos = 0
        errores = []
        for item in list(self.portapapeles):
            if not item.exists(): continue
            destino = self.ruta_actual / item.name
            try:
                if self.accion_portapapeles == "cortar":
                    shutil.move(str(item), str(destino))
                else:
                    if item.is_dir():
                        shutil.copytree(str(item), str(destino), dirs_exist_ok=True)
                    else:
                        shutil.copy2(str(item), str(destino))
                exitos += 1
            except Exception as e:
                errores.append(f"{item.name}: {e}")

        if self.accion_portapapeles == "cortar" and exitos > 0:
            self.portapapeles = []

        if exitos > 0:
            return True, f"{exitos} elemento(s) pegado(s) con éxito"
        return False, "; ".join(errores) if errores else "No se pudo pegar ningún elemento"

