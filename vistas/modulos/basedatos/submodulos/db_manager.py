"""
db_manager.py - Motor de conexión y operaciones de base de datos multibase (SQLite, PostgreSQL, MySQL, MongoDB, Redis, NoSQL Local)
para MultiTool con descarga y verificación dinámica de drivers bajo autorización.
"""
import sqlite3
import time
import csv
import json
import re
import shlex
import uuid
from datetime import datetime
import importlib.util
import subprocess
import sys
import os
import io
import zipfile
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union

from ..utils.driver_installer import DriverManager
from ..utils.connection_base import BaseConnection, RelationalConnection
from ..utils.nosql_connections import (
    MongoDBConnection,
    RedisConnection,
    LocalDocumentConnection
)


class DatabaseConnection(RelationalConnection):
    """Conexión nativa a base de datos SQLite"""
    def __init__(self, db_path: str, name: str = ""):
        init_name = name or (Path(db_path).name if db_path != ":memory:" else "En Memoria (:memory:)")
        super().__init__(name=init_name, engine="sqlite")
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> bool:
        try:
            iso = None if self.autocommit else "DEFERRED"
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=iso)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self.is_connected = True
            self.last_error = ""
            return True
        except Exception as e:
            self.last_error = str(e)
            self.is_connected = False
            return False

    def close(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        self.is_connected = False

    def execute_query(self, sql: str, params: tuple = ()) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], float, int, str]:
        if not self.is_connected or not self._conn:
            if not self.connect():
                return None, None, 0.0, 0, f"No conectado: {self.last_error}"

        start_time = time.perf_counter()
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, params)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = [dict(row) for row in cursor.fetchall()]
                affected = len(rows)
                return rows, columns, elapsed_ms, affected, ""
            else:
                if self.autocommit:
                    try:
                        self._conn.commit()
                    except Exception:
                        pass
                affected = cursor.rowcount
                return [], [], elapsed_ms, affected, ""
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            try:
                self._conn.rollback()
            except Exception:
                pass
            return None, None, elapsed_ms, 0, str(e)

    def get_tables(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT name, type, sql 
            FROM sqlite_master 
            WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name;
        """
        rows, _, _, _, err = self.execute_query(sql)
        if err or not rows:
            return []

        tables = []
        for r in rows:
            t_name = r["name"]
            t_type = r["type"]
            t_sql = r.get("sql", "")
            row_count = 0
            if t_type == "table":
                try:
                    c_rows, _, _, _, _ = self.execute_query(f'SELECT COUNT(*) as cnt FROM "{t_name}";')
                    if c_rows:
                        row_count = c_rows[0].get("cnt", 0)
                except Exception:
                    pass

            tables.append({
                "name": t_name,
                "type": t_type,
                "sql": t_sql,
                "row_count": row_count
            })
        return tables

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        cols_rows, _, _, _, _ = self.execute_query(f'PRAGMA table_info("{table_name}");')
        columns = []
        if cols_rows:
            for c in cols_rows:
                columns.append({
                    "cid": c.get("cid"),
                    "name": c.get("name"),
                    "type": c.get("type", "TEXT") or "TEXT",
                    "notnull": bool(c.get("notnull", 0)),
                    "default_value": c.get("dflt_value"),
                    "pk": bool(c.get("pk", 0))
                })

        idx_rows, _, _, _, _ = self.execute_query(f'PRAGMA index_list("{table_name}");')
        indexes = []
        if idx_rows:
            for idx in idx_rows:
                indexes.append({
                    "name": idx.get("name"),
                    "unique": bool(idx.get("unique", 0)),
                    "origin": idx.get("origin")
                })

        ddl_row, _, _, _, _ = self.execute_query(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (table_name,)
        )
        ddl = ddl_row[0].get("sql", "") if ddl_row else ""

        return {
            "table_name": table_name,
            "columns": columns,
            "indexes": indexes,
            "ddl": ddl
        }

    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Obtiene las relaciones de claves foráneas de una tabla en SQLite"""
        fk_rows, _, _, _, _ = self.execute_query(f'PRAGMA foreign_key_list("{table_name}");')
        fks = []
        if fk_rows:
            for r in fk_rows:
                fks.append({
                    "from": r.get("from"),
                    "to_table": r.get("table"),
                    "to_column": r.get("to")
                })
        return fks

    def update_cell(self, table_name: str, pk_column: str, pk_value: Any, col_name: str, new_value: Any) -> Tuple[bool, str]:
        sql = f'UPDATE "{table_name}" SET "{col_name}" = ? WHERE "{pk_column}" = ?;'
        _, _, _, affected, err = self.execute_query(sql, (new_value, pk_value))
        if err:
            return False, err
        return True, f"{affected} fila(s) actualizada(s)."

    def delete_row(self, table_name: str, pk_column: str, pk_value: Any) -> Tuple[bool, str]:
        sql = f'DELETE FROM "{table_name}" WHERE "{pk_column}" = ?;'
        _, _, _, affected, err = self.execute_query(sql, (pk_value,))
        if err:
            return False, err
        return True, f"{affected} fila eliminada."

    def set_autocommit(self, enabled: bool):
        self.autocommit = enabled
        if self._conn:
            self._conn.isolation_level = None if enabled else "DEFERRED"

    def commit(self) -> Tuple[bool, str]:
        if self._conn:
            try:
                self._conn.commit()
                return True, "Transacción confirmada (COMMIT exitoso)."
            except Exception as e:
                return False, str(e)
        return False, "No conectado"

    def rollback(self) -> Tuple[bool, str]:
        if self._conn:
            try:
                self._conn.rollback()
                return True, "Transacción revertida (ROLLBACK exitoso)."
            except Exception as e:
                return False, str(e)
        return False, "No conectado"

    def get_databases(self) -> List[str]:
        dbs = ["main"]
        rows, _, _, _, _ = self.execute_query("PRAGMA database_list;")
        if rows:
            dbs = [r.get("name", "main") for r in rows]
        return dbs

    def get_explain_plan(self, sql: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], str]:
        clean_sql = sql.strip().rstrip(';')
        explain_sql = f"EXPLAIN QUERY PLAN {clean_sql};"
        rows, cols, _, _, err = self.execute_query(explain_sql)
        return rows, cols, err


class PostgreSQLConnection(RelationalConnection):
    """Conexión remota a bases de datos PostgreSQL (psycopg2 o pg8000)"""
    def __init__(self, host="localhost", port=5432, database="postgres", user="postgres", password="", name=""):
        init_name = name or f"Postgres: {database or 'postgres'}@{host}"
        super().__init__(name=init_name, engine="postgresql")
        self.host = host
        self.port = int(port or 5432)
        self.database = database or "postgres"
        self.user = user or "postgres"
        self.password = password
        self._conn = None

    def connect(self) -> bool:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            self._conn = psycopg2.connect(
                host=self.host, port=self.port, dbname=self.database,
                user=self.user, password=self.password,
                cursor_factory=RealDictCursor
            )
            self._conn.autocommit = True
            self.is_connected = True
            self.last_error = ""
            return True
        except ImportError:
            try:
                import pg8000.native
                self._conn = pg8000.native.Connection(
                    user=self.user, host=self.host, port=self.port,
                    database=self.database, password=self.password
                )
                self.is_connected = True
                self.last_error = ""
                return True
            except Exception as e:
                self.last_error = f"Error cargando driver PostgreSQL: {e}"
                self.is_connected = False
                return False
        except Exception as e:
            self.last_error = str(e)
            self.is_connected = False
            return False

    def close(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        self.is_connected = False

    def execute_query(self, sql: str, params: tuple = ()) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], float, int, str]:
        if not self.is_connected or not self._conn:
            if not self.connect():
                return None, None, 0.0, 0, f"No conectado: {self.last_error}"

        start_time = time.perf_counter()
        try:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                raw = cur.fetchall()
                rows = [dict(r) for r in raw]
                affected = len(rows)
                return rows, columns, elapsed_ms, affected, ""
            else:
                affected = cur.rowcount if hasattr(cur, "rowcount") else 0
                return [], [], elapsed_ms, affected, ""
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return None, None, elapsed_ms, 0, str(e)

    def get_tables(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT table_name as name, table_type as type
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_type, table_name;
        """
        rows, _, _, _, err = self.execute_query(sql)
        if err or not rows:
            return []
        tables = []
        for r in rows:
            t_name = r["name"]
            t_type = "table" if "TABLE" in r.get("type", "").upper() else "view"
            c_rows, _, _, _, _ = self.execute_query(f'SELECT COUNT(*) as cnt FROM "{t_name}";')
            cnt = c_rows[0].get("cnt", 0) if c_rows else 0
            tables.append({"name": t_name, "type": t_type, "row_count": cnt})
        return tables

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        sql_cols = f"""
            SELECT column_name as name, data_type as type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}' AND table_schema = 'public'
            ORDER BY ordinal_position;
        """
        cols_rows, _, _, _, _ = self.execute_query(sql_cols)
        sql_pk = f"""
            SELECT c.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage c ON c.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = '{table_name}';
        """
        pk_rows, _, _, _, _ = self.execute_query(sql_pk)
        pks = {r["column_name"] for r in (pk_rows or [])}

        columns = []
        for c in (cols_rows or []):
            is_pk = c["name"] in pks
            columns.append({
                "name": c["name"],
                "type": c.get("type", "text").upper(),
                "notnull": c.get("is_nullable") == "NO",
                "pk": is_pk
            })

        return {
            "table_name": table_name,
            "columns": columns,
            "indexes": [],
            "ddl": f"-- PostgreSQL Table: public.{table_name}"
        }

    def update_cell(self, table_name: str, pk_column: str, pk_value: Any, col_name: str, new_value: Any) -> Tuple[bool, str]:
        sql = f'UPDATE "{table_name}" SET "{col_name}" = %s WHERE "{pk_column}" = %s;'
        _, _, _, affected, err = self.execute_query(sql, (new_value, pk_value))
        if err:
            return False, err
        return True, f"{affected} fila(s) actualizada(s)."

    def set_autocommit(self, enabled: bool):
        self.autocommit = enabled
        if self._conn and hasattr(self._conn, "autocommit"):
            try:
                self._conn.autocommit = enabled
            except Exception:
                pass

    def commit(self) -> Tuple[bool, str]:
        if self._conn:
            try:
                self._conn.commit()
                return True, "Transacción confirmada (COMMIT exitoso)."
            except Exception as e:
                return False, str(e)
        return False, "No conectado"

    def rollback(self) -> Tuple[bool, str]:
        if self._conn:
            try:
                self._conn.rollback()
                return True, "Transacción revertida (ROLLBACK exitoso)."
            except Exception as e:
                return False, str(e)
        return False, "No conectado"

    def get_databases(self) -> List[str]:
        sql = "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;"
        rows, _, _, _, _ = self.execute_query(sql)
        if rows:
            return [r["datname"] for r in rows if "datname" in r]
        return [self.database]

    def get_explain_plan(self, sql: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], str]:
        clean_sql = sql.strip().rstrip(';')
        explain_sql = f"EXPLAIN {clean_sql};"
        rows, cols, _, _, err = self.execute_query(explain_sql)
        return rows, cols, err


class MySQLConnection(RelationalConnection):
    """Conexión remota a bases de datos MySQL / MariaDB (PyMySQL)"""
    def __init__(self, host="localhost", port=3306, database="", user="root", password="", name=""):
        init_name = name or f"MySQL: {database or 'localhost'}@{host}"
        super().__init__(name=init_name, engine="mysql")
        self.host = host
        self.port = int(port or 3306)
        self.database = database
        self.user = user or "root"
        self.password = password
        self._conn = None

    def connect(self) -> bool:
        try:
            import pymysql
            import pymysql.cursors
            self._conn = pymysql.connect(
                host=self.host, port=self.port, user=self.user,
                password=self.password, database=self.database or None,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            self.is_connected = True
            self.last_error = ""
            return True
        except Exception as e:
            self.last_error = str(e)
            self.is_connected = False
            return False

    def close(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        self.is_connected = False

    def execute_query(self, sql: str, params: tuple = ()) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], float, int, str]:
        if not self.is_connected or not self._conn:
            if not self.connect():
                return None, None, 0.0, 0, f"No conectado: {self.last_error}"

        start_time = time.perf_counter()
        try:
            # Detectar si la sentencia es USE <nombre_db>
            use_match = re.match(r"^\s*USE\s+([a-zA-Z0-9_`\"-]+)", sql, re.IGNORECASE)
            if use_match:
                new_db = use_match.group(1).strip('`"\' ')
                self.database = new_db
                self.name = f"MySQL: {self.database}@{self.host}"

            with self._conn.cursor() as cur:
                cur.execute(sql, params)
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = list(cur.fetchall())
                    affected = len(rows)
                    return rows, columns, elapsed_ms, affected, ""
                else:
                    affected = cur.rowcount
                    return [], [], elapsed_ms, affected, ""
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return None, None, elapsed_ms, 0, str(e)

    def get_tables(self) -> List[Dict[str, Any]]:
        if not self.database:
            sql = "SHOW DATABASES;"
            rows, _, _, _, _ = self.execute_query(sql)
            return [{"name": r.get("Database", ""), "type": "database", "row_count": 0} for r in (rows or [])]

        sql = f"""
            SELECT table_name as name, table_type as type
            FROM information_schema.tables
            WHERE table_schema = '{self.database}'
            ORDER BY table_type, table_name;
        """
        rows, _, _, _, err = self.execute_query(sql)
        if err or not rows:
            return []
        tables = []
        for r in rows:
            t_name = r["name"]
            t_type = "table" if "TABLE" in r.get("type", "").upper() else "view"
            c_rows, _, _, _, _ = self.execute_query(f'SELECT COUNT(*) as cnt FROM `{t_name}`;')
            cnt = c_rows[0].get("cnt", 0) if c_rows else 0
            tables.append({"name": t_name, "type": t_type, "row_count": cnt})
        return tables

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        sql = f"DESCRIBE `{table_name}`;"
        rows, _, _, _, _ = self.execute_query(sql)
        columns = []
        for r in (rows or []):
            is_pk = r.get("Key") == "PRI"
            columns.append({
                "name": r.get("Field"),
                "type": r.get("Type", "varchar").upper(),
                "notnull": r.get("Null") == "NO",
                "pk": is_pk
            })

        ddl_rows, _, _, _, _ = self.execute_query(f"SHOW CREATE TABLE `{table_name}`;")
        ddl = ""
        if ddl_rows:
            ddl = ddl_rows[0].get("Create Table", "")

        return {
            "table_name": table_name,
            "columns": columns,
            "indexes": [],
            "ddl": ddl
        }

    def update_cell(self, table_name: str, pk_column: str, pk_value: Any, col_name: str, new_value: Any) -> Tuple[bool, str]:
        sql = f"UPDATE `{table_name}` SET `{col_name}` = %s WHERE `{pk_column}` = %s;"
        _, _, _, affected, err = self.execute_query(sql, (new_value, pk_value))
        if err:
            return False, err
        return True, f"{affected} fila(s) actualizada(s)."

    def set_autocommit(self, enabled: bool):
        self.autocommit = enabled
        if self._conn and hasattr(self._conn, "autocommit"):
            try:
                self._conn.autocommit(enabled)
            except Exception:
                pass

    def commit(self) -> Tuple[bool, str]:
        if self._conn:
            try:
                self._conn.commit()
                return True, "Transacción confirmada (COMMIT exitoso)."
            except Exception as e:
                return False, str(e)
        return False, "No conectado"

    def rollback(self) -> Tuple[bool, str]:
        if self._conn:
            try:
                self._conn.rollback()
                return True, "Transacción revertida (ROLLBACK exitoso)."
            except Exception as e:
                return False, str(e)
        return False, "No conectado"

    def get_databases(self) -> List[str]:
        rows, _, _, _, _ = self.execute_query("SHOW DATABASES;")
        if rows:
            return [r.get("Database", "") for r in rows if r.get("Database")]
        return [self.database] if self.database else []

    def get_explain_plan(self, sql: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], str]:
        clean_sql = sql.strip().rstrip(';')
        explain_sql = f"EXPLAIN {clean_sql};"
        rows, cols, _, _, err = self.execute_query(explain_sql)
        return rows, cols, err
