"""
crypto.py - Utilidades criptográficas para el módulo de Seguridad
Implementa derivación de claves PBKDF2HMAC, cifrado AES-256-CBC con PKCS7 padding,
compatibilidad con formatos legados y cálculo de hashes.
"""

import os
import json
import base64
import hashlib
from typing import Dict, Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


def derive_key(password: str, salt: bytes) -> bytes:
    """Deriva una clave AES de 256 bits mediante PBKDF2HMAC-SHA256 con 100,000 iteraciones."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
        backend=default_backend()
    )
    return kdf.derive(password.encode('utf-8'))


def encrypt_vault(data_str: str, password: str) -> Dict[str, str]:
    """Cifra una cadena JSON con AES-256-CBC y padding PKCS7, generando salt e IV aleatorios."""
    salt = os.urandom(16)
    iv = os.urandom(16)
    key = derive_key(password, salt)
    
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data_str.encode('utf-8')) + padder.finalize()
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    
    return {
        "salt": base64.b64encode(salt).decode('utf-8'),
        "iv": base64.b64encode(iv).decode('utf-8'),
        "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
        "version": "aes-256-cbc-v2"
    }


def decrypt_vault(enc_dict: Dict[str, Any], password: str) -> str:
    """Descifra un diccionario cifrado con AES-256-CBC y retorna la cadena JSON original."""
    salt = base64.b64decode(enc_dict["salt"])
    iv = base64.b64decode(enc_dict["iv"])
    ciphertext = base64.b64decode(enc_dict["ciphertext"])
    
    key = derive_key(password, salt)
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()
    
    unpadder = padding.PKCS7(128).unpadder()
    decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
    
    return decrypted.decode('utf-8')


def encrypt_decrypt_vigenere(text: str, key: str) -> str:
    """Cifrado/Descifrado XOR simétrico legacy para migración automática de versiones antiguas."""
    if not key:
        return text
    res = []
    for i, c in enumerate(text):
        key_c = key[i % len(key)]
        res.append(chr(ord(c) ^ ord(key_c)))
    return "".join(res)


def calcular_hashes_texto(text: str) -> Dict[str, str]:
    """Calcula los hashes MD5, SHA-1, SHA-256 y SHA-512 de un texto en UTF-8."""
    b = text.encode('utf-8')
    return {
        "md5": hashlib.md5(b).hexdigest(),
        "sha1": hashlib.sha1(b).hexdigest(),
        "sha256": hashlib.sha256(b).hexdigest(),
        "sha512": hashlib.sha512(b).hexdigest()
    }


def calcular_hashes_archivo(filepath: str) -> Dict[str, str]:
    """Calcula los hashes MD5, SHA-1, SHA-256 y SHA-512 de un archivo por bloques."""
    h_md5 = hashlib.md5()
    h_sha1 = hashlib.sha1()
    h_sha256 = hashlib.sha256()
    h_sha512 = hashlib.sha512()
    
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h_md5.update(chunk)
            h_sha1.update(chunk)
            h_sha256.update(chunk)
            h_sha512.update(chunk)
            
    return {
        "md5": h_md5.hexdigest(),
        "sha1": h_sha1.hexdigest(),
        "sha256": h_sha256.hexdigest(),
        "sha512": h_sha512.hexdigest()
    }
