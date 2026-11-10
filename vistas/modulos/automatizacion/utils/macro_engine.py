"""
macro_engine.py
Motor de grabación y reproducción de macros para teclado y ratón.
Permite registrar secuencias de acciones, serializarlas a JSON y reproducirlas
a velocidades ajustables con bucles configurables.
"""

import time
import json
import threading
from pathlib import Path
from typing import Callable, Optional

from .input_simulator import (
    user32, get_cursor_pos, set_cursor_pos, mouse_click,
    key_down, key_up, key_press, VK_MAP
)

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04

class MacroEvent:
    def __init__(self, time_offset: float, action: str, params: dict):
        self.time_offset = round(time_offset, 3)
        self.action = action  # 'click', 'move', 'key_press'
        self.params = params

    def to_dict(self) -> dict:
        return {
            "time_offset": self.time_offset,
            "action": self.action,
            "params": self.params
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            time_offset=data.get("time_offset", 0.0),
            action=data.get("action", ""),
            params=data.get("params", {})
        )


class MacroRecorder:
    """
    Grabador en segundo plano que detecta clics de ratón, posición y pulsaciones de teclas.
    """
    def __init__(self):
        self._recording = False
        self._thread = None
        self.events: list[MacroEvent] = []
        self._start_time = 0.0
        self.record_mouse_clicks = True
        self.record_mouse_moves = False
        self.record_keys = True
        self._last_mouse_pos = (0, 0)

        # Monitorear estado de botones y teclas
        self._key_states = {}
        self.on_event_recorded: Optional[Callable[[MacroEvent], None]] = None

    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self, record_clicks=True, record_moves=False, record_keys=True):
        if self._recording or not user32:
            return
        self.events = []
        self.record_mouse_clicks = record_clicks
        self.record_mouse_moves = record_moves
        self.record_keys = record_keys
        self._recording = True
        self._start_time = time.perf_counter()
        self._last_mouse_pos = get_cursor_pos()

        # Inicializar estados de teclas monitoreadas
        self._key_states = {}
        for vk in list(VK_MAP.values()) + [VK_LBUTTON, VK_RBUTTON, VK_MBUTTON]:
            self._key_states[vk] = (user32.GetAsyncKeyState(vk) & 0x8000) != 0

        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop_recording(self) -> list[MacroEvent]:
        self._recording = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        return self.events

    def _record_loop(self):
        while self._recording:
            now = time.perf_counter()
            offset = now - self._start_time
            curr_pos = get_cursor_pos()

            # 1. Movimiento del ratón
            if self.record_mouse_moves and curr_pos != self._last_mouse_pos:
                evt = MacroEvent(offset, "move", {"x": curr_pos[0], "y": curr_pos[1]})
                self.events.append(evt)
                self._last_mouse_pos = curr_pos
                if self.on_event_recorded:
                    self.on_event_recorded(evt)

            # 2. Clics del ratón (flanco de subida)
            if self.record_mouse_clicks:
                for vk, btn_name in [(VK_LBUTTON, "left"), (VK_RBUTTON, "right"), (VK_MBUTTON, "middle")]:
                    pressed = (user32.GetAsyncKeyState(vk) & 0x8000) != 0
                    if pressed and not self._key_states.get(vk, False):
                        evt = MacroEvent(offset, "click", {
                            "button": btn_name,
                            "click_type": "single",
                            "x": curr_pos[0],
                            "y": curr_pos[1]
                        })
                        self.events.append(evt)
                        if self.on_event_recorded:
                            self.on_event_recorded(evt)
                    self._key_states[vk] = pressed

            # 3. Teclas
            if self.record_keys:
                for key_name, vk in VK_MAP.items():
                    if vk in (0x01, 0x02, 0x04, 0x05, 0x06) or key_name in ("F8", "F9"):
                        continue
                    pressed = (user32.GetAsyncKeyState(vk) & 0x8000) != 0
                    if pressed and not self._key_states.get(vk, False):
                        evt = MacroEvent(offset, "key_press", {
                            "key": key_name,
                            "vk": vk
                        })
                        self.events.append(evt)
                        if self.on_event_recorded:
                            self.on_event_recorded(evt)
                    self._key_states[vk] = pressed

            time.sleep(0.01)


class MacroPlayer:
    """
    Reproductor de secuencias de eventos de macros con velocidad y repetición ajustables.
    """
    def __init__(self):
        self._playing = False
        self._paused = False
        self._thread = None
        self.on_progress: Optional[Callable[[int, int], None]] = None
        self.on_finished: Optional[Callable[[], None]] = None

    def is_playing(self) -> bool:
        return self._playing

    def play(self, events: list[MacroEvent], speed: float = 1.0, repeat_count: int = 1, delay_between_loops: float = 0.5):
        """
        Inicia la reproducción de la macro.
        - repeat_count: 0 o negativo para infinito, o número fijo de repeticiones.
        - speed: multiplicador (ej. 2.0 = el doble de rápido).
        """
        if self._playing or not events:
            return
        self._playing = True
        self._paused = False
        self._thread = threading.Thread(
            target=self._play_loop,
            args=(events, max(0.1, speed), repeat_count, delay_between_loops),
            daemon=True
        )
        self._thread.start()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        self._playing = False
        self._paused = False

    def _play_loop(self, events: list[MacroEvent], speed: float, repeat_count: int, delay_between_loops: float):
        total_events = len(events)
        loop = 0
        try:
            while self._playing and (repeat_count <= 0 or loop < repeat_count):
                last_offset = 0.0
                for idx, evt in enumerate(events):
                    if not self._playing:
                        break

                    while self._paused and self._playing:
                        time.sleep(0.05)

                    delta = (evt.time_offset - last_offset) / speed
                    if delta > 0.001:
                        time.sleep(delta)
                    last_offset = evt.time_offset

                    # Ejecutar acción
                    self._execute_event(evt)

                    if self.on_progress:
                        self.on_progress(idx + 1, total_events)

                loop += 1
                if self._playing and (repeat_count <= 0 or loop < repeat_count) and delay_between_loops > 0:
                    time.sleep(delay_between_loops)
        finally:
            self._playing = False
            if self.on_finished:
                self.on_finished()

    def _execute_event(self, evt: MacroEvent):
        try:
            if evt.action == "click":
                btn = evt.params.get("button", "left")
                click_t = evt.params.get("click_type", "single")
                x = evt.params.get("x")
                y = evt.params.get("y")
                mouse_click(button=btn, click_type=click_t, x=x, y=y)
            elif evt.action == "move":
                x = evt.params.get("x")
                y = evt.params.get("y")
                if x is not None and y is not None:
                    set_cursor_pos(x, y)
            elif evt.action == "key_press":
                vk = evt.params.get("vk")
                if vk:
                    key_press(vk, hold_duration=0.01)
        except Exception as e:
            print(f"[MacroPlayer Error] Al ejecutar evento: {e}")


def save_macro_file(filepath: Path, events: list[MacroEvent], name: str = "Nueva Macro") -> bool:
    try:
        data = {
            "name": name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event_count": len(events),
            "events": [evt.to_dict() for evt in events]
        }
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando macro: {e}")
        return False


def load_macro_file(filepath: Path) -> tuple[str, list[MacroEvent]]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        name = data.get("name", "Macro")
        events = [MacroEvent.from_dict(d) for d in data.get("events", [])]
        return name, events
    except Exception as e:
        print(f"Error cargando macro: {e}")
        return "Error", []

