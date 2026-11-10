"""
hotkey_widget.py
Widget interactivo de asignación de teclas (Hotkey Selector) idéntico a OP AutoClicker.
Permite hacer clic y presionar cualquier tecla del teclado para asignarla instantáneamente.
"""

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent

from .input_simulator import GlobalHotkeyListener, VK_TO_NAME

class HotkeyCaptureButton(QPushButton):
    """
    Botón inteligente de captura de teclas.
    Al pulsarlo, pasa a modo escucha ('Presiona cualquier tecla...')
    y registra la siguiente tecla pulsada tanto de forma local como global.
    """
    hotkey_changed = pyqtSignal(str, int)  # key_name, vk_code

    def __init__(self, default_key: str = "F6", listener: GlobalHotkeyListener = None, colores: dict = None, parent=None):
        super().__init__(parent)
        self.listener = listener
        self.colores = colores or {
            "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "acento": "#6366F1", "acento_hover": "#818CF8",
            "error": "#F87171", "fg_principal": "#FFFFFF",
        }
        self.current_key = default_key
        self.current_vk = 0x75  # F6
        self.is_capturing = False

        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._actualizar_estilo(capturing=False)
        self._actualizar_texto()

        self.clicked.connect(self._toggle_capturing)

        if self.listener:
            self.listener.signals.key_captured.connect(self._on_global_key_captured)

    def _actualizar_texto(self):
        if self.is_capturing:
            self.setText("⌨️ [ Presiona una tecla... ]")
        else:
            self.setText(f"⌨️ Tecla: [ {self.current_key} ]")

    def _actualizar_estilo(self, capturing: bool):
        if capturing:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(248, 113, 113, 0.25);
                    color: {self.colores['error']};
                    border: 2px dashed {self.colores['error']};
                    border-radius: 8px;
                    padding: 8px 16px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colores['bg_terciario']};
                    color: {self.colores['fg_principal']};
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 8px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background-color: rgba(99, 102, 241, 0.2);
                    border: 1px solid {self.colores['acento']};
                    color: #FFFFFF;
                }}
            """)

    def _toggle_capturing(self):
        if self.is_capturing:
            self.cancel_capture()
        else:
            self.start_capture()

    def start_capture(self):
        self.is_capturing = True
        self._actualizar_estilo(capturing=True)
        self._actualizar_texto()
        if self.listener:
            self.listener.start_capturing()

    def cancel_capture(self):
        self.is_capturing = False
        if self.listener:
            self.listener.cancel_capturing()
        self._actualizar_estilo(capturing=False)
        self._actualizar_texto()

    def _on_global_key_captured(self, vk: int, key_name: str):
        if not self.is_capturing:
            return
        self.current_key = key_name
        self.current_vk = vk
        self.is_capturing = False
        self._actualizar_estilo(capturing=False)
        self._actualizar_texto()
        self.hotkey_changed.emit(key_name, vk)

    def keyPressEvent(self, event: QKeyEvent):
        """Captura local en caso de que el foco esté en el botón."""
        if not self.is_capturing:
            super().keyPressEvent(event)
            return

        k = event.key()
        if k == Qt.Key.Key_Escape:
            self.cancel_capture()
            event.accept()
            return

        text = event.text().upper()
        name = text if text and text.isalnum() else event.keyCombination().key().name.replace("Key_", "")
        self._on_global_key_captured(0, name)
        event.accept()
