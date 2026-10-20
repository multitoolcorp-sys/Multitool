"""
nosql_connections.py - Motores de conexión para bases de datos NoSQL:
MongoDB (pymongo), Redis (redis-py) y LocalDocumentConnection (JSON puro).
"""
import time
import json
import uuid
import shlex
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from .connection_base import BaseConnection


class MongoDBConnection(BaseConnection):
    """Conexión a base de datos NoSQL MongoDB (pymongo) con soporte para documentos JSON/BSON"""
    def __init__(self, uri: str = "", host: str = "localhost", port: int = 27017, database: str = "admin",
                 user: str = "", password: str = "", auth_source: str = "admin", name: str = ""):
        init_name = name or (f"MongoDB: {database}@{host}:{port}" if not uri else f"MongoDB: {uri[:30]}...")
        super().__init__(name=init_name, engine="mongodb", engine_type="document")
        self.uri = uri.strip()
        self.host = host.strip() or "localhost"
        self.port = int(port or 27017)
        self.database_name = database.strip() or "test"
        self.user = user.strip()
        self.password = password
        self.auth_source = auth_source.strip() or "admin"
        self._client = None

    def connect(self) -> bool:
        try:
            import pymongo
            if self.uri:
                self._client = pymongo.MongoClient(self.uri, serverSelectionTimeoutMS=4000)
            else:
                conn_kwargs = {
                    "host": self.host,
                    "port": self.port,
                    "serverSelectionTimeoutMS": 4000
                }
                if self.user:
                    conn_kwargs["username"] = self.user
                    conn_kwargs["password"] = self.password
                    conn_kwargs["authSource"] = self.auth_source
                self._client = pymongo.MongoClient(**conn_kwargs)

            # Verificar conexión real haciendo ping
            self._client.admin.command('ping')
            self.is_connected = True
            self.last_error = ""
            return True
        except ImportError:
            self.last_error = "Driver 'pymongo' no instalado. Descárgalo desde el gestor de conexiones."
            self.is_connected = False
            return False
        except Exception as e:
            self.last_error = str(e)
            self.is_connected = False
            return False

    def close(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self.is_connected = False

    def get_databases(self) -> List[str]:
        if not self.is_connected or not self._client:
            if not self.connect():
                return [self.database_name]
        try:
            return self._client.list_database_names()
        except Exception:
            return [self.database_name]

    def get_collections(self, database: str = "") -> List[Dict[str, Any]]:
        target_db = database or self.database_name
        if not self.is_connected or not self._client:
            if not self.connect():
                return []
        try:
            db = self._client[target_db]
            cols = db.list_collection_names()
            res = []
            for col_name in cols:
                count = 0
                try:
                    count = db[col_name].estimated_document_count()
                except Exception:
                    pass
                res.append({
                    "name": col_name,
                    "type": "collection",
                    "doc_count": count
                })
            return res
        except Exception as e:
            self.last_error = str(e)
            return []

    def get_collection_indexes(self, database: str, collection: str) -> List[Dict[str, Any]]:
        target_db = database or self.database_name
        if not self.is_connected or not self._client:
            return []
        try:
            db = self._client[target_db]
            info = db[collection].index_information()
            indexes = []
            for idx_name, idx_spec in info.items():
                indexes.append({
                    "name": idx_name,
                    "keys": idx_spec.get("key", []),
                    "unique": idx_spec.get("unique", False)
                })
            return indexes
        except Exception:
            return []

    def _serialize_doc(self, doc: Any) -> Any:
        """Convierte tipos BSON (ObjectId, datetime) en tipos serializables JSON"""
        if isinstance(doc, dict):
            return {k: self._serialize_doc(v) for k, v in doc.items()}
        elif isinstance(doc, list):
            return [self._serialize_doc(item) for item in doc]
        elif hasattr(doc, "__str__") and doc.__class__.__name__ == "ObjectId":
            return str(doc)
        elif isinstance(doc, (datetime, time.struct_time)):
            return doc.isoformat() if hasattr(doc, "isoformat") else str(doc)
        return doc

    def find_documents(self, database: str, collection: str, filter_dict: Optional[dict] = None,
                       projection: Optional[dict] = None, sort_list: Optional[list] = None,
                       limit: int = 50, skip: int = 0) -> Tuple[List[Dict[str, Any]], int, float, str]:
        target_db = database or self.database_name
        if not self.is_connected or not self._client:
            if not self.connect():
                return [], 0, 0.0, f"No conectado: {self.last_error}"

        start_time = time.perf_counter()
        try:
            col = self._client[target_db][collection]
            flt = filter_dict or {}
            total_count = col.count_documents(flt)
            cursor = col.find(flt, projection)
            if sort_list:
                cursor = cursor.sort(sort_list)
            cursor = cursor.skip(skip).limit(limit)
            
            docs = [self._serialize_doc(d) for d in cursor]
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return docs, total_count, elapsed_ms, ""
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return [], 0, elapsed_ms, str(e)

    def insert_document(self, database: str, collection: str, doc: dict) -> Tuple[bool, str]:
        target_db = database or self.database_name
        if not self.is_connected or not self._client:
            if not self.connect():
                return False, self.last_error
        try:
            col = self._client[target_db][collection]
            res = col.insert_one(doc)
            return True, str(res.inserted_id)
        except Exception as e:
            return False, str(e)

    def update_document(self, database: str, collection: str, doc_id: Any, doc: dict) -> Tuple[bool, str]:
        target_db = database or self.database_name
        if not self.is_connected or not self._client:
            if not self.connect():
                return False, self.last_error
        try:
            import bson
            col = self._client[target_db][collection]
            filter_id = doc_id
            if isinstance(doc_id, str) and len(doc_id) == 24:
                try:
                    filter_id = bson.ObjectId(doc_id)
                except Exception:
                    pass
            clean_doc = {k: v for k, v in doc.items() if k != "_id"}
            res = col.update_one({"_id": filter_id}, {"$set": clean_doc})
            if res.matched_count > 0:
                return True, "Documento actualizado correctamente."
            return False, "No se encontró ningún documento con ese _id."
        except Exception as e:
            return False, str(e)

    def delete_document(self, database: str, collection: str, doc_id: Any) -> Tuple[bool, str]:
        target_db = database or self.database_name
        if not self.is_connected or not self._client:
            if not self.connect():
                return False, self.last_error
        try:
            import bson
            col = self._client[target_db][collection]
            filter_id = doc_id
            if isinstance(doc_id, str) and len(doc_id) == 24:
                try:
                    filter_id = bson.ObjectId(doc_id)
                except Exception:
                    pass
            res = col.delete_one({"_id": filter_id})
            if res.deleted_count > 0:
                return True, "Documento eliminado."
            return False, "No se encontró ningún documento con ese _id."
        except Exception as e:
            return False, str(e)

    def create_collection(self, database: str, collection: str) -> Tuple[bool, str]:
        target_db = database or self.database_name
        if not self.is_connected or not self._client:
            if not self.connect():
                return False, self.last_error
        try:
            self._client[target_db].create_collection(collection)
            return True, f"Colección '{collection}' creada."
        except Exception as e:
            return False, str(e)

    def drop_collection(self, database: str, collection: str) -> Tuple[bool, str]:
        target_db = database or self.database_name
        if not self.is_connected or not self._client:
            if not self.connect():
                return False, self.last_error
        try:
            self._client[target_db].drop_collection(collection)
            return True, f"Colección '{collection}' eliminada."
        except Exception as e:
            return False, str(e)

    def execute_query(self, sql: str, params: tuple = ()) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], float, int, str]:
        """Ejecuta consultas pseudo-SQL básicas (SELECT, SHOW COLLECTIONS) sobre MongoDB"""
        if not self.is_connected or not self._client:
            if not self.connect():
                return None, None, 0.0, 0, f"No conectado: {self.last_error}"

        start_time = time.perf_counter()
        clean = sql.strip().rstrip(";")
        upper_clean = clean.upper()

        try:
            if upper_clean.startswith("SELECT"):
                m = re.match(r"SELECT\s+(.*?)\s+FROM\s+[`\"']?(\w+)[`\"']?(?:\s+LIMIT\s+(\d+))?$", clean, re.IGNORECASE)
                if m:
                    fields_str, col_name, limit_str = m.groups()
                    limit = int(limit_str) if limit_str else 100
                    docs, _, _, _ = self.find_documents(self.database_name, col_name.strip(), {}, limit=limit)
                    columns = list(docs[0].keys()) if docs else ["_id"]
                    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return docs, columns, elapsed_ms, len(docs), ""
                else:
                    return None, None, 0.0, 0, "Sintaxis SELECT no reconocida. Use: SELECT * FROM <colección> [LIMIT n];"
            elif upper_clean in ("SHOW TABLES", "SHOW COLLECTIONS"):
                cols = self.get_collections(self.database_name)
                rows = [{"Collection": c.get("name"), "Documents": c.get("count", 0)} for c in cols]
                columns = ["Collection", "Documents"]
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return rows, columns, elapsed_ms, len(rows), ""
            else:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return None, None, elapsed_ms, 0, f"Comando no soportado para MongoDB: {clean}. Use SELECT * FROM <colección>."
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return None, None, elapsed_ms, 0, str(e)

    def get_tables(self) -> List[Dict[str, Any]]:
        """Devuelve las colecciones mapeadas como tablas para diagramas ER y herramientas relacionales"""
        cols = self.get_collections(self.database_name)
        return [{"name": c.get("name"), "type": "table", "row_count": c.get("count", 0)} for c in cols]

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Infiere el esquema de campos y tipos analizando los documentos de la colección de MongoDB"""
        docs, _, _, _ = self.find_documents(self.database_name, table_name, {}, limit=15)
        field_types = {}
        for d in docs:
            for k, v in d.items():
                if k not in field_types:
                    t_name = type(v).__name__.upper()
                    if t_name == "STR": t_name = "STRING"
                    elif t_name == "INT": t_name = "INTEGER"
                    elif t_name == "FLOAT": t_name = "DOUBLE"
                    elif t_name == "BOOL": t_name = "BOOLEAN"
                    elif t_name == "LIST": t_name = "ARRAY"
                    elif t_name == "DICT": t_name = "OBJECT"
                    field_types[k] = t_name

        if not field_types:
            field_types = {"_id": "OBJECTID"}

        columns = []
        for f_name, f_type in field_types.items():
            columns.append({
                "name": f_name,
                "type": f_type,
                "pk": (f_name == "_id"),
                "notnull": (f_name == "_id")
            })

        return {"columns": columns, "indexes": [], "foreign_keys": []}

    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        return []


class RedisConnection(BaseConnection):
    """Conexión a almacén Clave-Valor Redis (redis-py) con soporte para tipos de datos y CLI"""
    def __init__(self, host: str = "localhost", port: int = 6379, db_index: int = 0,
                 password: str = "", name: str = ""):
        init_name = name or f"Redis: {host}:{port} [db{db_index}]"
        super().__init__(name=init_name, engine="redis", engine_type="kv")
        self.host = host.strip() or "localhost"
        self.port = int(port or 6379)
        self.db_index = int(db_index or 0)
        self.password = password
        self._client = None

    def connect(self) -> bool:
        try:
            import redis
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db_index,
                password=self.password or None,
                decode_responses=True,
                socket_timeout=4.0
            )
            self._client.ping()
            self.is_connected = True
            self.last_error = ""
            return True
        except ImportError:
            self.last_error = "Driver 'redis' no instalado. Descárgalo desde el gestor de conexiones."
            self.is_connected = False
            return False
        except Exception as e:
            self.last_error = str(e)
            self.is_connected = False
            return False

    def close(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self.is_connected = False

    def get_databases(self) -> List[str]:
        return [f"db{i}" for i in range(16)]

    def select_db(self, db_index: int) -> bool:
        self.db_index = db_index
        if self._client:
            try:
                self._client.execute_command("SELECT", db_index)
                self.name = f"Redis: {self.host}:{self.port} [db{self.db_index}]"
                return True
            except Exception:
                return False
        return False

    def scan_keys(self, pattern: str = "*", limit: int = 250) -> Tuple[List[Dict[str, Any]], float, str]:
        if not self.is_connected or not self._client:
            if not self.connect():
                return [], 0.0, f"No conectado: {self.last_error}"

        start_time = time.perf_counter()
        try:
            matched_keys = []
            cursor = 0
            pat = pattern.strip() or "*"
            while True:
                cursor, keys = self._client.scan(cursor=cursor, match=pat, count=100)
                matched_keys.extend(keys)
                if cursor == 0 or len(matched_keys) >= limit:
                    break
            
            matched_keys = matched_keys[:limit]
            results = []
            for k in matched_keys:
                k_type = self._client.type(k)
                ttl = self._client.ttl(k)
                size = 0
                try:
                    size = self._client.memory_usage(k) or 0
                except Exception:
                    pass
                results.append({
                    "key": k,
                    "type": (k_type or "none").upper(),
                    "ttl": ttl,
                    "size_bytes": size
                })

            results.sort(key=lambda item: item["key"].lower())
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return results, elapsed_ms, ""
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return [], elapsed_ms, str(e)

    def get_key_value(self, key: str) -> Tuple[str, Any, int, str]:
        if not self.is_connected or not self._client:
            return "none", None, -1, "No conectado"
        try:
            k_type = (self._client.type(key) or "none").lower()
            ttl = self._client.ttl(key)
            if k_type == "string":
                val = self._client.get(key)
            elif k_type == "hash":
                val = self._client.hgetall(key)
            elif k_type == "list":
                val = self._client.lrange(key, 0, 500)
            elif k_type == "set":
                val = list(self._client.smembers(key))
            elif k_type == "zset":
                val = self._client.zrange(key, 0, 500, withscores=True)
            else:
                val = str(self._client.get(key))
            return k_type, val, ttl, ""
        except Exception as e:
            return "none", None, -1, str(e)

    def set_key_value(self, key: str, key_type: str, value: Any, ttl: int = -1) -> Tuple[bool, str]:
        if not self.is_connected or not self._client:
            return False, "No conectado"
        try:
            t = key_type.lower()
            if t == "string":
                self._client.set(key, str(value))
            elif t == "hash":
                if isinstance(value, dict):
                    self._client.delete(key)
                    if value:
                        self._client.hset(key, mapping=value)
                else:
                    self._client.set(key, str(value))
            elif t == "list":
                self._client.delete(key)
                if isinstance(value, list) and value:
                    self._client.rpush(key, *value)
            elif t == "set":
                self._client.delete(key)
                if isinstance(value, (list, set)) and value:
                    self._client.sadd(key, *value)
            else:
                self._client.set(key, str(value))

            if ttl > 0:
                self._client.expire(key, ttl)
            elif ttl == -1:
                self._client.persist(key)
            return True, "Clave guardada con éxito."
        except Exception as e:
            return False, str(e)

    def delete_key(self, key: str) -> Tuple[bool, str]:
        if not self.is_connected or not self._client:
            return False, "No conectado"
        try:
            self._client.delete(key)
            return True, f"Clave '{key}' eliminada."
        except Exception as e:
            return False, str(e)

    def set_ttl(self, key: str, seconds: int) -> Tuple[bool, str]:
        if not self.is_connected or not self._client:
            return False, "No conectado"
        try:
            if seconds == -1:
                self._client.persist(key)
                return True, "Expiración removida (persistente)."
            else:
                self._client.expire(key, seconds)
                return True, f"TTL configurado a {seconds}s."
        except Exception as e:
            return False, str(e)

    def execute_command(self, cmd_line: str) -> Tuple[Any, float, str]:
        if not self.is_connected or not self._client:
            if not self.connect():
                return None, 0.0, f"No conectado: {self.last_error}"
        start_time = time.perf_counter()
        try:
            parts = shlex.split(cmd_line.strip())
            if not parts:
                return None, 0.0, "Comando vacío"
            cmd = parts[0].upper()
            args = parts[1:]
            res = self._client.execute_command(cmd, *args)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return res, elapsed_ms, ""
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return None, elapsed_ms, str(e)

    def flush_current_db(self) -> Tuple[bool, str]:
        if not self.is_connected or not self._client:
            return False, "No conectado"
        try:
            self._client.flushdb()
            return True, f"Base de datos db{self.db_index} vaciada (FLUSHDB)."
        except Exception as e:
            return False, str(e)

    def execute_query(self, sql: str, params: tuple = ()) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], float, int, str]:
        """Ejecuta comandos Redis y devuelve el resultado en formato tabular"""
        clean = sql.strip().rstrip(";")
        res, elapsed_ms, err = self.execute_command(clean)
        if err:
            return None, None, elapsed_ms, 0, err

        if isinstance(res, list):
            rows = [{"Index": i, "Value": str(item)} for i, item in enumerate(res)]
            cols = ["Index", "Value"]
            return rows, cols, elapsed_ms, len(rows), ""
        elif isinstance(res, dict):
            rows = [{"Key": str(k), "Value": str(v)} for k, v in res.items()]
            cols = ["Key", "Value"]
            return rows, cols, elapsed_ms, len(rows), ""
        else:
            rows = [{"Result": str(res)}]
            cols = ["Result"]
            return rows, cols, elapsed_ms, 1, ""

    def get_tables(self) -> List[Dict[str, Any]]:
        return []

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        return {"columns": [], "indexes": [], "foreign_keys": []}

    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        return []


class LocalDocumentConnection(BaseConnection):
    """Base de datos NoSQL de documentos local (JSON puro autónomo, sin dependencias externas)"""
    def __init__(self, file_path: str, name: str = ""):
        self.file_path = Path(file_path)
        init_name = name or f"NoSQL Local: {self.file_path.name}"
        super().__init__(name=init_name, engine="localdoc", engine_type="document")
        self._data = {"collections": {}}

    def connect(self) -> bool:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            if self.file_path.exists():
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            self._data = json.loads(content)
                        else:
                            self._data = {"collections": {}}
                except Exception:
                    self._data = {"collections": {}}
            else:
                self._data = {"collections": {"sample_docs": [
                    {"_id": "1", "nombre": "MultiTool", "tipo": "Suite", "activo": True, "tags": ["python", "pyqt6"]},
                    {"_id": "2", "nombre": "NoSQL Store", "tipo": "DocumentDB", "activo": True, "version": 1.0}
                ]}}
                self._save()

            if not self._data.get("collections") or not isinstance(self._data.get("collections"), dict):
                self._data["collections"] = {"sample_docs": [
                    {"_id": "1", "nombre": "MultiTool", "tipo": "Suite", "activo": True, "tags": ["python", "pyqt6"]},
                    {"_id": "2", "nombre": "NoSQL Store", "tipo": "DocumentDB", "activo": True, "version": 1.0}
                ]}
                self._save()

            self.is_connected = True
            self.last_error = ""
            return True
        except Exception as e:
            self.last_error = str(e)
            self.is_connected = False
            return False

    def close(self):
        self._save()
        self.is_connected = False

    def _save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[LocalDocumentConnection] Error guardando JSON: {e}")

    def get_databases(self) -> List[str]:
        return [self.file_path.stem]

    def get_collections(self, database: str = "") -> List[Dict[str, Any]]:
        cols = []
        for name, items in self._data.get("collections", {}).items():
            cols.append({
                "name": name,
                "type": "collection",
                "doc_count": len(items) if isinstance(items, list) else 0
            })
        return cols

    def find_documents(self, database: str, collection: str, filter_dict: Optional[dict] = None,
                       projection: Optional[dict] = None, sort_list: Optional[list] = None,
                       limit: int = 50, skip: int = 0) -> Tuple[List[Dict[str, Any]], int, float, str]:
        start_time = time.perf_counter()
        try:
            items = self._data.get("collections", {}).get(collection, [])
            flt = filter_dict or {}

            # Filtrado simple en memoria
            matched = []
            for doc in items:
                match = True
                for k, v in flt.items():
                    if k.startswith("$"):
                        continue
                    if k not in doc or doc[k] != v:
                        match = False
                        break
                if match:
                    matched.append(doc)

            total_count = len(matched)
            paginated = matched[skip:skip + limit]
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return paginated, total_count, elapsed_ms, ""
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return [], 0, elapsed_ms, str(e)

    def insert_document(self, database: str, collection: str, doc: dict) -> Tuple[bool, str]:
        try:
            if collection not in self._data["collections"]:
                self._data["collections"][collection] = []
            new_doc = dict(doc)
            if "_id" not in new_doc or not new_doc["_id"]:
                new_doc["_id"] = uuid.uuid4().hex[:12]
            self._data["collections"][collection].append(new_doc)
            self._save()
            return True, str(new_doc["_id"])
        except Exception as e:
            return False, str(e)

    def update_document(self, database: str, collection: str, doc_id: Any, doc: dict) -> Tuple[bool, str]:
        try:
            items = self._data.get("collections", {}).get(collection, [])
            for idx, existing in enumerate(items):
                if str(existing.get("_id")) == str(doc_id):
                    updated = dict(existing)
                    updated.update(doc)
                    updated["_id"] = existing.get("_id")
                    items[idx] = updated
                    self._save()
                    return True, "Documento actualizado."
            return False, f"Documento con _id '{doc_id}' no encontrado."
        except Exception as e:
            return False, str(e)

    def delete_document(self, database: str, collection: str, doc_id: Any) -> Tuple[bool, str]:
        try:
            items = self._data.get("collections", {}).get(collection, [])
            new_items = [d for d in items if str(d.get("_id")) != str(doc_id)]
            if len(new_items) < len(items):
                self._data["collections"][collection] = new_items
                self._save()
                return True, "Documento eliminado."
            return False, f"Documento '{doc_id}' no encontrado."
        except Exception as e:
            return False, str(e)

    def create_collection(self, database: str, collection: str) -> Tuple[bool, str]:
        try:
            if collection in self._data["collections"]:
                return True, "La colección ya existe."
            self._data["collections"][collection] = []
            self._save()
            return True, f"Colección '{collection}' creada."
        except Exception as e:
            return False, str(e)

    def drop_collection(self, database: str, collection: str) -> Tuple[bool, str]:
        try:
            if collection in self._data["collections"]:
                del self._data["collections"][collection]
                self._save()
                return True, f"Colección '{collection}' eliminada."
            return False, "Colección no encontrada."
        except Exception as e:
            return False, str(e)

    def execute_query(self, sql: str, params: tuple = ()) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], float, int, str]:
        """Ejecuta consultas pseudo-SQL (SELECT, INSERT, SHOW) sobre colecciones JSON locales"""
        if not self.is_connected:
            if not self.connect():
                return None, None, 0.0, 0, f"No conectado: {self.last_error}"

        start_time = time.perf_counter()
        clean = sql.strip().rstrip(";")
        upper_clean = clean.upper()

        try:
            # 1. SELECT * FROM <collection> [LIMIT n]
            if upper_clean.startswith("SELECT"):
                m = re.match(r"SELECT\s+(.*?)\s+FROM\s+[`\"']?(\w+)[`\"']?(?:\s+WHERE\s+(.*?))?(?:\s+LIMIT\s+(\d+))?$", clean, re.IGNORECASE)
                if m:
                    fields_str, col_name, where_str, limit_str = m.groups()
                    col_name = col_name.strip()
                    docs, _, _, _ = self.find_documents("", col_name, {})

                    if limit_str:
                        docs = docs[:int(limit_str)]

                    if fields_str.strip() != "*":
                        req_fields = [f.strip(" `\"'") for f in fields_str.split(",")]
                        filtered_docs = []
                        for d in docs:
                            fd = {k: d.get(k) for k in req_fields}
                            filtered_docs.append(fd)
                        docs = filtered_docs

                    columns = list(docs[0].keys()) if docs else ["_id"]
                    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return docs, columns, elapsed_ms, len(docs), ""
                else:
                    return None, None, 0.0, 0, "Sintaxis SELECT no reconocida. Use: SELECT * FROM <colección> [LIMIT n];"

            # 2. INSERT INTO <collection> VALUES (...) o JSON
            elif upper_clean.startswith("INSERT"):
                m = re.match(r"INSERT\s+INTO\s+[`\"']?(\w+)[`\"']?\s*(.*)", clean, re.IGNORECASE)
                if m:
                    col_name, rest = m.groups()
                    col_name = col_name.strip()
                    doc_json = None
                    if "{" in rest and "}" in rest:
                        json_str = rest[rest.find("{"):rest.rfind("}")+1]
                        doc_json = json.loads(json_str)
                    elif "VALUES" in rest.upper():
                        val_str = rest[rest.upper().find("VALUES") + 6:].strip().strip("()")
                        parts = [p.strip().strip("'\"") for p in val_str.split(",")]
                        doc_json = {f"campo_{i+1}": p for i, p in enumerate(parts)}

                    if doc_json:
                        ok, new_id = self.insert_document("", col_name, doc_json)
                        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                        if ok:
                            return [], [], elapsed_ms, 1, ""
                        else:
                            return None, None, elapsed_ms, 0, new_id
                return None, None, 0.0, 0, "Sintaxis INSERT no reconocida para DocumentDB. Ejemplo: INSERT INTO sample_docs {'nombre': 'Test'};"

            # 3. SHOW TABLES / SHOW COLLECTIONS
            elif upper_clean in ("SHOW TABLES", "SHOW COLLECTIONS"):
                cols = self.get_collections()
                rows = [{"Collection": c.get("name"), "Documents": c.get("count", 0)} for c in cols]
                columns = ["Collection", "Documents"]
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return rows, columns, elapsed_ms, len(rows), ""

            else:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return None, None, elapsed_ms, 0, f"El motor NoSQL Local no reconoce la sentencia SQL '{clean}'."

        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return None, None, elapsed_ms, 0, str(e)

    def get_tables(self) -> List[Dict[str, Any]]:
        """Devuelve las colecciones locales mapeadas como tablas para diagramas ER"""
        cols = self.get_collections()
        return [{"name": c.get("name"), "type": "table", "row_count": c.get("count", 0)} for c in cols]

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Infiere el esquema analizando los documentos de la colección local"""
        docs, _, _, _ = self.find_documents("", table_name, {}, limit=15)
        field_types = {}
        for d in docs:
            for k, v in d.items():
                if k not in field_types:
                    t_name = type(v).__name__.upper()
                    if t_name == "STR": t_name = "STRING"
                    elif t_name == "INT": t_name = "INTEGER"
                    elif t_name == "FLOAT": t_name = "DOUBLE"
                    elif t_name == "BOOL": t_name = "BOOLEAN"
                    elif t_name == "LIST": t_name = "ARRAY"
                    elif t_name == "DICT": t_name = "OBJECT"
                    field_types[k] = t_name

        if not field_types:
            field_types = {"_id": "STRING"}

        columns = []
        for f_name, f_type in field_types.items():
            columns.append({
                "name": f_name,
                "type": f_type,
                "pk": (f_name == "_id"),
                "notnull": (f_name == "_id")
            })

        return {"columns": columns, "indexes": [], "foreign_keys": []}

    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        return []
