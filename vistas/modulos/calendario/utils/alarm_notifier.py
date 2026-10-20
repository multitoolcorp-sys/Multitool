import datetime
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

class AlarmNotifier(QObject):
    """Notificador en segundo plano para alertas de recordatorios en la hora exacta"""
    alerta_disparada = pyqtSignal(dict)

    def __init__(self, calendar_manager, colores, parent=None):
        super().__init__(parent)
        self.manager = calendar_manager
        self.colores = colores
        self.notificados_hoy = set()
        
        # Timer de verificación cada 20 segundos
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._verificar_alarmas)
        self.timer.start(20000)

    def _verificar_alarmas(self):
        ahora = datetime.datetime.now()
        fecha_str = ahora.strftime("%Y-%m-%d")
        hora_str = ahora.strftime("%H:%M")
        
        # Obtener todos los recordatorios del día
        recs = self.manager.get_recordatorios_por_fecha(fecha_str)
        for r in recs:
            r_id = r.get("id")
            r_hora = r.get("hora", "00:00")
            
            # Si coincide la hora exacta y no ha sido notificado aún en esta sesión
            clave_notif = f"{fecha_str}_{r_id}_{r_hora}"
            if r_hora == hora_str and clave_notif not in self.notificados_hoy:
                self.notificados_hoy.add(clave_notif)
                self.alerta_disparada.emit(r)
                self._mostrar_popup(r)

    def _mostrar_popup(self, recordatorio):
        titulo = recordatorio.get("titulo", "Recordatorio")
        desc = recordatorio.get("descripcion", "")
        hora = recordatorio.get("hora", "")
        cat = recordatorio.get("categoria", "General")

        msg = QMessageBox()
        msg.setWindowTitle("🔔 RECORDATORIO DE AGENDA")
        msg.setText(f"<b>[{hora}] {titulo}</b> ({cat})")
        if desc:
            msg.setInformativeText(desc)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
            }}
            QLabel {{ color: white; font-size: 11px; }}
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white; border-radius: 6px; padding: 6px 14px; font-weight: bold;
            }}
        """)
        msg.exec()
