"""
formula_engine.py — Motor de evaluación de fórmulas matemáticas y estadísticas estilo Excel para Cuaderno.
Soporta:
- Funciones: SUMA/SUM, PROMEDIO/AVERAGE, MAX, MIN, CONTAR/COUNT, PRODUCTO/PRODUCT, REDONDEAR/ROUND, ABS
- Referencias individuales: A1, B2, C10
- Rangos de celdas: A1:A10, B2:D5
- Operadores aritméticos: +, -, *, /, %, ^
- Evaluación segura basada en AST (sin eval inseguro) y detección de referencias circulares.
"""
import re
import ast
import operator
from typing import Set, Tuple, List, Optional

# Operadores aritméticos seguros
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def col_name_to_index(col_str: str) -> int:
    """Convierte nombre de columna (A, B, Z, AA) a índice 0-indexed."""
    col = 0
    for ch in col_str.upper():
        if 'A' <= ch <= 'Z':
            col = col * 26 + (ord(ch) - ord('A') + 1)
        else:
            return 0
    return max(0, col - 1)

def index_to_col_name(idx: int) -> str:
    """Convierte índice 0-indexed a letra de columna (A, B, Z, AA)."""
    idx += 1
    letters = []
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters.append(chr(65 + rem))
    return "".join(reversed(letters))

def cell_ref_to_coords(ref: str) -> Optional[Tuple[int, int]]:
    """Convierte referencia 'A1', 'B12' a tupla (fila, columna) 0-indexed."""
    m = re.match(r'^([A-Za-z]+)(\d+)$', ref.strip())
    if not m:
        return None
    col_str, row_str = m.groups()
    try:
        col = col_name_to_index(col_str)
        row = int(row_str) - 1
        return row, col
    except Exception:
        return None

def expand_range(range_str: str) -> List[Tuple[int, int]]:
    """Expande rango 'A1:B3' a lista de coordenadas [(r, c), ...]."""
    parts = range_str.split(':')
    if len(parts) != 2:
        c = cell_ref_to_coords(range_str)
        return [c] if c else []
    
    start = cell_ref_to_coords(parts[0])
    end = cell_ref_to_coords(parts[1])
    if not start or not end:
        return []
    
    r1, c1 = start
    r2, c2 = end
    min_r, max_r = min(r1, r2), max(r1, r2)
    min_c, max_c = min(c1, c2), max(c1, c2)
    
    coords = []
    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            coords.append((r, c))
    return coords

def safe_eval_ast(node):
    """Evalúa de forma segura un árbol AST conteniendo únicamente aritmética y literales."""
    if isinstance(node, ast.Expression):
        return safe_eval_ast(node.body)
    elif isinstance(node, ast.Constant): # Python 3.8+ literales numéricos
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Valor no numérico en expresión: {node.value}")
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](safe_eval_ast(node.operand))
        raise ValueError("Operador unario no soportado")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            left = safe_eval_ast(node.left)
            right = safe_eval_ast(node.right)
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("División por cero")
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError("Operador binario no soportado")
    else:
        raise ValueError(f"Expresión no permitida: {type(node).__name__}")


class FormulaEngine:
    """Motor de cálculo de fórmulas para hojas de cálculo de Cuaderno."""

    @classmethod
    def is_formula(cls, text: str) -> bool:
        if not text:
            return False
        t = text.strip()
        return t.startswith("=") and len(t) > 1

    @classmethod
    def get_cell_value(cls, table, r: int, c: int, visiting: Optional[Set[Tuple[int, int]]] = None) -> float:
        """Obtiene el valor numérico de una celda, resolviendo fórmulas si es necesario."""
        if r < 0 or r >= table.rowCount() or c < 0 or c >= table.columnCount():
            return 0.0
        
        item = table.item(r, c)
        if not item:
            return 0.0
        
        raw_text = item.text().strip()
        # Verificar si la celda tiene una fórmula guardada
        from PyQt6.QtCore import Qt
        formula = item.data(Qt.ItemDataRole.UserRole)
        if formula and str(formula).startswith("="):
            res_str = cls.evaluate(str(formula), table, visiting=visiting, current_cell=(r, c))
            try:
                return float(res_str.replace(',', '.'))
            except Exception:
                return 0.0
        
        if raw_text.startswith("="):
            res_str = cls.evaluate(raw_text, table, visiting=visiting, current_cell=(r, c))
            try:
                return float(res_str.replace(',', '.'))
            except Exception:
                return 0.0
        
        try:
            return float(raw_text.replace(',', '.').replace('$', '').replace('%', '').strip())
        except ValueError:
            return 0.0

    @classmethod
    def evaluate(cls, formula_text: str, table, visiting: Optional[Set[Tuple[int, int]]] = None, current_cell: Optional[Tuple[int, int]] = None) -> str:
        """
        Evalúa una fórmula de hoja de cálculo y devuelve el valor formateado como string.
        Ej: '=SUMA(A1:A5)', '=PROMEDIO(B1:B10)', '=A1+B1*2'
        """
        if not formula_text or not formula_text.startswith("="):
            return formula_text
        
        if visiting is None:
            visiting = set()
        
        if current_cell:
            if current_cell in visiting:
                return "#¡CIRCULAR!"
            visiting = visiting.copy()
            visiting.add(current_cell)

        expr = formula_text[1:].strip()
        if not expr:
            return ""

        # Reemplazar operador exponencial '^' por '**'
        expr = expr.replace('^', '**')

        try:
            # 1. Procesar funciones estadísticas de rangos
            expr = cls._process_range_functions(expr, table, visiting)

            # 2. Reemplazar referencias individuales de celdas (ej: A1, B12)
            expr = cls._replace_cell_references(expr, table, visiting)

            # 3. Evaluar expresión matemática de forma segura con AST
            parsed = ast.parse(expr, mode='eval')
            val = safe_eval_ast(parsed)

            if isinstance(val, float):
                if val.is_integer():
                    return str(int(val))
                return f"{val:.4f}".rstrip('0').rstrip('.')
            return str(val)

        except ZeroDivisionError:
            return "#¡DIV/0!"
        except Exception:
            return "#¡ERROR!"

    @classmethod
    def _process_range_functions(cls, expr: str, table, visiting: Set[Tuple[int, int]]) -> str:
        """Reemplaza funciones como SUMA(A1:A5) por sus valores numéricos calculados."""
        # Patrón para NOMBRE_FUNCION(ARGUMENTOS)
        func_pattern = re.compile(r'(?i)\b(SUMA|SUM|PROMEDIO|AVERAGE|MAX|MIN|CONTAR|COUNT|PRODUCTO|PRODUCT|ABS|REDONDEAR|ROUND|RAIZ|SQRT|POTENCIA|POWER|MEDIANA|MEDIAN)\s*\(([^)]+)\)')

        def replace_func(match):
            fn_name = match.group(1).upper()
            args_str = match.group(2)
            
            # Separar argumentos por comas o punto y coma
            args = [a.strip() for a in re.split(r'[,;]', args_str) if a.strip()]
            
            # Recolectar todos los valores numéricos de los argumentos (pueden ser rangos o constantes)
            numbers = []
            for arg in args:
                if ':' in arg:
                    coords = expand_range(arg)
                    for r, c in coords:
                        numbers.append(cls.get_cell_value(table, r, c, visiting))
                else:
                    c_coord = cell_ref_to_coords(arg)
                    if c_coord:
                        numbers.append(cls.get_cell_value(table, c_coord[0], c_coord[1], visiting))
                    else:
                        try:
                            numbers.append(float(arg.replace(',', '.')))
                        except ValueError:
                            pass

            if fn_name in ("SUMA", "SUM"):
                return str(sum(numbers))
            elif fn_name in ("PROMEDIO", "AVERAGE"):
                return str(sum(numbers) / len(numbers)) if numbers else "0"
            elif fn_name == "MAX":
                return str(max(numbers)) if numbers else "0"
            elif fn_name == "MIN":
                return str(min(numbers)) if numbers else "0"
            elif fn_name in ("CONTAR", "COUNT"):
                return str(len(numbers))
            elif fn_name in ("PRODUCTO", "PRODUCT"):
                p = 1.0
                for n in numbers:
                    p *= n
                return str(p)
            elif fn_name == "ABS":
                return str(abs(numbers[0])) if numbers else "0"
            elif fn_name in ("REDONDEAR", "ROUND"):
                dec = int(numbers[1]) if len(numbers) > 1 else 0
                return str(round(numbers[0], dec)) if numbers else "0"
            elif fn_name in ("RAIZ", "SQRT"):
                import math
                return str(math.sqrt(numbers[0])) if numbers and numbers[0] >= 0 else "0"
            elif fn_name in ("POTENCIA", "POWER"):
                import math
                return str(math.pow(numbers[0], numbers[1])) if len(numbers) >= 2 else "0"
            elif fn_name in ("MEDIANA", "MEDIAN"):
                import statistics
                return str(statistics.median(numbers)) if numbers else "0"
            return "0"

        # Resolver iterativamente funciones anidadas
        for _ in range(5):
            new_expr = func_pattern.sub(replace_func, expr)
            if new_expr == expr:
                break
            expr = new_expr
        return expr

    @classmethod
    def _replace_cell_references(cls, expr: str, table, visiting: Set[Tuple[int, int]]) -> str:
        """Reemplaza referencias individuales de celda como 'A1' o 'B12' por sus valores numéricos."""
        cell_pattern = re.compile(r'\b([A-Za-z]+)(\d+)\b')

        def replace_cell(m):
            ref = m.group(0)
            coords = cell_ref_to_coords(ref)
            if coords:
                val = cls.get_cell_value(table, coords[0], coords[1], visiting)
                return str(val)
            return ref

        return cell_pattern.sub(replace_cell, expr)


CATALOGO_FORMULAS = [
    {
        "nombre": "SUMA",
        "categoria": "Matemáticas & Aritmética",
        "sintaxis": "=SUMA(número1:númeroN)",
        "plantilla": "=SUMA({rango})",
        "descripcion": "Suma todos los números en un rango de celdas o lista de valores.",
        "ejemplo": "=SUMA(A1:A10)",
        "retorno": "Número (suma total)"
    },
    {
        "nombre": "PROMEDIO",
        "categoria": "Estadísticas",
        "sintaxis": "=PROMEDIO(número1:númeroN)",
        "plantilla": "=PROMEDIO({rango})",
        "descripcion": "Calcula el promedio (media aritmética) de los números en un rango o lista.",
        "ejemplo": "=PROMEDIO(B1:B5)",
        "retorno": "Número (media aritmética)"
    },
    {
        "nombre": "MAX",
        "categoria": "Estadísticas",
        "sintaxis": "=MAX(número1:númeroN)",
        "plantilla": "=MAX({rango})",
        "descripcion": "Devuelve el valor más grande de un conjunto de valores o rango.",
        "ejemplo": "=MAX(C1:C20)",
        "retorno": "Número (valor más alto)"
    },
    {
        "nombre": "MIN",
        "categoria": "Estadísticas",
        "sintaxis": "=MIN(número1:númeroN)",
        "plantilla": "=MIN({rango})",
        "descripcion": "Devuelve el valor mínimo de un conjunto de valores o rango.",
        "ejemplo": "=MIN(C1:C20)",
        "retorno": "Número (valor más bajo)"
    },
    {
        "nombre": "CONTAR",
        "categoria": "Estadísticas",
        "sintaxis": "=CONTAR(valor1:valorN)",
        "plantilla": "=CONTAR({rango})",
        "descripcion": "Cuenta la cantidad de celdas que contienen números en el rango especificado.",
        "ejemplo": "=CONTAR(A1:D10)",
        "retorno": "Número entero (conteo)"
    },
    {
        "nombre": "MEDIANA",
        "categoria": "Estadísticas",
        "sintaxis": "=MEDIANA(número1:númeroN)",
        "plantilla": "=MEDIANA({rango})",
        "descripcion": "Devuelve la mediana estadística de los números en el rango.",
        "ejemplo": "=MEDIANA(A1:A9)",
        "retorno": "Número (mediana)"
    },
    {
        "nombre": "PRODUCTO",
        "categoria": "Matemáticas & Aritmética",
        "sintaxis": "=PRODUCTO(número1:númeroN)",
        "plantilla": "=PRODUCTO({rango})",
        "descripcion": "Multiplica todos los números suministrados como argumentos.",
        "ejemplo": "=PRODUCTO(A1:A3)",
        "retorno": "Número (multiplicación)"
    },
    {
        "nombre": "REDONDEAR",
        "categoria": "Matemáticas & Aritmética",
        "sintaxis": "=REDONDEAR(número, núm_decimales)",
        "plantilla": "=REDONDEAR({celda}, 2)",
        "descripcion": "Redondea un número a una cantidad especificada de decimales.",
        "ejemplo": "=REDONDEAR(A1*1.16, 2)",
        "retorno": "Número redondeado"
    },
    {
        "nombre": "ABS",
        "categoria": "Matemáticas & Aritmética",
        "sintaxis": "=ABS(número)",
        "plantilla": "=ABS({celda})",
        "descripcion": "Devuelve el valor absoluto de un número (sin signo negativo).",
        "ejemplo": "=ABS(A1-B1)",
        "retorno": "Número absoluto positivo"
    },
    {
        "nombre": "RAIZ",
        "categoria": "Matemáticas & Aritmética",
        "sintaxis": "=RAIZ(número)",
        "plantilla": "=RAIZ({celda})",
        "descripcion": "Calcula la raíz cuadrada de un número positivo.",
        "ejemplo": "=RAIZ(A1)",
        "retorno": "Número (raíz cuadrada)"
    },
    {
        "nombre": "POTENCIA",
        "categoria": "Matemáticas & Aritmética",
        "sintaxis": "=POTENCIA(número, exponente)",
        "plantilla": "=POTENCIA({celda}, 2)",
        "descripcion": "Eleva el número dado a una potencia específica.",
        "ejemplo": "=POTENCIA(A1, 3)",
        "retorno": "Número exponencial"
    },
    {
        "nombre": "ARITMÉTICA DIRECTA",
        "categoria": "Aritmética Básica",
        "sintaxis": "=A1 + B1 * (C1 - D1)",
        "plantilla": "={celda} + 10",
        "descripcion": "Combinación libre de operadores (+, -, *, /, ^, %) con celdas y números.",
        "ejemplo": "=A1*1.21 + B2/2",
        "retorno": "Resultado aritmético evaluado"
    }
]
