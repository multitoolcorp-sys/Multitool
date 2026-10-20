import os
import json
import importlib.util
import datetime
import sys
from pathlib import Path
from controlador.utils.paths import get_user_path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from vistas.gui import BaseAppGUI
from vistas.utils.app_context import AppContext
from vistas.utils.logs import JsonLogger
from vistas.configurations import (
    discover_modules_and_plugins,
    DynamicModuleContainer
)

# ─────────────────────────────────────────────────────────────
#  HILO DE CARGA  (importación pesada off-main-thread)
# ─────────────────────────────────────────────────────────────

class ModuloLoaderThread(QThread):
    """
    Importa los módulos (importlib.util.spec_from_file_location + exec_module) en un hilo secundario
    para que el QTimer de la PantallaCarga siga funcionando y la barra
    de progreso nunca se congele.

    Sólo hace las importaciones; la instanciación de widgets Qt
    se hace después en el hilo principal a través de la señal `terminado`.
    """

    progreso = pyqtSignal(int, str)   # (porcentaje, texto)
    terminado = pyqtSignal(list)      # lista completa de módulos con .cls cargado

    def __init__(self, modulos_encontrados, logger):
        super().__init__()
        self.modulos_encontrados = modulos_encontrados
        self.logger = logger

    def run(self):
        import importlib
        import sys
        from controlador.utils.paths import get_resource_path
        from vistas.configurations import load_class_dynamically

        base_dir = get_resource_path()
        if str(base_dir) not in sys.path:
            sys.path.insert(0, str(base_dir))

        # Eliminar archivos .old huérfanos de actualizaciones anteriores
        try:
            # Limpiar archivos .old en la raíz
            for item in base_dir.iterdir():
                if item.is_file() and item.name.endswith(".old"):
                    try:
                        item.unlink()
                        print(f"[Loader Cleanup] Eliminado archivo core viejo: {item.name}")
                    except:
                        pass

            # Limpiar archivos .old en los módulos
            modulos_dir = base_dir / "vistas" / "modulos"
            if modulos_dir.exists():
                for root, dirs, files in os.walk(modulos_dir):
                    for file in files:
                        if file.endswith(".old"):
                            try:
                                os.unlink(os.path.join(root, file))
                                print(f"[Loader Cleanup] Eliminado archivo de actualización viejo: {file}")
                            except:
                                pass
        except Exception as cleanup_err:
            print(f"[Loader Cleanup] Advertencia al limpiar archivos .old: {cleanup_err}")

        # Recolectar todos los submódulos de módulos visibles
        visibles = [m for m in self.modulos_encontrados if m.get("visible", True)]
        todos_subs = []
        for mod in visibles:
            for sub in mod.get("submodules", []):
                if sub.get("visible", True):
                    todos_subs.append((mod["name"], sub))

        total = max(len(todos_subs), 1)

        for i, (m_name, sub) in enumerate(todos_subs):
            porcentaje = int(((i + 1) / total) * 92)
            self.progreso.emit(porcentaje, f"Cargando {m_name.capitalize()} > {sub['name']}...")

            try:
                # Carga dinámica off-main-thread
                cls = load_class_dynamically(sub)
                sub["cls"] = cls
                self.logger.log("INFO", f"[Thread] OK: {m_name} > {sub['name']}", modulo="Loader")
            except Exception as e:
                self.logger.log("ERROR", f"[Thread] FALLO {m_name} > {sub['name']}: {e}", modulo="Loader")
                sub["cls"] = None
                sub["error"] = str(e)

        self.progreso.emit(95, "Construyendo interfaz...")
        self.terminado.emit(self.modulos_encontrados)


# ─────────────────────────────────────────────────────────────
#  VENTANA PRINCIPAL
# ─────────────────────────────────────────────────────────────

class AppMultitareasGUI(BaseAppGUI):
    def __init__(self, usuario, persona, callback_progreso=None):
        self.persona = persona
        self.ruta_usuario = get_user_path(persona)
        self.config = {}
        self.callback_progreso = callback_progreso
        self._loader_thread = None

        self.cargar_configuracion()

        # Iniciar sistema de logs JSON del usuario
        self.logger = JsonLogger(self.ruta_usuario)
        self.logger.log("INFO", f"Iniciando Multitool para {usuario}", modulo="Cargador")

        # Obtener colores del tema configurado por el usuario
        from vistas.estilos import obtener_colores_tema
        tema_nombre = self.config.get("tema", "azul_oscuro")
        colores_tema = obtener_colores_tema(tema_nombre, self.config)

        # Inicializa UI base PyQt6 (crea la ventana, notebook, etc.)
        super().__init__(usuario, colores=colores_tema)
        
        fondo_img = self.config.get("fondo_imagen", "")
        if fondo_img:
            self.aplicar_fondo_e_estilo(colores=colores_tema, fondo_imagen=fondo_img)

        self.actualizar_ultimo_acceso()

        self.context = AppContext(
            usuario=self.usuario,
            persona=self.persona,
            ruta_usuario=self.ruta_usuario,
            config=self.config,
            app=self
        )

        # Descubrir módulos (rápido) y lanzar el hilo de carga pesada
        self.cargar_modulos()

    # ── Configuración ─────────────────────────────────────────────────────

    def cargar_configuracion(self):
        config_path = self.ruta_usuario / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except:
                self.config = {}
        else:
            self.config = {}

    def guardar_configuracion(self):
        config_path = self.ruta_usuario / "config.json"
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración: {e}")

    def actualizar_ultimo_acceso(self):
        self.config["ultimo_acceso"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.guardar_configuracion()

    # ── Carga de módulos ──────────────────────────────────────────────────

    def cargar_modulos(self):
        """
        FASE 1 (hilo principal, rápida):
          • Ejecuta la migración de módulos clásicos a plugins
          • Lee las configuraciones config.json dinámicas
          • Crea las pestañas placeholder
        
        FASE 2 (ModuloLoaderThread, pesada):
          • Importa los submódulos con importlib
          • Cuando termina, instancia los widgets en el hilo principal
        """
        try:
            # 1. Descubrir módulos dinámicos
            modulos_encontrados = discover_modules_and_plugins(self.ruta_usuario)

            self.modulos_cargados = modulos_encontrados
            self.clases_modulos = {}
            self._frames_modulos = {}

            # Crear pestañas placeholder en el hilo principal (requerido por Qt)
            for mod in modulos_encontrados:
                if not mod.get("visible", True):
                    continue

                tab_widget = QWidget()
                layout = QVBoxLayout(tab_widget)
                layout.setContentsMargins(0, 0, 0, 0)

                lbl = QLabel(f"🔄 Cargando {mod['name'].capitalize()}...")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet(
                    "color: #6366F1; font-size: 14px; font-weight: bold; background: transparent; border: none;"
                )
                layout.addWidget(lbl)

                self._frames_modulos[mod["name"]] = tab_widget
                self.notebook.addTab(tab_widget, mod["name"].capitalize())
                mod["loaded"] = False
                mod["dummy_frame"] = tab_widget

            QApplication.processEvents()
            if self.callback_progreso:
                self.callback_progreso(5, "Iniciando carga de módulos...")

            # Lanzar hilo de importación pesada
            self._loader_thread = ModuloLoaderThread(modulos_encontrados, self.logger)
            self._loader_thread.progreso.connect(self._on_loader_progreso)
            self._loader_thread.terminado.connect(self._on_loader_terminado)
            self._loader_thread.start()

        except Exception as e:
            import traceback
            traceback.print_exc()
            if self.callback_progreso:
                self.callback_progreso(100, "Error de inicio")

    def _on_loader_progreso(self, porcentaje, mensaje):
        """Reenvía el progreso del hilo a la pantalla de carga (hilo principal)."""
        if self.callback_progreso:
            self.callback_progreso(porcentaje, mensaje)
        QApplication.processEvents()

    def _on_loader_terminado(self, modulos_con_clase):
        """
        Slot ejecutado en el HILO PRINCIPAL cuando el loader termina.
        Instancia únicamente los módulos que inician por defecto: 'general' y 'widgets'.
        Los demás módulos permanecen en modo reposo hasta que el usuario haga clic en sus pestañas.
        """
        self.modulos_cargados = modulos_con_clase

        # Sincronizar los botones de navegación y pestañas
        self.actualizar_menu_ver(self.modulos_cargados)

        # 1. Instanciar únicamente los módulos por defecto: 'general' y 'widgets'
        mod_general = None
        mod_widgets = None
        for mod in self.modulos_cargados:
            m_name = mod.get("name", "").lower()
            if m_name == "general":
                mod_general = mod
            elif m_name == "widgets":
                mod_widgets = mod

        if mod_general and mod_general.get("visible", True):
            self._instanciar_modulo(mod_general)

        if mod_widgets and mod_widgets.get("visible", True):
            self._instanciar_modulo(mod_widgets)

        # 2. Instanciar módulos adicionales ÚNICAMENTE si el usuario configuró explícitamente autostart
        for mod in self.modulos_cargados:
            m_name = mod.get("name", "").lower()
            if m_name not in ("general", "widgets"):
                if mod.get("visible", True) and mod.get("autostart", False) and not mod.get("loaded", False):
                    self._instanciar_modulo(mod)

        # 3. Establecer y enfocar la pestaña activa en 'General' por defecto
        visibles = [m for m in self.modulos_cargados if m.get("visible", True)]
        idx_general = 0
        for idx, m in enumerate(visibles):
            if m.get("name", "").lower() == "general":
                idx_general = idx
                break

        if visibles:
            self.notebook.setCurrentIndex(idx_general)
            if hasattr(self, "nav_bar"):
                self.nav_bar.select_tab(idx_general)

        if self.callback_progreso:
            self.callback_progreso(100, "¡Multitool Listo!")

    def on_tab_changed(self, index):
        """Sobrescribe el método de BaseAppGUI para cargar módulos dinámicamente bajo demanda."""
        if index < 0:
            return

        import datetime, time
        visibles = [m for m in self.modulos_cargados if m.get("visible", True)]
        if index < len(visibles):
            mod = visibles[index]
            mod["last_opened"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            mod["last_opened_timestamp"] = time.time()
            if not mod.get("loaded", False):
                self.set_status(f"Cargando {mod['name']}...")
                self._instanciar_modulo(mod)
                self.set_status(f"Módulo {mod['name']} listo.")

        if hasattr(self, "nav_bar"):
            self.nav_bar.select_tab(index)

        super().on_tab_changed(index)

    def _instanciar_modulo(self, mod):
        """Instancia e incrusta el módulo en su pestaña correspondiente usando DynamicModuleContainer."""
        if not mod.get("visible", True) or mod.get("loaded", False):
            return

        try:
            parent_frame = self._frames_modulos.get(mod["name"])
            if not parent_frame:
                parent_frame = mod.get("dummy_frame")
            if not parent_frame:
                raise KeyError("dummy_frame")

            # Limpiar placeholder
            if parent_frame.layout():
                while parent_frame.layout().count():
                    item = parent_frame.layout().takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

            # Instanciar el contenedor dinámico
            container = DynamicModuleContainer(parent_frame, self.context, mod["name"], mod["submodules"], self.COLORES)
            parent_frame.layout().addWidget(container)
            container.show()

            # Guardar referencias para compatibilidad
            setattr(self, f"tab_{mod['name']}", container)
            
            # Registrar el contenedor principal
            self.clases_modulos[mod["name"]] = container
            self.clases_modulos[mod["name"].lower()] = container
            self.clases_modulos[mod["name"].capitalize()] = container
            
            # Registrar submódulos individuales para acceso directo
            for sub_name, sub_inst in container.submodules_instances.items():
                self.clases_modulos[sub_name] = sub_inst
                self.clases_modulos[sub_name.lower()] = sub_inst
                self.clases_modulos[sub_name.capitalize()] = sub_inst

            import datetime, time
            mod["loaded"] = True
            mod["last_opened"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            mod["last_opened_timestamp"] = time.time()
            self.logger.log("INFO", f"'{mod['name']}' instanciado OK.", modulo="Cargador")
            print(f"[+] Módulo '{mod['name']}' listo y mostrado.")

        except Exception as e:
            self.logger.log("ERROR", f"Error instanciando {mod['name']}: {e}", modulo="Cargador")
            self._mostrar_error_modulo(mod, str(e))
            import traceback
            traceback.print_exc()

    def descargar_modulo(self, mod_name):
        """Pone un módulo en reposo liberando su memoria RAM y restableciendo su estado inicial sin abrir."""
        target_mod = None
        for mod in self.modulos_cargados:
            if mod.get("name", "").lower() == mod_name.lower():
                target_mod = mod
                break

        if not target_mod or not target_mod.get("loaded", False):
            return False

        # Prevenir descarga del módulo principal General (Core UI)
        if target_mod.get("name", "").lower() == "general":
            return False

        parent_frame = self._frames_modulos.get(target_mod["name"]) or target_mod.get("dummy_frame")
        if parent_frame and parent_frame.layout():
            while parent_frame.layout().count():
                item = parent_frame.layout().takeAt(0)
                widget = item.widget()
                if widget:
                    if hasattr(widget, "cleanup"):
                        try:
                            widget.cleanup()
                        except Exception:
                            pass
                    widget.deleteLater()

            # Restaurar el placeholder elegante de reposo
            lbl = QLabel(f"💤 {target_mod['name'].capitalize()} en reposo\n(Haz clic en esta pestaña para reactivarlo)")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "color: #818CF8; font-size: 13px; font-weight: bold; background: transparent; border: none; padding: 20px;"
            )
            parent_frame.layout().addWidget(lbl)

        target_mod["loaded"] = False
        name = target_mod["name"]
        if hasattr(self, f"tab_{name}"):
            delattr(self, f"tab_{name}")
        for k in [name, name.lower(), name.capitalize()]:
            self.clases_modulos.pop(k, None)

        import gc
        gc.collect()
        self.logger.log("INFO", f"Módulo '{mod_name}' puesto en reposo y memoria liberada.", modulo="Cargador")
        return True

    def _mostrar_error_modulo(self, mod, error_msg):
        """Muestra error en el placeholder del módulo fallido."""
        parent_frame = self._frames_modulos.get(mod["name"])
        if not parent_frame:
            parent_frame = mod.get("dummy_frame")
        if not parent_frame:
            return
        if parent_frame.layout():
            while parent_frame.layout().count():
                item = parent_frame.layout().takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        err_lbl = QLabel(f"⚠️ Error al cargar '{mod['name']}'\n\n{error_msg}")
        err_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        err_lbl.setStyleSheet(
            "color: #F87171; font-weight: bold; background: #2D2D3D; "
            "border: 1px solid #F87171; border-radius: 5px; padding: 20px;"
        )
        err_lbl.setWordWrap(True)
        parent_frame.layout().addWidget(err_lbl)

    # ── Resto de métodos ─────────────────────────────────────────────────


    def abrir_gestor_modulos(self):
        """Abre el gestor de módulos (PyQt6)."""
        from vistas.utils.module_manager import ModuleManagerGUI
        manager = ModuleManagerGUI(
            self, self.obtener_todos_los_modulos(), self.COLORES,
            self.guardar_modificaciones_modulos
        )
        manager.exec()

    def cerrar_sesion(self):
        """Cierra sesión y deshabilita el acceso rápido."""
        respuesta = QMessageBox.question(
            self, "Cerrar Sesión", "¿Está seguro de que desea cerrar sesión?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if respuesta == QMessageBox.StandardButton.Yes:
            self.config["login"] = False
            self.guardar_configuracion()
            self.close()
            import main
            main.main()

    def obtener_todos_los_modulos(self):
        """Retorna todos los módulos con el estado actual (global + usuario)."""
        from vistas.configurations import discover_modules_and_plugins
        return discover_modules_and_plugins(self.ruta_usuario)

    def guardar_modificaciones_modulos(self, modulos):
        """Guarda la visibilidad y orden en el modulos.conf del usuario."""
        user_data = {}
        for mod in modulos:
            user_data[mod["name"]] = {
                "visible": mod.get("visible", True),
                "position": mod.get("position", 99)
            }

        try:
            user_prefs_path = self.ruta_usuario / "modulos.conf"
            with open(user_prefs_path, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)
            QMessageBox.information(
                self, "Módulos",
                "Configuración guardada. Los cambios se aplicarán al reiniciar."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")

