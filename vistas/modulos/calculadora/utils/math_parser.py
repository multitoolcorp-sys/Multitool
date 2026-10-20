import math
import re

class MathParser:
    def __init__(self):
        self.operators = {
            '+': (1, 'L'), '-': (1, 'L'),
            '*': (2, 'L'), '/': (2, 'L'), '%': (2, 'L'),
            '^': (3, 'R')
        }
        self.functions = {
            'sin', 'cos', 'tan', 'log', 'ln', 'sqrt', 'cbrt', 'abs', 'fact', 'exp'
        }
        self.constants = {
            'pi': math.pi,
            'e': math.e
        }

    def evaluate(self, expression):
        try:
            tokens = self._tokenize(expression)
            rpn = self._shunting_yard(tokens)
            return self._eval_rpn(rpn)
        except ZeroDivisionError:
            raise ZeroDivisionError("División por cero")
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Sintaxis inválida: {e}")

    def _tokenize(self, expression):
        # 1. Limpieza y reemplazos de alias
        expr = expression.replace(',', '.')
        expr = expr.replace('π', 'pi')
        expr = expr.replace('√', 'sqrt')
        expr = expr.replace('∛', 'cbrt')
        expr = expr.replace('n!', 'fact')
        # Distinguir % de mod
        # Si el usuario escribe mod, es binario. Si escribe %, es porcentaje.
        # Ya que regrabamos 'mod' como '%' arriba por error, lo corregimos:
        # expr = expr.replace('mod', '%') # ELIMINADO
        
        # 3. Tokenización
        pattern = r'\d+\.?\d*|[a-zA-Z_][a-zA-Z0-9_]*|[\+\-\*\/\%\^\(\)]'
        raw_tokens = re.findall(pattern, expr)
        
        # 4. Manejo de menos unario e Inserción de multiplicación implícita
        processed = []
        for i, token in enumerate(raw_tokens):
            # Lógica de multiplicación implícita
            if i > 0:
                prev = processed[-1]
                # Modificamos: si el anterior es % o fact, también puede haber multiplicación implícita
                # (ej: 5% 3 -> 0.05 * 3)
                prev_es_valor = (self._is_number(prev) or prev in self.constants or 
                                 prev == ')' or prev == '%' or prev == 'fact')
                
                actual_es_inicio = (self._is_number(token) or token in self.constants or 
                                    token == '(' or token in self.functions)
                
                if prev_es_valor and actual_es_inicio:
                    processed.append('*')

            if token == '-' :
                if i == 0 or (i > 0 and raw_tokens[i-1] in '(+-*/%^'):
                    processed.append('u-')
                else:
                    processed.append('-')
            else:
                processed.append(token)
        return processed

    def _shunting_yard(self, tokens):
        output = []
        stack = []
        
        for token in tokens:
            if self._is_number(token):
                output.append(float(token))
            elif token in self.constants:
                output.append(self.constants[token])
            elif token in self.functions or token == '%' or token == 'fact':
                # % y fact actúan como funciones post-fijas
                if token in ['%', 'fact']:
                    output.append(token)
                else:
                    stack.append(token)
            elif token == '(':
                stack.append(token)
            elif token == ')':
                while stack and stack[-1] != '(':
                    output.append(stack.pop())
                if not stack:
                    raise Exception("Falta paréntesis de apertura '('")
                stack.pop() 
                if stack and stack[-1] in self.functions:
                    output.append(stack.pop())
            elif token in self.operators or token == 'u-':
                p1, a1 = self._get_op_info(token)
                while stack and stack[-1] != '(':
                    top = stack[-1]
                    if top in self.functions:
                        output.append(stack.pop())
                        continue
                    
                    p2, a2 = self._get_op_info(top)
                    if (a1 == 'L' and p1 <= p2) or (a1 == 'R' and p1 < p2):
                        output.append(stack.pop())
                    else:
                        break
                stack.append(token)
        
        while stack:
            if stack[-1] == '(':
                raise Exception("Faltan paréntesis de cierre ')'")
            output.append(stack.pop())
        return output

    def _get_op_info(self, op):
        if op == 'u-': return (4, 'R')
        return self.operators.get(op, (0, 'L'))

    def _eval_rpn(self, rpn):
        stack = []
        if not rpn: return 0
        
        for token in rpn:
            if isinstance(token, (int, float)):
                stack.append(token)
            elif token == 'u-':
                if not stack: raise Exception("Error de signo")
                a = stack.pop()
                stack.append(-a)
            elif token == '%':
                if not stack: raise Exception("Error de porcentaje")
                a = stack.pop()
                stack.append(a / 100)
            elif token in self.operators:
                if len(stack) < 2: raise Exception(f"Falta operando para '{token}'")
                b = stack.pop()
                a = stack.pop()
                if token == '+': stack.append(a + b)
                elif token == '-': stack.append(a - b)
                elif token == '*': stack.append(a * b)
                elif token == '/': 
                    if b == 0: raise ZeroDivisionError()
                    stack.append(a / b)
                elif token == '^': stack.append(math.pow(a, b))
                # elif token == '%': # Mapeado arriba como unario
            elif token in self.functions or token == 'fact':
                if not stack: raise Exception(f"Falta argumento")
                a = stack.pop()
                if token == 'sin': stack.append(math.sin(math.radians(a)))
                elif token == 'cos': stack.append(math.cos(math.radians(a)))
                elif token == 'tan': stack.append(math.tan(math.radians(a)))
                elif token == 'log': 
                    if a <= 0: raise ValueError("Logaritmo requiere base positiva")
                    stack.append(math.log10(a))
                elif token == 'ln': 
                    if a <= 0: raise ValueError("LN requiere valor positivo")
                    stack.append(math.log(a))
                elif token == 'sqrt': 
                    if a < 0: raise ValueError("Raíz negativa")
                    stack.append(math.sqrt(a))
                elif token == 'cbrt': stack.append(math.pow(a, 1/3))
                elif token == 'abs': stack.append(abs(a))
                elif token == 'fact': 
                    if a < 0 or not float(a).is_integer():
                         raise ValueError("Factorial solo para enteros ≥ 0")
                    if a > 170: raise ValueError("Número muy grande para factorial")
                    stack.append(math.factorial(int(a)))
                elif token == 'exp': stack.append(math.exp(a))
        
        if len(stack) != 1:
            raise Exception("Expresión mal formada")
        return stack[0]

    def _is_number(self, s):
        try:
            float(s)
            return True
        except:
            return False

    def format_number(self, n):
        if n is None: return "0"
        try:
            if isinstance(n, float) and n.is_integer():
                n = int(n)
            
            if isinstance(n, int):
                # Separador de miles punto
                return "{:,}".format(n).replace(",", ".")
            else:
                # Limitamos decimales para que no se sature la pantalla
                s = "{:.10g}".format(n) 
                if "." in s:
                    entero, decimal = s.split(".")
                    entero_f = "{:,}".format(int(entero)).replace(",", ".")
                    return f"{entero_f},{decimal}"
                return s.replace(".", ",")
        except:
            return str(n)

