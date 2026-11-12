"""
updates_log_dialog.py — Gestor interactivo de Historial de Actualizaciones (.mtu), Instalación en Caliente y Rollback en 1 Clic.
"""
import json
import shutil
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from controlador.utils.paths import get_data_path, get_resource_path


class UpdatesLogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle("Gestor e Historial de Actualizaciones (.mtu)")
        self.setMinimumSize(680, 480)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #121218;
                color: #E2E2E2;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #E2E2E2;
                background: transparent;
            }
            QScrollArea {
                background-color: #161622;
                border: 1px solid #2D2D3D;
                border-radius: 6px;
            }
            QPushButton {
                background-color: #2D2D3D;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 7px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_lay = QHBoxLayout()
        lbl_title = QLabel("📋 Historial de Actualizaciones y Rollback Dinámico (.mtu)")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #818CF8;")
        header_lay.addWidget(lbl_title)
        header_lay.addStretch()

        lbl_hint = QLabel("💡 Puedes arrastrar un archivo .mtu aquí para instalarlo")
        lbl_hint.setStyleSheet("font-size: 11px; color: #94A3B8;")
        header_lay.addWidget(lbl_hint)
        layout.addLayout(header_lay)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background-color: #161622;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(10, 10, 10, 10)
        self.cards_layout.setSpacing(10)
        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area, 1)

        btn_layout = QHBoxLayout()
        self.btn_install = QPushButton("📦 Instalar Actualización (.mtu)...")
        self.btn_install.setStyleSheet("background-color: #6366F1; color: white;")
        self.btn_install.clicked.connect(self._instalar_nuevo_mtu)
        btn_layout.addWidget(self.btn_install)

        self.btn_refresh = QPushButton("🔄 Actualizar Lista")
        self.btn_refresh.clicked.connect(self.cargar_log)
        btn_layout.addWidget(self.btn_refresh)

        btn_layout.addStretch()

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        self.cargar_log()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                if u.toLocalFile().lower().endswith(".mtu"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for u in event.mimeData().urls():
            f_path = u.toLocalFile()
            if f_path.lower().endswith(".mtu"):
                event.acceptProposedAction()
                if self.parent_app and hasattr(self.parent_app, "instalar_actualizacion_mtu"):
                    self.parent_app.instalar_actualizacion_mtu(f_path)
                    self.cargar_log()
                return

    def _instalar_nuevo_mtu(self):
        if self.parent_app and hasattr(self.parent_app, "instalar_actualizacion_mtu"):
            self.parent_app.instalar_actualizacion_mtu()
            self.cargar_log()

    def _obtener_rutas_historial(self):
        base_dir = get_resource_path()
        data_dir = get_data_path()
        candidatas = [
            data_dir / "actualizaciones.json",
            base_dir / "data" / "actualizaciones.json",
            base_dir / "actualizaciones.json",
        ]
        unicas = []
        vistos = set()
        for p in candidatas:
            try:
                res = str(p.resolve())
            except Exception:
                res = str(p)
            if res not in vistos:
                vistos.add(res)
                unicas.append(p)
        return unicas

    def _leer_historial_unificado(self):
        registros = []
        vistos_clave = set()
        for ruta in self._obtener_rutas_historial():
            if not ruta.exists():
                continue
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    lista = json.load(f)
                if isinstance(lista, list):
                    for item in lista:
                        if not isinstance(item, dict):
                            continue
                        clave = item.get("id") or f"{item.get('fecha', '')}_{item.get('archivo', '')}"
                        if clave not in vistos_clave:
                            vistos_clave.add(clave)
                            registros.append(item)
            except Exception:
                pass
        return registros

    def _guardar_historial_unificado(self, registros):
        for ruta in self._obtener_rutas_historial():
            try:
                ruta.parent.mkdir(parents=True, exist_ok=True)
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump(registros, f, indent=4, ensure_ascii=False)
            except Exception:
                pass

    def cargar_log(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        historial = self._leer_historial_unificado()
        if not historial:
            lbl_empty = QLabel("No se ha registrado ninguna actualización instalada en este sistema todavía.")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("color: #94A3B8; font-size: 13px; padding: 30px;")
            self.cards_layout.addWidget(lbl_empty)
            self.cards_layout.addStretch()
            return

        for idx, entrada in enumerate(reversed(historial), 1):
            card = QFrame()
            es_revertido = bool(entrada.get("rollback", False)) or entrada.get("estado") == "revertido"
            border_col = "#475569" if es_revertido else "#6366F1"
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #1E1E2E;
                    border: 1px solid {border_col};
                    border-radius: 6px;
                }}
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(12, 10, 12, 10)
            c_lay.setSpacing(6)

            top_row = QHBoxLayout()
            archivo = entrada.get("archivo", "N/A")
            version = entrada.get("version", "N/A")
            fecha = entrada.get("fecha", "N/A")
            tipo = str(entrada.get("tipo", "modulo")).upper()
            modo = "🔥 En Caliente" if entrada.get("modo") == "caliente" else "🔄 Con Reinicio"
            estado_txt = "⏪ Revertida (Rollback)" if es_revertido else "✅ Activa"
            estado_col = "#FBBF24" if es_revertido else "#34D399"

            lbl_main = QLabel(f"#{idx}  📦 {archivo}  (v{version})  —  [{tipo}]  •  {modo}")
            lbl_main.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF; border: none;")
            top_row.addWidget(lbl_main)
            top_row.addStretch()

            lbl_state = QLabel(f"{estado_txt}  |  🕒 {fecha}")
            lbl_state.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {estado_col}; border: none;")
            top_row.addWidget(lbl_state)
            c_lay.addLayout(top_row)

            desc = entrada.get("descripcion", "").strip()
            if desc:
                lbl_desc = QLabel(f"📝 {desc}")
                lbl_desc.setWordWrap(True)
                lbl_desc.setStyleSheet("font-size: 11px; color: #CBD5E1; border: none;")
                c_lay.addWidget(lbl_desc)

            afectados = entrada.get("archivos_afectados", [])
            if afectados:
                resumen_af = ", ".join(afectados[:5])
                if len(afectados) > 5:
                    resumen_af += f" (+{len(afectados) - 5} más)"
                lbl_af = QLabel(f"📂 Archivos extraídos: {resumen_af}")
                lbl_af.setWordWrap(True)
                lbl_af.setStyleSheet("font-size: 10px; color: #94A3B8; font-family: 'Consolas', monospace; border: none;")
                c_lay.addWidget(lbl_af)

            backup_dir_str = entrada.get("backup_dir", "")
            backup_path = Path(backup_dir_str) if backup_dir_str else None
            puede_rollback = bool(backup_path and backup_path.exists() and not es_revertido)

            if puede_rollback:
                act_row = QHBoxLayout()
                act_row.addStretch()
                btn_rb = QPushButton("⏪ Revertir esta Actualización (Rollback en 1 Clic)")
                btn_rb.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_rb.setStyleSheet("""
                    QPushButton {
                        background-color: #B45309;
                        color: #FFFFFF;
                        border-radius: 4px;
                        padding: 5px 12px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #D97706;
                    }
                """)
                btn_rb.clicked.connect(lambda ch, ent=entrada: self._ejecutar_rollback(ent))
                act_row.addWidget(btn_rb)
                c_lay.addLayout(act_row)

            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def _ejecutar_rollback(self, entrada: dict):
        archivo = entrada.get("archivo", "Actualización")
        backup_dir = Path(entrada.get("backup_dir", ""))
        if not backup_dir.exists():
            QMessageBox.warning(self, "Backup no disponible", "La carpeta de respaldo para esta actualización ya no existe en disco.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar Rollback",
            f"¿Desea revertir la actualización '{archivo}' y restaurar los archivos previos desde la copia de seguridad?\n\n"
            "Los módulos afectados se recargarán en caliente automáticamente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        base_dir = get_resource_path()
        restaurados = []
        try:
            meta_file = backup_dir / "backup_meta.json"
            created_files = []
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as fm:
                        mdata = json.load(fm)
                        created_files = mdata.get("created_files", [])
                except Exception:
                    pass

            # 1. Restaurar archivos sobrescritos desde backup_dir
            for sub_f in backup_dir.rglob("*"):
                if sub_f.is_file() and sub_f.name != "backup_meta.json":
                    rel_p = sub_f.relative_to(backup_dir)
                    dest_f = base_dir / rel_p
                    dest_f.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(sub_f, dest_f)
                    restaurados.append(rel_p.as_posix())

            # 2. Eliminar archivos nuevos que no existían antes del parche
            for rel_new in created_files:
                cand = base_dir / rel_new
                if cand.exists() and cand.is_file():
                    try:
                        cand.unlink()
                        restaurados.append(rel_new)
                    except Exception:
                        pass

            # 3. Actualizar estado en el historial
            historial = self._leer_historial_unificado()
            clave_target = entrada.get("id") or f"{entrada.get('fecha', '')}_{entrada.get('archivo', '')}"
            for item in historial:
                clave_item = item.get("id") or f"{item.get('fecha', '')}_{item.get('archivo', '')}"
                if clave_item == clave_target:
                    item["rollback"] = True
                    item["estado"] = "revertido"
                    item["fecha_rollback"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._guardar_historial_unificado(historial)

            # 4. Recargar en caliente en la aplicación principal si está disponible
            msg_recarga = ""
            if self.parent_app and hasattr(self.parent_app, "_recargar_componentes_actualizados"):
                msg_recarga = "\n" + self.parent_app._recargar_componentes_actualizados(
                    restaurados or entrada.get("archivos_afectados", [])
                )

            self.cargar_log()
            QMessageBox.information(
                self,
                "Rollback Completado",
                f"⏪ Se revirtió '{archivo}' con éxito ({len(restaurados)} archivo(s) restaurado(s)).{msg_recarga}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error en Rollback", f"Ocurrió un error al restaurar la copia de seguridad:\n{e}")
