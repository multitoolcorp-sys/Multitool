import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

def abrir_dialogo_forma_avatar(parent, config, ruta_usuario, colores, font_family, on_success_callback=None):
    """Diálogo modal para cambiar la forma geométrica del avatar (círculo, cuadrado, redondeado)"""
    shapes = [("🔴 Circular", "circle"), ("⬛ Cuadrado", "square"), ("⏹️ Bordes Redondeados", "rounded")]
    dlg = QDialog(parent)
    dlg.setWindowTitle("📐 Forma del Avatar")
    dlg.setFixedSize(320, 190)
    dlg.setStyleSheet(f"background: {colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 10px;")
    
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(12)
    
    lbl_info = QLabel("Selecciona la forma del avatar:")
    lbl_info.setFont(QFont(font_family, 10, QFont.Weight.Bold))
    lbl_info.setStyleSheet("color: white;")
    lay.addWidget(lbl_info)
    
    combo = QComboBox()
    combo.setStyleSheet(f"""
        QComboBox {{
            background: {colores.get('bg_terciario', '#2D2D3D')};
            color: white;
            padding: 8px;
            border-radius: 6px;
        }}
        QComboBox QAbstractItemView {{
            background: {colores.get('bg_terciario', '#2D2D3D')};
            color: white;
            selection-background-color: {colores.get('acento', '#6366F1')};
        }}
    """)
    for label, s_code in shapes:
        combo.addItem(label, s_code)
        
    curr_shape = config.get("avatar_shape", "circle")
    idx = combo.findData(curr_shape)
    if idx != -1:
        combo.setCurrentIndex(idx)
        
    lay.addWidget(combo)
    
    btn_apply = QPushButton("Aplicar Forma")
    btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_apply.setStyleSheet(f"background: {colores.get('acento', '#6366F1')}; color: white; padding: 8px; border-radius: 6px; font-weight: bold; border: none;")
    
    def _apply():
        new_shape = combo.currentData()
        config["avatar_shape"] = new_shape
        from controlador.auth.crypto_utils import process_config_for_save
        with open(Path(ruta_usuario) / "config.json", "w", encoding="utf-8") as f:
            json.dump(process_config_for_save(config), f, indent=4)
        if callable(on_success_callback):
            on_success_callback(config)
        dlg.accept()
        QMessageBox.information(parent, "Forma de Avatar", "¡La forma del avatar ha sido actualizada correctamente!")
        
    btn_apply.clicked.connect(_apply)
    lay.addWidget(btn_apply)
    dlg.exec()
