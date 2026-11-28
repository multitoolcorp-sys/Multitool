"""Mixin para navegación entre módulos, historial atrás/adelante y despacho de archivos."""

from pathlib import Path
from PyQt6.QtWidgets import QWidget


class NavigationMixin:
    """Provee historial de navegación y apertura/despacho universal entre módulos."""

    def navegar_atras(self):
        """Vuelve al módulo/submódulo anterior en el historial (Alt+←)."""
        if getattr(self, "_nav_history_idx", -1) > 0:
            self._nav_history_idx -= 1
            mod_name, sub_name = self._nav_history[self._nav_history_idx]
            self._nav_history_locked = True
            try:
                self.abrir_en_modulo(mod_name, submodulo_nombre=sub_name, registrar_historial=False)
            finally:
                self._nav_history_locked = False
            self._actualizar_botones_historial()

    def navegar_adelante(self):
        """Avanza al siguiente módulo/submódulo en el historial (Alt+→)."""
        if hasattr(self, "_nav_history") and getattr(self, "_nav_history_idx", -1) + 1 < len(self._nav_history):
            self._nav_history_idx += 1
            mod_name, sub_name = self._nav_history[self._nav_history_idx]
            self._nav_history_locked = True
            try:
                self.abrir_en_modulo(mod_name, submodulo_nombre=sub_name, registrar_historial=False)
            finally:
                self._nav_history_locked = False
            self._actualizar_botones_historial()

    def _actualizar_botones_historial(self):
        """Habilita o deshabilita los botones ◀ y ▶ según la posición en el historial."""
        if hasattr(self, "btn_nav_back") and self.btn_nav_back:
            can_back = getattr(self, "_nav_history_idx", -1) > 0
            self.btn_nav_back.setEnabled(can_back)
        if hasattr(self, "btn_nav_forward") and self.btn_nav_forward:
            can_fwd = hasattr(self, "_nav_history") and getattr(self, "_nav_history_idx", -1) + 1 < len(self._nav_history)
            self.btn_nav_forward.setEnabled(can_fwd)

    def abrir_en_modulo(self, modulo_nombre, submodulo_nombre=None, ruta_archivo=None, registrar_historial=True):
        """
        Método central universal para abrir o enviar archivos a cualquier módulo/submódulo
        compatible tanto en Modo MMS (Clásico) como en Modo IDE (Dashboard).
        """
        try:
            mod_target = None
            mod_idx = -1
            visibles = [m for m in getattr(self, "modulos_cargados", []) if m.get("visible", True)]
            for i, m in enumerate(visibles):
                if m.get("name", "").lower() == modulo_nombre.lower():
                    mod_target = m
                    mod_idx = i
                    break

            if not mod_target:
                print(f"[MultiTool] Módulo '{modulo_nombre}' no encontrado.")
                return False

            if not mod_target.get("loaded", False):
                self._instanciar_modulo(mod_target)

            container = getattr(self, "clases_modulos", {}).get(mod_target["name"])

            sub_idx = 0
            if submodulo_nombre and container and hasattr(container, "tabs") and isinstance(container.tabs, QWidget):
                for si in range(container.tabs.count()):
                    t_text = container.tabs.tabText(si).strip().lower()
                    if t_text == submodulo_nombre.strip().lower() or submodulo_nombre.strip().lower() in t_text:
                        sub_idx = si
                        submodulo_nombre = container.tabs.tabText(si).strip()
                        break
            elif not submodulo_nombre and container and hasattr(container, "tabs") and isinstance(container.tabs, QWidget):
                if container.tabs.count() > 0:
                    sub_idx = container.tabs.currentIndex()
                    submodulo_nombre = container.tabs.tabText(sub_idx).strip()

            modo = getattr(self, "modo_vista", "clasico")
            if modo == "dashboard":
                self.notebook.setCurrentIndex(mod_idx)
                if container and hasattr(container, "tabs") and isinstance(container.tabs, QWidget):
                    container.tabs.setCurrentIndex(sub_idx)
                self.notebook.show()
                if hasattr(self, "dashboard_empty_view"):
                    self.dashboard_empty_view.hide()
                clean_sub = (submodulo_nombre or "").strip()
                title = f"{modulo_nombre.capitalize()} › {clean_sub}" if clean_sub else modulo_nombre.capitalize()
                self.editor_tab_bar.add_tab(modulo_nombre, clean_sub, title, make_active=True)
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.renderizar_arbol()
            else:
                self.notebook.setCurrentIndex(mod_idx)
                if hasattr(self, "nav_bar"):
                    self.nav_bar.select_tab(mod_idx)
                if container and hasattr(container, "tabs") and isinstance(container.tabs, QWidget):
                    container.tabs.setCurrentIndex(sub_idx)

            if ruta_archivo:
                self._despachar_archivo_a_modulo(modulo_nombre, container, ruta_archivo)

            if registrar_historial and not getattr(self, "_nav_history_locked", False):
                if not hasattr(self, "_nav_history"):
                    self._nav_history = []
                    self._nav_history_idx = -1
                if self._nav_history_idx + 1 < len(self._nav_history):
                    self._nav_history = self._nav_history[:self._nav_history_idx + 1]
                self._nav_history.append((modulo_nombre, submodulo_nombre))
                self._nav_history_idx = len(self._nav_history) - 1
                self._actualizar_botones_historial()

            if getattr(self, "modo_vista", "") == "dashboard":
                self._guardar_sesion_editor_tabs()

            return True
        except Exception as e:
            print(f"[MultiTool] Error en abrir_en_modulo ({modulo_nombre}): {e}")
            return False

    def _despachar_archivo_a_modulo(self, modulo_nombre, container, ruta_archivo):
        """Despacha la ruta de archivo al módulo destino de manera desacoplada."""
        p = Path(ruta_archivo)
        if not p.exists():
            return

        m_low = modulo_nombre.lower()
        try:
            if m_low == "notas":
                notas_inst = None
                if container:
                    if hasattr(container, "import_manager"):
                        notas_inst = container
                    elif hasattr(container, "submodules_instances"):
                        for inst in container.submodules_instances.values():
                            if hasattr(inst, "import_manager"):
                                notas_inst = inst
                                break
                    if not notas_inst and hasattr(container, "tabs") and hasattr(container.tabs, "currentWidget"):
                        cw = container.tabs.currentWidget()
                        if hasattr(cw, "import_manager"):
                            notas_inst = cw
                if notas_inst and hasattr(notas_inst, "import_manager"):
                    notas_inst.import_manager.importar_archivo_individual(str(p))
                    if hasattr(notas_inst, "cargar_lista_notas"):
                        notas_inst.cargar_lista_notas()

            elif m_low == "reproductor":
                rep_inst = None
                if container:
                    if hasattr(container, "reproducir_directo"):
                        rep_inst = container
                    elif hasattr(container, "submodules_instances"):
                        for inst in container.submodules_instances.values():
                            if hasattr(inst, "reproducir_directo"):
                                rep_inst = inst
                                break
                if rep_inst:
                    rep_inst.reproducir_directo(str(p))

            elif m_low == "navegador":
                nav_browser = None
                if container:
                    from vistas.modulos.navegador.submodulos.integrado.browser import MultiTabBrowser
                    for ch in container.findChildren(MultiTabBrowser):
                        nav_browser = ch
                        break
                if nav_browser and hasattr(nav_browser, "add_new_tab"):
                    from PyQt6.QtCore import QUrl
                    nav_browser.add_new_tab(QUrl.fromLocalFile(str(p.resolve())), label=p.name)

            elif m_low == "cuaderno":
                pass
        except Exception as ex:
            print(f"[MultiTool] Error despachando archivo a {modulo_nombre}: {ex}")

    def _abrir_en_reproductor(self, path_str):
        self.abrir_en_modulo("reproductor", ruta_archivo=path_str)

    def _abrir_en_notas(self, path_str):
        self.abrir_en_modulo("notas", ruta_archivo=path_str)

    def _abrir_en_archivos(self, path_str):
        self.abrir_en_modulo("archivos", ruta_archivo=path_str)

    def _abrir_en_navegador(self, path_str):
        self.abrir_en_modulo("navegador", ruta_archivo=path_str)

    def _navegar_a_modulo_nombre(self, mod_name):
        self.abrir_en_modulo(mod_name)
