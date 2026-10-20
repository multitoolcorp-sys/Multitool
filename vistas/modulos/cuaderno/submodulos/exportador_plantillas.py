import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGroupBox, QRadioButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class ExportadorPlantillasSubmodule(QWidget):
    """Submódulo 4: Centro de Exportación (PDF/CSV/HTML) & Catálogo de Plantillas Predefinidas"""
    def __init__(self, parent, context, colores, callbacks):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(20)

        # Header
        lbl_tit = QLabel("📤 CENTRO DE EXPORTACIÓN Y PLANTILLAS")
        lbl_tit.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tit)

        # ── Sección 1: Exportadores Unificados ──
        exp_box = QGroupBox("📄 Exportar Documento Actual")
        exp_box.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        exp_box.setStyleSheet(f"""
            QGroupBox {{
                background: {bg_sec};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                margin-top: 10px;
                padding: 15px;
                color: {acento};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }}
        """)
        e_lay = QHBoxLayout(exp_box)
        e_lay.setSpacing(15)

        btn_pdf = QPushButton("📕 Exportar a PDF\n(Orientación Horizontal)")
        btn_pdf.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pdf.setStyleSheet(f"""
            QPushButton {{
                background: rgba(239, 68, 68, 0.15);
                color: white; border: 1px solid #EF4444;
                border-radius: 10px; padding: 12px;
            }}
            QPushButton:hover {{ background: #EF4444; }}
        """)
        btn_pdf.clicked.connect(self.callbacks.get("exportar_pdf", lambda: None))
        e_lay.addWidget(btn_pdf)

        btn_csv = QPushButton("📊 Exportar a Excel CSV\n(Compatible UTF-8 BOM)")
        btn_csv.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_csv.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_csv.setStyleSheet(f"""
            QPushButton {{
                background: rgba(52, 211, 153, 0.15);
                color: white; border: 1px solid {exito};
                border-radius: 10px; padding: 12px;
            }}
            QPushButton:hover {{ background: {exito}; color: black; }}
        """)
        btn_csv.clicked.connect(self.callbacks.get("exportar_excel", lambda: None))
        e_lay.addWidget(btn_csv)

        btn_html = QPushButton("🌐 Exportar a HTML\n(Página Web Independiente)")
        btn_html.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_html.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_html.setStyleSheet(f"""
            QPushButton {{
                background: rgba(99, 102, 241, 0.15);
                color: white; border: 1px solid {acento};
                border-radius: 10px; padding: 12px;
            }}
            QPushButton:hover {{ background: {acento}; }}
        """)
        btn_html.clicked.connect(self.callbacks.get("exportar_html", lambda: None))
        e_lay.addWidget(btn_html)

        layout.addWidget(exp_box)

        # ── Sección 2: Catálogo de Plantillas Listas para Usar ──
        tpl_box = QGroupBox("✨ Catálogo de Plantillas Predefinidas")
        tpl_box.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        tpl_box.setStyleSheet(exp_box.styleSheet())
        t_lay = QVBoxLayout(tpl_box)
        t_lay.setSpacing(12)

        lbl_desc = QLabel("Haz clic en una plantilla para cargar una estructura lista en el cuaderno actual:")
        lbl_desc.setFont(QFont(self.font_family, 9))
        lbl_desc.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        t_lay.addWidget(lbl_desc)

        grid_tpl = QHBoxLayout()
        grid_tpl.setSpacing(12)

        btn_t1 = self._create_template_card("📈 Presupuesto Personal", "Ingresos, gastos y balance mensual automatizado", self._cargar_plantilla_presupuesto)
        btn_t2 = self._create_template_card("📅 Horario Semanal", "Planificador de clases, horarios y actividades", self._cargar_plantilla_horario)
        btn_t3 = self._create_template_card("📋 Plan de Proyecto", "Tareas, responsable, estado y entregables", self._cargar_plantilla_proyecto)
        btn_t4 = self._create_template_card("📦 Control Inventario", "Productos, stock, precio unitario y valor total", self._cargar_plantilla_inventario)

        grid_tpl.addWidget(btn_t1)
        grid_tpl.addWidget(btn_t2)
        grid_tpl.addWidget(btn_t3)
        grid_tpl.addWidget(btn_t4)

        t_lay.addLayout(grid_tpl)
        layout.addWidget(tpl_box, 1)

    def _create_template_card(self, title, desc, callback):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 10px;
                padding: 12px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            QFrame:hover {{
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
        lay = QVBoxLayout(frame)
        
        lbl_t = QLabel(title)
        lbl_t.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_t.setStyleSheet("color: white;")
        lay.addWidget(lbl_t)

        lbl_d = QLabel(desc)
        lbl_d.setFont(QFont(self.font_family, 8))
        lbl_d.setWordWrap(True)
        lbl_d.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        lay.addWidget(lbl_d, 1)

        btn = QPushButton("Cargar Plantilla")
        btn.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')};
                color: white; border-radius: 6px; padding: 6px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento', '#6366F1')}dd; }}
        """)
        btn.clicked.connect(callback)
        lay.addWidget(btn)

        return frame

    def _cargar_plantilla_presupuesto(self):
        headers = ["Categoría", "Descripción", "Presupuestado", "Real", "Diferencia"]
        rows = [
            ["Ingresos", "Sueldo Principal", "2500", "2500", "0"],
            ["Ingresos", "Ventas Extra", "300", "450", "150"],
            ["Gastos", "Alquiler / Vivienda", "800", "800", "0"],
            ["Gastos", "Servicios (Luz, Agua, Net)", "150", "140", "-10"],
            ["Gastos", "Comida & Supermercado", "400", "420", "20"],
            ["Gastos", "Entretenimiento", "100", "80", "-20"],
        ]
        self._aplicar_plantilla("Presupuesto Mensual", headers, rows)

    def _cargar_plantilla_horario(self):
        headers = ["Hora", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        rows = [
            ["08:00 - 09:30", "Matemáticas", "Física", "Matemáticas", "Programación", "Inglés"],
            ["09:30 - 11:00", "Programación", "Química", "Historia", "Física", "Algoritmos"],
            ["11:00 - 12:00", "RECESO", "RECESO", "RECESO", "RECESO", "RECESO"],
            ["12:00 - 13:30", "Bases de Datos", "Inglés", "Bases de Datos", "Estadística", "Proyecto"],
        ]
        self._aplicar_plantilla("Horario Semanal", headers, rows)

    def _cargar_plantilla_proyecto(self):
        headers = ["ID", "Tarea", "Responsable", "Prioridad", "Estado", "Fecha Límite"]
        rows = [
            ["T-01", "Diseño de Maqueta UI", "Ana", "Alta", "Completado", "2026-09-01"],
            ["T-02", "Desarrollo Backend", "Carlos", "Alta", "En Progreso", "2026-09-10"],
            ["T-03", "Pruebas de Calidad", "Luis", "Media", "Pendiente", "2026-09-15"],
            ["T-04", "Despliegue a Staging", "Ana", "Alta", "Pendiente", "2026-09-20"],
        ]
        self._aplicar_plantilla("Plan de Proyecto", headers, rows)

    def _cargar_plantilla_inventario(self):
        headers = ["Código", "Producto", "Categoría", "Stock", "Precio Unitario ($)", "Valor Total ($)"]
        rows = [
            ["P-101", "Laptop HP 15'", "Electrónica", "10", "650", "6500"],
            ["P-102", "Mouse Inalámbrico", "Accesorios", "45", "15", "675"],
            ["P-103", "Teclado Mecánico", "Accesorios", "20", "45", "900"],
            ["P-104", "Monitor 24' FHD", "Pantallas", "8", "140", "1120"],
        ]
        self._aplicar_plantilla("Inventario de Productos", headers, rows)

    def _aplicar_plantilla(self, nombre, headers, rows):
        if "cargar_plantilla_cb" in self.callbacks:
            self.callbacks["cargar_plantilla_cb"](nombre, headers, rows)
            if self.isVisible():
                QMessageBox.information(self, "Plantilla Cargada", f"¡Plantilla '{nombre}' cargada con éxito en la hoja de cálculo!")

    def actualizar_tema(self, colores):
        self.colores = colores
        bg_main = colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
