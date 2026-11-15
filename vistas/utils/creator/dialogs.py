# -*- coding: utf-8 -*-
"""Diálogos auxiliares y generadores de código PyQt6 para el Modo Creador."""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
)


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
        self.rb_func = QRadioButton("⚙️ Funcionalidad (Backend / Lógica — con snippets Multitool)")
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


def generar_codigo_pyqt(design_items: list[dict], class_name: str, titulo: str) -> str:
    """Genera código PyQt6 completo a partir de los elementos del lienzo visual."""
    lines = [
        "# -*- coding: utf-8 -*-",
        "from PyQt6.QtWidgets import (",
        "    QCheckBox, QComboBox, QFrame, QLabel, QLineEdit,",
        "    QProgressBar, QPushButton, QTextEdit",
        ")",
        "",
        "",
        f"class {class_name}(QFrame):",
        f'    """Módulo {titulo} generado con Modo Creador (mode MT)."""',
        "",
        "    def __init__(self, parent=None, context=None, **kwargs):",
        "        super().__init__(parent)",
        "        self.context = context",
        "        self._init_ui()",
        "",
        "    def _init_ui(self):",
        '        self.setStyleSheet("QFrame { background: transparent; } QLabel, QCheckBox { color: #f8fafc; }")',
        "        self.setMinimumSize(560, 400)",
        "",
    ]
    for it in design_items:
        var = it["var"]
        txt = it["texto"].replace('"', '\\"')
        t = it["tipo"]
        x, y, w, h = it.get("x", 16), it.get("y", 16), it.get("w", 200), it.get("h", 32)
        target = it.get("target_sub", "")

        if t == "QLabel_title":
            lines.append(f'        self.{var} = QLabel("{txt}", self)')
            lines.append(f'        self.{var}.setStyleSheet("font-size: 17px; font-weight: 700; color: #ffffff;")')
        elif t == "QLabel":
            lines.append(f'        self.{var} = QLabel("{txt}", self)')
            lines.append(f'        self.{var}.setStyleSheet("font-size: 12px; color: #e2e8f0;")')
        elif t == "QPushButton":
            lines.append(f'        self.{var} = QPushButton("{txt}", self)')
            if target.startswith("notificacion:"):
                lines.append(
                    f'        self.{var}.clicked.connect(lambda: getattr(self.context, "app", None) '
                    f'and self.context.app.mostrar_notificacion("{txt}", "Acción ejecutada", tipo="info"))'
                )
        elif t == "QLineEdit":
            ph = it.get("placeholder", "").replace('"', '\\"')
            lines.append(f'        self.{var} = QLineEdit("{txt}", self)')
            if ph:
                lines.append(f'        self.{var}.setPlaceholderText("{ph}")')
        elif t == "QTextEdit":
            lines.append(f'        self.{var} = QTextEdit("{txt}", self)')
        elif t == "QComboBox":
            lines.append(f"        self.{var} = QComboBox(self)")
            lines.append(f'        self.{var}.addItems(["{txt or "Opción 1"}", "Opción 2"])')
        elif t == "QCheckBox":
            lines.append(f'        self.{var} = QCheckBox("{txt}", self)')
        elif t == "QProgressBar":
            lines.append(f"        self.{var} = QProgressBar(self)")
            lines.append(f"        self.{var}.setValue(0)")
        elif t == "SubmoduleSlot":
            lines.append(f"        self.{var} = QFrame(self)")
            lines.append(f'        self.{var}.setStyleSheet("border: 1px dashed #6366f1; border-radius: 6px;")')
        lines.append(f"        self.{var}.setGeometry({x}, {y}, {w}, {h})")
        lines.append("")
    return "\n".join(lines)
