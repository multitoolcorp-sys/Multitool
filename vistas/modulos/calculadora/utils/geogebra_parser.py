"""
geogebra_parser.py - Analizador Sintáctico GeoGebra para Ecuaciones, Multiplicación Implícita y Cálculo de Propiedades
"""
import re
import math


class GeoGebraParser:
    """Parser especializado en notación estilo GeoGebra f(x) = mx + b y cálculo de propiedades analíticas"""
    
    @staticmethod
    def parse_function_input(raw_str):
        """Extrae el nombre de la función y la expresión matemática pura"""
        s = raw_str.strip()
        if not s:
            return "f", "0"

        # Buscar notación f(x) = ..., g(x) = ..., y = ...
        match = re.match(r'^\s*([a-zA-Z]+)\s*\(([a-zA-Z]+)\)\s*=\s*(.+)$', s)
        if match:
            nombre = match.group(1)
            var = match.group(2)
            body = match.group(3)
            return nombre, body

        match_y = re.match(r'^\s*y\s*=\s*(.+)$', s, re.IGNORECASE)
        if match_y:
            return "y", match_y.group(1)

        return "f", s

    @staticmethod
    def fix_implicit_multiplication(expr_str, var_name="x"):
        """Transforma sintaxis matemática natural a expresiones evaluables en Python
        Ejemplos:
          2x -> 2*x
          2 sin(3t) -> 2*sin(3*t)
          x sin(1/x) -> x*sin(1/x)
          3(x+1) -> 3*(x+1)
          x^2 -> x**2
        """
        s = expr_str.strip()
        if not s:
            return "0"

        # Reemplazar potencias ^ por **
        s = s.replace("^", "**")
        s = s.replace("sen", "sin")
        s = s.replace("ln(", "log(")

        # Multiplicación implícita entre número/variable y funciones (ej: 2 sin -> 2*sin, x sin -> x*sin)
        s = re.sub(r'(\d+(?:\.\d+)?|[a-zA-Z])\s+(sin|cos|tan|sqrt|abs|exp|log)', r'\1*\2', s)

        # Multiplicación implícita: Número seguido de variable (ej: 2x -> 2*x, 3.5x -> 3.5*x, 3t -> 3*t)
        s = re.sub(r'(\d+(?:\.\d+)?)\s*([a-zA-Z])', r'\1*\2', s)

        # Multiplicación implícita: Variable seguida de número u otra variable (ej: x x -> x*x)
        s = re.sub(r'([a-zA-Z])\s+([a-zA-Z])', r'\1*\2', s)

        # Multiplicación implícita: Número seguido de paréntesis (ej: 3(x+1) -> 3*(x+1))
        s = re.sub(r'(\d+(?:\.\d+)?)\s*\(', r'\1*(', s)

        # Multiplicación implícita: Paréntesis cerrado seguido de variable o paréntesis (ej: (x+1)x -> (x+1)*x)
        s = re.sub(r'\)\s*([a-zA-Z\(])', r')*\1', s)

        # Restablecer nombres de funciones protegidos
        funciones = ["sin", "cos", "tan", "sqrt", "abs", "exp", "log"]
        for f in funciones:
            s = s.replace(f + "*(", f + "(")

        return s

    @classmethod
    def parse_curve_input(cls, raw_str):
        """Parsea notación de curvas paramétricas: Curve(x(t), y(t), t, t_min, t_max) o Curva(...)"""
        s = raw_str.strip()
        match = re.match(r'^\s*(?:Curve|Curva)\s*\(\s*(.+?)\s*,\s*(.+?)\s*,\s*([a-zA-Z])\s*,\s*(.+?)\s*,\s*(.+?)\s*\)\s*$', s, re.IGNORECASE)
        if match:
            return {
                "tipo": "curva",
                "expr_x": cls.fix_implicit_multiplication(match.group(1), match.group(3)),
                "expr_y": cls.fix_implicit_multiplication(match.group(2), match.group(3)),
                "var": match.group(3),
                "t_min": float(cls.fix_implicit_multiplication(match.group(4))),
                "t_max": float(cls.fix_implicit_multiplication(match.group(5)))
            }
        return None

    @classmethod
    def evaluar(cls, expr_str, var_val, var_name="x"):
        """Evalúa una expresión limpia para un valor dado con manejo seguro de divisiones por cero"""
        clean_expr = cls.fix_implicit_multiplication(expr_str, var_name)
        allowed_globals = {
            var_name: var_val,
            "x": var_val,
            "t": var_val,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "sqrt": math.sqrt,
            "abs": abs,
            "exp": math.exp,
            "log": math.log,
            "pi": math.pi,
            "e": math.e
        }
        try:
            return float(eval(clean_expr, {"__builtins__": None}, allowed_globals))
        except ZeroDivisionError:
            # Para expresiones como x*sin(1/x) cuando x=0, el límite es 0
            if abs(var_val) < 1e-7:
                return 0.0
            raise

    @classmethod
    def calcular_propiedades(cls, expr_str):
        """Calcula propiedades analíticas: Intersección con Y f(0) y Ceros/Raíces f(x) = 0"""
        nombre, body = cls.parse_function_input(expr_str)
        clean = cls.fix_implicit_multiplication(body)

        propiedades = {
            "nombre": nombre,
            "expresion_limpia": clean,
            "interseccion_y": None,
            "raices": []
        }

        # 1. Intersección con Y (f(0))
        try:
            val_y = cls.evaluar(clean, 0.0)
            propiedades["interseccion_y"] = round(val_y, 4)
        except Exception:
            propiedades["interseccion_y"] = "Indefinido"

        # 2. Búsqueda de Raíces/Ceros f(x) = 0 por cambio de signo (Bolzano / Bisección)
        raices_encontradas = []
        x_start, x_end, step = -20.0, 20.0, 0.1
        curr_x = x_start
        
        last_val = None
        try:
            last_val = cls.evaluar(clean, curr_x)
        except Exception:
            pass

        while curr_x <= x_end:
            next_x = curr_x + step
            try:
                val = cls.evaluar(clean, next_x)
                if abs(val) < 1e-4:
                    r_round = round(next_x, 3)
                    if r_round not in raices_encontradas:
                        raices_encontradas.append(r_round)
                elif last_val is not None and (last_val * val < 0):
                    # Bisección rápida
                    r = cls._biseccion(clean, curr_x, next_x)
                    if r is not None:
                        r_round = round(r, 3)
                        if r_round not in raices_encontradas:
                            raices_encontradas.append(r_round)
                last_val = val
            except Exception:
                last_val = None
            curr_x = next_x

        propiedades["raices"] = raices_encontradas[:5] # Máximo 5 raíces representativas
        return propiedades

    @classmethod
    def _biseccion(cls, clean_expr, a, b, tol=1e-5, max_iter=20):
        try:
            fa = cls.evaluar(clean_expr, a)
            fb = cls.evaluar(clean_expr, b)
            if fa * fb > 0: return None
            for _ in range(max_iter):
                c = (a + b) / 2.0
                fc = cls.evaluar(clean_expr, c)
                if abs(fc) < tol or (b - a) / 2.0 < tol:
                    return c
                if fa * fc < 0:
                    b = c; fb = fc
                else:
                    a = c; fa = fc
            return (a + b) / 2.0
        except Exception:
            return None

    @classmethod
    def generar_tabla_valores(cls, expr_str, x_min=-5, x_max=5, paso=1):
        """Genera una lista de puntos de coordenadas (x, y)"""
        nombre, body = cls.parse_function_input(expr_str)
        clean = cls.fix_implicit_multiplication(body)
        puntos = []
        
        curr = float(x_min)
        while curr <= x_max + 1e-9:
            try:
                y_val = cls.evaluar(clean, curr)
                puntos.append((round(curr, 2), round(y_val, 4)))
            except Exception:
                puntos.append((round(curr, 2), "Indefinido"))
            curr += paso
        return puntos
