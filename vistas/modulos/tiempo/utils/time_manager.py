import json
import time
import datetime
from pathlib import Path

class TimeManager:
    def __init__(self, ruta_datos):
        self.ruta_datos = Path(ruta_datos)
        self.ruta_datos.mkdir(parents=True, exist_ok=True)
        self.ruta_alarmas = self.ruta_datos / "alarmas.json"
        self.ruta_ciudades = self.ruta_datos / "ciudades_mundiales.json"
        self.ruta_pomodoro = self.ruta_datos / "pomodoro_stats.json"
        self.ruta_eventos = self.ruta_datos / "eventos_calendario.json"
        self.ruta_tracker = self.ruta_datos / "time_tracker.json"
        
        # Cronómetro
        self.crono_running = False
        self.crono_start_time = 0
        self.crono_accum = 0
        self.laps = []
        
        # Temporizador
        self.timer_running = False
        self.timer_remaining = 0
        self.timer_start_time = 0
        
        # Alarmas
        self.alarmas = []
        self.sonido_alarma = ""
        self.cargar_alarmas()

        # Ciudades del Reloj Mundial
        self.ciudades = []
        self.cargar_ciudades()

        # Pomodoro Stats
        self.pomodoro_stats = {"sesiones_hoy": 0, "minutos_enfoque": 0}
        self.cargar_pomodoro_stats()

        # Calendario & Eventos
        self.eventos = []
        self.cargar_eventos()

        # Time Tracker
        self.tracker_records = []
        self.tracker_activo = None
        self.cargar_tracker()

    def cargar_alarmas(self):
        if self.ruta_alarmas.exists():
            try:
                with open(self.ruta_alarmas, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.alarmas = data.get("alarmas", [])
                    self.sonido_alarma = data.get("sonido_alarma", "")
            except Exception:
                self.alarmas = []

    def guardar_alarmas(self):
        try:
            with open(self.ruta_alarmas, "w", encoding="utf-8") as f:
                json.dump({
                    "alarmas": self.alarmas,
                    "sonido_alarma": self.sonido_alarma
                }, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def añadir_alarma(self, h, m, label="Alarma", sonido=None, dias=None, is_snooze=False):
        aid = int(time.time() * 1000)
        dias_validos = dias if (dias is not None and len(dias) > 0) else list(range(7))
        self.alarmas.append({
            "id": aid, "hora": int(h), "minuto": int(m),
            "label": label or "Alarma", "active": True,
            "sonido": sonido, "dias": dias_validos,
            "is_snooze": is_snooze
        })
        self.guardar_alarmas()
        return aid

    def eliminar_alarma(self, aid):
        self.alarmas = [a for a in self.alarmas if str(a["id"]) != str(aid) and a["id"] != aid]
        self.guardar_alarmas()

    def toggle_alarma(self, aid):
        for a in self.alarmas:
            if str(a["id"]) == str(aid) or a["id"] == aid:
                a["active"] = not a["active"]
                break
        self.guardar_alarmas()

    def editar_alarma(self, aid, h, m, label="Alarma", sonido=None, dias=None):
        for a in self.alarmas:
            if str(a["id"]) == str(aid) or a["id"] == aid:
                a["hora"] = int(h)
                a["minuto"] = int(m)
                a["label"] = label or "Alarma"
                if sonido is not None:
                    a["sonido"] = sonido
                if dias is not None:
                    a["dias"] = dias
                break
        self.guardar_alarmas()

    def posponer_alarma(self, minutos=2):
        self.alarmas = [a for a in self.alarmas if not a.get("is_snooze")]
        now = datetime.datetime.now() + datetime.timedelta(minutes=minutos)
        aid = int(time.time() * 1000)
        self.alarmas.append({
            "id": aid,
            "hora": now.hour,
            "minuto": now.minute,
            "label": f"😴 Posposición ({minutos} min)",
            "active": True,
            "dias": list(range(7)),
            "is_snooze": True
        })
        self.guardar_alarmas()
        return aid

    def limpiar_alarmas_pospuestas(self):
        self.alarmas = [a for a in self.alarmas if not a.get("is_snooze")]
        self.guardar_alarmas()

    def check_alarmas(self):
        now = datetime.datetime.now()
        dia_sem = now.isoweekday() - 1 # 0-6
        triggered = []
        has_snooze = False
        for a in self.alarmas:
            if a.get("active", True) and a["hora"] == now.hour and a["minuto"] == now.minute:
                dias = a.get("dias")
                if not dias or len(dias) == 0 or dia_sem in dias:
                    triggered.append(a)
                    if a.get("is_snooze"):
                        a["active"] = False
                        has_snooze = True
        if has_snooze:
            self.guardar_alarmas()
        return triggered

    # ── Ciudades Mundial ─────────────────────────────────────────────────
    def cargar_ciudades(self):
        if self.ruta_ciudades.exists():
            try:
                with open(self.ruta_ciudades, "r", encoding="utf-8") as f:
                    self.ciudades = json.load(f)
            except Exception:
                self.ciudades = self._ciudades_predeterminadas()
        else:
            self.ciudades = self._ciudades_predeterminadas()
            self.guardar_ciudades()

    def _ciudades_predeterminadas(self):
        return [
            {"nombre": "Nueva York", "timezone": "America/New_York", "bandera": "🇺🇸"},
            {"nombre": "Londres", "timezone": "Europe/London", "bandera": "🇬🇧"},
            {"nombre": "Madrid", "timezone": "Europe/Madrid", "bandera": "🇪🇸"},
            {"nombre": "Tokio", "timezone": "Asia/Tokyo", "bandera": "🇯🇵"},
            {"nombre": "Sídney", "timezone": "Australia/Sydney", "bandera": "🇦🇺"}
        ]

    def guardar_ciudades(self):
        try:
            with open(self.ruta_ciudades, "w", encoding="utf-8") as f:
                json.dump(self.ciudades, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def añadir_ciudad(self, nombre, timezone_str, bandera="🌐"):
        self.ciudades.append({"nombre": nombre, "timezone": timezone_str, "bandera": bandera})
        self.guardar_ciudades()

    def eliminar_ciudad(self, nombre):
        self.ciudades = [c for c in self.ciudades if c["nombre"] != nombre]
        self.guardar_ciudades()

    # ── Pomodoro Stats ───────────────────────────────────────────────────
    def cargar_pomodoro_stats(self):
        if self.ruta_pomodoro.exists():
            try:
                with open(self.ruta_pomodoro, "r", encoding="utf-8") as f:
                    self.pomodoro_stats = json.load(f)
            except Exception:
                self.pomodoro_stats = {"sesiones_hoy": 0, "minutos_enfoque": 0}

    def registrar_sesion_pomodoro(self, minutos=25):
        self.pomodoro_stats["sesiones_hoy"] = self.pomodoro_stats.get("sesiones_hoy", 0) + 1
        self.pomodoro_stats["minutos_enfoque"] = self.pomodoro_stats.get("minutos_enfoque", 0) + minutos
        try:
            with open(self.ruta_pomodoro, "w", encoding="utf-8") as f:
                json.dump(self.pomodoro_stats, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    # ── Cronómetro Logic ─────────────────────────────────────────────────
    def control_cronometro(self, action):
        if action == "start":
            self.crono_running = True
            self.crono_start_time = time.time() - self.crono_accum
        elif action == "pause":
            if self.crono_running:
                self.crono_accum = time.time() - self.crono_start_time
                self.crono_running = False
        elif action == "reset":
            self.crono_running = False
            self.crono_accum = 0
            self.laps = []

    def get_crono_time(self):
        if self.crono_running: return time.time() - self.crono_start_time
        return self.crono_accum

    def registrar_lap(self):
        t = self.get_crono_time()
        self.laps.append(t)
        return t

    # ── Calendario & Eventos ─────────────────────────────────────────────
    def cargar_eventos(self):
        if self.ruta_eventos.exists():
            try:
                with open(self.ruta_eventos, "r", encoding="utf-8") as f:
                    self.eventos = json.load(f)
            except Exception:
                self.eventos = []
        else:
            self.eventos = []

    def guardar_eventos(self):
        try:
            with open(self.ruta_eventos, "w", encoding="utf-8") as f:
                json.dump(self.eventos, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def añadir_evento(self, titulo, fecha_str, hora_str="09:00", categoria="General", descripcion="", color="#6366F1"):
        eid = int(time.time() * 1000)
        evento = {
            "id": eid,
            "titulo": titulo or "Nuevo Evento",
            "fecha": fecha_str,  # YYYY-MM-DD
            "hora": hora_str,    # HH:MM
            "categoria": categoria,
            "descripcion": descripcion,
            "color": color
        }
        self.eventos.append(evento)
        self.guardar_eventos()
        return evento

    def editar_evento(self, eid, titulo, fecha_str, hora_str="09:00", categoria="General", descripcion="", color="#6366F1"):
        for ev in self.eventos:
            if str(ev.get("id")) == str(eid):
                ev["titulo"] = titulo or "Evento"
                ev["fecha"] = fecha_str
                ev["hora"] = hora_str
                ev["categoria"] = categoria
                ev["descripcion"] = descripcion
                ev["color"] = color
                break
        self.guardar_eventos()

    def eliminar_evento(self, eid):
        self.eventos = [ev for ev in self.eventos if str(ev.get("id")) != str(eid)]
        self.guardar_eventos()

    def obtener_eventos_fecha(self, fecha_str):
        return [ev for ev in self.eventos if ev.get("fecha") == fecha_str]

    # ── Time Tracker (Registro de Actividades) ───────────────────────────
    def cargar_tracker(self):
        if self.ruta_tracker.exists():
            try:
                with open(self.ruta_tracker, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tracker_records = data.get("registros", [])
                    self.tracker_activo = data.get("activo", None)
            except Exception:
                self.tracker_records = []
                self.tracker_activo = None
        else:
            self.tracker_records = []
            self.tracker_activo = None

    def guardar_tracker(self):
        try:
            with open(self.ruta_tracker, "w", encoding="utf-8") as f:
                json.dump({
                    "registros": self.tracker_records,
                    "activo": self.tracker_activo
                }, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def iniciar_tarea_tracker(self, proyecto="General", descripcion=""):
        ahora = time.time()
        self.tracker_activo = {
            "id": int(ahora * 1000),
            "proyecto": proyecto.strip() or "General",
            "descripcion": descripcion.strip(),
            "inicio_ts": ahora,
            "inicio_str": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.guardar_tracker()
        return self.tracker_activo

    def detener_tarea_tracker(self):
        if not self.tracker_activo:
            return None
        fin_ts = time.time()
        inicio_ts = self.tracker_activo.get("inicio_ts", fin_ts)
        duracion_seg = max(1, int(fin_ts - inicio_ts))
        
        nuevo_registro = {
            "id": self.tracker_activo.get("id", int(fin_ts * 1000)),
            "proyecto": self.tracker_activo.get("proyecto", "General"),
            "descripcion": self.tracker_activo.get("descripcion", ""),
            "inicio_str": self.tracker_activo.get("inicio_str", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "fin_str": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duracion_seg": duracion_seg
        }
        self.tracker_records.insert(0, nuevo_registro)
        self.tracker_activo = None
        self.guardar_tracker()
        return nuevo_registro

    def eliminar_registro_tracker(self, rid):
        self.tracker_records = [r for r in self.tracker_records if str(r.get("id")) != str(rid)]
        self.guardar_tracker()

    def obtener_estadisticas_tracker(self):
        hoy_str = datetime.datetime.now().strftime("%Y-%m-%d")
        total_hoy = 0
        por_proyecto = {}
        for r in self.tracker_records:
            d_seg = r.get("duracion_seg", 0)
            proj = r.get("proyecto", "General")
            por_proyecto[proj] = por_proyecto.get(proj, 0) + d_seg
            if str(r.get("inicio_str", "")).startswith(hoy_str):
                total_hoy += d_seg
        return {
            "total_hoy_seg": total_hoy,
            "por_proyecto": por_proyecto,
            "total_general_seg": sum(por_proyecto.values())
        }
