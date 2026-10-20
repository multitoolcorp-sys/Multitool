"""
schedule_manager.py  –  Backend del módulo Horarios
Exporta a: TXT, CSV, HTML
"""
import json
import os
import csv
import datetime
from pathlib import Path

def _hex_to_rgb(hex_color: str):
    """Convierte #RRGGBB a tupla (r, g, b) 0-255."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (255, 255, 255)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


class ScheduleManager:
    def __init__(self, ruta_horarios):
        self.ruta_horarios = Path(ruta_horarios)
        self.ruta_horarios.mkdir(parents=True, exist_ok=True)
        self.horarios = []

    def listar_horarios(self):
        self.horarios = []
        for archivo in sorted(self.ruta_horarios.glob("*.json")):
            self.horarios.append({"nombre": archivo.stem, "ruta": archivo})
        return self.horarios

    def cargar_datos(self, ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)

    def guardar_datos(self, nombre, actividades, ruta_actual=None, horas=None, headers=None):
        datos = {
            "nombre": nombre,
            "fecha_modificacion": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "actividades": actividades,
            "horas": horas,
            "headers": headers
        }
        nueva_ruta = self.ruta_horarios / f"{nombre}.json"
        if ruta_actual and Path(ruta_actual).stem != nombre and Path(ruta_actual).exists():
            try:
                os.remove(ruta_actual)
            except Exception:
                pass
        with open(nueva_ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        return nueva_ruta

    def nuevo_horario(self, nombre):
        ruta = self.ruta_horarios / f"{nombre}.json"
        nuevo = {
            "nombre": nombre,
            "fecha_creacion": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "actividades": [],
            "horas": [f"{h:02d}:00" for h in range(8, 21)]
        }
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(nuevo, f, indent=4, ensure_ascii=False)
        return {"nombre": nombre, "ruta": ruta}

    def eliminar_horario(self, ruta):
        if os.path.exists(ruta):
            os.remove(ruta)
            return True
        return False

    def _matrix(self, actividades, horas=None, headers=None):
        if horas is None:
            orden_horas = []
            for act in actividades:
                h = act.get("hora", "")
                if h and h not in orden_horas: orden_horas.append(h)
            horas = orden_horas
        
        if headers is None:
            headers = sorted(list(set(act.get("dia", "Lunes") for act in actividades)))

        mat = {h: {d: {} for d in headers} for h in horas}
        for act in actividades:
            h = act.get("hora", "")
            d = act.get("dia", "")
            if h in mat and d in mat[h]:
                mat[h][d] = act
        return mat, horas, headers

    def exportar_txt(self, ruta_salida, nombre, actividades, horas=None, headers=None):
        mat, horas, headers = self._matrix(actividades, horas, headers)
        with open(ruta_salida, "w", encoding="utf-8") as f:
            f.write(f"HORARIO: {nombre}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"{' ':12}" + "".join(f"{d:<20}" for d in headers) + "\n")
            f.write("-" * (12 + 20 * len(headers)) + "\n")
            for h in horas:
                row = f"{h:<12}"
                for d in headers:
                    texto = mat[h][d].get("descripcion", "")
                    row += f"{texto[:19]:<20}"
                f.write(row + "\n")

    def exportar_csv(self, ruta_salida, nombre, actividades, horas=None, headers=None):
        mat, horas, headers = self._matrix(actividades, horas, headers)
        with open(ruta_salida, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["HORA"] + headers)
            for h in horas:
                row = [h] + [mat[h][d].get("descripcion", "") for d in headers]
                writer.writerow(row)

    def exportar_html(self, ruta_salida, nombre, actividades, horas=None, headers=None):
        mat, horas, headers = self._matrix(actividades, horas, headers)
        css = """
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121218; color: #eee; padding: 20px; }
        h1 { color: #6366F1; margin-bottom: 5px; }
        .meta { color: #AAB0B8; font-size: 0.9em; margin-bottom: 20px; }
        table { border-collapse: collapse; width: 100%; border-radius: 8px; border: 1px solid #333; overflow: hidden; table-layout: fixed; }
        th { background: #1E1E2E; color: #6366F1; padding: 12px 15px; text-align: left; font-weight: 600; border: 1px solid #333; }
        td { border: 1px solid #333; padding: 12px 15px; vertical-align: top; min-height: 44px; word-wrap: break-word; }
        td.hora { background: #1e1e2e; color: #AAB0B8; font-weight: bold; width: 100px; text-align: center; }
        """
        html = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>"
        html += f"<h1>Horario: {nombre}</h1>"
        html += f"<div class='meta'>Exportado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>"
        html += "<table><thead><tr><th style='width:100px'>HORA</th>"
        for h in headers: html += f"<th>{h}</th>"
        html += "</tr></thead><tbody>"
        for h in horas:
            html += f"<tr><td class='hora'>{h}</td>"
            for d in headers:
                act = mat[h][d]
                text = act.get("descripcion", "").replace("\n", "<br>")
                bg = act.get("color", "")
                fg = act.get("fg", "")
                sz = act.get("font_size", "")
                bold = "font-weight:bold;" if act.get("bold") else ""
                italic = "font-style:italic;" if act.get("italic") else ""
                style = f"{bold} {italic}"
                if bg: style += f"background-color: {bg};"
                if fg: style += f"color: {fg};"
                if sz: style += f"font-size: {sz}pt;"
                html += f"<td style='{style}'>{text}</td>"
            html += "</tr>"
        html += "</tbody></table></body></html>"
        with open(ruta_salida, "w", encoding="utf-8") as f:
            f.write(html)

