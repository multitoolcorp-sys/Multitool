import sys
import os
import secrets
import hashlib
import base64
import json
import urllib.parse
import urllib.request
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt, QUrl
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QFrame
)
from PyQt6.QtGui import QFont, QDesktopServices

# --- UTILIDADES PKCE ---

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def generate_pkce():
    """Genera un code_verifier y su correspondiente code_challenge (S256)"""
    verifier_bytes = secrets.token_bytes(48)
    code_verifier = _base64url_encode(verifier_bytes)
    
    digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = _base64url_encode(digest)
    
    return code_verifier, code_challenge


# --- SERVIDOR LOCAL HTTP CALLBACK ---

class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    auth_code = None
    error = None

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            _OAuthCallbackHandler.auth_code = params["code"][0]
            html_response = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Autenticación Exitosa - MultiTool</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: #12121e;
                        color: #ffffff;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .card {
                        background: #1e1e2d;
                        padding: 40px;
                        border-radius: 16px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                        text-align: center;
                        max-width: 420px;
                        border: 1px solid rgba(99, 102, 241, 0.3);
                    }
                    h1 { color: #43A047; font-size: 24px; margin-bottom: 10px; }
                    p { color: #a0a0a0; font-size: 14px; line-height: 1.6; }
                    .badge {
                        display: inline-block;
                        background: #6366F1;
                        color: white;
                        padding: 8px 16px;
                        border-radius: 20px;
                        font-weight: bold;
                        margin-top: 15px;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>✅ ¡Inicio de Sesión Exitoso!</h1>
                    <p>Google ha verificado tu cuenta correctamente con MultiTool.</p>
                    <div class="badge">Puedes cerrar esta ventana y regresar a la App.</div>
                </div>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_response.encode("utf-8"))
        else:
            _OAuthCallbackHandler.error = params.get("error", ["Error desconocido"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h1>Error de autenticación: {_OAuthCallbackHandler.error}</h1>".encode("utf-8"))


class OAuthServerWorker(QThread):
    code_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, port=8080):
        super().__init__()
        self.port = port
        self.httpd = None

    def run(self):
        _OAuthCallbackHandler.auth_code = None
        _OAuthCallbackHandler.error = None
        try:
            self.httpd = HTTPServer(('127.0.0.1', self.port), _OAuthCallbackHandler)
            self.httpd.timeout = 1.0
            
            for _ in range(180):
                if self.isInterruptionRequested():
                    break
                self.httpd.handle_request()
                if _OAuthCallbackHandler.auth_code:
                    self.code_received.emit(_OAuthCallbackHandler.auth_code)
                    break
                if _OAuthCallbackHandler.error:
                    self.error_occurred.emit(_OAuthCallbackHandler.error)
                    break
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if self.httpd:
                try:
                    self.httpd.server_close()
                except Exception:
                    pass

    def stop(self):
        self.requestInterruption()
        self.wait(2000)


# --- GESTOR OAUTH GOOGLE ---

class GoogleOAuthManager(QObject):
    login_success = pyqtSignal(dict)   # {"name": ..., "email": ..., "picture": ...}
    login_completed = pyqtSignal(dict) # Alias para compatibilidad
    auth_success = pyqtSignal(dict)    # Alias para compatibilidad
    login_error = pyqtSignal(str)      # Mensaje de error
    login_failed = pyqtSignal(str)     # Alias para compatibilidad
    auth_error = pyqtSignal(str)       # Alias para compatibilidad
    logout_completed = pyqtSignal()

    DEFAULT_CLIENT_ID = ""
    DEFAULT_CLIENT_SECRET = ""

    def __init__(self, ruta_usuario=None):
        super().__init__()
        if not ruta_usuario:
            try:
                from controlador.utils.paths import get_data_path
                self.ruta_usuario = get_data_path()
            except Exception:
                self.ruta_usuario = Path.cwd()
        else:
            self.ruta_usuario = Path(ruta_usuario)
        self.session_file = self.ruta_usuario / "browser_data" / "google_session.json"
        self.config_file = self.ruta_usuario / "browser_data" / "google_client_config.json"
        
        self.server_worker = None
        self.current_code_verifier = None
        self.current_code_challenge = None
        self.port = 9004
        self.redirect_uri = f"http://127.0.0.1:{self.port}/callback"
        
        self.client_id = self.load_client_id()
        self.client_secret = self.DEFAULT_CLIENT_SECRET

        # Enlazar alias de señales
        self.login_success.connect(self.login_completed.emit)
        self.login_success.connect(self.auth_success.emit)
        self.login_error.connect(self.login_failed.emit)
        self.login_error.connect(self.auth_error.emit)

    def load_client_id(self) -> str:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    cid = cfg.get("client_id", "").strip()
                    if cid and "multitooldesktopclient" not in cid and "1098670840502" not in cid:
                        return cid
            except Exception:
                pass
        # Sobrescribir archivo de configuracion previo si tenia el ID invalido
        self.save_client_id(self.DEFAULT_CLIENT_ID)
        return self.DEFAULT_CLIENT_ID

    def save_client_id(self, new_client_id: str):
        self.client_id = new_client_id.strip()
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({"client_id": self.client_id}, f, indent=4)
        except Exception as e:
            print(f"[ERROR-OAUTH] No se pudo guardar client_id: {e}")

    def is_logged_in(self) -> bool:
        sess = self.load_session()
        return bool(sess and "user" in sess and sess["user"])

    def get_user_info(self) -> dict:
        sess = self.load_session()
        return sess.get("user", {}) if sess else {}

    def load_session(self) -> dict:
        if self.session_file.exists():
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def login(self):
        self.start_oauth_flow()

    def start_oauth_flow(self):
        """Genera par PKCE, inicia servidor local HTTP en puerto 9004 y abre el navegador con la URL de autorización"""
        if not self.client_id:
            self.login_error.emit("No se ha configurado un Client ID de Google.")
            return

        self.current_code_verifier, self.current_code_challenge = generate_pkce()

        if self.server_worker and self.server_worker.isRunning():
            self.server_worker.stop()

        self.server_worker = OAuthServerWorker(port=self.port)
        self.server_worker.code_received.connect(self._on_code_received)
        self.server_worker.error_occurred.connect(lambda err: self.login_error.emit(f"Error OAuth: {err}"))
        self.server_worker.start()

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "code_challenge": self.current_code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "select_account"
        }
        oauth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
        
        QDesktopServices.openUrl(QUrl(oauth_url))

    def _on_code_received(self, auth_code: str):
        """Intercambia el código de autorización + code_verifier por Tokens de Google"""
        try:
            token_url = "https://oauth2.googleapis.com/token"
            payload = {
                "client_id": self.client_id,
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": self.current_code_verifier
            }
            if hasattr(self, "client_secret") and self.client_secret:
                payload["client_secret"] = self.client_secret

            data = urllib.parse.urlencode(payload).encode("utf-8")

            req = urllib.request.Request(token_url, data=data, headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "MultiTool-DesktopApp/1.0"
            })

            with urllib.request.urlopen(req) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))

            access_token = token_data.get("access_token")
            if not access_token:
                self.login_error.emit("No se recibió el token de acceso de Google.")
                return

            user_info = self._fetch_user_info(access_token)
            
            session_data = {
                "access_token": access_token,
                "refresh_token": token_data.get("refresh_token", ""),
                "expires_in": token_data.get("expires_in", 3600),
                "token_type": token_data.get("token_type", "Bearer"),
                "id_token": token_data.get("id_token", ""),
                "user": user_info
            }
            self.save_session(session_data)
            self.login_success.emit(session_data)

        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            self.login_error.emit(f"Error al intercambiar token ({e.code}): {err_msg}")
        except Exception as e:
            self.login_error.emit(f"Excepción en intercambio de token: {e}")

    def _fetch_user_info(self, access_token: str) -> dict:
        info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        req = urllib.request.Request(info_url, headers={
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "MultiTool-DesktopApp/1.0"
        })
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def save_session(self, session_data: dict):
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR-OAUTH] No se pudo guardar la sesión de Google: {e}")

    def logout(self):
        if self.session_file.exists():
            try:
                self.session_file.unlink()
            except Exception:
                pass
        self.logout_completed.emit()


# --- DIÁLOGO DE CONFIGURACIÓN CLIENT ID ---

class GoogleClientConfigDialog(QDialog):
    def __init__(self, current_client_id: str, colores: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Client ID de Google OAuth 2.0")
        self.setFixedWidth(460)
        self.colores = colores or {}

        bg = self.colores.get('bg_principal', '#1E1E1E')
        fg = self.colores.get('fg_principal', '#E0E0E0')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background: {bg}; color: {fg}; font-family: 'Inter';")
        
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        lbl_info = QLabel("🔑 Configuración de Cliente Google Cloud")
        lbl_info.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        lay.addWidget(lbl_info)

        lbl_desc = QLabel(
            "Para autenticarte con Google vía OAuth 2.0 + PKCE, puedes utilizar tu propio "
            "Client ID de Google Cloud Console (Tipo: Aplicación de Escritorio)."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        lay.addWidget(lbl_desc)

        group = QGroupBox("Credenciales")
        group.setStyleSheet(f"color: {fg}; font-weight: bold; border: 1px solid rgba(255,255,255,0.1); margin-top: 5px;")
        g_lay = QVBoxLayout(group)

        g_lay.addWidget(QLabel("Client ID:"))
        self.txt_client_id = QLineEdit(current_client_id)
        self.txt_client_id.setFont(QFont("Consolas", 9))
        self.txt_client_id.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#2D2D2D')}; color: white; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 6px;")
        g_lay.addWidget(self.txt_client_id)

        lay.addWidget(group)

        btn_lay = QHBoxLayout()
        btn_save = QPushButton("Guardar")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"background: {acento}; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        btn_save.clicked.connect(self.accept)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#3D3D3D')}; color: white; border: none; padding: 8px 16px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)

        btn_lay.addStretch()
        btn_lay.addWidget(btn_cancel)
        btn_lay.addWidget(btn_save)
        lay.addLayout(btn_lay)

    def get_client_id(self) -> str:
        return self.txt_client_id.text().strip()
