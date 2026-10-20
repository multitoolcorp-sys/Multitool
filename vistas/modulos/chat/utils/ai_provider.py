import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, QObject

class AIConfigManager:
    """Gestor de configuración y almacenamiento seguro de claves API"""
    
    DEFAULT_CONFIG = {
        "provider": "ollama",          # "ollama", "openai", "groq", "deepseek", "gemini", "custom"
        "ollama_url": "http://127.0.0.1:11434",
        "selected_model": "llama3:latest",
        "temperature": 0.7,
        "pii_filter_enabled": True,
        "api_keys": {
            "openai": "",
            "groq": "",
            "deepseek": "",
            "gemini": "",
            "custom": ""
        },
        "custom_endpoint": "https://api.openai.com/v1"
    }

    def __init__(self, ruta_usuario=None):
        self.ruta_usuario = Path(ruta_usuario) if ruta_usuario else Path.home() / ".multitool"
        self.config_file = self.ruta_usuario / "ai_config.json"
        self.config = self.load_config()

    def load_config(self) -> dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cfg = self.DEFAULT_CONFIG.copy()
                    cfg.update(data)
                    return cfg
            except Exception:
                pass
        return self.DEFAULT_CONFIG.copy()

    def save_config(self, new_config: dict):
        self.config.update(new_config)
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[AI-CONFIG] Error al guardar configuración de IA: {e}")


def check_ollama_models(ollama_url="http://127.0.0.1:11434") -> list[str]:
    """Retorna la lista de modelos de Ollama instalados localmente"""
    try:
        url = f"{ollama_url.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, headers={"User-Agent": "MultiTool-AI/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name") for m in data.get("models", []) if m.get("name")]
            return models if models else ["llama3"]
    except Exception:
        return []


class AIWorkerThread(QThread):
    """Hilo secundario asíncrono para generar respuestas de IA sin congelar la interfaz gráfica"""
    chunk_received = pyqtSignal(str)
    finished_response = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, provider: str, model: str, prompt: str = "", system_prompt: str = "",
                 config: dict = None, temperature: float = 0.7, messages: list = None):
        super().__init__()
        self.provider = provider
        self.model = model
        self.prompt = prompt
        self.system_prompt = system_prompt
        self.config = config or {}
        self.temperature = temperature
        self.messages = messages or []

    def run(self):
        try:
            if self.provider == "ollama":
                self._run_ollama()
            elif self.provider in ("openai", "groq", "deepseek", "gemini", "custom"):
                self._run_openai_compatible()
            else:
                self.error_occurred.emit(f"Proveedor de IA desconocido: {self.provider}")
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _run_ollama(self):
        url = f"{self.config.get('ollama_url', 'http://127.0.0.1:11434').rstrip('/')}/api/chat"
        
        msgs = []
        if self.system_prompt:
            msgs.append({"role": "system", "content": self.system_prompt})
        if self.messages:
            for m in self.messages:
                msgs.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        elif self.prompt:
            msgs.append({"role": "user", "content": self.prompt})

        payload = {
            "model": self.model or "llama3",
            "messages": msgs,
            "options": {
                "temperature": self.temperature,
                "num_predict": 512,
                "num_ctx": 4096
            },
            "keep_alive": "30m",
            "stream": True
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers={
            "Content-Type": "application/json",
            "User-Agent": "MultiTool-AI/1.0"
        })

        full_text = ""
        try:
            with urllib.request.urlopen(req, timeout=240) as resp:
                for line in resp:
                    if self.isInterruptionRequested():
                        break
                    if line:
                        chunk_data = json.loads(line.decode("utf-8"))
                        text_chunk = chunk_data.get("message", {}).get("content", "") or chunk_data.get("response", "")
                        if text_chunk:
                            full_text += text_chunk
                            self.chunk_received.emit(text_chunk)
                        if chunk_data.get("done", False):
                            break
            self.finished_response.emit(full_text)
        except TimeoutError:
            self.error_occurred.emit(
                "⏳ <b>Tiempo de espera agotado (Timeout):</b> Ollama local tardó más de lo esperado en procesar los archivos en la CPU."
            )
        except urllib.error.URLError as e:
            if "timed out" in str(e).lower():
                self.error_occurred.emit(
                    "⏳ <b>Tiempo de espera agotado:</b> Ollama tardó más tiempo del esperado en procesar el prompt/archivo en la CPU."
                )
            else:
                self.error_occurred.emit(
                    f"No se pudo conectar al servidor Ollama local ({self.config.get('ollama_url', 'http://127.0.0.1:11434')}).\n\n"
                    f"💡 Verifica que Ollama esté iniciado en tu equipo con 'ollama run llama3' o selecciona un proveedor en la Nube (Groq, OpenAI, Gemini) en ⚙️ Ajustes."
                )

    def _run_openai_compatible(self):
        api_keys = self.config.get("api_keys", {})
        api_key = api_keys.get(self.provider, "")
        
        # Carga automática de token Google OAuth PKCE para Gemini si no hay API Key manual
        if self.provider == "gemini" and not api_key:
            try:
                from vistas.modulos.navegador.utils.oauth_pkce import GoogleOAuthManager
                oauth_mgr = GoogleOAuthManager(self.config.get("ruta_usuario"))
                sess = oauth_mgr.load_session()
                if sess and sess.get("access_token"):
                    api_key = sess.get("access_token")
            except Exception as e:
                print(f"[AI-PROVIDER] No se pudo cargar la sesión OAuth para Gemini: {e}")

        endpoints = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "deepseek": "https://api.deepseek.com/v1/chat/completions",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "custom": f"{self.config.get('custom_endpoint', 'https://api.openai.com/v1').rstrip('/')}/chat/completions"
        }

        url = endpoints.get(self.provider, endpoints["openai"])
        if not api_key and self.provider != "custom":
            if self.provider == "gemini":
                self.error_occurred.emit(
                    "No se ha configurado la API Key para GEMINI ni iniciado sesión con Google OAuth.\n\n"
                    "💡 Presiona 🔑 Google OAuth en la barra superior para vincular tu cuenta en 1 clic o ingresa tu clave en ⚙️ Ajustes."
                )
            else:
                self.error_occurred.emit(
                    f"No se ha configurado la API Key para {self.provider.upper()}.\n\n"
                    f"💡 Presiona ⚙️ Ajustes de IA para ingresarla u obtener una clave gratuita en 1 clic."
                )
            return

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        if self.messages:
            for m in self.messages:
                messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        elif self.prompt:
            messages.append({"role": "user", "content": self.prompt})

        payload = {
            "model": self.model or "gpt-3.5-turbo",
            "messages": messages,
            "temperature": self.temperature,
            "stream": True
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "MultiTool-AI/1.0"
        }

        req = urllib.request.Request(url, data=data_bytes, headers=headers)
        full_text = ""

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                for line in resp:
                    if self.isInterruptionRequested():
                        break
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        json_str = line_str[6:].strip()
                        if json_str == "[DONE]":
                            break
                        try:
                            chunk_obj = json.loads(json_str)
                            choices = chunk_obj.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content_chunk = delta.get("content", "")
                                if content_chunk:
                                    full_text += content_chunk
                                    self.chunk_received.emit(content_chunk)
                        except Exception:
                            pass
            self.finished_response.emit(full_text)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            self.error_occurred.emit(f"Error HTTP {e.code} de {self.provider.upper()}: {err_body}")
