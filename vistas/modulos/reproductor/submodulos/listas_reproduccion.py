import os
import shutil
import string
import ctypes
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QFileDialog, QMessageBox, 
    QInputDialog, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class ListasReproduccionSubmodule(QWidget):
    """Submódulo 3: Playlists Físicas en la Cuenta de Usuario & Biblioteca Multimedia Escaneada"""
    def __init__(self, parent, context, manager, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        # Ruta base física de Playlists dentro de la cuenta del usuario
        if self.context and hasattr(self.context, 'ruta_usuario') and self.context.ruta_usuario:
            self.playlists_dir = Path(self.context.ruta_usuario) / "playlists"
        else:
            self.playlists_dir = Path.home() / "Music" / "Playlists"
        self.playlists_dir.mkdir(parents=True, exist_ok=True)

        # Crear al menos una playlist por defecto si no hay ninguna
        def_pl = self.playlists_dir / "Mis Favoritas"
        def_pl.mkdir(parents=True, exist_ok=True)

        self.mapa_archivos = {}
        self.inicializar_ui()
        self.refrescar_selector_playlists()
        self.refrescar_biblioteca()

    def inicializar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("🎵 BIBLIOTECA MULTIMEDIA & PLAYLISTS DE LA CUENTA")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        btn_rescan = QPushButton("🔄 Re-escanear Archivos & USB")
        btn_rescan.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rescan.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_rescan.setStyleSheet(f"background-color: {self.colores.get('acento', '#6366F1')}; color: white; padding: 6px 14px; border-radius: 6px; border: none;")
        btn_rescan.clicked.connect(self.refrescar_biblioteca)
        hdr.addWidget(btn_rescan)

        layout.addLayout(hdr)

        # Layout de 2 Columnas (Biblioteca Escaneada vs Playlists Físicas)
        cols_lay = QHBoxLayout()
        cols_lay.setSpacing(15)

        # ---------------------------------------------------------------------
        # COLUMNA IZQUIERDA: BIBLIOTECA LOCAL & USB
        # ---------------------------------------------------------------------
        lib_frame = QFrame()
        lib_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }}
        """)
        l_lay = QVBoxLayout(lib_frame)
        l_lay.setContentsMargins(15, 12, 15, 12)
        l_lay.setSpacing(10)

        lbl_l_h = QLabel("📁 Biblioteca Local & Dispositivos USB")
        lbl_l_h.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_l_h.setStyleSheet("color: white;")
        l_lay.addWidget(lbl_l_h)

        self.list_lib = QListWidget()
        self.list_lib.setFont(QFont(self.font_family, 9))
        self.list_lib.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white; border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
            }}
            QListWidget::item {{
                padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.05);
            }}
            QListWidget::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')}; color: white;
            }}
        """)
        self.list_lib.itemDoubleClicked.connect(self._reproducir_desde_biblioteca)
        l_lay.addWidget(self.list_lib, 1)

        lib_btns = QHBoxLayout()
        btn_add_file = QPushButton("📂 Abrir y Reproducir...")
        btn_add_file.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_file.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; padding: 6px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        btn_add_file.clicked.connect(self._abrir_archivo_manual)
        lib_btns.addWidget(btn_add_file)

        btn_copy_to_pl = QPushButton("➕ Copiar a Playlist Activa")
        btn_copy_to_pl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_to_pl.setStyleSheet(f"background-color: {self.colores.get('acento', '#6366F1')}; color: white; padding: 6px 12px; border-radius: 6px; border: none; font-weight: bold;")
        btn_copy_to_pl.clicked.connect(self._copiar_seleccionado_a_playlist)
        lib_btns.addWidget(btn_copy_to_pl)

        l_lay.addLayout(lib_btns)
        cols_lay.addWidget(lib_frame, 1)

        # ---------------------------------------------------------------------
        # COLUMNA DERECHA: PLAYLISTS FÍSICAS EN LA CUENTA
        # ---------------------------------------------------------------------
        pl_frame = QFrame()
        pl_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }}
        """)
        p_lay = QVBoxLayout(pl_frame)
        p_lay.setContentsMargins(15, 12, 15, 12)
        p_lay.setSpacing(10)

        # Fila superior de selección y gestión de Playlist
        top_pl_row = QHBoxLayout()
        lbl_p_h = QLabel("⭐ Playlist:")
        lbl_p_h.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_p_h.setStyleSheet(f"color: {self.colores.get('advertencia', '#FBBF24')};")
        top_pl_row.addWidget(lbl_p_h)

        self.cb_playlists = QComboBox()
        self.cb_playlists.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.cb_playlists.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white; border-radius: 6px; padding: 5px 10px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white; selection-background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self.cb_playlists.currentIndexChanged.connect(self._on_playlist_seleccionada)
        top_pl_row.addWidget(self.cb_playlists, 1)

        btn_new_pl = QPushButton("✨ Nueva")
        btn_new_pl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_pl.setStyleSheet(f"background-color: {self.colores.get('acento', '#6366F1')}; color: white; padding: 5px 10px; border-radius: 6px; border: none; font-weight: bold;")
        btn_new_pl.clicked.connect(self._crear_nueva_playlist)
        top_pl_row.addWidget(btn_new_pl)

        btn_del_pl = QPushButton("🗑️")
        btn_del_pl.setToolTip("Eliminar esta Playlist")
        btn_del_pl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_pl.setStyleSheet(f"background-color: {self.colores.get('error', '#F87171')}; color: white; padding: 5px 8px; border-radius: 6px; border: none;")
        btn_del_pl.clicked.connect(self._eliminar_playlist_actual)
        top_pl_row.addWidget(btn_del_pl)

        p_lay.addLayout(top_pl_row)

        # Lista de canciones/videos de la playlist seleccionada
        self.list_playlist_items = QListWidget()
        self.list_playlist_items.setFont(QFont(self.font_family, 9))
        self.list_playlist_items.setStyleSheet(self.list_lib.styleSheet())
        self.list_playlist_items.itemDoubleClicked.connect(self._reproducir_desde_playlist)
        p_lay.addWidget(self.list_playlist_items, 1)

        # Botones inferiores de la playlist
        pl_btns = QHBoxLayout()
        btn_add_ext = QPushButton("📥 Copiar Archivos a la Playlist...")
        btn_add_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_ext.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; padding: 6px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        btn_add_ext.clicked.connect(self._importar_archivos_a_playlist)
        pl_btns.addWidget(btn_add_ext)

        btn_del_item = QPushButton("❌ Quitar de Playlist")
        btn_del_item.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_item.setStyleSheet(f"background-color: {self.colores.get('error', '#F87171')}; color: white; padding: 6px 12px; border-radius: 6px; border: none;")
        btn_del_item.clicked.connect(self._eliminar_item_de_playlist)
        pl_btns.addWidget(btn_del_item)

        p_lay.addLayout(pl_btns)
        cols_lay.addWidget(pl_frame, 1)

        layout.addLayout(cols_lay)

    def refrescar_selector_playlists(self):
        """Lee las carpetas de playlists físicas en la cuenta del usuario."""
        self.cb_playlists.blockSignals(True)
        self.cb_playlists.clear()
        
        carpetas = [d for d in self.playlists_dir.iterdir() if d.is_dir()]
        carpetas.sort(key=lambda x: x.name.lower())

        if not carpetas:
            def_dir = self.playlists_dir / "Mis Favoritas"
            def_dir.mkdir(parents=True, exist_ok=True)
            carpetas = [def_dir]

        for d in carpetas:
            self.cb_playlists.addItem(f"📁 {d.name}", str(d))

        self.cb_playlists.blockSignals(False)
        self._on_playlist_seleccionada(0)

    def _on_playlist_seleccionada(self, index):
        """Carga en la lista todos los archivos multimedia copiados en la carpeta de la playlist."""
        self.list_playlist_items.clear()
        folder_str = self.cb_playlists.currentData()
        if not folder_str:
            return

        folder_path = Path(folder_str)
        if not folder_path.exists():
            return

        archivos = []
        for f in folder_path.iterdir():
            if f.is_file() and f.suffix.lower() in ('.mp3', '.mp4', '.wav', '.m4a', '.mkv', '.flac', '.avi', '.mov'):
                archivos.append(f)

        archivos.sort(key=lambda x: x.name.lower())
        for f in archivos:
            icon = "🎬" if f.suffix.lower() in ('.mp4', '.mkv', '.avi', '.mov') else "🎵"
            item = QListWidgetItem(f"{icon} {f.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(f))
            self.list_playlist_items.addItem(item)

    def _crear_nueva_playlist(self):
        nombre, ok = QInputDialog.getText(self, "Nueva Playlist", "Nombre de la carpeta de Playlist:")
        if ok and nombre.strip():
            # Limpiar caracteres inválidos para carpetas en Windows/Linux
            nombre_limpio = "".join(c for c in nombre.strip() if c not in '<>:"/\\|?*')
            if not nombre_limpio:
                QMessageBox.warning(self, "Nombre Inválido", "Por favor ingresa un nombre válido para la playlist.")
                return

            nueva_carpeta = self.playlists_dir / nombre_limpio
            nueva_carpeta.mkdir(parents=True, exist_ok=True)
            self.refrescar_selector_playlists()
            
            # Seleccionar la recién creada
            idx = self.cb_playlists.findText(f"📁 {nombre_limpio}")
            if idx >= 0:
                self.cb_playlists.setCurrentIndex(idx)

    def _eliminar_playlist_actual(self):
        folder_str = self.cb_playlists.currentData()
        if not folder_str:
            return

        folder = Path(folder_str)
        resp = QMessageBox.question(
            self, "Eliminar Playlist",
            f"¿Estás seguro de que deseas eliminar la playlist '{folder.name}' y todos sus archivos copiados?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(folder)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar la carpeta: {e}")
            self.refrescar_selector_playlists()

    def _copiar_seleccionado_a_playlist(self):
        item = self.list_lib.currentItem()
        if not item:
            QMessageBox.information(self, "Añadir a Playlist", "Selecciona primero un archivo de la biblioteca o usa 'Copiar Archivos a la Playlist...'.")
            return

        origen = item.data(Qt.ItemDataRole.UserRole)
        self._copiar_archivo_a_playlist_activa(origen)

    def _importar_archivos_a_playlist(self):
        archivos, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar Archivos Multimedia para Copiar a la Playlist",
            str(Path.home() / "Music"),
            "Multimedia (*.mp3 *.mp4 *.wav *.m4a *.mkv *.flac *.avi *.mov);;Todos los archivos (*.*)"
        )
        if archivos:
            copiados = 0
            for a in archivos:
                if self._copiar_archivo_a_playlist_activa(a, silencioso=True):
                    copiados += 1
            self._on_playlist_seleccionada(self.cb_playlists.currentIndex())
            QMessageBox.information(self, "Archivos Copiados", f"Se copiaron con éxito {copiados} archivos a la playlist '{self.cb_playlists.currentText()}'.")

    def _copiar_archivo_a_playlist_activa(self, ruta_origen, silencioso=False):
        folder_str = self.cb_playlists.currentData()
        if not folder_str:
            return False

        destino_dir = Path(folder_str)
        if not destino_dir.exists():
            destino_dir.mkdir(parents=True, exist_ok=True)

        try:
            origen_path = Path(ruta_origen)
            if not origen_path.exists():
                if not silencioso:
                    QMessageBox.warning(self, "Archivo no encontrado", f"No se encontró el archivo origen:\n{ruta_origen}")
                return False

            destino_file = destino_dir / origen_path.name
            if destino_file.exists() and destino_file.resolve() == origen_path.resolve():
                if not silencioso:
                    QMessageBox.information(self, "Ya existe", "El archivo ya se encuentra en esta playlist.")
                return False

            shutil.copy2(str(origen_path), str(destino_file))
            if not silencioso:
                self._on_playlist_seleccionada(self.cb_playlists.currentIndex())
                QMessageBox.information(self, "Canción Copiada", f"'{origen_path.name}' se copió con éxito a la playlist '{self.cb_playlists.currentText()}'.")
            return True
        except Exception as e:
            if not silencioso:
                QMessageBox.critical(self, "Error al Copiar", f"No se pudo copiar el archivo:\n{e}")
            return False

    def _eliminar_item_de_playlist(self):
        item = self.list_playlist_items.currentItem()
        if not item:
            return

        file_path_str = item.data(Qt.ItemDataRole.UserRole)
        if not file_path_str:
            return

        p = Path(file_path_str)
        resp = QMessageBox.question(
            self, "Quitar de Playlist",
            f"¿Deseas eliminar '{p.name}' de esta playlist?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            try:
                if p.exists():
                    p.unlink()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el archivo: {e}")
            self._on_playlist_seleccionada(self.cb_playlists.currentIndex())

    def _obtener_unidades_usb(self):
        drives = []
        if os.name == 'nt':
            try:
                bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                for letter in string.ascii_uppercase:
                    if bitmask & 1:
                        drive = f"{letter}:\\"
                        if ctypes.windll.kernel32.GetDriveTypeW(drive) == 2:
                            drives.append(drive)
                    bitmask >>= 1
            except: pass
        return drives

    def refrescar_biblioteca(self):
        rutas = [Path.home() / "Music", Path.home() / "Videos"]
        if self.context and hasattr(self.context, 'ruta_usuario') and self.context.ruta_usuario:
            rutas.append(Path(self.context.ruta_usuario) / "descargas" / "musicas")
            rutas.append(Path(self.context.ruta_usuario) / "descargas" / "videos")

        for usb in self._obtener_unidades_usb():
            rutas.append(Path(usb))

        self.mapa_archivos.clear()
        self.list_lib.clear()

        for ruta in rutas:
            if not ruta.exists(): continue
            try:
                for root, dirs, filenames in os.walk(ruta):
                    for f in filenames:
                        if f.lower().endswith(('.mp3', '.mp4', '.wav', '.m4a', '.mkv', '.flac', '.avi', '.mov')):
                            full_p = os.path.join(root, f)
                            self.mapa_archivos[f] = full_p
                            icon = "🎬" if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')) else "🎶"
                            item = QListWidgetItem(f"{icon} {f}")
                            item.setData(Qt.ItemDataRole.UserRole, full_p)
                            self.list_lib.addItem(item)
            except Exception: pass

    def _reproducir_desde_biblioteca(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and "reproducir_directo" in self.callbacks:
            self.callbacks["reproducir_directo"](path)

    def _reproducir_desde_playlist(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and "reproducir_directo" in self.callbacks:
            self.callbacks["reproducir_directo"](path)

    def _abrir_archivo_manual(self):
        f, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo Multimedia", str(Path.home() / "Music"), "Archivos Multimedia (*.mp3 *.mp4 *.wav *.m4a *.mkv *.flac *.avi *.mov)")
        if f:
            if "reproducir_directo" in self.callbacks:
                self.callbacks["reproducir_directo"](f)

    def actualizar_tema(self, colores):
        self.colores = colores
