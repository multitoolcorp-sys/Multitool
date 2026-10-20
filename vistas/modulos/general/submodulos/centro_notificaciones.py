import json
import datetime
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QComboBox, QTextEdit,
    QDialog, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class CentroNotificacionesGUI(QWidget):
    """Submódulo Centro de Notificaciones: Historial, recordatorios y avisos del sistema"""
    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent)
        if isinstance(context, dict):
            self.colores = context
            self.context = colores
        elif isinstance(colores, dict):
            self.colores = colores
            self.context = context
        else:
            self.context = context
            self.colores = getattr(context, "colores", {}) if context else {}

        if not self.colores and self.context and hasattr(self.context, "app") and hasattr(self.context.app, "COLORES"):
            self.colores = self.context.app.COLORES

        if not isinstance(self.colores, dict):
            self.colores = {}

        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.filtro_actual = "todas"
        self.notificaciones = []
        
        self.ruta_notif = None
        if self.context and hasattr(self.context, "ruta_usuario") and self.context.ruta_usuario:
            self.ruta_notif = Path(self.context.ruta_usuario) / "notificaciones.json"

        self.cargar_notificaciones()
        self.init_ui()

    def cargar_notificaciones(self):
        if self.ruta_notif and self.ruta_notif.exists():
            try:
                with open(self.ruta_notif, "r", encoding="utf-8") as f:
                    self.notificaciones = json.load(f)
                    return
            except Exception:
                pass
        
        # Datos iniciales si está vacío
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.notificaciones = [
            {
                "id": "1",
                "tipo": "sistema",
                "titulo": "¡Bienvenido a Multitool!",
                "mensaje": "Todos tus módulos y herramientas están listos para utilizarse.",
                "fecha": ahora,
                "prioridad": "baja",
                "leida": False
            },
            {
                "id": "2",
                "tipo": "recordatorio",
                "titulo": "Revisar hábitos de hoy",
                "mensaje": "No olvides marcar tus progresos en el submódulo Hábitos.",
                "fecha": ahora,
                "prioridad": "media",
                "leida": False
            }
        ]
        self.guardar_notificaciones()

    def guardar_notificaciones(self):
        if self.ruta_notif:
            try:
                with open(self.ruta_notif, "w", encoding="utf-8") as f:
                    json.dump(self.notificaciones, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Error guardando notificaciones: {e}")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        header_text_lay = QVBoxLayout()
        
        lbl_titulo = QLabel("🔔 Centro de Notificaciones")
        lbl_titulo.setFont(QFont(self.font_family, 20, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet("color: white; border: none; background: transparent;")
        header_text_lay.addWidget(lbl_titulo)

        self.lbl_subtitulo = QLabel("Gestiona tus alertas, avisos del sistema y recordatorios")
        self.lbl_subtitulo.setFont(QFont(self.font_family, 10))
        self.lbl_subtitulo.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#9CA3AF')}; border: none; background: transparent;")
        header_text_lay.addWidget(self.lbl_subtitulo)
        header.addLayout(header_text_lay, 1)

        btn_nueva = QPushButton("➕ Nuevo Aviso")
        btn_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nueva.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_nueva.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white; border-radius: 8px; padding: 8px 16px; border: none;
            }}
            QPushButton:hover {{ background-color: #4F46E5; }}
        """)
        btn_nueva.clicked.connect(self._dialogo_nueva_notificacion)
        header.addWidget(btn_nueva)

        btn_marcar_leidas = QPushButton("✓ Marcar Leídas")
        btn_marcar_leidas.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_marcar_leidas.setFont(QFont(self.font_family, 9))
        btn_marcar_leidas.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white; border-radius: 8px; padding: 8px 14px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.1); }}
        """)
        btn_marcar_leidas.clicked.connect(self.marcar_todas_leidas)
        header.addWidget(btn_marcar_leidas)

        btn_limpiar = QPushButton("🗑️ Limpiar")
        btn_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_limpiar.setFont(QFont(self.font_family, 9))
        btn_limpiar.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #EF4444; border-radius: 8px; padding: 8px 12px;
                border: 1px solid rgba(239,68,68,0.4);
            }
            QPushButton:hover { background-color: rgba(239,68,68,0.15); }
        """)
        btn_limpiar.clicked.connect(self.limpiar_todas)
        header.addWidget(btn_limpiar)

        layout.addLayout(header)

        # Filtros por categorías
        filtros_lay = QHBoxLayout()
        filtros_lay.setSpacing(10)
        self.btn_filtros = {}
        categorias = [
            ("todas", "📋 Todas"),
            ("sistema", "⚙️ Sistema"),
            ("recordatorio", "⏰ Recordatorios"),
            ("alerta", "⚠️ Alertas")
        ]
        for key, name in categorias:
            b = QPushButton(name)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            b.clicked.connect(lambda _, k=key: self.filtrar_por(k))
            filtros_lay.addWidget(b)
            self.btn_filtros[key] = b
        filtros_lay.addStretch()
        layout.addLayout(filtros_lay)
        self._actualizar_estilo_filtros()

        # Lista de notificaciones con Scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container_cards = QWidget()
        self.cards_layout = QVBoxLayout(self.container_cards)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll.setWidget(self.container_cards)
        layout.addWidget(self.scroll, 1)

        self.renderizar_lista()

    def _actualizar_estilo_filtros(self):
        acento = self.colores.get('acento', '#6366F1')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        for k, btn in self.btn_filtros.items():
            if k == self.filtro_actual:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {acento};
                        color: white; border-radius: 6px; padding: 6px 14px; border: none;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_sec};
                        color: #9CA3AF; border-radius: 6px; padding: 6px 14px;
                        border: 1px solid rgba(255,255,255,0.06);
                    }}
                    QPushButton:hover {{ color: white; background-color: rgba(255,255,255,0.05); }}
                """)

    def filtrar_por(self, cat):
        self.filtro_actual = cat
        self._actualizar_estilo_filtros()
        self.renderizar_lista()

    def renderizar_lista(self):
        # Limpiar completamente widgets y elementos previos
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        filtradas = [
            n for n in self.notificaciones
            if self.filtro_actual == "todas" or n.get("tipo") == self.filtro_actual
        ]

        if not filtradas:
            empty_frame = QFrame()
            empty_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                    border-radius: 12px; border: 1px dashed rgba(255,255,255,0.1);
                    padding: 40px;
                }}
            """)
            ef_lay = QVBoxLayout(empty_frame)
            ef_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty = QLabel("✨ No tienes notificaciones en esta categoría")
            lbl_empty.setFont(QFont(self.font_family, 11))
            lbl_empty.setStyleSheet("color: #9CA3AF; border: none; background: transparent;")
            ef_lay.addWidget(lbl_empty)
            self.cards_layout.addWidget(empty_frame)
            return

        for notif in filtradas:
            card = self._crear_card_notificacion(notif)
            self.cards_layout.addWidget(card)

        if hasattr(self, "scroll") and self.scroll.verticalScrollBar():
            self.scroll.verticalScrollBar().setValue(0)

    def _crear_card_notificacion(self, notif):
        card = QFrame()
        leida = notif.get("leida", False)
        bg = self.colores.get('bg_secundario', '#1E1E2E')
        b_color = "rgba(99, 102, 241, 0.4)" if not leida else "rgba(255, 255, 255, 0.05)"

        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {b_color};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
        c_lay = QHBoxLayout(card)
        c_lay.setContentsMargins(18, 14, 18, 14)
        c_lay.setSpacing(15)

        # Icono según tipo
        tipo = notif.get("tipo", "sistema")
        icon_map = {
            "sistema": "⚙️",
            "recordatorio": "⏰",
            "alerta": "⚠️"
        }
        lbl_icon = QLabel(icon_map.get(tipo, "📢"))
        lbl_icon.setFont(QFont(self.font_family, 18))
        lbl_icon.setStyleSheet("border: none; background: transparent;")
        c_lay.addWidget(lbl_icon)

        # Contenido Central
        content_lay = QVBoxLayout()
        content_lay.setSpacing(4)

        top_row = QHBoxLayout()
        lbl_tit = QLabel(notif.get("titulo", "Sin título"))
        lbl_tit.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_tit.setStyleSheet("color: white; border: none; background: transparent;")
        top_row.addWidget(lbl_tit)

        # Badge de prioridad
        prio = notif.get("prioridad", "baja")
        prio_colors = {
            "alta": ("#EF4444", "rgba(239, 68, 68, 0.15)"),
            "media": ("#F59E0B", "rgba(245, 158, 11, 0.15)"),
            "baja": ("#10B981", "rgba(16, 185, 129, 0.15)")
        }
        fg_p, bg_p = prio_colors.get(prio, ("#9CA3AF", "rgba(255,255,255,0.05)"))
        badge = QLabel(f" {prio.upper()} ")
        badge.setFont(QFont(self.font_family, 7, QFont.Weight.Bold))
        badge.setStyleSheet(f"color: {fg_p}; background-color: {bg_p}; border-radius: 4px; border: 1px solid {fg_p}33; padding: 2px 4px;")
        top_row.addWidget(badge)

        top_row.addStretch()

        lbl_fecha = QLabel(notif.get("fecha", ""))
        lbl_fecha.setFont(QFont(self.font_family, 8))
        lbl_fecha.setStyleSheet("color: #6B7280; border: none; background: transparent;")
        top_row.addWidget(lbl_fecha)

        content_lay.addLayout(top_row)

        lbl_msg = QLabel(notif.get("mensaje", ""))
        lbl_msg.setFont(QFont(self.font_family, 9))
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet(f"color: {'#D1D5DB' if not leida else '#9CA3AF'}; border: none; background: transparent;")
        content_lay.addWidget(lbl_msg)

        c_lay.addLayout(content_lay, 1)

        # Acciones individuales
        actions_lay = QVBoxLayout()
        actions_lay.setSpacing(6)

        if not leida:
            btn_ok = QPushButton("✓")
            btn_ok.setToolTip("Marcar como leída")
            btn_ok.setFixedSize(26, 26)
            btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_ok.setStyleSheet("QPushButton { background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981; border-radius: 6px; } QPushButton:hover { background: #10B981; color: white; }")
            btn_ok.clicked.connect(lambda _, n=notif: self._marcar_leida(n))
            actions_lay.addWidget(btn_ok)

        btn_del = QPushButton("✕")
        btn_del.setToolTip("Eliminar")
        btn_del.setFixedSize(26, 26)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet("QPushButton { background: transparent; color: #6B7280; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; } QPushButton:hover { background: rgba(239, 68, 68, 0.15); color: #EF4444; border-color: #EF4444; }")
        btn_del.clicked.connect(lambda _, n=notif: self._eliminar_notif(n))
        actions_lay.addWidget(btn_del)

        c_lay.addLayout(actions_lay)
        return card

    def _marcar_leida(self, notif):
        notif["leida"] = True
        self.guardar_notificaciones()
        self.renderizar_lista()

    def _eliminar_notif(self, notif):
        if notif in self.notificaciones:
            self.notificaciones.remove(notif)
            self.guardar_notificaciones()
            self.renderizar_lista()

    def marcar_todas_leidas(self):
        for n in self.notificaciones:
            n["leida"] = True
        self.guardar_notificaciones()
        self.renderizar_lista()

    def limpiar_todas(self):
        if not self.notificaciones:
            return
        res = QMessageBox.question(self, "Limpiar Notificaciones", "¿Deseas eliminar todo el historial de notificaciones?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            self.notificaciones.clear()
            self.guardar_notificaciones()
            self.renderizar_lista()

    def _dialogo_nueva_notificacion(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Crear Recordatorio o Notificación")
        dlg.setFixedWidth(420)
        dlg.setStyleSheet(f"""
            QDialog {{ background-color: {self.colores.get('bg_principal', '#121218')}; color: white; }}
            QLabel {{ color: white; }}
        """)
        d_lay = QVBoxLayout(dlg)
        d_lay.setContentsMargins(24, 24, 24, 24)
        d_lay.setSpacing(14)

        d_lay.addWidget(QLabel("Título:"))
        ent_tit = QLineEdit()
        ent_tit.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 8px; border: 1px solid rgba(255,255,255,0.1);")
        d_lay.addWidget(ent_tit)

        d_lay.addWidget(QLabel("Tipo:"))
        cb_tipo = QComboBox()
        cb_tipo.addItems(["recordatorio", "alerta", "sistema"])
        cb_tipo.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 6px; border: 1px solid rgba(255,255,255,0.1);")
        d_lay.addWidget(cb_tipo)

        d_lay.addWidget(QLabel("Prioridad:"))
        cb_prio = QComboBox()
        cb_prio.addItems(["baja", "media", "alta"])
        cb_prio.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 6px; border: 1px solid rgba(255,255,255,0.1);")
        d_lay.addWidget(cb_prio)

        d_lay.addWidget(QLabel("Mensaje:"))
        txt_msg = QTextEdit()
        txt_msg.setFixedHeight(80)
        txt_msg.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 8px; border: 1px solid rgba(255,255,255,0.1);")
        d_lay.addWidget(txt_msg)

        btn_guardar = QPushButton("Guardar Aviso")
        btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guardar.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_guardar.setStyleSheet(f"background-color: {self.colores.get('acento', '#6366F1')}; color: white; border-radius: 8px; padding: 10px; border: none;")
        
        def on_save():
            tit = ent_tit.text().strip()
            msg = txt_msg.toPlainText().strip()
            if not tit:
                QMessageBox.warning(dlg, "Error", "El título es obligatorio.")
                return
            nueva = {
                "id": str(int(datetime.datetime.now().timestamp())),
                "tipo": cb_tipo.currentText(),
                "titulo": tit,
                "mensaje": msg,
                "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "prioridad": cb_prio.currentText(),
                "leida": False
            }
            self.notificaciones.insert(0, nueva)
            self.guardar_notificaciones()
            self.renderizar_lista()
            dlg.accept()

        btn_guardar.clicked.connect(on_save)
        d_lay.addWidget(btn_guardar)
        dlg.exec()
