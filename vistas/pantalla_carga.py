import time
import platform
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QScreen

class PantallaCarga(QWidget):
    def __init__(self, parent=None, auto_play=True):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool  # Evita que aparezca en la barra de tareas por separado
        )
        self.resize(400, 250)
        self.setStyleSheet("background-color: #1E1E1E; border: 1px solid #2D2D2D; border-radius: 10px;")
        
        self.center_window(parent)
            
        self.auto_play = auto_play
        self.carga_completa = False
        self.drag_pos = None # Para poder mover la ventana
        
        self.crear_widgets()
        
        if self.auto_play:
            self.animar_carga()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None


    def center_window(self, parent):
        if parent:
            # Centrar respecto al padre
            geo = parent.geometry()
            self.move(geo.center().x() - self.width() // 2, geo.center().y() - self.height() // 2)
        else:
            # Centrar en pantalla disponible actual
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(
                screen.left() + (screen.width() - self.width()) // 2,
                screen.top() + (screen.height() - self.height()) // 2
            )

    def crear_widgets(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # Fuente adaptable
        font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": font_family = ".AppleSystemUIFont"

        # Título
        title = QLabel("MULTITOOL")
        title.setFont(QFont(font_family, 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #6366F1; ")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Subtítulo
        self.lbl_subtitle = QLabel("Iniciando aplicación...")
        self.lbl_subtitle.setFont(QFont(font_family, 11))
        self.lbl_subtitle.setStyleSheet("color: #E2E2E2;")
        self.lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_subtitle)
        
        layout.addStretch()
        
        # Barra de progreso premium
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 0px;
                background-color: #2D2D3D;
                height: 6px;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #6366F1;
                border-radius: 3px;
            }
        """)
        self.progress.setTextVisible(False)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # Mensaje Variable
        self.lbl_mensaje = QLabel("Inicializando componentes...")
        self.lbl_mensaje.setFont(QFont(font_family, 9))
        self.lbl_mensaje.setStyleSheet("color: #AAB0B8;")
        self.lbl_mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_mensaje)
        
        layout.addStretch()
        
        # Versión
        version = QLabel("v1.0 PREMIUM")
        version.setFont(QFont(font_family, 8, QFont.Weight.Bold))
        version.setStyleSheet("color: #4D4D4D;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

    def animar_carga(self):
        self.progress.setValue(0)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar_progreso_auto)
        self.timer.start(40)

    def actualizar_progreso_auto(self):
        if self.carga_completa:
            self.progress.setValue(100)
            self.timer.stop()
            return
            
        val = self.progress.value()
        if val < 100:
            val += 2
            self.progress.setValue(val)
            
            if val < 20: self.lbl_mensaje.setText("Configurando núcleo...")
            elif val < 40: self.lbl_mensaje.setText("Cargando módulos de sistema...")
            elif val < 60: self.lbl_mensaje.setText("Estableciendo conexión segura...")
            elif val < 80: self.lbl_mensaje.setText("Preparando interfaz de usuario...")
            else: self.lbl_mensaje.setText("Finalizando carga...")
        else:
            self.timer.stop()
            self.finalizar()

    def actualizar(self, progreso, mensaje):
        """Actualiza el progreso manualmente (usado externamente)"""
        self.progress.setValue(progreso)
        self.lbl_mensaje.setText(mensaje)
        QApplication.processEvents()
        
        if progreso >= 100:
            self.finalizar()
            
    def finalizar(self):
        self.carga_completa = True
        self.progress.setValue(100)
        self.lbl_mensaje.setText("Carga completada")

