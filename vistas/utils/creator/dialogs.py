# -*- coding: utf-8 -*-
"""Diálogos auxiliares y plantillas de inicio para el Modo Creador."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
)

from vistas.utils.creator.ast_sync import generate_pyqt_from_design

MODULE_TEMPLATES = {
    "basico": {
        "label": "🧩 Módulo Básico (Inicio limpio)",
        "layout": "free",
        "items": [
            {"tipo": "QLabel_title", "var": "lbl_titulo", "texto": "{titulo}", "placeholder": "", "x": 16, "y": 16, "w": 280, "h": 32, "target_sub": ""},
            {"tipo": "QLabel", "var": "lbl_desc", "texto": "Módulo creado con Modo Creador.", "placeholder": "", "x": 16, "y": 56, "w": 320, "h": 24, "target_sub": ""},
            {"tipo": "QPushButton", "var": "btn_accion", "texto": "Ejecutar", "placeholder": "", "x": 16, "y": 96, "w": 150, "h": 34, "target_sub": "notificacion:info"},
        ],
    },
    "dashboard": {
        "label": "📊 Dashboard con Tarjetas y Métricas",
        "layout": "vbox",
        "items": [
            {"tipo": "QLabel_title", "var": "lbl_titulo", "texto": "{titulo} — Panel", "placeholder": "", "x": 16, "y": 16, "w": 320, "h": 32, "target_sub": ""},
            {"tipo": "QProgressBar", "var": "prg_estado", "texto": "", "placeholder": "", "x": 16, "y": 60, "w": 300, "h": 24, "target_sub": ""},
            {"tipo": "SubmoduleSlot", "var": "card_resumen", "texto": "Tarjeta de Métricas", "placeholder": "", "x": 16, "y": 96, "w": 320, "h": 120, "target_sub": ""},
            {"tipo": "QPushButton", "var": "btn_actualizar", "texto": "🔄 Actualizar Datos", "placeholder": "", "x": 16, "y": 230, "w": 180, "h": 34, "target_sub": "notificacion:info"},
        ],
    },
    "terminal": {
        "label": "💻 Herramienta con Terminal / Logs",
        "layout": "vbox",
        "items": [
            {"tipo": "QLabel_title", "var": "lbl_titulo", "texto": "{titulo} — Consola", "placeholder": "", "x": 16, "y": 16, "w": 300, "h": 32, "target_sub": ""},
            {"tipo": "QLineEdit", "var": "ent_comando", "texto": "", "placeholder": "Escribe un comando...", "x": 16, "y": 56, "w": 320, "h": 32, "target_sub": ""},
            {"tipo": "QPushButton", "var": "btn_ejecutar", "texto": "▶ Ejecutar", "placeholder": "", "x": 16, "y": 96, "w": 140, "h": 32, "target_sub": ""},
            {"tipo": "QTextEdit", "var": "txt_logs", "texto": "Esperando comandos...", "placeholder": "", "x": 16, "y": 140, "w": 420, "h": 180, "target_sub": ""},
        ],
    },
    "formulario": {
        "label": "📋 Formulario de Entrada + Opciones",
        "layout": "vbox",
        "items": [
            {"tipo": "QLabel_title", "var": "lbl_titulo", "texto": "Formulario: {titulo}", "placeholder": "", "x": 16, "y": 16, "w": 300, "h": 32, "target_sub": ""},
            {"tipo": "QLineEdit", "var": "ent_nombre", "texto": "", "placeholder": "Nombre...", "x": 16, "y": 56, "w": 260, "h": 32, "target_sub": ""},
            {"tipo": "QComboBox", "var": "cmb_opcion", "texto": "Opción A", "placeholder": "", "x": 16, "y": 96, "w": 220, "h": 30, "target_sub": ""},
            {"tipo": "QCheckBox", "var": "chk_activo", "texto": "Activar opción avanzada", "placeholder": "", "x": 16, "y": 134, "w": 220, "h": 26, "target_sub": ""},
            {"tipo": "QPushButton", "var": "btn_guardar", "texto": "💾 Guardar Registro", "placeholder": "", "x": 16, "y": 170, "w": 170, "h": 34, "target_sub": "notificacion:info"},
        ],
    },
    "servicio": {
        "label": "⚙️ Servicio en Segundo Plano (QThread)",
        "layout": "vbox",
        "items": [
            {"tipo": "QLabel_title", "var": "lbl_titulo", "texto": "Servicio: {titulo}", "placeholder": "", "x": 16, "y": 16, "w": 300, "h": 32, "target_sub": ""},
            {"tipo": "QLabel", "var": "lbl_estado", "texto": "Estado: Detenido", "placeholder": "", "x": 16, "y": 56, "w": 240, "h": 24, "target_sub": ""},
            {"tipo": "QProgressBar", "var": "prg_servicio", "texto": "", "placeholder": "", "x": 16, "y": 88, "w": 300, "h": 22, "target_sub": ""},
            {"tipo": "QPushButton", "var": "btn_iniciar", "texto": "▶ Iniciar Servicio", "placeholder": "", "x": 16, "y": 122, "w": 160, "h": 34, "target_sub": "notificacion:info"},
        ],
    },
}


class NewFileTypeDialog(QDialog):
    """Pregunta si el nuevo archivo será Visual (Submódulo UI) o Funcionalidad (Backend)."""

    def __init__(self, base_dir_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Archivo en Módulo")
        self.setMinimumWidth(380)
        self.setStyleSheet("""
            QDialog, QWidget { background-color: #151824; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QLabel, QRadioButton { color: #f8fafc; }
            QLineEdit { background-color: #0f111a; color: #f8fafc; border: 1px solid #2e344d; border-radius: 5px; padding: 5px; }
            QPushButton { background-color: #252a3d; color: #f8fafc; border: 1px solid #38405e; border-radius: 5px; padding: 5px 12px; }
        """)
        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        lay.addWidget(QLabel(f"Crear dentro de <b>{base_dir_name}/</b>:"))
        self.ent_nombre = QLineEdit()
        self.ent_nombre.setPlaceholderText("Ej: tab_reportes.py  o  gestor_red.py")
        lay.addWidget(self.ent_nombre)

        self.rb_visual = QRadioButton("🎨 Visual (Submódulo / Pestaña UI — se añade a config.json)")
        self.rb_visual.setChecked(True)
        self.rb_func = QRadioButton("⚙️ Funcionalidad (Backend / Lógica — solo modo Código)")
        lay.addWidget(self.rb_visual)
        lay.addWidget(self.rb_func)

        self.box_visual = QFrame()
        v_lay = QFormLayout(self.box_visual)
        v_lay.setContentsMargins(16, 4, 4, 4)
        self.ent_sub_name = QLineEdit("Nueva Pestaña")
        self.ent_sub_icon = QLineEdit("🧩")
        v_lay.addRow("Nombre en pestaña:", self.ent_sub_name)
        v_lay.addRow("Icono:", self.ent_sub_icon)
        lay.addWidget(self.box_visual)

        self.rb_visual.toggled.connect(self.box_visual.setVisible)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)


class NewModuleTemplateDialog(QDialog):
    """Diálogo para crear un nuevo módulo eligiendo una plantilla de inicio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crear Nuevo Módulo")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog, QWidget { background-color: #151824; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #f8fafc; }
            QLineEdit, QComboBox { background-color: #0f111a; color: #f8fafc; border: 1px solid #2e344d; border-radius: 5px; padding: 5px; }
            QPushButton { background-color: #252a3d; color: #f8fafc; border: 1px solid #38405e; border-radius: 5px; padding: 5px 12px; }
        """)
        lay = QFormLayout(self)
        lay.setSpacing(8)

        self.ent_nombre = QLineEdit()
        self.ent_nombre.setPlaceholderText("Ej: Gestor Redes")
        self.ent_icono = QLineEdit("🧩")
        self.cmb_tpl = QComboBox()
        for k, tpl in MODULE_TEMPLATES.items():
            self.cmb_tpl.addItem(tpl["label"], k)

        lay.addRow("Nombre del módulo:", self.ent_nombre)
        lay.addRow("Icono:", self.ent_icono)
        lay.addRow("Plantilla inicial:", self.cmb_tpl)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addRow(btns)


def generar_codigo_pyqt(design_items: list[dict], class_name: str, titulo: str, layout_mode: str = "free") -> str:
    return generate_pyqt_from_design(design_items, class_name, titulo, layout_mode)
