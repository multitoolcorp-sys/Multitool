import os
import platform
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QMessageBox, QFileDialog, QInputDialog, QProgressDialog
from PyQt6.QtCore import Qt, QFileSystemWatcher, QTimer
from .submodulos.gui_archivos import ArchivosGUI
from .submodulos.commander import TabCommander
from .submodulos.diff_viewer import TabDiffViewer
from .submodulos.zip_manager import TabZipManager
from .utils.file_manager import FileManager
from .utils.office_previewer import OfficePreviewer
from .utils.operation_worker import FileOperationWorker
from .utils.shell_utils import mostrar_propiedades_windows, abrir_dispositivo_adb

class TabArchivos(QWidget):
    """Suite Principal del Módulo de Archivos (Explorador, Commander, Diff Viewer, Zip)"""
    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent)
        self.context = context
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", ".")) if context else Path(".")
        if colores:
            self.colores = colores
        elif context and hasattr(context, "app") and hasattr(context.app, "COLORES"):
            self.colores = context.app.COLORES
        else:
            self.colores = {
                "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
                "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
                "acento_hover": "#818CF8", "error": "#F87171", "exito": "#34D399", "advertencia": "#FBBF24"
            }
        
        # Estado interno
        self.carpetas_original = []
        self.archivos_original = []
        self.orden_actual = ("nombre", False)
        self.archivo_editando = None 
        
        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Tab Widget Principal
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ 
                border: 0; 
                background: {self.colores['bg_principal']};
                margin-top: -1px;
            }}
            QTabBar::tab {{ 
                background: transparent; 
                color: {self.colores['fg_secundario']};
                padding: 8px 18px;
                font-family: 'Segoe UI', 'Inter';
                font-weight: 600;
                font-size: 11px;
                border-bottom: 2px solid transparent;
                margin-right: 6px;
            }}
            QTabBar::tab:hover {{ 
                color: {self.colores['fg_principal']};
                background: {self.colores['bg_secundario']};
                border-top-left-radius: 8px; border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{ 
                background: rgba(99, 102, 241, 0.05);
                color: {self.colores['acento']}; 
                border-bottom: 2px solid {self.colores['acento']};
            }}
        """)
        self.main_layout.addWidget(self.tabs)

        # Monitor de archivos para auto-actualización con debounce
        self._watcher_timer = QTimer(self)
        self._watcher_timer.setSingleShot(True)
        self._watcher_timer.setInterval(1200) # 1.2 segundos para amortiguar ráfagas de escritura (ej. descargas activas)
        self._watcher_timer.timeout.connect(self._on_watcher_timeout)
        self._watcher_pending = False

        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self._on_directory_changed)        
        
        # Callbacks para la GUI del explorador
        callbacks = {
            "subir_nivel": self.subir_nivel,
            "ir_inicio": self.ir_inicio,
            "refrescar": self.refrescar,
            "ir_a_ruta_manual": self.ir_a_ruta_manual,
            "seleccionar_directorio": self.seleccionar_directorio,
            "nuevo_archivo": self.nuevo_archivo,
            "nueva_carpeta": self.nueva_carpeta,
            "operacion_archivo": self.operacion_archivo,
            "pegar": self.pegar,
            "eliminar": self.eliminar,
            "restaurar_elemento": self.restaurar_elemento,
            "eliminar_definitivo": self.eliminar_definitivo,
            "vaciar_papelera": self.vaciar_papelera,
            "abrir_seleccionado": self.abrir_seleccionado,
            "al_seleccionar_item": self.al_seleccionar_item,
            "guardar_archivo": self.guardar_archivo,
            "filtrar": self.filtrar,
            "ordenar": self.ordenar,
            "ejecutar_comando_ruta": self.ejecutar_comando_ruta,
            "mostrar_arbol_carpetas": self.mostrar_arbol_carpetas,
            "abrir_con_seleccionado": self.abrir_con_seleccionado,
            "mover_archivo": self.mover_archivo,
            "busqueda_global": self.busqueda_global,
            "mostrar_papelera": self.mostrar_papelera,
            "renombrar_item": self.renombrar_item,
            "mostrar_en_explorador": self.mostrar_en_explorador,
            "mostrar_propiedades": self.mostrar_propiedades,
            "copiar_ruta_acceso": self.copiar_ruta_acceso,
            "limpiar_vista_previa": lambda: self.gui.limpiar_vista_previa() if hasattr(self, 'gui') else None,
            "toggle_ocultos": self.toggle_ocultos,
            "toggle_extensiones": self.toggle_extensiones,
            "toggle_casillas": self.toggle_casillas,
            "agrupar_por": self.agrupar_por,
            "ajustar_columnas": self.ajustar_columnas,
            "toggle_columna": self.toggle_columna,
            "elegir_columnas_dialog": self.elegir_columnas_dialog,
            "cambiar_modo_vista": self.cambiar_modo_vista,
            "is_inside_archive": lambda: self.manager.is_inside_archive
        }
        
        # Iniciar Worker de búsqueda
        self.search_worker = None
        
        # Instanciar submódulos
        self.gui = ArchivosGUI(self, self.colores, callbacks)
        self.sub_commander = TabCommander(self, self.colores, callbacks)
        self.sub_diff = TabDiffViewer(self, self.colores, callbacks)
        self.sub_zip = TabZipManager(self, self.colores, callbacks)

        # Registrar pestañas
        self.tabs.addTab(self.gui, "📁 EXPLORADOR")
        self.tabs.addTab(self.sub_commander, "⚔️ COMMANDER")
        self.tabs.addTab(self.sub_diff, "🔍 COMPARADOR DIFF")
        self.tabs.addTab(self.sub_zip, "📦 COMPRESOR ZIP")

        if parent and hasattr(parent, 'layout') and parent.layout():
            parent.layout().addWidget(self)
        
        # Cargar layout del splitter persistente
        self.cargar_layout()
        
        # Registrar cierre seguro
        from PyQt6.QtCore import QCoreApplication
        app_inst = QCoreApplication.instance()
        if app_inst:
            app_inst.aboutToQuit.connect(self.cleanup)
        
        # Inicializar Manager
        self.manager = FileManager(self.ruta_usuario)
        
        # Carga inicial
        self.refrescar()

    def _on_directory_changed(self, path=None):
        """Maneja los cambios en la carpeta con debounce para evitar congelamiento durante descargas intensivas."""
        if not self._watcher_timer.isActive():
            self._watcher_timer.start()
        else:
            self._watcher_pending = True

    def _on_watcher_timeout(self):
        # Refrescar sin manipular el watcher durante el refresco
        self.refrescar(update_watcher=False)
        if self._watcher_pending:
            self._watcher_pending = False
            self._watcher_timer.start()

    def refrescar(self, update_watcher=True):
        self.archivo_editando = None
        self.en_papelera = False
        self.carpetas_original, self.archivos_original = self.manager.obtener_elementos()
        self.filtrar()
        self.gui.limpiar_vista_previa()
        
        # Registrar carpeta en la lista de recientes (últimas 4)
        if hasattr(self, 'gui') and hasattr(self.gui, 'sidebar') and hasattr(self.gui.sidebar, 'registrar_carpeta_reciente'):
            self.gui.sidebar.registrar_carpeta_reciente(self.manager.ruta_actual)
        
        # Actualizar el monitor en la ruta actual solo si es necesario
        if update_watcher:
            self._actualizar_watcher_path()

    def _actualizar_watcher_path(self):
        try:
            target_path = str(self.manager.archive_path.parent) if self.manager.is_inside_archive else str(self.manager.ruta_actual)
            current_dirs = self.watcher.directories()
            if current_dirs != [target_path]:
                if current_dirs:
                    self.watcher.removePaths(current_dirs)
                if target_path and Path(target_path).exists():
                    self.watcher.addPath(target_path)
        except Exception as e:
            print(f"[Archivos] Error actualizando watcher: {e}")

    def mostrar_papelera(self):
        """Muestra los elementos eliminados en la vista actual"""
        self.en_papelera = True
        items = self.manager.trash_manager.list_trash()
        archivos = []
        for it in items:
            archivos.append({
                "name": it["trash_id"], # Usamos el ID interno para poder restaurar
                "original_name": it["name"],
                "path": it["original_path"],
                "date": it["deleted_at"],
                "type": "Eliminado",
                "size": "--", "size_raw": 0
            })
        self.gui.actualizar_lista([], archivos, "PAPELERA_RECICLAJE")
        self.gui.barra_estado.showMessage("Viendo archivos eliminados (Papelera)", 3000)

    def busqueda_global(self, query):
        """Inicia una búsqueda recursiva en segundo plano"""
        if not query:
            self.refrescar()
            return
            
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.stop()
            
        from .utils.search_engine import GlobalSearchWorker
        ruta_busqueda = self.manager.archive_path.parent if self.manager.is_inside_archive else self.manager.ruta_actual
        self.search_worker = GlobalSearchWorker(ruta_busqueda, query)
        self.search_worker.match_found.connect(self._on_search_match)
        self.search_worker.finished.connect(lambda count: self.gui.barra_estado.showMessage(f"Búsqueda finalizada: {count} coincidencias", 5000))
        
        self.gui.actualizar_lista([], [], f"Buscando '{query}'...")
        self.search_worker.start()

    def _on_search_match(self, data):
        """Insertar resultados uno a uno en la lista sin limpiar la vista"""
        self.gui.explorer.agregar_resultado_busqueda(data)
        self.archivo_editando = None

    def filtrar(self):
        busq = self.gui.busqueda_var.lower()
        carpetas = [c for c in self.carpetas_original if busq in c["name"].lower()]
        archivos = [a for a in self.archivos_original if busq in a["name"].lower()]
        if self.manager.is_inside_archive:
            virtual_path = str(self.manager.archive_path) + os.sep + self.manager.archive_internal_dir.replace('/', os.sep)
            self.gui.actualizar_lista(carpetas, archivos, virtual_path)
        else:
            self.gui.actualizar_lista(carpetas, archivos, self.manager.ruta_actual)

    def toggle_ocultos(self, state):
        self.gui.explorer.mostrar_ocultos = state
        self.filtrar()
        self.guardar_layout()

    def toggle_extensiones(self, state):
        self.gui.explorer.mostrar_extensiones = state
        self.filtrar()
        self.guardar_layout()

    def toggle_casillas(self, state):
        self.gui.explorer.mostrar_casillas = state
        self.filtrar()
        self.guardar_layout()

    def agrupar_por(self, grp):
        self.gui.explorer.grupo_actual = grp
        self.filtrar()
        self.guardar_layout()

    def cambiar_modo_vista(self, modo):
        self.gui.explorer.cambiar_modo_vista(modo)
        self.filtrar()
        self.guardar_layout()

    def ajustar_columnas(self):
        self.gui.explorer.ajustar_columnas()

    def toggle_columna(self, col_idx):
        tree = self.gui.explorer.tree
        hidden = tree.isColumnHidden(col_idx)
        tree.setColumnHidden(col_idx, not hidden)
        self.guardar_layout()

    def elegir_columnas_dialog(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QPushButton, QLabel
        dlg = QDialog(self)
        dlg.setWindowTitle("Elegir columnas")
        dlg.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white;")
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("Selecciona las columnas visibles en la tabla:"))
        tree = self.gui.explorer.tree
        col_names = ["Nombre", "Fecha de modificación", "Tipo", "Tamaño"]
        cbs = []
        for i, name in enumerate(col_names):
            cb = QCheckBox(name)
            cb.setChecked(not tree.isColumnHidden(i))
            cbs.append((i, cb))
            lay.addWidget(cb)
        btn_ok = QPushButton("Aceptar")
        btn_ok.clicked.connect(dlg.accept)
        lay.addWidget(btn_ok)
        if dlg.exec():
            for idx, cb in cbs:
                tree.setColumnHidden(idx, not cb.isChecked())
            self.guardar_layout()

    def ordenar(self, columna):
        rev = self.orden_actual[1] if self.orden_actual[0] == columna else False
        self.orden_actual = (columna, not rev)
        key_map = {
            "nombre": lambda x: x["name"].lower(),
            "fecha": lambda x: x["date"],
            "tipo": lambda x: x["type"],
            "tamaño": lambda x: x["size_raw"]
        }
        self.carpetas_original.sort(key=key_map[columna], reverse=self.orden_actual[1])
        self.archivos_original.sort(key=key_map[columna], reverse=self.orden_actual[1])
        self.filtrar()

    def subir_nivel(self):
        if self.manager.subir_nivel(): self.refrescar()

    def ir_inicio(self):
        self.manager.ir_inicio()
        self.refrescar()

    def ir_a_ruta_manual(self, ruta_texto):
        if not ruta_texto: return
        
        # 🔥 SOPORTE PARA DISPOSITIVOS ADB (Móviles Android)
        if str(ruta_texto).startswith("adb://"):
            dev_id = str(ruta_texto).replace("adb://", "").strip()
            abrir_dispositivo_adb(dev_id, self.gui)
            return

        # 🔥 SOPORTE PARA DISPOSITIVOS MTP / RUTAS SHELL (::{20D04FE0...}, shell:...)
        if str(ruta_texto).startswith("::") or str(ruta_texto).lower().startswith("shell:"):
            self._abrir_ruta_sistema(ruta_texto)
            return

        # 🔥 SOPORTE PARA %APPDATA%, %TEMP%, etc.
        ruta_texto = os.path.expandvars(ruta_texto)
        
        # Soporte para "ejecución" similar a Windows (cmd, notepad, etc)
        if self.manager.ir_a_ruta(ruta_texto):
            self.refrescar()
        else:
            # Si no es una ruta, intentar ejecutar como comando o abrir como archivo
            try:
                # Si es una ruta de archivo existente, abrirla
                potencial_archivo = Path(ruta_texto) if os.path.isabs(ruta_texto) else self.manager.ruta_actual / ruta_texto
                if potencial_archivo.exists() and potencial_archivo.is_file():
                    self._abrir_ruta_sistema(potencial_archivo)
                    return

                # Si es un comando (ej: cmd), ejecutar en la ruta actual
                self.ejecutar_comando_ruta(ruta_texto)
            except:
                self.gui.barra_estado.showMessage(f"No se pudo resolver: {ruta_texto}", 3000)

    def _abrir_ruta_sistema(self, ruta):
        system = platform.system()
        ruta_str = str(ruta)
        if system == "Windows":
            if ruta_str.startswith("::") or ruta_str.lower().startswith("shell:"):
                subprocess.Popen(["explorer.exe", ruta_str])
            else:
                try:
                    os.startfile(ruta_str)
                except Exception:
                    subprocess.Popen(["explorer.exe", ruta_str])
        elif system == "Darwin": subprocess.Popen(["open", ruta_str])
        else: subprocess.Popen(["xdg-open", ruta_str])

    def seleccionar_directorio(self):
        ruta = QFileDialog.getExistingDirectory(self.gui, "Seleccionar Directorio", str(self.manager.ruta_actual))
        if ruta:
            self.ir_a_ruta_manual(ruta)

    def al_seleccionar_item(self):
        """Maneja la vista previa o edición al seleccionar un item"""
        nombre = self.gui.get_selected_name()
        if not nombre:
            self.gui.limpiar_vista_previa()
            self.archivo_editando = None
            return
            
        if self.manager.is_inside_archive:
            if self.manager.es_directorio_interno(nombre):
                self.archivo_editando = None
                self.gui.mostrar_info_general(nombre, "Carpeta de archivos comprimidos")
                return
            else:
                ruta_temp = self.manager.extraer_archivo_temporal(nombre)
                if not ruta_temp:
                    self.archivo_editando = None
                    self.gui.mostrar_info_general(nombre, "Error al extraer archivo para vista previa")
                    return
                ruta = ruta_temp
        else:
            ruta = self.manager.ruta_actual / nombre
        
        if ruta.is_file():
            ext = ruta.suffix.lower()
            
            # Imágenes
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.webp']:
                self.archivo_editando = None
                self.gui.mostrar_vista_imagen(str(ruta))
            # Texto (Editable)
            elif ext in ['.txt', '.py', '.js', '.html', '.css', '.json', '.md', '.log', '.ini', '.cfg', '.yaml', '.sh', '.bat']:
                try:
                    size = ruta.stat().st_size
                    if size < 2 * 1024 * 1024: # Límite 2MB para edición
                        with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        if self.manager.is_inside_archive:
                            self.archivo_editando = None # Solo lectura
                            self.gui.mostrar_vista_texto(content, nombre, editable=False)
                        else:
                            self.archivo_editando = ruta
                            self.gui.mostrar_vista_texto(content, nombre, editable=True)
                    else:
                        with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                            snippet = f.read(5000)
                        self.archivo_editando = None
                        self.gui.mostrar_vista_texto(snippet + "\n\n[Archivo demasiado grande para edición]", nombre, editable=False)
                except Exception as e:
                    self.gui.mostrar_info_general(nombre, f"Error al leer archivo: {str(e)}")
            # Office
            elif ext in ['.docx', '.xlsx', '.pptx']:
                try:
                    content = ""
                    if ext == '.docx': content = OfficePreviewer.extract_text_from_docx(str(ruta))
                    elif ext == '.xlsx': content = OfficePreviewer.extract_text_from_xlsx(str(ruta))
                    elif ext == '.pptx': content = OfficePreviewer.extract_text_from_pptx(str(ruta))
                    
                    self.archivo_editando = None
                    self.gui.mostrar_vista_texto(content, nombre, editable=False)
                except:
                    self.gui.mostrar_info_general(nombre, "Error al extraer vista previa de Office")
            else:
                self.archivo_editando = None
                self.gui.mostrar_info_general(nombre, f"Archivo {ext.upper()} • Sin vista previa disponible")
        else:
            self.archivo_editando = None
            self.gui.mostrar_info_general(nombre, "Carpeta de archivos")

    def guardar_archivo(self):
        """Guarda el contenido del editor de texto al disco"""
        if not self.archivo_editando: return
        
        try:
            nuevo_contenido = self.gui.preview.text_edit.toPlainText()
            with open(self.archivo_editando, 'w', encoding='utf-8') as f:
                f.write(nuevo_contenido)
            
            self.gui.barra_estado.showMessage(f"¡'{self.archivo_editando.name}' guardado correctamente!", 3000)
            self.carpetas_original, self.archivos_original = self.manager.obtener_elementos()
        except Exception as e:
            QMessageBox.critical(self.gui, "Error al Guardar", f"No se pudo guardar el archivo:\n{e}")

    def renombrar_item(self):
        if self.manager.is_inside_archive:
            QMessageBox.warning(self.gui, "Acción no permitida", "No se pueden renombrar elementos dentro de un archivo comprimido.")
            return
        nombre_actual = self.gui.get_selected_name()
        if not nombre_actual: return
        
        nuevo_nombre, ok = QInputDialog.getText(self.gui, "Renombrar", "Nuevo nombre:", text=nombre_actual)
        if ok and nuevo_nombre and nuevo_nombre != nombre_actual:
            exito, msg = self.manager.renombrar(nombre_actual, nuevo_nombre)
            if exito:
                self.refrescar()
            else:
                QMessageBox.critical(self.gui, "Error", f"No se pudo renombrar:\n{msg}")

    def abrir_seleccionado(self):
        """Abre un archivo con la aplicación predeterminada del sistema"""
        nombre = self.gui.get_selected_name()
        
        # Lógica especial si estamos dentro de un archivo comprimido
        if self.manager.is_inside_archive and nombre:
            if self.manager.es_directorio_interno(nombre):
                self.manager.entrar_a_directorio_interno(nombre)
                self.refrescar()
            else:
                # Extraer archivo y abrir con la app por defecto del sistema
                ruta_temp = self.manager.extraer_archivo_temporal(nombre)
                if ruta_temp:
                    self._abrir_ruta_sistema(ruta_temp)
            return

        # Intentar obtener ruta completa acumulada (ej: en búsqueda global)
        ruta_str = self.gui.explorer.get_selected_full_path()
        
        if not ruta_str and nombre:
            ruta = self.manager.ruta_actual / nombre
        elif ruta_str:
            ruta = Path(ruta_str)
        else: return # Nada seleccionado
 
        # Lógica especial para Papelera
        if getattr(self, "en_papelera", False):
            res = QMessageBox.question(self.gui, "Restaurar", f"¿Desea restaurar '{nombre}' a su ubicación original?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if res == QMessageBox.StandardButton.Yes:
                if self.manager.trash_manager.restore_item(nombre):
                    self.mostrar_papelera()
            return
 
        # Abrir archivo comprimido o directorio normal
        if not self.manager.is_inside_archive and self.manager.es_archivo_comprimido(ruta):
            try:
                if self.manager.entrar_a_archivo(ruta):
                    self.refrescar()
                    return
            except ImportError:
                QMessageBox.warning(self.gui, "Lector de RAR", 
                                    "Para leer archivos RAR se requiere el módulo 'rarfile'.\n"
                                    "Puedes instalarlo ejecutando:\npip install rarfile")
                return
            except Exception as e:
                QMessageBox.warning(self.gui, "Lector de Archivos", 
                                    f"No se pudo leer el archivo comprimido:\n{str(e)}\n\n"
                                    "Nota: Los archivos RAR pueden requerir la herramienta 'unrar' instalada.")
                return

        if ruta.is_dir():
            if self.manager.ir_a_ruta(ruta): self.refrescar()
        else:
            try:
                self._abrir_ruta_sistema(ruta)
            except Exception as e:
                QMessageBox.critical(self.gui, "Error", f"No se pudo abrir:\n{e}")

    def abrir_con_seleccionado(self):
        """Abre el diálogo 'Abrir con...' del sistema operativo"""
        nombre = self.gui.get_selected_name()
        if not nombre: return
        ruta = self.manager.ruta_actual / nombre
        if not ruta.is_file(): return
        
        try:
            system = platform.system()
            if system == "Windows":
                subprocess.Popen(["Rundll32.exe", "shell32.dll,OpenAs_RunDLL", str(ruta.resolve())])
            elif system == "Darwin":
                # En Mac, 'open -R' revela en Finder, 'open' abre con default. 'open -a' requiere el nombre de la app.
                # No hay un diálogo directo 'Open With' programático fácil sin AppleScript.
                subprocess.Popen(["open", str(ruta)]) 
            else:
                # En Linux, muchos entornos tienen 'mimeopen'
                subprocess.Popen(["mimeopen", "-n", str(ruta)])
        except Exception as e:
            QMessageBox.warning(self.gui, "Error", f"No se pudo abrir el menú 'Abrir con...': {e}")

    def nuevo_archivo(self):
        if self.manager.is_inside_archive:
            QMessageBox.warning(self.gui, "Acción no permitida", "No se pueden crear archivos dentro de un archivo comprimido.")
            return
        nombre, ok = QInputDialog.getText(self.gui, "Nuevo Archivo", "Escriba el nombre del archivo:")
        if ok and nombre:
            if self.manager.crear_archivo(nombre): self.refrescar()

    def nueva_carpeta(self):
        if self.manager.is_inside_archive:
            QMessageBox.warning(self.gui, "Acción no permitida", "No se pueden crear carpetas dentro de un archivo comprimido.")
            return
        nombre, ok = QInputDialog.getText(self.gui, "Nueva Carpeta", "Escriba el nombre de la carpeta:")
        if ok and nombre:
            if self.manager.crear_carpeta(nombre): self.refrescar()

    def operacion_archivo(self, accion):
        if self.manager.is_inside_archive:
            QMessageBox.warning(self.gui, "Acción no permitida", "No se permite cortar ni copiar elementos desde dentro de un archivo comprimido.")
            return
        nombres = self.gui.get_selected_names()
        if not nombres: return
        self.manager.preparar_operacion(nombres, accion)
        cant = len(nombres)
        txt = f"'{nombres[0]}'" if cant == 1 else f"{cant} elementos"
        self.gui.barra_estado.showMessage(f"{txt} listo(s) para {accion}", 3000)

    def pegar(self):
        if self.manager.is_inside_archive:
            QMessageBox.warning(self.gui, "Acción no permitida", "No se pueden pegar archivos dentro de un archivo comprimido.")
            return
        if not self.manager.portapapeles:
            QMessageBox.warning(self.gui, "Portapapeles", "No hay elementos para pegar.")
            return
            
        items = [p for p in self.manager.portapapeles if p.exists()]
        if not items:
            QMessageBox.warning(self.gui, "Portapapeles", "Los elementos en el portapapeles ya no existen.")
            return

        # Comprobar conflictos de nombres en destino
        conflictos = [p for p in items if (self.manager.ruta_actual / p.name).exists()]
        if conflictos:
            conf_str = f"'{conflictos[0].name}'" if len(conflictos) == 1 else f"{len(conflictos)} elementos"
            res = QMessageBox.question(
                self.gui, "Conflicto de archivos",
                f"El destino ya contiene {conf_str}. ¿Desea reemplazar los elementos existentes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res != QMessageBox.StandardButton.Yes:
                return

        exito, msg = self.manager.pegar()
        self.refrescar()
        if exito:
            self.gui.barra_estado.showMessage(msg, 3000)
        else:
            QMessageBox.critical(self.gui, "Error al pegar", f"No se pudo completar la operación:\n{msg}")

    def eliminar(self):
        if self.manager.is_inside_archive:
            QMessageBox.warning(self.gui, "Acción no permitida", "No se pueden eliminar elementos dentro de un archivo comprimido.")
            return
            
        nombres = self.gui.get_selected_names()
        if not nombres: return

        if getattr(self, "en_papelera", False):
            self.eliminar_definitivo()
            return

        cant = len(nombres)
        txt = f"'{nombres[0]}'" if cant == 1 else f"{cant} elementos seleccionados"
        res = QMessageBox.question(
            self.gui, "Mover a la Papelera",
            f"¿Está seguro de que desea mover {txt} a la papelera?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            eliminados = 0
            for n in nombres:
                if self.manager.eliminar(n):
                    eliminados += 1
            self.refrescar()
            self.gui.barra_estado.showMessage(f"{eliminados} elemento(s) movido(s) a la papelera", 3000)

    def restaurar_elemento(self):
        """Restaura los elementos seleccionados de la papelera a su ubicación original"""
        nombres = self.gui.get_selected_names()
        if not nombres: return
        cant = len(nombres)
        txt = f"este elemento" if cant == 1 else f"{cant} elementos seleccionados"
        res = QMessageBox.question(
            self.gui, "Restaurar elementos",
            f"¿Desea restaurar {txt} a su ubicación original?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            restaurados = 0
            for n in nombres:
                if self.manager.trash_manager.restore_item(n):
                    restaurados += 1
            self.mostrar_papelera()
            self.gui.barra_estado.showMessage(f"{restaurados} elemento(s) restaurado(s) con éxito", 3000)

    def eliminar_definitivo(self):
        """Elimina permanentemente los elementos seleccionados de la papelera"""
        nombres = self.gui.get_selected_names()
        if not nombres: return
        cant = len(nombres)
        txt = f"este elemento" if cant == 1 else f"{cant} elementos seleccionados"
        res = QMessageBox.question(
            self.gui, "Eliminar permanentemente",
            f"¿Está seguro de que desea eliminar {txt} de forma permanente?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            borrados = 0
            for n in nombres:
                if self.manager.trash_manager.delete_forever(n):
                    borrados += 1
            self.mostrar_papelera()
            self.gui.barra_estado.showMessage(f"{borrados} elemento(s) eliminado(s) permanentemente", 3000)

    def vaciar_papelera(self):
        """Vacía todos los elementos de la papelera"""
        res = QMessageBox.question(
            self.gui, "Vaciar Papelera",
            "¿Está seguro de que desea vaciar toda la papelera?\nTodos los archivos eliminados se perderán permanentemente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            if self.manager.trash_manager.empty_trash():
                self.mostrar_papelera()
                self.gui.barra_estado.showMessage("Papelera vaciada correctamente", 3000)
            else:
                QMessageBox.warning(self.gui, "Error", "No se pudo vaciar la papelera.")

    def ejecutar_comando_ruta(self, cmd):
        """Ejecuta terminal nativa o comandos del sistema en la ruta actual"""
        ruta = str(self.manager.ruta_actual)
        system = platform.system()
        try:
            if cmd.lower() == "cmd":
                if system == "Windows":
                    # 🔥 FIX DEFINITIVO: Forzar CWD y usar /K para mantener abierta
                    subprocess.Popen(["cmd.exe", "/K"], cwd=ruta, creationflags=subprocess.CREATE_NEW_CONSOLE)
                else: self._ejecutar_app_sistema(cmd, ruta)
            else:
                # Ejecución genérica
                self._ejecutar_app_sistema(cmd, ruta)
        except Exception as e:
            self.gui.barra_estado.showMessage(f"Error al ejecutar: {e}", 3000)

    def _ejecutar_app_sistema(self, cmd, working_dir):
        system = platform.system()
        if system == "Windows":
            # Usar shell=True para comandos internos o alias
            subprocess.Popen(cmd, shell=True, cwd=working_dir)
        else:
            subprocess.Popen(cmd.split(), cwd=working_dir)

    def mostrar_arbol_carpetas(self):
        from .submodulos.tree_dialog import FolderTreeDialog
        dialog = FolderTreeDialog(self.gui, self.colores, self.manager.ruta_actual)
        if dialog.exec() == FolderTreeDialog.DialogCode.Accepted:
            if dialog.selected_path:
                self.ir_a_ruta_manual(dialog.selected_path)

    def mover_archivo(self, nombre_origen, nombre_carpeta_destino):
        origen = self.manager.ruta_actual / nombre_origen
        destino_dir = self.manager.ruta_actual / nombre_carpeta_destino
        destino_final = destino_dir / nombre_origen
        
        if not origen.exists() or not destino_dir.is_dir() or origen == destino_dir: return

        if platform.system() == "Windows":
            from .submodulos.file_op_dialog import ejecutar_operacion_nativa_windows
            hwnd = self.gui.winId() if hasattr(self.gui, "winId") else None
            success = ejecutar_operacion_nativa_windows("move", str(origen), str(destino_final), parent_hwnd=hwnd)
            if success:
                self.refrescar()
                return

        from .submodulos.file_op_dialog import WinStyleFileOpDialog
        dlg = WinStyleFileOpDialog(
            self.gui,
            titulo="Mover elemento",
            mensaje=f"¿Desea mover '{nombre_origen}' a '{nombre_carpeta_destino}'?",
            item_path=str(origen),
            es_permiso_admin=not os.access(destino_dir, os.W_OK),
            colores=self.colores
        )
        if dlg.exec() == WinStyleFileOpDialog.DialogCode.Accepted and dlg.respuesta == "continue":
            self.worker = FileOperationWorker(origen, destino_final, "cortar")
            self.worker.progress.connect(self._actualizar_progreso_pegado)
            self.worker.finished.connect(self._finalizar_pegado)
            self.worker.start()

    def cargar_layout(self):
        ruta = self.ruta_usuario / "config_archivos_layout.json"
        if ruta.exists():
            try:
                import json
                with open(ruta, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sizes = []
                    cfg = {}
                    if isinstance(data, list):
                        sizes = data
                    elif isinstance(data, dict):
                        sizes = data.get("sizes", [])
                        cfg = data

                    if isinstance(sizes, list) and len(sizes) == 3:
                        if sizes[0] < 150: sizes[0] = 200
                        if sizes[1] < 300: sizes[1] = 550
                        if sizes[2] < 200: sizes[2] = 300
                        self.gui.body_splitter.setSizes(sizes)

                    # Restaurar configuración de vista y casillas
                    if cfg and hasattr(self, "gui"):
                        # 1. Casillas de elemento
                        if "mostrar_casillas" in cfg:
                            val = bool(cfg["mostrar_casillas"])
                            self.gui.explorer.mostrar_casillas = val
                            if hasattr(self.gui, "header") and hasattr(self.gui.header, "act_boxes"):
                                self.gui.header.act_boxes.blockSignals(True)
                                self.gui.header.act_boxes.setChecked(val)
                                self.gui.header.act_boxes.blockSignals(False)

                        # 2. Extensiones de archivo
                        if "mostrar_extensiones" in cfg:
                            val = bool(cfg["mostrar_extensiones"])
                            self.gui.explorer.mostrar_extensiones = val
                            if hasattr(self.gui, "header") and hasattr(self.gui.header, "act_ext"):
                                self.gui.header.act_ext.blockSignals(True)
                                self.gui.header.act_ext.setChecked(val)
                                self.gui.header.act_ext.blockSignals(False)

                        # 3. Elementos ocultos
                        if "mostrar_ocultos" in cfg:
                            val = bool(cfg["mostrar_ocultos"])
                            self.gui.explorer.mostrar_ocultos = val
                            if hasattr(self.gui, "header") and hasattr(self.gui.header, "act_hid"):
                                self.gui.header.act_hid.blockSignals(True)
                                self.gui.header.act_hid.setChecked(val)
                                self.gui.header.act_hid.blockSignals(False)

                        # 4. Modo de vista
                        if "modo_vista" in cfg:
                            self.gui.explorer.cambiar_modo_vista(cfg["modo_vista"])

                        # 5. Agrupación
                        if "grupo_actual" in cfg:
                            self.gui.explorer.grupo_actual = cfg["grupo_actual"]

                        # 6. Columnas ocultas
                        if "columnas_ocultas" in cfg and isinstance(cfg["columnas_ocultas"], list):
                            for col_idx in range(self.gui.explorer.tree.columnCount()):
                                self.gui.explorer.tree.setColumnHidden(col_idx, col_idx in cfg["columnas_ocultas"])
            except Exception as e:
                print(f"Error al cargar layout de archivos: {e}")

    def guardar_layout(self):
        ruta = self.ruta_usuario / "config_archivos_layout.json"
        try:
            import json
            sizes = self.gui.body_splitter.sizes() if hasattr(self, "gui") and hasattr(self.gui, "body_splitter") else []
            cols_ocultas = []
            if hasattr(self, "gui") and hasattr(self.gui, "explorer") and hasattr(self.gui.explorer, "tree"):
                cols_ocultas = [i for i in range(self.gui.explorer.tree.columnCount()) if self.gui.explorer.tree.isColumnHidden(i)]

            data = {
                "sizes": sizes,
                "mostrar_casillas": getattr(self.gui.explorer, "mostrar_casillas", False) if hasattr(self, "gui") and hasattr(self.gui, "explorer") else False,
                "mostrar_extensiones": getattr(self.gui.explorer, "mostrar_extensiones", False) if hasattr(self, "gui") and hasattr(self.gui, "explorer") else False,
                "mostrar_ocultos": getattr(self.gui.explorer, "mostrar_ocultos", False) if hasattr(self, "gui") and hasattr(self.gui, "explorer") else False,
                "modo_vista": getattr(self.gui.explorer, "modo_vista", "detalles") if hasattr(self, "gui") and hasattr(self.gui, "explorer") else "detalles",
                "grupo_actual": getattr(self.gui.explorer, "grupo_actual", "none") if hasattr(self, "gui") and hasattr(self.gui, "explorer") else "none",
                "columnas_ocultas": cols_ocultas
            }
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error al guardar layout de archivos: {e}")

    def cleanup(self):
        if hasattr(self, '_watcher_timer') and self._watcher_timer.isActive():
            self._watcher_timer.stop()
        self.guardar_layout()
        if hasattr(self, 'manager'):
            self.manager.limpiar_temporales()

    def mostrar_en_explorador(self):
        nombre = self.gui.get_selected_name()
        destacar = False
        
        if self.manager.is_inside_archive:
            ruta = self.manager.archive_path
            destacar = True
        elif nombre:
            ruta = self.manager.ruta_actual / nombre
            destacar = True
        else:
            ruta = self.manager.ruta_actual
            
        system = platform.system()
        try:
            if system == "Windows":
                if destacar:
                    # Usamos cadena completa en Popen para evitar que python introduzca comillas escapadas incorrectas
                    subprocess.Popen(f'explorer.exe /select,"{ruta.resolve()}"')
                else:
                    os.startfile(ruta)
            elif system == "Darwin":
                if destacar:
                    subprocess.Popen(["open", "-R", str(ruta)])
                else:
                    subprocess.Popen(["open", str(ruta)])
            else:
                if destacar:
                    subprocess.Popen(["xdg-open", str(ruta.parent)])
                else:
                    subprocess.Popen(["xdg-open", str(ruta)])
        except Exception as e:
            self.gui.barra_estado.showMessage(f"Error al mostrar en explorador: {e}", 3000)

    def mostrar_propiedades(self):
        nombre = self.gui.get_selected_name()
        
        if self.manager.is_inside_archive:
            ruta = self.manager.archive_path
        elif nombre:
            ruta = self.manager.ruta_actual / nombre
        else:
            ruta = self.manager.ruta_actual
            
        if platform.system() == "Windows":
            success = mostrar_propiedades_windows(ruta)
            if not success:
                self.gui.barra_estado.showMessage("No se pudieron cargar las propiedades de Windows", 3000)
        else:
            self.gui.barra_estado.showMessage("Propiedades de Windows solo disponibles en Windows", 3000)

    def copiar_ruta_acceso(self):
        nombre = self.gui.get_selected_name()
        
        if self.manager.is_inside_archive:
            if nombre:
                path_str = str(self.manager.archive_path) + os.sep + (self.manager.archive_internal_dir + nombre).replace('/', os.sep)
            else:
                path_str = str(self.manager.archive_path) + os.sep + self.manager.archive_internal_dir.replace('/', os.sep)
        else:
            if nombre:
                path_str = str((self.manager.ruta_actual / nombre).resolve())
            else:
                path_str = str(self.manager.ruta_actual.resolve())
            
        from PyQt6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(path_str)
        self.gui.barra_estado.showMessage("Ruta copiada al portapapeles", 3000)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ 
                border: 0; 
                background: {self.colores['bg_principal']};
                margin-top: -1px;
            }}
            QTabBar::tab {{ 
                background: transparent; 
                color: {self.colores['fg_secundario']};
                padding: 8px 18px;
                font-family: 'Segoe UI', 'Inter';
                font-weight: 600;
                font-size: 11px;
                border-bottom: 2px solid transparent;
                margin-right: 6px;
            }}
            QTabBar::tab:hover {{ 
                color: {self.colores['fg_principal']};
                background: {self.colores['bg_secundario']};
                border-top-left-radius: 8px; border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{ 
                background: rgba(99, 102, 241, 0.05);
                color: {self.colores['acento']}; 
                border-bottom: 2px solid {self.colores['acento']};
            }}
        """)
        if hasattr(self.gui, 'actualizar_tema'):
            self.gui.actualizar_tema(colores)
        if hasattr(self.sub_commander, 'actualizar_tema'):
            self.sub_commander.actualizar_tema(colores)
        if hasattr(self.sub_diff, 'actualizar_tema'):
            self.sub_diff.actualizar_tema(colores)
        if hasattr(self.sub_zip, 'actualizar_tema'):
            self.sub_zip.actualizar_tema(colores)



