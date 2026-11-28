"""Mixin para monitoreo de memoria RAM y liberación manual en BaseAppGUI."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QPushButton


class ResourceMonitorMixin:
    """Provee monitoreo periódico de RSS y recolección manual de basura."""

    def _setup_ram_monitor(self):
        """Inicializa el widget y timer para monitorear el consumo de RAM en tiempo real insertándolo en la barra de estado."""
        parent_w = getattr(self, "barra_estado_frame", self)
        self.btn_ram_monitor = QPushButton("⚡ RAM: -- MB", parent_w)
        self.btn_ram_monitor.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ram_monitor.setToolTip("Consumo de RAM en tiempo real. Haz clic para optimizar y liberar memoria (Garbage Collector).")
        self.btn_ram_monitor.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(99, 102, 241, 0.12);
                color: {self.COLORES.get('acento', '#6366F1')};
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 4px;
                padding: 2px 8px;
                font-family: Consolas, monospace;
                font-size: 10px;
                font-weight: bold;
                margin-left: 6px;
            }}
            QPushButton:hover {{
                background-color: {self.COLORES.get('acento', '#6366F1')};
                color: #FFFFFF;
            }}
        """)
        self.btn_ram_monitor.clicked.connect(self._liberar_memoria_manual)

        if hasattr(self, "barra_estado_layout") and self.barra_estado_layout:
            self.barra_estado_layout.addWidget(self.btn_ram_monitor)
        elif hasattr(self, "barra_layout") and self.barra_layout:
            self.barra_layout.addWidget(self.btn_ram_monitor)

        self._ram_timer = QTimer(self)
        self._ram_timer.timeout.connect(self._actualizar_ram_display)
        self._ram_timer.start(2000)
        self._actualizar_ram_display()

    def _get_ram_usage_mb(self):
        """Retorna el consumo actual de memoria RAM del proceso en MB usando psutil o fallbacks."""
        try:
            import os
            import psutil
            proc = psutil.Process(os.getpid())
            mem_bytes = proc.memory_info().rss
            return round(mem_bytes / (1024 * 1024), 1)
        except Exception:
            try:
                import resource
                mem_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                return round(mem_kb / 1024, 1)
            except Exception:
                return 0.0

    def _actualizar_ram_display(self):
        ram_mb = self._get_ram_usage_mb()
        if hasattr(self, "btn_ram_monitor") and self.btn_ram_monitor:
            if ram_mb > 0:
                self.btn_ram_monitor.setText(f"⚡ RAM: {ram_mb} MB")
            else:
                self.btn_ram_monitor.setText("⚡ RAM: OK")

    def _liberar_memoria_manual(self):
        """Ejecuta una recolección forzada de basura para liberar RAM de módulos en reposo."""
        import gc
        antes = self._get_ram_usage_mb()
        gc.collect()
        self._actualizar_ram_display()
        despues = self._get_ram_usage_mb()
        ahorro = max(0, round(antes - despues, 1))
        msg = (
            f"🧹 Memoria optimizada con éxito. RAM actual: {despues} MB ({ahorro} MB liberados)"
            if ahorro > 0
            else f"🧹 Memoria optimizada. RAM actual: {despues} MB"
        )
        self.set_status(msg)
