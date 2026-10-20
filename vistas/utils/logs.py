import os
import json
import datetime
import zipfile
import sys
import io
from pathlib import Path


class JsonLogger:
    _instancia = None

    @staticmethod
    def log_global(nivel, mensaje, modulo="Sistema"):
        if JsonLogger._instancia:
            JsonLogger._instancia.log(nivel, mensaje, modulo)
        else:
            # Fallback a logging estándar si no hay instancia personalizada
            import logging
            if nivel == "INFO": logging.info(f"[{modulo}] {mensaje}")
            elif nivel == "ERROR": logging.error(f"[{modulo}] {mensaje}")

    def __init__(self, ruta_usuario):
        self.ruta_logs = Path(ruta_usuario) / "logs"
        self.ruta_logs.mkdir(parents=True, exist_ok=True)

        self.fecha_actual = datetime.date.today().isoformat()
        self.archivo_actual = self.ruta_logs / f"{self.fecha_actual}.json"

        self._rotar_logs_antiguos()
        self._setup_streams()
        
        # Registrar esta instancia como la activa
        JsonLogger._instancia = self

    # ─────────────────────────────────────────────

    def _rotar_logs_antiguos(self):
        for item in self.ruta_logs.glob("*.json"):
            if item.stem != self.fecha_actual:
                self._archivar_log(item)

    def _archivar_log(self, archivo_path):
        zip_path = archivo_path.with_suffix(".zip")
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(archivo_path, archivo_path.name)
            archivo_path.unlink()
        except Exception:
            pass  # evitar romper la app por logs

    # ─────────────────────────────────────────────

    def log(self, nivel, mensaje, modulo="Sistema"):
        mensaje = str(mensaje)

        entrada = {
            "timestamp": datetime.datetime.now().isoformat(),
            "nivel": nivel,
            "modulo": modulo,
            "mensaje": mensaje
        }

        # 🔹 imprimir en consola ORIGINAL si existe
        try:
            if hasattr(self, "old_stdout") and self.old_stdout:
                self.old_stdout.write(f"[{nivel}] [{modulo}] {mensaje}\n")
        except Exception:
            pass

        # 🔹 guardar en JSON
        try:
            logs = []

            if self.archivo_actual.exists():
                try:
                    with open(self.archivo_actual, "r", encoding="utf-8") as f:
                        logs = json.load(f)
                except Exception:
                    logs = []

            logs.append(entrada)

            with open(self.archivo_actual, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=4, ensure_ascii=False)

        except Exception:
            # nunca romper la app por logs
            try:
                if hasattr(self, "old_stdout") and self.old_stdout:
                    self.old_stdout.write("[ERROR] Fallo guardando log\n")
            except:
                pass

    # ─────────────────────────────────────────────

    def _setup_streams(self):
        # 🔥 IMPORTANTE: fallback seguro para exe sin consola
        self.old_stdout = sys.stdout or sys.__stdout__ or io.StringIO()
        self.old_stderr = sys.stderr or sys.__stderr__ or io.StringIO()

        sys.stdout = StreamLogger(self, "INFO", self.old_stdout)
        sys.stderr = StreamLogger(self, "ERROR", self.old_stderr)


# ─────────────────────────────────────────────


class StreamLogger:
    def __init__(self, logger, nivel, terminal):
        self.logger = logger
        self.nivel = nivel
        self.terminal = terminal if terminal else io.StringIO()

    def write(self, message):
        if not message or message.strip() == "":
            return

        # 🔹 enviar al JSON log
        try:
            self.logger.log(self.nivel, message.strip(), modulo="Terminal")
        except Exception:
            pass

        # 🔹 escribir en terminal real si existe
        try:
            if self.terminal:
                self.terminal.write(message)
        except Exception:
            pass

    def flush(self):
        try:
            if self.terminal:
                self.terminal.flush()
        except Exception:
            pass
