import time
import json
from pathlib import Path
from PyQt6.QtCore import QObject, QEvent, QTimer
from PyQt6.QtWidgets import QApplication

from .pin_lock_dialog import QuickPinLockDialog

class IdleLockWatcher(QObject):
    """
    Vigilante global de inactividad del usuario (Idle Auto-Lock).
    Monitorea eventos de ratón y teclado en toda la aplicación.
    Si se supera el tiempo configurado en idle_lock_minutes y existe un PIN configurado,
    bloquea la interfaz de MultiTool inmediatamente con QuickPinLockDialog.
    """
    def __init__(self, context, colores, parent=None):
        super().__init__(parent)
        self.context = context
        self.colores = colores or {}
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.parent_window = parent
        self.ultimo_movimiento = time.time()
        self._bloqueo_en_curso = False

        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

        self.timer_check = QTimer(self)
        self.timer_check.timeout.connect(self._verificar_inactividad)
        self.timer_check.start(10000)  # Chequear cada 10 segundos

    def eventFilter(self, obj, event):
        t = event.type()
        if t in (
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.KeyPress,
            QEvent.Type.KeyRelease,
            QEvent.Type.Wheel,
            QEvent.Type.TouchBegin
        ):
            self.ultimo_movimiento = time.time()
        return super().eventFilter(obj, event)

    def _cargar_config(self):
        cfg_path = self.ruta_usuario / "config.json"
        if cfg_path.exists():
            try:
                from controlador.auth.crypto_utils import process_config_for_load
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return process_config_for_load(json.load(f))
            except Exception:
                pass
        return {}

    def _verificar_inactividad(self):
        if self._bloqueo_en_curso:
            return

        app = QApplication.instance()
        if getattr(app, "_pin_lock_active", False):
            return

        cfg = self._cargar_config()
        minutos_limite = int(cfg.get("idle_lock_minutes", 0) or 0)
        pin = cfg.get("pin_lock")

        if minutos_limite <= 0 or not pin:
            return

        segundos_inactivo = time.time() - self.ultimo_movimiento
        if segundos_inactivo >= (minutos_limite * 60):
            self._disparar_bloqueo(pin)

    def _disparar_bloqueo(self, pin):
        self._bloqueo_en_curso = True
        try:
            top_win = self.parent_window
            if top_win and hasattr(top_win, "window"):
                top_win = top_win.window()
            if not top_win:
                app = QApplication.instance()
                top_win = app.activeWindow() if app else None

            dlg = QuickPinLockDialog(pin, self.colores, top_win)
            dlg.exec()
        finally:
            self.ultimo_movimiento = time.time()
            self._bloqueo_en_curso = False
