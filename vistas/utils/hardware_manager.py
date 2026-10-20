from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtMultimedia import QMediaDevices, QAudioDevice
from PyQt6.QtGui import QGuiApplication, QScreen

class HardwareManager(QObject):
    """
    Gestor centralizado de Hardware (Pantallas, Micrófonos y Altavoces).
    Detecta cambios en tiempo real (Hot-swapping) sin reiniciar la app.
    """
    devices_changed = pyqtSignal() # Señal genérica para cualquier cambio

    def __init__(self):
        super().__init__()
        # Conectar señales nativas de Qt para detección automática
        self.audio_devices = QMediaDevices()
        self.audio_devices.audioInputsChanged.connect(self.on_hardware_change)
        self.audio_devices.audioOutputsChanged.connect(self.on_hardware_change)
        
        # Para pantallas, usamos QGuiApplication
        QGuiApplication.instance().screenAdded.connect(self.on_hardware_change)
        QGuiApplication.instance().screenRemoved.connect(self.on_hardware_change)

    def on_hardware_change(self, *args):
        """Callback cuando algo cambia (se enchufa/desenchufa un dispositivo)."""
        print("[HardwareManager] Cambio detectado en el hardware.")
        self.devices_changed.emit()

    # ── PANTALLAS ──
    def get_screens(self):
        """Lista de pantallas con su geometría y nombre."""
        screens = QGuiApplication.screens()
        res = []
        for i, s in enumerate(screens):
            g = s.geometry()
            res.append({
                "id": i,
                "name": s.name(),
                "width": g.width(),
                "height": g.height(),
                "x": g.x(),
                "y": g.y(),
                "obj": s # Referencia al objeto QScreen
            })
        return res

    def get_screens_strings(self):
        """Formato amigable para ComboBoxes."""
        return [f"{s['id']}: {s['name']} ({s['width']}x{s['height']})" for s in self.get_screens()]

    # ── AUDIO INPUT (Micrófonos) ──
    def get_audio_inputs(self):
        """Lista de dispositivos de entrada (Micrófonos)."""
        inputs = QMediaDevices.audioInputs()
        res = []
        for i, d in enumerate(inputs):
            res.append({
                "id": i,
                "name": d.description(),
                "default": d == QMediaDevices.defaultAudioInput(),
                "obj": d
            })
        return res

    def get_inputs_strings(self):
        return [f"{d['id']}: {d['name']}" for d in self.get_audio_inputs()]

    # ── AUDIO OUTPUT (Altavoces/Parlantes) ──
    def get_audio_outputs(self):
        """Lista de dispositivos de salida (Altavoces)."""
        outputs = QMediaDevices.audioOutputs()
        res = []
        for i, d in enumerate(outputs):
            res.append({
                "id": i,
                "name": d.description(),
                "default": d == QMediaDevices.defaultAudioOutput(),
                "obj": d
            })
        return res

    def get_outputs_strings(self):
        return [f"{d['id']}: {d['name']}" for d in self.get_audio_outputs()]

# Instancia única (Singleton) para ser compartida por todos los módulos
_instance = None

def get_hardware_manager():
    global _instance
    if _instance is None:
        _instance = HardwareManager()
    return _instance
