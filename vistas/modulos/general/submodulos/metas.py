"""
metas.py - Submódulo de Gestión de Metas y Objetivos (OKRs / Milestones) para General
"""
import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QLineEdit, QProgressBar, QDialog, QMessageBox,
    QComboBox, QTextEdit, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


CATEGORIAS_METAS = ["🎯 General", "💼 Trabajo & Carrera", "📚 Estudio & Aprendizaje", "💪 Salud & Fitness", "💰 Finanzas", "🚀 Proyecto Personal"]


class TabMetasGUI(QWidget):
    """Submódulo de Gestión de Metas y Objetivos con hitos medibles (OKRs)"""
    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent if isinstance(parent, QWidget) else None)
        
        if isinstance(context, dict):
            self.colores = context
            self.context = colores
        elif isinstance(colores, dict):
            self.colores = colores
            self.context = context
        elif isinstance(parent, dict):
            self.colores = parent
            self.context = context
        else:
            self.context = context
            self.colores = colores if isinstance(colores, dict) else {}

        if not self.colores and self.context and hasattr(self.context, "app") and hasattr(self.context.app, "COLORES"):
            self.colores = self.context.app.COLORES

        if not isinstance(self.colores, dict):
            self.colores = {}

        ruta_base = Path(getattr(self.context, "ruta_usuario", ".")) if self.context and hasattr(self.context, "ruta_usuario") else Path(".")
        self.ruta_json = ruta_base / "metas_okrs_data.json"
        self.metas = []

        self.cargar_datos()
        self.init_ui()

    def cargar_datos(self):
        if self.ruta_json.exists():
            try:
                with open(self.ruta_json, "r", encoding="utf-8") as f:
                    self.metas = json.load(f)
            except Exception:
                self.metas = []
        else:
            self.metas = [
                {
                    "id": 1,
                    "titulo": "Dominar PyQt6 y Arquitectura Limpia",
                    "categoria": "📚 Estudio & Aprendizaje",
                    "fecha_limite": "2026-12-31",
                    "descripcion": "Completar la optimización de todos los módulos de MultiTool.",
                    "hitos": [
                        {"texto": "Modularizar módulos pesados a <1000 líneas", "completado": True},
                        {"texto": "Implementar carga dinámica en todos los submódulos", "completado": True},
                        {"texto": "Añadir tests de integración automatizados", "completado": False}
                    ]
                }
            ]

    def guardar_datos(self):
        try:
            self.ruta_json.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ruta_json, "w", encoding="utf-8") as f:
                json.dump(self.metas, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar metas: {e}")

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {bg_p}; }}")

        container = QWidget()
        self.cont_lay = QVBoxLayout(container)
        self.cont_lay.setContentsMargins(24, 24, 24, 24)
        self.cont_lay.setSpacing(18)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("🎯 Metas & Objetivos (OKRs)")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')};")

        lbl_desc = QLabel("Define objetivos a mediano y largo plazo con hitos medibles para alcanzar tus metas.")
        lbl_desc.setFont(QFont("Segoe UI", 10))
        lbl_desc.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#A0A0A0')};")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_desc)

        btn_nueva = QPushButton("＋ Nueva Meta")
        btn_nueva.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nueva.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                border-radius: 8px;
                padding: 10px 18px;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#4F46E5')};
            }}
        """)
        btn_nueva.clicked.connect(self.mostrar_dialogo_nueva_meta)

        header.addLayout(title_box)
        header.addStretch()
        header.addWidget(btn_nueva)
        self.cont_lay.addLayout(header)

        # Filtro de categorías
        filtro_box = QHBoxLayout()
        lbl_filtro = QLabel("Filtrar por:")
        lbl_filtro.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#A0A0A0')}; font-size: 11px;")
        
        self.cb_filtro = QComboBox()
        self.cb_filtro.addItem("Todas las Categorías")
        self.cb_filtro.addItems(CATEGORIAS_METAS)
        self.cb_filtro.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 180px;
            }}
        """)
        self.cb_filtro.currentTextChanged.connect(self.renderizar_metas)

        filtro_box.addWidget(lbl_filtro)
        filtro_box.addWidget(self.cb_filtro)
        filtro_box.addStretch()
        self.cont_lay.addLayout(filtro_box)

        # Contenedor dinámico de tarjetas de metas
        self.cards_layout = QVBoxLayout()
        self.cards_layout.setSpacing(14)
        self.cont_lay.addLayout(self.cards_layout)
        self.cont_lay.addStretch()

        scroll.setWidget(container)
        main_lay.addWidget(scroll)

        self.renderizar_metas()

    def renderizar_metas(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        filtro = self.cb_filtro.currentText()
        metas_filtradas = [
            m for m in self.metas 
            if filtro == "Todas las Categorías" or m.get("categoria") == filtro
        ]

        if not metas_filtradas:
            vacio = QLabel("No hay metas registradas en esta categoría. ¡Crea una nueva meta arriba!")
            vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vacio.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#7A7A8C')}; padding: 40px; font-size: 12px;")
            self.cards_layout.addWidget(vacio)
            return

        for meta in metas_filtradas:
            card = self._crear_tarjeta_meta(meta)
            self.cards_layout.addWidget(card)

    def _crear_tarjeta_meta(self, meta):
        card = QFrame()
        bg_card = self.colores.get('bg_secundario', '#1E1E2E')
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_card};
                border: 1px solid {self.colores.get('bg_terciario', '#2A2A3C')};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setSpacing(10)

        # Fila superior: Categoría, Fecha límite, Botón Eliminar
        top_row = QHBoxLayout()
        cat_badge = QLabel(meta.get("categoria", "🎯 General"))
        cat_badge.setStyleSheet(f"""
            background-color: {self.colores.get('bg_terciario', '#2A2A3C')};
            color: {self.colores.get('acento', '#6366F1')};
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: bold;
        """)
        top_row.addWidget(cat_badge)

        if meta.get("fecha_limite"):
            fecha_lbl = QLabel(f"📅 Meta: {meta.get('fecha_limite')}")
            fecha_lbl.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#A0A0A0')}; font-size: 11px;")
            top_row.addWidget(fecha_lbl)

        top_row.addStretch()

        btn_eliminar = QPushButton("✕")
        btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eliminar.setFixedSize(26, 26)
        btn_eliminar.setStyleSheet("background: transparent; color: #EF4444; border: none; font-weight: bold; font-size: 14px;")
        btn_eliminar.clicked.connect(lambda _, m_id=meta.get("id"): self.eliminar_meta(m_id))
        top_row.addWidget(btn_eliminar)
        lay.addLayout(top_row)

        # Título y descripción
        lbl_titulo = QLabel(meta.get("titulo", "Sin título"))
        lbl_titulo.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')};")
        lay.addWidget(lbl_titulo)

        if meta.get("descripcion"):
            lbl_desc = QLabel(meta.get("descripcion"))
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#A0A0A0')}; font-size: 11px;")
            lay.addWidget(lbl_desc)

        # Cálculo de progreso por hitos
        hitos = meta.get("hitos", [])
        total_hitos = len(hitos)
        completados = sum(1 for h in hitos if h.get("completado", False))
        porcentaje = int((completados / total_hitos * 100)) if total_hitos > 0 else 0

        prog_box = QHBoxLayout()
        prog_bar = QProgressBar()
        prog_bar.setRange(0, 100)
        prog_bar.setValue(porcentaje)
        prog_bar.setTextVisible(False)
        prog_bar.setFixedHeight(8)
        color_prog = self.colores.get('exito', '#10B981') if porcentaje == 100 else self.colores.get('acento', '#6366F1')
        prog_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.colores.get('bg_terciario', '#2A2A3C')};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color_prog};
                border-radius: 4px;
            }}
        """)
        prog_txt = QLabel(f"{porcentaje}% ({completados}/{total_hitos} hitos)")
        prog_txt.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#A0A0A0')}; font-size: 11px; font-weight: bold;")
        prog_box.addWidget(prog_bar)
        prog_box.addWidget(prog_txt)
        lay.addLayout(prog_box)

        # Lista interactiva de hitos (Checkboxes)
        if hitos:
            hitos_frame = QFrame()
            hitos_frame.setStyleSheet(f"background: transparent; border: none;")
            hitos_lay = QVBoxLayout(hitos_frame)
            hitos_lay.setContentsMargins(6, 4, 6, 4)
            hitos_lay.setSpacing(6)

            for idx, hito in enumerate(hitos):
                chk = QCheckBox(hito.get("texto", ""))
                chk.setChecked(hito.get("completado", False))
                chk.setCursor(Qt.CursorShape.PointingHandCursor)
                chk.setStyleSheet(f"""
                    QCheckBox {{
                        color: {self.colores.get('fg_principal', '#E0E0E0')};
                        font-size: 11px;
                    }}
                    QCheckBox::indicator {{
                        width: 14px;
                        height: 14px;
                        border-radius: 3px;
                        border: 1px solid {self.colores.get('acento', '#6366F1')};
                    }}
                    QCheckBox::indicator:checked {{
                        background-color: {self.colores.get('acento', '#6366F1')};
                    }}
                """)
                chk.toggled.connect(lambda checked, m=meta, i=idx: self._toggle_hito(m, i, checked))
                hitos_lay.addWidget(chk)

            lay.addWidget(hitos_frame)

        return card

    def _toggle_hito(self, meta, hito_idx, completado):
        if "hitos" in meta and 0 <= hito_idx < len(meta["hitos"]):
            meta["hitos"][hito_idx]["completado"] = completado
            self.guardar_datos()
            self.renderizar_metas()

    def eliminar_meta(self, meta_id):
        confirm = QMessageBox.question(
            self, "Confirmar Eliminación",
            "¿Estás seguro de que deseas eliminar este objetivo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.metas = [m for m in self.metas if m.get("id") != meta_id]
            self.guardar_datos()
            self.renderizar_metas()

    def mostrar_dialogo_nueva_meta(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Definir Nuevo Objetivo / Meta")
        dlg.setFixedSize(480, 460)
        bg = self.colores.get('bg_principal', '#121218')
        dlg.setStyleSheet(f"background-color: {bg}; color: white;")

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        lay.addWidget(QLabel("Título del Objetivo:"))
        txt_titulo = QLineEdit()
        txt_titulo.setPlaceholderText("Ej: Lanzar versión 2.0 del proyecto")
        txt_titulo.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 8px;")
        lay.addWidget(txt_titulo)

        lay.addWidget(QLabel("Categoría:"))
        cb_cat = QComboBox()
        cb_cat.addItems(CATEGORIAS_METAS)
        cb_cat.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 6px;")
        lay.addWidget(cb_cat)

        lay.addWidget(QLabel("Fecha Límite (YYYY-MM-DD):"))
        txt_fecha = QLineEdit(datetime.now().strftime("%Y-12-31"))
        txt_fecha.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 8px;")
        lay.addWidget(txt_fecha)

        lay.addWidget(QLabel("Descripción o Alcance:"))
        txt_desc = QTextEdit()
        txt_desc.setPlaceholderText("Detalles o notas sobre lo que se espera alcanzar...")
        txt_desc.setFixedHeight(60)
        txt_desc.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 6px;")
        lay.addWidget(txt_desc)

        lay.addWidget(QLabel("Hitos clave (1 por línea):"))
        txt_hitos = QTextEdit()
        txt_hitos.setPlaceholderText("Hito 1: Diseñar interfaz\nHito 2: Programar lógica\nHito 3: Probar y desplegar")
        txt_hitos.setFixedHeight(80)
        txt_hitos.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 6px;")
        lay.addWidget(txt_hitos)

        btn_guardar = QPushButton("Guardar Meta")
        btn_guardar.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn_guardar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                border-radius: 8px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#4F46E5')};
            }}
        """)

        def _guardar():
            titulo = txt_titulo.text().strip()
            if not titulo:
                QMessageBox.warning(dlg, "Campo Requerido", "Por favor ingresa un título para la meta.")
                return

            lineas_hitos = [h.strip() for h in txt_hitos.toPlainText().splitlines() if h.strip()]
            hitos_objs = [{"texto": h, "completado": False} for h in lineas_hitos]

            nueva = {
                "id": int(datetime.now().timestamp() * 1000),
                "titulo": titulo,
                "categoria": cb_cat.currentText(),
                "fecha_limite": txt_fecha.text().strip(),
                "descripcion": txt_desc.toPlainText().strip(),
                "hitos": hitos_objs
            }
            self.metas.insert(0, nueva)
            self.guardar_datos()
            self.renderizar_metas()
            dlg.accept()

        btn_guardar.clicked.connect(_guardar)
        lay.addWidget(btn_guardar)

        dlg.exec()

    def actualizar_tema(self, colores):
        if isinstance(colores, dict):
            self.colores = colores
            bg_p = self.colores.get('bg_principal', '#121218')
            self.setStyleSheet(f"background-color: {bg_p}; color: white;")
            self.renderizar_metas()
