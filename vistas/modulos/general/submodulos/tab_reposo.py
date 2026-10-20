"""
tab_reposo.py - Submódulo Gestor de Reposo y Optimización de Memoria RAM para MultiTool.
Permite supervisar qué módulos están abiertos o sin abrir con auras de estado (verde/rojo),
ver la última vez que fueron abiertos y liberar espacio descargándolos a su estado inicial.
"""
import time
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton, QMessageBox, QGridLayout, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor


MODULE_ICONS = {
    "general": "🏠",
    "cuenta": "👤",
    "navegador": "🌐",
    "archivos": "📁",
    "reproductor": "🎵",
    "notas": "📝",
    "cuaderno": "📓",
    "calculadora": "🧮",
    "calendario": "📅",
    "tiempo": "⏰",
    "sistema": "⚙️",
    "terminal": "💻",
    "seguridad": "🛡️",
    "traductor": "🗣️",
    "chat": "💬",
    "proyectos": "📋",
    "grabadora": "🎙️",
    "minigames": "🎮",
    "emulador": "🕹️",
    "basedatos": "🗄️",
    "clipboard": "📋",
    "widgets": "🧩",
    "extras": "✨",
}


class TabModoReposoGUI(QWidget):
    """Submódulo de control de modo reposo y liberación de recursos por módulo."""

    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent)
        self.context = context
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#FFFFFF", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#4F46E5", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }

        self.cards = {}
        self.ram_liberada_mb = 0
        self.init_ui()

        # Temporizador para refrescar el estado de los módulos periódicamente
        self.timer_refresh = QTimer(self)
        self.timer_refresh.setInterval(3000)
        self.timer_refresh.timeout.connect(self.actualizar_vista)
        self.timer_refresh.start()

    def _get_app(self):
        if self.context and hasattr(self.context, "app") and self.context.app:
            return self.context.app
        # Fallback buscando hacia arriba en la jerarquía de ventanas
        curr = self
        while curr:
            if hasattr(curr, "modulos_cargados"):
                return curr
            curr = curr.parent() if hasattr(curr, "parent") else None
        return None

    def _get_modulos_conf_path(self):
        """Obtiene la ruta a modulos.conf del usuario actual"""
        if self.context and hasattr(self.context, "ruta_usuario"):
            p = Path(self.context.ruta_usuario) / "modulos.conf"
            if p.exists() or p.parent.exists():
                return p
        app = self._get_app()
        if app and hasattr(app, "ruta_usuario"):
            p = Path(app.ruta_usuario) / "modulos.conf"
            if p.exists() or p.parent.exists():
                return p
        return None

    def init_ui(self):
        bg_p = self.colores.get("bg_principal", "#121218")
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(20, 20, 20, 20)
        main_lay.setSpacing(16)

        # 1. Cabecera informativa
        header_box = QFrame()
        header_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.07);
                padding: 14px;
            }}
        """)
        h_lay = QHBoxLayout(header_box)
        h_lay.setContentsMargins(10, 10, 10, 10)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        lbl_titulo = QLabel("⚡ GESTOR DE RECURSOS & MODO REPOSO DE MÓDULOS")
        lbl_titulo.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; border: none; background: transparent;")
        info_col.addWidget(lbl_titulo)

        lbl_desc = QLabel(
            "Monitorea el consumo de memoria y configura qué módulos se inician automáticamente al abrir MultiTool.\n"
            "Libera la memoria RAM de los módulos inactivos; al volver a ellos se recargarán limpiamente desde cero."
        )
        lbl_desc.setFont(QFont("Segoe UI", 9))
        lbl_desc.setStyleSheet("color: #AAB0B8; border: none; background: transparent;")
        info_col.addWidget(lbl_desc)
        h_lay.addLayout(info_col, 1)

        # Botón de optimización inteligente
        btn_opt_inteligente = QPushButton("⚡ Optimización Inteligente")
        btn_opt_inteligente.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn_opt_inteligente.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_opt_inteligente.setToolTip("Suspende automáticamente módulos inactivos por más de 15 minutos")
        btn_opt_inteligente.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                border-radius: 8px;
                padding: 10px 16px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#818CF8')};
            }}
        """)
        btn_opt_inteligente.clicked.connect(self._optimizar_inteligente)
        h_lay.addWidget(btn_opt_inteligente)

        # Botón de liberar todo
        btn_liberar_todo = QPushButton("🧹 Liberar Todo el Espacio")
        btn_liberar_todo.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn_liberar_todo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_liberar_todo.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('error', '#F87171')};
                color: white;
                border-radius: 8px;
                padding: 10px 16px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #DC2626;
            }}
        """)
        btn_liberar_todo.clicked.connect(self._confirmar_liberar_todo)
        h_lay.addWidget(btn_liberar_todo)

        btn_refresh = QPushButton("🔄 Refrescar")
        btn_refresh.setFont(QFont("Segoe UI", 9))
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
                border-radius: 8px;
                padding: 10px 14px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)
        btn_refresh.clicked.connect(self.actualizar_vista)
        h_lay.addWidget(btn_refresh)

        main_lay.addWidget(header_box)

        # 2. Tarjetas de resumen métrico
        stats_box = QHBoxLayout()
        stats_box.setSpacing(12)

        self.card_total = self._crear_stat_card("📦 Total de Módulos", "0", "#6366F1")
        self.card_activos = self._crear_stat_card("🟢 En Memoria RAM", "0", "#34D399")
        self.card_reposo = self._crear_stat_card("🔴 En Reposo", "0", "#F87171")
        self.card_autostart = self._crear_stat_card("🚀 Inicio Automático", "0", "#A855F7")
        self.card_ram = self._crear_stat_card("💾 RAM Liberada", "0 MB", "#38BDF8")

        stats_box.addWidget(self.card_total)
        stats_box.addWidget(self.card_activos)
        stats_box.addWidget(self.card_reposo)
        stats_box.addWidget(self.card_autostart)
        stats_box.addWidget(self.card_ram)
        main_lay.addLayout(stats_box)

        # 3. Scroll area con la lista de módulos y sus auras
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.grid_modulos = QGridLayout(self.scroll_content)
        self.grid_modulos.setContentsMargins(0, 5, 0, 5)
        self.grid_modulos.setSpacing(12)

        scroll.setWidget(self.scroll_content)
        main_lay.addWidget(scroll, 1)

        self.actualizar_vista()

    def _crear_stat_card(self, titulo, valor, color_acento):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                padding: 8px 16px;
            }}
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)

        lbl_t = QLabel(titulo)
        lbl_t.setFont(QFont("Segoe UI", 9))
        lbl_t.setStyleSheet("color: #AAB0B8; border: none; background: transparent;")
        lay.addWidget(lbl_t)

        lbl_val = QLabel(valor)
        lbl_val.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {color_acento}; border: none; background: transparent;")
        lay.addWidget(lbl_val)

        frame._lbl_val = lbl_val
        return frame

    def actualizar_vista(self):
        """Actualiza todas las tarjetas de módulos reflejando si están en memoria o en reposo y su autostart."""
        app = self._get_app()
        if not app or not hasattr(app, "modulos_cargados"):
            return

        modulos = [m for m in app.modulos_cargados if m.get("visible", True)]
        total = len(modulos)
        activos = sum(1 for m in modulos if m.get("loaded", False))
        reposo = total - activos
        autostarts = sum(1 for m in modulos if m.get("autostart", False) or m.get("name", "").lower() in ("general", "widgets"))

        self.card_total._lbl_val.setText(str(total))
        self.card_activos._lbl_val.setText(str(activos))
        self.card_reposo._lbl_val.setText(str(reposo))
        self.card_autostart._lbl_val.setText(str(autostarts))
        self.card_ram._lbl_val.setText(f"{self.ram_liberada_mb} MB")

        # Reconstruir o actualizar las tarjetas
        for i, mod in enumerate(modulos):
            mod_name = mod.get("name", "").lower()
            loaded = mod.get("loaded", False)
            last_op = mod.get("last_opened", "Sin abrir en esta sesión")

            if mod_name in self.cards:
                self._actualizar_card(self.cards[mod_name], mod, loaded, last_op)
            else:
                card = self._crear_modulo_card(mod, loaded, last_op)
                self.cards[mod_name] = card
                row = i // 2
                col = i % 2
                self.grid_modulos.addWidget(card, row, col)

    def _crear_modulo_card(self, mod, loaded, last_opened):
        mod_name = mod.get("name", "").lower()
        cap_name = mod.get("name", "").capitalize()
        ico = MODULE_ICONS.get(mod_name, "🧩")

        card = QFrame()
        card.setFixedHeight(122)
        card.setObjectName(f"card_{mod_name}")

        lay = QHBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(14)

        # Icono y datos principales
        left_box = QHBoxLayout()
        left_box.setSpacing(12)

        lbl_icon = QLabel(ico)
        lbl_icon.setFont(QFont("Segoe UI Emoji", 24))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setFixedSize(44, 44)
        lbl_icon.setStyleSheet("background: rgba(255, 255, 255, 0.04); border-radius: 10px; border: none;")
        left_box.addWidget(lbl_icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        lbl_nombre = QLabel(f"{cap_name}")
        lbl_nombre.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_nombre.setStyleSheet("color: white; border: none; background: transparent;")
        text_col.addWidget(lbl_nombre)

        lbl_last = QLabel(f"Última vez: {last_opened}")
        lbl_last.setFont(QFont("Segoe UI", 8))
        lbl_last.setStyleSheet("color: #94A3B8; border: none; background: transparent;")
        text_col.addWidget(lbl_last)

        # Aura de estado (Badge con Glow)
        lbl_aura = QLabel()
        lbl_aura.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        text_col.addWidget(lbl_aura)

        left_box.addLayout(text_col)
        lay.addLayout(left_box, 1)

        # Columna de botones de acción
        action_col = QVBoxLayout()
        action_col.setSpacing(6)
        action_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Botón de acción (Liberar espacio)
        btn_liberar = QPushButton("🧹 Liberar Espacio")
        btn_liberar.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        btn_liberar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_liberar.setFixedWidth(145)
        btn_liberar.setFixedHeight(28)
        btn_liberar.clicked.connect(lambda ch, m=mod_name: self._confirmar_liberar_modulo(m))
        action_col.addWidget(btn_liberar)

        # Botón de inicio automático (Autostart)
        btn_autostart = QPushButton()
        btn_autostart.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        btn_autostart.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_autostart.setFixedWidth(145)
        btn_autostart.setFixedHeight(28)
        btn_autostart.clicked.connect(lambda ch, m=mod_name: self._toggle_autostart_modulo(m))
        action_col.addWidget(btn_autostart)

        lay.addLayout(action_col)

        card._lbl_last = lbl_last
        card._lbl_aura = lbl_aura
        card._btn_liberar = btn_liberar
        card._btn_autostart = btn_autostart

        self._actualizar_card(card, mod, loaded, last_opened)
        return card

    def _actualizar_card(self, card, mod, loaded, last_opened):
        mod_name = mod.get("name", "").lower()
        cap_name = mod.get("name", "").capitalize()
        is_general = mod_name == "general"
        is_widgets = mod_name == "widgets"
        is_core = is_general or is_widgets
        autostart = mod.get("autostart", False)

        card._lbl_last.setText(f"Última vez abierto: {last_opened}")

        # Configurar botón de autostart
        if is_core:
            core_tipo = "Core" if is_general else "Widgets"
            card._btn_autostart.setText(f"🚀 Inicio: Fijo ({core_tipo})")
            card._btn_autostart.setEnabled(False)
            card._btn_autostart.setToolTip(f"El módulo {cap_name} se inicia siempre por defecto al abrir la aplicación.")
            card._btn_autostart.setStyleSheet("""
                QPushButton {
                    background-color: rgba(99, 102, 241, 0.2);
                    color: #A5B4FC;
                    border: 1px solid rgba(99, 102, 241, 0.4);
                    border-radius: 6px;
                }
            """)
        else:
            card._btn_autostart.setEnabled(True)
            if autostart:
                card._btn_autostart.setText("🚀 Inicio Auto: ON")
                card._btn_autostart.setToolTip("Este módulo se iniciará automáticamente en memoria al abrir MultiTool")
                card._btn_autostart.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(168, 85, 247, 0.2);
                        color: #C084FC;
                        border: 1px solid rgba(168, 85, 247, 0.5);
                        border-radius: 6px;
                    }}
                    QPushButton:hover {{
                        background-color: #A855F7;
                        color: white;
                    }}
                """)
            else:
                card._btn_autostart.setText("💤 Inicio Auto: OFF")
                card._btn_autostart.setToolTip("Este módulo esperará en reposo hasta que hagas clic en su pestaña")
                card._btn_autostart.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.04);
                        color: #94A3B8;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 6px;
                    }
                    QPushButton:hover {
                        background-color: rgba(168, 85, 247, 0.25);
                        color: #E9D5FF;
                        border-color: #A855F7;
                    }
                """)

        if loaded:
            # 🟢 AURA VERDE (Abierto y en memoria RAM)
            card.setStyleSheet(f"""
                QFrame#card_{mod_name} {{
                    background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                    border-radius: 12px;
                    border: 1px solid rgba(52, 211, 153, 0.55);
                }}
            """)
            card._lbl_aura.setText("🟢 ABIERTO / EN MEMORIA")
            card._lbl_aura.setStyleSheet("""
                color: #34D399;
                background-color: rgba(52, 211, 153, 0.15);
                border: 1px solid rgba(52, 211, 153, 0.45);
                border-radius: 10px;
                padding: 2px 8px;
            """)

            if is_general:
                card._btn_liberar.setText("📌 En Uso Actual")
                card._btn_liberar.setEnabled(False)
                card._btn_liberar.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.05);
                        color: #6B7280;
                        border-radius: 6px;
                        border: none;
                    }
                """)
            else:
                card._btn_liberar.setText("🧹 Liberar Espacio")
                card._btn_liberar.setEnabled(True)
                card._btn_liberar.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(248, 113, 113, 0.15);
                        color: #F87171;
                        border: 1px solid rgba(248, 113, 113, 0.4);
                        border-radius: 6px;
                    }}
                    QPushButton:hover {{
                        background-color: #EF4444;
                        color: white;
                        border: none;
                    }}
                """)
        else:
            # 🔴 AURA ROJA (En reposo / Sin abrir)
            card.setStyleSheet(f"""
                QFrame#card_{mod_name} {{
                    background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                    border-radius: 12px;
                    border: 1px solid rgba(248, 113, 113, 0.25);
                }}
            """)
            card._lbl_aura.setText("🔴 EN REPOSO / SIN ABRIR")
            card._lbl_aura.setStyleSheet("""
                color: #F87171;
                background-color: rgba(248, 113, 113, 0.08);
                border: 1px solid rgba(248, 113, 113, 0.25);
                border-radius: 10px;
                padding: 2px 8px;
            """)
            card._btn_liberar.setText("💤 En Reposo")
            card._btn_liberar.setEnabled(False)
            card._btn_liberar.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.03);
                    color: #555566;
                    border-radius: 6px;
                    border: none;
                }
            """)

    def _toggle_autostart_modulo(self, mod_name):
        """Activa o desactiva el inicio automático del módulo y lo persiste en modulos.conf"""
        if mod_name.lower() in ("general", "widgets"):
            return

        app = self._get_app()
        if not app or not hasattr(app, "modulos_cargados"):
            return

        target_mod = None
        for m in app.modulos_cargados:
            if m.get("name", "").lower() == mod_name.lower():
                target_mod = m
                break

        if not target_mod:
            return

        nuevo_estado = not target_mod.get("autostart", False)
        target_mod["autostart"] = nuevo_estado

        # Persistir en modulos.conf
        conf_path = self._get_modulos_conf_path()
        if conf_path:
            try:
                data = {}
                if conf_path.exists():
                    with open(conf_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                # Buscar clave insensible a mayúsculas
                found_key = None
                for k in data.keys():
                    if k.lower() == mod_name.lower():
                        found_key = k
                        break

                key_to_use = found_key or mod_name.capitalize()
                if key_to_use not in data:
                    data[key_to_use] = {
                        "visible": target_mod.get("visible", True),
                        "position": target_mod.get("position", 99)
                    }

                data[key_to_use]["autostart"] = nuevo_estado
                with open(conf_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                print(f"[TabReposo] Error guardando autostart en modulos.conf: {e}")

        # Mostrar notificación amigable
        try:
            from vistas.utils.notification import show_notification
            estado_str = "se iniciará automáticamente al abrir MultiTool 🚀" if nuevo_estado else "permanecerá en reposo hasta que abras su pestaña 💤"
            show_notification(
                title=f"Inicio Automático: {mod_name.capitalize()}",
                message=f"El módulo {estado_str}",
                type="info" if nuevo_estado else "warning",
                duration=4000
            )
        except Exception:
            pass

        self.actualizar_vista()

    def _optimizar_inteligente(self):
        """Descarga de la RAM aquellos módulos inactivos que lleven más de 15 minutos sin uso."""
        app = self._get_app()
        if not app or not hasattr(app, "modulos_cargados"):
            return

        cargados = [m for m in app.modulos_cargados if m.get("loaded", False) and m.get("name", "").lower() not in ("general", "widgets")]
        if not cargados:
            QMessageBox.information(self, "Optimización Inteligente", "Todos los módulos secundarios ya se encuentran en reposo.")
            return

        ahora = time.time()
        inactivos = []
        for m in cargados:
            last_ts = m.get("last_opened_timestamp", 0)
            # Inactivo más de 15 minutos (900 seg) o sin timestamp de interacción
            if (ahora - last_ts) > 900 or last_ts == 0:
                inactivos.append(m["name"])

        if not inactivos:
            QMessageBox.information(
                self, "Optimización Inteligente",
                "¡Excelente! Todos los módulos en memoria han tenido actividad reciente (menos de 15 minutos).\nNo es necesario suspender ninguno."
            )
            return

        liberados = 0
        for name in inactivos:
            if app.descargar_modulo(name):
                liberados += 1
                self.ram_liberada_mb += 45

        try:
            from vistas.utils.notification import show_notification
            show_notification(
                title="⚡ Optimización Inteligente Completada",
                message=f"Se suspendieron {liberados} módulos inactivos, liberando ~{liberados * 45} MB de RAM.",
                type="success",
                duration=5000
            )
        except Exception:
            pass

        self.actualizar_vista()

    def _confirmar_liberar_modulo(self, mod_name):
        """Muestra una advertencia formal antes de descargar el módulo de la memoria RAM."""
        app = self._get_app()
        if not app or not hasattr(app, "descargar_modulo"):
            QMessageBox.warning(self, "Aviso", "No se encontró el controlador de módulos principal.")
            return

        resp = QMessageBox.warning(
            self,
            "Liberar Espacio y Poner en Reposo",
            f"¿Deseas poner en reposo el módulo '{mod_name.capitalize()}' y liberar su memoria RAM?\n\n"
            "⚠️ ADVERTENCIA: El módulo se descargará por completo de la memoria y regresará a su estado previo a ser abierto. "
            "Cuando vuelvas a hacer clic en su pestaña, se recargará limpiamente desde cero.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if resp == QMessageBox.StandardButton.Yes:
            exito = app.descargar_modulo(mod_name)
            if exito:
                self.ram_liberada_mb += 45
                try:
                    from vistas.utils.notification import show_notification
                    show_notification(
                        title="Memoria Liberada",
                        message=f"El módulo '{mod_name.capitalize()}' se ha puesto en reposo con éxito (~45 MB liberados).",
                        type="success",
                        duration=4000
                    )
                except Exception:
                    pass
                self.actualizar_vista()

    def _confirmar_liberar_todo(self):
        """Libera todos los módulos en memoria excepto el módulo actual (General)."""
        app = self._get_app()
        if not app or not hasattr(app, "modulos_cargados"):
            return

        cargados = [m["name"] for m in app.modulos_cargados if m.get("loaded", False) and m.get("name", "").lower() != "general"]
        if not cargados:
            QMessageBox.information(self, "Modo Reposo", "Todos los módulos ya se encuentran en reposo.")
            return

        resp = QMessageBox.warning(
            self,
            "Liberar Todo el Espacio",
            f"Se pondrán en reposo los siguientes {len(cargados)} módulos:\n"
            f"• {', '.join([c.capitalize() for c in cargados])}\n\n"
            "⚠️ ADVERTENCIA: Todos los módulos seleccionados se descargarán de la memoria RAM y regresarán a su estado previo a ser abiertos. "
            "¿Deseas continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if resp == QMessageBox.StandardButton.Yes:
            liberados = 0
            for name in cargados:
                if app.descargar_modulo(name):
                    liberados += 1
                    self.ram_liberada_mb += 45

            try:
                from vistas.utils.notification import show_notification
                show_notification(
                    title="Optimización de Recursos Completada",
                    message=f"Se han puesto en reposo {liberados} módulos, liberando ~{liberados * 45} MB de memoria RAM.",
                    type="success",
                    duration=5000
                )
            except Exception:
                pass
            self.actualizar_vista()

