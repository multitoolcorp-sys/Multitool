"""
editor_components.py - Componentes visuales desacoplados del editor de notas (Búsqueda y Reemplazo, Editor RichText)
"""
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLineEdit, QPushButton, QTextEdit,
    QApplication, QMenu, QFileDialog, QColorDialog, QDialog,
    QVBoxLayout, QLabel, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QTextTableFormat, QImage, QPixmap, QColor, QTextDocument
import datetime
import webbrowser
import urllib.parse


class FindReplaceWidget(QFrame):
    """Barra flotante de búsqueda y reemplazo de texto"""
    def __init__(self, parent=None, callback_find=None, callback_replace=None, callback_replace_all=None, colors=None):
        super().__init__(parent)
        self.colors = colors or {
            "bg_secundario": "#2D2D2D",
            "bg_terciario": "#3D3D3D",
            "acento": "#4A86E8",
            "fg_principal": "#E0E0E0"
        }
        self.callback_find = callback_find
        self.callback_replace = callback_replace
        self.callback_replace_all = callback_replace_all
        
        self.setFixedHeight(38)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors.get('bg_secundario', '#2D2D2D')};
                border-top: 1px solid rgba(255,255,255,0.08);
                border-bottom: 1px solid rgba(255,255,255,0.08);
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)
        
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar texto...")
        self.txt_buscar.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colors.get('bg_terciario', '#3D3D3D')};
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 2px 6px; color: white; font-size: 11px;
            }}
        """)
        self.txt_buscar.returnPressed.connect(self.on_find)
        layout.addWidget(self.txt_buscar, 2)
        
        btn_find = QPushButton("🔍")
        btn_find.setFixedSize(26, 26)
        btn_find.setToolTip("Buscar siguiente")
        btn_find.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_find.setStyleSheet(f"background: {self.colors.get('acento', '#4A86E8')}; color: white; border-radius: 4px;")
        btn_find.clicked.connect(self.on_find)
        layout.addWidget(btn_find)
        
        self.txt_reemplazar = QLineEdit()
        self.txt_reemplazar.setPlaceholderText("Reemplazar con...")
        self.txt_reemplazar.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colors.get('bg_terciario', '#3D3D3D')};
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px; padding: 2px 6px; color: white; font-size: 11px;
            }}
        """)
        self.txt_reemplazar.returnPressed.connect(self.on_replace)
        layout.addWidget(self.txt_reemplazar, 2)
        
        btn_replace = QPushButton("Reemplazar")
        btn_replace.setFixedHeight(26)
        btn_replace.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_replace.setStyleSheet("background: rgba(255,255,255,0.1); color: white; border-radius: 4px; padding: 0 8px; font-size: 10px;")
        btn_replace.clicked.connect(self.on_replace)
        layout.addWidget(btn_replace)
        
        btn_replace_all = QPushButton("Todo")
        btn_replace_all.setFixedHeight(26)
        btn_replace_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_replace_all.setStyleSheet("background: rgba(255,255,255,0.1); color: white; border-radius: 4px; padding: 0 8px; font-size: 10px;")
        btn_replace_all.clicked.connect(self.on_replace_all)
        layout.addWidget(btn_replace_all)
        
        btn_close = QPushButton("✖")
        btn_close.setFixedSize(22, 22)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("background: transparent; color: #A0A0A0; font-weight: bold; border: none;")
        btn_close.clicked.connect(self.hide)
        layout.addWidget(btn_close)

    def on_find(self):
        if self.callback_find:
            self.callback_find(self.txt_buscar.text())

    def on_replace(self):
        if self.callback_replace:
            self.callback_replace(self.txt_buscar.text(), self.txt_reemplazar.text())

    def on_replace_all(self):
        if self.callback_replace_all:
            self.callback_replace_all(self.txt_buscar.text(), self.txt_reemplazar.text())


class NotesEditor(QTextEdit):
    """Editor de texto enriquecido con soporte para imágenes, menús contextuales y checkboxes interactivos"""
    def __init__(self, parent=None, callbacks=None):
        super().__init__(parent)
        self.callbacks = callbacks
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            if self._intentar_toggle_checkbox(cursor):
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()
        text = self.document().toPlainText()
        is_over_cb = False
        for offset in (0, -1, 1):
            p = pos + offset
            if 0 <= p < len(text) and text[p] in ("☐", "☑"):
                is_over_cb = True
                break
            if 0 <= p and p + 3 <= len(text) and text[p:p+3] in ("[ ]", "[x]", "[X]"):
                is_over_cb = True
                break
        if is_over_cb:
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(event)

    def _intentar_toggle_checkbox(self, cursor):
        """Detecta si la posición del cursor o el clic está sobre o adyacente a un checkbox y lo alterna."""
        pos = cursor.position()
        doc = self.document()
        text = doc.toPlainText()
        if not text:
            return False

        for offset in (0, -1, 1, -2, 2):
            p = pos + offset
            if 0 <= p < len(text):
                ch = text[p]
                if ch in ("☐", "☑"):
                    nuevo = "☑" if ch == "☐" else "☐"
                    cur = QTextCursor(doc)
                    cur.setPosition(p)
                    cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
                    cur.insertText(nuevo)
                    return True
                
                if p + 3 <= len(text):
                    sub = text[p:p+3]
                    if sub == "[ ]":
                        cur = QTextCursor(doc)
                        cur.setPosition(p)
                        cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 3)
                        cur.insertText("[x]")
                        return True
                    elif sub in ("[x]", "[X]"):
                        cur = QTextCursor(doc)
                        cur.setPosition(p)
                        cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 3)
                        cur.insertText("[ ]")
                        return True
        return False

    def alternar_checkbox_linea_actual(self):
        """Alterna el checkbox presente en la línea o bloque actual del cursor"""
        cursor = self.textCursor()
        block = cursor.block()
        text = block.text()
        block_pos = block.position()
        
        for i, ch in enumerate(text):
            if ch in ("☐", "☑"):
                nuevo = "☑" if ch == "☐" else "☐"
                cur = QTextCursor(self.document())
                cur.setPosition(block_pos + i)
                cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
                cur.insertText(nuevo)
                return True
            if i + 3 <= len(text):
                sub = text[i:i+3]
                if sub == "[ ]":
                    cur = QTextCursor(self.document())
                    cur.setPosition(block_pos + i)
                    cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 3)
                    cur.insertText("[x]")
                    return True
                elif sub in ("[x]", "[X]"):
                    cur = QTextCursor(self.document())
                    cur.setPosition(block_pos + i)
                    cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 3)
                    cur.insertText("[ ]")
                    return True
        return False

    def contextMenuEvent(self, event):
        try:
            menu = self.createStandardContextMenu()
            menu.setStyleSheet("""
                QMenu {
                    background-color: #1E1E2E;
                    color: #E0E0E0;
                    border: 1px solid #6366F1;
                    border-radius: 8px;
                    padding: 6px;
                }
                QMenu::item {
                    padding: 6px 20px 6px 12px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #6366F1;
                    color: white;
                }
                QMenu::separator {
                    height: 1px;
                    background: rgba(255, 255, 255, 0.1);
                    margin: 4px 6px;
                }
            """)
            cursor = self.cursorForPosition(event.pos())
            
            # --- ACCIONES DE TEXTO PLANO ---
            clipboard = QApplication.clipboard()
            if clipboard and clipboard.text():
                act_paste_plain = menu.addAction("📋 Pegar como Texto Plano")
                act_paste_plain.triggered.connect(lambda: self.textCursor().insertText(clipboard.text()))

            menu.addSeparator()

            # --- ACCIONES DE FORMATO BÁSICO ---
            act_b = menu.addAction("𝐁 Negrita")
            act_i = menu.addAction("𝐼 Cursiva")
            act_u = menu.addAction("U̲ Subrayado")
            
            act_b.triggered.connect(lambda: self.callbacks["aplicar_formato"]("negrita") if self.callbacks else None)
            act_i.triggered.connect(lambda: self.callbacks["aplicar_formato"]("cursiva") if self.callbacks else None)
            act_u.triggered.connect(lambda: self.callbacks["aplicar_formato"]("subrayado") if self.callbacks else None)

            # --- TRANSFORMACIÓN Y BÚSQUEDA SI HAY SELECCIÓN ---
            sel_text = self.textCursor().selectedText()
            if sel_text:
                menu.addSeparator()
                m_case = menu.addMenu("🔠 Transformar Selección")
                act_upper = m_case.addAction("MAYÚSCULAS")
                act_lower = m_case.addAction("minúsculas")
                act_title = m_case.addAction("Tipo Título")
                
                act_upper.triggered.connect(lambda: self.textCursor().insertText(sel_text.upper()))
                act_lower.triggered.connect(lambda: self.textCursor().insertText(sel_text.lower()))
                act_title.triggered.connect(lambda: self.textCursor().insertText(sel_text.title()))

                clean_search = sel_text.strip().replace("\u2029", " ")
                act_web = menu.addAction(f"🔍 Buscar en la Web: \"{clean_search[:20]}...\"")
                act_web.triggered.connect(lambda: webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(clean_search)}"))

            # --- INSERTAR FECHA Y HORA ---
            act_date = menu.addAction("📅 Insertar Fecha y Hora")
            act_date.triggered.connect(lambda: self.textCursor().insertText(datetime.datetime.now().strftime("%d/%m/%Y %H:%M ")))
            
            # --- DETECCIÓN DE IMAGEN ---
            temp_cursor = QTextCursor(cursor)
            temp_cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            fmt = temp_cursor.charFormat()
            
            if fmt.isImageFormat():
                menu.addSeparator()
                m_img = menu.addMenu("🖼️ Opciones de Imagen")
                
                act_align_left = m_img.addAction("⬅️ Ajustar a la Izquierda")
                act_align_center = m_img.addAction("↔️ Centrado")
                act_align_right = m_img.addAction("➡️ Ajustar a la Derecha")
                m_img.addSeparator()
                act_resize = m_img.addAction("📏 Cambiar Tamaño (px)")
                act_copy_img = m_img.addAction("📋 Copiar Imagen al Portapapeles")
                act_save_img = m_img.addAction("💾 Guardar Imagen como...")
                act_view_full = m_img.addAction("🔍 Ver en Tamaño Completo")
                m_img.addSeparator()
                act_del = m_img.addAction("🗑️ Eliminar Imagen")

                def ajustar_img(modo):
                    self.setTextCursor(cursor)
                    if self.callbacks and "ajustar_imagen" in self.callbacks:
                        self.callbacks["ajustar_imagen"](cursor, modo)

                def redim_img():
                    self.setTextCursor(cursor)
                    if self.callbacks and "redimensionar_imagen" in self.callbacks:
                        self.callbacks["redimensionar_imagen"](cursor)

                def borrar_imagen_pos():
                    self.setTextCursor(cursor)
                    if self.callbacks:
                        QTimer.singleShot(10, lambda: self.callbacks["eliminar_nota_obj"]())

                def copiar_img_clipboard():
                    img_name = fmt.name()
                    img_var = self.document().resource(QTextDocument.ResourceType.ImageResource, QUrl(img_name))
                    if isinstance(img_var, (QImage, QPixmap)):
                        QApplication.clipboard().setImage(QImage(img_var))

                def guardar_img_disco():
                    img_name = fmt.name()
                    img_var = self.document().resource(QTextDocument.ResourceType.ImageResource, QUrl(img_name))
                    if isinstance(img_var, (QImage, QPixmap)):
                        dest, _ = QFileDialog.getSaveFileName(self, "Guardar Imagen", "imagen_nota.png", "Imágenes PNG (*.png);;JPG (*.jpg)")
                        if dest:
                            QImage(img_var).save(dest)

                def ver_img_dialogo():
                    img_name = fmt.name()
                    img_var = self.document().resource(QTextDocument.ResourceType.ImageResource, QUrl(img_name))
                    if isinstance(img_var, (QImage, QPixmap)):
                        dlg = QDialog(self)
                        dlg.setWindowTitle("Visualizador de Imagen")
                        dlg.resize(600, 500)
                        dlg_lay = QVBoxLayout(dlg)
                        lbl = QLabel()
                        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        lbl.setPixmap(QPixmap.fromImage(QImage(img_var)))
                        sc = QScrollArea()
                        sc.setWidget(lbl)
                        dlg_lay.addWidget(sc)
                        dlg.exec()

                act_align_left.triggered.connect(lambda: ajustar_img("izquierda"))
                act_align_center.triggered.connect(lambda: ajustar_img("centro"))
                act_align_right.triggered.connect(lambda: ajustar_img("derecha"))
                act_resize.triggered.connect(redim_img)
                act_copy_img.triggered.connect(copiar_img_clipboard)
                act_save_img.triggered.connect(guardar_img_disco)
                act_view_full.triggered.connect(ver_img_dialogo)
                act_del.triggered.connect(borrar_imagen_pos)

            # --- DETECCIÓN DE TABLA ---
            if cursor.currentTable():
                menu.addSeparator()
                m_tab = menu.addMenu("📊 Opciones de Tabla")
                act_add_row_down = m_tab.addAction("➕ Insertar Fila Abajo")
                act_add_row_up = m_tab.addAction("➕ Insertar Fila Arriba")
                act_add_col_right = m_tab.addAction("➕ Insertar Columna a la Derecha")
                act_add_col_left = m_tab.addAction("➕ Insertar Columna a la Izquierda")
                m_tab.addSeparator()
                act_del_row = m_tab.addAction("➖ Eliminar Fila")
                act_del_col = m_tab.addAction("➖ Eliminar Columna")
                m_tab.addSeparator()
                act_cell_color = m_tab.addAction("🎨 Color de Fondo de Celda")
                act_del_table = m_tab.addAction("🗑️ Eliminar Tabla Completa")

                table = cursor.currentTable()
                cell = table.cellAt(cursor)

                def insertar_fila_arriba():
                    table.insertRows(cell.row(), 1)

                def insertar_col_izquierda():
                    table.insertColumns(cell.column(), 1)

                def colorear_celda():
                    col = QColorDialog.getColor(QColor("#2D2D3D"), self, "Color de Celda")
                    if col.isValid():
                        c_fmt = cell.format()
                        c_fmt.setBackground(col)
                        cell.setFormat(c_fmt)

                def borrar_tabla_completa():
                    cursor.setPosition(table.firstPosition() - 1)
                    cursor.setPosition(table.lastPosition() + 1, QTextCursor.MoveMode.KeepAnchor)
                    cursor.removeSelectedText()

                act_add_row_down.triggered.connect(lambda: self.callbacks["agregar_fila"]() if self.callbacks and "agregar_fila" in self.callbacks else table.insertRows(cell.row() + 1, 1))
                act_add_row_up.triggered.connect(insertar_fila_arriba)
                act_add_col_right.triggered.connect(lambda: self.callbacks["agregar_columna"]() if self.callbacks and "agregar_columna" in self.callbacks else table.insertColumns(cell.column() + 1, 1))
                act_add_col_left.triggered.connect(insertar_col_izquierda)
                act_del_row.triggered.connect(lambda: self.callbacks["eliminar_fila"]() if self.callbacks and "eliminar_fila" in self.callbacks else table.removeRows(cell.row(), 1))
                act_del_col.triggered.connect(lambda: self.callbacks["eliminar_columna"]() if self.callbacks and "eliminar_columna" in self.callbacks else table.removeColumns(cell.column(), 1))
                act_cell_color.triggered.connect(colorear_celda)
                act_del_table.triggered.connect(borrar_tabla_completa)
                
            menu.exec(event.globalPos())
        except Exception:
            super().contextMenuEvent(event)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_F:
            if self.callbacks and "toggle_buscar_reemplazar" in self.callbacks:
                self.callbacks["toggle_buscar_reemplazar"]()
                return

        if event.text() == " " or event.key() == Qt.Key.Key_Space:
            cursor = self.textCursor()
            block_text = cursor.block().text()
            if block_text == "-" or block_text == "*":
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                if self.callbacks:
                    self.callbacks["insertar_vineta"]("circulo")
                return
                
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            lista_actual = cursor.currentList()
            if lista_actual:
                if cursor.block().text().strip() == "":
                    lista_actual.remove(cursor.block())
                    fmt = cursor.blockFormat()
                    fmt.setIndent(0)
                    cursor.setBlockFormat(fmt)
                    return
                    
        super().keyPressEvent(event)

    def canInsertFromMimeData(self, source):
        if source.hasImage():
            return True
        if source.hasUrls() and any(u.toLocalFile().lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')) for u in source.urls()):
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage():
            qimg = source.imageData()
            if qimg and self.callbacks and "insertar_imagen_data" in self.callbacks:
                self.callbacks["insertar_imagen_data"](qimg)
                return
        elif source.hasUrls():
            for u in source.urls():
                lf = u.toLocalFile()
                if lf.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    if self.callbacks and "insertar_imagen_archivo" in self.callbacks:
                        self.callbacks["insertar_imagen_archivo"](lf)
                        return
        super().insertFromMimeData(source)

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasImage() or (mime.hasUrls() and any(u.toLocalFile().lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')) for u in mime.urls())):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        mime = event.mimeData()
        if mime.hasImage() or (mime.hasUrls() and any(u.toLocalFile().lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')) for u in mime.urls())):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        mime = event.mimeData()
        cursor = self.cursorForPosition(event.position().toPoint())
        self.setTextCursor(cursor)
        if mime.hasImage():
            qimg = mime.imageData()
            if qimg and self.callbacks and "insertar_imagen_data" in self.callbacks:
                self.callbacks["insertar_imagen_data"](qimg)
                event.acceptProposedAction()
                return
        elif mime.hasUrls():
            for u in mime.urls():
                lf = u.toLocalFile()
                if lf.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    if self.callbacks and "insertar_imagen_archivo" in self.callbacks:
                        self.callbacks["insertar_imagen_archivo"](lf)
                        event.acceptProposedAction()
                        return
        super().dropEvent(event)
