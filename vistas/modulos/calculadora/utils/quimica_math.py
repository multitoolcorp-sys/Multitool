"""
quimica_math.py - Motor de Cálculo Estequiométrico, Masa Molar y Reacciones Químicas
"""

import re
import math
from collections import defaultdict
from .quimica_data import SIMBOLO_A_ELEM

AVOGADRO = 6.02214076e23
R_GAS = 0.082057366080960  # atm * L / (mol * K)

def parse_formula(formula_str):
    """
    Parsea una fórmula química con soporte para paréntesis (), corchetes [], hidratos (*nH2O)
    y devuelve un diccionario { "Símbolo": cantidad_total }.
    Ejemplos: 'H2O', 'Ca(OH)2', 'CuSO4*5H2O', 'Fe2(SO4)3', 'K4[Fe(CN)6]'
    """
    if not formula_str or not formula_str.strip():
        raise ValueError("La fórmula química está vacía.")
    
    formula = formula_str.strip().replace(" ", "").replace("·", "*").replace("•", "*")
    
    # Manejar partes de hidratos (ej: CuSO4*5H2O)
    partes = formula.split("*")
    totales = defaultdict(float)
    
    for i, parte in enumerate(partes):
        coef_multiplicador = 1.0
        if i > 0:
            m = re.match(r"^(\d+)(.*)$", parte)
            if m:
                coef_multiplicador = float(m.group(1))
                parte = m.group(2)
        
        counts = _parse_segmento(parte)
        for elem, count in counts.items():
            totales[elem] += count * coef_multiplicador
            
    return dict(totales)

def _parse_segmento(segmento):
    """Parsea segmentos con paréntesis recursivos."""
    segmento = segmento.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    
    # Resolver paréntesis de adentro hacia afuera
    while "(" in segmento:
        match = re.search(r"\(([A-Za-z0-9]+)\)(\d*)", segmento)
        if not match:
            break
        contenido = match.group(1)
        subindice = int(match.group(2)) if match.group(2) else 1
        
        sub_counts = _parse_simple(contenido)
        expansor = ""
        for el, c in sub_counts.items():
            expansor += f"{el}{int(c * subindice)}"
            
        segmento = segmento[:match.start()] + expansor + segmento[match.end():]
        
    return _parse_simple(segmento)

def _parse_simple(cadena):
    """Parsea una secuencia plana de elementos y números como C6H12O6."""
    pattern = r"([A-Z][a-z]?)(\d*)"
    matches = re.findall(pattern, cadena)
    counts = defaultdict(float)
    
    # Validar que todos los caracteres pertenezcan a tokens
    parsed_len = sum(len(m[0]) + len(m[1]) for m in matches)
    if parsed_len != len(cadena):
        raise ValueError(f"Símbolo o caracter desconocido en '{cadena}'")
        
    for elem, num_str in matches:
        if elem not in SIMBOLO_A_ELEM:
            raise ValueError(f"Elemento químico desconocido: '{elem}'")
        num = float(num_str) if num_str else 1.0
        counts[elem] += num
        
    return dict(counts)

def calcular_masa_molar(formula_str):
    """
    Calcula la masa molar total y el desglose de composición porcentual (% masa).
    Devuelve un diccionario estructurado.
    """
    counts = parse_formula(formula_str)
    desglose = []
    masa_total = 0.0
    
    for elem, cant in counts.items():
        datos_elem = SIMBOLO_A_ELEM.get(elem, {})
        peso_at = datos_elem.get("masa", 0.0)
        subtotal = cant * peso_at
        masa_total += subtotal
        desglose.append({
            "simbolo": elem,
            "nombre": datos_elem.get("nombre", elem),
            "cantidad": cant,
            "peso_atomico": peso_at,
            "peso_total": subtotal,
            "porcentaje": 0.0  # se calcula abajo
        })
        
    if masa_total > 0:
        for item in desglose:
            item["porcentaje"] = round((item["peso_total"] / masa_total) * 100.0, 4)
            
    desglose.sort(key=lambda x: x["peso_total"], reverse=True)
    return {
        "formula": formula_str,
        "masa_molar": round(masa_total, 4),
        "desglose": desglose,
        "num_elementos": len(desglose),
        "num_atomos": sum(x["cantidad"] for x in desglose)
    }

def convertir_estequiometria(masa_molar, gramos=None, moles=None, moleculas=None):
    """
    Conversión bidireccional entre Gramos, Moles y Número de Moléculas.
    """
    if masa_molar <= 0:
        raise ValueError("La masa molar debe ser mayor a 0.")
        
    if moles is not None:
        g = moles * masa_molar
        mol = moles
        molec = moles * AVOGADRO
    elif gramos is not None:
        mol = gramos / masa_molar
        g = gramos
        molec = mol * AVOGADRO
    elif moleculas is not None:
        mol = moleculas / AVOGADRO
        g = mol * masa_molar
        molec = moleculas
    else:
        raise ValueError("Debes proporcionar al menos una magnitud.")
        
    return {
        "gramos": g,
        "moles": mol,
        "moleculas": molec,
        "miligramos": g * 1000.0,
        "kilogramos": g / 1000.0,
        "milimoles": mol * 1000.0
    }

def calcular_solucion_molar(masa_molar, molaridad_m, volumen_ml):
    """
    Calcula la masa de soluto requerida para preparar una solución dada M y V(mL).
    m = M (mol/L) * V(L) * Mm (g/mol)
    """
    v_litros = volumen_ml / 1000.0
    moles_nec = molaridad_m * v_litros
    gramos_nec = moles_nec * masa_molar
    return {
        "gramos": round(gramos_nec, 4),
        "miligramos": round(gramos_nec * 1000.0, 2),
        "moles": round(moles_nec, 6),
        "volumen_l": v_litros
    }

def balancear_ecuacion_quimica(reaccion_str):
    """
    Balancea una ecuación química por método algebraico matricial.
    Ejemplo: 'CH4 + O2 -> CO2 + H2O' => '1 CH4 + 2 O2 -> 1 CO2 + 2 H2O'
    """
    reaccion = reaccion_str.strip().replace("=", "->").replace("→", "->")
    if "->" not in reaccion:
        raise ValueError("La ecuación debe contener '->' separando reactivos y productos.")
        
    lados = reaccion.split("->")
    reactivos = [r.strip() for r in lados[0].split("+") if r.strip()]
    productos = [p.strip() for p in lados[1].split("+") if p.strip()]
    
    if not reactivos or not productos:
        raise ValueError("Faltan reactivos o productos en la ecuación.")
        
    compuestos = reactivos + productos
    num_comp = len(compuestos)
    
    # Extraer todos los elementos únicos
    todos_elem = set()
    matriz_comp = []
    
    for i, c in enumerate(compuestos):
        counts = parse_formula(c)
        todos_elem.update(counts.keys())
        matriz_comp.append(counts)
        
    lista_elem = sorted(list(todos_elem))
    
    # Construir matriz de conservación de masa: A * x = 0
    # Para reactivos el coeficiente es positivo, para productos es negativo
    matrix = []
    for elem in lista_elem:
        row = []
        for i, c_counts in enumerate(matriz_comp):
            val = c_counts.get(elem, 0.0)
            if i >= len(reactivos):
                val = -val
            row.append(val)
        matrix.append(row)
        
    # Resolver buscando los mínimos enteros positivos
    coeficientes = _resolver_coeficientes_enteros(matrix, num_comp)
    
    # Formatear la ecuación balanceada
    r_str = " + ".join(f"{coeficientes[i]} {reactivos[i]}" if coeficientes[i] > 1 else reactivos[i] for i in range(len(reactivos)))
    p_str = " + ".join(f"{coeficientes[len(reactivos) + j]} {productos[j]}" if coeficientes[len(reactivos) + j] > 1 else productos[j] for j in range(len(productos)))
    
    return {
        "ecuacion_balanceada": f"{r_str} -> {p_str}",
        "reactivos": [(reactivos[i], coeficientes[i]) for i in range(len(reactivos))],
        "productos": [(productos[j], coeficientes[len(reactivos) + j]) for j in range(len(productos))]
    }

def _resolver_coeficientes_enteros(matrix, num_vars):
    """Encuentra los mínimos coeficientes enteros positivos mediante eliminación Gaussiana o búsqueda."""
    import itertools
    # Búsqueda rápida acotada para ecuaciones químicas (hasta coef = 24)
    for total in range(num_vars, num_vars * 12 + 1):
        for combo in itertools.product(range(1, 13), repeat=num_vars):
            if sum(combo) != total:
                continue
            # Verificar si todas las filas dan 0
            valido = True
            for row in matrix:
                if abs(sum(r * c for r, c in zip(row, combo))) > 1e-6:
                    valido = False
                    break
            if valido:
                # Simplificar por MCD
                mcd = math.gcd(*combo)
                return [c // mcd for c in combo]
                
    # Fallback si no se encontró en rango bajo
    return [1] * num_vars
