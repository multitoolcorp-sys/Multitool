import psutil
import platform
import datetime
import threading
import time
import subprocess
import socket
import os
from PyQt6.QtCore import QObject, pyqtSignal

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False

from .advanced_logic import NetworkLogic, SecurityLogic, SystemToolsLogic

class SystemManager(QObject):
    update_ui_signal = pyqtSignal(dict)

    def __init__(self, callbacks=None):
        super().__init__()
        self.callbacks = callbacks or {}
        self.monitoreo_activo = False
        
        # Datos para gráficos
        self.datos = {
            "tiempo": [],
            "cpu": [],
            "memoria": [],
            "disco": [],
            "gpu": []
        }
        
        self.last_net_io = psutil.net_io_counters()
        self.last_time = time.time()

    def obtener_total_info(self):
        info = self.obtener_info_hardware()
        net = NetworkLogic.get_network_details()
        
        resumen = {
            "so": f"{platform.system()} {platform.release()}",
            "version": platform.version(),
            "arch": platform.machine(),
            "nodo": platform.node(),
            "usuario": os.getlogin() if hasattr(os, "getlogin") else "User",
            "cpu_modelo": info.get("cpu", {}).get("nombre", "N/A"),
            "cpu_hilos": f"{info.get('cpu', {}).get('f', 0)} núcleos / {info.get('cpu', {}).get('l', 0)} hilos",
            "ram_total": info.get("memoria", {}).get("total", "N/A"),
            "ram_disp": info.get("memoria", {}).get("disponible", "N/A"),
            "ip_local": net.get("local_ip", "N/A"),
            "uptime": info.get("uptime", "N/A")
        }
        return resumen

    def obtener_info_hardware(self):
        info = {}
        try:
            cpu_freq = psutil.cpu_freq()
            info["cpu"] = {
                "nombre": self._get_cpu_name(),
                "f": psutil.cpu_count(logical=False),
                "l": psutil.cpu_count(logical=True),
                "freq_max": f"{cpu_freq.max:.0f}MHz" if cpu_freq else "N/A"
            }
            mem = psutil.virtual_memory()
            info["memoria"] = {
                "total": self._format_bytes(mem.total),
                "disponible": self._format_bytes(mem.available)
            }
            info["uptime"] = self._get_uptime()
        except: pass
        return info

    def _get_uptime(self):
        diff = time.time() - psutil.boot_time()
        hours, rem = divmod(diff, 3600)
        minutes, seconds = divmod(rem, 60)
        days, hours = divmod(hours, 24)
        if days > 0: return f"{int(days)}d {int(hours)}h {int(minutes)}m"
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

    def _get_cpu_name(self):
        """Obtiene el nombre comercial de la CPU de forma multiplataforma"""
        try:
            os_name = platform.system()
            if os_name == "Windows":
                import winreg
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
            elif os_name == "Darwin":
                # macOS
                import subprocess
                return subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
            elif os_name == "Linux":
                # Linux (leer de cpuinfo)
                if os.path.exists("/proc/cpuinfo"):
                    with open("/proc/cpuinfo", "r") as f:
                        for line in f:
                            if "model name" in line:
                                return line.split(":")[1].strip()
            return platform.processor()
        except: return platform.processor()

    def _format_bytes(self, b):
        if not b: return "0 B"
        for u in ['B', 'KB', 'MB', 'GB', 'TB']:
            if b < 1024: return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} PB"

    def iniciar_monitoreo(self):
        if not self.monitoreo_activo:
            self.monitoreo_activo = True
            threading.Thread(target=self._run_monitoreo, daemon=True).start()

    def detener_monitoreo(self):
        self.monitoreo_activo = False

    def _run_monitoreo(self):
        while self.monitoreo_activo:
            try:
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                # Ruta de disco raíz adaptable
                disk_path = 'C:\\' if platform.system() == "Windows" else '/'
                disk = psutil.disk_usage(disk_path)
                
                net_io = psutil.net_io_counters()
                now = time.time()
                dt = now - self.last_time
                up_speed = (net_io.bytes_sent - self.last_net_io.bytes_sent) / dt if dt > 0 else 0
                down_speed = (net_io.bytes_recv - self.last_net_io.bytes_recv) / dt if dt > 0 else 0
                self.last_net_io = net_io
                self.last_time = now
                
                gpu_data = self._obtener_gpu_status()
                
                # Procesos pesados (Top 5)
                top_procs = []
                try:
                   # Obtener iterador una sola vez
                   all_procs = []
                   for p in psutil.process_iter(['name', 'cpu_percent']):
                       all_procs.append(p.info)
                   
                   sorted_procs = sorted(all_procs, key=lambda x: x.get('cpu_percent', 0), reverse=True)
                   for p in sorted_procs[:5]:
                       if p.get('cpu_percent', 0) > 0.1:
                           top_procs.append(f"{p['name']} ({p['cpu_percent']:.1f}%)")
                except: pass

                data = {
                    "cpu": cpu, "mem_p": mem.percent, "mem_u": self._format_bytes(mem.used), "mem_t": self._format_bytes(mem.total),
                    "disk_p": disk.percent, "net_up": f"{self._format_bytes(up_speed)}/s", "net_down": f"{self._format_bytes(down_speed)}/s",
                    "gpu": gpu_data, "uptime": self._get_uptime(), "top_procs": top_procs
                }
                self.update_ui_signal.emit(data)
                self._update_graph_data(cpu, mem.percent, disk.percent, gpu_data.get("uso", 0))
                
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(2)

    def _obtener_gpu_status(self):
        if GPUTIL_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    g = gpus[0]
                    return {"uso": g.load*100, "nombre": g.name}
            except: pass
        return {"uso": 0, "nombre": "No detectada"}

    def _update_graph_data(self, c, m, d, g):
        for k, v in zip(["cpu", "memoria", "disco", "gpu"], [c or 0, m or 0, d or 0, g or 0]):
            self.datos[k].append(v)
            if len(self.datos[k]) > 60: self.datos[k].pop(0)

    def obtener_procesos(self):
        res = []
        mem_t = 0
        if not hasattr(self, '_proc_cache'):
            self._proc_cache = {}
            
        # Limpiar caché de procesos que han finalizado
        try:
            active_pids = set(psutil.pids())
            self._proc_cache = {pid: proc for pid, proc in self._proc_cache.items() if pid in active_pids}
        except:
            active_pids = []
            
        for pid in active_pids:
            try:
                if pid not in self._proc_cache:
                    self._proc_cache[pid] = psutil.Process(pid)
                p = self._proc_cache[pid]
                
                cpu_p = p.cpu_percent()
                mem_info = p.memory_info()
                m = mem_info.rss if mem_info else 0
                mem_t += m
                
                res.append({
                    'pid': pid, 'nombre': p.name(), 'usuario': p.username() or "Sistema",
                    'memoria': self._format_bytes(m), 'estado': p.status(),
                    'cpu': f"{cpu_p:.1f}%", 'cpu_raw': cpu_p, 'mem_raw': m
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except:
                pass
                
        res.sort(key=lambda x: x['cpu_raw'], reverse=True)
        return res, psutil.cpu_percent(), self._format_bytes(mem_t)

    def ejecutar_ping(self, host, count):
        try:
            flag = '-n' if platform.system() == "Windows" else '-c'
            # Desinfectar host mínimamente
            safe_host = "".join(c for c in host if c.isalnum() or c in ".-")
            return subprocess.check_output(['ping', flag, str(count), safe_host], stderr=subprocess.STDOUT, text=True)
        except subprocess.CalledProcessError as e:
            return f"Error en ping: {e.output}"
        except: return "No se pudo realizar el ping."

    def info_red_completa(self):
        dat = NetworkLogic.get_network_details()
        dat['public_ip'] = NetworkLogic.get_public_ip()
        dat['internet'] = "Conectado" if NetworkLogic.check_internet() else "Sin conexión"
        return dat

    def obtener_entorno(self):
        return os.environ.items()

    def obtener_seguridad(self):
        return {
            "puertos": SecurityLogic.get_open_ports(),
            "firewall": SecurityLogic.get_firewall_status(),
            "servicios": SecurityLogic.get_active_services()
        }

    def limpiar_temp(self):
        return SystemToolsLogic.limpiar_temp()

    def flush_dns(self):
        return SystemToolsLogic.flush_dns()

    def restart_shell(self):
        return SystemToolsLogic.restart_shell()

