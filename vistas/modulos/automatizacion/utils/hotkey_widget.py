"""
hotkey_widget.py
Widget interactivo de asignación de teclas, botones de ratón (LButton, RButton, MButton,
XButton1, XButton2) y otros dispositivos (Mandos XInput, Joysticks, Volantes, Pedales).
Permite hacer clic en el selector y luego presionar cualquier clic del ratón, tecla
o botón de mando para asignarlo instantáneamente (ESC cancela).
"""

import time
from PyQt6.QtWidgets import (
    QPushButton, QDialog, QVBoxLayout, QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent, QMouseEvent

from .input_simulator import GlobalHotkeyListener, VK_TO_NAME, VK_MAP


QT_MOUSE_TO_VK = {
    Qt.MouseButton.LeftButton: (0x01, "LButton"),
    Qt.MouseButton.RightButton: (0x02, "RButton"),
    Qt.MouseButton.MiddleButton: (0x04, "MButton"),
    Qt.MouseButton.BackButton: (0x05, "XButton1"),
    Qt.MouseButton.ForwardButton: (0x06, "XButton2"),
}


class HotkeyCaptureButton(QPushButton):
    """
    Botón inteligente de captura de periféricos (Teclado, Ratón y Mandos/Joysticks).
    Al pulsarlo con clic izquierdo, entra en modo escucha y registra el siguiente
    clic izquierdo (LButton), clic derecho (RButton), rueda central (MButton),
    botones laterales (XButton1/2), tecla de teclado o botón de mando.
    Presionar ESC cancela la captura.
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
        self.current_vk = VK_MAP.get(default_key, None) or VK_MAP.get(default_key.upper(), 0x75)
        self.is_capturing = False
        self._last_capture_ts = 0.0
        self._ignore_next_release = False

        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self._actualizar_estilo(capturing=False)
        self._actualizar_texto()

        if self.listener:
            self.listener.signals.key_captured.connect(self._on_global_key_captured)
            self.listener.signals.capture_cancelled.connect(self.cancel_capture)

    def _actualizar_texto(self):
        if self.is_capturing:
            self.setText("🖱️⌨️ [ Presiona tecla, clic o mando (ESC cancela) ]")
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

    def start_capture(self):
        if time.perf_counter() - self._last_capture_ts < 0.25:
            return
        self.is_capturing = True
        self._actualizar_estilo(capturing=True)
        self._actualizar_texto()
        self.setFocus()
        if self.listener:
            self.listener.start_capturing()

    def cancel_capture(self):
        self.is_capturing = False
        self._last_capture_ts = time.perf_counter()
        if self.listener:
            self.listener.cancel_capturing()
        self._actualizar_estilo(capturing=False)
        self._actualizar_texto()

    def set_key(self, key_name: str, vk: int = 0):
        self.current_key = key_name
        self.current_vk = vk or VK_MAP.get(key_name, None) or VK_MAP.get(key_name.upper(), 0)
        self.is_capturing = False
        self._actualizar_estilo(capturing=False)
        self._actualizar_texto()

    def _on_global_key_captured(self, vk: int, key_name: str):
        if not self.is_capturing:
            return
        self.current_key = key_name
        self.current_vk = vk
        self.is_capturing = False
        self._last_capture_ts = time.perf_counter()
        self._ignore_next_release = True
        if self.listener:
            self.listener.cancel_capturing()
        self._actualizar_estilo(capturing=False)
        self._actualizar_texto()
        self.hotkey_changed.emit(key_name, vk)

    def mousePressEvent(self, event: QMouseEvent):
        if self.is_capturing:
            btn = event.button()
            if btn in QT_MOUSE_TO_VK:
                vk, name = QT_MOUSE_TO_VK[btn]
                self._on_global_key_captured(vk, name)
                event.accept()
                return
        else:
            if event.button() == Qt.MouseButton.LeftButton:
                if time.perf_counter() - self._last_capture_ts >= 0.25:
                    self._ignore_next_release = False
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._ignore_next_release:
            self._ignore_next_release = False
            event.accept()
            return
        if not self.is_capturing and event.button() == Qt.MouseButton.LeftButton:
            if self.rect().contains(event.position().toPoint()):
                self.start_capture()
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if not self.is_capturing:
            super().keyPressEvent(event)
            return

        k = event.key()
        if k == Qt.Key.Key_Escape:
            self.cancel_capture()
            event.accept()
            return

        # Si no hay listener global activo (ej. modo aislado), capturar por evento Qt
        if not self.listener:
            text = event.text().upper()
            name = text if text and text.isalnum() else event.keyCombination().key().name.replace("Key_", "")
            vk = VK_MAP.get(name, 0)
            self._on_global_key_captured(vk, name)
        event.accept()


class HotkeySettingDialog(QDialog):
    """Diálogo modal 'Hotkey setting' estilo OP AutoClicker con soporte para Ratón, Teclado y Mandos."""
    def __init__(self, current_key="F6", listener=None, colores=None, parent=None):
        super().__init__(parent)
        self.listener = listener
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E",
            "bg_terciario": "#2D2D3D", "acento": "#6366F1",
            "acento_hover": "#818CF8", "fg_principal": "#FFFFFF",
            "fg_secundario": "#AAB0B8", "error": "#EF4444", "exito": "#10B981"
        }
        self.selected_key = current_key
        self.selected_vk = VK_MAP.get(current_key, None) or VK_MAP.get(current_key.upper(), 0x75)

        self.setWindowTitle("Hotkey setting - Configurar Atajo")
        self.setFixedSize(410, 220)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores['bg_secundario']};
                color: {self.colores['fg_principal']};
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        lbl_info = QLabel(
            "Haz clic en el botón inferior y luego presiona cualquier tecla del teclado, "
            "botón del ratón (Clic Izquierdo, Derecho, Central, Lateral) o botón de mando:"
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        layout.addWidget(lbl_info)

        # Botón capturador
        self.btn_capture = HotkeyCaptureButton(
            default_key=current_key,
            listener=self.listener,
            colores=self.colores,
            parent=self
        )
        self.btn_capture.hotkey_changed.connect(self._on_key_chosen)
        layout.addWidget(self.btn_capture)

        # Botones Aceptar y Cancelar
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_ok = QPushButton("Aceptar")
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: {self.colores['fg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.1); }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        layout.addLayout(btn_box)

    def _on_key_chosen(self, key_name: str, vk: int):
        self.selected_key = key_name
        self.selected_vk = vk

    def closeEvent(self, event):
        if self.btn_capture.is_capturing:
            self.btn_capture.cancel_capture()
        super().closeEvent(event)
