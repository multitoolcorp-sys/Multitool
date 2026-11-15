# -*- coding: utf-8 -*-
"""
Sincronización bidireccional (Código Python <-> Lienzo Visual) mediante `ast`.
Soporta posicionamiento libre (`setGeometry`) y layouts responsivos
(`QVBoxLayout`, `QHBoxLayout`, `QGridLayout`).
"""

import ast

LAYOUT_MODES = [
    ("Libre (setGeometry)", "free"),
    ("Vertical (QVBoxLayout)", "vbox"),
    ("Horizontal (QHBoxLayout)", "hbox"),
    ("Cuadrícula (QGridLayout)", "grid"),
]

SUPPORTED_WIDGETS = {
    "QLabel",
    "QPushButton",
    "QLineEdit",
    "QTextEdit",
    "QComboBox",
    "QCheckBox",
    "QProgressBar",
    "QFrame",
}


def _const_str(node) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _const_int(node, default: int = 0) -> int:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return int(node.value)
    return default


def parse_pyqt_to_design(code: str) -> tuple[list[dict], str]:
    """
    Parsea código PyQt6 con `ast` y extrae:
    - lista de widgets (`design_items`)
    - modo de layout detectado ('free', 'vbox', 'hbox', 'grid')
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return [], "free"

    items_by_var: dict[str, dict] = {}
    order: list[str] = []
    layout_mode = "free"

    for node in ast.walk(tree):
        # Detectar tipo de layout
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "QVBoxLayout":
                layout_mode = "vbox"
            elif node.func.id == "QHBoxLayout":
                layout_mode = "hbox"
            elif node.func.id == "QGridLayout":
                layout_mode = "grid"

        # Detectar creación: self.var = QPushButton("Texto", self)
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if (
                isinstance(tgt, ast.Attribute)
                and isinstance(tgt.value, ast.Name)
                and tgt.value.id == "self"
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id in SUPPORTED_WIDGETS
            ):
                var = tgt.attr
                w_cls = node.value.func.id
                texto = _const_str(node.value.args[0]) if node.value.args else ""
                w_type = "SubmoduleSlot" if w_cls == "QFrame" else w_cls
                idx = len(order)
                spec = {
                    "tipo": w_type,
                    "var": var,
                    "texto": texto,
                    "placeholder": "",
                    "x": 16,
                    "y": 16 + idx * 42,
                    "w": 240 if w_cls in {"QLabel", "QLineEdit", "QProgressBar"} else 180,
                    "h": 80 if w_cls == "QTextEdit" else 32,
                    "target_sub": "",
                }
                items_by_var[var] = spec
                if var not in order:
                    order.append(var)

        # Detectar llamadas sobre self.<var>: setGeometry, setPlaceholderText, setStyleSheet, addItems
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "self"
        ):
            var = node.func.value.attr
            method = node.func.attr
            if var not in items_by_var:
                continue
            spec = items_by_var[var]
            if method == "setGeometry" and len(node.args) >= 4:
                spec["x"] = _const_int(node.args[0], spec["x"])
                spec["y"] = _const_int(node.args[1], spec["y"])
                spec["w"] = _const_int(node.args[2], spec["w"])
                spec["h"] = _const_int(node.args[3], spec["h"])
            elif method == "setPlaceholderText" and node.args:
                spec["placeholder"] = _const_str(node.args[0])
            elif method == "setStyleSheet" and node.args:
                css = _const_str(node.args[0])
                if spec["tipo"] == "QLabel" and ("17px" in css or "18px" in css or "700" in css):
                    spec["tipo"] = "QLabel_title"
            elif method == "addItems" and node.args and isinstance(node.args[0], ast.List):
                elts = node.args[0].elts
                if elts:
                    spec["texto"] = _const_str(elts[0]) or spec["texto"]

    return [items_by_var[v] for v in order], layout_mode


def generate_pyqt_from_design(
    design_items: list[dict],
    class_name: str,
    titulo: str,
    layout_mode: str = "free",
) -> str:
    """Genera código PyQt6 limpio y con letras blancas desde el lienzo visual."""
    layout_import = ""
    if layout_mode == "vbox":
        layout_import = ", QVBoxLayout"
    elif layout_mode == "hbox":
        layout_import = ", QHBoxLayout"
    elif layout_mode == "grid":
        layout_import = ", QGridLayout"

    lines = [
        "# -*- coding: utf-8 -*-",
        "from PyQt6.QtWidgets import (",
        f"    QCheckBox, QComboBox, QFrame, QLabel, QLineEdit,",
        f"    QProgressBar, QPushButton, QTextEdit{layout_import}",
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
        '        self.setStyleSheet("QFrame { background: transparent; } QLabel, QCheckBox, QPushButton { color: #ffffff; }")',
    ]

    if layout_mode == "vbox":
        lines.append("        layout = QVBoxLayout(self)")
        lines.append("        layout.setContentsMargins(16, 16, 16, 16)")
        lines.append("        layout.setSpacing(10)")
    elif layout_mode == "hbox":
        lines.append("        layout = QHBoxLayout(self)")
        lines.append("        layout.setContentsMargins(16, 16, 16, 16)")
        lines.append("        layout.setSpacing(10)")
    elif layout_mode == "grid":
        lines.append("        layout = QGridLayout(self)")
        lines.append("        layout.setContentsMargins(16, 16, 16, 16)")
        lines.append("        layout.setSpacing(10)")
    else:
        lines.append("        self.setMinimumSize(560, 400)")

    lines.append("")
    parent_arg = "self"

    for idx, it in enumerate(design_items):
        var = it["var"]
        txt = it.get("texto", "").replace('"', '\\"')
        t = it["tipo"]
        x, y, w, h = it.get("x", 16), it.get("y", 16), it.get("w", 200), it.get("h", 32)
        target = it.get("target_sub", "")

        if t == "QLabel_title":
            lines.append(f'        self.{var} = QLabel("{txt}", {parent_arg})')
            lines.append(f'        self.{var}.setStyleSheet("font-size: 17px; font-weight: 700; color: #ffffff;")')
        elif t == "QLabel":
            lines.append(f'        self.{var} = QLabel("{txt}", {parent_arg})')
            lines.append(f'        self.{var}.setStyleSheet("font-size: 12px; color: #f1f5f9;")')
        elif t == "QPushButton":
            lines.append(f'        self.{var} = QPushButton("{txt}", {parent_arg})')
            lines.append(f'        self.{var}.setStyleSheet("background-color: #4f46e5; color: #ffffff; border-radius: 6px; padding: 6px 12px; font-weight: 600;")')
            if target.startswith("notificacion:"):
                lines.append(
                    f'        self.{var}.clicked.connect(lambda: getattr(self.context, "app", None) '
                    f'and self.context.app.mostrar_notificacion("{txt}", "Acción ejecutada", tipo="info"))'
                )
        elif t == "QLineEdit":
            ph = it.get("placeholder", "").replace('"', '\\"')
            lines.append(f'        self.{var} = QLineEdit("{txt}", {parent_arg})')
            lines.append(f'        self.{var}.setStyleSheet("background-color: #181b28; color: #ffffff; border: 1px solid #38405e; border-radius: 5px; padding: 5px;")')
            if ph:
                lines.append(f'        self.{var}.setPlaceholderText("{ph}")')
        elif t == "QTextEdit":
            lines.append(f'        self.{var} = QTextEdit("{txt}", {parent_arg})')
            lines.append(f'        self.{var}.setStyleSheet("background-color: #181b28; color: #ffffff; border: 1px solid #38405e; border-radius: 5px; padding: 5px;")')
        elif t == "QComboBox":
            lines.append(f"        self.{var} = QComboBox({parent_arg})")
            lines.append(f'        self.{var}.addItems(["{txt or "Opción 1"}", "Opción 2"])')
            lines.append(f'        self.{var}.setStyleSheet("background-color: #181b28; color: #ffffff; border: 1px solid #38405e; border-radius: 5px; padding: 4px;")')
        elif t == "QCheckBox":
            lines.append(f'        self.{var} = QCheckBox("{txt}", {parent_arg})')
            lines.append(f'        self.{var}.setStyleSheet("color: #ffffff;")')
        elif t == "QProgressBar":
            lines.append(f"        self.{var} = QProgressBar({parent_arg})")
            lines.append("        self.{var}.setValue(0)".format(var=var))
            lines.append(f'        self.{var}.setStyleSheet("color: #ffffff;")')
        elif t == "SubmoduleSlot":
            lines.append(f"        self.{var} = QFrame({parent_arg})")
            lines.append(f'        self.{var}.setStyleSheet("border: 1px dashed #6366f1; border-radius: 6px; color: #ffffff;")')

        if layout_mode == "free":
            lines.append(f"        self.{var}.setGeometry({x}, {y}, {w}, {h})")
        elif layout_mode in {"vbox", "hbox"}:
            lines.append(f"        layout.addWidget(self.{var})")
        elif layout_mode == "grid":
            row, col = divmod(idx, 2)
            lines.append(f"        layout.addWidget(self.{var}, {row}, {col})")
        lines.append("")

    if layout_mode in {"vbox", "hbox"}:
        lines.append("        layout.addStretch(1)")
        lines.append("")

    return "\n".join(lines)
