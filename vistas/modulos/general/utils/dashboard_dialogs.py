import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QFrame, QInputDialog, QFileDialog, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class DialogoConfigurarIconos(QDialog):
    """Diálogo para configurar iconos de los accesos rápidos con URL, imagen o reset."""
    def __init__(self, parent, modulos, ruta_usuario, colores, on_guardado=None):
        super().__init__(parent)
        self.modulos = modulos
        self.ruta_usuario = Path(ruta_usuario)
        self.colores = colores
        self.on_guardado = on_guardado
        self.cfg_file = self.ruta_usuario / "iconos_modulos.json"
        
        self.iconos_actuales = {}
        if self.cfg_file.exists():
            try:
                with open(self.cfg_file, "r", encoding="utf-8") as f:
                    self.iconos_actuales = json.load(f)
            except Exception:
                pass
                
        self.setWindowTitle("Configurar Iconos de Accesos Rápidos")
        self.setMinimumSize(540, 480)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores.get('bg_principal', '#121218')};
                color: white;
            }}
        """)
        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        lbl_tit = QLabel("🚀 CONFIGURAR ICONOS DEL LANZADOR")
        lbl_tit.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        lay.addWidget(lbl_tit)

        lbl_desc = QLabel("Personaliza los iconos de cada módulo indicando una URL web, una imagen local o restaurando su icono original.")
        lbl_desc.setFont(QFont("Segoe UI", 9))
        lbl_desc.setStyleSheet("color: #AAB0B8;")
        lbl_desc.setWordWrap(True)
        lay.addWidget(lbl_desc)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cont = QWidget()
        cont_lay = QVBoxLayout(cont)
        cont_lay.setContentsMargins(0, 0, 0, 0)
        cont_lay.setSpacing(8)

        self.filas = {}
        for mod in self.modulos:
            m_name = mod.get("name", "")
            if not m_name or m_name.lower() == "inicio":
                continue
            
            row_frame = QFrame()
            row_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }}
            """)
            r_lay = QHBoxLayout(row_frame)
            r_lay.setContentsMargins(12, 8, 12, 8)
            r_lay.setSpacing(10)

            val_actual = self.iconos_actuales.get(m_name.lower(), mod.get("icon", "🧩"))

            lbl_mod = QLabel(f"{m_name.capitalize()}")
            lbl_mod.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl_mod.setStyleSheet("color: white;")
            lbl_mod.setFixedWidth(120)
            r_lay.addWidget(lbl_mod)

            lbl_val = QLabel(str(val_actual)[:30] + ("..." if len(str(val_actual)) > 30 else ""))
            lbl_val.setFont(QFont("Consolas", 8))
            lbl_val.setStyleSheet("color: #AAB0B8;")
            r_lay.addWidget(lbl_val, 1)

            btn_url = QPushButton("🌐 URL")
            btn_url.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_url.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border: none; border-radius: 4px; padding: 5px 10px; font-weight: bold;")
            btn_url.clicked.connect(lambda _, n=m_name.lower(), l=lbl_val: self._pedir_url(n, l))
            r_lay.addWidget(btn_url)

            btn_img = QPushButton("🖼️ Imagen")
            btn_img.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_img.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; border: none; border-radius: 4px; padding: 5px 10px; font-weight: bold;")
            btn_img.clicked.connect(lambda _, n=m_name.lower(), l=lbl_val: self._pedir_img(n, l))
            r_lay.addWidget(btn_img)

            btn_rst = QPushButton("🔄 Reset")
            btn_rst.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_rst.setStyleSheet("background-color: transparent; color: #F87171; border: 1px solid #F87171; border-radius: 4px; padding: 4px 8px; font-size: 10px;")
            btn_rst.clicked.connect(lambda _, n=m_name.lower(), l=lbl_val, def_v=mod.get("icon", "🧩"): self._reset_icon(n, l, def_v))
            r_lay.addWidget(btn_rst)

            cont_lay.addWidget(row_frame)

        scroll.setWidget(cont)
        lay.addWidget(scroll, 1)

        b_box = QHBoxLayout()
        b_box.addStretch()
        btn_close = QPushButton("💾 Guardar y Aplicar")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white; border: none; border-radius: 8px;
                padding: 8px 24px;
            }}
            QPushButton:hover {{ background-color: #4F46E5; }}
        """)
        btn_close.clicked.connect(self._guardar_y_cerrar)
        b_box.addWidget(btn_close)
        lay.addLayout(b_box)

    def _pedir_url(self, mod_key, label):
        url, ok = QInputDialog.getText(self, "Icono por URL", f"Introduce la URL de la imagen para el módulo {mod_key}:")
        if ok and url.strip():
            self.iconos_actuales[mod_key] = url.strip()
            label.setText(url.strip()[:30] + "...")

    def _pedir_img(self, mod_key, label):
        f, _ = QFileDialog.getOpenFileName(self, "Seleccionar Imagen de Icono", "", "Imágenes (*.png *.ico *.jpg *.jpeg *.svg *.bmp)")
        if f:
            self.iconos_actuales[mod_key] = str(Path(f).resolve())
            label.setText(Path(f).name)

    def _reset_icon(self, mod_key, label, default_val):
        if mod_key in self.iconos_actuales:
            del self.iconos_actuales[mod_key]
        label.setText(str(default_val))

    def _guardar_y_cerrar(self):
        try:
            with open(self.cfg_file, "w", encoding="utf-8") as f:
                json.dump(self.iconos_actuales, f, indent=4)
        except Exception as e:
            print(f"Error guardando iconos: {e}")
        self.accept()
        if self.on_guardado:
            self.on_guardado()
