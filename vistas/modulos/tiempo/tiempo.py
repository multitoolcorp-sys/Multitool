import os
import sys
import time
import json
import datetime
import platform
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QMessageBox, QFileDialog, QDialog, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from .submodulos.alarmas_timer import AlarmasTimerSubmodule
from .submodulos.cronometro import CronometroSubmodule
from .submodulos.reloj_mundial import RelojMundialSubmodule
from .submodulos.pomodoro import PomodoroSubmodule
from .submodulos.calendario_eventos import CalendarioEventosSubmodule
from .submodulos.time_tracker import TimeTrackerSubmodule
from .submodulos.calculadora_fechas import CalculadoraFechasSubmodule
from .utils.time_manager import TimeManager
from vistas.utils.notification import NotificationManager
from vistas.utils.hardware_manager import get_hardware_manager

# Intentar winsound para alarmas en Windows
try:
    import winsound
except ImportError:
    winsound = None

class TabTiempo(QWidget):
    """Módulo Principal de Tiempo y Productividad estructurado en Submódulos estilo TabCuenta"""
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        # Paleta de colores
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        })

        # Managers
        self.manager = TimeManager(self.ruta_usuario / "tiempo")
        self.notifier = NotificationManager()

        # Callbacks
        self.callbacks = {
            "crono_start": lambda: self.manager.control_cronometro("start"),
            "crono_pause": lambda: self.manager.control_cronometro("pause"),
            "crono_reset": self.crono_reset,
            "crono_lap": self.crono_lap,
            "timer_start": self.timer_start,
            "timer_pause": self.timer_pause,
            "timer_reset": self.timer_reset,
            "alarm_add": self.alarm_add,
            "alarm_edit_save": self.alarm_edit_save,
            "alarm_toggle": self.alarm_toggle,
            "alarm_del": self.alarm_del,
            "alarm_change_sound": self.alarm_change_sound,
            "alarm_change_device": self.alarm_change_device
        }

        # Hardware Manager Centralizado
        self.hw_manager = get_hardware_manager()
        self.hw_manager.devices_changed.connect(self._refrescar_hardware_audio)

        # Sonido predeterminado
        try: base_path = sys._MEIPASS
        except Exception: base_path = os.path.abspath(".")
        self.sonido_default_path = self._obtener_ruta_alarma_wav() or os.path.join(base_path, "vistas", "utils", "alarma.wav")

        self.last_alarm_trigger = ""
        self.alarm_device_id = None

        self.inicializar_ui()

        # Bucle de actualización cada 100ms
        self.loop_timer = QTimer(self)
        self.loop_timer.timeout.connect(self._actualizar_bucle)
        self.loop_timer.start(100)

    def inicializar_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # TabWidget Principal
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont(self.font_family, 9))
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['acento']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)

        # Submódulos dinámicos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        extra_kwargs = {
            "callbacks": self.callbacks,
            "manager": self.manager
        }
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores, extra_kwargs)

        if self.tabs.count() == 0:
            self.submod_reloj = RelojMundialSubmodule(self, self.context, self.manager, self.colores)
            self.submod_alarmas = AlarmasTimerSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.submod_cronometro = CronometroSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.submod_pomodoro = PomodoroSubmodule(self, self.context, self.manager, self.colores)
            self.submod_calendario = CalendarioEventosSubmodule(self, self.context, self.manager, self.colores)
            self.submod_tracker = TimeTrackerSubmodule(self, self.context, self.manager, self.colores)
            self.submod_calc = CalculadoraFechasSubmodule(self, self.context, self.manager, self.colores)

            self.tabs.addTab(self.submod_reloj, "🌐 Reloj Mundial")
            self.tabs.addTab(self.submod_alarmas, "⏰ Alarmas & Temporizador")
            self.tabs.addTab(self.submod_cronometro, "⏱️ Cronómetro & Vueltas")
            self.tabs.addTab(self.submod_pomodoro, "🍅 Pomodoro & Enfoque")
            self.tabs.addTab(self.submod_calendario, "📅 Calendario & Eventos")
            self.tabs.addTab(self.submod_tracker, "📊 Time Tracker")
            self.tabs.addTab(self.submod_calc, "🧮 Calculadora de Fechas")
        else:
            self.submod_reloj = self.submod_instances.get("RelojMundialSubmodule")
            self.submod_alarmas = self.submod_instances.get("AlarmasTimerSubmodule") or self.submod_instances.get("alarmastimersubmodule")
            if not self.submod_alarmas:
                self.submod_alarmas = AlarmasTimerSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.submod_cronometro = self.submod_instances.get("CronometroSubmodule")
            self.submod_pomodoro = self.submod_instances.get("PomodoroSubmodule")
            self.submod_calendario = self.submod_instances.get("CalendarioEventosSubmodule")
            self.submod_tracker = self.submod_instances.get("TimeTrackerSubmodule")
            self.submod_calc = self.submod_instances.get("CalculadoraFechasSubmodule")

        self.gui = self.submod_alarmas  # Alias de compatibilidad
        main_lay.addWidget(self.tabs)
        self._refrescar_hardware_audio()

    def _actualizar_bucle(self):
        # 1. Cronómetro
        t_crono = self.manager.get_crono_time()
        if self.submod_cronometro:
            self.submod_cronometro.actualizar_crono_ui(t_crono)

        # 2. Temporizador
        if self.manager.timer_running and self.submod_alarmas:
            elapsed = time.time() - self.manager.timer_start_time
            rem = max(0, self.manager.timer_remaining - elapsed)
            self.submod_alarmas._update_timer_digits(rem)
            if rem <= 0:
                self.manager.timer_running = False
                self.submod_alarmas.btn_timer_start.setText("▶ Iniciar")
                self.disparar_alarma("⏰ TEMPORIZADOR FINALIZADO", "¡El tiempo ha terminado!")

        # 3. Reloj Mundial
        if self.submod_reloj:
            self.submod_reloj.actualizar_relojes()

        # 4. Pomodoro
        if self.submod_pomodoro:
            self.submod_pomodoro.tick_100ms()

        # 5. Time Tracker
        if self.submod_tracker and hasattr(self.submod_tracker, "tick_100ms"):
            self.submod_tracker.tick_100ms()

        # 6. Verificación de Alarmas Programadas
        triggered = self.manager.check_alarmas()
        if triggered:
            now_key = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            if self.last_alarm_trigger != now_key:
                self.last_alarm_trigger = now_key
                for a in triggered:
                    lbl = a.get("label", "Alarma")
                    self.disparar_alarma(f"⏰ ALARMA: {lbl}", f"Son las {a['hora']:02d}:{a['minuto']:02d}")

    # ── Alarmas Logic ────────────────────────────────────────────────────
    def alarm_add(self, h, m, label="Alarma", sonido=None, dias=None):
        self.manager.añadir_alarma(h, m, label, sonido=sonido, dias=dias)
        self.submod_alarmas.refrescar_alarmas()

    def alarm_edit_save(self, aid, h, m, label="Alarma", sonido=None, dias=None):
        self.manager.editar_alarma(aid, h, m, label, sonido, dias)
        self.submod_alarmas.refrescar_alarmas()

    def alarm_toggle(self, aid):
        self.manager.toggle_alarma(aid)
        self.submod_alarmas.refrescar_alarmas()

    def alarm_del(self, aid):
        self.manager.eliminar_alarma(aid)
        self.submod_alarmas.refrescar_alarmas()

    def alarm_change_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Sonido de Alarma", "", "Archivos de Audio (*.wav)")
        if file_path:
            self.manager.sonido_alarma = file_path
            self.manager.guardar_alarmas()
            sonido_actual = Path(file_path).name
            self.submod_alarmas.lbl_sonido_actual.setText(f"🎵 Sonido: {sonido_actual}")

    def alarm_change_device(self, device_id):
        self.alarm_device_id = device_id

    def disparar_alarma(self, titulo, mensaje):
        def on_posponer():
            if winsound and platform.system() == "Windows":
                try: winsound.PlaySound(None, 0)
                except Exception: pass
            if hasattr(self, "_alarm_sound_effect") and self._alarm_sound_effect.isPlaying():
                self._alarm_sound_effect.stop()
            self.manager.posponer_alarma(2)
            self.submod_alarmas.refrescar_alarmas()

        def on_detener():
            if winsound and platform.system() == "Windows":
                try: winsound.PlaySound(None, 0)
                except Exception: pass
            if hasattr(self, "_alarm_sound_effect") and self._alarm_sound_effect.isPlaying():
                self._alarm_sound_effect.stop()
            self.manager.limpiar_alarmas_pospuestas()
            self.submod_alarmas.refrescar_alarmas()

        # 1. Reproducir sonido de alarma configurado con fallbacks garantizados
        sound_file = self.manager.sonido_alarma or self.sonido_default_path or self._obtener_ruta_alarma_wav()
        played = False
        
        if winsound and platform.system() == "Windows":
            try:
                if sound_file and os.path.exists(sound_file):
                    winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    played = True
                else:
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    played = True
            except Exception as e:
                print(f"[Tiempo] Error winsound: {e}")

        if not played:
            try:
                from PyQt6.QtMultimedia import QSoundEffect
                from PyQt6.QtCore import QUrl
                if not hasattr(self, "_alarm_sound_effect"):
                    self._alarm_sound_effect = QSoundEffect(self)
                if sound_file and os.path.exists(sound_file):
                    self._alarm_sound_effect.setSource(QUrl.fromLocalFile(sound_file))
                    self._alarm_sound_effect.setVolume(1.0)
                    self._alarm_sound_effect.play()
                    played = True
            except Exception as e:
                print(f"[Tiempo] Error QSoundEffect: {e}")

        if not played:
            try:
                from PyQt6.QtWidgets import QApplication
                QApplication.beep()
            except Exception:
                pass

        # 2. Notificación emergente flotante en la esquina inferior derecha con botones interactivos
        try:
            win = self.window() or self
            actions = {
                "😴 Posponer 2 min": on_posponer,
                "🛑 Detener Alarma": on_detener
            }
            self.notifier.show(win, titulo, mensaje, type="info", duration=10000, actions=actions)
        except Exception as e:
            print(f"Error mostrando notificación flotante: {e}")

    # ── Cronómetro & Temporizador Logic ─────────────────────────────────
    def crono_reset(self):
        self.manager.control_cronometro("reset")
        self.submod_cronometro.lbl_crono_digits.setText("00:00:00.00")
        if hasattr(self.submod_cronometro, "table_laps"):
            self.submod_cronometro.table_laps.setRowCount(0)
        if hasattr(self.submod_cronometro, "btn_crono_start"):
            self.submod_cronometro.btn_crono_start.setText("▶ Iniciar")

    def crono_lap(self):
        self.manager.registrar_lap()

    def timer_start(self):
        if self.manager.timer_remaining > 0:
            self.manager.timer_running = True
            self.manager.timer_start_time = time.time()

    def timer_pause(self):
        if self.manager.timer_running:
            elapsed = time.time() - self.manager.timer_start_time
            self.manager.timer_remaining = max(0, self.manager.timer_remaining - elapsed)
            self.manager.timer_running = False

    def timer_reset(self):
        self.manager.timer_running = False
        self.manager.timer_remaining = 0
        self.submod_alarmas._update_timer_digits(0)

    def _refrescar_hardware_audio(self):
        output_devices = self.hw_manager.get_audio_outputs()
        self.submod_alarmas.combo_audio_hw.blockSignals(True)
        self.submod_alarmas.combo_audio_hw.clear()
        self.submod_alarmas.combo_audio_hw.addItem("🔊 Audio Predeterminado", None)
        for dev in output_devices:
            self.submod_alarmas.combo_audio_hw.addItem(f"🎧 {dev['name']}", dev['id'])
        self.submod_alarmas.combo_audio_hw.blockSignals(False)

    def _obtener_ruta_alarma_wav(self):
        candidatos = [
            Path(__file__).resolve().parents[2] / "utils" / "alarma.wav",
            Path(__file__).resolve().parents[3] / "vistas" / "utils" / "alarma.wav",
            Path(sys.executable).resolve().parent / "vistas" / "utils" / "alarma.wav",
            Path(os.path.abspath(".")) / "vistas" / "utils" / "alarma.wav",
        ]
        if hasattr(sys, "_MEIPASS"):
            candidatos.insert(0, Path(sys._MEIPASS) / "vistas" / "utils" / "alarma.wav")
        for c in candidatos:
            if c and c.exists():
                return str(c)
        return None

    def actualizar_tema(self, colores):
        self.colores = colores
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['acento']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)
        for sub in [self.submod_reloj, self.submod_alarmas, self.submod_cronometro, 
                    self.submod_pomodoro, self.submod_calendario, self.submod_tracker, self.submod_calc]:
            if sub and hasattr(sub, "actualizar_tema"):
                try:
                    sub.actualizar_tema(colores)
                except Exception as e:
                    print(f"Error actualizando tema en {sub}: {e}")

    def cleanup(self):
        if hasattr(self, "loop_timer") and self.loop_timer.isActive():
            self.loop_timer.stop()
        if hasattr(self, "hw_manager"):
            try:
                self.hw_manager.devices_changed.disconnect(self._refrescar_hardware_audio)
            except Exception:
                pass
        if hasattr(self, "_alarm_sound_effect") and self._alarm_sound_effect.isPlaying():
            try:
                self._alarm_sound_effect.stop()
            except Exception:
                pass
        if winsound and platform.system() == "Windows":
            try:
                winsound.PlaySound(None, 0)
            except Exception:
                pass
