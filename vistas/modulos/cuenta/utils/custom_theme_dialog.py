import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QComboBox, QMessageBox, QGridLayout, QFileDialog, QColorDialog, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

PRESETS_TEMAS = {
    "🌌 Cyberpunk Neon": {
        "bg_principal": "#0F0F17", "bg_secundario": "#1A1A26", "bg_terciario": "#262638",
        "fg_principal": "#FFFFFF", "fg_secundario": "#A0A5B5", "acento": "#F43F5E",
        "acento_hover": "#FB7185", "exito": "#10B981", "error": "#EF4444", "advertencia": "#F59E0B"
    },
    "💎 Midnight Obsidian": {
        "bg_principal": "#090D16", "bg_secundario": "#111827", "bg_terciario": "#1F2937",
        "fg_principal": "#F9FAFB", "fg_secundario": "#9CA3AF", "acento": "#3B82F6",
        "acento_hover": "#60A5FA", "exito": "#10B981", "error": "#EF4444", "advertencia": "#F59E0B"
    },
    "🍃 Emerald Forest": {
        "bg_principal": "#061A14", "bg_secundario": "#0B2920", "bg_terciario": "#133E31",
        "fg_principal": "#ECFDF5", "fg_secundario": "#6EE7B7", "acento": "#10B981",
        "acento_hover": "#34D399", "exito": "#059669", "error": "#F87171", "advertencia": "#FBBF24"
    },
    "🔮 Dracula Purple": {
        "bg_principal": "#1E1E2E", "bg_secundario": "#282A36", "bg_terciario": "#44475A",
        "fg_principal": "#F8F8F2", "fg_secundario": "#6272A4", "acento": "#BD93F9",
        "acento_hover": "#FF79C6", "exito": "#50FA7B", "error": "#FF5555", "advertencia": "#F1FA8C"
    },
    "☀️ Minimal Light": {
        "bg_principal": "#F8FAFC", "bg_secundario": "#FFFFFF", "bg_terciario": "#E2E8F0",
        "fg_principal": "#0F172A", "fg_secundario": "#64748B", "acento": "#6366F1",
        "acento_hover": "#4F46E5", "exito": "#16A34A", "error": "#DC2626", "advertencia": "#D97706"
    },
    "🌅 Sunset Orange": {
        "bg_principal": "#181111", "bg_secundario": "#261A1A", "bg_terciario": "#3B2727",
        "fg_principal": "#FFF7ED", "fg_secundario": "#FDBA74", "acento": "#F97316",
        "acento_hover": "#FB923C", "exito": "#10B981", "error": "#EF4444", "advertencia": "#FBBF24"
    }
}


class CustomThemeDialog(QDialog):
    """Diálogo para personalizar la paleta de colores del tema (Theme Engine 2.0)"""
    def __init__(self, parent, colores_init, colores_base):
        super().__init__(parent)
        self.setWindowTitle("🎨 Theme Engine 2.0 - Paleta de Colores")
        self.setMinimumWidth(500)
        self.setMinimumHeight(520)
        self.colores_base = colores_base or {}
        self.colores_resultado = dict(self.colores_base)
        if isinstance(colores_init, dict):
            self.colores_resultado.update(colores_init)

        self.preview_labels = {}

        self.setStyleSheet("""
            QDialog {
                background-color: #121218;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
            }
            QComboBox {
                background-color: #262638;
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #262638;
                color: #FFFFFF;
                selection-background-color: #6366F1;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl_desc = QLabel("🎨 Selecciona un Preset oficial o personaliza cada color:")
        lbl_desc.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 13px; margin-bottom: 2px;")
        layout.addWidget(lbl_desc)

        # Combo Presets
        preset_layout = QHBoxLayout()
        lbl_p_tag = QLabel("Presets Oficiales:")
        lbl_p_tag.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        preset_layout.addWidget(lbl_p_tag)
        self.combo_presets = QComboBox()
        self.combo_presets.addItem(" Personalizado")
        for name in PRESETS_TEMAS.keys():
            self.combo_presets.addItem(name)
        self.combo_presets.currentTextChanged.connect(self._aplicar_preset)
        preset_layout.addWidget(self.combo_presets, 1)
        layout.addLayout(preset_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: #181824; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); } QWidget { background-color: #181824; }")

        content = QWidget()
        content.setStyleSheet("background-color: #181824; border-radius: 8px;")
        form_grid = QGridLayout(content)
        form_grid.setSpacing(10)

        self.color_keys = [
            ("bg_principal", "Fondo Principal"),
            ("bg_secundario", "Fondo Secundario"),
            ("bg_terciario", "Fondo Terciario / Tarjetas"),
            ("fg_principal", "Texto Principal"),
            ("fg_secundario", "Texto Secundario"),
            ("acento", "Color de Acento / Destacado"),
            ("acento_hover", "Acento (Hover)"),
            ("exito", "Mensajes de Éxito"),
            ("error", "Mensajes de Error"),
            ("advertencia", "Mensajes de Advertencia"),
        ]

        for idx, (key, label_text) in enumerate(self.color_keys):
            val = self.colores_resultado.get(key, "#6366F1")

            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 10))
            lbl.setStyleSheet("color: #FFFFFF; font-weight: 500;")

            preview = QLabel(val)
            preview.setFixedSize(95, 26)
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            self.preview_labels[key] = preview
            self._update_preview_style(preview, val)

            btn = QPushButton("Cambiar")
            btn.setFixedSize(75, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores_base.get('bg_terciario', '#2D2D3D')};
                    color: white;
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 4px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {self.colores_base.get('acento', '#6366F1')};
                }}
            """)
            btn.clicked.connect(lambda checked, k=key, p=preview: self._seleccionar_color(k, p))

            form_grid.addWidget(lbl, idx, 0)
            form_grid.addWidget(preview, idx, 1)
            form_grid.addWidget(btn, idx, 2)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Botones Exportar e Importar Tema (.mttheme)
        theme_io_lay = QHBoxLayout()
        theme_io_lay.setSpacing(10)

        btn_export = QPushButton("📥 Exportar Tema (.mttheme)")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores_base.get('bg_terciario', '#2D2D3D')};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{ border-color: {self.colores_base.get('acento', '#6366F1')}; }}
        """)
        btn_export.clicked.connect(self._exportar_tema)
        theme_io_lay.addWidget(btn_export)

        btn_import = QPushButton("📤 Importar Tema (.mttheme)")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores_base.get('bg_terciario', '#2D2D3D')};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{ border-color: {self.colores_base.get('acento', '#6366F1')}; }}
        """)
        btn_import.clicked.connect(self._importar_tema)
        theme_io_lay.addWidget(btn_import)
        theme_io_lay.addStretch()
        layout.addLayout(theme_io_lay)

        # Botones de acción
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFixedSize(100, 32)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #AAA;
                border: 1px solid #444;
                border-radius: 6px;
            }
            QPushButton:hover { color: white; border-color: #666; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Guardar Tema")
        btn_save.setFixedSize(110, 32)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores_base.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {self.colores_base.get('acento_hover', '#818CF8')};
            }}
        """)
        btn_save.clicked.connect(self.accept)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def _aplicar_preset(self, preset_name):
        if preset_name in PRESETS_TEMAS:
            data = PRESETS_TEMAS[preset_name]
            self.colores_resultado.update(data)
            for k, hex_val in data.items():
                if k in self.preview_labels:
                    self._update_preview_style(self.preview_labels[k], hex_val)

    def _exportar_tema(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar Tema", "mi_tema.mttheme", "Archivos de Tema (*.mttheme *.json)")
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(self.colores_resultado, f, indent=4)
                QMessageBox.information(self, "Éxito", "¡Tema exportado correctamente!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo exportar el tema:\n{e}")

    def _importar_tema(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Importar Tema", "", "Archivos de Tema (*.mttheme *.json)")
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.colores_resultado.update(data)
                    for k, hex_val in data.items():
                        if k in self.preview_labels and isinstance(hex_val, str):
                            self._update_preview_style(self.preview_labels[k], hex_val)
                    QMessageBox.information(self, "Éxito", "¡Tema importado y aplicado correctamente!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo importar el tema:\n{e}")

    def _update_preview_style(self, preview_label, hex_color):
        try:
            color = QColor(hex_color)
            text_col = "#000000" if color.lightness() > 128 else "#FFFFFF"
        except Exception:
            text_col = "#FFFFFF"
        preview_label.setText(str(hex_color).upper())
        preview_label.setStyleSheet(f"""
            QLabel {{
                background-color: {hex_color};
                color: {text_col};
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 4px;
            }}
        """)

    def _seleccionar_color(self, key, preview_label):
        actual = QColor(self.colores_resultado.get(key, "#6366F1"))
        color = QColorDialog.getColor(actual, self, f"Seleccionar color para {key}")
        if color.isValid():
            hex_val = color.name()
            self.colores_resultado[key] = hex_val
            self._update_preview_style(preview_label, hex_val)
