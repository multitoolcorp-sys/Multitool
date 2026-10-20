"""
gui_notas.py - Interfaz gráfica principal del módulo de Notas Pro
"""
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QSplitter, QComboBox, QToolButton, 
    QMenu, QFrame, QLineEdit,
    QListWidget, QPushButton, QMessageBox, QScrollArea, QSizePolicy,
    QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QShortcut, QKeySequence

from vistas.modulos.notas.utils.editor_components import FindReplaceWidget, NotesEditor


class NotasGUI(QWidget):
    """Interfaz principal del módulo de Notas Pro"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.inicializar_ui()

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{ background-color: rgba(255,255,255,0.05); }}
            QSplitter::handle:horizontal {{ width: 1px; }}
        """)
        
        # --- PANEL LISTA (IZQUIERDA) ---
        self.panel_izq = QFrame()
        self.panel_izq.setMinimumWidth(220)
        self.panel_izq.setMaximumWidth(320)
        self.panel_izq.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; border-right: 1px solid rgba(255,255,255,0.05);")
        layout_izq = QVBoxLayout(self.panel_izq)
        layout_izq.setContentsMargins(12, 14, 12, 14)
        layout_izq.setSpacing(8)
        
        lbl_notas = QLabel("BIBLIOTECA")
        lbl_notas.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_notas.setStyleSheet(f"color: {self.colores['acento']}; ")
        layout_izq.addWidget(lbl_notas)
        
        # Búsqueda
        self.txt_busqueda = QLineEdit()
        self.txt_busqueda.setPlaceholderText("Buscar en mis notas...")
        self.txt_busqueda.setMinimumHeight(32)
        self.txt_busqueda.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_terciario']};
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 6px; padding: 0 10px; color: white;
            }}
            QLineEdit:focus {{ border-color: {self.colores['acento']}; }}
        """)
        self.txt_busqueda.textChanged.connect(self.callbacks["filtrar_notas"])
        layout_izq.addWidget(self.txt_busqueda)
        
        btn_search_content = QPushButton("🔍 Búsqueda profunda")
        btn_search_content.setFont(QFont(self.font_family, 8, QFont.Weight.Medium))
        btn_search_content.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search_content.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; color: {self.colores['fg_secundario']}; 
                border: 1px dashed rgba(255,255,255,0.1); border-radius: 6px; padding: 4px;
            }}
            QPushButton:hover {{ color: white; border-color: {self.colores['acento']}; }}
        """)
        btn_search_content.clicked.connect(self.callbacks["buscar_en_contenido"])
        layout_izq.addWidget(btn_search_content)

        # Barra de Etiquetas (Tags)
        self._crear_barra_tags(layout_izq)
        
        # Botones Nueva, Importar y Eliminar Nota
        row_btn_top = QHBoxLayout()
        row_btn_top.setSpacing(6)
        
        self.btn_nueva = QPushButton("➕ Nueva")
        self.btn_nueva.setFixedHeight(32)
        self.btn_nueva.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nueva.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']}; color: white; border-radius: 6px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        self.btn_nueva.clicked.connect(self.callbacks["nueva_nota"])

        self.btn_importar = QPushButton("📥")
        self.btn_importar.setFixedSize(32, 32)
        self.btn_importar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_importar.setToolTip("Importar Notas (.md, .txt, .html)")
        self.btn_importar.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); }
        """)
        if "importar_notas" in self.callbacks:
            self.btn_importar.clicked.connect(self.callbacks["importar_notas"])
        
        self.btn_eliminar = QPushButton("🗑️")
        self.btn_eliminar.setFixedSize(32, 32)
        self.btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eliminar.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05); color: #F87171; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);
            }
            QPushButton:hover { background: rgba(248,113,113,0.1); border-color: #F87171; }
        """)
        self.btn_eliminar.setToolTip("Mover nota seleccionada a la Papelera")
        self.btn_eliminar.clicked.connect(self.callbacks["eliminar_nota"])
        
        row_btn_top.addWidget(self.btn_nueva, 1)
        row_btn_top.addWidget(self.btn_importar)
        row_btn_top.addWidget(self.btn_eliminar)
        layout_izq.addLayout(row_btn_top)
        
        # Lista de notas
        self.list_notas = QListWidget()
        self.list_notas.setSpacing(5)
        self.list_notas.setStyleSheet(f"""
            QListWidget {{
                background: transparent; border: none; outline: none;
            }}
            QListWidget::item {{
                background: {self.colores['bg_terciario']}; color: white;
                border-radius: 6px; padding: 10px; border: 1px solid transparent;
            }}
            QListWidget::item:hover {{
                border-color: {self.colores['acento']}44;
            }}
            QListWidget::item:selected {{
                background: {self.colores['acento']}; color: white;
            }}
        """)
        self.list_notas.itemSelectionChanged.connect(self.callbacks["seleccionar_nota"])
        layout_izq.addWidget(self.list_notas)
        
        self.splitter.addWidget(self.panel_izq)
        
        # --- PANEL DERECHO CON STACKED WIDGET (Vacío / Editor) ---
        self.panel_der = QFrame()
        self.panel_der.setStyleSheet(f"background-color: {self.colores['bg_principal']};")
        layout_panel_der = QVBoxLayout(self.panel_der)
        layout_panel_der.setContentsMargins(0, 0, 0, 0)
        layout_panel_der.setSpacing(0)

        self.stack_der = QStackedWidget(self.panel_der)
        layout_panel_der.addWidget(self.stack_der)

        # ── PÁGINA 0: ESTADO VACÍO (WhatsApp Web style) ──
        self.widget_vacio = QWidget()
        v_layout = QVBoxLayout(self.widget_vacio)
        v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.setContentsMargins(40, 40, 40, 40)
        v_layout.setSpacing(14)

        ico_empty = QLabel("📝")
        ico_empty.setFont(QFont("Segoe UI Emoji", 50))
        ico_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico_empty.setStyleSheet("background: transparent; color: rgba(255,255,255,0.2);")
        v_layout.addWidget(ico_empty)

        lbl_tit_empty = QLabel("Mis Notas MultiTool")
        lbl_tit_empty.setFont(QFont(self.font_family, 18, QFont.Weight.Bold))
        lbl_tit_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_tit_empty.setStyleSheet(f"color: {self.colores['fg_principal']};")
        v_layout.addWidget(lbl_tit_empty)

        lbl_sub_empty = QLabel("Selecciona una nota de la biblioteca para leer o editar, o crea una nueva para empezar a redactar.")
        lbl_sub_empty.setFont(QFont(self.font_family, 11))
        lbl_sub_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub_empty.setWordWrap(True)
        lbl_sub_empty.setStyleSheet(f"color: {self.colores['fg_secundario']}; max-width: 480px;")
        v_layout.addWidget(lbl_sub_empty)

        row_quick = QHBoxLayout()
        row_quick.setSpacing(12)
        row_quick.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_q_new = QPushButton("➕ Crear Nota")
        btn_q_new.setFixedHeight(36)
        btn_q_new.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_q_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_new.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']}; color: white; border-radius: 8px; padding: 0 20px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_q_new.clicked.connect(self.callbacks["nueva_nota"])
        row_quick.addWidget(btn_q_new)

        btn_q_imp = QPushButton("📥 Importar Archivo")
        btn_q_imp.setFixedHeight(36)
        btn_q_imp.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_q_imp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_imp.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.06); color: white; border-radius: 8px; padding: 0 16px; border: 1px solid rgba(255,255,255,0.1);
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.12); }}
        """)
        if "importar_notas" in self.callbacks:
            btn_q_imp.clicked.connect(self.callbacks["importar_notas"])
        row_quick.addWidget(btn_q_imp)

        btn_q_tpl = QPushButton("📋 Plantillas")
        btn_q_tpl.setFixedHeight(36)
        btn_q_tpl.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_q_tpl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_q_tpl.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.06); color: #FBBF24; border-radius: 8px; padding: 0 16px; border: 1px solid rgba(251,191,36,0.3);
            }}
            QPushButton:hover {{ background: rgba(251,191,36,0.15); }}
        """)
        if "ir_a_plantillas" in self.callbacks:
            btn_q_tpl.clicked.connect(self.callbacks["ir_a_plantillas"])
        row_quick.addWidget(btn_q_tpl)

        v_layout.addLayout(row_quick)

        lbl_esc_hint = QLabel("💡 Presiona la tecla Esc para deseleccionar y volver a esta pantalla")
        lbl_esc_hint.setFont(QFont(self.font_family, 9))
        lbl_esc_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_esc_hint.setStyleSheet("color: rgba(255,255,255,0.35); margin-top: 15px;")
        v_layout.addWidget(lbl_esc_hint)

        self.stack_der.addWidget(self.widget_vacio)

        # ── PÁGINA 1: EDITOR COMPLETO (Header, Toolbar, Editor, Footer) ──
        self.widget_editor = QWidget()
        layout_der = QVBoxLayout(self.widget_editor)
        layout_der.setContentsMargins(0, 0, 0, 0)
        layout_der.setSpacing(0)

        # Header Editor
        header_ed = QFrame()
        header_ed.setFixedHeight(48)
        header_ed.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-bottom: 1px solid rgba(255,255,255,0.05);")
        he_layout = QHBoxLayout(header_ed)
        he_layout.setContentsMargins(15, 0, 15, 0)
        he_layout.setSpacing(10)
        
        self.btn_fijar = QToolButton()
        self.btn_fijar.setText("📌")
        self.btn_fijar.setCheckable(True)
        self.btn_fijar.setFixedSize(32, 32)
        self.btn_fijar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fijar.setStyleSheet(f"""
            QToolButton {{ 
                background: transparent; color: {self.colores['fg_secundario']}; font-size: 16px; border-radius: 16px;
            }} 
            QToolButton:hover {{ background: rgba(255,255,255,0.05); }}
            QToolButton:checked {{ color: {self.colores['advertencia']}; }}
        """)
        self.btn_fijar.clicked.connect(self.callbacks["toggle_fijar"])
        he_layout.addWidget(self.btn_fijar)

        self.txt_titulo = QLineEdit()
        self.txt_titulo.setPlaceholderText("Sin título...")
        self.txt_titulo.setFont(QFont(self.font_family, 14, QFont.Weight.Bold))
        self.txt_titulo.setStyleSheet("background: transparent; border: none; color: white; padding: 5px 0;")
        self.txt_titulo.editingFinished.connect(self.callbacks["actualizar_titulo"])
        he_layout.addWidget(self.txt_titulo, 1)

        self.btn_favorito = QToolButton()
        self.btn_favorito.setText("★")
        self.btn_favorito.setCheckable(True)
        self.btn_favorito.setFixedSize(32, 32)
        self.btn_favorito.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_favorito.setStyleSheet(f"""
            QToolButton {{ 
                background: transparent; color: {self.colores['fg_secundario']}; font-size: 16px; border-radius: 16px;
            }} 
            QToolButton:hover {{ background: rgba(255,255,255,0.05); }}
            QToolButton:checked {{ color: {self.colores['advertencia']}; }}
        """)
        self.btn_favorito.clicked.connect(self.callbacks["toggle_favorito"])
        he_layout.addWidget(self.btn_favorito)

        self.btn_proteger = QPushButton("🔒")
        self.btn_proteger.setFixedSize(30, 30)
        self.btn_proteger.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_proteger.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        self.btn_proteger.setToolTip("Proteger / Desproteger nota con PIN")
        if "proteger_nota" in self.callbacks:
            self.btn_proteger.clicked.connect(self.callbacks["proteger_nota"])
        he_layout.addWidget(self.btn_proteger)

        self.btn_enfoque = QPushButton("🧘")
        self.btn_enfoque.setFixedSize(30, 30)
        self.btn_enfoque.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_enfoque.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        self.btn_enfoque.setToolTip("Modo Enfoque / Escritura sin distracciones")
        self.btn_enfoque.clicked.connect(self._toggle_modo_enfoque)
        he_layout.addWidget(self.btn_enfoque)

        self.btn_tts = QPushButton("🔊")
        self.btn_tts.setFixedSize(30, 30)
        self.btn_tts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tts.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        self.btn_tts.setToolTip("Leer Nota en Voz Alta (TTS)")
        self.btn_tts.clicked.connect(self._leer_nota_tts)
        he_layout.addWidget(self.btn_tts)

        self.btn_snapshots = QPushButton("🕒")
        self.btn_snapshots.setFixedSize(30, 30)
        self.btn_snapshots.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_snapshots.setStyleSheet("background: rgba(255,255,255,0.05); color: #60A5FA; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        self.btn_snapshots.setToolTip("Historial de Versiones / Snapshots")
        if "mostrar_snapshots" in self.callbacks:
            self.btn_snapshots.clicked.connect(self.callbacks["mostrar_snapshots"])
        he_layout.addWidget(self.btn_snapshots)

        self.btn_plantilla = QPushButton("📋")
        self.btn_plantilla.setFixedSize(30, 30)
        self.btn_plantilla.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plantilla.setStyleSheet("background: rgba(255,255,255,0.05); color: #FBBF24; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        self.btn_plantilla.setToolTip("Guardar nota actual como Plantilla personalizada")
        if "guardar_como_plantilla" in self.callbacks:
            self.btn_plantilla.clicked.connect(self.callbacks["guardar_como_plantilla"])
        he_layout.addWidget(self.btn_plantilla)

        self.btn_export_pdf = QPushButton("📄")
        self.btn_export_pdf.setFixedSize(30, 30)
        self.btn_export_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_pdf.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        self.btn_export_pdf.setToolTip("Exportar a PDF")
        self.btn_export_pdf.clicked.connect(self.callbacks["exportar_pdf"])
        he_layout.addWidget(self.btn_export_pdf)

        self.btn_export_md = QPushButton("📝")
        self.btn_export_md.setFixedSize(30, 30)
        self.btn_export_md.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_md.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        self.btn_export_md.setToolTip("Exportar a Markdown (.md)")
        self.btn_export_md.clicked.connect(self.callbacks["exportar_markdown"])
        he_layout.addWidget(self.btn_export_md)

        self.btn_export_txt = QPushButton("📃")
        self.btn_export_txt.setFixedSize(30, 30)
        self.btn_export_txt.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_txt.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        self.btn_export_txt.setToolTip("Exportar a Texto plano (.txt)")
        self.btn_export_txt.clicked.connect(self.callbacks["exportar_txt"])
        he_layout.addWidget(self.btn_export_txt)

        self.btn_guardar = QPushButton("💾 Guardar")
        self.btn_guardar.setFixedHeight(30)
        self.btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guardar.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px; border: none; padding: 0 12px; font-weight: bold;")
        self.btn_guardar.setToolTip("Guardar nota ahora")
        self.btn_guardar.clicked.connect(self.callbacks["guardar_nota"])
        he_layout.addWidget(self.btn_guardar)
        
        layout_der.addWidget(header_ed)
        
        # BARRA DE HERRAMIENTAS PREMIUM
        toolbar = QFrame()
        toolbar.setFixedHeight(42)
        toolbar.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-bottom: 1px solid rgba(255,255,255,0.02);")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 0, 12, 0)
        tb_layout.setSpacing(4)
        
        # Deshacer / Rehacer
        btn_undo = QPushButton("↩️")
        btn_undo.setFixedSize(28, 28)
        btn_undo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_undo.setToolTip("Deshacer (Ctrl+Z)")
        btn_undo.setStyleSheet("background: rgba(0,0,0,0.2); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        if "deshacer" in self.callbacks:
            btn_undo.clicked.connect(self.callbacks["deshacer"])
        else:
            btn_undo.clicked.connect(lambda: self.editor.undo())

        btn_redo = QPushButton("↪️")
        btn_redo.setFixedSize(28, 28)
        btn_redo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_redo.setToolTip("Rehacer (Ctrl+Y)")
        btn_redo.setStyleSheet("background: rgba(0,0,0,0.2); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        if "rehacer" in self.callbacks:
            btn_redo.clicked.connect(self.callbacks["rehacer"])
        else:
            btn_redo.clicked.connect(lambda: self.editor.redo())

        tb_layout.addWidget(btn_undo)
        tb_layout.addWidget(btn_redo)

        div0 = QFrame(); div0.setFixedSize(1, 18); div0.setStyleSheet("background: rgba(255,255,255,0.1);")
        tb_layout.addWidget(div0)

        # Selector de Encabezados (H1, H2, H3, Párrafo, Cita)
        self.combo_heading = QComboBox()
        self.combo_heading.addItems(["Párrafo", "Título 1", "Título 2", "Título 3", "Cita"])
        self.combo_heading.setMinimumWidth(85)
        self.combo_heading.setStyleSheet(f"""
            QComboBox {{ 
                background: rgba(0,0,0,0.2); color: white; border-radius: 6px; padding: 2px 6px; border: 1px solid rgba(255,255,255,0.05); font-size: 11px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        self.combo_heading.activated.connect(self._on_heading_changed)
        tb_layout.addWidget(self.combo_heading)

        # Formatos básicos
        self.btn_negrita = self._crear_btn_tb("B", "negrita")
        self.btn_cursiva = self._crear_btn_tb("I", "cursiva", italic=True)
        self.btn_subrayado = self._crear_btn_tb("U", "subrayado", underline=True)
        self.btn_tachado = self._crear_btn_tb("S", "tachado", strikeout=True)
        
        btn_super = QPushButton("X²")
        btn_super.setFixedSize(28, 28)
        btn_super.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_super.setToolTip("Superíndice (X²)")
        btn_super.setStyleSheet("background: rgba(0,0,0,0.2); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); font-weight: bold; font-size: 10px;")
        if "aplicar_superindice" in self.callbacks:
            btn_super.clicked.connect(self.callbacks["aplicar_superindice"])

        btn_sub = QPushButton("X₂")
        btn_sub.setFixedSize(28, 28)
        btn_sub.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sub.setToolTip("Subíndice (X₂)")
        btn_sub.setStyleSheet("background: rgba(0,0,0,0.2); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); font-weight: bold; font-size: 10px;")
        if "aplicar_subindice" in self.callbacks:
            btn_sub.clicked.connect(self.callbacks["aplicar_subindice"])

        btn_clean = QPushButton("🧹")
        btn_clean.setFixedSize(28, 28)
        btn_clean.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clean.setToolTip("Limpiar Formato")
        btn_clean.setStyleSheet("background: rgba(0,0,0,0.2); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        if "limpiar_formato" in self.callbacks:
            btn_clean.clicked.connect(self.callbacks["limpiar_formato"])

        btn_code = QPushButton("💻")
        btn_code.setFixedSize(28, 28)
        btn_code.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_code.setToolTip("Bloque de Código Monospace")
        btn_code.setStyleSheet("background: rgba(0,0,0,0.2); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        if "insertar_bloque_codigo" in self.callbacks:
            btn_code.clicked.connect(self.callbacks["insertar_bloque_codigo"])
        
        tb_layout.addWidget(self.btn_negrita); tb_layout.addWidget(self.btn_cursiva)
        tb_layout.addWidget(self.btn_subrayado); tb_layout.addWidget(self.btn_tachado)
        tb_layout.addWidget(btn_super); tb_layout.addWidget(btn_sub)
        tb_layout.addWidget(btn_clean); tb_layout.addWidget(btn_code)
        
        divider = QFrame(); divider.setFixedSize(1, 18); divider.setStyleSheet("background: rgba(255,255,255,0.1);")
        tb_layout.addWidget(divider)
        
        # Selector de Fuentes, Tamaño y Color
        self.combo_font = QComboBox()
        self.combo_font.addItems(["Segoe UI", "Inter", "Arial", "Georgia", "Courier New", "Times New Roman", "Verdana", "Consolas"])
        self.combo_font.setCurrentText(self.font_family)
        self.combo_font.setMinimumWidth(100)
        self.combo_font.setStyleSheet(f"""
            QComboBox {{ 
                background: rgba(0,0,0,0.2); color: white; border-radius: 6px; padding: 2px 6px; border: 1px solid rgba(255,255,255,0.05); font-size: 11px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        self.combo_font.currentTextChanged.connect(self.callbacks["cambiar_familia_fuente"])
        tb_layout.addWidget(self.combo_font)
 
        self.combo_size = QComboBox()
        self.combo_size.addItems(["8", "10", "11", "12", "14", "16", "18", "24", "32", "48"])
        self.combo_size.setCurrentText("12")
        self.combo_size.setMinimumWidth(48)
        self.combo_size.setStyleSheet(f"""
            QComboBox {{ 
                background: rgba(0,0,0,0.2); color: white; border-radius: 6px; padding: 2px 6px; border: 1px solid rgba(255,255,255,0.05); font-size: 11px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        self.combo_size.currentTextChanged.connect(self.callbacks["cambiar_tamano_fuente"])
        tb_layout.addWidget(self.combo_size)
        
        btn_color = QPushButton("🎨")
        btn_color.setFixedSize(28, 28)
        btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_color.setStyleSheet(f"background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px;")
        btn_color.setToolTip("Color de texto (Paleta rápida)")
        btn_color.clicked.connect(self._mostrar_paleta_color)
        tb_layout.addWidget(btn_color)
 
        btn_highlight = QPushButton("🟨")
        btn_highlight.setFixedSize(28, 28)
        btn_highlight.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_highlight.setStyleSheet(f"background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px;")
        btn_highlight.setToolTip("Resaltar texto")
        btn_highlight.clicked.connect(self.callbacks["cambiar_color_fondo"])
        tb_layout.addWidget(btn_highlight)
        
        div2 = QFrame(); div2.setFixedSize(1, 18); div2.setStyleSheet("background: rgba(255,255,255,0.1);")
        tb_layout.addWidget(div2)

        # Checklists, Separador, Enlace
        btn_chk = QPushButton("☑️")
        btn_chk.setFixedSize(28, 28)
        btn_chk.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_chk.setStyleSheet("background: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        btn_chk.setToolTip("Insertar casilla de verificación (Checklist)")
        if "insertar_checklist" in self.callbacks:
            btn_chk.clicked.connect(self.callbacks["insertar_checklist"])
        tb_layout.addWidget(btn_chk)

        btn_sep = QPushButton("➖")
        btn_sep.setFixedSize(28, 28)
        btn_sep.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sep.setStyleSheet("background: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        btn_sep.setToolTip("Insertar línea separadora")
        if "insertar_separador" in self.callbacks:
            btn_sep.clicked.connect(self.callbacks["insertar_separador"])
        tb_layout.addWidget(btn_sep)

        btn_link = QPushButton("🔗")
        btn_link.setFixedSize(28, 28)
        btn_link.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_link.setStyleSheet("background: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        btn_link.setToolTip("Insertar hipervínculo")
        if "insertar_enlace" in self.callbacks:
            btn_link.clicked.connect(self.callbacks["insertar_enlace"])
        tb_layout.addWidget(btn_link)

        # Insertables
        btn_img = QPushButton("🖼️")
        btn_img.setFixedSize(28, 28)
        btn_img.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_img.setStyleSheet("background: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        btn_img.setToolTip("Insertar imagen")
        btn_img.clicked.connect(self.callbacks["insertar_imagen"])
        tb_layout.addWidget(btn_img)
        
        btn_tab = QPushButton("📅")
        btn_tab.setFixedSize(28, 28)
        btn_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_tab.setStyleSheet("background: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        btn_tab.setToolTip("Insertar tabla")
        btn_tab.clicked.connect(self.callbacks["insertar_tabla"])
        tb_layout.addWidget(btn_tab)
        
        btn_listas = QPushButton("≡")
        btn_listas.setFixedSize(28, 28)
        btn_listas.setCursor(Qt.CursorShape.PointingHandCursor)
        m_listas = QMenu(self)
        m_listas.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border: 1px solid rgba(255,255,255,0.1);")
        for t in ["punto", "circulo", "cuadrado", "flecha", "check"]:
            act = m_listas.addAction(t.capitalize())
            act.triggered.connect(lambda ch, t=t: self.callbacks["insertar_vineta"](t))
        btn_listas.setMenu(m_listas)
        btn_listas.setStyleSheet("QPushButton { background: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); } QPushButton::menu-indicator { image: none; }")
        tb_layout.addWidget(btn_listas)
 
        btn_tema = QPushButton("🗒️")
        btn_tema.setFixedSize(28, 28)
        btn_tema.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_tema.setToolTip("Fondo del papel (Post-it)")
        m_temas = QMenu(self)
        m_temas.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border: 1px solid rgba(255,255,255,0.1);")
        temas_opciones = [
            ("default", "Por defecto"),
            ("yellow", "Post-it Amarillo 🟨"),
            ("blue", "Post-it Azul 🟦"),
            ("green", "Post-it Verde 🟩"),
            ("purple", "Post-it Morado 🟪")
        ]
        for t_id, t_name in temas_opciones:
            act = m_temas.addAction(t_name)
            act.triggered.connect(lambda ch, tid=t_id: self.callbacks["cambiar_pastel_fondo"](tid))
        btn_tema.setMenu(m_temas)
        btn_tema.setStyleSheet("QPushButton { background: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); } QPushButton::menu-indicator { image: none; }")
        tb_layout.addWidget(btn_tema)
        
        tb_layout.addStretch()

        # Alineaciones
        for align_icon, align_type, align_tip in [
            ("⇤", Qt.AlignmentFlag.AlignLeft, "Alinear a la izquierda"),
            ("↔", Qt.AlignmentFlag.AlignCenter, "Centrar texto"),
            ("⇥", Qt.AlignmentFlag.AlignRight, "Alinear a la derecha"),
            ("☰", Qt.AlignmentFlag.AlignJustify, "Justificar texto")
        ]:
            btn_align = QPushButton(align_icon)
            btn_align.setFixedSize(28, 28)
            btn_align.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_align.setToolTip(align_tip)
            btn_align.setStyleSheet("background: rgba(255,255,255,0.05); color: white; border-radius: 4px; border: none; font-size: 13px;")
            btn_align.clicked.connect(lambda ch, a=align_type: self.editor.setAlignment(a))
            tb_layout.addWidget(btn_align)

        layout_der.addWidget(toolbar)

        # Buscador Flotante
        self.find_replace_bar = FindReplaceWidget(
            self, 
            callback_find=self.callbacks.get("buscar_texto"),
            callback_replace=self.callbacks.get("reemplazar_texto"),
            callback_replace_all=self.callbacks.get("reemplazar_todo_texto"),
            colors=self.colores
        )
        self.find_replace_bar.hide()
        layout_der.addWidget(self.find_replace_bar)
        
        # Editor
        self.editor = NotesEditor(self, callbacks=self.callbacks)
        self.editor.setFont(QFont(self.font_family, 12))
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background: {self.colores['bg_principal']}; color: {self.colores['fg_principal']}; 
                padding: 15px 25px; border: none; selection-background-color: {self.colores['acento']}44;
            }}
        """)
        self.editor.setViewportMargins(0, 0, 0, 0)
        self.editor.textChanged.connect(self.callbacks["actualizar_contenido"])
        self.editor.cursorPositionChanged.connect(self.callbacks["actualizar_estado_formato"])
        layout_der.addWidget(self.editor, 1)
        
        # Footer Informativo
        footer = QFrame()
        footer.setFixedHeight(28)
        footer.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-top: 1px solid rgba(255,255,255,0.02);")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(15, 0, 15, 0)
        
        self.lbl_stats = QLabel("Palabras: 0 | Caracteres: 0 | Tiempo estimado: 0 min")
        self.lbl_stats.setFont(QFont(self.font_family, 8))
        self.lbl_stats.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        f_layout.addWidget(self.lbl_stats, 1)
        
        self.lbl_status = QLabel("Lista para escribir...")
        self.lbl_status.setFont(QFont(self.font_family, 8, QFont.Weight.Medium))
        self.lbl_status.setStyleSheet(f"color: {self.colores['acento']}; font-style: italic;")
        f_layout.addWidget(self.lbl_status)
        
        layout_der.addWidget(footer)
        self.stack_der.addWidget(self.widget_editor)
        self.stack_der.setCurrentIndex(0)

        # Atajo de teclado Esc para deseleccionar nota y volver a pantalla de espera
        self.shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_esc.activated.connect(self._on_esc_pressed)
        
        self.splitter.addWidget(self.panel_der)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([260, 740])
        self.main_layout.addWidget(self.splitter)

    def _on_esc_pressed(self):
        """Manejador al presionar Esc: deselecciona la nota y muestra la pantalla de espera"""
        if "deseleccionar_nota" in self.callbacks:
            self.callbacks["deseleccionar_nota"]()
        else:
            self.list_notas.clearSelection()
            self.mostrar_editor(False)

    def deseleccionar_nota(self):
        """Alias para deseleccionar nota"""
        self._on_esc_pressed()

    def mostrar_editor(self, habilitado=True):
        """Alterna entre la pantalla de espera (vacía) y el editor de notas"""
        if hasattr(self, "stack_der"):
            self.stack_der.setCurrentIndex(1 if habilitado else 0)

    def _toggle_modo_enfoque(self):
        is_visible = self.panel_izq.isVisible()
        self.panel_izq.setVisible(not is_visible)
        if is_visible:
            self.lbl_status.setText("🧘 Modo Enfoque Activo")
        else:
            self.lbl_status.setText("Lista para escribir...")

    def _leer_nota_tts(self):
        txt = self.editor.toPlainText().strip()
        if not txt:
            QMessageBox.information(self, "Lector TTS", "La nota está vacía.")
            return
        try:
            from PyQt6.QtTextToSpeech import QTextToSpeech
            if not hasattr(self, "_tts") or self._tts is None:
                self._tts = QTextToSpeech(self)
            self._tts.say(txt[:1000])
        except Exception:
            QMessageBox.information(self, "Lector TTS", f"Lectura de Nota:\n\n{txt[:400]}...")

    def _crear_btn_tb(self, text, tipo, italic=False, underline=False, strikeout=False):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        font = QFont(self.font_family, 9, QFont.Weight.Bold)
        if italic: font.setItalic(True)
        if underline: font.setUnderline(True)
        if strikeout: font.setStrikeOut(True)
        btn.setFont(font)
        acento = self.colores.get('acento', '#6366F1')
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(0,0,0,0.2); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); 
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.08); border: 1px solid {acento}44; }}
            QPushButton:checked {{ background: {acento}; color: white; border: none; }}
        """)
        btn.clicked.connect(lambda: self.callbacks["aplicar_formato"](tipo))
        return btn

    def _on_heading_changed(self, index):
        opciones = ["p", "h1", "h2", "h3", "quote"]
        if 0 <= index < len(opciones):
            tipo = opciones[index]
            if "aplicar_encabezado" in self.callbacks:
                self.callbacks["aplicar_encabezado"](tipo)

    def _mostrar_paleta_color(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 6px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores['acento']};
                color: white;
            }}
        """)
        colores_rapidos = [
            ("Blanco", "#FFFFFF"),
            ("Gris Claro", "#D1D5DB"),
            ("Amarillo", "#FBBF24"),
            ("Naranja", "#FB923C"),
            ("Rojo", "#F87171"),
            ("Verde", "#34D399"),
            ("Azul", "#60A5FA"),
            ("Púrpura", "#A78BFA"),
            ("Rosa", "#F472B6"),
        ]
        for nombre, hex_col in colores_rapidos:
            act = menu.addAction(f"●  {nombre}")
            act.triggered.connect(lambda ch, c=hex_col: self.callbacks["cambiar_color_texto"](c))
        
        menu.addSeparator()
        act_custom = menu.addAction("🎨 Selector completo...")
        act_custom.triggered.connect(lambda: self.callbacks["cambiar_color_texto"](None))
        menu.exec(self.cursor().pos())

    def _crear_barra_tags(self, layout_izq):
        self.tag_activo = None
        self.tags_disponibles = []
        
        # Cinta horizontal ultra-compacta y elegante para chips de etiquetas
        self.scroll_tags = QScrollArea()
        self.scroll_tags.setFixedHeight(28)
        self.scroll_tags.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.scroll_tags.setWidgetResizable(True)
        self.scroll_tags.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_tags.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_tags.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Habilitar scroll horizontal intuitivo con la rueda del ratón
        self.scroll_tags.wheelEvent = lambda event: self.scroll_tags.horizontalScrollBar().setValue(
            self.scroll_tags.horizontalScrollBar().value() - (event.angleDelta().y() or event.angleDelta().x())
        )

        self.widget_chips = QWidget()
        self.widget_chips.setStyleSheet("background: transparent;")
        self.layout_chips = QHBoxLayout(self.widget_chips)
        self.layout_chips.setContentsMargins(0, 0, 0, 0)
        self.layout_chips.setSpacing(4)
        self.scroll_tags.setWidget(self.widget_chips)

        layout_izq.addWidget(self.scroll_tags)
        self._actualizar_tags_ui(["Todas"])

    def _actualizar_tags_ui(self, tags=None, tag_activo=None):
        if tags is not None:
            self.tags_disponibles = list(tags)
        if "Todas" not in self.tags_disponibles:
            self.tags_disponibles.insert(0, "Todas")
        if tag_activo is not None:
            self.tag_activo = tag_activo

        # Limpiar chips existentes
        while self.layout_chips.count():
            item = self.layout_chips.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Botón chip "+ Tag" al principio para acceso inmediato
        btn_add = QPushButton("➕ Tag")
        btn_add.setFixedHeight(22)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setToolTip("Asignar o editar etiquetas a la nota actual")
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background: rgba(99,102,241,0.15); color: {self.colores.get('acento', '#6366F1')};
                border-radius: 11px; padding: 0 8px; border: 1px solid rgba(99,102,241,0.35); font-weight: bold; font-size: 8pt;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento', '#6366F1')}; color: white; }}
        """)
        if "asignar_tag" in self.callbacks:
            btn_add.clicked.connect(self.callbacks["asignar_tag"])
        self.layout_chips.addWidget(btn_add)

        for t in self.tags_disponibles:
            is_active = (self.tag_activo == t) or (self.tag_activo is None and t == "Todas")
            label_text = "🏷️ Todas" if t == "Todas" else (t if t.startswith("#") else f"#{t}")
            btn = QPushButton(label_text)
            btn.setFixedHeight(22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont(self.font_family, 7, QFont.Weight.Bold if is_active else QFont.Weight.Normal))
            
            acento = self.colores.get('acento', '#6366F1')
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {acento}; color: white; border-radius: 11px; padding: 0 8px; border: none;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: rgba(255,255,255,0.06); color: {self.colores['fg_secundario']};
                        border-radius: 11px; padding: 0 8px; border: 1px solid rgba(255,255,255,0.05);
                    }}
                    QPushButton:hover {{ background: rgba(255,255,255,0.12); color: white; }}
                """)
            btn.clicked.connect(lambda ch, tag=t: self._filtrar_por_tag(tag))
            self.layout_chips.addWidget(btn)

    def _filtrar_por_tag(self, tag):
        self.tag_activo = None if tag == "Todas" else tag
        self._actualizar_tags_ui(tag_activo=tag)
        if "filtrar_por_tag" in self.callbacks:
            self.callbacks["filtrar_por_tag"](self.tag_activo)

    def actualizar_estado_botones(self, formatos):
        if hasattr(self, 'btn_negrita'):
            self.btn_negrita.setChecked(formatos.get('negrita', False))
        if hasattr(self, 'btn_cursiva'):
            self.btn_cursiva.setChecked(formatos.get('cursiva', False))
        if hasattr(self, 'btn_subrayado'):
            self.btn_subrayado.setChecked(formatos.get('subrayado', False))
        if hasattr(self, 'btn_tachado'):
            self.btn_tachado.setChecked(formatos.get('tachado', False))
