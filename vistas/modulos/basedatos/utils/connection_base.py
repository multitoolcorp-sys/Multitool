"""
connection_base.py - Clases base abstractas para conexiones a bases de datos relacionales y NoSQL.
"""
from typing import List


class BaseConnection:
    """Clase base para todos los motores de bases de datos (Relacionales y NoSQL)"""
    def __init__(self, name: str = "", engine: str = "", engine_type: str = "relational"):
        self.name = name
        self.engine = engine
        self.engine_type = engine_type  # "relational", "document", "kv"
        self.is_connected = False
        self.last_error = ""

    def connect(self) -> bool:
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def get_databases(self) -> List[str]:
        return []

    def execute_query(self, sql: str, params: tuple = ()):
        return None, None, 0.0, 0, f"El motor '{self.engine}' no soporta execute_query."

    def get_tables(self) -> List[dict]:
        return []

    def get_table_schema(self, table_name: str) -> dict:
        return {"columns": [], "indexes": [], "foreign_keys": []}

    def get_foreign_keys(self, table_name: str) -> List[dict]:
        return []


class RelationalConnection(BaseConnection):
    """Clase base especializada para motores de bases de datos relacionales (SQL)"""
    def __init__(self, name: str = "", engine: str = "sqlite"):
        super().__init__(name=name, engine=engine, engine_type="relational")
        self.autocommit = True

    def execute_query(self, sql: str, params: tuple = ()):
        raise NotImplementedError

    def get_tables(self):
        raise NotImplementedError

    def get_table_schema(self, table_name: str):
        raise NotImplementedError

    def update_cell(self, table_name: str, pk_column: str, pk_value, col_name: str, new_value):
        raise NotImplementedError

    def delete_row(self, table_name: str, pk_column: str, pk_value):
        raise NotImplementedError

    def set_autocommit(self, enabled: bool):
        self.autocommit = enabled

    def commit(self):
        return True, ""

    def rollback(self):
        return True, ""

    def get_explain_plan(self, sql: str):
        return None, None, "No soportado"
