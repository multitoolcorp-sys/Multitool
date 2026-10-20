"""
scrum_proyectos.py — Metodología Scrum (Sprints, Product Backlog, Sprint Backlog y Story Points)
Permite planificar y ejecutar iteraciones ágiles dentro de cada proyecto.
"""
import uuid
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QComboBox, QLineEdit, QDialog, QMessageBox, QSpinBox,
    QProgressBar, QDateEdit, QDialogButtonBox, QTextEdit, QInputDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor


class TareaScrumCard(QFrame):
    """Tarjeta de tarea optimizada para metodología Scrum con Story Points y asignación de Sprint."""
    def __init__(self, tarea, colores, en_sprint=False, parent=None, on_action=None):
        super().__init__(parent)
        self.tarea = tarea
        self.colores = colores
        self.en_sprint = en_sprint
        self.on_action = on_action
        self._build()

    def _build(self):
        tid = self.tarea["id"]
        points = self.tarea.get("story_points", 3)
        prio = self.tarea.get("prioridad", "media")
        estado = self.tarea.get("estado", "todo")

        prio_color = {"alta": "#EF4444", "media": "#FBBF24", "baja": "#34D399"}.get(prio, "#FBBF24")
        estado_badge = {"todo": "📋 Por Hacer", "doing": "▶️ En Progreso", "done": "✅ Hecho"}.get(estado, "📋 Por Hacer")
        borde_color = "#34D399" if estado == "done" else "rgba(255,255,255,0.08)"

        self.setStyleSheet(f"""
            QFrame {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid {borde_color};
                border-radius: 8px;
                padding: 6px;
            }}
            QFrame:hover {{ border-color: {self.colores.get('acento', '#6366F1')}; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # Header: Story Points + Título
        top = QHBoxLayout()
        lbl_pts = QLabel(f"{points} SP")
        lbl_pts.setStyleSheet("background: rgba(99,102,241,0.25); color: #818CF8; border-radius: 4px; padding: 2px 6px; font-weight: bold; font-size: 10px;")
        top.addWidget(lbl_pts)

        lbl_tit = QLabel(self.tarea.get("titulo", "Sin título"))
        lbl_tit.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_tit.setStyleSheet("color: white;")
        lbl_tit.setWordWrap(True)
        top.addWidget(lbl_tit, 1)

        lay.addLayout(top)

        # Descripción
        desc = self.tarea.get("descripcion", "")
        if desc:
            lbl_desc = QLabel(desc[:75] + ("..." if len(desc) > 75 else ""))
            lbl_desc.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px;")
            lbl_desc.setWordWrap(True)
            lay.addWidget(lbl_desc)

        # Fila inferior: Estado y Botón de acción rápida
        bot = QHBoxLayout()
        lbl_st = QLabel(estado_badge)
        lbl_st.setStyleSheet(f"color: {prio_color}; font-size: 10px; font-weight: bold;")
        bot.addWidget(lbl_st)
        bot.addStretch()

        if self.en_sprint:
            # Botones para cambiar estado dentro del Sprint
            if estado != "done":
                btn_done = QPushButton("✅ Hecho")
                btn_done.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_done.setStyleSheet("background: rgba(52,211,153,0.2); color: #34D399; border: 1px solid #34D399; border-radius: 4px; padding: 2px 6px; font-size: 9px; font-weight: bold;")
                btn_done.clicked.connect(lambda: self.on_action("marcar_done", tid))
                bot.addWidget(btn_done)

            btn_regresar = QPushButton("⬅️ Al Backlog")
            btn_regresar.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_regresar.setStyleSheet("background: rgba(255,255,255,0.06); color: #AAA; border: none; border-radius: 4px; padding: 2px 6px; font-size: 9px;")
            btn_regresar.clicked.connect(lambda: self.on_action("quitar_de_sprint", tid))
            bot.addWidget(btn_regresar)
        else:
            btn_add = QPushButton("➕ Al Sprint Activo")
            btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_add.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border: none; border-radius: 4px; padding: 3px 8px; font-size: 9px; font-weight: bold;")
            btn_add.clicked.connect(lambda: self.on_action("asignar_a_sprint", tid))
            bot.addWidget(btn_add)

        lay.addLayout(bot)


class SprintDialog(QDialog):
    """Diálogo para configurar un nuevo Sprint Scrum."""
    def __init__(self, colores, sprint=None, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.sprint = sprint or {}
        self.setWindowTitle("Configurar Sprint Scrum")
        self.setMinimumWidth(380)
        self.setStyleSheet(f"background: {colores.get('bg_principal', '#121218')}; color: white;")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(18, 18, 18, 18)

        lay.addWidget(QLabel("Nombre del Sprint:"))
        self.txt_nombre = QLineEdit(self.sprint.get("nombre", "Sprint 1"))
        self.txt_nombre.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 6px;")
        lay.addWidget(self.txt_nombre)

        lay.addWidget(QLabel("Meta / Objetivo del Sprint:"))
        self.txt_meta = QTextEdit()
        self.txt_meta.setPlaceholderText("¿Qué objetivo clave se logrará al completar este Sprint?...")
        self.txt_meta.setPlainText(self.sprint.get("meta", ""))
        self.txt_meta.setMaximumHeight(70)
        self.txt_meta.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 6px;")
        lay.addWidget(self.txt_meta)

        h_fechas = QHBoxLayout()
        v_ini = QVBoxLayout()
        v_ini.addWidget(QLabel("Fecha Inicio:"))
        self.d_ini = QDateEdit()
        self.d_ini.setCalendarPopup(True)
        self.d_ini.setDate(QDate.currentDate())
        v_ini.addWidget(self.d_ini)
        h_fechas.addLayout(v_ini)

        v_fin = QVBoxLayout()
        v_fin.addWidget(QLabel("Fecha Fin:"))
        self.d_fin = QDateEdit()
        self.d_fin.setCalendarPopup(True)
        self.d_fin.setDate(QDate.currentDate().addDays(14))
        v_fin.addWidget(self.d_fin)
        h_fechas.addLayout(v_fin)
        lay.addLayout(h_fechas)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_datos(self):
        return {
            "nombre": self.txt_nombre.text().strip() or "Sprint",
            "meta": self.txt_meta.toPlainText().strip(),
            "inicio": self.d_ini.date().toString("yyyy-MM-dd"),
            "fin": self.d_fin.date().toString("yyyy-MM-dd")
        }


class TabScrumProyectos(QWidget):
    """Submódulo de Gestión de Metodología Scrum (Sprints, Backlogs y Story Points)."""
    def __init__(self, parent=None, colores=None, callbacks=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.cb = callbacks or {}
        self.pid_activo = None

        self.init_ui()

    def init_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(16, 16, 16, 16)
        main_lay.setSpacing(12)

        # ── Header Superior ──
        hdr = QHBoxLayout()
        lbl_tit = QLabel("🏃 GESTOR SCRUM & SPRINTS")
        lbl_tit.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        hdr.addWidget(lbl_tit)

        self.lbl_sprint_nombre = QLabel("Sprint: (Ninguno activo)")
        self.lbl_sprint_nombre.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        hdr.addWidget(self.lbl_sprint_nombre)

        hdr.addStretch()

        btn_crear_sprint = QPushButton("➕ Nuevo Sprint")
        btn_crear_sprint.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_crear_sprint.setStyleSheet(self._btn_style())
        btn_crear_sprint.clicked.connect(self._dialog_crear_sprint)
        hdr.addWidget(btn_crear_sprint)

        self.btn_estado_sprint = QPushButton("🚀 Iniciar Sprint")
        self.btn_estado_sprint.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_estado_sprint.setStyleSheet("background: #10B981; color: white; border-radius: 6px; padding: 5px 12px; font-weight: bold; font-size: 10px;")
        self.btn_estado_sprint.clicked.connect(self._toggle_estado_sprint)
        hdr.addWidget(self.btn_estado_sprint)

        main_lay.addLayout(hdr)

        # ── Card de Resumen de Métricas del Sprint Activo ──
        self.sprint_card = QFrame()
        self.sprint_card.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; border-radius: 10px; padding: 12px;")
        sc_lay = QVBoxLayout(self.sprint_card)
        sc_lay.setSpacing(6)

        self.lbl_sprint_meta = QLabel("Meta: No hay metas definidas para el Sprint actual.")
        self.lbl_sprint_meta.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 11px;")
        sc_lay.addWidget(self.lbl_sprint_meta)

        self.lbl_pts_info = QLabel("Puntos de Historia: 0 SP Comprometidos | 0 SP Hechos | 0 SP Restantes")
        self.lbl_pts_info.setStyleSheet("color: white; font-size: 10px; font-weight: bold;")
        sc_lay.addWidget(self.lbl_pts_info)

        self.pbar_sprint = QProgressBar()
        self.pbar_sprint.setFixedHeight(12)
        self.pbar_sprint.setValue(0)
        self.pbar_sprint.setTextVisible(False)
        self.pbar_sprint.setStyleSheet(f"""
            QProgressBar {{ background: rgba(255,255,255,0.06); border-radius: 6px; }}
            QProgressBar::chunk {{ background: {self.colores.get('acento', '#6366F1')}; border-radius: 6px; }}
        """)
        sc_lay.addWidget(self.pbar_sprint)
        main_lay.addWidget(self.sprint_card)

        # ── Dos Columnas: Sprint Backlog vs Product Backlog ──
        cols_lay = QHBoxLayout()
        cols_lay.setSpacing(14)

        # 1. Columna Sprint Backlog
        col_sb = QFrame()
        col_sb.setStyleSheet(f"background: rgba(18,18,24,0.6); border-radius: 10px; border-top: 3px solid #6366F1;")
        sb_lay = QVBoxLayout(col_sb)
        sb_lay.setContentsMargins(10, 10, 10, 10)
        sb_lay.setSpacing(8)

        sb_hdr = QHBoxLayout()
        lbl_sb_t = QLabel("🎯 SPRINT BACKLOG")
        lbl_sb_t.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_sb_t.setStyleSheet("color: #818CF8;")
        sb_hdr.addWidget(lbl_sb_t)
        self.lbl_sb_count = QLabel("0 tareas")
        self.lbl_sb_count.setStyleSheet("color: #888; font-size: 10px;")
        sb_hdr.addWidget(self.lbl_sb_count)
        sb_hdr.addStretch()
        sb_lay.addLayout(sb_hdr)

        scroll_sb = QScrollArea()
        scroll_sb.setWidgetResizable(True)
        scroll_sb.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.cont_sb = QWidget()
        self.lay_sb_items = QVBoxLayout(self.cont_sb)
        self.lay_sb_items.setSpacing(6)
        self.lay_sb_items.addStretch()
        scroll_sb.setWidget(self.cont_sb)
        sb_lay.addWidget(scroll_sb, 1)
        cols_lay.addWidget(col_sb, 1)

        # 2. Columna Product Backlog
        col_pb = QFrame()
        col_pb.setStyleSheet(f"background: rgba(18,18,24,0.6); border-radius: 10px; border-top: 3px solid #FBBF24;")
        pb_lay = QVBoxLayout(col_pb)
        pb_lay.setContentsMargins(10, 10, 10, 10)
        pb_lay.setSpacing(8)

        pb_hdr = QHBoxLayout()
        lbl_pb_t = QLabel("📋 PRODUCT BACKLOG")
        lbl_pb_t.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_pb_t.setStyleSheet("color: #FBBF24;")
        pb_hdr.addWidget(lbl_pb_t)
        self.lbl_pb_count = QLabel("0 tareas")
        self.lbl_pb_count.setStyleSheet("color: #888; font-size: 10px;")
        pb_hdr.addWidget(self.lbl_pb_count)
        pb_hdr.addStretch()

        btn_nueva_backlog = QPushButton("＋ Tarea")
        btn_nueva_backlog.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nueva_backlog.setStyleSheet("background: rgba(251,191,36,0.2); color: #FBBF24; border: 1px solid #FBBF24; border-radius: 4px; padding: 2px 8px; font-size: 9px; font-weight: bold;")
        btn_nueva_backlog.clicked.connect(self._crear_tarea_backlog)
        pb_hdr.addWidget(btn_nueva_backlog)
        pb_lay.addLayout(pb_hdr)

        scroll_pb = QScrollArea()
        scroll_pb.setWidgetResizable(True)
        scroll_pb.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.cont_pb = QWidget()
        self.lay_pb_items = QVBoxLayout(self.cont_pb)
        self.lay_pb_items.setSpacing(6)
        self.lay_pb_items.addStretch()
        scroll_pb.setWidget(self.cont_pb)
        pb_lay.addWidget(scroll_pb, 1)
        cols_lay.addWidget(col_pb, 1)

        main_lay.addLayout(cols_lay, 1)

    def _btn_style(self):
        return f"""
            QPushButton {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white;
                border: 1px solid rgba(255,255,255,0.1); border-radius: 6px;
                padding: 5px 12px; font-size: 10px; font-weight: bold;
            }}
            QPushButton:hover {{ border-color: {self.colores.get('acento', '#6366F1')}; }}
        """

    def configurar_proyecto(self, pid):
        self.pid_activo = pid
        self.refrescar_scrum()

    def refrescar_scrum(self):
        # Limpiar contenedores
        while self.lay_sb_items.count() > 1:
            it = self.lay_sb_items.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        while self.lay_pb_items.count() > 1:
            it = self.lay_pb_items.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        if not self.pid_activo or "get_proyectos" not in self.cb:
            self.lbl_sprint_nombre.setText("Sprint: (Ningún proyecto activo)")
            return

        proys = self.cb["get_proyectos"]()
        p = next((x for x in proys if x["id"] == self.pid_activo), None)
        if not p:
            return

        # Sprints del proyecto
        sprints = p.setdefault("sprints", [])
        sprint_activo = next((s for s in sprints if s.get("estado") == "activo"), None)
        if not sprint_activo and sprints:
            sprint_activo = sprints[0]

        if sprint_activo:
            st = sprint_activo.get("estado", "planificado")
            self.lbl_sprint_nombre.setText(f"Sprint Activo: {sprint_activo['nombre']} ({st.upper()})")
            self.lbl_sprint_meta.setText(f"Meta: {sprint_activo.get('meta', 'Sin meta especificada')}")
            self.btn_estado_sprint.setText("🏁 Completar Sprint" if st == "activo" else "🚀 Iniciar Sprint")
            self.btn_estado_sprint.setStyleSheet("background: #EF4444; color: white; border-radius: 6px; padding: 5px 12px; font-weight: bold; font-size: 10px;" if st == "activo" else "background: #10B981; color: white; border-radius: 6px; padding: 5px 12px; font-weight: bold; font-size: 10px;")
        else:
            self.lbl_sprint_nombre.setText("Sprint: (Crea tu primer Sprint)")
            self.lbl_sprint_meta.setText("Meta: Planifica tu iteración ágil creando un nuevo Sprint.")
            self.btn_estado_sprint.setText("🚀 Iniciar Sprint")

        sprint_id = sprint_activo["id"] if sprint_activo else None
        tareas = p.get("tareas", [])

        sb_tareas = []
        pb_tareas = []
        total_sp = 0
        hecho_sp = 0

        for t in tareas:
            # Asegurar campo story_points
            if "story_points" not in t:
                t["story_points"] = 3

            t_sprint = t.get("sprint_id")
            if sprint_id and t_sprint == sprint_id:
                sb_tareas.append(t)
                total_sp += t.get("story_points", 0)
                if t.get("estado") == "done":
                    hecho_sp += t.get("story_points", 0)
            else:
                pb_tareas.append(t)

        self.lbl_sb_count.setText(f"{len(sb_tareas)} tareas")
        self.lbl_pb_count.setText(f"{len(pb_tareas)} tareas")

        rem_sp = total_sp - hecho_sp
        self.lbl_pts_info.setText(f"Puntos de Historia: {total_sp} SP Comprometidos | {hecho_sp} SP Completados | {rem_sp} SP Restantes")
        pct = int(hecho_sp / total_sp * 100) if total_sp > 0 else 0
        self.pbar_sprint.setValue(pct)

        # Poblar Sprint Backlog
        for t in sb_tareas:
            card = TareaScrumCard(t, self.colores, en_sprint=True, on_action=self._on_tarea_action)
            self.lay_sb_items.insertWidget(self.lay_sb_items.count() - 1, card)

        # Poblar Product Backlog
        for t in pb_tareas:
            card = TareaScrumCard(t, self.colores, en_sprint=False, on_action=self._on_tarea_action)
            self.lay_pb_items.insertWidget(self.lay_pb_items.count() - 1, card)

    def _on_tarea_action(self, accion, tid):
        if not self.pid_activo:
            return
        proys = self.cb["get_proyectos"]()
        p = next((x for x in proys if x["id"] == self.pid_activo), None)
        if not p:
            return
        t = next((x for x in p.get("tareas", []) if x["id"] == tid), None)
        if not t:
            return

        sprint_activo = next((s for s in p.get("sprints", []) if s.get("estado") == "activo"), None)
        if not sprint_activo and p.get("sprints"):
            sprint_activo = p["sprints"][0]

        if accion == "asignar_a_sprint":
            if not sprint_activo:
                QMessageBox.information(self, "Aviso", "Crea un Sprint primero para asignarle tareas.")
                return
            t["sprint_id"] = sprint_activo["id"]
        elif accion == "quitar_de_sprint":
            t["sprint_id"] = None
        elif accion == "marcar_done":
            t["estado"] = "done"

        if "guardar_datos" in self.cb:
            self.cb["guardar_datos"]()
        self.refrescar_scrum()

    def _dialog_crear_sprint(self):
        if not self.pid_activo:
            QMessageBox.information(self, "Aviso", "Selecciona un proyecto primero.")
            return
        dlg = SprintDialog(self.colores, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            datos = dlg.get_datos()
            proys = self.cb["get_proyectos"]()
            p = next((x for x in proys if x["id"] == self.pid_activo), None)
            if p:
                sprint_id = str(uuid.uuid4())
                sprint_data = {
                    "id": sprint_id,
                    "nombre": datos["nombre"],
                    "meta": datos["meta"],
                    "inicio": datos["inicio"],
                    "fin": datos["fin"],
                    "estado": "activo" if not p.get("sprints") else "planificado"
                }
                p.setdefault("sprints", []).append(sprint_data)
                if "guardar_datos" in self.cb:
                    self.cb["guardar_datos"]()
                self.refrescar_scrum()

    def _toggle_estado_sprint(self):
        if not self.pid_activo:
            return
        proys = self.cb["get_proyectos"]()
        p = next((x for x in proys if x["id"] == self.pid_activo), None)
        if not p or not p.get("sprints"):
            return
        sprint_activo = next((s for s in p["sprints"] if s.get("estado") == "activo"), None)
        if sprint_activo:
            sprint_activo["estado"] = "completado"
            QMessageBox.information(self, "Sprint Completado", f"¡Felicitaciones! Has completado '{sprint_activo['nombre']}'.")
        else:
            sprint = p["sprints"][0]
            sprint["estado"] = "activo"
            QMessageBox.information(self, "Sprint Iniciado", f"Se ha iniciado '{sprint['nombre']}'.")
        if "guardar_datos" in self.cb:
            self.cb["guardar_datos"]()
        self.refrescar_scrum()

    def _crear_tarea_backlog(self):
        if not self.pid_activo:
            return
        tit, ok = QInputDialog.getText(self, "Nueva Tarea de Backlog", "Título de la historia / tarea:")
        if ok and tit.strip():
            pts, ok2 = QInputDialog.getInt(self, "Story Points", "Estimación en Story Points (1, 2, 3, 5, 8):", 3, 1, 21)
            if not ok2: pts = 3
            if "nueva_tarea" in self.cb:
                self.cb["nueva_tarea"](self.pid_activo, tit.strip(), "", "media", "", "todo")
                # actualizar story points en la tarea recién creada
                proys = self.cb["get_proyectos"]()
                p = next((x for x in proys if x["id"] == self.pid_activo), None)
                if p and p.get("tareas"):
                    p["tareas"][-1]["story_points"] = pts
                    if "guardar_datos" in self.cb:
                        self.cb["guardar_datos"]()
            self.refrescar_scrum()

    def actualizar_tema(self, colores):
        self.colores = colores
        self.refrescar_scrum()
