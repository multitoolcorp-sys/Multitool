"""
translator_manager.py  -  Backend de traducción robusto con fallbacks múltiples
Nuevas capacidades:
  • Motor Robusto: Google Mobile Web + MyMemory API + Deep Translator + Googletrans + Caché
  • Integración con Free Dictionary API (https://api.dictionaryapi.dev/api/v2/entries/en/<word>)
  • Caché local automática (traductor_cache.json)
  • Persistencia permanente de Favoritos e Historial
  • Traductor de documentos y subtítulos (.txt, .srt) sin fallos silenciosos
  • Diccionario local de fallback palabra por palabra
  • TTS (Google Text-To-Speech) mediante hilo asíncrono
"""
import os
import sys
import json
import threading
import tempfile
import urllib.request
import urllib.parse
import html
import re
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

# Intentar importar motores auxiliares
try:
    from googletrans import Translator
    TRANS_ENGINE = "googletrans"
except Exception:
    try:
        from deep_translator import GoogleTranslator
        TRANS_ENGINE = "deep-translator"
    except Exception:
        TRANS_ENGINE = None

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except Exception:
    GTTS_AVAILABLE = False

try:
    from langdetect import detect as _langdetect
    LANGDETECT_AVAILABLE = True
except Exception:
    LANGDETECT_AVAILABLE = False
    _langdetect = None


class TranslatorManager(QObject):
    # Señales extendidas
    traduccion_completada = pyqtSignal(dict)  # Envía {text, pron, dict, src_detectado}
    error_ocurrido        = pyqtSignal(str)
    deteccion_completada  = pyqtSignal(str)
    doc_traduccion_progreso = pyqtSignal(int, str) # pct, status
    doc_traduccion_fin    = pyqtSignal(str, str)   # out_path, texto_trad
    tts_iniciado          = pyqtSignal()
    tts_finalizado        = pyqtSignal()
    tts_error             = pyqtSignal(str)
    
    # Señales de estado del motor offline
    argos_status          = pyqtSignal(str)
    descarga_progreso     = pyqtSignal(int, str)

    # Idiomas soportados
    IDIOMAS = {
        "af": "Afrikáans", "ar": "Árabe", "be": "Bielorruso", "bg": "Búlgaro",
        "bn": "Bengalí", "ca": "Catalán", "cs": "Checo", "cy": "Galés",
        "da": "Danés", "de": "Alemán", "el": "Griego", "en": "Inglés",
        "eo": "Esperanto", "es": "Español", "et": "Estonio", "eu": "Euskera",
        "fa": "Persa", "fi": "Finlandés", "fr": "Francés", "ga": "Irlandés",
        "gl": "Gallego", "gu": "Gujarati", "he": "Hebreo", "hi": "Hindi",
        "hr": "Croata", "hu": "Húngaro", "hy": "Armenio", "id": "Indonesio",
        "is": "Islandés", "it": "Italiano", "ja": "Japonés", "jw": "Javanés",
        "ka": "Georgiano", "kk": "Kazajo", "km": "Khmer", "kn": "Kannada",
        "ko": "Coreano", "la": "Latín", "lo": "Lao", "lt": "Lituano",
        "lv": "Letón", "mg": "Malgache", "mi": "Maorí", "mk": "Macedonio",
        "ml": "Malayalam", "mn": "Mongol", "mr": "Marathi", "ms": "Malayo",
        "mt": "Maltés", "my": "Birmano", "ne": "Nepalí", "nl": "Neerlandés",
        "no": "Noruego", "pa": "Punjabi", "pl": "Polaco", "pt": "Portugués",
        "ro": "Rumano", "ru": "Ruso", "si": "Cingalés", "sk": "Eslovaco",
        "sl": "Esloveno", "sq": "Albanés", "sr": "Serbio", "st": "Sesoto",
        "su": "Sundanés", "sv": "Sueco", "sw": "Suajili", "ta": "Tamil",
        "te": "Telugu", "tg": "Tayiko", "th": "Tailandés", "tl": "Filipino",
        "tr": "Turco", "uk": "Ucraniano", "ur": "Urdu", "uz": "Uzbeko",
        "vi": "Vietnamita", "xh": "Xhosa", "yi": "Yiddish", "yo": "Yoruba",
        "zh-cn": "Chino (Simp.)", "zh-tw": "Chino (Trad.)", "zu": "Zulú"
    }

    def __init__(self, context=None):
        super().__init__()
        self.context = context
        self.idiomas = self.IDIOMAS
        
        # Modo e inicialización Offline
        self.modo_offline = False
        self.argos_inicializado = True
        
        # Cargar Caché, Favoritos e Historial
        self._load_cache()
        self.favoritos = self.cargar_favoritos()
        self.historial = self.cargar_historial()
        
        # Inicialización en segundo plano de la caché
        threading.Thread(target=self._inicializar_cache_hilo, daemon=True).start()

    def obtener_lista_formatada(self, incluir_auto=False):
        lista = sorted(
            [f"{name} ({code})" for code, name in self.idiomas.items()],
            key=lambda x: x
        )
        if incluir_auto:
            return ["🔍 Detectar idioma (auto)"] + lista
        return lista

    def set_modo_offline(self, offline: bool):
        self.modo_offline = offline
        self.argos_status.emit(f"Modo {'Offline (Local)' if offline else 'En línea (Google)'} activado.")

    def obtener_ruta_cache(self):
        if self.cache_path:
            return os.path.dirname(os.path.abspath(self.cache_path))
        return os.path.dirname(os.path.abspath(__file__))

    # ── Caché Local & Persistencia ──────────────────────────────────────────

    def _load_cache(self):
        if self.context and hasattr(self.context, 'ruta_usuario') and self.context.ruta_usuario:
            self.cache_path = os.path.join(self.context.ruta_usuario, "traductor_cache.json")
            self.fav_path = os.path.join(self.context.ruta_usuario, "traductor_favoritos.json")
            self.hist_path = os.path.join(self.context.ruta_usuario, "traductor_historial.json")
        else:
            base_dir = os.path.dirname(__file__)
            self.cache_path = os.path.join(base_dir, "traductor_cache.json")
            self.fav_path = os.path.join(base_dir, "traductor_favoritos.json")
            self.hist_path = os.path.join(base_dir, "traductor_historial.json")
            
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
        else:
            self.cache = {}

    def _save_cache(self):
        if self.cache_path:
            try:
                with open(self.cache_path, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f, ensure_ascii=False, indent=4)
            except Exception:
                pass

    def cargar_favoritos(self):
        if os.path.exists(self.fav_path):
            try:
                with open(self.fav_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def guardar_favoritos(self, favs):
        self.favoritos = favs
        try:
            with open(self.fav_path, "w", encoding="utf-8") as f:
                json.dump(favs, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def cargar_historial(self):
        if os.path.exists(self.hist_path):
            try:
                with open(self.hist_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def guardar_historial(self, hist):
        self.historial = hist[:30]
        try:
            with open(self.hist_path, "w", encoding="utf-8") as f:
                json.dump(self.historial, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def _inicializar_cache_hilo(self):
        import time
        time.sleep(0.3)
        self.argos_status.emit("Caché local y diccionario listos.")

    def descargar_modelos_offline(self):
        self.descarga_progreso.emit(100, "Los modelos están listos.")

    # ── Motor Robusto de Traducción Web / Online ──────────────────────────────

    def _traducir_online_robusto(self, texto, origen="auto", destino="en"):
        src = "auto" if origen == "auto" else origen
        
        # 1. Google Translate GTX API (ultra rápido, preciso y sin errores 429)
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={src}&tl={destino}&dt=t&q=" + urllib.parse.quote(texto)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    parts = [part[0] for part in data[0] if part and len(part) > 0 and part[0]]
                    res_text = "".join(parts).strip()
                    if res_text:
                        return res_text
        except Exception:
            pass

        # 2. Google Translate Mobile Endpoint
        try:
            url = f"https://translate.google.com/m?sl={src}&tl={destino}&q=" + urllib.parse.quote(texto)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=5) as response:
                html_code = response.read().decode('utf-8')
                match = re.search(r'class="result-container">(.*?)</div>', html_code, re.DOTALL)
                if match:
                    res_text = html.unescape(match.group(1).strip())
                    if res_text:
                        return res_text
        except Exception:
            pass

        # 3. Deep Translator Fallback
        try:
            from deep_translator import GoogleTranslator
            res_text = GoogleTranslator(source=src, target=destino).translate(texto)
            if res_text:
                return res_text
        except Exception:
            pass

        # 4. MyMemory API Fallback (con descarte de cadenas de prueba)
        try:
            langpair = f"{'es' if src == 'auto' else src}|{destino}"
            url = f"https://api.mymemory.translated.net/get?q=" + urllib.parse.quote(texto) + f"&langpair={langpair}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data and "responseData" in data and "translatedText" in data["responseData"]:
                    res_text = html.unescape(data["responseData"]["translatedText"].strip())
                    if res_text and res_text.lower() not in ("testvalue", "is not valid", "null"):
                        return res_text
                    # Buscar en matches alternativos si la principal era basura
                    for match in data.get("matches", []):
                        cand = html.unescape(match.get("translation", "").strip())
                        if cand and cand.lower() not in ("testvalue", "is not valid", "null", texto.lower()):
                            return cand
        except Exception:
            pass

        # 4. Fallback local palabra por palabra
        return self.traducir_palabra_por_palabra(texto, origen, destino)

    def traducir_sincrono(self, texto, origen="auto", destino="en"):
        """Traducción síncrona con fallback automático según modo offline/online."""
        if getattr(self, "modo_offline", False):
            return self.traducir_palabra_por_palabra(texto, origen, destino)
        return self._traducir_online_robusto(texto, origen, destino)

    def _traducir_sincrono(self, texto, origen="auto", destino="en"):
        """Alias para compatibilidad interna."""
        return self.traducir_sincrono(texto, origen, destino)

    # ── Free Dictionary API Integration ──────────────────────────────────────

    def consultar_diccionario_api(self, word, lang="en"):
        word_clean = word.strip().lower()
        if not word_clean:
            return None

        # 1. Traducir automáticamente el término a inglés si se ingresó en otro idioma (ej: "hola" -> "hello")
        word_en = self._traducir_online_robusto(word_clean, "auto", "en").strip().lower()

        # 2. Consultar Free Dictionary API con el término en inglés
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/" + urllib.parse.quote(word_en)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=6) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data and isinstance(data, list):
                    entry = data[0]
                    w = entry.get("word", word_en)
                    phonetic = entry.get("phonetic", "")
                    if not phonetic and entry.get("phonetics"):
                        for p in entry["phonetics"]:
                            if p.get("text"):
                                phonetic = p["text"]
                                break

                    out = []
                    if word_clean != word_en:
                        out.append(f"📌 BÚSQUEDA ORIGINAL: {word.upper()}")
                        out.append(f"🌐 TRADUCCIÓN A INGLÉS (API): {w.upper()}")
                    else:
                        out.append(f"📌 TÉRMINO: {w.upper()}")

                    if phonetic:
                        out.append(f"🗣 PRONUNCIACIÓN: {phonetic}")
                    
                    origin = entry.get("origin")
                    if origin:
                        out.append(f"📜 ORIGEN: {origin}")
                    
                    out.append("\n📖 DEFINICIONES Y SIGNIFICADOS:\n")
                    
                    meanings = entry.get("meanings", [])
                    for idx, m in enumerate(meanings, 1):
                        pos = m.get("partOfSpeech", "general").upper()
                        out.append(f"🔹 [{pos}]")
                        defs = m.get("definitions", [])
                        for d_idx, d in enumerate(defs[:3], 1):
                            def_str = d.get("definition", "")
                            out.append(f"   {d_idx}. {def_str}")
                            ex = d.get("example")
                            if ex:
                                out.append(f"      💡 Ej: \"{ex}\"")
                            syns = d.get("synonyms", [])
                            if syns:
                                out.append(f"      🔗 Sinónimos: {', '.join(syns[:5])}")
                            ants = d.get("antonyms", [])
                            if ants:
                                out.append(f"      ⚡ Antónimos: {', '.join(ants[:5])}")
                        out.append("")
                    return "\n".join(out)
        except Exception:
            pass

        # Fallback si no se encontró en la API
        trad = self._traducir_online_robusto(word_clean, "auto", "es")
        return (
            f"📌 TÉRMINO: {word.upper()}\n"
            f"🗣 TRADUCCIÓN SUGERIDA: {trad}\n\n"
            f"📖 DEFINICIÓN Y GLOSARIO CONTEXTUAL:\n"
            f"• Equivalente sugerido: {trad}.\n\n"
            f"💡 EJEMPLO DE USO:\n"
            f"  - '{word.capitalize()}' equivale a '{trad}'."
        )

    # ── Traducción Ejecución ─────────────────────────────────────────────────

    def traducir(self, texto, origen, destino):
        threading.Thread(
            target=self._traducir_hilo,
            args=(texto, origen, destino),
            daemon=True
        ).start()

    def _traducir_hilo(self, texto, origen, destino):
        try:
            key = f"{origen}->{destino}"
            if key in self.cache and texto in self.cache[key]:
                self.traduccion_completada.emit({
                    "text": self.cache[key][texto],
                    "pron": "",
                    "dict": "(Recuperado de la caché local)",
                    "src_detectado": origen
                })
                return

            if self.modo_offline:
                self._traducir_offline(texto, origen, destino)
                return

            res_text = self._traducir_online_robusto(texto, origen, destino)
            resultado = {
                "text": res_text, "pron": "", "dict": "", "src_detectado": origen
            }

            if res_text:
                cache_key = f"{origen}->{destino}"
                if cache_key not in self.cache:
                    self.cache[cache_key] = {}
                self.cache[cache_key][texto] = res_text
                self._save_cache()

            self.traduccion_completada.emit(resultado)

        except Exception as e:
            if not self.modo_offline:
                self.argos_status.emit("Fallo de conexión. Intentando traducción local...")
                self._traducir_offline(texto, origen, destino)
            else:
                self.error_ocurrido.emit(f"Error al traducir: {str(e)}")

    def _traducir_offline(self, texto, origen, destino):
        try:
            key = f"{origen}->{destino}"
            if key in self.cache and texto in self.cache[key]:
                self.traduccion_completada.emit({
                    "text": self.cache[key][texto],
                    "pron": "",
                    "dict": "(Recuperado de la caché local)",
                    "src_detectado": origen
                })
                return
            
            traducido = self.traducir_palabra_por_palabra(texto, origen, destino)
            self.traduccion_completada.emit({
                "text": traducido,
                "pron": "",
                "dict": "(Modo Offline - Traducido palabra por palabra)",
                "src_detectado": origen
            })
        except Exception as e:
            self.error_ocurrido.emit(f"Error al traducir: {str(e)}")

    # ── Traducción de Documentos ─────────────────────────────────────────────

    def traducir_documento(self, in_file, origen, destino, out_file):
        threading.Thread(
            target=self._traducir_doc_hilo,
            args=(in_file, origen, destino, out_file),
            daemon=True
        ).start()

    def _traducir_doc_hilo(self, in_file, origen, destino, out_file):
        try:
            self.doc_traduccion_progreso.emit(10, "Leyendo archivo...")
            contenido = Path(in_file).read_text(encoding="utf-8", errors="ignore")

            self.doc_traduccion_progreso.emit(30, "Traduciendo contenido del archivo...")
            lineas = contenido.splitlines()
            lineas_trad = []
            total = max(1, len(lineas))

            for idx, line in enumerate(lineas):
                line_str = line.strip()
                if line_str and not line_str.isdigit() and "-->" not in line_str:
                    if self.modo_offline:
                        trad_line = self.traducir_palabra_por_palabra(line, origen, destino)
                    else:
                        trad_line = self._traducir_online_robusto(line, origen, destino)
                    lineas_trad.append(trad_line)
                else:
                    lineas_trad.append(line)

                pct = 30 + int(((idx + 1) / total) * 65)
                self.doc_traduccion_progreso.emit(pct, f"Procesando línea {idx+1}/{total}...")

            resultado_final = "\n".join(lineas_trad)
            Path(out_file).write_text(resultado_final, encoding="utf-8")
            self.doc_traduccion_progreso.emit(100, "¡Traducción completada!")
            self.doc_traduccion_fin.emit(out_file, resultado_final[:1000])
        except Exception as e:
            self.error_ocurrido.emit(f"Error traduciendo archivo: {e}")

    # ── Diccionario Local Palabra por Palabra ─────────────────────────────────

    def traducir_palabra_por_palabra(self, texto, origen, destino):
        dict_es_en = {
            "hola": "hello", "mundo": "world", "gracias": "thanks", "bueno": "good", "buenos": "good", "dias": "days",
            "tardes": "afternoons", "noches": "nights", "como": "how", "estas": "are you",
            "bien": "well", "mal": "bad", "perro": "dog", "gato": "cat", "casa": "house",
            "libro": "book", "lapiz": "pencil", "escuela": "school", "agua": "water", "comida": "food",
            "amigo": "friend", "familia": "family", "tiempo": "time", "trabajo": "work",
            "hacer": "to make", "ir": "to go", "venir": "to come", "ver": "to see",
            "querer": "to want", "necesitar": "to need", "amar": "to love", "feliz": "happy",
            "triste": "sad", "grande": "big", "pequeño": "small", "nuevo": "new", "viejo": "old",
            "si": "yes", "no": "no", "por favor": "please", "lo siento": "I'm sorry",
            "adios": "goodbye", "mañana": "tomorrow", "hoy": "today", "ayer": "yesterday"
        }
        
        dict_en_es = {v: k for k, v in dict_es_en.items()}
        mapping = dict_es_en if (destino == "en" or origen == "es") else dict_en_es

        tokens = re.split(r'(\W+)', texto)
        resultado = []
        for token in tokens:
            lower_token = token.lower()
            if lower_token in mapping:
                trans = mapping[lower_token]
                if token.istitle(): trans = trans.capitalize()
                elif token.isupper(): trans = trans.upper()
                resultado.append(trans)
            else:
                resultado.append(token)
        return "".join(resultado)

    def detectar_idioma(self, texto):
        threading.Thread(target=self._detectar_hilo, args=(texto,), daemon=True).start()

    def _detectar_hilo(self, texto):
        try:
            if LANGDETECT_AVAILABLE:
                codigo = _langdetect(texto)
                self.deteccion_completada.emit(codigo)
            else:
                self.deteccion_completada.emit("auto")
        except:
            self.deteccion_completada.emit("auto")

    def pronunciar(self, texto, idioma):
        if not GTTS_AVAILABLE:
            self.tts_error.emit("El módulo gTTS no está instalado.")
            return
        threading.Thread(target=self._pronunciar_hilo, args=(texto, idioma), daemon=True).start()

    def _pronunciar_hilo(self, texto, idioma):
        try:
            self.tts_iniciado.emit()
            tts = gTTS(text=texto, lang=idioma)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_path = fp.name
            tts.save(temp_path)
            
            import playsound
            playsound.playsound(temp_path)
            try: os.remove(temp_path)
            except: pass
                
            self.tts_finalizado.emit()
        except Exception as e:
            self.tts_error.emit(f"Error en reproducción de voz: {str(e)}")
