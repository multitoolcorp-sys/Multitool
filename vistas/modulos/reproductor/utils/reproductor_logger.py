import os
import datetime

class ReproductorLogger:
    """
    Logger dedicado y aislado para el módulo Reproductor.
    Guarda todos los eventos de inicialización, plugins, buffers, estados, 
    volúmenes, seeks y descargas en 'vistas/modulos/reproductor/logs/reproductor.log'
    evitando saturar la terminal principal y los logs generales del sistema.
    """
    _log_path = None

    @classmethod
    def get_log_file(cls):
        if not cls._log_path:
            # Directorio base del módulo reproductor: vistas/modulos/reproductor
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logs_dir = os.path.join(base_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            cls._log_path = os.path.join(logs_dir, "reproductor.log")
        return cls._log_path

    @classmethod
    def log(cls, nivel, mensaje):
        try:
            log_file = cls.get_log_file()
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            line = f"[{ts}] [{nivel.upper()}] {mensaje}\n"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    @classmethod
    def info(cls, mensaje):
        cls.log("INFO", mensaje)

    @classmethod
    def warning(cls, mensaje):
        cls.log("WARNING", mensaje)

    @classmethod
    def error(cls, mensaje):
        cls.log("ERROR", mensaje)
