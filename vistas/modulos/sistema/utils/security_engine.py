import os
import psutil
import hashlib
import platform
import time
import threading

# Importar WMI solo en Windows para monitoreo USB
WMI_AVAILABLE = False
if platform.system() == "Windows":
    try:
        import wmi
        WMI_AVAILABLE = True
    except ImportError: pass

class UniversalSecurityEngine:
    """Motor de seguridad avanzado para Windows, Linux y macOS"""
    def __init__(self):
        self.malware_names = ["xmrig", "minerd", "nicehash", "keylogger", "mimikatz", "psexec"]
        
    def escanear_software(self):
        findings = []
        # Escaneo de procesos (Universal con psutil)
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                pinfo = proc.info
                name = str(pinfo['name']).lower()
                exe = pinfo.get('exe')
                
                # Check lista negra
                if any(m in name for m in self.malware_names):
                    findings.append({
                        "tipo": "Malware",
                        "cat": "Firma Detectada",
                        "det": f"Proceso: {name} (PID: {pinfo['pid']})",
                        "nivel": "CRÍTICO"
                    })
                
                # Check rutas temporales
                if exe:
                    path_low = str(exe).lower()
                    if any(temp in path_low for temp in ["/tmp/", "/temp/", "appdata/local/temp"]):
                        findings.append({
                            "tipo": "Amenaza",
                            "cat": "Ejecución Temporal",
                            "det": f"Binario en carpeta temporal: {name}",
                            "nivel": "ALTO"
                        })
            except: continue
        return findings

    def escanear_persistencia(self):
        """Busca programas que se inician automáticamente de forma sospechosa"""
        findings = []
        system = platform.system()
        
        if system == "Windows":
            # REVISAR REGISTRO
            try:
                import winreg
                keys = [
                    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")
                ]
                for hive, path in keys:
                    try:
                        k = winreg.OpenKey(hive, path)
                        for i in range(winreg.QueryInfoKey(k)[1]):
                            findings.append({"tipo": "Inicio", "cat": "Registro", "det": f"Autorun: {winreg.EnumValue(k, i)[0]}", "nivel": "BAJO"})
                    except: continue
            except: pass
            
        elif system in ["Linux", "Darwin"]:
            # REVISAR CARPETAS DE INICIO
            check_paths = ["~/.config/autostart", "/etc/init.d", "~/Library/LaunchAgents"]
            for p in check_paths:
                full_p = os.path.expanduser(p)
                if os.path.exists(full_p):
                    try:
                        items = os.listdir(full_p)
                        for item in items:
                            findings.append({"tipo": "Inicio", "cat": "Script/Config", "det": f"Encontrado en {p}: {item}", "nivel": "BAJO"})
                    except: continue
        return findings

    def monitor_usb(self, callback):
        """Monitoreo de Hardware (USB Connect)"""
        system = platform.system()
        if system == "Windows" and WMI_AVAILABLE:
            def _win_usb():
                c = wmi.WMI()
                watcher = c.watch_for(notification_type="Creation", wmi_class="Win32_USBControllerDevice")
                while True:
                    try: watcher(); callback("Windows")
                    except: break
            threading.Thread(target=_win_usb, daemon=True).start()
        
        elif system == "Linux":
            def _linux_usb():
                last_devs = set(os.listdir('/dev'))
                while True:
                    time.sleep(2)
                    curr_devs = set(os.listdir('/dev'))
                    if curr_devs - last_devs: callback("Linux")
                    last_devs = curr_devs
            threading.Thread(target=_linux_usb, daemon=True).start()
            
        elif system == "Darwin":
            def _mac_usb():
                while True:
                    time.sleep(3)
                    # Simple check via system_profiler
                    try:
                        subprocess.check_output(['system_profiler', 'SPUSBDataType'])
                        # Notificar cambio es mas complejo en macOS sin libs extras, pero al menos intentamos
                    except: pass
            threading.Thread(target=_mac_usb, daemon=True).start()

    @staticmethod
    def escanear_archivo_downloader(file_path):
        """Firma básica para downloader.py"""
        if not os.path.exists(file_path): return []
        threats = []
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".exe", ".bat", ".vbs", ".sh", ".ps1"]:
            threats.append(f"Archivo ejecutable: {os.path.basename(file_path)}")
        if file_path.count(".") > 1:
            threats.append("Doble extensión sospechosa")
        return threats
