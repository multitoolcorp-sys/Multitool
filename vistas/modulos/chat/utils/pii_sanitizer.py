import re

class PIISanitizer:
    """
    Sanitizador de Información de Identificación Personal (PII) y Datos Sensibles.
    Redacta datos confidenciales antes de enviarlos a proveedores de IA en la nube.
    """
    
    # Patrones Regex para datos confidenciales
    EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    IPV4_REGEX = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    IPV6_REGEX = r'\b(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}\b'
    WIN_PATH_REGEX = r'[a-zA-Z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*'
    UNIX_PATH_REGEX = r'/(?:[a-zA-Z0-9_-]+/)+[a-zA-Z0-9_-]+'
    API_KEY_REGEX = r'\b(?:sk-[a-zA-Z0-9]{20,T}|AIza[0-9A-Za-z-_]{35}|gsk_[a-zA-Z0-9]{20,})\b'
    CREDIT_CARD_REGEX = r'\b(?:\d[ -]*?){13,16}\b'
    PASS_PATTERN_REGEX = r'(?i)\b(password|passwd|clave|contraseña|secret|api_key)\s*[:=]\s*([^\s;]+)'

    def __init__(self, enabled=True):
        self.enabled = enabled

    def sanitize(self, text: str) -> tuple[str, dict]:
        """
        Devuelve el texto desinfectado y un diccionario con el recuento de elementos sanitizados.
        """
        if not self.enabled or not text:
            return text, {}

        redactions = {
            "emails": 0,
            "ips": 0,
            "paths": 0,
            "api_keys": 0,
            "passwords": 0,
            "credit_cards": 0
        }

        sanitized_text = text

        # 1. API Keys y Tokens
        def sub_key(match):
            redactions["api_keys"] += 1
            return "[API_KEY_PROTEGIDA]"
        sanitized_text = re.sub(self.API_KEY_REGEX, sub_key, sanitized_text)

        # 2. Contraseñas / Secretos explícitos
        def sub_pass(match):
            redactions["passwords"] += 1
            kw = match.group(1)
            return f"{kw}: [CONTRASEÑA_PROTEGIDA]"
        sanitized_text = re.sub(self.PASS_PATTERN_REGEX, sub_pass, sanitized_text)

        # 3. Correos Electrónicos
        def sub_email(match):
            redactions["emails"] += 1
            return "[EMAIL_PROTEGIDO]"
        sanitized_text = re.sub(self.EMAIL_REGEX, sub_email, sanitized_text)

        # 4. Direcciones IP
        def sub_ip(match):
            # No redactar localhost 127.0.0.1 ni 0.0.0.0
            ip = match.group(0)
            if ip in ("127.0.0.1", "0.0.0.0", "localhost"):
                return ip
            redactions["ips"] += 1
            return "[IP_PROTEGIDA]"
        sanitized_text = re.sub(self.IPV4_REGEX, sub_ip, sanitized_text)

        # 5. Rutas de Archivos Windows / Unix (sin alterar menciones intencionales @ruta)
        def sub_win_path(match):
            full_match = match.group(0)
            start_idx = match.start()
            if start_idx > 0 and sanitized_text[start_idx - 1] == "@":
                return full_match
            redactions["paths"] += 1
            return "[RUTA_WINDOWS_PROTEGIDA]"
        sanitized_text = re.sub(self.WIN_PATH_REGEX, sub_win_path, sanitized_text)

        def sub_unix_path(match):
            p = match.group(0)
            start_idx = match.start()
            if start_idx > 0 and sanitized_text[start_idx - 1] == "@":
                return p
            if p.startswith("/api/") or p.startswith("/v1/"):
                return p
            redactions["paths"] += 1
            return "[RUTA_UNIX_PROTEGIDA]"
        sanitized_text = re.sub(self.UNIX_PATH_REGEX, sub_unix_path, sanitized_text)

        return sanitized_text, redactions
