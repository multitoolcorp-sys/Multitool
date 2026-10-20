"""
tray_manager.py - Gestor del Icono y Menú Contextual en la Bandeja del Sistema (System Tray)
"""
import os
import psutil
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal


class TrayControlManager(QObject):
    """Administrador de la Bandeja de Sistema (System Tray)"""
    mostrar_ocultar_signal = pyqtSignal()
    bloquear_pin_signal = pyqtSignal()
    salir_signal = pyqtSignal()

    def __init__(self, parent_window=None, icon_path=None):
        super().__init__()
        self.parent_window = parent_window
        self.icon_path = icon_path

        self.tray_icon = QSystemTrayIcon(self)
        self.init_tray()

    def init_tray(self):
        if self.icon_path and os.path.exists(self.icon_path):
            self.tray_icon.setIcon(QIcon(self.icon_path))
        else:
            self.tray_icon.setIcon(QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ComputerIcon))

        self.tray_icon.setToolTip("MultiTool Suite OS")

        # Menú Contextual de Bandeja
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { 
                background-color: #1E1E2E; 
                color: #E2E8F0; 
                border: 1px solid rgba(255,255,255,0.15); 
                border-radius: 8px; 
                padding: 5px; 
            }
            QMenu::item { 
                background-color: transparent;
                padding: 8px 22px; 
                font-weight: 500; 
                font-size: 11px; 
                border-radius: 5px;
                color: #E2E8F0;
            }
            QMenu::item:selected { 
                background-color: #6366F1; 
                color: #FFFFFF !important; 
                font-weight: bold;
            }
            QMenu::item:disabled { 
                color: #64748B !important; 
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 0.08);
                margin: 4px 6px;
            }
        """)

        a_show = QAction("👁️ Mostrar / Ocultar MultiTool", menu)
        a_show.triggered.connect(self._on_toggle_visibility)
        menu.addAction(a_show)

        a_lock = QAction("🔒 Ocultar y Bloquear con PIN", menu)
        a_lock.triggered.connect(self._on_lock_pin)
        menu.addAction(a_lock)

        menu.addSeparator()

        a_metrics = QAction("📊 Ver Métricas CPU / RAM", menu)
        a_metrics.triggered.connect(self._mostrar_metricas_popup)
        menu.addAction(a_metrics)

        menu.addSeparator()

        a_exit = QAction("🚪 Salir de MultiTool", menu)
        a_exit.triggered.connect(self._on_exit)
        menu.addAction(a_exit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_toggle_visibility(self):
        self.mostrar_ocultar_signal.emit()

    def _on_lock_pin(self):
        self.bloquear_pin_signal.emit()

    def _on_exit(self):
        self.salir_signal.emit()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger or reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.mostrar_ocultar_signal.emit()

    def _mostrar_metricas_popup(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            self.tray_icon.showMessage(
                "Métricas de Sistema",
                f"🧠 CPU: {cpu:.1f}%\n💾 RAM: {ram:.1f}%",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
        except Exception: pass
