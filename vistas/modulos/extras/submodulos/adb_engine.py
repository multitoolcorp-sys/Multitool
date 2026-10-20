import os
import sys
import subprocess
import string
import platform
from pathlib import Path

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class ADBEngine:
    """Motor de gestión para Android Debug Bridge (ADB) y Scrcpy"""
    @staticmethod
    def buscar_adb():
        rutas_comunes = [
            str(Path.home() / "Documents" / "Multitool" / "tools" / "adb" / "platform-tools" / "adb.exe"),
            "adb",
            r"C:\platform-tools\adb.exe",
            r"C:\adb\adb.exe",
            r"C:\scrcpy\adb.exe",
            os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe")
        ]
        for r in rutas_comunes:
            try:
                res = subprocess.run([r, "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2, creationflags=CREATE_NO_WINDOW)
                if res.returncode == 0:
                    return r
            except Exception:
                continue
        return None

    @staticmethod
    def buscar_scrcpy():
        rutas_comunes = [
            str(Path.home() / "Documents" / "Multitool" / "tools" / "scrcpy" / "scrcpy-win64-v2.4" / "scrcpy.exe"),
            str(Path.home() / "Documents" / "Multitool" / "tools" / "scrcpy" / "scrcpy.exe"),
            "scrcpy",
            r"C:\scrcpy\scrcpy.exe",
            r"C:\Program Files\scrcpy\scrcpy.exe"
        ]
        for r in rutas_comunes:
            try:
                res = subprocess.run([r, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2, creationflags=CREATE_NO_WINDOW)
                if res.returncode == 0:
                    return r
            except Exception:
                continue
        return None

    @staticmethod
    def listar_dispositivos(adb_bin="adb"):
        dispositivos = []
        try:
            res = subprocess.run([adb_bin, "devices", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3, creationflags=CREATE_NO_WINDOW)
            lines = res.stdout.strip().split("\n")
            for line in lines[1:]:
                line_str = line.strip()
                if not line_str:
                    continue
                parts = line_str.split()
                if len(parts) >= 2:
                    dev_id = parts[0]
                    state = parts[1]  # "device", "unauthorized", "offline"
                    model = "Dispositivo Android"
                    for p in parts:
                        if p.startswith("model:"):
                            model = p.split(":")[1].replace("_", " ")
                    
                    if (model == "Dispositivo Android" or not model) and state == "device":
                        try:
                            m_res = subprocess.run([adb_bin, "-s", dev_id, "shell", "getprop", "ro.product.model"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2, creationflags=CREATE_NO_WINDOW)
                            m_out = m_res.stdout.strip()
                            if m_out:
                                model = m_out
                        except Exception:
                            pass

                    dispositivos.append({"id": dev_id, "model": model, "state": state, "raw": line_str})
        except Exception:
            pass
        return dispositivos

    @staticmethod
    def detectar_instancia_movil(adb_bin="adb"):
        """
        Detecta si existe una instancia de dispositivo móvil conectado al sistema:
        1. Mediante almacenamiento móvil MTP / WPD en Windows (Shell.Application NameSpace 17)
        2. Mediante ADB si hay un dispositivo conectado
        Retorna un dict con la información del teléfono y almacenamiento.
        """
        info = {
            "conectado": False,
            "nombre": "Ningún celular detectado",
            "almacenamiento": "",
            "tipo": "",
            "id": "virtual",
            "estado": "desconectado"
        }

        # 1. Comprobar instancia de almacenamiento móvil MTP / WPD en Windows
        if platform.system() == "Windows":
            try:
                import win32com.client
                shell = win32com.client.Dispatch("Shell.Application")
                ns = shell.NameSpace(17)
                if ns:
                    user_home = os.path.expanduser("~").lower()
                    ignorar = {"objetos 3d", "imágenes", "imagenes", "música", "musica", "escritorio", "documentos", "vídeos", "videos", "descargas", "papelera de reciclaje", "red"}
                    for item in ns.Items():
                        name = item.Name.strip()
                        path = str(item.Path).strip() if item.Path else ""
                        if name.lower() in ignorar or path.lower().startswith(user_home):
                            continue
                        is_drive = len(path) >= 2 and path[0] in string.ascii_letters and path[1] == ':'
                        if is_drive:
                            continue
                        
                        info["conectado"] = True
                        info["nombre"] = name
                        info["tipo"] = "Almacenamiento Móvil (USB / MTP)"
                        info["estado"] = "conectado"
                        if item.IsFolder:
                            try:
                                f = item.GetFolder
                                if f:
                                    subs = [s.Name.strip() for s in f.Items()]
                                    if subs:
                                        info["almacenamiento"] = ", ".join(subs)
                            except Exception:
                                pass
                        break
            except Exception:
                pass

        # 2. Comprobar ADB
        try:
            devs = ADBEngine.listar_dispositivos(adb_bin)
            if devs:
                primer = devs[0]
                info["conectado"] = True
                if not info["nombre"] or info["nombre"] == "Ningún celular detectado":
                    info["nombre"] = primer["model"]
                info["id"] = primer["id"]
                info["estado"] = "listo" if primer["state"] == "device" else "pendiente"
                info["tipo"] = "ADB (Depuración USB)" if not info["tipo"] else f"{info['tipo']} + ADB"
        except Exception:
            pass

        return info

    @staticmethod
    def enviar_tap(adb_bin, dev_id, x, y):
        try:
            res = subprocess.run([adb_bin, "-s", dev_id, "shell", "input", "tap", str(int(x)), str(int(y))], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3, creationflags=CREATE_NO_WINDOW)
            return "SecurityException" not in (res.stderr or "")
        except Exception:
            return False

    @staticmethod
    def enviar_swipe(adb_bin, dev_id, x1, y1, x2, y2, duracion_ms=300):
        try:
            res = subprocess.run([adb_bin, "-s", dev_id, "shell", "input", "swipe", str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(int(duracion_ms))], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3, creationflags=CREATE_NO_WINDOW)
            return "SecurityException" not in (res.stderr or "")
        except Exception:
            return False

    @staticmethod
    def enviar_tecla(adb_bin, dev_id, keycode):
        try:
            res = subprocess.run([adb_bin, "-s", dev_id, "shell", "input", "keyevent", str(keycode)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3, creationflags=CREATE_NO_WINDOW)
            return "SecurityException" not in (res.stderr or "")
        except Exception:
            return False

    @staticmethod
    def capturar_pantalla(adb_bin, dev_id, ruta_guardar):
        try:
            res = subprocess.run([adb_bin, "-s", dev_id, "exec-out", "screencap", "-p"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            if res.returncode == 0 and res.stdout:
                with open(ruta_guardar, "wb") as f:
                    f.write(res.stdout)
                return True
        except Exception:
            pass
        return False
