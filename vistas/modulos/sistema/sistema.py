import os
import threading
import subprocess
import psutil
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QTableWidgetItem
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont

from .submodulos.gui_sistema import SistemaGUI
from .utils.system_manager import SystemManager, GPUTIL_AVAILABLE
import platform

# Detectar disponibilidad de Matplotlib
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class TabSistema(QWidget):
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        
        # Paleta de colores
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#1E1E1E", "bg_secundario": "#2D2D2D", "bg_terciario": "#3D3D3D",
            "fg_principal": "#E0E0E0", "fg_secundario": "#A0A0A0", "acento": "#4A86E8",
            "acento_hover": "#6366F1", "exito": "#43A047", "error": "#E53935", "advertencia": "#FDD835"
        })
        
        self.callbacks = {
            "cargar_panel_resumen": self.cargar_panel_resumen,
            "iniciar_monitoreo": self.iniciar_monitoreo,
            "detener_monitoreo": self.detener_monitoreo,
            "actualizar_procesos": self.actualizar_procesos,
            "finalizar_proceso": self.finalizar_proceso,
            "abrir_carpeta": self.abrir_carpeta_proyecto,
            "abrir_admin": self.abrir_admin_tareas,
            "abrir_cmd": self.abrir_cmd,
            "abrir_panel": self.abrir_panel_control,
            "abrir_dispositivos": self.abrir_admin_dispositivos,
            "abrir_discos": self.abrir_admin_discos,
            "abrir_redes": self.abrir_conexiones_red,
            "abrir_servicios": self.abrir_servicios,
            "abrir_regedit": self.abrir_regedit,
            "cargar_entorno": self.cargar_entorno,
            "cargar_red_avanzada": self.cargar_red_avanzada,
            "ejecutar_ping": self.ejecutar_ping,
            "escanear_seguridad": self.escanear_seguridad,
            "limpiar_temp": self.limpiar_temp,
            "flush_dns": self.flush_dns,
            "restart_shell": self.restart_shell
        }
        
        # Manager
        self.manager = SystemManager()
        self.manager.update_ui_signal.connect(self._real_update_ui)
        
        # GUI
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.gui = SistemaGUI(self, self.colores, True, GPUTIL_AVAILABLE, MATPLOTLIB_AVAILABLE, self.callbacks)
        self.main_layout.addWidget(self.gui)
        
        if MATPLOTLIB_AVAILABLE:
            self._setup_graficos()
            
        # Carga inicial
        # Cargamos únicamente el panel resumen para evitar lagueos al abrir la sección "Sistema"
        self.cargar_panel_resumen()
        
        # Conectar el cambio de pestaña interna para activar recursos on-demand
        self.gui.tabs.currentChanged.connect(self._on_subtab_cambiada)

    def _on_subtab_cambiada(self, index):
        nombre_tab = self.gui.tabs.tabText(index)
        if nombre_tab == "Procesos":
            self.actualizar_procesos()
            self.iniciar_monitoreo()
        else:
            self.detener_monitoreo()

    def _real_update_ui(self, d):
        # Actualizar Dashboard Resumen
        self.gui.actualizar_dashboard(d)
        
        # Enviar puntos al gráfico de procesos en tiempo real si está activo
        if hasattr(self.gui, 'tab_procesos') and hasattr(self.gui.tab_procesos, 'chart'):
            try:
                self.gui.tab_procesos.chart.add_points(d['cpu'], d['mem_p'])
            except:
                pass

        # Resto de la UI (Monitor)
        self.gui.lbl_cpu_val.setText(f"{d['cpu']:.1f}%")
        self.gui.bar_cpu.setValue(int(d['cpu']))
        self.gui.lbl_mem_val.setText(f"{d['mem_p']:.1f}%")
        self.gui.bar_mem.setValue(int(d['mem_p']))
        self.gui.lbl_disk_val.setText(f"{d['disk_p']:.1f}%")
        self.gui.bar_disk.setValue(int(d['disk_p']))
        
        self.gui.lbl_net_up.setText(d['net_up'])
        self.gui.lbl_net_down.setText(d['net_down'])
        self.gui.lbl_uptime.setText(f"Activo: {d['uptime']}")
        
        # Top procesos
        self.gui.txt_top_procs.setText("\n".join(d['top_procs']))
        
        if MATPLOTLIB_AVAILABLE and getattr(self, 'graph_active', False):
            self._draw_plots()

    def iniciar_monitoreo(self):
        self.manager.iniciar_monitoreo()
        self.gui.btn_iniciar.setEnabled(False)
        self.gui.btn_detener.setEnabled(True)
        self.graph_active = True

    def detener_monitoreo(self):
        self.manager.detener_monitoreo()
        self.gui.btn_iniciar.setEnabled(True)
        self.gui.btn_detener.setEnabled(False)
        self.graph_active = False

    def cargar_panel_resumen(self):
        def load():
            info = self.manager.obtener_total_info()
            # Inyectamos en la grid de la GUI
            # Necesitamos pasar los datos a la UI thread
            QTimer.singleShot(0, lambda: self.gui.rellenar_grid_info(info))
        threading.Thread(target=load, daemon=True).start()

    def actualizar_procesos(self):
        busq = self.gui.txt_proc_search.text().lower()
        def run():
            procs, _, _ = self.manager.obtener_procesos()
            QTimer.singleShot(0, lambda: self._update_procs_ui(procs, busq))
        threading.Thread(target=run, daemon=True).start()

    def _update_procs_ui(self, procs, busq):
        self.gui.table_procs.setRowCount(0)
        for p in procs:
            if not busq or busq in p['nombre'].lower() or busq in str(p['pid']):
                row = self.gui.table_procs.rowCount()
                self.gui.table_procs.insertRow(row)

                it_pid = QTableWidgetItem(str(p['pid']))
                it_pid.setFont(QFont("Consolas", 9))
                it_pid.setForeground(QColor("#AAB0B8"))
                self.gui.table_procs.setItem(row, 0, it_pid)

                it_name = QTableWidgetItem(p['nombre'])
                it_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                it_name.setForeground(QColor("#FFFFFF"))
                self.gui.table_procs.setItem(row, 1, it_name)

                it_user = QTableWidgetItem(p['usuario'])
                it_user.setFont(QFont("Segoe UI", 8))
                it_user.setForeground(QColor("#D1D5DB"))
                self.gui.table_procs.setItem(row, 2, it_user)

                it_cpu = QTableWidgetItem(p['cpu'])
                it_cpu.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
                cpu_num = p.get('cpu_raw', 0)
                if cpu_num >= 20.0:
                    it_cpu.setForeground(QColor("#F87171"))
                elif cpu_num >= 5.0:
                    it_cpu.setForeground(QColor("#FBBF24"))
                else:
                    it_cpu.setForeground(QColor("#34D399"))
                self.gui.table_procs.setItem(row, 3, it_cpu)

                it_mem = QTableWidgetItem(p['memoria'])
                it_mem.setFont(QFont("Consolas", 9))
                it_mem.setForeground(QColor("#60A5FA"))
                self.gui.table_procs.setItem(row, 4, it_mem)

                it_st = QTableWidgetItem(p['estado'])
                it_st.setFont(QFont("Segoe UI", 8))
                it_st.setForeground(QColor("#34D399") if p['estado'] in ('running', 'activo', 'active') else QColor("#9CA3AF"))
                self.gui.table_procs.setItem(row, 5, it_st)

    def finalizar_proceso(self):
        item = self.gui.table_procs.currentItem()
        if not item: return
        pid = int(self.gui.table_procs.item(item.row(), 0).text())
        btn = QMessageBox.question(self, "Confirmar", f"¿Matar proceso {pid}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if btn == QMessageBox.StandardButton.Yes:
            try:
                psutil.Process(pid).kill()
                self.actualizar_procesos()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Falla: {e}")

    def abrir_carpeta_proyecto(self):
        import platform
        if platform.system() == "Windows":
            os.startfile(os.getcwd())
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", os.getcwd()])
        else:
            subprocess.Popen(["xdg-open", os.getcwd()])

    def abrir_admin_tareas(self):
        import platform
        if platform.system() == "Windows":
            os.startfile("taskmgr.exe")
        else:
            QMessageBox.information(self, "Sistema", "Usa el Monitor de Actividad o el Monitor del Sistema de tu SO.")

    def abrir_cmd(self):
        import platform
        if platform.system() == "Windows":
            subprocess.Popen('start cmd', shell=True)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-a", "Terminal"])
        else:
            subprocess.Popen(["x-terminal-emulator"])

    def abrir_panel_control(self):
        sys = platform.system()
        if sys == "Windows": os.startfile("control.exe")
        elif sys == "Linux": subprocess.Popen(["gnome-control-center"])
        elif sys == "Darwin": subprocess.Popen(["open", "-b", "com.apple.systempreferences"])

    def abrir_admin_dispositivos(self):
        sys = platform.system()
        if sys == "Windows": os.startfile("devmgmt.msc")
        elif sys == "Linux": subprocess.Popen(["x-terminal-emulator", "-e", "lsusb; lspci; read"])
        elif sys == "Darwin": subprocess.Popen(["open", "/Applications/Utilities/System Information.app"])

    def abrir_admin_discos(self):
        sys = platform.system()
        if sys == "Windows": os.startfile("diskmgmt.msc")
        elif sys == "Linux": 
            # Intentar herramientas comunes de discos
            for cmd in ["gnome-disks", "gparted"]:
                try: 
                    subprocess.Popen([cmd])
                    break
                except: continue
        elif sys == "Darwin": subprocess.Popen(["open", "/Applications/Utilities/Disk Utility.app"])

    def abrir_conexiones_red(self):
        sys = platform.system()
        if sys == "Windows": os.startfile("ncpa.cpl")
        elif sys == "Linux": subprocess.Popen(["nm-connection-editor"])
        elif sys == "Darwin": subprocess.Popen(["open", "/System/Library/PreferencePanes/Network.prefPane"])

    def abrir_servicios(self):
        sys = platform.system()
        if sys == "Windows": os.startfile("services.msc")
        elif sys == "Linux": subprocess.Popen(["gnome-system-monitor", "-s"])
        elif sys == "Darwin": subprocess.Popen(["open", "/Applications/Utilities/Activity Monitor.app"])

    def abrir_regedit(self):
        sys = platform.system()
        if sys == "Windows": os.startfile("regedit.exe")
        elif sys == "Linux": subprocess.Popen(["dconf-editor"])
        elif sys == "Darwin": 
             # No hay regedit real, pero abrimos la carpeta de preferencias
             subprocess.Popen(["open", os.path.expanduser("~/Library/Preferences")])

    def cargar_entorno(self):
        self.gui.txt_env.clear()
        for k, v in self.manager.obtener_entorno():
            self.gui.txt_env.append(f"<b>{k}</b>: {v}")

    def cargar_red_avanzada(self):
        self.gui.lbl_red_info.setText("Cargando...")
        def run():
            d = self.manager.info_red_completa()
            txt = (f"<b>Hostname:</b> {d['hostname']}<br>"
                   f"<b>IP Local:</b> {d['local_ip']}<br>"
                   f"<b>IP Pública:</b> {d['public_ip']}<br>"
                   f"<b>Internet:</b> {d['internet']}")
            QTimer.singleShot(0, lambda: self.gui.lbl_red_info.setText(txt))
        threading.Thread(target=run, daemon=True).start()

    def ejecutar_ping(self):
        host = self.gui.txt_ping_host.text()
        self.gui.txt_ping_res.append(f"Pingeando {host}...")
        def run():
            res = self.manager.ejecutar_ping(host, 4)
            QTimer.singleShot(0, lambda: self.gui.txt_ping_res.append(res))
        threading.Thread(target=run, daemon=True).start()

    def escanear_seguridad(self):
        self.gui.txt_sec_info.clear()
        self.gui.txt_sec_info.append("Escaneando...")
        def run():
            sec = self.manager.obtener_seguridad()
            QTimer.singleShot(0, lambda: self._update_sec_ui(sec))
        threading.Thread(target=run, daemon=True).start()

    def _update_sec_ui(self, sec):
        self.gui.lbl_fw_status.setText(f"Firewall: {sec['firewall']}")
        self.gui.txt_sec_info.append("<b>Puertos Abiertos:</b>")
        for p in sec['puertos']:
            self.gui.txt_sec_info.append(f"Port: {p['port']} | PID: {p['pid']}")

    def limpiar_temp(self):
        cleaned = self.manager.limpiar_temp()
        if cleaned > 0:
            QMessageBox.information(self, "Limpieza", f"Se limpiaron {cleaned} archivos temporales.")
        else:
            QMessageBox.information(self, "Limpieza", "La carpeta temporal ya estaba limpia o los archivos están en uso.")

    def flush_dns(self):
        if self.manager.flush_dns():
            QMessageBox.information(self, "Red", "Caché DNS vaciado exitosamente.")
        else:
            QMessageBox.warning(self, "Error", "No se pudo vaciar la caché DNS (Se requieren permisos de administrador o SO no soportado).")

    def restart_shell(self):
        btn = QMessageBox.question(self, "Confirmar", f"¿Reiniciar la interfaz gráfica? (La pantalla parpadeará)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if btn == QMessageBox.StandardButton.Yes:
            self.manager.restart_shell()

    def _setup_graficos(self):
        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.canvas = FigureCanvas(self.fig)
        self.gui.layout_grafico.addWidget(self.canvas)
        self.fig.patch.set_facecolor(self.colores["bg_principal"])
        self._config_ax()
        self.graph_active = False

    def _config_ax(self):
        self.ax.set_facecolor(self.colores["bg_secundario"])
        self.ax.tick_params(colors=self.colores["fg_secundario"], labelsize=8)
        self.ax.set_ylim(0, 105)
        self.ax.grid(True, color="white", alpha=0.05, linestyle=":", linewidth=0.5)
        for spine in ["top", "right"]:
            self.ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            self.ax.spines[spine].set_color((1, 1, 1, 0.1))

    def _draw_plots(self):
        d = self.manager.datos
        if not d["cpu"]: return
        self.ax.clear()
        self._config_ax()
        
        x = list(range(len(d["cpu"])))
        self.ax.plot(x, d["cpu"], color=self.colores["acento"], label="CPU %", linewidth=1.8, antialiased=True)
        self.ax.plot(x, d["memoria"], color=self.colores["exito"], label="RAM %", linewidth=1.8, antialiased=True)
        
        self.ax.fill_between(x, d["cpu"], color=self.colores["acento"], alpha=0.15)
        self.ax.fill_between(x, d["memoria"], color=self.colores["exito"], alpha=0.10)
        
        self.ax.legend(loc="upper left", frameon=False, fontsize=8, labelcolor="white")
        self.canvas.draw()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.detener_monitoreo()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'gui') and hasattr(self.gui, 'tabs'):
            idx = self.gui.tabs.currentIndex()
            if self.gui.tabs.tabText(idx) == "Procesos":
                self.iniciar_monitoreo()

    def actualizar_tema(self, colores=None):
        """Actualiza la paleta de colores del módulo dinámicamente."""
        if colores:
            self.colores = colores
        self.setStyleSheet(f"background-color: {self.colores.get('bg_principal', '#1E1E1E')}; border: none;")
        if hasattr(self, 'gui') and hasattr(self.gui, 'tabs'):
            self.gui.tabs.setStyleSheet(f"""
                QTabWidget::pane {{ border: 0; background: {self.colores['bg_principal']}; }}
                QTabBar::tab {{ 
                    background: {self.colores['bg_secundario']}; 
                    color: {self.colores['fg_secundario']};
                    padding: 12px 18px;
                    border-bottom: 2px solid transparent;
                }}
                QTabBar::tab:hover {{ background: {self.colores['bg_terciario']}; }}
                QTabBar::tab:selected {{ 
                    background: {self.colores['bg_principal']}; 
                    color: {self.colores['acento']}; 
                    border-bottom: 2px solid {self.colores['acento']};
                    font-weight: bold;
                }}
            """)
