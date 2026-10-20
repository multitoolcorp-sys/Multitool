import os
import json
import datetime
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QMessageBox, 
    QFileDialog, QInputDialog, QTableWidgetItem, QMenu, QPushButton
)
from PyQt6.QtCore import Qt, QStandardPaths, QTimer, QCoreApplication
from PyQt6.QtGui import QFont, QBrush, QColor

from .submodulos.editor_grid import EditorGridSubmodule
from .submodulos.editor_texto import EditorTextoSubmodule
from .submodulos.vista_previa import VistaPreviaSubmodule
from .submodulos.exportador_plantillas import ExportadorPlantillasSubmodule


class TabCuaderno(QWidget):
    """
    Módulo Principal de Cuaderno de Notas y Hojas de Cálculo con QTabWidget y 4 Submódulos Desacoplados:
    1. Editor Grid Excel & ChartStudio
    2. Editor de Texto / Markdown / JSON Raw
    3. Vista Previa HD & Impresión
    4. Centro de Exportación & Catálogo de Plantillas
    """
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter" if hasattr(platform, 'system') else "Arial"
        self.usuario = getattr(context, "usuario", "Invitado")
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1", "acento_hover": "#4F46E5",
            "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        })
        
        # Ruta de datos
        self.ruta_data = self.ruta_usuario / "cuadernos"
        self.ruta_data.mkdir(parents=True, exist_ok=True)
        self.ruta_state = self.ruta_data / "config_cuaderno_vista.json"
        
        self.callbacks = {
            "guardar": self.guardar_cuaderno,
            "nuevo": self.nuevo_cuaderno,
            "marcar_modificado": self.verificar_modificaciones,
            "exportar_pdf": self.exportar_pdf,
            "exportar_excel": self.exportar_excel,
            "exportar_html": self.exportar_html,
            "eliminar": self.eliminar_cuaderno,
            "cargar": self.cargar_cuaderno_seleccionado,
            "generar_html": self._generar_html_render,
            "cargar_plantilla_cb": self.cargar_plantilla_predefinida,
            "deseleccionar": self.deseleccionar_cuaderno,
            "ir_a_plantillas": lambda: self.tabs.setCurrentIndex(3)
        }
        
        self.modificado = False
        self.cuaderno_actual = None
        self._iniciando = True

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(1500)
        self.autosave_timer.timeout.connect(self._autosave_timeout)

        app_inst = QCoreApplication.instance()
        if app_inst:
            try:
                app_inst.aboutToQuit.connect(self.cleanup)
            except Exception:
                pass

        self.inicializar_ui()
        self._set_editor_enabled(False)
        self.actualizar_lista()
        self._restaurar_vista_inicial()
        self._iniciando = False

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # TabWidget Superior de Alto Contraste
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont(self.font_family, 9))
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['acento']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)

        # Submódulos dinámicos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        extra_kwargs = {
            "callbacks": self.callbacks
        }
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores, extra_kwargs)

        if self.tabs.count() == 0:
            self.tab_grid = EditorGridSubmodule(self, self.context, self.colores, self.callbacks)
            self.tab_texto = EditorTextoSubmodule(self, self.context, self.colores, self.callbacks)
            self.tab_preview = VistaPreviaSubmodule(self, self.context, self.colores, self.callbacks)
            self.tab_export = ExportadorPlantillasSubmodule(self, self.context, self.colores, self.callbacks)

            self.tabs.addTab(self.tab_grid, "📊 Editor Grid & Gráficos")
            self.tabs.addTab(self.tab_texto, "📝 Editor Notas & Markdown")
            self.tabs.addTab(self.tab_preview, "👁️ Vista Previa & Impresión")
            self.tabs.addTab(self.tab_export, "📤 Exportador & Plantillas")
        else:
            self.tab_grid = self.submod_instances.get("EditorGridSubmodule") or self.submod_instances.get("editorgridsubmodule")
            if not self.tab_grid:
                self.tab_grid = EditorGridSubmodule(self, self.context, self.colores, self.callbacks)
            self.tab_texto = self.submod_instances.get("EditorTextoSubmodule") or self.submod_instances.get("editortextosubmodule")
            if not self.tab_texto:
                self.tab_texto = EditorTextoSubmodule(self, self.context, self.colores, self.callbacks)
            self.tab_preview = self.submod_instances.get("VistaPreviaSubmodule") or self.submod_instances.get("vistapreviasubmodule")
            if not self.tab_preview:
                self.tab_preview = VistaPreviaSubmodule(self, self.context, self.colores, self.callbacks)
            self.tab_export = self.submod_instances.get("ExportadorPlantillasSubmodule") or self.submod_instances.get("exportadorplantillassubmodule")
            if not self.tab_export:
                self.tab_export = ExportadorPlantillasSubmodule(self, self.context, self.colores, self.callbacks)

        # Aliases Proxy para compatibilidad total con llamadas internas
        self.gui = self
        if self.tab_grid:
            self.txt_nombre = getattr(self.tab_grid, "txt_nombre", None)
            if hasattr(self.tab_grid, "sidebar"):
                self.list_horarios = self.tab_grid.sidebar.list_horarios
            self.tabla = getattr(self.tab_grid, "tabla", None)
            self.lbl_status = getattr(self.tab_grid, "lbl_status", None)
        if self.tab_texto:
            self.text_editor = getattr(self.tab_texto, "text_editor", None)
        if self.tab_preview:
            self.preview_browser = getattr(self.tab_preview, "preview_browser", None)
        self.current_view_index = 0

        # Context menu en pestañas para fijar vista inicial
        self.tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.tabBar().customContextMenuRequested.connect(self._mostrar_menu_tab)

        # Botón de menú de Vistas en la esquina superior derecha del TabWidget
        self.btn_vista_menu = QPushButton("⚙️ Vista")
        self.btn_vista_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_vista_menu.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.05);
                color: #AAB0B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 10px;
                font-weight: bold;
                margin-right: 6px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.1);
                color: white;
            }}
        """)
        self._actualizar_menu_vista_btn()
        self.tabs.setCornerWidget(self.btn_vista_menu, Qt.Corner.TopRightCorner)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.main_layout.addWidget(self.tabs)

    def _actualizar_menu_vista_btn(self):
        v_menu = QMenu(self)
        for i in range(self.tabs.count()):
            t_text = self.tabs.tabText(i)
            v_menu.addAction(f"Ir a: {t_text}", lambda idx=i: self.tabs.setCurrentIndex(idx))
        v_menu.addSeparator()
        v_menu.addAction("⭐ Fijar pestaña actual como Vista Inicial", lambda: self._fijar_vista_inicial(self.tabs.currentIndex()))
        self.btn_vista_menu.setMenu(v_menu)

    def _mostrar_menu_tab(self, pos):
        idx = self.tabs.tabBar().tabAt(pos)
        if idx < 0:
            return
        menu = QMenu(self)
        tab_name = self.tabs.tabText(idx)
        act_fijar = menu.addAction(f"⭐ Establecer '{tab_name}' como Vista Inicial Predeterminada")
        act_fijar.triggered.connect(lambda: self._fijar_vista_inicial(idx))
        menu.exec(self.tabs.tabBar().mapToGlobal(pos))

    def _fijar_vista_inicial(self, idx):
        self._guardar_vista_estado(idx)
        tab_name = self.tabs.tabText(idx)
        if hasattr(self, 'lbl_status') and self.lbl_status:
            self.lbl_status.setText(f"Vista inicial guardada: {tab_name}")

    def _guardar_vista_estado(self, index=None):
        if index is None:
            index = self.tabs.currentIndex()
        try:
            state = {
                "vista_inicial": int(index),
                "ultimo_cuaderno": self.cuaderno_actual,
                "recordar_ultima": True
            }
            with open(self.ruta_state, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception:
            pass

    def _restaurar_vista_inicial(self):
        if not self.ruta_state.exists():
            return
        try:
            with open(self.ruta_state, "r", encoding="utf-8") as f:
                state = json.load(f)
            ult_cuaderno = state.get("ultimo_cuaderno")
            if ult_cuaderno and (self.ruta_data / f"{ult_cuaderno}.json").exists():
                for i in range(self.list_horarios.count()):
                    item = self.list_horarios.item(i)
                    if item and item.text() == ult_cuaderno:
                        self.list_horarios.setCurrentItem(item)
                        break
            vista_idx = state.get("vista_inicial", 0)
            if 0 <= vista_idx < self.tabs.count():
                self.tabs.setCurrentIndex(vista_idx)
        except Exception as e:
            print(f"[TabCuaderno] Error restaurando vista inicial: {e}")

    def _on_tab_changed(self, index):
        self.current_view_index = index
        if not self._iniciando:
            self._guardar_vista_estado(index)
            if self.modificado:
                self.guardar_cuaderno(silencioso=True)
        try:
            if index == 1: # Texto / Notas Markdown
                # Mantener notas del usuario intactas; si está vacío, sugerir título
                if self.text_editor and not self.text_editor.toPlainText().strip():
                    nombre_cur = self.txt_nombre.text().strip() if self.txt_nombre else "Mi Cuaderno"
                    self.text_editor.setPlainText(f"# Notas de {nombre_cur}\n\n- Escribe aquí tus observaciones, fórmulas especiales o resumen.\n")
            elif index == 2: # Vista Previa
                modo_imp = getattr(self.tab_preview, "modo_impresion", False)
                html = self._generar_html_render(for_print=modo_imp)
                if self.preview_browser:
                    self.preview_browser.setHtml(html)
        except Exception as e:
            print(f"[TabCuaderno] Excepción en cambio de pestaña {index}: {e}")

    def actualizar_lista(self):
        self.list_horarios.blockSignals(True)
        self.list_horarios.clear()
        archivos = [f.stem for f in self.ruta_data.glob("*.json")]
        archivos.sort(key=lambda x: os.path.getmtime(self.ruta_data / f"{x}.json"), reverse=True)
        self.list_horarios.addItems(archivos)
        self.list_horarios.blockSignals(False)
        
        if archivos:
            self.list_horarios.setCurrentRow(0)
            self.cargar_cuaderno_seleccionado()
        else:
            self._set_editor_enabled(False)

    def crear_cuaderno_inicial(self):
        nombre = "Mi Cuaderno"
        self.tabla.blockSignals(True)
        self.tabla.clearContents()
        self.tabla.setRowCount(20)
        self.tabla.setColumnCount(12)
        self.tabla.setHorizontalHeaderLabels([chr(65+i) if i < 26 else f"Col {i}" for i in range(12)])
        self.tabla.blockSignals(False)
        
        if self.text_editor:
            self.text_editor.blockSignals(True)
            self.text_editor.clear()
            self.text_editor.blockSignals(False)

        self.txt_nombre.setText(nombre)
        self.cuaderno_actual = nombre
        self.guardar_cuaderno()
        self._set_editor_enabled(True)

    def nuevo_cuaderno(self):
        if self.modificado:
            if QMessageBox.question(self, "Guardar", "¿Guardar cambios del libro actual antes de crear uno nuevo?", 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.guardar_cuaderno()

        nombre, ok = QInputDialog.getText(self, "Nuevo Libro", "Nombre del Cuaderno:", text="Mi Cuaderno")
        if not ok or not nombre.strip(): return

        nombre = nombre.strip()
        path = self.ruta_data / f"{nombre}.json"
        if path.exists():
            QMessageBox.warning(self, "Error", f"'{nombre}' ya existe.")
            return

        self.tabla.blockSignals(True)
        self.tabla.clearContents()
        self.tabla.setRowCount(20)
        self.tabla.setColumnCount(12)
        self.tabla.setHorizontalHeaderLabels([chr(65+i) if i < 26 else f"Col {i}" for i in range(12)])
        self.tabla.blockSignals(False)
        
        if self.text_editor:
            self.text_editor.blockSignals(True)
            self.text_editor.clear()
            self.text_editor.blockSignals(False)

        self.txt_nombre.setText(nombre)
        self.cuaderno_actual = nombre
        self.guardar_cuaderno()
        self._set_editor_enabled(True)
        self.lbl_status.setText(f"Libro '{nombre}' creado.")

    def guardar_cuaderno(self, silencioso=False):
        nombre = self.txt_nombre.text().strip()
        if not nombre: return
        nombre_file = "".join([c for c in nombre if c.isalnum() or c in (' ', '_')]).rstrip()
        if not nombre_file: return
        path = self.ruta_data / f"{nombre_file}.json"
        
        try:
            snapshot = self.tabla._crear_snapshot()
            notas = self.text_editor.toPlainText() if self.text_editor else ""
            data = {
                "nombre": nombre,
                "snapshot": snapshot,
                "notas": notas,
                "metadata": {
                    "usuario": self.usuario,
                    "ultima_modificacion": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            
            self.cuaderno_actual = nombre_file
            self.modificado = False
            self._guardar_vista_estado()
            if hasattr(self, 'lbl_status') and self.lbl_status:
                self.lbl_status.setText("Guardado automáticamente." if silencioso else "Sincronizado.")
            self._sincronizar_items_sidebar(nombre_file)
        except Exception as e:
            if not silencioso:
                QMessageBox.critical(self, "Error", str(e))

    def _sincronizar_items_sidebar(self, nombre_activo):
        if not hasattr(self, 'list_horarios') or not self.list_horarios:
            return
        self.list_horarios.blockSignals(True)
        encontrado = False
        for i in range(self.list_horarios.count()):
            it = self.list_horarios.item(i)
            if it and it.text() == nombre_activo:
                self.list_horarios.setCurrentItem(it)
                encontrado = True
                break
        if not encontrado:
            self.list_horarios.insertItem(0, nombre_activo)
            self.list_horarios.setCurrentRow(0)
        self.list_horarios.blockSignals(False)

    def cargar_cuaderno_seleccionado(self):
        item = self.list_horarios.currentItem()
        if not item: return
        if self.modificado:
            self.guardar_cuaderno(silencioso=True)

        nombre = item.text()
        path = self.ruta_data / f"{nombre}.json"
        if not path.exists(): return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.tabla.blockSignals(True)
            self.tabla.clearContents()
            self.txt_nombre.setText(data.get("nombre", nombre))
            if "snapshot" in data:
                self.tabla._restaurar_snapshot(data["snapshot"])
            self.tabla.blockSignals(False)

            if self.text_editor:
                self.text_editor.blockSignals(True)
                self.text_editor.setPlainText(data.get("notas", ""))
                self.text_editor.blockSignals(False)

            self.cuaderno_actual = nombre
            self.modificado = False
            self.lbl_status.setText(f"Abierto: {nombre}")
            self._set_editor_enabled(True)
            
            self._on_tab_changed(self.tabs.currentIndex())
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def cargar_plantilla_predefinida(self, nombre, headers, rows):
        self.tabla.blockSignals(True)
        self.tabla.clearContents()
        self.tabla.setColumnCount(len(headers))
        self.tabla.setRowCount(max(20, len(rows) + 5))
        self.tabla.setHorizontalHeaderLabels(headers)

        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                it = QTableWidgetItem(str(val))
                it.setForeground(QBrush(QColor("#ffffff")))
                self.tabla.setItem(r, c, it)

        self.tabla.blockSignals(False)
        self.txt_nombre.setText(nombre)
        self.cuaderno_actual = nombre
        self._set_editor_enabled(True)
        self.guardar_cuaderno()
        self.tabs.setCurrentIndex(0) # Cambiar al Grid

    # --- EXPORTACIONES ---
    def exportar_html(self):
        nombre = self.txt_nombre.text().strip() or "Cuaderno"
        def_name = f"{nombre}.html"
        docs_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Libro a HTML", 
            str(Path(docs_dir) / def_name), 
            "HTML Files (*.html)"
        )
        if not path: return
        try:
            self.lbl_status.setText("Exportando a HTML...")
            html = self._generar_html_render(for_print=False)
            with open(path, "w", encoding="utf-8") as f: f.write(html)
            self.lbl_status.setText(f"Exportado a HTML correctamente.")
            QMessageBox.information(self, "Éxito", f"Exportado a {Path(path).name} correctamente.")
        except Exception as e:
            self.lbl_status.setText("Error al exportar HTML.")
            QMessageBox.critical(self, "Error", f"No se pudo exportar a HTML: {e}")

    def exportar_excel(self):
        nombre = self.txt_nombre.text().strip() or "Cuaderno"
        def_name = f"{nombre}.csv"
        docs_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar a Excel / CSV", 
            str(Path(docs_dir) / def_name), 
            "Excel CSV (*.csv)"
        )
        if not path: return
        import csv
        try:
            self.lbl_status.setText("Exportando a Excel CSV...")
            total_rows = self.tabla.rowCount()
            total_cols = self.tabla.columnCount()
            
            non_empty_rows = [r for r in range(total_rows) if any(self.tabla.item(r, c) and self.tabla.item(r, c).text().strip() for c in range(total_cols))]
            non_empty_cols = [c for c in range(total_cols) if any(self.tabla.item(r, c) and self.tabla.item(r, c).text().strip() for r in range(total_rows))]

            if not non_empty_rows: non_empty_rows = [0]
            if not non_empty_cols: non_empty_cols = [0]

            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                f.write("sep=,\n")
                writer = csv.writer(f, delimiter=",")
                headers = [self.tabla.horizontalHeaderItem(c).text() if self.tabla.horizontalHeaderItem(c) else chr(65 + c) for c in non_empty_cols]
                writer.writerow(headers)
                for r in non_empty_rows:
                    row_data = [self.tabla.item(r, c).text() if self.tabla.item(r, c) else "" for c in non_empty_cols]
                    writer.writerow(row_data)
            self.lbl_status.setText("Exportado a Excel CSV correctamente.")
            QMessageBox.information(self, "Éxito", f"El archivo '{Path(path).name}' ha sido exportado correctamente en formato compatible con Excel.")
        except Exception as e:
            self.lbl_status.setText("Error al exportar a CSV.")
            QMessageBox.critical(self, "Error", f"No se pudo exportar: {e}")

    def exportar_pdf(self):
        nombre = self.txt_nombre.text().strip() or "Cuaderno"
        def_name = f"{nombre}.pdf"
        docs_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar a PDF", 
            str(Path(docs_dir) / def_name), 
            "PDF Files (*.pdf)"
        )
        if not path: return
        
        try:
            from PyQt6.QtPrintSupport import QPrinter
            from PyQt6.QtGui import QTextDocument, QPageLayout
            from PyQt6.QtCore import QMarginsF
            
            self.lbl_status.setText("Generando PDF...")
            printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)
            printer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
            
            html = self._generar_html_render(for_print=True)
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print(printer)
            
            self.lbl_status.setText(f"Exportado a PDF correctamente.")
            QMessageBox.information(self, "Éxito", f"El archivo '{Path(path).name}' ha sido exportado correctamente.")
        except Exception as e:
            self.lbl_status.setText("Error al exportar PDF.")
            QMessageBox.critical(self, "Error", f"No se pudo exportar a PDF: {e}")

    def _generar_html_render(self, for_print=False):
        nombre_libro = self.txt_nombre.text().strip() or "Sin Título"
        
        if for_print:
            bg_body, color_text, color_title = "#ffffff", "#1f2937", "#4f46e5"
            border_color, bg_th, fg_th = "#d1d5db", "#4f46e5", "#ffffff"
            bg_row_even, bg_row_odd = "#f9fafb", "#ffffff"
            fs_h1, fs_th, fs_td, fs_footer = "22pt", "11pt", "10pt", "9pt"
        else:
            bg_body, color_text = "#121218", "#e2e2e2"
            color_title = self.colores.get("acento", "#6366F1")
            border_color = "rgba(255, 255, 255, 0.08)"
            bg_th = "rgba(45, 45, 61, 0.95)"
            fg_th = self.colores.get("acento", "#6366F1")
            bg_row_even, bg_row_odd = "rgba(255, 255, 255, 0.02)", "transparent"
            fs_h1, fs_th, fs_td, fs_footer = "24px", "12px", "11px", "10px"

        total_rows = self.tabla.rowCount()
        total_cols = self.tabla.columnCount()
        
        non_empty_rows = [r for r in range(total_rows) if any(self.tabla.item(r, c) and self.tabla.item(r, c).text().strip() for c in range(total_cols))]
        non_empty_cols = [c for c in range(total_cols) if any(self.tabla.item(r, c) and self.tabla.item(r, c).text().strip() for r in range(total_rows))]

        if not non_empty_rows: non_empty_rows = [0]
        if not non_empty_cols: non_empty_cols = [0]

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ background: {bg_body}; color: {color_text}; font-family: 'Segoe UI', Arial, sans-serif; padding: 30px; margin: 0; }}
                h1 {{ color: {color_title}; text-align: center; font-size: {fs_h1}; margin-bottom: 25px; font-weight: bold; }}
                table {{ border-collapse: collapse; margin: 15px auto; width: auto; max-width: 100%; border: 1px solid {border_color}; border-radius: 8px; overflow: hidden; }}
                th {{ padding: 12px 10px; background: {bg_th}; color: {fg_th}; font-weight: bold; font-size: {fs_th}; text-transform: uppercase; border: 1px solid {border_color}; text-align: center; }}
                td {{ padding: 10px; font-size: {fs_td}; border: 1px solid {border_color}; min-width: 80px; }}
                .row-even {{ background: {bg_row_even}; }}
                .row-odd {{ background: {bg_row_odd}; }}
                .footer {{ font-size: {fs_footer}; color: #6b7280; text-align: right; margin-top: 30px; border-top: 1px solid {border_color}; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <h1>{nombre_libro}</h1>
            <table>
                <thead>
                    <tr>
        """
        for c in non_empty_cols:
            h = self.tabla.horizontalHeaderItem(c).text() if self.tabla.horizontalHeaderItem(c) else chr(65 + c)
            html += f"<th>{h}</th>"
            
        html += "</tr></thead><tbody>"
        for i, r in enumerate(non_empty_rows):
            row_class = "row-even" if i % 2 == 0 else "row-odd"
            html += f"<tr class='{row_class}'>"
            for c in non_empty_cols:
                it = self.tabla.item(r, c)
                txt = it.text() if it else ""
                style_attr = ""
                if it:
                    bg_s = f"background-color: {it.background().color().name()};" if it.background().style() != Qt.BrushStyle.NoBrush and it.background().color().isValid() else ""
                    fg_s = f"color: {it.foreground().color().name()};" if it.foreground().color().isValid() else ""
                    if it.font().bold(): fg_s += " font-weight: bold;"
                    if it.font().italic(): fg_s += " font-style: italic;"
                    if bg_s or fg_s: style_attr = f" style='{bg_s} {fg_s}'"
                html += f"<td{style_attr}>{txt}</td>"
            html += "</tr>"
            
        notas_html = ""
        notas_raw = self.text_editor.toPlainText().strip() if self.text_editor else ""
        if notas_raw:
            lineas = []
            for l in notas_raw.split("\n"):
                l_s = l.strip()
                if l_s.startswith("# "):
                    lineas.append(f"<h2 style='color:{color_title}; margin-top:15px; margin-bottom:8px; font-size:16px;'>{l_s[2:]}</h2>")
                elif l_s.startswith("## "):
                    lineas.append(f"<h3 style='color:{color_title}; margin-top:12px; margin-bottom:6px; font-size:14px;'>{l_s[3:]}</h3>")
                elif l_s.startswith("- ") or l_s.startswith("* "):
                    lineas.append(f"<li style='margin-left:20px; font-size:{fs_td}; margin-bottom:4px;'>{l_s[2:]}</li>")
                elif l_s:
                    lineas.append(f"<p style='margin:5px 0; font-size:{fs_td}; line-height:1.4;'>{l}</p>")
            notas_box_bg = "#f3f4f6" if for_print else "rgba(30, 30, 46, 0.5)"
            notas_box_border = "#e5e7eb" if for_print else "rgba(255, 255, 255, 0.08)"
            notas_html = f"""
            <div style="margin-top: 25px; padding: 15px 20px; border: 1px solid {notas_box_border}; border-radius: 8px; background: {notas_box_bg};">
                <div style="font-weight: bold; font-size: 13px; color: {color_title}; margin-bottom: 10px; border-bottom: 1px solid {notas_box_border}; padding-bottom: 5px;">
                    📝 Notas y Resumen
                </div>
                {''.join(lineas)}
            </div>
            """

        html += f"""
                </tbody>
            </table>
            {notas_html}
            <p class="footer">Generado por Multitool Global • {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        </body>
        </html>
        """
        return html

    def eliminar_cuaderno(self):
        it = self.list_horarios.currentItem()
        if not it: return
        nombre = it.text()
        if QMessageBox.question(self, "Borrar", f"¿Eliminar '{nombre}' permanentemente?", 
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            path = self.ruta_data / f"{nombre}.json"
            if path.exists(): os.remove(path)
            if self.cuaderno_actual == nombre:
                self.deseleccionar_cuaderno()
            self.actualizar_lista()

    def deseleccionar_cuaderno(self):
        """Deselecciona el cuaderno actual y muestra la vista de espera vacía estilo Notas."""
        if self.modificado and not self._iniciando:
            self.guardar_cuaderno(silencioso=True)
        self.cuaderno_actual = None
        if hasattr(self, 'list_horarios') and self.list_horarios:
            self.list_horarios.blockSignals(True)
            self.list_horarios.clearSelection()
            self.list_horarios.setCurrentItem(None)
            self.list_horarios.blockSignals(False)
        self._set_editor_enabled(False)

    def verificar_modificaciones(self, *args):
        if self._iniciando:
            return
        self.modificado = True
        if hasattr(self, 'lbl_status') and self.lbl_status:
            self.lbl_status.setText("● Guardando...")
        if hasattr(self, 'autosave_timer'):
            self.autosave_timer.start(1500)

    def _autosave_timeout(self):
        if self.modificado and not self._iniciando:
            self.guardar_cuaderno(silencioso=True)

    def hideEvent(self, event):
        if self.modificado and not self._iniciando:
            self.guardar_cuaderno(silencioso=True)
        try:
            super().hideEvent(event)
        except Exception:
            pass

    def _set_editor_enabled(self, status):
        # El sidebar SIEMPRE debe estar habilitado para poder pulsar 'Nuevo' o seleccionar un cuaderno
        if hasattr(self.tab_grid, "sidebar"):
            self.tab_grid.sidebar.setEnabled(True)
        if hasattr(self.tab_grid, "mostrar_editor"):
            self.tab_grid.mostrar_editor(status)
        if hasattr(self.tab_grid, "tabla") and self.tab_grid.tabla:
            self.tab_grid.tabla.setEnabled(status)
        if hasattr(self.tab_grid, "toolbar") and self.tab_grid.toolbar:
            self.tab_grid.toolbar.setEnabled(status)
        if hasattr(self.tab_grid, "txt_nombre") and self.tab_grid.txt_nombre:
            self.tab_grid.txt_nombre.setEnabled(status)
        if hasattr(self.tab_grid, "txt_formula") and self.tab_grid.txt_formula:
            self.tab_grid.txt_formula.setEnabled(status)
        if hasattr(self.tab_grid, "btn_toggle_chart") and self.tab_grid.btn_toggle_chart:
            self.tab_grid.btn_toggle_chart.setEnabled(status)
        if hasattr(self, "tab_texto") and self.tab_texto:
            self.tab_texto.setEnabled(status)
        if hasattr(self, "tab_preview") and self.tab_preview:
            self.tab_preview.setEnabled(status)
        if hasattr(self, "tab_export") and self.tab_export:
            self.tab_export.setEnabled(status)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores.get('bg_principal', '#121218')};
            }}
            QTabBar::tab {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)
        for submod in [self.tab_grid, self.tab_texto, self.tab_preview, self.tab_export]:
            if submod and hasattr(submod, 'actualizar_tema'):
                try:
                    submod.actualizar_tema(colores)
                except Exception:
                    pass

    def cleanup(self):
        if hasattr(self, 'autosave_timer') and self.autosave_timer.isActive():
            self.autosave_timer.stop()
        if self.modificado and not self._iniciando:
            try:
                self.guardar_cuaderno(silencioso=True)
            except Exception:
                pass
