import os
import platform
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QStackedWidget, QTextBrowser
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

from ..utils.highlighter import CodeHighlighter

class FilePreview(QFrame):
    """Panel de vista previa avanzado con modos intercambiables (Edición / Previs / Info)"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "monospace"

        self.highlighter = None
        self.ruta_archivo_actual = None # Para saber qué estamos viendo
        self.inicializar_ui()

    def inicializar_ui(self):
        self.setMinimumWidth(380)
        self.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-left: 1px solid rgba(255,255,255,0.05);")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Cabecera con Selector de Modos (Estilo Cuaderno)
        head = QFrame()
        head.setFixedHeight(36)
        head.setStyleSheet("background: rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.03);")
        h_lay = QHBoxLayout(head)
        h_lay.setContentsMargins(10, 0, 10, 0)
        h_lay.setSpacing(5)
        
        self.btn_view_preview = self._create_mode_btn("👁️ Previa", 0)
        self.btn_view_edit = self._create_mode_btn("📝 Editor", 1)
        self.btn_view_info = self._create_mode_btn("ℹ️ Info", 2)
        
        h_lay.addWidget(self.btn_view_preview)
        h_lay.addWidget(self.btn_view_edit)
        h_lay.addWidget(self.btn_view_info)
        h_lay.addStretch()
        
        # Botón Guardar (Compacto)
        self.btn_save = QPushButton("💾 GUARDAR")
        self.btn_save.setFixedSize(80, 26)
        self.btn_save.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{ 
                background: {self.colores['acento']}; color: white; border-radius: 6px; 
            }}
            QPushButton:hover {{ background: {self.colores['acento']}cc; }}
            QPushButton:disabled {{ background: {self.colores['bg_terciario']}; color: #555; }}
        """)
        self.btn_save.hide()
        self.btn_save.clicked.connect(self.callbacks.get("guardar_archivo"))
        h_lay.addWidget(self.btn_save)
        
        main_layout.addWidget(head)

        # 2. Stacked Widget Central
        self.stack = QStackedWidget()
        
        # Vista 0: Render / Imagen
        self.view_render = QFrame()
        vr_lay = QVBoxLayout(self.view_render)
        self.lbl_image = QLabel("Seleccione un archivo")
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setWordWrap(True)
        self.lbl_image.setStyleSheet(f"color: {self.colores['fg_secundario']}; margin: 20px;")
        
        self.web_preview = QTextBrowser() # Para HTML/MD
        self.web_preview.setStyleSheet("background:transparent; border:none;")
        self.web_preview.hide()
        
        vr_lay.addWidget(self.lbl_image)
        vr_lay.addWidget(self.web_preview)
        self.stack.addWidget(self.view_render)
        
        # Vista 1: Editor de Texto / Código
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont(self.mono_font, 10))
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {self.colores['bg_terciario']};
                color: #C5D1DE; border: none; padding: 8px; font-family: '{self.mono_font}';
            }}
        """)
        self.highlighter = CodeHighlighter(self.text_edit.document(), self.colores)
        self.stack.addWidget(self.text_edit)
        
        # Vista 2: Metadatos Avanzados
        self.view_info = QFrame()
        vi_lay = QVBoxLayout(self.view_info)
        vi_lay.setContentsMargins(15, 15, 15, 15)
        self.lbl_info_title = QLabel("DETALLES DEL ARCHIVO")
        self.lbl_info_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        self.lbl_info_data = QLabel("-")
        self.lbl_info_data.setWordWrap(True)
        self.lbl_info_data.setAlignment(Qt.AlignmentFlag.AlignTop)
        vi_lay.addWidget(self.lbl_info_title)
        vi_lay.addWidget(self.lbl_info_data)
        vi_lay.addStretch()
        self.stack.addWidget(self.view_info)

        # Vista 3: Estado Vacío / Por Defecto (Sin selección)
        self.view_vacio = QFrame()
        vv_lay = QVBoxLayout(self.view_vacio)
        vv_lay.setContentsMargins(20, 24, 20, 16)
        vv_lay.setSpacing(10)
        vv_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_vacio_ico = QLabel("📁")
        lbl_vacio_ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_vacio_ico.setFont(QFont(self.font_family, 36))
        vv_lay.addWidget(lbl_vacio_ico)

        self.lbl_vacio_titulo = QLabel("Explorador de Archivos")
        self.lbl_vacio_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vacio_titulo.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        self.lbl_vacio_titulo.setStyleSheet("color: white;")
        vv_lay.addWidget(self.lbl_vacio_titulo)

        self.lbl_vacio_desc = QLabel("Selecciona un elemento de la lista para previsualizar imágenes, editar código o consultar sus propiedades.")
        self.lbl_vacio_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vacio_desc.setWordWrap(True)
        self.lbl_vacio_desc.setFont(QFont(self.font_family, 9))
        self.lbl_vacio_desc.setStyleSheet(f"color: {self.colores['fg_secundario']}; line-height: 1.4;")
        vv_lay.addWidget(self.lbl_vacio_desc)

        vv_lay.addSpacing(6)

        actions_box = QFrame()
        actions_box.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        a_lay = QVBoxLayout(actions_box)
        a_lay.setSpacing(6)
        a_lay.setContentsMargins(8, 8, 8, 8)

        lbl_act_tit = QLabel("ACCIONES RÁPIDAS")
        lbl_act_tit.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_act_tit.setStyleSheet(f"color: {self.colores['acento']}; letter-spacing: 1px;")
        a_lay.addWidget(lbl_act_tit)

        def _crear_btn_accion(texto, cb_key, is_cmd=False):
            btn = QPushButton(texto)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont(self.font_family, 8, QFont.Weight.Medium))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores['bg_terciario']};
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 6px;
                    text-align: left;
                    padding-left: 10px;
                }}
                QPushButton:hover {{
                    background: {self.colores['acento']}25;
                    border-color: {self.colores['acento']}66;
                    color: {self.colores['acento']};
                }}
            """)
            if is_cmd:
                btn.clicked.connect(lambda: self.callbacks.get("ejecutar_comando_ruta", lambda x: None)("cmd"))
            else:
                btn.clicked.connect(lambda: self.callbacks.get(cb_key, lambda: None)())
            return btn

        a_lay.addWidget(_crear_btn_accion("📄  Nuevo Archivo", "nuevo_archivo"))
        a_lay.addWidget(_crear_btn_accion("📁  Nueva Carpeta", "nueva_carpeta"))
        a_lay.addWidget(_crear_btn_accion("⚡  Abrir Terminal (CMD)", "cmd", is_cmd=True))
        vv_lay.addWidget(actions_box)

        tip_box = QLabel("💡 <b>Atajos:</b> [Esc] Deseleccionar • [F5] Refrescar • Clic en espacio vacío de la barra para editar ruta")
        tip_box.setFont(QFont(self.font_family, 8))
        tip_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip_box.setWordWrap(True)
        tip_box.setStyleSheet(f"color: {self.colores['fg_secundario']}; background: transparent; padding: 4px;")
        vv_lay.addWidget(tip_box)

        vv_lay.addStretch()
        self.stack.addWidget(self.view_vacio)
        
        main_layout.addWidget(self.stack)

        # 3. Footer de Metadata (Fijo)
        self.footer = QFrame()
        self.footer.setStyleSheet(f"background: rgba(0,0,0,0.1); border-top: 1px solid rgba(255,255,255,0.03);")
        f_lay = QVBoxLayout(self.footer)
        f_lay.setContentsMargins(20, 8, 20, 8)
        
        self.lbl_name_footer = QLabel("-")
        self.lbl_name_footer.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_name_footer.setStyleSheet("color: white;")
        f_lay.addWidget(self.lbl_name_footer)
        
        self.lbl_size_footer = QLabel("-")
        self.lbl_size_footer.setFont(QFont(self.font_family, 8))
        self.lbl_size_footer.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        f_lay.addWidget(self.lbl_size_footer)
        
        main_layout.addWidget(self.footer)

        # Cargar estado inicial vacío
        self.limpiar()

    def _create_mode_btn(self, text, index):
        btn = QPushButton(text)
        btn.setCheckable(True)
        if index == 0: btn.setChecked(True)
        btn.setFixedHeight(26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background:transparent; color:{self.colores['fg_secundario']}; border-radius:4px; padding:0 10px; font-weight:bold; font-size:9px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.05); color:white; }}
            QPushButton:checked {{ background: {self.colores['bg_terciario']}; color: {self.colores['acento']}; border: 1px solid {self.colores['acento']}44; }}
        """)
        btn.clicked.connect(lambda: self._on_mode_clicked(index))
        return btn

    def _on_mode_clicked(self, index):
        self.btn_view_preview.setChecked(index == 0)
        self.btn_view_edit.setChecked(index == 1)
        self.btn_view_info.setChecked(index == 2)
        self.stack.setCurrentIndex(index)
        
        # Mostrar botón de guardar solo si hay edición
        self.btn_save.setVisible(index == 1 and not self.text_edit.isReadOnly())

    def mostrar_imagen(self, image_path):
        self.ruta_archivo_actual = image_path
        pixmap = QPixmap(image_path)
        self.lbl_image.setPixmap(pixmap.scaled(
            350, 350, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))
        self.lbl_image.setText("")
        self.lbl_image.show()
        self.web_preview.hide()
        
        name = os.path.basename(image_path)
        size = self._get_size_str(image_path)
        self.lbl_name_footer.setText(name)
        self.lbl_size_footer.setText(f"Imagen • {pixmap.width()}x{pixmap.height()} px • {size}")
        self.lbl_info_data.setText(f"Ruta: {image_path}\nDimensiones: {pixmap.width()}x{pixmap.height()}\nTamaño: {size}")
        
        self._on_mode_clicked(0) # Forzar vista previa

    def mostrar_texto(self, content, name, editable=False):
        self.text_edit.setPlainText(content)
        self.text_edit.setReadOnly(not editable)
        self.lbl_name_footer.setText(name)
        self.lbl_size_footer.setText("Editor de Texto" if editable else "Archivo de Código / Lectura")
        self.lbl_info_data.setText(f"Archivo: {name}\nEstado: {'Editable' if editable else 'Solo lectura'}")
        
        # Si es HTML o Markdown, mostrar render en 'Previa'
        if name.lower().endswith(('.html', '.htm')):
            self.lbl_image.hide()
            self.web_preview.setHtml(content)
            self.web_preview.show()
        else:
            self.lbl_image.setText(f"Archivo de texto: {name}\nUse la pestaña 'Editor' para leer el contenido.")
            self.lbl_image.show()
            self.web_preview.hide()

        self._on_mode_clicked(1 if editable else 0)

    def mostrar_info_general(self, name, details):
        self.lbl_name_footer.setText(name)
        self.lbl_size_footer.setText(details)
        self.lbl_info_data.setText(details)
        self._on_mode_clicked(2)

    def _get_size_str(self, path):
        try:
            size = os.path.getsize(path)
            for u in ['B', 'KB', 'MB', 'GB']:
                if size < 1024: return f"{size:.1f} {u}"
                size /= 1024
        except: return "--"

    def limpiar(self):
        self.ruta_archivo_actual = None
        self.lbl_image.clear()
        self.lbl_image.setText("Seleccione un archivo")
        self.web_preview.clear()
        self.text_edit.clear()
        self.lbl_name_footer.setText("Ningún archivo seleccionado")
        self.lbl_size_footer.setText("Listo para explorar")
        self.lbl_info_data.setText("-")
        self.btn_save.hide()
        self.btn_view_preview.setChecked(False)
        self.btn_view_edit.setChecked(False)
        self.btn_view_info.setChecked(False)
        self.stack.setCurrentIndex(3)

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-left: 1px solid rgba(255,255,255,0.05);")
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {self.colores['bg_terciario']};
                color: #C5D1DE; border: none; padding: 8px; font-family: '{self.mono_font}';
            }}
        """)
        if self.highlighter:
            self.highlighter.actualizar_colores(colores)
