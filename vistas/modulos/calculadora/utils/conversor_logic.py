import re
import json
import time
import urllib.request
from pathlib import Path

class ConversorLogic:
    @staticmethod
    def obtener_tasas_cambio(cache_dir=None) -> dict:
        # Tasas de cambio por defecto (fallback offline aproximado)
        tasas_defecto = {
            "USD": 1.0,
            "EUR": 0.92,
            "GBP": 0.79,
            "JPY": 155.0,
            "BOB": 6.91,
            "MXN": 16.7,
            "ARS": 890.0,
            "BRL": 5.15,
            "CLP": 910.0,
            "PEN": 3.72,
            "COP": 3850.0
        }
        
        if not cache_dir:
            return tasas_defecto
            
        cache_file = Path(cache_dir) / "divisas_cache.json"
        ahora = time.time()
        
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                if ahora - cached_data.get("timestamp", 0) < 86400: # 24 horas
                    return cached_data.get("rates", tasas_defecto)
            except Exception:
                pass
                
        try:
            url = "https://open.er-api.com/v6/latest/USD"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get("result") == "success":
                    rates = data.get("rates", {})
                    try:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump({"timestamp": ahora, "rates": rates}, f, indent=4)
                    except Exception:
                        pass
                    return rates
        except Exception as e:
            print(f"[!] Error al descargar tasas de cambio online: {e}")
            
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                return cached_data.get("rates", tasas_defecto)
            except Exception:
                pass
                
        return tasas_defecto

    @staticmethod
    def convertir(valor_entrada, tipo, origen, destino, cache_dir=None):
        """Realiza la conversión entre unidades del mismo tipo"""
        if origen == destino:
            return valor_entrada

        # --- CATEGORÍAS NUEVAS: DIVISAS, BASES NUMÉRICAS, FORMATOS DE COLOR ---
        if tipo == "Divisas":
            try:
                val = float(str(valor_entrada).replace(',', '.'))
            except ValueError:
                raise ValueError("La cantidad a convertir debe ser un número válido.")

            # Extraer códigos de 3 letras de origen/destino (ej: "Dólar (USD)")
            code_origen = re.search(r'\(([A-Z]{3})\)', origen)
            code_destino = re.search(r'\(([A-Z]{3})\)', destino)
            
            if not code_origen or not code_destino:
                raise ValueError("No se pudieron parsear los códigos de divisas.")
                
            co = code_origen.group(1)
            cd = code_destino.group(1)
            
            tasas = ConversorLogic.obtener_tasas_cambio(cache_dir)
            if co not in tasas or cd not in tasas:
                raise ValueError("Tasa de cambio no disponible para la divisa seleccionada.")
                
            # Convertir a USD (Base)
            val_usd = val / tasas[co]
            # Convertir de USD a destino
            return val_usd * tasas[cd]

        elif tipo == "Bases Numéricas":
            val_str = str(valor_entrada).strip()
            
            # Obtener base de origen
            base_origen = 10
            if "Binario" in origen: base_origen = 2
            elif "Octal" in origen: base_origen = 8
            elif "Decimal" in origen: base_origen = 10
            elif "Hexadecimal" in origen: base_origen = 16
            
            # Obtener base de destino
            base_destino = 10
            if "Binario" in destino: base_destino = 2
            elif "Octal" in destino: base_destino = 8
            elif "Decimal" in destino: base_destino = 10
            elif "Hexadecimal" in destino: base_destino = 16

            try:
                val_int = int(val_str, base_origen)
            except ValueError:
                raise ValueError(f"El valor '{val_str}' no es una representación válida en {origen}.")

            if base_destino == 2:
                return bin(val_int)[2:]
            elif base_destino == 8:
                return oct(val_int)[2:]
            elif base_destino == 10:
                return str(val_int)
            elif base_destino == 16:
                return hex(val_int)[2:].upper()

        elif tipo == "Formatos de Color":
            val_str = str(valor_entrada).strip()
            
            # Parsear a RGB (0-255)
            r, g, b = ConversorLogic._parse_color(val_str, origen)
            
            # Formatear al destino
            return ConversorLogic._format_color(r, g, b, destino)

        # --- CATEGORÍAS ORIGINALES (Se mantiene compatibilidad de flotantes) ---
        try:
            valor = float(str(valor_entrada).replace(',', '.'))
        except ValueError:
            raise ValueError("La cantidad a convertir debe ser un número válido.")

        if tipo == "Longitud":
            # Base: Metros
            factores = {
                "Kilómetro": 1000,
                "Metro": 1,
                "Centímetro": 0.01,
                "Milímetro": 0.001,
                "Milla": 1609.34,
                "Yarda": 0.9144,
                "Pie": 0.3048,
                "Pulgada": 0.0254
            }
            valor_base = 0
            for name, fact in factores.items():
                if name in origen:
                    valor_base = valor * fact
                    break
            
            for name, fact in factores.items():
                if name in destino:
                    return valor_base / fact
        
        elif tipo == "Masa":
            # Base: Gramos
            factores = {
                "Tonelada": 1000000,
                "Kilogramo": 1000,
                "Gramo": 1,
                "Miligramo": 0.001,
                "Libra": 453.592,
                "Onza": 28.3495
            }
            valor_base = 0
            for name, fact in factores.items():
                if name in origen:
                    valor_base = valor * fact
                    break
            
            for name, fact in factores.items():
                if name in destino:
                    return valor_base / fact
        
        elif tipo == "Volumen":
            # Base: Mililitros
            factores = {
                "Metro cúbico": 1000000,
                "Litro": 1000,
                "Mililitro": 1,
                "Galón": 3785.41,
                "Cuarto": 946.353,
                "Pinta": 473.176,
                "Onza líquida": 29.5735
            }
            valor_base = 0
            for name, fact in factores.items():
                if name in origen:
                    valor_base = valor * fact
                    break
            
            for name, fact in factores.items():
                if name in destino:
                    return valor_base / fact
        
        elif tipo == "Temperatura":
            # Base: Kelvin
            if "Celsius" in origen:
                valor_base = valor + 273.15
            elif "Fahrenheit" in origen:
                valor_base = (valor - 32) * 5/9 + 273.15
            elif "Kelvin" in origen:
                valor_base = valor
            else:
                return valor
            
            if "Celsius" in destino:
                return valor_base - 273.15
            elif "Fahrenheit" in destino:
                return (valor_base - 273.15) * 9/5 + 32
            elif "Kelvin" in destino:
                return valor_base
        
        elif tipo == "Área":
            # Base: Metros cuadrados
            factores = {
                "Kilómetro cuadrado": 1000000,
                "Metro cuadrado": 1,
                "Centímetro cuadrado": 0.0001,
                "Milla cuadrada": 2589988.11,
                "Acre": 4046.86,
                "Pie cuadrado": 0.092903
            }
            valor_base = 0
            for name, fact in factores.items():
                if name in origen:
                    valor_base = valor * fact
                    break
            
            for name, fact in factores.items():
                if name in destino:
                    if "Centímetro cuadrado" in name:
                         return valor_base / 0.0001
                    return valor_base / fact
        
        elif tipo == "Tiempo":
            # Base: Segundos
            factores = {
                "Año": 31536000,
                "Mes": 2592000,
                "Semana": 604800,
                "Día": 86400,
                "Hora": 3600,
                "Minuto": 60,
                "Segundo": 1,
                "Milisegundo": 0.001
            }
            valor_base = 0
            for name, fact in factores.items():
                if name in origen:
                    valor_base = valor * fact
                    break
            
            for name, fact in factores.items():
                if name in destino:
                    return valor_base / fact
        
        elif tipo == "Velocidad":
            # Base: Metros por segundo
            factores = {
                "Kilómetro por hora": 0.277778,
                "Metro por segundo": 1,
                "Milla por hora": 0.44704,
                "Pie por segundo": 0.3048,
                "Nudo": 0.514444
            }
            valor_base = 0
            for name, fact in factores.items():
                if name in origen:
                    valor_base = valor * fact
                    break
            
            for name, fact in factores.items():
                if name in destino:
                    return valor_base / fact
        
        elif tipo == "Datos":
            # Base: Bytes
            factores = {
                "Byte": 1,
                "Kilobyte": 1024,
                "Megabyte": 1024**2,
                "Gigabyte": 1024**3,
                "Terabyte": 1024**4,
                "Petabyte": 1024**5
            }
            valor_base = 0
            for name, fact in factores.items():
                if name in origen:
                    valor_base = valor * fact
                    break
            
            for name, fact in factores.items():
                if name in destino:
                    return valor_base / fact
        
        return valor

    @staticmethod
    def _parse_color(input_str, formato):
        input_str = input_str.strip().lower()
        if "HEX" in formato:
            hex_str = input_str.lstrip('#')
            if len(hex_str) == 3:
                hex_str = "".join(c*2 for c in hex_str)
            if len(hex_str) != 6:
                raise ValueError("Formato HEX inválido. Ej: #FF5733 o FF5733")
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return r, g, b
        
        elif "RGB" in formato:
            nums = [int(x) for x in re.findall(r'\d+', input_str)]
            if len(nums) < 3:
                raise ValueError("Formato RGB inválido. Ej: 255, 87, 51 o rgb(255, 87, 51)")
            r, g, b = nums[0], nums[1], nums[2]
            if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
                raise ValueError("Los valores RGB deben estar entre 0 y 255.")
            return r, g, b
            
        elif "HSL" in formato:
            nums = [int(x) for x in re.findall(r'\d+', input_str)]
            if len(nums) < 3:
                raise ValueError("Formato HSL inválido. Ej: 11, 100%, 60% o hsl(11, 100, 60)")
            h, s, l = nums[0], nums[1], nums[2]
            if not (0 <= h <= 360 and 0 <= s <= 100 and 0 <= l <= 100):
                raise ValueError("Valores HSL fuera de rango (H: 0-360, S: 0-100, L: 0-100).")
            
            # Convertir HSL a RGB
            h_n = h / 360.0
            s_n = s / 100.0
            l_n = l / 100.0
            
            if s_n == 0:
                r = g = b = l_n
            else:
                def hue_to_rgb(p, q, t):
                    if t < 0: t += 1
                    if t > 1: t -= 1
                    if t < 1/6: return p + (q - p) * 6 * t
                    if t < 1/2: return q
                    if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                    return p
                q = l_n * (1 + s_n) if l_n < 0.5 else l_n + s_n - l_n * s_n
                p = 2 * l_n - q
                r = hue_to_rgb(p, q, h_n + 1/3)
                g = hue_to_rgb(p, q, h_n)
                b = hue_to_rgb(p, q, h_n - 1/3)
            return round(r * 255), round(g * 255), round(b * 255)
            
        elif "CMYK" in formato:
            nums = [int(x) for x in re.findall(r'\d+', input_str)]
            if len(nums) < 4:
                raise ValueError("Formato CMYK inválido. Ej: 0, 66, 80, 0 o cmyk(0, 66, 80, 0)")
            c, m, y, k = nums[0], nums[1], nums[2], nums[3]
            if not (0 <= c <= 100 and 0 <= m <= 100 and 0 <= y <= 100 and 0 <= k <= 100):
                raise ValueError("Los valores CMYK deben estar entre 0 y 100.")
            
            # Convertir CMYK a RGB
            c_n = c / 100.0
            m_n = m / 100.0
            y_n = y / 100.0
            k_n = k / 100.0
            
            r = round(255 * (1 - c_n) * (1 - k_n))
            g = round(255 * (1 - m_n) * (1 - k_n))
            b = round(255 * (1 - y_n) * (1 - k_n))
            return r, g, b
            
        raise ValueError("Formato de color no reconocido.")

    @staticmethod
    def _format_color(r, g, b, formato):
        if "HEX" in formato:
            return f"#{r:02X}{g:02X}{b:02X}"
        elif "RGB" in formato:
            return f"rgb({r}, {g}, {b})"
        elif "HSL" in formato:
            r_n = r / 255.0
            g_n = g / 255.0
            b_n = b / 255.0
            cmax = max(r_n, g_n, b_n)
            cmin = min(r_n, g_n, b_n)
            diff = cmax - cmin
            
            l = (cmax + cmin) / 2
            if diff == 0:
                h = s = 0
            else:
                s = diff / (cmax + cmin) if l < 0.5 else diff / (2 - cmax - cmin)
                if cmax == r_n:
                    h = (g_n - b_n) / diff + (6 if g_n < b_n else 0)
                elif cmax == g_n:
                    h = (b_n - r_n) / diff + 2
                else:
                    h = (r_n - g_n) / diff + 4
                h /= 6
            return f"hsl({round(h * 360)}, {round(s * 100)}%, {round(l * 100)}%)"
            
        elif "CMYK" in formato:
            r_n = r / 255.0
            g_n = g / 255.0
            b_n = b / 255.0
            
            k = 1 - max(r_n, g_n, b_n)
            if k == 1:
                c = m = y = 0
            else:
                c = (1 - r_n - k) / (1 - k)
                m = (1 - g_n - k) / (1 - k)
                y = (1 - b_n - k) / (1 - k)
            return f"cmyk({round(c * 100)}%, {round(m * 100)}%, {round(y * 100)}%, {round(k * 100)}%)"
            
        raise ValueError("Formato de color no reconocido.")
