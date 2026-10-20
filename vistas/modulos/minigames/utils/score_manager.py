"""
ScoreManager — Gestor universal de puntuaciones, récords y balance de apuestas para MiniGames.
Mantiene sincronización bidireccional en tiempo real entre:
1. 'minigames_scores.json' (registro estructurado por minijuego con puntos_totales)
2. 'extras_scores.json' (compatibilidad con perfiles, historial y récords)
3. 'puntos_totales.txt' (puntos totales en texto plano legible)
Optimizado con caché en memoria de alto rendimiento para eliminar micro-congelamientos y lag.
"""
import json
from pathlib import Path

LISTA_JUEGOS = [
    "space_invaders", "galaga", "asteroids", "tetris", "pacman", "isaac",
    "buscaminas", "snake", "tres_en_raya", "memory", "ajedrez", "damas",
    "battleship", "adivina_quien", "ahorcado", "casino"
]

class ScoreManager:
    _instancias = {}
    _listeners = []

    @classmethod
    def registrar_listener(cls, callback):
        if callback not in cls._listeners:
            cls._listeners.append(callback)

    @classmethod
    def remover_listener(cls, callback):
        if callback in cls._listeners:
            cls._listeners.remove(callback)

    @classmethod
    def notificar_cambio(cls, nuevo_total=None):
        for cb in list(cls._listeners):
            try:
                cb(nuevo_total)
            except Exception:
                try:
                    cb()
                except Exception:
                    pass

    def __new__(cls, ruta_usuario=None):
        # Patrón Borg / Multitón por ruta para evitar recreaciones redundantes y escrituras en disco
        ruta_str = str(Path(ruta_usuario or ".").resolve())
        if ruta_str not in cls._instancias:
            inst = super().__new__(cls)
            cls._instancias[ruta_str] = inst
            inst._inicializado = False
        return cls._instancias[ruta_str]

    def __init__(self, ruta_usuario=None):
        if getattr(self, "_inicializado", False):
            return
        self._inicializado = True
        self.ruta_usuario = Path(ruta_usuario or ".")
        self.archivo_extras = self.ruta_usuario / "extras_scores.json"
        self.archivo_minigames = self.ruta_usuario / "minigames_scores.json"
        self.archivo_txt = self.ruta_usuario / "puntos_totales.txt"
        
        self.data_extras = {}
        self.data_minigames = {}
        self.data = {}
        self.sincronizar_archivos(forzar_escritura=False)

    def _leer_json(self, path):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                print(f"[ScoreManager] Error al leer {path.name}: {e}")
        return {}

    def _escribir_json(self, path, data):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ScoreManager] Error al guardar {path.name}: {e}")

    def _escribir_txt(self, total):
        try:
            self.archivo_txt.parent.mkdir(parents=True, exist_ok=True)
            with open(self.archivo_txt, "w", encoding="utf-8") as f:
                f.write(f"{int(total)}\n")
        except Exception as e:
            print(f"[ScoreManager] Error al guardar puntos_totales.txt: {e}")

    def sincronizar_archivos(self, forzar_escritura=True):
        """Sincroniza y fusiona en memoria extras_scores.json y minigames_scores.json."""
        extras = self._leer_json(self.archivo_extras)
        minigames = self._leer_json(self.archivo_minigames)

        # 1. Fusionar puntos individuales respetando el valor mayor existente
        for juego in LISTA_JUEGOS:
            clave_ext = f"{juego}_puntos"
            pts_ext = extras.get(clave_ext, 0)
            if not isinstance(pts_ext, (int, float)):
                pts_ext = 0

            sub_mg = minigames.get(juego, {})
            if isinstance(sub_mg, dict):
                pts_mg = sub_mg.get("puntos", 0)
            elif isinstance(sub_mg, (int, float)):
                pts_mg = int(sub_mg)
                sub_mg = {"puntos": pts_mg}
            else:
                pts_mg = 0
                sub_mg = {}

            pts_final = max(int(pts_ext), int(pts_mg))
            extras[clave_ext] = pts_final

            # Récord / Highscore
            clave_hs_ext = f"{juego}_highscore"
            hs_ext = extras.get(clave_hs_ext, 0)
            hs_mg = sub_mg.get("highscore") or sub_mg.get("max_score") or 0
            hs_final = max(int(hs_ext), int(hs_mg))
            if hs_final > 0:
                extras[clave_hs_ext] = hs_final

            sub_mg["puntos"] = pts_final
            if juego in ["space_invaders", "galaga", "asteroids", "tetris", "pacman", "isaac", "casino"]:
                sub_mg["highscore"] = hs_final
            elif juego == "snake":
                sub_mg.setdefault("max_score", hs_final)
            elif juego == "buscaminas":
                sub_mg.setdefault("partidas_ganadas", 0)
                sub_mg.setdefault("mejor_tiempo", None)
            elif juego in ["tres_en_raya", "ajedrez", "damas"]:
                sub_mg.setdefault("vs_ia_ganadas", 0)
                if juego == "tres_en_raya":
                    sub_mg.setdefault("vs_ia_perdidas", 0)
            elif juego == "memory":
                sub_mg.setdefault("mejor_movimientos", None)
            elif juego in ["battleship", "adivina_quien"]:
                sub_mg.setdefault("partidas_ganadas", 0)
            elif juego == "ahorcado":
                sub_mg.setdefault("palabras_adivinadas", 0)

            minigames[juego] = sub_mg

        # 2. Calcular total consolidado
        total = sum(int(extras.get(f"{j}_puntos", 0)) for j in LISTA_JUEGOS)

        extras["puntos_totales"] = total
        minigames["puntos_totales"] = total

        self.data_extras = extras
        self.data_minigames = minigames
        self.data = extras

        if forzar_escritura and self.ruta_usuario and self.ruta_usuario != Path("."):
            self.guardar()

    def cargar(self):
        return self.data_extras

    def guardar(self):
        """Guarda en disco los dos archivos JSON y el archivo de texto plano."""
        total = self.data_extras.get("puntos_totales", 0)
        if self.ruta_usuario and self.ruta_usuario != Path("."):
            self._escribir_json(self.archivo_extras, self.data_extras)
            self._escribir_json(self.archivo_minigames, self.data_minigames)
            self._escribir_txt(total)
        self.notificar_cambio(total)

    def sumar_puntos(self, juego, puntos_ganados, max_cap=None):
        """Suma puntos en memoria y persiste a disco sin lag."""
        pts = int(puntos_ganados)
        if max_cap is not None:
            pts = min(int(max_cap), max(0, pts))
        else:
            pts = max(0, pts)

        if pts <= 0:
            return self.get_puntos(juego)

        clave = f"{juego}_puntos"
        old_p = self.data_extras.get(clave, 0)
        nuevo_p = old_p + pts
        self.data_extras[clave] = nuevo_p

        if juego not in self.data_minigames or not isinstance(self.data_minigames[juego], dict):
            self.data_minigames[juego] = {}
        self.data_minigames[juego]["puntos"] = nuevo_p

        total = sum(int(self.data_extras.get(f"{j}_puntos", 0)) for j in LISTA_JUEGOS)
        self.data_extras["puntos_totales"] = total
        self.data_minigames["puntos_totales"] = total

        self.guardar()
        return nuevo_p

    def restar_puntos(self, juego, puntos_perdidos):
        """Resta puntos por apuestas perdidas en Casino tanto de extras como de minigames_scores."""
        pts_a_restar = max(0, int(puntos_perdidos))
        if pts_a_restar <= 0:
            return self.get_total_puntos()

        clave = f"{juego}_puntos"
        juego_p = self.data_extras.get(clave, 0)

        if juego_p >= pts_a_restar:
            self.data_extras[clave] = juego_p - pts_a_restar
        else:
            sobrante = pts_a_restar - juego_p
            self.data_extras[clave] = 0
            for k in LISTA_JUEGOS:
                if sobrante <= 0:
                    break
                ck = f"{k}_puntos"
                val = self.data_extras.get(ck, 0)
                if val > 0:
                    deducir = min(val, sobrante)
                    self.data_extras[ck] = val - deducir
                    sobrante -= deducir

        for j in LISTA_JUEGOS:
            if j not in self.data_minigames or not isinstance(self.data_minigames[j], dict):
                self.data_minigames[j] = {}
            self.data_minigames[j]["puntos"] = self.data_extras.get(f"{j}_puntos", 0)

        total = sum(int(self.data_extras.get(f"{j}_puntos", 0)) for j in LISTA_JUEGOS)
        self.data_extras["puntos_totales"] = total
        self.data_minigames["puntos_totales"] = total

        self.guardar()
        return total

    def set_puntos_totales(self, nuevo_total, juego="casino"):
        """Establece directamente los puntos totales (usado por comandos/trampas de consola)."""
        tot = max(0, int(nuevo_total))
        # Ajustar en el juego especificado o repartir
        for j in LISTA_JUEGOS:
            self.data_extras[f"{j}_puntos"] = 0
            if j in self.data_minigames and isinstance(self.data_minigames[j], dict):
                self.data_minigames[j]["puntos"] = 0
        
        self.data_extras[f"{juego}_puntos"] = tot
        if juego in self.data_minigames and isinstance(self.data_minigames[juego], dict):
            self.data_minigames[juego]["puntos"] = tot

        self.data_extras["puntos_totales"] = tot
        self.data_minigames["puntos_totales"] = tot
        self.guardar()
        return tot

    def get_puntos(self, juego=None):
        """Consulta ultra-rápida desde la memoria (0 disk I/O)."""
        if juego:
            return self.data_extras.get(f"{juego}_puntos", 0)
        return self.get_total_puntos()

    def get_total_puntos(self):
        """Retorna instantáneamente el saldo total desde memoria sin lag."""
        return max(0, int(self.data_extras.get("puntos_totales", 0)))

    def actualizar_highscore(self, juego, score):
        """Actualiza el récord más alto de un juego en ambos archivos."""
        clave = f"{juego}_highscore"
        actual = self.data_extras.get(clave, 0)
        if int(score) > actual:
            self.data_extras[clave] = int(score)
            if juego not in self.data_minigames or not isinstance(self.data_minigames[juego], dict):
                self.data_minigames[juego] = {}
            if "max_score" in self.data_minigames[juego]:
                self.data_minigames[juego]["max_score"] = int(score)
            else:
                self.data_minigames[juego]["highscore"] = int(score)
            self.guardar()
            return True
        return False
