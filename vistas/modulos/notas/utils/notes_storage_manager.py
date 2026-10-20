"""
notes_storage_manager.py - Gestor de almacenamiento en disco para notas (Favoritas, Fijadas, Protegidas con PIN)
"""
import json
import hashlib
from pathlib import Path


class NotesStorageManager:
    def __init__(self, ruta_usuario):
        self.ruta_usuario = Path(ruta_usuario)
        self.ruta_notas = self.ruta_usuario / "notas"
        self.ruta_notas.mkdir(parents=True, exist_ok=True)

    def cargar_favoritas(self):
        ruta = self.ruta_usuario / "notas_favoritas.json"
        if ruta.exists():
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def guardar_favoritas(self, favoritas):
        ruta = self.ruta_usuario / "notas_favoritas.json"
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(favoritas, f)
        except Exception:
            pass

    def cargar_fijadas(self):
        ruta = self.ruta_usuario / "notas_fijadas.json"
        if ruta.exists():
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def guardar_fijadas(self, fijadas):
        ruta = self.ruta_usuario / "notas_fijadas.json"
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(fijadas, f)
        except Exception:
            pass

    def cargar_protegidas(self):
        ruta = self.ruta_usuario / "notas_protegidas.json"
        if ruta.exists():
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def guardar_protegidas(self, protegidas):
        ruta = self.ruta_usuario / "notas_protegidas.json"
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(protegidas, f, indent=4)
        except Exception:
            pass

    def desencriptar_hash_pin(self, pin):
        return hashlib.sha256(f"{pin.strip()}".encode('utf-8')).hexdigest()

    # --- HISTORIAL DE VERSIONES (SNAPSHOTS) ---
    def guardar_snapshot(self, nombre_nota, datos):
        """Guarda un snapshot histórico de la nota (máximo 8 snapshots por nota)"""
        try:
            import datetime
            import re
            snap_dir = self.ruta_notas / ".snapshots" / nombre_nota
            snap_dir.mkdir(parents=True, exist_ok=True)
            
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            snap_file = snap_dir / f"{ts}.json"
            
            # Normalizar datos a dict si vino como string html
            if isinstance(datos, str):
                datos_dict = {"html": datos}
                html = datos
            elif isinstance(datos, dict):
                datos_dict = datos
                html = datos.get("html", "")
            else:
                datos_dict = {"html": str(datos)}
                html = str(datos)

            plain = re.sub(r'<[^>]+>', ' ', html).strip()[:100]
            
            payload = {
                "timestamp": ts,
                "preview": plain,
                "datos": datos_dict
            }
            with open(snap_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                
            # Limitar a los 8 más recientes
            archivos = sorted(snap_dir.glob("*.json"))
            if len(archivos) > 8:
                for viejo in archivos[:-8]:
                    try: viejo.unlink()
                    except Exception: pass
        except Exception as e:
            print(f"Error guardando snapshot: {e}")

    def listar_snapshots(self, nombre_nota):
        """Retorna lista de snapshots disponibles ordenados de más reciente a más antiguo"""
        snap_dir = self.ruta_notas / ".snapshots" / nombre_nota
        if not snap_dir.exists():
            return []
        res = []
        for f in sorted(snap_dir.glob("*.json"), reverse=True):
            try:
                with open(f, "r", encoding="utf-8") as s:
                    data = json.load(s)
                    res.append({
                        "file": f.name,
                        "timestamp": data.get("timestamp", f.stem),
                        "preview": data.get("preview", ""),
                        "path": str(f)
                    })
            except Exception:
                continue
        return res

    def restaurar_snapshot(self, nombre_nota, snapshot_ref):
        """Lee y retorna los datos del snapshot seleccionado"""
        filename = snapshot_ref.get("file", snapshot_ref) if isinstance(snapshot_ref, dict) else str(snapshot_ref)
        if not filename.endswith(".json") and not filename.endswith(".txt"):
            filename = f"{filename}.json"
        snap_file = self.ruta_notas / ".snapshots" / nombre_nota / filename
        if snap_file.exists():
            with open(snap_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                d = data.get("datos", {})
                if isinstance(d, dict):
                    return d.get("html", "")
                return str(d)
        return None

    # --- GESTIÓN DE ETIQUETAS (TAGS) ---
    def cargar_tags(self):
        ruta = self.ruta_usuario / "notas_tags.json"
        if ruta.exists():
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def guardar_tags(self, tags_map_o_nota, tags_lista=None):
        ruta = self.ruta_usuario / "notas_tags.json"
        try:
            if tags_lista is not None:
                tags_map = self.cargar_tags()
                tags_map[str(tags_map_o_nota)] = list(tags_lista)
            elif isinstance(tags_map_o_nota, dict):
                tags_map = tags_map_o_nota
            else:
                tags_map = {}
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(tags_map, f, indent=4)
        except Exception:
            pass

    def obtener_todos_los_tags(self):
        """Retorna la lista única de todos los tags usados en el sistema"""
        tags_map = self.cargar_tags()
        todos = set()
        for tlist in tags_map.values():
            if isinstance(tlist, list):
                for t in tlist:
                    todos.add(t.strip())
        return sorted(list(todos))

    # --- PLANTILLAS PERSONALIZADAS DE USUARIO ---
    def cargar_plantillas_usuario(self):
        ruta = self.ruta_usuario / "plantillas_usuario.json"
        if ruta.exists():
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def guardar_plantilla_usuario(self, titulo_o_dict, descripcion="", html=""):
        import datetime
        import uuid
        ruta = self.ruta_usuario / "plantillas_usuario.json"
        plantillas = self.cargar_plantillas_usuario()
        
        if isinstance(titulo_o_dict, dict):
            p = titulo_o_dict
        else:
            p = {
                "id": str(uuid.uuid4())[:8],
                "titulo": str(titulo_o_dict),
                "descripcion": str(descripcion),
                "categoria": "Personalizada",
                "html": str(html),
                "personalizada": True,
                "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        
        # Reemplazar si mismo id o agregar
        plantillas = [item for item in plantillas if item.get("id") != p.get("id")]
        plantillas.append(p)
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(plantillas, f, indent=4)
            return True
        except Exception:
            return False

    def eliminar_plantilla_usuario(self, plantilla_id):
        ruta = self.ruta_usuario / "plantillas_usuario.json"
        plantillas = self.cargar_plantillas_usuario()
        nuevas = [p for p in plantillas if p.get("id") != plantilla_id]
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(nuevas, f, indent=4)
            return True
        except Exception:
            return False


