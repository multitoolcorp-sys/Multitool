"""
dialogs.py - Diálogos modales y ventanas auxiliares para el navegador integrado
"""

import json
import socket
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QCheckBox, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ...utils.webview2_widget import WebView2Widget


class BrowserPopupWindow(QDialog):
    """Ventana emergente nativa para autenticación OAuth (Google Sign-In, Discord, etc.) y popups web."""
    def __init__(self, parent_browser=None, width=520, height=650, user_data_folder=None, colores=None):
        super().__init__(parent_browser)
        self.parent_browser = parent_browser
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#FFFFFF", "acento": "#6366F1"
        }
        self.setWindowTitle("Iniciar sesión - MultiTool")
        self.resize(max(420, width), max(500, height))
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores.get('bg_principal', '#121218')};
                color: #FFFFFF;
            }}
        """)

        # Centrar sobre la ventana principal
        if parent_browser:
            try:
                parent_win = parent_browser.window()
                geo = parent_win.geometry()
                x = geo.x() + max(0, (geo.width() - self.width()) // 2)
                y = geo.y() + max(0, (geo.height() - self.height()) // 2)
                self.move(x, y)
            except Exception:
                pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.browser = WebView2Widget(self, "about:blank", user_data_folder)
        layout.addWidget(self.browser)

        if hasattr(self.browser, "windowCloseRequested"):
            self.browser.windowCloseRequested.connect(self._on_window_close)
        self.browser.titleChanged.connect(self._on_title_changed)
        if hasattr(self.browser, "newWindowRequested"):
            self.browser.newWindowRequested.connect(self._on_sub_popup_requested)

    def _on_sub_popup_requested(self, uri_str):
        if self.parent_browser and hasattr(self.parent_browser, "add_new_tab"):
            self.parent_browser.add_new_tab(QUrl(uri_str), "Enlace")

    def _on_title_changed(self, title):
        if title and title.strip():
            self.setWindowTitle(f"{title} - MultiTool")

    def _on_window_close(self):
        self.close()
        self.deleteLater()

    def closeEvent(self, event):
        try:
            if self.parent_browser and hasattr(self.parent_browser, "_active_popups"):
                if self in self.parent_browser._active_popups:
                    self.parent_browser._active_popups.remove(self)
        except Exception:
            pass
        try:
            if hasattr(self, "browser") and hasattr(self.browser, "dispose_browser"):
                self.browser.dispose_browser()
        except Exception:
            pass
        event.accept()


class DialogoProxy(QDialog):
    """Diálogo completo de configuración de servidores proxy para el navegador."""
    def __init__(self, parent, colores, ruta_usuario):
        super().__init__(parent)
        self.colores = colores
        self.ruta_usuario = Path(ruta_usuario)
        self.config_dir = self.ruta_usuario / "browser_data"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "proxy_config.json"
        
        self.setWindowTitle("🛡️ Configuración de Servidores Proxy")
        self.setFixedWidth(460)
        self.setStyleSheet(f"""
            QDialog {{ background: {self.colores['bg_principal']}; color: white; }}
            QLabel {{ color: {self.colores['fg_principal']}; font-family: 'Inter'; font-size: 9pt; }}
            QLineEdit, QComboBox {{
                background: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 6px 10px;
                font-family: 'Inter';
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {self.colores['acento']};
            }}
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: bold;
                font-family: 'Inter';
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)
        
        lbl_tit = QLabel("🛡️ Servidor Proxy del Navegador")
        lbl_tit.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']};")
        lay.addWidget(lbl_tit)
        
        lbl_desc = QLabel("Configura cómo se conecta el navegador a Internet. Los cambios se guardan y aplican a las sesiones de navegación.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #9CA3AF; font-size: 8.5pt;")
        lay.addWidget(lbl_desc)
        
        # Modo
        lay.addWidget(QLabel("<b>Modo de conexión:</b>"))
        self.cb_modo = QComboBox()
        self.cb_modo.addItems([
            "🟢 Sin Proxy (Conexión Directa a Internet)",
            "💻 Usar Configuración de Proxy de Windows",
            "🛡️ Configurar Servidor Proxy Manual"
        ])
        lay.addWidget(self.cb_modo)
        
        # Frame de detalles de Proxy manual
        self.frame_manual = QFrame()
        self.frame_manual.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 8px; padding: 10px;")
        m_lay = QVBoxLayout(self.frame_manual)
        m_lay.setSpacing(8)
        
        # Protocolo
        row_tipo = QHBoxLayout()
        row_tipo.addWidget(QLabel("Protocolo:"))
        self.cb_tipo = QComboBox()
        self.cb_tipo.addItems(["HTTP", "HTTPS", "SOCKS5"])
        row_tipo.addWidget(self.cb_tipo, 1)
        m_lay.addLayout(row_tipo)
        
        # Servidor y Puerto
        row_srv = QHBoxLayout()
        v_host = QVBoxLayout()
        v_host.addWidget(QLabel("Dirección del Servidor / Host:"))
        self.txt_host = QLineEdit()
        self.txt_host.setPlaceholderText("ej. 127.0.0.1 o proxy.ejemplo.com")
        v_host.addWidget(self.txt_host)
        row_srv.addLayout(v_host, 2)
        
        v_port = QVBoxLayout()
        v_port.addWidget(QLabel("Puerto:"))
        self.txt_puerto = QLineEdit()
        self.txt_puerto.setPlaceholderText("ej. 8080")
        v_port.addWidget(self.txt_puerto)
        row_srv.addLayout(v_port, 1)
        m_lay.addLayout(row_srv)
        
        # Bypass
        m_lay.addWidget(QLabel("Omitir proxy para (separados por punto y coma):"))
        self.txt_bypass = QLineEdit()
        self.txt_bypass.setPlaceholderText("ej. <local>;localhost;127.0.0.1")
        self.txt_bypass.setText("<local>;localhost;127.0.0.1")
        m_lay.addWidget(self.txt_bypass)
        
        lay.addWidget(self.frame_manual)
        
        # Botones
        btn_box = QHBoxLayout()
        self.btn_test = QPushButton("🔄 Probar Conexión")
        self.btn_test.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white;")
        self.btn_test.clicked.connect(self._probar_conexion)
        btn_box.addWidget(self.btn_test)
        
        btn_box.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white;")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        self.btn_guardar = QPushButton("💾 Guardar Proxy")
        self.btn_guardar.clicked.connect(self._guardar)
        btn_box.addWidget(self.btn_guardar)
        lay.addLayout(btn_box)
        
        self.cb_modo.currentIndexChanged.connect(self._actualizar_visibilidad_manual)
        self._cargar_configuracion()

    def _actualizar_visibilidad_manual(self, index):
        self.frame_manual.setVisible(index == 2)
        self.btn_test.setVisible(index == 2)
        self.adjustSize()

    def _cargar_configuracion(self):
        modo_idx = 0
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                modo = data.get("modo", "directo")
                if modo == "sistema":
                    modo_idx = 1
                elif modo == "manual":
                    modo_idx = 2
                
                self.cb_modo.setCurrentIndex(modo_idx)
                tipo = data.get("tipo", "http").upper()
                idx_tipo = self.cb_tipo.findText(tipo)
                if idx_tipo >= 0:
                    self.cb_tipo.setCurrentIndex(idx_tipo)
                
                self.txt_host.setText(data.get("host", ""))
                self.txt_puerto.setText(data.get("puerto", ""))
                self.txt_bypass.setText(data.get("bypass", "<local>;localhost;127.0.0.1"))
            except Exception:
                pass
        self._actualizar_visibilidad_manual(modo_idx)

    def _probar_conexion(self):
        if self.cb_modo.currentIndex() != 2:
            QMessageBox.information(self, "Prueba de Proxy", "El modo seleccionado no requiere servidor manual.")
            return

        host = self.txt_host.text().strip()
        puerto_str = self.txt_puerto.text().strip()
        if not host or not puerto_str:
            QMessageBox.warning(self, "Campos Incompletos", "Por favor ingresa el host y puerto del proxy.")
            return

        try:
            puerto = int(puerto_str)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3.0)
            res = s.connect_ex((host, puerto))
            s.close()
            if res == 0:
                QMessageBox.information(self, "Conexión Exitosa", f"🟢 Servidor proxy {host}:{puerto} alcanzable correctamente.")
            else:
                QMessageBox.warning(self, "Sin Respuesta", f"🔴 No se pudo conectar al puerto {puerto} en {host}. Código: {res}")
        except Exception as e:
            QMessageBox.critical(self, "Error de Conexión", f"Error al probar el servidor proxy: {e}")

    def _guardar(self):
        modo_str = "directo"
        if self.cb_modo.currentIndex() == 1:
            modo_str = "sistema"
        elif self.cb_modo.currentIndex() == 2:
            modo_str = "manual"

        data = {
            "modo": modo_str,
            "tipo": self.cb_tipo.currentText().lower(),
            "host": self.txt_host.text().strip(),
            "puerto": self.txt_puerto.text().strip(),
            "bypass": self.txt_bypass.text().strip()
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            QMessageBox.information(self, "Proxy Guardado", "✅ Configuración de Proxy guardada correctamente.\nSe aplicará a las nuevas pestañas y sesiones de navegación.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración: {e}")


class DialogoPermisos(QDialog):
    """Diálogo de administración de permisos de páginas web por pestaña/dominio."""
    def __init__(self, parent, colores, ruta_usuario):
        super().__init__(parent)
        self.parent_browser = parent
        self.colores = colores
        self.ruta_usuario = Path(ruta_usuario)
        self.config_dir = self.ruta_usuario / "browser_data"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "permisos_config.json"
        
        # Determinar el dominio u origen de la pestaña activa
        self.origen_actual = "https://www.google.com"
        try:
            if hasattr(self.parent_browser, "current_browser") and self.parent_browser.current_browser():
                b = self.parent_browser.current_browser()
                u_str = b.url().toString() if hasattr(b, "url") else ""
                import urllib.parse
                parsed = urllib.parse.urlparse(u_str)
                if parsed.scheme and parsed.netloc:
                    self.origen_actual = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass

        self.setWindowTitle("🔒 Permisos de Sitios Web")
        self.setFixedWidth(460)
        self.setStyleSheet(f"""
            QDialog {{ background: {self.colores['bg_principal']}; color: white; }}
            QLabel {{ color: {self.colores['fg_principal']}; font-family: 'Inter'; font-size: 9pt; }}
            QCheckBox {{
                color: white;
                font-family: 'Inter';
                font-size: 9.5pt;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(255,255,255,0.2);
                background: {self.colores['bg_secundario']};
            }}
            QCheckBox::indicator:checked {{
                background: {self.colores['acento']};
                border: 1px solid {self.colores['acento']};
            }}
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: bold;
                font-family: 'Inter';
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(14)
        
        lbl_tit = QLabel("🔒 Permisos de Sitios Web")
        lbl_tit.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']};")
        lay.addWidget(lbl_tit)
        
        # Etiqueta destacada del sitio actual
        self.lbl_origen = QLabel(f"🌐 Sitio Web Activo: {self.origen_actual}")
        self.lbl_origen.setStyleSheet(f"color: #FFFFFF; font-weight: bold; font-size: 10pt; background: {self.colores['bg_secundario']}; padding: 8px 12px; border-radius: 6px;")
        lay.addWidget(self.lbl_origen)

        lbl_desc = QLabel("Por defecto, ningún permiso se encuentra activo hasta que el sitio web lo solicite y tú lo autorices explícitamente:")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #9CA3AF; font-size: 8.5pt;")
        lay.addWidget(lbl_desc)
        
        frame_box = QFrame()
        frame_box.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 8px; padding: 12px;")
        fb_lay = QVBoxLayout(frame_box)
        fb_lay.setSpacing(10)
        
        self.chk_notif = QCheckBox("🔔 Notificaciones Web")
        fb_lay.addWidget(self.chk_notif)
        
        self.chk_geo = QCheckBox("📍 Geolocalización (Ubicación GPS)")
        fb_lay.addWidget(self.chk_geo)
        
        self.chk_mic = QCheckBox("🎤 Micrófono")
        fb_lay.addWidget(self.chk_mic)
        
        self.chk_cam = QCheckBox("📷 Cámara Web")
        fb_lay.addWidget(self.chk_cam)
        
        self.chk_clip = QCheckBox("📋 Acceso al Portapapeles")
        fb_lay.addWidget(self.chk_clip)
        
        lay.addWidget(frame_box)
        
        # Botones
        btn_box = QHBoxLayout()
        btn_reset = QPushButton("↺ Restablecer a 'Preguntar'")
        btn_reset.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: #E0E0E0;")
        btn_reset.clicked.connect(self._restablecer_sitio)
        btn_box.addWidget(btn_reset)
        
        btn_box.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white;")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        self.btn_guardar = QPushButton("💾 Guardar Permisos")
        self.btn_guardar.clicked.connect(self._guardar)
        btn_box.addWidget(self.btn_guardar)
        lay.addLayout(btn_box)
        
        self._cargar_configuracion()

    def _cargar_configuracion(self):
        # Por defecto NINGUNO está activo
        sitio_perms = {}
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sitio_perms = data.get("sitios", {}).get(self.origen_actual, {})
            except Exception:
                pass
                
        self.chk_notif.setChecked(sitio_perms.get("notificaciones", False))
        self.chk_geo.setChecked(sitio_perms.get("geolocalizacion", False))
        self.chk_mic.setChecked(sitio_perms.get("microfono", False))
        self.chk_cam.setChecked(sitio_perms.get("camara", False))
        self.chk_clip.setChecked(sitio_perms.get("portapapeles", False))

    def _restablecer_sitio(self):
        """Elimina las reglas guardadas para el sitio actual para que vuelva a preguntar."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "sitios" in data and self.origen_actual in data["sitios"]:
                    del data["sitios"][self.origen_actual]
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass
        self._cargar_configuracion()
        QMessageBox.information(self, "Permisos Restablecidos", f"✅ Los permisos para {self.origen_actual} se han restablecido al modo predeterminado (Preguntar al solicitar).")
        self.accept()

    def _guardar(self):
        data = {"sitios": {}, "predeterminados": {}}
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        if "sitios" not in data:
            data["sitios"] = {}

        data["sitios"][self.origen_actual] = {
            "notificaciones": self.chk_notif.isChecked(),
            "geolocalizacion": self.chk_geo.isChecked(),
            "microfono": self.chk_mic.isChecked(),
            "camara": self.chk_cam.isChecked(),
            "portapapeles": self.chk_clip.isChecked()
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            QMessageBox.information(self, "Permisos Guardados", f"✅ Preferencias de permisos para '{self.origen_actual}' actualizadas correctamente.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración: {e}")


class DialogoBorrarDatosNavegacion(QDialog):
    """Diálogo completo para borrar datos de navegación con casillas de selección e intervalo de tiempo."""
    def __init__(self, parent_browser, colores, ruta_usuario):
        super().__init__(parent_browser)
        self.parent_browser = parent_browser
        self.colores = colores
        self.ruta_usuario = Path(ruta_usuario)
        
        self.setWindowTitle("🧹 Borrar Datos de Navegación")
        self.setFixedWidth(460)
        self.setStyleSheet(f"""
            QDialog {{ background: {self.colores['bg_principal']}; color: white; }}
            QLabel {{ color: {self.colores['fg_principal']}; font-family: 'Inter'; font-size: 9pt; }}
            QComboBox {{
                background: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 6px 10px;
                font-family: 'Inter';
            }}
            QCheckBox {{
                color: white;
                font-family: 'Inter';
                font-size: 9.5pt;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(255,255,255,0.2);
                background: {self.colores['bg_secundario']};
            }}
            QCheckBox::indicator:checked {{
                background: {self.colores['acento']};
                border: 1px solid {self.colores['acento']};
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
                font-family: 'Inter';
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        lbl_tit = QLabel("🧹 Borrar Datos de Navegación")
        lbl_tit.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']};")
        lay.addWidget(lbl_tit)

        # Intervalo de tiempo
        lay_time = QHBoxLayout()
        lbl_time = QLabel("Intervalo de tiempo:")
        lbl_time.setStyleSheet("font-weight: bold;")
        lay_time.addWidget(lbl_time)

        self.cb_tiempo = QComboBox()
        self.cb_tiempo.addItems([
            "⏱️ Última hora",
            "⏱️ Últimas 24 horas",
            "⏱️ Últimos 7 días",
            "⏱️ Últimas 4 semanas",
            "⏱️ Desde el principio (Todo el tiempo)"
        ])
        self.cb_tiempo.setCurrentIndex(4) # Por defecto: Todo el tiempo
        lay_time.addWidget(self.cb_tiempo, 1)
        lay.addLayout(lay_time)

        # Caja de casillas
        frame_box = QFrame()
        frame_box.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 8px; padding: 12px;")
        fb_lay = QVBoxLayout(frame_box)
        fb_lay.setSpacing(10)

        self.chk_historial = QCheckBox("📜 Historial de navegación y búsquedas")
        self.chk_historial.setChecked(True)
        fb_lay.addWidget(self.chk_historial)

        self.chk_cookies = QCheckBox("🍪 Cookies y otros datos de sitios web")
        self.chk_cookies.setChecked(True)
        fb_lay.addWidget(self.chk_cookies)

        self.chk_cache = QCheckBox("📦 Archivos e imágenes en caché")
        self.chk_cache.setChecked(True)
        fb_lay.addWidget(self.chk_cache)

        self.chk_descargas = QCheckBox("⚡ Historial de descargas")
        self.chk_descargas.setChecked(True)
        fb_lay.addWidget(self.chk_descargas)

        self.chk_storage = QCheckBox("💾 Almacenamiento web (LocalStorage e IndexedDB)")
        self.chk_storage.setChecked(True)
        fb_lay.addWidget(self.chk_storage)

        self.chk_permisos = QCheckBox("🔒 Permisos de páginas web guardados")
        self.chk_permisos.setChecked(False)
        fb_lay.addWidget(self.chk_permisos)

        lay.addWidget(frame_box)

        # Botones inferiores
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white;")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_box.addStretch()

        self.btn_borrar = QPushButton("🗑️ Borrar Datos")
        self.btn_borrar.setStyleSheet("background: #EF4444; color: white;")
        self.btn_borrar.clicked.connect(self._ejecutar_borrado)
        btn_box.addWidget(self.btn_borrar)
        lay.addLayout(btn_box)

    def _ejecutar_borrado(self):
        try:
            import Microsoft.Web.WebView2.Core as CoreWV2
            
            # Construir máscara de flags de WebView2
            mask = CoreWV2.CoreWebView2BrowsingDataKinds(0)
            if self.chk_cookies.isChecked():
                mask |= CoreWV2.CoreWebView2BrowsingDataKinds.Cookies
            if self.chk_cache.isChecked():
                mask |= CoreWV2.CoreWebView2BrowsingDataKinds.DiskCache
                mask |= CoreWV2.CoreWebView2BrowsingDataKinds.CacheStorage
            if self.chk_descargas.isChecked():
                mask |= CoreWV2.CoreWebView2BrowsingDataKinds.DownloadHistory
            if self.chk_storage.isChecked():
                mask |= CoreWV2.CoreWebView2BrowsingDataKinds.AllDomStorage
                mask |= CoreWV2.CoreWebView2BrowsingDataKinds.LocalStorage
                mask |= CoreWV2.CoreWebView2BrowsingDataKinds.IndexedDb
                mask |= CoreWV2.CoreWebView2BrowsingDataKinds.ServiceWorkers
            if self.chk_historial.isChecked():
                mask |= CoreWV2.CoreWebView2BrowsingDataKinds.BrowsingHistory

            # Ejecutar en WebView2
            b = self.parent_browser.current_browser() if hasattr(self.parent_browser, "current_browser") else None
            if b and hasattr(b, "clear_browsing_data_async"):
                b.clear_browsing_data_async(mask)

            # Limpiar historial de MultiTool si se seleccionó
            if self.chk_historial.isChecked():
                hist_file = self.ruta_usuario / "browser_data" / "historial.json"
                if hist_file.exists():
                    try:
                        with open(hist_file, "w", encoding="utf-8") as f:
                            json.dump([], f)
                    except Exception:
                        pass
                if hasattr(self.parent_browser, "parent_module") and hasattr(self.parent_browser.parent_module, "nav_manager"):
                    self.parent_browser.parent_module.nav_manager.historial = []
                    if hasattr(self.parent_browser.parent_module, "actualizar_lista_historial"):
                        self.parent_browser.parent_module.actualizar_lista_historial()

            # Restablecer permisos si se seleccionó
            if self.chk_permisos.isChecked():
                perm_file = self.ruta_usuario / "browser_data" / "permisos_config.json"
                if perm_file.exists():
                    try:
                        with open(perm_file, "w", encoding="utf-8") as f:
                            json.dump({"sitios": {}, "predeterminados": {}}, f, indent=2)
                    except Exception:
                        pass

            try:
                from vistas.utils.notification import show_notification
                show_notification("MultiTool - Navegador", "✅ Los datos de navegación seleccionados han sido borrados con éxito.", "info")
            except Exception:
                QMessageBox.information(self, "Datos Borrados", "✅ Los datos de navegación seleccionados han sido borrados con éxito.")

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al Borrar Datos", f"No se pudieron borrar todos los datos: {e}")


class DialogoConfiguracionReposo(QDialog):
    """Diálogo modal para configurar el reposo automático de pestañas inactivas."""
    def __init__(self, parent=None, colores=None, sleep_enabled=True, sleep_timeout_minutes=5):
        super().__init__(parent)
        self.colores = colores or {
            "bg_principal": "#1E1E1E", "bg_secundario": "#2D2D2D", "bg_terciario": "#3D3D3D",
            "fg_principal": "#E0E0E0", "fg_secundario": "#A0A0A0", "acento": "#6366F1", "acento_hover": "#818CF8"
        }
        self.sleep_enabled = sleep_enabled
        self.sleep_timeout_minutes = sleep_timeout_minutes
        self.resultado_guardado = False

        self.setWindowTitle("💤 Modo Reposo de Pestañas")
        self.setFixedSize(480, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores['bg_principal']};
                color: {self.colores['fg_principal']};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QFrame#card {{
                background-color: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 16px;
            }}
            QCheckBox {{
                color: {self.colores['fg_principal']};
                font-size: 13px;
                font-weight: bold;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                background: {self.colores['bg_terciario']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colores['acento']};
                border-color: {self.colores['acento']};
            }}
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: #FFFFFF;
                selection-background-color: {self.colores['acento']};
            }}
            QPushButton#btn_save {{
                background-color: {self.colores['acento']};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton#btn_save:hover {{
                background-color: {self.colores['acento_hover']};
            }}
            QPushButton#btn_cancel {{
                background-color: transparent;
                color: {self.colores['fg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton#btn_cancel:hover {{
                background-color: rgba(255, 255, 255, 0.05);
                color: #FFFFFF;
            }}
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Encabezado
        lbl_titulo = QLabel("💤 Ahorro de Recursos y Reposo de Pestañas", self)
        lbl_titulo.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        layout.addWidget(lbl_titulo)

        lbl_desc = QLabel(
            "El modo reposo suspende automáticamente las pestañas inactivas en segundo plano, "
            "liberando memoria RAM y procesador. Al hacer clic sobre cualquier pestaña suspendida, "
            "se reactiva de inmediato con su contenido intacto.", self
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px; line-height: 1.4;")
        layout.addWidget(lbl_desc)

        # Tarjeta de opciones
        card = QFrame(self)
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        self.chk_enable = QCheckBox("Activar suspensión automática de pestañas", card)
        self.chk_enable.setChecked(self.sleep_enabled)
        card_layout.addWidget(self.chk_enable)

        row_time = QHBoxLayout()
        lbl_time = QLabel("Suspender pestañas tras inactividad:", card)
        lbl_time.setStyleSheet(f"color: {self.colores['fg_principal']}; font-size: 12px;")
        
        self.combo_timeout = QComboBox(card)
        tiempos = [
            ("1 minuto", 1),
            ("2 minutos", 2),
            ("5 minutos (Recomendado)", 5),
            ("10 minutos", 10),
            ("15 minutos", 15),
            ("30 minutos", 30),
            ("60 minutos (1 hora)", 60)
        ]
        for label, val in tiempos:
            self.combo_timeout.addItem(label, val)

        # Seleccionar valor actual
        idx_to_select = 2  # 5 minutos por defecto
        for idx, (_, val) in enumerate(tiempos):
            if val == self.sleep_timeout_minutes:
                idx_to_select = idx
                break
        self.combo_timeout.setCurrentIndex(idx_to_select)

        self.chk_enable.toggled.connect(self.combo_timeout.setEnabled)
        self.combo_timeout.setEnabled(self.sleep_enabled)

        row_time.addWidget(lbl_time)
        row_time.addWidget(self.combo_timeout)
        card_layout.addLayout(row_time)

        lbl_tip = QLabel("💡 Tip: También puedes suspender cualquier pestaña manualmente haciendo clic derecho sobre ella.", card)
        lbl_tip.setStyleSheet(f"color: {self.colores['acento_hover']}; font-size: 11px;")
        lbl_tip.setWordWrap(True)
        card_layout.addWidget(lbl_tip)

        layout.addWidget(card)
        layout.addStretch()

        # Botones inferiores
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancelar", self)
        btn_cancel.setObjectName("btn_cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Guardar Configuración", self)
        btn_save.setObjectName("btn_save")
        btn_save.clicked.connect(self._guardar)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _guardar(self):
        self.sleep_enabled = self.chk_enable.isChecked()
        self.sleep_timeout_minutes = int(self.combo_timeout.currentData() or 5)
        self.resultado_guardado = True
        self.accept()


class DialogoConfiguracionDescargas(QDialog):
    """Diálogo modal para configurar la carpeta predeterminada de descargas y la solicitud de ubicación."""
    def __init__(self, parent=None, config_file=None, colores=None):
        super().__init__(parent)
        self.config_file = Path(config_file) if config_file else None
        self.colores = colores or {
            "bg_principal": "#1E1E2E", "bg_secundario": "#252538",
            "fg_principal": "#FFFFFF", "fg_secundario": "#A0A0A0",
            "acento": "#6366F1", "acento_hover": "#818CF8"
        }
        self.auto_save = False
        self.download_dir = str(Path.home() / "Downloads")
        self.remember_last_dir = True
        self.last_download_dir = ""
        self._cargar_configuracion()
        self.init_ui()

    def _cargar_configuracion(self):
        if self.config_file and self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.auto_save = cfg.get("auto_save_downloads", False)
                    self.download_dir = cfg.get("download_dir", str(Path.home() / "Downloads"))
                    self.remember_last_dir = cfg.get("remember_last_dir", True)
                    self.last_download_dir = cfg.get("last_download_dir", "")
            except Exception:
                pass

    def init_ui(self):
        self.setWindowTitle("Configuración de Descargas")
        self.setFixedSize(520, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        bg_p = self.colores.get("bg_principal", "#1E1E2E")
        bg_s = self.colores.get("bg_secundario", "#252538")
        fg_p = self.colores.get("fg_principal", "#FFFFFF")
        acento = self.colores.get("acento", "#6366F1")
        acento_h = self.colores.get("acento_hover", "#818CF8")

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_p}; color: {fg_p}; font-family: 'Segoe UI', Arial, sans-serif; }}
            QFrame#card {{ background-color: {bg_s}; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px; }}
            QCheckBox {{ color: {fg_p}; font-size: 13px; spacing: 8px; }}
            QLineEdit {{ background-color: rgba(0, 0, 0, 0.25); color: {fg_p}; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 10px; font-size: 12px; }}
            QPushButton {{ background-color: rgba(255, 255, 255, 0.08); color: {fg_p}; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 14px; font-size: 12px; }}
            QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.16); }}
            QPushButton#btn_save {{ background-color: {acento}; border: none; color: #FFFFFF; font-weight: bold; }}
            QPushButton#btn_save:hover {{ background-color: {acento_h}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        lbl_tit = QLabel("📥 Configuración de Descargas", self)
        lbl_tit.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento};")
        layout.addWidget(lbl_tit)

        card = QFrame(self)
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        self.chk_ask = QCheckBox("Preguntar siempre dónde guardar cada archivo antes de descargar", card)
        self.chk_ask.setChecked(not self.auto_save)
        card_layout.addWidget(self.chk_ask)

        self.chk_remember_last = QCheckBox("Recordar y sugerir la última carpeta seleccionada al descargar", card)
        self.chk_remember_last.setChecked(self.remember_last_dir)
        card_layout.addWidget(self.chk_remember_last)

        lbl_dir = QLabel("Carpeta predeterminada de descarga:", card)
        lbl_dir.setStyleSheet("font-size: 12px; font-weight: bold; margin-top: 4px;")
        card_layout.addWidget(lbl_dir)

        row_dir = QHBoxLayout()
        self.txt_dir = QLineEdit(self.download_dir, card)
        btn_browse = QPushButton("📁 Examinar...", card)
        btn_browse.clicked.connect(self._examinar_carpeta)
        btn_reset = QPushButton("🔄", card)
        btn_reset.setToolTip("Restablecer a Descargas del sistema")
        btn_reset.clicked.connect(lambda: self.txt_dir.setText(str(Path.home() / "Downloads")))

        row_dir.addWidget(self.txt_dir, 1)
        row_dir.addWidget(btn_browse)
        row_dir.addWidget(btn_reset)
        card_layout.addLayout(row_dir)

        layout.addWidget(card)
        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_cancel = QPushButton("Cancelar", self)
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar Preferencias", self)
        btn_save.setObjectName("btn_save")
        btn_save.clicked.connect(self._guardar)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def _examinar_carpeta(self):
        from PyQt6.QtWidgets import QFileDialog
        d = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Descargas", self.txt_dir.text())
        if d:
            self.txt_dir.setText(d)

    def _guardar(self):
        self.auto_save = not self.chk_ask.isChecked()
        self.download_dir = self.txt_dir.text().strip() or str(Path.home() / "Downloads")
        self.remember_last_dir = self.chk_remember_last.isChecked()
        if self.config_file:
            try:
                cfg = {}
                if self.config_file.exists():
                    try:
                        with open(self.config_file, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                    except Exception:
                        pass
                cfg["auto_save_downloads"] = self.auto_save
                cfg["download_dir"] = self.download_dir
                cfg["remember_last_dir"] = self.remember_last_dir
                if self.last_download_dir:
                    cfg["last_download_dir"] = self.last_download_dir
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            except Exception as e:
                print(f"[DialogoConfiguracionDescargas] Error guardando config: {e}")
        self.accept()


