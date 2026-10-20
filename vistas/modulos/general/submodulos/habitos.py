"""
habitos.py - Submódulo de Seguimiento de Hábitos y Objetivos Diarios
"""
import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QLineEdit, QCheckBox, QDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


DEFAULT_HABITOS = []

class TabHabitosGUI(QWidget):
    """Submódulo de Gestión de Hábitos y Metas Diarias con contador de racha"""
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
        self.ruta_json = ruta_base / "habitos_data.json"
        self.habitos = []

        self.cargar_datos()
        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {bg_p}; }}")

        content = QWidget()
        content.setStyleSheet(f"background-color: {bg_p};")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        lbl_t = QLabel("🎯 HÁBITOS & OBJETIVOS DIARIOS")
        lbl_t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        hdr.addWidget(lbl_t)
        hdr.addStretch()

        btn_add = QPushButton("➕ Nuevo Hábito")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')}; color: white;
                border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 11px;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_add.clicked.connect(self._dialog_nuevo_habito)
        hdr.addWidget(btn_add)
        lay.addLayout(hdr)

        # Lista de tarjetas de hábitos
        self.container_cards = QVBoxLayout()
        self.container_cards.setSpacing(10)
        lay.addLayout(self.container_cards)

        lay.addStretch()
        scroll.setWidget(content)
        main_lay.addWidget(scroll)

        self.refrescar_lista()

    def cargar_datos(self):
        if self.ruta_json.exists():
            try:
                with open(self.ruta_json, "r", encoding="utf-8") as f:
                    self.habitos = json.load(f)
            except Exception: self.habitos = []

        if not self.habitos:
            self.habitos = list(DEFAULT_HABITOS)
            self.guardar_datos()

    def guardar_datos(self):
        try:
            with open(self.ruta_json, "w", encoding="utf-8") as f:
                json.dump(self.habitos, f, indent=4, ensure_ascii=False)
        except Exception: pass

    def refrescar_lista(self):
        while self.container_cards.count():
            item = self.container_cards.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for idx, hab in enumerate(self.habitos):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {self.colores.get('bg_secundario', '#1E1E2E')};
                    border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 12px;
                }}
                QFrame:hover {{ border-color: {self.colores.get('acento', '#6366F1')}; }}
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setSpacing(12)

            chk = QCheckBox()
            chk.setChecked(hab.get("completado_hoy", False))
            chk.setStyleSheet("QCheckBox::indicator { width: 20px; height: 20px; }")
            chk.toggled.connect(lambda checked, i=idx: self._toggle_habito(i, checked))
            c_lay.addWidget(chk)

            info_lay = QVBoxLayout()
            info_lay.setSpacing(2)
            lbl_nom = QLabel(hab.get("nombre", "Hábito"))
            lbl_nom.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl_nom.setStyleSheet("color: white;" if not hab.get("completado_hoy") else "color: #888; text-decoration: line-through;")
            info_lay.addWidget(lbl_nom)

            lbl_cat = QLabel(f"Categoría: {hab.get('categoria', 'General')}")
            lbl_cat.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 9px;")
            info_lay.addWidget(lbl_cat)
            c_lay.addLayout(info_lay, 1)

            # Racha
            racha = hab.get("racha", 0)
            lbl_streak = QLabel(f"🔥 {racha} días de racha")
            lbl_streak.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl_streak.setStyleSheet("color: #FBBF24;")
            c_lay.addWidget(lbl_streak)

            btn_del = QPushButton("🗑️")
            btn_del.setFixedSize(24, 24)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background: transparent; border: none; font-size: 11px;")
            btn_del.clicked.connect(lambda ch, i=idx: self._borrar_habito(i))
            c_lay.addWidget(btn_del)

            self.container_cards.addWidget(card)

    def _toggle_habito(self, idx, checked):
        if 0 <= idx < len(self.habitos):
            self.habitos[idx]["completado_hoy"] = checked
            if checked:
                self.habitos[idx]["racha"] += 1
            else:
                self.habitos[idx]["racha"] = max(0, self.habitos[idx]["racha"] - 1)
            self.guardar_datos()
            self.refrescar_lista()

    def _borrar_habito(self, idx):
        if 0 <= idx < len(self.habitos):
            self.habitos.pop(idx)
            self.guardar_datos()
            self.refrescar_lista()

    def _dialog_nuevo_habito(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Nuevo Hábito")
        dlg.setMinimumWidth(320)
        dlg.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; color: white;")

        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)

        lbl_n = QLabel("Nombre del Hábito:")
        txt_n = QLineEdit()
        txt_n.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 6px;")
        lay.addWidget(lbl_n); lay.addWidget(txt_n)

        lbl_c = QLabel("Categoría:")
        txt_c = QLineEdit("Salud")
        txt_c.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 6px;")
        lay.addWidget(lbl_c); lay.addWidget(txt_c)

        btn_save = QPushButton("💾 Guardar Hábito")
        btn_save.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; font-weight: bold; border-radius: 6px; padding: 8px;")
        def save():
            if txt_n.text().strip():
                self.habitos.append({
                    "id": len(self.habitos) + 1,
                    "nombre": txt_n.text().strip(),
                    "categoria": txt_c.text().strip() or "General",
                    "racha": 0,
                    "completado_hoy": False
                })
                self.guardar_datos()
                self.refrescar_lista()
                dlg.accept()
        btn_save.clicked.connect(save)
        lay.addWidget(btn_save)

        dlg.exec()
