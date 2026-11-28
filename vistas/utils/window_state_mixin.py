"""Mixin para estado de ventana, geometría, pantalla completa y Modo Zen en BaseAppGUI."""

import json
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton


class WindowStateMixin:
    """Gestiona persistencia de geometría, botón de salida de fullscreen y Modo Zen."""

    def _mostrar_boton_flotante_salir_fullscreen(self):
        if not hasattr(self, "btn_exit_fullscreen") or not self.btn_exit_fullscreen:
            self.btn_exit_fullscreen = QPushButton("✕ Salir de Pantalla Completa (F11)", self)
            self.btn_exit_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_exit_fullscreen.setStyleSheet("""
                QPushButton {
                    background-color: rgba(30, 30, 46, 0.94);
                    color: #FFFFFF;
                    border: 1px solid #6366F1;
                    border-radius: 14px;
                    padding: 6px 18px;
                    font-size: 11px;
                    font-weight: bold;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QPushButton:hover {
                    background-color: #6366F1;
                    color: #FFFFFF;
                }
            """)
            self.btn_exit_fullscreen.clicked.connect(self.toggle_pantalla_completa)

        w_btn = 220
        h_btn = 30
        self.btn_exit_fullscreen.setGeometry((self.width() - w_btn) // 2, 8, w_btn, h_btn)
        self.btn_exit_fullscreen.show()
        self.btn_exit_fullscreen.raise_()

    def _ocultar_boton_flotante_salir_fullscreen(self):
        if hasattr(self, "btn_exit_fullscreen") and self.btn_exit_fullscreen:
            self.btn_exit_fullscreen.hide()

    def _get_window_state_path(self):
        try:
            from controlador.utils.paths import get_data_path
            p = get_data_path() / "browser_data" / "window_state.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            return Path("window_state.json")

    def _restaurar_geometria_ventana(self):
        state_file = self._get_window_state_path()
        restaurado = False
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                x = data.get("x")
                y = data.get("y")
                w = data.get("width")
                h = data.get("height")
                is_max = data.get("is_maximized", False)

                if w and h and w >= 400 and h >= 300:
                    screen = self.screen().geometry()
                    if x is not None and y is not None:
                        x = max(screen.left(), min(x, screen.right() - 250))
                        y = max(screen.top(), min(y, screen.bottom() - 250))
                        self.move(x, y)
                    self.resize(w, h)
                    if is_max:
                        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
                    restaurado = True
            except Exception as e:
                print(f"[BaseAppGUI] Error restaurando geometría: {e}")

        if not restaurado:
            screen = self.screen().geometry()
            w, h = int(screen.width() * 0.85), int(screen.height() * 0.85)
            self.resize(w, h)
            x = (screen.width() - w) // 2
            y = (screen.height() - h) // 2
            self.move(x, y)

    def _guardar_geometria_ventana(self):
        try:
            state_file = self._get_window_state_path()
            is_max = self.isMaximized()
            data = {"is_maximized": is_max}
            if not is_max:
                data["width"] = self.width()
                data["height"] = self.height()
                data["x"] = self.x()
                data["y"] = self.y()
            else:
                normal_geom = self.normalGeometry()
                if normal_geom.isValid() and normal_geom.width() > 300 and normal_geom.height() > 200:
                    data["width"] = normal_geom.width()
                    data["height"] = normal_geom.height()
                    data["x"] = normal_geom.x()
                    data["y"] = normal_geom.y()

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[BaseAppGUI] Error guardando geometría: {e}")

    def toggle_zen_mode(self):
        """Alterna el Modo Zen / Enfoque limpio (F10) ocultando o restaurando barras."""
        if not getattr(self, "is_zen_mode", False):
            self.is_zen_mode = True
            self._zen_saved_state = {
                "sidebar": self.sidebar.isVisible() if hasattr(self, "sidebar") else False,
                "editor_tab_bar": self.editor_tab_bar.isVisible() if hasattr(self, "editor_tab_bar") else False,
                "nav_bar": self.nav_bar.isVisible() if hasattr(self, "nav_bar") else False,
                "menu_bar": self.menuBar().isVisible() if self.menuBar() else False,
                "barra_estado": self.barra_estado_frame.isVisible() if hasattr(self, "barra_estado_frame") else False,
            }
            if hasattr(self, "sidebar"):
                self.sidebar.hide()
            if hasattr(self, "editor_tab_bar"):
                self.editor_tab_bar.hide()
            if hasattr(self, "nav_bar"):
                self.nav_bar.hide()
            if self.menuBar():
                self.menuBar().hide()
            if hasattr(self, "barra_estado_frame"):
                self.barra_estado_frame.hide()
            self.mostrar_notificacion("Modo Zen", "🧘 Modo Enfoque activado. Presiona F10 para restaurar las barras.", "info")
        else:
            self.is_zen_mode = False
            modo = getattr(self, "modo_vista", "clasico")
            self._aplicar_modo_vista(modo)
            if hasattr(self, "barra_estado_frame"):
                self.barra_estado_frame.show()
            self.mostrar_notificacion("Modo Zen", "Modo normal restaurado.", "info")
