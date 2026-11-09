"""
command_palette.py
Paleta de comandos flotante universal para Multitool (accesible con Ctrl+Shift+P o F1).
Permite buscar y saltar instantáneamente a cualquier módulo, submódulo o ejecutar
acciones del sistema rápidamente desde el teclado estilo VSCode / Spotlight.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QKeyEvent, QIcon

class CommandPaletteDialog(QDialog):
    def __init__(self, parent=None, colores=None, on_action=None):
        super().__init__(parent)
        self.colores = colores or {
            'bg_principal': '#121218',
            'bg_secundario': '#1E1E2E',
            'bg_terciario': '#2D2D3D',
            'fg_principal': '#FFFFFF',
            'fg_secundario': '#AAB0B8',
            'acento': '#6366F1',
            'acento_hover': '#4F46E5',
        }
        self.on_action = on_action
        self.font_family = "Segoe UI"
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(560)
        self.setFixedHeight(380)

        self._comandos = []
        self._cargar_comandos_disponibles()
        self._init_ui()

    def _init_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(12, 12, 12, 12)

        # Contenedor con borde y sombra elegante
        self.container = QFrame()
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid {self.colores['acento']};
                border-radius: 10px;
            }}
        """)
        
        # Efecto de sombra
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 6)
        self.container.setGraphicsEffect(shadow)

        lay = QVBoxLayout(self.container)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        # Campo de Búsqueda
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("> Escribe un comando o nombre de módulo...")
        self.input_search.setFont(QFont(self.font_family, 11))
        self.input_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                border: 1px solid {self.colores['bg_terciario']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colores['acento']};
            }}
        """)
        self.input_search.textChanged.connect(self._filtrar_comandos)
        lay.addWidget(self.input_search)

        # Lista de Comandos
        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont(self.font_family, 10))
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                color: {self.colores['fg_principal']};
            }}
            QListWidget::item {{
                padding: 8px 10px;
                border-radius: 6px;
                margin-bottom: 2px;
            }}
            QListWidget::item:selected {{
                background-color: {self.colores['acento']};
                color: #FFFFFF;
                font-weight: bold;
            }}
            QListWidget::item:hover:!selected {{
                background-color: {self.colores['bg_terciario']};
            }}
        """)
        self.list_widget.itemDoubleClicked.connect(self._ejecutar_seleccionado)
        lay.addWidget(self.list_widget, 1)

        # Footer con atajos de teclado
        lbl_hint = QLabel("↑/↓ para navegar  •  Enter para ejecutar  •  Esc para cerrar")
        lbl_hint.setFont(QFont(self.font_family, 8))
        lbl_hint.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none; padding-top: 4px;")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_hint)

        root_lay.addWidget(self.container)

        self._filtrar_comandos("")

    def _cargar_comandos_disponibles(self):
        """Carga la lista completa de módulos y comandos rápidos disponibles."""
        self._comandos = [
            # Módulos y Submódulos Clave
            {"cat": "Módulo", "text": "📁 Archivos: Explorador de Archivos", "action": "goto_archivos_explorador"},
            {"cat": "Módulo", "text": "⚔️ Archivos: Commander de Doble Panel", "action": "goto_archivos_commander"},
            {"cat": "Módulo", "text": "🔍 Archivos: Comparador Diff", "action": "goto_archivos_diff"},
            {"cat": "Módulo", "text": "📦 Archivos: Compresor ZIP / RAR", "action": "goto_archivos_zip"},
            {"cat": "Red",    "text": "🌐 Archivos: Conectar a Unidad de Red (UNC/SMB)", "action": "conectar_red"},
            {"cat": "Módulo", "text": "🗄️ Base de Datos: Gestor Estático y Consola SQL", "action": "goto_basedatos"},
            {"cat": "Módulo", "text": "🌐 Navegador: Navegador Web Integrado", "action": "goto_navegador"},
            {"cat": "Módulo", "text": "⚡ Terminal: Terminal y Consola de Comandos", "action": "goto_terminal"},
            {"cat": "Módulo", "text": "📝 Notas: Editor Markdown y Apuntes", "action": "goto_notas"},
            {"cat": "Módulo", "text": "📊 Cuaderno: Hojas de Cálculo y CSV", "action": "goto_cuaderno"},
            {"cat": "Módulo", "text": "📋 Portapapeles: Historial de Copiado", "action": "goto_clipboard"},
            {"cat": "Módulo", "text": "🎵 Reproductor: Reproductor Multimedia", "action": "goto_reproductor"},
            {"cat": "Módulo", "text": "🎙️ Grabadora: Grabadora de Sonido", "action": "goto_grabadora"},
            {"cat": "Módulo", "text": "🎮 Minijuegos: Juegos y Entretenimiento", "action": "goto_minigames"},
            {"cat": "Módulo", "text": "🛡️ Seguridad: Bóveda de Contraseñas", "action": "goto_seguridad"},
            {"cat": "Módulo", "text": "⚙️ Sistema: Monitor de Recursos y Hardware", "action": "goto_sistema"},
            {"cat": "Módulo", "text": "📅 Calendario: Agenda y Recordatorios", "action": "goto_calendario"},
            {"cat": "Módulo", "text": "🧮 Calculadora: Calculadora y Conversor", "action": "goto_calculadora"},
            {"cat": "Módulo", "text": "🌍 Traductor: Traductor Multilingüe", "action": "goto_traductor"},
            {"cat": "Módulo", "text": "⏱️ Tiempo: Clima, Reloj Mundial y Cronómetro", "action": "goto_tiempo"},
            {"cat": "Módulo", "text": "💡 General: Dashboard y Resumen de Estado", "action": "goto_general"},

            # Acciones Rápidas del Sistema
            {"cat": "Vista",   "text": "🖥️ Vista: Cambiar a modo MMS (MultiModulesStatics Clásico)", "action": "set_vista_mms"},
            {"cat": "Vista",   "text": "💻 Vista: Cambiar a modo IDE (Dashboard con Sidebar)", "action": "set_vista_ide"},
            {"cat": "Sistema", "text": "📦 Actualizaciones: Instalar Actualización (.mtu)...", "action": "instalar_mtu"},
            {"cat": "Sistema", "text": "⚙️ Compilador: Abrir Compilador de Actualizaciones", "action": "abrir_compilador"},
            {"cat": "Sistema", "text": "📋 Actualizaciones: Ver Catálogo y Parches Disponibles", "action": "ver_actualizaciones"},
            {"cat": "Sistema", "text": "⚡ Consola: Abrir Terminal Interactiva Dev", "action": "toggle_consola"},
            {"cat": "Sistema", "text": "🔄 Configuración: Respaldar o Reiniciar Config (.ZIP)", "action": "reiniciar_zip"},
            {"cat": "Sistema", "text": "🚪 Salir: Cerrar Multitool Suite", "action": "salir_app"},
        ]

    def _filtrar_comandos(self, query: str):
        self.list_widget.clear()
        q = query.strip().lower()
        if q.startswith(">"):
            q = q[1:].strip()

        for c in self._comandos:
            txt = c["text"]
            cat = c["cat"]
            if not q or q in txt.lower() or q in cat.lower() or q in c["action"].lower():
                item = QListWidgetItem(f"[{cat}]  {txt}")
                item.setData(Qt.ItemDataRole.UserRole, c)
                self.list_widget.addItem(item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            row = self.list_widget.currentRow()
            total = self.list_widget.count()
            if total > 0:
                if key == Qt.Key.Key_Down:
                    next_row = (row + 1) % total
                else:
                    next_row = (row - 1 + total) % total
                self.list_widget.setCurrentRow(next_row)
            event.accept()
            return
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._ejecutar_seleccionado()
            event.accept()
            return
        elif key == Qt.Key.Key_Escape:
            self.reject()
            event.accept()
            return
        super().keyPressEvent(event)

    def _ejecutar_seleccionado(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        c_data = item.data(Qt.ItemDataRole.UserRole)
        action = c_data.get("action")
        self.accept()
        if self.on_action:
            self.on_action(action)
