import os
import json
import base64
import platform
import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSplitter, QListWidget, QListWidgetItem,
    QTextEdit, QFileDialog, QMessageBox, QMenu, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QAction, QCursor, QGuiApplication

from .submodulos.sala_chat import SalaChatSubmodule
from .submodulos.conexion_lan import ConexionLanSubmodule
from .submodulos.stickers_emojis import StickersEmojisSubmodule
from .submodulos.historial_chats import HistorialChatsSubmodule
from .submodulos.asistente_ia import AsistenteIASubmodule
from .utils.chat_display import ChatDisplay
from .utils.chat_manager import ChatManager


class ChatInput(QTextEdit):
    """QTextEdit personalizado para enviar mensaje con Enter, y salto de línea con Shift+Enter"""
    send_pressed = pyqtSignal()

    def __init__(self, parent=None, colores=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.setPlaceholderText("Escribe un mensaje aquí...")
        self.setFont(QFont("Segoe UI", 10))
        self.setFixedHeight(38)
        self.textChanged.connect(self._adjust_height)
        self.init_style()

    def _adjust_height(self):
        lines = max(1, self.document().blockCount())
        fm = self.fontMetrics()
        calculated = (lines - 1) * fm.lineSpacing() + 38
        new_height = max(38, min(100, calculated))
        self.setFixedHeight(new_height)

    def init_style(self):
        self.setStyleSheet("""
            QTextEdit {
                background-color: #2A3942;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 18px;
                padding: 8px 14px;
                color: #E9EDEF;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QTextEdit:focus {
                border: 1px solid #00A884;
            }
        """)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_pressed.emit()
        else:
            super().keyPressEvent(event)


class TabChat(QWidget):
    """
    Módulo Principal de Chat Local LAN & Stickers con QTabWidget y 4 Submódulos Desacoplados:
    1. Sala de Chat & Transmisión en Vivo
    2. Servidor Host & Conexión LAN (Diagnóstico IP)
    3. Creador/Galería de Stickers Personalizados & Emojis
    4. Historial & Registro de Sesiones
    """
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.usuario = getattr(context, "usuario", "Usuario")
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.ruta_chats = self.ruta_usuario / "chats"
        self.ruta_chats.mkdir(parents=True, exist_ok=True)

        app = getattr(context, "app", None)
        self.colores = getattr(app, "COLORES", {
            "bg_principal": "#1E1E1E", "bg_secundario": "#2D2D2D", "bg_terciario": "#3D3D3D",
            "fg_principal": "#E0E0E0", "fg_secundario": "#A0A0A0", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#4CAF50", "error": "#F44336"
        })

        self.manager = ChatManager(self.usuario)
        self.manager.configurar_callbacks(
            msg_cb=self.manejar_mensaje,
            status_cb=self.manejar_estado,
            users_cb=self.manejar_usuarios,
            ip_cb=self.manejar_ip,
            notify_cb=self.manejar_notificacion
        )

        self.viendo_historial = False
        self.historial_actual_path = None
        self.conexion_activa = False
        self.mensajes_sesion = []

        self.callbacks = {
            "enviar_mensaje": self.enviar_mensaje,
            "enviar_imagen": self.enviar_imagen_dialog,
            "enviar_archivo": self.enviar_archivo_dialog,
            "enviar_sticker": self.enviar_sticker_directo,
            "insertar_emoji": self.insertar_emoji_en_input,
            "iniciar_host": self.iniciar_host,
            "unirse_host": self.unirse_host,
            "desconectar": self.desconectar,
            "exportar_chat": self.exportar_chat,
            "cargar_chat": self.cargar_chat_seleccionado,
            "eliminar_chat": self.eliminar_chat_seleccionado,
            "actualizar_lista_historial": self.actualizar_lista_guardados,
            "abrir_stickers_tab": self._abrir_stickers_tab,
            "cambiar_tab": self.cambiar_tab,
            "mostrar_vista_vacia": self.mostrar_vista_vacia_sala,
            "mostrar_chat_activo": self.mostrar_chat_activo_sala
        }

        self.txt_input = ChatInput(colores=self.colores)
        self.txt_input.send_pressed.connect(self.enviar_mensaje)

        self.inicializar_ui()
        self.actualizar_lista_guardados()
        self.mostrar_vista_vacia_sala()

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # TabWidget Superior
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont(self.font_family, 9))
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['acento']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)

        # Submódulos dinámicos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        extra_kwargs = {
            "callbacks": self.callbacks,
            "manager": self.manager,
            "txt_input": self.txt_input,
            "chat_input_widget": self.txt_input
        }
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores, extra_kwargs)

        if self.tabs.count() == 0:
            # Fallback seguro
            self.tab_sala = SalaChatSubmodule(self, self.context, self.colores, self.callbacks, self.manager, self.txt_input)
            self.tab_lan = ConexionLanSubmodule(self, self.context, self.colores, self.callbacks, self.manager)
            self.tab_stickers = StickersEmojisSubmodule(self, self.context, self.colores, self.callbacks)
            self.tab_historial = HistorialChatsSubmodule(self, self.context, self.colores, self.callbacks, self.manager)
            self.tab_ai = AsistenteIASubmodule(self, self.context, self.colores)

            self.tabs.addTab(self.tab_sala, "💬 Sala de Chat")
            self.tabs.addTab(self.tab_lan, "🌐 Servidor & Conexión LAN")
            self.tabs.addTab(self.tab_stickers, "🎨 Stickers & Emojis")
            self.tabs.addTab(self.tab_historial, "📜 Historial de Chats")
            self.tabs.addTab(self.tab_ai, "🤖 Asistente IA (Privado)")
        else:
            self.tab_sala = self.submod_instances.get("SalaChatSubmodule") or self.submod_instances.get("salachatsubmodule")
            self.tab_lan = self.submod_instances.get("ConexionLanSubmodule") or self.submod_instances.get("conexionlansubmodule")
            self.tab_stickers = self.submod_instances.get("StickersEmojisSubmodule") or self.submod_instances.get("stickersemojissubmodule")
            self.tab_historial = self.submod_instances.get("HistorialChatsSubmodule") or self.submod_instances.get("historialchatssubmodule")
            self.tab_ai = self.submod_instances.get("AsistenteIASubmodule") or self.submod_instances.get("asistenteiasubmodule")

        # Aliases Proxy para compatibilidad total con llamadas internas
        self.gui = self
        if self.tab_lan:
            self.txt_usuario = self.tab_lan.txt_usuario
            self.txt_ip = self.tab_lan.txt_ip
            self.txt_port = self.tab_lan.txt_port
            self.btn_host = self.tab_lan.btn_host
            self.btn_join = self.tab_lan.btn_join
            self.btn_disconnect = self.tab_lan.btn_disconnect
            self.list_online = self.tab_lan.list_online
        if self.tab_sala:
            self.lbl_estado = self.tab_sala.lbl_estado
            self.lbl_contacto = self.tab_sala.lbl_contacto
            self.display = self.tab_sala.display
            self.btn_send = self.tab_sala.btn_send
        if self.tab_historial:
            self.list_saved = self.tab_historial.list_saved

        self.main_layout.addWidget(self.tabs)

    def _abrir_stickers_tab(self):
        self.tabs.setCurrentIndex(0)
        self.tab_sala._toggle_drawer()

    def insertar_emoji_en_input(self, emoji):
        self.txt_input.insertPlainText(emoji)
        self.tabs.setCurrentIndex(0)
        self.txt_input.setFocus()

    def enviar_sticker_directo(self, path_sticker):
        if not self.conexion_activa:
            QMessageBox.warning(self, "Sin Conexión", "Debes crear un Host o unirte a uno antes de enviar stickers.")
            return
        try:
            with open(path_sticker, "rb") as f:
                raw_bytes = f.read()
            b64_data = base64.b64encode(raw_bytes).decode('utf-8')
            ext = Path(path_sticker).suffix.lstrip('.') or "png"
            self.manager.enviar_sticker(b64_data, ext)
            self.tabs.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo enviar el sticker: {e}")

    def cambiar_tab(self, index: int):
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def mostrar_vista_vacia_sala(self):
        if hasattr(self, 'tab_sala') and self.tab_sala and hasattr(self.tab_sala, 'mostrar_vista_vacia'):
            self.tab_sala.mostrar_vista_vacia()

    def mostrar_chat_activo_sala(self):
        if hasattr(self, 'tab_sala') and self.tab_sala and hasattr(self.tab_sala, 'mostrar_chat_activo'):
            self.tab_sala.mostrar_chat_activo()

    # --- CONTROL DE CONEXIÓN Y SERVIDOR ---
    def iniciar_host(self):
        usr = self.txt_usuario.text().strip()
        if not usr:
            QMessageBox.warning(self, "Usuario requerido", "Por favor ingresa un nombre de usuario.")
            return

        try: port = int(self.txt_port.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Puerto inválido", "El puerto debe ser un número entre 1024 y 65535.")
            return

        self.usuario = usr
        self.manager.usuario = usr
        if self.manager.iniciar_servidor(port):
            self.conexion_activa = True
            self.viendo_historial = False
            self.mensajes_sesion = []
            self.display.clear_chat()
            self.actualizar_ui_conexion()
            self.mostrar_chat_activo_sala()
            self.tabs.setCurrentIndex(0)

    def unirse_host(self):
        usr = self.txt_usuario.text().strip()
        ip = self.txt_ip.text().strip()
        if not usr or not ip:
            QMessageBox.warning(self, "Campos requeridos", "Ingresa usuario e IP del Host.")
            return

        try: port = int(self.txt_port.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Puerto inválido", "Ingresa un puerto válido.")
            return

        self.usuario = usr
        self.manager.usuario = usr
        if self.manager.conectar(ip, port):
            self.conexion_activa = True
            self.viendo_historial = False
            self.mensajes_sesion = []
            self.display.clear_chat()
            self.actualizar_ui_conexion()
            self.mostrar_chat_activo_sala()
            self.tabs.setCurrentIndex(0)

    def desconectar(self):
        if self.conexion_activa:
            if self.mensajes_sesion:
                self.guardar_historial(self.mensajes_sesion)
                self.actualizar_lista_guardados()

            self.manager.detener_sesion()
            self.conexion_activa = False
            self.lbl_estado.setText("SIN CONEXIÓN")
            self.lbl_estado.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#A0A0A0')};")
            self.actualizar_ui_conexion()
            self.mostrar_vista_vacia_sala()

    def actualizar_ui_conexion(self):
        activo = self.conexion_activa
        self.btn_host.setVisible(not activo)
        self.btn_join.setVisible(not activo)
        self.btn_disconnect.setVisible(activo)
        self.txt_usuario.setEnabled(not activo)
        self.txt_ip.setEnabled(not activo)
        self.txt_port.setEnabled(not activo)
        self.btn_send.setEnabled(activo)
        self.txt_input.setEnabled(activo)

    # --- CALLBACKS DESDE CHATMANAGER ---
    def manejar_mensaje(self, data):
        sender = data.get("usuario", "Anónimo")
        es_mio = (sender == self.usuario)
        timestamp = data.get("timestamp", datetime.datetime.now().strftime("%H:%M"))
        self.mensajes_sesion.append(data)

        msg_type = data.get("tipo", "texto")
        if msg_type == "texto":
            contenido = data.get("contenido", "")
            self.display.add_message(sender, contenido, timestamp, es_mio=es_mio)
        elif msg_type == "imagen":
            b64_data = data.get("data", "")
            ext = data.get("ext", "png")
            self.display.add_image_message(sender, b64_data, timestamp, es_mio=es_mio, ext=ext)
        elif msg_type == "archivo":
            nombre = data.get("nombre", "archivo")
            b64_data = data.get("data", "")
            self.display.add_file_message(sender, nombre, b64_data, timestamp, es_mio=es_mio)
        elif msg_type == "sticker":
            b64_data = data.get("data", "")
            ext = data.get("ext", "png")
            self.display.add_image_message(sender, b64_data, timestamp, es_mio=es_mio, ext=ext, es_sticker=True)
            if not es_mio:
                try:
                    raw_bytes = base64.b64decode(b64_data)
                    self.tab_stickers.guardar_sticker_externo(raw_bytes)
                except Exception: pass

    def manejar_estado(self, status_str):
        self.lbl_estado.setText(status_str.upper())
        if "HOST ACTIVO" in status_str.upper() or "CONECTADO" in status_str.upper():
            self.lbl_estado.setStyleSheet(f"color: {self.colores['exito']}; border: none;")
        else:
            self.lbl_estado.setStyleSheet(f"color: {self.colores.get('error', '#F44336')}; border: none;")

    def manejar_usuarios(self, lista_users):
        self.list_online.clear()
        for u in lista_users:
            self.list_online.addItem(f"🟢 {u}")

    def manejar_ip(self, ip, puerto):
        self.lbl_contacto.setText(f"📡 RED LAN: {ip}:{puerto}")

    def manejar_notificacion(self, notif_str):
        self.display.add_system_message(notif_str)

    # --- ENVIAR CONTENIDO ---
    def enviar_mensaje(self):
        text = self.txt_input.toPlainText().strip()
        if not text or not self.conexion_activa: return
        self.manager.enviar_texto(text)
        self.txt_input.clear()

    def enviar_imagen_dialog(self):
        if not self.conexion_activa: return
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Imagen", "", "Imágenes (*.png *.jpg *.jpeg *.gif *.webp)")
        if path:
            try:
                with open(path, "rb") as f: data = base64.b64encode(f.read()).decode('utf-8')
                ext = Path(path).suffix.lstrip('.')
                self.manager.enviar_imagen(data, ext)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo enviar la imagen: {e}")

    def enviar_archivo_dialog(self):
        if not self.conexion_activa: return
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo", "", "Todos los Archivos (*.*)")
        if path:
            try:
                with open(path, "rb") as f: data = base64.b64encode(f.read()).decode('utf-8')
                nombre = Path(path).name
                self.manager.enviar_archivo(data, nombre)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo enviar el archivo: {e}")

    # --- HISTORIAL DE CHATS (PERSISTENCIA LOCAL) ---
    def obtener_historiales_guardados(self):
        archivos = []
        if self.ruta_chats.exists():
            for f in sorted(self.ruta_chats.glob("*.json"), reverse=True):
                archivos.append({"nombre": f.stem, "path": str(f)})
        return archivos

    def cargar_historial(self, nombre):
        path = self.ruta_chats / f"{nombre}.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception: pass
        return None

    def guardar_historial(self, mensajes):
        if not mensajes: return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"chat_{ts}"
        path = self.ruta_chats / f"{nombre}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"nombre": nombre, "mensajes": mensajes}, f, indent=4)
        except Exception: pass

    def eliminar_historial(self, nombre):
        path = self.ruta_chats / f"{nombre}.json"
        if path.exists():
            try: path.unlink()
            except Exception: pass

    def actualizar_lista_guardados(self):
        self.list_saved.clear()
        archivos = self.obtener_historiales_guardados()
        for f in archivos:
            self.list_saved.addItem(f"📜 {f['nombre']}")

    def cargar_chat_seleccionado(self):
        item = self.list_saved.currentItem()
        if not item: return
        nombre = item.text().replace("📜 ", "").strip()
        datos = self.cargar_historial(nombre)
        if datos:
            self.viendo_historial = True
            self.display.clear_chat()
            self.lbl_contacto.setText(f"📜 HISTORIAL: {nombre}")
            for msg in datos.get("mensajes", []):
                self.manejar_mensaje(msg)
            self.mostrar_chat_activo_sala()
            self.tabs.setCurrentIndex(0)

    def eliminar_chat_seleccionado(self):
        item = self.list_saved.currentItem()
        if not item: return
        nombre = item.text().replace("📜 ", "").strip()
        if QMessageBox.question(self, "Eliminar Historial", f"¿Eliminar permanentemente '{nombre}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.eliminar_historial(nombre)
            self.actualizar_lista_guardados()

    def exportar_chat(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Chat", str(Path.home() / "chat_export.html"), "HTML Files (*.html);;Text Files (*.txt)")
        if not path: return
        try:
            content = self.display.get_html_content() if path.endswith(".html") else self.display.get_text_content()
            with open(path, "w", encoding="utf-8") as f: f.write(content)
            QMessageBox.information(self, "Éxito", f"Chat exportado a {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def actualizar_tema(self, colores: dict):
        """Actualiza la paleta de colores del módulo principal y propaga a todos los submódulos."""
        if not colores or not isinstance(colores, dict):
            return
        self.colores.update(colores)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: #0B141A;
            }}
            QTabBar::tab {{
                background: #202C33;
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: #00A884;
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)
        if hasattr(self, 'txt_input') and hasattr(self.txt_input, 'init_style'):
            self.txt_input.init_style()

        for submod in [
            getattr(self, "tab_sala", None),
            getattr(self, "tab_lan", None),
            getattr(self, "tab_stickers", None),
            getattr(self, "tab_historial", None),
            getattr(self, "tab_ai", None)
        ]:
            if submod and hasattr(submod, "actualizar_tema"):
                try:
                    submod.actualizar_tema(self.colores)
                except Exception:
                    pass

    def cleanup(self):
        """Libera sockets de conexión y recursos en segundo plano."""
        try:
            self.desconectar()
        except Exception:
            pass
        for submod in [
            getattr(self, "tab_sala", None),
            getattr(self, "tab_lan", None),
            getattr(self, "tab_stickers", None),
            getattr(self, "tab_historial", None),
            getattr(self, "tab_ai", None)
        ]:
            if submod and hasattr(submod, "cleanup"):
                try:
                    submod.cleanup()
                except Exception:
                    pass

