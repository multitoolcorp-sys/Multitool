"""
socket_hub.py
Sistema de comunicación en tiempo real basado en sockets TCP para Multitool.
Permite notificar eventos de actualización, recarga de módulos y sincronización
inter-proceso sin necesidad de realizar peticiones HTTP periódicas (polling).
"""
import socket
import threading
import json
import time
from typing import Callable, Dict, List, Any

DEFAULT_SOCKET_HOST = "127.0.0.1"
DEFAULT_SOCKET_PORT = 49285

_global_server = None
_server_lock = threading.Lock()

class SocketHubServer:
    """
    Servidor de sockets local que escucha en segundo plano eventos en tiempo real.
    Permite a la aplicación recibir avisos inmediatos de actualizaciones,
    compilaciones o cambios de estado sin sobrecargar la red ni el disco.
    """
    def __init__(self, host: str = DEFAULT_SOCKET_HOST, port: int = DEFAULT_SOCKET_PORT):
        self.host = host
        self.port = port
        self.running = False
        self._server_socket = None
        self._thread = None
        self._callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._lock = threading.Lock()

    def start(self):
        """Inicia el servidor en un hilo secundario daemon."""
        with self._lock:
            if self.running:
                return
            self.running = True

        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.5)
        except Exception as e:
            # Si el puerto ya está en uso por otra instancia de Multitool, no bloquea
            self.running = False
            return False

        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="SocketHubServerThread")
        self._thread.start()
        return True

    def stop(self):
        """Detiene el servidor de forma segura."""
        with self._lock:
            self.running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass

    def on_event(self, event_name: str, callback: Callable[[Dict[str, Any]], None]):
        """Registra un callback para un evento específico."""
        with self._lock:
            if event_name not in self._callbacks:
                self._callbacks[event_name] = []
            if callback not in self._callbacks[event_name]:
                self._callbacks[event_name].append(callback)

    def off_event(self, event_name: str, callback: Callable[[Dict[str, Any]], None]):
        """Desregistra un callback."""
        with self._lock:
            if event_name in self._callbacks:
                if callback in self._callbacks[event_name]:
                    self._callbacks[event_name].remove(callback)

    def _listen_loop(self):
        while self.running:
            try:
                client_sock, _ = self._server_socket.accept()
                t = threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    time.sleep(0.5)
                break

    def _handle_client(self, client_sock: socket.socket):
        try:
            client_sock.settimeout(5.0)
            data_buffer = b""
            while self.running:
                chunk = client_sock.recv(4096)
                if not chunk:
                    break
                data_buffer += chunk
                if b"\n" in data_buffer:
                    break

            if data_buffer:
                for line in data_buffer.decode("utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        event = msg.get("event")
                        payload = msg.get("payload", {})
                        if event:
                            self._dispatch_event(event, payload)
                    except json.JSONDecodeError:
                        pass

            client_sock.sendall(b'{"status":"ok"}\n')
        except Exception:
            pass
        finally:
            try:
                client_sock.close()
            except Exception:
                pass

    def _dispatch_event(self, event_name: str, payload: Dict[str, Any]):
        """Ejecuta los callbacks asociados al evento."""
        callbacks_to_run = []
        with self._lock:
            if event_name in self._callbacks:
                callbacks_to_run.extend(self._callbacks[event_name])
            if "*" in self._callbacks:
                callbacks_to_run.extend(self._callbacks["*"])

        for cb in callbacks_to_run:
            try:
                cb(payload)
            except Exception as e:
                print(f"[SocketHub] Error en callback para evento '{event_name}': {e}")


def get_socket_hub() -> SocketHubServer:
    """Retorna o inicia la instancia singleton del servidor de sockets."""
    global _global_server
    with _server_lock:
        if _global_server is None:
            _global_server = SocketHubServer()
            _global_server.start()
        return _global_server


def send_socket_event(event_name: str, payload: Dict[str, Any] = None, port: int = DEFAULT_SOCKET_PORT) -> bool:
    """
    Envía un evento de socket hacia la instancia activa de Multitool.
    Retorna True si fue entregado con éxito, False en caso contrario.
    """
    if payload is None:
        payload = {}
    message = json.dumps({"event": event_name, "payload": payload}) + "\n"

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((DEFAULT_SOCKET_HOST, port))
        sock.sendall(message.encode("utf-8"))
        sock.close()
        return True
    except Exception:
        return False
