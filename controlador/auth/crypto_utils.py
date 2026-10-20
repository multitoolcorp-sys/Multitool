import base64
import hashlib
from cryptography.fernet import Fernet

SECRET_KEY_BASE = b"Multitool_Security_Salt_2026_Key"

def _get_fernet() -> Fernet:
    key_raw = hashlib.pbkdf2_hmac('sha256', SECRET_KEY_BASE, b"Multitool_User_Enc", 100000)
    fernet_key = base64.urlsafe_b64encode(key_raw)
    return Fernet(fernet_key)

def encrypt_str(val: str) -> str:
    """Encripta una cadena de texto y le antepone el prefijo ENC:"""
    if not isinstance(val, str) or not val:
        return val
    if val.startswith("ENC:"):
        return val
    try:
        f = _get_fernet()
        enc = f.encrypt(val.encode("utf-8")).decode("utf-8")
        return f"ENC:{enc}"
    except Exception:
        return val

def decrypt_str(val: str) -> str:
    """Desencripta una cadena de texto con prefijo ENC:"""
    if not isinstance(val, str) or not val.startswith("ENC:"):
        return val
    try:
        raw = val[4:]
        f = _get_fernet()
        return f.decrypt(raw.encode("utf-8")).decode("utf-8")
    except Exception:
        return val

def process_config_for_save(config: dict) -> dict:
    """
    Prepara la configuración para ser guardada en disco según nivel_seguridad:
    - 'facil' (por defecto): Usuario en texto plano, auto-login permitido.
    - 'normal': Auto-login deshabilitado (login=False), 'usuario' encriptado.
    - 'avanzado': Auto-login deshabilitado (login=False), 'usuario' y datos personales encriptados.
    """
    config_copy = dict(config)
    nivel = str(config_copy.get("nivel_seguridad", "facil")).lower().strip()
    config_copy["nivel_seguridad"] = nivel

    # 1. Desencriptar primero todos los valores para operar sobre datos limpios
    for k in list(config_copy.keys()):
        if isinstance(config_copy[k], str):
            config_copy[k] = decrypt_str(config_copy[k])
        elif isinstance(config_copy[k], list):
            config_copy[k] = [decrypt_str(x) if isinstance(x, str) else x for x in config_copy[k]]

    # 2. Aplicar reglas según el nivel
    if nivel in ("normal", "avanzado"):
        # Auto-login deshabilitado obligatoriamente en modo normal y avanzado
        config_copy["login"] = False
        # Encriptar nombre de usuario
        if "usuario" in config_copy and config_copy["usuario"]:
            config_copy["usuario"] = encrypt_str(config_copy["usuario"])

    if nivel == "avanzado":
        # Encriptar datos sensibles adicionales
        campos_sensibles = ["correo", "cumpleaños", "telefono"]
        for campo in campos_sensibles:
            if campo in config_copy and config_copy[campo]:
                config_copy[campo] = encrypt_str(config_copy[campo])

    return config_copy

def process_config_for_load(config: dict) -> dict:
    """
    Desencripta los datos encriptados de config.json para uso transparente en la app.
    """
    if not isinstance(config, dict):
        return config
    config_copy = dict(config)
    for k, val in list(config_copy.items()):
        if isinstance(val, str):
            config_copy[k] = decrypt_str(val)
        elif isinstance(val, list):
            config_copy[k] = [decrypt_str(x) if isinstance(x, str) else x for x in config_copy[k]]
    return config_copy
