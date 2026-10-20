"""
submodule_loader.py - Motor universal de carga dinámica de submódulos para MultiTool.
Lee el archivo config.json de cada módulo y carga/instancia las pestañas e interfaces
declaradas en 'submodulos' de forma automática y tolerante a fallos.
"""

import os
import sys
import json
import inspect
import importlib.util
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QTabWidget

def load_submodules_from_config(
    module_dir: Path,
    tab_widget: QTabWidget,
    parent_container: QWidget,
    context=None,
    colores: dict = None,
    extra_kwargs: dict = None
) -> dict[str, QWidget]:
    """
    Lee config.json en module_dir, carga dinámicamente cada submódulo visible
    y lo agrega como pestaña en tab_widget.

    Retorna un diccionario {clave/nombre_clase: instancia_widget}.
    """
    instances = {}
    config_path = module_dir / "config.json"
    
    if not config_path.exists():
        return instances

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"[Loader Error] No se pudo leer {config_path}: {e}")
        return instances

    submodulos = config_data.get("submodulos", [])
    if not isinstance(submodulos, list):
        return instances

    # Resolver contexto y colores predeterminados
    default_paleta = {
        "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
        "fg_principal": "#FFFFFF", "fg_secundario": "#AAB0B8", "acento": "#6366F1", "acento_hover": "#4F46E5",
        "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
    }
    colores_in = colores or (getattr(getattr(context, "app", None), "COLORES", None) if context else None)
    colores = {**default_paleta, **(colores_in if isinstance(colores_in, dict) else {})}
    usuario = getattr(context, "usuario", None) if context else None
    persona = getattr(context, "persona", None) if context else None
    ruta_usuario = Path(getattr(context, "ruta_usuario", ".")) if context else Path(".")

    for sub in submodulos:
        if not isinstance(sub, dict):
            continue

        if not sub.get("visible", True):
            continue

        name = sub.get("name", "Submódulo")
        file_name = sub.get("file_name", "")
        class_name = sub.get("class_name", "")

        if not file_name or not class_name:
            continue

        target_file = (module_dir / file_name).resolve()
        if not target_file.exists():
            print(f"[Loader Warning] Archivo de submódulo no encontrado: {target_file}")
            continue

        # Obtener nombre de módulo calificado para soportar imports relativos
        try:
            rel = target_file.relative_to(Path.cwd())
            parts = list(rel.with_suffix("").parts)
            mod_name = ".".join(parts)
        except Exception:
            sub_part = file_name.replace("/", ".").replace("\\", "")
            if sub_part.endswith(".py"):
                sub_part = sub_part[:-3]
            mod_name = f"vistas.modulos.{module_dir.name}.{sub_part}"

        # 0. Activar librerías aisladas y comprobar dependencias
        try:
            from controlador.utils.dependency_manager import DependencyManager, MissingDependenciesWidget
            DependencyManager.activar_entorno_modulo(module_dir)
            faltantes = DependencyManager.analizar_dependencias_faltantes(module_dir)
        except Exception:
            faltantes = []

        try:
            # Importar dinámicamente el módulo
            cls = None
            try:
                if mod_name in sys.modules:
                    module = sys.modules[mod_name]
                else:
                    try:
                        module = importlib.import_module(mod_name)
                    except Exception:
                        spec = importlib.util.spec_from_file_location(mod_name, str(target_file))
                        if spec is None or spec.loader is None:
                            continue
                        module = importlib.util.module_from_spec(spec)
                        module.__package__ = mod_name.rpartition('.')[0]
                        sys.modules[mod_name] = module
                        spec.loader.exec_module(module)

                cls = getattr(module, class_name, None)
            except (ModuleNotFoundError, ImportError, Exception) as e_imp:
                print(f"[Loader] Fallo al importar {mod_name}: {e_imp}")
                if faltantes:
                    # Mostrar widget de dependencias faltantes en la pestaña correspondiente
                    def _crear_reload_callback(sub_name_str, target_cls_name):
                        def _on_installed():
                            # Recargar submódulo en caliente
                            inst = load_submodules_from_config(
                                module_dir, tab_widget, parent_container, 
                                context=context, colores=colores, extra_kwargs=extra_kwargs
                            )
                        return _on_installed

                    missing_widget = MissingDependenciesWidget(
                        module_dir, name, faltantes,
                        on_success_callback=_crear_reload_callback(name, class_name),
                        colores=colores, parent=parent_container
                    )
                    tab_widget.addTab(missing_widget, name)
                    instances[class_name] = missing_widget
                    continue

            if cls is None:
                continue

            # Inyección inteligente de dependencias basada en la firma
            sig = inspect.signature(cls.__init__)
            params = sig.parameters
            kwargs = {}
            args = []

            param_map = {
                "parent": parent_container,
                "context": context,
                "colores": colores,
                "usuario": usuario,
                "persona": persona,
                "ruta_usuario": ruta_usuario,
            }
            if extra_kwargs:
                param_map.update(extra_kwargs)

            has_varargs = False
            has_varkw = False

            for p_name, p in list(params.items())[1:]:  # Omitir 'self'
                if p.kind == inspect.Parameter.VAR_POSITIONAL:
                    has_varargs = True
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
                            if "agregar" in p_name.lower() or "add" in p_name.lower():
                                args.append(param_map.get("agregar_al_historial_callback", param_map.get("add_hist", lambda *a, **k: None)))
                            elif "obtener" in p_name.lower() or "get" in p_name.lower():
                                args.append(param_map.get("obtener_historial_callback", param_map.get("get_hist_callback", lambda *a, **k: [])))
                            elif "limpiar" in p_name.lower() or "clean" in p_name.lower():
                                args.append(param_map.get("limpiar_historial_callback", param_map.get("clean_hist_callback", lambda *a, **k: None)))
                            else:
                                args.append(lambda *a, **k: None)
                        elif "colores" in p_name.lower() or "color" in p_name.lower():
                            args.append(colores)
                        elif "context" in p_name.lower():
                            args.append(context)
                        elif "path" in p_name.lower() or "ruta" in p_name.lower():
                            args.append(ruta_usuario)
                        else:
                            args.append(None)

            try:
                if has_varkw:
                    kwargs.setdefault("context", context)
                    kwargs.setdefault("colores", colores)
                instance = cls(*args, **kwargs)
            except TypeError:
                try:
                    instance = cls(parent_container, context)
                except TypeError:
                    try:
                        instance = cls(parent_container, context, colores)
                    except TypeError:
                        try:
                            instance = cls(parent_container)
                        except TypeError:
                            instance = cls()

            if isinstance(instance, QWidget):
                tab_widget.addTab(instance, name)
                instances[class_name] = instance
                instances[class_name.lower()] = instance
                if "id" in sub:
                    instances[sub["id"]] = instance

        except Exception as e:
            try:
                print(f"[Loader Error] Fallo al cargar submodulo '{class_name}': {e}")
            except Exception:
                pass

    return instances
