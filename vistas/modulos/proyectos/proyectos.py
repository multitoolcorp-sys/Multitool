"""
TabProyectos — Gestor de Proyectos / TODO Kanban & Agile Studio
Controlador principal. Gestiona la persistencia JSON de proyectos, Kanban, Scrum, Code Studio, estadísticas y archivados.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QMessageBox, QInputDialog, QTabWidget,
    QPushButton, QMenu
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QAction, QCursor

from .submodulos.gui_proyectos import ProyectosGUI
from .submodulos.scrum_proyectos import TabScrumProyectos
from .submodulos.codigo_proyectos import TabEditorCodigoProyectos
from .submodulos.estadisticas import TabEstadisticasProyectos
from .submodulos.archivados import TabArchivadosProyectos


class TabProyectos(QWidget):
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.usuario = getattr(context, "usuario", "Invitado")
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        })

        self.ruta_data = self.ruta_usuario / "proyectos.json"
        self.ruta_config_vista = self.ruta_usuario / "config_proyectos_vista.json"
        self.proyectos = []          # Lista de dicts de proyectos
        self.proyecto_activo = None  # ID del proyecto seleccionado

        self.cargar_datos()

        callbacks = {
            "nuevo_proyecto":       self.nuevo_proyecto,
            "seleccionar_proyecto": self.seleccionar_proyecto,
            "eliminar_proyecto":    self.eliminar_proyecto,
            "renombrar_proyecto":   self.renombrar_proyecto,
            "archivar_proyecto":    self.archivar_proyecto,
            "importar_proyecto":    self.importar_proyecto,
            "nueva_tarea":          self.nueva_tarea,
            "duplicar_tarea":       self.duplicar_tarea,
            "mover_tarea":          self.mover_tarea,
            "editar_tarea":         self.editar_tarea,
            "eliminar_tarea":       self.eliminar_tarea,
            "get_proyectos":        lambda: self.proyectos,
            "get_tareas":           self.get_tareas,
            "guardar_datos":        self.guardar_datos,
        }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # QTabWidget principal
        self.tabs = QTabWidget()
        self._aplicar_estilos_tabs()

        # Botón de menú de vista en esquina derecha superior
        self.btn_vista_menu = QPushButton("⚙️ Vista")
        self.btn_vista_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_vista_menu.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 5px; padding: 4px 10px; font-size: 11px; font-weight: bold; margin: 4px;
            }}
            QPushButton:hover {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white; border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.btn_vista_menu.clicked.connect(self._mostrar_menu_vista)
        self.tabs.setCornerWidget(self.btn_vista_menu, Qt.Corner.TopRightCorner)

        # Context menu en la barra de pestañas
        tab_bar = self.tabs.tabBar()
        tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tab_bar.customContextMenuRequested.connect(self._mostrar_menu_pestana)

        # Cargar submódulos dinámicos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        extra_kwargs = {
            "callbacks": callbacks,
            "fn_obtener_proyectos": lambda: self.proyectos,
            "get_proyectos_cb": lambda: self.proyectos
        }
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores, extra_kwargs)

        if self.tabs.count() == 0:
            self.gui = ProyectosGUI(self, self.colores, callbacks)
            self.tab_scrum = TabScrumProyectos(self, self.colores, callbacks)
            self.tab_code = TabEditorCodigoProyectos(self, self.colores, callbacks)
            self.tab_stats = TabEstadisticasProyectos(self, self.colores, lambda: self.proyectos)
            self.tab_archivados = TabArchivadosProyectos(self, self.colores, callbacks)

            self.tabs.addTab(self.gui, "📋 Tablero Kanban")
            self.tabs.addTab(self.tab_scrum, "🏃 Metodología Scrum")
            self.tabs.addTab(self.tab_code, "💻 Editor de Código")
            self.tabs.addTab(self.tab_stats, "📊 Estadísticas")
            self.tabs.addTab(self.tab_archivados, "📦 Archivados & Exportación")
        else:
            self.gui = self.submod_instances.get("ProyectosGUI") or self.submod_instances.get("proyectosgui")
            if not self.gui:
                self.gui = ProyectosGUI(self, self.colores, callbacks)
            self.tab_scrum = self.submod_instances.get("TabScrumProyectos")
            self.tab_code = self.submod_instances.get("TabEditorCodigoProyectos")
            self.tab_stats = self.submod_instances.get("TabEstadisticasProyectos")
            self.tab_archivados = self.submod_instances.get("TabArchivadosProyectos")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

        # Restaurar vista guardada y proyecto activo
        self.cargar_config_vista()

    def _aplicar_estilos_tabs(self):
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores.get('bg_principal', '#121218')};
            }}
            QTabBar::tab {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: bold;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
        """)

    def _on_tab_changed(self, idx):
        self.guardar_config_vista()
        widget = self.tabs.widget(idx)
        if widget == self.tab_stats and self.tab_stats:
            self.tab_stats.actualizar_metricas()
        elif widget == self.tab_archivados and self.tab_archivados:
            self.tab_archivados.refrescar_archivados()
        elif widget == self.tab_scrum and self.tab_scrum:
            self.tab_scrum.configurar_proyecto(self.proyecto_activo)
        elif widget == self.tab_code and self.tab_code:
            p = self._proyecto_por_id(self.proyecto_activo)
            self.tab_code.configurar_proyecto(p)
        elif widget == self.gui and self.gui:
            if self.proyecto_activo:
                self.gui.mostrar_tablero(self.proyecto_activo)

    # ── Menú de Vista y Pestañas ──────────────────────────────────────────
    def _mostrar_menu_vista(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {self.colores['bg_terciario']}; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); }}
            QMenu::item {{ color: white; padding: 6px 16px; }}
            QMenu::item:selected {{ background: {self.colores['acento']}; }}
        """)
        for i in range(self.tabs.count()):
            texto = self.tabs.tabText(i)
            action = menu.addAction(f"Ir a: {texto}")
            action.triggered.connect(lambda checked, idx=i: self.tabs.setCurrentIndex(idx))

        menu.addSeparator()
        def_action = menu.addAction("📌 Establecer pestaña actual como vista por defecto")
        def_action.triggered.connect(lambda: self.guardar_config_vista(forzar_defecto=True))

        menu.exec(QCursor.pos())

    def _mostrar_menu_pestana(self, pos):
        idx = self.tabs.tabBar().tabAt(pos)
        if idx < 0:
            return
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {self.colores['bg_terciario']}; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); }}
            QMenu::item {{ color: white; padding: 6px 16px; }}
            QMenu::item:selected {{ background: {self.colores['acento']}; }}
        """)
        act_sel = menu.addAction(f"Ir a {self.tabs.tabText(idx)}")
        act_sel.triggered.connect(lambda: self.tabs.setCurrentIndex(idx))

        act_def = menu.addAction("📌 Abrir siempre en esta pestaña")
        act_def.triggered.connect(lambda: self._fijar_pestana_defecto(idx))

        menu.exec(self.tabs.tabBar().mapToGlobal(pos))

    def _fijar_pestana_defecto(self, idx):
        self.tabs.setCurrentIndex(idx)
        self.guardar_config_vista(forzar_defecto=True)
        QMessageBox.information(self, "Vista Configurada", f"'{self.tabs.tabText(idx)}' se abrirá de manera predeterminada.")

    # ── Persistencia de Configuración de Vista ───────────────────────────
    def cargar_config_vista(self):
        if self.ruta_config_vista.exists():
            try:
                with open(self.ruta_config_vista, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                pestana = cfg.get("pestana_activa", 0)
                if 0 <= pestana < self.tabs.count():
                    self.tabs.setCurrentIndex(pestana)
                ultimo_pid = cfg.get("ultimo_proyecto_id")
                if ultimo_pid and self._proyecto_por_id(ultimo_pid):
                    self.seleccionar_proyecto(ultimo_pid)
                elif self.proyectos:
                    self.seleccionar_proyecto(self.proyectos[0]["id"])
            except Exception:
                pass
        else:
            if self.proyectos:
                self.seleccionar_proyecto(self.proyectos[0]["id"])

    def guardar_config_vista(self, forzar_defecto=False):
        try:
            cfg = {
                "pestana_activa": self.tabs.currentIndex(),
                "ultimo_proyecto_id": self.proyecto_activo,
                "pestana_nombre": self.tabs.tabText(self.tabs.currentIndex())
            }
            with open(self.ruta_config_vista, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    # ── Persistencia de Proyectos ─────────────────────────────────────────
    def cargar_datos(self):
        if self.ruta_data.exists():
            try:
                with open(self.ruta_data, "r", encoding="utf-8") as f:
                    self.proyectos = json.load(f)
            except Exception:
                self.proyectos = []

    def guardar_datos(self):
        try:
            with open(self.ruta_data, "w", encoding="utf-8") as f:
                json.dump(self.proyectos, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def _proyecto_por_id(self, pid):
        return next((p for p in self.proyectos if p["id"] == pid), None)

    # ── Proyectos ────────────────────────────────────────────────────────
    def nuevo_proyecto(self, nombre=None, color="#6366F1"):
        if nombre is None:
            nombre, ok = QInputDialog.getText(self, "Nuevo Proyecto", "Nombre del proyecto:")
            if not ok or not nombre.strip():
                return
        proyecto = {
            "id": str(uuid.uuid4()),
            "nombre": nombre.strip(),
            "color": color,
            "archivado": False,
            "creado": datetime.now().isoformat(),
            "tareas": [],
            "sprints": [],
            "carpeta_codigo": ""
        }
        self.proyectos.append(proyecto)
        self.guardar_datos()
        self.gui.refrescar_proyectos()
        self.seleccionar_proyecto(proyecto["id"])

    def seleccionar_proyecto(self, pid):
        self.proyecto_activo = pid
        p = self._proyecto_por_id(pid)
        if self.gui:
            self.gui.mostrar_tablero(pid)
        if self.tab_scrum:
            self.tab_scrum.configurar_proyecto(pid)
        if self.tab_code:
            self.tab_code.configurar_proyecto(p)
        self.guardar_config_vista()

    def eliminar_proyecto(self, pid):
        p = self._proyecto_por_id(pid)
        if not p:
            return
        resp = QMessageBox.question(
            self, "Eliminar Proyecto",
            f"¿Eliminar el proyecto '{p['nombre']}' y todas sus tareas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.proyectos = [x for x in self.proyectos if x["id"] != pid]
            if self.proyecto_activo == pid:
                self.proyecto_activo = self.proyectos[0]["id"] if self.proyectos else None
                if self.proyecto_activo:
                    self.seleccionar_proyecto(self.proyecto_activo)
                else:
                    self.gui.limpiar_tablero()
                    if self.tab_scrum: self.tab_scrum.configurar_proyecto(None)
                    if self.tab_code: self.tab_code.configurar_proyecto(None)
            self.guardar_datos()
            self.gui.refrescar_proyectos()

    def renombrar_proyecto(self, pid):
        p = self._proyecto_por_id(pid)
        if not p:
            return
        nombre, ok = QInputDialog.getText(self, "Renombrar", "Nuevo nombre:", text=p["nombre"])
        if ok and nombre.strip():
            p["nombre"] = nombre.strip()
            self.guardar_datos()
            self.gui.refrescar_proyectos()
            if self.proyecto_activo == pid:
                self.seleccionar_proyecto(pid)

    def archivar_proyecto(self, pid):
        p = self._proyecto_por_id(pid)
        if p:
            p["archivado"] = not p.get("archivado", False)
            self.guardar_datos()
            self.gui.refrescar_proyectos()
            if self.tab_archivados:
                self.tab_archivados.refrescar_archivados()

    def importar_proyecto(self, proyecto_dict):
        proyecto_dict["id"] = str(uuid.uuid4())
        proyecto_dict["archivado"] = False
        self.proyectos.append(proyecto_dict)
        self.guardar_datos()
        self.gui.refrescar_proyectos()
        self.seleccionar_proyecto(proyecto_dict["id"])

    # ── Tareas ────────────────────────────────────────────────────────────
    def get_tareas(self, pid):
        p = self._proyecto_por_id(pid)
        return p["tareas"] if p else []

    def nueva_tarea(self, pid, titulo, descripcion="", prioridad="media", fecha_limite="", estado="todo",
                    etiqueta="", story_points=3, subtareas=None):
        p = self._proyecto_por_id(pid)
        if not p:
            return
        tarea = {
            "id": str(uuid.uuid4()),
            "titulo": titulo,
            "descripcion": descripcion,
            "prioridad": prioridad,          # "alta" | "media" | "baja"
            "fecha_limite": fecha_limite,    # ISO date string o ""
            "estado": estado,                # "todo" | "doing" | "done"
            "etiqueta": etiqueta,
            "story_points": story_points,
            "subtareas": subtareas or [],
            "creado": datetime.now().isoformat()
        }
        p["tareas"].append(tarea)
        self.guardar_datos()
        if self.gui:
            self.gui.mostrar_tablero(pid)
        if self.tab_scrum:
            self.tab_scrum.refrescar_scrum()

    def duplicar_tarea(self, pid, tid):
        p = self._proyecto_por_id(pid)
        if not p:
            return
        tarea = next((t for t in p["tareas"] if t["id"] == tid), None)
        if not tarea:
            return
        nueva = dict(tarea)
        nueva["id"] = str(uuid.uuid4())
        nueva["titulo"] = f"{tarea.get('titulo', 'Tarea')} (Copia)"
        nueva["creado"] = datetime.now().isoformat()
        p["tareas"].append(nueva)
        self.guardar_datos()
        if self.gui:
            self.gui.mostrar_tablero(pid)
        if self.tab_scrum:
            self.tab_scrum.refrescar_scrum()

    def mover_tarea(self, pid, tid, nuevo_estado):
        p = self._proyecto_por_id(pid)
        if not p:
            return
        for t in p["tareas"]:
            if t["id"] == tid:
                t["estado"] = nuevo_estado
                break
        self.guardar_datos()
        if self.gui:
            self.gui.mostrar_tablero(pid)
        if self.tab_scrum:
            self.tab_scrum.refrescar_scrum()

    def editar_tarea(self, pid, tid, datos):
        p = self._proyecto_por_id(pid)
        if not p:
            return
        for t in p["tareas"]:
            if t["id"] == tid:
                t.update(datos)
                break
        self.guardar_datos()
        if self.gui:
            self.gui.mostrar_tablero(pid)
        if self.tab_scrum:
            self.tab_scrum.refrescar_scrum()

    def eliminar_tarea(self, pid, tid):
        p = self._proyecto_por_id(pid)
        if not p:
            return
        p["tareas"] = [t for t in p["tareas"] if t["id"] != tid]
        self.guardar_datos()
        if self.gui:
            self.gui.mostrar_tablero(pid)
        if self.tab_scrum:
            self.tab_scrum.refrescar_scrum()

    def actualizar_tema(self, colores):
        self.colores = colores
        self._aplicar_estilos_tabs()
        for submod in [self.gui, self.tab_scrum, self.tab_code, self.tab_stats, self.tab_archivados]:
            if submod and hasattr(submod, "actualizar_tema"):
                try:
                    submod.actualizar_tema(colores)
                except Exception:
                    pass

    def cleanup(self):
        if self.tab_code and hasattr(self.tab_code, "cleanup"):
            self.tab_code.cleanup()
