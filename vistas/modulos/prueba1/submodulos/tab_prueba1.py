# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGroupBox, QLabel, QLineEdit,
    QProgressBar, QPushButton, QSlider, QSpinBox, QTableWidget, QTextEdit
)


class TabPrueba1(QFrame):
    """Módulo prueba1 generado con Modo Creador (mode MT)."""

    def __init__(self, parent=None, context=None, **kwargs):
        super().__init__(parent)
        self.context = context
        self._init_ui()

    def _init_ui(self):
        # <UI_START>
        self.setStyleSheet("QFrame { background: transparent; } QLabel, QCheckBox, QPushButton, QGroupBox { color: #ffffff; }")
        self.setMinimumSize(560, 400)

        self.lbl_titulo = QLabel("Mi Módulo", self)
        self.lbl_titulo.setStyleSheet("font-size: 17px; font-weight: 700; color: #ffffff;")
        self.lbl_titulo.setGeometry(344, 200, 320, 160)

        self.lbl_desc = QLabel("Arrastra o edita componentes en el lienzo.", self)
        self.lbl_desc.setStyleSheet("font-size: 12px; color: #ffffff;")
        self.lbl_desc.setGeometry(16, 56, 320, 24)

        self.ent_entrada = QLineEdit("", self)
        self.ent_entrada.setStyleSheet("background-color: #181b28; color: #ffffff; border: 1px solid #38405e; border-radius: 5px; padding: 5px;")
        self.ent_entrada.setPlaceholderText("Escribe aquí...")
        self.ent_entrada.setGeometry(16, 88, 240, 32)

        self.btn_accion = QPushButton("Ejecutar", self)
        self.btn_accion.setStyleSheet("background-color: #4f46e5; color: #ffffff; border-radius: 6px; padding: 6px 12px; font-weight: 600;")
        self.btn_accion.setGeometry(16, 132, 150, 34)

        # <UI_END>
