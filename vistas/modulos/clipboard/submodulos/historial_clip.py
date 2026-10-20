"""
historial_clip.py - Submódulo de Historial del Portapapeles (Texto, Imágenes, Detección Inteligente y Privacidad)
"""
import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QLineEdit, QApplication, QMenu, QMessageBox,
    QToolButton, QComboBox, QFileDialog, QDialog, QPlainTextEdit, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QCursor, QPixmap, QColor, QAction, QDesktopServices


MAX_ITEMS = 60
MAX_PREVIEW = 240


def _detectar_tipo(texto):
    if not texto:
        return "vacio", "❓"
    txt_s = texto.strip()
    # Color HEX o RGB
    if re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', txt_s):
        return "color_hex", "🎨"
    if re.match(r'^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(?:\s*,\s*[\d\.]+)?\s*\)$', txt_s, re.IGNORECASE):
        return "color_rgb", "🎨"
    if re.match(r'https?://', txt_s):
        return "url", "🔗"
    if re.match(r'^-?\d+(\.\d+)?$', txt_s):
        return "numero", "🔢"
    if re.match(r'^[\w.+-]+@[\w.-]+\.\w+$', txt_s):
        return "email", "📧"
    if (txt_s.startswith("{") and txt_s.endswith("}")) or (txt_s.startswith("[") and txt_s.endswith("]")):
        try:
            json.loads(txt_s)
            return "json", "✨"
        except Exception:
            pass
    if Path(txt_s).exists() and (os.path.isabs(txt_s) or "/" in txt_s or "\\" in txt_s):
        return "archivo", "📂"
    if any(k in txt_s for k in ["def ", "function", "import ", "class ", "<html", "SELECT ", "var ", "const ", "public static", "console.log"]):
        return "codigo", "💻"
    if len(txt_s) > 100 or "\n" in txt_s:
        return "texto_largo", "📄"
    return "texto", "📋"


class ClipDetalleDialog(QDialog):
    """Diálogo modal para visualizar y editar texto completo o ver imágenes a resolución completa."""
    guardar_como_snippet_signal = pyqtSignal(str)

    def __init__(self, item, colores, parent=None):
        super().__init__(parent)
        self.item = item
        self.colores = colores
        self.setWindowTitle("Detalle del Elemento - Portapapeles")
        self.setMinimumSize(620, 440)
        self.setStyleSheet(f"background: {colores.get('bg_principal', '#121218')}; color: white;")
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)

        tipo = self.item.get("tipo", "texto")
        fecha = self.item.get("fecha", "")
        fijado = self.item.get("fijado", False)

        hdr = QHBoxLayout()
        lbl_tipo = QLabel(f"Detalle de {'Imagen' if tipo == 'imagen' else 'Texto'} ({fecha})")
        lbl_tipo.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_tipo.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        hdr.addWidget(lbl_tipo)
        hdr.addStretch()

        self.btn_fijar = QPushButton("⭐ Guardado para después" if fijado else "☆ Guardar para después")
        self.btn_fijar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._estilizar_btn_fijar()
        self.btn_fijar.clicked.connect(self._toggle_fijar)
        hdr.addWidget(self.btn_fijar)
        lay.addLayout(hdr)

        if tipo == "imagen":
            ruta_img = self.item.get("ruta_img", "")
            lbl_img = QLabel()
            lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if ruta_img and Path(ruta_img).exists():
                pix = QPixmap(ruta_img)
                lbl_img.setPixmap(pix.scaled(500, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            lay.addWidget(lbl_img, 1)

            btn_box = QHBoxLayout()
            btn_save = QPushButton("💾 Guardar Imagen Como...")
            btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_save.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
            btn_save.clicked.connect(self._guardar_imagen_como)
            btn_box.addWidget(btn_save)

            btn_copy_img = QPushButton("📋 Copiar Imagen al Portapapeles")
            btn_copy_img.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy_img.setStyleSheet("background: rgba(255,255,255,0.08); color: white; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
            btn_copy_img.clicked.connect(self._copiar_imagen_actual)
            btn_box.addWidget(btn_copy_img)
            lay.addLayout(btn_box)
        else:
            self.txt_edit = QPlainTextEdit()
            self.txt_edit.setPlainText(self.item.get("texto", ""))
            self.txt_edit.setFont(QFont("Consolas", 10))
            self.txt_edit.setStyleSheet(f"""
                QPlainTextEdit {{
                    background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white;
                    border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px;
                }}
            """)
            lay.addWidget(self.txt_edit, 1)

            btn_box = QHBoxLayout()
            btn_guardar_cambios = QPushButton("💾 Guardar Cambios en este Clip")
            btn_guardar_cambios.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_guardar_cambios.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border-radius: 6px; padding: 8px 14px; font-weight: bold; font-size: 11px;")
            btn_guardar_cambios.clicked.connect(self._guardar_cambios_texto)
            btn_box.addWidget(btn_guardar_cambios)

            btn_snip = QPushButton("📌 Guardar como Snippet")
            btn_snip.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_snip.setStyleSheet("background: rgba(255,255,255,0.08); color: white; border-radius: 6px; padding: 8px 14px; font-weight: bold; font-size: 11px;")
            btn_snip.clicked.connect(self._guardar_como_snippet)
            btn_box.addWidget(btn_snip)

            btn_copy = QPushButton("📋 Copiar al Portapapeles")
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy.setStyleSheet("background: rgba(52,211,153,0.18); color: #34D399; border: 1px solid #34D399; border-radius: 6px; padding: 8px 14px; font-weight: bold; font-size: 11px;")
            btn_copy.clicked.connect(self._copiar_texto_actual)
            btn_box.addWidget(btn_copy)
            lay.addLayout(btn_box)

    def _estilizar_btn_fijar(self):
        fijado = self.item.get("fijado", False)
        if fijado:
            self.btn_fijar.setText("⭐ Guardado para después")
            self.btn_fijar.setStyleSheet("background: rgba(251, 191, 36, 0.2); color: #FBBF24; border: 1px solid #FBBF24; border-radius: 6px; padding: 6px 12px; font-weight: bold; font-size: 10px;")
        else:
            self.btn_fijar.setText("☆ Guardar para después")
            self.btn_fijar.setStyleSheet("background: rgba(255, 255, 255, 0.06); color: #D1D5DB; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 12px; font-weight: bold; font-size: 10px;")

    def _toggle_fijar(self):
        self.item["fijado"] = not self.item.get("fijado", False)
        self._estilizar_btn_fijar()
        if self.parent() and hasattr(self.parent(), "guardar_datos"):
            self.parent().guardar_datos()
            self.parent().refrescar_lista()

    def _guardar_cambios_texto(self):
        nuevo_txt = self.txt_edit.toPlainText()
        self.item["texto"] = nuevo_txt
        if self.parent() and hasattr(self.parent(), "guardar_datos"):
            self.parent().guardar_datos()
            self.parent().refrescar_lista()
        QMessageBox.information(self, "Guardado", "Cambios guardados en el elemento exitosamente.")

    def _guardar_como_snippet(self):
        txt = self.txt_edit.toPlainText()
        self.guardar_como_snippet_signal.emit(txt)
        if self.parent() and hasattr(self.parent(), "guardar_como_snippet"):
            self.parent().guardar_como_snippet.emit(txt)
        self.accept()

    def _guardar_imagen_como(self):
        ruta = self.item.get("ruta_img", "")
        if not ruta or not Path(ruta).exists():
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Guardar Imagen", "captura_portapapeles.png", "PNG (*.png);;JPG (*.jpg)")
        if dest:
            try:
                pix = QPixmap(ruta)
                pix.save(dest)
                QMessageBox.information(self, "Guardado", "Imagen guardada exitosamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar la imagen: {e}")

    def _copiar_imagen_actual(self):
        ruta = self.item.get("ruta_img", "")
        if ruta and Path(ruta).exists():
            QApplication.clipboard().setPixmap(QPixmap(ruta))
            self.accept()

    def _copiar_texto_actual(self):
        txt = self.txt_edit.toPlainText()
        QApplication.clipboard().setText(txt)
        self.accept()


class ClipItemCard(QFrame):
    """Tarjeta visual para elementos del portapapeles con acciones contextuales inteligentes."""
    pegar_signal = pyqtSignal(int)
    fijar_signal = pyqtSignal(int)
    eliminar_signal = pyqtSignal(int)
    ver_detalle_signal = pyqtSignal(int)
    enviar_herramientas_signal = pyqtSignal(str)
    guardar_snippet_signal = pyqtSignal(str)

    def __init__(self, idx, item, colores, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.item = item
        self.colores = colores
        self._build()

    def _build(self):
        fijado = self.item.get("fijado", False)
        es_img = self.item.get("tipo") == "imagen"
        tipo, icon = ("imagen", "🖼️") if es_img else _detectar_tipo(self.item.get("texto", ""))

        color_borde = self.colores.get('acento', '#6366F1') if fijado else "rgba(255,255,255,0.08)"
        self.setStyleSheet(f"""
            QFrame {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1.5px solid {color_borde};
                border-radius: 10px;
            }}
            QFrame:hover {{ border-color: rgba(255,255,255,0.22); }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        # ── Header de Tarjeta ──
        hdr = QHBoxLayout()
        lbl_icon = QLabel(icon)
        lbl_icon.setFixedWidth(20)
        hdr.addWidget(lbl_icon)

        fecha = self.item.get("fecha", "")
        lbl_fecha = QLabel(fecha)
        lbl_fecha.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 9px;")
        hdr.addWidget(lbl_fecha)
        hdr.addStretch()

        if fijado:
            lbl_pin = QLabel("⭐ Guardado")
            lbl_pin.setStyleSheet("color: #FBBF24; font-size: 10px; font-weight: bold;")
            hdr.addWidget(lbl_pin)

        btn_menu = QToolButton()
        btn_menu.setText("⋮")
        btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_menu.setStyleSheet("background: transparent; color: #888; border: none; font-size: 14px;")
        btn_menu.clicked.connect(self._mostrar_menu)
        hdr.addWidget(btn_menu)
        lay.addLayout(hdr)

        # ── Contenido de Tarjeta ──
        if es_img:
            ruta_img = self.item.get("ruta_img", "")
            if ruta_img and Path(ruta_img).exists():
                lbl_img = QLabel()
                pix = QPixmap(ruta_img)
                if not pix.isNull():
                    lbl_img.setPixmap(pix.scaled(280, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_img.setCursor(Qt.CursorShape.PointingHandCursor)
                lbl_img.mousePressEvent = lambda e: self.ver_detalle_signal.emit(self.idx)
                lay.addWidget(lbl_img)
        else:
            texto = self.item.get("texto", "")
            if self.item.get("enmascarado", False):
                preview = "••••••••••••••••••••••••••••••••••••••••"
            else:
                preview = texto[:MAX_PREVIEW] + ("…" if len(texto) > MAX_PREVIEW else "")

            lbl_txt = QLabel(preview)
            lbl_txt.setStyleSheet(f"color: {self.colores.get('fg_principal', '#E2E2E2')}; font-size: 11px;")
            lbl_txt.setWordWrap(True)
            lbl_txt.setMaximumHeight(70)
            lbl_txt.setCursor(Qt.CursorShape.PointingHandCursor)
            lbl_txt.mousePressEvent = lambda e: self.ver_detalle_signal.emit(self.idx)
            lay.addWidget(lbl_txt)

            # ── Acciones Rápidas Contextuales Inteligentes ──
            acts_lay = QHBoxLayout()
            acts_lay.setSpacing(6)

            if tipo == "url":
                btn_url = QPushButton("🌐 Abrir Enlace")
                btn_url.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_url.setStyleSheet("background: rgba(59,130,246,0.2); color: #60A5FA; border: none; border-radius: 4px; padding: 2px 8px; font-size: 9px; font-weight: bold;")
                btn_url.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(texto.strip())))
                acts_lay.addWidget(btn_url)

            elif tipo == "email":
                btn_mail = QPushButton("📧 Enviar Correo")
                btn_mail.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_mail.setStyleSheet("background: rgba(168,85,247,0.2); color: #C084FC; border: none; border-radius: 4px; padding: 2px 8px; font-size: 9px; font-weight: bold;")
                btn_mail.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"mailto:{texto.strip()}")))
                acts_lay.addWidget(btn_mail)

            elif tipo in ["color_hex", "color_rgb"]:
                swatch = QLabel()
                swatch.setFixedSize(14, 14)
                swatch.setStyleSheet(f"background-color: {texto.strip()}; border-radius: 3px; border: 1px solid white;")
                acts_lay.addWidget(swatch)
                lbl_color = QLabel(f"Color: {texto.strip()}")
                lbl_color.setStyleSheet("color: #E2E2E2; font-size: 9px; font-family: Consolas;")
                acts_lay.addWidget(lbl_color)

            elif tipo == "json":
                btn_json = QPushButton("✨ Enviar a Formateador")
                btn_json.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_json.setStyleSheet("background: rgba(234,179,8,0.2); color: #FBBF24; border: none; border-radius: 4px; padding: 2px 8px; font-size: 9px; font-weight: bold;")
                btn_json.clicked.connect(lambda: self.enviar_herramientas_signal.emit(texto))
                acts_lay.addWidget(btn_json)

            elif tipo == "archivo":
                btn_file = QPushButton("📂 Abrir Carpeta")
                btn_file.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_file.setStyleSheet("background: rgba(16,185,129,0.2); color: #34D399; border: none; border-radius: 4px; padding: 2px 8px; font-size: 9px; font-weight: bold;")
                def abrir_arch(p=texto.strip()):
                    target = Path(p).parent if Path(p).is_file() else Path(p)
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
                btn_file.clicked.connect(abrir_arch)
                acts_lay.addWidget(btn_file)

            # Evaluación matemática rápida
            if re.match(r'^[\d\s\+\-\*\/\(\)\.]+$', texto.strip()) and len(texto.strip()) > 2:
                try:
                    res = eval(texto.strip())
                    btn_calc = QPushButton(f"⚡ = {res}")
                    btn_calc.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_calc.setStyleSheet("background: rgba(52,211,153,0.2); color: #34D399; border: none; border-radius: 4px; padding: 2px 8px; font-size: 9px; font-weight: bold;")
                    btn_calc.clicked.connect(lambda: QApplication.clipboard().setText(str(res)))
                    acts_lay.addWidget(btn_calc)
                except Exception:
                    pass

            btn_det = QPushButton("🔍 Detalle")
            btn_det.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_det.setStyleSheet("background: rgba(255,255,255,0.06); color: #CCC; border: none; border-radius: 4px; padding: 2px 6px; font-size: 9px;")
            btn_det.clicked.connect(lambda: self.ver_detalle_signal.emit(self.idx))
            acts_lay.addWidget(btn_det)

            btn_mask = QPushButton("🔑 " + ("Ver" if self.item.get("enmascarado") else "Ocultar"))
            btn_mask.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_mask.setStyleSheet("background: rgba(255,255,255,0.06); color: #CCC; border: none; border-radius: 4px; padding: 2px 6px; font-size: 9px;")
            btn_mask.clicked.connect(self._toggle_mask)
            acts_lay.addWidget(btn_mask)

            acts_lay.addStretch()
            lay.addLayout(acts_lay)

        # ── Botones de Acción de Tarjeta ──
        b_lay = QHBoxLayout()
        b_lay.setSpacing(6)

        btn_copy = QPushButton("📋 Copiar")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(f"background: rgba(99,102,241,0.18); color: {self.colores.get('acento', '#6366F1')}; border: 1px solid {self.colores.get('acento', '#6366F1')}; border-radius: 6px; padding: 5px 12px; font-size: 10px; font-weight: bold;")
        btn_copy.clicked.connect(lambda: self.pegar_signal.emit(self.idx))
        b_lay.addWidget(btn_copy)

        btn_star = QPushButton("⭐ Guardado" if fijado else "☆ Guardar para después")
        btn_star.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_star.setStyleSheet("background: rgba(251, 191, 36, 0.2); color: #FBBF24; border: 1px solid #FBBF24; border-radius: 6px; padding: 5px 10px; font-size: 10px; font-weight: bold;" if fijado else "background: rgba(255, 255, 255, 0.05); color: #D1D5DB; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 5px 10px; font-size: 10px; font-weight: bold;")
        btn_star.setToolTip("Guarda y fija esta copia de forma permanente para que nunca se borre automáticamente.")
        btn_star.clicked.connect(lambda: self.fijar_signal.emit(self.idx))
        b_lay.addWidget(btn_star)

        if not es_img:
            btn_snip = QPushButton("📌 A Snippets")
            btn_snip.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_snip.setStyleSheet("background: rgba(255, 255, 255, 0.05); color: #AAB0B8; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 5px 10px; font-size: 10px; font-weight: bold;")
            btn_snip.setToolTip("Guarda esta copia en el armario de Snippets y Plantillas para usarla cuando quieras.")
            btn_snip.clicked.connect(lambda: self.guardar_snippet_signal.emit(texto))
            b_lay.addWidget(btn_snip)

        b_lay.addStretch()
        lay.addLayout(b_lay)

    def _toggle_mask(self):
        self.item["enmascarado"] = not self.item.get("enmascarado", False)
        self._build()

    def _mostrar_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {self.colores.get('bg_terciario', '#2D2D3D')}; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08); }}
            QMenu::item {{ color: white; padding: 6px 18px; }}
            QMenu::item:selected {{ background: {self.colores.get('acento', '#6366F1')}; }}
        """)
        pin_txt = "⭐ Desmarcar de Guardados" if self.item.get("fijado") else "⭐ Guardar para después"
        menu.addAction(pin_txt, lambda: self.fijar_signal.emit(self.idx))
        menu.addAction("🔍 Ver Pantalla Completa", lambda: self.ver_detalle_signal.emit(self.idx))
        if self.item.get("tipo") != "imagen":
            menu.addAction("📌 Guardar como Snippet / Plantilla", lambda: self.guardar_snippet_signal.emit(self.item.get("texto", "")))
            menu.addAction("✨ Abrir en Herramientas de Texto", lambda: self.enviar_herramientas_signal.emit(self.item.get("texto", "")))
        menu.addSeparator()
        menu.addAction("🗑️ Eliminar", lambda: self.eliminar_signal.emit(self.idx))
        menu.exec(QCursor.pos())


class TabHistorialClipboard(QWidget):
    """Submódulo principal del historial de portapapeles con pausa, modo privado y filtros."""
    enviar_a_herramientas = pyqtSignal(str)
    guardar_como_snippet = pyqtSignal(str)

    def __init__(self, parent=None, colores=None, ruta_data=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.ruta_data = ruta_data or Path("clipboard_historial.json")

        self.historial = []
        self._ultimo_texto = ""
        self._ultimo_img_hash = None
        self._is_updating_clipboard = False
        self._pausado = False
        self._modo_privado = False
        self._cards_refs = []
        self.filtro_chip_activo = "todos"
        self._chip_btns = {}

        self.cargar_datos()
        self.init_ui()

        # Monitor de portapapeles
        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self._on_clipboard_changed)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_clipboard)
        self._timer.start(1200)

    def init_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(16, 16, 16, 16)
        main_lay.setSpacing(10)

        # ── Header Superior ──
        hdr = QHBoxLayout()
        lbl_tit = QLabel("🗃️ HISTORIAL DEL PORTAPAPELES")
        lbl_tit.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        hdr.addWidget(lbl_tit)
        hdr.addStretch()

        self.lbl_count = QLabel("0 elementos")
        self.lbl_count.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 11px;")
        hdr.addWidget(self.lbl_count)

        # Botón Guardar Nueva Copia Manualmente
        btn_nueva_copia = QPushButton("➕ Guardar Nueva Copia")
        btn_nueva_copia.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nueva_copia.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')}; color: white;
                border: none; border-radius: 6px; padding: 5px 12px;
                font-weight: bold; font-size: 10px;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_nueva_copia.setToolTip("Escribe o pega una copia manualmente para guardarla para después.")
        btn_nueva_copia.clicked.connect(self._dialog_nueva_copia)
        hdr.addWidget(btn_nueva_copia)

        # Botón Pausar / Reanudar Captura
        self.btn_pausa = QPushButton("⏸️ Pausar")
        self.btn_pausa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pausa.setToolTip("Pausar temporalmente el monitoreo de portapapeles")
        self.btn_pausa.setStyleSheet(self._btn_hdr_style())
        self.btn_pausa.clicked.connect(self._toggle_pausa)
        hdr.addWidget(self.btn_pausa)

        # Botón Modo Privado / Incógnito
        self.btn_privado = QPushButton("🛡️ Modo Privado: OFF")
        self.btn_privado.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_privado.setToolTip("Enmascara automáticamente los clips nuevos para proteger contraseñas")
        self.btn_privado.setStyleSheet(self._btn_hdr_style())
        self.btn_privado.clicked.connect(self._toggle_privado)
        hdr.addWidget(self.btn_privado)

        btn_exp = QPushButton("📤 Exportar")
        btn_exp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exp.setStyleSheet(self._btn_hdr_style())
        btn_exp.clicked.connect(self._exportar_historial)
        hdr.addWidget(btn_exp)

        btn_limpiar = QPushButton("🗑️ Limpiar")
        btn_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_limpiar.setStyleSheet("background: rgba(248,113,113,0.15); color: #F87171; border: 1px solid rgba(248,113,113,0.3); border-radius: 6px; padding: 5px 12px; font-weight: bold; font-size: 10px;")
        btn_limpiar.clicked.connect(self._limpiar_historial)
        hdr.addWidget(btn_limpiar)

        main_lay.addLayout(hdr)

        # ── Barra de Búsqueda y Filtros ──
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar texto, enlaces o números en el historial...")
        self.txt_buscar.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white;
                border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); padding: 6px 12px;
                font-size: 11px;
            }}
            QLineEdit:focus {{ border-color: {self.colores.get('acento', '#6366F1')}; }}
        """)
        self.txt_buscar.textChanged.connect(self.refrescar_lista)
        bar.addWidget(self.txt_buscar, 1)

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Todos los tipos", "🔗 Enlaces URL", "📧 Correos", "🎨 Colores HEX/RGB", "🔢 Números", "✨ JSON", "📂 Archivos", "💻 Código", "🖼️ Imágenes", "📌 Solo Fijados"])
        self.combo_tipo.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white;
                border-radius: 6px; padding: 5px 10px; border: 1px solid rgba(255,255,255,0.1);
                font-size: 11px;
            }}
        """)
        self.combo_tipo.currentIndexChanged.connect(self.refrescar_lista)
        bar.addWidget(self.combo_tipo)
        main_lay.addLayout(bar)

        # ── Chips de Acceso Rápido ──
        chips_lay = QHBoxLayout()
        chips_lay.setSpacing(6)
        lbl_chip_tit = QLabel("Acceso:")
        lbl_chip_tit.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px; font-weight: bold;")
        chips_lay.addWidget(lbl_chip_tit)

        self._chip_btns = {}
        for chip_id, chip_label in [
            ("todos", "📋 Todos"),
            ("fijados", "⭐ Guardados para después"),
            ("textos", "📄 Textos"),
            ("imagenes", "🖼️ Imágenes"),
            ("codigo", "💻 Código")
        ]:
            b_chip = QPushButton(chip_label)
            b_chip.setCursor(Qt.CursorShape.PointingHandCursor)
            b_chip.clicked.connect(lambda ch, cid=chip_id: self._activar_chip_filtro(cid))
            self._chip_btns[chip_id] = b_chip
            chips_lay.addWidget(b_chip)

        chips_lay.addStretch()
        main_lay.addLayout(chips_lay)
        self._actualizar_estilo_chips()

        # ── Contenedor Scroll ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cont_items = QWidget()
        self.lay_items = QVBoxLayout(self.cont_items)
        self.lay_items.setSpacing(8)
        self.lay_items.addStretch()
        scroll.setWidget(self.cont_items)
        main_lay.addWidget(scroll, 1)

        self.refrescar_lista()

    def _btn_hdr_style(self):
        return f"""
            QPushButton {{
                background: rgba(255,255,255,0.06); color: white;
                border: 1px solid rgba(255,255,255,0.1); border-radius: 6px;
                padding: 5px 10px; font-weight: bold; font-size: 10px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.12);
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """

    def _toggle_pausa(self):
        self._pausado = not self._pausado
        if self._pausado:
            self.btn_pausa.setText("▶️ Reanudar")
            self.btn_pausa.setStyleSheet("background: rgba(245,158,11,0.2); color: #FBBF24; border: 1px solid #FBBF24; border-radius: 6px; padding: 5px 10px; font-weight: bold; font-size: 10px;")
        else:
            self.btn_pausa.setText("⏸️ Pausar")
            self.btn_pausa.setStyleSheet(self._btn_hdr_style())

    def _toggle_privado(self):
        self._modo_privado = not self._modo_privado
        if self._modo_privado:
            self.btn_privado.setText("🛡️ Modo Privado: ON")
            self.btn_privado.setStyleSheet("background: rgba(99,102,241,0.25); color: #818CF8; border: 1px solid #818CF8; border-radius: 6px; padding: 5px 10px; font-weight: bold; font-size: 10px;")
        else:
            self.btn_privado.setText("🛡️ Modo Privado: OFF")
            self.btn_privado.setStyleSheet(self._btn_hdr_style())

    def cargar_datos(self):
        if self.ruta_data.exists():
            try:
                with open(self.ruta_data, "r", encoding="utf-8") as f:
                    self.historial = json.load(f)
            except Exception:
                self.historial = []

    def guardar_datos(self):
        try:
            with open(self.ruta_data, "w", encoding="utf-8") as f:
                json.dump(self.historial, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _on_clipboard_changed(self):
        self._check_clipboard()

    def _check_clipboard(self):
        if self._is_updating_clipboard or self._pausado:
            return

        # 1. Comprobar imagen
        qimg = self._clipboard.image()
        if not qimg.isNull() and qimg.width() > 0 and qimg.height() > 0:
            try:
                bpl = qimg.bytesPerLine()
                h = qimg.height()
                ptr = qimg.constBits()
                ptr.setsize(h * bpl)
                img_hash = hashlib.md5(bytes(ptr)).hexdigest()

                if img_hash == self._ultimo_img_hash:
                    return

                self._ultimo_img_hash = img_hash

                img_dir = self.ruta_data.parent / "clip_images"
                img_dir.mkdir(parents=True, exist_ok=True)
                img_path = img_dir / f"clip_{img_hash[:12]}.png"
                if not img_path.exists():
                    qimg.save(str(img_path), "PNG")

                item = {
                    "tipo": "imagen",
                    "ruta_img": str(img_path),
                    "hash": img_hash,
                    "fecha": datetime.now().strftime("%d/%m %H:%M"),
                    "fijado": False,
                    "enmascarado": self._modo_privado
                }
                self._agregar_item_dict(item)
                return
            except Exception as e:
                print(f"[TabHistorialClipboard] Error procesando imagen: {e}")
        else:
            self._ultimo_img_hash = None

        # 2. Comprobar texto
        texto = self._clipboard.text()
        if texto and texto != self._ultimo_texto:
            self._ultimo_texto = texto
            item = {
                "tipo": "texto",
                "texto": texto,
                "fecha": datetime.now().strftime("%d/%m %H:%M"),
                "fijado": False,
                "enmascarado": self._modo_privado
            }
            self._agregar_item_dict(item)

    def _agregar_item_dict(self, item):
        if self.historial:
            if item.get("tipo") == "texto" and self.historial[0].get("texto") == item.get("texto"):
                return
            if item.get("tipo") == "imagen":
                if self.historial[0].get("tipo") == "imagen" and (
                    self.historial[0].get("hash") == item.get("hash") or 
                    self.historial[0].get("ruta_img") == item.get("ruta_img")
                ):
                    return
        self.historial.insert(0, item)
        no_fijados = [x for x in self.historial if not x.get("fijado")]
        while len(no_fijados) > MAX_ITEMS:
            for i in range(len(self.historial) - 1, -1, -1):
                if not self.historial[i].get("fijado"):
                    self.historial.pop(i)
                    break
            no_fijados = [x for x in self.historial if not x.get("fijado")]
        self.guardar_datos()
        self.refrescar_lista()

    def refrescar_lista(self):
        while self.lay_items.count() > 1:
            item = self.lay_items.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards_refs.clear()

        query = self.txt_buscar.text().strip().lower()
        idx_filtro = self.combo_tipo.currentIndex()

        # ["Todos los tipos", "🔗 Enlaces URL", "📧 Correos", "🎨 Colores HEX/RGB", "🔢 Números", "✨ JSON", "📂 Archivos", "💻 Código", "🖼️ Imágenes", "📌 Solo Fijados"]
        filtro_clave = ["", "url", "email", "color", "numero", "json", "archivo", "codigo", "imagen", "fijados"][idx_filtro]

        visibles = 0
        for idx, item in enumerate(self.historial):
            txt = item.get("texto", "")
            es_img = item.get("tipo") == "imagen"
            tipo_item, _ = ("imagen", "🖼️") if es_img else _detectar_tipo(txt)

            if query and (query not in txt.lower() and query not in item.get("fecha", "").lower()):
                continue

            # Filtro por Chips de acceso rápido
            if self.filtro_chip_activo == "fijados" and not item.get("fijado"):
                continue
            elif self.filtro_chip_activo == "textos" and es_img:
                continue
            elif self.filtro_chip_activo == "imagenes" and not es_img:
                continue
            elif self.filtro_chip_activo == "codigo" and tipo_item != "codigo":
                continue

            # Filtro por ComboBox de tipos
            if filtro_clave:
                if filtro_clave == "fijados" and not item.get("fijado"):
                    continue
                elif filtro_clave == "imagen" and not es_img:
                    continue
                elif filtro_clave == "color" and tipo_item not in ["color_hex", "color_rgb"]:
                    continue
                elif filtro_clave not in ["fijados", "imagen", "color"] and tipo_item != filtro_clave:
                    continue

            card = ClipItemCard(idx, item, self.colores)
            card.pegar_signal.connect(self._pegar_item)
            card.fijar_signal.connect(self._fijar_item)
            card.eliminar_signal.connect(self._eliminar_item)
            card.ver_detalle_signal.connect(self._ver_detalle_item)
            card.enviar_herramientas_signal.connect(self.enviar_a_herramientas.emit)
            card.guardar_snippet_signal.connect(self.guardar_como_snippet.emit)

            self.lay_items.insertWidget(self.lay_items.count() - 1, card)
            self._cards_refs.append(card)
            visibles += 1

        if visibles == 0:
            empty_card = QFrame()
            empty_card.setStyleSheet(f"""
                QFrame {{
                    background: rgba(30, 30, 46, 0.35);
                    border: 1px dashed rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    padding: 30px;
                }}
            """)
            e_lay = QVBoxLayout(empty_card)
            e_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ico = QLabel("📋")
            ico.setFont(QFont("Segoe UI Emoji", 36))
            ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
            e_lay.addWidget(ico)

            tit = QLabel("El historial está vacío")
            tit.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tit.setStyleSheet("color: white;")
            e_lay.addWidget(tit)

            desc = QLabel("Copia cualquier texto, enlace o imagen (Ctrl+C) en cualquier aplicación para verlo aquí al instante.")
            desc.setFont(QFont("Segoe UI", 10))
            desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc.setWordWrap(True)
            desc.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; max-width: 440px;")
            e_lay.addWidget(desc)

            self.lay_items.insertWidget(0, empty_card)

        self.lbl_count.setText(f"{len(self.historial)} elementos ({visibles} visibles)")

    def _activar_chip_filtro(self, cid):
        self.filtro_chip_activo = cid
        self._actualizar_estilo_chips()
        self.refrescar_lista()

    def _actualizar_estilo_chips(self):
        for cid, btn in self._chip_btns.items():
            if cid == self.filtro_chip_activo:
                btn.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border: 1px solid {self.colores.get('acento', '#6366F1')}; border-radius: 6px; padding: 3px 10px; font-size: 10px; font-weight: bold;")
            else:
                btn.setStyleSheet("background: rgba(255, 255, 255, 0.05); color: #AAB0B8; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 3px 10px; font-size: 10px;")

    def _dialog_nueva_copia(self):
        """Permite guardar manualmente una copia de texto con opción de guardado permanente."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Guardar Nueva Copia en Portapapeles")
        dlg.setMinimumWidth(440)
        dlg.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; color: white;")
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Texto o contenido a guardar para después:"))
        txt_input = QPlainTextEdit()
        txt_input.setPlaceholderText("Pega o escribe aquí el texto, notas, claves o enlaces...")
        txt_input.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 6px; padding: 8px; border: 1px solid rgba(255,255,255,0.1); font-family: Consolas, monospace;")
        lay.addWidget(txt_input)

        chk_fijar = QCheckBox("⭐ Guardar permanentemente para después (fijar)")
        chk_fijar.setChecked(True)
        chk_fijar.setStyleSheet("color: #FBBF24; font-weight: bold; font-size: 11px;")
        lay.addWidget(chk_fijar)

        btn_guardar = QPushButton("💾 Guardar Copia")
        btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guardar.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; font-weight: bold; border-radius: 6px; padding: 8px; border: none;")

        def guardar():
            contenido = txt_input.toPlainText().strip()
            if not contenido:
                QMessageBox.warning(dlg, "Texto vacío", "Por favor ingresa texto para guardar.")
                return
            item = {
                "tipo": "texto",
                "texto": contenido,
                "fecha": datetime.now().strftime("%d/%m %H:%M"),
                "fijado": chk_fijar.isChecked(),
                "enmascarado": self._modo_privado
            }
            self.historial.insert(0, item)
            self.guardar_datos()
            self.refrescar_lista()
            dlg.accept()

        btn_guardar.clicked.connect(guardar)
        lay.addWidget(btn_guardar)
        dlg.exec()

    def _pegar_item(self, idx):
        if 0 <= idx < len(self.historial):
            self._is_updating_clipboard = True
            try:
                item = self.historial[idx]
                if item.get("tipo") == "imagen" and Path(item.get("ruta_img", "")).exists():
                    pix = QPixmap(item["ruta_img"])
                    self._clipboard.setPixmap(pix)
                else:
                    self._clipboard.setText(item.get("texto", ""))
                    self._ultimo_texto = item.get("texto", "")
                self.historial.pop(idx)
                item["fecha"] = datetime.now().strftime("%d/%m %H:%M")
                self.historial.insert(0, item)
                self.guardar_datos()
                self.refrescar_lista()
            finally:
                self._is_updating_clipboard = False

    def _fijar_item(self, idx):
        if 0 <= idx < len(self.historial):
            self.historial[idx]["fijado"] = not self.historial[idx].get("fijado", False)
            self.guardar_datos()
            self.refrescar_lista()

    def _eliminar_item(self, idx):
        if 0 <= idx < len(self.historial):
            self.historial.pop(idx)
            self.guardar_datos()
            self.refrescar_lista()

    def _ver_detalle_item(self, idx):
        if 0 <= idx < len(self.historial):
            item = self.historial[idx]
            dlg = ClipDetalleDialog(item, self.colores, self)
            dlg.guardar_como_snippet_signal.connect(self.guardar_como_snippet.emit)
            dlg.exec()
            self.guardar_datos()
            self.refrescar_lista()

    def _limpiar_historial(self):
        resp = QMessageBox.question(self, "Limpiar Historial", "¿Deseas borrar los elementos no fijados del historial?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            self.historial = [x for x in self.historial if x.get("fijado")]
            self.guardar_datos()
            self.refrescar_lista()

    def _exportar_historial(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Historial", "historial_clipboard.json", "JSON (*.json);;Texto (*.txt)")
        if not path:
            return
        try:
            if path.endswith(".txt"):
                lineas = [x.get("texto", f"[Imagen: {x.get('ruta_img')}]") for x in self.historial]
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n\n---\n\n".join(lineas))
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.historial, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Exportado", f"Se exportaron {len(self.historial)} elementos exitosamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar: {e}")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.refrescar_lista()

    def cleanup(self):
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()
