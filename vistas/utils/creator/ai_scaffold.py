# -*- coding: utf-8 -*-
"""
Asistente Generador de Módulos por Descripción (Copiloto IA / Heurístico offline).
Permite describir en lenguaje natural qué módulo necesitas y construye automáticamente
el diseño visual (layout + widgets), el backend en `utils/backend.py` y el `config.json`.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
)


def generar_especificacion_desde_prompt(nombre: str, prompt: str) -> tuple[list[dict], str, str]:
    """
    Analiza la descripción en español y devuelve:
    - items de diseño visual
    - layout_mode ('vbox', 'grid', 'free')
    - código backend sugerido para `utils/backend.py`
    """
    p = prompt.lower()
    items = [
        {"tipo": "QLabel_title", "var": "lbl_titulo", "texto": nombre, "placeholder": "", "x": 16, "y": 16, "w": 300, "h": 32, "target_sub": ""},
    ]
    y = 56

    if any(k in p for k in ("buscar", "texto", "nombre", "comando", "ruta", "url", "escribir", "entrada")):
        items.append({"tipo": "QLineEdit", "var": "ent_entrada", "texto": "", "placeholder": "Ingresa el dato o comando...", "x": 16, "y": y, "w": 280, "h": 32, "target_sub": ""})
        y += 42

    if any(k in p for k in ("numero", "cantidad", "limite", "puerto", "tiempo", "minutos")):
        items.append({"tipo": "QSpinBox", "var": "spn_valor", "texto": "", "placeholder": "", "x": 16, "y": y, "w": 120, "h": 30, "target_sub": ""})
        y += 38

    if any(k in p for k in ("opcion", "lista", "elegir", "filtro", "modo", "tipo")):
        items.append({"tipo": "QComboBox", "var": "cmb_opcion", "texto": "Opción 1", "placeholder": "", "x": 16, "y": y, "w": 200, "h": 30, "target_sub": ""})
        y += 38

    if any(k in p for k in ("activar", "check", "auto", "habilitar")):
        items.append({"tipo": "QCheckBox", "var": "chk_auto", "texto": "Activar modo automático", "placeholder": "", "x": 16, "y": y, "w": 220, "h": 26, "target_sub": ""})
        y += 34

    items.append({"tipo": "QPushButton", "var": "btn_ejecutar", "texto": "▶ Ejecutar", "placeholder": "", "x": 16, "y": y, "w": 160, "h": 34, "target_sub": "backend:backend:ejecutar_accion"})
    y += 42

    if any(k in p for k in ("progreso", "barra", "carga", "porcentaje", "cpu", "ram")):
        items.append({"tipo": "QProgressBar", "var": "prg_avance", "texto": "", "placeholder": "", "x": 16, "y": y, "w": 300, "h": 22, "target_sub": ""})
        y += 32

    if any(k in p for k in ("tabla", "lista", "datos", "registro", "historial", "archivos")):
        items.append({"tipo": "QTableWidget", "var": "tbl_datos", "texto": "", "placeholder": "", "x": 16, "y": y, "w": 380, "h": 150, "target_sub": ""})
        y += 160

    if any(k in p for k in ("log", "consola", "terminal", "resultado", "salida", "nota")):
        items.append({"tipo": "QTextEdit", "var": "txt_salida", "texto": "Salida lista...", "placeholder": "", "x": 16, "y": y, "w": 380, "h": 120, "target_sub": ""})

    backend_code = (
        "# -*- coding: utf-8 -*-\n"
        f'"""Backend generado por Asistente IA para: {nombre}."""\n\n\n'
        "def ejecutar_accion(context=None, **kwargs):\n"
        '    app = getattr(context, "app", None) if context else None\n'
        '    if app and hasattr(app, "mostrar_notificacion"):\n'
        f'        app.mostrar_notificacion("{nombre}", "Acción ejecutada correctamente", tipo="success")\n'
        "    return True\n"
    )
    return items, "vbox", backend_code


class AIScaffoldDialog(QDialog):
    """Diálogo para crear un módulo describiendo su propósito."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🤖 Generador de Módulo por Descripción")
        self.setMinimumWidth(440)
        self.setStyleSheet("""
            QDialog, QWidget { background-color: #151824; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #f8fafc; }
            QLineEdit, QTextEdit { background-color: #0f111a; color: #f8fafc; border: 1px solid #2e344d; border-radius: 5px; padding: 6px; }
            QPushButton { background-color: #252a3d; color: #f8fafc; border: 1px solid #38405e; border-radius: 5px; padding: 6px 12px; }
        """)
        lay = QFormLayout(self)
        lay.setSpacing(8)
        self.ent_nombre = QLineEdit()
        self.ent_nombre.setPlaceholderText("Ej: Analizador de Logs")
        self.txt_prompt = QTextEdit()
        self.txt_prompt.setPlaceholderText(
            "Describe qué quieres que tenga el módulo.\n"
            "Ej: Un campo de texto para buscar ruta, botón ejecutar, barra de progreso y tabla de resultados con logs."
        )
        self.txt_prompt.setFixedHeight(100)
        lay.addRow("Nombre del módulo:", self.ent_nombre)
        lay.addRow("Descripción:", self.txt_prompt)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addRow(btns)
