import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class HistorialFavoritosSubmodule(QWidget):
    """Submódulo 4: Historial de Traducciones & Favoritos Persistentes"""
    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("⭐ FAVORITOS & 🕐 HISTORIAL DE TRADUCCIÓN")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        layout.addLayout(hdr)

        # Layout de 2 Columnas
        cols_lay = QHBoxLayout()
        cols_lay.setSpacing(15)

        # =========================================================================
        # COLUMNA IZQUIERDA: FAVORITOS
        # =========================================================================
        self.fav_frame = QFrame()
        self.fav_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }}
        """)
        f_lay = QVBoxLayout(self.fav_frame)
        f_lay.setContentsMargins(15, 12, 15, 12)
        f_lay.setSpacing(10)

        lbl_f_h = QLabel("⭐ Traducciones Guardadas en Favoritos")
        lbl_f_h.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_f_h.setStyleSheet(f"color: {self.colores['advertencia']};")
        f_lay.addWidget(lbl_f_h)

        self.list_favs = QListWidget()
        self.list_favs.setFont(QFont(self.font_family, 9))
        self.list_favs.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
            }}
            QListWidget::item {{
                padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.05);
            }}
            QListWidget::item:selected {{
                background-color: {self.colores['acento']}; color: white;
            }}
        """)
        self.list_favs.itemDoubleClicked.connect(self._cargar_fav_al_editor)
        f_lay.addWidget(self.list_favs, 1)

        fav_btns = QHBoxLayout()
        btn_del_fav = QPushButton("🗑️ Eliminar")
        btn_del_fav.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_fav.setStyleSheet(f"background-color: {self.colores['error']}; color: white; padding: 6px 12px; border-radius: 6px; border: none;")
        btn_del_fav.clicked.connect(self._eliminar_favorito)
        fav_btns.addWidget(btn_del_fav)

        btn_copy_fav = QPushButton("📋 Copiar")
        btn_copy_fav.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_fav.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; padding: 6px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        btn_copy_fav.clicked.connect(self._copiar_favorito)
        fav_btns.addWidget(btn_copy_fav)

        f_lay.addLayout(fav_btns)
        cols_lay.addWidget(self.fav_frame, 1)

        # =========================================================================
        # COLUMNA DERECHA: HISTORIAL
        # =========================================================================
        self.hist_frame = QFrame()
        self.hist_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }}
        """)
        h_lay = QVBoxLayout(self.hist_frame)
        h_lay.setContentsMargins(15, 12, 15, 12)
        h_lay.setSpacing(10)

        lbl_h_h = QLabel("🕐 Historial Reciente de Traducción")
        lbl_h_h.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_h_h.setStyleSheet("color: white;")
        h_lay.addWidget(lbl_h_h)

        self.list_hist = QListWidget()
        self.list_hist.setFont(QFont(self.font_family, 9))
        self.list_hist.setStyleSheet(self.list_favs.styleSheet())
        self.list_hist.itemDoubleClicked.connect(self._cargar_hist_al_editor)
        h_lay.addWidget(self.list_hist, 1)

        hist_btns = QHBoxLayout()
        btn_clr_hist = QPushButton("🗑️ Limpiar Historial")
        btn_clr_hist.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clr_hist.setStyleSheet(f"background-color: {self.colores['error']}; color: white; padding: 6px 12px; border-radius: 6px; border: none;")
        btn_clr_hist.clicked.connect(self._limpiar_historial)
        hist_btns.addWidget(btn_clr_hist)

        h_lay.addLayout(hist_btns)
        cols_lay.addWidget(self.hist_frame, 1)

        layout.addLayout(cols_lay)

        self.refrescar_favoritos()
        self.refrescar_historial()

    def actualizar_tema(self, colores: dict):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#121218')
        bg_sec = colores.get('bg_secundario', '#1E1E2E')
        bg_terc = colores.get('bg_terciario', '#2D2D3D')
        acento = colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        frame_style = f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }}
        """
        if hasattr(self, 'fav_frame'):
            self.fav_frame.setStyleSheet(frame_style)
        if hasattr(self, 'hist_frame'):
            self.hist_frame.setStyleSheet(frame_style)

        list_style = f"""
            QListWidget {{
                background-color: {bg_terc};
                color: white; border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
            }}
            QListWidget::item {{
                padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.05);
            }}
            QListWidget::item:selected {{
                background-color: {acento}; color: white;
            }}
        """
        self.list_favs.setStyleSheet(list_style)
        self.list_hist.setStyleSheet(list_style)

    def cleanup(self):
        pass

    def refrescar_favoritos(self):
        self.list_favs.clear()
        favs = self.manager.favoritos
        for f in favs:
            item = QListWidgetItem(f"⭐ {f.get('origen', 'auto')} → {f.get('destino', 'es')}: {f.get('original', '')[:30]}...")
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.list_favs.addItem(item)

    def refrescar_historial(self):
        self.list_hist.clear()
        hist = self.manager.historial
        for h in hist:
            item = QListWidgetItem(f"🕐 {h.get('origen', 'auto')} → {h.get('destino', 'es')}: {h.get('original', '')[:35]}...")
            item.setData(Qt.ItemDataRole.UserRole, h)
            self.list_hist.addItem(item)

    def agregar_favorito(self, orig, trad, origen, destino):
        favs = self.manager.favoritos
        favs.append({"original": orig, "traducido": trad, "origen": origen, "destino": destino})
        self.manager.guardar_favoritos(favs)
        self.refrescar_favoritos()

    def agregar_historial(self, orig, trad, origen, destino):
        hist = self.manager.historial
        hist.insert(0, {"original": orig, "traducido": trad, "origen": origen, "destino": destino})
        self.manager.guardar_historial(hist)
        self.refrescar_historial()

    def _eliminar_favorito(self):
        curr = self.list_favs.currentRow()
        if curr >= 0:
            favs = self.manager.favoritos
            if 0 <= curr < len(favs):
                favs.pop(curr)
                self.manager.guardar_favoritos(favs)
                self.refrescar_favoritos()

    def _copiar_favorito(self):
        item = self.list_favs.currentItem()
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                QApplication.clipboard().setText(data.get("traducido", ""))
                QMessageBox.information(self, "Copiado", "Traducción copiada al portapapeles.")

    def _limpiar_historial(self):
        self.manager.guardar_historial([])
        self.refrescar_historial()

    def _cargar_fav_al_editor(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and "cargar_al_editor" in self.callbacks:
            self.callbacks["cargar_al_editor"](data.get("original", ""), data.get("traducido", ""))

    def _cargar_hist_al_editor(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and "cargar_al_editor" in self.callbacks:
            self.callbacks["cargar_al_editor"](data.get("original", ""), data.get("traducido", ""))
