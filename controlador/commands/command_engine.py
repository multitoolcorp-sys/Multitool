import os
import sys
import re
import json
import datetime
from pathlib import Path


class PlaceholderParser:
    """
    Parser para resolución de placeholders y variables dinámicas en acciones y mensajes.
    Soporta:
      - %user% o %player%: Nombre del usuario / perfil actual.
      - %module%: Nombre del módulo actualmente en foco.
      - %app%: Nombre de la aplicación (MultiTool).
      - %date%: Fecha actual (YYYY-MM-DD).
      - %time%: Hora actual (HH:MM:SS).
      - %points%: Puntos totales de la cuenta activa.
      - %args%: Cadena completa de argumentos recibidos.
      - %arg_N%: Argumento posicional N (1-based), ej: %arg_1%.
      - %arg_N:valor_defecto%: Argumento posicional con valor predeterminado si no se provee.
    """
    @staticmethod
    def replace(template: str, context: dict, args: list) -> str:
        if not template or not isinstance(template, str):
            return ""

        res = template
        user = context.get("user", "Usuario")
        module = context.get("module", "General")
        app_name = context.get("app", "MultiTool")
        points = str(context.get("points", 0))

        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        # Reemplazos básicos
        res = res.replace("%user%", user)
        res = res.replace("%player%", user)
        res = res.replace("%module%", module)
        res = res.replace("%current_module%", module)
        res = res.replace("%app%", app_name)
        res = res.replace("%date%", date_str)
        res = res.replace("%time%", time_str)
        res = res.replace("%points%", points)
        res = res.replace("%args%", " ".join(args) if args else "")

        # Reemplazo de argumentos posicionales con valor por defecto: %arg_1:defecto%
        def _replace_arg_default(match):
            idx = int(match.group(1)) - 1
            default_val = match.group(2)
            if 0 <= idx < len(args) and args[idx]:
                return args[idx]
            return default_val

        res = re.sub(r'%arg_(\d+):([^%]+)%', _replace_arg_default, res)

        # Reemplazo de argumentos posicionales estándar: %arg_1%
        def _replace_arg_simple(match):
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(args):
                return args[idx]
            return ""

        res = re.sub(r'%arg_(\d+)%', _replace_arg_simple, res)

        return res


class ModuleCommandRegistry:
    """
    Registro y cargador dinámico de manifiestos de comandos específicos por módulo (commands.json).
    Descubre los archivos commands.json en vistas/modulos/<nombre>/commands.json.
    """
    def __init__(self, modulos_dir: Path = None):
        if modulos_dir:
            p = Path(modulos_dir)
            if (p / "vistas" / "modulos").exists():
                self.modulos_dir = p / "vistas" / "modulos"
            else:
                self.modulos_dir = p
        else:
            self.modulos_dir = Path(__file__).resolve().parents[2] / "vistas" / "modulos"
        self._cache = {}
        self.recargar()

    def recargar(self):
        """Escanea todos los directorios de módulos y carga sus comandos JSON."""
        self._cache.clear()
        if not self.modulos_dir.exists():
            return

        for item in self.modulos_dir.iterdir():
            if item.is_dir() and not item.name.startswith((".", "_")):
                cmd_file = item / "commands.json"
                if cmd_file.exists():
                    try:
                        with open(cmd_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        mod_key = item.name.lower()
                        self._cache[mod_key] = data
                    except Exception as e:
                        print(f"[CommandRegistry] Error al leer {cmd_file}: {e}")

    def obtener_modulos_disponibles(self) -> list:
        """Devuelve una lista con los nombres de carpetas de todos los módulos del sistema."""
        mods = []
        if self.modulos_dir.exists():
            for item in self.modulos_dir.iterdir():
                if item.is_dir() and not item.name.startswith((".", "_")):
                    mods.append(item.name.lower())
        return sorted(mods)

    def obtener_modulos_con_comandos(self) -> dict:
        """Devuelve diccionario de módulos que tienen archivo commands.json cargado."""
        return self._cache

    def obtener_comandos_de_modulo(self, module_name: str) -> list:
        """Devuelve la lista de comandos definidos para un módulo específico."""
        mod_key = module_name.lower().strip()
        data = self._cache.get(mod_key)
        if data:
            return data.get("commands", [])
        return []

    def buscar_comando(self, cmd_name: str, module_name: str = None) -> tuple:
        """
        Busca un comando por nombre o alias.
        Retorna (module_name, comando_dict) o (None, None).
        Si module_name se especifica, prioriza la búsqueda en ese módulo.
        """
        clean_name = cmd_name.lower().strip()
        if clean_name.startswith("/"):
            clean_name = clean_name[1:]

        # 1. Buscar en módulo específico si se provee
        if module_name:
            mod_key = module_name.lower().strip()
            data = self._cache.get(mod_key)
            if data:
                for c in data.get("commands", []):
                    c_cmd = c.get("command", "") or c.get("command_sudo", "") or c.get("trigger", "")
                    c_clean = c_cmd.lstrip("/").lower()
                    aliases = [a.lstrip("/").lower() for a in c.get("aliases", [])]
                    c_name = c.get("name", "").lower()

                    if clean_name == c_clean or clean_name in aliases or clean_name == c_name:
                        return (mod_key, c)

        # 2. Si no se encontró o no se pasó módulo, buscar en todos los módulos registrados
        for mod_key, data in self._cache.items():
            for c in data.get("commands", []):
                c_cmd = c.get("command", "") or c.get("command_sudo", "") or c.get("trigger", "")
                c_clean = c_cmd.lstrip("/").lower()
                aliases = [a.lstrip("/").lower() for a in c.get("aliases", [])]
                c_name = c.get("name", "").lower()

                if clean_name == c_clean or clean_name in aliases or clean_name == c_name:
                    return (mod_key, c)

        return (None, None)


class CommandEngine:
    """
    Motor central de ejecución de comandos profesionales para MultiTool:
    - Comandos globales integrados de gestión, navegación y auditoría.
    - Soporte para módulos activos con comandos personalizados cargados desde commands.json.
    - Procesamiento de acciones modulares y placeholders dinámicos.
    """
    def __init__(self, context=None, main_window=None, user_path=None):
        self.context = context
        self.main_window = main_window
        self.user_path = user_path or self._detect_user_path()
        self.active_module = None  # None = Global, o string con nombre de módulo activo

        # Importar gestor de trampas y ventajas
        try:
            from console import CheatManager
            self.cheat_mgr = CheatManager.get_instance()
        except Exception:
            self.cheat_mgr = None

        self.registry = ModuleCommandRegistry()

    def _detect_user_path(self):
        candidates = [
            Path.cwd() / "cuentas" / "Luna",
            Path.cwd() / "cuentas" / "default",
            Path.cwd()
        ]
        for c in candidates:
            if (c / "minigames_scores.json").exists() or (c / "extras_scores.json").exists():
                return c
        cdir = Path.cwd() / "cuentas"
        if cdir.exists():
            for sub in cdir.iterdir():
                if sub.is_dir():
                    return sub
        return Path.cwd()

    def get_prompt_label(self) -> str:
        """Devuelve el texto del prompt para la interfaz de consola."""
        if self.active_module:
            return f"[{self.active_module}] > "
        return "[global] > "

    def execute(self, raw_cmd: str) -> list:
        """
        Ejecuta una línea de comando y devuelve una lista de mensajes coloreados (§).
        """
        cmd = raw_cmd.strip()
        if not cmd:
            return []

        if cmd.startswith("/"):
            cmd = cmd[1:].strip()

        partes = cmd.split()
        if not partes:
            return []

        nombre = partes[0].lower()
        args = partes[1:]

        try:
            # 1. Comandos Globales Integrados
            if nombre in ["help", "ayuda", "?"]:
                return self._cmd_help(args)
            elif nombre in ["use", "usar", "select", "modulo"]:
                return self._cmd_use(args)
            elif nombre in ["unuse", "deseleccionar", "leave", "global"]:
                self.active_module = None
                return ["§e[Command Engine] Contexto restablecido a comandos globales.§r"]
            elif nombre in ["modules", "modulos", "list"]:
                return self._cmd_modules(args)
            elif nombre in ["goto", "ir"]:
                return self._cmd_goto(args)
            elif nombre in ["status", "info"]:
                return self._cmd_status(args)
            elif nombre in ["clear", "cls"]:
                return ["__CLEAR__"]
            elif nombre in ["points", "puntos", "score"]:
                return self._cmd_points(args)
            elif nombre in ["give"]:
                return self._cmd_give(args)
            elif nombre in ["cheat", "cheats", "trampa", "trampas"]:
                return self._cmd_cheats(args)
            elif nombre in ["godmode", "god"]:
                return self._cmd_godmode(args)
            elif nombre in ["luck", "suerte"]:
                return self._cmd_luck(args)
            elif nombre in ["lives", "vida", "vidas"]:
                return self._cmd_lives(args)
            elif nombre in ["damage", "danio", "daño"]:
                return self._cmd_damage(args)
            elif nombre in ["jackpot"]:
                return self._cmd_jackpot(args)
            elif nombre in ["logs", "log"]:
                return self._cmd_logs(args)

            # 2. Búsqueda y Ejecución de Comandos Específicos por Módulo (commands.json)
            mod_found, cmd_def = self.registry.buscar_comando(nombre, self.active_module)
            if cmd_def:
                return self._ejecutar_comando_modulo(mod_found, cmd_def, args)

            # 3. Comando Desconocido
            active_info = f" en contexto '{self.active_module}'" if self.active_module else ""
            return [
                f"§cComando desconocido: '{nombre}'{active_info}.§r",
                "§7Escribe §ehelp §7para consultar los comandos disponibles o §euse module <nombre> §7para cambiar de módulo."
            ]

        except Exception as e:
            return [f"§c[Error ejecutando '{cmd}']: {e}§r"]

    def _cmd_use(self, args: list) -> list:
        if not args:
            return [
                "§cFormato: use module <nombre>  ó  use <nombre>§r",
                "§7Ejemplos: §fuse minigames§7, §fuse extras§7, §fuse proyectos§7. Para volver a comandos globales usa §fuse default§7."
            ]

        target = args[0].lower()
        if target == "module" and len(args) > 1:
            target = args[1].lower()

        if target in ["default", "global", "none", "off"]:
            self.active_module = None
            return ["§e[Command Engine] Contexto restablecido a comandos globales.§r"]

        todos = self.registry.obtener_modulos_disponibles()
        con_cmds = self.registry.obtener_modulos_con_comandos()

        if target not in todos:
            # Búsqueda difusa
            match = next((m for m in todos if target in m), None)
            if match:
                target = match
            else:
                return [
                    f"§cMódulo '{target}' no encontrado en la aplicación.§r",
                    f"§7Módulos existentes: {', '.join(todos)}"
                ]

        self.active_module = target
        cmds = self.registry.obtener_comandos_de_modulo(target)
        cnt = len(cmds)

        out = [
            f"§a[Command Engine] Módulo activo establecido en: §e{target.upper()}§a.§r"
        ]
        if cnt > 0:
            out.append(f"§7Manifiesto commands.json cargado: §f{cnt} comando(s) personalizado(s) disponible(s).§r")
            out.append("§7Escribe §ehelp §7para ver la lista de comandos de este módulo.")
        else:
            out.append(f"§7(Nota: El módulo '{target}' no cuenta con un archivo commands.json personalizado aún).§r")

        return out

    def _cmd_modules(self, args: list) -> list:
        todos = self.registry.obtener_modulos_disponibles()
        con_cmds = self.registry.obtener_modulos_con_comandos()

        lineas = ["§6=== 📦 MÓDULOS DE MULTITOOL ===§r"]
        for m in todos:
            tiene = "§a[commands.json]§r" if m in con_cmds else "§8[estándar]§r"
            activo = " §e★ (ACTIVO)§r" if self.active_module == m else ""
            lineas.append(f"§f• {m.capitalize()} {tiene}{activo}")

        lineas.append("§7Usa §euse module <nombre> §7para activar los comandos específicos de un módulo.")
        return lineas

    def _cmd_help(self, args: list) -> list:
        lineas = []

        # Si hay un módulo activo, mostrar primero sus comandos específicos
        if self.active_module:
            cmds = self.registry.obtener_comandos_de_modulo(self.active_module)
            lineas.append(f"§6=== 🛠️ COMANDOS ESPECÍFICOS DEL MÓDULO [{self.active_module.upper()}] ===§r")
            if cmds:
                for c in cmds:
                    cmd_str = c.get("command", "") or c.get("command_sudo", "")
                    syntax = c.get("syntax", cmd_str)
                    desc = c.get("description", c.get("name", ""))
                    lineas.append(f"§e{syntax} §7- {desc}")
            else:
                lineas.append("§7No se registraron comandos personalizados en commands.json para este módulo.")
            lineas.append("§7Para salir de este módulo y volver al contexto global escribe §euse default§7.")
            lineas.append("")

        # Comandos globales
        lineas.extend([
            "§6=== ⚡ COMANDOS GLOBALES DE MULTITOOL ===§r",
            "§euse module <nombre> §7- Selecciona un módulo para usar sus comandos personalizados.",
            "§euse default §7- Restablece el contexto a comandos globales.",
            "§emodules §7- Lista todos los módulos y cuáles tienen commands.json.",
            "§egoto <modulo> §7- Navega visualmente hacia el módulo indicado.",
            "§estatus §7- Muestra información del usuario, módulo activo y estado.",
            "§eclear §7- Limpia la pantalla de la terminal.",
            "§epoints [add|set] <cant> §7- Administra puntos del perfil de usuario.",
            "§echeats §7- Consulta o activa opciones de ventaja en minijuegos.",
            "§elogs [clear] §7- Administra los registros de eventos de la terminal."
        ])
        return lineas

    def _ejecutar_comando_modulo(self, module_name: str, cmd_def: dict, args: list) -> list:
        """Ejecuta las acciones definidas en el commands.json para un comando."""
        actions = cmd_def.get("actions", [])
        if isinstance(actions, str):
            actions = [actions]

        # Contexto para resolución de placeholders
        sm_pts = 0
        try:
            from vistas.modulos.minigames.utils.score_manager import ScoreManager
            sm = ScoreManager(self.user_path)
            sm_pts = sm.get_total_puntos()
        except Exception:
            pass

        context = {
            "user": self.user_path.name if self.user_path else "Usuario",
            "module": module_name,
            "app": "MultiTool",
            "points": sm_pts
        }

        output = []
        for raw_action in actions:
            action_text = PlaceholderParser.replace(raw_action, context, args).strip()
            if not action_text:
                continue

            # Parsear tipo de acción
            if action_text.startswith("message:") or action_text.startswith("echo:"):
                msg = action_text.split(":", 1)[1].strip()
                output.append(msg)

            elif action_text.startswith("success:"):
                msg = action_text.split(":", 1)[1].strip()
                output.append(f"§a[Éxito] {msg}§r")

            elif action_text.startswith("warning:"):
                msg = action_text.split(":", 1)[1].strip()
                output.append(f"§e[Aviso] {msg}§r")

            elif action_text.startswith("error:"):
                msg = action_text.split(":", 1)[1].strip()
                output.append(f"§c[Error] {msg}§r")

            elif action_text.startswith("exec:") or action_text.startswith("cmd:"):
                sub_cmd = action_text.split(":", 1)[1].strip()
                sub_res = self.execute(sub_cmd)
                output.extend(sub_res)

            elif action_text.startswith("goto:") or action_text.startswith("module:"):
                dest = action_text.split(":", 1)[1].strip()
                res = self._cmd_goto([dest])
                output.extend(res)

            elif action_text.startswith("tab:"):
                t_arg = action_text.split(":", 1)[1].strip()
                self._cambiar_pestana_modulo(t_arg)

            elif action_text.startswith("cheat:"):
                cheat_arg = action_text.split(":", 1)[1].strip().split()
                if self.cheat_mgr and cheat_arg:
                    tipo = cheat_arg[0].lower()
                    val = cheat_arg[1:] if len(cheat_arg) > 1 else []
                    if tipo in ["godmode", "god"]:
                        self._cmd_godmode(val)
                    elif tipo in ["vida", "vidas", "lives"]:
                        self._cmd_lives(val)
                    elif tipo in ["suerte", "luck"]:
                        self._cmd_luck(val)
                    elif tipo in ["jackpot"]:
                        self._cmd_jackpot([])
                    elif tipo in ["daño", "danio", "damage"]:
                        self._cmd_damage(val)

            elif action_text.startswith("action:"):
                act_name = action_text.split(":", 1)[1].strip()
                self._invocar_accion_en_vista(module_name, act_name)

        if not output:
            cmd_name = cmd_def.get("name", cmd_def.get("command", "comando"))
            output.append(f"§a[Comando] '{cmd_name}' ejecutado correctamente.§r")

        return output

    def _cambiar_pestana_modulo(self, tab_arg: str):
        """Intenta cambiar la pestaña activa dentro del módulo visual si tiene QTabWidget."""
        if not self.main_window or not hasattr(self.main_window, "notebook"):
            return
        nb = self.main_window.notebook
        current_widget = nb.currentWidget()
        if not current_widget:
            return

        # Buscar pestañas en el widget actual
        tabs_obj = getattr(current_widget, "tabs", None)
        if tabs_obj and hasattr(tabs_obj, "setCurrentIndex"):
            try:
                # Si es un número de índice
                idx = int(tab_arg)
                if 0 <= idx < tabs_obj.count():
                    tabs_obj.setCurrentIndex(idx)
                    return
            except ValueError:
                # Si es texto de pestaña
                for i in range(tabs_obj.count()):
                    if tab_arg.lower() in tabs_obj.tabText(i).lower():
                        tabs_obj.setCurrentIndex(i)
                        return

    def _invocar_accion_en_vista(self, module_name: str, action_name: str):
        """Invoca un método o acción en la vista del módulo si existe."""
        if not self.main_window or not hasattr(self.main_window, "notebook"):
            return
        nb = self.main_window.notebook
        current_widget = nb.currentWidget()
        if not current_widget:
            return

        partes = action_name.split()
        method_name = partes[0]
        params = partes[1:]

        for target in [current_widget, getattr(current_widget, "gui", None)]:
            if target and hasattr(target, method_name) and callable(getattr(target, method_name)):
                try:
                    fn = getattr(target, method_name)
                    if params:
                        fn(*params)
                    else:
                        fn()
                    break
                except Exception as e:
                    print(f"[CommandEngine] Error al invocar acción {method_name}: {e}")

    # ── MÉTODOS DE COMANDOS ESTÁNDAR (COMPATIBILIDAD) ──────────────────
    def _cmd_points(self, args):
        try:
            from vistas.modulos.minigames.utils.score_manager import ScoreManager
            sm = ScoreManager(self.user_path)
        except Exception as e:
            return [f"§c[ScoreManager] No disponible: {e}"]

        if not args or args[0] in ["get", "show"]:
            tot = sm.get_total_puntos()
            return [
                f"§a[Puntos] §fPuntos totales consolidados: §6{tot:,} PTS§r",
                f"§7Guardados en: §f{sm.archivo_minigames.name} §7y §f{sm.archivo_txt.name}"
            ]

        sub = args[0].lower()
        if sub in ["add", "sumar"]:
            if len(args) < 2:
                return ["§cFormato: points add <cantidad> [juego]"]
            try:
                pts = int(args[1])
            except ValueError:
                return [f"§cValor inválido: {args[1]}"]
            juego = args[2].lower() if len(args) > 2 else "casino"
            nuevo = sm.sumar_puntos(juego, pts)
            tot = sm.get_total_puntos()
            self._refresh_points_ui(tot)
            return [
                f"§a[Puntos] §fAñadidos §6+{pts:,} PTS §fa '{juego}'.",
                f"§a[Puntos] §fSaldo total actualizado: §e{tot:,} PTS§r"
            ]

        elif sub in ["set", "fijar"]:
            if len(args) < 2:
                return ["§cFormato: points set <cantidad>"]
            try:
                pts = int(args[1])
            except ValueError:
                return [f"§cValor inválido: {args[1]}"]
            tot = sm.set_puntos_totales(pts)
            self._refresh_points_ui(tot)
            return [f"§a[Puntos] §fSaldo total establecido en: §6{tot:,} PTS§r"]

        elif sub in ["reset"]:
            tot = sm.set_puntos_totales(0)
            self._refresh_points_ui(0)
            return ["§e[Puntos] Saldo reseteado a 0 PTS."]

        return ["§cSubcomando desconocido. Usa points add o points set."]

    def _refresh_points_ui(self, nuevo_total=None):
        try:
            from vistas.modulos.minigames.utils.score_manager import ScoreManager
            ScoreManager.notificar_cambio(nuevo_total)
        except Exception:
            pass
        if not self.main_window:
            return
        try:
            notebook = getattr(self.main_window, "notebook", None)
            if notebook:
                for idx in range(notebook.count()):
                    w = notebook.widget(idx)
                    if hasattr(w, "gui_user") and hasattr(w.gui_user, "actualizar_puntos_ui"):
                        w.gui_user.actualizar_puntos_ui(nuevo_total)
                    elif hasattr(w, "actualizar_puntos_ui"):
                        w.actualizar_puntos_ui(nuevo_total)
            modulos = getattr(self.main_window, "modulos_cargados", {})
            if isinstance(modulos, dict):
                cuenta_mod = modulos.get("cuenta")
                if cuenta_mod:
                    gui_u = getattr(cuenta_mod, "gui_user", None)
                    if gui_u and hasattr(gui_u, "actualizar_puntos_ui"):
                        gui_u.actualizar_puntos_ui(nuevo_total)
        except Exception:
            pass

    def _cmd_give(self, args):
        if len(args) >= 2 and args[0].lower() in ["points", "puntos", "@s"]:
            pts_str = args[1] if args[0].lower() in ["points", "puntos"] else (args[2] if len(args) > 2 else "100")
            try:
                pts = int(pts_str)
            except ValueError:
                return [f"§cValor inválido: {pts_str}"]
            return self._cmd_points(["add", str(pts), "casino"])
        return ["§cFormato: give points <cantidad>"]

    def _cmd_cheats(self, args):
        if not self.cheat_mgr:
            return ["§cGestor de ventajas no disponible."]
        if not args:
            st = self.cheat_mgr.get_status_dict()
            estado_gen = "§aACTIVADAS" if st["cheats_activos"] else "§cDESACTIVADAS"
            return [
                f"§6=== ⚙️ ESTADO DE VENTAJAS ({estado_gen}) ===§r",
                f"§7• Modo Invencible (Godmode): §f{st['godmode_invencible']}",
                f"§7• Vidas Fijas: §f{st['vidas_fijadas']}",
                f"§7• Multiplicador de Daño: §f{st['multiplicador_danio']}",
                f"§7• Probabilidad Casino: §f{st['suerte_casino']}",
                f"§7• Premio Mayor Pendiente: §f{st['jackpot_pendiente']}",
                "§7Usa §echeat [on|off] §7o configura individualmente con §echeat <opcion>§7."
            ]

        sub = args[0].lower()
        if sub in ["on", "enable", "activar"]:
            self.cheat_mgr.cheats_enabled = True
            return ["§a[Ventajas] Modo ventajas ACTIVADO globalmente."]
        elif sub in ["off", "disable", "desactivar"]:
            self.cheat_mgr.reset_cheats()
            return ["§c[Ventajas] Modo ventajas DESACTIVADO globalmente."]
        elif sub in ["godmode", "god"]:
            return self._cmd_godmode(args[1:])
        elif sub in ["luck", "suerte"]:
            return self._cmd_luck(args[1:])
        elif sub in ["lives", "vida", "vidas"]:
            return self._cmd_lives(args[1:])
        elif sub in ["damage", "danio", "daño"]:
            return self._cmd_damage(args[1:])
        elif sub in ["jackpot"]:
            return self._cmd_jackpot(args[1:])
        return ["§cOpción desconocida. Usa cheats para ver el estado."]

    def _cmd_godmode(self, args):
        if not self.cheat_mgr: return ["§cNo disponible."]
        self.cheat_mgr.cheats_enabled = True
        if args and args[0].lower() in ["off", "false", "0", "no"]:
            self.cheat_mgr.godmode = False
            return ["§e[Godmode] Invencibilidad desactivada."]
        self.cheat_mgr.godmode = True
        return ["§a[Godmode] ¡Invencibilidad ACTIVADA! No recibirás daño en minijuegos arcade."]

    def _cmd_luck(self, args):
        if not self.cheat_mgr: return ["§cNo disponible."]
        self.cheat_mgr.cheats_enabled = True
        if args and args[0].lower() in ["off", "false", "0", "no"]:
            self.cheat_mgr.casino_luck = False
            return ["§e[Suerte] Probabilidad en juegos de azar restablecida a nivel normal."]
        self.cheat_mgr.casino_luck = True
        return ["§a[Suerte] ¡Suerte aumentada ACTIVADA para Slots, Ruleta y Blackjack!"]

    def _cmd_lives(self, args):
        if not self.cheat_mgr: return ["§cNo disponible."]
        self.cheat_mgr.cheats_enabled = True
        if not args:
            self.cheat_mgr.extra_lives = 99
            return ["§a[Vidas] Vidas fijadas a 99 en juegos arcade."]
        try:
            v = int(args[0])
            self.cheat_mgr.extra_lives = v
            return [f"§a[Vidas] Vidas fijadas a {v} en juegos arcade."]
        except ValueError:
            return [f"§cValor inválido: {args[0]}"]

    def _cmd_damage(self, args):
        if not self.cheat_mgr: return ["§cNo disponible."]
        self.cheat_mgr.cheats_enabled = True
        if not args:
            self.cheat_mgr.damage_multiplier = 5.0
            return ["§a[Daño] Daño de proyectiles aumentado a x5.0."]
        try:
            m = float(args[0])
            self.cheat_mgr.damage_multiplier = m
            return [f"§a[Daño] Daño de proyectiles establecido en x{m}."]
        except ValueError:
            return [f"§cValor inválido: {args[0]}"]

    def _cmd_jackpot(self, args):
        if not self.cheat_mgr: return ["§cNo disponible."]
        self.cheat_mgr.cheats_enabled = True
        self.cheat_mgr.force_jackpot = True
        return ["§6[Casino] ¡Jackpot 777 garantizado para la siguiente tirada de Tragamonedas!"]

    def _cmd_goto(self, args):
        if not args:
            return ["§cFormato: goto <nombre_modulo> (ej: goto minigames)"]
        destino = args[0].lower()

        if self.main_window and hasattr(self.main_window, "notebook"):
            nb = self.main_window.notebook
            for i in range(nb.count()):
                t_name = nb.tabText(i).lower()
                if destino in t_name:
                    nb.setCurrentIndex(i)
                    return [f"§a[Navegación] Cambiado a módulo: §e{nb.tabText(i)}§r"]

        return [f"§cNo se pudo encontrar el módulo '{destino}' o la interfaz no está vinculada."]

    def _cmd_status(self, args):
        pts = 0
        try:
            from vistas.modulos.minigames.utils.score_manager import ScoreManager
            sm = ScoreManager(self.user_path)
            pts = sm.get_total_puntos()
        except Exception:
            pass

        cheats_act = False
        if self.cheat_mgr:
            cheats_act = self.cheat_mgr.cheats_enabled

        return [
            "§6=== ℹ️ ESTADO GENERAL DE MULTITOOL ===§r",
            f"§7• Perfil de Usuario: §f{self.user_path.name if self.user_path else 'Desconocido'}",
            f"§7• Módulo Activo en Consola: §e{self.active_module.upper() if self.active_module else 'GLOBAL (Sin Módulo Fijo)'}",
            f"§7• Puntos Consolidados: §6{pts:,} PTS",
            f"§7• Modo Ventajas: §f{'Activado' if cheats_act else 'Desactivado'}"
        ]

    def _cmd_logs(self, args):
        try:
            from console import TerminalLogManager
            lm = TerminalLogManager.get_instance()
            if args and args[0].lower() in ["clear", "limpiar"]:
                lm.history.clear()
                return ["§a[Logs] Historial de terminal limpiado con éxito."]
            return [
                "§6=== 📋 REGISTRO DE TERMINAL Y EVENTOS ===§r",
                f"§7• Captura activa: §a{'Sí' if lm.installed else 'No'}",
                f"§7• Mensajes en búfer: §f{len(lm.history)}",
                "§7Usa §elogs clear §7para vaciar el buffer o §eclear §7para limpiar la pantalla."
            ]
        except Exception as e:
            return [f"§cError consultando logs: {e}"]
