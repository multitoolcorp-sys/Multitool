import os
import sys
import platform
import datetime
import urllib.request
import json
import threading

_cached_weather_info = "Consultando clima local..."
_cached_location_info = "Ubicación local"
_last_fetch_time = 0


def _fetch_weather_async():
    global _cached_weather_info, _cached_location_info, _last_fetch_time
    import time
    now = time.time()
    if now - _last_fetch_time < 300: # Cache por 5 minutos
        return
    _last_fetch_time = now

    try:
        req = urllib.request.Request(
            "https://wttr.in/?format=j1",
            headers={"User-Agent": "MultiTool/1.0"}
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            current = data.get("current_condition", [{}])[0]
            temp_c = current.get("temp_C", "")
            desc = current.get("weatherDesc", [{}])[0].get("value", "")
            humidity = current.get("humidity", "")
            wind = current.get("windspeedKmph", "")

            area = data.get("nearest_area", [{}])[0]
            city = area.get("areaName", [{}])[0].get("value", "")
            country = area.get("country", [{}])[0].get("value", "")

            if city:
                _cached_location_info = f"{city}, {country}"
            if temp_c:
                _cached_weather_info = f"{desc}, {temp_c}°C (Humedad: {humidity}%, Viento: {wind} km/h)"
    except Exception:
        # Fallback a consulta IP simple
        try:
            req2 = urllib.request.Request("http://ip-api.com/json", headers={"User-Agent": "MultiTool/1.0"})
            with urllib.request.urlopen(req2, timeout=3) as resp2:
                data2 = json.loads(resp2.read().decode("utf-8"))
                city2 = data2.get("city", "")
                country2 = data2.get("country", "")
                if city2:
                    _cached_location_info = f"{city2}, {country2}"
                    _cached_weather_info = "Condiciones locales templadas"
        except Exception:
            _cached_weather_info = "No disponible actualmente"


# Iniciar actualización en segundo plano
threading.Thread(target=_fetch_weather_async, daemon=True).start()


def get_system_environmental_context(enabled: bool = True) -> str:
    """Devuelve un bloque de texto con el contexto del entorno para el prompt del sistema"""
    if not enabled:
        return ""

    now = datetime.datetime.now()
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    dia_str = dias[now.weekday()]
    mes_str = meses[now.month - 1]
    fecha_formato = f"{dia_str}, {now.day} de {mes_str} de {now.year}, {now.strftime('%I:%M:%S %p')}"

    # Disparar actualización si pasaron más de 5 minutos
    threading.Thread(target=_fetch_weather_async, daemon=True).start()

    sistema = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"

    return (
        f"\n\n[CONTEXTO_ENTORNO_LOCAL]\n"
        f"- Fecha y Hora Actual: {fecha_formato}\n"
        f"- Sistema Operativo: {sistema}\n"
        f"- Ubicación Aproximada: {_cached_location_info}\n"
        f"- Clima Actual: {_cached_weather_info}\n"
        f"[/CONTEXTO_ENTORNO_LOCAL]"
    )
