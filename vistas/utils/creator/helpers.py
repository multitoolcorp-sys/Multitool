# -*- coding: utf-8 -*-
"""Constantes, utilidades de nombres, snippets y hoja de estilos para el Modo Creador."""

import re

WIDGET_PALETTE = [
    ("Título", "QLabel_title", "🏷️ Título", 260, 30),
    ("Etiqueta", "QLabel", "📝 Etiqueta", 240, 24),
    ("Botón", "QPushButton", "🔘 Botón", 160, 34),
    ("Campo Texto", "QLineEdit", "✏️ Campo Texto", 220, 32),
    ("Área Texto", "QTextEdit", "📄 Área Texto", 280, 90),
    ("Lista", "QComboBox", "🔽 Lista", 190, 30),
    ("Casilla", "QCheckBox", "☑️ Casilla", 180, 26),
    ("Progreso", "QProgressBar", "📊 Progreso", 240, 22),
    ("Submódulo", "SubmoduleSlot", "🧩 Contenedor Submódulo", 300, 140),
]

MULTITOOL_SNIPPETS = {
    "🔔 Notificación App": (
        '        app = getattr(self.context, "app", None) if self.context else None\n'
        '        if app and hasattr(app, "mostrar_notificacion"):\n'
        '            app.mostrar_notificacion("Título", "Mensaje de notificación", tipo="info")\n'
    ),
    "⚠️ Alerta / Confirmación": (
        '        from PyQt6.QtWidgets import QMessageBox\n'
        '        resp = QMessageBox.question(self, "Confirmar", "¿Deseas continuar?")\n'
        '        if resp == QMessageBox.StandardButton.Yes:\n'
        '            pass\n'
    ),
    "📝 Log en Consola": (
        '        app = getattr(self.context, "app", None) if self.context else None\n'
        '        if app and hasattr(app, "logger"):\n'
        '            app.logger.log("INFO", "Acción ejecutada", modulo="MiModulo")\n'
    ),
    "📊 Barra de Estado": (
        '        app = getattr(self.context, "app", None) if self.context else None\n'
        '        if app and hasattr(app, "set_status"):\n'
        '            app.set_status("Proceso completado correctamente")\n'
    ),
    "🧵 Hilo QThread": (
        'from PyQt6.QtCore import QThread, pyqtSignal\n\n'
        'class MiTareaWorker(QThread):\n'
        '    terminado = pyqtSignal(str)\n'
        '    def run(self):\n'
        '        self.terminado.emit("OK")\n'
    ),
}

CREATOR_QSS = """
    QDialog, QWidget {
        background-color: #11131c;
        color: #f8fafc;
        font-family: 'Segoe UI', sans-serif;
        font-size: 11px;
    }
    QLabel, QCheckBox, QRadioButton {
        color: #f8fafc;
        background: transparent;
    }
    QScrollArea {
        background-color: transparent;
        border: none;
    }
    QFrame#IdeBar, QFrame#Panel {
        background-color: #181b28;
        border: 1px solid #2a2f45;
        border-radius: 6px;
    }
    QLabel#HeaderTitle {
        font-size: 13px;
        font-weight: 700;
        color: #ffffff;
    }
    QLabel#Section {
        font-size: 10px;
        font-weight: 700;
        color: #93c5fd;
        text-transform: uppercase;
    }
    QTreeWidget, QListWidget, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox {
        background-color: #0f111a;
        color: #f8fafc;
        border: 1px solid #2a2f45;
        border-radius: 5px;
        padding: 4px;
        font-size: 11px;
    }
    QHeaderView::section {
        background-color: #181b28;
        color: #f8fafc;
        border: none;
        border-bottom: 1px solid #2a2f45;
        padding: 4px;
        font-weight: 600;
    }
    QTreeWidget::item, QListWidget::item {
        color: #f1f5f9;
        padding: 2px 4px;
    }
    QTreeWidget::item:selected, QListWidget::item:selected {
        background-color: #4f46e5;
        color: #ffffff;
    }
    QMenu {
        background-color: #181b28;
        color: #f8fafc;
        border: 1px solid #38405e;
    }
    QMenu::item:selected {
        background-color: #4f46e5;
        color: #ffffff;
    }
    QTabWidget::pane {
        border: 1px solid #2a2f45;
        border-radius: 6px;
        background-color: #161925;
    }
    QTabBar::tab {
        background-color: #1e2233;
        color: #cbd5e1;
        padding: 5px 12px;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        margin-right: 2px;
        font-weight: 600;
        font-size: 11px;
    }
    QTabBar::tab:selected {
        background-color: #4f46e5;
        color: #ffffff;
    }
    QPushButton {
        background-color: #252a3d;
        color: #f8fafc;
        border: 1px solid #38405e;
        border-radius: 5px;
        padding: 4px 9px;
        font-size: 11px;
        font-weight: 600;
    }
    QPushButton:hover {
        background-color: #323952;
    }
    QPushButton:disabled {
        background-color: #1b1e2b;
        color: #64748b;
        border-color: #232738;
    }
    QPushButton#Accent {
        background-color: #4f46e5;
        border-color: #6366f1;
        color: #ffffff;
    }
    QPushButton#Accent:hover {
        background-color: #6366f1;
    }
    QPushButton#Success {
        background-color: #059669;
        border-color: #10b981;
        color: #ffffff;
    }
    QPushButton#Success:hover {
        background-color: #10b981;
    }
"""


def normalizar_id_modulo(nombre: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9_]+", "_", nombre.strip().lower())
    limpio = re.sub(r"_+", "_", limpio).strip("_")
    if not limpio or limpio[0].isdigit():
        limpio = f"mod_{limpio}" if limpio else "nuevo_modulo"
    return limpio


def a_pascal_case(texto: str) -> str:
    partes = [p for p in re.split(r"[^a-zA-Z0-9]+", texto) if p]
    if not partes:
        return "TabPrincipal"
    return "".join(p.capitalize() for p in partes)
