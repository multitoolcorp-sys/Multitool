"""
plantillas_notas.py - Submódulo de Biblioteca de Plantillas de Notas Predefinidas
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

PLANTILLAS_DISPONIBLES = [
    {
        "id": "minuta",
        "titulo": "📝 Minuta de Reunión",
        "descripcion": "Estructura formal para registrar asistentes, agenda, compromisos y acuerdos de reunión.",
        "categoria": "Trabajo",
        "html": """
            <h2>📝 Minuta de Reunión</h2>
            <p><b>Fecha:</b> DD/MM/AAAA | <b>Hora:</b> 00:00 AM</p>
            <p><b>Participantes:</b> Persona 1, Persona 2, Persona 3</p>
            <hr>
            <h3>📌 Agenda</h3>
            <ul>
                <li>Punto 1: Revisión de avances</li>
                <li>Punto 2: Discusión de requerimientos</li>
                <li>Punto 3: Asignación de tareas</li>
            </ul>
            <h3>✅ Acuerdos y Asignaciones</h3>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #2D2D3D; color: white;">
                    <th>Responsable</th>
                    <th>Tarea / Compromiso</th>
                    <th>Fecha Entrega</th>
                </tr>
                <tr>
                    <td>Juan Pérez</td>
                    <td>Preparar reporte mensual</td>
                    <td>Viernes</td>
                </tr>
            </table>
            <h3>💡 Notas Adicionales</h3>
            <p>Escribe aquí cualquier observación relevante...</p>
        """
    },
    {
        "id": "planificador",
        "titulo": "📅 Planificador Diario",
        "descripcion": "Organiza tus prioridades del día, tareas clave y reflexiones de cierre.",
        "categoria": "Productividad",
        "html": """
            <h2>📅 Planificador Diario</h2>
            <p><b>Fecha:</b> DD/MM/AAAA</p>
            <hr>
            <h3>🎯 3 Prioridades del Día</h3>
            <ol>
                <li><b>Prioridad 1:</b> Tarea principal urgente</li>
                <li><b>Prioridad 2:</b> Tarea secundaria</li>
                <li><b>Prioridad 3:</b> Tarea de seguimiento</li>
            </ol>
            <h3>📋 Lista de Tareas</h3>
            <ul>
                <li>[ ] Tarea de la mañana</li>
                <li>[ ] Tarea de la tarde</li>
                <li>[ ] Revisión de correos</li>
            </ul>
            <h3>✨ Reflexión de Cierre</h3>
            <p>¿Qué logré hoy? ¿Qué puedo mejorar mañana?</p>
        """
    },
    {
        "id": "brainstorming",
        "titulo": "💡 Lluvia de Ideas (Brainstorming)",
        "descripcion": "Lienzo estructurado para capturar ideas, evaluar pros/contras y definir soluciones.",
        "categoria": "Creatividad",
        "html": """
            <h2>💡 Sesión de Lluvia de Ideas</h2>
            <p><b>Objetivo / Problema a Resolver:</b> Describe el reto aquí...</p>
            <hr>
            <h3>🚀 Ideas Propuestas</h3>
            <ul>
                <li><b>Idea A:</b> Descripción rápida de la alternativa A</li>
                <li><b>Idea B:</b> Descripción rápida de la alternativa B</li>
                <li><b>Idea C:</b> Descripción rápida de la alternativa C</li>
            </ul>
            <h3>⚖️ Evaluación Pros & Contras</h3>
            <p>Analizar factibilidad, costo e impacto de cada propuesta...</p>
            <h3>🏁 Siguientes Pasos</h3>
            <p>Definir prototipo o prueba piloto...</p>
        """
    },
    {
        "id": "apuntes",
        "titulo": "📚 Apuntes de Clase / Resumen",
        "descripcion": "Formato estilo Método Cornell para tomar notas de estudio de forma ordenada.",
        "categoria": "Estudio",
        "html": """
            <h2>📚 Apuntes de Clase / Estudio</h2>
            <p><b>Materia / Tema:</b> Nombre de la materia | <b>Profesor:</b> Nombre</p>
            <hr>
            <h3>🔑 Conceptos Clave & Preguntas</h3>
            <ul>
                <li><b>Concepto 1:</b> Definición o término clave</li>
                <li><b>Concepto 2:</b> Pregunta importante de examen</li>
            </ul>
            <h3>📝 Notas Principales</h3>
            <p>Desarrollo detallado de los temas explicados en clase...</p>
            <h3>📌 Resumen Breve</h3>
            <p>Síntesis en 2 o 3 oraciones con lo más importante de la sesión.</p>
        """
    }
]


class TabPlantillasNotas(QWidget):
    """Submódulo de Catálogo de Plantillas Predefinidas y Personalizadas para Notas"""
    def __init__(self, parent=None, context=None, colores=None, callback_usar_plantilla=None, storage=None):
        super().__init__(parent)
        self.context = context
        self.colores = colores or (getattr(context, "colores", {}) if context else {})
        self.callback_usar_plantilla = callback_usar_plantilla
        self.storage = storage or (getattr(parent, "storage", None) if parent else None)
        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {bg_p}; }}")

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: {bg_p};")
        self.lay = QVBoxLayout(self.content_widget)
        self.lay.setContentsMargins(20, 20, 20, 20)
        self.lay.setSpacing(16)

        scroll.setWidget(self.content_widget)
        main_lay.addWidget(scroll)

        self.recargar_plantillas()

    def recargar_plantillas(self):
        # Limpiar layout
        while self.lay.count():
            item = self.lay.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                while item.layout().count():
                    subitem = item.layout().takeAt(0)
                    if subitem.widget():
                        subitem.widget().deleteLater()

        # Header
        lbl_tit = QLabel("📋 BIBLIOTECA DE PLANTILLAS PARA NOTAS")
        lbl_tit.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        self.lay.addWidget(lbl_tit)

        lbl_desc = QLabel("Selecciona una plantilla predefinida o personalizada para crear automáticamente una nota:")
        lbl_desc.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 11px;")
        self.lay.addWidget(lbl_desc)

        # Cargar plantillas de usuario si hay storage
        plantillas_usuario = []
        if self.storage and hasattr(self.storage, "cargar_plantillas_usuario"):
            plantillas_usuario = self.storage.cargar_plantillas_usuario()

        todas_plantillas = list(PLANTILLAS_DISPONIBLES) + plantillas_usuario

        # Grid de plantillas
        grid = QGridLayout()
        grid.setSpacing(14)

        for idx, p in enumerate(todas_plantillas):
            es_personalizada = p.get("personalizada", False)
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {self.colores.get('bg_secundario', '#1E1E2E')};
                    border: 1px solid {"rgba(99,102,241,0.3)" if es_personalizada else "rgba(255,255,255,0.08)"}; 
                    border-radius: 10px; padding: 16px;
                }}
                QFrame:hover {{ border-color: {self.colores.get('acento', '#6366F1')}; }}
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setSpacing(8)

            row_top = QHBoxLayout()
            lbl_t = QLabel(p.get("titulo", "Plantilla"))
            lbl_t.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            lbl_t.setStyleSheet("color: white;")
            row_top.addWidget(lbl_t, 1)

            if es_personalizada and self.storage:
                btn_del = QPushButton("🗑️")
                btn_del.setFixedSize(24, 24)
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setStyleSheet("background: transparent; border: none; font-size: 11px;")
                btn_del.setToolTip("Eliminar plantilla personalizada")
                btn_del.clicked.connect(lambda ch, pid=p.get("id"): self._eliminar_plantilla(pid))
                row_top.addWidget(btn_del)

            c_lay.addLayout(row_top)

            cat = p.get("categoria", "Personalizada" if es_personalizada else "General")
            lbl_cat = QLabel(f"🏷️ Categoría: {cat}")
            lbl_cat.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; font-size: 9px; font-weight: bold;")
            c_lay.addWidget(lbl_cat)

            lbl_d = QLabel(p.get("descripcion", "Plantilla personalizada guardada por el usuario."))
            lbl_d.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px;")
            lbl_d.setWordWrap(True)
            c_lay.addWidget(lbl_d, 1)

            btn_use = QPushButton("✨ Usar esta Plantilla")
            btn_use.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_use.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores.get('acento', '#6366F1')}; color: white;
                    border: none; border-radius: 6px; padding: 7px 12px; font-weight: bold; font-size: 10px;
                }}
                QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
            """)
            btn_use.clicked.connect(lambda ch, plant=p: self._usar_plantilla(plant))
            c_lay.addWidget(btn_use)

            row = idx // 2
            col = idx % 2
            grid.addWidget(card, row, col)

        self.lay.addLayout(grid)
        self.lay.addStretch()

    def _eliminar_plantilla(self, plantilla_id):
        confirm = QMessageBox.question(
            self, "Eliminar Plantilla",
            "¿Deseas eliminar esta plantilla personalizada?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes and self.storage:
            self.storage.eliminar_plantilla_usuario(plantilla_id)
            self.recargar_plantillas()

    def _usar_plantilla(self, plantilla):
        if callable(self.callback_usar_plantilla):
            titulo_limpio = plantilla.get("titulo", "Nueva Nota")
            for icon in ["📝 ", "📅 ", "💡 ", "📚 ", "📋 "]:
                titulo_limpio = titulo_limpio.replace(icon, "")
            self.callback_usar_plantilla(titulo_limpio, plantilla.get("html", ""))
            QMessageBox.information(self, "Plantilla Creada", f"¡Se ha creado la nota basada en '{plantilla.get('titulo')}'!")
