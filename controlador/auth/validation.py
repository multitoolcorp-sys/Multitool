import os
import json
import hashlib
import time
import datetime
import shutil
from pathlib import Path
from ..utils.paths import get_cuentas_path, get_user_path
from .crypto_utils import process_config_for_load, process_config_for_save

# Constantes
MAX_INTENTOS_LOGIN = 3
TIEMPO_BLOQUEO = 300  # 5 minutos en segundos

class AuthValidator:
    """Clase encargada de las validaciones de autenticación"""
    
    @staticmethod
    def hash_password(password, salt=None):
        """Genera un hash seguro para la contraseña"""
        if salt is None:
            salt = os.urandom(32)
        
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        return salt.hex() + ':' + key.hex()
    
    @staticmethod
    def verify_password(stored_password, provided_password):
        """Verifica si la contraseña coincide con el hash almacenado"""
        try:
            salt_hex, key_hex = stored_password.split(':')
            salt = bytes.fromhex(salt_hex)
            new_hash = AuthValidator.hash_password(provided_password, salt)
            return new_hash == stored_password
        except ValueError:
            return False

    @staticmethod
    def verificar_bloqueo(usuario, intentos_login):
        """
        Verifica si un usuario está bloqueado.
        Retorna (bloqueado: bool, mensaje: str o None)
        """
        if usuario in intentos_login:
            intentos = intentos_login[usuario]
            
            if 'tiempo_bloqueo' in intentos:
                tiempo_restante = intentos['tiempo_bloqueo'] - time.time()
                if tiempo_restante > 0:
                    minutos = int(tiempo_restante // 60)
                    segundos = int(tiempo_restante % 60)
                    return True, f"Demasiados intentos fallidos. Cuenta bloqueada por {minutos}m {segundos}s."
                else:
                    intentos_login[usuario] = {'intentos': 0}
            
            if intentos.get('intentos', 0) >= MAX_INTENTOS_LOGIN:
                intentos_login[usuario]['tiempo_bloqueo'] = time.time() + TIEMPO_BLOQUEO
                return True, "Demasiados intentos fallidos. Cuenta bloqueada por 5 minutos."
                
        return False, None

    @staticmethod
    def validar_credenciales(usuario, password, intentos_login):
        """
        Valida las credenciales del usuario.
        Retorna (exito: bool, mensaje: str, config: dict o None, persona: str o None)
        """
        ruta_cuentas = get_cuentas_path()
        if not ruta_cuentas.exists():
            return False, "No hay cuentas registradas", None, None

        for carpeta_usuario in ruta_cuentas.iterdir():
            if not carpeta_usuario.is_dir():
                continue
                
            config_path = carpeta_usuario / "config.json"
            if not config_path.exists():
                continue
                
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = process_config_for_load(json.load(f))
                
                # Nick config: si no existe, usamos el nombre de la carpeta (retrocompatibilidad)
                nick_config = config.get("usuario", carpeta_usuario.name)
                
                if nick_config == usuario:
                    # Verificar bloqueo usando el nombre de la carpeta como ID único
                    bloqueado, msg = AuthValidator.verificar_bloqueo(carpeta_usuario.name, intentos_login)
                    if bloqueado:
                        return False, msg, None, None
                        
                    stored_password = config.get("password", "")
                    if ":" in stored_password:
                        password_correcta = AuthValidator.verify_password(stored_password, password)
                    else:
                        password_correcta = False # No permitir texto plano por seguridad

                    if not password_correcta:
                        AuthValidator._registrar_fallo(carpeta_usuario.name, intentos_login)
                        return False, "Contraseña incorrecta", None, None
                        
                    # Login exitoso
                    if carpeta_usuario.name in intentos_login:
                        intentos_login[carpeta_usuario.name] = {'intentos': 0}
                    
                    return True, "Login exitoso", config, carpeta_usuario.name
            except Exception:
                continue

        AuthValidator._registrar_fallo(usuario, intentos_login)
        return False, "Usuario no encontrado", None, None

    @staticmethod
    def _registrar_fallo(usuario, intentos_login):
        if usuario not in intentos_login:
            intentos_login[usuario] = {'intentos': 1}
        else:
            intentos_login[usuario]['intentos'] = intentos_login[usuario].get('intentos', 0) + 1


class AuthCreator:
    """Clase para la creación de usuarios"""
    
    @staticmethod
    def crear_usuario(persona, usuario, password, avatar_img=None, avatar_shape="circle"):
        """
        Crea un nuevo usuario. 
        persona: nombre de la carpeta
        usuario: nick de login
        """
        # Verificar que el usuario no esté duplicado en otras cuentas
        ruta_cuentas = get_cuentas_path()
        if ruta_cuentas.exists():
            for carpeta in ruta_cuentas.iterdir():
                if carpeta.is_dir():
                    cfg = carpeta / "config.json"
                    if cfg.exists():
                        try:
                            with open(cfg, "r", encoding="utf-8") as f:
                                data = process_config_for_load(json.load(f))
                            if data.get("usuario", "").strip().lower() == usuario.strip().lower():
                                return False, "El nombre de usuario ya está registrado por otra persona"
                        except Exception:
                            pass

        ruta_usuario = get_user_path(persona)
        
        if ruta_usuario.exists():
            return False, "Ya existe una persona con ese nombre o carpeta"
            
        try:
            # Crear directorios
            ruta_usuario.mkdir(parents=True, exist_ok=True)
            for carpeta in ["documentos", "notas", "descargas", "recordatorios"]:
                (ruta_usuario / carpeta).mkdir(exist_ok=True)
            
            # Copiar interfaces
            if Path("interfaces_predeterminadas").exists():
                shutil.copytree("interfaces_predeterminadas", ruta_usuario / "interfaces", dirs_exist_ok=True)
            else:
                (ruta_usuario / "interfaces").mkdir(exist_ok=True)
            
            # Gestionar Avatar
            from ..utils.avatar import AvatarGenerator
            
            if avatar_img:
                avatar_path = AvatarGenerator.save_avatar_file(avatar_img, persona)
            else:
                initial = usuario[0].upper() if usuario else "?"
                img = AvatarGenerator.generate_letter_avatar(initial)
                avatar_path = AvatarGenerator.save_avatar_file(img, persona)
            
            # Configuración (Por defecto: nivel fácil)
            config = {
                "persona": persona,
                "usuario": usuario,
                "password": AuthValidator.hash_password(password),
                "fecha_registro": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ultimo_acceso": "",
                "login": False,
                "intentos_fallidos": 0,
                "cuenta_bloqueada_hasta": None,
                "nivel_seguridad": "facil",
                "telefono": "",
                "avatar": str(avatar_path),
                "avatar_shape": avatar_shape
            }
            
            config_final = process_config_for_save(config)
            with open(ruta_usuario / "config.json", "w", encoding="utf-8") as f:
                json.dump(config_final, f, indent=4)

            
            # Preferencias
            preferencias = {
                "tema": "azul",
                "mostrar_clima": True,
                "ciudad_clima": "Madrid",
                "pais_clima": "ES",
                "api_clima": "openweathermap",
                "mostrar_noticias": True,
                "categoria_noticias": "general",
                "pais_noticias": "es",
                "api_noticias": "newsapi",
                "mostrar_reloj": True,
                "formato_24h": True,
                "mostrar_mini_calendario": True,
                "mostrar_info_usuario": True,
                "mostrar_info_sistema": True,
                "notificaciones": True
            }
            
            with open(ruta_usuario / "preferencias.json", "w", encoding="utf-8") as f:
                json.dump(preferencias, f, indent=4)
                
            return True, "Cuenta creada exitosamente"
            
        except Exception as e:
            if ruta_usuario.exists():
                shutil.rmtree(ruta_usuario)
            return False, f"Error al crear usuario: {str(e)}"
