import os
import shutil
import json
from datetime import datetime
from pathlib import Path

class TrashManager:
    """Gestor de Papelera propio con indexación local"""
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.trash_dir = self.base_path / ".papelera"
        self.index_file = self.trash_dir / "trash_meta.json"
        
        if not self.trash_dir.exists():
            self.trash_dir.mkdir(parents=True)
        
        if not self.index_file.exists():
            self._save_index({})

    def move_to_trash(self, item_path):
        """Mueve un elemento a la papelera con metadatos de origen"""
        item_path = Path(item_path)
        if not item_path.exists(): return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trash_name = f"{timestamp}_{item_path.name}"
        trash_path = self.trash_dir / trash_name
        
        try:
            shutil.move(str(item_path), str(trash_path))
            
            # Guardar metadatos
            index = self._load_index()
            index[trash_name] = {
                "original_path": str(item_path.absolute()),
                "deleted_at": timestamp,
                "name": item_path.name
            }
            self._save_index(index)
            return True
        except Exception as e:
            print(f"Error Papelera: {e}")
            return False

    def restore_item(self, trash_name):
        index = self._load_index()
        if trash_name not in index: return False
        
        meta = index[trash_name]
        src = self.trash_dir / trash_name
        dest = Path(meta["original_path"])
        
        if not src.exists():
            del index[trash_name]
            self._save_index(index)
            return False

        if not dest.parent.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            
        try:
            if dest.exists():
                # Si el archivo destino ya existe, renombrar con sufijo (Restaurado)
                dest = dest.parent / f"{dest.stem} (Restaurado){dest.suffix}"
            shutil.move(str(src), str(dest))
            del index[trash_name]
            self._save_index(index)
            return True
        except Exception as e:
            print(f"Error restaurando elemento: {e}")
            return False

    def delete_forever(self, trash_name):
        """Elimina permanentemente un elemento de la papelera"""
        index = self._load_index()
        src = self.trash_dir / trash_name
        try:
            if src.exists():
                if src.is_dir():
                    shutil.rmtree(str(src), ignore_errors=True)
                else:
                    src.unlink()
            if trash_name in index:
                del index[trash_name]
                self._save_index(index)
            return True
        except Exception as e:
            print(f"Error eliminando de la papelera: {e}")
            return False

    def empty_trash(self):
        """Vacía todos los elementos de la papelera"""
        try:
            for item in self.trash_dir.iterdir():
                if item.name == "trash_meta.json":
                    continue
                if item.is_dir():
                    shutil.rmtree(str(item), ignore_errors=True)
                else:
                    item.unlink()
            self._save_index({})
            return True
        except Exception as e:
            print(f"Error vaciando papelera: {e}")
            return False

    def list_trash(self):
        index = self._load_index()
        return [{"trash_id": k, **v} for k, v in index.items()]

    def _load_index(self):
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}

    def _save_index(self, data):
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
