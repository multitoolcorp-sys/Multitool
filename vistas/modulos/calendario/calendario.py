import datetime
import platform
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QMessageBox, QFileDialog, QApplication
from PyQt6.QtGui import QFont

from .submodulos.gui_calendario import CalendarioGUI
from .submodulos.vista_semanal import VistaSemanalSubmodule
from .submodulos.planificador_anual import PlanificadorAnual
from .submodulos.estadisticas_agenda import EstadisticasAgenda
from .utils.calendar_manager import CalendarManager
from .utils.alarm_notifier import AlarmNotifier

class TabCalendario(QWidget):
    """Módulo Principal de Agenda y Calendario estructurado en Submódulos estilo TabCuenta"""
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.usuario = getattr(context, "usuario", "Usuario")
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.colores = getattr(context.app, "COLORES", {
            "bg_principal": "#121218",
            "bg_secundario": "#1E1E2E",
            "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2",
            "fg_secundario": "#AAB0B8",
            "acento": "#6366F1",
            "acento_hover": "#818CF8",
            "error": "#F87171",
            "exito": "#34D399",
            "advertencia": "#FBBF24"
        })
        
        # Inicializar Manager de Lógica
        self.manager = CalendarManager(self.ruta_usuario / "recordatorios")
        
        # Inicializar Notificador de Alarmas en Segundo Plano
        self.alarm_notifier = AlarmNotifier(self.manager, self.colores, self)
        
        # Callbacks para los Submódulos
        self.callbacks = {
            "mes_anterior": self.mes_anterior,
            "mes_siguiente": self.mes_siguiente,
            "ir_a_hoy": self.ir_a_hoy,
            "ver_detalle": self.ver_detalle,
            "añadir_recordatorio": self.añadir_recordatorio,
            "eliminar": self.eliminar_recordatorio,
            "guardar": self.guardar_recordatorio,
            "exportar": self.exportar_recordatorios,
            "get_cat_color": self.get_cat_color,
            "ventana_formulario": self.ventana_formulario,
            "ir_a_fecha": self.ir_a_fecha
        }
        
        self.inicializar_ui()
        self.refrescar()

    def inicializar_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # TabWidget Principal del Módulo Calendario
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont(self.font_family, 9))
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['acento']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)

        # Submódulo 1: Vista Mensual & Agenda
        self.submod_calendario = CalendarioGUI(self, self.colores, self.callbacks)
        self.gui = self.submod_calendario  # Alias de compatibilidad

        # Submódulo 2: Vista Semanal & Bloques Horarios
        self.submod_semanal = VistaSemanalSubmodule(self, self.context, self.manager, self.colores, self.callbacks)

        # Submódulo 3: Planificador Anual & Objetivos del Año
        self.submod_anual = PlanificadorAnual(self, self.context, self.manager, self.colores, self.callbacks)

        # Submódulo 4: Análisis & Estadísticas de Productividad
        self.submod_stats = EstadisticasAgenda(self, self.context, self.manager, self.colores)

        self.tabs.addTab(self.submod_calendario, "📅 Vista Mensual & Agenda")
        self.tabs.addTab(self.submod_semanal, "📆 Vista Semanal")
        self.tabs.addTab(self.submod_anual, "🗓️ Planificador Anual & Objetivos")
        self.tabs.addTab(self.submod_stats, "📊 Análisis & Estadísticas")

        self.tabs.currentChanged.connect(self._on_tab_changed)

        main_lay.addWidget(self.tabs)

    def _on_tab_changed(self, index):
        self.refrescar()

    def refrescar(self):
        """Actualiza todos los submódulos activos"""
        # Actualizar Vista Mensual
        dias_info = self.manager.get_dias_mes(self.colores)
        self.submod_calendario.actualizar_calendario(
            self.manager.get_mes_nombre(), 
            self.manager.año, 
            dias_info
        )
        self.submod_calendario.actualizar_proximos(self.manager.get_proximos())

        # Actualizar Vista Semanal si existe
        if hasattr(self, 'submod_semanal'):
            self.submod_semanal.refrescar()

        # Actualizar Planificador Anual si existe
        if hasattr(self, 'submod_anual'):
            self.submod_anual.refrescar()

        # Actualizar Estadísticas si existe
        if hasattr(self, 'submod_stats'):
            self.submod_stats.refrescar()

    def mes_anterior(self):
        self.manager.navegar_mes(-1)
        self.refrescar()

    def mes_siguiente(self):
        self.manager.navegar_mes(1)
        self.refrescar()

    def ir_a_hoy(self):
        hoy = datetime.datetime.now()
        self.manager.año = hoy.year
        self.manager.mes = hoy.month
        self.refrescar()

    def ir_a_fecha(self, año, mes, dia=None):
        self.manager.año = int(año)
        self.manager.mes = int(mes)
        self.tabs.setCurrentIndex(0) # Cambiar a pestaña de Vista Mensual
        self.refrescar()
        if dia:
            self.ver_detalle(datetime.date(int(año), int(mes), int(dia)))

    def ver_detalle(self, fecha):
        if not fecha: return
        fecha_str = fecha.strftime("%Y-%m-%d")
        recs = self.manager.get_recordatorios_por_fecha(fecha_str)
        self.gui.ventana_detalle(fecha, recs)

    def añadir_recordatorio(self, fecha=None):
        if not fecha:
            fecha = datetime.date.today()
        self.gui.ventana_formulario("Añadir", fecha)

    def ventana_formulario(self, modo, fecha, r_obj=None):
        self.gui.ventana_formulario(modo, fecha, r_obj)

    def guardar_recordatorio(self, fecha_str, titulo, desc, r_id_old, categoria, hora, dialog, anual=False, alarma=True):
        if not titulo.strip():
            QMessageBox.warning(self, "Campo Requerido", "El título del recordatorio no puede estar vacío.")
            return
            
        try:
            datetime.datetime.strptime(hora, "%H:%M")
        except:
            QMessageBox.warning(self, "Formato Inválido", "Por favor ingresa un formato de hora válido (HH:MM).")
            return

        if r_id_old:
            self.manager.editar_recordatorio(fecha_str, r_id_old, titulo, desc, categoria, hora, anual, alarma)
        else:
            self.manager.añadir_recordatorio(fecha_str, titulo, desc, categoria, hora, anual, alarma)
            
        dialog.accept()
        self.refrescar()

    def eliminar_recordatorio(self, fecha, r_id, dialog_detalle):
        btn = QMessageBox.question(
            self, "Confirmar Eliminación", "¿Estás seguro de que deseas eliminar este recordatorio?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if btn == QMessageBox.StandardButton.Yes:
            fecha_str = fecha.strftime("%Y-%m-%d")
            if self.manager.eliminar_recordatorio(fecha_str, r_id):
                if dialog_detalle: dialog_detalle.close()
                self.refrescar()

    def get_cat_color(self, categoria):
        return self.manager.categorias.get(categoria, self.colores["fg_secundario"])

    def exportar_recordatorios(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Agenda", str(Path.home()), "Archivos iCalendar (*.ics);;Archivos CSV (*.csv);;Archivos de texto (*.txt)"
        )
        if not path: return
        
        try:
            if path.endswith(".ics"):
                self.manager.exportar_ical(path)
            elif path.endswith(".csv"):
                self.manager.exportar_csv(path)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"--- AGENDA PERSONAL DE {self.usuario.upper()} ---\n")
                    f.write(f"Documento generado el: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
                    f.write("=" * 40 + "\n\n")
                    
                    fechas = sorted(self.manager.recordatorios.keys())
                    for f_str in fechas:
                        f_dt = datetime.datetime.strptime(f_str, "%Y-%m-%d")
                        f.write(f"▶ {f_dt.strftime('%A, %d de %B de %Y').upper()}\n")
                        for r in self.manager.recordatorios[f_str]:
                            cat = r.get('categoria', 'General')
                            hora = r.get('hora', '00:00')
                            f.write(f"   [{hora}] ({cat}) {r['titulo']}\n")
                            if r['descripcion']:
                                f.write(f"   Nota: {r['descripcion']}\n")
                            f.write("   " + "-" * 30 + "\n")
                        f.write("\n")
            QMessageBox.information(self, "Exportación Exitosa", "Tu agenda ha sido exportada correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error Crítico", f"No se pudo completar la exportación: {e}")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['acento']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)
        for sub in [self.submod_calendario, getattr(self, "submod_semanal", None), self.submod_anual, self.submod_stats]:
            if sub and hasattr(sub, "actualizar_tema"):
                try:
                    sub.actualizar_tema(colores)
                except Exception as e:
                    print(f"Error actualizando tema en {sub}: {e}")
        self.refrescar()

    def cleanup(self):
        if hasattr(self, 'alarm_notifier') and hasattr(self.alarm_notifier, 'timer'):
            try:
                self.alarm_notifier.timer.stop()
            except Exception:
                pass
