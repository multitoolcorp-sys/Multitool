"""
estadisticas.py - Submódulo de Estadísticas y Métricas de Rendimiento de Proyectos
"""
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QScrollArea, QComboBox, QGridLayout, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


class TabEstadisticasProyectos(QWidget):
    """Vista de Métricas y Estadísticas de Productividad de Proyectos"""
    def __init__(self, parent=None, colores=None, get_proyectos_cb=None, callbacks=None, fn_obtener_proyectos=None):
        super().__init__(parent)
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }
        cb_dict = callbacks if isinstance(callbacks, dict) else {}
        self.get_proyectos_cb = get_proyectos_cb or fn_obtener_proyectos or cb_dict.get("get_proyectos")

        self.init_ui()

    def init_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"""
            TabEstadisticasProyectos {{ background-color: {bg_main}; color: white; }}
            QWidget {{ background-color: transparent; color: white; }}
            QScrollArea {{ border: none; background: transparent; }}
        """)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(16, 16, 16, 16)
        main_lay.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        lbl_title = QLabel("📊 Métricas & Estadísticas de Productividad")
        lbl_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        top_bar.addWidget(lbl_title)

        top_bar.addStretch()

        lbl_f = QLabel("Proyecto:")
        lbl_f.setStyleSheet("color: #AAA; font-size: 11px;")
        top_bar.addWidget(lbl_f)

        self.combo_filtro_proy = QComboBox()
        self.combo_filtro_proy.addItem("📂 Todos los Proyectos", None)
        self.combo_filtro_proy.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 4px 10px; font-size: 11px;
            }}
        """)
        self.combo_filtro_proy.currentIndexChanged.connect(self._on_filtro_cambiado)
        top_bar.addWidget(self.combo_filtro_proy)

        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 5px 12px; font-weight: bold;
            }}
            QPushButton:hover {{ border-color: {self.colores.get('acento', '#6366F1')}; }}
        """)
        btn_refresh.clicked.connect(self.actualizar_metricas)
        top_bar.addWidget(btn_refresh)
        main_lay.addLayout(top_bar)

        # Scroll principal
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        c_lay = QVBoxLayout(container)
        c_lay.setSpacing(14)

        # Tarjetas resumidas (KPIs)
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(12)

        self.card_total_p = self._crear_kpi_card("📂 Total Proyectos", "0", "#6366F1")
        self.card_total_t = self._crear_kpi_card("📝 Total Tareas", "0", "#3B82F6")
        self.card_done_t = self._crear_kpi_card("✅ Tareas Hechas", "0", "#34D399")
        self.card_venc_t = self._crear_kpi_card("⚠️ Tareas Vencidas", "0", "#F87171")

        kpi_grid.addWidget(self.card_total_p, 0, 0)
        kpi_grid.addWidget(self.card_total_t, 0, 1)
        kpi_grid.addWidget(self.card_done_t, 0, 2)
        kpi_grid.addWidget(self.card_venc_t, 0, 3)

        c_lay.addLayout(kpi_grid)

        # Barra de Eficiencia Global
        eff_card = QFrame()
        eff_card.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; border-radius: 10px; padding: 14px;")
        eff_lay = QVBoxLayout(eff_card)
        eff_lay.setSpacing(6)

        self.lbl_eff_title = QLabel("🎯 Eficiencia Global de Cumplimiento: 0%")
        self.lbl_eff_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_eff_title.setStyleSheet("color: white;")
        eff_lay.addWidget(self.lbl_eff_title)

        self.pbar_eff = QProgressBar()
        self.pbar_eff.setFixedHeight(18)
        self.pbar_eff.setValue(0)
        self.pbar_eff.setTextVisible(True)
        self.pbar_eff.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white; font-weight: bold; border-radius: 9px; text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {self.colores.get('acento', '#6366F1')};
                border-radius: 9px;
            }}
        """)
        eff_lay.addWidget(self.pbar_eff)
        c_lay.addWidget(eff_card)

        # Desglose por Prioridad y Estado
        details_grid = QGridLayout()
        details_grid.setSpacing(12)

        # Tarjeta Prioridades
        prio_card = QFrame()
        prio_card.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; border-radius: 10px; padding: 14px;")
        prio_lay = QVBoxLayout(prio_card)
        prio_lay.setSpacing(8)

        lbl_prio_h = QLabel("🔴 Tareas por Nivel de Prioridad")
        lbl_prio_h.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_prio_h.setStyleSheet("color: white;")
        prio_lay.addWidget(lbl_prio_h)

        self.lbl_prio_alta = QLabel("🔴 Alta: 0 tareas")
        self.lbl_prio_alta.setStyleSheet("color: #F87171; font-weight: bold;")
        prio_lay.addWidget(self.lbl_prio_alta)

        self.lbl_prio_media = QLabel("🟡 Media: 0 tareas")
        self.lbl_prio_media.setStyleSheet("color: #FBBF24; font-weight: bold;")
        prio_lay.addWidget(self.lbl_prio_media)

        self.lbl_prio_baja = QLabel("🟢 Baja: 0 tareas")
        self.lbl_prio_baja.setStyleSheet("color: #34D399; font-weight: bold;")
        prio_lay.addWidget(self.lbl_prio_baja)

        details_grid.addWidget(prio_card, 0, 0)

        # Tarjeta Estados
        state_card = QFrame()
        state_card.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; border-radius: 10px; padding: 14px;")
        state_lay = QVBoxLayout(state_card)
        state_lay.setSpacing(8)

        lbl_state_h = QLabel("📌 Estado de Kanban Actual")
        lbl_state_h.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_state_h.setStyleSheet("color: white;")
        state_lay.addWidget(lbl_state_h)

        self.lbl_st_todo = QLabel("📝 Por Hacer: 0")
        self.lbl_st_todo.setStyleSheet("color: #AAB0B8;")
        state_lay.addWidget(self.lbl_st_todo)

        self.lbl_st_doing = QLabel("▶️ En Progreso: 0")
        self.lbl_st_doing.setStyleSheet("color: #6366F1; font-weight: bold;")
        state_lay.addWidget(self.lbl_st_doing)

        self.lbl_st_done = QLabel("✅ Completadas: 0")
        self.lbl_st_done.setStyleSheet("color: #34D399; font-weight: bold;")
        state_lay.addWidget(self.lbl_st_done)

        details_grid.addWidget(state_card, 0, 1)

        c_lay.addLayout(details_grid)
        c_lay.addStretch()

        scroll.setWidget(container)
        main_lay.addWidget(scroll)

    def _crear_kpi_card(self, titulo, valor_ini, color):
        card = QFrame()
        card.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; border-radius: 10px; padding: 12px;")
        lay = QVBoxLayout(card)
        lay.setSpacing(4)

        lbl_t = QLabel(titulo)
        lbl_t.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px;")
        lay.addWidget(lbl_t)

        lbl_val = QLabel(valor_ini)
        lbl_val.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {color};")
        lay.addWidget(lbl_val)

        card.lbl_val = lbl_val
        return card

    def _on_filtro_cambiado(self):
        self.actualizar_metricas(recargar_combo=False)

    def actualizar_metricas(self, recargar_combo=True):
        proyectos = self.get_proyectos_cb() if self.get_proyectos_cb else []

        if recargar_combo:
            cur_id = self.combo_filtro_proy.currentData()
            self.combo_filtro_proy.blockSignals(True)
            self.combo_filtro_proy.clear()
            self.combo_filtro_proy.addItem("📂 Todos los Proyectos", None)
            idx_restore = 0
            for p in proyectos:
                if not p.get("archivado"):
                    self.combo_filtro_proy.addItem(f"● {p.get('nombre', 'Proyecto')}", p["id"])
                    if p["id"] == cur_id:
                        idx_restore = self.combo_filtro_proy.count() - 1
            self.combo_filtro_proy.setCurrentIndex(idx_restore)
            self.combo_filtro_proy.blockSignals(False)

        filtro_pid = self.combo_filtro_proy.currentData()
        if filtro_pid:
            proyectos_analizar = [p for p in proyectos if p["id"] == filtro_pid]
        else:
            proyectos_analizar = [p for p in proyectos if not p.get("archivado")]

        total_proyectos = len(proyectos_analizar)
        total_tareas = 0
        hechas = 0
        vencidas = 0
        prio_alta = 0
        prio_media = 0
        prio_baja = 0
        st_todo = 0
        st_doing = 0
        st_done = 0
        total_sp = 0
        hecho_sp = 0

        hoy = date.today()

        for p in proyectos_analizar:
            tareas = p.get("tareas", [])
            total_tareas += len(tareas)
            for t in tareas:
                sp = t.get("story_points", 0)
                total_sp += sp

                est = t.get("estado", "todo")
                if est == "todo":
                    st_todo += 1
                elif est == "doing":
                    st_doing += 1
                elif est == "done":
                    st_done += 1
                    hechas += 1
                    hecho_sp += sp

                prio = t.get("prioridad", "media")
                if prio == "alta":
                    prio_alta += 1
                elif prio == "media":
                    prio_media += 1
                elif prio == "baja":
                    prio_baja += 1

                fecha = t.get("fecha_limite", "")
                if fecha and est != "done":
                    try:
                        if date.fromisoformat(fecha) < hoy:
                            vencidas += 1
                    except Exception:
                        pass

        self.card_total_p.lbl_val.setText(str(total_proyectos))
        self.card_total_t.lbl_val.setText(str(total_tareas))
        self.card_done_t.lbl_val.setText(str(hechas))
        self.card_venc_t.lbl_val.setText(str(vencidas))

        eff = (hechas / total_tareas * 100) if total_tareas > 0 else 0
        txt_sp = f" | ⚡ {hecho_sp}/{total_sp} SP" if total_sp > 0 else ""
        self.lbl_eff_title.setText(f"🎯 Cumplimiento: {eff:.1f}% ({hechas}/{total_tareas} tareas{txt_sp})")
        self.pbar_eff.setValue(int(eff))

        self.lbl_prio_alta.setText(f"🔴 Alta: {prio_alta} tareas")
        self.lbl_prio_media.setText(f"🟡 Media: {prio_media} tareas")
        self.lbl_prio_baja.setText(f"🟢 Baja: {prio_baja} tareas")

        self.lbl_st_todo.setText(f"📝 Por Hacer: {st_todo}")
        self.lbl_st_doing.setText(f"▶️ En Progreso: {st_doing}")
        self.lbl_st_done.setText(f"✅ Completadas: {st_done}")

    def actualizar_tema(self, colores):
        self.colores = colores
        bg_main = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"""
            TabEstadisticasProyectos {{ background-color: {bg_main}; color: white; }}
            QWidget {{ background-color: transparent; color: white; }}
            QScrollArea {{ border: none; background: transparent; }}
        """)
        self.actualizar_metricas()
