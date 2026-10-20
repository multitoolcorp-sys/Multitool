import json
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QScrollArea,
    QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

COLOR_PALETTE = ["#6366F1", "#3B82F6", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6", "#14B8A6", "#F97316"]

class TabActividad(QWidget):
    """Submódulo de Auditoría de Sesión y Estadísticas de Uso Diario en Tiempo Real desde Logs"""
    def __init__(self, parent, context, colores):
        super().__init__(parent)
        self.context = context
        self.colores = colores or {}
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.persona = getattr(context, "persona", "Usuario")
        self.font_family = "Segoe UI"

        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        self.lbl_val_logins = None
        self.lbl_val_score = None
        self.lbl_val_modo = None
        self.lbl_val_fecha = None
        self.mod_bars_container = None

        self.init_ui()

        # Temporizador para actualización en tiempo real cada 3 segundos
        self.timer_refresh = QTimer(self)
        self.timer_refresh.timeout.connect(self.actualizar_datos_realtime)
        self.timer_refresh.start(3000)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "lbl_val_logins") and self.lbl_val_logins is not None:
            self.actualizar_datos_realtime()

    def cargar_config(self):
        cfg_path = self.ruta_usuario / "config.json"
        if cfg_path.exists():
            try:
                from controlador.auth.crypto_utils import process_config_for_load
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return process_config_for_load(json.load(f))
            except Exception:
                pass
        return {}

    def cargar_log_del_dia(self):
        """Carga el archivo JSON de logs correspondiente a la fecha de HOY o los logs más recientes"""
        hoy_str = datetime.datetime.now().strftime("%Y-%m-%d")
        logs_dir = self.ruta_usuario / "logs"
        today_log_path = logs_dir / f"{hoy_str}.json"

        if today_log_path.exists():
            try:
                with open(today_log_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        return data
            except Exception:
                pass

        if logs_dir.exists():
            for p in sorted(logs_dir.glob("*.json"), reverse=True):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list) and data:
                            return data
                except Exception:
                    pass
        return []

    def calcular_actividad_hoy(self, today_entries):
        """Calcula dinámicamente el tiempo y visitas de cada módulo a partir del log de HOY"""
        mod_stats = {}
        current_mod = None
        current_start_dt = None

        for item in today_entries:
            if not isinstance(item, dict):
                continue

            mod = item.get("modulo", "")
            msg = item.get("mensaje", "")
            ts_str = item.get("timestamp", "")

            new_mod = None
            if mod in ("AcciónUsuario", "AccionUsuario") and msg.startswith("Clic en Botón: "):
                target = msg.replace("Clic en Botón: ", "").strip()
                if target and not target.startswith("+") and not target.startswith("&") and len(target) < 25:
                    new_mod = target
            elif mod in ("Navegación", "Navegacion"):
                if "Modulo: " in msg:
                    target = msg.split(">")[0].replace("Modulo: ", "").strip()
                    if target:
                        new_mod = target
                elif "Selección de Pestaña: " in msg:
                    target = msg.replace("Selección de Pestaña: ", "").strip()
                    if target:
                        new_mod = target

            if new_mod:
                dt = None
                try:
                    dt = datetime.datetime.fromisoformat(ts_str)
                except Exception:
                    pass

                if dt and current_mod and current_start_dt:
                    delta = (dt - current_start_dt).total_seconds()
                    if 0 < delta < 14400:
                        if current_mod not in mod_stats:
                            mod_stats[current_mod] = {"visitas": 0, "tiempo_segundos": 0}
                        mod_stats[current_mod]["tiempo_segundos"] += int(delta)

                if new_mod not in mod_stats:
                    mod_stats[new_mod] = {"visitas": 0, "tiempo_segundos": 0}
                
                if current_mod != new_mod:
                    mod_stats[new_mod]["visitas"] += 1

                current_mod = new_mod
                current_start_dt = dt

        # Sumar el tiempo transcurrido en el módulo activo hasta el segundo actual (en vivo)
        if current_mod and current_start_dt:
            now_dt = datetime.datetime.now()
            live_delta = (now_dt - current_start_dt).total_seconds()
            if 0 < live_delta < 14400:
                if current_mod not in mod_stats:
                    mod_stats[current_mod] = {"visitas": 1, "tiempo_segundos": 0}
                mod_stats[current_mod]["tiempo_segundos"] += int(live_delta)

        return mod_stats

    def calcular_score_seguridad(self, config):
        score = 20
        if config.get("pin_lock"):
            score += 30
        modo_pin = config.get("pin_modo", "normal")
        if modo_pin == "siempre":
            score += 30
        elif modo_pin == "normal":
            score += 15
        if config.get("facial_enabled"):
            score += 10
        if config.get("idle_lock_minutes", 0) > 0:
            score += 10
        return min(100, score)

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 8, 10, 8)
        main_lay.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {bg_p}; }}")

        content = QWidget()
        content.setStyleSheet(f"background-color: {bg_p};")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # Header con fecha de hoy y botón de actualización inmediata
        hdr_row = QHBoxLayout()
        hoy_fecha = datetime.datetime.now().strftime("%d/%m/%Y")
        self.lbl_head = QLabel(f"📊 AUDITORÍA Y ACTIVIDAD EN TIEMPO REAL (HOY: {hoy_fecha})")
        self.lbl_head.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        self.lbl_head.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; margin-bottom: 2px;")
        hdr_row.addWidget(self.lbl_head)
        hdr_row.addStretch()

        btn_refresh_now = QPushButton("🔄 Actualizar Ahora")
        btn_refresh_now.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_refresh_now.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh_now.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #818CF8;
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
        """)
        btn_refresh_now.clicked.connect(self.actualizar_datos_realtime)
        hdr_row.addWidget(btn_refresh_now)
        lay.addLayout(hdr_row)

        config = self.cargar_config()

        # ── 1. TARJETAS DE MÉTRICAS RÁPIDAS ─────────────────────────────
        self.grid_cards = QHBoxLayout()
        self.grid_cards.setSpacing(10)

        self.lbl_val_logins = QLabel("0")
        self.lbl_val_score = QLabel(f"{self.calcular_score_seguridad(config)}%")
        self.lbl_val_modo = QLabel(config.get("pin_modo", "normal").capitalize())
        self.lbl_val_fecha = QLabel(config.get("fecha_registro", "2026-08-01")[:10])

        cards_data = [
            ("🔐 Eventos de Hoy", self.lbl_val_logins, "#3B82F6"),
            ("🛡️ Score Seguridad", self.lbl_val_score, "#10B981"),
            ("⚙️ Modo de PIN", self.lbl_val_modo, "#8B5CF6"),
            ("📅 Registro Cuenta", self.lbl_val_fecha, "#EC4899")
        ]

        for title, lbl_v, color in cards_data:
            c_frame = QFrame()
            c_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 8px;
                }}
            """)
            c_lay = QVBoxLayout(c_frame)
            c_lay.setContentsMargins(12, 10, 12, 10)
            c_lay.setSpacing(2)

            lbl_t = QLabel(title)
            lbl_t.setFont(QFont(self.font_family, 8))
            lbl_t.setStyleSheet("color: #AAB0B8;")

            lbl_v.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
            lbl_v.setStyleSheet(f"color: {color};")

            c_lay.addWidget(lbl_t)
            c_lay.addWidget(lbl_v)
            self.grid_cards.addWidget(c_frame)

        lay.addLayout(self.grid_cards)

        # ── 2. CONTENEDOR DE BARRAS DE ACTIVIDAD ──────────────────────
        self.mod_box = QFrame()
        self.mod_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }}
        """)
        self.mod_lay = QVBoxLayout(self.mod_box)
        self.mod_lay.setContentsMargins(14, 12, 14, 12)
        self.mod_lay.setSpacing(8)

        lbl_mod_t = QLabel("📈 Tiempo de Actividad del Día (Se reinicia diariamente)")
        lbl_mod_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_mod_t.setStyleSheet("color: white;")
        self.mod_lay.addWidget(lbl_mod_t)

        self.mod_bars_container = QVBoxLayout()
        self.mod_lay.addLayout(self.mod_bars_container)
        lay.addWidget(self.mod_box)

        # ── 3. TABLA DE REGISTRO DE AUDITORÍA DE HOY ──────────────────────
        tab_box = QFrame()
        tab_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }}
        """)
        tab_lay = QVBoxLayout(tab_box)
        tab_lay.setContentsMargins(14, 12, 14, 12)
        tab_lay.setSpacing(8)

        lbl_tab_t = QLabel("📋 Registro Oficial de Eventos de Hoy")
        lbl_tab_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_tab_t.setStyleSheet("color: white;")
        tab_lay.addWidget(lbl_tab_t)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Hora", "Evento / Módulo", "Estado"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
                gridline-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
            }}
            QHeaderView::section {{
                background-color: #121218;
                color: {self.colores.get('acento', '#6366F1')};
                font-weight: bold;
                padding: 5px;
                border: none;
            }}
        """)
        self.table.setFixedHeight(220)
        tab_lay.addWidget(self.table)
        lay.addWidget(tab_box)

        scroll.setWidget(content)
        main_lay.addWidget(scroll)

        self.actualizar_datos_realtime()

    def actualizar_datos_realtime(self):
        """Actualiza las barras y la tabla en tiempo real leyendo el JSON de HOY"""
        if not hasattr(self, "lbl_val_logins") or self.lbl_val_logins is None or not hasattr(self, "mod_bars_container") or self.mod_bars_container is None:
            return

        entries = self.cargar_log_del_dia()
        config = self.cargar_config()

        self.lbl_val_logins.setText(str(len(entries)))
        self.lbl_val_score.setText(f"{self.calcular_score_seguridad(config)}%")

        # 1. Limpiar barras anteriores
        while self.mod_bars_container.count():
            item = self.mod_bars_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Limpiar layouts internos
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget(): sub.widget().deleteLater()

        actividad_hoy = self.calcular_actividad_hoy(entries)

        if actividad_hoy:
            max_time = max([item["tiempo_segundos"] for item in actividad_hoy.values()] + [60])
            sorted_mods = sorted(actividad_hoy.items(), key=lambda x: x[1]["tiempo_segundos"], reverse=True)

            for idx_c, (mod_name, data) in enumerate(sorted_mods):
                sec = data.get("tiempo_segundos", 0)
                visitas = data.get("visitas", 0)
                mod_color = COLOR_PALETTE[idx_c % len(COLOR_PALETTE)]

                mins = sec // 60
                seg_rem = sec % 60
                if mins > 0:
                    time_fmt = f"{mins}m {seg_rem}s ({visitas} accesos)"
                else:
                    time_fmt = f"{sec}s ({visitas} accesos)"

                pct = int((sec / max_time) * 100) if max_time > 0 else 0
                if sec > 0 and pct == 0:
                    pct = 5

                row_widget = QWidget()
                row = QHBoxLayout(row_widget)
                row.setContentsMargins(0, 2, 0, 2)
                row.setSpacing(8)

                lbl_m = QLabel(f"📦 Módulo: {mod_name}")
                lbl_m.setFont(QFont(self.font_family, 9))
                lbl_m.setStyleSheet("color: #DDD;")
                lbl_m.setFixedWidth(200)

                pbar = QProgressBar()
                pbar.setValue(pct)
                pbar.setFixedHeight(10)
                pbar.setTextVisible(False)
                pbar.setStyleSheet(f"""
                    QProgressBar {{
                        background: {self.colores.get('bg_terciario', '#2D2D3D')};
                        border-radius: 5px;
                        border: none;
                    }}
                    QProgressBar::chunk {{
                        background-color: {mod_color};
                        border-radius: 5px;
                    }}
                """)

                lbl_pct = QLabel(time_fmt)
                lbl_pct.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
                lbl_pct.setStyleSheet(f"color: {mod_color};")
                lbl_pct.setFixedWidth(160)
                lbl_pct.setAlignment(Qt.AlignmentFlag.AlignRight)

                row.addWidget(lbl_m)
                row.addWidget(pbar, 1)
                row.addWidget(lbl_pct)
                self.mod_bars_container.addWidget(row_widget)
        else:
            lbl_empty = QLabel("ℹ️ No hay actividad registrada aún para hoy. Navega por MultiTool para generar registros.")
            lbl_empty.setFont(QFont(self.font_family, 9))
            lbl_empty.setStyleSheet("color: #AAB0B8; font-style: italic;")
            self.mod_bars_container.addWidget(lbl_empty)

        # 2. Actualizar Tabla de Auditoría de Hoy
        reversed_entries = list(reversed(entries))[:30]
        self.table.setRowCount(len(reversed_entries))

        for idx, entry in enumerate(reversed_entries):
            if isinstance(entry, dict):
                ts = entry.get("timestamp", "")
                hora_str = ts.split("T")[1][:8] if "T" in ts else ts
                mod_msg = f"[{entry.get('modulo', '')}] {entry.get('mensaje', '')}"
                st_str = entry.get("nivel", "INFO")
            else:
                hora_str = str(entry)
                mod_msg = "Evento de sistema"
                st_str = "INFO"

            item_time = QTableWidgetItem(hora_str)
            item_evt = QTableWidgetItem(mod_msg)
            item_st = QTableWidgetItem(f"✅ {st_str}")
            item_st.setForeground(QColor("#10B981"))

            self.table.setItem(idx, 0, item_time)
            self.table.setItem(idx, 1, item_evt)
            self.table.setItem(idx, 2, item_st)
