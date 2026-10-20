"""
sql_parser.py - Divisor inteligente de sentencias SQL multi-bloque y analizador
de comandos de gestión (USE DATABASE, USE TABLE, CREATE/DROP DATABASE, SHOW).
"""
import re
from typing import List, Optional, Dict, Any


def split_sql_statements(sql_text: str) -> List[str]:
    """
    Divide un script SQL en sentencias individuales separadas por punto y coma (;),
    respetando cadenas literales ('...', "..."), identificadores entrecomillados (`...`),
    comentarios de una línea (-- ...) y comentarios multilínea (/* ... */).
    """
    if not sql_text:
        return []

    statements = []
    current: List[str] = []
    length = len(sql_text)
    i = 0

    in_single_quote = False
    in_double_quote = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False

    while i < length:
        char = sql_text[i]
        next_char = sql_text[i + 1] if i + 1 < length else ''

        # Manejo de comentarios de una línea (-- ...)
        if in_line_comment:
            current.append(char)
            if char == '\n':
                in_line_comment = False
            i += 1
            continue

        # Manejo de comentarios multilínea (/* ... */)
        if in_block_comment:
            current.append(char)
            if char == '*' and next_char == '/':
                current.append(next_char)
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        # Apertura de comentarios fuera de comillas
        if not (in_single_quote or in_double_quote or in_backtick):
            if char == '-' and next_char == '-':
                in_line_comment = True
                current.append(char)
                current.append(next_char)
                i += 2
                continue
            if char == '/' and next_char == '*':
                in_block_comment = True
                current.append(char)
                current.append(next_char)
                i += 2
                continue

        # Comillas simples ('...')
        if char == "'" and not (in_double_quote or in_backtick):
            current.append(char)
            if in_single_quote:
                # Comprobar comilla escapada ('')
                if next_char == "'":
                    current.append(next_char)
                    i += 2
                    continue
                in_single_quote = False
            else:
                in_single_quote = True
            i += 1
            continue

        # Comillas dobles ("...")
        if char == '"' and not (in_single_quote or in_backtick):
            current.append(char)
            if in_double_quote:
                if next_char == '"':
                    current.append(next_char)
                    i += 2
                    continue
                in_double_quote = False
            else:
                in_double_quote = True
            i += 1
            continue

        # Backticks (`...`)
        if char == '`' and not (in_single_quote or in_double_quote):
            current.append(char)
            in_backtick = not in_backtick
            i += 1
            continue

        # Delimitador de sentencia (;) fuera de comillas y comentarios
        if char == ';' and not (in_single_quote or in_double_quote or in_backtick):
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue

        current.append(char)
        i += 1

    # Agregar última sentencia si existe sin punto y coma final
    remainder = "".join(current).strip()
    if remainder:
        statements.append(remainder)

    return statements


def _clean_sql_identifier(raw: str) -> str:
    """Elimina comillas simples, dobles, acentos graves o corchetes de identificadores SQL"""
    raw = raw.strip()
    if (raw.startswith("`") and raw.endswith("`")) or \
       (raw.startswith('"') and raw.endswith('"')) or \
       (raw.startswith("'") and raw.endswith("'")) or \
       (raw.startswith("[") and raw.endswith("]")):
        return raw[1:-1].strip()
    return raw


def parse_special_command(statement: str) -> Optional[Dict[str, Any]]:
    """
    Analiza una sentencia individual para determinar si corresponde a un comando especial
    de administración: USE DATABASE, USE TABLE, CREATE/DROP DATABASE, SHOW DATABASES/TABLES.
    Retorna un diccionario con la instrucción o None si es SQL estándar.
    """
    clean = statement.strip().rstrip(';').strip()
    if not clean:
        return None

    # 1. USE TABLE <nombre>
    m_use_tbl = re.match(r"^\s*USE\s+TABLE\s+(.+)$", clean, re.IGNORECASE)
    if m_use_tbl:
        target = _clean_sql_identifier(m_use_tbl.group(1))
        return {"type": "USE_TABLE", "target": target}

    # 2. USE DATABASE <nombre> o USE SCHEMA <nombre>
    m_use_db = re.match(r"^\s*USE\s+(?:DATABASE|SCHEMA)\s+(.+)$", clean, re.IGNORECASE)
    if m_use_db:
        target = _clean_sql_identifier(m_use_db.group(1))
        return {"type": "USE_DATABASE", "target": target}

    # 3. USE <nombre> (Genérico: puede resolver a base de datos o tabla según contexto)
    m_use = re.match(r"^\s*USE\s+(.+)$", clean, re.IGNORECASE)
    if m_use:
        target = _clean_sql_identifier(m_use.group(1))
        return {"type": "USE_AUTO", "target": target}

    # 4. CREATE DATABASE [IF NOT EXISTS] <nombre>
    m_create_db = re.match(r"^\s*CREATE\s+DATABASE(?:\s+(IF\s+NOT\s+EXISTS))?\s+(.+)$", clean, re.IGNORECASE)
    if m_create_db:
        if_not_exists = bool(m_create_db.group(1))
        name = _clean_sql_identifier(m_create_db.group(2))
        return {"type": "CREATE_DATABASE", "name": name, "if_not_exists": if_not_exists}

    # 5. DROP DATABASE [IF EXISTS] <nombre>
    m_drop_db = re.match(r"^\s*DROP\s+DATABASE(?:\s+(IF\s+EXISTS))?\s+(.+)$", clean, re.IGNORECASE)
    if m_drop_db:
        if_exists = bool(m_drop_db.group(1))
        name = _clean_sql_identifier(m_drop_db.group(2))
        return {"type": "DROP_DATABASE", "name": name, "if_exists": if_exists}

    # 6. SHOW DATABASES / SHOW SCHEMAS
    if re.match(r"^\s*SHOW\s+(?:DATABASES|SCHEMAS)\s*$", clean, re.IGNORECASE):
        return {"type": "SHOW_DATABASES"}

    # 7. SHOW TABLES
    if re.match(r"^\s*SHOW\s+TABLES\s*$", clean, re.IGNORECASE):
        return {"type": "SHOW_TABLES"}

    return None

