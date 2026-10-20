"""
notas.py - Orquestador principal del módulo de Notas
"""
import os
import shutil
import datetime
import json
import platform
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QInputDialog, QFileDialog, 
    QTabWidget, QListWidgetItem, QLabel, QListWidget, QDialog, QTextEdit, 
    QSplitter, QPushButton, QColorDialog
)
from PyQt6.QtCore import Qt, QTimer, QFileSystemWatcher, QCoreApplication
from PyQt6.QtGui import QTextCursor, QFont, QTextDocument
from PyQt6.sip import isdeleted

from .submodulos.gui_notas import NotasGUI
from .submodulos.papelera import TabPapelera
from .submodulos.plantillas_notas import TabPlantillasNotas

from .utils.format_manager import FormatManager
from .utils.image_manager import ImageManager
from .utils.table_manager import TableManager
from .utils.export_manager import ExportManager
from .utils.notes_storage_manager import NotesStorageManager
from .utils.import_manager import ImportManager
from .utils.snapshot_dialog import SnapshotViewerDialog


class TabNotas(QWidget):
    """Orquestador principal del módulo de Notas Pro"""
    _instancias_activas = []

    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.ruta_notas = self.ruta_usuario / "notas"
        self.ruta_notas.mkdir(parents=True, exist_ok=True)
        
        self.storage = NotesStorageManager(self.ruta_usuario)
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.nota_actual = None
        self.favoritas = self.storage.cargar_favoritas()
        self.fijadas = self.storage.cargar_fijadas()
        self.protegidas = self.storage.cargar_protegidas()
        self.imagenes = {}
        self.imagenes_nota = {}
        
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#1E1E1E", "bg_secundario": "#2D2D2D", "bg_terciario": "#3D3D3D",
            "fg_principal": "#E0E0E0", "fg_secundario": "#A0A0A0", "acento": "#4A86E8",
            "acento_hover": "#5A96F8", "exito": "#43A047", "error": "#E53935", "advertencia": "#FDD835"
        })
        
        self.temas_pastel = {
            "default": {"bg": self.colores['bg_principal'], "fg": self.colores['fg_principal']},
            "yellow": {"bg": "#FEF9C3", "fg": "#1E293B"},
            "blue": {"bg": "#DBEAFE", "fg": "#1E293B"},
            "green": {"bg": "#DCFCE7", "fg": "#1E293B"},
            "purple": {"bg": "#F3E8FF", "fg": "#1E293B"}
        }
        self.current_tema = "default"
        self._cargando_lista = False
        self._guardando_interno = False
        self.filtro_tag_actual = None

        # Callbacks para la GUI
        self.callbacks = {
            "filtrar_notas": self.filtrar_notas,
            "buscar_en_contenido": self.buscar_en_contenido,
            "nueva_nota": self.nueva_nota,
            "eliminar_nota": self.eliminar_nota,
            "seleccionar_nota": self.seleccionar_nota,
            "actualizar_titulo": self.actualizar_titulo,
            "toggle_favorito": self.toggle_favorito,
            "toggle_fijar": self.toggle_fijar,
            "proteger_nota": self.proteger_nota,
            "guardar_nota": self.guardar_nota,
            "aplicar_formato": self.aplicar_formato,
            "insertar_imagen": self.insertar_imagen,
            "insertar_vineta": self.insertar_vineta,
            "insertar_tabla": self.insertar_tabla,
            "actualizar_contenido": self.actualizar_contenido,
            "actualizar_estado_formato": self.actualizar_estado_formato,
            "mostrar_menu_contextual": self.mostrar_menu_contextual,
            "cambiar_tamano_fuente": self.cambiar_tamano_fuente,
            "cambiar_color_texto": self.cambiar_color_texto,
            "eliminar_nota_obj": self.eliminar_nota_obj,
            "cambiar_familia_fuente": self.cambiar_familia_fuente,
            "cambiar_color_fondo": self.cambiar_color_fondo,
            "toggle_buscar_reemplazar": self.toggle_buscar_reemplazar,
            "buscar_texto": self.buscar_texto,
            "reemplazar_texto": self.reemplazar_texto,
            "reemplazar_todo_texto": self.reemplazar_todo_texto,
            "cambiar_pastel_fondo": self.cambiar_pastel_fondo,
            "exportar_pdf": lambda: self.exporter.exportar_pdf(),
            "exportar_markdown": lambda: self.exporter.exportar_markdown(),
            "exportar_txt": lambda: self.exporter.exportar_txt(),
            "limpiar_formato": lambda: self.format_manager.limpiar_formato(),
            "aplicar_superindice": lambda: self.format_manager.aplicar_superindice(),
            "aplicar_subindice": lambda: self.format_manager.aplicar_subindice(),
            "insertar_bloque_codigo": lambda: self.format_manager.insertar_bloque_codigo(),
            "ajustar_imagen": lambda c, m: self.image_manager.cambiar_posicion_imagen(c, m),
            "redimensionar_imagen": lambda c: self.image_manager.cambiar_tamano_dialogo(c),
            "insertar_imagen_data": lambda img: self.image_manager.insertar_desde_qimage(img),
            "insertar_imagen_archivo": lambda p: self.image_manager.insertar_desde_archivo(p),
            "agregar_fila": lambda: self.table_manager.agregar_fila(),
            "agregar_columna": lambda: self.table_manager.agregar_columna(),
            "eliminar_fila": lambda: self.table_manager.eliminar_fila(),
            "eliminar_columna": lambda: self.table_manager.eliminar_columna(),
            # Nuevas acciones y mejoras
            "importar_notas": self.importar_notas,
            "mostrar_snapshots": self.mostrar_snapshots,
            "guardar_como_plantilla": self.guardar_como_plantilla,
            "asignar_tag": self.asignar_tag,
            "filtrar_por_tag": self.filtrar_por_tag,
            "insertar_checklist": lambda: self.format_manager.insertar_checklist(),
            "insertar_separador": lambda: self.format_manager.insertar_separador(),
            "insertar_enlace": self.insertar_enlace_dialogo,
            "aplicar_encabezado": lambda t: self.format_manager.aplicar_encabezado(t),
            "deshacer": lambda: self.format_manager.deshacer(),
            "rehacer": lambda: self.format_manager.rehacer(),
            "deseleccionar_nota": self.deseleccionar_nota,
            "ir_a_plantillas": lambda: self.tabs.setCurrentIndex(1)
        }

        if self not in TabNotas._instancias_activas:
            TabNotas._instancias_activas.append(self)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self._aplicar_estilo_tabs()

        # Submódulos dinámicos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        extra_kwargs = {
            "callbacks": self.callbacks,
            "callback_usar_plantilla": self.crear_nota_desde_plantilla,
            "callback_restaurar": self.cargar_lista_notas,
            "storage": self.storage
        }
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores, extra_kwargs)

        if self.tabs.count() == 0:
            self.gui = NotasGUI(self, self.colores, self.callbacks)
            self.tab_plantillas = TabPlantillasNotas(self, context=self.context, colores=self.colores, callback_usar_plantilla=self.crear_nota_desde_plantilla, storage=self.storage)
            self.tab_papelera = TabPapelera(self, context=self.context, colores=self.colores, callback_restaurar=self.cargar_lista_notas)

            self.tabs.addTab(self.gui, "📝 Mis Notas & Editor")
            self.tabs.addTab(self.tab_plantillas, "📋 Plantillas de Notas")
            self.tabs.addTab(self.tab_papelera, "🗑️ Papelera de Reciclaje")
        else:
            self.gui = self.submod_instances.get("NotasGUI") or self.submod_instances.get("notasgui")
            if not self.gui:
                self.gui = NotasGUI(self, self.colores, self.callbacks)
            self.tab_plantillas = self.submod_instances.get("TabPlantillasNotas")
            self.tab_papelera = self.submod_instances.get("TabPapelera")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.main_layout.addWidget(self.tabs)

        # Inicializar managers
        self.format_manager = FormatManager(
            self.gui.editor, self.colores, 
            status_callback=self.gui.lbl_status.setText,
            stats_callback=self.actualizar_estadisticas
        )
        self.image_manager = ImageManager(
            self.gui.editor, self.gui.lbl_status.setText, self.imagenes, self.imagenes_nota
        )
        self.table_manager = TableManager(self.gui.editor, self.colores)
        self.exporter = ExportManager(self, self.gui.editor)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.timeout.connect(self.guardar_nota_automatica)

        app_inst = QCoreApplication.instance()
        if app_inst:
            app_inst.aboutToQuit.connect(self.cleanup)

        self.cargar_lista_notas()
        self._toggle_editor(False)

        self.watcher = QFileSystemWatcher([str(self.ruta_notas)])
        self.watcher.directoryChanged.connect(self._on_directory_changed)
        self.watcher.fileChanged.connect(self._verificar_integridad_nota_actual)

    def _on_tab_changed(self, index):
        if self.nota_actual:
            self.guardar_nota()

    def _on_directory_changed(self):
        if not self._guardando_interno and not self._cargando_lista:
            self.cargar_lista_notas()

    def _verificar_integridad_nota_actual(self, path):
        if self._guardando_interno or self._cargando_lista:
            return
        if self.nota_actual and str(self.ruta_notas / f"{self.nota_actual}.txt") == path:
            if not Path(path).exists():
                self.nota_actual = None
                self.gui.editor.clear()
                self._toggle_editor(False)
            self.cargar_lista_notas()

    def cargar_lista_notas(self):
        try:
            if isdeleted(self) or not hasattr(self, "gui") or isdeleted(self.gui) or not hasattr(self.gui, "list_notas") or isdeleted(self.gui.list_notas):
                return
        except Exception:
            pass

        self._cargando_lista = True
        self.gui.list_notas.blockSignals(True)
        self.gui.list_notas.clear()
        try:
            archivos = list(self.ruta_notas.glob("*.txt"))
            archivos.sort(key=lambda x: (x.stem not in self.fijadas, x.stem not in self.favoritas, -os.path.getmtime(x)))

            # Filtro por etiqueta activa (si es 'Todas' o None se muestran todas las notas)
            filtro = getattr(self, "filtro_tag_actual", None)
            if filtro and str(filtro).strip() not in ("Todas", "🏷️ Todas", "todas", "None"):
                tags_map = self.storage.cargar_tags()
                tag_f = str(filtro).lstrip("#").strip().lower()
                archivos = [
                    a for a in archivos 
                    if any(t.lower() == tag_f for t in tags_map.get(a.stem, []))
                ]

            item_a_seleccionar = None
            for archivo in archivos:
                prefijo = ""
                if archivo.stem in self.fijadas: prefijo += "📌 "
                if archivo.stem in self.favoritas: prefijo += "★ "
                if archivo.stem in self.protegidas: prefijo += "🔒 "

                item = QListWidgetItem(f"{prefijo}{archivo.stem}")
                item.setFont(QFont(self.font_family, 10))
                self.gui.list_notas.addItem(item)
                if self.nota_actual and archivo.stem == self.nota_actual:
                    item_a_seleccionar = item
            
            if item_a_seleccionar:
                self.gui.list_notas.setCurrentItem(item_a_seleccionar)
                item_a_seleccionar.setSelected(True)
                self._toggle_editor(True)
            elif not self.nota_actual:
                self._toggle_editor(False)
                
            self.gui.lbl_status.setText(f"{len(archivos)} notas en biblioteca")

            # Actualizar barra de tags en la GUI
            if hasattr(self.gui, "_actualizar_tags_ui"):
                todos_tags = self.storage.obtener_todos_los_tags()
                self.gui._actualizar_tags_ui(todos_tags, getattr(self, "filtro_tag_actual", None))
        except Exception:
            pass
        finally:
            try:
                self.gui.list_notas.blockSignals(False)
            except Exception:
                pass
            self._cargando_lista = False

    def _desempaquetar_html_seguro(self, html_raw):
        content = html_raw
        max_loops = 5
        while max_loops > 0 and isinstance(content, str):
            content_strip = content.strip()
            if content_strip.startswith("{") or content_strip.startswith('{"html"'):
                try:
                    parsed = json.loads(content_strip)
                    if isinstance(parsed, dict) and "html" in parsed:
                        content = parsed["html"]
                    else: break
                except Exception: break
            else: break
            max_loops -= 1
        return content

    def crear_nota_desde_plantilla(self, titulo, html_content):
        if self.nota_actual:
            self.guardar_nota()

        fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_base = re.sub(r'[\\/*?:"<>|]', "", titulo.strip()).replace(" ", "_")
        nombre = f"{nombre_base}_{fecha}" if nombre_base else f"Nota_{fecha}"

        try:
            self._guardando_interno = True
            ruta_nota = self.ruta_notas / f"{nombre}.txt"
            datos_iniciales = {
                "html": html_content,
                "imagenes_metadata": {},
                "favorita": False,
                "background_color": "default"
            }
            with open(ruta_nota, "w", encoding="utf-8") as f:
                json.dump(datos_iniciales, f, indent=4)

            self.nota_actual = nombre
            self.gui.txt_titulo.setText(nombre)
            
            self.gui.editor.blockSignals(True)
            self.gui.editor.setHtml(html_content)
            self.gui.editor.blockSignals(False)

            self.imagenes_nota.clear()
            self.gui.btn_favorito.setChecked(False)
            self.aplicar_tema_color("default")
            self.actualizar_estadisticas()
            self._toggle_editor(True)

            self.cargar_lista_notas()
            self.seleccionar_nota_por_nombre(nombre)
            self.tabs.setCurrentIndex(0)
            self._guardando_interno = False
        except Exception as e:
            self._guardando_interno = False
            print(f"Error al crear nota desde plantilla: {e}")

    def seleccionar_nota_por_nombre(self, nombre):
        for i in range(self.gui.list_notas.count()):
            item = self.gui.list_notas.item(i)
            if item and nombre in item.text():
                self.gui.list_notas.setCurrentItem(item)
                break

    def nueva_nota(self):
        if self.nota_actual:
            self.guardar_nota()
             
        fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"Nota_{fecha}"
        try:
            ruta_nota = self.ruta_notas / f"{nombre}.txt"
            datos_iniciales = {
                "html": "<p></p>",
                "imagenes_metadata": {},
                "background_color": "default"
            }
            with open(ruta_nota, "w", encoding="utf-8") as f:
                json.dump(datos_iniciales, f, indent=4)
            
            self.nota_actual = nombre
            self.cargar_lista_notas()
            
            self.gui.editor.blockSignals(True)
            self.gui.txt_titulo.setText(nombre)
            self.gui.editor.clear()
            self.gui.editor.blockSignals(False)
            
            self.imagenes_nota.clear()
            self.gui.btn_favorito.setChecked(False)
            self.aplicar_tema_color("default")
            self.actualizar_estadisticas()
            self.gui.lbl_status.setText("Nueva nota lista")
            self._toggle_editor(True)
            self.gui.txt_titulo.setFocus()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear: {e}")

    def guardar_nota_automatica(self):
        if self.nota_actual and not self._guardando_interno:
            self.guardar_nota()

    def guardar_nota(self):
        if not self.nota_actual: return
        try:
            self._guardando_interno = True
            datos = {
                "html": self.gui.editor.toHtml(),
                "imagenes_metadata": self.imagenes_nota,
                "favorita": self.nota_actual in self.favoritas,
                "background_color": getattr(self, "current_tema", "default")
            }
            ruta_nota = self.ruta_notas / f"{self.nota_actual}.txt"
            with open(ruta_nota, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=4)
            self.gui.lbl_status.setText(f"Cambios guardados {datetime.datetime.now().strftime('%H:%M:%S')}")

            # Guardar snapshot para historial de versiones
            if datos["html"] and datos["html"].strip():
                self.storage.guardar_snapshot(self.nota_actual, datos["html"])

            # Sincronización en tiempo real hacia otras vistas activas (p. ej. Widget vs App principal)
            for inst in list(TabNotas._instancias_activas):
                if inst is not self:
                    try:
                        inst.sincronizar_desde_externo(self.nota_actual, datos)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error al guardar: {e}")
        finally:
            QTimer.singleShot(100, self._reset_guardando_interno)

    def sincronizar_desde_externo(self, nombre_nota, datos):
        """Sincroniza en tiempo real los cambios generados desde otra instancia de TabNotas (p. ej. Widget vs App)"""
        try:
            if isdeleted(self) or not hasattr(self, "gui") or isdeleted(self.gui) or not hasattr(self.gui, "list_notas") or isdeleted(self.gui.list_notas):
                if self in TabNotas._instancias_activas:
                    TabNotas._instancias_activas.remove(self)
                return
        except Exception:
            pass

        try:
            # Si tiene abierta la misma nota
            if self.nota_actual == nombre_nota and not self._guardando_interno:
                self._guardando_interno = True
                self.imagenes_nota.clear()
                if "imagenes_metadata" in datos:
                    self.imagenes_nota.update(datos["imagenes_metadata"])
                
                cursor_pos = self.gui.editor.textCursor().position()
                self.gui.editor.blockSignals(True)
                self.gui.editor.setHtml(datos.get("html", ""))
                self.image_manager.cargar_imagenes_desde_datos()
                c = self.gui.editor.textCursor()
                c.setPosition(min(cursor_pos, len(self.gui.editor.toPlainText())))
                self.gui.editor.setTextCursor(c)
                self.gui.editor.blockSignals(False)
                
                self.gui.lbl_status.setText("⚡ Sincronizado en tiempo real")
                QTimer.singleShot(150, self._reset_guardando_interno)
            
            # Refrescar lista de notas para reflejar cambios
            self.cargar_lista_notas()
        except Exception as e:
            pass

    def _reset_guardando_interno(self):
        self._guardando_interno = False

    def seleccionar_nota(self):
        if getattr(self, "_cargando_lista", False):
            return
        item = self.gui.list_notas.currentItem()
        if not item or not item.isSelected():
            self._toggle_editor(False)
            return
        
        nombre_nota = item.text()
        for prefix in ["📌 ", "★ ", "🔒 "]:
            while nombre_nota.startswith(prefix):
                nombre_nota = nombre_nota[len(prefix):]
        
        if self.nota_actual == nombre_nota:
            return

        if nombre_nota in self.protegidas:
            pin, ok = QInputDialog.getText(self, "Nota Protegida por PIN", f"La nota '{nombre_nota}' está protegida.\nIntroduce tu PIN:", QInputDialog.EchoMode.Password)
            if not ok or self.storage.desencriptar_hash_pin(pin) != self.protegidas[nombre_nota]:
                QMessageBox.warning(self, "Acceso Denegado", "⚠️ PIN Incorrecto. No se puede abrir esta nota.")
                self.gui.list_notas.clearSelection()
                return

        self.autosave_timer.stop()
        
        if self.nota_actual and self.nota_actual != nombre_nota:
            self.guardar_nota()
        
        self.nota_actual = nombre_nota
        self.gui.btn_fijar.setChecked(self.nota_actual in self.fijadas)
        self.gui.btn_favorito.setChecked(self.nota_actual in self.favoritas)
        self.imagenes_nota.clear()
        
        nuevo_doc = QTextDocument(self.gui.editor)
        nuevo_doc.setDefaultFont(QFont(self.font_family, 12))
        
        self.gui.editor.blockSignals(True)
        self.gui.editor.setDocument(nuevo_doc)
        
        try:
            ruta_nota = self.ruta_notas / f"{nombre_nota}.txt"
            with open(ruta_nota, "r", encoding="utf-8") as f:
                raw = f.read()
            
            self.gui.txt_titulo.setText(nombre_nota)
            self.gui.btn_favorito.setChecked(nombre_nota in self.favoritas)
            
            try:
                datos = json.loads(raw)
                if isinstance(datos, dict) and "html" in datos:
                    html_limpio = self._desempaquetar_html_seguro(datos["html"])
                    self.gui.editor.setHtml(html_limpio)
                    self.imagenes_nota.update(datos.get("imagenes_metadata", {}))
                    self.image_manager.cargar_imagenes_desde_datos()
                    tema = datos.get("background_color", "default")
                    self.aplicar_tema_color(tema)
                else:
                    self.gui.editor.setPlainText(raw)
                    self.aplicar_tema_color("default")
            except Exception:
                raw_strip = raw.strip()
                if raw_strip.startswith("<") or raw_strip.startswith("<!DOCTYPE"):
                    self.gui.editor.setHtml(raw)
                else:
                    self.gui.editor.setPlainText(raw)
                self.aplicar_tema_color("default")
            
            self.actualizar_estadisticas()
            self._toggle_editor(True)
            self.gui.lbl_status.setText("Nota sincronizada")
            
            self.watcher.blockSignals(True)
            existentes = self.watcher.files()
            if existentes: self.watcher.removePaths(existentes)
            self.watcher.addPath(str(ruta_nota))
            self.watcher.blockSignals(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar: {e}")
        finally:
            self.gui.editor.blockSignals(False)

    def eliminar_nota(self):
        item = self.gui.list_notas.currentItem()
        if not item: return
        
        nombre = item.text()
        for prefix in ["📌 ", "★ ", "🔒 "]:
            while nombre.startswith(prefix):
                nombre = nombre[len(prefix):]
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Eliminar Nota")
        msg.setText(f"¿Estás seguro de mover la nota '{nombre}' a la Papelera de Reciclaje?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        res = msg.exec()
        
        if res == QMessageBox.StandardButton.Yes:
            try:
                self._guardando_interno = True
                self.watcher.blockSignals(True)

                dir_papelera = self.ruta_notas / ".papelera"
                dir_papelera.mkdir(parents=True, exist_ok=True)
                src_file = self.ruta_notas / f"{nombre}.txt"
                dst_file = dir_papelera / f"{nombre}.txt"
                if src_file.exists():
                    shutil.move(src_file, dst_file)

                if nombre in self.favoritas:
                    self.favoritas.remove(nombre)
                    self.storage.guardar_favoritas(self.favoritas)
                if nombre in self.fijadas:
                    self.fijadas.remove(nombre)
                    self.storage.guardar_fijadas(self.fijadas)

                if self.nota_actual == nombre:
                    self.nota_actual = None
                    self.gui.editor.clear()
                    self.gui.txt_titulo.clear()
                    self._toggle_editor(False)
                self.cargar_lista_notas()
                if hasattr(self, 'tab_papelera'):
                    self.tab_papelera.cargar_papelera()
                self.gui.lbl_status.setText("Nota enviada a la Papelera de Reciclaje")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo mover a la papelera: {e}")
            finally:
                self.watcher.blockSignals(False)
                QTimer.singleShot(100, self._reset_guardando_interno)

    def actualizar_titulo(self):
        if not self.nota_actual: return
        nuevo = self.gui.txt_titulo.text().strip()
        if not nuevo or nuevo == self.nota_actual: return
        
        if any(c in nuevo for c in '\\/:*?"<>|'):
            QMessageBox.warning(self, "Título", "El título contiene caracteres no permitidos.")
            self.gui.txt_titulo.setText(self.nota_actual)
            return

        self.guardar_nota()
            
        ruta_old = self.ruta_notas / f"{self.nota_actual}.txt"
        ruta_new = self.ruta_notas / f"{nuevo}.txt"
        
        if ruta_new.exists():
            QMessageBox.warning(self, "Título Duplicado", f"Ya existe una nota con el nombre '{nuevo}'.")
            self.gui.txt_titulo.setText(self.nota_actual)
            return
            
        try:
            self._guardando_interno = True
            self.watcher.blockSignals(True)
            os.rename(ruta_old, ruta_new)
            
            existentes = self.watcher.files()
            if existentes: 
                self.watcher.removePaths(existentes)
            self.watcher.addPath(str(ruta_new))
            
            if self.nota_actual in self.favoritas:
                self.favoritas.remove(self.nota_actual)
                self.favoritas.append(nuevo)
                self.storage.guardar_favoritas(self.favoritas)
                
            self.nota_actual = nuevo
            self.cargar_lista_notas()
        except Exception as e:
            QMessageBox.warning(self, "Error al renombrar", f"No se pudo renombrar la nota: {e}")
            self.gui.txt_titulo.setText(self.nota_actual)
        finally:
            self.watcher.blockSignals(False)
            QTimer.singleShot(100, self._reset_guardando_interno)

    def aplicar_formato(self, tipo): self.format_manager.aplicar_formato(tipo)
    def actualizar_estado_formato(self): 
        btns_info = [
            {"btn": self.gui.btn_negrita, "tipo": "negrita", "var": None},
            {"btn": self.gui.btn_cursiva, "tipo": "cursiva", "var": None},
            {"btn": self.gui.btn_subrayado, "tipo": "subrayado", "var": None},
            {"btn": self.gui.btn_tachado, "tipo": "tachado", "var": None}
        ]
        self.format_manager.actualizar_estado_botones(None, btns_info)
        formatos = self.format_manager.obtener_formatos_activos()
        if hasattr(self.gui, "actualizar_estado_botones"):
            self.gui.actualizar_estado_botones(formatos)

        try:
            cursor = self.gui.editor.textCursor()
            fmt = cursor.charFormat()
            font_family = fmt.font().family() or "Segoe UI"
            font_size = int(fmt.fontPointSize()) if fmt.fontPointSize() > 0 else 12

            self.gui.combo_font.blockSignals(True)
            idx_f = self.gui.combo_font.findText(font_family)
            if idx_f != -1: self.gui.combo_font.setCurrentIndex(idx_f)
            self.gui.combo_font.blockSignals(False)

            self.gui.combo_size.blockSignals(True)
            idx_s = self.gui.combo_size.findText(str(font_size))
            if idx_s != -1: self.gui.combo_size.setCurrentIndex(idx_s)
            self.gui.combo_size.blockSignals(False)
        except Exception:
            pass

    def toggle_fijar(self):
        if not self.nota_actual: return
        fij = self.gui.btn_fijar.isChecked()
        if fij:
            if self.nota_actual not in self.fijadas: self.fijadas.append(self.nota_actual)
        else:
            if self.nota_actual in self.fijadas: self.fijadas.remove(self.nota_actual)
        self.storage.guardar_fijadas(self.fijadas)
        self.cargar_lista_notas()

    def proteger_nota(self):
        if not self.nota_actual: return
        if self.nota_actual in self.protegidas:
            pin, ok = QInputDialog.getText(self, "Desproteger Nota", "Esta nota está protegida.\nIntroduce tu PIN actual para quitar la protección:", QInputDialog.EchoMode.Password)
            if ok and pin.strip():
                if self.storage.desencriptar_hash_pin(pin) == self.protegidas[self.nota_actual]:
                    del self.protegidas[self.nota_actual]
                    self.storage.guardar_protegidas(self.protegidas)
                    self.cargar_lista_notas()
                    self.gui.btn_proteger.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
                    QMessageBox.information(self, "Protección Removida", f"¡La protección por PIN de la nota '{self.nota_actual}' ha sido quitada con éxito!")
                else:
                    QMessageBox.warning(self, "Acceso Denegado", "⚠️ PIN Incorrecto. No se pudo quitar la protección.")
        else:
            pin, ok = QInputDialog.getText(self, "Proteger Nota con PIN", "Introduce un PIN de 4 dígitos para proteger esta nota:", QInputDialog.EchoMode.Password)
            if ok and pin.strip():
                self.protegidas[self.nota_actual] = self.storage.desencriptar_hash_pin(pin)
                self.storage.guardar_protegidas(self.protegidas)
                self.cargar_lista_notas()
                self.gui.btn_proteger.setStyleSheet("background: rgba(239,68,68,0.2); color: #EF4444; border-radius: 6px; border: 1px solid #EF4444;")
                QMessageBox.information(self, "Nota Protegida", f"¡La nota '{self.nota_actual}' ahora requiere PIN para ser leída!")

    def cambiar_tamano_fuente(self, size_str): self.format_manager.cambiar_tamano(size_str)
    def cambiar_color_texto(self):
        color = QColorDialog.getColor(initial=Qt.GlobalColor.white, parent=self)
        if color.isValid(): self.format_manager.cambiar_color_texto(color.name())

    def cambiar_color_fondo(self):
        color = QColorDialog.getColor(initial=Qt.GlobalColor.yellow, parent=self)
        if color.isValid(): self.format_manager.cambiar_color_fondo(color.name())

    def cambiar_familia_fuente(self, fuente): self.format_manager.cambiar_familia_fuente(fuente)

    def cambiar_pastel_fondo(self, tema_id):
        if tema_id not in self.temas_pastel: return
        self.aplicar_tema_color(tema_id)
        self.guardar_nota()

    def aplicar_tema_color(self, tema_id):
        if tema_id not in self.temas_pastel: tema_id = "default"
        self.current_tema = tema_id
        t = self.temas_pastel[tema_id]
        self.gui.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t['bg']}; color: {t['fg']}; padding: 15px 25px; border: none;
            }}
        """)

    def insertar_imagen(self): self.image_manager.insertar_imagen()
    def insertar_vineta(self, tipo): self.format_manager.insertar_vineta(tipo)
    def insertar_tabla(self): self.table_manager.insertar_tabla()

    def filtrar_notas(self, texto):
        t = texto.lower().strip()
        for i in range(self.gui.list_notas.count()):
            item = self.gui.list_notas.item(i)
            item.setHidden(t not in item.text().lower())

    def buscar_en_contenido(self):
        query, ok = QInputDialog.getText(self, "Búsqueda Profunda", "Introduce la palabra clave a buscar en el contenido de todas las notas:")
        if not ok or not query.strip(): return
        q = query.lower().strip()
        coincidencias = 0
        for i in range(self.gui.list_notas.count()):
            item = self.gui.list_notas.item(i)
            nombre = item.text()
            for prefix in ["📌 ", "★ ", "🔒 "]:
                while nombre.startswith(prefix): nombre = nombre[len(prefix):]
            ruta = self.ruta_notas / f"{nombre}.txt"
            cont = False
            if ruta.exists():
                try:
                    with open(ruta, "r", encoding="utf-8") as f:
                        if q in f.read().lower(): cont = True
                except Exception: pass
            item.setHidden(not cont)
            if cont: coincidencias += 1
        self.gui.lbl_status.setText(f"{coincidencias} notas coinciden con '{query}'")

    def toggle_buscar_reemplazar(self):
        vis = self.gui.find_replace_bar.isVisible()
        self.gui.find_replace_bar.setVisible(not vis)
        if not vis: self.gui.find_replace_bar.txt_buscar.setFocus()

    def buscar_texto(self, texto):
        if not texto: return
        self.gui.editor.find(texto)

    def reemplazar_texto(self, buscar, reemplazar):
        cursor = self.gui.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == buscar:
            cursor.insertText(reemplazar)
        self.buscar_texto(buscar)

    def reemplazar_todo_texto(self, buscar, reemplazar):
        if not buscar: return
        cursor = self.gui.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.gui.editor.setTextCursor(cursor)
        cont = 0
        while self.gui.editor.find(buscar):
            c = self.gui.editor.textCursor()
            c.insertText(reemplazar)
            cont += 1
        self.gui.lbl_status.setText(f"Reemplazadas {cont} coincidencias")

    def mostrar_menu_contextual(self, pos): pass

    def eliminar_nota_obj(self): self.image_manager.eliminar_imagen_seleccionada()

    def actualizar_contenido(self):
        self.actualizar_estadisticas()
        self.gui.lbl_status.setText("Guardando borrador...")
        self.autosave_timer.start(1000)

    def actualizar_estadisticas(self):
        txt = self.gui.editor.toPlainText()
        palabras = len([w for w in txt.split() if w.strip()])
        chars = len(txt.rstrip())
        tiempo = max(1, round(palabras / 200))
        self.gui.lbl_stats.setText(f"Palabras: {palabras} | Caracteres: {chars} | Lectura: ~{tiempo} min")

    def toggle_favorito(self):
        if not self.nota_actual: return
        fav = self.gui.btn_favorito.isChecked()
        if fav:
            if self.nota_actual not in self.favoritas: self.favoritas.append(self.nota_actual)
        else:
            if self.nota_actual in self.favoritas: self.favoritas.remove(self.nota_actual)
        self.storage.guardar_favoritas(self.favoritas)
        self.cargar_lista_notas()

    def _toggle_editor(self, habilitado):
        self.gui.editor.setEnabled(habilitado)
        self.gui.txt_titulo.setEnabled(habilitado)
        if hasattr(self.gui, "mostrar_editor"):
            self.gui.mostrar_editor(habilitado)

    def deseleccionar_nota(self):
        """Deselecciona la nota activa (al pulsar Esc) y muestra la vista vacía tipo WhatsApp"""
        if self.nota_actual:
            self.guardar_nota()
        self.nota_actual = None
        if hasattr(self, "gui") and hasattr(self.gui, "list_notas"):
            try:
                if not isdeleted(self.gui) and not isdeleted(self.gui.list_notas):
                    self.gui.list_notas.blockSignals(True)
                    self.gui.list_notas.clearSelection()
                    self.gui.list_notas.setCurrentItem(None)
                    self.gui.list_notas.blockSignals(False)
            except Exception:
                pass
        self._toggle_editor(False)

    def mostrar_snapshots(self):
        if not self.nota_actual:
            QMessageBox.information(self, "Historial", "Abre una nota primero para ver sus versiones.")
            return
        
        snaps = self.storage.listar_snapshots(self.nota_actual)
        if not snaps:
            QMessageBox.information(self, "Historial de Versiones", f"No hay versiones previas guardadas para '{self.nota_actual}'.")
            return

        dlg = SnapshotViewerDialog(
            parent=self,
            nota_actual=self.nota_actual,
            storage=self.storage,
            colores=self.colores,
            editor=self.gui.editor,
            on_restored=self.guardar_nota
        )
        dlg.exec()

    def guardar_como_plantilla(self):
        if not self.nota_actual:
            QMessageBox.information(self, "Guardar Plantilla", "Abre una nota con contenido primero.")
            return

        nombre_defecto = self.nota_actual
        for prefix in ["📌 ", "★ ", "🔒 "]:
            while nombre_defecto.startswith(prefix):
                nombre_defecto = nombre_defecto[len(prefix):]

        titulo, ok = QInputDialog.getText(
            self, "Guardar como Plantilla", 
            "Título de la nueva plantilla personal:",
            text=nombre_defecto
        )
        if not ok or not titulo.strip():
            return

        desc, ok_d = QInputDialog.getText(
            self, "Descripción de Plantilla", 
            "Descripción breve de la plantilla:",
            text=f"Plantilla personalizada basada en {nombre_defecto}"
        )
        if not ok_d:
            desc = ""

        html = self.gui.editor.toHtml()
        self.storage.guardar_plantilla_usuario(titulo.strip(), desc.strip(), html)
        
        if hasattr(self, "tab_plantillas") and hasattr(self.tab_plantillas, "recargar_plantillas"):
            self.tab_plantillas.recargar_plantillas()

        QMessageBox.information(self, "Plantilla Guardada", f"¡La nota '{titulo}' ha sido guardada en la biblioteca de plantillas!")

    def asignar_tag(self):
        if not self.nota_actual:
            QMessageBox.information(self, "Etiquetas", "Abre una nota primero para asignarle etiquetas.")
            return

        tags_map = self.storage.cargar_tags()
        tags_actuales = tags_map.get(self.nota_actual, [])
        tags_str = ", ".join(tags_actuales)

        nuevo, ok = QInputDialog.getText(
            self, "Asignar Etiquetas",
            f"Etiquetas para '{self.nota_actual}' (separadas por comas):\nEjemplo: trabajo, ideas, urgente",
            text=tags_str
        )
        if ok:
            tags_lista = [t.strip().lstrip("#") for t in nuevo.split(",") if t.strip()]
            self.storage.guardar_tags(self.nota_actual, tags_lista)
            self.cargar_lista_notas()
            self.gui.lbl_status.setText(f"Etiquetas actualizadas: {', '.join(tags_lista)}")

    def filtrar_por_tag(self, tag):
        if not tag or str(tag).strip() in ("Todas", "🏷️ Todas", "todas"):
            self.filtro_tag_actual = None
        else:
            self.filtro_tag_actual = str(tag).strip()
        self.cargar_lista_notas()

    def importar_notas(self):
        importer = ImportManager(self, self.ruta_notas, on_import_success=self._on_import_success)
        importer.importar_archivo()

    def _on_import_success(self, nombre=None):
        self.cargar_lista_notas()
        if nombre:
            self.seleccionar_nota_por_nombre(nombre)
        self.tabs.setCurrentIndex(0)

    def insertar_enlace_dialogo(self):
        url, ok = QInputDialog.getText(self, "Insertar Enlace", "Introduce la URL o dirección web:\n(ej. https://ejemplo.com)")
        if ok and url.strip():
            cursor = self.gui.editor.textCursor()
            texto = cursor.selectedText().strip() or url.strip()
            self.format_manager.insertar_enlace(texto=texto, url=url.strip())

    def _aplicar_estilo_tabs(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background-color: {bg_p}; }}
            QTabBar::tab {{
                background: {bg_sec}; color: #AAB0B8; padding: 8px 16px; font-weight: bold;
                font-size: 11px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px;
            }}
            QTabBar::tab:selected {{ background: {acento}; color: white; }}
            QTabBar::tab:hover {{ color: white; }}
        """)

    def actualizar_tema(self, colores):
        if isinstance(colores, dict):
            self.colores = colores
            self._aplicar_estilo_tabs()
            if hasattr(self, "gui") and hasattr(self.gui, "actualizar_tema") and callable(self.gui.actualizar_tema):
                try:
                    self.gui.actualizar_tema(colores)
                except Exception as e:
                    print(f"[WARN] Error actualizando tema en gui_notas: {e}")
            for instance in getattr(self, "submod_instances", {}).values():
                if hasattr(instance, "actualizar_tema") and callable(instance.actualizar_tema):
                    try:
                        instance.actualizar_tema(colores)
                    except Exception as e:
                        print(f"[WARN] Error actualizando tema en submódulo de Notas: {e}")

    def cleanup(self):
        if self in TabNotas._instancias_activas:
            TabNotas._instancias_activas.remove(self)
        if hasattr(self, "watcher"):
            try:
                self.watcher.blockSignals(True)
                f = self.watcher.files()
                if f: self.watcher.removePaths(f)
                d = self.watcher.directories()
                if d: self.watcher.removePaths(d)
            except Exception:
                pass
        if self.nota_actual:
            self.guardar_nota()
