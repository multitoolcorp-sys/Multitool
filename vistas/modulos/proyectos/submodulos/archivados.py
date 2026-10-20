"""
archivados.py - Submódulo de Gestión de Proyectos Archivados, Exportación e Importación
"""
import csv
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QFileDialog, QMessageBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QDesktopServices


class TabArchivadosProyectos(QWidget):
    """Vista de Administración de Proyectos Archivados y Exportación/Importación"""
    def __init__(self, parent=None, colores=None, callbacks=None):
        super().__init__(parent)
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1"
        }
        self.callbacks = callbacks or {}

        self.init_ui()

    def init_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(16, 16, 16, 16)
        main_lay.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        lbl_title = QLabel("📦 Proyectos Archivados & Exportación")
        lbl_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        top_bar.addWidget(lbl_title)

        top_bar.addStretch()

        btn_import = QPushButton("📥 Importar Proyecto (.json)")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')};
                color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_import.clicked.connect(self._importar_proyecto_json)
        top_bar.addWidget(btn_import)

        main_lay.addLayout(top_bar)

        # Lista de Proyectos Archivados
        lbl_sub = QLabel("Proyectos archivados que puedes restaurar o exportar a JSON/Markdown/CSV:")
        lbl_sub.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 11px;")
        main_lay.addWidget(lbl_sub)

        self.list_archivados = QListWidget()
        self.list_archivados.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px; color: white; padding: 6px;
            }}
            QListWidget::item {{
                padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); border-radius: 6px;
            }}
            QListWidget::item:hover {{ background: rgba(99,102,241,0.12); }}
        """)
        main_lay.addWidget(self.list_archivados, 1)

        # Acciones de fila
        bot_bar = QHBoxLayout()

        btn_unarchive = QPushButton("🔄 Restaurar Proyecto")
        btn_unarchive.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_unarchive.setStyleSheet("background: #34D399; color: white; border-radius: 6px; padding: 8px 14px; font-weight: bold;")
        btn_unarchive.clicked.connect(self._restaurar_seleccionado)
        bot_bar.addWidget(btn_unarchive)

        btn_exp_json = QPushButton("📄 Exportar JSON")
        btn_exp_json.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exp_json.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border-radius: 6px; padding: 8px 14px; font-weight: bold;")
        btn_exp_json.clicked.connect(self._exportar_json)
        bot_bar.addWidget(btn_exp_json)

        btn_exp_md = QPushButton("📝 Reporte Markdown")
        btn_exp_md.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exp_md.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border-radius: 6px; padding: 8px 14px; font-weight: bold;")
        btn_exp_md.clicked.connect(self._exportar_markdown)
        bot_bar.addWidget(btn_exp_md)

        btn_exp_csv = QPushButton("📊 Exportar CSV")
        btn_exp_csv.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exp_csv.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border-radius: 6px; padding: 8px 14px; font-weight: bold;")
        btn_exp_csv.clicked.connect(self._exportar_csv)
        bot_bar.addWidget(btn_exp_csv)

        bot_bar.addStretch()
        main_lay.addLayout(bot_bar)

        self.refrescar_archivados()

    def refrescar_archivados(self):
        self.list_archivados.clear()
        get_proyectos = self.callbacks.get("get_proyectos")
        proyectos = get_proyectos() if get_proyectos else []

        archivados = [p for p in proyectos if p.get("archivado", False)]
        for p in archivados:
            item = QListWidgetItem(f"📦 {p.get('nombre', 'Sin Nombre')} — {len(p.get('tareas', []))} tareas")
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.list_archivados.addItem(item)

        if not archivados:
            item = QListWidgetItem("No hay proyectos archivados actualmente.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_archivados.addItem(item)

    def _obtener_pid_seleccionado(self):
        item = self.list_archivados.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            QMessageBox.information(self, "Aviso", "Selecciona un proyecto de la lista.")
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _restaurar_seleccionado(self):
        pid = self._obtener_pid_seleccionado()
        if pid and "archivar_proyecto" in self.callbacks:
            self.callbacks["archivar_proyecto"](pid)
            self.refrescar_archivados()
            QMessageBox.information(self, "Éxito", "El proyecto se restauró al tablero activo.")

    def _exportar_json(self):
        pid = self._obtener_pid_seleccionado()
        if not pid: return
        get_proyectos = self.callbacks.get("get_proyectos")
        proyectos = get_proyectos() if get_proyectos else []
        p = next((x for x in proyectos if x["id"] == pid), None)
        if not p: return

        fn, _ = QFileDialog.getSaveFileName(self, "Exportar Proyecto JSON", f"{p['nombre']}.json", "Archivo JSON (*.json)")
        if fn:
            try:
                with open(fn, "w", encoding="utf-8") as f:
                    json.dump(p, f, indent=4, ensure_ascii=False)
                QMessageBox.information(self, "Exportación Éxito", f"Proyecto exportado a:\n{fn}")
            except Exception as e:
                QMessageBox.warning(self, "Error Exportación", f"No se pudo exportar:\n{e}")

    def _exportar_markdown(self):
        pid = self._obtener_pid_seleccionado()
        if not pid: return
        get_proyectos = self.callbacks.get("get_proyectos")
        proyectos = get_proyectos() if get_proyectos else []
        p = next((x for x in proyectos if x["id"] == pid), None)
        if not p: return

        fn, _ = QFileDialog.getSaveFileName(self, "Exportar Reporte Markdown", f"Reporte_{p['nombre']}.md", "Markdown (*.md)")
        if fn:
            try:
                md_lines = [
                    f"# Reporte de Proyecto: {p.get('nombre', 'Sin Nombre')}",
                    f"**Fecha de informe**: {p.get('creado', '')[:10]}",
                    f"**Total de tareas**: {len(p.get('tareas', []))}\n",
                    "## Tareas",
                ]
                for t in p.get("tareas", []):
                    st = "✅" if t.get("estado") == "done" else ("▶️" if t.get("estado") == "doing" else "📝")
                    md_lines.append(f"- [{st}] **{t.get('titulo')}** (Prioridad: {t.get('prioridad')})")
                    if t.get("descripcion"):
                        md_lines.append(f"  - *{t.get('descripcion')}*")

                with open(fn, "w", encoding="utf-8") as f:
                    f.write("\n".join(md_lines))
                QMessageBox.information(self, "Exportación Éxito", f"Reporte Markdown guardado en:\n{fn}")
            except Exception as e:
                QMessageBox.warning(self, "Error Exportación", f"No se pudo exportar:\n{e}")

    def _importar_proyecto_json(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Importar Proyecto", "", "Archivo JSON (*.json)")
        if fn:
            try:
                with open(fn, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                if isinstance(datos, dict) and "nombre" in datos and "tareas" in datos:
                    if "importar_proyecto" in self.callbacks:
                        self.callbacks["importar_proyecto"](datos)
                        self.refrescar_archivados()
                        QMessageBox.information(self, "Éxito", f"Proyecto '{datos['nombre']}' importado correctamente.")
                else:
                    QMessageBox.warning(self, "Error Formato", "El archivo JSON no tiene un formato válido de proyecto.")
            except Exception as e:
                QMessageBox.warning(self, "Error Importación", f"Error al leer JSON:\n{e}")

    def _exportar_csv(self):
        pid = self._obtener_pid_seleccionado()
        if not pid:
            return
        get_proyectos = self.callbacks.get("get_proyectos")
        proyectos = get_proyectos() if get_proyectos else []
        p = next((x for x in proyectos if x["id"] == pid), None)
        if not p:
            return

        fn, _ = QFileDialog.getSaveFileName(self, "Exportar Tareas a CSV", f"{p['nombre']}_tareas.csv", "Archivo CSV (*.csv)")
        if fn:
            try:
                with open(fn, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Título", "Descripción", "Prioridad", "Estado", "Fecha Límite", "Story Points", "Etiqueta", "Subtareas"])
                    for t in p.get("tareas", []):
                        sub_str = "; ".join([st.get("titulo", "") for st in t.get("subtareas", []) if isinstance(st, dict)])
                        writer.writerow([
                            t.get("id", ""),
                            t.get("titulo", ""),
                            t.get("descripcion", ""),
                            t.get("prioridad", ""),
                            t.get("estado", ""),
                            t.get("fecha_limite", ""),
                            t.get("story_points", ""),
                            t.get("etiqueta", ""),
                            sub_str
                        ])
                QMessageBox.information(self, "Exportación Éxito", f"Datos CSV exportados correctamente a:\n{fn}")
            except Exception as e:
                QMessageBox.warning(self, "Error Exportación", f"No se pudo exportar CSV:\n{e}")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.refrescar_archivados()

