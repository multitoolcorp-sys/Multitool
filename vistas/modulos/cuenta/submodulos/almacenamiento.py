"""
almacenamiento.py - Submódulo Gestor de Almacenamiento, Cuotas y Limpieza de Caché de MultiTool
Permite supervisar el espacio en disco utilizado por cada módulo y liberar espacio con 1 clic.
"""
import os
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QProgressBar, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class TabAlmacenamientoGUI(QWidget):
    """Submódulo para auditar el uso de disco por módulo y limpiar archivos temporales"""
    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent if isinstance(parent, QWidget) else None)
        self.context = context
        self.colores = colores or (getattr(context.app, "COLORES", {}) if context and hasattr(context, "app") else {})

        self.ruta_usuario = Path(getattr(self.context, "ruta_usuario", ".")) if self.context else Path(".")
        self.rutas_auditadas = {}
        self.init_ui()
        self.calcular_espacio()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(20, 20, 20, 20)
        main_lay.setSpacing(16)

        # Header
        top_bar = QHBoxLayout()
        header_text = QVBoxLayout()
        lbl_titulo = QLabel("💾 Almacenamiento & Cuotas")
        lbl_titulo.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')};")

        lbl_desc = QLabel("Audita el tamaño ocupado por notas, bases de datos, descargas y libera espacio.")
        lbl_desc.setFont(QFont("Segoe UI", 10))
        lbl_desc.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#A0A0A0')};")
        header_text.addWidget(lbl_titulo)
        header_text.addWidget(lbl_desc)

        # Botones de acción
        btn_box = QHBoxLayout()
        btn_recalcular = QPushButton("🔄 Recalcular")
        btn_recalcular.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_recalcular.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: {self.colores.get('fg_principal', '#FFFFFF')};
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
                padding: 9px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn_recalcular.clicked.connect(self.calcular_espacio)

        btn_limpiar = QPushButton("🧹 Limpiar Temporales")
        btn_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_limpiar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                border-radius: 8px;
                padding: 9px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('acento_hover', '#4F46E5')};
            }}
        """)
        btn_limpiar.clicked.connect(self.limpiar_temporales)

        btn_box.addWidget(btn_recalcular)
        btn_box.addWidget(btn_limpiar)

        top_bar.addLayout(header_text)
        top_bar.addStretch()
        top_bar.addLayout(btn_box)
        main_lay.addLayout(top_bar)

        # Banner de Espacio Total
        self.banner_total = QFrame()
        bg_card = self.colores.get('bg_secundario', '#1E1E2E')
        self.banner_total.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_card};
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        banner_lay = QVBoxLayout(self.banner_total)
        self.lbl_total_mb = QLabel("Calculando espacio total...")
        self.lbl_total_mb.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_total_mb.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')}; border: none;")
        banner_lay.addWidget(self.lbl_total_mb)

        self.bar_global = QProgressBar()
        self.bar_global.setRange(0, 100)
        self.bar_global.setValue(0)
        self.bar_global.setTextVisible(False)
        self.bar_global.setFixedHeight(10)
        self.bar_global.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background-color: {self.colores.get('acento', '#6366F1')};
                border-radius: 5px;
            }}
        """)
        banner_lay.addWidget(self.bar_global)
        main_lay.addWidget(self.banner_total)

        # Scroll de desglose por carpetas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }}")

        container = QWidget()
        self.cards_layout = QVBoxLayout(container)
        self.cards_layout.setContentsMargins(0, 8, 0, 8)
        self.cards_layout.setSpacing(10)

        scroll.setWidget(container)
        main_lay.addWidget(scroll, 1)

    def _obtener_tamano_carpeta(self, ruta: Path) -> int:
        total = 0
        if not ruta.exists():
            return 0
        try:
            if ruta.is_file():
                return ruta.stat().st_size
            for p in ruta.rglob("*"):
                if p.is_file():
                    total += p.stat().st_size
        except Exception:
            pass
        return total

    def calcular_espacio(self):
        # Carpetas clave a auditar
        directorios = {
            "📝 Notas & Snapshots": self.ruta_usuario / "notas",
            "🗄️ Bases de Datos Locales": self.ruta_usuario / "basedatos",
            "⬇️ Descargas & Archivos": self.ruta_usuario / "descargas",
            "🎵 Audios & Multimedia": self.ruta_usuario / "ambiental_sounds",
            "🔑 Bóveda de Claves": self.ruta_usuario / "boveda",
            "🗑️ Papelera de Reciclaje": self.ruta_usuario / "papelera",
            "⚡ Caché & Temporales": self.ruta_usuario / ".cache",
            "📊 Historial & Auditoría": self.ruta_usuario / "actividad",
        }

        # Vaciar layout anterior
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        total_bytes = 0
        detalles = []
        for nombre, ruta in directorios.items():
            bytes_ocupados = self._obtener_tamano_carpeta(ruta)
            total_bytes += bytes_ocupados
            detalles.append((nombre, ruta, bytes_ocupados))

        total_mb = total_bytes / (1024 * 1024)
        self.lbl_total_mb.setText(f"Total utilizado por MultiTool: {total_mb:.2f} MB")
        self.bar_global.setValue(min(100, int(total_mb)))

        bg_card = self.colores.get('bg_secundario', '#1E1E2E')
        for nombre, ruta, tam_bytes in detalles:
            tam_mb = tam_bytes / (1024 * 1024)
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_card};
                    border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                    border-radius: 8px;
                    padding: 10px 14px;
                }}
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(6, 6, 6, 6)

            info_col = QVBoxLayout()
            lbl_nom = QLabel(nombre)
            lbl_nom.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            lbl_nom.setStyleSheet(f"color: {self.colores.get('fg_principal', '#FFFFFF')}; border: none;")
            
            lbl_ruta = QLabel(str(ruta.name if ruta.exists() else "(No inicializada aún)"))
            lbl_ruta.setFont(QFont("Segoe UI", 9))
            lbl_ruta.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#A0A0A0')}; border: none;")
            info_col.addWidget(lbl_nom)
            info_col.addWidget(lbl_ruta)

            lbl_tam = QLabel(f"{tam_mb:.2f} MB" if tam_mb >= 0.01 else f"{tam_bytes} bytes")
            lbl_tam.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            color_tam = self.colores.get('acento', '#6366F1') if tam_mb < 50 else self.colores.get('advertencia', '#F59E0B')
            lbl_tam.setStyleSheet(f"color: {color_tam}; border: none;")

            c_lay.addLayout(info_col)
            c_lay.addStretch()
            c_lay.addWidget(lbl_tam)

            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def limpiar_temporales(self):
        confirm = QMessageBox.question(
            self, "Confirmar Limpieza",
            "¿Deseas vaciar la memoria caché y los archivos temporales de la aplicación?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            liberados = 0
            cache_dirs = [
                self.ruta_usuario / ".cache",
                self.ruta_usuario / "temp",
                self.ruta_usuario / "snapshots_temp"
            ]
            for c in cache_dirs:
                if c.exists():
                    try:
                        liberados += self._obtener_tamano_carpeta(c)
                        shutil.rmtree(c, ignore_errors=True)
                        c.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        pass
            mb = liberados / (1024 * 1024)
            QMessageBox.information(self, "Limpieza Completada", f"Se han liberado exitosamente {mb:.2f} MB de memoria temporal.")
            self.calcular_espacio()

    def actualizar_tema(self, colores):
        if isinstance(colores, dict):
            self.colores = colores
            bg_p = self.colores.get('bg_principal', '#121218')
            self.setStyleSheet(f"background-color: {bg_p}; color: white;")
            self.calcular_espacio()
