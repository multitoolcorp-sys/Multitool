import sys
import os
import json
import html
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QTextEdit, QTextBrowser, QLineEdit, QDialog, QGroupBox, 
    QCheckBox, QSlider, QMessageBox, QFrame, QSplitter
)
from PyQt6.QtGui import QFont, QDesktopServices

from ..utils.pii_sanitizer import PIISanitizer
from ..utils.ai_provider import AIConfigManager, check_ollama_models, AIWorkerThread
from ..utils.system_context import get_system_environmental_context
from ..utils.ai_dialog import (
    find_ollama_binary,
    format_ai_response_to_html,
    AIChatInputEdit,
    AIConfigDialog
)


class AsistenteIASubmodule(QWidget):
    """
    Submódulo de Chat IA Híbrido:
    - Ollama Local 100% Offline (Cero fuga externa).
    - Modelos de la Nube con LLaves Personales (BYOK).
    - Filtro Sanitizador PII de Datos Confidenciales en tiempo real.
    """
    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent)
        import datetime
        self.context = context
        self.colores = colores or {}
        
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", ".")) if context else Path.home() / ".multitool"
        self.ruta_ai_chats = self.ruta_usuario / "ai_chats"
        self.ruta_ai_chats.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.chat_history_messages = []

        self.config_mgr = AIConfigManager(self.ruta_usuario)
        self.sanitizer = PIISanitizer(enabled=self.config_mgr.config.get("pii_filter_enabled", True))
        
        self.worker_thread = None
        self.current_ai_message = ""

        self._init_ui()
        self._cargar_modelos_ollama()

    def _init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # --- BARRA SUPERIOR DE HERRAMIENTAS ---
        top_toolbar = QHBoxLayout()

        btn_new_chat = QPushButton("➕ Nuevo Chat")
        btn_new_chat.setToolTip("Iniciar una nueva conversación limpia con la IA")
        btn_new_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_chat.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        btn_new_chat.clicked.connect(self._nuevo_chat)
        top_toolbar.addWidget(btn_new_chat)

        btn_history = QPushButton("📜 Historial")
        btn_history.setToolTip("Ver y cargar conversaciones guardadas de IA")
        btn_history.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_history.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#3D3D3D')}; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        btn_history.clicked.connect(self._mostrar_historial_chats)
        top_toolbar.addWidget(btn_history)

        top_toolbar.addWidget(QLabel("🤖"))

        self.combo_provider = QComboBox()
        self.combo_provider.addItems([
            "🦙 Ollama (100% Local Offline)",
            "⚡ Groq Cloud (Ultra Rápido)",
            "🤖 OpenAI (GPT-4o / GPT-3.5)",
            "🐋 DeepSeek (DeepSeek-Coder)",
            "💎 Google Gemini"
        ])
        self.combo_provider.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores.get('bg_terciario', '#3D3D3D')};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 4px 8px; font-size: 11px;
            }}
        """)
        self.combo_provider.currentIndexChanged.connect(self._on_provider_changed)
        top_toolbar.addWidget(self.combo_provider)

        self.combo_model = QComboBox()
        self.combo_model.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores.get('bg_terciario', '#3D3D3D')};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 4px 8px; font-size: 11px; min-width: 130px;
            }}
        """)
        top_toolbar.addWidget(self.combo_model)

        btn_refresh_ollama = QPushButton("↻")
        btn_refresh_ollama.setToolTip("Refrescar modelos de Ollama")
        btn_refresh_ollama.setFixedSize(26, 26)
        btn_refresh_ollama.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh_ollama.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#3D3D3D')}; color: white; border: none; border-radius: 13px;")
        btn_refresh_ollama.clicked.connect(self._cargar_modelos_ollama)
        top_toolbar.addWidget(btn_refresh_ollama)

        self.btn_install_ollama = QPushButton("⚡ Iniciar/Instalar Ollama")
        self.btn_install_ollama.setToolTip("Ejecutar el instalador de Ollama y configurar el modelo llama3 en CMD")
        self.btn_install_ollama.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install_ollama.setStyleSheet("background: #059669; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        self.btn_install_ollama.clicked.connect(self._instalar_iniciar_ollama)
        top_toolbar.addWidget(self.btn_install_ollama)

        # Botón Filtro PII
        self.btn_pii = QPushButton("🛡️ Filtro PII: ON")
        self.btn_pii.setToolTip("Sanear correos, IPs, rutas de archivos y claves antes de enviar a la nube")
        self.btn_pii.setCheckable(True)
        self.btn_pii.setChecked(self.sanitizer.enabled)
        self.btn_pii.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_pii_btn_style()
        self.btn_pii.clicked.connect(self._toggle_pii)
        top_toolbar.addWidget(self.btn_pii)

        # Botón Google OAuth (Gemini)
        self.btn_google_oauth = QPushButton("🔑 Google OAuth")
        self.btn_google_oauth.setToolTip("Cuenta de Google para Gemini (Clic para ver opciones o cambiar cuenta)")
        self.btn_google_oauth.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_google_oauth.setStyleSheet("background: #EA4335; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        self.btn_google_oauth.clicked.connect(self._on_btn_google_clicked)
        top_toolbar.addWidget(self.btn_google_oauth)

        btn_config = QPushButton("⚙️ Ajustes")
        btn_config.setToolTip("Configurar servidor Ollama y Claves API de la Nube")
        btn_config.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_config.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#3D3D3D')}; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        btn_config.clicked.connect(self._abrir_configuracion)
        top_toolbar.addWidget(btn_config)

        lay.addLayout(top_toolbar)
        self._check_google_oauth_status()

        # --- ÁREA DE MENSAJES Y CHAT ---
        self.txt_display = QTextBrowser()
        self.txt_display.setReadOnly(True)
        self.txt_display.setOpenExternalLinks(True)
        self.txt_display.setFont(QFont("Segoe UI", 10))
        self.txt_display.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {self.colores.get('bg_secundario', '#2D2D2D')};
                color: {self.colores.get('fg_principal', '#E0E0E0')};
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 10px; padding: 12px;
            }}
        """)
        self.txt_display.installEventFilter(self)
        lay.addWidget(self.txt_display, 1)

        # Mensaje de bienvenida inicial
        self._append_system_message(
            "👋 <b>¡Bienvenido al Asistente de IA Privado de MultiTool!</b><br>"
            "🔒 <i>Tus conversaciones en modo <b>Ollama Local</b> son 100% privadas y nunca salen de tu equipo. "
            "Para llamadas a la nube, el filtro <b>🛡️ PII</b> redacta automáticamente correos, IPs y claves sensibles.<br>"
            "💡 <b>Consejo:</b> Puedes escribir <code>@</code> para referenciar archivos o arrastrar archivos/carpetas directamente a la caja de texto.</i>"
        )

        # --- BARRA INFERIOR DE CONTROLES E INPUT ---
        bot_lay = QVBoxLayout()

        prompt_preset_lay = QHBoxLayout()
        prompt_preset_lay.addWidget(QLabel("🎯 Rol:"))
        
        self.combo_sys_prompt = QComboBox()
        self.combo_sys_prompt.addItems([
            "🤖 General y Versátil",
            "💻 Programación Python / C++",
            "📝 Redacción y Resúmenes",
            "🌐 Traductor Multilingüe",
            "🔍 Análisis y Seguridad"
        ])
        self.combo_sys_prompt.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores.get('bg_terciario', '#3D3D3D')};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 2px 8px; font-size: 10px;
            }}
        """)
        prompt_preset_lay.addWidget(self.combo_sys_prompt, 1)

        self.btn_env_context = QPushButton("🌍 Entorno: ON")
        self.btn_env_context.setToolTip("Inyectar fecha, hora, ubicación y clima actual al asistente")
        self.btn_env_context.setCheckable(True)
        self.btn_env_context.setChecked(True)
        self.btn_env_context.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_env_context.setStyleSheet("background: #0284C7; color: white; border: none; padding: 3px 8px; border-radius: 6px; font-size: 10px; font-weight: bold;")
        self.btn_env_context.clicked.connect(self._toggle_env_context)
        prompt_preset_lay.addWidget(self.btn_env_context)

        self.combo_file_perms = QComboBox()
        self.combo_file_perms.addItems([
            "🔒 Archivos: Desactivado",
            "👁️ Archivos: Solo Lectura",
            "✏️ Archivos: Lectura y Escritura"
        ])
        self.combo_file_perms.setToolTip("Permisos de acceso a archivos y carpetas locales para la IA")
        self.combo_file_perms.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores.get('bg_terciario', '#3D3D3D')};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 2px 8px; font-size: 10px;
            }}
        """)
        prompt_preset_lay.addWidget(self.combo_file_perms)

        self.btn_attach = QPushButton("📎 Adjuntar")
        self.btn_attach.setToolTip("Adjuntar un archivo de código/documento o una carpeta completa para analizar")
        self.btn_attach.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_attach.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; border: none; padding: 3px 8px; border-radius: 6px; font-size: 10px; font-weight: bold;")
        self.btn_attach.clicked.connect(self._adjuntar_archivo_o_carpeta)
        prompt_preset_lay.addWidget(self.btn_attach)

        bot_lay.addLayout(prompt_preset_lay)

        input_lay = QHBoxLayout()
        self.txt_input = AIChatInputEdit(self.ruta_usuario, self.colores, self)
        self.txt_input.setFixedHeight(55)
        self.txt_input.setPlaceholderText("Escribe tu consulta... Usa @ para referenciar archivos o arrastra archivos aquí (Ctrl+Enter para enviar)")
        self.txt_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colores.get('bg_principal', '#1E1E1E')};
                color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px; padding: 6px; font-family: 'Segoe UI';
            }}
            QTextEdit:focus {{ border: 1px solid {self.colores.get('acento', '#6366F1')}; }}
        """)
        self.txt_input.returnPressed.connect(self._enviar_prompt)
        input_lay.addWidget(self.txt_input, 1)

        self.btn_send = QPushButton("🚀 Enviar")
        self.btn_send.setFixedSize(80, 55)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')};
                color: white; font-weight: bold; border: none; border-radius: 8px;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        self.btn_send.clicked.connect(self._enviar_prompt)
        input_lay.addWidget(self.btn_send)

        self.btn_stop = QPushButton("🛑")
        self.btn_stop.setFixedSize(40, 55)
        self.btn_stop.setToolTip("Detener generación")
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#3D3D3D')}; color: white; border: none; border-radius: 8px;")
        self.btn_stop.clicked.connect(self._detener_generacion)
        input_lay.addWidget(self.btn_stop)

        bot_lay.addLayout(input_lay)
        lay.addLayout(bot_lay)

    def _update_pii_btn_style(self):
        if self.btn_pii.isChecked():
            self.btn_pii.setText("🛡️ Filtro PII: ON")
            self.btn_pii.setStyleSheet(f"background: #10B981; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        else:
            self.btn_pii.setText("⚠️ Filtro PII: OFF")
            self.btn_pii.setStyleSheet(f"background: #EF4444; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")

    def _toggle_pii(self):
        self.sanitizer.enabled = self.btn_pii.isChecked()
        self._update_pii_btn_style()
        self.config_mgr.save_config({"pii_filter_enabled": self.sanitizer.enabled})

    def _abrir_configuracion(self):
        diag = AIConfigDialog(self.config_mgr, self.colores, self)
        if diag.exec() == QDialog.DialogCode.Accepted:
            self._cargar_modelos_ollama()

    def _check_google_oauth_status(self):
        try:
            from vistas.modulos.navegador.utils.oauth_pkce import GoogleOAuthManager
            oauth_mgr = GoogleOAuthManager(self.ruta_usuario)
            sess = oauth_mgr.load_session()
            if sess and sess.get("user"):
                email = sess["user"].get("email", "Conectado")
                self.btn_google_oauth.setText(f"🟢 {email}")
                self.btn_google_oauth.setStyleSheet("background: #10B981; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
            else:
                self.btn_google_oauth.setText("🔑 Conectar Google OAuth")
                self.btn_google_oauth.setStyleSheet("background: #EA4335; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        except Exception:
            pass

    def _on_btn_google_clicked(self):
        try:
            from vistas.modulos.navegador.utils.oauth_pkce import GoogleOAuthManager
            oauth_mgr = GoogleOAuthManager(self.ruta_usuario)
            if oauth_mgr.is_logged_in():
                self._mostrar_menu_cuenta_google(oauth_mgr)
            else:
                self._iniciar_google_oauth()
        except Exception:
            self._iniciar_google_oauth()

    def _mostrar_menu_cuenta_google(self, oauth_mgr):
        from PyQt6.QtWidgets import QMenu, QWidgetAction, QFrame
        sess = oauth_mgr.load_session()
        user = sess.get("user", {})
        name = user.get("name", "Usuario Google")
        email = user.get("email", "Sin correo")

        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#2D2D2D')};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 6px;
            }}
        """)

        container = QWidget()
        container.setFixedWidth(280)
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(14, 14, 14, 14)
        c_lay.setSpacing(8)

        lbl_user = QLabel(f"<b>👤 {name}</b>")
        lbl_user.setStyleSheet("color: white; font-size: 13px; font-family: 'Segoe UI';")
        c_lay.addWidget(lbl_user)

        lbl_email = QLabel(email)
        lbl_email.setStyleSheet("color: #a0a0a0; font-size: 11px; font-family: 'Segoe UI';")
        c_lay.addWidget(lbl_email)

        lbl_badge = QLabel("🟢 Gemini AI Habilitado")
        lbl_badge.setStyleSheet("color: #10B981; font-weight: bold; font-size: 11px; margin-bottom: 4px;")
        c_lay.addWidget(lbl_badge)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.1);")
        c_lay.addWidget(sep)

        btn_change = QPushButton("🔄 Cambiar de Cuenta")
        btn_change.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#3D3D3D')}; color: white; border: none; padding: 7px 12px; border-radius: 6px; text-align: left; font-size: 11px;")
        btn_change.clicked.connect(lambda: (menu.close(), self._iniciar_google_oauth()))
        c_lay.addWidget(btn_change)

        btn_logout = QPushButton("🚪 Cerrar Sesión")
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.setStyleSheet("background: #EF4444; color: white; border: none; padding: 7px 12px; border-radius: 6px; text-align: left; font-weight: bold; font-size: 11px;")
        btn_logout.clicked.connect(lambda: (menu.close(), self._cerrar_google_oauth(oauth_mgr)))
        c_lay.addWidget(btn_logout)

        act = QWidgetAction(menu)
        act.setDefaultWidget(container)
        menu.addAction(act)

        def on_hide():
            try:
                container.setParent(self)
                container.hide()
            except Exception:
                pass
        menu.aboutToHide.connect(on_hide)

        pos = self.btn_google_oauth.mapToGlobal(self.btn_google_oauth.rect().bottomLeft())
        menu.exec(pos)

    def _cerrar_google_oauth(self, oauth_mgr):
        oauth_mgr.logout()
        self.btn_google_oauth.setText("🔑 Conectar Google OAuth")
        self.btn_google_oauth.setStyleSheet("background: #EA4335; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        self._append_system_message("ℹ️ <b>Sesión de Google cerrada.</b><br>Se requiere API Key manual o iniciar sesión de nuevo para usar Gemini.")

    def _iniciar_google_oauth(self):
        try:
            from vistas.modulos.navegador.utils.oauth_pkce import GoogleOAuthManager
            self.oauth_mgr = GoogleOAuthManager(self.ruta_usuario)
            self.oauth_mgr.login_success.connect(self._on_google_auth_success)
            self.oauth_mgr.login_error.connect(lambda err: QMessageBox.warning(self, "OAuth Error", f"Error de autenticación: {err}"))
            self.oauth_mgr.start_oauth_flow()
            QMessageBox.information(self, "OAuth en Proceso", "Se ha abierto el navegador para iniciar sesión con Google.\nAl completar la autorización en el navegador, Gemini se activará automáticamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error OAuth", f"No se pudo iniciar el flujo de autenticación: {e}")

    def _on_google_auth_success(self, data):
        user_info = data.get("user", data) if isinstance(data, dict) else {}
        email = user_info.get("email", "Conectado")
        self.btn_google_oauth.setText(f"🟢 {email}")
        self.btn_google_oauth.setStyleSheet("background: #10B981; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        self._append_system_message(f"✅ <b>Sesión de Google vinculada con éxito ({email}).</b><br>Gemini ya está listo para responder sin necesidad de API Key manual.")

    def _nuevo_chat(self):
        import datetime
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.chat_history_messages = []
        self.txt_display.clear()
        self._append_system_message(
            "✨ <b>Nueva Conversación Iniciada</b><br>"
            "Tus mensajes se guardan automáticamente en el historial local."
        )

    def _guardar_sesion_actual(self):
        if not self.chat_history_messages:
            return
        try:
            session_file = self.ruta_ai_chats / f"chat_{self.session_id}.json"
            data = {
                "session_id": self.session_id,
                "provider": self._get_current_provider_code(),
                "model": self.combo_model.currentText(),
                "timestamp": self.session_id,
                "messages": self.chat_history_messages
            }
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AI-HISTORY] Error guardando sesion: {e}")

    def _mostrar_historial_chats(self):
        from PyQt6.QtWidgets import QMenu
        chat_files = sorted(list(self.ruta_ai_chats.glob("chat_*.json")), reverse=True)
        if not chat_files:
            QMessageBox.information(self, "Historial AI", "No hay conversaciones previas guardadas aún.")
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#2D2D2D')};
                color: {self.colores.get('fg_principal', '#E0E0E0')};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
        """)

        for cf in chat_files[:20]:
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                msgs = cdata.get("messages", [])
                preview = "Chat sin mensajes"
                for m in msgs:
                    if m.get("role") == "user":
                        preview = m.get("content", "")[:35]
                        break
                ts = cdata.get("timestamp", cf.stem)
                action = menu.addAction(f"💬 {ts} - {preview}...")
                action.triggered.connect(lambda checked, path=cf: self._cargar_sesion_chat(path))
            except Exception:
                pass

        menu.addSeparator()
        act_clear = menu.addAction("🗑️ Borrar Todo el Historial")
        act_clear.triggered.connect(self._borrar_todo_historial)

        pos = self.mapToGlobal(self.rect().topLeft())
        menu.exec(pos)

    def _cargar_sesion_chat(self, chat_file: Path):
        try:
            with open(chat_file, "r", encoding="utf-8") as f:
                cdata = json.load(f)
            self.session_id = cdata.get("session_id", chat_file.stem.replace("chat_", ""))
            self.chat_history_messages = cdata.get("messages", [])
            self.txt_display.clear()
            self._append_system_message(f"📂 <i>Conversación cargada desde: {chat_file.name}</i>")
            
            for m in self.chat_history_messages:
                role = m.get("role")
                content = m.get("content", "")
                if role == "user":
                    self._append_user_message(content, save=False)
                elif role == "assistant":
                    self._append_ai_header(cdata.get("model", "Asistente"))
                    cursor = self.txt_display.textCursor()
                    cursor.movePosition(cursor.MoveOperation.End)
                    cursor.insertText(content)
                    cursor.insertHtml("<br><br>")
        except Exception as e:
            QMessageBox.warning(self, "Error al Cargar", f"No se pudo cargar la conversación: {e}")

    def _borrar_todo_historial(self):
        resp = QMessageBox.question(self, "Confirmar", "¿Deseas eliminar todo el historial de conversaciones de IA?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            for cf in self.ruta_ai_chats.glob("chat_*.json"):
                try:
                    cf.unlink()
                except Exception:
                    pass
            self._append_system_message("🗑️ <i>Historial de conversaciones eliminado.</i>")

    def _on_provider_changed(self, idx):
        self.combo_model.clear()
        prov_code = self._get_current_provider_code()
        
        if prov_code == "ollama":
            self._cargar_modelos_ollama()
        elif prov_code == "groq":
            self.combo_model.addItems(["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"])
        elif prov_code == "openai":
            self.combo_model.addItems(["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"])
        elif prov_code == "deepseek":
            self.combo_model.addItems(["deepseek-coder", "deepseek-chat"])
        elif prov_code == "gemini":
            self.combo_model.addItems(["gemini-1.5-flash", "gemini-1.5-pro"])

    def _get_current_provider_code(self) -> str:
        idx = self.combo_provider.currentIndex()
        codes = ["ollama", "groq", "openai", "deepseek", "gemini"]
        return codes[idx] if idx < len(codes) else "ollama"

    def _toggle_env_context(self):
        if self.btn_env_context.isChecked():
            self.btn_env_context.setText("🌍 Entorno: ON")
            self.btn_env_context.setStyleSheet("background: #0284C7; color: white; border: none; padding: 3px 8px; border-radius: 6px; font-size: 10px; font-weight: bold;")
            self._append_system_message("🌍 <i>Contexto ambiental activado (Hora, Fecha, Clima y Ubicación).</i>")
        else:
            self.btn_env_context.setText("🌍 Entorno: OFF")
            self.btn_env_context.setStyleSheet("background: #64748B; color: white; border: none; padding: 3px 8px; border-radius: 6px; font-size: 10px; font-weight: bold;")
            self._append_system_message("🌍 <i>Contexto ambiental desactivado.</i>")

    def _adjuntar_archivo_o_carpeta(self):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#2D2D2D')};
                color: white; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 4px;
            }}
            QMenu::item:selected {{ background-color: {self.colores.get('acento', '#6366F1')}; }}
        """)
        act_file = menu.addAction("📄 Adjuntar Archivo de Código o Documento")
        act_folder = menu.addAction("📁 Adjuntar Carpeta / Directorio Completo")

        act_file.triggered.connect(self._adjuntar_archivo_dialog)
        act_folder.triggered.connect(self._adjuntar_carpeta_dialog)

        pos = self.btn_attach.mapToGlobal(self.btn_attach.rect().bottomLeft())
        menu.exec(pos)

    def _adjuntar_archivo_dialog(self):
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo para referenciar a la IA", "",
            "Archivos Compatibles (*.txt *.py *.js *.html *.css *.json *.md *.csv *.cpp *.h *.log *.yaml *.xml);;Todos los archivos (*.*)"
        )
        if not filepath:
            return
        p = Path(filepath)
        cursor = self.txt_input.textCursor()
        cursor.insertText(f" @{p} ")
        self._append_system_message(f"📎 <i>Archivo referenciado: <b>{p.name}</b></i>")
        if self.combo_file_perms.currentIndex() == 0:
            self.combo_file_perms.setCurrentIndex(1)

    def _adjuntar_carpeta_dialog(self):
        from PyQt6.QtWidgets import QFileDialog
        dirpath = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta para referenciar a la IA")
        if not dirpath:
            return
        p = Path(dirpath)
        cursor = self.txt_input.textCursor()
        cursor.insertText(f" @{p} ")
        self._append_system_message(f"📁 <i>Carpeta referenciada: <b>{p.name}</b></i>")
        if self.combo_file_perms.currentIndex() == 0:
            self.combo_file_perms.setCurrentIndex(1)

    def _cargar_modelos_ollama(self):
        url = self.config_mgr.config.get("ollama_url", "http://127.0.0.1:11434")
        models = check_ollama_models(url)
        if models:
            self.btn_install_ollama.setText("🟢 Ollama Activo")
            self.btn_install_ollama.setEnabled(False)
            self.btn_install_ollama.setToolTip("El servidor de Ollama ya está activo y respondiendo en segundo plano")
            self.btn_install_ollama.setStyleSheet("background: #059669; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        else:
            self.btn_install_ollama.setText("⚡ Iniciar Ollama")
            self.btn_install_ollama.setEnabled(True)
            self.btn_install_ollama.setToolTip("Iniciar el servidor de Ollama en segundo plano")
            self.btn_install_ollama.setStyleSheet("background: #10B981; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")

        if self._get_current_provider_code() != "ollama":
            return
        self.combo_model.clear()
        if models:
            self.combo_model.addItems(models)
        else:
            self.combo_model.addItem("Ollama Desconectado / Sin modelos")

    def _get_system_prompt_text(self) -> str:
        idx = self.combo_sys_prompt.currentIndex()
        prompts = [
            "Eres un asistente de Inteligencia Artificial servicial, conciso y preciso.",
            "Eres un desarrollador experto en Python, C++, Qt y arquitectura de software. Proporciona código limpio e interactivo.",
            "Eres un asistente experto en redacción, síntesis y corrección de estilo.",
            "Eres un traductor técnico multilingüe que preserva la estructura y el formato original.",
            "Eres un especialista en ciberseguridad y análisis estático de código."
        ]
        base_prompt = prompts[idx] if idx < len(prompts) else prompts[0]

        # 1. Inyectar contexto ambiental si está activo
        if getattr(self, "btn_env_context", None) and self.btn_env_context.isChecked():
            base_prompt += get_system_environmental_context(True)

        # 2. Inyectar permisos de archivos
        perm_idx = self.combo_file_perms.currentIndex() if getattr(self, "combo_file_perms", None) else 0
        if perm_idx == 1:
            base_prompt += (
                "\n\n[PERMISOS_SISTEMA: MODO_SOLO_LECTURA_DE_ARCHIVOS_ACTIVO]\n"
                "El usuario te ha concedido permiso para inspeccionar y analizar archivos o carpetas del equipo.\n"
                "[/PERMISOS_SISTEMA]"
            )
        elif perm_idx == 2:
            base_prompt += (
                "\n\n[PERMISOS_SISTEMA: MODO_LECTURA_Y_ESCRITURA_DE_ARCHIVOS_ACTIVO]\n"
                "El usuario te ha concedido permiso para leer, crear y modificar archivos en el equipo.\n"
                "Para proponer la creación o edición de un archivo, incluye un bloque:\n"
                "[ESCRIBIR_ARCHIVO: ruta_del_archivo]\ncontenido del archivo\n[/ESCRIBIR_ARCHIVO]\n"
                "El sistema solicitará confirmación al usuario antes de escribir en disco.\n"
                "[/PERMISOS_SISTEMA]"
            )

        return base_prompt

    def _instalar_iniciar_ollama(self):
        import subprocess
        from PyQt6.QtCore import QTimer, QUrl
        from PyQt6.QtGui import QDesktopServices

        installer_path = Path(__file__).resolve().parent.parent / "utils" / "OllamaSetup.exe"
        ollama_bin = find_ollama_binary()

        if not ollama_bin:
            if installer_path.exists():
                self._append_system_message("🚀 <b>Ejecutando instalador local OllamaSetup.exe...</b>")
                try:
                    subprocess.Popen([str(installer_path)])
                except Exception as e:
                    QMessageBox.critical(self, "Error al Iniciar", f"No se pudo ejecutar OllamaSetup.exe: {e}")
                return
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Ollama no detectado")
            msg.setText("<b>El motor local de Inteligencia Artificial (Ollama) no está instalado.</b>")
            msg.setInformativeText("Para chat privado offline:\n1. Descarga e instala Ollama desde https://ollama.com/download\n2. Una vez instalado, presiona '⚡ Iniciar Ollama' nuevamente.")
            btn_dl = msg.addButton("🌐 Ir a Descargar Ollama", QMessageBox.ButtonRole.ActionRole)
            msg.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
            msg.exec()
            if msg.clickedButton() == btn_dl:
                QDesktopServices.openUrl(QUrl("https://ollama.com/download"))
            return

        self._append_system_message(
            "⚡ <b>Iniciando Ollama en segundo plano...</b><br>"
            "El servidor se está levantando de forma silenciosa sin abrir consolas emergentes."
        )

        try:
            bin_path = str(ollama_bin) if ollama_bin else "ollama"
            # 0x08000000 = CREATE_NO_WINDOW en Windows
            creation_flags = 0x08000000 if sys.platform == "win32" else 0
            self._ollama_proc = subprocess.Popen(
                [bin_path, "serve"],
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            QMessageBox.warning(self, "Error al Iniciar", f"No se pudo iniciar Ollama en segundo plano: {e}")

        # Monitorear disponibilidad de Ollama cada 2 segundos
        self._ollama_poll_timer = QTimer(self)
        self._ollama_poll_count = 0

        def check_ollama_ready():
            self._ollama_poll_count += 1
            models = check_ollama_models(self.config_mgr.config.get("ollama_url", "http://127.0.0.1:11434"))
            if models:
                self._ollama_poll_timer.stop()
                self._cargar_modelos_ollama()
                self._append_system_message(f"✅ <b>¡Ollama Local activo en segundo plano!</b><br>Modelos disponibles: {', '.join(models)}")
                self.combo_provider.setCurrentIndex(0)
            elif self._ollama_poll_count >= 25:
                self._ollama_poll_timer.stop()

        self._ollama_poll_timer.timeout.connect(check_ollama_ready)
        self._ollama_poll_timer.start(2000)

    def _append_loading_indicator(self, model_name: str):
        html_loading = f"""
        <div style='margin: 4px 0; color: #818CF8; font-size: 11px; background: rgba(99,102,241,0.08); padding: 6px 12px; border-radius: 6px; border-left: 3px solid #6366F1;'>
            🤖 <i>Asistente ({html.escape(model_name)}) generando respuesta... ⏳</i>
        </div>
        """
        self.txt_display.append(html_loading)

    def _append_ai_bubble(self, model_name: str, text: str, duration: float = 0.0):
        import datetime
        now_str = datetime.datetime.now().strftime("%I:%M %p")
        time_info = f"⚡ {duration:.1f}s | " if duration > 0 else ""
        formatted_content = format_ai_response_to_html(text)

        html_bubble = f"""
        <div style='margin-top: 4px; margin-bottom: 8px;'>
            <div style='background: {self.colores.get("bg_secundario", "#2D2D3D")}; border: 1px solid rgba(255,255,255,0.08); padding: 12px 16px; border-radius: 2px 14px 14px 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.2);'>
                <div style='margin-bottom: 6px; display: flex; justify-content: space-between;'>
                    <span style='color: #34D399; font-weight: bold; font-size: 11.5px;'>
                        🤖 Asistente ({html.escape(model_name)})
                    </span>
                    <span style='color: #94A3B8; font-size: 10px; margin-left: 12px;'>
                        {time_info}🕒 {now_str}
                    </span>
                </div>
                <div style='color: #F1F5F9; font-size: 12px; line-height: 1.5;'>
                    {formatted_content}
                </div>
            </div>
        </div>
        """
        self.txt_display.append(html_bubble)
        self.txt_display.ensureCursorVisible()

    def _enviar_prompt(self):
        import time
        prompt_text = self.txt_input.toPlainText().strip()
        if not prompt_text:
            return

        sanitized_prompt, redactions = self.sanitizer.sanitize(prompt_text)

        if redactions and sum(redactions.values()) > 0:
            red_summary = ", ".join([f"{k}: {v}" for k, v in redactions.items() if v > 0])
            self._append_system_message(f"🛡️ <i>Filtro PII Redactó: {red_summary} antes de enviar.</i>")

        self.txt_input.clear()
        # Registrar y renderizar el mensaje del usuario
        self._append_user_message(prompt_text)

        # Resolver menciones de archivos o carpetas con @
        import re
        mentions = re.findall(r'@(?:"([^"]+)"|([^\s\n]+))', prompt_text)
        attached_files_text = []

        for m_quoted, m_unquoted in mentions:
            file_path_str = (m_quoted or m_unquoted).strip()
            if not file_path_str:
                continue
            p = Path(file_path_str)
            if p.exists():
                try:
                    if p.is_file():
                        with open(p, "r", encoding="utf-8", errors="ignore") as f:
                            c = f.read(30000)
                        attached_files_text.append(f"[ARCHIVO_MENCIONADO: {p.name} (Ruta: {p})]\n{c}\n[/ARCHIVO_MENCIONADO]")
                        self._append_system_message(f"🔍 <i>Archivo leído bajo demanda: <b>{p.name}</b></i>")
                    elif p.is_dir():
                        tree_lines = [f"📁 {p.name}/"]
                        count = 0
                        for root, dirs, files in os.walk(p):
                            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "venv", ".venv", "node_modules", ".gemini")]
                            rel_root = os.path.relpath(root, p)
                            indent = "  " * (rel_root.count(os.sep) if rel_root != "." else 0)
                            if rel_root != ".":
                                tree_lines.append(f"{indent}📁 {os.path.basename(root)}/")
                            for f in files[:15]:
                                tree_lines.append(f"{indent}  📄 {f}")
                                count += 1
                            if count > 45:
                                tree_lines.append(f"{indent}  ... (más archivos)")
                                break
                        attached_files_text.append(f"[ESTRUCTURA_CARPETA: {p.name} (Ruta: {p})]\n" + "\n".join(tree_lines[:40]) + "\n[/ESTRUCTURA_CARPETA]")
                        self._append_system_message(f"📁 <i>Directorio leído bajo demanda: <b>{p.name}</b></i>")
                except Exception as e:
                    print(f"[AI-FILE] Error leyendo archivo referenciado: {e}")

        final_prompt_for_ai = sanitized_prompt
        if attached_files_text:
            final_prompt_for_ai += "\n\n" + "\n\n".join(attached_files_text)

        provider_code = self._get_current_provider_code()
        selected_model = self.combo_model.currentText()
        system_prompt = self._get_system_prompt_text()

        if provider_code == "ollama" and ("Desconectado" in selected_model or "Sin modelos" in selected_model or not selected_model):
            self._append_system_message(
                "⚠️ <b>Servidor Ollama no detectado en tu equipo.</b><br>"
                "• Presiona el botón verde <b>⚡ Iniciar/Instalar Ollama</b> arriba para configurar el entorno automáticamente.<br>"
                "• O bien, cambia de proveedor arriba a <b>⚡ Groq Cloud</b>, <b>🤖 OpenAI</b> o <b>💎 Gemini</b> e ingresa tu clave API en <b>⚙️ Ajustes</b>."
            )
            return

        # Iniciar Hilo Worker y cronómetro pasando ventana deslizante de los últimos 10 mensajes
        self._start_prompt_time = time.time()
        self.btn_send.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.current_ai_message = ""

        # Iniciar contenedor de streaming en tiempo real
        self._start_streaming_ai_bubble(selected_model)

        # Preparar snapshot optimizado (últimos 10 mensajes) para máxima velocidad de inferencia
        history_snapshot = list(self.chat_history_messages[-10:])

        self.worker_thread = AIWorkerThread(
            provider=provider_code,
            model=selected_model,
            prompt=final_prompt_for_ai,
            system_prompt=system_prompt,
            config=self.config_mgr.config,
            temperature=0.7,
            messages=history_snapshot
        )
        self.worker_thread.chunk_received.connect(self._on_ai_chunk)
        self.worker_thread.finished_response.connect(self._on_ai_finished)
        self.worker_thread.error_occurred.connect(self._on_ai_error)
        self.worker_thread.start()

    def _start_streaming_ai_bubble(self, model_name: str):
        import datetime
        now_str = datetime.datetime.now().strftime("%I:%M %p")
        header_html = f"""
        <div style='margin-top: 4px; margin-bottom: 8px;'>
            <div style='background: {self.colores.get("bg_secundario", "#2D2D3D")}; border: 1px solid rgba(255,255,255,0.08); padding: 12px 16px; border-radius: 2px 14px 14px 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.2);'>
                <div style='margin-bottom: 6px; display: flex; justify-content: space-between;'>
                    <span style='color: #34D399; font-weight: bold; font-size: 11.5px;'>
                        🤖 Asistente ({html.escape(model_name)})
                    </span>
                    <span style='color: #94A3B8; font-size: 10px; margin-left: 12px;'>
                        🕒 {now_str}
                    </span>
                </div>
                <div style='color: #F1F5F9; font-size: 12px; line-height: 1.5;'>
        """
        self.txt_display.append(header_html)
        self.txt_display.ensureCursorVisible()

    def _detener_generacion(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.requestInterruption()
            self.btn_stop.setEnabled(False)
            self.btn_send.setEnabled(True)
            self._append_system_message("🛑 <i>Generación de IA interrumpida por el usuario.</i>")

    def _on_ai_chunk(self, chunk_text: str):
        self.current_ai_message += chunk_text
        cursor = self.txt_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk_text)
        self.txt_display.ensureCursorVisible()

    def _on_ai_finished(self, full_text: str):
        import time
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        
        cursor = self.txt_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml("</div></div></div><br>")
        self.txt_display.ensureCursorVisible()

        duration = time.time() - getattr(self, "_start_prompt_time", time.time())
        res_text = full_text or self.current_ai_message
        if res_text:
            # 1. Guardar en JSON con duración
            self.chat_history_messages.append({"role": "assistant", "content": res_text, "duration": round(duration, 2)})
            self._guardar_sesion_actual()

            # 2. Si la respuesta contiene markdown rico (código, enlaces, encabezados), refrescar con el renderizador definitivo
            if "```" in res_text or "http" in res_text or "**" in res_text or "###" in res_text:
                self._recargar_conversacion_actual_ui()

            # 3. Procesar acciones de escritura de archivo con permiso y confirmación
            self._procesar_posible_escritura_archivo(res_text)

    def _recargar_conversacion_actual_ui(self):
        self.txt_display.clear()
        self._append_system_message(
            "👋 <b>¡Bienvenido al Asistente de IA Privado de MultiTool!</b><br>"
            "🔒 <i>Tus conversaciones en modo <b>Ollama Local</b> son 100% privadas y nunca salen de tu equipo. "
            "Para llamadas a la nube, el filtro <b>🛡️ PII</b> redacta automáticamente correos, IPs y claves sensibles.<br>"
            "💡 <b>Consejo:</b> Puedes escribir <code>@</code> para referenciar archivos o arrastrar archivos/carpetas directamente a la caja de texto.</i>"
        )
        selected_model = self.combo_model.currentText()
        for msg in self.chat_history_messages:
            if msg.get("role") == "user":
                self._append_user_message(msg.get("content", ""), save=False)
            elif msg.get("role") == "assistant":
                self._append_ai_bubble(selected_model, msg.get("content", ""), msg.get("duration", 0.0))

    def _procesar_posible_escritura_archivo(self, text: str):
        import re
        perm_idx = self.combo_file_perms.currentIndex() if getattr(self, "combo_file_perms", None) else 0
        if perm_idx != 2: # Solo si tiene permiso de Lectura y Escritura
            return

        pattern = r'\[ESCRIBIR_ARCHIVO:\s*(.*?)\]\n?(.*?)\[/ESCRIBIR_ARCHIVO\]'
        matches = re.findall(pattern, text, flags=re.DOTALL)
        for target_path_str, file_content in matches:
            target_path_str = target_path_str.strip()
            if not target_path_str:
                continue
            target_path = Path(target_path_str)
            resp = QMessageBox.question(
                self, "Confirmar Creación/Edición de Archivo",
                f"La IA solicita guardar/modificar el siguiente archivo:\n\n📁 {target_path}\n\n¿Deseas autorizar la escritura en disco?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.Yes:
                try:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(file_content)
                    self._append_system_message(f"✅ <b>Archivo guardado con éxito:</b> <code>{target_path}</code>")
                except Exception as e:
                    self._append_system_message(f"❌ <b>Error al escribir archivo:</b> {e}")

    def _on_ai_error(self, err_msg: str):
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._append_system_message(f"❌ <b>Error de IA:</b> {html.escape(err_msg)}")

    def _append_user_message(self, text: str, save: bool = True):
        import datetime
        now_str = datetime.datetime.now().strftime("%I:%M %p")
        if save:
            self.chat_history_messages.append({"role": "user", "content": text, "time": now_str})
            self._guardar_sesion_actual()
        escaped = html.escape(text).replace("\n", "<br>")
        html_bubble = f"""
        <div style='margin-top: 6px; margin-bottom: 6px; text-align: right;'>
            <div style='display: inline-block; text-align: left; max-width: 85%; background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%); color: white; padding: 8px 14px; border-radius: 14px 14px 2px 14px;'>
                <div style='font-weight: bold; font-size: 11px; margin-bottom: 2px; color: #E0E7FF;'>
                    👤 Tú <span style='font-weight: normal; font-size: 10px; color: rgba(255,255,255,0.7); margin-left: 6px;'>🕒 {now_str}</span>
                </div>
                <div style='font-size: 12px; line-height: 1.4;'>
                    {escaped}
                </div>
            </div>
        </div>
        """
        self.txt_display.append(html_bubble)
        self.txt_display.ensureCursorVisible()

    def _append_ai_header(self, model_name: str):
        html_hdr = f"""
        <div style='margin-top: 10px; margin-bottom: 4px;'>
            <span style='color: #10B981; font-weight: bold;'>🤖 Asistente ({html.escape(model_name)}):</span>
        </div>
        """
        self.txt_display.append(html_hdr)

    def _append_system_message(self, msg_html: str):
        html_sys = f"""
        <div style='margin: 8px 0; color: #a0a0a0; font-size: 0.85em; background: rgba(255,255,255,0.03); padding: 6px 10px; border-radius: 6px;'>
            {msg_html}
        </div>
        """
        self.txt_display.append(html_sys)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj == self.txt_display and event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if event.angleDelta().y() > 0:
                    self.txt_display.zoomIn(1)
                else:
                    self.txt_display.zoomOut(1)
                return True
        return super().eventFilter(obj, event)

