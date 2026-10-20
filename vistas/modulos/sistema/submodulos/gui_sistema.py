import platform
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtGui import QFont

from .tab_resumen import TabResumen
from .tab_monitoreo import TabMonitoreo
from .tab_procesos import TabProcesos
from .tab_startup import TabStartup
from .tab_limpiador import TabLimpiador
from .tab_antivirus import TabAntivirus
from .tab_remote import TabRemote
from .tab_avanzado import TabAvanzado
from .tab_seguridad import TabSeguridad


class SistemaGUI(QWidget):
    """Interfaz principal del módulo de Sistema"""
    def __init__(self, parent, colores, pyqt_available, gputil_available, matplotlib_available, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.gputil_available = gputil_available
        self.matplotlib_available = matplotlib_available
        self.context = getattr(parent, "context", None)
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.inicializar_ui()

    def inicializar_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Notebook / Tabs
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont(self.font_family, 10))
        self.tabs.setStyleSheet(f"""
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
        
        # Submódulos dinámicos desde config.json
        from pathlib import Path
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent.parent
        extra_kwargs = {
            "callbacks": self.callbacks,
            "pyqt_available": self.gputil_available,
            "gputil_available": self.gputil_available,
            "matplotlib_available": self.matplotlib_available
        }
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores, extra_kwargs)

        if self.tabs.count() == 0:
            self.tab_resumen = TabResumen(self.tabs, self.colores, self.callbacks)
            self.tab_monitoreo = TabMonitoreo(self.tabs, self.colores, self.callbacks)
            self.tab_procesos = TabProcesos(self.tabs, self.colores, self.callbacks)
            self.tab_startup = TabStartup(self.tabs, self.colores, self.callbacks)
            self.tab_limpiador = TabLimpiador(self.tabs, self.colores, self.callbacks)
            self.tab_seguridad = TabSeguridad(self.tabs, self.colores, self.callbacks)
            self.tab_antivirus = TabAntivirus(self.tabs, self.colores, self.callbacks, self.context)
            self.tab_remote = TabRemote(self.tabs, self.colores, self.callbacks)
            self.tab_avanzado = TabAvanzado(self.tabs, self.colores, self.callbacks)
            
            self.tabs.addTab(self.tab_resumen, "📊 Resumen")
            self.tabs.addTab(self.tab_monitoreo, "📈 Monitor")
            self.tabs.addTab(self.tab_procesos, "⚡ Procesos")
            self.tabs.addTab(self.tab_startup, "🚀 Inicio")
            self.tabs.addTab(self.tab_limpiador, "🧹 Limpiador")
            self.tabs.addTab(self.tab_seguridad, "🔌 Dispositivos")
            self.tabs.addTab(self.tab_antivirus, "🛡️ Antivirus")
            self.tabs.addTab(self.tab_remote, "🌐 Red")
            self.tabs.addTab(self.tab_avanzado, "🛠️ Avanzado")
        else:
            self.tab_resumen = self.submod_instances.get("TabResumen") or self.submod_instances.get("tabresumen")
            self.tab_monitoreo = self.submod_instances.get("TabMonitoreo") or self.submod_instances.get("tabmonitoreo")
            self.tab_procesos = self.submod_instances.get("TabProcesos") or self.submod_instances.get("tabprocesos")
            self.tab_startup = self.submod_instances.get("TabStartup") or self.submod_instances.get("tabstartup")
            self.tab_limpiador = self.submod_instances.get("TabLimpiador") or self.submod_instances.get("tablimpiador")
            self.tab_seguridad = self.submod_instances.get("TabSeguridad") or self.submod_instances.get("tabseguridad")
            self.tab_antivirus = self.submod_instances.get("TabAntivirus") or self.submod_instances.get("tabantivirus")
            self.tab_remote = self.submod_instances.get("TabRemote") or self.submod_instances.get("tabremote")
            self.tab_avanzado = self.submod_instances.get("TabAvanzado") or self.submod_instances.get("tabavanzado")
        
        self.main_layout.addWidget(self.tabs)

    # Métodos Proxy para compatibilidad con controlador sistema.py
    def rellenar_grid_info(self, info):
        self.tab_resumen.rellenar_grid_info(info)

    def actualizar_dashboard(self, data):
        self.tab_resumen.actualizar_dashboard(data)

    @property
    def lbl_cpu_val(self): return self.tab_monitoreo.lbl_cpu_val
    @property
    def bar_cpu(self): return self.tab_monitoreo.bar_cpu
    @property
    def lbl_mem_val(self): return self.tab_monitoreo.lbl_mem_val
    @property
    def bar_mem(self): return self.tab_monitoreo.bar_mem
    @property
    def lbl_disk_val(self): return self.tab_monitoreo.lbl_disk_val
    @property
    def bar_disk(self): return self.tab_monitoreo.bar_disk
    @property
    def layout_grafico(self): return self.tab_monitoreo.layout_grafico
    @property
    def btn_iniciar(self): return self.tab_monitoreo.btn_iniciar
    @property
    def btn_detener(self): return self.tab_monitoreo.btn_detener
    @property
    def lbl_net_up(self): return self.tab_monitoreo.lbl_net_up
    @property
    def lbl_net_down(self): return self.tab_monitoreo.lbl_net_down
    @property
    def lbl_uptime(self): return self.tab_monitoreo.lbl_uptime
    @property
    def txt_top_procs(self): return self.tab_monitoreo.txt_top_procs
    @property
    def txt_proc_search(self): return self.tab_procesos.txt_proc_search
    @property
    def table_procs(self): return self.tab_procesos.table_procs
    @property
    def txt_env(self): return self.tab_avanzado.txt_env
    @property
    def lbl_red_info(self): return self.tab_avanzado.lbl_red_info
    @property
    def txt_ping_host(self): return self.tab_avanzado.txt_ping_host
    @property
    def txt_ping_res(self): return self.tab_avanzado.txt_ping_res
    @property
    def txt_sec_info(self): return self.tab_seguridad.txt_sec_info
    @property
    def lbl_fw_status(self): return self.tab_seguridad.lbl_fw_status
