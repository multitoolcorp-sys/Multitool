import hashlib
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QApplication
)
from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtGui import QFont


class PinLockEventFilter(QObject):
    """Filtro de eventos para mantener el bloqueo estricto cuando la app se restaura"""
    def __init__(self, dialog, main_win):
        super().__init__(main_win)
        self.dialog = dialog
        self.main_win = main_win
        self._was_minimized = False

    def eventFilter(self, obj, event):
        if obj == self.main_win and event.type() == QEvent.Type.WindowStateChange:
            if getattr(self.dialog, '_is_exiting', False):
                return super().eventFilter(obj, event)

            is_min = self.main_win.isMinimized()
            if is_min and not self._was_minimized:
                self._was_minimized = True
                self.dialog.hide()
            elif not is_min and self._was_minimized:
                self._was_minimized = False
                if self.dialog.result() != QDialog.DialogCode.Accepted:
                    self.main_win.setEnabled(False)
                    self.dialog.show()
                    self.dialog.raise_()
                    self.dialog.activateWindow()
        return super().eventFilter(obj, event)


class QuickPinLockDialog(QDialog):
    """Diálogo de desbloqueo rápido por PIN de 4 dígitos con Bloqueo Estricto Global"""
    def __init__(self, pin_correcto, colores_base, parent=None):
        super().__init__(None)
        self.pin_correcto = str(pin_correcto)
        self.colores = colores_base or {}
        
        # Identificar la ventana principal de la aplicación
        self.main_win = parent
        if self.main_win and hasattr(self.main_win, 'window'):
            self.main_win = self.main_win.window()

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(400, 320)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 2px solid {self.colores.get('acento', '#6366F1')};
                border-radius: 14px;
            }}
            QLabel {{ color: white; }}
        """)
        self.init_ui()

        self.hidden_floating_widgets = []
        self._bloquear_widgets_y_main()

        if self.main_win:
            self._event_filter = PinLockEventFilter(self, self.main_win)
            self.main_win.installEventFilter(self._event_filter)

        self.setEnabled(True)
        self.ent_pin.setEnabled(True)
        self.ent_pin.setFocus()

    def _bloquear_widgets_y_main(self):
        app = QApplication.instance()
        if app:
            app._pin_lock_active = True

        # 1. Deshabilitar completamente la ventana principal para bloquear clics en la barra de navegación, menú y módulos
        if self.main_win and hasattr(self.main_win, 'setEnabled'):
            self.main_win.setEnabled(False)

        # 2. Ocultar todas las ventanas flotantes secundarias y botones de widgets flotantes
        if app:
            for top_w in app.topLevelWidgets():
                if top_w != self and top_w != self.main_win and top_w.isVisible():
                    top_w.hide()
                    self.hidden_floating_widgets.append(top_w)

    def _desbloquear_widgets_y_main(self):
        app = QApplication.instance()
        if app:
            app._pin_lock_active = False

        if self.main_win and hasattr(self.main_win, 'setEnabled'):
            self.main_win.setEnabled(True)
            self.main_win.activateWindow()

        for top_w in self.hidden_floating_widgets:
            try:
                top_w.show()
            except Exception:
                pass
        self.hidden_floating_widgets.clear()

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(25, 20, 25, 20)
        lay.setSpacing(12)

        # Header con botón minimizar y cerrar app
        head = QHBoxLayout()
        lbl_icon = QLabel("🔒 DESBLOQUEAR MULTITOOL")
        lbl_icon.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_icon.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        head.addWidget(lbl_icon)
        head.addStretch()

        btn_min = QPushButton("🗕 Minimizar")
        btn_min.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_min.setStyleSheet("background: transparent; color: #AAB0B8; border: none; font-size: 11px;")
        btn_min.clicked.connect(self.minimizar_app)
        head.addWidget(btn_min)

        btn_exit = QPushButton("✕ Salir")
        btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exit.setStyleSheet("background: transparent; color: #F87171; border: none; font-size: 11px; font-weight: bold;")
        btn_exit.clicked.connect(self.salir_app_completa)
        head.addWidget(btn_exit)

        lay.addLayout(head)

        lbl_sub = QLabel("Acceso Bloqueado. Introduce tu PIN de 4 dígitos:")
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setStyleSheet("color: #AAB0B8;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_sub)

        self.ent_pin = QLineEdit()
        self.ent_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.ent_pin.setMaxLength(4)
        self.ent_pin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ent_pin.setFont(QFont("Consolas", 22, QFont.Weight.Bold))
        self.ent_pin.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.15);
                padding: 8px;
            }}
        """)
        self.ent_pin.returnPressed.connect(self.verificar_pin)
        lay.addWidget(self.ent_pin)

        self.lbl_error = QLabel("")
        self.lbl_error.setFont(QFont("Segoe UI", 9))
        self.lbl_error.setStyleSheet("color: #F87171;")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_error)

        actions_lay = QHBoxLayout()
        actions_lay.setSpacing(8)

        btn_unlock = QPushButton("🔓 Desbloquear Acceso")
        btn_unlock.setFixedHeight(38)
        btn_unlock.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_unlock.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        btn_unlock.clicked.connect(self.verificar_pin)
        actions_lay.addWidget(btn_unlock, 1)

        btn_quit = QPushButton("🚪 Salir de MultiTool")
        btn_quit.setFixedHeight(38)
        btn_quit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_quit.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #EF4444;
            }
        """)
        btn_quit.clicked.connect(self.salir_app_completa)
        actions_lay.addWidget(btn_quit)

        lay.addLayout(actions_lay)

    def verificar_pin(self):
        input_text = self.ent_pin.text().strip()
        input_hash = hashlib.sha256(f"{input_text}".encode('utf-8')).hexdigest()

        if input_hash == self.pin_correcto or input_text == self.pin_correcto:
            self.accept()
        else:
            self.lbl_error.setText("⚠️ PIN Incorrecto. Inténtalo de nuevo.")
            self.ent_pin.clear()
            self.ent_pin.setFocus()

    def accept(self):
        if hasattr(self, '_event_filter') and self.main_win:
            try:
                self.main_win.removeEventFilter(self._event_filter)
            except Exception:
                pass
        self._desbloquear_widgets_y_main()
        super().accept()

    def reject(self):
        self.minimizar_app()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.minimizar_app()
            event.ignore()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.result() != QDialog.DialogCode.Accepted:
            self.minimizar_app()
            event.ignore()
        else:
            super().closeEvent(event)

    def minimizar_app(self):
        self.hide()
        if self.main_win and hasattr(self.main_win, 'showMinimized'):
            self.main_win.showMinimized()

    def salir_app_completa(self):
        self.minimizar_app()
