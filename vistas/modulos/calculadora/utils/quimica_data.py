"""
quimica_data.py - Base de Datos Química Completa para MultiTool
Contiene los 118 elementos de la tabla periódica con propiedades físicas/químicas,
colores estándar CPK, configuración electrónica, masas atómicas y recetas moleculares.
"""

# Categorías químicas y sus colores temáticos modernos
CATEGORIAS = {
    "alcalino": {"nombre": "Metales Alcalinos", "color": "#E53935", "bg": "rgba(229, 57, 53, 0.25)"},
    "alcalinoterreo": {"nombre": "Alcalinotérreos", "color": "#FB8C00", "bg": "rgba(251, 140, 0, 0.25)"},
    "transicion": {"nombre": "Metales de Transición", "color": "#FDD835", "bg": "rgba(253, 216, 53, 0.25)"},
    "lantanido": {"nombre": "Lantánidos", "color": "#8E24AA", "bg": "rgba(142, 36, 170, 0.25)"},
    "actinido": {"nombre": "Actínidos", "color": "#D81B60", "bg": "rgba(216, 27, 96, 0.25)"},
    "post_transicion": {"nombre": "Metales del Bloque p", "color": "#1E88E5", "bg": "rgba(30, 136, 229, 0.25)"},
    "metaloide": {"nombre": "Metaloides", "color": "#00ACC1", "bg": "rgba(0, 172, 193, 0.25)"},
    "no_metal": {"nombre": "No Metales Reactivos", "color": "#43A047", "bg": "rgba(67, 160, 71, 0.25)"},
    "halogeno": {"nombre": "Halógenos", "color": "#7CB342", "bg": "rgba(124, 179, 66, 0.25)"},
    "gas_noble": {"nombre": "Gases Nobles", "color": "#3949AB", "bg": "rgba(57, 73, 171, 0.25)"},
    "desconocido": {"nombre": "Propiedades Desconocidas", "color": "#757575", "bg": "rgba(117, 117, 117, 0.25)"}
}

# Colores estándar CPK para elementos en gráficos moleculares
CPK_COLORS = {
    "H": "#FFFFFF", "C": "#333333", "N": "#2196F3", "O": "#F44336", "F": "#4CAF50",
    "Cl": "#8BC34A", "Br": "#795548", "I": "#9C27B0", "He": "#00BCD4", "Ne": "#00BCD4",
    "Ar": "#00BCD4", "Kr": "#00BCD4", "Xe": "#00BCD4", "P": "#FF9800", "S": "#FFEB3B",
    "B": "#FFC107", "Li": "#9C27B0", "Na": "#9C27B0", "K": "#9C27B0", "Rb": "#9C27B0",
    "Cs": "#9C27B0", "Be": "#4CAF50", "Mg": "#4CAF50", "Ca": "#4CAF50", "Sr": "#4CAF50",
    "Ba": "#4CAF50", "Fe": "#E65100", "Cu": "#C2185B", "Zn": "#607D8B", "Ag": "#B0BEC5",
    "Au": "#FFD700", "Pt": "#CFD8DC", "Al": "#90A4AE", "Si": "#78909C", "Ti": "#757575"
}

# Base de datos completa de los 118 Elementos (Z, Símbolo, Nombre, Masa, Periodo, Grupo, Categoría, Estado a 20°C, Electronegatividad, Configuración)
ELEMENTOS = {
    1: {"simbolo": "H", "nombre": "Hidrógeno", "masa": 1.008, "periodo": 1, "grupo": 1, "cat": "no_metal", "estado": "Gas", "electroneg": 2.20, "config": "1s¹", "ox": "+1, -1"},
    2: {"simbolo": "He", "nombre": "Helio", "masa": 4.0026, "periodo": 1, "grupo": 18, "cat": "gas_noble", "estado": "Gas", "electroneg": None, "config": "1s²", "ox": "0"},
    3: {"simbolo": "Li", "nombre": "Litio", "masa": 6.94, "periodo": 2, "grupo": 1, "cat": "alcalino", "estado": "Sólido", "electroneg": 0.98, "config": "[He] 2s¹", "ox": "+1"},
    4: {"simbolo": "Be", "nombre": "Berilio", "masa": 9.0122, "periodo": 2, "grupo": 2, "cat": "alcalinoterreo", "estado": "Sólido", "electroneg": 1.57, "config": "[He] 2s²", "ox": "+2"},
    5: {"simbolo": "B", "nombre": "Boro", "masa": 10.81, "periodo": 2, "grupo": 13, "cat": "metaloide", "estado": "Sólido", "electroneg": 2.04, "config": "[He] 2s² 2p¹", "ox": "+3"},
    6: {"simbolo": "C", "nombre": "Carbono", "masa": 12.011, "periodo": 2, "grupo": 14, "cat": "no_metal", "estado": "Sólido", "electroneg": 2.55, "config": "[He] 2s² 2p²", "ox": "+4, +2, -4"},
    7: {"simbolo": "N", "nombre": "Nitrógeno", "masa": 14.007, "periodo": 2, "grupo": 15, "cat": "no_metal", "estado": "Gas", "electroneg": 3.04, "config": "[He] 2s² 2p³", "ox": "+5, +4, +3, +2, -3"},
    8: {"simbolo": "O", "nombre": "Oxígeno", "masa": 15.999, "periodo": 2, "grupo": 16, "cat": "no_metal", "estado": "Gas", "electroneg": 3.44, "config": "[He] 2s² 2p⁴", "ox": "-2, -1"},
    9: {"simbolo": "F", "nombre": "Flúor", "masa": 18.998, "periodo": 2, "grupo": 17, "cat": "halogeno", "estado": "Gas", "electroneg": 3.98, "config": "[He] 2s² 2p⁵", "ox": "-1"},
    10: {"simbolo": "Ne", "nombre": "Neón", "masa": 20.180, "periodo": 2, "grupo": 18, "cat": "gas_noble", "estado": "Gas", "electroneg": None, "config": "[He] 2s² 2p⁶", "ox": "0"},
    11: {"simbolo": "Na", "nombre": "Sodio", "masa": 22.990, "periodo": 3, "grupo": 1, "cat": "alcalino", "estado": "Sólido", "electroneg": 0.93, "config": "[Ne] 3s¹", "ox": "+1"},
    12: {"simbolo": "Mg", "nombre": "Magnesio", "masa": 24.305, "periodo": 3, "grupo": 2, "cat": "alcalinoterreo", "estado": "Sólido", "electroneg": 1.31, "config": "[Ne] 3s²", "ox": "+2"},
    13: {"simbolo": "Al", "nombre": "Aluminio", "masa": 26.982, "periodo": 3, "grupo": 13, "cat": "post_transicion", "estado": "Sólido", "electroneg": 1.61, "config": "[Ne] 3s² 3p¹", "ox": "+3"},
    14: {"simbolo": "Si", "nombre": "Silicio", "masa": 28.085, "periodo": 3, "grupo": 14, "cat": "metaloide", "estado": "Sólido", "electroneg": 1.90, "config": "[Ne] 3s² 3p²", "ox": "+4, -4"},
    15: {"simbolo": "P", "nombre": "Fósforo", "masa": 30.974, "periodo": 3, "grupo": 15, "cat": "no_metal", "estado": "Sólido", "electroneg": 2.19, "config": "[Ne] 3s² 3p³", "ox": "+5, +3, -3"},
    16: {"simbolo": "S", "nombre": "Azufre", "masa": 32.06, "periodo": 3, "grupo": 16, "cat": "no_metal", "estado": "Sólido", "electroneg": 2.58, "config": "[Ne] 3s² 3p⁴", "ox": "+6, +4, -2"},
    17: {"simbolo": "Cl", "nombre": "Cloro", "masa": 35.45, "periodo": 3, "grupo": 17, "cat": "halogeno", "estado": "Gas", "electroneg": 3.16, "config": "[Ne] 3s² 3p⁵", "ox": "+7, +5, +3, +1, -1"},
    18: {"simbolo": "Ar", "nombre": "Argón", "masa": 39.948, "periodo": 3, "grupo": 18, "cat": "gas_noble", "estado": "Gas", "electroneg": None, "config": "[Ne] 3s² 3p⁶", "ox": "0"},
    19: {"simbolo": "K", "nombre": "Potasio", "masa": 39.098, "periodo": 4, "grupo": 1, "cat": "alcalino", "estado": "Sólido", "electroneg": 0.82, "config": "[Ar] 4s¹", "ox": "+1"},
    20: {"simbolo": "Ca", "nombre": "Calcio", "masa": 40.078, "periodo": 4, "grupo": 2, "cat": "alcalinoterreo", "estado": "Sólido", "electroneg": 1.00, "config": "[Ar] 4s²", "ox": "+2"},
    21: {"simbolo": "Sc", "nombre": "Escandio", "masa": 44.956, "periodo": 4, "grupo": 3, "cat": "transicion", "estado": "Sólido", "electroneg": 1.36, "config": "[Ar] 3d¹ 4s²", "ox": "+3"},
    22: {"simbolo": "Ti", "nombre": "Titanio", "masa": 47.867, "periodo": 4, "grupo": 4, "cat": "transicion", "estado": "Sólido", "electroneg": 1.54, "config": "[Ar] 3d² 4s²", "ox": "+4, +3, +2"},
    23: {"simbolo": "V", "nombre": "Vanadio", "masa": 50.942, "periodo": 4, "grupo": 5, "cat": "transicion", "estado": "Sólido", "electroneg": 1.63, "config": "[Ar] 3d³ 4s²", "ox": "+5, +4, +3, +2"},
    24: {"simbolo": "Cr", "nombre": "Cromo", "masa": 51.996, "periodo": 4, "grupo": 6, "cat": "transicion", "estado": "Sólido", "electroneg": 1.66, "config": "[Ar] 3d⁵ 4s¹", "ox": "+6, +3, +2"},
    25: {"simbolo": "Mn", "nombre": "Manganeso", "masa": 54.938, "periodo": 4, "grupo": 7, "cat": "transicion", "estado": "Sólido", "electroneg": 1.55, "config": "[Ar] 3d⁵ 4s²", "ox": "+7, +6, +4, +3, +2"},
    26: {"simbolo": "Fe", "nombre": "Hierro", "masa": 55.845, "periodo": 4, "grupo": 8, "cat": "transicion", "estado": "Sólido", "electroneg": 1.83, "config": "[Ar] 3d⁶ 4s²", "ox": "+3, +2"},
    27: {"simbolo": "Co", "nombre": "Cobalto", "masa": 58.933, "periodo": 4, "grupo": 9, "cat": "transicion", "estado": "Sólido", "electroneg": 1.88, "config": "[Ar] 3d⁷ 4s²", "ox": "+3, +2"},
    28: {"simbolo": "Ni", "nombre": "Níquel", "masa": 58.693, "periodo": 4, "grupo": 10, "cat": "transicion", "estado": "Sólido", "electroneg": 1.91, "config": "[Ar] 3d⁸ 4s²", "ox": "+3, +2"},
    29: {"simbolo": "Cu", "nombre": "Cobre", "masa": 63.546, "periodo": 4, "grupo": 11, "cat": "transicion", "estado": "Sólido", "electroneg": 1.90, "config": "[Ar] 3d¹⁰ 4s¹", "ox": "+2, +1"},
    30: {"simbolo": "Zn", "nombre": "Zinc", "masa": 65.38, "periodo": 4, "grupo": 12, "cat": "transicion", "estado": "Sólido", "electroneg": 1.65, "config": "[Ar] 3d¹⁰ 4s²", "ox": "+2"},
    31: {"simbolo": "Ga", "nombre": "Galio", "masa": 69.723, "periodo": 4, "grupo": 13, "cat": "post_transicion", "estado": "Sólido", "electroneg": 1.81, "config": "[Ar] 3d¹⁰ 4s² 4p¹", "ox": "+3"},
    32: {"simbolo": "Ge", "nombre": "Germanio", "masa": 72.630, "periodo": 4, "grupo": 14, "cat": "metaloide", "estado": "Sólido", "electroneg": 2.01, "config": "[Ar] 3d¹⁰ 4s² 4p²", "ox": "+4, +2"},
    33: {"simbolo": "As", "nombre": "Arsénico", "masa": 74.922, "periodo": 4, "grupo": 15, "cat": "metaloide", "estado": "Sólido", "electroneg": 2.18, "config": "[Ar] 3d¹⁰ 4s² 4p³", "ox": "+5, +3, -3"},
    34: {"simbolo": "Se", "nombre": "Selenio", "masa": 78.971, "periodo": 4, "grupo": 16, "cat": "no_metal", "estado": "Sólido", "electroneg": 2.55, "config": "[Ar] 3d¹⁰ 4s² 4p⁴", "ox": "+6, +4, -2"},
    35: {"simbolo": "Br", "nombre": "Bromo", "masa": 79.904, "periodo": 4, "grupo": 17, "cat": "halogeno", "estado": "Líquido", "electroneg": 2.96, "config": "[Ar] 3d¹⁰ 4s² 4p⁵", "ox": "+5, +3, +1, -1"},
    36: {"simbolo": "Kr", "nombre": "Kriptón", "masa": 83.798, "periodo": 4, "grupo": 18, "cat": "gas_noble", "estado": "Gas", "electroneg": 3.00, "config": "[Ar] 3d¹⁰ 4s² 4p⁶", "ox": "+2"},
    37: {"simbolo": "Rb", "nombre": "Rubidio", "masa": 85.468, "periodo": 5, "grupo": 1, "cat": "alcalino", "estado": "Sólido", "electroneg": 0.82, "config": "[Kr] 5s¹", "ox": "+1"},
    38: {"simbolo": "Sr", "nombre": "Estroncio", "masa": 87.62, "periodo": 5, "grupo": 2, "cat": "alcalinoterreo", "estado": "Sólido", "electroneg": 0.95, "config": "[Kr] 5s²", "ox": "+2"},
    39: {"simbolo": "Y", "nombre": "Itrio", "masa": 88.906, "periodo": 5, "grupo": 3, "cat": "transicion", "estado": "Sólido", "electroneg": 1.22, "config": "[Kr] 4d¹ 5s²", "ox": "+3"},
    40: {"simbolo": "Zr", "nombre": "Circonio", "masa": 91.224, "periodo": 5, "grupo": 4, "cat": "transicion", "estado": "Sólido", "electroneg": 1.33, "config": "[Kr] 4d² 5s²", "ox": "+4"},
    41: {"simbolo": "Nb", "nombre": "Niobio", "masa": 92.906, "periodo": 5, "grupo": 5, "cat": "transicion", "estado": "Sólido", "electroneg": 1.6, "config": "[Kr] 4d⁴ 5s¹", "ox": "+5, +3"},
    42: {"simbolo": "Mo", "nombre": "Molibdeno", "masa": 95.95, "periodo": 5, "grupo": 6, "cat": "transicion", "estado": "Sólido", "electroneg": 2.16, "config": "[Kr] 4d⁵ 5s¹", "ox": "+6, +4, +3"},
    43: {"simbolo": "Tc", "nombre": "Tecnecio", "masa": 98.0, "periodo": 5, "grupo": 7, "cat": "transicion", "estado": "Sólido", "electroneg": 1.9, "config": "[Kr] 4d⁵ 5s²", "ox": "+7, +4"},
    44: {"simbolo": "Ru", "nombre": "Rutenio", "masa": 101.07, "periodo": 5, "grupo": 8, "cat": "transicion", "estado": "Sólido", "electroneg": 2.2, "config": "[Kr] 4d⁷ 5s¹", "ox": "+4, +3, +2"},
    45: {"simbolo": "Rh", "nombre": "Rodio", "masa": 102.91, "periodo": 5, "grupo": 9, "cat": "transicion", "estado": "Sólido", "electroneg": 2.28, "config": "[Kr] 4d⁸ 5s¹", "ox": "+3"},
    46: {"simbolo": "Pd", "nombre": "Paladio", "masa": 106.42, "periodo": 5, "grupo": 10, "cat": "transicion", "estado": "Sólido", "electroneg": 2.20, "config": "[Kr] 4d¹⁰", "ox": "+4, +2"},
    47: {"simbolo": "Ag", "nombre": "Plata", "masa": 107.87, "periodo": 5, "grupo": 11, "cat": "transicion", "estado": "Sólido", "electroneg": 1.93, "config": "[Kr] 4d¹⁰ 5s¹", "ox": "+1"},
    48: {"simbolo": "Cd", "nombre": "Cadmio", "masa": 112.41, "periodo": 5, "grupo": 12, "cat": "transicion", "estado": "Sólido", "electroneg": 1.69, "config": "[Kr] 4d¹⁰ 5s²", "ox": "+2"},
    49: {"simbolo": "In", "nombre": "Indio", "masa": 114.82, "periodo": 5, "grupo": 13, "cat": "post_transicion", "estado": "Sólido", "electroneg": 1.78, "config": "[Kr] 4d¹⁰ 5s² 5p¹", "ox": "+3"},
    50: {"simbolo": "Sn", "nombre": "Estaño", "masa": 118.71, "periodo": 5, "grupo": 14, "cat": "post_transicion", "estado": "Sólido", "electroneg": 1.96, "config": "[Kr] 4d¹⁰ 5s² 5p²", "ox": "+4, +2"},
    51: {"simbolo": "Sb", "nombre": "Antimonio", "masa": 121.76, "periodo": 5, "grupo": 15, "cat": "metaloide", "estado": "Sólido", "electroneg": 2.05, "config": "[Kr] 4d¹⁰ 5s² 5p³", "ox": "+5, +3, -3"},
    52: {"simbolo": "Te", "nombre": "Telurio", "masa": 127.60, "periodo": 5, "grupo": 16, "cat": "metaloide", "estado": "Sólido", "electroneg": 2.1, "config": "[Kr] 4d¹⁰ 5s² 5p⁴", "ox": "+6, +4, -2"},
    53: {"simbolo": "I", "nombre": "Yodo", "masa": 126.90, "periodo": 5, "grupo": 17, "cat": "halogeno", "estado": "Sólido", "electroneg": 2.66, "config": "[Kr] 4d¹⁰ 5s² 5p⁵", "ox": "+7, +5, +1, -1"},
    54: {"simbolo": "Xe", "nombre": "Xenón", "masa": 131.29, "periodo": 5, "grupo": 18, "cat": "gas_noble", "estado": "Gas", "electroneg": 2.6, "config": "[Kr] 4d¹⁰ 5s² 5p⁶", "ox": "+6, +4, +2"},
    55: {"simbolo": "Cs", "nombre": "Cesio", "masa": 132.91, "periodo": 6, "grupo": 1, "cat": "alcalino", "estado": "Sólido", "electroneg": 0.79, "config": "[Xe] 6s¹", "ox": "+1"},
    56: {"simbolo": "Ba", "nombre": "Bario", "masa": 137.33, "periodo": 6, "grupo": 2, "cat": "alcalinoterreo", "estado": "Sólido", "electroneg": 0.89, "config": "[Xe] 6s²", "ox": "+2"},
    57: {"simbolo": "La", "nombre": "Lantano", "masa": 138.91, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.10, "config": "[Xe] 5d¹ 6s²", "ox": "+3"},
    58: {"simbolo": "Ce", "nombre": "Cerio", "masa": 140.12, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.12, "config": "[Xe] 4f¹ 5d¹ 6s²", "ox": "+4, +3"},
    59: {"simbolo": "Pr", "nombre": "Praseodimio", "masa": 140.91, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.13, "config": "[Xe] 4f³ 6s²", "ox": "+3"},
    60: {"simbolo": "Nd", "nombre": "Neodimio", "masa": 144.24, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.14, "config": "[Xe] 4f⁴ 6s²", "ox": "+3"},
    61: {"simbolo": "Pm", "nombre": "Prometio", "masa": 145.0, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.13, "config": "[Xe] 4f⁵ 6s²", "ox": "+3"},
    62: {"simbolo": "Sm", "nombre": "Samario", "masa": 150.36, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.17, "config": "[Xe] 4f⁶ 6s²", "ox": "+3, +2"},
    63: {"simbolo": "Eu", "nombre": "Europio", "masa": 151.96, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.20, "config": "[Xe] 4f⁷ 6s²", "ox": "+3, +2"},
    64: {"simbolo": "Gd", "nombre": "Gadolinio", "masa": 157.25, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.20, "config": "[Xe] 4f⁷ 5d¹ 6s²", "ox": "+3"},
    65: {"simbolo": "Tb", "nombre": "Terbio", "masa": 158.93, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.22, "config": "[Xe] 4f⁹ 6s²", "ox": "+3"},
    66: {"simbolo": "Dy", "nombre": "Disprosio", "masa": 162.50, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.22, "config": "[Xe] 4f¹⁰ 6s²", "ox": "+3"},
    67: {"simbolo": "Ho", "nombre": "Holmio", "masa": 164.93, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.23, "config": "[Xe] 4f¹¹ 6s²", "ox": "+3"},
    68: {"simbolo": "Er", "nombre": "Erbio", "masa": 167.26, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.24, "config": "[Xe] 4f¹² 6s²", "ox": "+3"},
    69: {"simbolo": "Tm", "nombre": "Tulio", "masa": 168.93, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.25, "config": "[Xe] 4f¹³ 6s²", "ox": "+3"},
    70: {"simbolo": "Yb", "nombre": "Iterbio", "masa": 173.05, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.10, "config": "[Xe] 4f¹⁴ 6s²", "ox": "+3, +2"},
    71: {"simbolo": "Lu", "nombre": "Lutecio", "masa": 174.97, "periodo": 6, "grupo": 3, "cat": "lantanido", "estado": "Sólido", "electroneg": 1.27, "config": "[Xe] 4f¹⁴ 5d¹ 6s²", "ox": "+3"},
    72: {"simbolo": "Hf", "nombre": "Hafnio", "masa": 178.49, "periodo": 6, "grupo": 4, "cat": "transicion", "estado": "Sólido", "electroneg": 1.3, "config": "[Xe] 4f¹⁴ 5d² 6s²", "ox": "+4"},
    73: {"simbolo": "Ta", "nombre": "Tántalo", "masa": 180.95, "periodo": 6, "grupo": 5, "cat": "transicion", "estado": "Sólido", "electroneg": 1.5, "config": "[Xe] 4f¹⁴ 5d³ 6s²", "ox": "+5"},
    74: {"simbolo": "W", "nombre": "Wolframio", "masa": 183.84, "periodo": 6, "grupo": 6, "cat": "transicion", "estado": "Sólido", "electroneg": 2.36, "config": "[Xe] 4f¹⁴ 5d⁴ 6s²", "ox": "+6, +4"},
    75: {"simbolo": "Re", "nombre": "Renio", "masa": 186.21, "periodo": 6, "grupo": 7, "cat": "transicion", "estado": "Sólido", "electroneg": 1.9, "config": "[Xe] 4f¹⁴ 5d⁵ 6s²", "ox": "+7, +4"},
    76: {"simbolo": "Os", "nombre": "Osmio", "masa": 190.23, "periodo": 6, "grupo": 8, "cat": "transicion", "estado": "Sólido", "electroneg": 2.2, "config": "[Xe] 4f¹⁴ 5d⁶ 6s²", "ox": "+4, +3"},
    77: {"simbolo": "Ir", "nombre": "Iridio", "masa": 192.22, "periodo": 6, "grupo": 9, "cat": "transicion", "estado": "Sólido", "electroneg": 2.20, "config": "[Xe] 4f¹⁴ 5d⁷ 6s²", "ox": "+4, +3"},
    78: {"simbolo": "Pt", "nombre": "Platino", "masa": 195.08, "periodo": 6, "grupo": 10, "cat": "transicion", "estado": "Sólido", "electroneg": 2.28, "config": "[Xe] 4f¹⁴ 5d⁹ 6s¹", "ox": "+4, +2"},
    79: {"simbolo": "Au", "nombre": "Oro", "masa": 196.97, "periodo": 6, "grupo": 11, "cat": "transicion", "estado": "Sólido", "electroneg": 2.54, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s¹", "ox": "+3, +1"},
    80: {"simbolo": "Hg", "nombre": "Mercurio", "masa": 200.59, "periodo": 6, "grupo": 12, "cat": "transicion", "estado": "Líquido", "electroneg": 2.00, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s²", "ox": "+2, +1"},
    81: {"simbolo": "Tl", "nombre": "Talio", "masa": 204.38, "periodo": 6, "grupo": 13, "cat": "post_transicion", "estado": "Sólido", "electroneg": 1.62, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s² 6p¹", "ox": "+3, +1"},
    82: {"simbolo": "Pb", "nombre": "Plomo", "masa": 207.2, "periodo": 6, "grupo": 14, "cat": "post_transicion", "estado": "Sólido", "electroneg": 2.33, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s² 6p²", "ox": "+4, +2"},
    83: {"simbolo": "Bi", "nombre": "Bismuto", "masa": 208.98, "periodo": 6, "grupo": 15, "cat": "post_transicion", "estado": "Sólido", "electroneg": 2.02, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s² 6p³", "ox": "+3"},
    84: {"simbolo": "Po", "nombre": "Polonio", "masa": 209.0, "periodo": 6, "grupo": 16, "cat": "post_transicion", "estado": "Sólido", "electroneg": 2.0, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s² 6p⁴", "ox": "+4, +2"},
    85: {"simbolo": "At", "nombre": "Ástato", "masa": 210.0, "periodo": 6, "grupo": 17, "cat": "halogeno", "estado": "Sólido", "electroneg": 2.2, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s² 6p⁵", "ox": "+1, -1"},
    86: {"simbolo": "Rn", "nombre": "Radón", "masa": 222.0, "periodo": 6, "grupo": 18, "cat": "gas_noble", "estado": "Gas", "electroneg": None, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s² 6p⁶", "ox": "0"},
    87: {"simbolo": "Fr", "nombre": "Francio", "masa": 223.0, "periodo": 7, "grupo": 1, "cat": "alcalino", "estado": "Sólido", "electroneg": 0.7, "config": "[Rn] 7s¹", "ox": "+1"},
    88: {"simbolo": "Ra", "nombre": "Radio", "masa": 226.0, "periodo": 7, "grupo": 2, "cat": "alcalinoterreo", "estado": "Sólido", "electroneg": 0.9, "config": "[Rn] 7s²", "ox": "+2"},
    89: {"simbolo": "Ac", "nombre": "Actinio", "masa": 227.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.1, "config": "[Rn] 6d¹ 7s²", "ox": "+3"},
    90: {"simbolo": "Th", "nombre": "Torio", "masa": 232.04, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.3, "config": "[Rn] 6d² 7s²", "ox": "+4"},
    91: {"simbolo": "Pa", "nombre": "Protactinio", "masa": 231.04, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.5, "config": "[Rn] 5f² 6d¹ 7s²", "ox": "+5, +4"},
    92: {"simbolo": "U", "nombre": "Uranio", "masa": 238.03, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.38, "config": "[Rn] 5f³ 6d¹ 7s²", "ox": "+6, +4, +3"},
    93: {"simbolo": "Np", "nombre": "Neptunio", "masa": 237.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.36, "config": "[Rn] 5f⁴ 6d¹ 7s²", "ox": "+5, +4, +3"},
    94: {"simbolo": "Pu", "nombre": "Plutonio", "masa": 244.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.28, "config": "[Rn] 5f⁶ 7s²", "ox": "+6, +4, +3"},
    95: {"simbolo": "Am", "nombre": "Americio", "masa": 243.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.3, "config": "[Rn] 5f⁷ 7s²", "ox": "+4, +3"},
    96: {"simbolo": "Cm", "nombre": "Curio", "masa": 247.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.3, "config": "[Rn] 5f⁷ 6d¹ 7s²", "ox": "+3"},
    97: {"simbolo": "Bk", "nombre": "Berkelio", "masa": 247.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.3, "config": "[Rn] 5f⁹ 7s²", "ox": "+4, +3"},
    98: {"simbolo": "Cf", "nombre": "Californio", "masa": 251.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.3, "config": "[Rn] 5f¹⁰ 7s²", "ox": "+3"},
    99: {"simbolo": "Es", "nombre": "Einstenio", "masa": 252.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.3, "config": "[Rn] 5f¹¹ 7s²", "ox": "+3"},
    100: {"simbolo": "Fm", "nombre": "Fermio", "masa": 257.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.3, "config": "[Rn] 5f¹² 7s²", "ox": "+3"},
    101: {"simbolo": "Md", "nombre": "Mendelevio", "masa": 258.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.3, "config": "[Rn] 5f¹³ 7s²", "ox": "+3, +2"},
    102: {"simbolo": "No", "nombre": "Nobelio", "masa": 259.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.3, "config": "[Rn] 5f¹⁴ 7s²", "ox": "+3, +2"},
    103: {"simbolo": "Lr", "nombre": "Laurencio", "masa": 266.0, "periodo": 7, "grupo": 3, "cat": "actinido", "estado": "Sólido", "electroneg": 1.3, "config": "[Rn] 5f¹⁴ 7s² 7p¹", "ox": "+3"},
    104: {"simbolo": "Rf", "nombre": "Rutherfordio", "masa": 267.0, "periodo": 7, "grupo": 4, "cat": "transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d² 7s²", "ox": "+4"},
    105: {"simbolo": "Db", "nombre": "Dubnio", "masa": 268.0, "periodo": 7, "grupo": 5, "cat": "transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d³ 7s²", "ox": "+5"},
    106: {"simbolo": "Sg", "nombre": "Seaborgio", "masa": 269.0, "periodo": 7, "grupo": 6, "cat": "transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d⁴ 7s²", "ox": "+6"},
    107: {"simbolo": "Bh", "nombre": "Bohrio", "masa": 270.0, "periodo": 7, "grupo": 7, "cat": "transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d⁵ 7s²", "ox": "+7"},
    108: {"simbolo": "Hs", "nombre": "Hassio", "masa": 277.0, "periodo": 7, "grupo": 8, "cat": "transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d⁶ 7s²", "ox": "+8"},
    109: {"simbolo": "Mt", "nombre": "Meitnerio", "masa": 278.0, "periodo": 7, "grupo": 9, "cat": "transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d⁷ 7s²", "ox": "Desconocido"},
    110: {"simbolo": "Ds", "nombre": "Darmstatio", "masa": 281.0, "periodo": 7, "grupo": 10, "cat": "transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d⁸ 7s²", "ox": "Desconocido"},
    111: {"simbolo": "Rg", "nombre": "Roentgenio", "masa": 282.0, "periodo": 7, "grupo": 11, "cat": "transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d⁹ 7s²", "ox": "Desconocido"},
    112: {"simbolo": "Cn", "nombre": "Copernicio", "masa": 285.0, "periodo": 7, "grupo": 12, "cat": "transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d¹⁰ 7s²", "ox": "+2"},
    113: {"simbolo": "Nh", "nombre": "Nihonio", "masa": 286.0, "periodo": 7, "grupo": 13, "cat": "post_transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d¹⁰ 7s² 7p¹", "ox": "Desconocido"},
    114: {"simbolo": "Fl", "nombre": "Flerovio", "masa": 289.0, "periodo": 7, "grupo": 14, "cat": "post_transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d¹⁰ 7s² 7p²", "ox": "Desconocido"},
    115: {"simbolo": "Mc", "nombre": "Moscovio", "masa": 290.0, "periodo": 7, "grupo": 15, "cat": "post_transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d¹⁰ 7s² 7p³", "ox": "Desconocido"},
    116: {"simbolo": "Lv", "nombre": "Livermorio", "masa": 293.0, "periodo": 7, "grupo": 16, "cat": "post_transicion", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d¹⁰ 7s² 7p⁴", "ox": "Desconocido"},
    117: {"simbolo": "Ts", "nombre": "Teneso", "masa": 294.0, "periodo": 7, "grupo": 17, "cat": "halogeno", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d¹⁰ 7s² 7p⁵", "ox": "Desconocido"},
    118: {"simbolo": "Og", "nombre": "Oganesón", "masa": 294.0, "periodo": 7, "grupo": 18, "cat": "gas_noble", "estado": "Sintético", "electroneg": None, "config": "[Rn] 5f¹⁴ 6d¹⁰ 7s² 7p⁶", "ox": "Desconocido"}
}

# Diccionario inverso símbolo -> datos
SIMBOLO_A_ELEM = {v["simbolo"]: dict(v, z=k) for k, v in ELEMENTOS.items()}

# Compuestos comunes para sugerencias rápidas
COMPUESTOS_COMUNES = [
    {"formula": "H2O", "nombre": "Agua", "desc": "Compuesto esencial para la vida"},
    {"formula": "NaCl", "nombre": "Cloruro de Sodio (Sal Común)", "desc": "Sal de mesa fundamental"},
    {"formula": "CO2", "nombre": "Dióxido de Carbono", "desc": "Gas de efecto invernadero"},
    {"formula": "CH4", "nombre": "Metano", "desc": "Gas natural combustible"},
    {"formula": "C6H12O6", "nombre": "Glucosa", "desc": "Monosacárido fuente de energía celular"},
    {"formula": "C2H5OH", "nombre": "Etanol (Alcohol Etílico)", "desc": "Solvente y alcohol bebible"},
    {"formula": "H2SO4", "nombre": "Ácido Sulfúrico", "desc": "Ácido diprótico fuerte industrial"},
    {"formula": "HCl", "nombre": "Ácido Clorhídrico", "desc": "Ácido estomacal e industrial"},
    {"formula": "NH3", "nombre": "Amoníaco", "desc": "Gas alcalino para fertilizantes"},
    {"formula": "NaHCO3", "nombre": "Bicarbonato de Sodio", "desc": "Antiácido y leudante de cocina"},
    {"formula": "CaCO3", "nombre": "Carbonato de Calcio", "desc": "Caliza, mármol y conchas marinas"},
    {"formula": "C8H10N4O2", "nombre": "Cafeína", "desc": "Alcaloide estimulante del SNC"},
    {"formula": "C9H8O4", "nombre": "Ácido Acetilsalicílico (Aspirina)", "desc": "Analgésico y antiinflamatorio"},
    {"formula": "C12H22O11", "nombre": "Sacarosa (Azúcar Común)", "desc": "Disacárido glucosa + fructosa"},
    {"formula": "KMnO4", "nombre": "Permanganato de Potasio", "desc": "Oxidante y desinfectante fuerte"},
    {"formula": "CuSO4*5H2O", "nombre": "Sulfato de Cobre(II) Pentahidratado", "desc": "Cristales azules fungicidas"},
    {"formula": "Fe2O3", "nombre": "Óxido de Hierro(III) (Herrumbre)", "desc": "Pigmento rojo y óxido férrico"},
    {"formula": "CH3COOH", "nombre": "Ácido Acético (Vinagre)", "desc": "Ácido carboxílico característico"},
    {"formula": "H3PO4", "nombre": "Ácido Fosfórico", "desc": "Acidulante de bebidas y fertilizantes"},
    {"formula": "NaOH", "nombre": "Hidróxido de Sodio (Sosa Cáustica)", "desc": "Base fuerte desengrasante"},
    {"formula": "KOH", "nombre": "Hidróxido de Potasio (Potasa)", "desc": "Base para jabones líquidos"},
    {"formula": "C3H8", "nombre": "Propano", "desc": "Gas licuado de petróleo (GLP)"},
    {"formula": "C4H10", "nombre": "Butano", "desc": "Gas combustible para encendedores y cocina"},
    {"formula": "C6H6", "nombre": "Benceno", "desc": "Hidrocarburo aromático básico"},
    {"formula": "O3", "nombre": "Ozono", "desc": "Alótropo triatómico de oxígeno"}
]

# Recetas Moleculares para el Renderizador Gráfico 2D
ESTRUCTURAS_PREDEFINIDAS = {
    "H2O": {
        "atomos": [
            {"elem": "O", "x": 0, "y": 0, "r": 18},
            {"elem": "H", "x": -45, "y": 35, "r": 12},
            {"elem": "H", "x": 45, "y": 35, "r": 12}
        ],
        "enlaces": [(0, 1, 1), (0, 2, 1)]
    },
    "CO2": {
        "atomos": [
            {"elem": "C", "x": 0, "y": 0, "r": 16},
            {"elem": "O", "x": -60, "y": 0, "r": 16},
            {"elem": "O", "x": 60, "y": 0, "r": 16}
        ],
        "enlaces": [(0, 1, 2), (0, 2, 2)]
    },
    "CH4": {
        "atomos": [
            {"elem": "C", "x": 0, "y": 0, "r": 16},
            {"elem": "H", "x": 0, "y": -55, "r": 11},
            {"elem": "H", "x": 52, "y": 18, "r": 11},
            {"elem": "H", "x": -52, "y": 18, "r": 11},
            {"elem": "H", "x": 0, "y": 55, "r": 11}
        ],
        "enlaces": [(0, 1, 1), (0, 2, 1), (0, 3, 1), (0, 4, 1)]
    },
    "NH3": {
        "atomos": [
            {"elem": "N", "x": 0, "y": -15, "r": 16},
            {"elem": "H", "x": -45, "y": 35, "r": 11},
            {"elem": "H", "x": 45, "y": 35, "r": 11},
            {"elem": "H", "x": 0, "y": 48, "r": 11}
        ],
        "enlaces": [(0, 1, 1), (0, 2, 1), (0, 3, 1)]
    },
    "C2H5OH": {
        "atomos": [
            {"elem": "C", "x": -70, "y": 0, "r": 15},
            {"elem": "C", "x": 0, "y": 0, "r": 15},
            {"elem": "O", "x": 65, "y": -20, "r": 15},
            {"elem": "H", "x": 105, "y": 15, "r": 10},
            {"elem": "H", "x": -70, "y": -45, "r": 10},
            {"elem": "H", "x": -70, "y": 45, "r": 10},
            {"elem": "H", "x": -110, "y": 0, "r": 10},
            {"elem": "H", "x": 0, "y": -45, "r": 10},
            {"elem": "H", "x": 0, "y": 45, "r": 10}
        ],
        "enlaces": [(0, 1, 1), (1, 2, 1), (2, 3, 1), (0, 4, 1), (0, 5, 1), (0, 6, 1), (1, 7, 1), (1, 8, 1)]
    },
    "C6H6": {
        "atomos": [
            {"elem": "C", "x": 0, "y": -55, "r": 15},
            {"elem": "C", "x": 48, "y": -27, "r": 15},
            {"elem": "C", "x": 48, "y": 27, "r": 15},
            {"elem": "C", "x": 0, "y": 55, "r": 15},
            {"elem": "C", "x": -48, "y": 27, "r": 15},
            {"elem": "C", "x": -48, "y": -27, "r": 15},
            {"elem": "H", "x": 0, "y": -90, "r": 10},
            {"elem": "H", "x": 78, "y": -45, "r": 10},
            {"elem": "H", "x": 78, "y": 45, "r": 10},
            {"elem": "H", "x": 0, "y": 90, "r": 10},
            {"elem": "H", "x": -78, "y": 45, "r": 10},
            {"elem": "H", "x": -78, "y": -45, "r": 10}
        ],
        "enlaces": [
            (0, 1, 2), (1, 2, 1), (2, 3, 2), (3, 4, 1), (4, 5, 2), (5, 0, 1),
            (0, 6, 1), (1, 7, 1), (2, 8, 1), (3, 9, 1), (4, 10, 1), (5, 11, 1)
        ]
    },
    "NaCl": {
        "atomos": [
            {"elem": "Na", "x": -40, "y": 0, "r": 16},
            {"elem": "Cl", "x": 40, "y": 0, "r": 18}
        ],
        "enlaces": [(0, 1, 1)]
    },
    "HCl": {
        "atomos": [
            {"elem": "H", "x": -35, "y": 0, "r": 11},
            {"elem": "Cl", "x": 35, "y": 0, "r": 18}
        ],
        "enlaces": [(0, 1, 1)]
    },
    "O2": {
        "atomos": [
            {"elem": "O", "x": -35, "y": 0, "r": 16},
            {"elem": "O", "x": 35, "y": 0, "r": 16}
        ],
        "enlaces": [(0, 1, 2)]
    },
    "N2": {
        "atomos": [
            {"elem": "N", "x": -35, "y": 0, "r": 16},
            {"elem": "N", "x": 35, "y": 0, "r": 16}
        ],
        "enlaces": [(0, 1, 3)]
    }
}
