import datetime
import json
import logging
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox

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

def login(app):
    """Maneja el inicio de sesión"""
    usuario = app.login_username.text()
    password = app.login_password.text()
    
    if not usuario or not password:
        QMessageBox.critical(app, "Error", "Por favor complete todos los campos")
        return
    
    # 🔹 LOG INTENTO
    JsonLogger.log_global("INFO", f"Intento de login: {usuario}", modulo="Seguridad")

    # 1. Verificar bloqueo
    bloqueado, msg_bloqueo = AuthValidator.verificar_bloqueo(usuario, app.intentos_login)
    if bloqueado:
        JsonLogger.log_global("WARNING", f"Login bloqueado para: {usuario}", modulo="Seguridad")
        QMessageBox.warning(app, "Cuenta bloqueada", msg_bloqueo)
        return
    
    # 2. Validar credenciales
    exito, mensaje, config, persona = AuthValidator.validar_credenciales(usuario, password, app.intentos_login)
    
    if not exito:
        JsonLogger.log_global("ERROR", f"Login fallido para: {usuario} - {mensaje}", modulo="Seguridad")
        QMessageBox.critical(app, "Error", mensaje)
        return
    
    # 3. Login exitoso -> Actualizar config
    try:
        JsonLogger.log_global("INFO", f"Login exitoso: {usuario}", modulo="Seguridad")
        config["ultimo_acceso"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Si se marcó la casilla, habilitamos el acceso rápido
        config["login"] = app.login_remember.isChecked()
        
        ruta_usuario = get_user_path(persona)
        from .crypto_utils import process_config_for_save
        config_guardar = process_config_for_save(config)
        with open(ruta_usuario / "config.json", "w", encoding="utf-8") as f:
            json.dump(config_guardar, f, indent=4)
    except Exception as e:
        logging.error(f"Error al actualizar configuración de login: {e}")
    
    # 4. Cargar aplicación
    app.hide() # En PyQt6 ocultamos la ventana
    avatar_path = config.get("avatar", "")
    app.cargar_aplicacion(usuario, persona, avatar_path)

def register(app):
    """Maneja el registro de un nuevo usuario"""
    persona = app.register_persona.text()
    usuario = app.register_username.text()
    password = app.register_password.text()
    confirm = app.register_confirm.text()
    
    if not persona or not usuario or not password or not confirm:
        QMessageBox.critical(app, "Error", "Por favor complete todos los campos")
        return
    
    if password != confirm:
        QMessageBox.critical(app, "Error", "Las contraseñas no coinciden")
        return
    
    # Intentar crear usuario
    JsonLogger.log_global("INFO", f"Intentando registrar: {usuario}", modulo="Registro")
    avatar_img = getattr(app, 'avatar_image', None)
    avatar_shape = getattr(app, 'avatar_shape', 'circle')
    exito, mensaje = AuthCreator.crear_usuario(persona, usuario, password, avatar_img, avatar_shape)
    
    if exito:
        JsonLogger.log_global("INFO", f"Registro exitoso: {usuario}", modulo="Registro")
        QMessageBox.information(app, "Éxito", mensaje)
        
        # Limpiar y cambiar a login
        app.register_persona.clear()
        app.register_username.clear()
        app.register_password.clear()
        app.register_confirm.clear()
        
        # Limpiar avatar
        app.avatar_image = None
        if hasattr(app, 'avatar_preview'):
             app.avatar_preview.setText("?")
             app.avatar_preview.setPixmap(QMessageBox().iconPixmap()) # Placeholder o limpiar
            
        app.show_tab("login")
    else:
        JsonLogger.log_global("ERROR", f"Fallo al registrar: {usuario} - {mensaje}", modulo="Registro")
        QMessageBox.critical(app, "Error", mensaje)
