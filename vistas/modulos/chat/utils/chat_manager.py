import socket
import threading
import json
import datetime
import uuid
import base64
import time

class ChatSession:
    """Clase para representar el estado de una conexión local (Host o Cliente)"""
    def __init__(self, es_servidor=False, usuario_local="Usuario"):
        self.es_servidor = es_servidor
        self.activo = False
        self.puerto = None
        self.ip = None
        
        # Sockets
        self.servidor_socket = None
        self.cliente_socket = None
        self.clientes = {} # {socket: {'usuario': str, 'ip': str}}
        self.lista_usuarios = []
        
        if es_servidor:
            self.lista_usuarios = [f"{usuario_local} (Host)"]
        else:
            self.lista_usuarios = [usuario_local]

class ChatManager:
    DISCOVERY_PORT = 55401
    DISCOVERY_MAGIC = "MULTITOOL_CHAT_HOST_V1"
    DISCOVERY_PROBE = "MULTITOOL_CHAT_DISCOVER"

    def __init__(self, usuario):
        self.usuario = usuario
        self.sesion = None  # Instancia única de ChatSession

        # Callbacks de UI
        self.callback_mensaje = None
        self.callback_estado = None
        self.callback_usuarios = None
        self.callback_ip = None
        self.callback_notificacion = None
        self.callback_hosts_lan = None

        # Auto-descubrimiento LAN
        self._scanner_activo = False
        self._scanner_sock = None
        self._hosts_descubiertos = {}  # {"ip:port": dict}

    def configurar_callbacks(self, msg_cb, status_cb, users_cb, ip_cb=None, notify_cb=None, hosts_cb=None):
        self.callback_mensaje = msg_cb
        self.callback_estado = status_cb
        self.callback_usuarios = users_cb
        self.callback_ip = ip_cb
        self.callback_notificacion = notify_cb
        self.callback_hosts_lan = hosts_cb

    def esta_activo(self):
        return self.sesion.activo if self.sesion else False

    def es_host(self):
        return self.sesion.es_servidor if self.sesion else False

    def get_puerto(self):
        return self.sesion.puerto if self.sesion else None

    def get_ip(self):
        return self.sesion.ip if self.sesion else None

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            try:
                ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def iniciar_servidor(self, puerto):
        """Inicia el servidor socket (Host) con reintentos para evitar colisiones rápidas"""
        if self.esta_activo():
            self.detener_sesion()

        self.sesion = ChatSession(es_servidor=True, usuario_local=self.usuario)
        self.sesion.puerto = puerto
        
        try:
            srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Mecanismo de reintentos para resolver el bloqueo temporal del puerto en el OS
            for i in range(3):
                try:
                    srv_sock.bind(("", puerto))
                    break
                except OSError as e:
                    if i == 2:  # Último intento fallido, elevar excepción
                        raise e
                    time.sleep(0.2)
            
            srv_sock.listen(10)
            self.sesion.servidor_socket = srv_sock
            self.sesion.activo = True
            
            local_ip = self._get_local_ip()
            self.sesion.ip = local_ip
            
            # Lanzar hilo para aceptar conexiones y anuncio UDP LAN
            threading.Thread(target=self._aceptar_conexiones, daemon=True).start()
            threading.Thread(target=self._anunciar_host_lan, daemon=True).start()
            
            if self.callback_estado:
                self.callback_estado(f"Host Activo en IP: {local_ip} | Puerto: {puerto}")
            if self.callback_ip:
                self.callback_ip(local_ip, puerto)
            if self.callback_usuarios:
                self.callback_usuarios(self.sesion.lista_usuarios)
                
            return True
        except Exception as e:
            self.detener_sesion()
            if self.callback_estado:
                self.callback_estado(f"Error Host (Puerto {puerto}): {e}")
            return False

    def conectar(self, ip, puerto):
        """Conecta al host como cliente"""
        if self.esta_activo():
            self.detener_sesion()

        self.sesion = ChatSession(es_servidor=False, usuario_local=self.usuario)
        self.sesion.puerto = puerto
        self.sesion.ip = ip
        
        try:
            cl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cl_sock.settimeout(4.0)
            cl_sock.connect((ip, puerto))
            cl_sock.settimeout(None)
            
            self.sesion.cliente_socket = cl_sock
            self.sesion.activo = True
            
            # Enviar mensaje de autenticación inicial (join)
            self._enviar_raw(cl_sock, {
                "tipo": "join",
                "usuario": self.usuario
            })
            
            # Lanzar hilo para escuchar mensajes
            threading.Thread(target=self._escuchar_servidor, daemon=True).start()
            
            if self.callback_estado:
                self.callback_estado(f"Conectado a Host {ip}:{puerto}")
            if self.callback_ip:
                self.callback_ip(ip, puerto)
                
            return True
        except Exception as e:
            self.detener_sesion()
            if self.callback_estado:
                self.callback_estado(f"Error Conexión: {e}")
            return False

    def detener_sesion(self):
        """Cierra todos los sockets de forma limpia e inmediata"""
        sesion = self.sesion
        self.sesion = None
        if not sesion:
            if self.callback_estado:
                self.callback_estado("Desconectado")
            return

        sesion.activo = False

        # 1. Cerrar socket del servidor
        if sesion.servidor_socket:
            try:
                sesion.servidor_socket.shutdown(socket.SHUT_RDWR)
            except Exception: pass
            try:
                sesion.servidor_socket.close()
            except Exception: pass
            sesion.servidor_socket = None

        # 2. Cerrar sockets de clientes conectados
        for conn in list(sesion.clientes.keys()):
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except Exception: pass
            try:
                conn.close()
            except Exception: pass
        sesion.clientes.clear()

        # 3. Cerrar socket del cliente
        if sesion.cliente_socket:
            try:
                sesion.cliente_socket.shutdown(socket.SHUT_RDWR)
            except Exception: pass
            try:
                sesion.cliente_socket.close()
            except Exception: pass
            sesion.cliente_socket = None

        if self.callback_estado:
            self.callback_estado("Desconectado")
        if self.callback_usuarios:
            self.callback_usuarios([])

    def enviar_mensaje(self, texto):
        """Envía un mensaje de texto plano"""
        if not self.esta_activo(): return
        
        msg = {
            "tipo": "texto",
            "usuario": self.usuario,
            "contenido": texto,
            "timestamp": self._now()
        }
        self._enviar_y_procesar_propio(msg)

    def enviar_texto(self, texto):
        self.enviar_mensaje(texto)

    def enviar_imagen(self, b64_data, ext="png"):
        """Envía una imagen en base64"""
        if not self.esta_activo(): return
        
        msg = {
            "tipo": "imagen",
            "usuario": self.usuario,
            "data": b64_data,
            "ext": ext,
            "timestamp": self._now()
        }
        self._enviar_y_procesar_propio(msg)

    def enviar_sticker(self, b64_data, ext="png"):
        """Envía un sticker en base64"""
        if not self.esta_activo(): return
        
        msg = {
            "tipo": "sticker",
            "usuario": self.usuario,
            "data": b64_data,
            "ext": ext,
            "timestamp": self._now()
        }
        self._enviar_y_procesar_propio(msg)

    def enviar_archivo(self, b64_data, file_name):
        """Envía un archivo en base64"""
        if not self.esta_activo(): return
        
        msg = {
            "tipo": "archivo",
            "usuario": self.usuario,
            "nombre": file_name,
            "data": b64_data,
            "timestamp": self._now()
        }
        self._enviar_y_procesar_propio(msg)

    def ejecutar_kick(self, target_user):
        """Kicka a un usuario (solo disponible para el Host)"""
        if not self.esta_activo() or not self.es_host(): return
        
        # Buscar el socket del target
        target_sock = None
        for sock, info in self.sesion.clientes.items():
            if info["usuario"] == target_user:
                target_sock = sock
                break
                
        if target_sock:
            # Enviar señal de kick
            self._enviar_raw(target_sock, {"tipo": "kick"})
            try:
                target_sock.shutdown(socket.SHUT_RDWR)
                target_sock.close()
            except Exception: pass
            
            if target_sock in self.sesion.clientes:
                del self.sesion.clientes[target_sock]
                
            self._difundir_sistema(f"{target_user} ha sido expulsado por el Host.")
            self._enviar_lista_usuarios_clientes()

    # --- LÓGICA DE SERVIDOR INTERNA ---
    def _aceptar_conexiones(self):
        while self.sesion and self.sesion.activo:
            try:
                conn, addr = self.sesion.servidor_socket.accept()
                threading.Thread(target=self._manejar_conexion_servidor, args=(conn, addr), daemon=True).start()
            except Exception:
                break

    def _manejar_conexion_servidor(self, conn, addr):
        temp_user = f"Anon_{addr[1]}"
        self.sesion.clientes[conn] = {"usuario": temp_user, "ip": addr[0]}
        
        try:
            while self.sesion and self.sesion.activo:
                msg = self._recibir_completo(conn)
                if not msg: break
                
                tipo = msg.get("tipo")
                
                if tipo == "join":
                    usuario_solicitado = msg.get("usuario", temp_user)
                    
                    # Asegurar nombre de usuario único
                    nombres_activos = [self.usuario] + [c["usuario"] for c in self.sesion.clientes.values() if c["usuario"] != temp_user]
                    nombre_final = usuario_solicitado
                    contador = 1
                    while nombre_final in nombres_activos:
                        nombre_final = f"{usuario_solicitado}_{contador}"
                        contador += 1
                        
                    self.sesion.clientes[conn]["usuario"] = nombre_final
                    
                    # Confirmar conexión y enviar parámetros iniciales
                    self._enviar_raw(conn, {
                        "tipo": "join_ok",
                        "usuario_asignado": nombre_final
                    })
                    
                    self._difundir_sistema(f"{nombre_final} se ha unido al chat.")
                    self._enviar_lista_usuarios_clientes()
                    
                elif tipo in ["texto", "mensaje", "imagen", "archivo", "sticker"]:
                    # Propagar mensaje a todos los demás clientes
                    msg["usuario"] = self.sesion.clientes[conn]["usuario"]
                    # Mostrar localmente en el Host
                    if self.callback_mensaje:
                        self.callback_mensaje(msg)
                    # Enviar a todos los clientes excepto al remitente
                    for c_sock in list(self.sesion.clientes.keys()):
                        if c_sock != conn:
                            self._enviar_raw(c_sock, msg)
                            
        except Exception: pass
        finally:
            if conn in self.sesion.clientes:
                user_quit = self.sesion.clientes[conn]["usuario"]
                del self.sesion.clientes[conn]
                try:
                    conn.close()
                except Exception: pass
                
                self._difundir_sistema(f"{user_quit} se ha desconectado.")
                self._enviar_lista_usuarios_clientes()

    def _enviar_lista_usuarios_clientes(self):
        """Actualiza la lista local y difunde la nueva lista a todos los clientes"""
        lista = [f"{self.usuario} (Host)"]
        for c in self.sesion.clientes.values():
            lista.append(c["usuario"])
            
        self.sesion.lista_usuarios = lista
        
        # Enviar lista a todos
        for conn in self.sesion.clientes:
            self._enviar_raw(conn, {
                "tipo": "lista_usuarios",
                "lista": lista
            })
            
        # Actualizar local
        if self.callback_usuarios:
            self.callback_usuarios(lista)

    def _difundir_sistema(self, texto):
        """Difunde un mensaje de sistema a todos los clientes y lo dibuja localmente"""
        msg = {
            "tipo": "sistema",
            "usuario": "SISTEMA",
            "mensaje": texto,
            "timestamp": self._now()
        }
        if self.callback_mensaje:
            self.callback_mensaje(msg)
        for conn in self.sesion.clientes:
            self._enviar_raw(conn, msg)

    # --- LÓGICA DE CLIENTE INTERNA ---
    def _escuchar_servidor(self):
        while self.sesion and self.sesion.activo:
            try:
                msg = self._recibir_completo(self.sesion.cliente_socket)
                if not msg: break
                
                tipo = msg.get("tipo")
                
                if tipo == "join_ok":
                    self.usuario = msg.get("usuario_asignado", self.usuario)
                    if self.callback_notificacion:
                        self.callback_notificacion("username_sync", self.usuario)
                elif tipo == "lista_usuarios":
                    self.sesion.lista_usuarios = msg.get("lista", [])
                    if self.callback_usuarios:
                        self.callback_usuarios(self.sesion.lista_usuarios)
                elif tipo == "kick":
                    if self.callback_estado:
                        self.callback_estado("EXPULSADO DE LA SALA")
                    break
                elif tipo in ["texto", "mensaje", "imagen", "archivo", "sticker", "sistema"]:
                    if self.callback_mensaje:
                        self.callback_mensaje(msg)
            except Exception:
                break
                
        # Si se sale del bucle, cerrar sesión
        self.detener_sesion()

    # --- PROTOCOLO DE RED ---
    def _enviar_raw(self, sock, data_dict):
        try:
            encoded_data = json.dumps(data_dict).encode("utf-8")
            length_prefix = len(encoded_data).to_bytes(4, byteorder="big")
            sock.sendall(length_prefix + encoded_data)
        except Exception:
            pass

    def _recibir_completo(self, sock):
        try:
            raw_len = sock.recv(4)
            if not raw_len or len(raw_len) < 4: return None
            
            longitud = int.from_bytes(raw_len, byteorder="big")
            chunks = []
            bytes_received = 0
            
            while bytes_received < longitud:
                chunk = sock.recv(min(longitud - bytes_received, 8192))
                if not chunk: return None
                chunks.append(chunk)
                bytes_received += len(chunk)
                
            return json.loads(b"".join(chunks).decode("utf-8"))
        except Exception:
            return None

    # --- COMUN ---
    def _enviar_y_procesar_propio(self, msg):
        """Envía el mensaje según seamos Host o Cliente, y lo muestra localmente"""
        if self.es_host():
            # Servidor: Mostrar localmente y difundir a todos los clientes
            if self.callback_mensaje:
                self.callback_mensaje(msg)
            for conn in self.sesion.clientes:
                self._enviar_raw(conn, msg)
        else:
            # Cliente: Enviar al servidor (el servidor se encargará de reenviarlo o procesarlo)
            if self.sesion.cliente_socket:
                self._enviar_raw(self.sesion.cliente_socket, msg)
            # Para una mejor respuesta, los clientes procesamos localmente nuestro propio mensaje al enviarlo
            if self.callback_mensaje:
                self.callback_mensaje(msg)

    def _now(self):
        return datetime.datetime.now().strftime("%H:%M:%S")

    # --- AUTO-DESCUBRIMIENTO LAN (UDP BROADCAST) ---
    def _crear_payload_anuncio(self) -> bytes:
        if not self.sesion:
            return b""
        payload = {
            "magic": self.DISCOVERY_MAGIC,
            "host": self.usuario,
            "sala": f"Sala de {self.usuario}",
            "ip": self.sesion.ip or self._get_local_ip(),
            "port": self.sesion.puerto,
            "usuarios": len(self.sesion.lista_usuarios),
        }
        return json.dumps(payload).encode("utf-8")

    def _anunciar_host_lan(self):
        """Anuncia periódicamente este Host en la red LAN vía UDP Broadcast."""
        udp_sock = None
        try:
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            while self.sesion and self.sesion.activo and self.sesion.es_servidor:
                data = self._crear_payload_anuncio()
                if data:
                    for target in ("255.255.255.255", "127.0.0.1"):
                        try:
                            udp_sock.sendto(data, (target, self.DISCOVERY_PORT))
                        except Exception:
                            pass
                for _ in range(15):
                    if not (self.sesion and self.sesion.activo and self.sesion.es_servidor):
                        break
                    time.sleep(0.1)
        except Exception:
            pass
        finally:
            if udp_sock:
                try:
                    udp_sock.close()
                except Exception:
                    pass

    def iniciar_escaneo_lan(self):
        """Inicia la escucha pasiva + sondeo activo de hosts de chat en la red local."""
        if self._scanner_activo:
            self.sondear_hosts_lan()
            return
        self._scanner_activo = True
        threading.Thread(target=self._bucle_escaneo_lan, daemon=True).start()
        self.sondear_hosts_lan()

    def detener_escaneo_lan(self):
        self._scanner_activo = False
        if self._scanner_sock:
            try:
                self._scanner_sock.close()
            except Exception:
                pass
            self._scanner_sock = None

    def sondear_hosts_lan(self):
        """Envía un broadcast UDP para que todos los Hosts LAN respondan de inmediato."""
        def _probe():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                msg = self.DISCOVERY_PROBE.encode("utf-8")
                for target in ("255.255.255.255", "127.0.0.1"):
                    try:
                        s.sendto(msg, (target, self.DISCOVERY_PORT))
                    except Exception:
                        pass
                s.close()
            except Exception:
                pass
        threading.Thread(target=_probe, daemon=True).start()

    def _bucle_escaneo_lan(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)
            sock.bind(("", self.DISCOVERY_PORT))
            self._scanner_sock = sock
        except Exception:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
            self._scanner_activo = False
            return

        last_prune = time.time()
        while self._scanner_activo:
            changed = False
            try:
                raw, addr = sock.recvfrom(2048)
                text = raw.decode("utf-8", errors="ignore").strip()
                if text == self.DISCOVERY_PROBE:
                    if self.esta_activo() and self.es_host():
                        reply = self._crear_payload_anuncio()
                        if reply:
                            sock.sendto(reply, (addr[0], self.DISCOVERY_PORT))
                elif text.startswith("{"):
                    info = json.loads(text)
                    if info.get("magic") == self.DISCOVERY_MAGIC:
                        ip = info.get("ip") or addr[0]
                        port = int(info.get("port", 55400))
                        key = f"{ip}:{port}"
                        info["ip"] = ip
                        info["port"] = port
                        info["last_seen"] = time.time()
                        self._hosts_descubiertos[key] = info
                        changed = True
            except socket.timeout:
                pass
            except Exception:
                if not self._scanner_activo:
                    break

            ahora = time.time()
            if ahora - last_prune >= 2.0:
                expirados = [k for k, v in self._hosts_descubiertos.items() if ahora - v.get("last_seen", 0) > 6.0]
                for k in expirados:
                    del self._hosts_descubiertos[k]
                    changed = True
                last_prune = ahora

            if changed and self.callback_hosts_lan:
                self.callback_hosts_lan(list(self._hosts_descubiertos.values()))

        try:
            sock.close()
        except Exception:
            pass
        self._scanner_sock = None
