import socket
import json
import threading

class GameSocketManager:
    """Gestor de Sockets TCP para Multijugador Local LAN (1v1) en Minijuegos"""
    def __init__(self, usuario="Jugador"):
        self.usuario = usuario
        self.sock = None
        self.conn = None
        self.es_servidor = False
        self.activo = False
        self.callback_movimiento = None
        self.callback_estado = None

    def configurar_callbacks(self, callback_movimiento, callback_estado=None):
        self.callback_movimiento = callback_movimiento
        self.callback_estado = callback_estado

    def iniciar_servidor_host(self, puerto=55500):
        if self.activo: self.detener()
        self.es_servidor = True
        
        puerto_exito = None
        for p in [puerto, 55501, 55502, 55503, 55504]:
            try:
                temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                temp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                temp_sock.bind(("", p))
                temp_sock.listen(1)
                self.sock = temp_sock
                puerto_exito = p
                break
            except Exception:
                continue

        if not puerto_exito or not self.sock:
            self.detener()
            if self.callback_estado: 
                self.callback_estado("❌ Error: No se pudo abrir puerto host LAN (Puertos 55500-55504 en uso).")
            return False, "127.0.0.1"

        self.activo = True
        ip = self._get_local_ip()
        if self.callback_estado:
            self.callback_estado(f"📡 Servidor Host 1v1 Activo en {ip}:{puerto_exito} - Esperando rival...")
        threading.Thread(target=self._aceptar_cliente, daemon=True).start()
        return True, f"{ip}:{puerto_exito}"

    def _aceptar_cliente(self):
        try:
            conn, addr = self.sock.accept()
            self.conn = conn
            if self.callback_estado:
                self.callback_estado(f"🟢 Jugador conectado desde {addr[0]}. ¡Partida 1v1 iniciada!")
            threading.Thread(target=self._escuchar_mensajes, daemon=True).start()
        except Exception: pass

    def conectar_a_host(self, ip_host, puerto=55500):
        if self.activo: self.detener()
        self.es_servidor = False
        
        # Probar puertos host posibles
        puertos_a_probar = [puerto, 55501, 55502, 55503, 55504]
        if ":" in ip_host:
            parts = ip_host.split(":")
            ip_host = parts[0]
            try: puertos_a_probar.insert(0, int(parts[1]))
            except ValueError: pass

        conectado = False
        for p in puertos_a_probar:
            try:
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.settimeout(3.0)
                self.conn.connect((ip_host, p))
                self.conn.settimeout(None)
                conectado = True
                break
            except Exception:
                continue

        if not conectado:
            self.detener()
            if self.callback_estado: 
                self.callback_estado(f"❌ No se pudo conectar al Host LAN {ip_host}.")
            return False

        self.activo = True
        if self.callback_estado:
            self.callback_estado(f"🟢 Conectado con éxito al Host 1v1 {ip_host}.")
        threading.Thread(target=self._escuchar_mensajes, daemon=True).start()
        return True

    def enviar_movimiento(self, tipo_juego, payload):
        if not self.activo or not self.conn: return False
        try:
            data = json.dumps({
                "juego": tipo_juego,
                "usuario": self.usuario,
                "payload": payload
            }) + "\n"
            self.conn.sendall(data.encode('utf-8'))
            return True
        except Exception as e:
            if self.callback_estado: self.callback_estado(f"❌ Error al enviar movimiento: {e}")
            return False

    def _escuchar_mensajes(self):
        buffer = ""
        while self.activo and self.conn:
            try:
                chunk = self.conn.recv(4096).decode('utf-8')
                if not chunk: break
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        msg = json.loads(line)
                        if self.callback_movimiento:
                            self.callback_movimiento(msg)
            except Exception:
                break
        self.detener()
        if self.callback_estado: self.callback_estado("🔴 Conexión 1v1 LAN finalizada.")

    def detener(self):
        self.activo = False
        if self.conn:
            try: self.conn.close()
            except Exception: pass
            self.conn = None
        if self.sock:
            try: self.sock.close()
            except Exception: pass
            self.sock = None

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
