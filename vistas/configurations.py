import zipfile
import datetime
import os
import json
import sys
import importlib
import importlib.util
import types
import shutil
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class SafeCallbackDict(dict):
    """Diccionario seguro que devuelve una función no-op para cualquier callback no definido."""
    def __getitem__(self, item):
        if item not in self:
            return lambda *args, **kwargs: None
        return super().__getitem__(item)

    def get(self, item, default=None):
        if item not in self:
            return default if default is not None else (lambda *args, **kwargs: None)
        return super().get(item, default)


class DynamicModuleContainer(QWidget):
    """
    Contenedor de interfaz para módulos dinámicos.
    Si tiene solo 1 submódulo visible, lo muestra directamente (sin barra de pestañas).
    Si tiene más de 1 submódulo, crea un QTabWidget con pestañas para navegar entre ellos.
    """
    def __init__(self, parent, context, module_name, submodules_info, colores):
        super().__init__(parent)
        self.context = context
        self.module_name = module_name
        self.submodules_info = submodules_info
        self.colores = colores
        self.submodules_instances = {}
        self.font_family = "Segoe UI"
        
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Filtrar sub-módulos visibles
        visibles = [s for s in self.submodules_info if s.get("visible", True)]

        if len(visibles) == 0:
            lbl = QLabel(f"⚠️ El módulo '{self.module_name}' no tiene submódulos activos.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #F87171; font-weight: bold; background: transparent; border: none;")
            self.main_layout.addWidget(lbl)
            return

        if len(visibles) == 1:
            # Solo 1 submódulo: no mostrar barra de pestañas secundarias
            sub = visibles[0]
            widget = self._instanciar_submodulo(sub)
            if widget:
                self.main_layout.addWidget(widget)
            else:
                self._mostrar_error_submodulo(sub, "No se pudo instanciar la clase.")
        else:
            # Más de 1 submódulo: mostrar barra de pestañas secundarias
            self.tabs = QTabWidget()
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane {{ 
                    border: 0px; 
                    background: {self.colores.get('bg_principal', '#121218')}; 
                }}
                QTabBar {{
                    background: {self.colores.get('bg_secundario', '#1E1E2E')};
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                }}
                QTabBar::tab {{ 
                    background: transparent; 
                    color: {self.colores.get('fg_secundario', '#AAB0B8')}; 
                    padding: 12px 28px; 
                    font-family: '{self.font_family}'; 
                    font-size: 11px;
                    font-weight: bold;
                }}
                QTabBar::tab:selected {{ 
                    color: {self.colores.get('acento', '#6366F1')}; 
                    border-bottom: 2px solid {self.colores.get('acento', '#6366F1')};
                    background: rgba(99, 102, 241, 0.1);
                }}
                QTabBar::tab:hover:!selected {{
                    color: white;
                    background: rgba(255, 255, 255, 0.02);
                }}
            """)
            
            for sub in visibles:
                widget = self._instanciar_submodulo(sub)
                if not widget:
                    widget = QWidget()
                    lay = QVBoxLayout(widget)
                    lbl = QLabel(f"⚠️ Error cargando {sub['name']}")
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lay.addWidget(lbl)
                self.tabs.addTab(widget, sub["name"].upper())

            self.main_layout.addWidget(self.tabs)

    def _instanciar_submodulo(self, sub):
        try:
            cls = sub.get("cls")
            if not cls:
                cls = load_class_dynamically(sub)
                sub["cls"] = cls

            if not cls:
                try:
                    from controlador.utils.paths import get_resource_path
                    from controlador.utils.dependency_manager import DependencyManager, MissingDependenciesWidget
                    folder = sub.get("folder", "")
                    folder_clean = folder.replace("modulos/", "")
                    folder_path = get_resource_path() / "vistas" / "modulos" / folder_clean
                    faltantes = DependencyManager.analizar_dependencias_faltantes(folder_path)
                    if faltantes:
                        def _on_installed():
                            sub["cls"] = load_class_dynamically(sub)
                            new_w = self._instanciar_submodulo(sub)
                            if new_w and hasattr(self, "tabs"):
                                idx = self.tabs.indexOf(missing_w)
                                if idx >= 0:
                                    self.tabs.removeTab(idx)
                                    self.tabs.insertTab(idx, new_w, sub.get("name", "Módulo").upper())
                                    self.tabs.setCurrentIndex(idx)
                            elif new_w and hasattr(self, "main_layout"):
                                self.main_layout.removeWidget(missing_w)
                                missing_w.deleteLater()
                                self.main_layout.addWidget(new_w)

                        missing_w = MissingDependenciesWidget(
                            folder_path, sub.get("name", "Módulo"), faltantes,
                            on_success_callback=_on_installed, colores=self.colores, parent=self
                        )
                        return missing_w
                except Exception as e_dep:
                    print(f"[DynamicContainer] Error evaluando dependencias: {e_dep}")
                return None

            import inspect
            sig = inspect.signature(cls.__init__)
            params = sig.parameters

            # Mapa de dependencias conocidas
            usuario = getattr(self.context, "usuario", "Invitado")
            persona = getattr(self.context, "persona", "Usuario")
            ruta_usuario = getattr(self.context, "ruta_usuario", ".")
            raw_callbacks = getattr(self, "callbacks", {}) or {}
            callbacks = SafeCallbackDict(raw_callbacks)

            param_map = {
                "parent": self,
                "context": self.context,
                "colores": self.colores,
                "usuario": usuario,
                "persona": persona,
                "ruta_usuario": ruta_usuario,
                "callbacks": callbacks,
                "agregar_al_historial_callback": callbacks["agregar_al_historial_callback"],
                "obtener_historial_callback": callbacks.get("obtener_historial_callback", lambda *args, **kwargs: []),
                "limpiar_historial_callback": callbacks["limpiar_historial_callback"],
                "chat_input_widget": getattr(self, "txt_input", None),
                "txt_input": getattr(self, "txt_input", None),
                "manager": getattr(self.context, "manager", None),
                "canvas": getattr(self, "canvas", None)
            }

            args = []
            kwargs = {}
            has_varkw = False

            for p_name, p in list(params.items())[1:]:  # Omitir 'self'
                if p.kind == inspect.Parameter.VAR_POSITIONAL:
                    pass
                elif p.kind == inspect.Parameter.VAR_KEYWORD:
                    has_varkw = True
                elif p_name in param_map:
                    if p.default == inspect.Parameter.empty:
                        args.append(param_map[p_name])
                    else:
                        kwargs[p_name] = param_map[p_name]
                else:
                    if p.default != inspect.Parameter.empty:
                        pass
                    else:
                        if "callback" in p_name.lower():
                            args.append(lambda *args, **kwargs: None)
                        elif "colores" in p_name.lower() or "color" in p_name.lower():
                            args.append(self.colores)
                        elif "context" in p_name.lower():
                            args.append(self.context)
                        elif "path" in p_name.lower() or "ruta" in p_name.lower():
                            args.append(ruta_usuario)
                        else:
                            args.append(None)

            if has_varkw:
                kwargs.setdefault("context", self.context)
                kwargs.setdefault("colores", self.colores)

            try:
                instance = cls(*args, **kwargs)
            except TypeError:
                try:
                    instance = cls(self, self.context, self.colores)
                except TypeError:
                    try:
                        instance = cls(self, self.context)
                    except TypeError:
                        instance = cls(self)

            self.submodules_instances[sub["name"]] = instance
            
            widget = None
            if isinstance(instance, QWidget):
                widget = instance
            elif hasattr(instance, "gui") and isinstance(instance.gui, QWidget):
                widget = instance.gui
            
            return widget
        except Exception as e:
            try:
                print(f"[DynamicContainer Error] Fallo instanciando '{sub.get('name', 'sub')}': {e}")
            except Exception:
                pass
            return None

    def _mostrar_error_submodulo(self, sub, error_msg):
        err_lbl = QLabel(f"⚠️ Error al cargar '{sub['name']}'\n\n{error_msg}")
        err_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        err_lbl.setStyleSheet(
            f"color: #F87171; font-weight: bold; background: {self.colores.get('bg_secundario', '#1E1E2E')}; "
            "border: 1px solid #F87171; border-radius: 8px; padding: 20px;"
        )
        err_lbl.setWordWrap(True)
        self.main_layout.addWidget(err_lbl)


def load_class_dynamically(sub_info):
    """
    Carga e importa dinámicamente la clase definida en sub_info.
    Mapea la carpeta del módulo a su respectiva importación.
    """
    from controlador.utils.paths import get_resource_path
    
    base_dir = get_resource_path()
    folder = sub_info.get("folder")
    file_name = sub_info.get("file_name")
    class_name = sub_info.get("class_name")
    
    # Determinar ruta física del archivo (.py, .pyd, .so) bajo vistas/modulos
    folder_clean = folder.replace("modulos/", "")
    folder_path = base_dir / "vistas" / "modulos" / folder_clean

    try:
        from controlador.utils.dependency_manager import DependencyManager
        DependencyManager.activar_entorno_modulo(folder_path)
    except Exception:
        pass
    
    path_archivo = folder_path / file_name
    path_pyd = folder_path / file_name.replace(".py", ".pyd")
    path_so = folder_path / file_name.replace(".py", ".so")
    main_pyd = folder_path / f"{folder_clean}.pyd"
    main_so = folder_path / f"{folder_clean}.so"
    main_py = folder_path / f"{folder_clean}.py"

    # Candidatos específicos para este sub-módulo
    candidates = []
    for p in [path_pyd, path_so, path_archivo]:
        if p.exists():
            candidates.append(p)

    # Solo si no se encontró candidato específico para file_name y es el archivo de entrada del módulo
    file_rel = file_name.replace("\\", "/").strip()
    if not candidates and file_rel in ["main.py", f"{folder_clean}.py"]:
        for p in [main_pyd, main_so, main_py]:
            if p.exists():
                candidates.append(p)

    # Ordenar candidatos por fecha de modificación mtime (el más reciente primero)
    if candidates:
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    # Normalizar file_name eliminando extensión y convirtiendo separadores de ruta en puntos
    file_name_clean = file_name.replace(".py", "").replace(".pyd", "").replace(".so", "")
    module_ns = file_name_clean.replace("/", ".").replace("\\", ".")
    
    pkg_name = f"vistas.modulos.{folder_clean}"
    import_path = f"{pkg_name}.{module_ns}"

    # 1. PRIORIDAD ALTA: Cargar archivo físico en disco permitiendo importaciones relativas (from . y from ..)
    for candidate in candidates:
        try:
            # Determinar el nombre completo del módulo e interfaz de paquete dentro de vistas.modulos
            mod_root = base_dir / "vistas" / "modulos"
            try:
                rel_cand = candidate.relative_to(mod_root)
                parts = list(rel_cand.with_suffix("").parts)
                full_mod_name = "vistas.modulos." + ".".join(parts)
                full_pkg_name = "vistas.modulos." + ".".join(parts[:-1]) if len(parts) > 1 else f"vistas.modulos.{folder_clean}"
            except Exception:
                full_mod_name = import_path
                full_pkg_name = pkg_name

            # Purgar caché previa en sys.modules para este módulo y todos sus submódulos
            # para obligar a Python a cargar los archivos físicos actualizados del disco
            prefix_to_purge = f"vistas.modulos.{folder_clean}"
            for k in list(sys.modules.keys()):
                if k == prefix_to_purge or k.startswith(f"{prefix_to_purge}."):
                    del sys.modules[k]

            # Asegurar que la jerarquía de paquetes padres exista en sys.modules con __path__ apuntando a su carpeta real en disco
            pkg_parts = full_pkg_name.split(".")
            curr_pkg = ""
            for p in pkg_parts:
                curr_pkg = f"{curr_pkg}.{p}" if curr_pkg else p
                curr_dir = base_dir / Path(*curr_pkg.split("."))
                target_dir_str = str(curr_dir) if curr_dir.exists() else str(candidate.parent)
                
                if curr_pkg not in sys.modules or not hasattr(sys.modules[curr_pkg], "__path__"):
                    p_mod = types.ModuleType(curr_pkg)
                    p_mod.__package__ = curr_pkg
                    p_mod.__path__ = [target_dir_str]
                    sys.modules[curr_pkg] = p_mod
                else:
                    existing_pkg = sys.modules[curr_pkg]
                    if hasattr(existing_pkg, "__path__") and isinstance(existing_pkg.__path__, list):
                        if target_dir_str not in existing_pkg.__path__:
                            existing_pkg.__path__.insert(0, target_dir_str)

            # Cargar módulo físico usando la especificidad del archivo
            spec = importlib.util.spec_from_file_location(full_mod_name, str(candidate))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                module.__package__ = full_pkg_name
                sys.modules[full_mod_name] = module
                spec.loader.exec_module(module)

                cls = getattr(module, class_name, None)
                if cls:
                    print(f"[Loader Dynamic Patch] Clase '{class_name}' cargada con ÉXITO desde archivo físico: {candidate.name}")
                    return cls
        except Exception as e:
            print(f"[Loader] Falló carga dinámica desde {candidate.name}: {e}. Probando siguiente...")

    # 2. FALLBACK: Carga desde el binario original estático de Nuitka
    try:
        if import_path in sys.modules:
            mod_compiled = sys.modules[import_path]
        else:
            mod_compiled = importlib.import_module(import_path)
            
        cls = getattr(mod_compiled, class_name, None)
        if cls:
            print(f"[Loader Static] Clase '{class_name}' cargada desde compilado estático Nuitka.")
            return cls
    except Exception as e:
        print(f"[Loader Error] Falló carga estática Nuitka para {import_path}: {e}")

    return None


def guardar_modulo_usuario_config(ruta_usuario, folder_name, config_data):
    """Guarda la configuración personalizada de un módulo en la cuenta del usuario (modulesconf)."""
    if not ruta_usuario:
        return False
    try:
        user_dir = Path(ruta_usuario) / "modulesconf" / folder_name
        user_dir.mkdir(parents=True, exist_ok=True)
        cfg_file = user_dir / "config.json"
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Configurations] Error guardando config de usuario para {folder_name}: {e}")
        return False


def backup_and_reset_modulesconf(ruta_usuario, modulos_dir=None):
    """
    Realiza un backup comprimido en .zip de la configuración actual del usuario (modulesconf)
    en la carpeta 'backups' y restablece los config.json desde las plantillas originales en vistas/modulos/.
    """
    if not ruta_usuario:
        return False, "Ruta de usuario no especificada."

    ruta_u = Path(ruta_usuario)
    user_mod_dir = ruta_u / "modulesconf"
    backups_dir = ruta_u / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = backups_dir / f"backup_modulesconf_{timestamp}.zip"

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Respaldar carpeta modulesconf
            if user_mod_dir.exists():
                for item in user_mod_dir.rglob("*"):
                    if item.is_file():
                        arcname = item.relative_to(ruta_u)
                        zf.write(item, arcname)

            # 2. Respaldar modulos.conf si existe
            mod_conf = ruta_u / "modulos.conf"
            if mod_conf.exists():
                zf.write(mod_conf, "modulos.conf")

        # 3. Restaurar configuraciones de fábrica desde vistas/modulos
        if not modulos_dir:
            from controlador.utils.paths import get_resource_path
            modulos_dir = get_resource_path() / "vistas" / "modulos"

        modulos_dir = Path(modulos_dir)
        if modulos_dir.exists():
            for item in modulos_dir.iterdir():
                if item.is_dir() and not item.name.startswith((".", "_")):
                    src_cfg = item / "config.json"
                    if src_cfg.exists():
                        target_dir = user_mod_dir / item.name
                        target_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_cfg, target_dir / "config.json")

        return True, str(zip_path)

    except Exception as e:
        return False, f"Error durante el reinicio: {e}"


def discover_modules_and_plugins(ruta_usuario=None):
    """
    Busca módulos core en vistas/modulos/ utilizando los archivos de configuración config.json.
    Prioriza las configuraciones personalizadas del usuario en cuentas/<Usuario>/modulesconf/<modulo>/config.json.
    Retorna la lista ordenada de módulos con sus submódulos correspondientes.
    """
    from controlador.utils.paths import get_resource_path
    
    base_dir = get_resource_path()
    modulos_dir = base_dir / "vistas" / "modulos"

    # Preferencias de orden y visibilidad del usuario (retrocompatibilidad)
    user_prefs = {}
    user_mod_dir = None
    if ruta_usuario:
        ruta_u = Path(ruta_usuario)
        user_mod_dir = ruta_u / "modulesconf"
        user_mod_dir.mkdir(parents=True, exist_ok=True)

        user_prefs_path = ruta_u / "modulos.conf"
        if user_prefs_path.exists():
            try:
                with open(user_prefs_path, "r", encoding="utf-8") as f:
                    user_prefs = json.load(f)
            except Exception:
                pass

    modules_map = {}

    def registrar_config_modulo(config_data, folder_name):
        module_name = config_data.get("name", "").capitalize()
        if not module_name:
            module_name = folder_name.capitalize()

        position = config_data.get("position", 99)
        visible = config_data.get("visible", True)

        # Aplicar preferencias del usuario si existían en modulos.conf
        u_cfg = user_prefs.get(module_name, {})
        position = u_cfg.get("position", position)
        visible = u_cfg.get("visible", visible)
        autostart = u_cfg.get("autostart", False)

        # Icono predeterminado "🧩" si no tiene ninguno asignado
        icon_val = config_data.get("icon") or config_data.get("icono") or "🧩"
        alias_val = config_data.get("alias") or folder_name.lower()

        # Crear estructura del módulo
        if module_name not in modules_map:
            modules_map[module_name] = {
                "name": module_name,
                "alias": alias_val,
                "position": position,
                "visible": visible,
                "autostart": autostart,
                "folder": folder_name,
                "icon": icon_val,
                "submodules": []
            }
        else:
            modules_map[module_name]["alias"] = alias_val
            modules_map[module_name]["position"] = position
            modules_map[module_name]["visible"] = visible
            modules_map[module_name]["autostart"] = autostart
            modules_map[module_name]["folder"] = folder_name
            modules_map[module_name]["icon"] = icon_val

        # Submódulos ejecutables
        main_file = config_data.get("file_name")
        main_class = config_data.get("class_name")
        
        if not main_file or not main_class:
            candidates_main = [
                (f"{folder_name}.py", f"Tab{folder_name.capitalize()}"),
                (f"{folder_name}.py", f"Tab{folder_name}"),
                (f"{folder_name}.py", "TabMiniGames"),
                (f"{folder_name}.py", f"{folder_name.capitalize()}Tab"),
                (f"{folder_name}.py", "GeneralTab"),
                (f"{folder_name}_main.py", f"Tab{folder_name.capitalize()}"),
                (f"{folder_name}_main.py", f"Tab{folder_name}"),
                (f"{folder_name}.py", "TabMain"),
                ("main.py", f"Tab{folder_name.capitalize()}"),
                ("main.py", "MainWidget")
            ]
            for fn, cn in candidates_main:
                if (modulos_dir / folder_name / fn).exists():
                    main_file = fn
                    main_class = cn
                    break

        if main_file and main_class and (modulos_dir / folder_name / main_file).exists():
            modules_map[module_name]["submodules"] = [{
                "name": module_name,
                "alias": alias_val,
                "folder": folder_name,
                "file_name": main_file,
                "class_name": main_class,
                "position": 0,
                "visible": True,
                "icon": icon_val,
                "cls": None
            }]
        else:
            submodulos_lista = config_data.get("submodulos", [])
            for idx_s, sub in enumerate(submodulos_lista, 1):
                s_name = sub.get("name", module_name)
                s_alias = sub.get("alias") or s_name.lower().replace(" ", "_")
                s_icon = sub.get("icon") or "🧩"
                modules_map[module_name]["submodules"].append({
                    "name": s_name,
                    "alias": s_alias,
                    "folder": folder_name,
                    "file_name": sub.get("file_name", "main.py"),
                    "class_name": sub.get("class_name", "Tab"),
                    "position": sub.get("position", idx_s),
                    "visible": sub.get("visible", True),
                    "icon": s_icon,
                    "cls": None
                })

    # Escanear vistas/modulos/
    if modulos_dir.exists():
        for item in modulos_dir.iterdir():
            if item.is_dir() and not item.name.startswith((".", "_")):
                # Determinar si el usuario tiene configuración personalizada en modulesconf
                cfg_to_read = None
                if user_mod_dir:
                    u_cfg = user_mod_dir / item.name / "config.json"
                    if u_cfg.exists():
                        cfg_to_read = u_cfg
                    else:
                        # Inicializar modulesconf/<folder>/config.json desde el original
                        core_cfg = item / "config.json"
                        if core_cfg.exists():
                            try:
                                u_target_dir = user_mod_dir / item.name
                                u_target_dir.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(core_cfg, u_cfg)
                                cfg_to_read = u_cfg
                            except Exception:
                                cfg_to_read = core_cfg

                if not cfg_to_read:
                    cfg_to_read = item / "config.json"

                if cfg_to_read and cfg_to_read.exists():
                    try:
                        with open(cfg_to_read, "r", encoding="utf-8") as f:
                            config_data = json.load(f)
                        registrar_config_modulo(config_data, item.name)
                    except Exception as e:
                        print(f"[Loader] Error al cargar config.json de {item.name}: {e}")

    # Convertir mapa a lista y ordenar por posición
    res = list(modules_map.values())
    res.sort(key=lambda x: int(x.get("position", 99)))

    # Ordenar sub-módulos internos por posición
    for m in res:
        m["submodules"].sort(key=lambda x: int(x.get("position", 99)))

    return res
