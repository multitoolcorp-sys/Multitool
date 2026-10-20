import os
import subprocess
import socket


class ControladorAvanzado:

    def __init__(self, vista):
        self.vista = vista


    def cargar_entorno(self):

        texto = ""

        for k, v in os.environ.items():
            texto += f"{k} = {v}\n"

        self.vista.txt_env.setPlainText(texto)


    def cargar_red_avanzada(self):

        texto = ""

        try:

            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)

            texto += f"Host: {hostname}\n"
            texto += f"IP: {ip}\n\n"

            res = subprocess.check_output(
                "ipconfig",
                shell=True,
                text=True
            )

            texto += res

        except Exception as e:
            texto = str(e)

        self.vista.txt_red_info.setPlainText(texto)


    def ejecutar_diagnostico(self):
        """Ejecuta el diagnóstico y escribe el resultado en la vista (solo hilo principal)."""
        resultado = self.obtener_resultado_diagnostico()
        self.vista.txt_ping_res.setPlainText(resultado)

    def obtener_resultado_diagnostico(self) -> str:
        """
        Ejecuta el comando y retorna el resultado completo como texto.
        Seguro para llamar desde un hilo secundario (no toca widgets Qt).
        """
        host = self.vista.txt_ping_host.text().strip()
        tipo = self.vista.combo_diag.currentText()
        count = self.vista.spin_ping_count.value()

        if not host:
            return "Error: ingresa un host o IP antes de ejecutar."

        try:
            if tipo == "Ping":
                cmd = ["ping", host, "-n", str(count)] if os.name == 'nt' else ["ping", "-c", str(count), host]
            elif tipo == "Tracert":
                cmd = ["tracert", "-h", str(count), host] if os.name == 'nt' else ["traceroute", "-m", str(count), host]
            elif tipo == "NSLookup":
                cmd = ["nslookup", host]
            else:
                return f"Tipo desconocido: {tipo}"

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="cp850" if os.name == 'nt' else "utf-8",
                errors="replace",
                creationflags=0x08000000 if os.name == 'nt' else 0  # CREATE_NO_WINDOW en Windows
            )
            lineas = []
            for linea in proc.stdout:
                lineas.append(linea.rstrip())
            proc.wait(timeout=90)
            return "\n".join(lineas)

        except subprocess.TimeoutExpired:
            return f"Error: tiempo de espera agotado (90s) para '{host}'."
        except Exception as e:
            return f"Error inesperado: {e}"

    def ejecutar_diagnostico_streaming(self, callback_linea, callback_fin):
        """
        Versión streaming: llama callback_linea(str) por cada línea en tiempo real.
        callback_fin() se llama al terminar.
        Diseñado para ejecutarse en un hilo secundario.
        """
        host = self.vista.txt_ping_host.text().strip()
        tipo = self.vista.combo_diag.currentText()
        count = self.vista.spin_ping_count.value()

        if not host:
            callback_linea("Error: ingresa un host o IP antes de ejecutar.")
            callback_fin()
            return

        try:
            if tipo == "Ping":
                cmd = ["ping", host, "-n", str(count)] if os.name == 'nt' else ["ping", "-c", str(count), host]
            elif tipo == "Tracert":
                cmd = ["tracert", "-h", str(count), host] if os.name == 'nt' else ["traceroute", "-m", str(count), host]
            elif tipo == "NSLookup":
                cmd = ["nslookup", host]
            else:
                callback_linea(f"Tipo desconocido: {tipo}")
                callback_fin()
                return

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="cp850" if os.name == 'nt' else "utf-8",
                errors="replace",
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            for linea in proc.stdout:
                callback_linea(linea.rstrip())
            proc.wait(timeout=90)

        except subprocess.TimeoutExpired:
            callback_linea(f"\n[Tiempo agotado — 90s para '{host}']")
        except Exception as e:
            callback_linea(f"\n[Error: {e}]")
        finally:
            callback_fin()


    def escanear_seguridad(self):

        try:

            firewall = subprocess.check_output(
                "netsh advfirewall show allprofiles",
                shell=True,
                text=True
            )

            self.vista.lbl_fw_status.setText("Estado del Firewall: Detectado")
            self.vista.txt_sec_info.setPlainText(firewall)

        except Exception as e:

            self.vista.txt_sec_info.setPlainText(str(e))


    def limpiar_temp(self):

        temp = os.getenv("TEMP")

        eliminado = 0

        for f in os.listdir(temp):

            try:
                os.remove(os.path.join(temp, f))
                eliminado += 1
            except:
                pass

        self.vista.txt_tools_info.setPlainText(
            f"Archivos temporales eliminados: {eliminado}"
        )


    def flush_dns(self):

        try:

            resultado = subprocess.check_output(
                "ipconfig /flushdns",
                shell=True,
                text=True
            )

            self.vista.txt_tools_info.setPlainText(resultado)

        except Exception as e:

            self.vista.txt_tools_info.setPlainText(str(e))


    def restart_shell(self):

        try:

            subprocess.call("taskkill /f /im explorer.exe", shell=True)
            subprocess.Popen("explorer")

            self.vista.txt_tools_info.setPlainText(
                "Explorador reiniciado correctamente."
            )

        except Exception as e:

            self.vista.txt_tools_info.setPlainText(str(e))
