"""
ProyectosGUI — Interfaz visual del Gestor de Proyectos / TODO Kanban
"""
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSplitter, QLineEdit, QTextEdit, QComboBox, QDateEdit,
    QDialog, QDialogButtonBox, QMenu, QStackedWidget, QGridLayout,
    QSizePolicy, QToolButton, QListWidget, QListWidgetItem, QMessageBox,
    QSpinBox
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QSize, QMimeData
from PyQt6.QtGui import QFont, QColor, QAction, QCursor, QDrag

# Prioridades
PRIORIDADES = {
    "alta":  ("🔴", "#EF4444"),
    "media": ("🟡", "#FBBF24"),
    "baja":  ("🟢", "#34D399"),
}
COLORES_PROYECTO = [
    "#6366F1", "#EC4899", "#10B981", "#FBBF24",
    "#3B82F6", "#F59E0B", "#8B5CF6", "#06B6D4",
    "#EF4444", "#84CC16"
]


class TareaCard(QFrame):
    """Tarjeta visual de una tarea dentro del tablero Kanban."""
    mover_signal = pyqtSignal(str, str)  # (tid, nuevo_estado)
    editar_signal = pyqtSignal(str)      # tid
    eliminar_signal = pyqtSignal(str)    # tid
    duplicar_signal = pyqtSignal(str)    # tid

    def __init__(self, tarea, colores, parent=None):
        super().__init__(parent)
        self.tarea = tarea
        self.colores = colores
        self.tid = tarea["id"]
        self._build()

    def _build(self):
        prio_icon, prio_color = PRIORIDADES.get(self.tarea.get("prioridad", "media"), ("🟡", "#FBBF24"))
        fecha = self.tarea.get("fecha_limite", "")
        vencida = False
        if fecha:
            try:
                vencida = date.fromisoformat(fecha) < date.today()
            except Exception:
                pass

        border_color = "#EF4444" if vencida else "rgba(255,255,255,0.06)"
        self.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 2px;
            }}
            QFrame:hover {{ border-color: rgba(255,255,255,0.15); }}
        """)
        self.setMaximumWidth(280)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)

        # Cabecera: prioridad + título + menú
        top = QHBoxLayout()
        lbl_prio = QLabel(prio_icon)
        lbl_prio.setFixedWidth(16)
        lbl_prio.setStyleSheet(f"color: {prio_color}; font-size: 11px;")
        top.addWidget(lbl_prio)

        lbl_titulo = QLabel(self.tarea.get("titulo", "Sin título"))
        lbl_titulo.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet("color: white;")
        lbl_titulo.setWordWrap(True)
        top.addWidget(lbl_titulo, 1)

        btn_menu = QToolButton()
        btn_menu.setText("⋮")
        btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_menu.setStyleSheet("background: transparent; color: #888; border: none; font-size: 14px;")
        btn_menu.clicked.connect(self._mostrar_menu)
        top.addWidget(btn_menu)
        lay.addLayout(top)

        # Descripción (truncada)
        desc = self.tarea.get("descripcion", "")
        if desc:
            lbl_desc = QLabel(desc[:80] + ("..." if len(desc) > 80 else ""))
            lbl_desc.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 10px;")
            lbl_desc.setWordWrap(True)
            lay.addWidget(lbl_desc)

        # Badges: Etiquetas, Story Points y Checklist de subtareas
        badges_lay = QHBoxLayout()
        badges_lay.setSpacing(4)
        has_badges = False

        tag = self.tarea.get("etiqueta", "").strip()
        if tag:
            has_badges = True
            lbl_tag = QLabel(f"🏷️ {tag}")
            lbl_tag.setStyleSheet("background: rgba(99,102,241,0.22); color: #A5B4FC; border-radius: 4px; padding: 1px 5px; font-size: 9px; font-weight: bold;")
            badges_lay.addWidget(lbl_tag)

        sp = self.tarea.get("story_points")
        if sp is not None:
            has_badges = True
            lbl_sp = QLabel(f"⚡ {sp} SP")
            lbl_sp.setStyleSheet("background: rgba(251,191,36,0.18); color: #FBBF24; border-radius: 4px; padding: 1px 5px; font-size: 9px; font-weight: bold;")
            badges_lay.addWidget(lbl_sp)

        subtareas = self.tarea.get("subtareas", [])
        if subtareas:
            has_badges = True
            completas = sum(1 for st in subtareas if isinstance(st, dict) and st.get("hecho"))
            total_st = len(subtareas)
            lbl_chk = QLabel(f"☑ {completas}/{total_st}")
            lbl_chk.setStyleSheet("background: rgba(52,211,153,0.18); color: #34D399; border-radius: 4px; padding: 1px 5px; font-size: 9px; font-weight: bold;")
            badges_lay.addWidget(lbl_chk)

        if has_badges:
            badges_lay.addStretch()
            lay.addLayout(badges_lay)

        # Fecha límite
        if fecha:
            color_fecha = "#EF4444" if vencida else self.colores['fg_secundario']
            lbl_fecha = QLabel(f"📅 {fecha}" + (" ⚠️ Vencida" if vencida else ""))
            lbl_fecha.setStyleSheet(f"color: {color_fecha}; font-size: 9px;")
            lay.addWidget(lbl_fecha)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.tid)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)
        super().mousePressEvent(event)

    def _mostrar_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {self.colores['bg_terciario']}; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; }}
            QMenu::item {{ color: white; padding: 6px 20px; }}
            QMenu::item:selected {{ background: {self.colores['acento']}; border-radius: 4px; }}
        """)
        estado = self.tarea.get("estado", "todo")
        if estado != "todo":
            a = menu.addAction("⬅️ Mover a Por Hacer")
            a.triggered.connect(lambda: self.mover_signal.emit(self.tid, "todo"))
        if estado != "doing":
            a = menu.addAction("▶️ Mover a En Progreso")
            a.triggered.connect(lambda: self.mover_signal.emit(self.tid, "doing"))
        if estado != "done":
            a = menu.addAction("✅ Mover a Hecho")
            a.triggered.connect(lambda: self.mover_signal.emit(self.tid, "done"))
        menu.addSeparator()
        a = menu.addAction("✏️ Editar")
        a.triggered.connect(lambda: self.editar_signal.emit(self.tid))
        a = menu.addAction("📄 Duplicar")
        a.triggered.connect(lambda: self.duplicar_signal.emit(self.tid))
        a = menu.addAction("🗑️ Eliminar")
        a.triggered.connect(lambda: self.eliminar_signal.emit(self.tid))
        menu.exec(QCursor.pos())


class TareaDialog(QDialog):
    """Diálogo para crear o editar una tarea."""
    def __init__(self, colores, tarea=None, estado_inicial=None, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.tarea = tarea or {}
        self.estado_inicial = estado_inicial
        self.setWindowTitle("Editar tarea" if tarea else "Nueva tarea")
        self.setMinimumWidth(440)
        self.setStyleSheet(f"""
            QDialog {{ background: {colores['bg_principal']}; }}
            QLabel {{ color: white; font-size: 11px; }}
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox {{
                background: {colores['bg_secundario']}; color: white; border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.1); padding: 6px;
            }}
            QPushButton {{
                background: {colores['acento']}; color: white; border-radius: 6px;
                padding: 6px 20px; border: none;
            }}
            QPushButton:hover {{ background: {colores['acento_hover']}; }}
        """)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 20)

        lay.addWidget(QLabel("Título:"))
        self.txt_titulo = QLineEdit(self.tarea.get("titulo", ""))
        self.txt_titulo.setPlaceholderText("Título de la tarea...")
        lay.addWidget(self.txt_titulo)

        lay.addWidget(QLabel("Descripción:"))
        self.txt_desc = QTextEdit()
        self.txt_desc.setPlainText(self.tarea.get("descripcion", ""))
        self.txt_desc.setMaximumHeight(70)
        lay.addWidget(self.txt_desc)

        h_tags = QHBoxLayout()
        v_tag = QVBoxLayout()
        v_tag.addWidget(QLabel("Etiqueta / Tag:"))
        self.txt_etiqueta = QLineEdit(self.tarea.get("etiqueta", ""))
        self.txt_etiqueta.setPlaceholderText("Ej: Frontend, Bug, Diseño...")
        v_tag.addWidget(self.txt_etiqueta)
        h_tags.addLayout(v_tag)

        v_sp = QVBoxLayout()
        v_sp.addWidget(QLabel("Story Points (SP):"))
        self.sp_points = QSpinBox()
        self.sp_points.setRange(1, 100)
        self.sp_points.setValue(self.tarea.get("story_points", 3))
        v_sp.addWidget(self.sp_points)
        h_tags.addLayout(v_sp)
        lay.addLayout(h_tags)

        h = QHBoxLayout()
        # Prioridad
        v_prio = QVBoxLayout()
        v_prio.addWidget(QLabel("Prioridad:"))
        self.combo_prio = QComboBox()
        for k, (icon, _) in PRIORIDADES.items():
            self.combo_prio.addItem(f"{icon} {k.capitalize()}", k)
        idx = list(PRIORIDADES.keys()).index(self.tarea.get("prioridad", "media"))
        self.combo_prio.setCurrentIndex(idx)
        v_prio.addWidget(self.combo_prio)
        h.addLayout(v_prio)

        # Estado
        v_est = QVBoxLayout()
        v_est.addWidget(QLabel("Estado:"))
        self.combo_est = QComboBox()
        for key, label in [("todo", "📋 Por Hacer"), ("doing", "▶️ En Progreso"), ("done", "✅ Hecho")]:
            self.combo_est.addItem(label, key)
        est = self.tarea.get("estado", self.estado_inicial or "todo")
        self.combo_est.setCurrentIndex(["todo", "doing", "done"].index(est) if est in ["todo", "doing", "done"] else 0)
        v_est.addWidget(self.combo_est)
        h.addLayout(v_est)

        # Fecha Límite
        v_fecha = QVBoxLayout()
        v_fecha.addWidget(QLabel("Fecha Límite:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        fl = self.tarea.get("fecha_limite", "")
        if fl:
            try:
                d = date.fromisoformat(fl)
                self.date_edit.setDate(QDate(d.year, d.month, d.day))
            except Exception:
                self.date_edit.setDate(QDate.currentDate())
        else:
            self.date_edit.setDate(QDate.currentDate())
        v_fecha.addWidget(self.date_edit)
        h.addLayout(v_fecha)
        lay.addLayout(h)

        self.chk_sin_fecha = QPushButton("Sin fecha límite")
        self.chk_sin_fecha.setCheckable(True)
        self.chk_sin_fecha.setChecked(not bool(fl))
        self.chk_sin_fecha.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.05); }
            QPushButton:checked { background: rgba(99,102,241,0.3); }
        """)
        lay.addWidget(self.chk_sin_fecha)

        lay.addWidget(QLabel("Checklist / Subtareas (una por línea, anteponer [x] si completada):"))
        self.txt_subtareas = QTextEdit()
        self.txt_subtareas.setMaximumHeight(65)
        self.txt_subtareas.setPlaceholderText("Diseñar mockup UI\n[x] Crear estructura base\nProbar en navegador")
        st_lines = []
        for item in self.tarea.get("subtareas", []):
            if isinstance(item, dict):
                pref = "[x] " if item.get("hecho") else ""
                st_lines.append(pref + item.get("titulo", ""))
            elif isinstance(item, str):
                st_lines.append(item)
        self.txt_subtareas.setPlainText("\n".join(st_lines))
        lay.addWidget(self.txt_subtareas)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_datos(self):
        fecha = "" if self.chk_sin_fecha.isChecked() else self.date_edit.date().toString("yyyy-MM-dd")
        raw_st = self.txt_subtareas.toPlainText().splitlines()
        subtareas = []
        for line in raw_st:
            line_str = line.strip()
            if not line_str:
                continue
            hecho = False
            if line_str.startswith("[x] ") or line_str.startswith("[X] "):
                hecho = True
                line_str = line_str[4:].strip()
            elif line_str.startswith("[] ") or line_str.startswith("[ ] "):
                line_str = line_str[line_str.find("]") + 1:].strip()
            subtareas.append({"titulo": line_str, "hecho": hecho})

        return {
            "titulo": self.txt_titulo.text().strip(),
            "descripcion": self.txt_desc.toPlainText().strip(),
            "prioridad": self.combo_prio.currentData(),
            "estado": self.combo_est.currentData(),
            "fecha_limite": fecha,
            "etiqueta": self.txt_etiqueta.text().strip(),
            "story_points": self.sp_points.value(),
            "subtareas": subtareas,
        }


class KanbanColumna(QFrame):
    """Una columna del tablero Kanban."""
    def __init__(self, titulo, estado, colores, parent_gui=None, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.colores = colores
        self.parent_gui = parent_gui
        self._cards = []
        self.setAcceptDrops(True)

        color_col = {"todo": "#6366F1", "doing": "#FBBF24", "done": "#34D399"}.get(estado, "#888")
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(18,18,24,0.6);
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.05);
                border-top: 3px solid {color_col};
            }}
        """)
        self.setMinimumWidth(270)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 10, 8, 8)
        lay.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        lbl = QLabel(titulo)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {color_col};")
        hdr.addWidget(lbl)
        self.lbl_count = QLabel("0")
        self.lbl_count.setStyleSheet(f"background: {color_col}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;")
        hdr.addWidget(self.lbl_count)
        hdr.addStretch()

        btn_add = QToolButton()
        btn_add.setText("＋")
        btn_add.setToolTip(f"Añadir tarea en {titulo}")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet("background: rgba(255,255,255,0.06); color: white; border: none; border-radius: 4px; font-weight: bold; padding: 2px 6px;")
        btn_add.clicked.connect(self._on_quick_add)
        hdr.addWidget(btn_add)
        lay.addLayout(hdr)

        # Scroll de tarjetas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollBar:vertical { width: 4px; }")

        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setSpacing(6)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)

        self.lbl_vacio = QLabel("Sin tareas aquí")
        self.lbl_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vacio.setStyleSheet("color: rgba(255,255,255,0.25); font-size: 11px; padding: 24px 0;")
        self.cards_layout.addWidget(self.lbl_vacio)

        self.cards_layout.addStretch()
        scroll.setWidget(self.cards_widget)
        lay.addWidget(scroll, 1)

    def _on_quick_add(self):
        if self.parent_gui:
            self.parent_gui._dialog_nueva_tarea(estado_inicial=self.estado)

    def limpiar(self):
        while self.cards_layout.count() > 2:
            item = self.cards_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()
        self.lbl_count.setText("0")
        self.lbl_vacio.setVisible(True)

    def agregar_tarjeta(self, card):
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        self._cards.append(card)
        self.lbl_count.setText(str(len(self._cards)))
        self.lbl_vacio.setVisible(False)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        tid = event.mimeData().text()
        if tid and self.parent_gui and self.parent_gui.pid_activo:
            self.parent_gui.cb["mover_tarea"](self.parent_gui.pid_activo, tid, self.estado)
            event.acceptProposedAction()


class ProyectosGUI(QWidget):
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.cb = callbacks
        self.pid_activo = None
        self._build()

    def _build(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Panel Izquierdo: Lista de Proyectos ───────────────────────────
        self.panel_izq = QFrame()
        self.panel_izq.setFixedWidth(240)
        self.panel_izq.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-right: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        iz_lay = QVBoxLayout(self.panel_izq)
        iz_lay.setContentsMargins(12, 16, 12, 12)
        iz_lay.setSpacing(8)

        # Título del panel
        lbl_tit = QLabel("📦 PROYECTOS")
        lbl_tit.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']}; letter-spacing: 1px;")
        iz_lay.addWidget(lbl_tit)

        # Búsqueda
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar proyecto...")
        self.txt_buscar.setStyleSheet(f"""
            QLineEdit {{ background: {self.colores['bg_terciario']}; color: white;
                border-radius: 6px; border: none; padding: 6px 10px; font-size: 11px; }}
        """)
        self.txt_buscar.textChanged.connect(self.filtrar_proyectos)
        iz_lay.addWidget(self.txt_buscar)

        # Lista de proyectos
        self.lista_proyectos = QListWidget()
        self.lista_proyectos.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; }}
            QListWidget::item {{ color: white; padding: 8px 10px; border-radius: 6px; margin-bottom: 2px; }}
            QListWidget::item:selected {{ background: {self.colores['acento']}; }}
            QListWidget::item:hover:!selected {{ background: rgba(255,255,255,0.04); }}
        """)
        self.lista_proyectos.itemClicked.connect(self._on_proyecto_click)
        self.lista_proyectos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lista_proyectos.customContextMenuRequested.connect(self._menu_proyecto)
        iz_lay.addWidget(self.lista_proyectos, 1)

        # Botón nuevo proyecto
        self.btn_nuevo_proy = QPushButton("＋ Nuevo Proyecto")
        self.btn_nuevo_proy.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_nuevo_proy.setFixedHeight(38)
        self.btn_nuevo_proy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nuevo_proy.setStyleSheet(f"""
            QPushButton {{ background: {self.colores['acento']}; color: white; border-radius: 8px; border: none; }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        self.btn_nuevo_proy.clicked.connect(lambda: self.cb["nuevo_proyecto"]())
        iz_lay.addWidget(self.btn_nuevo_proy)

        main.addWidget(self.panel_izq)

        # ── Panel Derecho: Tablero / Vacío ────────────────────────────────
        self.stack = QStackedWidget()
        main.addWidget(self.stack, 1)

        # Página 0: Vacío (sin proyecto seleccionado)
        self.pag_vacia = QWidget()
        v = QVBoxLayout(self.pag_vacia)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_empty = QLabel("📦")
        lbl_empty.setFont(QFont("Segoe UI", 48))
        lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl_empty)
        lbl_sel = QLabel("Selecciona o crea un proyecto\npara ver su tablero Kanban")
        lbl_sel.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 14px;")
        lbl_sel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl_sel)
        self.stack.addWidget(self.pag_vacia)

        # Página 1: Tablero
        self.pag_tablero = QWidget()
        self.pag_tablero.setStyleSheet(f"background: {self.colores['bg_principal']};")
        tab_main = QVBoxLayout(self.pag_tablero)
        tab_main.setContentsMargins(16, 16, 16, 16)
        tab_main.setSpacing(12)

        # Barra superior del tablero
        self.barra_tablero = QHBoxLayout()
        self.lbl_nombre_proy = QLabel("Proyecto")
        self.lbl_nombre_proy.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_nombre_proy.setStyleSheet("color: white;")
        self.barra_tablero.addWidget(self.lbl_nombre_proy)

        self.lbl_progreso = QLabel("")
        self.lbl_progreso.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        self.barra_tablero.addWidget(self.lbl_progreso)
        self.barra_tablero.addStretch()

        # Filtro de prioridad
        lbl_filtro = QLabel("Filtrar:")
        lbl_filtro.setStyleSheet("color: #AAA; font-size: 11px;")
        self.barra_tablero.addWidget(lbl_filtro)
        self.combo_filtro = QComboBox()
        self.combo_filtro.addItems(["Todas", "🔴 Alta", "🟡 Media", "🟢 Baja"])
        self.combo_filtro.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border-radius: 4px; padding: 4px 8px;")
        self.combo_filtro.currentIndexChanged.connect(lambda: self.mostrar_tablero(self.pid_activo))
        self.barra_tablero.addWidget(self.combo_filtro)

        # Búsqueda de tareas
        self.txt_buscar_tarea = QLineEdit()
        self.txt_buscar_tarea.setPlaceholderText("🔍 Buscar tarea...")
        self.txt_buscar_tarea.setMaximumWidth(160)
        self.txt_buscar_tarea.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border-radius: 6px; padding: 4px 8px; border: none;")
        self.txt_buscar_tarea.textChanged.connect(lambda: self.mostrar_tablero(self.pid_activo))
        self.barra_tablero.addWidget(self.txt_buscar_tarea)

        btn_nueva = QPushButton("＋ Tarea")
        btn_nueva.setFixedHeight(30)
        btn_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nueva.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px; border: none; padding: 0 12px; font-weight: bold;")
        btn_nueva.clicked.connect(self._dialog_nueva_tarea)
        self.barra_tablero.addWidget(btn_nueva)
        tab_main.addLayout(self.barra_tablero)

        # Columnas Kanban
        kanban_scroll = QScrollArea()
        kanban_scroll.setWidgetResizable(True)
        kanban_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        kanban_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        kanban_cont = QWidget()
        kanban_cont.setStyleSheet("background: transparent;")
        kanban_lay = QHBoxLayout(kanban_cont)
        kanban_lay.setSpacing(12)
        kanban_lay.setContentsMargins(0, 0, 0, 0)

        self.col_todo  = KanbanColumna("📋  POR HACER",    "todo",  self.colores, parent_gui=self)
        self.col_doing = KanbanColumna("▶️  EN PROGRESO",  "doing", self.colores, parent_gui=self)
        self.col_done  = KanbanColumna("✅  HECHO",         "done",  self.colores, parent_gui=self)
        for col in [self.col_todo, self.col_doing, self.col_done]:
            kanban_lay.addWidget(col, 1)
        kanban_lay.addStretch()
        kanban_scroll.setWidget(kanban_cont)
        tab_main.addWidget(kanban_scroll, 1)
        self.stack.addWidget(self.pag_tablero)

        self.stack.setCurrentIndex(0)
        self.refrescar_proyectos()

    # ── Proyectos ─────────────────────────────────────────────────────────
    def refrescar_proyectos(self):
        query = self.txt_buscar.text().strip().lower()
        self.lista_proyectos.clear()
        for p in self.cb["get_proyectos"]():
            if p.get("archivado"):
                continue
            if query and query not in p["nombre"].lower():
                continue
            tareas = p.get("tareas", [])
            tot = len(tareas)
            hechas = sum(1 for t in tareas if t.get("estado") == "done")
            pct = int(hechas / tot * 100) if tot else 0
            item = QListWidgetItem(f"●  {p['nombre']}  ({pct}%)")
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            item.setForeground(QColor(p.get("color", "#6366F1")))
            self.lista_proyectos.addItem(item)
            if p["id"] == self.pid_activo:
                self.lista_proyectos.setCurrentItem(item)

    def filtrar_proyectos(self):
        self.refrescar_proyectos()

    def _on_proyecto_click(self, item):
        pid = item.data(Qt.ItemDataRole.UserRole)
        self.cb["seleccionar_proyecto"](pid)

    def _menu_proyecto(self, pos):
        item = self.lista_proyectos.itemAt(pos)
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background: {self.colores['bg_terciario']}; border-radius: 6px; }} QMenu::item {{ color: white; padding: 6px 16px; }} QMenu::item:selected {{ background: {self.colores['acento']}; }}")
        menu.addAction("✏️ Renombrar", lambda: self.cb["renombrar_proyecto"](pid))
        menu.addAction("📦 Archivar",  lambda: self.cb["archivar_proyecto"](pid))
        menu.addSeparator()
        menu.addAction("🗑️ Eliminar",  lambda: self.cb["eliminar_proyecto"](pid))
        menu.exec(self.lista_proyectos.viewport().mapToGlobal(pos))

    # ── Tablero ──────────────────────────────────────────────────────────
    def mostrar_tablero(self, pid):
        if not pid:
            return
        self.pid_activo = pid
        proyectos = self.cb["get_proyectos"]()
        p = next((x for x in proyectos if x["id"] == pid), None)
        if not p:
            return

        self.stack.setCurrentIndex(1)
        self.lbl_nombre_proy.setText(f"● {p['nombre']}")
        self.lbl_nombre_proy.setStyleSheet(f"color: {p.get('color','white')}; font-size: 14px; font-weight: bold;")

        tareas = self.cb["get_tareas"](pid)
        total = len(tareas)
        hechas = sum(1 for t in tareas if t.get("estado") == "done")
        pct = int(hechas / total * 100) if total else 0
        self.lbl_progreso.setText(f"  {hechas}/{total} completadas ({pct}%)")

        # Aplicar filtros
        filtro_prio = ["", "alta", "media", "baja"][self.combo_filtro.currentIndex()]
        query_t = self.txt_buscar_tarea.text().strip().lower()

        def pasa_filtro(t):
            if filtro_prio and t.get("prioridad") != filtro_prio:
                return False
            if query_t and query_t not in t.get("titulo", "").lower() and query_t not in t.get("descripcion", "").lower():
                return False
            return True

        for col in [self.col_todo, self.col_doing, self.col_done]:
            col.limpiar()

        col_map = {"todo": self.col_todo, "doing": self.col_doing, "done": self.col_done}
        for t in tareas:
            if not pasa_filtro(t):
                continue
            card = TareaCard(t, self.colores)
            card.mover_signal.connect(lambda tid, est: self.cb["mover_tarea"](self.pid_activo, tid, est))
            card.editar_signal.connect(self._dialog_editar_tarea)
            card.duplicar_signal.connect(self._duplicar_tarea)
            card.eliminar_signal.connect(lambda tid: self.cb["eliminar_tarea"](self.pid_activo, tid))
            col = col_map.get(t.get("estado", "todo"), self.col_todo)
            col.agregar_tarjeta(card)

    def limpiar_tablero(self):
        self.stack.setCurrentIndex(0)

    # ── Diálogos de Tarea ─────────────────────────────────────────────────
    def _dialog_nueva_tarea(self, estado_inicial=None):
        if not self.pid_activo:
            QMessageBox.information(self, "Proyectos", "Selecciona un proyecto primero.")
            return
        dlg = TareaDialog(self.colores, estado_inicial=estado_inicial, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            datos = dlg.get_datos()
            if not datos["titulo"]:
                return
            self.cb["nueva_tarea"](
                self.pid_activo,
                datos["titulo"], datos["descripcion"],
                datos["prioridad"], datos["fecha_limite"], datos["estado"],
                etiqueta=datos.get("etiqueta", ""),
                story_points=datos.get("story_points", 3),
                subtareas=datos.get("subtareas", [])
            )

    def _dialog_editar_tarea(self, tid):
        tareas = self.cb["get_tareas"](self.pid_activo)
        tarea = next((t for t in tareas if t["id"] == tid), None)
        if not tarea:
            return
        dlg = TareaDialog(self.colores, tarea=tarea, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            datos = dlg.get_datos()
            if datos["titulo"]:
                self.cb["editar_tarea"](self.pid_activo, tid, datos)

    def _duplicar_tarea(self, tid):
        if not self.pid_activo:
            return
        if "duplicar_tarea" in self.cb:
            self.cb["duplicar_tarea"](self.pid_activo, tid)
        else:
            tareas = self.cb["get_tareas"](self.pid_activo)
            tarea = next((t for t in tareas if t["id"] == tid), None)
            if tarea:
                self.cb["nueva_tarea"](
                    self.pid_activo,
                    f"{tarea.get('titulo')} (Copia)",
                    tarea.get("descripcion", ""),
                    tarea.get("prioridad", "media"),
                    tarea.get("fecha_limite", ""),
                    tarea.get("estado", "todo"),
                    etiqueta=tarea.get("etiqueta", ""),
                    story_points=tarea.get("story_points", 3),
                    subtareas=list(tarea.get("subtareas", []))
                )

    def actualizar_tema(self, colores):
        self.colores = colores
        self.pag_tablero.setStyleSheet(f"background: {colores['bg_principal']};")
        self.panel_izq.setStyleSheet(f"background: {colores['bg_secundario']}; border-right: 1px solid rgba(255,255,255,0.06);")
        self.refrescar_proyectos()
        if self.pid_activo:
            self.mostrar_tablero(self.pid_activo)
