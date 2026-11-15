# -*- coding: utf-8 -*-
"""
Sincronización bidireccional (Código Python <-> Lienzo Visual) mediante `ast`.
- Soporta posicionamiento libre (`setGeometry`) y layouts responsivos.
- Preserva métodos y lógica personalizada fuera de los marcadores `# <UI_START>` / `# <UI_END>`.
- Descubre funciones en `utils/*.py` para conectar eventos desde el Inspector.
"""

import ast
from pathlib import Path

UI_START = "# <UI_START>"
UI_END = "# <UI_END>"

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
    "QSpinBox",
    "QSlider",
    "QTableWidget",
    "QGroupBox",
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


def discover_backend_functions(mod_dir: Path) -> list[str]:
    """Escanea `utils/*.py` con AST y devuelve `backend:<archivo>:<funcion>`."""
    utils_dir = mod_dir / "utils"
    if not utils_dir.exists():
        return []
    found: list[str] = []
    for py in sorted(utils_dir.glob("*.py")):
        if py.name == "__init__.py":
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                found.append(f"backend:{py.stem}:{node.name}")
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                        found.append(f"backend:{py.stem}:{node.name}.{item.name}")
    return found


def parse_pyqt_to_design(code: str) -> tuple[list[dict], str]:
    """Parsea código PyQt6 con `ast` y extrae `design_items` y el modo de layout."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return [], "free"

    items_by_var: dict[str, dict] = {}
    order: list[str] = []
    layout_mode = "free"

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "QVBoxLayout":
                layout_mode = "vbox"
            elif node.func.id == "QHBoxLayout":
                layout_mode = "hbox"
            elif node.func.id == "QGridLayout":
                layout_mode = "grid"

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
                default_w = 340 if w_cls == "QTableWidget" else (300 if w_cls == "QGroupBox" else 220)
                default_h = 140 if w_cls in {"QTableWidget", "QGroupBox"} else (80 if w_cls == "QTextEdit" else 32)
                spec = {
                    "tipo": w_type,
                    "var": var,
                    "texto": texto,
                    "placeholder": "",
                    "x": 16,
                    "y": 16 + idx * 42,
                    "w": default_w,
                    "h": default_h,
                    "target_sub": "",
                    "fg_color": "",
                    "bg_color": "",
                }
                items_by_var[var] = spec
                if var not in order:
                    order.append(var)

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


def _build_ui_block(design_items: list[dict], layout_mode: str) -> list[str]:
    lines = [
        f"        {UI_START}",
        '        self.setStyleSheet("QFrame { background: transparent; } QLabel, QCheckBox, QPushButton, QGroupBox { color: #ffffff; }")',
    ]
    if layout_mode == "vbox":
        lines.extend(["        layout = QVBoxLayout(self)", "        layout.setContentsMargins(16, 16, 16, 16)", "        layout.setSpacing(10)"])
    elif layout_mode == "hbox":
        lines.extend(["        layout = QHBoxLayout(self)", "        layout.setContentsMargins(16, 16, 16, 16)", "        layout.setSpacing(10)"])
    elif layout_mode == "grid":
        lines.extend(["        layout = QGridLayout(self)", "        layout.setContentsMargins(16, 16, 16, 16)", "        layout.setSpacing(10)"])
    else:
        lines.append("        self.setMinimumSize(560, 400)")

    lines.append("")
    for idx, it in enumerate(design_items):
        var = it["var"]
        txt = it.get("texto", "").replace('"', '\\"')
        t = it["tipo"]
        x, y, w, h = it.get("x", 16), it.get("y", 16), it.get("w", 200), it.get("h", 32)
        target = it.get("target_sub", "")
        fg = it.get("fg_color") or "#ffffff"
        bg = it.get("bg_color") or ""

        if t == "QLabel_title":
            lines.append(f'        self.{var} = QLabel("{txt}", self)')
            lines.append(f'        self.{var}.setStyleSheet("font-size: 17px; font-weight: 700; color: {fg};")')
        elif t == "QLabel":
            lines.append(f'        self.{var} = QLabel("{txt}", self)')
            lines.append(f'        self.{var}.setStyleSheet("font-size: 12px; color: {fg};")')
        elif t == "QPushButton":
            btn_bg = bg or "#4f46e5"
            lines.append(f'        self.{var} = QPushButton("{txt}", self)')
            lines.append(f'        self.{var}.setStyleSheet("background-color: {btn_bg}; color: {fg}; border-radius: 6px; padding: 6px 12px; font-weight: 600;")')
            if target.startswith("notificacion:"):
                lines.append(
                    f'        self.{var}.clicked.connect(lambda: getattr(self.context, "app", None) '
                    f'and self.context.app.mostrar_notificacion("{txt}", "Acción ejecutada", tipo="info"))'
                )
            elif target.startswith("backend:"):
                parts = target.split(":", 2)
                if len(parts) == 3:
                    mod_stem, fn_expr = parts[1], parts[2]
                    if "." in fn_expr:
                        cls_n, meth_n = fn_expr.split(".", 1)
                        lines.append(f'        from ..utils.{mod_stem} import {cls_n}')
                        lines.append(f'        self.{var}.clicked.connect(lambda: {cls_n}().{meth_n}(""))')
                    else:
                        lines.append(f'        from ..utils.{mod_stem} import {fn_expr}')
                        lines.append(f'        self.{var}.clicked.connect(lambda: {fn_expr}(self.context))')
        elif t == "QLineEdit":
            ph = it.get("placeholder", "").replace('"', '\\"')
            lines.append(f'        self.{var} = QLineEdit("{txt}", self)')
            lines.append(f'        self.{var}.setStyleSheet("background-color: {bg or "#181b28"}; color: {fg}; border: 1px solid #38405e; border-radius: 5px; padding: 5px;")')
            if ph:
                lines.append(f'        self.{var}.setPlaceholderText("{ph}")')
        elif t == "QTextEdit":
            lines.append(f'        self.{var} = QTextEdit("{txt}", self)')
            lines.append(f'        self.{var}.setStyleSheet("background-color: {bg or "#181b28"}; color: {fg}; border: 1px solid #38405e; border-radius: 5px; padding: 5px;")')
        elif t == "QComboBox":
            lines.append(f"        self.{var} = QComboBox(self)")
            lines.append(f'        self.{var}.addItems(["{txt or "Opción 1"}", "Opción 2"])')
            lines.append(f'        self.{var}.setStyleSheet("background-color: {bg or "#181b28"}; color: {fg}; border: 1px solid #38405e; border-radius: 5px; padding: 4px;")')
        elif t == "QCheckBox":
            lines.append(f'        self.{var} = QCheckBox("{txt}", self)')
            lines.append(f'        self.{var}.setStyleSheet("color: {fg};")')
        elif t == "QSpinBox":
            lines.append(f"        self.{var} = QSpinBox(self)")
            lines.append(f'        self.{var}.setStyleSheet("background-color: {bg or "#181b28"}; color: {fg}; border: 1px solid #38405e;")')
        elif t == "QSlider":
            lines.append(f"        self.{var} = QSlider(Qt.Orientation.Horizontal, self)")
        elif t == "QTableWidget":
            lines.append(f"        self.{var} = QTableWidget(3, 3, self)")
            lines.append(f'        self.{var}.setStyleSheet("background-color: {bg or "#181b28"}; color: {fg}; gridline-color: #2e344d;")')
        elif t == "QGroupBox":
            lines.append(f'        self.{var} = QGroupBox("{txt}", self)')
            lines.append(f'        self.{var}.setStyleSheet("color: {fg}; border: 1px solid #38405e; border-radius: 6px;")')
        elif t == "QProgressBar":
            lines.append(f"        self.{var} = QProgressBar(self)")
            lines.append(f"        self.{var}.setValue(0)")
            lines.append(f'        self.{var}.setStyleSheet("color: {fg};")')
        elif t == "SubmoduleSlot":
            lines.append(f"        self.{var} = QFrame(self)")
            lines.append(f'        self.{var}.setStyleSheet("border: 1px dashed #6366f1; border-radius: 6px; color: {fg};")')

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
    lines.append(f"        {UI_END}")
    return lines


def generate_pyqt_from_design(
    design_items: list[dict],
    class_name: str,
    titulo: str,
    layout_mode: str = "free",
    existing_code: str | None = None,
) -> str:
    """
    Genera código PyQt6 completo, o si `existing_code` contiene `# <UI_START>` y `# <UI_END>`,
    reemplaza únicamente ese bloque preservando métodos propios e imports del usuario.
    """
    ui_block = "\n".join(_build_ui_block(design_items, layout_mode))

    if existing_code and UI_START in existing_code and UI_END in existing_code:
        start_idx = existing_code.index(UI_START)
        # Retroceder hasta el inicio de la línea de UI_START
        line_start = existing_code.rfind("\n", 0, start_idx)
        line_start = 0 if line_start == -1 else line_start + 1
        end_idx = existing_code.index(UI_END) + len(UI_END)
        return existing_code[:line_start] + ui_block + existing_code[end_idx:]

    layout_import = ""
    if layout_mode == "vbox":
        layout_import = ", QVBoxLayout"
    elif layout_mode == "hbox":
        layout_import = ", QHBoxLayout"
    elif layout_mode == "grid":
        layout_import = ", QGridLayout"

    header = [
        "# -*- coding: utf-8 -*-",
        "from PyQt6.QtCore import Qt",
        "from PyQt6.QtWidgets import (",
        "    QCheckBox, QComboBox, QFrame, QGroupBox, QLabel, QLineEdit,",
        f"    QProgressBar, QPushButton, QSlider, QSpinBox, QTableWidget, QTextEdit{layout_import}",
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
        ui_block,
        "",
    ]
    return "\n".join(header)
