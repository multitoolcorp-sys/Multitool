import json
import io
import platform
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QScrollArea, QComboBox, QCheckBox, QMessageBox, QGridLayout,
    QFileDialog, QDialog, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QColor, QImage, QPainter, QPainterPath, QPen

from controlador.auth.validation import AuthValidator

try:
    from vistas.modulos.cuenta.utils.pin_lock_dialog import PinLockEventFilter, QuickPinLockDialog
    from vistas.modulos.cuenta.utils.custom_theme_dialog import PRESETS_TEMAS, CustomThemeDialog
    from vistas.modulos.cuenta.utils.editar_datos_dialog import EditarDatosDialog
    from vistas.modulos.cuenta.utils.account_backup_manager import generar_carnet_hd, exportar_respaldo_cuenta, importar_respaldo_cuenta
    from vistas.modulos.cuenta.utils.google_oauth_card import GoogleOAuthCardWidget
    from vistas.modulos.cuenta.utils.avatar_shape_dialog import abrir_dialogo_forma_avatar
    from vistas.modulos.cuenta.utils.plugin_installer_helper import instalar_complemento_dialog, reiniciar_app
    from vistas.modulos.cuenta.utils.autostart_helper import is_autostart_enabled, toggle_autostart, is_desktop_shortcut_present
except ImportError:
    from ..utils.pin_lock_dialog import PinLockEventFilter, QuickPinLockDialog
    from ..utils.custom_theme_dialog import PRESETS_TEMAS, CustomThemeDialog
    from ..utils.editar_datos_dialog import EditarDatosDialog
    from ..utils.account_backup_manager import generar_carnet_hd, exportar_respaldo_cuenta, importar_respaldo_cuenta
    from ..utils.google_oauth_card import GoogleOAuthCardWidget
    from ..utils.avatar_shape_dialog import abrir_dialogo_forma_avatar
    from ..utils.plugin_installer_helper import instalar_complemento_dialog, reiniciar_app
    from ..utils.autostart_helper import is_autostart_enabled, toggle_autostart, is_desktop_shortcut_present

# Utilidades de Avatar del sistema
try:
    from controlador.utils.avatar import AvatarGenerator, AvatarEditor
    from vistas.utils.selector_avatar import SelectorAvatar
    from vistas.utils.img_editor import ImageEditorDialog
except Exception:
    AvatarGenerator = None
    AvatarEditor = None
    SelectorAvatar = None
    ImageEditorDialog = None


class GuiUser(QWidget):
    """Interfaz de gestión de perfil de usuario evolucionada"""
    def __init__(self, parent, usuario, persona, ruta_usuario, colores, context=None):
        super().__init__(parent)
        self.usuario = usuario
        self.persona = persona
        self.ruta_usuario = Path(ruta_usuario)
        self.colores = colores
        self.context = context
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.inicializar_ui()
        try:
            from vistas.modulos.minigames.utils.score_manager import ScoreManager
            ScoreManager.registrar_listener(self.actualizar_puntos_ui)
        except Exception:
            pass
        self._timer_puntos = QTimer(self)
        self._timer_puntos.setInterval(1000)
        self._timer_puntos.timeout.connect(self.actualizar_puntos_ui)
        self._timer_puntos.start()

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {self.colores['bg_principal']}; }}")
        
        self.container = QWidget()
        self.container.setStyleSheet(f"background: {self.colores['bg_principal']};")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(25)
        
        config = self.cargar_config()
        
        # 1. SECCIÓN PERFIL DE USUARIO
        self.layout.addWidget(self._crear_seccion_perfil(config))
        
        # 2. SECCIÓN MULTITOOL ANALYTICS
        self.layout.addWidget(self._crear_seccion_analytics(config))
        
        # 3. SECCIÓN AJUSTES Y SEGURIDAD DE LA CUENTA
        self._crear_seccion_ajustes(config)
        
        # 4. SECCIÓN CUENTAS VINCULADAS (Google OAuth)
        self.layout.addWidget(self._crear_seccion_google())
        
        # 5. SECCIÓN PERSONALIZACIÓN Y PLUGINS
        self._crear_seccion_personalizacion(config)
        
        # 6. SECCIÓN REGISTROS
        self._crear_seccion_registros(config)
        
        self.layout.addStretch()
        self.scroll.setWidget(self.container)
        self.main_layout.addWidget(self.scroll)

    def _crear_seccion_perfil(self, config):
        card = QFrame()
        card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        
        lbl_title = QLabel("PERFIL DE USUARIO")
        lbl_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; ")
        card_layout.addWidget(lbl_title)
        
        header = QHBoxLayout()
        header.setContentsMargins(0, 15, 0, 10)
        header.setSpacing(25)
        
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(100, 100)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.avatar_label)
        
        info = QVBoxLayout()
        info.setSpacing(4)

        self.lbl_nick_title = QLabel(config.get("usuario", self.usuario))
        self.lbl_nick_title.setFont(QFont(self.font_family, 20, QFont.Weight.Bold))
        self.lbl_nick_title.setStyleSheet("color: white; border: none;")
        info.addWidget(self.lbl_nick_title)
        
        correo_str = config.get("correo", "") or "Sin correo configurado"
        self.lbl_email_perfil = QLabel(f"📧 Correo: {correo_str}")
        self.lbl_email_perfil.setFont(QFont(self.font_family, 10))
        self.lbl_email_perfil.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        info.addWidget(self.lbl_email_perfil)

        cumple_str = config.get("cumpleaños", "") or "No especificado"
        self.lbl_cumple_perfil = QLabel(f"🎂 Cumpleaños: {cumple_str}")
        self.lbl_cumple_perfil.setFont(QFont(self.font_family, 9))
        self.lbl_cumple_perfil.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        info.addWidget(self.lbl_cumple_perfil)
        
        lbl_reg = QLabel(f"📅 Registrado: {config.get('fecha_registro', 'N/A')}")
        lbl_reg.setFont(QFont(self.font_family, 9))
        lbl_reg.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        info.addWidget(lbl_reg)
        
        # Puntaje total de juegos
        total_puntos = self.obtener_total_puntos_juegos()
        self.lbl_puntos = QLabel(f"🎮 Puntaje Total Juegos: {total_puntos} pts")
        self.lbl_puntos.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_puntos.setStyleSheet(f"color: {self.colores['acento']}; border: none; margin-top: 4px;")
        info.addWidget(self.lbl_puntos)
        
        header.addLayout(info, 1)
        card_layout.addLayout(header)
        
        lay_btns = QHBoxLayout()
        lay_btns.setSpacing(10)

        btn_edit_data = QPushButton("✏️ Modificar Datos Personales")
        btn_edit_data.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit_data.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px; padding: 8px 16px; font-weight: bold; border: none;")
        btn_edit_data.clicked.connect(self._abrir_dialogo_editar_datos)
        lay_btns.addWidget(btn_edit_data)

        btn_badge = QPushButton("🪪 Carnet HD (.PNG)")
        btn_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_badge.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px 15px; font-weight: bold; border: 1px solid rgba(255,255,255,0.1);")
        btn_badge.clicked.connect(self._generar_carnet_hd)
        lay_btns.addWidget(btn_badge)

        btn_avatar = QPushButton("✨ Cambiar Avatar")
        btn_avatar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_avatar.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px 15px; border: none;")
        btn_avatar.clicked.connect(self.solicitar_cambio_avatar)
        lay_btns.addWidget(btn_avatar)
        
        btn_shape = QPushButton("📐 Cambiar Forma")
        btn_shape.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_shape.setStyleSheet(f"background: transparent; color: {self.colores['acento']}; border: none; font-size: 11px; text-decoration: underline;")
        btn_shape.clicked.connect(self.solicitar_cambio_forma)
        lay_btns.addWidget(btn_shape)
        lay_btns.addStretch()
        
        card_layout.addLayout(lay_btns)
        
        self.actualizar_avatar_ui(config)
        return card

    def _generar_carnet_hd(self):
        generar_carnet_hd(self, self.cargar_config(), self.usuario, self.colores, self.font_family)

    def _crear_seccion_analytics(self, config):
        card = QFrame()
        card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(14)

        lbl_title = QLabel("📊 MULTITOOL ANALYTICS & DIAGNÓSTICO DE USO")
        lbl_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores['acento']}; border: none;")
        card_layout.addWidget(lbl_title)

        grid = QGridLayout()
        grid.setSpacing(12)

        total_sesiones = config.get("total_sesiones", 1)
        minutos_activos = config.get("minutos_activos", 45)
        horas_act = round(minutos_activos / 60, 1)

        def _add_stat(r, c, title, val, color):
            b = QFrame()
            b.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 8px;")
            l = QVBoxLayout(b)
            l.setContentsMargins(14, 12, 14, 12)
            l.setSpacing(4)
            t = QLabel(title)
            t.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            t.setStyleSheet("color: white;")
            l.addWidget(t)
            v = QLabel(val)
            v.setFont(QFont(self.font_family, 14, QFont.Weight.Bold))
            v.setStyleSheet(f"color: {color};")
            l.addWidget(v)
            grid.addWidget(b, r, c)

        _add_stat(0, 0, "⏱️ Tiempo Activo", f"{horas_act} hrs", self.colores['acento'])
        _add_stat(0, 1, "📊 Inicios de Sesión", f"{total_sesiones} sesiones", "#34D399")

        has_pin = bool(config.get("pin_lock"))
        try:
            from controlador.auth.facial_auth import FacialAuthManager
            has_facial = FacialAuthManager.is_facial_enabled(self.ruta_usuario)
        except Exception:
            has_facial = False

        has_email = bool(config.get("correo"))
        has_shortcut = is_autostart_enabled() or is_desktop_shortcut_present()
        score = (25 if has_pin else 0) + (25 if has_facial else 0) + (25 if has_email else 0) + (25 if has_shortcut else 0)
        color_score = "#34D399" if score >= 75 else ("#FBBF24" if score >= 50 else "#F87171")
        badge_score = "🛡️ Excelente" if score == 100 else ("⚡ Bueno" if score >= 75 else "⚠️ Básico")
        _add_stat(0, 2, "🛡️ Puntaje de Seguridad", f"{score}% ({badge_score})", color_score)

        card_layout.addLayout(grid)
        return card

    def _exportar_respaldo_cuenta(self):
        exportar_respaldo_cuenta(self, self.cargar_config())

    def _importar_respaldo_cuenta(self):
        importar_respaldo_cuenta(self, self.ruta_usuario, on_success_callback=lambda data: self.cargar_config())

    def _configurar_pin_bloqueo(self):
        from PyQt6.QtWidgets import QInputDialog
        import hashlib
        pin, ok = QInputDialog.getText(self, "PIN de Bloqueo Rápido", "Introduce un PIN de 4 dígitos para proteger el acceso:")
        if ok and pin.strip():
            if len(pin.strip()) == 4 and pin.strip().isdigit():
                cfg = self.cargar_config()
                pin_text = pin.strip()
                cfg["pin_lock"] = hashlib.sha256(f"{pin_text}".encode('utf-8')).hexdigest()
                from controlador.auth.crypto_utils import process_config_for_save
                with open(self.ruta_usuario / "config.json", "w", encoding="utf-8") as f:
                    json.dump(process_config_for_save(cfg), f, indent=4)
                QMessageBox.information(self, "PIN Configurado", "¡PIN de bloqueo de 4 dígitos configurado exitosamente y cifrado con SHA-256!")

    def _bloquear_pantalla_ahora(self):
        cfg = self.cargar_config()
        pin = cfg.get("pin_lock")
        if pin:
            dlg = QuickPinLockDialog(pin, self.colores, self.window())
            dlg.exec()
        else:
            QMessageBox.information(self, "Bloqueo por PIN", "Configura un PIN primero antes de bloquear la pantalla.")

    def _abrir_dialogo_editar_datos(self):
        oauth = getattr(self, 'oauth_manager', None)
        dlg = EditarDatosDialog(
            parent=self,
            config=self.cargar_config(),
            colores=self.colores,
            font_family=self.font_family,
            ruta_usuario=self.ruta_usuario,
            usuario_actual=self.usuario,
            oauth_manager=oauth,
            on_google_connect=self._conectar_google
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_data = dlg.nuevos_datos
            if new_data:
                self.usuario = new_data["usuario"]
                if hasattr(self, "lbl_nick_title"):
                    self.lbl_nick_title.setText(self.usuario)
                if hasattr(self, "lbl_email_perfil"):
                    self.lbl_email_perfil.setText(f"📧 Correo: {new_data.get('correo') or 'Sin correo configurado'}")
                if hasattr(self, "lbl_cumple_perfil"):
                    self.lbl_cumple_perfil.setText(f"🎂 Cumpleaños: {new_data.get('cumpleaños') or 'No especificado'}")

    def _crear_seccion_ajustes(self, config):
        card = QFrame()
        card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(12)
        
        lbl_title = QLabel("AJUSTES Y SEGURIDAD DE LA CUENTA")
        lbl_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; ")
        card_layout.addWidget(lbl_title)

        # Nivel de Seguridad
        sec_lay = QHBoxLayout()
        lbl_sec = QLabel("Nivel de Seguridad de la Cuenta:")
        lbl_sec.setStyleSheet("color: white; border: none; font-weight: bold;")
        sec_lay.addWidget(lbl_sec)

        self.cb_sec_level = QComboBox()
        self.cb_sec_level.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_terciario']};
                color: white;
                padding: 8px 12px;
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.03);
            }}
            QComboBox QAbstractItemView {{
                background: {self.colores['bg_terciario']};
                color: white;
                selection-background-color: {self.colores['acento']};
            }}
        """)
        self.cb_sec_level.addItem("🟢 Fácil (Usuario/Contraseña, Auto-login permitido)", "facil")
        self.cb_sec_level.addItem("🟡 Normal (Usuario encriptado, sin Auto-login)", "normal")
        self.cb_sec_level.addItem("🔴 Avanzada (Todo encriptado, sin Auto-login)", "avanzado")

        nivel_actual = config.get("nivel_seguridad", "facil").lower()
        idx_sec = self.cb_sec_level.findData(nivel_actual)
        if idx_sec != -1:
            self.cb_sec_level.setCurrentIndex(idx_sec)

        sec_lay.addWidget(self.cb_sec_level, 1)
        card_layout.addLayout(sec_lay)
        
        # Checkbox Auto-login
        self.cb_login = QCheckBox("Habilitar Auto-login al iniciar MultiTool")
        self.cb_login.setChecked(config.get("login", False))
        self.cb_login.setStyleSheet("color: white; border: none;")
        
        def _on_sec_level_change():
            level = self.cb_sec_level.currentData()
            if level in ("normal", "avanzado"):
                self.cb_login.setChecked(False)
                self.cb_login.setEnabled(False)
                self.cb_login.setToolTip("El inicio de sesión automático está deshabilitado en niveles Normal y Avanzado.")
            else:
                self.cb_login.setEnabled(True)
                self.cb_login.setToolTip("")

        self.cb_sec_level.currentIndexChanged.connect(_on_sec_level_change)
        _on_sec_level_change()
        card_layout.addWidget(self.cb_login)

        # Iniciar con Windows
        shortcut_active = is_desktop_shortcut_present()
        autostart_active = is_autostart_enabled()
        is_checked = autostart_active or shortcut_active
        
        status_suffix = " (Acceso Directo Detectado)" if shortcut_active else (" (Activo)" if autostart_active else "")
        self.cb_autostart_secreto = QCheckBox(f"⚡ Iniciar MultiTool automáticamente con Windows{status_suffix}")
        self.cb_autostart_secreto.setChecked(is_checked)
        self.cb_autostart_secreto.setStyleSheet("color: #FBBF24; font-weight: bold; border: none; font-size: 11px;")
        
        def _on_autostart_toggled(checked):
            ok, msg = toggle_autostart(checked)
            if ok:
                QMessageBox.information(self, "⚡ Función Secreta", msg)
            else:
                QMessageBox.warning(self, "Advertencia", msg)
                self.cb_autostart_secreto.setChecked(not checked)

        self.cb_autostart_secreto.toggled.connect(_on_autostart_toggled)
        card_layout.addWidget(self.cb_autostart_secreto)

        # SECCIÓN RECONOCIMIENTO FACIAL
        try:
            from controlador.auth.facial_auth import FacialAuthManager, FacialRegisterDialog
            has_facial = FacialAuthManager.is_facial_enabled(self.ruta_usuario)
        except Exception:
            FacialAuthManager = None
            FacialRegisterDialog = None
            has_facial = False

        facial_lay = QHBoxLayout()
        facial_lay.setContentsMargins(0, 5, 0, 5)

        self.lbl_facial_info = QLabel("📷 Reconocimiento Facial: " + ("✅ Activo" if has_facial else "❌ Desactivado"))
        self.lbl_facial_info.setStyleSheet("color: white; font-weight: bold; border: none;")
        facial_lay.addWidget(self.lbl_facial_info)

        btn_facial = QPushButton("✨ Registrar Rostro" if not has_facial else "🔄 Recalibrar Rostro")
        btn_facial.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_facial.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px 14px; border: none;")
        
        def _configurar_facial():
            if not FacialRegisterDialog:
                QMessageBox.warning(self, "Aviso", "El módulo de reconocimiento facial no está disponible.")
                return
            dlg = FacialRegisterDialog(self.window(), self.ruta_usuario, self.colores)
            if dlg.exec():
                cfg = self.cargar_config()
                cfg["facial_enabled"] = True
                from controlador.auth.crypto_utils import process_config_for_save
                with open(self.ruta_usuario / "config.json", "w", encoding="utf-8") as f:
                    json.dump(process_config_for_save(cfg), f, indent=4)
                self.lbl_facial_info.setText("📷 Reconocimiento Facial: ✅ Activo")

        btn_facial.clicked.connect(_configurar_facial)
        facial_lay.addWidget(btn_facial)

        if has_facial and FacialAuthManager:
            btn_remove_facial = QPushButton("🗑️ Desactivar")
            btn_remove_facial.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_remove_facial.setStyleSheet(f"background: transparent; color: {self.colores['error']}; border: none; font-size: 11px;")
            def _desactivar_facial():
                FacialAuthManager.remove_face_template(self.ruta_usuario)
                cfg = self.cargar_config()
                cfg["facial_enabled"] = False
                from controlador.auth.crypto_utils import process_config_for_save
                with open(self.ruta_usuario / "config.json", "w", encoding="utf-8") as f:
                    json.dump(process_config_for_save(cfg), f, indent=4)
                self.lbl_facial_info.setText("📷 Reconocimiento Facial: ❌ Desactivado")
                btn_remove_facial.hide()
                btn_facial.setText("✨ Registrar Rostro")
            btn_remove_facial.clicked.connect(_desactivar_facial)
            facial_lay.addWidget(btn_remove_facial)

        card_layout.addLayout(facial_lay)

        # SECCIÓN DE SEGURIDAD POR PIN Y MODO DE BLOQUEO
        pin_box = QFrame()
        pin_box.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        pin_lay = QVBoxLayout(pin_box)
        pin_lay.setContentsMargins(14, 12, 14, 12)
        pin_lay.setSpacing(10)

        lbl_pin_tag = QLabel("🔒 SEGURO POR PIN Y RESPALDO DE CUENTA (.mtbackup)")
        lbl_pin_tag.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_pin_tag.setStyleSheet(f"color: {self.colores['acento']};")
        pin_lay.addWidget(lbl_pin_tag)

        # Modo de Bloqueo por PIN
        modo_lay = QHBoxLayout()
        lbl_modo = QLabel("Modo de Bloqueo por PIN:")
        lbl_modo.setStyleSheet("color: white; font-weight: bold;")
        modo_lay.addWidget(lbl_modo)

        self.cb_pin_modo = QComboBox()
        self.cb_pin_modo.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_secundario']};
                color: white;
                padding: 6px 10px;
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            QComboBox QAbstractItemView {{
                background: {self.colores['bg_secundario']};
                color: white;
                selection-background-color: {self.colores['acento']};
            }}
        """)
        self.cb_pin_modo.addItem("🟢 Bloqueo Normal (Solicitar PIN solo al desbloquear manualmente)", "normal")
        self.cb_pin_modo.addItem("🔒 Bloqueo Estricto (Solicitar PIN SIEMPRE al abrir la app)", "siempre")

        modo_actual = config.get("pin_modo", "normal")
        idx_modo = self.cb_pin_modo.findData(modo_actual)
        if idx_modo != -1:
            self.cb_pin_modo.setCurrentIndex(idx_modo)

        def _on_pin_modo_change():
            new_modo = self.cb_pin_modo.currentData()
            cfg = self.cargar_config()
            cfg["pin_modo"] = new_modo
            from controlador.auth.crypto_utils import process_config_for_save
            with open(self.ruta_usuario / "config.json", "w", encoding="utf-8") as f:
                json.dump(process_config_for_save(cfg), f, indent=4)

        self.cb_pin_modo.currentIndexChanged.connect(_on_pin_modo_change)
        modo_lay.addWidget(self.cb_pin_modo, 1)
        pin_lay.addLayout(modo_lay)

        # Botones de Acción
        lay_btns = QHBoxLayout()
        lay_btns.setSpacing(8)

        btn_pin = QPushButton("🔒 Configurar / Cambiar PIN")
        btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pin.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px; padding: 7px 12px; font-weight: bold; border: none;")
        btn_pin.clicked.connect(self._configurar_pin_bloqueo)
        lay_btns.addWidget(btn_pin)

        has_pin = bool(config.get("pin_lock"))
        if has_pin:
            btn_lock_now = QPushButton("🔒 Bloquear Pantalla Ahora")
            btn_lock_now.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_lock_now.setStyleSheet("background: #EF4444; color: white; border-radius: 6px; padding: 7px 12px; font-weight: bold; border: none;")
            btn_lock_now.clicked.connect(self._bloquear_pantalla_ahora)
            lay_btns.addWidget(btn_lock_now)

        btn_export = QPushButton("📦 Exportar Respaldo (.mtbackup)")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border-radius: 6px; padding: 7px 12px; font-weight: bold; border: 1px solid rgba(255,255,255,0.1);")
        btn_export.clicked.connect(self._exportar_respaldo_cuenta)
        lay_btns.addWidget(btn_export)

        btn_import = QPushButton("📥 Importar Respaldo")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border-radius: 6px; padding: 7px 12px; font-weight: bold; border: 1px solid rgba(255,255,255,0.1);")
        btn_import.clicked.connect(self._importar_respaldo_cuenta)
        lay_btns.addWidget(btn_import)

        pin_lay.addLayout(lay_btns)
        card_layout.addWidget(pin_box)

        btn_save = QPushButton("💾 GUARDAR AJUSTES")
        btn_save.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"background: {self.colores['acento']}; color: white; padding: 10px 20px; border-radius: 8px; border: none;")
        btn_save.clicked.connect(self.intentar_guardar)
        card_layout.addWidget(btn_save, 0, Qt.AlignmentFlag.AlignRight)
        
        self.layout.addWidget(card)

    def _crear_seccion_personalizacion(self, config):
        card = QFrame()
        card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(15)
        
        lbl_title = QLabel("PERSONALIZACIÓN Y PLUGINS")
        lbl_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; ")
        card_layout.addWidget(lbl_title)
        
        # Tema Dropdown
        theme_lay = QHBoxLayout()
        lbl_theme = QLabel("Tema Visual:")
        lbl_theme.setStyleSheet("color: white; border: none;")
        theme_lay.addWidget(lbl_theme)
        
        self.cb_theme = QComboBox()
        self.cb_theme.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_terciario']};
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {self.colores['bg_terciario']};
                color: white;
                selection-background-color: {self.colores['acento']};
            }}
        """)
        
        try:
            from vistas.estilos import obtener_todos_los_temas
            temas = obtener_todos_los_temas()
        except Exception:
            temas = {}
        
        for k, t in temas.items():
            self.cb_theme.addItem(t.get("nombre", k), k)
            
        self.cb_theme.addItem("🎨 Personalizado (Tus Colores)", "personalizado")

        # Seleccionar tema actual
        tema_actual = config.get("tema", "azul_oscuro")
        idx = self.cb_theme.findData(tema_actual)
        if idx != -1:
            self.cb_theme.setCurrentIndex(idx)
            
        theme_lay.addWidget(self.cb_theme, 1)

        # Botón para personalizar paleta
        btn_custom_colors = QPushButton("🎨 Colores...")
        btn_custom_colors.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_custom_colors.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px 12px; border: 1px solid rgba(255,255,255,0.05);")
        
        def _abrir_paleta_personalizada():
            colores_init = config.get("colores_personalizados", {})
            dlg = CustomThemeDialog(self.window(), colores_init, self.colores)
            if dlg.exec():
                self.colores_personalizados = dlg.colores_resultado
                idx_p = self.cb_theme.findData("personalizado")
                if idx_p != -1:
                    self.cb_theme.setCurrentIndex(idx_p)
                QMessageBox.information(self, "Paleta de Colores", "Paleta personalizada guardada. Haz clic en 'Guardar Cambios' para aplicarla.")

        btn_custom_colors.clicked.connect(_abrir_paleta_personalizada)
        theme_lay.addWidget(btn_custom_colors)

        card_layout.addLayout(theme_lay)

        # Botón para abrir el Rearrastre de Módulos (Gestor de Plugins)
        btn_manage = QPushButton("🧩 PERSONALIZAR MENÚ (PLUGINS)")
        btn_manage.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_manage.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_manage.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: white;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            QPushButton:hover {{
                border-color: {self.colores['acento']};
            }}
        """)
        btn_manage.clicked.connect(self._abrir_personalizar_menu)
        card_layout.addWidget(btn_manage)
        
        # Botón para instalar un complemento nuevo
        btn_install = QPushButton("📥 INSTALAR COMPLEMENTO (.ZIP / .MTP)")
        btn_install.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_install.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: white;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            QPushButton:hover {{
                border-color: {self.colores['acento']};
            }}
        """)
        btn_install.clicked.connect(self._instalar_complemento)
        card_layout.addWidget(btn_install)
        
        self.layout.addWidget(card)

    def _crear_seccion_google(self):
        """Crea la card de vinculación de cuenta Google OAuth 2.0."""
        self._google_card = GoogleOAuthCardWidget(
            ruta_usuario=self.ruta_usuario,
            colores=self.colores,
            font_family=self.font_family,
            parent=self
        )
        self.oauth_manager = self._google_card.oauth_manager
        return self._google_card

    def _conectar_google(self):
        if hasattr(self, "_google_card") and self._google_card:
            self._google_card.conectar_google()

    def _desconectar_google(self):
        if hasattr(self, "_google_card") and self._google_card:
            self._google_card.desconectar_google()

    def _crear_seccion_registros(self, config):
        card = QFrame()
        card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        
        lbl_title = QLabel("ACTIVIDAD RECIENTE")
        lbl_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; ")
        card_layout.addWidget(lbl_title)
        
        historial = config.get("historial", [])
        logs_text = "\n".join(historial[-8:][::-1])
        
        self.lbl_logs = QLabel(logs_text or "Sin actividad reciente.")
        self.lbl_logs.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: #888; padding: 15px; border-radius: 8px; font-family: monospace;")
        self.lbl_logs.setWordWrap(True)
        card_layout.addWidget(self.lbl_logs)
        
        self.layout.addWidget(card)

    def _abrir_personalizar_menu(self):
        from vistas.modulos.inicio.submodulos.plugins import TabPlugins
        manager = QDialog(self.window())
        manager.setWindowTitle("Personalizar Menú y Módulos")
        manager.setMinimumSize(850, 600)
        lay = QVBoxLayout(manager)
        lay.setContentsMargins(0, 0, 0, 0)
        tab_p = TabPlugins(manager, self.context, self.colores)
        lay.addWidget(tab_p)
        manager.exec()

    def _instalar_complemento(self):
        instalar_complemento_dialog(self)

    def _reiniciar_app(self):
        reiniciar_app()

    def intentar_guardar(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Confirmar Seguridad")
        dialog.setFixedSize(350, 180)
        dialog.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border-radius: 10px;")
        
        v_lay = QVBoxLayout(dialog)
        v_lay.setContentsMargins(20, 20, 20, 20)
        
        lbl = QLabel("Ingresa tu contraseña actual para guardar:")
        lbl.setFont(QFont(self.font_family, 10))
        lbl.setWordWrap(True)
        v_lay.addWidget(lbl)
        
        h_lay = QHBoxLayout()
        h_lay.setSpacing(0)
        pass_edit = QLineEdit()
        pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        pass_edit.setPlaceholderText("••••••••")
        pass_edit.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; padding: 10px; border-top-left-radius: 6px; border-bottom-left-radius: 6px; border: none;")
        h_lay.addWidget(pass_edit)
        
        btn_toggle = QPushButton("👁️")
        btn_toggle.setFixedSize(40, 36)
        btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_toggle.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-top-right-radius: 6px; border-bottom-right-radius: 6px; border: none;")
        def toggle():
            if pass_edit.echoMode() == QLineEdit.EchoMode.Password:
                pass_edit.setEchoMode(QLineEdit.EchoMode.Normal)
                btn_toggle.setText("🙈")
            else:
                pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
                btn_toggle.setText("👁️")
        btn_toggle.clicked.connect(toggle)
        h_lay.addWidget(btn_toggle)
        v_lay.addLayout(h_lay)
        
        btn_confirm = QPushButton("VERIFICAR Y GUARDAR")
        btn_confirm.setMinimumHeight(40)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet(f"background: {self.colores['acento']}; color: white; font-weight: bold; margin-top: 10px; border-radius: 6px;")
        v_lay.addWidget(btn_confirm)
        
        config = self.cargar_config()
        
        def validar():
            password = pass_edit.text()
            stored = config.get("password", "")
            if AuthValidator.verify_password(stored, password) or (stored and stored == password):
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "Error", "Contraseña incorrecta.")
        
        btn_confirm.clicked.connect(validar)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.aplicar_cambios(config)

    def aplicar_cambios(self, config):
        try:
            ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            historial = config.get("historial", [])
            
            nuevo_tema = self.cb_theme.currentData()
            tema_cambiado = config.get("tema", "azul_oscuro") != nuevo_tema

            nuevo_nivel = self.cb_sec_level.currentData()
            config["nivel_seguridad"] = nuevo_nivel

            config["login"] = self.cb_login.isChecked() if nuevo_nivel == "facil" else False
            config["tema"] = nuevo_tema
            
            if nuevo_tema == "personalizado" and hasattr(self, 'colores_personalizados'):
                config["colores_personalizados"] = self.colores_personalizados
                
            config.pop("fondo_imagen", None)
            
            if hasattr(self, 'nueva_img_avatar') and AvatarGenerator:
                path = AvatarGenerator.save_avatar_file(self.nueva_img_avatar, self.persona)
                config["avatar"] = str(path)
                config["avatar_shape"] = getattr(self, 'nuevo_avatar_shape', 'circle')
                delattr(self, 'nueva_img_avatar')

            historial.append(f"[{ahora}] Perfil actualizado.")
            config["historial"] = historial
            
            from controlador.auth.crypto_utils import process_config_for_save
            config_guardar = process_config_for_save(config)
            with open(self.ruta_usuario / "config.json", "w", encoding="utf-8") as f:
                json.dump(config_guardar, f, indent=4)

            self.usuario = config["usuario"]
            self.lbl_nick_title.setText(self.usuario)
            self.lbl_email_perfil.setText(f"📧 {config['correo'] or 'Sin correo'}")
            self.actualizar_avatar_ui(config)

            if hasattr(self, 'context') and self.context and self.context.app:
                try:
                    self.context.app.config = config
                    from vistas.estilos import obtener_colores_tema
                    colores_nuevos = obtener_colores_tema(nuevo_tema, config)
                    if hasattr(self.context.app, 'aplicar_fondo_e_estilo'):
                        self.context.app.aplicar_fondo_e_estilo(colores=colores_nuevos)
                    from vistas.utils.logs import JsonLogger
                    JsonLogger.log_global("INFO", f"Tema aplicado: {nuevo_tema}", modulo="Tema")
                except Exception as ex_t:
                    from vistas.utils.logs import JsonLogger
                    JsonLogger.log_global("ERROR", f"Fallo al aplicar tema visual {nuevo_tema}: {ex_t}", modulo="Tema")

            QMessageBox.information(self, "Perfil", "Datos guardados correctamente.")

            if tema_cambiado:
                confirm = QMessageBox.question(
                    self, "Reiniciar requerido",
                    "Has cambiado el tema visual de la aplicación. Para aplicar los cambios estéticos se requiere reiniciar.\n¿Deseas reiniciar ahora?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirm == QMessageBox.StandardButton.Yes:
                    self._reiniciar_app()
        except Exception as e:
            from vistas.utils.logs import JsonLogger
            JsonLogger.log_global("ERROR", f"Error al guardar configuración/tema de usuario: {e}", modulo="Tema")
            QMessageBox.critical(self, "Error", str(e))

    def cargar_config(self):
        try:
            path = self.ruta_usuario / "config.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    from controlador.auth.crypto_utils import process_config_for_load
                    return process_config_for_load(json.load(f))
        except Exception:
            pass
        return {}

    def actualizar_avatar_ui(self, config):
        path = config.get("avatar")
        shape = config.get("avatar_shape", "circle")
        
        if path and Path(path).exists():
            pix = QPixmap(path)
            if pix.isNull():
                self.avatar_label.setText("👤")
                self.avatar_label.setFont(QFont(self.font_family, 40))
                self.avatar_label.setStyleSheet("background: transparent; border: none;")
                return

            scaled_pix = pix.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)

            out_pix = QPixmap(100, 100)
            out_pix.fill(Qt.GlobalColor.transparent)

            painter = QPainter(out_pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            path_obj = QPainterPath()
            if shape == "circle":
                path_obj.addEllipse(0, 0, 100, 100)
            elif shape == "square":
                path_obj.addRect(0, 0, 100, 100)
            else:
                path_obj.addRoundedRect(0, 0, 100, 100, 18, 18)

            painter.setClipPath(path_obj)
            x_off = (100 - scaled_pix.width()) // 2
            y_off = (100 - scaled_pix.height()) // 2
            painter.drawPixmap(x_off, y_off, scaled_pix)

            pen = QPen(QColor(self.colores['acento']), 2)
            painter.setPen(pen)
            if shape == "circle":
                painter.drawEllipse(1, 1, 98, 98)
            elif shape == "square":
                painter.drawRect(1, 1, 98, 98)
            else:
                painter.drawRoundedRect(1, 1, 98, 98, 18, 18)
            painter.end()

            self.avatar_label.setPixmap(out_pix)
            self.avatar_label.setStyleSheet("background: transparent; border: none;")
            self.avatar_label.clearMask()
        else:
            self.avatar_label.setText("👤")
            self.avatar_label.setFont(QFont(self.font_family, 40))
            self.avatar_label.setStyleSheet("background: transparent; border: none;")

    def solicitar_cambio_avatar(self):
        if not SelectorAvatar:
            QMessageBox.warning(self, "Aviso", "El selector de avatar no está disponible.")
            return
        SelectorAvatar(self.window(), self._abrir_editor_pixel, self._seleccionar_del_escritorio, self.colores).show()

    def solicitar_cambio_forma(self):
        abrir_dialogo_forma_avatar(
            parent=self,
            config=self.cargar_config(),
            ruta_usuario=self.ruta_usuario,
            colores=self.colores,
            font_family=self.font_family,
            on_success_callback=self.actualizar_avatar_ui
        )

    def _abrir_editor_pixel(self):
        if AvatarEditor:
            AvatarEditor(self.window(), self.pre_guardar_avatar).show()

    def _seleccionar_del_escritorio(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar Imagen", "", "Imágenes (*.png *.jpg *.jpeg *.bmp)")
        if ruta and ImageEditorDialog:
            editor = ImageEditorDialog(self.window(), ruta, self.pre_guardar_avatar, self.colores)
            editor.exec()

    def pre_guardar_avatar(self, img, shape="circle"):
        self.nueva_img_avatar = img
        self.nuevo_avatar_shape = shape
        try:
            if not AvatarGenerator:
                return
            path = AvatarGenerator.save_avatar_file(img, self.persona)
            config = self.cargar_config()
            config["avatar"] = str(path)
            config["avatar_shape"] = shape
            
            from controlador.auth.crypto_utils import process_config_for_save
            with open(self.ruta_usuario / "config.json", "w", encoding="utf-8") as f:
                json.dump(process_config_for_save(config), f, indent=4)

            if hasattr(self, 'context') and self.context and getattr(self.context, 'app', None):
                self.context.app.config = config

            self.actualizar_avatar_ui(config)
            QMessageBox.information(self, "Avatar Actualizado", "¡Tu nuevo avatar ha sido guardado y aplicado correctamente!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la nueva imagen de avatar:\n{e}")

    def actualizar_puntos_ui(self, nuevo_total=None):
        if hasattr(self, "lbl_puntos") and self.lbl_puntos:
            tot = int(nuevo_total) if nuevo_total is not None and isinstance(nuevo_total, (int, float)) else self.obtener_total_puntos_juegos()
            txt = f"🎮 Puntaje Total Juegos: {tot} pts"
            if self.lbl_puntos.text() != txt:
                self.lbl_puntos.setText(txt)

    def obtener_total_puntos_juegos(self):
        try:
            from vistas.modulos.minigames.utils.score_manager import ScoreManager
            return ScoreManager(self.ruta_usuario).get_total_puntos()
        except Exception:
            pass
        try:
            path_scores = self.ruta_usuario / "extras_scores.json"
            if path_scores.exists():
                with open(path_scores, "r", encoding="utf-8") as f:
                    scores = json.load(f)
                tot = scores.get("puntos_totales")
                if tot is not None:
                    return int(tot)
                return sum(int(v) for k, v in scores.items() if (k.endswith("_puntos") or k.startswith("snake_highscore_")) and isinstance(v, (int, float)))
        except Exception:
            pass
        return 0

    def showEvent(self, event):
        super().showEvent(event)
        self.actualizar_puntos_ui()
