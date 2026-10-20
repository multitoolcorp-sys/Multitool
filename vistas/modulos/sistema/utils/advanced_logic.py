import psutil
import socket
import subprocess
import platform
import os
import requests
import threading
from pathlib import Path

class NetworkLogic:
    """Lógica de Red Avanzada agnóstica al sistema operativo"""
    @staticmethod
    def get_public_ip():
        try:
            # Lista de servicios para redundancia
            for url in ['https://api.ipify.org', 'https://ifconfig.me/ip', 'https://icanhazip.com']:
                try:
                    return requests.get(url, timeout=2).text.strip()
                except: continue
        except: pass
        return "No disponible"

    @staticmethod
    def get_network_details():
        details = {'dns': 'N/A', 'hostname': 'N/A', 'local_ip': 'N/A'}
        try:
            hostname = socket.gethostname()
            details['hostname'] = hostname
            # Intento de obtener IP privada real
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                details['local_ip'] = s.getsockname()[0]
            except:
                details['local_ip'] = socket.gethostbyname(hostname)
            finally:
                s.close()
            
            # DNS Dinámico por SO
            os_name = platform.system()
            if os_name == "Windows":
                import winreg
                try:
                    reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
                    key = winreg.OpenKey(reg, r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters")
                    details['dns'] = winreg.QueryValueEx(key, "NameServer")[0]
                    if not details['dns']: details['dns'] = "Auto (DHCP)"
                except: details['dns'] = "Windows DNS"
            elif os_name in ["Linux", "Darwin"]:
                try:
                    # Intento común para Unix (resolv.conf)
                    if Path("/etc/resolv.conf").exists():
                        with open("/etc/resolv.conf", "r") as f:
                            for line in f:
                                if line.startswith("nameserver"):
                                    details['dns'] = line.split()[1]
                                    break
                except: pass
        except: pass
        return details

    @staticmethod
    def check_internet():
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False

class SecurityLogic:
    """Monitoreo de Seguridad Multiplataforma"""
    @staticmethod
    def get_open_ports():
        ports = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'LISTEN':
                    ports.append({
                        'port': conn.laddr.port,
                        'ip': conn.laddr.ip,
                        'pid': conn.pid
                    })
        except: pass
        return ports

    @staticmethod
    def get_firewall_status():
        os_name = platform.system()
        try:
            if os_name == "Windows":
                out = subprocess.check_output('netsh advfirewall show allprofiles state', shell=True, text=True)
                return "Activo (Defender)" if "ON" in out else "Inactivo"
            elif os_name == "Linux":
                # UFW es el estándar en Ubuntu/Mint
                try:
                    out = subprocess.check_output('ufw status', shell=True, text=True)
                    return "Activo (UFW)" if "active" in out else "Inactivo"
                except:
                    # Alternativa iptables
                    return "Detectando (Iptables)"
            elif os_name == "Darwin":
                out = subprocess.check_output('/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate', shell=True, text=True)
                return "Activo (macOS)" if "enabled" in out.lower() else "Desactivado"
        except: pass
        return "No detectado"

    @staticmethod
    def get_active_services():
        services = []
        os_name = platform.system()
        try:
            if os_name == "Windows":
                # Limitar para no saturar la UI
                for s in list(psutil.win_service_iter())[:30]:
                    if s.status() == 'running':
                        services.append({'name': s.display_name(), 'status': 'Ejecutando'})
            elif os_name in ["Linux", "Darwin"]:
                # Listar servicios activos vía procesos principales o systemd si es Linux
                for p in psutil.process_iter(['name', 'username']):
                    if len(services) > 30: break
                    if p.info['username'] in ['root', '_windowserver', 'daemon']:
                        services.append({'name': p.info['name'], 'status': 'Servicio/Daemon'})
        except: pass
        return services

class SystemToolsLogic:
    """Utilidades Técnicas Multiplataforma"""
    @staticmethod
    def limpiar_temp():
        cleaned = 0
        os_name = platform.system()
        
        target_dirs = []
        if os_name == "Windows":
            target_dirs.append(os.environ.get('TEMP', 'C:\\Temp'))
        elif os_name == "Linux":
            target_dirs.append('/tmp')
            target_dirs.append(os.path.expanduser('~/.cache'))
        elif os_name == "Darwin":
            target_dirs.append(os.environ.get('TMPDIR', '/tmp'))
            target_dirs.append(os.path.expanduser('~/Library/Caches'))
            
        for t_dir in target_dirs:
            if not os.path.exists(t_dir): continue
            try:
                for root, dirs, files in os.walk(t_dir):
                    for f in files:
                        try:
                            os.remove(os.path.join(root, f))
                            cleaned += 1
                        except: pass
                    if cleaned > 1000: break # Evitar bucles infinitos en sistemas muy sucios
            except: pass
        return cleaned

    @staticmethod
    def flush_dns():
        os_name = platform.system()
        try:
            if os_name == "Windows":
                subprocess.check_call("ipconfig /flushdns", shell=True, stdout=subprocess.DEVNULL)
            elif os_name == "Linux":
                # Intenta varios comandos comunes
                cmds = ["resolvectl flush-caches", "systemd-resolve --flush-caches", "service nscd restart"]
                for c in cmds:
                    try: 
                        subprocess.check_call(c, shell=True, stdout=subprocess.DEVNULL)
                        break
                    except: continue
            elif os_name == "Darwin":
                subprocess.check_call("sudo killall -HUP mDNSResponder", shell=True)
            return True
        except: return False

    @staticmethod
    def restart_shell():
        os_name = platform.system()
        try:
            if os_name == "Windows":
                subprocess.check_call("taskkill /f /im explorer.exe", shell=True, stdout=subprocess.DEVNULL)
                subprocess.Popen("explorer.exe", shell=True)
                return True
            elif os_name == "Linux":
                # Reiniciar GNOME Shell (solo funciona en X11 de forma nativa)
                subprocess.Popen("gnome-shell --replace &", shell=True)
                return True
            elif os_name == "Darwin":
                subprocess.check_call("killall Finder", shell=True)
                return True
        except: pass
        return False

