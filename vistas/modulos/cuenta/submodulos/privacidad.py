import json
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QComboBox, QMessageBox, QScrollArea, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class TabPrivacidad(QWidget):
    """Submódulo de Privacidad, Auto-Bloqueo por Inactividad y Gestión de Caché"""
    def __init__(self, parent, context, colores):
        super().__init__(parent)
        self.context = context
        self.colores = colores or {}
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.persona = getattr(context, "persona", "Usuario")
        self.font_family = "Segoe UI"

        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        self.init_ui()

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

        # Header ajustado sin espacio excesivo


        config = self.cargar_config()

        # ── 1. AUTO-BLOQUEO POR INACTIVIDAD ─────────────────────────────
        idle_card = QFrame()
        idle_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }}
        """)
        idle_lay = QVBoxLayout(idle_card)
        idle_lay.setContentsMargins(14, 12, 14, 12)
        idle_lay.setSpacing(8)

        lbl_idle_t = QLabel("⏱️ Auto-Bloqueo por Inactividad (Idle Auto-Lock)")
        lbl_idle_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_idle_t.setStyleSheet("color: white;")
        idle_lay.addWidget(lbl_idle_t)

        lbl_idle_sub = QLabel("Bloquea automáticamente MultiTool con tu PIN si se detecta inactividad sin mover el ratón ni escribir.")
        lbl_idle_sub.setFont(QFont(self.font_family, 9))
        lbl_idle_sub.setStyleSheet("color: #AAB0B8;")
        idle_lay.addWidget(lbl_idle_sub)

        row_idle = QHBoxLayout()
        row_idle.addWidget(QLabel("Tiempo de Inactividad:"))
        
        self.cb_idle = QComboBox()
        self.cb_idle.addItem("🚫 Desactivado", 0)
        self.cb_idle.addItem("⏱️ 5 Minutos", 5)
        self.cb_idle.addItem("⏱️ 10 Minutos", 10)
        self.cb_idle.addItem("⏱️ 15 Minutos", 15)
        self.cb_idle.addItem("⏱️ 30 Minutos", 30)

        idle_val = config.get("idle_lock_minutes", 0)
        idx = self.cb_idle.findData(idle_val)
        if idx != -1:
            self.cb_idle.setCurrentIndex(idx)

        self.cb_idle.currentIndexChanged.connect(self._guardar_idle_lock)
        self.cb_idle.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
                border-radius: 6px;
                padding: 5px 10px;
                border: 1px solid rgba(255,255,255,0.15);
            }}
        """)
        row_idle.addWidget(self.cb_idle, 1)
        idle_lay.addLayout(row_idle)
        lay.addWidget(idle_card)

        # ── 2. LIMPIEZA DE DATOS DE SESIÓN Y CACHÉ ──────────────────────
        clean_card = QFrame()
        clean_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }}
        """)
        clean_lay = QVBoxLayout(clean_card)
        clean_lay.setContentsMargins(14, 12, 14, 12)
        clean_lay.setSpacing(8)

        lbl_clean_t = QLabel("🧹 Limpieza de Rastro y Archivos Temporales")
        lbl_clean_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_clean_t.setStyleSheet("color: white;")
        clean_lay.addWidget(lbl_clean_t)

        lbl_clean_sub = QLabel("Elimina de forma segura la caché local, miniaturas generadas y archivos temporales para liberar espacio.")
        lbl_clean_sub.setFont(QFont(self.font_family, 9))
        lbl_clean_sub.setStyleSheet("color: #AAB0B8;")
        clean_lay.addWidget(lbl_clean_sub)

        clean_btns = QHBoxLayout()
        clean_btns.setSpacing(10)

        btn_cache = QPushButton("🗑️ Limpiar Caché y Temporales")
        btn_cache.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cache.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border-radius: 6px; padding: 8px 14px; font-weight: bold; border: none;")
        btn_cache.clicked.connect(self._limpiar_cache)

        btn_logs = QPushButton("📋 Purgar Registros de Logs")
        btn_logs.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logs.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border-radius: 6px; padding: 8px 14px; border: 1px solid rgba(255,255,255,0.1);")
        btn_logs.clicked.connect(self._purgar_logs)

        clean_btns.addWidget(btn_cache)
        clean_btns.addWidget(btn_logs)
        clean_lay.addLayout(clean_btns)
        lay.addWidget(clean_card)

        # ── 3. GESTOR DE PERFILES MULTIUSUARIO ──────────────────────────
        prof_card = QFrame()
        prof_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }}
        """)
        prof_lay = QVBoxLayout(prof_card)
        prof_lay.setContentsMargins(14, 12, 14, 12)
        prof_lay.setSpacing(8)

        lbl_prof_t = QLabel("👥 Gestión de Ubicación y Espacio de Trabajo")
        lbl_prof_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_prof_t.setStyleSheet("color: white;")
        prof_lay.addWidget(lbl_prof_t)

        lbl_prof_loc = QLabel(f"📂 Carpeta Local del Perfil:\n{self.ruta_usuario.resolve()}")
        lbl_prof_loc.setFont(QFont("Consolas", 8))
        lbl_prof_loc.setStyleSheet("color: #818CF8; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 6px;")
        lbl_prof_loc.setWordWrap(True)
        prof_lay.addWidget(lbl_prof_loc)

        scroll.setWidget(content)
        main_lay.addWidget(scroll)

    def _guardar_idle_lock(self):
        val = self.cb_idle.currentData()
        cfg = self.cargar_config()
        cfg["idle_lock_minutes"] = val
        from controlador.auth.crypto_utils import process_config_for_save
        with open(self.ruta_usuario / "config.json", "w", encoding="utf-8") as f:
            json.dump(process_config_for_save(cfg), f, indent=4)

    def _limpiar_cache(self):
        temp_dir = self.ruta_usuario / "temp"
        cache_dir = self.ruta_usuario / "cache"
        count = 0

        for d in [temp_dir, cache_dir]:
            if d.exists():
                try:
                    for f in d.iterdir():
                        if f.is_file():
                            f.unlink()
                            count += 1
                except Exception:
                    pass

        QMessageBox.information(self, "Limpieza Completa", f"¡Se han eliminado {count} archivos temporales de la caché del sistema!")

    def _purgar_logs(self):
        logs_dir = self.ruta_usuario / "logs"
        if logs_dir.exists():
            try:
                for f in logs_dir.iterdir():
                    if f.is_file() and f.suffix in [".log", ".txt", ".json"]:
                        f.unlink()
            except Exception:
                pass
        QMessageBox.information(self, "Logs Purgados", "¡Registros de depuración y logs del perfil purgados correctamente!")
