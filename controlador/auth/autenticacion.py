import datetime
import json
import logging

from .validation import AuthValidator, AuthCreator
from ..utils.paths import get_user_path
from vistas.utils.logs import JsonLogger


# Funciones de inicialización de UI (migradas a AuthGUI PyQt6)
def init_login_tab(app):
    from .gui_auth import AuthGUI
    AuthGUI.init_login_tab(app)


def init_register_tab(app):
    from .gui_auth import AuthGUI
    AuthGUI.init_register_tab(app)


def autenticar_usuario(usuario: str, password: str, recordar: bool = False, intentos_login: dict | None = None):
    """
    Lógica pura de inicio de sesión desacoplada de la vista.
    Retorna (exito: bool, estado: str, mensaje: str, config: dict | None, persona: str | None)
    """
    if not usuario or not password:
        return False, "error", "Por favor complete todos los campos", None, None

    if intentos_login is None:
        intentos_login = AuthValidator.cargar_intentos_login()

    JsonLogger.log_global("INFO", f"Intento de login: {usuario}", modulo="Seguridad")

    bloqueado, msg_bloqueo = AuthValidator.verificar_bloqueo(usuario, intentos_login)
    if bloqueado:
        AuthValidator.guardar_intentos_login(intentos_login)
        JsonLogger.log_global("WARNING", f"Login bloqueado para: {usuario}", modulo="Seguridad")
        return False, "bloqueado", msg_bloqueo, None, None

    exito, mensaje, config, persona = AuthValidator.validar_credenciales(usuario, password, intentos_login)
    AuthValidator.guardar_intentos_login(intentos_login)

    if not exito:
        estado = "bloqueado" if "bloqueada" in mensaje.lower() else "error"
        JsonLogger.log_global("ERROR", f"Login fallido para: {usuario} - {mensaje}", modulo="Seguridad")
        return False, estado, mensaje, None, None

    try:
        JsonLogger.log_global("INFO", f"Login exitoso: {usuario}", modulo="Seguridad")
        config["ultimo_acceso"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config["login"] = bool(recordar)

        ruta_usuario = get_user_path(persona)
        from .crypto_utils import process_config_for_save
        config_guardar = process_config_for_save(config)
        with open(ruta_usuario / "config.json", "w", encoding="utf-8") as f:
            json.dump(config_guardar, f, indent=4)
    except Exception as e:
        logging.error(f"Error al actualizar configuración de login: {e}")

    return True, "ok", mensaje, config, persona


def registrar_usuario(persona: str, usuario: str, password: str, confirm: str, avatar_img=None, avatar_shape: str = "circle"):
    """Lógica pura de registro desacoplada de la vista. Retorna (exito: bool, mensaje: str)."""
    if not persona or not usuario or not password or not confirm:
        return False, "Por favor complete todos los campos"

    if password != confirm:
        return False, "Las contraseñas no coinciden"

    JsonLogger.log_global("INFO", f"Intentando registrar: {usuario}", modulo="Registro")
    exito, mensaje = AuthCreator.crear_usuario(persona, usuario, password, avatar_img, avatar_shape)

    if exito:
        JsonLogger.log_global("INFO", f"Registro exitoso: {usuario}", modulo="Registro")
    else:
        JsonLogger.log_global("ERROR", f"Fallo al registrar: {usuario} - {mensaje}", modulo="Registro")
    return exito, mensaje


def login(app):
    """Adaptador de vista PyQt6 para el inicio de sesión."""
    from PyQt6.QtWidgets import QMessageBox

    if not getattr(app, "intentos_login", None):
        app.intentos_login = AuthValidator.cargar_intentos_login()

    usuario = app.login_username.text()
    password = app.login_password.text()
    recordar = app.login_remember.isChecked()

    exito, estado, mensaje, config, persona = autenticar_usuario(
        usuario, password, recordar=recordar, intentos_login=app.intentos_login
    )
    if not exito:
        if estado == "bloqueado":
            QMessageBox.warning(app, "Cuenta bloqueada", mensaje)
        else:
            QMessageBox.critical(app, "Error", mensaje)
        return

    app.hide()
    avatar_path = config.get("avatar", "")
    app.cargar_aplicacion(usuario, persona, avatar_path)


def register(app):
    """Adaptador de vista PyQt6 para el registro de usuario."""
    from PyQt6.QtWidgets import QMessageBox

    persona = app.register_persona.text()
    usuario = app.register_username.text()
    password = app.register_password.text()
    confirm = app.register_confirm.text()
    avatar_img = getattr(app, 'avatar_image', None)
    avatar_shape = getattr(app, 'avatar_shape', 'circle')

    exito, mensaje = registrar_usuario(persona, usuario, password, confirm, avatar_img, avatar_shape)
    if exito:
        QMessageBox.information(app, "Éxito", mensaje)
        app.register_persona.clear()
        app.register_username.clear()
        app.register_password.clear()
        app.register_confirm.clear()
        app.avatar_image = None
        if hasattr(app, 'avatar_preview'):
            app.avatar_preview.setText("?")
            app.avatar_preview.setPixmap(QMessageBox().iconPixmap())
        app.show_tab("login")
    else:
        QMessageBox.critical(app, "Error", mensaje)
