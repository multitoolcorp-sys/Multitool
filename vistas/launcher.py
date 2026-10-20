import json
import logging
import datetime
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from vistas.vistas_login import AppMultitoolGUI, COLORES
from vistas.utils.seleccion import AccountSelector
from vistas.pantalla_carga import PantallaCarga
from vistas.utils.logs import JsonLogger

from controlador.utils.paths import get_data_path, get_user_path


class Launcher:

    def __init__(self):

        self.window = AppMultitoolGUI()
        self.cuentas_encontradas = []
        self.base_path = get_data_path()

        self.splash = None
        self.app_main = None

    # ─────────────────────────────────────────

    def start(self):

        self._buscar_cuentas()

        if self.cuentas_encontradas:
            self._mostrar_selector()
        else:
            self.window.show()

    # ─────────────────────────────────────────

    def _buscar_cuentas(self):

        cuentas_dir = self.base_path / "cuentas"

        if cuentas_dir.exists():
            for carpetita in cuentas_dir.iterdir():

                if carpetita.is_dir():

                    cfg = carpetita / "config.json"

                    if cfg.exists():

                        try:

                            from controlador.auth.crypto_utils import process_config_for_load
                            with open(cfg, "r", encoding="utf-8") as f:
                                data = process_config_for_load(json.load(f))

                            if data.get("login", False):
                                self.cuentas_encontradas.append(data)

                        except Exception as e:
                            logging.error(f"Error cargando config de {carpetita.name}: {e}")

    # ─────────────────────────────────────────

    def _mostrar_selector(self):
        JsonLogger.log_global("INFO", "Mostrando selector de cuentas", modulo="Selector")
        def on_selected(acc):

            try:

                user_path = get_user_path(acc["persona"])
                ruta_config = user_path / "config.json"
                if ruta_config.exists():
                    from controlador.auth.crypto_utils import process_config_for_load, process_config_for_save
                    with open(ruta_config, "r", encoding="utf-8") as f:
                        config_data = process_config_for_load(json.load(f))

                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    config_data["ultimo_acceso"] = now_str

                    with open(ruta_config, "w", encoding="utf-8") as f:
                        json.dump(process_config_for_save(config_data), f, indent=4)

                    # Registrar evento en auth_sesion_log.json
                    try:
                        log_path = user_path / "auth_sesion_log.json"
                        entries = []
                        if log_path.exists():
                            with open(log_path, "r", encoding="utf-8") as f:
                                entries = json.load(f)
                        entries.append({
                            "fecha": now_str,
                            "evento": "Inicio de sesión",
                            "estado": "Éxito"
                        })
                        with open(log_path, "w", encoding="utf-8") as f:
                            json.dump(entries, f, indent=4)
                    except Exception as e_log:
                        logging.error(f"Error escribiendo auth_sesion_log.json: {e_log}")

            except Exception as e:
                logging.error(f"Error actualizando acceso rápido: {e}")

            self._iniciar_multitool(acc)

        self.selector = AccountSelector(None, self.cuentas_encontradas, on_selected, COLORES)

        self.selector.finished.connect(
            lambda: self.window.show()
            if not self.window.isVisible() and not hasattr(self.window, 'app_main')
            else None
        )

        self.selector.show()

    # ─────────────────────────────────────────

    def _iniciar_multitool(self, acc):
        usuario = acc["usuario"]
        persona = acc["persona"]
        JsonLogger.log_global("INFO", f"Accediendo con cuenta: {usuario}", modulo="Sesión")

        # Cerrar login / registro
        if self.window:
            self.window.hide()

        if hasattr(self, "selector"):
            self.selector.close()

        # Crear splash
        self.splash = PantallaCarga(auto_play=False)
        self.splash.show()
        self.splash.raise_()
        self.splash.activateWindow()

        QApplication.processEvents()

        # Delay pequeño para que se renderice
        QTimer.singleShot(150, lambda: self._crear_app(usuario, persona))
    def _crear_app(self, usuario, persona):

        from vistas.cargar import AppMultitareasGUI

        try:
            # Crear app pero NO mostrarla
            self.app_main = AppMultitareasGUI(
                usuario,
                persona,
                callback_progreso=self.splash.actualizar
            )

            # Esperar a que el progreso llegue a 100
            QTimer.singleShot(200, self._verificar_carga)

        except Exception as e:

            logging.error(f"Error iniciando Multitool: {e}")

            if self.splash:
                self.splash.close()

            self.window.show()
    def _verificar_carga(self):

        if self.splash.progress.value() >= 100:

            self.splash.close()

            self.app_main.show()
            self.app_main.raise_()
            self.app_main.activateWindow()

        else:
            QTimer.singleShot(100, self._verificar_carga)
