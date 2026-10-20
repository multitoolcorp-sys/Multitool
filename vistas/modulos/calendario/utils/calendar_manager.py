import json
import datetime
import calendar
import csv
from pathlib import Path

class CalendarManager:
    def __init__(self, ruta_recordatorios):
        self.ruta_recordatorios = Path(ruta_recordatorios)
        self.ruta_recordatorios.mkdir(parents=True, exist_ok=True)
        self.recordatorios = {}
        self.objetivos_anuales = []
        self.fecha_actual = datetime.datetime.now()
        self.año = self.fecha_actual.year
        self.mes = self.fecha_actual.month
        
        self.categorias = {
            "General": "#6366F1",    # Indigo
            "Trabajo": "#F87171",    # Rojo
            "Personal": "#34D399",   # Esmeralda
            "Importante": "#FBBF24", # Ámbar
            "Otro": "#AAB0B8"        # Gris
        }
        
        self.cargar_recordatorios()
        self.cargar_objetivos()

    def cargar_recordatorios(self):
        archivo = self.ruta_recordatorios / "recordatorios.json"
        if archivo.exists():
            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    self.recordatorios = json.load(f)
            except Exception as e:
                print(f"Error cargando recordatorios: {e}")
                self.recordatorios = {}

    def guardar_recordatorios(self):
        archivo = self.ruta_recordatorios / "recordatorios.json"
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                json.dump(self.recordatorios, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando recordatorios: {e}")

    # ── Objetivos Anuales ─────────────────────────────────────────────────
    def cargar_objetivos(self):
        archivo = self.ruta_recordatorios / "objetivos_anuales.json"
        if archivo.exists():
            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    self.objetivos_anuales = json.load(f)
            except Exception as e:
                print(f"Error cargando objetivos: {e}")
                self.objetivos_anuales = []

    def guardar_objetivos(self):
        archivo = self.ruta_recordatorios / "objetivos_anuales.json"
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                json.dump(self.objetivos_anuales, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando objetivos: {e}")

    def get_objetivos(self, año=None):
        target_year = año or self.año
        return [o for o in self.objetivos_anuales if o.get("año") == target_year]

    def añadir_objetivo(self, titulo, categoria="General", año=None):
        target_year = año or self.año
        obj = {
            "id": datetime.datetime.now().timestamp(),
            "titulo": titulo,
            "categoria": categoria,
            "completado": False,
            "año": target_year,
            "creado": datetime.datetime.now().strftime("%Y-%m-%d")
        }
        self.objetivos_anuales.append(obj)
        self.guardar_objetivos()
        return obj

    def toggle_objetivo(self, obj_id):
        for o in self.objetivos_anuales:
            if o.get("id") == obj_id:
                o["completado"] = not o.get("completado", False)
                self.guardar_objetivos()
                return o.get("completado")
        return False

    def eliminar_objetivo(self, obj_id):
        self.objetivos_anuales = [o for o in self.objetivos_anuales if o.get("id") != obj_id]
        self.guardar_objetivos()

    # ── Navegación & Consultas ──────────────────────────────────────────
    def get_mes_nombre(self, num_mes=None):
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        m = num_mes if num_mes is not None else self.mes
        return meses[m - 1]

    def navegar_mes(self, delta):
        self.mes += delta
        if self.mes < 1:
            self.mes = 12
            self.año -= 1
        elif self.mes > 12:
            self.mes = 1
            self.año += 1

    def get_recordatorios_por_fecha(self, fecha_str):
        mes_dia = fecha_str[5:]
        resultados = list(self.recordatorios.get(fecha_str, []))
        
        for fs, recs in self.recordatorios.items():
            if fs == fecha_str: continue 
            if fs.endswith(mes_dia):
                for r in recs:
                    if r.get("anual", False):
                        resultados.append(r)
                        
        resultados.sort(key=lambda x: x.get("hora", "00:00"))
        return resultados

    def get_dias_mes(self, colores, año=None, mes=None):
        target_year = año or self.año
        target_month = mes or self.mes
        primer_dia = datetime.date(target_year, target_month, 1)
        dias_total = calendar.monthrange(target_year, target_month)[1]
        inicio_semana = primer_dia.weekday()
        hoy = datetime.date.today()
        
        if target_month == 1:
            mes_ant, año_ant = 12, target_year - 1
        else:
            mes_ant, año_ant = target_month - 1, target_year
        dias_mes_ant = calendar.monthrange(año_ant, mes_ant)[1]
        
        matriz = []
        dia_num = 1
        dia_sig_num = 1
        
        for f in range(6):
            fila = []
            for c in range(7):
                if f == 0 and c < inicio_semana:
                    d_num = dias_mes_ant - (inicio_semana - c - 1)
                    fila.append({
                        "num": str(d_num), "fecha": None, "recs": [], 
                        "es_mes_actual": False, "bg": colores["bg_principal"], "fg": colores["fg_secundario"]
                    })
                elif dia_num > dias_total:
                    fila.append({
                        "num": str(dia_sig_num), "fecha": None, "recs": [], 
                        "es_mes_actual": False, "bg": colores["bg_principal"], "fg": colores["fg_secundario"]
                    })
                    dia_sig_num += 1
                else:
                    fecha = datetime.date(target_year, target_month, dia_num)
                    fecha_str = fecha.strftime("%Y-%m-%d")
                    recs = self.get_recordatorios_por_fecha(fecha_str)
                    is_today = (fecha == hoy)
                    
                    bg = colores["bg_terciario"]
                    if is_today: bg = colores["acento"]
                    
                    fila.append({
                        "num": str(dia_num), "fecha": fecha, "recs": recs, 
                        "es_mes_actual": True, "is_today": is_today,
                        "bg": bg, "fg": "white" if is_today else colores["fg_principal"]
                    })
                    dia_num += 1
            matriz.append(fila)
        return matriz

    def get_proximos(self, limite=10):
        hoy = datetime.date.today()
        proximos = []
        fechas_futuras = {}
        
        for f_str, recs in self.recordatorios.items():
            try:
                f_dt = datetime.datetime.strptime(f_str, "%Y-%m-%d").date()
            except Exception:
                continue
            for r in recs:
                if f_dt >= hoy:
                    if f_str not in fechas_futuras: fechas_futuras[f_str] = []
                    fechas_futuras[f_str].append(r)
                
                if r.get("anual", False):
                    pro_f_dt = datetime.date(hoy.year, f_dt.month, f_dt.day)
                    if pro_f_dt < hoy:
                        pro_f_dt = datetime.date(hoy.year + 1, f_dt.month, f_dt.day)
                    
                    pro_str = pro_f_dt.strftime("%Y-%m-%d")
                    if pro_str != f_str:
                        if pro_str not in fechas_futuras: fechas_futuras[pro_str] = []
                        fechas_futuras[pro_str].append(r)
                        
        fechas_ordenadas = sorted(fechas_futuras.keys())
        
        for f_str in fechas_ordenadas:
            fecha_dt = datetime.datetime.strptime(f_str, "%Y-%m-%d").date()
            for r in fechas_futuras[f_str]:
                r_copy = r.copy()
                r_copy["fecha_str"] = f_str
                r_copy["fecha_dt"] = fecha_dt
                proximos.append(r_copy)
            if len(proximos) >= limite: break
                    
        return proximos[:limite]

    def añadir_recordatorio(self, fecha_str, titulo, desc, categoria="General", hora="00:00", anual=False, alarma=True):
        if fecha_str not in self.recordatorios:
            self.recordatorios[fecha_str] = []
        
        self.recordatorios[fecha_str].append({
            "id": datetime.datetime.now().timestamp(),
            "titulo": titulo,
            "descripcion": desc,
            "categoria": categoria,
            "hora": hora,
            "anual": anual,
            "alarma": alarma,
            "creado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        self.recordatorios[fecha_str].sort(key=lambda x: x.get("hora", "00:00"))
        self.guardar_recordatorios()

    def eliminar_recordatorio(self, fecha_str, r_id):
        for real_f_str, recs in self.recordatorios.items():
            for r in recs:
                if r.get("id") == r_id:
                    self.recordatorios[real_f_str] = [re for re in recs if re.get("id") != r_id]
                    if not self.recordatorios[real_f_str]: del self.recordatorios[real_f_str]
                    self.guardar_recordatorios()
                    return True
        return False

    def editar_recordatorio(self, fecha_str, r_id, nuevo_titulo, nueva_desc, nueva_cat, nueva_hora, anual=False, alarma=True):
        for real_f_str, recs in self.recordatorios.items():
            for r in recs:
                if r.get("id") == r_id:
                    r["titulo"] = nuevo_titulo
                    r["descripcion"] = nueva_desc
                    r["categoria"] = nueva_cat
                    r["hora"] = nueva_hora
                    r["anual"] = anual
                    r["alarma"] = alarma
                    self.recordatorios[real_f_str].sort(key=lambda x: x.get("hora", "00:00"))
                    self.guardar_recordatorios()
                    return True
        return False

    def buscar_recordatorios(self, query):
        query = query.lower()
        resultados = []
        for f_str, recs in self.recordatorios.items():
            for r in recs:
                if query in r["titulo"].lower() or query in r.get("descripcion", "").lower() or query in r.get("categoria", "").lower():
                    r_copy = r.copy()
                    r_copy["fecha_str"] = f_str
                    resultados.append(r_copy)
        return resultados

    # ── Estadísticas ─────────────────────────────────────────────────────
    def get_estadisticas_agenda(self):
        total_eventos = 0
        por_categoria = {cat: 0 for cat in self.categorias.keys()}
        eventos_anuales = 0
        
        for f_str, recs in self.recordatorios.items():
            for r in recs:
                total_eventos += 1
                cat = r.get("categoria", "General")
                if cat in por_categoria:
                    por_categoria[cat] += 1
                else:
                    por_categoria["Otro"] = por_categoria.get("Otro", 0) + 1
                if r.get("anual", False):
                    eventos_anuales += 1

        objs_año = self.get_objetivos()
        total_objs = len(objs_año)
        objs_cumplidos = len([o for o in objs_año if o.get("completado")])
        porcentaje_objs = int((objs_cumplidos / total_objs * 100)) if total_objs > 0 else 0

        return {
            "total_eventos": total_eventos,
            "por_categoria": por_categoria,
            "eventos_anuales": eventos_anuales,
            "total_objetivos": total_objs,
            "objetivos_cumplidos": objs_cumplidos,
            "porcentaje_objetivos": porcentaje_objs
        }

    # ── Exportaciones iCal (.ics) y CSV (.csv) ───────────────────────────
    def exportar_ical(self, filepath):
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Multitool//Agenda App//ES"
        ]
        for f_str, recs in self.recordatorios.items():
            for r in recs:
                hora = r.get("hora", "00:00").replace(":", "") + "00"
                fecha_clean = f_str.replace("-", "")
                dtstart = f"{fecha_clean}T{hora}"
                
                lines.append("BEGIN:VEVENT")
                lines.append(f"SUMMARY:{r.get('titulo', 'Evento')}")
                lines.append(f"DESCRIPTION:{r.get('descripcion', '')}")
                lines.append(f"CATEGORIES:{r.get('categoria', 'General')}")
                lines.append(f"DTSTART:{dtstart}")
                if r.get("anual"):
                    lines.append("RRULE:FREQ=YEARLY")
                lines.append("END:VEVENT")
        lines.append("END:VCALENDAR")

        Path(filepath).write_text("\n".join(lines), encoding="utf-8")

    def exportar_csv(self, filepath):
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Fecha", "Hora", "Título", "Descripción", "Categoría", "Anual"])
            for f_str, recs in self.recordatorios.items():
                for r in recs:
                    writer.writerow([
                        f_str, r.get("hora", "00:00"), r.get("titulo", ""), 
                        r.get("descripcion", ""), r.get("categoria", "General"),
                        "Sí" if r.get("anual") else "No"
                    ])
