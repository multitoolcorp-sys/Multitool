"""
extensions_dialog.py - Panel emergente visual para gestionar extensiones en Microsoft Edge WebView2
"""

import os
import json
import uuid
import zipfile
import io
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QWidget, QFrame, QCheckBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QIcon, QPixmap


class ExtensionsDialog(QDialog):
    """Panel de gestión de extensiones instaladas para Microsoft Edge WebView2."""
    def __init__(self, parent_browser, colores, user_data_folder):
        super().__init__(parent_browser)
        self.parent_browser = parent_browser
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#FFFFFF", "fg_secundario": "#AAB0B8", "acento": "#6366F1", "acento_hover": "#818CF8"
        }
        self.user_data_folder = Path(user_data_folder)
        self.extensions_dir = self.user_data_folder / "extensions"
        self.extensions_dir.mkdir(parents=True, exist_ok=True)

        self.setWindowTitle("🧩 Gestor de Extensiones - MultiTool")
        self.setFixedWidth(520)
        self.setMinimumHeight(450)
        self.setStyleSheet(f"""
            QDialog {{ background: {self.colores['bg_principal']}; color: white; }}
            QLabel {{ color: {self.colores['fg_principal']}; font-family: 'Segoe UI', Arial; }}
            QPushButton {{
                background: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: bold;
                font-size: 11px;
                font-family: 'Segoe UI', Arial;
            }}
            QPushButton:hover {{
                background: {self.colores['acento']};
                border-color: {self.colores['acento']};
            }}
        """)

        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(18, 18, 18, 18)
        self.layout_principal.setSpacing(14)

        # Header
        top_h = QHBoxLayout()
        lbl_tit = QLabel("🧩 Extensiones del Navegador")
        lbl_tit.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']};")
        top_h.addWidget(lbl_tit)

        top_h.addStretch()

        btn_edge_store = QPushButton("🌐 Edge Add-ons (Recomendada)")
        btn_edge_store.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edge_store.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        btn_edge_store.clicked.connect(self._abrir_edge_store)
        top_h.addWidget(btn_edge_store)

        btn_store = QPushButton("🌐 Chrome Web Store")
        btn_store.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_store.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento']}; }}
        """)
        btn_store.clicked.connect(self._abrir_chrome_store)
        top_h.addWidget(btn_store)
        self.layout_principal.addLayout(top_h)

        # Barra de instalación rápida por enlace o ID
        install_frame = QFrame()
        install_frame.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 8px; padding: 6px 10px;")
        install_lay = QHBoxLayout(install_frame)
        install_lay.setContentsMargins(0, 0, 0, 0)
        install_lay.setSpacing(8)

        self.txt_ext_id = QLineEdit()
        self.txt_ext_id.setPlaceholderText("Pega el enlace de la extensión o su ID de 32 caracteres (Edge Add-ons)...")
        self.txt_ext_id.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: white;
                font-size: 11px;
                padding: 4px;
            }
        """)
        install_lay.addWidget(self.txt_ext_id, 1)

        btn_dl = QPushButton("📥 Descargar e Instalar")
        btn_dl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dl.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_dl.clicked.connect(self._instalar_por_id_o_url)
        install_lay.addWidget(btn_dl)
        self.layout_principal.addWidget(install_frame)

        lbl_sub = QLabel("Administra las extensiones activas en tu perfil de navegación:")
        lbl_sub.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 11px;")
        self.layout_principal.addWidget(lbl_sub)

        # Área de desplazamiento para lista de extensiones
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.cards_widget)
        self.layout_principal.addWidget(self.scroll_area, 1)

        # Barra inferior de acciones
        bottom_h = QHBoxLayout()
        btn_unpack = QPushButton("📂 Cargar Descomprimida...")
        btn_unpack.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_unpack.clicked.connect(self._cargar_extension_carpeta)
        bottom_h.addWidget(btn_unpack)

        btn_crx = QPushButton("📥 Instalar .CRX o .ZIP...")
        btn_crx.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_crx.clicked.connect(self._instalar_archivo_crx)
        bottom_h.addWidget(btn_crx)

        bottom_h.addStretch()

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cerrar.clicked.connect(self.accept)
        bottom_h.addWidget(btn_cerrar)

        self.layout_principal.addLayout(bottom_h)

        self.cargar_extensiones()

    def _abrir_edge_store(self):
        self.accept()
        if self.parent_browser and hasattr(self.parent_browser, "add_new_tab"):
            self.parent_browser.add_new_tab(QUrl("https://microsoftedge.microsoft.com/addons/Microsoft-Edge-Extensions-Home"), "Microsoft Edge Add-ons")

    def _abrir_chrome_store(self):
        self.accept()
        if self.parent_browser and hasattr(self.parent_browser, "add_new_tab"):
            self.parent_browser.add_new_tab(QUrl("https://chromewebstore.google.com"), "Chrome Web Store")

    def _instalar_por_id_o_url(self):
        texto = self.txt_ext_id.text().strip()
        if not texto:
            QMessageBox.warning(self, "Entrada requerida", "Por favor ingresa un enlace de extensión o su ID de 32 caracteres.")
            return

        import re
        import urllib.request
        import io
        import zipfile
        import uuid
        import json

        match = re.search(r'([a-z]{32})', texto.lower())
        if not match:
            QMessageBox.warning(self, "ID No Encontrado", "No se detectó un identificador de extensión válido de 32 caracteres.")
            return

        ext_id = match.group(1)
        urls_a_intentar = []
        if texto.startswith("http") and ".crx" in texto.lower():
            urls_a_intentar.append(texto)
        urls_a_intentar.append(
            f"https://clients2.google.com/service/update2/crx?response=redirect&prodversion=120.0.6099.130&acceptformat=crx2,crx3&x=id%3D{ext_id}%26uc"
        )
        urls_a_intentar.append(
            f"https://edge.microsoft.com/extensionwebstorebase/v1/crx?response=redirect&prod=chromiumcrx&prodchannel=&x=id%3D{ext_id}%26installsource%3Dondemand%26uc"
        )

        try:
            data = None
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            for crx_url in urls_a_intentar:
                try:
                    req = urllib.request.Request(crx_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        resp_data = resp.read()
                        if resp_data and resp_data.find(b"PK\x03\x04") != -1:
                            data = resp_data
                            break
                except Exception:
                    continue

            if not data:
                QMessageBox.warning(self, "No Encontrada", f"No se pudo descargar la extensión con ID '{ext_id}' desde Chrome Web Store ni Microsoft Edge Add-ons.")
                return

            zip_offset = data.find(b"PK\x03\x04")
            zip_bytes = io.BytesIO(data[zip_offset:])
            with zipfile.ZipFile(zip_bytes, "r") as zf:
                manifest_raw = zf.read("manifest.json").decode("utf-8", errors="ignore")
                manifest_data = json.loads(manifest_raw)
                raw_name = manifest_data.get("name", ext_id)
                if str(raw_name).startswith("__MSG_"):
                    raw_name = manifest_data.get("short_name", ext_id)
                ext_name = re.sub(r'[\\/*?:"<>| ]', "_", str(raw_name))
                ext_version = manifest_data.get("version", "1.0")
                dest_dir = self.extensions_dir / f"{ext_name}_{ext_version}_{uuid.uuid4().hex[:6]}"
                dest_dir.mkdir(parents=True, exist_ok=True)
                zf.extractall(dest_dir)

            curr = self.parent_browser.current_browser() if self.parent_browser else None
            if curr and hasattr(curr, "add_unpacked_extension_async"):
                curr.add_unpacked_extension_async(str(dest_dir), callback=lambda ok: self.cargar_extensiones())
            else:
                self.cargar_extensiones()

            self.txt_ext_id.clear()
            QMessageBox.information(self, "Extensión Instalada", f"✅ Extensión '{ext_name}' instalada correctamente.")
            self.cargar_extensiones()
        except Exception as e:
            QMessageBox.critical(self, "Error al Instalar", f"Ocurrió un error al descargar la extensión: {e}")

    def cargar_extensiones(self):
        """Refresca la lista de extensiones instaladas."""
        # Limpiar tarjetas previas
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Consultar extensiones en la carpeta local de extensiones del perfil
        carpetas = []
        if self.extensions_dir.exists():
            for p in self.extensions_dir.iterdir():
                if p.is_dir() and (p / "manifest.json").exists():
                    carpetas.append(p)

        if not carpetas:
            empty_frame = QFrame()
            empty_frame.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 10px; padding: 25px;")
            ef_lay = QVBoxLayout(empty_frame)
            ef_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty = QLabel("No hay extensiones instaladas aún.\nPuedes instalar extensiones directamente desde la Chrome Web Store o cargar carpetas locales.")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("color: #9CA3AF; font-size: 11px;")
            ef_lay.addWidget(lbl_empty)
            self.cards_layout.addWidget(empty_frame)
            return

        for ext_folder in carpetas:
            manifest_file = ext_folder / "manifest.json"
            try:
                with open(manifest_file, "r", encoding="utf-8", errors="ignore") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}

            name = meta.get("name", ext_folder.name)
            version = meta.get("version", "1.0")
            desc = meta.get("description", "Sin descripción.")
            
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {self.colores['bg_secundario']};
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 10px;
                    padding: 10px;
                }}
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(10, 8, 10, 8)
            c_lay.setSpacing(12)

            # Icono
            lbl_ico = QLabel("🧩")
            lbl_ico.setFont(QFont("Segoe UI Emoji", 20))
            lbl_ico.setFixedSize(36, 36)
            lbl_ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_lay.addWidget(lbl_ico)

            # Información
            info_lay = QVBoxLayout()
            info_lay.setSpacing(2)

            lbl_name = QLabel(f"<b>{name}</b> <span style='color: #818CF8; font-size: 10px;'>v{version}</span>")
            lbl_name.setTextFormat(Qt.TextFormat.RichText)
            info_lay.addWidget(lbl_name)

            lbl_desc = QLabel(desc[:80] + ("..." if len(desc) > 80 else ""))
            lbl_desc.setStyleSheet("color: #9CA3AF; font-size: 10px;")
            info_lay.addWidget(lbl_desc)

            c_lay.addLayout(info_lay, 1)

            # Botón eliminar
            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("Eliminar extensión")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setFixedSize(32, 32)
            btn_del.setStyleSheet("""
                QPushButton {
                    background: rgba(248, 113, 113, 0.15);
                    color: #F87171;
                    border: 1px solid rgba(248, 113, 113, 0.3);
                    border-radius: 6px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: #F87171;
                    color: white;
                }
            """)
            btn_del.clicked.connect(lambda checked=False, p=ext_folder: self._eliminar_extension(p))
            c_lay.addWidget(btn_del)

            self.cards_layout.addWidget(card)

    def _eliminar_extension(self, folder_path):
        resp = QMessageBox.question(
            self, "Confirmar Eliminación", 
            f"¿Deseas desinstalar esta extensión?\n{folder_path.name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            import shutil
            try:
                shutil.rmtree(folder_path, ignore_errors=True)
                # Si el WebView2 actual tiene API de remover
                curr = self.parent_browser.current_browser() if self.parent_browser else None
                if curr and hasattr(curr, "remove_browser_extension_by_folder"):
                    curr.remove_browser_extension_by_folder(str(folder_path))
                self.cargar_extensiones()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar la extensión: {e}")

    def _cargar_extension_carpeta(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecciona la carpeta de la extensión (con manifest.json)")
        if folder:
            f_path = Path(folder)
            if not (f_path / "manifest.json").exists():
                QMessageBox.warning(self, "Carpeta Inválida", "La carpeta seleccionada no contiene un archivo 'manifest.json'.")
                return

            curr = self.parent_browser.current_browser() if self.parent_browser else None
            if curr and hasattr(curr, "add_unpacked_extension_async"):
                curr.add_unpacked_extension_async(str(f_path), callback=lambda ok: self.cargar_extensiones())
            else:
                # Copiar a carpeta de extensiones del perfil
                import shutil
                dest = self.extensions_dir / f_path.name
                shutil.copytree(f_path, dest, dirs_exist_ok=True)
                self.cargar_extensiones()
                QMessageBox.information(self, "Extensión Agregada", f"Extensión copiada correctamente a {dest.name}.\nSe cargará en las próximas pestañas.")

    def _instalar_archivo_crx(self):
        file, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo de extensión", "", "Archivos de Extensión (*.crx *.zip)")
        if file:
            f_path = Path(file)
            try:
                with open(f_path, "rb") as f:
                    data = f.read()
                zip_offset = data.find(b"PK\x03\x04")
                if zip_offset == -1:
                    QMessageBox.warning(self, "Archivo Inválido", "El archivo no contiene un archivo ZIP o CRX válido.")
                    return

                zip_bytes = io.BytesIO(data[zip_offset:])
                with zipfile.ZipFile(zip_bytes, "r") as zf:
                    manifest_raw = zf.read("manifest.json").decode("utf-8", errors="ignore")
                    manifest_data = json.loads(manifest_raw)
                    ext_name = manifest_data.get("name", f_path.stem).replace(" ", "_")
                    target_dir = self.extensions_dir / f"{ext_name}_{uuid.uuid4().hex[:6]}"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    zf.extractall(target_dir)

                curr = self.parent_browser.current_browser() if self.parent_browser else None
                if curr and hasattr(curr, "add_unpacked_extension_async"):
                    curr.add_unpacked_extension_async(str(target_dir), callback=lambda ok: self.cargar_extensiones())
                else:
                    self.cargar_extensiones()
                QMessageBox.information(self, "Extensión Instalada", f"✅ Extensión '{ext_name}' instalada con éxito.")
            except Exception as e:
                QMessageBox.critical(self, "Error al Instalar", f"No se pudo desempaquetar la extensión: {e}")
